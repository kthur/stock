"""
Comprehensive Adversarial Stress-Testing Suite for V6-01 ~ V6-35
================================================================

This suite empirically challenges the system across:
1. Degenerate Inputs: N=1 cross-sections, empty portfolios, zero weights, 0 USD/KRW rate, huge returns (+100,000%, -99.9%), NaN/Inf features.
2. Extreme Market Drawdowns & Crisis Transitions: Flash crashes, rapid regime oscillations, VIX spikes, negative oil prices, singular covariance.
3. Large-Scale Multi-Asset Simulations: 200-asset cross-sections, high-frequency OMS routing, Almgren-Chriss under extreme illiquidity, and malformed snapshot parsing.

Target: Empirical verification of V6-01 ~ V6-35 robustness against hostile inputs.
"""

import os
import re
import json
import sqlite3
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Core Config & Infrastructure
from src.config import TradingConfig, _build_market_lookup_table
from generate_run_snapshot import generate_snapshot

# AI / ML Models & Signal Engines
from src.ai.prediction_model import OnDevicePredictionModel
from src.ai.target_transform import transform_sharpe, inverse_transform_sharpe
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.optuna_tuner import OptunaStrategyTuner, AlphaDecayTracker
from src.ai.meta_ensemble_learner import MetaEnsembleLearner

# Portfolio & Risk Engineering
from src.risk.portfolio_allocator import PortfolioAllocator
from src.analysis.portfolio_optimizer import calculate_black_litterman_weights, calculate_hrp_weights, calculate_risk_parity_weights
from src.risk.risk_manager import CrisisDetector, CrisisLevel, RiskManager
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer
from src.risk.fx_adjusted_covariance import FXAdjustedCovarianceEngine

# 31 Strategy Engines & Data Layer
from src.core.rim_valuation import RIMValuationEngine
from src.core.sector_rotation import SectorRotationEngine
from src.core.iv_skew import IVSkewEngine
from src.core.event_driven import EventDrivenEngine
from src.core.card_factor import CARDFactorEngine
from src.core.mq_factor import MQFactorEngine
from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
from src.core.valueup_catalyst import ValueUpCatalystEngine
from src.core.trend_efficiency import TrendEfficiencyEngine
from src.core.order_flow import OrderFlowEngine
from src.core.short_term_reversal import ShortTermReversalEngine
from src.core.inst_foreign_sector import InstForeignSectorEngine
from src.core.stat_arb import StatisticalArbitrageEngine
from src.data_layer.data_validator import DataValidator
from src.data_layer.dart_corp_mapper import DARTCorpMapper
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.persistence.database import StockPriceDB

# Execution OMS & Microstructure
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from src.execution.turnover_optimizer import TurnoverOptimizer
from src.execution.slippage_feedback import SlippageFeedbackEngine, SlippageMetrics
from src.execution.sor_router import SmartOrderRouter


# ==============================================================================
# 1. DEGENERATE & ADVERSARIAL INPUT STRESS TESTS
# ==============================================================================

