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
