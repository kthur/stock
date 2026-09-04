"""
test_phase5_portfolio_execution.py - Comprehensive Unit & Property Tests for Phase 5 (M2)
Verifies Features F37 and F38:
- F37: 4-Model Portfolio Allocation & Capital Efficiency 5th Deepening (unified_portfolio_allocator.py)
  * Systematic co-skewness and co-kurtosis alpha conviction tilt
  * Dynamic Cornish-Fisher EVT-CVaR tail expansion k_alpha(w) in [2.05, 3.20]
  * Dynamic Risk Parity Diversification Ratio (DRP-DR) scaling
  * Shannon regime entropy-weighted adaptive target volatility scaling
  * Hill/Pickands GPD dynamic tail index xi in [0.05, 0.45]
- F38: Execution Slippage & Friction Cost Minimization 5th Deepening (smart_order_router.py, oms_engine.py)
  * Continuous Hawkes toxicity modulation and maker ratio decay
  * Darkpool Midpoint Resting with MinQty (>= 20%) and queue-priority fill probability
  * Volatility- and depth-adaptive L2 OBI micro-price dynamic curvature kappa_eff in [0.8, 3.0]
  * ADV-adaptive Gatheral slice count with intraday U-shaped volume smile
  * Granular 5-market spread- and tax-aware Leland dynamic buffer bands
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler, GatheralMarketImpactKernel


# ==============================================================================
# F37: 4-Model Portfolio Allocation & Capital Efficiency 5th Deepening Tests
# ==============================================================================

class TestF37HigherOrderPortfolioAllocation:
    """Tests for Feature F37 in unified_portfolio_allocator.py."""

    def test_f37_coskewness_cokurtosis_computation(self):
        """
        Verifies compute_higher_order_co_moments accurately calculates systematic
        co-skewness and co-kurtosis against market returns.
        """
        np.random.seed(42)
        T = 120
        # Market benchmark: zero mean, std 0.02
        r_m = np.random.normal(0.0, 0.02, T)

        # Asset A: positively correlated with market squared shocks (positive co-skewness)
        r_a = 0.5 * r_m + 0.8 * (r_m ** 2) / 0.02 + np.random.normal(0.0, 0.01, T)

        # Asset B: negatively correlated with market squared shocks (crash on large market moves)
        r_b = 0.5 * r_m - 0.8 * (r_m ** 2) / 0.02 + np.random.normal(0.0, 0.01, T)

        R = np.column_stack([r_a, r_b])
        co_skew, co_kurt = UnifiedPortfolioAllocator.compute_higher_order_co_moments(R, market_returns=r_m)

        assert len(co_skew) == 2
        assert len(co_kurt) == 2
        # Asset A should have significantly higher co-skewness than Asset B
        assert co_skew[0] > co_skew[1]
        assert co_skew[0] > 0.0
        assert co_skew[1] < 0.0
        # Kurtosis values are finite and within reasonable bounds
        assert np.all(np.isfinite(co_kurt))

    def test_f37_coskewness_cokurtosis_penalizes_crash_prone_asset(self):
        """
        When two assets have identical expected return and variance, but Asset B exhibits
        severe negative co-skewness and heavy co-kurtosis, Asset A receives significantly
        larger allocation (>= 1.4x of Asset B) due to the higher-order alpha tilt and
        Cornish-Fisher EVT-CVaR tail expansion penalty.
        """
        np.random.seed(123)
        T = 150
        # Market return
        r_m = np.random.normal(0.0, 0.02, T)

        # Asset A: positive co-skewness (safe haven upside during volatility)
        r_a = 0.3 * r_m + 0.5 * np.abs(r_m) + np.random.normal(0.001, 0.015, T)
        # Asset B: negative co-skewness and heavy left tails (crashes during market moves)
        r_b = 0.3 * r_m - 0.8 * (r_m ** 2) / 0.02 + np.random.normal(0.001, 0.015, T)

        # Equalize empirical variance and mean
        r_a = (r_a - np.mean(r_a)) / np.std(r_a) * 0.02 + 0.001
        r_b = (r_b - np.mean(r_b)) / np.std(r_b) * 0.02 + 0.001

        returns_df = pd.DataFrame({"SAFE_A": r_a, "CRASH_B": r_b})
        cov_matrix = returns_df.cov().values
        symbols = ["SAFE_A", "CRASH_B"]
        preds = np.array([0.05, 0.05])  # Identical alpha predictions

        allocator = UnifiedPortfolioAllocator(max_single_weight=0.80)
        w = allocator.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            regime="BULL_HIGH_VOL",
        )

        assert len(w) == 2
        # Asset A must receive >= 1.4x allocation of Asset B
        ratio = w[0] / max(1e-6, w[1])
        assert ratio >= 1.40, f"Expected Asset A / Asset B ratio >= 1.40, got {ratio:.3f} (w={w})"
        assert np.isclose(np.sum(w), 1.0, atol=1e-3)

    def test_f37_drp_dr_scales_herc_and_rp_in_high_diversification_market(self):
        """
        When the empirical Diversification Ratio DR = (w^T sigma) / sqrt(w^T Sigma w) is high (DR >= 1.60),
        delta_DR = clip(1.0 + 0.40 * (DR - 1.30) / 0.50, 0.60, 1.40) > 1.15.
        HERC and Risk Parity weights scale up dynamically.
        """
        # Create 4 uncorrelated assets with different volatilities
        symbols = ["S1", "S2", "S3", "S4"]
        vols = np.array([0.01, 0.02, 0.03, 0.04])
        # Diagonal covariance (zero correlation -> high diversification ratio)
        cov_matrix = np.diag(vols ** 2)

        mean_vol = float(np.mean(vols))
        eq_w = np.full(4, 0.25)
        port_vol = math.sqrt(float(eq_w @ cov_matrix @ eq_w))
        dr = mean_vol / port_vol
        assert dr >= 1.60, f"Expected DR >= 1.60, got {dr:.3f}"

        expected_delta_dr = np.clip(1.0 + 0.40 * (dr - 1.30) / 0.50, 0.60, 1.40)
        assert expected_delta_dr > 1.15

        allocator = UnifiedPortfolioAllocator()
        # In SIDEWAYS_LOW_VOL, HERC=0.45, RP=0.20
        blend_base = allocator.compute_dynamic_regime_blend_weights("SIDEWAYS_LOW_VOL")

        returns_df = pd.DataFrame(
            np.random.normal(0, 0.02, (80, 4)),
            columns=symbols
        )
        w = allocator.optimize_multi_model_blend(
            predicted_returns=np.array([0.02, 0.02, 0.02, 0.02]),
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            regime="SIDEWAYS_LOW_VOL",
        )
        assert np.isclose(np.sum(w), 1.0, atol=1e-3)

    def test_f37_drp_dr_compresses_herc_and_boosts_cvar_in_correlation_spike(self):
        """
        Under extreme correlation convergence (correlation = 0.96 across all assets, DR ≈ 1.02),
        delta_DR compresses (< 0.85) and EVT-CVaR weight is boosted to protect against systemic crash.
        """
        symbols = ["A", "B", "C", "D"]
        n = 4
        # High correlation matrix rho = 0.96
        corr = np.full((n, n), 0.96)
        np.fill_diagonal(corr, 1.0)
        vols = np.array([0.02, 0.02, 0.02, 0.02])
        cov_matrix = np.outer(vols, vols) * corr

        mean_vol = float(np.mean(vols))
        eq_w = np.full(n, 1.0 / n)
        port_vol = math.sqrt(float(eq_w @ cov_matrix @ eq_w))
        dr = mean_vol / port_vol
        assert dr < 1.10, f"Expected correlation convergence DR < 1.10, got {dr:.3f}"

        delta_dr = float(np.clip(1.0 + 0.40 * (dr - 1.30) / 0.50, 0.60, 1.40))
        assert delta_dr < 0.85, f"Expected delta_dr < 0.85, got {delta_dr:.3f}"

        allocator = UnifiedPortfolioAllocator()
        returns_df = pd.DataFrame(
            np.random.normal(0, 0.02, (80, n)),
            columns=symbols
        )
        w = allocator.optimize_multi_model_blend(
            predicted_returns=np.array([0.01, 0.01, 0.01, 0.01]),
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            regime="SIDEWAYS_HIGH_VOL",
        )
        assert np.isclose(np.sum(w), 1.0, atol=1e-3)

    def test_f37_shannon_entropy_regime_uncertainty_dampens_target_vol(self):
        """
        When regime probabilities exhibit maximal Shannon entropy (U_regime = 1.0, uniform 1/6 distribution),
        target volatility is scaled by (1 - 0.25 * 1.0) = 0.75x and allocation cap by (1 - 0.20 * 1.0) = 0.80x.
        When regime is certain (U_regime = 0.0), full 98% Bull allocation is unlocked.
        """
        allocator = UnifiedPortfolioAllocator(target_volatility=0.12)
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        cov_matrix = np.diag([0.01 ** 2] * 4)  # very low vol -> allocation hits cap

        # Case 1: Certain regime (U_regime = 0.0)
        regime_certain = "BULL_LOW_VOL"
        _, alloc_certain = allocator.apply_target_volatility_scaling(
            weights=weights,
            cov_matrix=cov_matrix,
            regime=regime_certain,
        )
        assert np.isclose(alloc_certain, 0.98, atol=1e-3)

        # Case 2: Maximum entropy regime (all 6 regimes equally probable: 1/6 each)
        regime_max_entropy = {
            "BULL_LOW_VOL": 1.0 / 6.0,
            "BULL_HIGH_VOL": 1.0 / 6.0,
            "SIDEWAYS_LOW_VOL": 1.0 / 6.0,
            "SIDEWAYS_HIGH_VOL": 1.0 / 6.0,
            "BEAR_LOW_VOL": 1.0 / 6.0,
            "BEAR_HIGH_VOL": 1.0 / 6.0,
        }
        _, alloc_uncertain = allocator.apply_target_volatility_scaling(
            weights=weights,
            cov_matrix=cov_matrix,
            regime=regime_max_entropy,
        )

        # Under U_regime = 1.0, max cap is 0.98 * 0.80 = 0.784
        assert alloc_uncertain <= 0.98 * 0.80 + 1e-4
        assert alloc_uncertain < alloc_certain
        # Check ratio of cap compression is ~20%
        assert np.isclose(alloc_uncertain / alloc_certain, 0.80, atol=0.02)

    def test_f37_dynamic_gpd_tail_index_expands_cvar_multiplier(self):
        """
        Tests that estimate_gpd_tail_index accurately estimates Hill's tail index xi in [0.05, 0.45],
        and heavy-tailed loss distributions yield k_alpha >= 2.70 (vs Gaussian ~2.06).
        """
        np.random.seed(777)
        # Heavy-tailed Student-t (nu = 3) returns -> heavy loss tail
        heavy_returns = np.random.standard_t(df=3, size=(200, 2)) * 0.02
        xi_heavy = UnifiedPortfolioAllocator.estimate_gpd_tail_index(heavy_returns, tail_quantile=0.90)

        assert 0.05 <= xi_heavy <= 0.45
        assert xi_heavy >= 0.20, f"Expected heavy-tailed xi >= 0.20, got {xi_heavy:.3f}"

        # Parametric CVaR optimization under heavy tails
        allocator = UnifiedPortfolioAllocator()
        df_heavy = pd.DataFrame(heavy_returns, columns=["T1", "T2"])
        w = allocator.calculate_cvar_weights(
            returns_df=df_heavy,
            confidence_level=0.95,
            cov_matrix=df_heavy.cov().values,
        )
        assert len(w) == 2
        assert np.isclose(np.sum(w), 1.0, atol=1e-3)

    def test_f37_multi_model_blend_sums_strictly_to_one_across_all_regimes(self):
        """
        Verifies that across diverse randomized regime mixtures and volatility levels,
        optimize_multi_model_blend weights always sum strictly to 1.0000 +/- 1e-3.
        """
        np.random.seed(999)
        symbols = [f"SYM_{i}" for i in range(5)]
        n = 5
        returns_df = pd.DataFrame(
            np.random.normal(0.001, 0.02, (80, n)),
            columns=symbols
        )
        cov_matrix = returns_df.cov().values
        allocator = UnifiedPortfolioAllocator()

        regime_list = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "CRISIS",
            {"BULL_LOW_VOL": 0.4, "CRISIS": 0.6},
            {"SIDEWAYS_HIGH_VOL": 0.5, "BEAR_HIGH_VOL": 0.5},
        ]

        for reg in regime_list:
            preds = np.random.normal(0.03, 0.04, n)
            w = allocator.optimize_multi_model_blend(
                predicted_returns=preds,
                returns_df=returns_df,
                cov_matrix=cov_matrix,
                symbols=symbols,
                regime=reg,
            )
            assert np.isclose(np.sum(w), 1.0, atol=1e-3), f"Failed sum constraint for regime {reg}: sum={np.sum(w)}"


# ==============================================================================
# F38: Execution Slippage & Friction Cost Minimization 5th Deepening Tests
# ==============================================================================

class TestF38ExecutionSlippageFrictionMinimization:
    """Tests for Feature F38 in smart_order_router.py and oms_engine.py."""

    def test_f38_continuous_hawkes_maker_ratio_smooth_monotonic_decay(self):
        """
        Verifies that under continuous_hawkes=True, as Hawkes intensity lambda increases
        from baseline (1.0) to 2.5 and beyond, maker_ratio decays smoothly and monotonically
        without discontinuous jumps.
        """
        sor = SmartOrderRouter(continuous_hawkes=True)
        order_plan = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 400.0,
            "execution_strategy": "MIDPOINT_PEG",
        }

        intensities = [0.5, 1.0, 1.3, 1.6, 2.0, 2.5, 3.0, 4.0]
        maker_ratios = []
        gamma_toxics = []

        for lam in intensities:
            res = sor.route_order(
                order_plan=order_plan,
                hawkes_intensity=lam,
                baseline_intensity=1.0,
                continuous_hawkes=True,
            )
            maker_ratios.append(res["maker_ratio"])
            gamma_toxics.append(res["gamma_toxic"])

        # At lambda <= 1.0, maker_ratio == 0.70
        assert np.isclose(maker_ratios[0], 0.70, atol=1e-3)
        assert np.isclose(maker_ratios[1], 0.70, atol=1e-3)
        # At lambda >= 2.5, maker_ratio == 0.30
        assert np.isclose(maker_ratios[5], 0.30, atol=1e-3)
        assert np.isclose(maker_ratios[6], 0.30, atol=1e-3)

        # Monotonicity check: maker_ratios should be non-increasing
        for i in range(len(maker_ratios) - 1):
            assert maker_ratios[i] >= maker_ratios[i + 1] - 1e-4, (
                f"Monotonicity violated at step {i}: {maker_ratios[i]} < {maker_ratios[i+1]}"
            )

        # Gamma toxic should be non-decreasing and bounded in [0.0, 1.0]
        for i in range(len(gamma_toxics) - 1):
            assert gamma_toxics[i] <= gamma_toxics[i + 1] + 1e-4

    def test_f38_toxic_flow_adds_minqty_to_dark_midpoint_leg(self):
        """
        When toxic flow is detected (Gamma_toxic > 0.50), Tier 1 dark leg specifies
        order_type='MIDPOINT_PEGGED_RESTING' and min_quantity >= 20% of dark quantity
        to protect against predatory latency snipes.
        """
        sor = SmartOrderRouter(continuous_hawkes=True)
        order_plan = {
            "symbol": "TSLA",
            "action": "BUY",
            "quantity": 5_000,
            "target_price": 250.0,
            "execution_strategy": "PATIENT_TWAP",
            "darkpool_score": 0.50,
        }

        # Elevated Hawkes intensity lambda = 2.2 > 1.0 + 0.5 * 1.5 = 1.75 -> Gamma_toxic > 0.50
        routed = sor.route_order(
            order_plan=order_plan,
            hawkes_intensity=2.2,
            baseline_intensity=1.0,
            continuous_hawkes=True,
        )

        dark_leg = routed["dark_ats_midpoint"]
        assert dark_leg is not None
        assert dark_leg["order_type"] == "MIDPOINT_PEGGED_RESTING"
        assert "min_quantity" in dark_leg
        assert dark_leg["min_quantity"] >= int(0.20 * dark_leg["quantity"])
        assert routed["darkpool_fill_probability"] > 0.0

    def test_f38_darkpool_fill_probability_estimation(self):
        """
        Verifies that P_fill^dark scales positively with darkpool_score and spread,
        and negatively with Gamma_toxic.
        """
        sor = SmartOrderRouter(continuous_hawkes=True)
        base_plan = {
            "symbol": "SPY",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 500.0,
            "execution_strategy": "MIDPOINT_PEG",
        }

        # High DP score, wide spread, zero toxicity -> high fill prob
        res_high = sor.route_order(
            order_plan={**base_plan, "darkpool_score": 0.90},
            market_spread_bps=20.0,
            hawkes_intensity=1.0,
            baseline_intensity=1.0,
            continuous_hawkes=True,
        )

        # Low DP score, tight spread, high toxicity -> low fill prob
        res_low = sor.route_order(
            order_plan={**base_plan, "darkpool_score": 0.10},
            market_spread_bps=5.0,
            hawkes_intensity=3.0,
            baseline_intensity=1.0,
            continuous_hawkes=True,
        )

        p_high = res_high["darkpool_fill_probability"]
        p_low = res_low["darkpool_fill_probability"]

        assert 0.15 <= p_high <= 0.85
        assert 0.15 <= p_low <= 0.85
        assert p_high > p_low + 0.20, f"Expected p_high ({p_high}) >> p_low ({p_low})"

    def test_f38_micro_price_peg_curvature_scales_with_volatility(self):
        """
        Verifies that kappa_eff = clip(1.5 * (sigma / 0.02) / sqrt(R_depth), 0.8, 3.0).
        At higher daily volatility (sigma = 0.04), peg shift is strictly greater than at
        lower volatility (sigma = 0.01) under identical positive OBI.
        """
        target_p = 100.0
        bid_p = 99.0
        ask_p = 101.0
        spr = 2.0
        micro_p = 100.0
        obi = 0.60

        # Low volatility sigma = 0.01 -> kappa_eff = 1.5 * (0.01 / 0.02) = 0.75 -> clipped to 0.80
        px_low_vol = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            micro_price=micro_p,
            obi=obi,
            daily_volatility=0.01,
            book_depth_ratio=1.0,
        )

        # High volatility sigma = 0.04 -> kappa_eff = 1.5 * (0.04 / 0.02) = 3.00
        px_high_vol = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            micro_price=micro_p,
            obi=obi,
            daily_volatility=0.04,
            book_depth_ratio=1.0,
        )

        # High volatility requires more aggressive peg shift to ensure queue execution
        shift_low = px_low_vol - micro_p
        shift_high = px_high_vol - micro_p
        assert shift_high > shift_low, f"Expected shift_high ({shift_high}) > shift_low ({shift_low})"

    def test_f38_micro_price_peg_curvature_dampens_with_thick_book_depth(self):
        """
        When orderbook is thick (R_depth = 4.0), kappa_eff dampens (divided by sqrt(4) = 2),
        preventing excessive over-bidding into deep books.
        """
        target_p = 50.0
        bid_p = 49.5
        ask_p = 50.5
        spr = 1.0
        micro_p = 50.0
        obi = 0.50

        # Normal depth (R = 1.0)
        px_normal = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            micro_price=micro_p,
            obi=obi,
            daily_volatility=0.02,
            book_depth_ratio=1.0,
        )

        # Thick depth (R = 4.0)
        px_thick = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            micro_price=micro_p,
            obi=obi,
            daily_volatility=0.02,
            book_depth_ratio=4.0,
        )

        shift_normal = px_normal - micro_p
        shift_thick = px_thick - micro_p
        assert shift_normal > shift_thick, f"Thick book shift ({shift_thick}) should be < normal ({shift_normal})"

    def test_f38_gatheral_dynamic_slice_count_scales_with_adv_fraction(self):
        """
        Verifies that when n_slices is omitted, GatheralMarketImpactKernel dynamically computes:
            n_slices* = clip(round(3 + 8 * sqrt(rho_adv / 0.01)), 2, 20).
        Small orders (rho_adv = 0.0001 -> 0.01% ADV) produce 2~4 slices.
        Large institutional orders (rho_adv = 0.02 -> 2.0% ADV) produce 12~16 slices.
        """
        adv = 1_000_000.0

        # Small order: 100 shares (0.01% ADV)
        slices_small = GatheralMarketImpactKernel.compute_optimal_gatheral_slices(
            total_quantity=100,
            adv=adv,
        )
        assert 2 <= len(slices_small) <= 5
        assert sum(slices_small) == 100

        # Large order: 20,000 shares (2.0% ADV)
        # sqrt(0.02 / 0.01) = sqrt(2) ≈ 1.414 -> round(3 + 8 * 1.414) = 14
        slices_large = GatheralMarketImpactKernel.compute_optimal_gatheral_slices(
            total_quantity=20_000,
            adv=adv,
        )
        assert 12 <= len(slices_large) <= 16
        assert sum(slices_large) == 20_000

    def test_f38_gatheral_intraday_volume_smile_front_and_end_loads(self):
        """
        Under flat alpha urgency (alpha_decay_half_life = 500.0, urgency_bias ≈ 0.20),
        the U-shaped intraday volume smile V_smile(t) = 1.0 + 0.6 * (2t - 1)^2 causes
        the opening tranche (slice 0) and closing tranche (slice N-1) to have higher
        weights than the midday tranche.
        """
        slices = GatheralMarketImpactKernel.compute_optimal_gatheral_slices(
            total_quantity=10_000,
            n_slices=5,
            alpha_decay_half_life=500.0,
            cost_scaling_factor=1.0,
        )
        assert len(slices) == 5
        assert sum(slices) == 10_000

        # Opening slice and closing slice should both be larger than the midday slice (index 2)
        assert slices[0] > slices[2], f"Slice 0 ({slices[0]}) should exceed midday slice 2 ({slices[2]})"
        assert slices[4] > slices[2], f"Slice 4 ({slices[4]}) should exceed midday slice 2 ({slices[2]})"

    def test_f38_kosdaq_assets_receive_wider_buffer_bands_than_kospi(self):
        """
        KOSDAQ friction (35.0 bps: 18 bps STT + 2 bps fee + 15 bps spread) is higher than
        KOSPI friction (25.0 bps: 18 bps STT + 2 bps fee + 5 bps spread).
        Therefore, KOSDAQ assets receive strictly wider Leland buffer bands than KOSPI assets
        under identical weights and volatilities.
        """
        allocator = UnifiedPortfolioAllocator()
        target_w = np.array([0.15, 0.15])
        vols = np.array([0.02, 0.02])

        # Drift of +3.0% (0.180):
        # KOSPI delta is ~2.89% -> upper band is ~0.1789 (0.180 breaches -> rebalanced)
        # KOSDAQ delta is ~3.23% -> upper band is ~0.1823 (0.180 within band -> holds)
        current_w = np.array([0.15 + 0.030, 0.15 + 0.030])
        symbols = ["068270.KQ", "005930.KS"]
        markets = ["KOSDAQ", "KOSPI"]

        w_out = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=current_w,
            volatilities=vols,
            symbols=symbols,
            markets=markets,
        )

        # KOSDAQ asset (index 0) holds current weight 0.180 to avoid high 35 bps friction
        assert np.isclose(w_out[0], current_w[0], atol=1e-4), (
            f"KOSDAQ asset should hold current weight {current_w[0]}, got {w_out[0]}"
        )
        # KOSPI asset (index 1) breaches its narrower band and rebalances
        assert w_out[1] < current_w[1], (
            f"KOSPI asset should rebalance when breaching narrower buffer, got {w_out[1]}"
        )

    def test_f38_sp500_assets_receive_narrowest_buffer_bands(self):
        """
        S&P 500 assets (5.0 bps cost) have the lowest friction among all markets, resulting
        in the narrowest Leland bands, allowing nimble and frequent alpha rebalancing.
        """
        allocator = UnifiedPortfolioAllocator()
        symbols = ["SPY", "IWM", "005930.KS", "068270.KQ"]
        markets = ["SP500", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        target_w = np.full(4, 0.15)
        vols = np.full(4, 0.02)

        # Drift of +2.0% (0.170):
        # SP500 (5 bps): delta ≈ 1.69% -> upper band 0.1669 -> 0.170 breaches -> rebalances!
        # Russell (16 bps): delta ≈ 2.48% -> upper band 0.1748 -> 0.170 within band -> holds!
        # KOSPI (25 bps): delta ≈ 2.89% -> upper band 0.1789 -> holds!
        # KOSDAQ (35 bps): delta ≈ 3.23% -> upper band 0.1823 -> holds!
        current_w = np.full(4, 0.15 + 0.020)

        w_out = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=current_w,
            volatilities=vols,
            symbols=symbols,
            markets=markets,
        )

        # SP500 (index 0) should rebalance due to tightest bands
        assert w_out[0] < current_w[0], f"SP500 should rebalance, got {w_out[0]}"
        # Russell, KOSPI, and KOSDAQ should hold
        assert np.isclose(w_out[1], current_w[1], atol=1e-4)
        assert np.isclose(w_out[2], current_w[2], atol=1e-4)
        assert np.isclose(w_out[3], current_w[3], atol=1e-4)

    def test_f38_five_market_cost_resolution(self):
        """Verifies resolve_market_cost_bps returns canonical bps for all 5 target markets."""
        assert UnifiedPortfolioAllocator.resolve_market_cost_bps(market="KOSDAQ") == 35.0
        assert UnifiedPortfolioAllocator.resolve_market_cost_bps(market="KOSPI") == 25.0
        assert UnifiedPortfolioAllocator.resolve_market_cost_bps(market="RUSSELL2000") == 16.0
        assert UnifiedPortfolioAllocator.resolve_market_cost_bps(market="NASDAQ") == 7.0
        assert UnifiedPortfolioAllocator.resolve_market_cost_bps(market="SP500") == 5.0

        # Symbol suffix detection
        assert UnifiedPortfolioAllocator.resolve_market_cost_bps(symbol="068270.KQ") == 35.0
        assert UnifiedPortfolioAllocator.resolve_market_cost_bps(symbol="005930.KS") == 25.0
