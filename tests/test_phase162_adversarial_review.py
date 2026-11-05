# -*- coding: utf-8 -*-
"""
tests/test_phase162_adversarial_review.py
Adversarial Stress & Edge Case Test Suite for Milestone 3:
Institutional Execution OMS & Microstructure Layer (Phase 162, Features F790-F794, Release R163).

Probes:
- F790: 1,000 randomized micro-states, simplex exactness sum(p_k) == 1.0, priority ordering of guards.
- F791: L3 LOB crossed books, odd-cent ATS crossings, huge notionals, zero/negative pricing.
- F792: 5D Joseph-stabilized covariance under near-singular P, zero H, extreme shocks (+-5000 bps).
- F793: Asymmetric Leland multipliers under extreme z-scores (+-100), extreme vols, instant bypass bounds.
- F794: 8-Safety Gates, Gate 8 inverse hedge regimes, and 32-thread high-concurrency determinism.
"""

from __future__ import annotations

import math
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.execution.rl_execution_agent import (
    ExecutionState,
    ContinuousAction,
    ExecutionAction,
    Phase162ExecutionActionResult,
    Phase162RLExecutionAgent,
    evaluate_execution_action_phase162,
)
from src.core.fast_lob_engine import (
    Phase162FastLOBEngine,
    Phase162ZeroCopyRingBuffer,
)
from src.execution.slippage_feedback import (
    Phase162SlippageFeedbackEngine,
    Phase162OnlineKalmanFilter,
)
from src.execution.turnover_optimizer import (
    Phase162TurnoverOptimizer,
    AsymmetricLelandMultipliers,
)
from src.execution.oms_engine import (
    Phase162ExecutionOMSEngine,
    _is_invalid_or_nonpositive_price,
)
from src.execution.lockless_oms_dispatcher import (
    Phase162LocklessOMSDispatcher,
    DispatchOrder,
)


