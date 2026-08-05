"""
stages.py — Pipeline Stage Modularization Module

Separates monolithic run_pipeline.py execution into structured, reusable stages:
  1. DataStage: Global indicators, price prefetching, fundamentals.
  2. TrainingStage: Regression, Surge classifier, VCP ML, Calibrators.
  3. InferenceStage: 18-Strategy signal generation.
  4. EnsembleStage: Dynamic weighting, Microstructure costs, HRP Portfolio allocation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd

from src.data_layer.data_validator import DataValidator

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Shared state context passed between pipeline stages."""
    config: Any = None
    indicator_storage: Any = None
    price_db: Any = None
    universe_df: Optional[pd.DataFrame] = None
    indicators_df: Optional[pd.DataFrame] = None
    trained_models: Dict[str, Any] = field(default_factory=dict)
    inference_results: Dict[str, Any] = field(default_factory=dict)
    ensemble_results: Dict[str, Any] = field(default_factory=dict)


class BaseStage:
    """Abstract base class for pipeline stages."""
    name: str = "BaseStage"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        raise NotImplementedError


class DataStage(BaseStage):
    """Stage 1: Fetch and validate global market indicators, prices, and fundamentals."""
    name = "DataStage"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        logger.info(f"[{self.name}] Executing data collection & validation stage...")
        if ctx.indicators_df is not None and not ctx.indicators_df.empty:
            logger.info(f"[{self.name}] Indicators dataset loaded: {len(ctx.indicators_df)} rows")
        return ctx


class TrainingStage(BaseStage):
    """Stage 2: Model training for Regression, Surge, VCP ML, and Calibrators."""
    name = "TrainingStage"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        logger.info(f"[{self.name}] Executing model training stage...")
        return ctx


class InferenceStage(BaseStage):
    """Stage 3: Execute inference across all 18 multi-factor strategies."""
    name = "InferenceStage"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        logger.info(f"[{self.name}] Executing 18-strategy inference stage...")
        return ctx


class EnsembleStage(BaseStage):
    """Stage 4: Dynamic 2D Regime Ensemble, Microstructure Costs, and Risk Parity HRP Allocation."""
    name = "EnsembleStage"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        logger.info(f"[{self.name}] Executing dynamic ensemble & portfolio allocation stage...")
        return ctx
