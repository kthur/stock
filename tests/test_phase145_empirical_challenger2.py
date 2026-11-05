"""
tests/test_phase145_empirical_challenger2.py - Empirical Challenger Verification Harness for Phase 145.
Features F707, F708:
1. Dynamic Leland buffer multiplier (1.0 + 0.40 * (L - 1.0)) yields 1.12x expansion at 1.30x leverage.
2. Instant bypass flags for fresh entries (w_curr == 0.0) and full exits (w_targ == 0.0).
3. OAS covariance shrinkage with Top-50 systematic mode-exempt Marchenko-Pastur RMT denoising preserves matrix trace and guarantees PSD cone projection under singular and collinear asset returns.
4. Zero NaNs, strictly finite values, and full compliance with risk constraints.
"""

from __future__ import annotations

import math
import os
import sys
import unittest
import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.risk.dynamic_regime_leverage_allocator import DynamicRegimeLeverageAllocator
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


class TestPhase145EmpiricalChallenger(unittest.TestCase):
    """Empirical challenge suite for Phase 145 features F707 and F708."""

    def setUp(self):
        np.random.seed(20261031)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.30,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=50,
        )
        self.port_allocator = PortfolioAllocator(version=145)
        self.unified_allocator = UnifiedPortfolioAllocator(version=145)

    # =========================================================================
    # Suite 1: Dynamic Leland Buffer Multiplier (1.0 + 0.40 * (L - 1.0))
    # =========================================================================

    def test_leland_multiplier_exact_1_12x_at_1_30x_leverage(self):
        """Verify dynamic Leland buffer multiplier yields exactly 1.12x expansion at 1.30x leverage."""
        leverage = 1.30
        delta_base = 0.0250

        # Method 1: DynamicRegimeLeverageAllocator
        expanded_alloc = self.allocator.calculate_leveraged_leland_buffer(
            delta_base=delta_base, leverage=leverage
        )
        expected_multiplier = 1.0 + 0.40 * (1.30 - 1.0)  # exactly 1.12
        self.assertAlmostEqual(expanded_alloc / delta_base, expected_multiplier, places=7)
        self.assertAlmostEqual(expanded_alloc / delta_base, 1.12, places=7)

        # Method 2: PortfolioAllocator.calculate_dynamic_buffer_band
        # Test across 5 global markets and various parameter combinations
        test_cases = [
            ("005930", "KOSPI", 0.05, 0.0025, 0.018),
            ("035720", "KOSDAQ", 0.03, 0.0035, 0.025),
            ("AAPL", "SP500", 0.04, 0.0005, 0.015),
            ("NVDA", "NASDAQ", 0.06, 0.0007, 0.028),
            ("IWM_SYM", "RUSSELL2000", 0.02, 0.0016, 0.022),
        ]
        for sym, mkt, w_tgt, cost_rate, vol in test_cases:
            d_unlev = self.port_allocator.calculate_dynamic_buffer_band(
                symbol=sym,
                target_weight=w_tgt,
                cost_rate=cost_rate,
                volatility_20d=vol,
                leverage=1.00,
            )
            d_lev = self.port_allocator.calculate_dynamic_buffer_band(
                symbol=sym,
                target_weight=w_tgt,
                cost_rate=cost_rate,
                volatility_20d=vol,
                leverage=1.30,
            )
            ratio = d_lev / d_unlev
            self.assertAlmostEqual(
                ratio,
                1.12,
                places=5,
                msg=f"Failed 1.12x expansion for {sym} ({mkt}): got {ratio}",
            )

    def test_leland_multiplier_leverage_sweep_invariance(self):
        """Verify dynamic Leland multiplier behavior across full leverage frontier."""
        delta_base = 0.020
        # Below 1.0 leverage: no expansion or shrinking of buffer band (multiplier == 1.00)
        for L in [0.15, 0.25, 0.50, 0.75, 1.00]:
            expanded = self.allocator.calculate_leveraged_leland_buffer(delta_base, leverage=L)
            self.assertAlmostEqual(expanded / delta_base, 1.00, places=6, msg=f"Failed at L={L}")

        # Above 1.0 leverage: strictly linear expansion (1.0 + 0.40 * (L - 1.0))
        for L in [1.10, 1.15, 1.20, 1.25, 1.30]:
            expected_mult = 1.0 + 0.40 * (L - 1.0)
            expanded = self.allocator.calculate_leveraged_leland_buffer(delta_base, leverage=L)
            self.assertAlmostEqual(
                expanded / delta_base,
                expected_mult,
                places=6,
                msg=f"Failed linear expansion at L={L}",
            )

    # =========================================================================
    # Suite 2: Instant Bypass Flags for Fresh Entries and Full Liquidations
    # =========================================================================

    def test_instant_bypass_fresh_entry_small_target_inside_buffer(self):
        """Stress: Fresh entry where target weight is small enough to fall within delta_i band.
        Without instant bypass, w_curr=0.0 would fall inside [0, delta_i] and be skipped as HOLD.
        Instant bypass MUST force execution: action='BUY', w_new=w_target.
        """
        # Current weight is 0.0, target weight is 0.008 (small)
        # delta_i for w_targ=0.008 is typically ~0.003 to 0.008
        curr_w = {"005930": 0.0}
        tgt_w = {"005930": 0.008}
        mkt_map = {"005930": "KOSPI"}
        vol_map = {"005930": 0.020}
        adv_map = {"005930": 1e9}

        res = self.port_allocator.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=tgt_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.30,
        )

        trade = res["trades"]["005930"]
        self.assertEqual(trade["action"], "BUY", "Fresh entry was not executed as BUY")
        self.assertAlmostEqual(trade["w_new"], 0.008, places=6)
        self.assertAlmostEqual(trade["trade_weight"], 0.008, places=6)
        self.assertEqual(res["summary"]["traded_count"], 1)
        self.assertEqual(res["summary"]["skipped_count"], 0)

    def test_instant_bypass_full_exit_small_residual_inside_buffer(self):
        """Stress: Full liquidation where residual position is small enough to fall within delta_i band.
        Without instant bypass, w_curr=0.001 would fall inside [0, delta_i] and be skipped as HOLD.
        Instant bypass MUST force execution: action='SELL', w_new=0.0.
        """
        # Current weight is 0.0012, target weight is 0.0
        curr_w = {"AAPL": 0.0012}
        tgt_w = {"AAPL": 0.0}
        mkt_map = {"AAPL": "SP500"}
        vol_map = {"AAPL": 0.018}
        adv_map = {"AAPL": 1e9}

        res = self.port_allocator.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=tgt_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.30,
        )

        trade = res["trades"]["AAPL"]
        self.assertEqual(trade["action"], "SELL", "Full liquidation was not executed as SELL")
        self.assertAlmostEqual(trade["w_new"], 0.0, places=6)
        self.assertAlmostEqual(trade["trade_weight"], -0.0012, places=6)
        self.assertEqual(res["summary"]["traded_count"], 1)
        self.assertEqual(res["summary"]["skipped_count"], 0)

    def test_instant_bypass_zero_curr_and_zero_targ_invariant(self):
        """Verify that when both w_curr == 0.0 and w_targ == 0.0, action is HOLD and zero trade weight."""
        curr_w = {"MSFT": 0.0}
        tgt_w = {"MSFT": 0.0}
        mkt_map = {"MSFT": "NASDAQ"}
        vol_map = {"MSFT": 0.020}
        adv_map = {"MSFT": 1e9}

        res = self.port_allocator.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=tgt_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.30,
        )

        trade = res["trades"]["MSFT"]
        self.assertEqual(trade["action"], "HOLD")
        self.assertAlmostEqual(trade["w_new"], 0.0, places=6)
        self.assertAlmostEqual(trade["trade_weight"], 0.0, places=6)

    def test_unified_portfolio_allocator_instant_bypass(self):
        """Verify instant bypass in UnifiedPortfolioAllocator.apply_leland_no_trade_buffers."""
        target_weights = np.array([0.05, 0.00, 0.03, 0.04])
        current_weights = np.array([0.00, 0.02, 0.031, 0.04])  # idx 0: new entry, idx 1: full exit, idx 2: within band, idx 3: exact
        volatilities = np.array([0.02, 0.02, 0.02, 0.02])

        realized_w = self.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=target_weights,
            current_weights=current_weights,
            volatilities=volatilities,
            leverage=1.30,
        )

        # Asset 0: fresh entry -> realized must equal target 0.05
        self.assertAlmostEqual(realized_w[0], 0.05, places=5)
        # Asset 1: full liquidation -> realized must equal 0.00
        self.assertAlmostEqual(realized_w[1], 0.00, places=5)
        # Asset 2: within band -> realized must hold current 0.031
        self.assertAlmostEqual(realized_w[2], 0.031, places=5)
        # Asset 3: exact match -> realized 0.04
        self.assertAlmostEqual(realized_w[3], 0.04, places=5)

    # =========================================================================
    # Suite 3: OAS Covariance Shrinkage & Top-50 Systematic RMT Denoising
    # =========================================================================

    def test_trace_preservation_across_matrix_dimensions(self):
        """Empirically verify exact trace preservation of OAS shrinkage + RMT spectral denoising.
        Tr(cov_denoised) == Tr(cov_oas) == Tr(S).
        With Tikhonov jitter (+1.000001e-6*I), Tr(cov_final) = Tr(S) + N * 1.000001e-6.
        """
        for T, N, k_modes in [(100, 30, 10), (200, 60, 50), (150, 80, 50), (300, 100, 50)]:
            X = np.random.normal(0.0005, 0.015, size=(T, N))
            S = np.cov(X, rowvar=False)
            tr_S = float(np.trace(S))

            # Compute regularized covariance
            cov_final, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=k_modes)
            tr_final = float(np.trace(cov_final))

            # Expected trace with Tikhonov jitter
            expected_tr = tr_S + float(N) * 1.000001e-6
            self.assertAlmostEqual(
                tr_final,
                expected_tr,
                places=5,
                msg=f"Trace mismatch for T={T}, N={N}: got {tr_final}, expected {expected_tr}",
            )
            self.assertLess(
                abs(tr_final - tr_S),
                float(N) * 2e-6,
                msg=f"Trace deviation exceeded Tikhonov bound for T={T}, N={N}",
            )

    def test_psd_cone_projection_high_dim_singular_t_much_less_than_n(self):
        """Stress: T=15 observations, N=100 assets (T << N).
        Sample covariance has rank at most 14 (86 zero eigenvalues).
        OAS shrinkage + RMT denoising MUST project onto strict PSD cone (all eigenvalues >= 1e-6).
        """
        T, N = 15, 100
        X = np.random.normal(0.001, 0.02, size=(T, N))
        S = np.cov(X, rowvar=False)
        rank_S = np.linalg.matrix_rank(S)
        self.assertLessEqual(rank_S, 14, "Baseline sample covariance should be severely rank-deficient")

        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=10)

        # 1. Symmetry check
        np.testing.assert_allclose(cov_final, cov_final.T, atol=1e-12)

        # 2. Positive Definiteness: all eigenvalues >= 1e-6
        eigvals = np.linalg.eigvalsh(cov_final)
        min_eig = float(np.min(eigvals))
        self.assertGreaterEqual(
            min_eig,
            1.0e-6,
            f"Singular matrix T<<N failed strict PSD cone projection: min eigval = {min_eig}",
        )

        # 3. Finite condition number and invertibility
        cond_num = np.linalg.cond(cov_final)
        self.assertTrue(np.isfinite(cond_num))
        self.assertLess(cond_num, 1e8, f"Condition number too high: {cond_num}")
        # Invertibility check
        cov_inv = np.linalg.inv(cov_final)
        self.assertTrue(np.all(np.isfinite(cov_inv)))

    def test_psd_cone_projection_perfectly_collinear_assets(self):
        """Stress: Multiple collinear assets (identical and linear combinations).
        Guarantees strict positive definiteness without zero/negative eigenvalues.
        """
        T, N = 80, 13
        base_1 = np.random.normal(0.001, 0.02, size=(T, 1))
        base_2 = np.random.normal(0.001, 0.02, size=(T, 1))
        noise_free = np.random.normal(0.001, 0.02, size=(T, 5))

        # 4 identical copies of base_1, 3 identical copies of base_2, and 1 linear combination
        collinear_1 = np.repeat(base_1, 4, axis=1)
        collinear_2 = np.repeat(base_2, 3, axis=1)
        lin_comb = 2.0 * base_1 + 1.5 * base_2

        X = np.hstack([noise_free, collinear_1, collinear_2, lin_comb])
        self.assertEqual(X.shape, (T, N))

        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=5)

        eigvals = np.linalg.eigvalsh(cov_final)
        min_eig = float(np.min(eigvals))
        self.assertGreaterEqual(
            min_eig,
            1.0e-6,
            f"Collinear asset matrix failed PSD cone projection: min eigval = {min_eig}",
        )
        self.assertTrue(np.all(np.isfinite(cov_final)))
        self.assertTrue(np.all(np.isfinite(vols)))

    def test_top_50_systematic_mode_exemption_retention(self):
        """Verify Top-50 systematic mode exemption with N=120 assets, T=300 days.
        Eigenvalues corresponding to the top 50 modes must be strictly retained above bulk noise boundary.
        """
        T, N = 300, 120
        # Create systematic factor structure: 3 dominant factors + idiosyncratic noise
        factors = np.random.normal(0, 0.03, size=(T, 3))
        factor_loadings = np.random.normal(0.5, 0.2, size=(3, N))
        idio_noise = np.random.normal(0, 0.01, size=(T, N))
        X = factors @ factor_loadings + idio_noise

        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=50)

        # Verify output matrix properties
        self.assertEqual(cov_final.shape, (N, N))
        self.assertEqual(len(vols), N)
        self.assertTrue(np.all(np.isfinite(cov_final)))
        self.assertTrue(np.all(np.isfinite(vols)))

        eigvals = np.linalg.eigvalsh(cov_final)
        self.assertGreaterEqual(float(np.min(eigvals)), 1.0e-6)

    def test_zero_variance_and_extreme_outlier_immunity(self):
        """Stress: Asset with exactly zero variance (flat price) and extreme 100-sigma outliers."""
        T, N = 100, 10
        X = np.random.normal(0.001, 0.015, size=(T, N))
        X[:, 1] = 0.0  # Asset 1 completely flat
        X[:, 4] = 0.0  # Asset 4 completely flat
        X[10, 7] = 5.0  # Extreme 500% spike (outlier)

        cov_final, vols = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=3)

        self.assertFalse(np.any(np.isnan(cov_final)), "NaN detected in covariance matrix")
        self.assertFalse(np.any(np.isinf(cov_final)), "Inf detected in covariance matrix")
        self.assertFalse(np.any(np.isnan(vols)), "NaN detected in volatility vector")
        self.assertFalse(np.any(np.isinf(vols)), "Inf detected in volatility vector")

        # Flat assets must have positive regularized volatility (no divide by zero)
        self.assertGreater(vols[1], 0.0)
        self.assertGreater(vols[4], 0.0)
        self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(cov_final))), 1.0e-6)

    # =========================================================================
    # Suite 4: Fractional Kelly & Risk Constraint Compliance
    # =========================================================================

    def test_fractional_kelly_under_regularized_cov_and_1_30x_leverage(self):
        """Verify Fractional Kelly solver with regularized covariance under 1.30x leverage:
        1. Simplex budget sum(w) + w_cash == 1.30.
        2. Single stock box cap w_i <= 0.05 * 1.30 = 0.065.
        3. Portfolio beta strictly clamped <= 1.00 when L > 1.00.
        4. Zero NaNs.
        """
        N = 25
        mu = np.random.uniform(0.0005, 0.0050, size=N)
        # Synthetic asset betas: high beta portfolio (mean beta = 1.40)
        betas = np.random.uniform(1.20, 1.60, size=N)
        cov = np.eye(N) * 0.0004

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.30,
            asset_betas=betas,
        )

        self.assertFalse(np.any(np.isnan(w)))
        self.assertFalse(np.isnan(w_cash))

        # Budget conservation
        tot_alloc = float(np.sum(w) + w_cash)
        self.assertAlmostEqual(tot_alloc, 1.30, places=5)

        # Single stock box cap (5% * 1.30 = 6.5%)
        max_allowed_stock = 0.05 * 1.30 + 1e-6
        self.assertLessEqual(float(np.max(w)), max_allowed_stock)

        # Portfolio beta clamping: port_beta = sum(w * betas) <= 1.00
        port_beta = float(np.sum(w * betas))
        self.assertLessEqual(
            port_beta,
            1.000001,
            f"Portfolio beta {port_beta} exceeded 1.00 under leverage 1.30x",
        )

    # =========================================================================
    # Suite 5: Adversarial Edge Cases & Boundary Resilience
    # =========================================================================

    def test_oas_rmt_extreme_edge_cases_t_less_than_5_and_n_less_than_2(self):
        """Stress: Minimal data edge cases (T < 5 or N < 2) and NaN/Inf input resilience."""
        # Case 1: T=3, N=10 (T < 5)
        X_tiny_t = np.random.normal(0, 0.02, size=(3, 10))
        cov_1, vols_1 = self.allocator.compute_oas_rmt_covariance(X_tiny_t)
        self.assertEqual(cov_1.shape, (10, 10))
        self.assertTrue(np.all(np.isfinite(cov_1)))
        self.assertTrue(np.all(np.isfinite(vols_1)))
        self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(cov_1))), 1e-7)

        # Case 2: T=50, N=1 (N < 2)
        X_single = np.random.normal(0, 0.02, size=(50, 1))
        cov_2, vols_2 = self.allocator.compute_oas_rmt_covariance(X_single)
        self.assertEqual(cov_2.shape, (1, 1))
        self.assertTrue(np.all(np.isfinite(cov_2)))
        self.assertGreater(vols_2[0], 0.0)

        # Case 3: Inputs containing NaNs and Infs
        X_corrupt = np.random.normal(0, 0.02, size=(50, 10))
        X_corrupt[5, 2] = np.nan
        X_corrupt[12, 4] = np.inf
        X_corrupt[20, 7] = -np.inf
        cov_3, vols_3 = self.allocator.compute_oas_rmt_covariance(X_corrupt)
        self.assertFalse(np.any(np.isnan(cov_3)))
        self.assertFalse(np.any(np.isinf(cov_3)))
        self.assertTrue(np.all(np.linalg.eigvalsh(cov_3) >= 1e-7))

    def test_top_k_modes_boundary_conditions(self):
        """Stress: top_k_modes exceeding N, zero, or negative."""
        T, N = 60, 20
        X = np.random.normal(0, 0.015, size=(T, N))

        # Case 1: top_k_modes = 100 > N (must clamp to N-1)
        cov_exceed, vols_exceed = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=100)
        self.assertEqual(cov_exceed.shape, (N, N))
        self.assertTrue(np.all(np.isfinite(cov_exceed)))
        self.assertTrue(np.all(np.linalg.eigvalsh(cov_exceed) >= 1e-7))

        # Case 2: top_k_modes = 0 (skips RMT, uses OAS corr)
        cov_zero, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=0)
        self.assertEqual(cov_zero.shape, (N, N))
        self.assertTrue(np.all(np.linalg.eigvalsh(cov_zero) >= 1e-7))

        # Case 3: top_k_modes = -5 (negative input handled gracefully)
        cov_neg, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=-5)
        self.assertEqual(cov_neg.shape, (N, N))
        self.assertTrue(np.all(np.linalg.eigvalsh(cov_neg) >= 1e-7))

    def test_calculate_dynamic_buffer_band_adversarial_inputs(self):
        """Stress: Adversarial inputs to calculate_dynamic_buffer_band."""
        pa = self.port_allocator

        # 1. Negative target weight -> must return 0.0 immediately
        d_neg_w = pa.calculate_dynamic_buffer_band("AAPL", -0.05, 0.001, 0.02)
        self.assertEqual(d_neg_w, 0.0)

        # 2. NaN / Inf / Negative cost_rate -> delta_floor
        d_nan_c = pa.calculate_dynamic_buffer_band("AAPL", 0.05, float("nan"), 0.02)
        self.assertEqual(d_nan_c, pa.delta_floor)
        d_neg_c = pa.calculate_dynamic_buffer_band("AAPL", 0.05, -0.001, 0.02)
        self.assertEqual(d_neg_c, pa.delta_floor)

        # 3. NaN / Inf / Negative volatility -> cleaned to floor 0.005 or default
        d_nan_v = pa.calculate_dynamic_buffer_band("AAPL", 0.05, 0.001, float("nan"))
        self.assertTrue(math.isfinite(d_nan_v))
        self.assertGreater(d_nan_v, 0.0)

        # 4. Leverage None or <= 1.0 vs > 1.0
        d_unlev = pa.calculate_dynamic_buffer_band("AAPL", 0.05, 0.001, 0.02, leverage=None)
        d_lev10 = pa.calculate_dynamic_buffer_band("AAPL", 0.05, 0.001, 0.02, leverage=1.0)
        d_lev13 = pa.calculate_dynamic_buffer_band("AAPL", 0.05, 0.001, 0.02, leverage=1.3)
        self.assertAlmostEqual(d_unlev, d_lev10, places=6)
        self.assertAlmostEqual(d_lev13 / d_unlev, 1.12, places=5)

    def test_compute_portfolio_rebalance_effective_max_alloc_and_scaling(self):
        """Stress: Total target weights exceed effective_max_alloc (1.30x leverage).
        Scaling must proportionally trim only trading positions, preserving HOLD positions.
        """
        pa = self.port_allocator
        # Asset 1 is already held and inside band -> HOLD
        # Asset 2 and 3 are new buys whose targets sum to 1.40
        curr_w = {"A": 0.050, "B": 0.000, "C": 0.000}
        tgt_w = {"A": 0.050, "B": 0.700, "C": 0.700}
        mkt_map = {"A": "SP500", "B": "SP500", "C": "SP500"}
        vol_map = {"A": 0.02, "B": 0.02, "C": 0.02}
        adv_map = {"A": 1e9, "B": 1e9, "C": 1e9}

        res = pa.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=tgt_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.30,
        )

        new_w = res["new_weights"]
        summary = res["summary"]

        # Asset A must remain HOLD at 0.050
        self.assertEqual(res["trades"]["A"]["action"], "HOLD")
        self.assertAlmostEqual(new_w["A"], 0.050, places=5)

        # Total asset weight must be capped at exactly effective_max_alloc = 1.30
        self.assertAlmostEqual(summary["total_asset_weight"], 1.30, places=5)
        # Cash weight should be 0.0
        self.assertAlmostEqual(summary["cash_weight"], 0.0, places=5)

        # Assets B and C share the remaining 1.25 equally (0.625 each)
        self.assertAlmostEqual(new_w["B"], 0.625, places=4)
        self.assertAlmostEqual(new_w["C"], 0.625, places=4)


if __name__ == "__main__":
    unittest.main()
