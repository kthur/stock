"""
tests/test_phase4_m2_challenger_stress.py - Empirical Challenger Stress Test Suite
Comprehensive adversarial stress-tests for Milestone 2 Features F28 to F30 in unified_portfolio_allocator.py:
1. Downside Semi-Covariance (Sortino) EVT-CVaR Optimization under extreme market conditions:
   - Rank-deficient / singular covariance matrices (N > T, identical collinear asset returns, zero variance).
   - Zero downside variance (all positive returns) vs pure downside variance (all negative returns).
   - Monotonicity of Sortino / downside allocation as semi_cov_weight sweeps from 0.0 to 1.0.
2. Dynamic Model Conviction & Return-Dispersion Blending:
   - Extreme return dispersions (zero dispersion, massive dispersion > 10.0, negative extremes).
   - Extreme regime probabilities (pure Crisis, pure Bull, pure Sideways, degenerate/empty dicts).
   - Strict weight conservation sum(w_m) = 1.0000 and non-negativity across all configurations.
3. Market-Specific STT & Fee-Aware Leland Dynamic Buffer Bands:
   - Korean assets (.KS, .KQ, 6-digit) vs US assets under extreme volatility (0.001 to 0.50) and costs (0.1 to 500 bps).
   - Verification of wider Korean buffers (c_i >= 25 bps STT floor) vs narrower US buffers (c_i <= 8 bps).
   - Edge case verification: new entries, liquidations, custom array vs scalar overrides.
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.risk.portfolio_allocator import PortfolioAllocator


# ==============================================================================
# 1. Downside Semi-Covariance (F28) Stress Tests
# ==============================================================================

class TestDownsideSemiCovarianceExtremeConditions:
    """Adversarial stress-testing of F28 Downside Semi-Covariance."""

    def test_rank_deficient_singular_n_greater_than_t(self):
        """
        Stress-test rank-deficient covariance when N (assets) > T (time observations).
        For example: N=15 assets, T=6 time steps.
        Must not crash with LinAlgError or NaN; must return valid weights summing to 1.0.
        """
        np.random.seed(101)
        N = 15
        T = 6
        returns = np.random.normal(0.001, 0.02, (T, N))
        symbols = [f"SYM_{i}" for i in range(N)]
        df = pd.DataFrame(returns, columns=symbols)

        allocator = UnifiedPortfolioAllocator(max_single_weight=0.30)
        
        # Test calculate_cvar_weights with cov_matrix=None (auto-computed)
        w = allocator.calculate_cvar_weights(
            returns_df=df,
            cov_matrix=None,
            use_downside_semi_cov=True,
            semi_cov_weight=0.40,
        )

        assert len(w) == N
        assert np.all(np.isfinite(w)), f"Weights contain non-finite values: {w}"
        assert np.all(w >= -1e-5), f"Found negative weights: {w[w < 0]}"
        assert np.isclose(np.sum(w), 1.0, atol=1e-3), f"Weights sum to {np.sum(w)}, expected 1.0"
        assert np.max(w) <= allocator.max_single_weight + 1e-4

    def test_identical_collinear_assets(self):
        """
        Stress-test collinear returns:
        Asset B is an exact duplicate of Asset A; Asset C is 2x Asset A.
        The covariance matrix is completely singular (rank 1).
        """
        T = 40
        np.random.seed(102)
        base_ret = np.random.normal(0.002, 0.015, T)
        
        # 4 assets where 0 and 1 are identical, 2 is scaled, 3 is uncorrelated
        ret_matrix = np.column_stack([
            base_ret,
            base_ret,
            2.0 * base_ret,
            np.random.normal(0.001, 0.02, T),
        ])
        df = pd.DataFrame(ret_matrix, columns=["A", "B", "C", "D"])

        allocator = UnifiedPortfolioAllocator(max_single_weight=0.50)
        w = allocator.calculate_cvar_weights(
            returns_df=df,
            use_downside_semi_cov=True,
            semi_cov_weight=0.35,
        )

        assert len(w) == 4
        assert np.all(np.isfinite(w))
        assert np.isclose(np.sum(w), 1.0, atol=1e-3)
        assert np.all(w >= -1e-5)
        # Identical assets A and B should receive virtually identical allocations
        assert np.isclose(w[0], w[1], atol=1e-3), f"Weights for identical assets diverged: {w[0]} vs {w[1]}"

    def test_zero_downside_variance_all_positive_returns(self):
        """
        Stress-test scenario where ALL assets have ONLY positive returns (zero downside variance).
        downside_diff = min(r - 0, 0) is identically 0 for all assets and all dates.
        Semi-covariance matrix is 0 + regularization jitter.
        Optimization must not divide by zero or fail.
        """
        T = 50
        np.random.seed(103)
        # All returns strictly positive between +0.5% and +5.0%
        pos_rets = np.random.uniform(0.005, 0.05, (T, 4))
        df = pd.DataFrame(pos_rets, columns=["P1", "P2", "P3", "P4"])

        allocator = UnifiedPortfolioAllocator()
        w = allocator.calculate_cvar_weights(
            returns_df=df,
            use_downside_semi_cov=True,
            semi_cov_weight=0.50,
        )

        assert len(w) == 4
        assert np.all(np.isfinite(w))
        assert np.isclose(np.sum(w), 1.0, atol=1e-3)
        assert np.all(w >= -1e-5)

    def test_pure_downside_variance_all_negative_returns(self):
        """
        Stress-test scenario where ALL assets have ONLY negative returns (pure downside variance).
        downside_diff = min(r - 0, 0) == r for all t.
        Total covariance equals downside semi-covariance (up to mean adjustments).
        Must produce stable, non-negative weights summing to 1.0.
        """
        T = 50
        np.random.seed(104)
        neg_rets = np.random.uniform(-0.05, -0.005, (T, 4))
        df = pd.DataFrame(neg_rets, columns=["N1", "N2", "N3", "N4"])

        allocator = UnifiedPortfolioAllocator()
        w = allocator.calculate_cvar_weights(
            returns_df=df,
            use_downside_semi_cov=True,
            semi_cov_weight=0.70,
        )

        assert len(w) == 4
        assert np.all(np.isfinite(w))
        assert np.isclose(np.sum(w), 1.0, atol=1e-3)
        assert np.all(w >= -1e-5)

    def test_downside_vs_upside_skew_asymmetric_allocation(self):
        """
        Asset Safe: All positive or tiny negative returns (virtually zero downside).
        Asset Toxic: Huge negative tail drops (-10%), but high positive gains on average.
        With semi_cov active, allocation to Asset Safe must strictly dominate Asset Toxic.
        """
        T = 100
        np.random.seed(105)
        # Asset Safe: small positive drift, very mild fluctuations
        ret_safe = np.random.normal(0.005, 0.004, T)
        # Asset Toxic: volatile, severe negative left tail crashes
        ret_toxic = np.random.normal(0.005, 0.02, T)
        ret_toxic[::8] = -0.12  # frequent 12% crashes

        df = pd.DataFrame({"Safe": ret_safe, "Toxic": ret_toxic})
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.85)

        w = allocator.calculate_cvar_weights(
            returns_df=df,
            use_downside_semi_cov=True,
            semi_cov_weight=0.50,
        )

        assert w[0] > w[1], f"Asset Safe ({w[0]:.4f}) should have higher allocation than Toxic ({w[1]:.4f})"
        assert w[0] > 0.65, f"Asset Safe should receive predominant weight, got {w[0]:.4f}"

    def test_monotonicity_of_allocation_across_semi_cov_weight_sweep(self):
        """
        Monotonicity Test:
        Asset U (Upside): Low downside variance, high upside variance.
        Asset D (Downside): High downside variance, low upside variance.
        Sweep semi_cov_weight from 0.0 to 0.9 in steps of 0.1.
        The allocation w(U) should increase monotonically (or weakly monotonically)
        as semi_cov_weight increases, because downside semi-cov penalizes D much more heavily than U.
        """
        np.random.seed(106)
        T = 120
        # Asset U: gains up to +8%, drops capped at -1%
        ret_u = np.random.normal(0.002, 0.018, T)
        ret_u = np.where(ret_u < -0.01, -0.01, ret_u)
        ret_u[::6] += 0.05

        # Asset D: gains capped at +1%, drops down to -8%
        ret_d = np.random.normal(0.002, 0.018, T)
        ret_d = np.where(ret_d > 0.01, 0.01, ret_d)
        ret_d[::6] -= 0.05

        df = pd.DataFrame({"AssetU": ret_u, "AssetD": ret_d})
        cov_tot = df.cov().values

        allocator = UnifiedPortfolioAllocator(max_single_weight=0.90)

        weights_u = []
        sweep = [0.0, 0.10, 0.20, 0.35, 0.50, 0.65, 0.80, 0.90]
        for sc_w in sweep:
            w = allocator.calculate_cvar_weights(
                returns_df=df,
                cov_matrix=cov_tot,
                use_downside_semi_cov=True,
                semi_cov_weight=sc_w,
            )
            weights_u.append(w[0])

        # Verify general monotonic upward trend for Asset U weight
        for k in range(len(weights_u) - 1):
            assert weights_u[k + 1] >= weights_u[k] - 1e-4, (
                f"Monotonicity violation at step {k} ({sweep[k]} -> {sweep[k+1]}): "
                f"{weights_u[k]:.4f} -> {weights_u[k+1]:.4f}"
            )
        # Strong verification: final weight should be significantly higher than initial weight
        assert weights_u[-1] > weights_u[0] + 0.05, (
            f"Expected substantial increase in Asset U allocation: "
            f"initial={weights_u[0]:.4f}, final={weights_u[-1]:.4f}"
        )


# ==============================================================================
# 2. Dynamic Model Conviction Blending (F29) Stress Tests
# ==============================================================================

class TestDynamicModelConvictionBlendingStress:
    """Adversarial stress-testing of F29 Dynamic Model Conviction Blending."""

    @pytest.fixture
    def market_setup(self):
        np.random.seed(201)
        symbols = ["S1", "S2", "S3", "S4", "S5"]
        returns_df = pd.DataFrame(
            np.random.normal(0.001, 0.015, (80, 5)),
            columns=symbols
        )
        cov_matrix = returns_df.cov().values
        return symbols, returns_df, cov_matrix

    def test_extreme_alpha_dispersion_zero_dispersion(self, market_setup):
        """
        Zero Dispersion: all predicted returns are exactly identical (e.g. 0.02).
        std(mu) == 0.0.
        BL scaling term tanh((0.0 - 0.03)/0.02) must not break or trigger invalid BL scaling.
        Weights must sum to 1.0000 and remain non-negative.
        """
        symbols, returns_df, cov_matrix = market_setup
        allocator = UnifiedPortfolioAllocator()

        zero_disp_returns = np.full(len(symbols), 0.025)
        for regime in ["BULL_LOW_VOL", "SIDEWAYS_LOW_VOL", "CRISIS", "BEAR_HIGH_VOL"]:
            w = allocator.optimize_multi_model_blend(
                predicted_returns=zero_disp_returns,
                returns_df=returns_df,
                cov_matrix=cov_matrix,
                symbols=symbols,
                regime=regime,
            )
            assert len(w) == len(symbols)
            assert np.all(np.isfinite(w))
            assert np.all(w >= -1e-5)
            assert np.isclose(np.sum(w), 1.0, atol=1e-3)

    def test_extreme_alpha_dispersion_massive_dispersion(self, market_setup):
        """
        Massive Dispersion: predicted returns ranging from -1500% to +1500% (raw or percentage).
        Dispersion std(mu) >> 10.0.
        tanh saturation term must smoothly bound BL scaling to 1.0 + 0.30 * 1.0 = 1.30.
        Must not produce overflow, NaN, or non-normalized weights.
        """
        symbols, returns_df, cov_matrix = market_setup
        allocator = UnifiedPortfolioAllocator()

        massive_disp_returns = np.array([-15.0, -5.0, 0.0, 5.0, 15.0])
        w = allocator.optimize_multi_model_blend(
            predicted_returns=massive_disp_returns,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            regime="BULL_LOW_VOL",
        )
        assert len(w) == len(symbols)
        assert np.all(np.isfinite(w))
        assert np.all(w >= -1e-5)
        assert np.isclose(np.sum(w), 1.0, atol=1e-3)
        # Highest alpha asset (S5) should have highest allocation
        assert w[4] > w[0]

    def test_extreme_regime_probabilities_pure_and_degenerate(self, market_setup):
        """
        Stress-test extreme regime dictionaries:
        - Pure Crisis: {"CRISIS": 1.0}
        - Pure Bull: {"BULL_LOW_VOL": 1.0}
        - Pure Sideways: {"SIDEWAYS_HIGH_VOL": 1.0}
        - Empty dict: {}
        - All-zero dict: {"BULL_LOW_VOL": 0.0, "CRISIS": 0.0}
        - Uniform dict: 6 regimes with 1/6 each
        In ALL cases:
        1. Model blend weights sum strictly to 1.0000.
        2. All model blend weights are non-negative (>= 0).
        3. Portfolio asset weights sum to 1.0000.
        """
        symbols, returns_df, cov_matrix = market_setup
        allocator = UnifiedPortfolioAllocator()
        preds = np.array([-0.03, -0.01, 0.01, 0.04, 0.08])

        regimes_to_test = [
            {"CRISIS": 1.0},
            {"BULL_LOW_VOL": 1.0},
            {"SIDEWAYS_HIGH_VOL": 1.0},
            {"BEAR_HIGH_VOL": 1.0},
            {},
            {"BULL_LOW_VOL": 0.0, "CRISIS": 0.0},
            {
                "BULL_LOW_VOL": 1/6, "BULL_HIGH_VOL": 1/6,
                "SIDEWAYS_LOW_VOL": 1/6, "SIDEWAYS_HIGH_VOL": 1/6,
                "BEAR_LOW_VOL": 1/6, "BEAR_HIGH_VOL": 1/6
            },
        ]

        for reg in regimes_to_test:
            # Check model blend config weights
            blend_cfg = allocator.compute_dynamic_regime_blend_weights(reg)
            tot_b = sum(blend_cfg.values())
            assert np.isclose(tot_b, 1.0, atol=1e-4), f"Model blend config sum is {tot_b} for {reg}"
            for m_name, m_w in blend_cfg.items():
                assert m_w >= -1e-6, f"Negative model weight for {m_name}: {m_w}"

            # Check full portfolio optimization
            w = allocator.optimize_multi_model_blend(
                predicted_returns=preds,
                returns_df=returns_df,
                cov_matrix=cov_matrix,
                symbols=symbols,
                regime=reg,
            )
            assert len(w) == len(symbols)
            assert np.all(np.isfinite(w)), f"Non-finite weights found for regime {reg}"
            assert np.all(w >= -1e-5), f"Negative asset weight found for regime {reg}: {w}"
            assert np.isclose(np.sum(w), 1.0, atol=1e-3), f"Asset weights sum to {np.sum(w)} for regime {reg}"


# ==============================================================================
# 3. Leland Dynamic No-Trade Buffers (F30) Stress Tests
# ==============================================================================

class TestMarketSpecificLelandBufferStress:
    """Adversarial stress-testing of F30 Leland Buffers: Korean vs US Assets."""

    def test_krx_vs_us_buffer_asymmetry_across_wide_volatility_spectrum(self):
        """
        Stress-test buffer band half-width Delta_i across extreme volatility spectrum:
        vol in [0.001, 0.005, 0.02, 0.05, 0.15, 0.40].
        At every volatility point, Korean asset buffer must be >= US asset buffer
        because Korean cost c_i >= 25 bps (STT) while US cost c_i <= 8 bps.
        """
        allocator = UnifiedPortfolioAllocator(leland_cost_bps=20.0, risk_aversion=1.0)
        symbols = ["005930.KS", "AAPL"]
        vols_spectrum = [0.001, 0.005, 0.02, 0.05, 0.15, 0.40]

        for vol in vols_spectrum:
            target_w = np.array([0.20, 0.20])
            vols = np.array([vol, vol])

            # Measure buffer width by testing smallest drift that triggers rebalancing
            # For a test drift eps:
            drifts = np.linspace(0.001, 0.05, 100)
            krx_rebalanced = None
            us_rebalanced = None

            for d in drifts:
                curr_w = target_w + d
                res = allocator.apply_leland_no_trade_buffers(
                    target_weights=target_w,
                    current_weights=curr_w,
                    volatilities=vols,
                    symbols=symbols,
                )
                if krx_rebalanced is None and res[0] < curr_w[0]:
                    krx_rebalanced = d
                if us_rebalanced is None and res[1] < curr_w[1]:
                    us_rebalanced = d

            # US must rebalance at a smaller or equal drift than Korean asset
            # because US buffer is narrower (or at minimum equal when hitting min clip 0.005)
            if krx_rebalanced is not None and us_rebalanced is not None:
                assert us_rebalanced <= krx_rebalanced + 1e-4, (
                    f"At vol={vol}, US rebalanced at drift {us_rebalanced:.4f} but KRX at {krx_rebalanced:.4f}. "
                    f"US buffer must be narrower or equal!"
                )

    def test_krx_vs_us_extreme_cost_settings(self):
        """
        Stress-test behavior when base leland_cost_bps is configured to extreme values:
        - leland_cost_bps = 0.5 bps: Korean cost floor of 25 bps must protect KRX, while US takes min(0.5, 8)=0.5 bps.
        - leland_cost_bps = 500 bps: Korean takes max(500, 25)=500 bps, US takes min(500, 8)=8 bps.
        """
        allocator_low = UnifiedPortfolioAllocator(leland_cost_bps=0.5)
        symbols = ["005930.KS", "AAPL"]
        target_w = np.array([0.15, 0.15])
        vols = np.array([0.02, 0.02])

        # Drift of 1.2%
        curr_w = np.array([0.15 + 0.012, 0.15 + 0.012])
        w_low = allocator_low.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=curr_w,
            volatilities=vols,
            symbols=symbols,
        )
        # Korean asset has c_i >= 25 bps -> buffer delta is ~2.5% -> holds (w_low[0] == 0.162)
        assert np.isclose(w_low[0], curr_w[0], atol=1e-4), "Korean asset should hold even when leland_cost_bps=0.5"
        # US asset has c_i = 0.5 bps -> buffer delta is clipped at 0.5% -> breaches and rebalances
        assert w_low[1] < curr_w[1], "US asset should rebalance when cost is 0.5 bps"

        # Extreme high cost (500 bps)
        allocator_high = UnifiedPortfolioAllocator(leland_cost_bps=500.0)
        w_high = allocator_high.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=curr_w,
            volatilities=vols,
            symbols=symbols,
        )
        # Both should hold or US buffer capped at 8 bps
        assert np.isclose(w_high[0], curr_w[0], atol=1e-4)

    def test_boundary_rebalancing_property(self):
        """
        Verifies boundary rebalancing:
        When current weight breaches upper buffer band (target + delta),
        the new weight is set to the boundary (target + delta), NOT the target weight.
        This minimizes unnecessary trading volume and market impact.
        """
        allocator = UnifiedPortfolioAllocator(rebalance_mode="boundary")
        target_w = np.array([0.10])
        # Current weight has massive drift to 0.18
        curr_w = np.array([0.18])
        vols = np.array([0.02])

        res = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=curr_w,
            volatilities=vols,
        )
        # In boundary mode, res[0] must be strictly greater than target_w[0] (0.10)
        # and strictly less than curr_w[0] (0.18)
        assert target_w[0] < res[0] < curr_w[0], (
            f"Boundary rebalancing should position at upper band: {target_w[0]} < {res[0]} < {curr_w[0]}"
        )

    def test_bypass_buffer_for_new_entry_and_liquidation(self):
        """
        Verifies critical bypass rules:
        - curr_w <= 1e-4: Brand new position entry must NOT be blocked by no-trade buffer.
        - target_w <= 1e-4: Full liquidation exit must NOT be blocked by no-trade buffer.
        """
        allocator = UnifiedPortfolioAllocator()
        target_w = np.array([0.10, 0.00])
        curr_w = np.array([0.00, 0.10])
        vols = np.array([0.02, 0.02])

        res = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=curr_w,
            volatilities=vols,
        )

        assert np.isclose(res[0], 0.10, atol=1e-4), "New entry was incorrectly dampened by buffer"
        assert np.isclose(res[1], 0.00, atol=1e-4), "Full liquidation was incorrectly dampened by buffer"

    def test_custom_asset_cost_bps_variations(self):
        """Tests custom asset_cost_bps handling: array, single scalar, mismatched length."""
        allocator = UnifiedPortfolioAllocator()
        target_w = np.array([0.10, 0.10, 0.10])
        curr_w = np.array([0.12, 0.12, 0.12])
        vols = np.array([0.02, 0.02, 0.02])

        # 1. Single scalar array [50.0]
        res_single = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=curr_w,
            volatilities=vols,
            asset_cost_bps=[50.0],
        )
        assert len(res_single) == 3

        # 2. Mismatched length [10.0, 20.0] -> should fallback gracefully to default leland_cost_bps
        res_mismatch = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=curr_w,
            volatilities=vols,
            asset_cost_bps=[10.0, 20.0],
        )
        assert len(res_mismatch) == 3
        assert np.all(np.isfinite(res_mismatch))
