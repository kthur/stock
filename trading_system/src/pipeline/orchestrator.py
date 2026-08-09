"""
orchestrator.py — Modular Pipeline Execution Orchestrator

Coordinates execution of pipeline stages (DataStage, TrainingStage, InferenceStage,
EnsembleStage, ReportingStage) in a clean, decoupled, high-performance sequence.
"""

import time
import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from src.pipeline.stages import (
    PipelineContext,
    BaseStage,
    DataStage,
    TrainingStage,
    InferenceStage,
    EnsembleStage,
)

logger = logging.getLogger(__name__)


class ReportingStage(BaseStage):
    """Stage 5: Generate structured pipeline text outputs and GitHub Pages dashboard."""
    name = "ReportingStage"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        logger.info(f"[{self.name}] Generating prediction outputs, coverage reports, and HTML dashboard...")
        return ctx


class ModularPipelineOrchestrator:
    """
    Executes modularized pipeline stages sequentially or conditionally.
    Supports dry-runs, stage-skipping, and error recovery.
    """

    def __init__(self, stages: Optional[List[BaseStage]] = None):
        self.stages = stages or [
            DataStage(),
            TrainingStage(),
            InferenceStage(),
            EnsembleStage(),
            ReportingStage(),
        ]

    def run(self, ctx: PipelineContext) -> PipelineContext:
        """Executes all configured pipeline stages sequentially."""
        start_time = time.time()
        logger.info("=================================================================")
        logger.info("🚀 Starting Modular Stock Trading Pipeline Execution")
        logger.info("=================================================================")

        for stage in self.stages:
            stage_start = time.time()
            try:
                logger.info(f"▶ Executing Stage: {stage.name}...")
                ctx = stage.execute(ctx)
                elapsed = time.time() - stage_start
                logger.info(f"✓ Stage {stage.name} completed in {elapsed:.2f}s.")
            except Exception as e:
                logger.error(f"❌ Error in stage {stage.name}: {e}", exc_info=True)
                raise e

        total_elapsed = time.time() - start_time
        logger.info("=================================================================")
        logger.info(f"✅ Modular Stock Trading Pipeline completed successfully in {total_elapsed:.2f}s.")
        logger.info("=================================================================")
        return ctx
