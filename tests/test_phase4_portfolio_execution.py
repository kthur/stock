"""
test_phase4_portfolio_execution.py - Comprehensive Unit & Property Tests for Phase 4 (M2)
Verifies Features F28 to F33:
- F28: Downside Semi-Covariance (Sortino) EVT-CVaR Optimization (unified_portfolio_allocator.py)
- F29: Dynamic Model Conviction & Return-Dispersion Blending (unified_portfolio_allocator.py)
- F30: Market-Specific STT & Fee-Aware Leland Dynamic Buffer Bands (unified_portfolio_allocator.py)
- F31: Multi-Tier L2 OBI & Volume-Weighted Micro-Price Pegging (oms_engine.py)
- F32: Hawkes Arrival Intensity Adverse Selection Gating (smart_order_router.py)
- F33: Closed-Loop Empirical Slippage Feedback Scaling (unified_portfolio_allocator.py, oms_engine.py)
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler, GatheralMarketImpactKernel


# ==============================================================================
# F28: Downside Semi-Covariance (Sortino) EVT-CVaR Optimization Tests
# ==============================================================================

class TestF28DownsideSemiCovarianceCVaR:
    """Tests for F28: Downside Semi-Covariance EVT-CVaR Optimization."""

    @pytest.fixture
    def asymmetric_returns(self):
        """
        Creates returns where:
        - Asset A has positive skew (large upside gains, small downside losses).
        - Asset B has negative skew (small upside gains, large downside drops).
        Both have roughly similar total variance, but Asset A has much lower downside semi-variance.
        """
        np.random.seed(42)
        T = 80
        # Asset A: positive skew
        ret_a = np.random.normal(0.003, 0.02, T)
        ret_a[ret_a < -0.015] = -0.010  # truncate downside drops
        ret_a[::10] += 0.06  # add upside spikes

        # Asset B: negative skew
        ret_b = np.random.normal(0.003, 0.02, T)
        ret_b[ret_b > 0.015] = 0.010  # truncate upside gains
        ret_b[::10] -= 0.06  # add downside spikes

        df = pd.DataFrame({"AssetA": ret_a, "AssetB": ret_b})
        return df

    def test_f28_semi_cov_boosts_upside_momentum_asset(self, asymmetric_returns):
        """
        Verifies that when downside semi-cov is active (use_downside_semi_cov=True),
        Asset A (low downside risk, high upside momentum) receives a higher allocation
        than when optimizing purely on total covariance.
        """
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.80)
        cov_total = asymmetric_returns.cov().values

        # Weights with standard total covariance (use_downside_semi_cov=False)
        w_total = allocator.calculate_cvar_weights(
            returns_df=asymmetric_returns,
            cov_matrix=cov_total,
            use_downside_semi_cov=False,
            confidence_level=0.95,
        )

        # Weights with downside semi-covariance enabled (use_downside_semi_cov=True, semi_cov_weight=0.50)
        w_semi = allocator.calculate_cvar_weights(
            returns_df=asymmetric_returns,
            cov_matrix=cov_total,
            use_downside_semi_cov=True,
            semi_cov_weight=0.50,
            confidence_level=0.95,
        )

        assert len(w_semi) == 2
        assert np.isclose(np.sum(w_semi), 1.0, atol=1e-4)
        # Asset A should have higher weight under downside semi-cov because its downside risk is lower
        assert w_semi[0] > w_total[0], (
            f"Expected Asset A weight with downside semi-cov ({w_semi[0]:.4f}) "
            f"to exceed total cov weight ({w_total[0]:.4f})"
        )

    def test_f28_semi_cov_weight_interpolation_property(self, asymmetric_returns):
        """Verifies monotonic shift as semi_cov_weight increases from 0.0 to 0.8."""
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.85)
        cov_total = asymmetric_returns.cov().values

        w_0 = allocator.calculate_cvar_weights(
            returns_df=asymmetric_returns,
            cov_matrix=cov_total,
            use_downside_semi_cov=True,
            semi_cov_weight=0.0,
        )
        w_35 = allocator.calculate_cvar_weights(
            returns_df=asymmetric_returns,
            cov_matrix=cov_total,
            use_downside_semi_cov=True,
            semi_cov_weight=0.35,
        )
        w_70 = allocator.calculate_cvar_weights(
            returns_df=asymmetric_returns,
            cov_matrix=cov_total,
            use_downside_semi_cov=True,
            semi_cov_weight=0.70,
        )

        # Weight of low-downside Asset A should increase monotonically with semi_cov_weight
        assert w_70[0] >= w_35[0] >= w_0[0] - 1e-4

    def test_f28_fallback_when_cov_matrix_is_none(self, asymmetric_returns):
        """Verifies that calculate_cvar_weights handles cov_matrix=None by computing sample & semi cov."""
        allocator = UnifiedPortfolioAllocator()
        w = allocator.calculate_cvar_weights(
            returns_df=asymmetric_returns,
            cov_matrix=None,
            use_downside_semi_cov=True,
        )
        assert len(w) == 2
        assert np.all(np.isfinite(w))
        assert np.isclose(np.sum(w), 1.0, atol=1e-4)

    def test_f28_edge_cases(self):
        """Tests edge cases: single asset, empty dataframe, very few observations."""
        allocator = UnifiedPortfolioAllocator()
        # Single asset
        df_single = pd.DataFrame({"AAPL": np.random.normal(0.001, 0.02, 50)})
        w_single = allocator.calculate_cvar_weights(df_single, use_downside_semi_cov=True)
        assert np.array_equal(w_single, np.array([1.0]))

        # Short T < 5
        df_short = pd.DataFrame({"A": [0.01, -0.01], "B": [-0.02, 0.02]})
        w_short = allocator.calculate_cvar_weights(df_short, use_downside_semi_cov=True)
        assert len(w_short) == 2
        assert np.isclose(np.sum(w_short), 1.0, atol=1e-4)


# ==============================================================================
# F29: Dynamic Model Conviction & Return-Dispersion Blending Tests
# ==============================================================================

class TestF29DynamicModelConvictionBlending:
    """Tests for F29: Dynamic Model Conviction & Return-Dispersion Blending."""

    @pytest.fixture
    def sample_data(self):
        np.random.seed(42)
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        returns_df = pd.DataFrame(
            np.random.normal(0.001, 0.02, (60, 4)),
            columns=symbols
        )
        cov_matrix = returns_df.cov().values
        return symbols, returns_df, cov_matrix

    def test_f29_high_dispersion_scales_black_litterman_in_bull(self, sample_data):
        """
        When cross-sectional alpha dispersion is high (std(mu) > 0.03) in Bull Low Vol regime,
        the Black-Litterman model weight scales up and top alpha receives larger weight.
        """
        symbols, returns_df, cov_matrix = sample_data
        allocator = UnifiedPortfolioAllocator()

        # High dispersion predicted returns: [ -8%, -2%, +4%, +10% ] -> std ≈ 0.066 > 0.03
        high_disp_returns = np.array([-0.08, -0.02, 0.04, 0.10])

        w_high = allocator.optimize_multi_model_blend(
            predicted_returns=high_disp_returns,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            regime="BULL_LOW_VOL",
        )

        # High dispersion should allocate strongly to top alpha asset (AMZN)
        assert w_high[3] > w_high[0]
        assert np.isclose(np.sum(w_high), 1.0, atol=1e-3)

    def test_f29_crisis_regime_boosts_cvar_and_herc(self, sample_data):
        """In crisis regime, EVT-CVaR and HERC are boosted to preserve capital."""
        symbols, returns_df, cov_matrix = sample_data
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.50)

        preds = np.array([0.01, 0.02, -0.01, 0.00])
        w_crisis = allocator.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            regime="CRISIS",
        )

        assert len(w_crisis) == 4
        assert np.isclose(np.sum(w_crisis), 1.0, atol=1e-3)
        assert np.max(w_crisis) <= allocator.max_single_weight + 1e-4

    def test_f29_blended_weights_strictly_sum_to_one(self, sample_data):
        """Verifies that sum of model weights strictly equals 1.0000 across regimes and dispersions."""
        symbols, returns_df, cov_matrix = sample_data
        allocator = UnifiedPortfolioAllocator()

        for regime in ["BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL", "BEAR_HIGH_VOL", "CRISIS"]:
            for disp in [0.01, 0.05, 0.12]:
                preds = np.array([-disp, -disp / 2, disp / 2, disp])
                w = allocator.optimize_multi_model_blend(
                    predicted_returns=preds,
                    returns_df=returns_df,
                    cov_matrix=cov_matrix,
                    symbols=symbols,
                    regime=regime,
                )
                assert np.isclose(np.sum(w), 1.0, atol=1e-3)


# ==============================================================================
# F30: Market-Specific STT & Fee-Aware Leland Dynamic Buffer Bands Tests
# ==============================================================================

class TestF30MarketSpecificLelandBufferBands:
    """Tests for F30: Market-Specific STT & Fee-Aware Leland Dynamic Buffer Bands."""

    def test_f30_is_korean_asset_helper(self):
        """Verifies correct identification of Korean assets vs US/global assets."""
        assert UnifiedPortfolioAllocator.is_korean_asset("005930.KS") is True
        assert UnifiedPortfolioAllocator.is_korean_asset("068270.KQ") is True
        assert UnifiedPortfolioAllocator.is_korean_asset("000660") is True   # 6-digit KRX symbol
        assert UnifiedPortfolioAllocator.is_korean_asset("AAPL") is False
        assert UnifiedPortfolioAllocator.is_korean_asset("MSFT.US") is False
        assert UnifiedPortfolioAllocator.is_korean_asset("NVDA") is False

    def test_f30_korean_assets_receive_wider_buffer_bands(self):
        """
        Korean assets pay 0.18% STT (>= 25 bps cost fraction), so their no-trade buffer bands
        Delta_i = (0.75 * c_i * w_i * (1-w_i) * sigma^2 / gamma)^(1/3) must be strictly wider
        than US assets (<= 8 bps cost fraction) under identical weights and volatilities.
        """
        allocator = UnifiedPortfolioAllocator(leland_cost_bps=20.0, risk_aversion=1.0)
        target_w = np.array([0.15, 0.15])
        vols = np.array([0.02, 0.02])

        symbols_mixed = ["005930.KS", "AAPL"]
        current_drift = np.array([0.15 + 0.017, 0.15 + 0.025])

        w_out = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=current_drift,
            volatilities=vols,
            symbols=symbols_mixed,
        )

        # Korean asset (005930.KS) at 0.167 is within its wide ~2.5%+ buffer -> should HOLD (remain 0.167)
        assert np.isclose(w_out[0], current_drift[0], atol=1e-4), (
            f"Korean asset should hold current weight {current_drift[0]} to avoid 0.18% STT, got {w_out[0]}"
        )
        # US asset (AAPL) at 0.175 breached its narrower ~1.9% buffer -> rebalanced
        assert w_out[1] < current_drift[1], (
            f"US asset should rebalance when breaching narrower buffer band, got {w_out[1]}"
        )

    def test_f30_custom_asset_cost_bps_override(self):
        """Verifies that providing custom asset_cost_bps directly shapes the bands."""
        allocator = UnifiedPortfolioAllocator()
        target_w = np.array([0.20, 0.20])
        current_w = np.array([0.22, 0.22])  # 2.0% drift
        vols = np.array([0.02, 0.02])

        # High cost (60 bps) vs Low cost (5 bps)
        custom_costs = [60.0, 5.0]
        w_res = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=current_w,
            volatilities=vols,
            asset_cost_bps=custom_costs,
        )

        # Asset 0 (high cost) holds current weight (0.22)
        assert np.isclose(w_res[0], 0.22, atol=1e-4)
        # Asset 1 (low cost) rebalances towards target or boundary
        assert w_res[1] < 0.22


# ==============================================================================
# F31: Multi-Tier L2 OBI & Volume-Weighted Micro-Price Pegging Tests
# ==============================================================================

class TestF31MultiTierOBIMicroPricePegging:
    """Tests for F31: Multi-Tier L2 OBI & Volume-Weighted Micro-Price Pegging."""

    def test_f31_micro_price_baseline(self):
        """When micro_price is provided, it replaces simple midpoint as the peg baseline."""
        target_p = 100.0
        bid_p = 99.0
        ask_p = 101.0
        spread = 2.0
        micro_p = 100.60

        peg_p = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spread,
            micro_price=micro_p,
        )

        assert np.isclose(peg_p, 100.60, atol=1e-3)

    def test_f31_multi_tier_composite_obi_shift(self):
        """
        When multi_obi (OBI_1, OBI_5, OBI_10) is provided, composite OBI is:
            OBI_comp = 0.50 * OBI_1 + 0.35 * OBI_5 + 0.15 * OBI_10
        and peg shift is 0.5 * spread * tanh(kappa * OBI_comp).
        """
        target_p = 1000.0
        bid_p = 990.0
        ask_p = 1010.0
        spread = 20.0
        micro_p = 1000.0
        kappa = 1.5

        multi_obi = {
            "OBI_1": 0.80,   # Level 1 book
            "OBI_5": 0.40,   # Level 5 book
            "OBI_10": 0.20,  # Level 10 book
        }
        exp_comp_obi = 0.50 * 0.80 + 0.35 * 0.40 + 0.15 * 0.20  # 0.57
        exp_shift = 0.5 * spread * math.tanh(kappa * exp_comp_obi)
        exp_peg = micro_p + exp_shift

        peg_p = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spread,
            kappa=kappa,
            micro_price=micro_p,
            multi_obi=multi_obi,
        )

        assert np.isclose(peg_p, exp_peg, atol=1e-3)
        assert bid_p <= peg_p <= ask_p

    def test_f31_scheduler_and_oms_parity(self):
        """Verifies ExecutionOMSEngine and AlmgrenChrissScheduler compute identical peg prices."""
        args = {
            "target_price": 500.0,
            "bid_price": 495.0,
            "ask_price": 505.0,
            "spread": 10.0,
            "micro_price": 502.0,
            "multi_obi": {"OBI_1": -0.6, "OBI_5": -0.3, "OBI_10": -0.1},
            "kappa": 1.2,
        }
        px_oms = ExecutionOMSEngine.calculate_peg_limit_price(**args)
        px_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(**args)
        assert np.isclose(px_oms, px_ac, atol=1e-4)


# ==============================================================================
# F32: Hawkes Arrival Intensity Adverse Selection Gating Tests
# ==============================================================================

class TestF32HawkesAdverseSelectionGating:
    """Tests for F32: Hawkes Arrival Intensity Adverse Selection Gating."""

    def test_f32_toxic_flow_detection_reduces_maker_and_expands_dark_probe(self):
        """
        When Hawkes arrival intensity lambda(t) > 2.5 * mu (toxic flow / aggressive sweep),
        SmartOrderRouter reduces primary maker leg from 70% to 30% and expands Tier 1
        dark midpoint probing to protect resting maker orders from front-running.
        """
        sor = SmartOrderRouter(dark_probe_ratio=0.40)
        order_plan = {
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 120.0,
            "execution_strategy": "PATIENT_TWAP",
            "market": "NASDAQ",
        }

        # Case 1: Normal flow (hawkes_intensity = 1.2 <= 2.5 * 1.0)
        route_normal = sor.route_order(
            order_plan=order_plan,
            hawkes_intensity=1.2,
            baseline_intensity=1.0,
        )
        assert route_normal["toxic_flow_detected"] is False
        assert route_normal["maker_ratio"] == 0.70

        # Case 2: Toxic flow burst (hawkes_intensity = 3.5 > 2.5 * 1.0)
        route_toxic = sor.route_order(
            order_plan=order_plan,
            hawkes_intensity=3.5,
            baseline_intensity=1.0,
        )
        assert route_toxic["toxic_flow_detected"] is True
        assert route_toxic["maker_ratio"] == 0.30
        assert route_toxic["effective_dark_ratio"] >= 0.60

        # Maker leg quantity under toxic flow should be significantly lower than normal flow
        maker_toxic = route_toxic["primary_exchange_maker"]["quantity"]
        maker_normal = route_normal["primary_exchange_maker"]["quantity"]
        assert maker_toxic < maker_normal

        # Total quantity across all 3 legs must strictly equal total_quantity
        total_q = sum(leg["quantity"] for leg in route_toxic["legs"])
        assert total_q == 10_000

    def test_f32_intensity_in_order_plan_dict(self):
        """Verifies that hawkes_intensity can be read directly from order_plan dictionary."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 5_000,
            "target_price": 200.0,
            "hawkes_intensity": 4.0,
            "baseline_intensity": 1.0,
            "execution_strategy": "MIDPOINT_PEG",
        }
        res = sor.route_order(plan)
        assert res["toxic_flow_detected"] is True
        assert res["maker_ratio"] == 0.30


