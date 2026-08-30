"""Adapters for ML/Pattern models (OnDevicePredictionModel, VCP, etc.) to register with StrategyRegistry."""

import logging
from typing import Any, Dict, Optional
import pandas as pd

from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


@register_strategy(
    StrategyMeta(
        strategy_id="regression",
        display_name="XGBoost Regression",
        score_column="reg_score",
        category="ml",
        output_file="pipeline_result.txt",
        default_regime_weights={
            "BEAR": 0.12, "BEAR_HIGH_VOL": 0.15, "SIDEWAYS_LOW_VOL": 0.08, "BULL_HIGH_VOL": 0.07, "BULL_LOW_VOL": 0.08
        },
    )
)
class RegressionStrategyAdapter(BaseStrategyEngine):
    """Adapter for Strategy 1: XGBoost Regression Model."""

    def __init__(self, model_instance: Optional[Any] = None, config: Optional[Any] = None) -> None:
        self.model_instance = model_instance
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        inst = self.model_instance
        if inst is None:
            from src.ai.prediction_model import OnDevicePredictionModel
            inst = OnDevicePredictionModel(config=self.config)
        try:
            import numpy as np
            if hasattr(inst, "process_and_predict_all"):
                preds = inst.process_and_predict_all(prices_dict, indicator_df=indicators_df)
            elif hasattr(inst, "predict_all"):
                res = inst.predict_all(prices_dict, indicator_df=indicators_df)
                preds = res[0] if isinstance(res, tuple) else res
            else:
                preds = pd.DataFrame()
            if isinstance(preds, pd.DataFrame):
                if "reg_score" not in preds.columns and "expected_return_5d" in preds.columns:
                    preds = preds.rename(columns={"expected_return_5d": "reg_score"})
                if "reg_score" in preds.columns:
                    preds["reg_score"] = pd.to_numeric(preds["reg_score"], errors="coerce").fillna(0.0)
                return preds
            records = [{"symbol": str(k), "reg_score": float(v) if (v is not None and np.isfinite(float(v))) else 0.0} for k, v in preds.items()]
            return pd.DataFrame(records)
        except Exception as e:
            logger.warning(f"[RegressionAdapter] Prediction failed: {e}")
            return pd.DataFrame(columns=["symbol", "reg_score"])


@register_strategy(
    StrategyMeta(
        strategy_id="surge",
        display_name="Surge Classifier",
        score_column="surge_score",
        category="ml",
        output_file="surge_predictions.txt",
        default_regime_weights={
            "BEAR": 0.02, "BEAR_HIGH_VOL": 0.00, "SIDEWAYS_LOW_VOL": 0.04, "BULL_HIGH_VOL": 0.10, "BULL_LOW_VOL": 0.08
        },
    )
)
class SurgeStrategyAdapter(BaseStrategyEngine):
    """Adapter for Strategy 2: Surge Classifier Model."""

    def __init__(self, model_instance: Optional[Any] = None, config: Optional[Any] = None) -> None:
        self.model_instance = model_instance
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        inst = self.model_instance
        if inst is None:
            from src.ai.prediction_model import OnDevicePredictionModel
            inst = OnDevicePredictionModel(config=self.config)
        try:
            import numpy as np
            if hasattr(inst, "predict_surge_all"):
                preds = inst.predict_surge_all(prices_dict, indicator_df=indicators_df)
            elif hasattr(inst, "predict_all"):
                res = inst.predict_all(prices_dict, indicator_df=indicators_df)
                preds = res[1] if isinstance(res, tuple) else res
            else:
                preds = pd.DataFrame()
            if isinstance(preds, pd.DataFrame):
                if "surge_score" not in preds.columns and "surge_prob_5d" in preds.columns:
                    preds = preds.rename(columns={"surge_prob_5d": "surge_score"})
                if "surge_score" in preds.columns:
                    preds["surge_score"] = pd.to_numeric(preds["surge_score"], errors="coerce").fillna(0.0)
                return preds
            records = [{"symbol": str(k), "surge_score": float(v) if (v is not None and np.isfinite(float(v))) else 0.0} for k, v in preds.items()]
            return pd.DataFrame(records)
        except Exception as e:
            logger.warning(f"[SurgeAdapter] Prediction failed: {e}")
            return pd.DataFrame(columns=["symbol", "surge_score"])


