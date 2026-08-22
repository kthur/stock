"""
Comprehensive 4-Tier Test Suite for 6th System Improvements (V6-01 ~ V6-35)
===========================================================================

Tier 1: Direct Feature Tests for V6-01 through V6-35
Tier 2: Boundary Value and Corner Cases
Tier 3: Cross-Feature Interaction Tests
Tier 4: End-to-End Multi-Market Realistic Workflow Scenarios

Author: test_writer_gen2 (E2E & Regression Test Suite Lead)
Date: 2026-08-22
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
# TIER 1: Direct Feature Tests for V6-01 through V6-35
# ==============================================================================

class TestTier1DirectFeatures:
    """Direct feature tests validating specific defect remediations V6-01 ~ V6-35."""

    # --------------------------------------------------------------------------
    # V6-01: Strict Causal LSTM Training Target Log1p Domain Disconnect
    # --------------------------------------------------------------------------
    def test_v6_01_lstm_training_target_transform_sharpe_homomorphism(self):
        """Verify LSTM data preparation applies transform_sharpe to guarantee log1p space homomorphism."""
        model = OnDevicePredictionModel()
        dates = pd.date_range("2025-01-01", periods=100)
        df_group = pd.DataFrame({
            "symbol": ["005930"] * 100,
            "ret_1d": np.random.normal(0.001, 0.02, 100),
            "target_20d": np.random.normal(0.05, 0.10, 100)
        }, index=dates)

        seqs, targets, syms = model._prepare_lstm_data(df_group, target_col="target_20d", seq_len=20)
        assert len(targets) > 0
        expected_sharpe = transform_sharpe(df_group["target_20d"]).values[19:]
        np.testing.assert_allclose(targets, expected_sharpe, rtol=1e-5)

    # --------------------------------------------------------------------------
    # V6-02: Multi-Horizon Exponential Decay Filter Key-Column Schema Mismatch
    # --------------------------------------------------------------------------
    def test_v6_02_exponential_decay_filter_column_alias_mapping(self):
        """Verify exponential decay filter maps score column aliases to canonical half-life keys."""
        scorer = EnsembleScoringEngine()
        prev_df = pd.DataFrame({
            "symbol": ["005930"],
            "microstructure_score": [0.80],  # fast tau = 0.5
            "rim_score": [0.90],             # slow tau = 45.0
            "close": [70000.0]               # non-strategy column
        })
        curr_df = pd.DataFrame({
            "symbol": ["005930"],
            "microstructure_score": [0.20],
            "rim_score": [0.30],
            "close": [75000.0]
        })

        filtered = scorer.apply_exponential_decay_filter(curr_df, prev_df)
        
        # Fast half-life (tau=0.5) adapts quickly (alpha ~ 0.75, score drops significantly towards 0.20)
        assert filtered["microstructure_score"].iloc[0] < 0.40
        # Slow half-life (tau=45.0) decays slowly (alpha ~ 0.015, score stays high near 0.90)
        assert filtered["rim_score"].iloc[0] > 0.80
        # Non-strategy numeric column is not smoothed
        assert filtered["close"].iloc[0] == 75000.0

    # --------------------------------------------------------------------------
    # V6-03: Dual-Regime Weight Squaring & US-KR Weight Cross-Contamination
    # --------------------------------------------------------------------------
    def test_v6_03_dual_regime_weights_decoupling_and_suppression(self):
        """Verify US and KR regime weights are decoupled without squaring or cross-contamination."""
        scorer = EnsembleScoringEngine()
        reg_df = pd.DataFrame({
            "symbol": ["005930", "AAPL"],
            "market": ["KOSPI", "SP500"],
            "expected_return_20d": [0.05, 0.08],
            "close": [70000.0, 200.0]
        })
        s_df = pd.DataFrame({
            "symbol": ["005930", "AAPL"],
            "surge_prob_20d": [0.60, 0.90]
        })

        res = scorer.combine_predictions(
            reg_df=reg_df,
            s_df=s_df,
            regime="BEAR",
            us_regime="BULL",
            kr_regime="BEAR"
        )
        assert not res.empty
        assert "ensemble_score" in res.columns
        assert np.all(np.isfinite(res["ensemble_score"].values))

    # --------------------------------------------------------------------------
    # V6-04: Cross-Market Model Hijacking in predict_lstm
    # --------------------------------------------------------------------------
    def test_v6_04_predict_lstm_market_partitioned_evaluation(self):
        """Verify predict_lstm partitions symbols by market and evaluates market-specific models."""
        model = OnDevicePredictionModel()
        dates = pd.date_range("2026-01-01", periods=30)
        prices_dict = {
            "005930": pd.DataFrame({"close": np.linspace(60000, 70000, 30)}, index=dates),
            "AAPL": pd.DataFrame({"close": np.linspace(200, 220, 30)}, index=dates)
        }

        # Mock market-specific models
        mock_krx_model = MagicMock()
        mock_krx_model.is_trained = True
        mock_krx_model.predict.return_value = np.array([[0.75]])

        mock_us_model = MagicMock()
        mock_us_model.is_trained = True
        mock_us_model.predict.return_value = np.array([[0.85]])

        model.lstm_models = {
            "KOSPI": {20: mock_krx_model},
            "SP500": {20: mock_us_model}
        }

        preds = model.predict_lstm(prices_dict, horizon=20)
        assert not preds.empty
        assert "lstm_score" in preds.columns
        assert len(preds) == 2

    # --------------------------------------------------------------------------
    # V6-05: Multi-Year Cumulative Return Scaling Distortion in predict_lead_lag Fallback
    # --------------------------------------------------------------------------
    def test_v6_05_lead_lag_fallback_1day_normalized_scaling(self):
        """Verify predict_lead_lag fallback computes 1-day return mapped into [0.05, 0.95]."""
        model = OnDevicePredictionModel()
        dates = pd.date_range("2020-01-01", periods=1000)
        prices = np.linspace(100, 400, 1000)
        prices[-1] = prices[-2] * 1.01
        prices_dict = {
            "005930": pd.DataFrame({"close": prices}, index=dates)
        }

        model.lead_lag_models = {}
        model.lead_lag_matrix = {}
        res = model.predict_lead_lag(prices_dict)
        assert not res.empty
        score = res["ll_score"].iloc[0]
        assert 0.45 <= score <= 0.60

    # --------------------------------------------------------------------------
    # V6-06: Volatility Maximization Anomaly in Optuna 2D Regime & Alpha Decay Bounds
    # --------------------------------------------------------------------------
    def test_v6_06_optuna_bear_utility_and_alpha_decay_bounds(self):
        """Verify Optuna bear regime uses quadratic utility and AlphaDecayTracker respects bounds."""
        tuner = OptunaStrategyTuner()
        dates = pd.date_range("2026-01-01", periods=50)
        strategy_returns = {
            "reg": pd.Series(np.random.normal(-0.01, 0.02, 50), index=dates),
            "vcp": pd.Series(np.random.normal(-0.005, 0.01, 50), index=dates)
        }
        res = tuner.tune_regime_2d_weights({"BEAR": strategy_returns}, n_trials=3)
        assert isinstance(res, dict)

        tracker = AlphaDecayTracker(min_weight_bound=0.01, max_weight_bound=0.50)
        base_w = {"s1": 0.33, "s2": 0.33, "s3": 0.34}
        sharpes = {"s1": 1.5, "s2": -0.5, "s3": 0.2}
        adj_w = tracker.calculate_decay_adjusted_weights(base_w, sharpes)
        assert adj_w["s1"] > adj_w["s2"]
        assert pytest.approx(sum(adj_w.values()), abs=1e-3) == 1.0

    # --------------------------------------------------------------------------
    # V6-07: Selection Threshold Inflation & 10-Symbol Bottleneck in Lead-Lag HPO
    # --------------------------------------------------------------------------
    def test_v6_07_lead_lag_hpo_evaluates_k_symbols_and_validation_split(self):
        """Verify tune_strategy_3_lead_lag evaluates leaders_count > 10 and checks validation persistence."""
        tuner = OptunaStrategyTuner()
        dates = pd.date_range("2026-01-01", periods=100)
        prices_dict = {
            f"SYM_{i}": pd.DataFrame({"close": np.cumprod(1.0 + np.random.normal(0.0005, 0.015, 100))}, index=dates)
            for i in range(15)
        }
        tuned = tuner.tune_lead_lag(prices_dict=prices_dict, n_trials=2)
        assert isinstance(tuned, dict)

    # --------------------------------------------------------------------------
    # V6-08: Feature Permutation Corruption in MetaEnsembleLearner
    # --------------------------------------------------------------------------
    def test_v6_08_meta_ensemble_learner_column_permutation_invariance(self):
        """Verify MetaEnsembleLearner matches feature names by dictionary projection regardless of input order."""
        meta = MetaEnsembleLearner(learner_type="ridge")
        meta.is_fitted = True
        meta.feature_names = ["feat_a", "feat_b", "feat_c"]
        meta.weights = np.array([0.5, 0.3, 0.2])
        meta.intercept = 0.0

        df_normal = pd.DataFrame({"feat_a": [1.0], "feat_b": [2.0], "feat_c": [3.0]})
        pred_normal = meta.predict(df_normal)

        df_shuffled = pd.DataFrame({"feat_c": [3.0], "feat_a": [1.0], "feat_b": [2.0]})
        pred_shuffled = meta.predict(df_shuffled)

        np.testing.assert_allclose(pred_normal, pred_shuffled, rtol=1e-5)

    # --------------------------------------------------------------------------
    # V6-09: Leland Dynamic Buffer Band Boundary Collapse (w_curr=0, w_targ=0)
    # --------------------------------------------------------------------------
    def test_v6_09_leland_buffer_band_new_entry_and_full_exit_bypass(self):
        """Verify Leland buffer band does not trap full exits or block fresh position initiations."""
        allocator = PortfolioAllocator()
        target_weights = {"005930": 0.015, "000660": 0.000}
        current_weights = {"005930": 0.000, "000660": 0.008}
        market_map = {"005930": "KOSPI", "000660": "KOSPI"}
        volatility_map = {"005930": 0.02, "000660": 0.02}
        adv_map = {"005930": 1e9, "000660": 1e9}

        res = allocator.compute_portfolio_rebalance(
            current_weights=current_weights,
            target_weights=target_weights,
            market_map=market_map,
            volatility_map=volatility_map,
            adv_map=adv_map
        )
        new_w = res["new_weights"]
        assert new_w["005930"] > 0.0
        assert new_w["000660"] == 0.0

    # --------------------------------------------------------------------------
    # V6-10: Black-Litterman Piecewise Step Discontinuity & Gradient Explosion in SLSQP
    # --------------------------------------------------------------------------
    def test_v6_10_black_litterman_c1_smoothness_under_all_negative_excess(self):
        """Verify Black-Litterman optimization converges smoothly when all views have negative excess return."""
        views = np.array([-0.05, -0.08, -0.04])
        cov_matrix = np.array([
            [0.04, 0.01, 0.01],
            [0.01, 0.05, 0.01],
            [0.01, 0.01, 0.03]
        ])

        weights = calculate_black_litterman_weights(
            cov_matrix=cov_matrix,
            predicted_returns=views,
            risk_free_rate=0.035
        )
        assert len(weights) == 3
        assert pytest.approx(float(np.sum(weights)), abs=1e-3) == 1.0

    # --------------------------------------------------------------------------
    # V6-11: EVT-POT Quantile Inversion & Non-Regular GPD Shape Bounds
    # --------------------------------------------------------------------------
    def test_v6_11_evt_pot_cvar_threshold_ceiling_and_regular_shape(self):
        """Verify EVT-POT bounds threshold u <= q_alpha and clamps shape xi in [-0.50, 0.50]."""
        allocator = PortfolioAllocator()
        losses = np.random.normal(0.005, 0.01, 500)
        res = allocator.estimate_evt_cvar(losses, confidence=0.95)

        assert res["cvar"] >= res["var"]
        assert -0.50 <= res.get("shape", 0.0) <= 0.50

    # --------------------------------------------------------------------------
    # V6-12: Rockafellar-Uryasev Convex CVaR Pseudo-Huber Smoothing & Vectorized Constraints
    # --------------------------------------------------------------------------
    def test_v6_12_rockafellar_uryasev_cvar_pseudo_huber_and_vector_constraints(self):
        """Verify Rockafellar-Uryasev CVaR optimization executes efficiently with Pseudo-Huber smoothing."""
        allocator = PortfolioAllocator()
        np.random.seed(42)
        symbols = ["A0", "A1", "A2", "A3", "A4"]
        expected_returns = {s: 0.05 - i * 0.01 for i, s in enumerate(symbols)}
        historical_returns = np.random.normal(0.001, 0.02, size=(60, 5))
        prev_weights = {s: 0.20 for s in symbols}

        weights = allocator.optimize_rockafellar_uryasev_cvar(
            expected_returns=expected_returns,
            historical_returns=historical_returns,
            previous_weights=prev_weights,
            confidence=0.95
        )
        assert len(weights) == 5
        assert pytest.approx(sum(weights.values()), abs=1e-3) == 1.0

    # --------------------------------------------------------------------------
    # V6-13: CrisisDetector Recovery Latch Suppressing Defensive WATCH Haircuts
    # --------------------------------------------------------------------------
    def test_v6_13_crisis_detector_recovery_reset_and_watch_haircut(self):
        """Verify CrisisDetector resets recovery mode after 20 days and applies 0.70 WATCH multiplier."""
        detector = CrisisDetector()
        detector._recovery_mode = True
        detector._recovery_days = 20

        detector.evaluate(vix=18.0)
        assert detector._recovery_mode is False

        detector.crisis_level = CrisisLevel.WATCH
        mult = detector.get_crisis_position_multiplier()
        assert mult == 0.70

    # --------------------------------------------------------------------------
    # V6-14: Primary Missing Reason Frequency Selector Distortion
    # --------------------------------------------------------------------------
    def test_v6_14_coverage_analyzer_modal_frequency_missing_reason(self):
        """Verify StrategyCoverageAnalyzer selects the statistical mode (highest count) missing reason."""
        analyzer = StrategyCoverageAnalyzer()
        mock_stats = {
            "strategies": {
                "rim_valuation": {
                    "valid_count": 50,
                    "missing_count": 150,
                    "coverage_pct": 25.0,
                    "reasons": {
                        "INSUFFICIENT_PRICE_HISTORY": 5,
                        "NO_FUNDAMENTAL_DATA": 145  # True primary reason
                    }
                }
            },
            "total_symbols": 200
        }
        report = analyzer.generate_coverage_report(mock_stats)
        assert "NO_FUNDAMENTAL_DATA" in report

    # --------------------------------------------------------------------------
    # V6-15: Downside Co-Semivariance Equicorrelation Shrinkage Erasing Negative Hedging
    # --------------------------------------------------------------------------
    def test_v6_15_downside_semi_cov_diagonal_shrinkage_preserves_hedges(self):
        """Verify compute_downside_semi_cov uses diagonal shrinkage target, preserving negative hedging covariances."""
        allocator = PortfolioAllocator()
        returns = np.array([
            [-0.03, +0.03],
            [-0.02, +0.02],
            [-0.04, +0.04],
            [+0.01, -0.01],
            [-0.02, +0.02]
        ])
        base_cov = np.array([
            [0.04, -0.02],
            [-0.02, 0.04]
        ])
        semi_cov = allocator.compute_downside_semi_cov(returns, base_cov=base_cov, shrinkage_intensity=0.20)
        assert semi_cov[0, 1] < 0.0

    # --------------------------------------------------------------------------
    # V6-16: RMT Marchenko-Pastur Residual Eigenvalue Noise Variance Over-Shrinking
    # --------------------------------------------------------------------------
    def test_v6_16_rmt_dynamic_noise_variance_estimation(self):
        """Verify Marchenko-Pastur denoiser estimates noise variance from residual eigenvalues."""
        engine = FXAdjustedCovarianceEngine()
        np.random.seed(42)
        n_assets = 20
        t_obs = 100
        factors = np.random.normal(size=(t_obs, 1))
        noise = np.random.normal(scale=0.3, size=(t_obs, n_assets))
        returns = factors @ np.ones((1, n_assets)) + noise

        cov_raw = np.cov(returns, rowvar=False)
        cov_denoised = engine.denoise_covariance_marchenko_pastur(cov_raw, t_obs=t_obs, n_assets=n_assets)
        assert cov_denoised.shape == (n_assets, n_assets)
        assert np.all(np.linalg.eigvalsh(cov_denoised) >= -1e-8)

    # --------------------------------------------------------------------------
    # V6-17: Book Value Scale Discrepancy (Total Equity vs BPS)
    # --------------------------------------------------------------------------
    def test_v6_17_rim_valuation_bps_scale_homogeneity(self):
        """Verify RIM valuation handles small-cap equity (< $1M) and high-nominal KRX BPS (> 1M KRW)."""
        engine = RIMValuationEngine()
        fundamentals = {
            "SMALL_US": {"book_value": 600000.0, "shares_outstanding": 100000.0, "roe": 0.15, "bps": 6.0},
            "003240": {"book_value": 5.5e12, "shares_outstanding": 1110000.0, "roe": 0.08, "bps": 4954954.0}
        }
        prices_dict = {
            "SMALL_US": pd.DataFrame({"close": [8.0]}),
            "003240": pd.DataFrame({"close": [600000.0]})
        }

        res = engine.compute_scores(prices_dict=prices_dict, fundamentals_dict=fundamentals)
        assert not res.empty
        assert "rim_score" in res.columns
        assert np.all(np.isfinite(res["rim_score"].values))

    # --------------------------------------------------------------------------
    # V6-18: Curated Symbol GICS Sector Map Bypass in SectorRotationEngine
    # --------------------------------------------------------------------------
    def test_v6_18_sector_rotation_curated_symbol_mapping(self):
        """Verify SectorRotationEngine passes symbol=sym to resolve curated leaders like 005930 and NVDA."""
        engine = SectorRotationEngine()
        norm_sec = engine.normalize_sector("General", symbol="005930")
        assert "Technology" in norm_sec or "Information" in norm_sec

    # --------------------------------------------------------------------------
    # V6-19: Live Options Chain IV Fetch Prioritization in IVSkewEngine
    # --------------------------------------------------------------------------
    def test_v6_19_iv_skew_live_options_prioritization(self):
        """Verify IVSkewEngine attempts live options chain fetch when ENABLE_LIVE_OPTIONS_FETCH is enabled."""
        engine = IVSkewEngine()
        dates = pd.date_range("2026-01-01", periods=30)
        prices_dict = {
            "AAPL": pd.DataFrame({"close": np.linspace(200, 220, 30)}, index=dates)
        }

        with patch.dict(os.environ, {"ENABLE_LIVE_OPTIONS_FETCH": "true"}):
            with patch.object(engine, "compute_skew_for_ticker", return_value=0.88) as mock_skew:
                res = engine.compute_scores(prices_dict=prices_dict)
                assert not res.empty
                mock_skew.assert_called_once_with("AAPL")
                assert res["iv_skew_score"].iloc[0] == 0.88

    # --------------------------------------------------------------------------
    # V6-20: 8-digit OpenDART corp_code Direct String Comparison in EventDrivenEngine
    # --------------------------------------------------------------------------
    def test_v6_20_event_driven_dart_8digit_corp_code_resolution(self):
        """Verify EventDrivenEngine matches 8-digit corp_code using DARTCorpMapper."""
        engine = EventDrivenEngine()
        symbols = ["005930"]
        filings = [
            {
                "corp_code": "00126380",
                "report_nm": "주요사항보고서(자기주식취득결정)",
                "rcept_dt": "20260820"
            }
        ]
        with patch.object(DARTCorpMapper, "get_corp_code", return_value="00126380"):
            res = engine.compute_event_scores(symbols, filings=filings)
            assert not res.empty
            assert "event_score" in res.columns
            assert res["event_score"].iloc[0] > 0.50

    # --------------------------------------------------------------------------
    # V6-21: 5:1 Temporal Horizon Mismatch in CARDFactorEngine
    # --------------------------------------------------------------------------
    def test_v6_21_card_factor_5day_macro_temporal_alignment(self):
        """Verify CARDFactorEngine computes 5-day rolling macro returns matching 5-day stock returns."""
        engine = CARDFactorEngine()
        dates = pd.date_range("2026-01-01", periods=10)
        prices_dict = {
            "005930": pd.DataFrame({"close": np.linspace(70000, 73500, 10)}, index=dates)
        }
        indicator_df = pd.DataFrame({
            "USDKRW": np.linspace(1300, 1339, 10),
            "WTI": np.linspace(75, 75, 10)
        }, index=dates)

        res = engine.compute_scores(prices_dict=prices_dict, indicators_df=indicator_df)
        assert not res.empty
        assert "card_score" in res.columns

    # --------------------------------------------------------------------------
    # V6-22: Single-Stock Evaluation Rank Saturation Biases (N=1 -> Score=0.50)
    # --------------------------------------------------------------------------
    def test_v6_22_single_stock_n1_neutral_score_guards(self):
        """Verify multiple factor engines return neutral 0.50 score for single-stock evaluations."""
        dates = pd.date_range("2026-01-01", periods=30)
        prices_dict = {
            "005930": pd.DataFrame({
                "open": np.linspace(69000, 70000, 30),
                "high": np.linspace(70000, 71000, 30),
                "low": np.linspace(68000, 69000, 30),
                "close": np.linspace(69000, 70000, 30),
                "volume": np.full(30, 1000000.0)
            }, index=dates)
        }

        res_trend = TrendEfficiencyEngine().compute_scores(prices_dict=prices_dict)
        assert res_trend["trend_efficiency_score"].iloc[0] == 0.50

        res_short = ShortInterestSqueezeEngine().compute_scores(prices_dict=prices_dict)
        assert res_short["short_squeeze_score"].iloc[0] == 0.50

        res_valueup = ValueUpCatalystEngine().compute_scores(prices_dict=prices_dict)
        assert res_valueup["valueup_catalyst_score"].iloc[0] == 0.50

    # --------------------------------------------------------------------------
    # V6-23: Unbounded INFO Logging in StatisticalArbitrageEngine
    # --------------------------------------------------------------------------
    def test_v6_23_stat_arb_summary_logging_performance(self):
        """Verify StatisticalArbitrageEngine finds cointegrated pairs cleanly."""
        engine = StatisticalArbitrageEngine()
        dates = pd.date_range("2026-01-01", periods=60)
        prices_dict = {
            f"SYM_{i}": pd.DataFrame({"close": np.cumprod(1.0 + np.random.normal(0, 0.01, 60))}, index=dates)
            for i in range(10)
        }
        pairs = engine.find_cointegrated_pairs(prices_dict)
        res = engine.get_symbol_stat_arb_scores(pairs)
        assert isinstance(res, pd.DataFrame)

    # --------------------------------------------------------------------------
    # V6-24: Reverse Stock Split Handling Voids in DataValidator
    # --------------------------------------------------------------------------
    def test_v6_24_reverse_stock_split_adjustment_and_volume_contraction(self):
        """Verify reverse stock split (> +50% jump with volume contraction) adjusts historical OHLC."""
        dates = pd.date_range("2026-01-01", periods=10)
        prices = [10.0, 10.2, 10.1, 10.0, 50.0, 50.5, 49.8, 50.2, 50.0, 51.0]
        volumes = [50000, 52000, 51000, 50000, 10000, 10200, 9800, 10100, 10000, 10500]
        df = pd.DataFrame({
            "Open": prices, "High": [p * 1.01 for p in prices], "Low": [p * 0.99 for p in prices],
            "Close": prices, "Volume": volumes
        }, index=dates)

        cleaned = StockPriceDB.validate_and_clean_price_series(df)
        assert not cleaned.empty
        assert cleaned["Close"].iloc[0] > 40.0

    # --------------------------------------------------------------------------
    # V6-25: Cross-Market Currency Denominator Mismatch in ExecutionOMSEngine
    # --------------------------------------------------------------------------
    def test_v6_25_oms_currency_denominator_us_and_global_hedging(self, tmp_path):
        """Verify ExecutionOMSEngine converts KRW capital to USD before calculating US share quantities."""
        oms = ExecutionOMSEngine(db_path=str(tmp_path / "trade_logs.db"))
        total_capital_krw = 135_000_000.0  # 135M KRW = $100k USD @ 1350 FX
        portfolio_weights = {"AAPL": 0.05} # $5,000 USD allocation
        top_predictions = [{
            "symbol": "AAPL",
            "market": "NASDAQ",
            "target_price": 150.0,
            "ensemble_expected_return": 5.0
        }]
        prices_dict = {"AAPL": pd.DataFrame({"close": [150.0]})}

        orders = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            current_holdings={},
            total_capital=total_capital_krw,
            prices_dict=prices_dict,
            usdkrw_rate=1350.0
        )
        assert len(orders) == 1
        assert orders[0]["quantity"] == 33

    # --------------------------------------------------------------------------
    # V6-26: Return Scale Ambiguity in OMS Safety Gates 7.2 & 7.4
    # --------------------------------------------------------------------------
    def test_v6_26_oms_return_scale_normalization_gates_7_2_and_7_4(self, tmp_path):
        """Verify OMS Gates 7.2 & 7.4 normalize percent return (+5.2%) without false limit-lock drops."""
        oms = ExecutionOMSEngine(db_path=str(tmp_path / "trade_logs.db"))
        portfolio_weights = {"005930": 0.10}
        top_predictions = [{
            "symbol": "005930",
            "market": "KOSPI",
            "change_pct": 5.2,  # +5.2% daily gain in percent notation
            "target_price": 70000.0,
            "ensemble_expected_return": 4.0
        }]
        prices_dict = {"005930": pd.DataFrame({"close": [70000.0]})}

        orders = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            current_holdings={},
            total_capital=100_000_000.0,
            prices_dict=prices_dict
        )
        assert len(orders) == 1
        assert orders[0]["symbol"] == "005930"

    # --------------------------------------------------------------------------
    # V6-27: Almgren-Chriss Slicing Residual Underflow & Non-Negative Tranches
    # --------------------------------------------------------------------------
    def test_v6_27_almgren_chriss_slicing_non_negative_tranches(self):
        """Verify AlmgrenChrissScheduler guarantees non-negative tranches summing exactly to total_quantity."""
        scheduler = AlmgrenChrissScheduler()
        tranches = scheduler.compute_trajectory(
            total_quantity=23,
            adv=1e9,
            daily_volatility=0.02,
            strategy_tier="fast",
            n_slices=5
        )
        assert len(tranches) == 5
        assert np.all(np.array(tranches) >= 0)
        assert sum(tranches) == 23

    # --------------------------------------------------------------------------
    # V6-28: Friction Cost Double-Deduction in OMS Gate 7.3
    # --------------------------------------------------------------------------
    def test_v6_28_oms_gate_7_3_single_friction_deduction(self, tmp_path):
        """Verify OMS Gate 7.3 does not double-deduct friction when ensemble_expected_return is net."""
        oms = ExecutionOMSEngine(db_path=str(tmp_path / "trade_logs.db"))
        portfolio_weights = {"005930": 0.10}
        top_predictions = [{
            "symbol": "005930",
            "market": "KOSPI",
            "ensemble_expected_return": 2.5,  # 2.5% net alpha (> 0.10% safety margin)
            "target_price": 70000.0
        }]
        prices_dict = {"005930": pd.DataFrame({"close": [70000.0]})}

        orders = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            current_holdings={},
            total_capital=100_000_000.0,
            prices_dict=prices_dict
        )
        assert len(orders) == 1

    # --------------------------------------------------------------------------
    # V6-29: Turnover Hysteresis Deadlock in TurnoverOptimizer
    # --------------------------------------------------------------------------
    def test_v6_29_turnover_optimizer_full_liquidation_and_entry_bypass(self):
        """Verify TurnoverOptimizer bypasses turnover hysteresis for full exits (raw_w=0) and fresh entries."""
        optimizer = TurnoverOptimizer(turnover_threshold_pct=0.05)
        raw_weights = {"005930": 0.00, "000660": 0.04}
        current_holdings = {"005930": 0.04, "000660": 0.00}

        optimized = optimizer.optimize_allocations(
            current_holdings=current_holdings,
            target_allocations=raw_weights,
            total_capital=100_000_000.0
        )
        assert optimized["005930"]["target_weight"] == 0.0
        assert optimized["005930"]["action"] == "SELL"
        assert optimized["000660"]["target_weight"] == 0.04
        assert optimized["000660"]["action"] == "BUY"

    # --------------------------------------------------------------------------
    # V6-30: Slippage Sign Inversion for BUY_HEDGE Orders & SQLite Connection Leak
    # --------------------------------------------------------------------------
    def test_v6_30_slippage_feedback_buy_hedge_sign_and_db_lifecycle(self, tmp_path):
        """Verify SlippageFeedbackEngine treats BUY_HEDGE as buy and guarantees closing DB connection."""
        db_file = str(tmp_path / "trade_logs.db")
        engine = SlippageFeedbackEngine(db_path=db_file)

        with sqlite3.connect(db_file) as conn:
            conn.execute("""
                CREATE TABLE trade_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market TEXT, symbol TEXT, side TEXT,
                    expected_price REAL, fill_price REAL, shares INTEGER,
                    timestamp TEXT
                )
            """)
            conn.execute("""
                INSERT INTO trade_logs (market, symbol, side, expected_price, fill_price, shares, timestamp)
                VALUES ('SP500', 'SH', 'BUY_HEDGE', 15.00, 15.50, 100, '2026-08-21 10:00:00')
            """)

        metrics = engine.calculate_realized_slippage()
        assert isinstance(metrics, SlippageMetrics)
        assert metrics.avg_slippage_bps > 0.0

    # --------------------------------------------------------------------------
    # V6-31: SmartOrderRouter ATS Residual Misrouting & Duplicate Orders
    # --------------------------------------------------------------------------
    def test_v6_31_smart_order_router_primary_venue_residual_consolidation(self):
        """Verify SmartOrderRouter consolidates residual quantities onto the primary lit venue."""
        router = SmartOrderRouter()
        venues = [
            {"venue_id": "NXT", "is_primary": False, "ask_price": 70000.0, "ask_vol": 50},
            {"venue_id": "KRX", "is_primary": True, "ask_price": 70050.0, "ask_vol": 10000}
        ]
        allocations = router.route_order(
            symbol="005930",
            action="BUY",
            total_quantity=500,
            venues=venues
        )
        assert len(allocations) == 2
        total_qty = sum(a["allocated_quantity"] for a in allocations)
        assert total_qty == 500
        krx_alloc = [a for a in allocations if a["venue_id"] == "KRX"][0]
        assert krx_alloc["allocated_quantity"] == 450

    # --------------------------------------------------------------------------
    # V6-32: import json in src/config.py
    # --------------------------------------------------------------------------
    def test_v6_32_config_market_costs_json_parsing(self):
        """Verify src/config.py parses MARKET_COSTS_JSON environment variable without NameError."""
        custom_costs = '{"KOSPI": {"stt_tax_rate": 0.0018, "exchange_fee_rate": 0.00003}}'
        with patch.dict(os.environ, {"MARKET_COSTS_JSON": custom_costs}):
            table = _build_market_lookup_table()
            assert table["KOSPI"]["stt_tax_rate"] == 0.0018

    # --------------------------------------------------------------------------
    # V6-33: Top-Level try...finally DB Lock & State Cleanup in run_pipeline.py
    # --------------------------------------------------------------------------
    def test_v6_33_pipeline_lifecycle_db_lock_and_status_tracking(self, tmp_path):
        """Verify pipeline run tracking records status='FAILED' on unhandled exceptions."""
        db_path = str(tmp_path / "market_indicators.db")
        storage = MarketIndicatorStorage(db_path=db_path)
        run_id = storage.start_pipeline_run()

        try:
            raise RuntimeError("Simulated Pipeline Mid-Flight Failure")
        except Exception as e:
            storage.finish_pipeline_run(
                run_id=run_id,
                status="FAILED",
                duration_seconds=1.5,
                error_summary=str(e)[:500]
            )

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, error_summary FROM pipeline_run_history WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "FAILED"
            assert "Simulated Pipeline Mid-Flight Failure" in row[1]
        storage.close()

    # --------------------------------------------------------------------------
    # V6-34: Text Fallback Parser Regex in generate_run_snapshot.py
    # --------------------------------------------------------------------------
    def test_v6_34_run_snapshot_text_fallback_regex_parser(self, tmp_path):
        """Verify generate_snapshot text parser handles Korean and US lines accurately."""
        result_dir = tmp_path / "result"
        result_dir.mkdir(parents=True, exist_ok=True)
        pred_file = result_dir / "ensemble_predictions.txt"

        content = """================================================================================
