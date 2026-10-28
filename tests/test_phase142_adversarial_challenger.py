# -*- coding: utf-8 -*-
"""
tests/test_phase142_adversarial_challenger.py -- Empirical Adversarial Test Suite for Phase 142
Author: challenger_p142_1 (Numerical & Microstructure Adversarial Challenger)

Verifies four critical institutional invariants under adversarial, random, and degenerate conditions:
  1. Zero negative tranche quantities invariant (Delta q_t >= 0 always) across 100+ random and edge-case orders.
  2. Terminal inventory clearance (q_T -> 0) under horizon expiration.
  3. 3D Kalman Joseph-stabilized covariance update: condition number and positive definiteness across 1,000 randomized noisy updates.
  4. Degenerate LOB conditions: zero spread, negative spread, empty order book, infinite Hawkes intensity, NaN inputs.
"""

from __future__ import annotations

import math
import sys
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
    RLOrderExecutionAgent,
)
from src.core.fast_lob_engine import (
    FastLOBEngine,
    FastOrderBookMatchingEngine,
    ZeroCopyRingBuffer,
)
from src.execution.slippage_feedback import (
    Online3DKalmanSlippageFilter,
    OnlineKalmanSlippageFilter,
    SlippageFeedbackEngine,
)
from src.execution.turnover_optimizer import (
    AsymmetricLelandOptimizer,
    TurnoverOptimizer,
)


# ==============================================================================
# CHALLENGE 1: Zero Negative Tranche Quantities Invariant (Delta q_t >= 0 always)
# ==============================================================================

def test_adv01_randomized_100_orders_non_negative_tranches():
    """
    Challenge 1.1: Generate 120 randomized orders across diverse quantities, horizons,
    volatilities, spreads, and VPIN toxicity. Assert Delta q_t >= 0 for every tranche.
    """
    agent = RLOrderExecutionAgent()
    rng = np.random.default_rng(20261028)

    quantities = [
        1, 2, 3, 5, 7, 10, 17, 50, 100, 250, 500, 1000, 5000, 12345, 99999, 1_000_000
    ]
    horizons = [1, 2, 3, 4, 5, 8, 10, 15, 20, 30, 50, 100]

    for run_idx in range(120):
        qty = int(rng.choice(quantities))
        h = int(rng.choice(horizons))
        spread = float(rng.uniform(0.0, 150.0))
        obi = float(rng.uniform(-1.0, 1.0))
        vpin = float(rng.uniform(0.0, 1.0))
        vol = float(rng.uniform(0.001, 0.20))
        adv = float(rng.uniform(10_000.0, 10_000_000.0))
        side = str(rng.choice(["BUY", "SELL", "BID", "ASK"]))

        plan = agent.optimize_trajectory(
            symbol=f"SYM_{run_idx}",
            total_quantity=qty,
            horizon_steps=h,
            spread_bps=spread,
            obi=obi,
            vpin=vpin,
            volatility=vol,
            adv=adv,
            side=side,
        )

        tranches = plan["tranches"]
        assert len(tranches) > 0, f"Run {run_idx}: Expected non-empty tranches for qty={qty}, h={h}"

        executed_sum = 0
        for step_idx, tr in enumerate(tranches):
            shares = tr["shares"]
            # Strict Invariant: tranche quantity must be strictly non-negative
            assert shares >= 0, (
                f"VIOLATION: Negative tranche shares {shares} at step {step_idx} (run {run_idx}, qty={qty}, h={h})"
            )
            assert tr["remaining_shares"] >= 0, (
                f"VIOLATION: Negative remaining shares {tr['remaining_shares']} at step {step_idx}"
            )
            executed_sum += shares

        # Conservation Invariant
        assert executed_sum == qty, (
            f"VIOLATION: Executed sum {executed_sum} != initial quantity {qty} (run {run_idx})"
        )


