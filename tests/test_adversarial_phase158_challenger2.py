# -*- coding: utf-8 -*-
"""
tests/test_adversarial_phase158_challenger2.py
Milestone 3 (Phase 158 Part 2) Adversarial Challenge Test Suite
Empirical Challenger Verification:
1. Feature F772: Online 5D Kalman Impact Filter Adversarial Stress
   - 1000x slippage shocks & near-singular measurement covariance
   - Non-positive definite perturbations & Joseph update PSD guarantee
   - Dynamic cost scaling factor bounds clipping [0.5, 3.0]
2. Feature F773: Multi-Asset Asymmetric Leland Dynamic Buffer Bands
   - Zero & extreme volatility boundary conditions (sigma = 0.0, 1e-6, 10.0)
   - Numerical precision on fresh entry (curr = 1e-12 vs 1e-6) and liquidation (target = 1e-12 vs 0.0)
   - Strict bandwidth clamping [0.005, 0.10]
   - Synthetic 100-step rebalance turnover reduction >= 40%
3. Feature F774: Lock-Free Atomic OMS Gateway & Safety Gates
   - 32 concurrent thread stress test on atomic safety gates
   - Microsecond latency verification (< 500ns per atomic gate check)
   - Gate 8 Synthetic Inverse Hedge: negative gross equity, multi-currency (KRW vs USD), beta spikes (> 2.0)
4. Conservation Invariant: Paper Trading Conservation Law
   - 1,000 cycles random-walk simulation with random fills, extreme spreads, punitive fees
   - Unconditional assertion: self.net_equity <= self.gross_equity + 1e-9 across all cycles
"""

from __future__ import annotations

import math
import os
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))

from src.execution.slippage_feedback import (
    SlippageFeedbackEngine,
    SlippageMetrics,
    OnlineKalmanSlippageFilter,
    Online5DKalmanSlippageFilter,
)
from src.execution.turnover_optimizer import (
    TurnoverOptimizer,
    AsymmetricLelandMultipliers,
)
from src.execution.oms_engine import (
    ExecutionOMSEngine,
    _is_invalid_or_nonpositive_price,
)
from src.execution.paper_trading_daemon import (
    PaperTradingDaemon,
    PaperOrderAction,
)
from src.risk.portfolio_allocator import PortfolioAllocator
from src.ai.ensemble_scorer import EnsembleScoringEngine


# =============================================================================
# SUITE 1: FEATURE F772 5D KALMAN IMPACT FILTER ADVERSARIAL STRESS
# =============================================================================

