"""
Unit and integration tests for Optuna HPO Strategy Tuner and 2D Regime + Rolling Sharpe Ensemble Scorer.
"""

import json
import pytest
import numpy as np
import pandas as pd
from src.ai.optuna_tuner import OptunaStrategyTuner
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.analysis.regime_detector import MarketRegimeDetector
from src.ai.vcp_detector import detect_vcp


@pytest.fixture
def temp_model_dir(tmp_path):
    d = tmp_path / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def synthetic_regression_data():
    np.random.seed(42)
    n = 100
    X = pd.DataFrame({
        'feature_1': np.random.randn(n),
        'feature_2': np.random.randn(n),
        'feature_3': np.random.randn(n),
    })
    y = pd.Series(2.0 * X['feature_1'] - 1.0 * X['feature_2'] + np.random.randn(n) * 0.1)
    return X, y


@pytest.fixture
def synthetic_surge_data():
    np.random.seed(42)
    n = 100
    X = pd.DataFrame({
        'ret_1d': np.random.randn(n),
        'vol_20d': np.abs(np.random.randn(n)),
        'rsi_14': np.random.uniform(30, 70, size=n),
    })
    probs = 1 / (1 + np.exp(-X['ret_1d']))
    y = pd.Series((probs > 0.5).astype(int))
    return X, y


@pytest.fixture
def synthetic_prices_dict():
    np.random.seed(42)
    n = 250
    dict_prices = {}
    for sym in ["AAPL", "MSFT", "GOOGL", "005930", "000660"]:
        dates = pd.date_range("2025-01-01", periods=n, freq="D")
        returns = np.random.normal(0.0005, 0.015, size=n)
        price_paths = 100.0 * np.exp(np.cumsum(returns))
        high = price_paths * (1 + np.abs(np.random.normal(0, 0.005, size=n)))
        low = price_paths * (1 - np.abs(np.random.normal(0, 0.005, size=n)))
        volume = np.random.randint(100000, 1000000, size=n)

        df = pd.DataFrame({
            "Open": price_paths,
            "High": high,
            "Low": low,
            "Close": price_paths,
            "Volume": volume
        }, index=dates)
        dict_prices[sym] = df
    return dict_prices