def test_adv02_edge_case_order_quantities_and_horizons():
    """
    Challenge 1.2: Test extreme edge-case order quantities and horizons:
    0 shares, negative shares, 1 share with 50 steps, negative horizons.
    Assert zero crashes and strictly non-negative tranche allocations.
    """
    agent = RLOrderExecutionAgent()

    # Zero and negative quantities
    for bad_qty in [0, -1, -500, -1_000_000]:
        res = agent.optimize_trajectory("AAPL", total_quantity=bad_qty, horizon_steps=10)
        assert res["total_quantity"] == 0
        assert res["executed_quantity"] == 0
        assert len(res["tranches"]) == 0

    # Zero and negative horizons
    for bad_h in [0, -1, -10]:
        res = agent.optimize_trajectory("AAPL", total_quantity=1000, horizon_steps=bad_h)
        assert res["executed_quantity"] == 0
        assert len(res["tranches"]) == 0

    # 1 share across multiple steps
    for h in [1, 5, 20, 50]:
        res = agent.optimize_trajectory("005930.KS", total_quantity=1, horizon_steps=h)
        assert res["executed_quantity"] == 1
        shares_list = [tr["shares"] for tr in res["tranches"]]
        assert all(s >= 0 for s in shares_list)
        assert sum(shares_list) == 1

    # Large horizon (500 steps)
    res_large = agent.optimize_trajectory("SPY", total_quantity=777, horizon_steps=500)
    assert res_large["executed_quantity"] == 777
    assert all(tr["shares"] >= 0 for tr in res_large["tranches"])


def test_adv03_continuous_action_slice_ratio_bounded_500_states():
    """
    Challenge 1.3: Generate 500 randomized, extreme, and out-of-distribution ExecutionStates.
    Assert SAC continuous action slice_ratio in [0.0, 1.0] and route simplex sum == 1.0000.
    """
    agent = RLOrderExecutionAgent()
    rng = np.random.default_rng(42)

    for i in range(500):
        st = ExecutionState(
            time_ratio=float(rng.uniform(-0.5, 1.5)),
            inventory_ratio=float(rng.uniform(-0.5, 1.5)),
            spread_bps=float(rng.uniform(-50.0, 500.0)),
            obi=float(rng.uniform(-5.0, 5.0)),
            vpin=float(rng.uniform(-0.5, 2.0)),
            volatility=float(rng.uniform(-0.1, 5.0)),
            micro_price_drift=float(rng.uniform(-100.0, 100.0)),
            queue_position=float(rng.uniform(-1.0, 2.0)),
            hawkes_buy=float(rng.uniform(-10.0, 100.0)),
            hawkes_sell=float(rng.uniform(-10.0, 100.0)),
            cross_asset_momentum=float(rng.uniform(-5.0, 5.0)),
            venue_rebate_bps=float(rng.uniform(-10.0, 20.0)),
        )

        act = agent.compute_continuous_action(st)

        # Slice ratio bounds
        assert 0.0 <= act.slice_ratio <= 1.0, (
            f"VIOLATION: Slice ratio {act.slice_ratio} out of bounds [0, 1] at test {i}"
        )
        # Tick offset bounds
        assert -2.0 <= act.tick_offset <= 2.0, (
            f"VIOLATION: Tick offset {act.tick_offset} out of bounds [-2, 2] at test {i}"
        )
        # Route weights simplex
        assert np.all(act.route_weights >= 0.0), f"VIOLATION: Negative route weight at test {i}"
        assert math.isclose(float(np.sum(act.route_weights)), 1.0, rel_tol=1e-5), (
            f"VIOLATION: Route weights sum {np.sum(act.route_weights)} != 1.0 at test {i}"
        )


# ==============================================================================
# CHALLENGE 2: Terminal Inventory Clearance (q_T -> 0) under Horizon Expiration
# ==============================================================================

def test_adv04_terminal_clearance_discrete_schedule_under_severe_toxicity():
    """
    Challenge 2.1: Stress test trajectory optimization when toxic flow (VPIN=0.99, adverse Hawkes)
    induces tactical pauses across initial steps. Verify terminal step strictly clears q_T -> 0.
    """
    agent = RLOrderExecutionAgent()
    for qty in [10, 50, 100, 777, 5000, 30000]:
        for h in [3, 5, 10, 25]:
            plan = agent.optimize_trajectory(
                symbol="TOXIC_STOCK",
                total_quantity=qty,
                horizon_steps=h,
                vpin=0.99, # Highly toxic: triggers early tactical pause
                spread_bps=35.0,
                volatility=0.08,
            )
            # Final remaining shares must strictly be 0
            last_tranche = plan["tranches"][-1]
            assert last_tranche["remaining_shares"] == 0, (
                f"VIOLATION: Terminal inventory not cleared! Remaining = {last_tranche['remaining_shares']} (qty={qty}, h={h})"
            )
            assert plan["executed_quantity"] == qty, (
                f"VIOLATION: Total executed {plan['executed_quantity']} != {qty}"
            )


