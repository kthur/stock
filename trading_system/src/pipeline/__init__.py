"""
Pipeline Modular Architecture Package
Decomposes the monolithic pipeline into cleanly separated execution stages.
Supports both stage-based orchestrators and component fetchers/trainers/predictors/reporters.
"""

from src.pipeline.stages import PipelineContext, BaseStage, DataStage, TrainingStage, InferenceStage, EnsembleStage
from src.pipeline.data_fetcher import PipelineDataFetcher
from src.pipeline.trainer import PipelineTrainer
from src.pipeline.predictor import PipelinePredictor
from src.pipeline.reporter import PipelineReporter

from src.pipeline.data_ingestion import DataIngestionStage
from src.pipeline.model_training import ModelTrainingStage
from src.pipeline.strategy_scoring import StrategyScoringStage
from src.pipeline.ensemble_allocation import EnsembleAllocationStage
from src.pipeline.report_generation import ReportGenerationStage
from src.pipeline.orchestrator import ModularPipelineOrchestrator


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
    "DataIngestionStage",
    "ModelTrainingStage",
    "StrategyScoringStage",
    "EnsembleAllocationStage",
    "ReportGenerationStage",
    "ModularPipelineOrchestrator",
]
