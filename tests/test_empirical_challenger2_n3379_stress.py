"""
tests/test_empirical_challenger2_n3379_stress.py
Empirical Adversarial Stress Harness for Phase 141 (Dynamic Regime Leverage & Kelly Allocator).
Author: Challenger 2 (critic, specialist).

Tasks & Verification:
1. Empirically stress-test portfolio allocation under high-dimensional universes (N=3,379).
2. Verify simplex budget conservation: | sum(w_i) + w_cash - L_t | <= 1e-6 across all regimes.
3. Verify bounded simplex water-filling: w_i <= 0.05 * L_t and sector sum <= 0.25 * L_t.
4. Verify portfolio beta clamping: beta_port <= 1.000 strictly whenever L_t > 1.00.
5. Verify Leveraged Leland dynamic buffer band expansion and instant bypass flags.
6. Verify UnifiedPortfolioAllocator integration and pure dictionary clean state (0 defeat devices).
"""

import math
import time
import numpy as np
import pytest

from src.risk.dynamic_regime_leverage_allocator import DynamicRegimeLeverageAllocator
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


class TestEmpiricalChallenger2N3379Stress:

    @pytest.fixture(autouse=True)
    def setup_allocators(self):
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

    def test_n3379_full_production_universe_allocation(self):
        """Task 1: Full high-dimensional universe N=3,379 stress test."""
        N = 3379
        np.random.seed(42)

        # Expected returns for 3,379 assets
        rets = np.random.uniform(0.005, 0.08, N)
        # Give top 100 assets high expected returns
        rets[:100] = np.random.uniform(0.15, 0.50, 100)

        # Diagonal covariance (efficient for N=3,379 Kelly solve)
        cov_diag = np.random.uniform(0.02, 0.08, N)
        cov = np.diag(cov_diag)

        # 11 GICS sectors mapping for N=3,379
        sector_names = [
            "Information Technology", "Financials", "Health Care",
            "Consumer Discretionary", "Communication Services", "Industrials",
            "Consumer Staples", "Energy", "Utilities", "Real Estate", "Materials"
        ]
        sector_indices = {s: [] for s in sector_names}
        for i in range(N):
            sec = sector_names[i % len(sector_names)]
            sector_indices[sec].append(i)

        # Asset betas ~ Uniform(0.6, 2.4)
        betas = np.random.uniform(0.6, 2.4, N)

        # Test across 5 representative leverage levels
        test_leverages = [0.15, 0.60, 0.95, 1.10, 1.25]

        for lev in test_leverages:
            t0 = time.perf_counter()
            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=rets,
                cov_matrix=cov,
                leverage=lev,
                max_single_stock=0.05,
                max_sector_exposure=0.25,
                sector_indices=sector_indices,
                asset_betas=betas,
            )
            elapsed = time.perf_counter() - t0

            # 1. Performance check
            assert elapsed < 5.0, f"N=3379 allocation took {elapsed:.2f}s (exceeded 5.0s budget)"

            # 2. Simplex conservation: |sum(w) + w_cash - lev| <= 1e-6
            tot = float(np.sum(w) + w_cash)
            assert math.isclose(tot, lev, abs_tol=1e-6), (
                f"Simplex violated for N={N}, L={lev}: tot={tot}"
            )
            assert np.all(w >= -1e-12), "Negative weight detected in N=3379"
            assert w_cash >= -1e-12, "Negative cash detected in N=3379"

            # 3. Single stock water-filling bound: w_i <= 0.05 * L_t
            cap_stock = 0.05 * lev
            max_w = float(np.max(w))
            assert max_w <= cap_stock + 1e-9, (
                f"Stock cap breached: {max_w} > {cap_stock} (L={lev})"
            )

            # 4. Sector water-filling bound: sector_sum <= 0.25 * L_t
            cap_sector = 0.25 * lev
            for sec_name, idxs in sector_indices.items():
                sec_sum = float(np.sum(w[idxs]))
                assert sec_sum <= cap_sector + 1e-9, (
                    f"Sector {sec_name} breached: {sec_sum} > {cap_sector} (L={lev})"
                )

            # 5. Beta clamping: beta_port <= 1.000 whenever L_t > 1.00
            if lev > 1.00:
                port_beta = float(np.sum(w * betas))
                assert port_beta <= 1.000001, (
                    f"Beta clamping failed: {port_beta} > 1.000 (L={lev})"
                )

    def test_simplex_budget_extreme_sweep(self):
        """Task 2: High-density sweep over leverage, dimensions, and condition numbers."""
        np.random.seed(777)
        for N in [1, 2, 8, 25, 75, 150, 500]:
            # Ill-conditioned random covariance
            A = np.random.randn(N, N)
            cov = A @ A.T + 1e-4 * np.eye(N)
            for lev in [0.15, 0.25, 0.50, 0.75, 0.95, 1.00, 1.15, 1.25]:
                rets = np.random.uniform(-0.10, 0.20, N)
                w, w_cash = self.allocator.compute_fractional_kelly_weights(
                    predicted_returns=rets,
                    cov_matrix=cov,
                    leverage=lev,
                )
                tot = float(np.sum(w) + w_cash)
                assert math.isclose(tot, lev, abs_tol=1e-6), (
                    f"Simplex budget failure: N={N}, L={lev}, total={tot}"
                )

    def test_bounded_water_filling_extreme_sector_concentration(self):
        """Task 3: Sector concentration stress with 500 assets in Sector A having 10,000% return."""
        N = 1000
        cov = np.eye(N) * 0.04
        rets = np.full(N, 0.01)
        rets[:500] = 100.0  # Astronomical return in Sector A

        sector_indices = {
            "Sector_A": list(range(0, 500)),
            "Sector_B": list(range(500, 1000)),
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

        sum_a = float(np.sum(w[:500]))
        sum_b = float(np.sum(w[500:]))
        cap_sec = 0.25 * lev
        cap_stock = 0.05 * lev

        assert sum_a <= cap_sec + 1e-9, f"Sector A breached: {sum_a} > {cap_sec}"
        assert math.isclose(sum_a, cap_sec, abs_tol=1e-6)
        assert sum_b <= cap_sec + 1e-9, f"Sector B breached: {sum_b} > {cap_sec}"
        assert float(np.max(w)) <= cap_stock + 1e-9
        assert math.isclose(float(np.sum(w) + w_cash), lev, abs_tol=1e-6)

    def test_portfolio_beta_clamping_exhaustive_stress(self):
        """Task 4: Adversarial portfolio beta clamping under extreme betas (up to 5.0)."""
        np.random.seed(999)
        N = 50
        cov = np.eye(N) * 0.04
        rets = np.random.uniform(0.05, 0.20, N)

        # High beta profile: mean beta = 3.2
        betas = np.random.uniform(2.0, 5.0, N)

        for lev in [1.01, 1.10, 1.20, 1.25, 1.50]:
            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=rets,
                cov_matrix=cov,
                leverage=lev,
                asset_betas=betas,
            )
            port_beta = float(np.sum(w * betas))
            assert port_beta <= 1.000001, f"Lev={lev}: port_beta={port_beta} > 1.000"
            assert math.isclose(float(np.sum(w) + w_cash), lev, abs_tol=1e-6)

        # Unleveraged exemption check: L <= 1.00 must not clamp beta <= 1.00
        for lev in [0.50, 0.85, 1.00]:
            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=rets,
                cov_matrix=cov,
                leverage=lev,
                asset_betas=betas,
            )
            port_beta = float(np.sum(w * betas))
            # Since min beta is 2.0 and lev >= 0.50, unconstrained beta is > 1.00
            assert port_beta > 1.00, f"Unleveraged L={lev} was inappropriately clamped to {port_beta}"
            assert math.isclose(float(np.sum(w) + w_cash), lev, abs_tol=1e-6)

    def test_leveraged_leland_buffer_expansion_and_bypass_triggers(self):
        """Task 5: Leland dynamic buffer formula and instant bypass triggers."""
        # 1. Bandwidth formula
        delta_base = 0.015
        assert math.isclose(
            self.allocator.calculate_leveraged_leland_buffer(delta_base, 1.00),
            0.015,
            abs_tol=1e-9
        )
        assert math.isclose(
            self.allocator.calculate_leveraged_leland_buffer(delta_base, 1.25),
            0.015 * (1.0 + 0.40 * 0.25),  # 0.015 * 1.10 = 0.0165
            abs_tol=1e-9
        )
        assert math.isclose(
            self.allocator.calculate_leveraged_leland_buffer(delta_base, 0.30),
            0.015,
            abs_tol=1e-9
        )

        # 2. UnifiedPortfolioAllocator Leland buffer execution
        # Bypass Case 1: Fresh entry (current == 0.0) -> must execute exactly to target
        target = np.array([0.04, 0.03, 0.02])
        curr_entry = np.array([0.0, 0.0, 0.02])
        vols = np.array([0.15, 0.15, 0.15])
        out_entry = self.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=target,
            current_weights=curr_entry,
            volatilities=vols,
            leverage=1.25,
        )
        assert math.isclose(out_entry[0], 0.04, abs_tol=1e-5), "Fresh entry 0 did not bypass"
        assert math.isclose(out_entry[1], 0.03, abs_tol=1e-5), "Fresh entry 1 did not bypass"
        assert math.isclose(out_entry[2], 0.02, abs_tol=1e-5), "Existing unchanged held"

        # Bypass Case 2: Full exit (target == 0.0) -> must execute exactly to 0.0
        curr_exit = np.array([0.04, 0.03, 0.02])
        target_exit = np.array([0.0, 0.0, 0.02])
        out_exit = self.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=target_exit,
            current_weights=curr_exit,
            volatilities=vols,
            leverage=1.25,
        )
        assert math.isclose(out_exit[0], 0.0, abs_tol=1e-5), "Full exit 0 did not bypass"
        assert math.isclose(out_exit[1], 0.0, abs_tol=1e-5), "Full exit 1 did not bypass"
        assert math.isclose(out_exit[2], 0.02, abs_tol=1e-5), "Existing unchanged held"

        # Bypass Case 3: Severe drift (drift >= 50%) -> must execute to target
        # Target = 0.04. Current = 0.065 -> Drift = 0.025 / 0.04 = 62.5% >= 50%
        curr_drift = np.array([0.065, 0.042])
        target_drift = np.array([0.040, 0.040])  # Asset 1 drift = 0.002 / 0.04 = 5% < 50%
        vols_drift = np.array([0.15, 0.15])
        out_drift = self.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=target_drift,
            current_weights=curr_drift,
            volatilities=vols_drift,
            leverage=1.25,
        )
        assert math.isclose(out_drift[0], 0.040, abs_tol=1e-4), "Severe drift did not bypass"
        assert math.isclose(out_drift[1], 0.042, abs_tol=1e-4), "Minor drift did not hold current"

    def test_pure_dictionary_and_no_defeat_devices(self):
        """Task 6: Strictly verify pure dict type and 0 defeat devices in UnifiedPortfolioAllocator."""
        assert type(UnifiedPortfolioAllocator.REGIME_ADAPTIVE_RISK_BUDGET) is dict
        for regime, cfg in UnifiedPortfolioAllocator.REGIME_ADAPTIVE_RISK_BUDGET.items():
            assert type(cfg) is dict, f"Regime {regime} is not pure dict: {type(cfg)}"
            assert "max_exposure" in cfg
            assert "min_exposure" in cfg
            assert 0.0 <= cfg["min_exposure"] <= cfg["max_exposure"] <= 1.00
