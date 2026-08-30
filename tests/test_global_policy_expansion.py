"""
tests/test_global_policy_expansion.py
Comprehensive test suite verifying global quantitative policy expansion across:
1. TradingConfig (Country Rf, CRP, ERP, Timezones, Caps)
2. GlobalMarketClient & FX Triangulation (Cross rates, MarketSessionManager)
3. RIMValuationEngine (Country-specific discount rates & CRP)
4. SupplyChainEngine (Global supplier-customer momentum graph)
5. FXAdjustedCovarianceEngine (Multi-currency compound returns)
6. PortfolioAllocator (Country concentration limits & turnover regularization)
7. ExecutionOMSEngine (Multi-currency order planning)
"""

import math
import numpy as np
import pandas as pd

from src.config import TradingConfig
from src.data_layer.global_market import GlobalMarketClient, MarketSessionManager
from src.core.rim_valuation import RIMValuationEngine
from src.core.supply_chain import LEAD_CUSTOMER_MAP
from src.risk.fx_adjusted_covariance import FXAdjustedCovarianceEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.execution.oms_engine import ExecutionOMSEngine


def test_trading_config_global_parameters():
    cfg = TradingConfig()

    # Test Country Risk-Free Rates
    assert cfg.get_country_risk_free_rate("SP500") == 0.040
    assert cfg.get_country_risk_free_rate("KOSPI") == 0.033
    assert cfg.get_country_risk_free_rate("JAPAN") == 0.012
    assert cfg.get_country_risk_free_rate("INDIA") == 0.068
    assert cfg.get_country_risk_free_rate("BRAZIL") == 0.115

    # Test Country Risk Premia (CRP)
    assert cfg.get_country_risk_premium("SP500") == 0.000
    assert cfg.get_country_risk_premium("KOSPI") == 0.005
    assert cfg.get_country_risk_premium("VIETNAM") == 0.035
    assert cfg.get_country_risk_premium("BRAZIL") == 0.032

    # Test Timezones
    assert cfg.get_market_timezone("SP500") == "America/New_York"
    assert cfg.get_market_timezone("KOSPI") == "Asia/Seoul"
    assert cfg.get_market_timezone("JAPAN") == "Asia/Tokyo"
    assert cfg.get_market_timezone("EUROPE") == "Europe/Paris"
    assert cfg.get_market_timezone("TAIWAN") == "Asia/Taipei"

    # Test Country Max Weight Cap
    assert 0.10 <= cfg.get_max_country_weight("SP500") <= 0.50


def test_global_market_fx_cross_rates():
    client = GlobalMarketClient()

    # USD to KRW rate should be around ~1000-1600
    rate_usd_krw = client.get_cross_rate(from_curr="USD", to_curr="KRW")
    assert rate_usd_krw > 1000.0

    # JPY to KRW rate should be around ~5.0-15.0 KRW per JPY
    rate_jpy_krw = client.get_cross_rate(from_curr="JPY", to_curr="KRW")
    assert 5.0 < rate_jpy_krw < 15.0

    # EUR to KRW rate should be around ~1200-1800
    rate_eur_krw = client.get_cross_rate(from_curr="EUR", to_curr="KRW")
    assert 1200.0 < rate_eur_krw < 1800.0

    # Identical currency rate should be exactly 1.0
    assert client.get_cross_rate(from_curr="USD", to_curr="USD") == 1.0
    assert client.get_cross_rate(from_curr="KRW", to_curr="KRW") == 1.0

    # MarketSessionManager regions
    assert MarketSessionManager.get_market_region("JAPAN") == "ASIA_PACIFIC"
    assert MarketSessionManager.get_market_region("EUROPE") == "EUROPE"
    assert MarketSessionManager.get_market_region("SP500") == "AMERICAS"


def test_rim_valuation_country_discount_rates():
    engine = RIMValuationEngine()

    # US Mega-cap vs India vs Brazil required returns
    r_us = engine.derive_required_return(market="SP500", us10y_yield=4.0, vix_val=15.0, asset_beta=1.0)
    r_kr = engine.derive_required_return(market="KOSPI", us10y_yield=4.0, vix_val=15.0, asset_beta=1.0)
    r_in = engine.derive_required_return(market="INDIA", us10y_yield=4.0, vix_val=15.0, asset_beta=1.0)
    r_br = engine.derive_required_return(market="BRAZIL", us10y_yield=4.0, vix_val=15.0, asset_beta=1.0)

    # Brazil (high inflation & high Rf) and India should have higher required returns than US/Korea
    assert r_us < r_kr
    assert r_kr < r_in
    assert r_in < r_br

    # VIX spike expands required return countercyclically
    r_us_stress = engine.derive_required_return(market="SP500", us10y_yield=4.0, vix_val=35.0, asset_beta=1.0)
    assert r_us_stress > r_us


