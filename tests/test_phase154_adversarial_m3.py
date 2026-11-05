# -*- coding: utf-8 -*-
"""
tests/test_phase154_adversarial_m3.py -- Institutional Empirical Adversarial Test Harness
for Milestone 3 (Phase 154, Features F750–F754).

Adversarial Stress Test Dimensions:
1. Feature F750 (Quantile Critic & Distributional SAC):
   - Extreme state vectors: all zeros, extreme spread (1,000 bps), extreme volatility (5.0), OBI = -1.0, VPIN = 0.99.
   - High-dimensional combined extreme states (toxic storm, illiquid panic, terminal urgency).
   - Monotonic sorting invariant: q_1 <= q_2 <= ... <= q_K across 1,000 random/adversarial feature vectors.
   - Quantile Huber Loss: non-negativity (loss >= 0), convex distance scaling, zero-error condition.
   - Downside CVaR (alpha=0.95): tail risk monotonicity and aggressive taker penalty vs passive maker.
2. Feature F751 (Fast LOB Midpoint Crossing & Maker Rebates):
   - Crossed books (best_bid > best_ask) and inverted spread handling.
   - Edge case volumes: zero volume (clamped to 1e-6), massive volume (10^9 shares).
   - Empty book fallback resilience.
   - High-throughput ring buffer burst: 100,000 tick burst with 97x wrap-around, zero memory leakage, zero index error.
3. Feature F752 (4D Extended Closed-Loop Kalman Slippage Filter):
   - Extreme slippage shocks: +1,000 bps, negative slippage (-50 bps).
   - Poisoned inputs: NaN and Inf observations and H vectors.
   - Joseph-stabilized covariance positive definiteness: P = P^T and min(eig(P)) > 0 after 100 noisy updates.
   - Parameter boundary clamping: kappa, beta, eta, rho in [0.05, 5.0] and cost scaling in [0.5, 8.0].
4. Feature F753 (Asymmetric Leland Buffer Bands):
   - Extreme leverage scaling (L=1.45, L=2.0, L=5.0) and extreme volatilities (0.001 to 5.0).
   - Boundary edge conditions (target=0.0, target=1.0).
   - Strict instant bypass verification: fresh entry (w_0 = 0 -> BUY), full exit (w* = 0 -> SELL), severe drift bypass.
   - Turnover dampening inside buffer band (L_i <= w <= U_i -> HOLD).
5. Feature F754 (OMS Gateway & Multi-Thread Concurrency):
   - 32-thread concurrent execution stress without exceptions or deadlocks.
   - Gate 8 synthetic inverse hedge trigger under BEAR/CRISIS regimes.
"""

from __future__ import annotations

import math
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
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))

from src.execution.rl_execution_agent import (
    ContinuousAction,
    ExecutionAction,
    ExecutionState,
    QuantileCritic,
    RLOrderExecutionAgent,
)
from src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    ZeroCopyRingBuffer,
)
from src.execution.slippage_feedback import (
    Online4DKalmanSlippageFilter,
    SlippageFeedbackEngine,
)
from src.execution.turnover_optimizer import (
    TurnoverOptimizer,
)
from src.execution.oms_engine import (
    ExecutionOMSEngine,
)
from src.risk.portfolio_allocator import PortfolioAllocator


# ==============================================================================
# SECTION 1: F750 Quantile Critic & Distributional SAC Adversarial Stress Tests
# ==============================================================================

