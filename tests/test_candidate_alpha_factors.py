"""Tests for Candidate Alpha Factor Engines (Phase 197 / Release R186+).

Covers:
1. StealthAccumulationEngine (SM-01)
2. VPINToxicityEngine (MF-01)
3. MacroStressSpilloverEngine (AD-04)
4. SUESURDecayEngine (FM-01)
5. SentimentDivergenceEngine (SM-05)
6. FCFVelocityEngine (FM-02)
7. Integration with AlphaStrategyExecutor and EnsembleScoringEngine
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.core.stealth_accumulation import StealthAccumulationEngine
from src.core.vpin_toxicity import VPINToxicityEngine
from src.core.macro_stress_spillover import MacroStressSpilloverEngine
from src.core.sue_sur_decay import SUESURDecayEngine
from src.core.sentiment_divergence import SentimentDivergenceEngine
from src.core.fcf_velocity import FCFVelocityEngine
from src.pipeline.strategy_executor import AlphaStrategyExecutor
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.backtest.historical_stock_universe_backtester import (
    HistoricalStockUniverseBacktester,
    CANONICAL_37_COLUMNS,
    CANONICAL_38_COLUMNS,
    CANONICAL_44_COLUMNS,
    STRATEGY_TO_COL_MAP,
    COL_TO_STRATEGY_MAP,
)


def _generate_synthetic_ohlcv(days: int = 60, seed: int = 42, drift: float = 0.001) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.normal(drift, 0.02, days)
    prices = 100.0 * np.exp(np.cumsum(returns))
    highs = prices * (1.0 + np.abs(rng.normal(0, 0.008, days)))
    lows = prices * (1.0 - np.abs(rng.normal(0, 0.008, days)))
    opens = prices * (1.0 + rng.normal(0, 0.004, days))
    volumes = rng.integers(100_000, 2_000_000, days).astype(float)
    dates = pd.date_range("2025-01-01", periods=days, freq="B")
    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": volumes,
    }, index=dates)


class TestStealthAccumulationEngine:
    def test_basic_scoring_and_bounds(self):
        engine = StealthAccumulationEngine()
        prices_dict = {
            "AAPL": _generate_synthetic_ohlcv(50, seed=1),
            "MSFT": _generate_synthetic_ohlcv(50, seed=2),
            "GOOG": _generate_synthetic_ohlcv(50, seed=3),
        }
        df = engine.compute_scores(prices_dict)
        assert not df.empty
        assert "stealth_accumulation_score" in df.columns
        for score in df["stealth_accumulation_score"].dropna():
            assert 0.05 <= score <= 0.95

    def test_short_history_and_zero_volume_fallback(self):
        engine = StealthAccumulationEngine()
        short_df = _generate_synthetic_ohlcv(3, seed=10)
        zero_vol_df = _generate_synthetic_ohlcv(50, seed=11)
        zero_vol_df["volume"] = 0.0
        
        prices_dict = {
            "SHORT": short_df,
            "ZERO_VOL": zero_vol_df,
        }
        df = engine.compute_scores(prices_dict)
        assert len(df) == 2
        short_score = df.loc[df["symbol"] == "SHORT", "stealth_accumulation_score"].iloc[0]
        zero_score = df.loc[df["symbol"] == "ZERO_VOL", "stealth_accumulation_score"].iloc[0]
        assert abs(short_score - 0.50) < 1e-4
        assert 0.05 <= zero_score <= 0.95


class TestVPINToxicityEngine:
    def test_basic_scoring_and_bounds(self):
        engine = VPINToxicityEngine()
        prices_dict = {
            "AAPL": _generate_synthetic_ohlcv(60, seed=21),
            "NVDA": _generate_synthetic_ohlcv(60, seed=22),
        }
        df = engine.compute_scores(prices_dict)
        assert not df.empty
        assert "vpin_toxicity_score" in df.columns
        for score in df["vpin_toxicity_score"].dropna():
            assert 0.05 <= score <= 0.95

    def test_adverse_selection_penalty(self):
        engine = VPINToxicityEngine(vpin_threshold_z=1.0, toxicity_penalty=0.20)
        # Create high volatility flash selloff
        df_crash = _generate_synthetic_ohlcv(60, seed=30)
        # Inject crash bars
        df_crash.loc[df_crash.index[-10:], "close"] *= 0.70
        df_crash.loc[df_crash.index[-10:], "volume"] *= 10.0
        
        prices_dict = {"CRASH": df_crash}
        df = engine.compute_scores(prices_dict)
        assert not df.empty
        score = df.loc[df["symbol"] == "CRASH", "vpin_toxicity_score"].iloc[0]
        assert 0.05 <= score <= 0.95


class TestMacroStressSpilloverEngine:
    def test_calm_vs_stress_differentiation(self):
        engine = MacroStressSpilloverEngine()
        days = 80
        dates = pd.date_range("2025-01-01", periods=days, freq="B")
        prices_dict = {
            "SPY": _generate_synthetic_ohlcv(days, seed=41),
            "VULNERABLE": _generate_synthetic_ohlcv(days, seed=42),
        }
        # Invert returns of VULNERABLE during market drops
        indicators_df = pd.DataFrame({
            "VIX": np.linspace(15.0, 45.0, days),
            "MOVE": np.linspace(80.0, 160.0, days),
            "HY_SPREAD": np.linspace(300.0, 700.0, days),
        }, index=dates)

        df = engine.compute_scores(prices_dict, indicators_df=indicators_df)
        assert not df.empty
        assert "macro_stress_spillover_score" in df.columns
        for score in df["macro_stress_spillover_score"].dropna():
            assert 0.05 <= score <= 0.95

    def test_missing_indicators_fallback(self):
        engine = MacroStressSpilloverEngine()
        prices_dict = {"STOCK": _generate_synthetic_ohlcv(40, seed=45)}
        df = engine.compute_scores(prices_dict, indicators_df=None)
        assert not df.empty
        score = df["macro_stress_spillover_score"].iloc[0]
        assert 0.05 <= score <= 0.95


class TestSUESURDecayEngine:
    def test_multi_quarter_decay_kernel(self):
        engine = SUESURDecayEngine()
        prices_dict = {"AAPL": _generate_synthetic_ohlcv(40, seed=51)}
        fundamentals_dict = {
            "AAPL": {
                "sue_history": [1.5, 1.2, 0.8, 0.5],
                "sur_history": [0.08, 0.05, 0.03, 0.01],
                "sue_quarters_ago": [0, 1, 2, 3],
            }
        }
        df = engine.compute_scores(prices_dict, fundamentals_dict=fundamentals_dict)
        assert not df.empty
        score = df.loc[df["symbol"] == "AAPL", "sue_sur_decay_score"].iloc[0]
        assert 0.05 <= score <= 0.95
        # Positive SUE/SUR history should yield score > 0.50
        assert score > 0.50

    def test_missing_fundamentals_neutral_baseline(self):
        engine = SUESURDecayEngine()
        prices_dict = {"UNKNOWN": _generate_synthetic_ohlcv(40, seed=52)}
        df = engine.compute_scores(prices_dict, fundamentals_dict={})
        assert not df.empty
        score = df.loc[df["symbol"] == "UNKNOWN", "sue_sur_decay_score"].iloc[0]
        assert abs(score - 0.50) < 1e-4


class TestSentimentDivergenceEngine:
    def test_contrarian_signals(self):
        engine = SentimentDivergenceEngine()
        df_euphoria = _generate_synthetic_ohlcv(50, seed=61, drift=0.005)
        prices_dict = {"BULL": df_euphoria}
        # Retail euphoria: high retail buying, overbought
        fundamentals_dict = {
            "BULL": {
                "inst_flow_z": -1.5,
                "retail_flow_z": 2.5,
            }
        }
        df = engine.compute_scores(prices_dict, fundamentals_dict=fundamentals_dict)
        assert not df.empty
        score = df.loc[df["symbol"] == "BULL", "sentiment_divergence_score"].iloc[0]
        assert 0.05 <= score <= 0.95
        # Retail euphoria + institutional selling should give bearish divergence (score < 0.50)
        assert score < 0.50

    def test_panic_capitulation_bullish_divergence(self):
        engine = SentimentDivergenceEngine()
        df_panic = _generate_synthetic_ohlcv(50, seed=62, drift=-0.005)
        prices_dict = {"PANIC": df_panic}
        # Institutional buying, retail panic selling
        fundamentals_dict = {
            "PANIC": {
                "inst_flow_z": 2.0,
                "retail_flow_z": -2.0,
            }
        }
        df = engine.compute_scores(prices_dict, fundamentals_dict=fundamentals_dict)
        score = df.loc[df["symbol"] == "PANIC", "sentiment_divergence_score"].iloc[0]
        assert 0.05 <= score <= 0.95
        assert score > 0.50


class TestFCFVelocityEngine:
    def test_floored_ev_prevents_negative_yield_anomaly(self):
        engine = FCFVelocityEngine()
        prices_dict = {"ZOMBIE": _generate_synthetic_ohlcv(40, seed=71)}
        # Cash-burning zombie with negative operating cash flows and net cash > MCAP (unfloored EV < 0)
        fundamentals_dict = {
            "ZOMBIE": {
                "market_cap": 1_000_000_000,
                "enterprise_value": -200_000_000,  # Negative EV unfloored
                "fcf_history": [-10_000_000, -20_000_000, -40_000_000, -80_000_000],
            }
        }
        df = engine.compute_scores(prices_dict, fundamentals_dict=fundamentals_dict)
        assert not df.empty
        score = df.loc[df["symbol"] == "ZOMBIE", "fcf_velocity_score"].iloc[0]
        # Floored EV ensures negative FCF produces negative velocity/yield, score < 0.50
        assert 0.05 <= score <= 0.95
        assert score < 0.50

    def test_growing_fcf_velocity_and_acceleration(self):
        engine = FCFVelocityEngine()
        prices_dict = {"GROWTH": _generate_synthetic_ohlcv(40, seed=72)}
        fundamentals_dict = {
            "GROWTH": {
                "market_cap": 10_000_000_000,
                "enterprise_value": 11_000_000_000,
                "fcf_history": [100_000_000, 200_000_000, 350_000_000, 550_000_000],
            }
        }
        df = engine.compute_scores(prices_dict, fundamentals_dict=fundamentals_dict)
        score = df.loc[df["symbol"] == "GROWTH", "fcf_velocity_score"].iloc[0]
        assert 0.05 <= score <= 0.95
        assert score > 0.50


class TestMultiFactorIntegration:
    def test_alpha_strategy_executor_44_strategies(self):
        executor = AlphaStrategyExecutor()
        assert len(AlphaStrategyExecutor.STRATEGY_SCORE_COLUMNS) == 44
        specs = executor._build_default_strategy_specs()
        assert len(specs) == 36
        spec_keys = {s.key for s in specs}
        expected_keys = [
            "stealth_accumulation",
            "vpin_toxicity",
            "macro_stress_spillover",
            "sue_sur_decay",
            "sentiment_divergence",
            "fcf_velocity",
        ]
        for key in expected_keys:
            assert key in spec_keys

        expected_new_cols = [
            "stealth_accumulation_score",
            "vpin_toxicity_score",
            "macro_stress_spillover_score",
            "sue_sur_decay_score",
            "sentiment_divergence_score",
            "fcf_velocity_score",
        ]
        for col in expected_new_cols:
            assert col in AlphaStrategyExecutor.STRATEGY_SCORE_COLUMNS.values()

    def test_ensemble_scorer_tiers_and_weights_sum_to_one(self):
        tiers = EnsembleScoringEngine.ALPHA_HORIZON_TIERS
        total_strategies = len(tiers["slow"]) + len(tiers["medium"]) + len(tiers["fast"])
        assert total_strategies == 44

        # 1D Regimes
        for regime_id, weights in EnsembleScoringEngine.REGIME_WEIGHTS.items():
            assert len(weights) == 44
            assert abs(sum(weights.values()) - 1.0) < 1e-4

        # 2D Regimes
        for state_key, weights in EnsembleScoringEngine.REGIME_2D_WEIGHTS.items():
            assert len(weights) == 44
            assert abs(sum(weights.values()) - 1.0) < 1e-4

    def test_backtester_canonical_columns(self):
        assert len(CANONICAL_37_COLUMNS) == 44
        assert len(CANONICAL_38_COLUMNS) == 44
        assert len(CANONICAL_44_COLUMNS) == 44
        assert len(STRATEGY_TO_COL_MAP) == 44
        assert len(COL_TO_STRATEGY_MAP) == 44


class TestEdgeCaseAdversarialRemediations:
    """Covers edge-case vulnerabilities remediated in Iteration 2."""

    def test_dataframe_input_truth_value_across_all_engines(self):
        """Verifies DataFrame input works across all 6 engines without raising ambiguous truth value errors."""
        panel_df = pd.DataFrame({
            "symbol": ["AAA", "AAA", "BBB", "BBB"],
            "Close": [10.0, 11.0, 20.0, 19.0],
            "Open": [9.9, 10.9, 20.1, 19.2],
            "High": [10.2, 11.2, 20.3, 19.5],
            "Low": [9.8, 10.8, 19.8, 18.9],
            "Volume": [1000.0, 1100.0, 2000.0, 2100.0],
        })
        engines = [
            StealthAccumulationEngine(),
            VPINToxicityEngine(),
            MacroStressSpilloverEngine(),
            SUESURDecayEngine(),
            SentimentDivergenceEngine(),
            FCFVelocityEngine(),
        ]
        for engine in engines:
            res = engine.compute_scores(panel_df)
            assert not res.empty, f"Failed for {engine.name}"
            assert len(res) == 2, f"Failed for {engine.name}"
            assert "symbol" in res.columns
            score_col = [c for c in res.columns if c != "symbol"][0]
            for s in res[score_col]:
                assert 0.05 <= s <= 0.95

    def test_sue_sur_decay_shape_mismatch_fallback(self):
        """Verifies SUESURDecayEngine on >=60 bars with missing fundamentals does not crash with shape mismatch."""
        engine = SUESURDecayEngine()
        p_df = pd.DataFrame({"Close": np.linspace(100.0, 110.0, 65)})
        res = engine.compute_scores({"SYM": p_df}, fundamentals_dict=None)
        assert not res.empty
        assert "sue_sur_decay_score" in res.columns
        score = res.loc[res["symbol"] == "SYM", "sue_sur_decay_score"].iloc[0]
        assert 0.05 <= score <= 0.95
        assert not np.isnan(score)

    def test_nan_fundamentals_boundary_invariant(self):
        """Verifies FCFVelocityEngine and SUESURDecayEngine with np.nan in fundamentals output clean numbers in [0.05, 0.95] with zero NaNs."""
        clean_df = pd.DataFrame({
            "Close": [10.0] * 50,
            "Open": [10.0] * 50,
            "High": [10.1] * 50,
            "Low": [9.9] * 50,
            "Volume": [1000.0] * 50,
        })
        # FCF Velocity with NaN fundamentals
        fcf_engine = FCFVelocityEngine()
        fcf_res = fcf_engine.compute_scores(
            {"SYM": clean_df},
            fundamentals_dict={"SYM": {"free_cash_flow": np.nan, "market_cap": np.nan, "total_debt": np.nan}}
        )
        assert not fcf_res.empty
        assert not fcf_res["fcf_velocity_score"].isna().any()
        fcf_score = fcf_res["fcf_velocity_score"].iloc[0]
        assert 0.05 <= fcf_score <= 0.95

        # SUE/SUR Decay with NaN fundamentals
        sue_engine = SUESURDecayEngine()
        sue_res = sue_engine.compute_scores(
            {"SYM": clean_df},
            fundamentals_dict={"SYM": {"roe": np.nan, "operating_margin": np.nan, "earnings_growth": np.nan}}
        )
        assert not sue_res.empty
        assert not sue_res["sue_sur_decay_score"].isna().any()
        sue_score = sue_res["sue_sur_decay_score"].iloc[0]
        assert 0.05 <= sue_score <= 0.95

    def test_macro_stress_firewall_acute_defense(self):
        """Verifies MacroStressSpilloverEngine under acute stress defends fragile stocks down toward 0.05."""
        engine = MacroStressSpilloverEngine()
        days = 60
        ind_df = pd.DataFrame({
            "cds_spread": np.linspace(100.0, 500.0, days),
            "fx_basis": np.linspace(-20.0, -150.0, days),
        })
        curr_s, delta_s = engine._extract_macro_stress_series(ind_df, {})
        assert curr_s > 0.70, f"Expected acute stress curr_s > 0.70, got {curr_s}"
        assert np.var(delta_s) > 1e-8

        # Fragile stock (crashing price)
        c_fragile = np.linspace(100.0, 50.0, days)
        df_fragile = pd.DataFrame({
            "Close": c_fragile,
            "Open": c_fragile,
            "High": c_fragile,
            "Low": c_fragile,
            "Volume": [1000.0] * days,
        })
        res = engine.compute_scores({"FRAGILE": df_fragile}, indicators_df=ind_df)
        assert not res.empty
        score = res.loc[res["symbol"] == "FRAGILE", "macro_stress_spillover_score"].iloc[0]
        assert score <= 0.10, f"Expected fragile score <= 0.10, got {score}"
        assert 0.05 <= score <= 0.95