class TestOptunaStrategyTuner:
    def test_init_and_paths(self, temp_model_dir):
        tuner = OptunaStrategyTuner(model_dir=str(temp_model_dir))
        assert tuner.model_dir == temp_model_dir
        assert tuner.params_file == temp_model_dir / "tuned_params.json"
        assert tuner.tuned_params == {}

    def test_save_and_load_params(self, temp_model_dir):
        tuner = OptunaStrategyTuner(model_dir=str(temp_model_dir))
        params = {
            "xgb": {"n_estimators": 50, "max_depth": 3},
            "lead_lag": {"leaders_count": 20, "lag_window": 1, "corr_cutoff": 0.3},
            "vcp_rule": {"contraction_threshold": 1.05, "volume_ratio_cutoff": 0.85}
        }
        tuner.save_tuned_params(params)
        assert (temp_model_dir / "tuned_params.json").exists()

        loaded = tuner.load_tuned_params()
        assert loaded["xgb"]["n_estimators"] == 50
        assert loaded["lead_lag"]["leaders_count"] == 20
        assert loaded["vcp_rule"]["contraction_threshold"] == 1.05

    def test_tune_strategy_1_regression(self, temp_model_dir, synthetic_regression_data):
        X, y = synthetic_regression_data
        tuner = OptunaStrategyTuner(model_dir=str(temp_model_dir))
        res = tuner.tune_strategy_1_regression(X, y, n_trials=2, n_splits=3)

        assert "xgb" in res
        assert "lgb" in res
        assert "cat" in res
        assert res["xgb"]["n_estimators"] >= 50
        assert "xgb" in tuner.tuned_params

    def test_tune_strategy_2_surge(self, temp_model_dir, synthetic_surge_data):
        X, y = synthetic_surge_data
        tuner = OptunaStrategyTuner(model_dir=str(temp_model_dir))
        res = tuner.tune_strategy_2_surge(X, y, n_trials=2, n_splits=3)

        assert "surge_xgb" in res
        assert "surge_lgb" in res
        assert "surge_cat" in res
        assert res["surge_xgb"]["max_depth"] >= 3

    def test_tune_strategy_3_lead_lag(self, temp_model_dir, synthetic_prices_dict):
        tuner = OptunaStrategyTuner(model_dir=str(temp_model_dir))
        res = tuner.tune_strategy_3_lead_lag(synthetic_prices_dict, n_trials=2)

        assert "leader_count" in res or "leaders_count" in res
        assert "lag_window" in res
        assert "corr_threshold" in res or "corr_cutoff" in res
        assert "lead_lag" in tuner.tuned_params

    def test_tune_strategy_4_vcp_rule(self, temp_model_dir, synthetic_prices_dict):
        tuner = OptunaStrategyTuner(model_dir=str(temp_model_dir))
        res = tuner.tune_strategy_4_vcp_rule(synthetic_prices_dict, n_trials=2)

        assert "contraction_ratio" in res or "contraction_threshold" in res
        assert "vol_declining_threshold" in res or "volume_ratio_cutoff" in res
        assert "near_high_cutoff" in res
        assert "vcp_rule" in tuner.tuned_params

    def test_tune_strategy_5_vcp_ml(self, temp_model_dir, synthetic_surge_data):
        X, y = synthetic_surge_data
        tuner = OptunaStrategyTuner(model_dir=str(temp_model_dir))
        res = tuner.tune_strategy_5_vcp_ml(X, y, n_trials=2, n_splits=3)

        assert "max_depth" in res
        assert "scale_pos_weight" in res or "scale_pos_weight_mult" in res
        assert "vcp_ml" in tuner.tuned_params


    def test_tune_all(self, temp_model_dir, synthetic_regression_data, synthetic_surge_data, synthetic_prices_dict):
        X_reg, y_reg = synthetic_regression_data
        X_s, y_s = synthetic_surge_data
        tuner = OptunaStrategyTuner(model_dir=str(temp_model_dir))
        all_params = tuner.tune_all(
            X_reg=X_reg, y_reg=y_reg,
            X_surge=X_s, y_surge=y_s,
            prices_dict=synthetic_prices_dict,
            X_vcp=X_s, y_vcp=y_s,
            n_trials=1
        )

        assert (temp_model_dir / "tuned_params.json").exists()
        assert "xgb" in all_params
        assert "surge_xgb" in all_params
        assert "lead_lag" in all_params
        assert "vcp_rule" in all_params
        assert "vcp_ml" in all_params