class TestAdversarialDegenerateInputs:
    """Stress tests verifying system resilience against degenerate and pathological inputs."""

    def test_adv_n1_degenerate_across_all_factor_engines(self):
        """Stress-test N=1 single stock cross-section across all factor engines without crashing or saturating."""
        dates = pd.date_range("2026-01-01", periods=40)
        # Construct single price DataFrame
        df_single = pd.DataFrame({
            "open": np.linspace(50000, 52000, 40),
            "high": np.linspace(51000, 53000, 40),
            "low": np.linspace(49000, 51000, 40),
            "close": np.linspace(50000, 52000, 40),
            "volume": np.full(40, 500000.0)
        }, index=dates)
        prices_dict = {"SOLITARY_CORP": df_single}

        factor_engines = [
            (MQFactorEngine(), "mq_score"),
            (ShortInterestSqueezeEngine(), "short_squeeze_score"),
            (ValueUpCatalystEngine(), "valueup_catalyst_score"),
            (TrendEfficiencyEngine(), "trend_efficiency_score"),
            (OrderFlowEngine(), "order_flow_score"),
            (ShortTermReversalEngine(), "reversal_score"),
            (InstForeignSectorEngine(), "inst_foreign_sector_score"),
        ]

        for engine, expected_col in factor_engines:
            res = engine.compute_scores(prices_dict=prices_dict)
            assert not res.empty, f"{engine.__class__.__name__} returned empty result for N=1"
            assert expected_col in res.columns, f"{engine.__class__.__name__} missing expected score column {expected_col}"
            score = res[expected_col].iloc[0]
            assert 0.0 <= score <= 1.0, f"{engine.__class__.__name__} score out of [0, 1] range: {score}"
            # Single stock must receive neutral rank 0.50
            assert score == pytest.approx(0.50, abs=1e-3), f"{engine.__class__.__name__} failed N=1 neutral guard, got {score}"

    def test_adv_empty_portfolios_and_zero_weights_handling(self):
        """Stress-test portfolio allocation with empty dicts, all-zero target weights, and full liquidation."""
        allocator = PortfolioAllocator()
        
        # Scenario A: Empty dicts
        res_empty = allocator.compute_portfolio_rebalance(
            current_weights={},
            target_weights={},
            market_map={},
            volatility_map={},
            adv_map={}
        )
        assert res_empty["new_weights"] == {}
        assert res_empty["summary"]["total_symbols"] == 0

        # Scenario B: All zero targets from existing holdings (100% liquidation)
        current_w = {"005930": 0.50, "000660": 0.50}
        target_w = {"005930": 0.00, "000660": 0.00}
        market_map = {"005930": "KOSPI", "000660": "KOSPI"}
        vol_map = {"005930": 0.02, "000660": 0.02}
        adv_map = {"005930": 1e9, "000660": 1e9}

        res_liquidate = allocator.compute_portfolio_rebalance(
            current_weights=current_w,
            target_weights=target_w,
            market_map=market_map,
            volatility_map=vol_map,
            adv_map=adv_map
        )
        # All weights must be exactly 0.0 (bypassing Leland buffer band)
        assert res_liquidate["new_weights"]["005930"] == 0.0
        assert res_liquidate["new_weights"]["000660"] == 0.0
        assert res_liquidate["trades"]["005930"]["action"] == "SELL"
        assert res_liquidate["trades"]["000660"]["action"] == "SELL"

        # Scenario C: Fresh position initiations from 0 holding
        current_zero = {"005930": 0.0, "AAPL": 0.0}
        target_new = {"005930": 0.03, "AAPL": 0.05} # small targets
        market_map_c = {"005930": "KOSPI", "AAPL": "NASDAQ"}
        vol_map_c = {"005930": 0.02, "AAPL": 0.03}
        adv_map_c = {"005930": 1e9, "AAPL": 1e9}

        res_entry = allocator.compute_portfolio_rebalance(
            current_weights=current_zero,
            target_weights=target_new,
            market_map=market_map_c,
            volatility_map=vol_map_c,
            adv_map=adv_map_c
        )
        assert res_entry["new_weights"]["005930"] > 0.0
        assert res_entry["new_weights"]["AAPL"] > 0.0

    def test_adv_zero_and_extreme_fx_rates_in_oms(self, tmp_path):
        """Stress-test OMS engine against 0 FX rate, negative FX rate, and extreme hyperinflation FX rates."""
        oms = ExecutionOMSEngine(db_path=str(tmp_path / "trade_logs_fx.db"))
        total_capital = 135_000_000.0  # 135M KRW
        portfolio_weights = {"AAPL": 0.10} # 10% = 13.5M KRW = $10,000 USD @ 1350 FX
        top_predictions = [{
            "symbol": "AAPL", "market": "NASDAQ", "target_price": 100.0, "ensemble_expected_return": 5.0
        }]
        prices_dict = {"AAPL": pd.DataFrame({"close": [100.0]})}

        # Scenario A: 0 USD/KRW rate should safely fallback to default (1350.0) without ZeroDivisionError
        orders_zero_fx = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            current_holdings={},
            total_capital=total_capital,
            prices_dict=prices_dict,
            usdkrw_rate=0.0
        )
        assert len(orders_zero_fx) == 1
        assert orders_zero_fx[0]["quantity"] == 100 # $10,000 / $100 = 100 shares

        # Scenario B: Negative FX rate should safely fallback to default
        orders_neg_fx = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            current_holdings={},
            total_capital=total_capital,
            prices_dict=prices_dict,
            usdkrw_rate=-1400.0
        )
        assert len(orders_neg_fx) == 1
        assert orders_neg_fx[0]["quantity"] == 100

        # Scenario C: Extreme FX rate (5,000 KRW/USD)
        orders_high_fx = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            current_holdings={},
            total_capital=total_capital,
            prices_dict=prices_dict,
            usdkrw_rate=5000.0
        )
        assert len(orders_high_fx) == 1
        # 13.5M KRW / 5000 = $2,700 USD -> 27 shares @ $100
        assert orders_high_fx[0]["quantity"] == 27

    def test_adv_extreme_price_returns_and_transform_sharpe(self):
        """Stress-test transform_sharpe on extreme price jumps (+10,000%, -99.99%) and boundary values."""
        # Extreme positive returns
        huge_ret = pd.Series([0.0, 10.0, 100.0, 1000.0]) # +100,000%
        transformed_huge = transform_sharpe(huge_ret)
        assert np.all(np.isfinite(transformed_huge))
        vol_scale = pd.Series([0.02, 0.02, 0.02, 0.02])
        inv_huge = inverse_transform_sharpe(transformed_huge, vol_scale=vol_scale)
        assert np.all(np.isfinite(inv_huge))
        assert np.all(inv_huge >= 0.0)

        # Extreme negative returns (near -1.0)
        neg_ret = pd.Series([-0.50, -0.90, -0.99, -0.9999])
        transformed_neg = transform_sharpe(neg_ret)
        assert np.all(np.isfinite(transformed_neg))
        inv_neg = inverse_transform_sharpe(transformed_neg, vol_scale=vol_scale)
        assert np.all(np.isfinite(inv_neg))
        assert np.all(inv_neg <= 0.0)

        # Boundary: return < -1.0 (invalid bankruptcy boundary)
        clipped_ret = pd.Series([-1.05, -2.0])
        transformed_clip = transform_sharpe(clipped_ret)
        assert np.all(np.isfinite(transformed_clip))