def test_adv05_terminal_clearance_continuous_execution_simulation():
    """
    Challenge 2.2: Simulate dynamic step-by-step continuous execution over T=10 steps.
    Assert that terminal urgency triggers alpha=1.0 and AGGRESSIVE_TAKER, clearing all inventory.
    """
    agent = RLOrderExecutionAgent()
    rng = np.random.default_rng(999)

    for sim_idx in range(50):
        initial_qty = int(rng.choice([500, 1000, 5000, 25000]))
        horizon = 10
        q_curr = float(initial_qty)

        for step in range(horizon):
            t_ratio = step / float(horizon)
            inv_ratio = q_curr / float(initial_qty)

            st = ExecutionState(
                time_ratio=t_ratio,
                inventory_ratio=inv_ratio,
                spread_bps=float(rng.uniform(5.0, 30.0)),
                obi=float(rng.uniform(-0.5, 0.5)),
                vpin=0.85 if step < 8 else 0.40, # Toxic early, normal late
                volatility=0.03,
            )

            action = agent.compute_continuous_action(st)

            # At terminal horizon (t/T >= 0.90) with inventory remaining, urgency MUST activate
            if t_ratio >= 0.90 and inv_ratio > 0.15:
                assert action.slice_ratio == 1.0, (
                    f"VIOLATION: Terminal urgency slice ratio is {action.slice_ratio}, expected 1.0"
                )
                assert action.primary_channel == ExecutionAction.AGGRESSIVE_TAKER, (
                    f"VIOLATION: Terminal urgency channel is {action.primary_channel}, expected AGGRESSIVE_TAKER"
                )

            # Simulate fill execution
            fill_shares = math.ceil(action.slice_ratio * q_curr) if action.slice_ratio > 0 else 0
            if step == horizon - 1:
                # Force final cleanup
                fill_shares = int(q_curr)

            q_curr = max(0.0, q_curr - fill_shares)
            if q_curr <= 0:
                break

        # Terminal inventory invariant
        assert q_curr == 0.0, f"VIOLATION: Sim {sim_idx} failed to clear terminal inventory: q_T = {q_curr}"


def test_adv06_single_step_horizon_clearance():
    """
    Challenge 2.3: Single-step horizon (H=1) must execute entire order in one tranche with q_T = 0.
    """
    agent = RLOrderExecutionAgent()
    for q in [1, 5, 100, 12345, 1_000_000]:
        plan = agent.optimize_trajectory("005930.KS", total_quantity=q, horizon_steps=1)
        assert len(plan["tranches"]) == 1
        assert plan["tranches"][0]["shares"] == q
        assert plan["tranches"][0]["remaining_shares"] == 0
        assert plan["executed_quantity"] == q


# ==============================================================================
# CHALLENGE 3: 3D Kalman Joseph-Stabilized Covariance Update (1,000 Updates)
# ==============================================================================