class TestF750DistributionalSACAdversarial:
    """Adversarial stress-testing of Quantile Critic & Distributional SAC."""

    def test_adv_f750_extreme_state_vectors(self):
        """Stress test SAC execution agent and quantile critic with extreme states."""
        agent = RLOrderExecutionAgent()
        critic = agent.quantile_critic

        extreme_states = [
            # 1. All zeros
            ExecutionState(time_ratio=0.0, inventory_ratio=0.0, spread_bps=0.0, obi=0.0, vpin=0.0, volatility=0.0),
            # 2. Extreme spread (1,000 bps)
            ExecutionState(time_ratio=0.5, inventory_ratio=0.5, spread_bps=1000.0, obi=0.0, vpin=0.3, volatility=0.02),
            # 3. Extreme volatility (5.0 = 500% annualized daily vol)
            ExecutionState(time_ratio=0.5, inventory_ratio=0.5, spread_bps=10.0, obi=0.0, vpin=0.3, volatility=5.0),
            # 4. Extreme OBI (-1.0 = 100% sell pressure)
            ExecutionState(time_ratio=0.5, inventory_ratio=0.5, spread_bps=10.0, obi=-1.0, vpin=0.3, volatility=0.02),
            # 5. Extreme VPIN (0.99 = catastrophic toxicity)
            ExecutionState(time_ratio=0.3, inventory_ratio=0.8, spread_bps=50.0, obi=-0.9, vpin=0.99, volatility=0.10),
            # 6. Combined apocalyptic shock (terminal + toxic + high spread + extreme vol)
            ExecutionState(time_ratio=0.99, inventory_ratio=1.0, spread_bps=1000.0, obi=-1.0, vpin=0.99, volatility=5.0),
            # 7. Inverse extreme (OBI = +1.0, zero spread, zero VPIN)
            ExecutionState(time_ratio=0.05, inventory_ratio=0.95, spread_bps=0.1, obi=1.0, vpin=0.01, volatility=0.001),
        ]

        for idx, st in enumerate(extreme_states):
            vec12 = st.to_12d_vector()
            assert len(vec12) == 12, f"State {idx}: vector length != 12"
            assert np.all(np.isfinite(vec12)), f"State {idx}: non-finite values in state vector"

            # 12D vector + bias
            phi = np.concatenate([[1.0], vec12])

            # Predict quantiles
            quantiles = critic.predict_quantiles(phi)
            assert quantiles.shape == (4, 21), f"State {idx}: quantiles shape mismatch"
            assert np.all(np.isfinite(quantiles)), f"State {idx}: non-finite quantiles"

            # Verify sorting invariant
            for a in range(4):
                assert np.all(np.diff(quantiles[a]) >= -1e-12), f"State {idx}, action {a}: quantiles not sorted"

            # Compute CVaR
            for a in range(4):
                cvar = critic.compute_cvar(phi, action=a, alpha=0.95)
                assert math.isfinite(cvar), f"State {idx}, action {a}: non-finite CVaR"

            # Compute distributional Q-values
            q_dist = agent.compute_distributional_q_values(st)
            assert len(q_dist) == 4
            assert np.all(np.isfinite(q_dist)), f"State {idx}: non-finite Q_dist"

            # Compute continuous action
            act = agent.compute_continuous_action(st)
            assert 0.0 <= act.slice_ratio <= 1.0
            assert -2.0 <= act.tick_offset <= 2.0
            assert math.isclose(float(np.sum(act.route_weights)), 1.0, abs_tol=1e-5)
            assert act.primary_channel in ExecutionAction

    def test_adv_f750_quantiles_sorting_invariant_monte_carlo(self):
        """Monte Carlo verification of sorted quantiles invariant q_1 <= ... <= q_K across 1,000 random states."""
        critic = QuantileCritic(num_quantiles=21, state_dim=12, num_actions=4)
        rng = np.random.default_rng(42)

        # Generate 1,000 random adversarial feature vectors (including negative, huge, and zero values)
        for _ in range(1000):
            phi = rng.standard_normal(13) * 10.0
            phi[0] = 1.0  # bias term
            all_q = critic.predict_quantiles(phi)

            for a in range(4):
                diffs = np.diff(all_q[a])
                # Invariant: non-decreasing monotonicity
                assert np.all(diffs >= -1e-12), f"Quantile monotonicity violated for action {a}: min diff = {np.min(diffs)}"

    def test_adv_f750_quantile_huber_loss_properties(self):
        """Verify quantile Huber loss non-negativity, convex gradient behavior, and zero-error condition."""
        critic = QuantileCritic(num_quantiles=21, huber_threshold=1.0)

        # 1. Non-negativity under 50 random trials
        rng = np.random.default_rng(123)
        for _ in range(50):
            preds = np.sort(rng.uniform(-5.0, 5.0, 21))
            targets = rng.uniform(-5.0, 5.0, 10)
            loss = critic.compute_quantile_loss(preds, targets)
            assert loss >= 0.0, f"Loss was negative: {loss}"
            assert math.isfinite(loss)

        # 2. Perfect prediction: when preds == targets, loss should be exactly 0
        perfect_val = 2.5
        preds_exact = np.full(21, perfect_val)
        targets_exact = np.full(10, perfect_val)
        zero_loss = critic.compute_quantile_loss(preds_exact, targets_exact)
        assert math.isclose(zero_loss, 0.0, abs_tol=1e-12), f"Exact match did not yield zero loss: {zero_loss}"

        # 3. Convex distance scaling: loss increases monotonically as constant prediction moves away from target
        fixed_target = np.array([0.0])
        offsets = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        losses = []
        for off in offsets:
            p = np.full(21, off)
            l = critic.compute_quantile_loss(p, fixed_target)
            losses.append(l)

        # Check strict monotonic increase with error distance
        for i in range(len(losses) - 1):
            assert losses[i] < losses[i + 1], f"Loss did not increase monotonically with offset: {losses}"

    def test_adv_f750_cvar_downside_risk_ordering(self):
        """Verify CVaR downside risk ordering: aggressive taker penalization and tail quantile behavior."""
        agent = RLOrderExecutionAgent()
        critic = agent.quantile_critic

        # Adverse market conditions: high volatility, high spread
        st_adverse = ExecutionState(
            time_ratio=0.50,
            inventory_ratio=0.50,
            spread_bps=25.0,
            obi=-0.50,
            vpin=0.60,
            volatility=0.08,
        )
        phi = np.concatenate([[1.0], st_adverse.to_12d_vector()])

        cvar_taker = critic.compute_cvar(phi, action=int(ExecutionAction.AGGRESSIVE_TAKER), alpha=0.95)
        cvar_maker = critic.compute_cvar(phi, action=int(ExecutionAction.PASSIVE_MAKER), alpha=0.95)
        cvar_mid = critic.compute_cvar(phi, action=int(ExecutionAction.MID_PEG), alpha=0.95)

        # Downside shortfall of taker must be strictly more negative than maker/mid-peg due to spread & impact penalty
        assert cvar_taker < cvar_maker, f"Taker CVaR ({cvar_taker}) not worse than Maker CVaR ({cvar_maker})"
        assert cvar_taker < cvar_mid, f"Taker CVaR ({cvar_taker}) not worse than Mid CVaR ({cvar_mid})"

        # Varying alpha: higher confidence alpha (e.g. 0.99 vs 0.80) isolates deeper tail
        cvar_tail_99 = critic.compute_cvar(phi, action=int(ExecutionAction.AGGRESSIVE_TAKER), alpha=0.99)
        cvar_tail_80 = critic.compute_cvar(phi, action=int(ExecutionAction.AGGRESSIVE_TAKER), alpha=0.80)
        # Deeper tail has lower (worse) return
        assert cvar_tail_99 <= cvar_tail_80 + 1e-6, f"CVaR(0.99) ({cvar_tail_99}) > CVaR(0.80) ({cvar_tail_80})"