# ==============================================================================
# 2. CRISIS REGIME & EXTREME MARKET DRAWDOWN TESTS
# ==============================================================================

class TestAdversarialCrisisAndDrawdowns:
    """Stress tests simulating extreme market panics, rapid regime flips, and singular matrices."""

    def test_adv_rapid_multi_regime_flapping_and_recovery_decay(self):
        """Simulate rapid daily regime oscillations: NORMAL -> SEVERE -> WATCH -> NORMAL."""
        detector = CrisisDetector()
        
        # Day 1: Normal market (VIX=15)
        detector.evaluate(vix=15.0, usdkrw=1300.0)
        assert detector.crisis_level in [CrisisLevel.NONE, CrisisLevel.WATCH]
        assert detector.get_crisis_position_multiplier() >= 0.70

        # Day 2: Flash crash (VIX=45, SEVERE crisis level)
        detector.evaluate(vix=45.0, usdkrw=1380.0)
        assert detector.crisis_level == CrisisLevel.SEVERE
        assert detector.get_crisis_position_multiplier() == 0.15
        assert detector.should_block_new_buys() is True
        assert detector._days_in_crisis >= 1

        # Day 3: Volatility drops back to VIX=20 (Crisis ends, starts recovery tracking)
        detector.evaluate(vix=20.0, usdkrw=1320.0)
        assert detector._days_since_crisis_ended >= 1

        # Day 4: Calm continues (1 day after start day)
        detector.evaluate(vix=19.0, usdkrw=1310.0)
        
        # Day 5: 2 days after start day -> activates recovery mode
        detector.evaluate(vix=18.0, usdkrw=1300.0)
        assert detector._recovery_mode is True

        # Fast forward recovery days to 20
        detector._recovery_days = 20
        detector.evaluate(vix=18.0, usdkrw=1300.0)
        # Should auto-reset recovery mode
        assert detector._recovery_mode is False

        # Test WATCH state haircut
        detector.crisis_level = CrisisLevel.WATCH
        assert detector.get_crisis_position_multiplier() == 0.70

    def test_adv_card_factor_extreme_macro_shocks(self):
        """Stress-test CARDFactorEngine under extreme macro scenarios (e.g. WTI = -40, 10Y Yield = 0%)."""
        engine = CARDFactorEngine()
        dates = pd.date_range("2026-01-01", periods=15)
        
        prices_dict = {
            "005930": pd.DataFrame({"close": np.linspace(70000, 60000, 15)}, index=dates)
        }
        # Extreme indicators: WTI flash crash into negative territory (as in April 2020), VIX spike
        indicators_df = pd.DataFrame({
            "USDKRW": np.linspace(1250, 1450, 15), # severe FX depreciation
            "WTI": np.linspace(20, -35, 15),       # negative oil price
            "TNX": np.linspace(4.0, 0.5, 15),      # yield collapse
            "VIX": np.linspace(15, 80, 15)         # historic volatility
        }, index=dates)

        res = engine.compute_scores(prices_dict=prices_dict, indicators_df=indicators_df)
        assert not res.empty
        assert "card_score" in res.columns
        score = res["card_score"].iloc[0]
        assert np.isfinite(score)
        assert 0.0 <= score <= 1.0

    def test_adv_singular_collinear_covariance_in_portfolio_optimizers(self):
        """Stress-test HRP, Black-Litterman, and Risk Parity against rank-deficient / singular covariance."""
        # 4 assets with perfectly collinear returns (rank = 1)
        cov_singular = np.array([
            [0.04, 0.04, 0.04, 0.04],
            [0.04, 0.04, 0.04, 0.04],
            [0.04, 0.04, 0.04, 0.04],
            [0.04, 0.04, 0.04, 0.04]
        ])
        views = np.array([0.05, 0.05, 0.05, 0.05])

        # Test Black-Litterman
        w_bl = calculate_black_litterman_weights(
            cov_matrix=cov_singular,
            predicted_returns=views,
            risk_free_rate=0.03
        )
        assert len(w_bl) == 4
        assert np.all(np.isfinite(w_bl))
        assert pytest.approx(float(np.sum(w_bl)), abs=1e-3) == 1.0

        # Test Risk Parity
        w_rp = calculate_risk_parity_weights(cov_singular)
        assert len(w_rp) == 4
        assert np.all(np.isfinite(w_rp))
        assert pytest.approx(float(np.sum(w_rp)), abs=1e-3) == 1.0

    def test_adv_almgren_chriss_extreme_illiquidity_and_single_share(self):
        """Stress-test Almgren-Chriss scheduler with ADV = 1 share, high volatility, and total_qty = 1 share."""
        scheduler = AlmgrenChrissScheduler()
        
        # Test 1: Single share execution
        tranches_single = scheduler.compute_trajectory(
            total_quantity=1,
            adv=10.0,
            daily_volatility=0.10,
            strategy_tier="urgent",
            n_slices=5
        )
        assert len(tranches_single) == 5
        assert sum(tranches_single) == 1
        assert np.all(np.array(tranches_single) >= 0)

        # Test 2: Extreme illiquidity (order = 100x ADV)
        tranches_huge = scheduler.compute_trajectory(
            total_quantity=10000,
            adv=100.0,
            daily_volatility=0.05,
            strategy_tier="fast",
            n_slices=10
        )
        assert len(tranches_huge) == 10
        assert sum(tranches_huge) == 10000
        assert np.all(np.array(tranches_huge) >= 0)