class Test2DRegimeAndEnsembleScorer:
    def test_predict_2d_regime_labels(self):
        detector = MarketRegimeDetector()
        dates = pd.date_range("2025-01-01", periods=50)
        indicator_df = pd.DataFrame({
            "sp500_change": np.random.normal(0.001, 0.01, size=50)
        }, index=dates)

        res = detector.predict_2d_regime(indicator_df)
        assert "direction_code" in res
        assert "direction_label" in res
        assert "volatility_label" in res
        assert "combo_label" in res

        valid_combos = {
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BULL_LOW_VOL", "BULL_HIGH_VOL"
        }
        assert res["combo_label"] in valid_combos
        label_str = detector.predict_2d_regime_label(indicator_df)
        assert label_str == res["combo_label"]

    def test_regime_2d_weights_coverage(self):
        engine = EnsembleScoringEngine()
        assert hasattr(engine, "REGIME_2D_WEIGHTS")
        combos = [
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BULL_LOW_VOL", "BULL_HIGH_VOL"
        ]
        for combo in combos:
            assert combo in engine.REGIME_2D_WEIGHTS
            weights = engine.get_base_weights(combo)
            assert len(weights) >= 9
            assert pytest.approx(sum(weights.values()), abs=1e-5) == 1.0
            for strat in [
                "regression", "surge", "lead_lag", "vcp_rule", "vcp_ml", "lstm",
                "stat_arb", "sector_rotation", "rim_valuation", "event_driven",
                "mq_factor", "iv_skew", "order_flow", "short_term_reversal"
            ]:
                assert strat in engine.REGIME_2D_WEIGHTS[combo]

    def test_compute_dynamic_weights_from_sharpe_exponential(self):
        engine = EnsembleScoringEngine()
        sharpes = {
            "regression": 0.5,
            "surge": 1.5,
            "lead_lag": 0.2,
            "vcp_rule": 0.8,
            "vcp_ml": 2.0
        }
        weights = engine.compute_dynamic_weights_from_sharpe(sharpes, regime="BULL_LOW_VOL", gamma=1.0)
        assert pytest.approx(sum(weights.values()), abs=1e-5) == 1.0
        # Strategy with higher Sharpe (vcp_ml = 2.0) should get boosted relative to lower Sharpe (lead_lag = 0.2)
        base = engine.get_base_weights("BULL_LOW_VOL")
        assert weights["vcp_ml"] / base["vcp_ml"] > weights["lead_lag"] / base["lead_lag"]

    def test_5_strategy_ensemble_score_calculation(self):
        engine = EnsembleScoringEngine()

        symbols = ["AAPL", "MSFT", "GOOGL"]
        reg_df = pd.DataFrame({"symbol": symbols, 20: [0.05, 0.12, 0.08]})
        surge_df = pd.DataFrame({"symbol": symbols, "surge_20d": [0.60, 0.85, 0.40]})
        ll_df = pd.DataFrame({"symbol": symbols, "lead_lag_score": [0.30, 0.70, 0.50]})
        vcp_rule_df = pd.DataFrame({"symbol": symbols, "vcp_score": [80.0, 50.0, 90.0]})
        vcp_ml_df = pd.DataFrame({"symbol": symbols, "vcp_20d": [0.75, 0.90, 0.65]})

        ensemble_df = engine.calculate_ensemble_score(
            regime="BULL_LOW_VOL",
            regression_df=reg_df,
            surge_df=surge_df,
            lead_lag_df=ll_df,
            vcp_ml_df=vcp_ml_df,
            vcp_patterns_df=vcp_rule_df,
            target_horizon=20
        )

        assert not ensemble_df.empty
        assert len(ensemble_df) == 3
        expected_cols = ["symbol", "reg_score", "surge_score", "ll_score", "vcp_rule_score", "vcp_ml_score", "ensemble_score", "ensemble_expected_return"]
        for col in expected_cols:
            assert col in ensemble_df.columns

        # Verify score bounds
        assert (ensemble_df["ensemble_score"] >= 0.0).all()
        assert (ensemble_df["ensemble_score"] <= 1.0).all()
        assert (ensemble_df["ensemble_expected_return"] >= 0.0).all()
        assert (ensemble_df["ensemble_expected_return"] <= 20.0).all()


def test_vcp_detector_with_tuned_params(temp_model_dir):
    tuned_file = temp_model_dir / "tuned_params.json"
    params = {
        "vcp_rule": {
            "contraction_threshold": 1.10,
            "volume_ratio_cutoff": 0.90,
            "near_high_cutoff": 0.55,
            "score_weights": {
                "decreasing": 30.0,
                "volume": 20.0
            }
        }
    }
    with open(tuned_file, "w", encoding="utf-8") as f:
        json.dump(params, f)

    dates = pd.date_range("2025-01-01", periods=210)
    df = pd.DataFrame({
        "High": 100 + np.random.randn(210),
        "Low": 95 + np.random.randn(210),
        "Close": 98 + np.random.randn(210),
        "Volume": np.random.randint(1000, 5000, size=210)
    }, index=dates)

    res = detect_vcp(df, params=params["vcp_rule"])
    assert "is_vcp" in res
    assert "vcp_score" in res