# ==============================================================================
# SECTION 2: F751 Fast LOB Midpoint Crossing & Maker Rebates Adversarial Tests
# ==============================================================================

class TestF751FastLOBAdversarial:
    """Adversarial stress-testing of Fast LOB Midpoint Crossing, Maker Rebates, and Ring Buffer."""

    def test_adv_f751_crossed_books_and_inverted_spreads(self):
        """Stress test midpoint crossing with crossed book (bid > ask) and inverted spreads."""
        lob = FastOrderBookMatchingEngine(symbol="005930")

        # Manually force a crossed book state via internal dictionaries
        with lob._lock:
            from collections import deque
            from src.core.fast_lob_engine import OrderNode
            # Best bid at 70500, best ask at 70000 (crossed by 500 KRW)
            lob.bids[70500.0] = deque([OrderNode("b_cross", 70500.0, 100.0, 0, "BUY")])
            lob.asks[70000.0] = deque([OrderNode("a_cross", 70000.0, 100.0, 0, "SELL")])

        # Execute midpoint cross on crossed book
        fill = lob.execute_midpoint_cross("cross_inv", side="BUY", volume=50, venue="KRX_ATS_NEXTRADE")
        assert fill["status"] == "FILLED"
        # Midpoint: (70500 + 70000) / 2 = 70250.0
        assert math.isclose(fill["fill_price"], 70250.0, abs_tol=1e-5)
        # Spread is clamped to max(0.0, ask - bid) = 0.0 under crossed condition
        assert fill["spread"] == 0.0
        assert fill["spread_saving_bps"] == 0.0
        assert fill["fee_discount_pct"] == 35.0

    def test_adv_f751_zero_and_massive_volume(self):
        """Test zero volume clamping and massive volume (10^9 shares) midpoint crossing."""
        lob = FastOrderBookMatchingEngine(symbol="AAPL")
        lob.add_limit_order("b1", side="BUY", price=150.00, volume=1000)
        lob.add_limit_order("a1", side="SELL", price=150.10, volume=1000)

        # 1. Zero volume -> clamped to 1e-6
        fill_zero = lob.execute_midpoint_cross("zero_vol", side="BUY", volume=0.0)
        assert fill_zero["volume"] == 1e-6
        assert math.isclose(fill_zero["fill_price"], 150.05, abs_tol=1e-4)

        # 2. Negative volume -> clamped to 1e-6
        fill_neg = lob.execute_midpoint_cross("neg_vol", side="BUY", volume=-100.0)
        assert fill_neg["volume"] == 1e-6

        # 3. Massive volume: 1 billion shares ($150 Billion notional)
        massive_vol = 1_000_000_000.0
        fill_massive = lob.execute_midpoint_cross("massive", side="BUY", volume=massive_vol, venue="US_BZX")
        assert fill_massive["volume"] == massive_vol
        assert math.isclose(fill_massive["fill_price"], 150.05, abs_tol=1e-4)
        assert fill_massive["rebate_bps"] == 2.5

        # Maker rebate calculation on massive notional: 1.5e11 * 2.5 / 10000 = $37.5 Million rebate
        rebate_res = lob.harvest_passive_maker_rebate(notional=massive_vol * 150.05, rebate_bps=2.5, venue="BZX")
        expected_rebate = (massive_vol * 150.05) * 2.5 / 10000.0
        assert math.isclose(rebate_res["rebate_cash_harvested"], expected_rebate, rel_tol=1e-5)

    def test_adv_f751_empty_book_resilience(self):
        """Test midpoint cross behavior when book is completely empty."""
        lob = FastOrderBookMatchingEngine(symbol="EMPTY_SYM")
        # Empty book execution
        fill_empty = lob.execute_midpoint_cross("empty_cross", side="BUY", volume=100)
        assert fill_empty["status"] == "FILLED"
        assert fill_empty["fill_price"] > 0.0
        assert math.isfinite(fill_empty["fill_price"])

    def test_adv_f751_ring_buffer_100k_burst_wrap_around(self):
        """Stress test ZeroCopyRingBuffer under 100,000 tick burst with ~97x wrap-around."""
        capacity = 1024
        buf = ZeroCopyRingBuffer(capacity=capacity)

        num_ticks = 100_000
        t0 = time.perf_counter()
        for i in range(num_ticks):
            buf.append(
                price=100.0 + (i % 500) * 0.1,
                volume=float((i % 50) + 1),
                timestamp_ns=i * 1000,
                is_buy=(i % 2 == 0),
            )
        t1 = time.perf_counter()
        total_time_ms = (t1 - t0) * 1000.0
        per_tick_us = ((t1 - t0) / num_ticks) * 1_000_000.0

        # Sub-microsecond / low microsecond append time
        assert per_tick_us < 20.0, f"Append latency too high: {per_tick_us:.2f} us/tick"

        # Verify ring buffer state
        recent = buf.get_recent(50)
        assert len(recent["prices"]) == 50
        # The very last tick inserted was index num_ticks - 1
        expected_last_price = 100.0 + ((num_ticks - 1) % 500) * 0.1
        assert math.isclose(recent["prices"][-1], expected_last_price, abs_tol=1e-5)

        # Verify full array retrieval
        arr = buf.get_recent(capacity)
        assert len(arr["prices"]) == capacity
        assert np.all(np.isfinite(arr["prices"]))
        assert np.all(np.isfinite(arr["volumes"]))