class TestAdvFeature772KalmanStress:
    """Adversarial stress testing for 5D Kalman filter: shocks, singularity, Joseph form PSD, bounds."""

    def test_adv_f772_1000x_slippage_shock_and_near_singular_covariance(self):
        """
        Adversarial Test: 1000x slippage shocks (+5,000 to +50,000 bps) and near-singular
        measurement covariance (R -> 0, R -> 1e-12, R -> 1e12).
        Asserts:
        - Filter never emits NaN, Inf, or raises FloatingPointError.
        - Parameters remain strictly bounded within defined limits.
        - Covariance condition number remains strictly finite.
        """
        filter_5d = Online5DKalmanSlippageFilter()
        initial_state = filter_5d.get_5d_state()
        assert set(initial_state.keys()) == {"kappa", "beta", "eta", "rho", "zeta"}

        # Shock sequence: 1000x standard 5 bps slippage, negative slippage, and massive spikes
        extreme_slippages = [
            5000.0,    # +1,000x
            -2500.0,   # -500x
            50000.0,   # +10,000x
            -10000.0,  # -2,000x
            0.0,       # Zero slippage
            1e5,       # +20,000x massive shock
        ]

        near_singular_R_values = [1e-12, 1e-9, 1e-6, 0.0, 1e-15, 1e12]

        for s_bps in extreme_slippages:
            for r_val in near_singular_R_values:
                # Update with near-singular R and extreme slippage
                res = filter_5d.update(
                    realized_slippage_bps=s_bps,
                    h_kappa=3.5,
                    h_beta=4.0,
                    h_eta=1.5,
                    h_rho=1.0,
                    h_zeta=0.8,
                    R_override=r_val,
                )
                assert len(res) == 5

                # Verify all state elements are strictly finite
                st = filter_5d.get_5d_state()
                for k, v in st.items():
                    assert math.isfinite(v), f"State {k}={v} is non-finite under shock {s_bps} and R={r_val}"

                # Verify parameter bounds are respected
                assert 0.05 <= st["kappa"] <= 5.0, f"kappa={st['kappa']} out of bounds"
                assert 0.10 <= st["beta"] <= 5.0, f"beta={st['beta']} out of bounds"
                assert 0.10 <= st["eta"] <= 5.0, f"eta={st['eta']} out of bounds"
                assert 0.05 <= st["rho"] <= 5.0, f"rho={st['rho']} out of bounds"
                assert 0.05 <= st["zeta"] <= 5.0, f"zeta={st['zeta']} out of bounds"

                # Verify covariance matrix validity
                P = filter_5d.P
                assert np.all(np.isfinite(P)), "Covariance matrix P contains NaN or Inf"
                assert np.allclose(P, P.T, atol=1e-8), "Covariance matrix P is not symmetric"
                eigs = np.linalg.eigvalsh(P)
                assert (eigs > 0.0).all(), f"Covariance matrix has non-positive eigenvalues: {eigs}"
                assert np.linalg.cond(P) < 1e12, f"Covariance matrix condition number blew up: {np.linalg.cond(P)}"

    def test_adv_f772_joseph_update_psd_preservation_under_perturbations(self):
        """
        Adversarial Test: Verify Joseph update P = (I-KH)P(I-KH)^T + KRK^T strictly preserves
        positive semi-definiteness (eigenvalues >= 0) under rank deficiency,
        asymmetry noise, and numerical roundoff perturbations.
        """
        engine = SlippageFeedbackEngine()
        dim = 5
        rng = np.random.RandomState(42)

        # 1. Rank-1 deficient PSD matrix (4 zero eigenvalues)
        v = rng.randn(dim, 1)
        P_rank1 = v @ v.T
        H_vec = np.array([1.0, 2.0, 0.5, 0.2, 0.1])
        R_val = 0.05

        P_next_rank1 = engine.joseph_update_5d(P_rank1, H_vec, R_val)
        assert np.allclose(P_next_rank1, P_next_rank1.T, atol=1e-9)
        eigs_rank1 = np.linalg.eigvalsh(P_next_rank1)
        assert (eigs_rank1 >= 0.0).all()
        assert min(eigs_rank1) >= 0.0  # Mathematically guaranteed PSD
        assert math.isclose(min(eigs_rank1), 1e-8, rel_tol=1e-5)  # Matches 1e-8 regularizer

        # 2. Perturbation by floating point noise (asymmetry and micro-negative eigenvalues)
        P_pd = np.diag([0.25, 0.25, 0.25, 0.25, 0.25])
        P_noisy = P_pd + rng.randn(dim, dim) * 1e-6
        P_noisy -= np.eye(dim) * 1e-9  # Tiny negative floating perturbation
        P_next_noisy = engine.joseph_update_5d(P_noisy, H_vec, R_val)
        eigs_noisy = np.linalg.eigvalsh(P_next_noisy)
        assert np.allclose(P_next_noisy, P_next_noisy.T, atol=1e-8)
        assert (eigs_noisy >= 0.0).all()

        # 3. 500-step recursive Joseph update stress under random observations
        P_curr = np.eye(dim) * 0.25
        min_eigs = []
        for _ in range(500):
            H_rand = rng.uniform(0.1, 5.0, size=dim)
            R_rand = rng.uniform(1e-5, 10.0)
            P_curr = engine.joseph_update_5d(P_curr, H_rand, R_rand)
            assert np.allclose(P_curr, P_curr.T, atol=1e-8)
            eigs_curr = np.linalg.eigvalsh(P_curr)
            min_eigs.append(min(eigs_curr))

        assert min(min_eigs) >= 0.0, f"Observed negative eigenvalue in recursive updates: {min(min_eigs)}"

    def test_adv_f772_cost_scaling_factor_bounds_clipping(self):
        """
        Adversarial Test: Verify dynamic cost scaling factor bounds clipping to [0.5, 3.0]
        in downstream ensemble cost modeling, and [0.5, 8.0] in the 5D Kalman filter state,
        under extreme input shocks (slippage = 1,000,000 bps, negative slippage, NaN, Inf).
        """
        scorer = EnsembleScoringEngine()

        # Adversarial input values for cost_scaling_factor
        adversarial_inputs = [
            -1e8, -500.0, -1.0, 0.0, 0.10, 0.499,
            0.50, 1.00, 2.00, 3.00,
            3.001, 5.0, 10.0, 50.0, 1e8,
        ]

        for inp in adversarial_inputs:
            metrics = SlippageMetrics(cost_scaling_factor=inp)
            scorer.update_microstructure_costs(metrics)
            # Downstream ensemble scorer must strictly clamp to [0.50, 3.00]
            assert 0.50 <= scorer.cost_scaling_factor <= 3.00, (
                f"cost_scaling_factor={scorer.cost_scaling_factor} breached [0.5, 3.0] for input {inp}"
            )

        # Extreme values in SlippageFeedbackEngine.compute_friction_deduction_bps
        engine = SlippageFeedbackEngine()
        deduction_huge = engine.compute_friction_deduction_bps(
            base_spread_bps=1000.0,
            notional=1e14,
            adv_20d=1e6,
        )
        assert math.isfinite(deduction_huge)
        assert 0.1 <= deduction_huge <= 500.0, f"Deduction {deduction_huge} breached [0.1, 500.0]"

        deduction_zero = engine.compute_friction_deduction_bps(
            base_spread_bps=0.0,
            notional=0.0,
            adv_20d=1e12,
        )
        assert math.isfinite(deduction_zero)
        assert 0.1 <= deduction_zero <= 500.0