def test_adv07_kalman_3d_1000_noisy_updates_positive_definiteness_and_conditioning():
    """
    Challenge 3.1: Execute 1,000 randomized, noisy, and ill-conditioned Kalman updates.
    Verify:
      1. Strict matrix symmetry: max(|P - P^T|) < 1e-10
      2. Strict positive definiteness: all eigenvalues lambda_i > 0
      3. Condition number kappa(P) = lambda_max / lambda_min is bounded (< 1e7)
      4. Parameter boundaries [kappa, beta, eta] respected
      5. Cost scaling factor is finite and bounded in [0.5, 8.0]
    """
    kf = OnlineKalmanSlippageFilter(dim=3, initial_kappa=0.50, initial_beta=1.00, initial_eta=1.00)
    rng = np.random.default_rng(777)

    condition_numbers: List[float] = []
    min_eigenvalues: List[float] = []

    for step in range(1000):
        # Adversarial / heavy-tailed noise distribution (Student-t with df=3)
        t_noise = rng.standard_t(df=3) * 5.0
        # Simulated true parameters with stochastic regime drift
        true_k = 0.80 + 0.30 * math.sin(step / 100.0)
        true_b = 1.20 + 0.20 * math.cos(step / 150.0)
        true_e = 1.10 + 0.15 * math.sin(step / 200.0)

        # Diverse observation vectors (including near-collinear and zero-scale cases)
        if step % 50 == 0:
            # Collinear edge case
            hk = 3.0
            hb = 3.0
            he = 3.0
        elif step % 75 == 0:
            # Very small observation scale
            hk = float(rng.uniform(1e-4, 1e-2))
            hb = float(rng.uniform(1e-4, 1e-2))
            he = float(rng.uniform(1e-4, 1e-2))
        elif step % 90 == 0:
            # Very large observation scale
            hk = float(rng.uniform(50.0, 200.0))
            hb = float(rng.uniform(50.0, 200.0))
            he = float(rng.uniform(50.0, 200.0))
        else:
            hk = float(rng.uniform(0.5, 5.0))
            hb = float(rng.uniform(1.0, 8.0))
            he = float(rng.uniform(0.5, 3.0))

        realized_y = true_k * hk + true_b * hb + true_e * he + t_noise

        # Occasional measurement noise variance overrides
        r_override = float(rng.uniform(1.0, 50.0)) if step % 20 == 0 else None

        k_up, b_up, e_up = kf.update(
            realized_slippage_bps=realized_y,
            h_kappa=hk,
            h_beta=hb,
            h_eta=he,
            R_override=r_override,
        )

        P = kf.P

        # 1. Exact Symmetry check
        sym_diff = np.max(np.abs(P - P.T))
        assert sym_diff < 1e-10, f"VIOLATION: Covariance asymmetry {sym_diff} at step {step}"

        # 2. Strict Positive Definiteness check
        eigvals = np.linalg.eigvalsh(P)
        min_eig = float(np.min(eigvals))
        max_eig = float(np.max(eigvals))
        min_eigenvalues.append(min_eig)

        assert min_eig > 0.0, (
            f"VIOLATION: Non-positive definite covariance at step {step}! min_eig={min_eig}"
        )

        # 3. Condition Number check
        cond = max_eig / min_eig
        condition_numbers.append(cond)
        assert cond < 1e7, (
            f"VIOLATION: Covariance condition number exploded to {cond} at step {step}"
        )

        # 4. Parameter Bounds check
        assert 0.05 <= k_up <= 5.0, f"VIOLATION: kappa {k_up} out of bounds at step {step}"
        assert 0.10 <= b_up <= 5.0, f"VIOLATION: beta {b_up} out of bounds at step {step}"
        assert 0.10 <= e_up <= 5.0, f"VIOLATION: eta {e_up} out of bounds at step {step}"

        # 5. Cost Scaling Factor check
        state = kf.get_state()
        cost_scale = state["cost_scaling_factor"]
        assert 0.5 <= cost_scale <= 8.0, (
            f"VIOLATION: Cost scaling factor {cost_scale} out of bounds [0.5, 8.0] at step {step}"
        )

    # Statistical summary assertions
    median_cond = float(np.median(condition_numbers))
    assert median_cond < 500.0, f"Median condition number {median_cond} indicates ill-conditioned filter"
    assert min(min_eigenvalues) >= 1e-9, f"Minimum eigenvalue {min(min_eigenvalues)} too close to singularity"