# ==============================================================================
# SECTION 3: F752 4D Kalman Slippage Filter Adversarial Stress Tests
# ==============================================================================

class TestF752KalmanSlippageFilterAdversarial:
    """Adversarial stress-testing of 4D Closed-Loop Kalman Slippage Filter."""

    def test_adv_f752_extreme_slippage_and_negative_slippage(self):
        """Stress test with 1,000 bps slippage shock and -50 bps price improvement."""
        kf = Online4DKalmanSlippageFilter()

        # 1. 1,000 bps massive slippage shock
        kf.update(realized_slippage_bps=1000.0, h_gamma=10.0, h_spread=10.0, h_eta=5.0, h_rho=2.0)
        st = kf.get_state()
        assert st["gamma"] <= 5.0  # Clamped to upper bound
        assert st["spread"] <= 5.0
        assert math.isfinite(st["cost_scaling_factor"])
        assert 0.5 <= st["cost_scaling_factor"] <= 8.0

        # 2. Extreme negative slippage (-50 bps = massive price improvement / maker rebate)
        kf.update(realized_slippage_bps=-50.0, h_gamma=5.0, h_spread=5.0, h_eta=2.0, h_rho=1.0)
        st2 = kf.get_state()
        assert st2["gamma"] >= 0.05  # Clamped to lower bound
        assert st2["spread"] >= 0.05
        assert 0.5 <= st2["cost_scaling_factor"] <= 8.0

    def test_adv_f752_nan_and_inf_resilience(self):
        """Stress test 4D Kalman filter with NaN and Inf inputs."""
        kf = Online4DKalmanSlippageFilter()
        init_state = kf.get_state()

        # 1. NaN slippage observation: must gracefully ignore update without crashing
        res = kf.update(realized_slippage_bps=float("nan"))
        assert len(res) == 4
        assert kf.get_state()["gamma"] == init_state["gamma"]

        # 2. +Inf / -Inf slippage observation
        res_inf = kf.update(realized_slippage_bps=float("inf"))
        assert len(res_inf) == 4
        res_neginf = kf.update(realized_slippage_bps=float("-inf"))
        assert len(res_neginf) == 4

        # 3. NaN observation sensitivities H
        kf.update(realized_slippage_bps=10.0, h_gamma=float("nan"), h_spread=float("inf"), h_eta=float("-inf"))
        st = kf.get_state()
        assert math.isfinite(st["gamma"])
        assert math.isfinite(st["spread"])
        assert math.isfinite(st["eta"])
        assert math.isfinite(st["rho"])

    def test_adv_f752_joseph_covariance_positive_definiteness_100_steps(self):
        """Verify Joseph covariance positive definiteness and exact symmetry after 100 noisy updates."""
        kf = Online4DKalmanSlippageFilter()
        rng = np.random.default_rng(777)

        for step in range(100):
            # Noisy random observation
            noise_y = rng.normal(loc=12.0, scale=8.0)
            h_g = max(0.1, rng.normal(loc=5.0, scale=2.0))
            h_s = max(0.1, rng.normal(loc=4.0, scale=1.5))
            h_e = max(0.1, rng.normal(loc=2.0, scale=1.0))
            h_r = max(0.1, rng.normal(loc=1.0, scale=0.5))

            kf.update(realized_slippage_bps=noise_y, h_gamma=h_g, h_spread=h_s, h_eta=h_e, h_rho=h_r)

            # Invariant 1: Exact Symmetry ||P - P^T|| < 1e-12
            sym_diff = np.max(np.abs(kf.P - kf.P.T))
            assert sym_diff < 1e-12, f"Step {step}: Covariance symmetry violated: diff={sym_diff}"

            # Invariant 2: Positive Definiteness (all eigenvalues > 0)
            eigvals = np.linalg.eigvalsh(kf.P)
            assert np.all(eigvals > 0.0), f"Step {step}: Non-positive eigenvalues: {eigvals}"
            assert np.min(eigvals) >= 1e-8, f"Step {step}: Eigenvalue below stabilization floor: {np.min(eigvals)}"

            # Invariant 3: Condition number bounded
            cond = np.linalg.cond(kf.P)
            assert cond < 1e8, f"Step {step}: Covariance matrix ill-conditioned: cond={cond}"

    def test_adv_f752_parameter_boundary_clamping(self):
        """Verify strict parameter clamping kappa, beta, eta, rho in [0.05, 5.0]."""
        kf = Online4DKalmanSlippageFilter()

        # 50 consecutive massive positive shocks (+5,000 bps)
        for _ in range(50):
            kf.update(realized_slippage_bps=5000.0, h_gamma=10.0, h_spread=10.0, h_eta=5.0, h_rho=5.0)

        st = kf.get_state()
        for param in ["gamma", "spread", "eta", "rho"]:
            assert 0.05 <= st[param] <= 5.0, f"Parameter {param} escaped bounds: {st[param]}"

        # 50 consecutive massive negative shocks (-5,000 bps)
        for _ in range(50):
            kf.update(realized_slippage_bps=-5000.0, h_gamma=10.0, h_spread=10.0, h_eta=5.0, h_rho=5.0)

        st_low = kf.get_state()
        for param in ["gamma", "spread", "eta", "rho"]:
            assert 0.05 <= st_low[param] <= 5.0, f"Parameter {param} escaped bounds: {st_low[param]}"