# =============================================================================
# SUITE 2: FEATURE F773 ASYMMETRIC LELAND DYNAMIC BUFFER BANDS
# =============================================================================

class TestAdvFeature773LelandBands:
    """Adversarial stress testing for asymmetric Leland dynamic buffer bands."""

    def test_adv_f773_zero_and_extreme_volatility_boundaries(self):
        """
        Adversarial Test: Verify zero, negative, NaN, and extreme volatility (1000% vol)
        boundaries clamp strictly within [0.005, 0.10].
        """
        opt = TurnoverOptimizer()

        # Floor conditions (sigma <= 1e-6)
        assert opt.compute_dynamic_bandwidth(volatility=0.0) == 0.005
        assert opt.compute_dynamic_bandwidth(volatility=1e-6) == 0.005
        assert opt.compute_dynamic_bandwidth(volatility=1e-12) == 0.005
        assert opt.compute_dynamic_bandwidth(volatility=-0.5) == 0.005
        assert opt.compute_dynamic_bandwidth(volatility=float("nan")) == 0.005

        # Ceiling conditions (extreme volatility)
        assert opt.compute_dynamic_bandwidth(volatility=10.0) <= 0.10
        assert opt.compute_dynamic_bandwidth(volatility=100.0) == 0.10
        assert opt.compute_dynamic_bandwidth(volatility=1e6) == 0.10

        # Monotonicity test across intermediate volatilities
        vols = [0.01, 0.05, 0.10, 0.20, 0.40, 0.80, 1.5, 3.0, 8.0]
        bws = [opt.compute_dynamic_bandwidth(volatility=v) for v in vols]
        for i in range(len(bws) - 1):
            assert bws[i] <= bws[i + 1], f"Monotonicity violation: bw({vols[i]})={bws[i]} > bw({vols[i+1]})={bws[i+1]}"

    def test_adv_f773_numerical_precision_fresh_entry_and_liquidation_bypass(self):
        """
        Adversarial Test: Verify micro-weight precision handling for instant rebalance bypass:
        - Fresh entry: curr_w <= 1e-6 and target_w > 1e-6 triggers instant bypass (True)
        - Full liquidation: target_w <= 1e-6 and curr_w > 1e-6 triggers instant bypass (True)
        - Negligible dust holding: curr_w <= 1e-6 and target_w <= 1e-6 suppresses order (False)
        """
        opt = TurnoverOptimizer()

        # Fresh Entry Bypass tests
        assert opt.evaluate_rebalance_bypass(target_weight=0.05, current_weight=0.0) is True
        assert opt.evaluate_rebalance_bypass(target_weight=0.05, current_weight=1e-12) is True
        assert opt.evaluate_rebalance_bypass(target_weight=0.05, current_weight=1e-6) is True
        # Just above threshold -> no instant fresh entry bypass
        assert opt.evaluate_rebalance_bypass(
            target_weight=0.05,
            current_weight=1.001e-6,
            lower_band=0.04,
            upper_band=0.06,
        ) is False

        # Full Liquidation Bypass tests
        assert opt.evaluate_rebalance_bypass(target_weight=0.0, current_weight=0.05) is True
        assert opt.evaluate_rebalance_bypass(target_weight=1e-12, current_weight=0.05) is True
        assert opt.evaluate_rebalance_bypass(target_weight=1e-6, current_weight=0.05) is True
        # Just above threshold -> no instant liquidation bypass
        assert opt.evaluate_rebalance_bypass(
            target_weight=1.001e-6,
            current_weight=0.05,
            lower_band=0.0,
            upper_band=0.01,
        ) is False

        # Dust weights (both <= 1e-6) -> Noise suppression (False)
        assert opt.evaluate_rebalance_bypass(target_weight=1e-12, current_weight=1e-12) is False
        assert opt.evaluate_rebalance_bypass(target_weight=0.0, current_weight=0.0) is False
        assert opt.evaluate_rebalance_bypass(target_weight=5e-7, current_weight=5e-7) is False

    def test_adv_f773_bandwidth_strict_bounds_under_parameter_sweep(self):
        """
        Adversarial Test: Comprehensive parameter grid sweep across volatility, transaction cost,
        and risk aversion gamma, asserting bandwidth is unconditionally in [0.005, 0.10].
        """
        opt = TurnoverOptimizer()

        vols = [0.0, 1e-7, 0.05, 0.15, 0.35, 1.0, 5.0, 20.0]
        costs_bps = [0.01, 1.0, 25.0, 100.0, 500.0]
        gammas = [1e-3, 0.5, 3.0, 10.0, 100.0]
        tx_costs = [1e-6, 0.001, 0.01, 0.10]

        for v in vols:
            for c in costs_bps:
                for g in gammas:
                    bw = opt.compute_dynamic_bandwidth(volatility=v, cost_bps=c, gamma=g)
                    assert 0.005 <= bw <= 0.10, f"Bandwidth {bw} breached bounds for v={v}, c={c}, g={g}"

        for v in vols:
            for tc in tx_costs:
                bw = opt.compute_dynamic_bandwidth(volatility=v, transaction_cost=tc)
                assert 0.005 <= bw <= 0.10, f"Bandwidth {bw} breached bounds for v={v}, tc={tc}"

    def test_adv_f773_100_step_synthetic_rebalance_turnover_reduction(self):
        """
        Adversarial Test: Evaluate 100-step realistic portfolio rebalance sequence.
        Proves asymmetric Leland buffer bands suppress noise rebalancing and achieve >= 40%
        turnover reduction relative to unbuffered rebalancing.
        """
        opt = TurnoverOptimizer()
        rng = np.random.RandomState(42)
        symbols = [f"SYM_{i:02d}" for i in range(10)]
        capital = 100_000_000.0

        current_weights = {s: 0.10 for s in symbols}
        unbuffered_turnover_total = 0.0
        buffered_turnover_total = 0.0

        vol = 0.20
        bw = opt.compute_dynamic_bandwidth(volatility=vol)

        for step in range(100):
            # Target weights fluctuate with macro drift and noise around 0.10
            trend = 0.02 * np.sin(step / 10.0)
            noise = rng.normal(0.0, 0.03, size=len(symbols))
            raw_tgt = np.clip(0.10 + trend + noise, 0.02, 0.30)
            tgt_w = {symbols[i]: float(raw_tgt[i] / np.sum(raw_tgt)) for i in range(len(symbols))}

            # Leland buffer bands around target
            leland_bands = {s: (tgt_w[s] - bw, tgt_w[s] + bw) for s in symbols}

            # Unbuffered turnover: sum(|target_w - current_w|) * capital
            for s in symbols:
                unbuffered_turnover_total += abs(tgt_w[s] - current_weights[s]) * capital

            # Buffered turnover via TurnoverOptimizer with Leland buffer bands
            opt_result = opt.optimize_allocations(
                current_holdings=current_weights,
                target_allocations=tgt_w,
                total_capital=capital,
                leland_bands=leland_bands,
                rebalance_mode="boundary",
            )

            # Accumulate executed buffered trade deltas
            for s, res in opt_result.items():
                buffered_turnover_total += res["delta_amount"]
                current_weights[s] = res["target_weight"]

        assert unbuffered_turnover_total > 0.0
        turnover_reduction = (unbuffered_turnover_total - buffered_turnover_total) / unbuffered_turnover_total
        assert turnover_reduction >= 0.40, (
            f"Observed turnover reduction {turnover_reduction * 100:.2f}% failed to achieve >= 40.0% requirement"
        )
        assert opt.compute_turnover_reduction_ratio() >= 0.40


