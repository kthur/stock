"""
trainer.py — Training Stage Pipeline Component

Encapsulates multi-market training for Regression (XGB/LGB/Cat), Surge Classifiers,
Lead-Lag shift matrices, VCP ML surge models, and Isotonic Regression Calibrators.
"""

import logging
from typing import Any, Dict
import pandas as pd

logger = logging.getLogger(__name__)


class PipelineTrainer:
    """
    Training Stage Component: Manages model training, walk-forward validation,
    and probability calibrators for multi-factor trading strategy predictions.
    """

    def train_all_models(
        self,
        prediction_model: Any,
        vcp_ml_predictor: Any,
        df_train: pd.DataFrame,
        indicator_df: pd.DataFrame,
        universe: pd.DataFrame,
        cfg: Any
    ) -> Dict[str, Any]:
        """Runs complete training pass across all markets and horizons."""
        logger.info("[PipelineTrainer] Starting multi-market model training pass...")
        trained_info: Dict[str, Any] = {}

        if df_train is None or not isinstance(df_train, pd.DataFrame) or df_train.empty:
            logger.warning("[PipelineTrainer] Training dataset is empty or invalid. Skipping training.")
            return trained_info

        # 1. Train Regression & Surge Classifier
        if hasattr(prediction_model, 'train'):
            try:
                prediction_model.train(df_train, indicator_df=indicator_df)
                prediction_model.train_surge(df_train)
                trained_info['prediction_model'] = True
                logger.info("[PipelineTrainer] Regression and Surge models trained successfully.")
            except Exception as e:
                logger.error(f"[PipelineTrainer] Regression/Surge training failed: {e}")

        # 2. Train Lead-Lag 2-Tier Shift Matrix
        if hasattr(prediction_model, 'compute_lead_lag'):
            try:
                prediction_model.compute_lead_lag(df_train, indicator_df=indicator_df)
                trained_info['lead_lag'] = True
                logger.info("[PipelineTrainer] Lead-Lag shift matrix computed.")
            except Exception as e:
                logger.error(f"[PipelineTrainer] Lead-Lag computation failed: {e}")

        # 3. Train VCP ML Surge Predictor
        if vcp_ml_predictor is not None and hasattr(vcp_ml_predictor, 'train'):
            try:
                vcp_ml_predictor.train(df_train, indicator_df=indicator_df, universe=universe)
                trained_info['vcp_ml'] = True
                logger.info("[PipelineTrainer] VCP ML surge models trained.")
            except Exception as e:
                logger.error(f"[PipelineTrainer] VCP ML training failed: {e}")

        return trained_info