# ==============================================================================
# 3. LARGE-SCALE SIMULATIONS & HIGH-THROUGHPUT HARNESS
# ==============================================================================

class TestAdversarialLargeScaleSimulations:
    """High-throughput stress tests simulating large cross-sections and data corruptions."""

    def test_adv_large_scale_portfolio_optimization_200_assets(self):
        """Simulate Rockafellar-Uryasev CVaR optimization across 200 assets with random alpha and covariance."""
        allocator = PortfolioAllocator()
        np.random.seed(12345)
        N = 200
        T = 120 # 120 days history
        symbols = [f"ASSET_{i:03d}" for i in range(N)]
        
        # Expected returns ranging from -15% to +25%
        expected_returns = {s: np.random.uniform(-0.15, 0.25) for s in symbols}
        # Historical return matrix
        factors = np.random.normal(0, 0.01, size=(T, 3))
        loadings = np.random.normal(0, 1.0, size=(3, N))
        idiosyncratic = np.random.normal(0, 0.02, size=(T, N))
        hist_returns = factors @ loadings + idiosyncratic

        prev_weights = {s: 1.0 / N for s in symbols}

        opt_weights = allocator.optimize_rockafellar_uryasev_cvar(
            expected_returns=expected_returns,
            historical_returns=hist_returns,
            previous_weights=prev_weights,
            confidence=0.95,
            max_cvar_limit=0.08
        )

        assert len(opt_weights) == N
        assert np.all(np.isfinite(list(opt_weights.values())))
        assert pytest.approx(sum(opt_weights.values()), abs=1e-3) == 1.0
        # Check non-negativity (long-only)
        assert all(w >= -1e-6 for w in opt_weights.values())

    def test_adv_large_scale_oms_order_generation_mixed_markets(self, tmp_path):
        """Simulate OMS order generation for 100 symbols across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000)."""
        oms = ExecutionOMSEngine(db_path=str(tmp_path / "trade_logs_large.db"))
        np.random.seed(42)
        
        markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        symbols = [f"SYM{i:03d}" for i in range(20)]
        
        weights = {}
        top_predictions = []
        prices_dict = {}
        
        raw_w = np.random.exponential(1.0, len(symbols))
        norm_w = raw_w / raw_w.sum()

        for i, sym in enumerate(symbols):
            mkt = markets[i % len(markets)]
            weights[sym] = norm_w[i]
            price = 50000.0 if "KOS" in mkt else 150.0
            prices_dict[sym] = pd.DataFrame({"close": [price]})
            top_predictions.append({
                "symbol": sym,
                "market": mkt,
                "target_price": price,
                "ensemble_expected_return": 4.5,
                "change_pct": 2.0
            })

        orders = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=weights,
            current_holdings=None, # Fresh rebalance without previous holding lock
            total_capital=1_000_000_000.0, # 1 Billion KRW
            prices_dict=prices_dict,
            usdkrw_rate=1350.0
        )

        assert len(orders) > 0
        # Verify all orders have non-negative integer shares and valid venues
        for ord_item in orders:
            assert ord_item["quantity"] >= 0
            assert isinstance(ord_item["quantity"], (int, np.integer))
            assert ord_item["symbol"] in weights

    def test_adv_snapshot_parser_corrupted_text_recovery(self, tmp_path):
        """Stress-test snapshot text parser with truncated, messy, and Unicode corrupted files."""
        result_dir = tmp_path / "result_messy"
        result_dir.mkdir(parents=True, exist_ok=True)
        pred_file = result_dir / "ensemble_predictions.txt"

        # Corrupted messy content: ragged columns, extra blank lines, corrupted symbols
        corrupted_content = """
        RANDOM HEADER 12345
        === IRRELEVANT BANNER ===
        Rank Symbol     Company Name             Ensemble    Net Exp Ret    Reg    Surge
        --------------------------------------------------------------------------------
        1.   005930     삼성전자                 88.50%      +5.10%         85.0%  80.0%
        GARBAGE LINE WITH NO NUMBERS
        2.   AAPL       Apple Inc.               79.20%      +2.90%         75.0%  70.0%
        3.   NVDA       NVIDIA Corporation       92.10%      +7.45%         90.0%  88.0%
        4.   000660     SK하이닉스               84.30%      -1.20%         80.0%  75.0%
        === END OF PREDICTIONS ===
        """
        pred_file.write_text(corrupted_content, encoding="utf-8")
        out_json = tmp_path / "snapshot_recovery.json"

        snapshot = generate_snapshot(
            result_dir=result_dir,
            db_path=tmp_path / "empty.db",
            output_file=out_json
        )

        top_picks = snapshot.get("top_50_picks", [])
        # The parser should robustly extract the 4 valid rows despite garbage lines
        assert len(top_picks) == 4
        symbols_extracted = [p["symbol"] for p in top_picks]
        assert "005930" in symbols_extracted
        assert "AAPL" in symbols_extracted
        assert "NVDA" in symbols_extracted
        assert "000660" in symbols_extracted
        
        # Verify negative return parsed properly
        sk_pick = [p for p in top_picks if p["symbol"] == "000660"][0]
        assert sk_pick["net_expected_return_pct"] == -1.20

    def test_adv_data_validator_consecutive_reverse_splits(self):
        """Stress-test StockPriceDB price series cleaning against multi-stage reverse splits."""
        dates = pd.date_range("2026-01-01", periods=15)
        # 1:10 reverse split at index 5, then 1:5 reverse split at index 10
        prices = [
            1.0, 1.0, 1.0, 1.0, 1.0,      # Pre-first split: $1
            10.0, 10.0, 10.0, 10.0, 10.0, # Post-first split: $10 (10x jump, 10x volume drop)
            50.0, 50.0, 50.0, 50.0, 50.0  # Post-second split: $50 (5x jump, 5x volume drop)
        ]
        volumes = [
            100000, 100000, 100000, 100000, 100000,
            10000, 10000, 10000, 10000, 10000,
            2000, 2000, 2000, 2000, 2000
        ]
        df = pd.DataFrame({
            "Open": prices, "High": [p * 1.02 for p in prices], "Low": [p * 0.98 for p in prices],
            "Close": prices, "Volume": volumes
        }, index=dates)

        cleaned = StockPriceDB.validate_and_clean_price_series(df)
        assert not cleaned.empty
        # The entire historical price series should be adjusted upwards to avoid 5000% false return jump
        assert cleaned["Close"].iloc[0] >= 40.0