@register_strategy(
    StrategyMeta(
        strategy_id="vcp_ml",
        display_name="VCP ML Predictor",
        score_column="vcp_ml_score",
        category="ml",
        output_file="vcp_ml_predictions.txt",
        default_regime_weights={
            "BEAR": 0.02, "BEAR_HIGH_VOL": 0.00, "SIDEWAYS_LOW_VOL": 0.06, "BULL_HIGH_VOL": 0.08, "BULL_LOW_VOL": 0.06
        },
    )
)
class VCPMLStrategyAdapter(BaseStrategyEngine):
    """Adapter for Strategy 5: VCP ML Predictor."""

    def __init__(self, model_instance: Optional[Any] = None, config: Optional[Any] = None) -> None:
        self.model_instance = model_instance
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        inst = self.model_instance
        if inst is None:
            from src.ai.vcp_ml_predictor import VCPSurgePredictor
            inst = VCPSurgePredictor()
        try:
            import numpy as np
            preds = inst.predict(prices_dict)
            if isinstance(preds, pd.DataFrame):
                if "vcp_ml_score" not in preds.columns and "score" in preds.columns:
                    preds = preds.rename(columns={"score": "vcp_ml_score"})
                elif "vcp_ml_score" not in preds.columns and "vcp_5d" in preds.columns:
                    preds = preds.rename(columns={"vcp_5d": "vcp_ml_score"})
                if "vcp_ml_score" in preds.columns:
                    preds["vcp_ml_score"] = pd.to_numeric(preds["vcp_ml_score"], errors="coerce").fillna(0.0)
                return preds
            records = [{"symbol": str(k), "vcp_ml_score": float(v) if (v is not None and np.isfinite(float(v))) else 0.0} for k, v in preds.items()]
            return pd.DataFrame(records)
        except Exception as e:
            logger.warning(f"[VCPMLAdapter] Prediction failed: {e}")
            return pd.DataFrame(columns=["symbol", "vcp_ml_score"])


@register_strategy(
    StrategyMeta(
        strategy_id="lead_lag",
        display_name="Lead-Lag Shift",
        score_column="ll_score",
        category="cross_asset",
        output_file="lead_lag_predictions.txt",
        default_regime_weights={
            "BEAR": 0.02, "BEAR_HIGH_VOL": 0.02, "SIDEWAYS_LOW_VOL": 0.05, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.03
        },
    )
)
class LeadLagStrategyAdapter(BaseStrategyEngine):
    """Adapter for Strategy 3: Lead-Lag Shift Engine."""

    def __init__(self, model_instance: Optional[Any] = None, config: Optional[Any] = None) -> None:
        self.model_instance = model_instance
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        inst = self.model_instance
        if inst is None:
            from src.core.lead_lag import LeadLagEngine
            inst = LeadLagEngine(config=self.config)
        if hasattr(inst, "compute_scores"):
            return inst.compute_scores(prices_dict=prices_dict, **kwargs)
        return pd.DataFrame(columns=["symbol", "ll_score"])


@register_strategy(
    StrategyMeta(
        strategy_id="vcp_rule",
        display_name="VCP Rule Pattern",
        score_column="vcp_rule_score",
        category="technical",
        output_file="vcp_patterns.txt",
        default_regime_weights={
            "BEAR": 0.02, "BEAR_HIGH_VOL": 0.02, "SIDEWAYS_LOW_VOL": 0.03, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.03
        },
    )
)
class VCPRuleStrategyAdapter(BaseStrategyEngine):
    """Adapter for Strategy 4: VCP Rule Pattern Detector."""

    def __init__(self, model_instance: Optional[Any] = None, config: Optional[Any] = None) -> None:
        self.model_instance = model_instance
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        if self.model_instance is not None and hasattr(self.model_instance, "compute_scores"):
            return self.model_instance.compute_scores(prices_dict=prices_dict, **kwargs)
        from src.ai.vcp_detector import detect_vcp
        records = []
        if prices_dict:
            for sym, df in prices_dict.items():
                try:
                    res = detect_vcp(df)
                    v_score = (res.get('vcp_score', 0.0) / 100.0) if res else 0.50
                    records.append({'symbol': str(sym), 'vcp_rule_score': float(np.clip(v_score, 0.0, 1.0))})
                except Exception:
                    records.append({'symbol': str(sym), 'vcp_rule_score': 0.50})
        return pd.DataFrame(records)