class TestPhase162AdversarialReview:
    """Adversarial challenger suite testing failure modes and boundary limits."""

    def test_adv01_simplex_conservation_and_sanitization_1000_states(self):
        """ADV01 [F790]: Assert strict simplex sum(p_k) == 1.0 across 1,000 perturbed & invalid states."""
        agent = Phase162RLExecutionAgent()
        rng = np.random.default_rng(162)

        for i in range(1000):
            # Generate random and extreme values
            t_ratio = float(rng.uniform(-0.5, 1.5))
            inv_ratio = float(rng.uniform(-0.5, 1.5))
            spread = float(rng.uniform(-50.0, 500.0))
            obi = float(rng.uniform(-2.0, 2.0))
            vpin = float(rng.uniform(-0.5, 1.5))
            vol = float(rng.uniform(-0.1, 1.0))

            # Inject NaN / Inf occasionally
            if i % 50 == 0:
                spread = float("nan")
            elif i % 50 == 1:
                vpin = float("inf")
            elif i % 50 == 2:
                t_ratio = float("-inf")

            st = ExecutionState(
                time_ratio=t_ratio,
                inventory_ratio=inv_ratio,
                spread_bps=spread,
                obi=obi,
                vpin=vpin,
                volatility=vol,
            )

            res = agent.evaluate_execution_action_phase162(st)
            assert isinstance(res, Phase162ExecutionActionResult)
            assert str(res) in ("TACTICAL_PAUSE", "AGGRESSIVE_TAKER", "PASSIVE_MAKER", "MID_PEG")

            # Unpack test
            simplex, ratio = res
            assert isinstance(simplex, dict)
            assert set(simplex.keys()) == {"lit_maker", "lit_taker", "dark_midpoint", "tactical_pause"}
            assert all(math.isfinite(v) and v >= 0.0 for v in simplex.values())
            assert math.isclose(sum(simplex.values()), 1.0, abs_tol=1e-6)
            assert 0.0 <= ratio <= 1.0

    def test_adv02_terminal_urgency_vs_toxic_cascade_priority(self):
        """ADV02 [F790]: Stress test priority resolution between terminal clearance and toxic cascade."""
        agent = Phase162RLExecutionAgent()

        # Both terminal urgency AND toxic VPIN active:
        # Near market close (<= 5% left) with unliquidated inventory -> terminal clearance MUST take precedence!
        st_both = ExecutionState(
            time_ratio=0.98,
            inventory_ratio=0.40,
            spread_bps=10.0,
            obi=-0.5,
            vpin=0.85,  # Extreme toxicity
            volatility=0.04,
        )
        res_both = agent.evaluate_execution_action_phase162(st_both, vpin=0.85, tau_close=0.02, q_rem=0.40)
        assert res_both == "AGGRESSIVE_TAKER", "Terminal clearance MUST override pause to prevent overnight hold"

        # Mid-day (tau_close = 0.50) with toxic VPIN -> tactical pause MUST be triggered
        st_mid = ExecutionState(
            time_ratio=0.50,
            inventory_ratio=0.40,
            spread_bps=10.0,
            obi=-0.5,
            vpin=0.85,
            volatility=0.04,
        )
        res_mid = agent.evaluate_execution_action_phase162(st_mid, vpin=0.85, tau_close=0.50, q_rem=0.40)
        assert res_mid == "TACTICAL_PAUSE"

        # Zero inventory remaining -> ratio MUST be 0.0
        ratio_zero = agent.compute_meta_tranche_ratio(remaining_time=0.02, remaining_inventory=0.0)
        assert ratio_zero == 0.0

    def test_adv03_joseph_stabilized_covariance_ill_conditioned_and_singular_shock(self):
        """ADV03 [F792]: Stress test Joseph covariance update on nearly singular matrix and zero noise."""
        engine = Phase162SlippageFeedbackEngine()

        # Construct nearly singular ill-conditioned 5D matrix
        eigs = np.array([1e-10, 1e-7, 1e-4, 0.1, 10.0])
        # Random orthogonal matrix Q
        rng = np.random.default_rng(42)
        A = rng.standard_normal((5, 5))
        Q, _ = np.linalg.qr(A)
        P_ill = Q @ np.diag(eigs) @ Q.T
        P_ill = 0.5 * (P_ill + P_ill.T)  # Ensure symmetric

        H = np.array([2.5, 1.0, 0.5, 0.2, 0.1])
        R_tiny = 1e-6

        # Update with extreme 5000 bps slippage shock
        P_next = engine.joseph_update_5d(P=P_ill, H=H, R=R_tiny, y=5000.0)

        # 1. Symmetry check
        assert np.allclose(P_next, P_next.T, atol=1e-10), "Joseph update must preserve exact symmetry"

        # 2. Positive definiteness check: all eigenvalues must be strictly positive
        next_eigs = np.linalg.eigvalsh(P_next)
        assert (next_eigs > 0.0).all(), f"Eigenvalues must be strictly positive, got min={next_eigs.min()}"

        # 3. Degenerate H = 0 test
        H_zero = np.zeros(5)
        P_zero_h = engine.joseph_update_5d(P=np.eye(5), H=H_zero, R=0.04, y=10.0)
        assert np.allclose(P_zero_h, P_zero_h.T, atol=1e-10)
        assert (np.linalg.eigvalsh(P_zero_h) > 0.0).all()

    def test_adv04_fast_lob_crossing_and_rebates_extreme_edge_cases(self):
        """ADV04 [F791]: Stress test L3 LOB crossed book, odd-cent ATS crossing, and huge notionals."""
        lob = Phase162FastLOBEngine(symbol="TEST_SYM")

        # Odd-cent midpoint crossing (e.g., bid=100.03, ask=100.05)
        cross_res = lob.execute_midpoint_crossing(symbol="TEST_SYM", qty=500, bid=100.03, ask=100.05)
        assert math.isclose(cross_res["exec_price"], 100.04, abs_tol=1e-4)
        assert cross_res["spread_saved_pct"] == 50.0

        # Inverted / crossed book (bid=105.0, ask=100.0)
        crossed = lob.execute_midpoint_crossing(symbol="TEST_SYM", qty=100, bid=105.0, ask=100.0)
        assert crossed["exec_price"] == 102.50

        # Strict rejection of zero and negative orders
        assert lob.submit_limit_order("ORD_BAD1", "TEST_SYM", "BUY", price=100.0, qty=0.0) is False
        assert lob.submit_limit_order("ORD_BAD2", "TEST_SYM", "BUY", price=-10.0, qty=10.0) is False

        # Huge notional rebate calculation (1 Trillion KRW = 1e12)
        rebate_huge = lob.compute_maker_rebate(notional=1e12, rebate_bps=2.5, venue="BZX")
        assert math.isclose(rebate_huge, 250_000_000.0, abs_tol=1e-2)

    def test_adv05_asymmetric_leland_multipliers_extreme_z_and_volatilities(self):
        """ADV05 [F793]: Stress test Leland multipliers under z=+-100 and extreme volatilities."""
        opt = Phase162TurnoverOptimizer()

        # Extreme runner z = 100.0
        m_huge_pos = opt.compute_asymmetric_leland_multipliers(z_score=100.0)
        assert m_huge_pos["upper"] == 2.4, "Upper multiplier must clamp to 2.4"
        assert m_huge_pos["lower"] == 2.4

        # Extreme loser z = -100.0
        m_huge_neg = opt.compute_asymmetric_leland_multipliers(z_score=-100.0)
        assert m_huge_neg["upper"] == 0.5, "Upper multiplier must clamp to 0.5"
        assert m_huge_neg["lower"] == 0.5, "Lower multiplier must clamp to 0.5"

        # Volatility boundary tests
        bw_zero = opt.compute_dynamic_bandwidth(volatility=0.0)
        assert bw_zero == 0.005, "Zero vol must return minimum floor bandwidth"

        bw_huge = opt.compute_dynamic_bandwidth(volatility=100.0)
        assert bw_huge == 0.10, "Extreme vol must clamp to upper limit 0.10"

        # Instant bypass behavior
        assert opt.evaluate_rebalance_bypass(target_weight=0.01, current_weight=0.0) is True
        assert opt.evaluate_rebalance_bypass(target_weight=0.0, current_weight=0.01) is True
        # Inside buffer bands
        assert opt.evaluate_rebalance_bypass(target_weight=0.05, current_weight=0.05, lower_band=0.04, upper_band=0.06) is False
        # Outside buffer bands
        assert opt.evaluate_rebalance_bypass(target_weight=0.07, current_weight=0.05, lower_band=0.04, upper_band=0.06) is True

    def test_adv06_oms_8_safety_gates_and_concurrency_stress(self):
        """ADV06 [F794]: Stress test 8 Safety Gates and 32-thread concurrent order dispatching."""
        oms = Phase162ExecutionOMSEngine()
        dispatcher = Phase162LocklessOMSDispatcher()

        # Price sanity gate (Gate 2)
        assert _is_invalid_or_nonpositive_price(None) is True
        assert _is_invalid_or_nonpositive_price(float("nan")) is True
        assert _is_invalid_or_nonpositive_price(float("inf")) is True
        assert _is_invalid_or_nonpositive_price(0.0) is True
        assert _is_invalid_or_nonpositive_price(-50.0) is True
        assert _is_invalid_or_nonpositive_price(100.0) is False

        # Capital slice gate (Gate 1)
        assert oms.check_capital_slice_gate(25_000_000.0, max_slice=20_000_000.0) is False
        assert oms.check_capital_slice_gate(15_000_000.0, max_slice=20_000_000.0) is True

        # Circuit breaker gate (Gate 4)
        assert oms.check_circuit_breaker_gate("005930", change_pct=0.30) is False
        assert oms.check_circuit_breaker_gate("005930", change_pct=-0.30) is False
        assert oms.check_circuit_breaker_gate("005930", change_pct=0.10) is True

        # ADV gate (Gate 6)
        assert oms.check_adv_participation_gate(order_qty=20000, adv=1000000) is False  # 2.0% > 1.5%
        assert oms.check_adv_participation_gate(order_qty=10000, adv=1000000) is True   # 1.0% <= 1.5%

        # Gate 8 Synthetic Inverse Hedge
        h_kospi_bear = oms.evaluate_gate8_inverse_hedge(regime="BEAR_HIGH_VOL", market="KOSPI")
        assert h_kospi_bear["hedge_active"] is True
        assert h_kospi_bear["hedge_symbol"] == "114800"

        h_nasdaq_panic = oms.evaluate_gate8_inverse_hedge(regime="PANIC_CRISIS", market="NASDAQ")
        assert h_nasdaq_panic["hedge_active"] is True
        assert h_nasdaq_panic["hedge_symbol"] == "PSQ"

        h_bull = oms.evaluate_gate8_inverse_hedge(regime="BULL_LOW_VOL", market="SP500")
        assert h_bull["hedge_active"] is False

        # 32-thread high-concurrency stress test on LocklessOMSDispatcher
        errors: List[Exception] = []
        success_counts: List[bool] = []

        def worker(tid: int):
            try:
                for j in range(25):
                    order = DispatchOrder(
                        order_id=tid * 1000 + j,
                        symbol="005930",
                        side="BUY",
                        order_type="LIMIT",
                        quantity=5.0,
                        price=70000.0,
                    )
                    res = dispatcher.dispatch(order, async_mode=False)
                    success_counts.append(res.success)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(32)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Encountered concurrency errors: {errors}"
        assert len(success_counts) == 32 * 25
        assert all(success_counts)