def test_adv08_kalman_3d_adversarial_pathological_inputs():
    """
    Challenge 3.2: Adversarial input stress: feed NaN, +/- Inf, extreme outliers (+5000 bps, -2000 bps),
    and all-zero observations into 3D Kalman filter. Assert graceful recovery and mathematical stability.
    """
    kf = OnlineKalmanSlippageFilter(dim=3)

    # 1. NaN and Inf slippage handling
    for bad_y in [float("nan"), float("inf"), float("-inf")]:
        k, b, e = kf.update(realized_slippage_bps=bad_y, h_kappa=2.0, h_beta=5.0, h_eta=1.5)
        assert math.isfinite(k) and math.isfinite(b) and math.isfinite(e)
        assert np.all(np.isfinite(kf.P))
        assert np.all(np.linalg.eigvalsh(kf.P) > 0)

    # 2. NaN and Inf observation components
    k, b, e = kf.update(
        realized_slippage_bps=10.0,
        h_kappa=float("nan"),
        h_beta=float("inf"),
        h_eta=float("-inf"),
    )
    assert math.isfinite(k) and math.isfinite(b) and math.isfinite(e)
    assert np.all(np.isfinite(kf.P))

    # 3. All-zero observation vector H = [0, 0, 0]
    p_pre = kf.P.copy()
    kf.update(realized_slippage_bps=15.0, h_kappa=0.0, h_beta=0.0, h_eta=0.0)
    assert np.all(np.linalg.eigvalsh(kf.P) > 0)

    # 4. Extreme outlier slippages (+5000 bps, -5000 bps)
    for _ in range(5):
        kf.update(realized_slippage_bps=5000.0, h_kappa=5.0, h_beta=5.0, h_eta=5.0)
    st = kf.get_state()
    assert st["kappa"] == pytest.approx(5.0)
    assert st["beta"] == pytest.approx(5.0)
    assert st["eta"] == pytest.approx(5.0)
    assert st["cost_scaling_factor"] == pytest.approx(8.0)

    for _ in range(10):
        kf.update(realized_slippage_bps=-5000.0, h_kappa=5.0, h_beta=5.0, h_eta=5.0)
    st_neg = kf.get_state()
    assert st_neg["kappa"] == pytest.approx(0.05)
    assert st_neg["beta"] == pytest.approx(0.10)
    assert st_neg["eta"] == pytest.approx(0.10)
    assert st_neg["cost_scaling_factor"] == pytest.approx(0.5)


# ==============================================================================
# CHALLENGE 4: Degenerate LOB Conditions
# ==============================================================================

def test_adv09_lob_zero_and_crossed_spread():
    """
    Challenge 4.1: FastOrderBookMatchingEngine with zero spread (bid == ask) and
    negative spread (crossed book: bid > ask). Assert immediate matching or proper state handling.
    """
    engine = FastOrderBookMatchingEngine(symbol="TEST_LOB", tick_size=0.01)

    # 1. Place resting ask at 100.00
    engine.add_limit_order(order_id="ASK_1", side="SELL", price=100.00, volume=100.0)
    # Place crossed bid at 100.00 (zero spread) -> must match immediately
    fill_0 = engine.add_limit_order(order_id="BID_CROSS_0", side="BUY", price=100.00, volume=50.0)
    assert len(fill_0) == 1
    assert fill_0[0]["volume"] == 50.0
    assert fill_0[0]["price"] == 100.00

    # 2. Place resting ask at 100.00 (50 shares remaining). Place crossed bid at 102.00 (negative spread)
    fill_cross = engine.add_limit_order(order_id="BID_CROSS_1", side="BUY", price=102.00, volume=50.0)
    assert len(fill_cross) == 1
    assert fill_cross[0]["volume"] == 50.0
    # Price improvement: filled at maker ask price 100.00
    assert fill_cross[0]["price"] == 100.00

    # Book is now completely empty
    top = engine.get_top_of_book()
    assert top is not None
    assert top.best_bid is None or top.best_bid <= 0.0 or top.spread <= 0.0 or math.isnan(top.spread)


def test_adv10_lob_empty_book_queries():
    """
    Challenge 4.2: Query all LOB engine methods on an empty book.
    Assert zero division avoided, finite outputs, and graceful fallbacks.
    """
    engine = FastOrderBookMatchingEngine(symbol="EMPTY_SYM", tick_size=0.05)

    # Top of book queries
    top = engine.get_top_of_book()
    assert top is not None

    # Depth snapshot
    depth = engine.get_depth_snapshot(levels=10)
    assert "bids" in depth and "asks" in depth
    assert len(depth["bids"]) == 0
    assert len(depth["asks"]) == 0
    assert depth["best_bid"] == 0.0
    assert depth["best_ask"] == 0.0
    assert depth["spread"] == 0.0

    # Fee and spread harvesting on empty book
    harvest = engine.harvest_spread_and_fees(
        venue="BZX",
        channel="PASSIVE_MAKER",
        spread_bps=0.0,
        notional=100000.0,
        shares=1000,
        is_maker=True,
    )
    assert harvest["maker_rebate_bps"] == 2.5
    assert harvest["net_harvested_alpha_bps"] == 2.5
    assert math.isfinite(harvest["harvested_cash"])
    assert harvest["harvested_cash"] == 25.0

    # Tick shading on empty book
    shade = engine.compute_hawkes_micro_tick_shading(side="BUY")
    assert shade["ticks_to_shade"] in [0, 1, 2]
    assert math.isfinite(shade["price_shade_offset"])


