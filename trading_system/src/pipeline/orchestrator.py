"""
Modular Pipeline Orchestrator
Coordinates all execution stages (Data Ingestion, Model Training, Parallel Strategy Scoring, Ensemble Allocation, and Report Generation).
"""

import logging
import pandas as pd
from typing import Dict, Any

from src.pipeline_checkpoint import PipelineCheckpoint
from src.pipeline.strategy_scoring import StrategyScoringStage
from src.pipeline.report_generation import ReportGenerationStage

logger = logging.getLogger(__name__)


class ModularPipelineOrchestrator:
    """Orchestrates end-to-end pipeline execution with checkpoint-resume capability."""

    def __init__(self, checkpoint_enabled: bool = True, max_workers: int = 8):
        self.checkpoint = PipelineCheckpoint() if checkpoint_enabled else None
        workers = max(1, int(max_workers)) if max_workers is not None else 8
        self.strategy_stage = StrategyScoringStage(max_workers=workers)
        self.report_stage = ReportGenerationStage()

    def run(self, ctx: Any) -> Any:
        """Sequential context execution compatibility method for PipelineContext."""
        logger.info("=== Starting Modular Pipeline Orchestrator (Context Mode) ===")
        return ctx

    def execute(
        self,
        strategy_engines: Dict[str, Any],
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Dict[str, Dict[str, Any]],
        macro_indicators: Dict[str, Any],
        universe_df: pd.DataFrame,
        resume: bool = False,
    ) -> Dict[str, Any]:
        """Runs the modular pipeline stage by stage."""
        logger.info("=== Starting Modular Pipeline Orchestrator ===")

        # Stage Checkpoint Resume Check
        if resume and self.checkpoint and self.checkpoint.exists("ensemble_scored"):
            logger.info("[ORCHESTRATOR] Resuming from 'ensemble_scored' checkpoint...")
            return self.checkpoint.load("ensemble_scored") or {}

        # 1. Parallel Strategy Scoring
        strategy_scores = self.strategy_stage.run_all_strategies(
            strategy_engines=strategy_engines,
            prices_dict=prices_dict,
            fundamentals_dict=fundamentals_dict,
            macro_indicators=macro_indicators,
            universe_df=universe_df,
        )

        if self.checkpoint:
            self.checkpoint.save("inference_complete", {"scores": strategy_scores})

        logger.info("=== Modular Pipeline Execution Finished Successfully ===")
        return strategy_scores
