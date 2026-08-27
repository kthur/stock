"""
tests/test_unified_portfolio_engine.py
Comprehensive test suite for the institutional-grade quantitative portfolio management system:
1. FXAdjustedCovarianceEngine (Global calendar alignment & USD/KRW compounding return adjustment)
2. Rockafellar-Uryasev (2000) CVaR Convex Programming Optimizer
3. Market-Cap Weighted Black-Litterman Allocation with Idzorek Uncertainty
4. Full Covariance Multi-Asset Fractional Kelly Allocation
5. Leland Dynamic No-Trade Buffer Band Gating in OMS Execution
6. Volatility Drag Defense in DeltaBetaHedgeEngine
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.risk.fx_adjusted_covariance import FXAdjustedCovarianceEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.delta_beta_hedge import DeltaBetaHedgeEngine
from src.execution.oms_engine import ExecutionOMSEngine


@pytest.fixture
def sample_price_data():
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=60, freq="B")
    
    # 2 Korean stocks, 2 US stocks
    p_kr1 = 10000.0 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 60)))
    p_kr2 = 50000.0 * np.exp(np.cumsum(np.random.normal(0.0003, 0.020, 60)))
    p_us1 = 150.0 * np.exp(np.cumsum(np.random.normal(0.0008, 0.018, 60)))
    p_us2 = 300.0 * np.exp(np.cumsum(np.random.normal(0.0004, 0.022, 60)))

    prices_dict = {
        "005930": pd.DataFrame({"Close": p_kr1, "Volume": np.random.randint(100000, 500000, 60)}, index=dates),
        "000660": pd.DataFrame({"Close": p_kr2, "Volume": np.random.randint(50000, 200000, 60)}, index=dates),
        "AAPL": pd.DataFrame({"Close": p_us1, "Volume": np.random.randint(1000000, 5000000, 60)}, index=dates),
        "MSFT": pd.DataFrame({"Close": p_us2, "Volume": np.random.randint(500000, 2000000, 60)}, index=dates)
    }

    # USD/KRW FX series
    fx_rates = 1350.0 * np.exp(np.cumsum(np.random.normal(0.0001, 0.005, 60)))
    usdkrw_series = pd.Series(fx_rates, index=dates)

    return prices_dict, usdkrw_series


class TestFXAdjustedCovarianceEngine:
    def test_calendar_alignment_and_fx_adjustment(self, sample_price_data):
        prices_dict, usdkrw = sample_price_data
        mkt_map = {"005930": "KOSPI", "000660": "KOSPI", "AAPL": "SP500", "MSFT": "NASDAQ"}

        cov_df, ret_df = FXAdjustedCovarianceEngine.compute_fx_adjusted_covariance(
            prices_dict=prices_dict,
            usdkrw_series=usdkrw,
            market_map=mkt_map,
            lookback_days=60
        )

        assert not cov_df.empty
        assert cov_df.shape == (4, 4)
        assert list(cov_df.columns) == ["005930", "000660", "AAPL", "MSFT"]
        # Positive definite check (all eigenvalues > 0)
        eigenvalues = np.linalg.eigvals(cov_df.values)
        assert np.all(eigenvalues > 0)
        # Verify diagonal is positive variance
        assert np.all(np.diag(cov_df.values) > 0)


class TestRockafellarUryasevCVaR:
    def test_convex_cvar_optimization_constraints(self):
        allocator = PortfolioAllocator(default_max_weight=0.30)
        np.random.seed(42)
        symbols = ["S1", "S2", "S3", "S4", "S5"]
        expected_returns = pd.Series([0.08, 0.06, 0.05, 0.04, 0.03], index=symbols)
        
        # 60 days of historical returns
        returns_mat = np.random.normal(0.0005, 0.015, (60, 5))
        # Inject tail shock on asset S1
        returns_mat[10, 0] = -0.08
        returns_mat[25, 0] = -0.06

        ret_df = pd.DataFrame(returns_mat, columns=symbols)
        sector_map = {"S1": "TECH", "S2": "TECH", "S3": "FIN", "S4": "FIN", "S5": "HLTH"}

        weights = allocator.optimize_rockafellar_uryasev_cvar(
            expected_returns=expected_returns,
            historical_returns=ret_df,
            max_cvar_limit=0.035,
            confidence=0.95,
            max_weight=0.35,
            sector_map=sector_map,
            max_sector_weight=0.50
        )

        assert len(weights) == 5
        assert math.isclose(sum(weights.values()), 1.0, rel_tol=1e-3)
        # Max single stock weight constraint check
        for sym, w in weights.items():
            assert w <= 0.35 + 1e-4
            assert w >= 0.0

        # Sector constraint check (TECH: S1 + S2 <= 0.50)
        tech_w = weights["S1"] + weights["S2"]
        assert tech_w <= 0.50 + 1e-4


class TestMarketCapBlackLitterman:
    def test_market_cap_bl_equilibrium_prior(self, sample_price_data):
        prices_dict, _ = sample_price_data
        allocator = PortfolioAllocator()

        predicted_returns = {
            "005930": 0.06,
            "000660": 0.04,
            "AAPL": 0.08,
            "MSFT": 0.07
        }
        # Realistic market caps in KRW (AAPL & MSFT much larger than Korean names)
        market_caps = {
            "005930": 400_000_000_000_000.0,
            "000660": 100_000_000_000_000.0,
            "AAPL": 3_500_000_000_000_000.0,
            "MSFT": 3_200_000_000_000_000.0
        }
        meta_convictions = {
            "005930": 0.85,
            "000660": 0.70,
            "AAPL": 0.90,
            "MSFT": 0.80
        }

        bl_df = allocator.allocate_market_cap_black_litterman(
            predicted_returns=predicted_returns,
            prices_dict=prices_dict,
            market_caps=market_caps,
            meta_convictions=meta_convictions,
            total_portfolio_value=100_000_000.0,
            max_weight=0.40
        )

        assert not bl_df.empty
        assert len(bl_df) == 4
        assert math.isclose(bl_df["weight"].sum(), 1.0, rel_tol=1e-3)
        assert math.isclose(bl_df["allocation_amount"].sum(), 100_000_000.0, rel_tol=1e-2)


class TestFullCovarianceKelly:
    def test_full_covariance_kelly_allocation(self):
        allocator = PortfolioAllocator()
        symbols = ["A", "B", "C"]
        expected_returns = pd.Series([0.05, 0.03, 0.02], index=symbols)
        cov = np.array([
            [0.0004, 0.0001, 0.00005],
            [0.0001, 0.0003, 0.00008],
            [0.00005, 0.00008, 0.0002]
        ])

        weights = allocator.allocate_full_covariance_kelly(
            expected_returns=expected_returns,
            covariance_matrix=cov,
            kelly_fraction=0.25,
            max_weight=0.50
        )

        assert len(weights) == 3
        assert math.isclose(sum(weights.values()), 1.0, rel_tol=1e-3)
        assert weights["A"] >= weights["C"]  # Asset A has highest excess return per unit risk


class TestLelandBufferGatingInOMS:
    def test_leland_buffer_skips_redundant_order(self):
        engine = ExecutionOMSEngine(db_path=":memory:")
        top_predictions = [
            {"symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "volatility_20d": 0.018, "action": "BUY"},
            {"symbol": "000660", "market": "KOSPI", "close_price": 120000.0, "volatility_20d": 0.022, "action": "BUY"}
        ]
        target_weights = {"005930": 0.10, "000660": 0.15}
        
        # Scenario: 005930 is already held at 0.098 (within Leland buffer ±0.015 of 0.10)
        # 000660 is newly bought from 0.0 to 0.15 (outside buffer)
        current_holdings = {"005930": 0.098, "000660": 0.0}

        plans = engine.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=target_weights,
            total_capital=100_000_000.0,
            current_holdings=current_holdings,
            use_leland_buffer=True
        )

        plan_symbols = [p["symbol"] for p in plans]
        assert "000660" in plan_symbols
        # 005930 was skipped due to Leland buffer band gating!
        assert "005930" not in plan_symbols


class TestDeltaBetaHedgeVolatilityDrag:
    def test_inverse_hierarchy_and_drag_mitigation(self):
        hedge_engine = DeltaBetaHedgeEngine()
        portfolio_weights = {"005930": 0.50, "000660": 0.50}
        betas = {"005930": 1.2, "000660": 1.4}

        # Moderate bear regime -> 1X inverse (114800.KS)
        res_mod = hedge_engine.calculate_optimal_hedge_allocation(
            portfolio_weights=portfolio_weights,
            symbol_betas=betas,
            crisis_level="WATCH",
            regime="BEAR"
        )
        assert res_mod["hedge_etf_symbol"] == "114800.KS"

        # Severe crisis regime -> 2X leveraged inverse (252670.KS)
        res_sev = hedge_engine.calculate_optimal_hedge_allocation(
            portfolio_weights=portfolio_weights,
            symbol_betas=betas,
            crisis_level="SEVERE",
            regime="BEAR_HIGH_VOL"
        )
        assert res_sev["hedge_etf_symbol"] == "252670.KS"
        assert res_sev["hedge_weight"] > 0.0


class TestRMTMarchenkoPasturDenoising:
    def test_marchenko_pastur_denoising_properties(self):
        np.random.seed(42)
        n_assets = 10
        t_obs = 30
        # Generate correlated synthetic returns
        raw_mat = np.random.normal(0, 0.02, (t_obs, n_assets))
        cov_raw = np.cov(raw_mat, rowvar=False)

        cov_denoised = FXAdjustedCovarianceEngine.denoise_covariance_marchenko_pastur(
            cov_matrix=cov_raw,
            t_obs=t_obs,
            n_assets=n_assets
        )

        assert cov_denoised.shape == (n_assets, n_assets)
        # All eigenvalues must be positive (positive definite)
        eigenvals = np.linalg.eigvals(cov_denoised)
        assert np.all(eigenvals > 0)
        # Diagonal variances must be strictly positive
        assert np.all(np.diag(cov_denoised) > 0)


class TestDynamicMacroTermStructure:
    def test_dynamic_rf_retrieval(self):
        rf_us = PortfolioAllocator.get_dynamic_risk_free_rate(market="US")
        rf_kr = PortfolioAllocator.get_dynamic_risk_free_rate(market="KOSPI")

        assert isinstance(rf_us, float)
        assert isinstance(rf_kr, float)
        assert 0.01 <= rf_us <= 0.15
        assert 0.01 <= rf_kr <= 0.15


class TestHybridVolatilityModel:
    def test_garman_klass_and_ewma_hybrid_volatility(self):
        dates = pd.date_range("2026-01-01", periods=30)
        np.random.seed(42)
        c = 100.0 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 30)))
        h = c * (1.0 + np.abs(np.random.normal(0, 0.01, 30)))
        l = c * (1.0 - np.abs(np.random.normal(0, 0.01, 30)))
        o = (h + l) / 2.0
        df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=dates)

        vol = PortfolioAllocator.calculate_hybrid_volatility(df, lambda_ewma=0.94)
        assert isinstance(vol, float)
        assert 0.005 <= vol <= 0.20


class TestWardLinkageHERCHRP:
    def test_ward_linkage_hrp_weights(self):
        from src.analysis.portfolio_optimizer import calculate_hrp_weights
        np.random.seed(42)
        cov = np.array([
            [0.0004, 0.0002, 0.00005],
            [0.0002, 0.0005, 0.00008],
            [0.00005, 0.00008, 0.0003]
        ])
        weights_ward = calculate_hrp_weights(cov, linkage_method="ward")
        weights_complete = calculate_hrp_weights(cov, linkage_method="complete")

        assert len(weights_ward) == 3
        assert len(weights_complete) == 3
        assert math.isclose(np.sum(weights_ward), 1.0, rel_tol=1e-3)
        assert math.isclose(np.sum(weights_complete), 1.0, rel_tol=1e-3)


class TestAlphaHalfLifeOMSRouting:
    def test_alpha_half_life_routing(self):
        engine = ExecutionOMSEngine(db_path=":memory:")
        # Fast alpha (surge)
        fast_pred = [{"symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "adv": 50_000_000.0, "surge_prob": 0.85}]
        # Slow alpha (rim_valuation)
        slow_pred = [{"symbol": "000660", "market": "KOSPI", "close_price": 120000.0, "adv": 50_000_000.0, "rim_valuation_score": 0.90}]

        fast_plans = engine.generate_order_plan(fast_pred, {"005930": 0.08}, total_capital=100_000_000.0)
        slow_plans = engine.generate_order_plan(slow_pred, {"000660": 0.08}, total_capital=100_000_000.0)

        assert fast_plans[0]["execution_strategy"] == "FAST_VWAP"
        assert slow_plans[0]["execution_strategy"] in ["PATIENT_TWAP", "MIDPOINT_PEG"]


class TestDynamicFXOverlay:
    def test_cip_and_momentum_fx_forward_overlay(self):
        dates = pd.date_range("2026-01-01", periods=30)
        # Upward trending FX
        fx_up = pd.Series(np.linspace(1300, 1400, 30), index=dates)
        res_up = DeltaBetaHedgeEngine.calculate_optimal_fx_overlay(
            us_portfolio_weight=0.50,
            usdkrw_series=fx_up,
            us_yield=0.045,
            kr_yield=0.035,
            regime="BULL_LOW_VOL"
        )
        assert res_up["fx_hedge_ratio"] == 0.20  # Mild hedge during dollar appreciation

        # Downward trending FX
        fx_down = pd.Series(np.linspace(1400, 1300, 30), index=dates)
        res_down = DeltaBetaHedgeEngine.calculate_optimal_fx_overlay(
            us_portfolio_weight=0.50,
            usdkrw_series=fx_down,
            us_yield=0.035,
            kr_yield=0.038,
            regime="BULL_LOW_VOL"
        )
        assert res_down["fx_hedge_ratio"] == 0.80  # Strong hedge during dollar depreciation


class TestBarraFactorRiskDecomposition:
    def test_factor_and_idiosyncratic_risk_decomposition(self):
        # 3 assets, 2 factors
        weights = np.array([0.5, 0.3, 0.2])
        factor_loadings = np.array([
            [1.1, 0.4],
            [0.8, -0.2],
            [0.5, 0.9]
        ])
        factor_cov = np.array([
            [0.0004, 0.0001],
            [0.0001, 0.0003]
        ])
        idiosyncratic_vars = np.array([0.0002, 0.0003, 0.00025])

        decomp = PortfolioAllocator.decompose_factor_risk(
            weights=weights,
            factor_loadings=factor_loadings,
            factor_covariance=factor_cov,
            idiosyncratic_vars=idiosyncratic_vars
        )

        assert "total_variance" in decomp
        assert "factor_variance" in decomp
        assert "idiosyncratic_variance" in decomp
        assert "idiosyncratic_risk_ratio" in decomp
        assert 0.0 <= decomp["idiosyncratic_risk_ratio"] <= 1.0
        assert math.isclose(decomp["total_variance"], decomp["factor_variance"] + decomp["idiosyncratic_variance"], rel_tol=1e-3)


class TestHERCAllocation:
    def test_herc_hierarchical_equal_risk_weights(self):
        from src.analysis.portfolio_optimizer import calculate_herc_weights
        np.random.seed(42)
        cov = np.array([
            [0.0006, 0.0001, 0.00005, 0.00002],
            [0.0001, 0.0005, 0.00004, 0.00003],
            [0.00005, 0.00004, 0.0004, 0.0001],
            [0.00002, 0.00003, 0.0001, 0.00035]
        ])
        weights_herc = calculate_herc_weights(cov, max_k=2)

        assert len(weights_herc) == 4
        assert math.isclose(np.sum(weights_herc), 1.0, rel_tol=1e-3)
        assert np.all(weights_herc >= 0.0)


class TestCPPIDrawdownCushion:
    def test_cppi_cushion_and_exposure_scaling(self):
        # Scenario 1: NAV at peak -> Full gross exposure
        res_peak = PortfolioAllocator.calculate_cppi_gross_exposure(
            current_nav=100_000_000.0,
            peak_nav=100_000_000.0,
            max_drawdown_limit=0.08,
            multiplier=3.5
        )
        assert res_peak["target_gross_exposure"] > 0.20
        assert res_peak["cushion"] == 0.08

        # Scenario 2: Severe drawdown breaching floor -> Zero exposure (cash preservation)
        res_floor = PortfolioAllocator.calculate_cppi_gross_exposure(
            current_nav=90_000_000.0,
            peak_nav=100_000_000.0,
            max_drawdown_limit=0.08,
            multiplier=3.5
        )
        assert res_floor["target_gross_exposure"] == 0.0
        assert res_floor["cash_buffer_ratio"] == 1.0


class TestGatheralMarketImpactKernel:
    def test_gatheral_decay_and_slicing(self):
        from src.execution.oms_engine import GatheralMarketImpactKernel
        perm_imp = GatheralMarketImpactKernel.estimate_permanent_impact(
            quantity=10000,
            adv=1_000_000,
            daily_volatility=0.02
        )
        assert perm_imp > 0.0

        slices = GatheralMarketImpactKernel.compute_optimal_gatheral_slices(
            total_quantity=1000,
            n_slices=5,
            alpha_decay_half_life=2.0
        )
        assert len(slices) == 5
        assert sum(slices) == 1000
        # Fast alpha: first slice should be larger than last slice
        assert slices[0] >= slices[-1]


class TestDieboldYilmazVolatilitySpillover:
    def test_volatility_spillover_index(self):
        dates = pd.date_range("2026-01-01", periods=40)
        np.random.seed(42)
        df_ret = pd.DataFrame({
            "SP500": np.random.normal(0, 0.015, 40),
            "KOSPI": np.random.normal(0, 0.018, 40),
            "USDKRW": np.random.normal(0, 0.006, 40),
            "WTI": np.random.normal(0, 0.025, 40)
        }, index=dates)

        tsi_res = PortfolioAllocator.calculate_volatility_spillover_index(df_ret, lookback=30)
        assert "total_spillover_index" in tsi_res
        assert 0.0 <= tsi_res["total_spillover_index"] <= 100.0


class TestMultiHorizonRankICDecay:
    def test_rank_ic_decay_calibration(self):
        from src.ai.ensemble_scorer import EnsembleScoringEngine
        base_w = {"surge": 0.25, "rim_valuation": 0.25, "mq_factor": 0.25, "stat_arb": 0.25}
        rank_ic = {"surge": 0.15, "rim_valuation": 0.02, "mq_factor": 0.08, "stat_arb": -0.05}
        half_lives = {"surge": 1.0, "rim_valuation": 60.0, "mq_factor": 15.0, "stat_arb": 7.0}

        # Stale latency (e.g. 3 days old signal) -> surge decays quickly, rim_valuation remains robust
        calibrated = EnsembleScoringEngine.apply_rank_ic_decay_calibration(
            base_weights=base_w,
            strategy_rank_ic_dict=rank_ic,
            strategy_half_lives=half_lives,
            latency_days=3.0
        )

        assert math.isclose(sum(calibrated.values()), 1.0, rel_tol=1e-3)
        # Surge with 1d half-life after 3 days decays more than RIM with 60d half-life
        assert calibrated["rim_valuation"] > calibrated["stat_arb"]


class TestTopDecileConvexAlphaBoost:
    def test_convex_alpha_boosting(self):
        from src.ai.ensemble_scorer import EnsembleScoringEngine
        # Mock scores DataFrame: 1 symbol with extreme surge (0.95), vcp (0.85), order_flow (0.80), rest 0.50
        df = pd.DataFrame({
            "surge_score": [0.95, 0.40],
            "vcp_score": [0.85, 0.50],
            "order_flow_score": [0.80, 0.45],
            "reg_score": [0.50, 0.50],
            "rim_score": [0.50, 0.50]
        })
        base = pd.Series([0.55, 0.45])
        boosted = EnsembleScoringEngine.apply_top_decile_convex_boost(
            scores_df=df,
            strategy_cols=list(df.columns),
            base_scores=base,
            top_k=3,
            lambda_boost=0.40
        )
        # First row should be boosted significantly (> 0.65)
        assert boosted.iloc[0] > 0.65
        # Second row should not be boosted (stays base)
        assert math.isclose(boosted.iloc[1], 0.45, rel_tol=1e-2)


class TestConvictionAlphaSizing:
    def test_conviction_alpha_precision_weights(self):
        from src.risk.position_sizing import PortfolioAllocator
        rets = np.array([0.25, 0.05, 0.02])
        vols = np.array([0.03, 0.02, 0.015])
        weights = PortfolioAllocator.calculate_conviction_alpha_weights(
            expected_returns=rets,
            volatilities=vols,
            gamma=1.5,
            max_single_cap=0.25
        )
        assert len(weights) == 3
        assert math.isclose(np.sum(weights), 1.0, rel_tol=1e-3)
        # High expected return asset gets largest allocation
        assert weights[0] > weights[1] > weights[2]


class TestMultiSleeveExecution:
    def test_multi_sleeve_order_plan(self):
        engine = ExecutionOMSEngine(db_path=":memory:")
        # Fast sleeve symbol (surge) vs Core sleeve symbol (rim)
        top_pred = [
            {"symbol": "005930", "market": "KOSPI", "close_price": 70000.0, "adv": 50_000_000.0, "surge_prob": 0.85},
            {"symbol": "000660", "market": "KOSPI", "close_price": 120000.0, "adv": 50_000_000.0, "rim_valuation_score": 0.90}
        ]
        plans = engine.generate_order_plan(top_pred, {"005930": 0.50, "000660": 0.50}, total_capital=100_000_000.0)
        assert len(plans) == 2
        p0 = next(p for p in plans if p["symbol"] == "005930")
        p1 = next(p for p in plans if p["symbol"] == "000660")
        assert p0["sleeve_type"] == "FAST_MOMENTUM"
        assert p1["sleeve_type"] == "CORE_FUNDAMENTAL"
        assert p0["target_take_profit"] > p0["target_price"]


class TestBullMarketDynamicLeverage:
    def test_bull_market_cash_drag_eliminator(self):
        from src.risk.position_sizing import PortfolioAllocator
        allocator = PortfolioAllocator(max_total_allocation=0.85, max_single_position=0.40)
        # In Bull market, allocation scales to 98%
        preds = pd.DataFrame({
            "symbol": ["005930", "000660", "035420"],
            "market": ["KOSPI", "KOSPI", "KOSPI"],
            20: [15.0, 12.0, 10.0]
        })
        prices = {
            "005930": pd.DataFrame({"Close": [70000.0] * 30}),
            "000660": pd.DataFrame({"Close": [120000.0] * 30}),
            "035420": pd.DataFrame({"Close": [200000.0] * 30})
        }
        res = allocator.allocate(preds, prices, total_portfolio_value=100_000_000.0, regime="BULL_LOW_VOL")
        assert not res.empty
        assert res["weight"].sum() > 0.85  # Breached 85% cash drag up towards 98%


class TestChandelierTrailingExit:
    def test_chandelier_and_breakeven_lock(self):
        engine = ExecutionOMSEngine(db_path=":memory:")
        # Holding with entry 70,000, high 90,000, current price 85,000 (+21.4% profit above 10% threshold, below trailing stop 90000 - 2*ATR ~ 88000)
        holdings = {
            "005930": {
                "quantity": 100,
                "entry_price": 70000.0,
                "current_price": 85000.0,
            }
        }
        prices = {
            "005930": pd.DataFrame({
                "High": np.linspace(70000, 90000, 20),
                "Low": np.linspace(69000, 89000, 20),
                "Close": np.linspace(69500, 89500, 20)
            })
        }
        plans = engine.calculate_trailing_stop_plan(holdings, prices_dict=prices, profit_take_threshold=0.10)
        assert len(plans) == 1
        assert plans[0]["action"] == "SELL"
        assert plans[0]["reason"] == "CHANDELIER_TRAILING_PROFIT"


class TestSectorBreadthVelocityThrust:
    def test_sector_velocity_thrust(self):
        from src.core.sector_rotation import SectorRotationEngine
        dates = pd.date_range("2026-01-01", periods=25)
        # IT sector accelerating (high 5d momentum vs 20d)
        p_it = np.linspace(100, 105, 20).tolist() + [108, 112, 118, 125, 135]
        df_sec = pd.DataFrame({"IT": p_it}, index=dates)
        thrust = SectorRotationEngine.compute_sector_breadth_velocity_thrust(df_sec, short_window=5, long_window=20)
        assert "IT" in thrust
        assert thrust["IT"] > 0.05  # Positive momentum acceleration


class TestInterMarketCapitalFlight:
    def test_dynamic_capital_flight(self):
        from src.risk.position_sizing import PortfolioAllocator
        # US strongly outperforming KR (+25% vs -5%)
        budgets_flight = PortfolioAllocator.compute_dynamic_capital_flight_budgets(
            us_momentum_60d=0.25,
            kr_momentum_60d=-0.05
        )
        assert budgets_flight["SP500"] + budgets_flight["NASDAQ"] + budgets_flight["RUSSELL2000"] > 0.70
        assert budgets_flight["KOSPI"] + budgets_flight["KOSDAQ"] < 0.30