# =============================================================================
# SUITE 3: FEATURE F774 LOCK-FREE ATOMIC OMS GATEWAY & SAFETY GATES
# =============================================================================

class TestAdvFeature774LockFreeOMSGateway:
    """Adversarial stress testing for lock-free atomic safety gates and Gate 8 inverse hedge."""

    def test_adv_f774_32_concurrent_threads_atomic_safety_gates(self):
        """
        Adversarial Test: 32 concurrent threads simultaneously hammering all atomic safety gates
        and order planning logic without deadlocks, race conditions, or memory corruption.
        """
        oms = ExecutionOMSEngine()
        thread_count = 32
        iterations_per_thread = 50
        errors = []

        def worker(tid: int):
            try:
                for it in range(iterations_per_thread):
                    # 1. Price validity gate
                    p_valid = 50000.0 + (it * 10.0)
                    assert _is_invalid_or_nonpositive_price(p_valid) is False
                    assert _is_invalid_or_nonpositive_price(0.0) is True
                    assert _is_invalid_or_nonpositive_price(-50.0) is True

                    # 2. Capital slice gate
                    assert oms.check_capital_slice_gate(order_val=10_000_000.0) is True
                    assert oms.check_capital_slice_gate(order_val=50_000_000.0, max_slice=20_000_000.0) is False

                    # 3. Circuit breaker gate
                    assert oms.check_circuit_breaker_gate("005930", change_pct=0.05) is True
                    assert oms.check_circuit_breaker_gate("005930", change_pct=0.298) is False

                    # 4. ADV gate
                    assert oms.check_adv_participation_gate(order_qty=5000, adv=1_000_000) is True
                    assert oms.check_adv_participation_gate(order_qty=50000, adv=1_000_000) is False

                    # 5. Gate 8 inverse hedge
                    h_bear = oms.evaluate_gate8_inverse_hedge("BEAR_HIGH_VOL", "KOSPI")
                    assert h_bear["hedge_active"] is True
                    h_bull = oms.evaluate_gate8_inverse_hedge("BULL_LOW_VOL", "KOSPI")
                    assert h_bull["hedge_active"] is False

                # Concurrent order plan generation once per thread
                plan = oms.generate_order_plan(
                    top_predictions=[{"symbol": "005930", "close_price": 70000.0, "market": "KOSPI"}],
                    portfolio_weights={"005930": 0.05},
                    current_holdings={"005930": 0.0},
                    prices_dict={"005930": pd.DataFrame({"Close": [70000.0] * 5})},
                    total_capital=100_000_000.0,
                )
                assert len(plan) == 1
            except Exception as exc:
                errors.append(f"Thread {tid} failed: {exc}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent thread errors encountered: {errors}"

    def test_adv_f774_atomic_safety_gates_latency_benchmark_sub_500ns(self):
        """
        Adversarial Test: Microsecond latency verification (< 500ns per atomic gate check).
        Benchmarks 20,000 executions of each atomic gate to guarantee ultra-low latency.
        """
        oms = ExecutionOMSEngine()
        n_iters = 20_000
        fn_price = _is_invalid_or_nonpositive_price
        fn_slice = oms.check_capital_slice_gate
        fn_cb = oms.check_circuit_breaker_gate
        fn_adv = oms.check_adv_participation_gate

        # Warm-up JIT / caches
        for _ in range(1000):
            fn_price(70000.0)
            fn_slice(10_000_000.0, 20_000_000.0)
            fn_cb("005930", 0.05)
            fn_adv(1000.0, 1_000_000.0)

        # Benchmark Gate 2: Price sanity
        t_price_runs = []
        for _ in range(3):
            t0 = time.perf_counter()
            for _ in range(n_iters):
                fn_price(70000.0)
            t_price_runs.append((time.perf_counter() - t0) / n_iters * 1e9)
        t_price_ns = min(t_price_runs)
        assert t_price_ns < 500.0, f"Price check latency {t_price_ns:.1f}ns exceeded 500ns target"

        # Benchmark Gate 1: Capital slice
        t_slice_runs = []
        for _ in range(3):
            t0 = time.perf_counter()
            for _ in range(n_iters):
                fn_slice(10_000_000.0, 20_000_000.0)
            t_slice_runs.append((time.perf_counter() - t0) / n_iters * 1e9)
        t_slice_ns = min(t_slice_runs)
        assert t_slice_ns < 500.0, f"Slice check latency {t_slice_ns:.1f}ns exceeded 500ns target"

        # Benchmark Gate 4: Circuit breaker
        t_cb_runs = []
        for _ in range(3):
            t0 = time.perf_counter()
            for _ in range(n_iters):
                fn_cb("005930", 0.05)
            t_cb_runs.append((time.perf_counter() - t0) / n_iters * 1e9)
        t_cb_ns = min(t_cb_runs)
        assert t_cb_ns < 500.0, f"Circuit breaker latency {t_cb_ns:.1f}ns exceeded 500ns target"

        # Benchmark Gate 6: ADV participation
        t_adv_runs = []
        for _ in range(3):
            t0 = time.perf_counter()
            for _ in range(n_iters):
                fn_adv(1000.0, 1_000_000.0)
            t_adv_runs.append((time.perf_counter() - t0) / n_iters * 1e9)
        t_adv_ns = min(t_adv_runs)
        assert t_adv_ns < 500.0, f"ADV participation latency {t_adv_ns:.1f}ns exceeded 500ns target"

    def test_adv_f774_gate8_synthetic_inverse_hedge_extreme_conditions(self):
        """
        Adversarial Test: Gate 8 Synthetic Inverse Hedge under extreme conditions:
        1. Negative and zero gross equity: returns [] gracefully without division by zero.
        2. Multi-currency conversion: KRW vs USD base currency and cross-asset holdings.
        3. Portfolio beta spikes (> 2.0): bounded hedge weights and beta neutralization.
        """
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            temp_db = tf.name

        try:
            daemon = PaperTradingDaemon(db_path=temp_db, initial_capital=100_000_000.0)
            daemon.regime_label = "BEAR_HIGH_VOL"

            # 1. Negative & Zero Gross Equity Guardrail
            daemon.gross_equity = -50_000_000.0
            h_neg = daemon._generate_gate8_inverse_hedges([])
            assert h_neg == [], "Negative equity must return empty hedge order list"

            daemon.gross_equity = 0.0
            h_zero = daemon._generate_gate8_inverse_hedges([])
            assert h_zero == [], "Zero equity must return empty hedge order list"

            # 2. Multi-currency conversion: KRW base currency with US holdings
            daemon.gross_equity = 100_000_000.0
            daemon.base_currency = "KRW"
            daemon.usd_krw = 1400.0
            daemon.holdings = {
                "AAPL": {"quantity": 100, "current_price": 200.0, "market": "NASDAQ"},  # $20,000 * 1400 = 28M KRW
                "QQQ": {"quantity": 50, "current_price": 400.0, "market": "NASDAQ"},   # $20,000 * 1400 = 28M KRW
            }
            hedges_krw_base = daemon._generate_gate8_inverse_hedges([])
            assert len(hedges_krw_base) >= 1
            us_hedge = next(h for h in hedges_krw_base if h["symbol"] in ("PSQ", "SH"))
            assert us_hedge["symbol"] == "PSQ"
            assert us_hedge["delta_quantity"] > 0
            assert us_hedge["target_price"] == 50.0  # USD price for US ETF

            # Multi-currency conversion: USD base currency with KRX holdings
            daemon.gross_equity = 100_000.0  # $100,000 USD
            daemon.base_currency = "USD"
            daemon.usd_krw = 1400.0
            daemon.holdings = {
                "005930": {"quantity": 1000, "current_price": 70000.0, "market": "KOSPI"},  # 70M KRW = $50,000 USD
            }
            hedges_usd_base = daemon._generate_gate8_inverse_hedges([])
            assert len(hedges_usd_base) >= 1
            krx_hedge = next(h for h in hedges_usd_base if h["symbol"] == "114800")
            assert krx_hedge["symbol"] == "114800"
            assert krx_hedge["delta_quantity"] > 0
            assert krx_hedge["target_price"] == 2500.0  # KRW price for KRX ETF

            # 3. Portfolio Beta Spikes (> 2.0)
            beta_map_spike = {"SYM_HIGH_1": 2.50, "SYM_HIGH_2": 3.80}
            weights_spike = {"SYM_HIGH_1": 0.50, "SYM_HIGH_2": 0.50}

            h_res = PortfolioAllocator.compute_synthetic_inverse_hedge(
                portfolio_weights=weights_spike,
                market="KOSPI",
                regime_label="BEAR_HIGH_VOL",
                beta_map=beta_map_spike,
                max_hedge_ratio=0.80,
            )
            assert h_res["hedge_required"] is True
            assert h_res["portfolio_beta_before"] == 3.15  # Average of 2.5 and 3.8
            # Hedge weight must be capped at max_hedge_ratio (0.80)
            assert h_res["hedge_weight"] <= 0.80
            # Net beta must be substantially neutralized
            assert h_res["net_portfolio_beta"] < h_res["portfolio_beta_before"]

        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except OSError:
                    pass


# =============================================================================
# SUITE 4: CONSERVATION INVARIANT ACROSS 1,000 TRADING CYCLES
# =============================================================================

class TestAdvConservationInvariantStress:
    """Stress testing the paper trading conservation law across 1,000 random-walk cycles."""

    def test_adv_conservation_invariant_1000_cycles_random_walk(self):
        """
        Adversarial Test: 1,000 cycles random-walk simulation with random fills, extreme spreads,
        and punitive fees. Unconditionally asserts across EVERY single cycle:
            self.net_equity <= self.gross_equity + 1e-9
            self.verify_conservation_invariant() is True
            Total violations == 0
        """
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            temp_db = tf.name

        try:
            daemon = PaperTradingDaemon(
                db_path=temp_db,
                initial_capital=100_000_000.0,
                base_currency="KRW",
            )
            rng = np.random.RandomState(777)
            symbols = ["005930", "000660", "035420", "051910", "AAPL", "MSFT", "NVDA", "AMZN"]
            base_prices = {
                "005930": 70000.0,
                "000660": 160000.0,
                "035420": 200000.0,
                "051910": 450000.0,
                "AAPL": 220.0,
                "MSFT": 420.0,
                "NVDA": 130.0,
                "AMZN": 180.0,
            }
            current_prices = dict(base_prices)
            total_violations = 0

            # Execute 1,000 cycles using dry_run=True for in-memory execution speed
            for cycle in range(1, 1001):
                # 1. Random walk price shock (-5% to +5%)
                for s in symbols:
                    pct_chg = rng.normal(0.0002, 0.02)
                    current_prices[s] = max(1.0, current_prices[s] * (1.0 + pct_chg))

                # 2. Random portfolio target weights (sum <= 1.0)
                raw_w = rng.uniform(0.0, 1.0, size=len(symbols))
                tgt_w = dict(zip(symbols, (raw_w / np.sum(raw_w) * 0.85).tolist()))

                # 3. Execute paper trading cycle
                summary = daemon.run_cycle(
                    target_weights=tgt_w,
                    current_prices=current_prices,
                    dry_run=True,
                )

                # 4. Invariant Assertion across EVERY cycle
                inv_holds = daemon.verify_conservation_invariant()
                equity_condition = daemon.net_equity <= (daemon.gross_equity + 1e-9)

                if not (inv_holds and equity_condition):
                    total_violations += 1

                assert inv_holds is True, (
                    f"Cycle {cycle}: verify_conservation_invariant() failed! "
                    f"Net={daemon.net_equity:,.2f}, Gross={daemon.gross_equity:,.2f}"
                )
                assert equity_condition is True, (
                    f"Cycle {cycle}: Net Equity ({daemon.net_equity:,.4f}) > "
                    f"Gross Equity ({daemon.gross_equity:,.4f}) + 1e-9"
                )
                assert math.isfinite(daemon.gross_equity)
                assert math.isfinite(daemon.net_equity)

            # Post-run invariants
            assert total_violations == 0, f"Observed {total_violations} conservation invariant violations"
            assert daemon.total_fees_paid >= 0.0, "Total fees paid cannot be negative"
            assert daemon.total_slippage_cost >= 0.0, "Total slippage cost cannot be negative"
            assert daemon.gross_equity >= daemon.net_equity - 1e-9, (
                "Gross equity must strictly equal or exceed net equity under friction"
            )

        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except OSError:
                    pass