@register_strategy(
    StrategyMeta(
        strategy_id="lstm",
        display_name="Causal LSTM",
        score_column="lstm_score",
        category="ml",
        output_file="lstm_predictions.txt",
        default_regime_weights={
            "BEAR": 0.03, "BEAR_HIGH_VOL": 0.03, "SIDEWAYS_LOW_VOL": 0.07, "BULL_HIGH_VOL": 0.06, "BULL_LOW_VOL": 0.06
        },
    )
)
class LSTMStrategyAdapter(BaseStrategyEngine):
    """Adapter for Strategy 6: Strict Causal LSTM Model."""

    def __init__(self, model_instance: Optional[Any] = None, config: Optional[Any] = None) -> None:
        self.model_instance = model_instance
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        if self.model_instance is not None:
            if hasattr(self.model_instance, "predict_lstm"):
                return self.model_instance.predict_lstm(prices_dict)
            if hasattr(self.model_instance, "predict_all"):
                preds = self.model_instance.predict_all(prices_dict)
                if isinstance(preds, pd.DataFrame):
                    if "lstm_score" not in preds.columns and "score" in preds.columns:
                        preds = preds.rename(columns={"score": "lstm_score"})
                    return preds
        from src.ai.prediction_model import OnDevicePredictionModel
        fallback_model = OnDevicePredictionModel(config=self.config)
        return fallback_model.predict_lstm(prices_dict)


@register_strategy(
    StrategyMeta(
        strategy_id="sentiment",
        display_name="NLP Sentiment Catalyst",
        score_column="sentiment_score",
        category="sentiment",
        output_file="sentiment_predictions.txt",
        default_regime_weights={
            "BEAR": 0.03, "BEAR_HIGH_VOL": 0.03, "SIDEWAYS_LOW_VOL": 0.03, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.03
        },
    )
)
class SentimentStrategyAdapter(BaseStrategyEngine):
    """Adapter for Strategy 20: NLP Sentiment Catalyst."""

    def __init__(self, model_instance: Optional[Any] = None, config: Optional[Any] = None) -> None:
        self.model_instance = model_instance
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        inst = self.model_instance
        if inst is None:
            from src.core.llm_sentiment_engine import DARTSECSentimentEngine
            inst = DARTSECSentimentEngine()
        if hasattr(inst, "compute_scores"):
            return inst.compute_scores(prices_dict=prices_dict, **kwargs)
        return pd.DataFrame(columns=["symbol", "sentiment_score"])


@register_strategy(
    StrategyMeta(
        strategy_id="darkpool",
        display_name="Dark Pool Flow",
        score_column="darkpool_score",
        category="microstructure",
        output_file="darkpool_predictions.txt",
        default_regime_weights={
            "BEAR": 0.03, "BEAR_HIGH_VOL": 0.03, "SIDEWAYS_LOW_VOL": 0.03, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.03
        },
    )
)
class DarkPoolStrategyAdapter(BaseStrategyEngine):
    """Adapter for Strategy 30: Dark Pool Flow & Block Trade Tracking."""

    def __init__(self, model_instance: Optional[Any] = None, config: Optional[Any] = None) -> None:
        self.model_instance = model_instance
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        if self.model_instance is not None and hasattr(self.model_instance, "compute_scores"):
            return self.model_instance.compute_scores(prices_dict=prices_dict, **kwargs)
        from src.core.hft_engine import MicrostructureImbalanceEngine
        engine = MicrostructureImbalanceEngine()
        res = engine.compute_scores(prices_dict=prices_dict, **kwargs)
        if isinstance(res, pd.DataFrame):
            if 'darkpool_score' not in res.columns and 'microstructure_score' in res.columns:
                res = res.rename(columns={'microstructure_score': 'darkpool_score'})
            elif 'darkpool_score' not in res.columns and 'hft_score' in res.columns:
                res = res.rename(columns={'hft_score': 'darkpool_score'})
            if 'darkpool_score' in res.columns:
                res['darkpool_score'] = pd.to_numeric(res['darkpool_score'], errors='coerce').fillna(0.50)
            return res
        return pd.DataFrame([{'symbol': str(s), 'darkpool_score': 0.50} for s in prices_dict.keys()])
