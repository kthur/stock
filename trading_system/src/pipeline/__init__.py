"""
src/pipeline — Stock Trading System Pipeline Package

Modular pipeline package providing decoupled stage components:
  - PipelineDataFetcher: Market indicators, stock universe, price prefetching
  - PipelineTrainer: Multi-market model training and calibrators
  - PipelinePredictor: 30-strategy inference and 2D regime ensemble scoring
  - PipelineReporter: Prediction text reports & GitHub Pages dashboard
  - ModularPipelineOrchestrator: Stage execution coordinator
"""

from src.pipeline.stages import PipelineContext, BaseStage, DataStage, TrainingStage, InferenceStage, EnsembleStage
from src.pipeline.data_fetcher import PipelineDataFetcher
from src.pipeline.trainer import PipelineTrainer
from src.pipeline.predictor import PipelinePredictor
from src.pipeline.reporter import PipelineReporter
from src.pipeline.orchestrator import ModularPipelineOrchestrator, ReportingStage

__all__ = [
    "PipelineContext",
    "BaseStage",
    "DataStage",
    "TrainingStage",
    "InferenceStage",
    "EnsembleStage",
    "ReportingStage",
    "PipelineDataFetcher",
    "PipelineTrainer",
    "PipelinePredictor",
    "PipelineReporter",
    "ModularPipelineOrchestrator",
]