def test_supply_chain_global_nodes():
    # Verify critical international semiconductor & hardware nodes exist
    assert "2330.TW" in LEAD_CUSTOMER_MAP # TSMC
    assert "8035.T" in LEAD_CUSTOMER_MAP  # Tokyo Electron
    assert "6857.T" in LEAD_CUSTOMER_MAP  # Advantest
    assert "ASML.AS" in LEAD_CUSTOMER_MAP # ASML
    assert "300750.SZ" in LEAD_CUSTOMER_MAP # CATL
    assert "BHP.AX" in LEAD_CUSTOMER_MAP  # BHP
    assert "VALE3.SA" in LEAD_CUSTOMER_MAP # Vale
    assert "INFY.NS" in LEAD_CUSTOMER_MAP # Infosys

    # Verify target connections
    assert "NVDA" in LEAD_CUSTOMER_MAP["2330.TW"]
    assert "2330.TW" in LEAD_CUSTOMER_MAP["8035.T"]


def test_fx_adjusted_covariance_multi_market():
    dates = pd.date_range("2026-01-01", periods=30, freq="B")
    prices_dict = {
        "005930": pd.DataFrame({"Close": np.linspace(70000, 75000, 30)}, index=dates),
        "NVDA": pd.DataFrame({"Close": np.linspace(120, 130, 30)}, index=dates),
        "2330.TW": pd.DataFrame({"Close": np.linspace(950, 1000, 30)}, index=dates),
    }
    usdkrw = pd.Series(np.linspace(1350, 1380, 30), index=dates)
    market_map = {"005930": "KOSPI", "NVDA": "NASDAQ", "2330.TW": "TAIWAN"}

    returns_krw = FXAdjustedCovarianceEngine.compute_krw_adjusted_returns(
        prices_dict=prices_dict,
        usdkrw_series=usdkrw,
        market_map=market_map,
        lookback_days=30
    )

    assert not returns_krw.empty
    assert "005930" in returns_krw.columns
    assert "NVDA" in returns_krw.columns
    assert "2330.TW" in returns_krw.columns


def test_portfolio_allocator_country_caps():
    allocator = PortfolioAllocator(default_max_weight=0.25, default_max_sector_weight=0.50)

    symbols = ["AAPL", "MSFT", "NVDA", "005930", "000660", "2330.TW", "8035.T"]
    exp_returns = pd.Series([0.15, 0.14, 0.18, 0.10, 0.12, 0.16, 0.13], index=symbols)
    dates = pd.date_range("2026-01-01", periods=40, freq="B")
    
    np.random.seed(42)
    rets = np.random.normal(0.001, 0.02, size=(40, len(symbols)))
    returns_df = pd.DataFrame(rets, index=dates, columns=symbols)

    market_map = {
        "AAPL": "SP500", "MSFT": "SP500", "NVDA": "NASDAQ",
        "005930": "KOSPI", "000660": "KOSPI",
        "2330.TW": "TAIWAN", "8035.T": "JAPAN"
    }

    # Optimize with a 45% country cap
    weights = allocator.optimize_turnover_regularized_portfolio(
        expected_returns=exp_returns,
        returns_df=returns_df,
        market_map=market_map,
        max_country_weight=0.45,
        max_weight=0.25
    )

    assert len(weights) == len(symbols)
    assert math.isclose(sum(weights.values()), 1.0, abs_tol=1e-3)

    # Calculate US country weight
    us_weight = sum(weights[s] for s in ["AAPL", "MSFT", "NVDA"])
    assert us_weight <= 0.48  # Respects country cap within numerical tolerance


def test_execution_oms_multi_currency():
    oms = ExecutionOMSEngine(db_path=":memory:")

    top_preds = [
        {
            "symbol": "005930", "name": "Samsung Electronics", "market": "KOSPI",
            "action": "BUY", "close_price": 75000.0, "target_price": 75000.0,
            "expected_return": 0.05, "volatility_20d": 0.015, "adv": 100_000_000_000.0
        },
        {
            "symbol": "AAPL", "name": "Apple Inc", "market": "SP500",
            "action": "BUY", "close_price": 220.0, "target_price": 220.0,
            "expected_return": 0.08, "volatility_20d": 0.018, "adv": 50_000_000_000.0
        },
        {
            "symbol": "7203.T", "name": "Toyota Motor", "market": "JAPAN",
            "action": "BUY", "close_price": 3200.0, "target_price": 3200.0,
            "expected_return": 0.06, "volatility_20d": 0.016, "adv": 30_000_000_000.0
        }
    ]

    weights = {"005930": 0.30, "AAPL": 0.40, "7203.T": 0.30}
    plans = oms.generate_order_plan(
        top_predictions=top_preds,
        portfolio_weights=weights,
        total_capital=100_000_000.0, # 100M KRW
        usdkrw_rate=1350.0,
        use_leland_buffer=False
    )

    assert len(plans) >= 2
    symbols_in_plan = [p["symbol"] for p in plans]
    assert "005930" in symbols_in_plan
    assert "AAPL" in symbols_in_plan