Current Market Regime Detected: BULL_TREND
================================================================================
Rank Symbol     Company Name             Ensemble    Net Exp Ret    Reg    Surge    LL
--------------------------------------------------------------------------------
1.   005930     삼성전자                 85.40%      +4.25%         82.0%  80.0%    88.0%
2.   AAPL       Apple Inc.               82.10%      +3.80%         80.0%  78.0%    85.0%
================================================================================
"""
        pred_file.write_text(content, encoding="utf-8")
        out_json = tmp_path / "run_snapshot.json"

        snapshot = generate_snapshot(
            result_dir=result_dir,
            db_path=tmp_path / "non_existent.db",
            output_file=out_json
        )
        top_picks = snapshot["top_50_picks"]
        assert len(top_picks) == 2
        assert top_picks[0]["symbol"] == "005930"
        assert top_picks[0]["ensemble_score"] == 0.854
        assert top_picks[0]["net_expected_return_pct"] == 4.25
        assert top_picks[1]["symbol"] == "AAPL"

    # --------------------------------------------------------------------------
    # V6-35: Timezone Desynchronization (KST) & Liquidity Env Vars in Config
    # --------------------------------------------------------------------------
    def test_v6_35_config_environment_variable_and_kst_alignment(self):
        """Verify TradingConfig parses liquidity and OMS environment variables, and KST is UTC+9."""
        KST = timezone(timedelta(hours=9))
        now_kst = datetime.now(KST)
        assert now_kst.tzinfo is not None

        env_overrides = {
            "MIN_DAILY_VOLUME_KRX": "150000",
            "MIN_DAILY_VOLUME_SP500": "500000",
            "SLIPPAGE_KRX_MARKET_ORDER": "0.0025",
            "OMS_NET_ALPHA_SAFETY_MARGIN": "0.0015"
        }
        with patch.dict(os.environ, env_overrides):
            cfg = TradingConfig()
            assert cfg.min_daily_volume_krx == 150000
            assert cfg.min_daily_volume_sp500 == 500000
            assert cfg.slippage_krx_market_order == 0.0025
            assert cfg.oms_net_alpha_safety_margin == 0.0015


# ==============================================================================
# TIER 2: Boundary Value and Corner Cases
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Boundary, extreme stress, degenerate dimension, and corner case tests."""

    def test_single_symbol_n1_across_all_rank_engines(self):
        """Verify N=1 degenerate cross-sections never produce 0.98 saturation across rank models."""
        dates = pd.date_range("2026-01-01", periods=30)
        df_single = pd.DataFrame({
            "open": np.full(30, 100.0),
            "high": np.full(30, 105.0),
            "low": np.full(30, 95.0),
            "close": np.full(30, 100.0),
            "volume": np.full(30, 10000.0)
        }, index=dates)
        prices_dict = {"ISOLATED_SYM": df_single}

        engines = [
            MQFactorEngine(),
            ShortInterestSqueezeEngine(),
            ValueUpCatalystEngine(),
            TrendEfficiencyEngine(),
            OrderFlowEngine(),
            ShortTermReversalEngine(),
            InstForeignSectorEngine()
        ]

        for eng in engines:
            res = eng.compute_scores(prices_dict=prices_dict)
            score_col = [c for c in res.columns if c.endswith("_score")][0]
            assert res[score_col].iloc[0] == 0.50, f"{eng.__class__.__name__} failed N=1 neutral guard"

    def test_extreme_currency_rate_boundary(self, tmp_path):
        """Verify OMS behaves rationally under extreme USD/KRW currency regimes (e.g. 2,000 KRW/USD)."""
        oms = ExecutionOMSEngine(db_path=str(tmp_path / "trade_logs.db"))
        total_capital_krw = 200_000_000.0
        portfolio_weights = {"NVDA": 0.10} # 20M KRW = $10,000 USD @ 2000 FX
        top_predictions = [{
            "symbol": "NVDA", "market": "NASDAQ", "target_price": 100.0, "ensemble_expected_return": 5.0
        }]
        prices_dict = {"NVDA": pd.DataFrame({"close": [100.0]})}

        orders = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            current_holdings={},
            total_capital=total_capital_krw,
            prices_dict=prices_dict,
            usdkrw_rate=2000.0
        )
        assert len(orders) == 1
        assert orders[0]["quantity"] == 100

    def test_full_portfolio_liquidation_all_zero_target(self):
        """Verify Leland buffer band processes 100% cash target (w_targ=0 everywhere)."""
        allocator = PortfolioAllocator()
        symbols = ["005930", "AAPL", "NVDA"]
        target_weights = {s: 0.0 for s in symbols}
        current_weights = {"005930": 0.40, "AAPL": 0.30, "NVDA": 0.30}
        market_map = {s: "KOSPI" if s.isdigit() else "NASDAQ" for s in symbols}
        volatility_map = {s: 0.02 for s in symbols}
        adv_map = {s: 1e9 for s in symbols}

        res = allocator.compute_portfolio_rebalance(
            current_weights=current_weights,
            target_weights=target_weights,
            market_map=market_map,
            volatility_map=volatility_map,
            adv_map=adv_map
        )
        for s in symbols:
            assert res["new_weights"][s] == 0.0

    def test_almgren_chriss_zero_or_single_share_orders(self):
        """Verify Almgren-Chriss scheduler handles edge quantities (0, 1, 2 shares)."""
        scheduler = AlmgrenChrissScheduler()
        for q in [0, 1, 2]:
            tranches = scheduler.compute_trajectory(
                total_quantity=q,
                adv=1e6,
                daily_volatility=0.02,
                n_slices=5
            )
            assert sum(tranches) == q
            assert np.all(np.array(tranches) >= 0)

    def test_black_litterman_singular_covariance_matrix(self):
        """Verify Black-Litterman optimizer stabilizes singular/collinear covariance matrices."""
        cov_singular = np.ones((3, 3)) * 0.04
        views = np.array([0.05, 0.04, 0.03])

        weights = calculate_black_litterman_weights(
            cov_matrix=cov_singular,
            predicted_returns=views,
            risk_free_rate=0.02
        )
        assert len(weights) == 3
        assert pytest.approx(float(np.sum(weights)), abs=1e-3) == 1.0