# ==============================================================================
# F33: Closed-Loop Empirical Slippage Feedback Scaling Tests
# ==============================================================================

class TestF33ClosedLoopSlippageFeedbackScaling:
    """Tests for F33: Closed-Loop Empirical Slippage Feedback Scaling."""

    def test_f33_allocator_kappa_eff_scaling(self):
        """
        Verifies that kappa_eff = kappa_0 * cost_scaling_factor * (1 - phi_dark)
        in UnifiedPortfolioAllocator.optimize_multi_model_blend.
        """
        allocator = UnifiedPortfolioAllocator()
        symbols = ["AAPL", "MSFT"]
        returns_df = pd.DataFrame(np.random.normal(0.001, 0.02, (50, 2)), columns=symbols)
        cov_matrix = returns_df.cov().values

        # Test with cost_scaling_factor = 1.0 vs 2.0
        w_norm = allocator.optimize_multi_model_blend(
            predicted_returns=np.array([0.05, 0.02]),
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            current_weights=np.array([0.0, 0.0]),
            advs=np.array([100_000.0, 100_000.0]),
            total_capital=10_000_000.0,
            cost_scaling_factor=1.0,
        )

        w_high_slip = allocator.optimize_multi_model_blend(
            predicted_returns=np.array([0.05, 0.02]),
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            current_weights=np.array([0.0, 0.0]),
            advs=np.array([100_000.0, 100_000.0]),
            total_capital=10_000_000.0,
            cost_scaling_factor=2.0,
        )

        # Higher slippage penalty increases kappa_eff, which dampens convergence speed theta*,
        # meaning executed weight step is smaller when starting from 0.0
        assert np.sum(w_high_slip) <= np.sum(w_norm) + 1e-4

    def test_f33_gatheral_transient_impact_eta_scaling(self):
        """
        GatheralMarketImpactKernel.compute_transient_impact_decay scales eff_eta = eta * cost_scaling_factor.
        """
        t = np.array([0.1, 0.2, 0.5])
        decay_1 = GatheralMarketImpactKernel.compute_transient_impact_decay(
            time_elapsed_slices=t, eta=0.50, cost_scaling_factor=1.0
        )
        decay_2 = GatheralMarketImpactKernel.compute_transient_impact_decay(
            time_elapsed_slices=t, eta=0.50, cost_scaling_factor=1.5
        )
        assert np.all(np.isclose(decay_2, decay_1 * 1.5))

    def test_f33_gatheral_slices_soften_urgency_under_high_slippage(self):
        """
        When realized slippage exceeds expectations (cost_scaling_factor > 1.0),
        Gatheral tranche slicing softens urgency bias to prevent excessive front-loading.
        """
        slices_normal = GatheralMarketImpactKernel.compute_optimal_gatheral_slices(
            total_quantity=1000, n_slices=5, alpha_decay_half_life=2.0, cost_scaling_factor=1.0
        )
        slices_high_slip = GatheralMarketImpactKernel.compute_optimal_gatheral_slices(
            total_quantity=1000, n_slices=5, alpha_decay_half_life=2.0, cost_scaling_factor=2.0
        )

        # Under high slippage penalty, the first tranche is less aggressive
        assert slices_high_slip[0] <= slices_normal[0]
        # Sum of tranches remains exactly equal to total_quantity
        assert sum(slices_high_slip) == 1000
        assert sum(slices_normal) == 1000