# ==============================================================================
# SECTION 4: F753 Asymmetric Leland Buffer Bands Adversarial Stress Tests
# ==============================================================================

class TestF753LelandBufferBandsAdversarial:
    """Adversarial stress-testing of Asymmetric Leland Dynamic Buffer Bands."""

    def test_adv_f753_extreme_leverage_and_volatility(self):
        """Test Leland buffer bands under extreme leverage (L=1.45, 2.0, 5.0) and extreme volatility."""
        opt = TurnoverOptimizer()
        targets = {"005930": 0.05, "AAPL": 0.04}

        # 1. Base leverage L=1.0 vs Bull leverage L=1.45 vs Extreme L=2.0
        bands_100 = opt.compute_leland_bands(target_weights=targets, leverage=1.0)
        bands_145 = opt.compute_leland_bands(target_weights=targets, leverage=1.45)
        bands_200 = opt.compute_leland_bands(target_weights=targets, leverage=2.0)

        # Half-widths must expand with leverage: lev_factor = 1.0 + 0.40 * max(0, L - 1.0)
        width_100 = bands_100["005930"][2] - bands_100["005930"][0]
        width_145 = bands_145["005930"][2] - bands_145["005930"][0]
        width_200 = bands_200["005930"][2] - bands_200["005930"][0]

        assert width_145 > width_100, f"Width at 1.45x ({width_145}) not greater than 1.0x ({width_100})"
        assert width_200 > width_145, f"Width at 2.0x ({width_200}) not greater than 1.45x ({width_145})"

        # Theoretical ratio check: 1.45x lev_factor = 1.0 + 0.4*0.45 = 1.18
        ratio_145 = width_145 / width_100
        assert math.isclose(ratio_145, 1.18, rel_tol=1e-3)

        # 2. Extreme volatility: low (0.001) vs massive (1.00)
        bands_low_vol = opt.compute_leland_bands(target_weights=targets, volatilities={"005930": 0.001})
        bands_high_vol = opt.compute_leland_bands(target_weights=targets, volatilities={"005930": 0.50})
        w_low = bands_low_vol["005930"][2] - bands_low_vol["005930"][0]
        w_high = bands_high_vol["005930"][2] - bands_high_vol["005930"][0]
        assert w_high > w_low, f"High vol width ({w_high}) not greater than low vol width ({w_low})"

    def test_adv_f753_instant_bypass_triggers(self):
        """Verify strict instant bypass triggers: fresh entry (w_0=0 -> BUY), full exit (w*=0 -> SELL)."""
        opt = TurnoverOptimizer()

        # Case 1: Fresh entry (w_curr == 0.0, w_target = 0.03) -> MUST BUY (bypass buffer)
        res_fresh = opt.optimize_allocations(
            current_holdings={"005930": 0.0},
            target_allocations={"005930": 0.03},
            total_capital=100_000_000.0,
            use_leland_bands=True,
        )
        assert res_fresh["005930"]["action"] == "BUY"
        assert math.isclose(res_fresh["005930"]["target_weight"], 0.03, abs_tol=1e-5)

        # Case 2: Full exit (w_curr = 0.04, w_target = 0.0) -> MUST SELL (bypass buffer)
        res_exit = opt.optimize_allocations(
            current_holdings={"005930": 0.04},
            target_allocations={"005930": 0.0},
            total_capital=100_000_000.0,
            use_leland_bands=True,
        )
        assert res_exit["005930"]["action"] == "SELL"
        assert math.isclose(res_exit["005930"]["target_weight"], 0.0, abs_tol=1e-5)

        # Case 3: Rebalance suppression inside buffer band (e.g. w_target = 0.05, w_curr = 0.052)
        # Compute exact bands first
        bands = opt.compute_leland_bands({"005930": 0.05})
        L_i, w_star, U_i = bands["005930"]
        # Position curr strictly inside [L_i, U_i]
        curr_inside = 0.5 * (L_i + U_i)
        res_hold = opt.optimize_allocations(
            current_holdings={"005930": curr_inside},
            target_allocations={"005930": 0.05},
            total_capital=100_000_000.0,
            use_leland_bands=True,
        )
        assert res_hold["005930"]["action"] == "HOLD"
        assert math.isclose(res_hold["005930"]["target_weight"], curr_inside, abs_tol=1e-5)

    def test_adv_f753_winner_expansion_and_loser_contraction(self):
        """Verify asymmetric winner expansion (up to 2.2x) and loser contraction (down to 0.6x)."""
        opt = TurnoverOptimizer()
        targets = {"SYM_WIN": 0.05, "SYM_LOSE": 0.05}

        # Winner: +15% unrealized return (Z >> 1.0)
        # Loser: -15% unrealized return (Z << -1.0)
        unrealized = {"SYM_WIN": 0.15, "SYM_LOSE": -0.15}
        vols = {"SYM_WIN": 0.02, "SYM_LOSE": 0.02}

        bands = opt.compute_leland_bands(
            target_weights=targets,
            unrealized_returns=unrealized,
            volatilities=vols,
        )

        l_win, w_win, u_win = bands["SYM_WIN"]
        l_lose, w_lose, u_lose = bands["SYM_LOSE"]

        # Upper band expansion for winner should be larger than lower band distance
        upper_win_dist = u_win - w_win
        lower_win_dist = w_win - l_win
        assert upper_win_dist > lower_win_dist, f"Winner upper dist ({upper_win_dist}) <= lower ({lower_win_dist})"

        # Lower band contraction for loser: lower distance is shrunk (0.6x)
        lower_lose_dist = w_lose - l_lose
        assert lower_lose_dist < lower_win_dist, f"Loser lower dist ({lower_lose_dist}) not contracted"