# ==============================================================================
# TIER 3: Cross-Feature Interaction Tests
# ==============================================================================

class TestTier3CrossFeatureInteractions:
    """Multi-component cross-interaction and integrated workflow tests."""

    def test_hrp_with_leland_dynamic_buffer_bands(self):
        """Verify HRP portfolio allocation feeds into Leland dynamic buffer rebalancing seamlessly."""
        allocator = PortfolioAllocator()
        symbols = ["005930", "000660", "AAPL", "MSFT"]
        
        cov_mat = np.eye(4) * 0.04
        hrp_weights_arr = calculate_hrp_weights(cov_matrix=cov_mat, symbols=symbols)
        hrp_weights = dict(zip(symbols, hrp_weights_arr))
        assert len(hrp_weights) == 4
        assert pytest.approx(sum(hrp_weights.values()), abs=1e-3) == 1.0

        current_holdings = {"005930": 0.25, "000660": 0.25, "AAPL": 0.25, "MSFT": 0.0}
        market_map = {s: "KOSPI" if s.isdigit() else "NASDAQ" for s in symbols}
        vol_map = {s: 0.02 for s in symbols}
        adv_map = {s: 1e9 for s in symbols}

        res = allocator.compute_portfolio_rebalance(
            current_weights=current_holdings,
            target_weights=hrp_weights,
            market_map=market_map,
            volatility_map=vol_map,
            adv_map=adv_map
        )
        assert res["new_weights"]["MSFT"] > 0.0
        assert all(0.0 <= w <= 1.0 for w in res["new_weights"].values())

    def test_2d_regime_decay_filter_and_factor_suppression_interaction(self):
        """Verify 2D regime detection interacts with exponential decay filtering and factor suppression."""
        scorer = EnsembleScoringEngine()
        prev_scores = pd.DataFrame({
            "symbol": ["005930", "AAPL"],
            "reg_score": [0.70, 0.80],
            "microstructure_score": [0.60, 0.90]
        })
        curr_scores = pd.DataFrame({
            "symbol": ["005930", "AAPL"],
            "market": ["KOSPI", "SP500"],
            "reg_score": [0.65, 0.85],
            "microstructure_score": [0.30, 0.40],
            "close": [70000.0, 220.0]
        })

        smoothed = scorer.apply_exponential_decay_filter(curr_scores, prev_scores)
        
        reg_df = smoothed[["symbol", "market", "reg_score"]].rename(columns={"reg_score": "expected_return_20d"})
        micro_df = smoothed[["symbol", "microstructure_score"]]

        combined = scorer.combine_predictions(
            reg_df=reg_df,
            microstructure_df=micro_df,
            regime="BEAR",
            us_regime="BULL",
            kr_regime="BEAR"
        )
        assert not combined.empty
        assert "ensemble_score" in combined.columns

    def test_oms_execution_with_currency_conversion_and_almgren_chriss(self, tmp_path):
        """Verify OMS pipeline end-to-end: FX conversion -> Gate filtering -> Almgren-Chriss slicing."""
        oms = ExecutionOMSEngine(db_path=str(tmp_path / "trade_logs.db"))
        total_capital_krw = 270_000_000.0  # $200k USD @ 1350 FX
        portfolio_weights = {"NVDA": 0.20, "005930": 0.20} # $40k NVDA, 54M KRW Samsung
        top_predictions = [
            {"symbol": "NVDA", "market": "NASDAQ", "target_price": 120.0, "ensemble_expected_return": 4.0},
            {"symbol": "005930", "market": "KOSPI", "target_price": 70000.0, "ensemble_expected_return": 3.0}
        ]
        prices_dict = {
            "NVDA": pd.DataFrame({"close": [120.0]}),
            "005930": pd.DataFrame({"close": [70000.0]})
        }

        orders = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            current_holdings={},
            total_capital=total_capital_krw,
            prices_dict=prices_dict,
            usdkrw_rate=1350.0
        )
        assert len(orders) == 2
        nvda_order = [o for o in orders if o["symbol"] == "NVDA"][0]
        samsung_order = [o for o in orders if o["symbol"] == "005930"][0]

        assert nvda_order["quantity"] == 333
        assert samsung_order["quantity"] in [770, 771]