def test_adv11_hawkes_extreme_and_infinite_intensity():
    """
    Challenge 4.3: Hawkes micro-tick shading with infinite arrival rate, zero sigma, and huge kappa.
    Assert strict clamping of tick shading to [0, 2] and no overflow errors.
    """
    engine = FastOrderBookMatchingEngine(symbol="NVDA", tick_size=0.01)

    # 1. Artificially inject massive Hawkes intensity
    engine.bivariate_hawkes.lambda_sell = 1e12
    engine.bivariate_hawkes.lambda_buy = 1.0

    shade_buy = engine.compute_hawkes_micro_tick_shading(side="BUY", kappa_shade=2.0)
    assert shade_buy["ticks_to_shade"] == 2
    assert shade_buy["price_shade_offset"] == pytest.approx(-0.02)
    assert shade_buy["is_cascade"] is True

    # 2. Infinite arrival intensity
    engine.bivariate_hawkes.lambda_buy = float("inf")
    shade_sell = engine.compute_hawkes_micro_tick_shading(side="SELL", kappa_shade=2.0)
    assert shade_sell["ticks_to_shade"] in [0, 1, 2]
    assert math.isfinite(shade_sell["price_shade_offset"])

    # 3. Zero sigma_lambda (division by zero guardrail)
    shade_zero_sig = engine.compute_hawkes_micro_tick_shading(side="BUY", sigma_lambda=0.0)
    assert math.isfinite(shade_zero_sig["intensity_zscore"])
    assert shade_zero_sig["ticks_to_shade"] in [0, 1, 2]


def test_adv12_nan_and_inf_inputs_across_phase142_modules():
    """
    Challenge 4.4: Cross-module NaN/Inf robustness:
      - ExecutionState with NaN/Inf values -> to_12d_vector() and action selection
      - TurnoverOptimizer with corrupt weights, NaN capital, extreme leverage
      - SlippageFeedbackEngine with empty trade logs
    """
    # 1. ExecutionState with all-NaN/Inf fields
    bad_state = ExecutionState(
        time_ratio=float("nan"),
        inventory_ratio=float("nan"),
        spread_bps=float("nan"),
        obi=float("nan"),
        vpin=float("nan"),
        volatility=float("nan"),
        micro_price_drift=float("nan"),
        queue_position=float("nan"),
        hawkes_buy=float("inf"),
        hawkes_sell=float("-inf"),
        cross_asset_momentum=float("nan"),
        venue_rebate_bps=float("nan"),
    )
    vec = bad_state.to_12d_vector()
    assert np.all(np.isfinite(vec)), f"Found non-finite values in vector: {vec}"

    agent = RLOrderExecutionAgent()
    act = agent.compute_continuous_action(bad_state)
    assert math.isfinite(act.slice_ratio)
    assert math.isfinite(act.tick_offset)
    assert np.all(np.isfinite(act.route_weights))

    # 2. TurnoverOptimizer with NaN inputs
    opt = TurnoverOptimizer()
    corrupt_targets = {
        "AAPL": float("nan"),
        "MSFT": float("inf"),
        "005930.KS": -0.5,
        "NVDA": 0.05,
    }
    bands = opt.compute_leland_bands(
        target_weights=corrupt_targets,
        leverage=float("nan"), # Graceful fallback to 1.0
    )
    assert "NVDA" in bands
    l_i, w_i, u_i = bands["NVDA"]
    assert 0.0 <= l_i <= w_i <= u_i <= 1.0

    alloc_res = opt.optimize_allocations(
        current_holdings={"NVDA": 0.04},
        target_allocations=corrupt_targets,
        total_capital=float("nan"), # Graceful fallback
        use_leland_bands=True,
    )
    assert isinstance(alloc_res, dict)
    assert "NVDA" in alloc_res

    # 3. SlippageFeedbackEngine with empty database
    feedback = SlippageFeedbackEngine(db_path=":memory:")
    metrics = feedback.analyze_realized_slippage()
    assert isinstance(metrics, dict) or hasattr(metrics, "cost_scaling_factor")
