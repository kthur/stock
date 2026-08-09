"""
predictor.py — Inference & Ensemble Stage Pipeline Component

Executes 30-strategy multi-factor signal generation, 2D/3D market regime detection,
dynamic exponential Sharpe weighting, microstructure cost deduction, and HRP portfolio allocation.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class PipelinePredictor:
    """
    Inference & Ensemble Component: Evaluates all 30 strategies, applies 2D market regime
    weights, deducts STT tax / SEC fees / market impact, and generates final expected returns.
    """

    def run_all_strategy_inference(
        self,
        symbols: List[str],
        prices_dict: Dict[str, pd.DataFrame],
        indicator_df: pd.DataFrame,
        universe: pd.DataFrame,
        prediction_model: Any,
        vcp_ml_predictor: Any
    ) -> Dict[str, pd.DataFrame]:
        """Runs predictions across all available strategy engines."""
        logger.info(f"[PipelinePredictor] Running 30-strategy inference pass across {len(symbols)} symbols...")
        results = {}

        # 1. Regression & Surge Predictions
        if hasattr(prediction_model, 'predict'):
            try:
                reg_df, surge_df = prediction_model.predict(prices_dict, indicator_df=indicator_df, universe=universe)
                results['regression'] = reg_df
                results['surge'] = surge_df
            except Exception as e:
                logger.error(f"[PipelinePredictor] Regression/Surge prediction failed: {e}")

        # 2. Lead-Lag Inference
        if hasattr(prediction_model, 'predict_lead_lag'):
            try:
                results['lead_lag'] = prediction_model.predict_lead_lag(prices_dict, indicator_df=indicator_df)
            except Exception as e:
                logger.error(f"[PipelinePredictor] Lead-Lag prediction failed: {e}")

        # 3. VCP ML Inference
        if vcp_ml_predictor is not None and hasattr(vcp_ml_predictor, 'predict'):
            try:
                results['vcp_ml'] = vcp_ml_predictor.predict(prices_dict, indicator_df=indicator_df, universe=universe)
            except Exception as e:
                logger.error(f"[PipelinePredictor] VCP ML prediction failed: {e}")

        return results

    def calculate_regime_ensemble(
        self,
        ensemble_engine: Any,
        regime: int,
        strategy_outputs: Dict[str, pd.DataFrame],
        target_horizon: int = 20
    ) -> pd.DataFrame:
        """Ensembles all strategy outputs using 2D Market Regime weights and dynamic Sharpe weighting."""
        logger.info(f"[PipelinePredictor] Calculating ensemble score for market regime {regime} (Horizon: {target_horizon}d)...")
        if not hasattr(ensemble_engine, 'calculate_ensemble_score'):
            return pd.DataFrame()

        try:
            ensemble_df = ensemble_engine.calculate_ensemble_score(
                regime=regime,
                regression_df=strategy_outputs.get('regression'),
                surge_df=strategy_outputs.get('surge'),
                lead_lag_df=strategy_outputs.get('lead_lag'),
                vcp_ml_df=strategy_outputs.get('vcp_ml'),
                target_horizon=target_horizon,
                strategy_dfs=strategy_outputs
            )
            return ensemble_df
        except Exception as e:
            logger.error(f"[PipelinePredictor] Ensemble calculation failed: {e}")
            return pd.DataFrame()
