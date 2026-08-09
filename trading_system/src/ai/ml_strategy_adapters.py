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
        if self.model_instance is None:
            return pd.DataFrame(columns=["symbol", "reg_score"])
        try:
            preds = self.model_instance.predict_all(prices_dict, fundamentals_dict=fundamentals_dict)
            if isinstance(preds, pd.DataFrame):
                if "reg_score" not in preds.columns and "expected_return_5d" in preds.columns:
                    preds = preds.rename(columns={"expected_return_5d": "reg_score"})
                return preds
            records = [{"symbol": k, "reg_score": v} for k, v in preds.items()]
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
        if self.model_instance is None:
            return pd.DataFrame(columns=["symbol", "surge_score"])
        try:
            preds = self.model_instance.predict_surge_all(prices_dict)
            if isinstance(preds, pd.DataFrame):
                if "surge_score" not in preds.columns and "surge_prob_5d" in preds.columns:
                    preds = preds.rename(columns={"surge_prob_5d": "surge_score"})
                return preds
            records = [{"symbol": k, "surge_score": v} for k, v in preds.items()]
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
        if self.model_instance is None:
            return pd.DataFrame(columns=["symbol", "vcp_ml_score"])
        try:
            preds = self.model_instance.predict(prices_dict)
            if isinstance(preds, pd.DataFrame):
                if "vcp_ml_score" not in preds.columns and "score" in preds.columns:
                    preds = preds.rename(columns={"score": "vcp_ml_score"})
                return preds
            records = [{"symbol": k, "vcp_ml_score": v} for k, v in preds.items()]
            return pd.DataFrame(records)
        except Exception as e:
            logger.warning(f"[VCPMLAdapter] Prediction failed: {e}")
            return pd.DataFrame(columns=["symbol", "vcp_ml_score"])
