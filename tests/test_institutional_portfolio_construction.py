"""
Tests for Unified Institutional Portfolio Construction & Allocation Engine
Verifies:
1. Multi-Model Regime-Adaptive Blending (BL + HERC + RP + CVaR)
2. 3/2-Power Non-Linear Market Impact Penalty
3. 12% Target Volatility Scaling & Bull Market Cash Drag Eliminator
4. Asymmetric Leland Dynamic No-Trade Buffer Bands
5. End-to-End Pipeline Allocation Integration
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


class TestMultiModelRegimeBlending:
    def test_regime_weights_shift(self):
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.30)
        n = 4
        symbols = ["A", "B", "C", "D"]
        pred_rets = np.array([0.15, 0.12, 0.08, 0.05])
        cov = np.eye(n) * 0.0004
        np.random.seed(42)
        rets_df = pd.DataFrame(np.random.normal(0.001, 0.02, (40, n)), columns=symbols)

        # 1. Bull Low-Vol: BL is dominant
        w_bull = allocator.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=rets_df,
            cov_matrix=cov,
            symbols=symbols,
            regime="BULL_LOW_VOL"
        )
        assert len(w_bull) == 4
        assert math.isclose(np.sum(w_bull), 1.0, rel_tol=1e-3)
        # Highest predicted return asset should get substantial allocation
        assert w_bull[0] >= w_bull[3]

        # 2. Crisis: CVaR is dominant (alpha views ignored, tail risk prioritized)
        w_crisis = allocator.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=rets_df,
            cov_matrix=cov,
            symbols=symbols,
            regime="CRISIS"
        )
        assert len(w_crisis) == 4
        assert math.isclose(np.sum(w_crisis), 1.0, rel_tol=1e-3)
        assert np.all(w_crisis <= 0.35)


class TestMarketImpactPenalty:
    def test_illiquid_asset_dampening(self):
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.40)
        symbols = ["LIQUID", "ILLIQUID"]
        pred_rets = np.array([0.10, 0.10])  # Identical return views
        cov = np.array([[0.0004, 0.0], [0.0, 0.0004]])  # Identical volatility
        rets_df = pd.DataFrame({
            "LIQUID": np.random.normal(0, 0.02, 30),
            "ILLIQUID": np.random.normal(0, 0.02, 30)
        })

        # Asset 1: Large ADV ($50M), Asset 2: Tiny ADV ($50k)
        advs = np.array([50_000_000.0, 50_000.0])
        w = allocator.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=rets_df,
            cov_matrix=cov,
            symbols=symbols,
            advs=advs,
            total_capital=10_000_000.0,  # $10M fund size creates massive impact on Asset 2
            regime="BULL_LOW_VOL"
        )

        # Liquid asset should receive significantly higher weight than illiquid asset
        assert w[0] > w[1] * 1.5


class TestTargetVolatilityScalingAndCashDrag:
    def test_bull_cash_drag_eliminator(self):
        allocator = UnifiedPortfolioAllocator(
            target_volatility=0.12,
            default_max_total_allocation=0.85
        )
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        # Low realized volatility: annualized vol ~ 8%
        cov = np.eye(4) * (0.08 / np.sqrt(252)) ** 2

        scaled_w, alloc_ratio = allocator.apply_target_volatility_scaling(
            weights=weights,
            cov_matrix=cov,
            regime="BULL_LOW_VOL"
        )

        # In Bull Low-Vol, allocation should scale up to 98% (cash drag eliminated)
        assert alloc_ratio >= 0.95
        assert math.isclose(np.sum(scaled_w), alloc_ratio, rel_tol=1e-3)

    def test_crisis_cash_preservation(self):
        allocator = UnifiedPortfolioAllocator(
            target_volatility=0.12,
            default_max_total_allocation=0.85
        )
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        # Extreme volatility: annualized vol ~ 40%
        cov = np.eye(4) * (0.40 / np.sqrt(252)) ** 2

        scaled_w, alloc_ratio = allocator.apply_target_volatility_scaling(
            weights=weights,
            cov_matrix=cov,
            regime="CRISIS"
        )

        # In Crisis, allocation scales down to preserve cash (40~50%)
        assert alloc_ratio <= 0.50
        assert math.isclose(np.sum(scaled_w), alloc_ratio, rel_tol=1e-3)


class TestLelandNoTradeBuffers:
    def test_no_trade_buffer_noise_suppression(self):
        allocator = UnifiedPortfolioAllocator(risk_aversion=1.0, leland_cost_bps=20.0)
        # Target weights vs current weights
        target_w = np.array([0.20, 0.15, 0.10])
        # Current weights are very close (drift < 1%)
        current_w = np.array([0.205, 0.145, 0.098])
        vols = np.array([0.02, 0.025, 0.03])

        realized_w = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=current_w,
            volatilities=vols
        )

        # Small drifts should be ignored, holding current weights
        assert math.isclose(realized_w[0], current_w[0], abs_tol=1e-5)
        assert math.isclose(realized_w[1], current_w[1], abs_tol=1e-5)
        assert math.isclose(realized_w[2], current_w[2], abs_tol=1e-5)

    def test_new_position_bypasses_buffer(self):
        allocator = UnifiedPortfolioAllocator()
        target_w = np.array([0.15, 0.10])
        current_w = np.array([0.00, 0.10])  # Asset 0 is a brand new position
        vols = np.array([0.02, 0.02])

        realized_w = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=current_w,
            volatilities=vols
        )

        # New entry should enter at target weight
        assert math.isclose(realized_w[0], 0.15, abs_tol=1e-5)


class TestUnifiedPortfolioAllocatorEndToEnd:
    def test_end_to_end_allocate(self):
        allocator = UnifiedPortfolioAllocator(target_volatility=0.12)
        symbols = ["005930", "000660", "AAPL", "MSFT"]
        preds = pd.DataFrame({
            "symbol": symbols,
            "market": ["KOSPI", "KOSPI", "SP500", "SP500"],
            "ensemble_expected_return": [15.0, 12.0, 18.0, 14.0],
            "adv": [100_000_000.0, 50_000_000.0, 200_000_000.0, 150_000_000.0]
        })

        # Mock price history
        dates = pd.date_range("2026-01-01", periods=30)
        prices = {}
        for s in symbols:
            base_p = 70000.0 if s.isdigit() else 200.0
            prices[s] = pd.DataFrame({"Close": np.linspace(base_p * 0.95, base_p, 30)}, index=dates)

        res = allocator.allocate(
            predictions_df=preds,
            prices_dict=prices,
            total_portfolio_value=100_000_000.0,
            regime="BULL_LOW_VOL"
        )

        assert not res.empty
        assert len(res) == 4
        assert "weight" in res.columns
        assert "shares" in res.columns
        assert "lot_size" in res.columns
        assert "allocation_amount" in res.columns

        # Lot sizes: KRX = 1 (single share standard since 2014), US = 1
        p_krx = res[res["symbol"] == "005930"].iloc[0]
        p_us = res[res["symbol"] == "AAPL"].iloc[0]
        assert p_krx["lot_size"] == 1
        assert p_krx["shares"] % 1 == 0
        assert p_us["lot_size"] == 1


class TestReportPortfolioParsing:
    def test_parse_portfolio_with_shares_and_lot(self):
        from generate_report import parse_portfolio_allocation
        mock_text = (
            "=== Portfolio Allocation Recommendations (Ensemble Kelly/Sharpe Optimized) ===\n"
            "Date: 2026-09-02 18:30\n"
            "Total Capital: 100,000,000 KRW\n"
            "Target Horizon: 20d\n\n"
            "Current Market Regime Detected: BULL_LOW_VOL (Code: 2)\n"
            "Maximum Total Allocation Allowed: 98.0%\n\n"
            "No.  Symbol       Name               Market       Shares    Lot   Return   Vol      Weight    Amount        \n"
            "---------------------------------------------------------------------------------------------------------\n"
            "1    005930       삼성전자             KOSPI           120    10   15.00%    2.50%    8.50%     8,500,000\n"
            "2    AAPL         Apple Inc          SP500            35     1   18.00%    2.20%    7.00%     7,000,000\n"
            "---------------------------------------------------------------------------------------------------------\n"
            "Allocated Capital: 15.50% (    15,500,000)\n"
            "Remaining Cash   : 84.50% (    84,500,000)\n"
        )
        data = parse_portfolio_allocation(mock_text)
        assert len(data.rows) == 2
        assert data.rows[0].symbol == "005930"
        assert data.rows[0].name == "삼성전자"
        assert data.rows[0].weight == "8.50%"
        assert data.rows[1].symbol == "AAPL"
        assert data.rows[1].weight == "7.00%"


class TestInstitutionalReturnEnhancements:
    def test_mean_cvar_alpha_tilt(self):
        """Verify that calculate_cvar_weights tilts toward high alpha assets when predicted returns are provided."""
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.50)
        np.random.seed(42)
        n = 3
        # Symmetric returns with similar volatility
        rets_df = pd.DataFrame(np.random.normal(0.001, 0.02, (60, n)), columns=["A", "B", "C"])
        
        # Predicted returns: Asset A has high alpha (+20%), Asset C has negative alpha (-10%)
        p_rets = np.array([0.20, 0.05, -0.10])
        w_tilted = allocator.calculate_cvar_weights(
            rets_df, confidence_level=0.95, predicted_returns=p_rets, lambda_alpha=1.0
        )
        assert len(w_tilted) == 3
        # Asset A must receive significantly higher allocation than Asset C
        assert w_tilted[0] > w_tilted[2]

    def test_market_cap_black_litterman_prior(self):
        """Verify that passing market_caps to optimize_multi_model_blend anchors BL prior to market capitalization."""
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.60)
        symbols = ["MEGA_CAP", "MICRO_CAP"]
        pred_rets = np.array([0.10, 0.10])
        cov = np.eye(2) * 0.0004
        rets_df = pd.DataFrame(np.random.normal(0, 0.02, (40, 2)), columns=symbols)
        # MEGA_CAP is 100x bigger than MICRO_CAP
        market_caps = np.array([100_000_000_000.0, 1_000_000_000.0])

        w = allocator.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=rets_df,
            cov_matrix=cov,
            symbols=symbols,
            market_caps=market_caps,
            regime="BULL_LOW_VOL"
        )
        assert w[0] > w[1]

    def test_fx_adjusted_returns_matrix(self):
        """Verify that compute_returns_matrix properly harmonizes US and KRX asset prices using fx_series."""
        dates = pd.date_range("2026-01-01", periods=30)
        # US stock price in USD: steady at $100
        p_us = pd.DataFrame({"Close": [100.0] * 30}, index=dates)
        # KR stock price in KRW: steady at 100,000 KRW
        p_kr = pd.DataFrame({"Close": [100_000.0] * 30}, index=dates)
        # USD/KRW surges 10% over the period (1,300 -> 1,430)
        fx_series = pd.Series(np.linspace(1300.0, 1430.0, 30), index=dates)

        prices_dict = {"AAPL": p_us, "005930": p_kr}
        returns_df, valid_symbols = UnifiedPortfolioAllocator.compute_returns_matrix(
            symbols=["AAPL", "005930"],
            prices_dict=prices_dict,
            fx_series=fx_series,
            base_currency="KRW"
        )
        assert len(valid_symbols) == 2
        # For a KRW investor, AAPL return must reflect the USD/KRW appreciation (+10%)
        # while 005930 return has 0 price change
        aapl_total_return = (1.0 + returns_df["AAPL"]).prod() - 1.0
        kr_total_return = (1.0 + returns_df["005930"]).prod() - 1.0
        assert aapl_total_return > 0.08
        assert abs(kr_total_return) < 0.001

    def test_allocate_black_litterman_convenience(self):
        """Verify allocate_black_litterman returns valid shares, lots, and weights."""
        allocator = UnifiedPortfolioAllocator()
        symbols = ["005930", "AAPL"]
        dates = pd.date_range("2026-01-01", periods=30)
        prices = {
            "005930": pd.DataFrame({"Close": np.linspace(70000, 72000, 30)}, index=dates),
            "AAPL": pd.DataFrame({"Close": np.linspace(200, 210, 30)}, index=dates),
        }
        pred_rets = {"005930": 12.0, "AAPL": 15.0}
        res = allocator.allocate_black_litterman(
            prices_dict=prices,
            predicted_returns=pred_rets,
            total_portfolio_value=100_000_000.0
        )
        assert not res.empty
        assert "weight" in res.columns
        assert "shares" in res.columns

    def test_bull_conviction_kelly_scaling(self):
        """Verify that high-conviction expected Sharpe in BULL_LOW_VOL triggers 100% allocation scaling."""
        allocator = UnifiedPortfolioAllocator(target_volatility=0.12)
        weights = np.array([0.50, 0.50])
        # Very low portfolio volatility (8% annualized)
        cov = np.eye(2) * (0.08 / np.sqrt(252.0)) ** 2
        # High expected return (20%)
        exp_rets = np.array([0.20, 0.20])

        w_scaled, alloc = allocator.apply_target_volatility_scaling(
            weights=weights,
            cov_matrix=cov,
            regime="BULL_LOW_VOL",
            expected_returns=exp_rets
        )
        assert alloc >= 0.98


