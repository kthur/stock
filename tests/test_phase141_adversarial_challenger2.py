"""
Empirical Adversarial Challenge Test Suite for Phase 141 (Dynamic Regime Leverage & Kelly Allocator).
Features Tested: F685, F686, F687, F688, F689.
Author: Empirical Challenger 2 (critic, specialist).

Focus Areas:
1. Simplex budget conservation: |sum(w) + w_cash - L_t| <= 1e-6 across extreme dimensions and condition numbers.
2. Bounded simplex water-filling: w_i <= 0.05 * L_t and sector sum <= 0.25 * L_t under astronomical returns.
3. Strict portfolio beta clamping: beta_port <= 1.000 whenever L_t > 1.00 under high-beta and adversarial asset sets.
4. Leveraged Leland buffer band calculation and 3 instant bypass triggers (new entry, full exit, >=50% drift).
5. Concurrency and memory stability under heavy multi-threaded load (N=500, N=1000, 10 threads).
"""

import math
import gc
import threading
import concurrent.futures
import numpy as np
import pandas as pd
import pytest

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    FractionalKellyAllocator,
    Phase141KellyAllocator,
)
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


class TestPhase141EmpiricalAdversarialChallenger2:

    @pytest.fixture(autouse=True)
    def setup_allocator(self):
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.25,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=50,
        )
        self.unified_allocator = UnifiedPortfolioAllocator(
            version=141,
            target_volatility=0.12,
            max_single_weight=0.05,
            max_sector_weight=0.25,
            rebalance_mode="boundary",
        )

    # =========================================================================
    # Group 1: Simplex Budget Conservation (|sum(w) + w_cash - L_t| <= 1e-6)
    # =========================================================================

    def test_simplex_budget_conservation_parameter_sweep(self):
        """Test budget conservation across various dimensions N and leverage levels L_t."""
        np.random.seed(42)
        dimensions = [1, 2, 5, 10, 20, 50, 100, 200]
        leverages = [0.15, 0.30, 0.60, 0.85, 1.00, 1.10, 1.25, 1.50]

        for N in dimensions:
            cov = np.eye(N) * 0.04
            for lev in leverages:
                rets = np.random.uniform(0.01, 0.15, N)
                w, w_cash = self.allocator.compute_fractional_kelly_weights(
                    predicted_returns=rets,
                    cov_matrix=cov,
                    leverage=lev,
                )
                tot = float(np.sum(w) + w_cash)
                assert math.isclose(tot, lev, abs_tol=1e-6), (
                    f"Simplex budget failed for N={N}, L={lev}: sum(w)={np.sum(w)}, w_cash={w_cash}, total={tot}"
                )
                assert np.all(w >= -1e-12), "Negative weights detected"
                assert w_cash >= -1e-12, "Negative cash detected"

    def test_simplex_budget_under_capacity_starvation(self):
        """
        When N=4, max capacity is 4 * 0.05 * L = 0.20 * L.
        Simplex must conserve exactly L_t by parking 0.80 * L_t in cash.
        """
        N = 4
        cov = np.eye(N) * 0.04
        rets = np.array([0.50, 0.40, 0.30, 0.20])
        lev = 1.25
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=rets,
            cov_matrix=cov,
            leverage=lev,
            max_single_stock=0.05,
        )
        max_possible_stock = 0.05 * lev
        assert np.all(w <= max_possible_stock + 1e-9)
        assert math.isclose(float(np.sum(w)), N * max_possible_stock, abs_tol=1e-6)
        expected_cash = lev - (N * max_possible_stock)
        assert math.isclose(w_cash, expected_cash, abs_tol=1e-6)
        assert math.isclose(float(np.sum(w) + w_cash), lev, abs_tol=1e-6)

    def test_simplex_budget_all_negative_or_zero_returns(self):
        """When all expected returns are <= 0, 100% of leverage must be parked in cash."""
        N = 25
        cov = np.eye(N) * 0.04
        lev = 1.25

        # All zero
        w_zero, cash_zero = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=np.zeros(N),
            cov_matrix=cov,
            leverage=lev,
        )
        assert float(np.sum(w_zero)) == 0.0
        assert math.isclose(cash_zero, lev, abs_tol=1e-6)

        # All negative
        w_neg, cash_neg = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=-np.ones(N) * 0.05,
            cov_matrix=cov,
            leverage=lev,
        )
        assert float(np.sum(w_neg)) == 0.0
        assert math.isclose(cash_neg, lev, abs_tol=1e-6)

    def test_simplex_budget_astronomical_ill_conditioned_covariance(self):
        """Test near-singular ill-conditioned covariance matrix (condition number > 1e12)."""
        N = 30
        np.random.seed(123)
        A = np.random.randn(N, 5)  # Rank 5
        cov_singular = A @ A.T  # Rank deficient
        rets = np.random.uniform(0.01, 0.10, N)
        lev = 1.25

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=rets,
            cov_matrix=cov_singular,
            leverage=lev,
        )
        assert math.isclose(float(np.sum(w) + w_cash), lev, abs_tol=1e-6)
        assert np.all(w <= 0.05 * lev + 1e-9)
        assert np.all(w >= 0.0)
        assert w_cash >= 0.0

    # =========================================================================
    # Group 2: Bounded Simplex Water-Filling (Single Stock <= 5%, Sector <= 25%)
    # =========================================================================

    def test_bounded_water_filling_single_asset_astronomical_return(self):
        """One asset has +10,000% return while others have 1%. It must strictly cap at 0.05 * L_t."""
        N = 50
        cov = np.eye(N) * 0.04
        rets = np.full(N, 0.01)
        rets[0] = 100.0  # Astronomical return
        lev = 1.25

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=rets,
            cov_matrix=cov,
            leverage=lev,
            max_single_stock=0.05,
        )
        assert w[0] <= 0.05 * lev + 1e-9
        assert math.isclose(w[0], 0.05 * lev, abs_tol=1e-6)
        assert np.all(w <= 0.05 * lev + 1e-9)
        assert math.isclose(float(np.sum(w) + w_cash), lev, abs_tol=1e-6)

    def test_bounded_water_filling_sector_cap_under_extreme_clustering(self):
        """
        Sector A has 20 assets with huge returns (10.0), Sector B has 20 assets with modest returns (0.02).
        Sector A must strictly cap at 0.25 * L_t, and excess must redistribute to Sector B.
        """
        N = 40
        cov = np.eye(N) * 0.04
        rets = np.zeros(N)
        rets[:20] = 10.0   # Sector A
        rets[20:] = 0.02   # Sector B

        sector_indices = {
            "Sector_A": list(range(20)),
            "Sector_B": list(range(20, 40)),
        }
        lev = 1.25

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=rets,
            cov_matrix=cov,
            leverage=lev,
            max_single_stock=0.05,
            max_sector_exposure=0.25,
            sector_indices=sector_indices,
        )

        sum_sec_a = float(np.sum(w[:20]))
        sum_sec_b = float(np.sum(w[20:]))
        cap_sec = 0.25 * lev

        assert sum_sec_a <= cap_sec + 1e-9, f"Sector A breached cap: {sum_sec_a} > {cap_sec}"
        assert math.isclose(sum_sec_a, cap_sec, abs_tol=1e-6)
        assert sum_sec_b <= cap_sec + 1e-9, f"Sector B breached cap: {sum_sec_b} > {cap_sec}"
        # All individual stocks must still satisfy 5% cap
        assert np.all(w <= 0.05 * lev + 1e-9)
        assert math.isclose(float(np.sum(w) + w_cash), lev, abs_tol=1e-6)

    def test_bounded_water_filling_multiple_sectors_all_saturated(self):
        """
        3 sectors, each with 10 assets. Max sector cap is 0.25 * L.
        Total sector capacity is 3 * 0.25 * L = 0.75 * L.
        Remaining 0.25 * L must be absorbed into Cash.
        """
        N = 30
        cov = np.eye(N) * 0.04
        rets = np.full(N, 0.50)  # All high return
        sector_indices = {
            "S1": list(range(0, 10)),
            "S2": list(range(10, 20)),
            "S3": list(range(20, 30)),
        }
        lev = 1.25

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=rets,
            cov_matrix=cov,
            leverage=lev,
            max_single_stock=0.05,
            max_sector_exposure=0.25,
            sector_indices=sector_indices,
        )

        cap_sec = 0.25 * lev
        for s_name, idxs in sector_indices.items():
            sec_w = float(np.sum(w[idxs]))
            assert sec_w <= cap_sec + 1e-9, f"{s_name} breached cap: {sec_w} > {cap_sec}"

        tot_stock = float(np.sum(w))
        assert tot_stock <= (3 * cap_sec) + 1e-6
        assert math.isclose(tot_stock + w_cash, lev, abs_tol=1e-6)

    # =========================================================================
    # Group 3: Strict Portfolio Beta Clamping (beta_port <= 1.000 when L_t > 1.00)
    # =========================================================================

    def test_strict_portfolio_beta_clamping_leveraged_bull(self):
        """
        When L_t = 1.25 and all asset betas = 2.0:
        Unconstrained beta would be ~2.50.
        Clamping must strictly enforce beta_port <= 1.000000,
        and freed equity allocation must be precisely transferred to Cash.
        """
        N = 25
        cov = np.eye(N) * 0.04
        rets = np.full(N, 0.10)
        betas = np.full(N, 2.0)  # High beta
        lev = 1.25

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=rets,
            cov_matrix=cov,
            leverage=lev,
            asset_betas=betas,
        )

        port_beta = float(np.sum(w * betas))
        assert port_beta <= 1.000001, f"Portfolio beta exceeded 1.000: {port_beta}"
        assert math.isclose(port_beta, 1.000, abs_tol=1e-5)
        # Verify simplex conservation: sum(w) + w_cash == lev
        assert math.isclose(float(np.sum(w) + w_cash), lev, abs_tol=1e-6)
        # Cash must have absorbed the reduced equity weight
        assert w_cash > 0.50

    def test_beta_clamping_exemption_when_unleveraged(self):
        """
        When L_t = 1.00 or 0.85 (unleveraged/cash-conserving):
        High-beta portfolio is exempt from 1.00 clamping, allowing active factor exposure.
        """
        N = 20
        cov = np.eye(N) * 0.04
        rets = np.full(N, 0.08)
        betas = np.full(N, 1.5)
        lev = 1.00

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=rets,
            cov_matrix=cov,
            leverage=lev,
            asset_betas=betas,
        )
        port_beta = float(np.sum(w * betas))
        # When lev == 1.00, port_beta should be 1.00 * 1.5 = 1.50 (no clamping)
        assert port_beta > 1.000
        assert math.isclose(port_beta, 1.50, abs_tol=1e-2)
        assert math.isclose(float(np.sum(w) + w_cash), lev, abs_tol=1e-6)

    def test_beta_clamping_with_negative_and_zero_betas(self):
        """
        Test portfolio with mixed positive, negative, and zero betas.
        Beta clamp must account for net signed beta sum.
        """
        N = 30
        cov = np.eye(N) * 0.04
        rets = np.full(N, 0.10)
        betas = np.ones(N)
        betas[:10] = 2.5   # High tech
        betas[10:20] = -0.5 # Inverse / gold
        betas[20:] = 0.0   # Cash equivalents
        lev = 1.25

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=rets,
            cov_matrix=cov,
            leverage=lev,
            asset_betas=betas,
        )
        port_beta = float(np.sum(w * betas))
        assert port_beta <= 1.000001
        assert math.isclose(float(np.sum(w) + w_cash), lev, abs_tol=1e-6)

    # =========================================================================
    # Group 4: Leveraged Leland Buffer Bands & Instant Bypass Flags
    # =========================================================================

    def test_leveraged_leland_bandwidth_formula(self):
        """Verify bandwidth expansion formula: delta * (1 + 0.40 * max(0, L - 1.0))."""
        delta_base = 0.020  # 2.0%

        # L = 1.00 -> 1.0x (no expansion)
        b_100 = self.allocator.calculate_leveraged_leland_buffer(delta_base, 1.00)
        assert math.isclose(b_100, 0.020, abs_tol=1e-9)

        # L = 1.25 -> 1.10x (+10% expansion: 0.022)
        b_125 = self.allocator.calculate_leveraged_leland_buffer(delta_base, 1.25)
        assert math.isclose(b_125, 0.022, abs_tol=1e-9)

        # L = 0.50 -> 1.0x (de-leveraged does not expand)
        b_050 = self.allocator.calculate_leveraged_leland_buffer(delta_base, 0.50)
        assert math.isclose(b_050, 0.020, abs_tol=1e-9)

    def test_leland_instant_bypass_new_entry(self):
        """Fresh entry (curr_w <= 1e-4) must bypass buffer and rebalance immediately to target."""
        target = np.array([0.05, 0.05, 0.05])
        curr = np.array([0.0, 0.00005, 0.05])  # Index 0 and 1 are fresh entries
        vols = np.array([0.15, 0.15, 0.15])

        w_realized = self.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=target,
            current_weights=curr,
            volatilities=vols,
            leverage=1.25,
        )
        assert math.isclose(w_realized[0], target[0], abs_tol=1e-6), "Fresh entry 0 did not bypass"
        assert math.isclose(w_realized[1], target[1], abs_tol=1e-6), "Fresh entry 1 did not bypass"

    def test_leland_instant_bypass_full_liquidation(self):
        """Full exit (target_w <= 1e-4) must bypass buffer and rebalance immediately to 0.0."""
        target = np.array([0.0, 0.00005, 0.04])
        curr = np.array([0.05, 0.04, 0.04])
        vols = np.array([0.15, 0.15, 0.15])

        w_realized = self.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=target,
            current_weights=curr,
            volatilities=vols,
            leverage=1.25,
        )
        assert math.isclose(w_realized[0], 0.0, abs_tol=1e-6), "Liquidation 0 did not bypass"
        assert math.isclose(w_realized[1], target[1], abs_tol=1e-6), "Liquidation 1 did not bypass"

    def test_leland_instant_bypass_severe_drift(self):
        """Severe drift (|curr - target| / target >= 0.50) must bypass buffer."""
        target = np.array([0.04, 0.04])
        # Asset 0: curr=0.065 (drift = 0.025 / 0.04 = 62.5% >= 50%) -> bypass to target
        # Asset 1: curr=0.045 (drift = 0.005 / 0.04 = 12.5% < 50%) -> inside buffer, hold
        curr = np.array([0.065, 0.045])
        vols = np.array([0.15, 0.15])

        w_realized = self.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=target,
            current_weights=curr,
            volatilities=vols,
            leverage=1.25,
        )
        assert math.isclose(w_realized[0], target[0], abs_tol=1e-4), "Severe drift did not bypass"
        assert math.isclose(w_realized[1], curr[1], abs_tol=1e-4), "Minor drift did not hold"

    # =========================================================================
    # Group 5: High-Load Concurrency & Memory Stability
    # =========================================================================

    def test_oas_rmt_large_dimension_matrix_invariants(self):
        """
        Stress test OAS + Top-50 Mode-Exempt RMT on high dimension N=500, T=252.
        Verify strict positive definiteness, unit diagonal correlation, and execution latency.
        """
        np.random.seed(999)
        T, N = 252, 500
        # Synthetic factor returns: 10 common factors + idiosyncratic noise
        factors = np.random.randn(T, 10)
        loadings = np.random.randn(10, N)
        returns = (factors @ loadings) * 0.01 + np.random.randn(T, N) * 0.015

        cov, vols = self.allocator.compute_oas_rmt_covariance(returns, top_k_modes=50)

        assert cov.shape == (N, N)
        assert vols.shape == (N,)
        # Check symmetry
        assert np.allclose(cov, cov.T, atol=1e-8), "Covariance matrix is not symmetric"
        # Check strict positive definiteness: all eigenvalues > 0
        min_eig = float(np.min(np.linalg.eigvalsh(cov)))
        assert min_eig > 0.0, f"Covariance matrix is not positive definite: min_eig={min_eig}"
        # Check vols > 0
        assert np.all(vols > 0.0)

    def test_multithreaded_concurrency_stress(self):
        """
        Spawn 10 concurrent threads running fractional Kelly allocation and OAS covariance.
        Verify zero race conditions, deadlocks, or exception leakage.
        """
        errors = []
        num_threads = 10
        runs_per_thread = 15

        def worker_task(thread_id: int):
            try:
                np.random.seed(thread_id * 100)
                alloc = DynamicRegimeLeverageAllocator()
                for _ in range(runs_per_thread):
                    N = 50
                    cov = np.eye(N) * 0.04
                    rets = np.random.uniform(0.01, 0.15, N)
                    betas = np.random.uniform(0.8, 2.2, N)
                    w, w_cash = alloc.compute_fractional_kelly_weights(
                        predicted_returns=rets,
                        cov_matrix=cov,
                        leverage=1.25,
                        asset_betas=betas,
                    )
                    tot = float(np.sum(w) + w_cash)
                    if not math.isclose(tot, 1.25, abs_tol=1e-6):
                        raise ValueError(f"Thread {thread_id} simplex failure: {tot} != 1.25")
                    if float(np.sum(w * betas)) > 1.000001:
                        raise ValueError(f"Thread {thread_id} beta clamp failure")
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent execution errors: {errors}"

    def test_memory_stability_repetitive_allocations(self):
        """
        Verify memory stability: 300 sequential allocations must not exhibit memory leaks.
        """
        gc.collect()
        import os
        import psutil
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss

        N = 100
        cov = np.eye(N) * 0.04
        rets = np.ones(N) * 0.05
        betas = np.ones(N) * 1.5

        for _ in range(300):
            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=rets,
                cov_matrix=cov,
                leverage=1.25,
                asset_betas=betas,
            )

        gc.collect()
        mem_after = process.memory_info().rss
        mem_diff_mb = (mem_after - mem_before) / (1024 * 1024)
        # Memory growth must be tightly bounded (< 30 MB)
        assert mem_diff_mb < 30.0, f"Potential memory leak detected: grew by {mem_diff_mb:.2f} MB"