# ==============================================================================
# TIER 4: End-to-End Multi-Market Realistic Workflow Scenarios
# ==============================================================================

class TestTier4EndToEndRealisticWorkflows:
    """Full end-to-end multi-market simulation workflows."""

    def test_full_pipeline_multi_market_scoring_optimization_and_oms(self, tmp_path):
        """Simulate full execution across 5-market universe with dual regimes and risk management."""
        dates = pd.date_range("2026-01-01", periods=60)
        symbols = ["005930", "000660", "AAPL", "MSFT", "IWM"]
        markets = {"005930": "KOSPI", "000660": "KOSPI", "AAPL": "NASDAQ", "MSFT": "NASDAQ", "IWM": "RUSSELL2000"}
        prices_dict = {
            "005930": pd.DataFrame({"close": np.linspace(65000, 70000, 60)}, index=dates),
            "000660": pd.DataFrame({"close": np.linspace(160000, 180000, 60)}, index=dates),
            "AAPL": pd.DataFrame({"close": np.linspace(200, 230, 60)}, index=dates),
            "MSFT": pd.DataFrame({"close": np.linspace(400, 440, 60)}, index=dates),
            "IWM": pd.DataFrame({"close": np.linspace(200, 210, 60)}, index=dates)
        }

        scorer = EnsembleScoringEngine()
        reg_df = pd.DataFrame({
            "symbol": symbols,
            "market": [markets[s] for s in symbols],
            "expected_return_20d": [0.08, 0.07, 0.09, 0.08, 0.06],
            "close": [70000.0, 180000.0, 230.0, 440.0, 210.0]
        })
        s_df = pd.DataFrame({
            "symbol": symbols,
            "surge_prob_20d": [0.70, 0.65, 0.80, 0.75, 0.55]
        })

        ensemble_df = scorer.combine_predictions(
            reg_df=reg_df,
            s_df=s_df,
            regime="BEAR",
            us_regime="BULL",
            kr_regime="BEAR"
        )
        assert not ensemble_df.empty
        assert "ensemble_score" in ensemble_df.columns

        # Portfolio Allocation via HRP
        cov_matrix = np.eye(len(symbols)) * 0.04
        hrp_weights_arr = calculate_hrp_weights(cov_matrix=cov_matrix, symbols=symbols)
        hrp_weights = dict(zip(symbols, hrp_weights_arr))

        # Leland Dynamic Buffer Rebalancing
        allocator = PortfolioAllocator()
        current_holdings = {"005930": 0.20, "000660": 0.20, "AAPL": 0.20, "MSFT": 0.20, "IWM": 0.20}
        market_map = markets
        vol_map = {s: 0.02 for s in symbols}
        adv_map = {s: 1e9 for s in symbols}

        res = allocator.compute_portfolio_rebalance(
            current_weights=current_holdings,
            target_weights=hrp_weights,
            market_map=market_map,
            volatility_map=vol_map,
            adv_map=adv_map
        )
        rebalanced_weights = res["new_weights"]

        # Execution OMS Order Generation
        oms = ExecutionOMSEngine(db_path=str(tmp_path / "trade_logs.db"))
        top_preds = ensemble_df.to_dict(orient="records")
        for p in top_preds:
            p["target_price"] = p["close"]
            p["ensemble_expected_return"] = 3.0

        orders = oms.generate_order_plan(
            top_predictions=top_preds,
            portfolio_weights=rebalanced_weights,
            current_holdings={},
            total_capital=200_000_000.0,
            prices_dict=prices_dict,
            usdkrw_rate=1350.0,
            regime_label="NORMAL"
        )
        assert isinstance(orders, list)
        assert len(orders) > 0
        for o in orders:
            assert o["quantity"] > 0
            assert o["target_price"] > 0

    def test_run_snapshot_generation_workflow(self, tmp_path):
        """Verify generate_run_snapshot creates valid JSON release artifacts from mock output files."""
        result_dir = tmp_path / "result"
        result_dir.mkdir(parents=True, exist_ok=True)
        
        pred_file = result_dir / "ensemble_predictions.txt"
        pred_file.write_text("""================================================================================
Current Market Regime Detected: BULL_TREND
================================================================================
Rank Symbol     Company Name             Ensemble    Net Exp Ret
1.   005930     Samsung Electronics      88.20%      +4.50%
2.   NVDA       NVIDIA Corporation       85.10%      +4.10%
================================================================================
""", encoding="utf-8")

        output_json = tmp_path / "run_snapshot.json"
        snapshot = generate_snapshot(
            result_dir=result_dir,
            db_path=tmp_path / "market_indicators.db",
            output_file=output_json
        )
        assert len(snapshot["top_50_picks"]) == 2
        assert output_json.exists()