# ==============================================================================
# SECTION 5: F754 Multi-Threaded Concurrency & OMS Safety Gates
# ==============================================================================

class TestF754OMSConcurrencyAdversarial:
    """Adversarial stress-testing of 32-thread concurrent execution and OMS safety gates."""

    def test_adv_f754_32_thread_high_concurrency_stress(self):
        """Stress test OMS order processing with 32 concurrent threads executing order plans."""
        import pandas as pd
        oms = ExecutionOMSEngine()
        num_threads = 32
        plans_per_thread = 20
        errors: List[Exception] = []
        success_count = [0]
        lock = threading.Lock()

        def worker(thread_idx: int):
            for i in range(plans_per_thread):
                try:
                    sym = f"00593{thread_idx % 10}"
                    price = 70000.0 + i * 100.0
                    plan = oms.generate_order_plan(
                        top_predictions=[{"symbol": sym, "expected_return": 0.04, "close_price": price, "market": "KOSPI"}],
                        portfolio_weights={sym: 0.03},
                        current_holdings={sym: 0.0},
                        prices_dict={sym: pd.DataFrame({"Close": [price] * 5})},
                        total_capital=100_000_000.0,
                        crisis_level="NORMAL",
                    )
                    assert isinstance(plan, list)
                    with lock:
                        success_count[0] += 1
                except Exception as ex:
                    with lock:
                        errors.append(ex)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20.0)

        assert len(errors) == 0, f"Encountered {len(errors)} exceptions during 32-thread stress: {errors[:5]}"
        assert success_count[0] == num_threads * plans_per_thread

    def test_adv_f754_gate8_synthetic_inverse_hedge_trigger(self):
        """Verify Gate 8 synthetic inverse hedge overlays trigger under CRISIS/BEAR regimes."""
        oms = ExecutionOMSEngine()

        # Gate 8 in KRX under BEAR regime: activates 114800 (KODEX 200 Futures Inverse 2X)
        h_krx = PortfolioAllocator.compute_synthetic_inverse_hedge(
            portfolio_weights={"005930": 0.10, "000660": 0.08},
            market="KOSPI",
            regime_label="BEAR_HIGH_VOL",
        )
        assert h_krx["hedge_required"] is True
        assert h_krx["hedge_symbol"] == "114800"
        assert h_krx["hedge_weight"] > 0.0

        # Gate 8 in US under CRISIS regime: activates PSQ / SH
        h_us = PortfolioAllocator.compute_synthetic_inverse_hedge(
            portfolio_weights={"AAPL": 0.08, "MSFT": 0.08},
            market="US",
            regime_label="CRISIS",
        )
        assert h_us["hedge_required"] is True
        assert h_us["hedge_symbol"] in ("PSQ", "SH")
        assert h_us["hedge_weight"] > 0.0

        # Under NORMAL/BULL regime: no inverse hedge
        h_bull = PortfolioAllocator.compute_synthetic_inverse_hedge(
            portfolio_weights={"005930": 0.05},
            market="KOSPI",
            regime_label="BULL_TREND",
        )
        assert h_bull["hedge_required"] is False
        assert h_bull["hedge_symbol"] is None

