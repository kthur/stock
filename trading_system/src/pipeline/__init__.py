"""
Pipeline Modular Architecture Package
Decomposes the monolithic pipeline into cleanly separated execution stages.
"""

from .data_ingestion import DataIngestionStage
from .model_training import ModelTrainingStage
from .strategy_scoring import StrategyScoringStage
from .ensemble_allocation import EnsembleAllocationStage
from .report_generation import ReportGenerationStage
from .orchestrator import ModularPipelineOrchestrator

__all__ = [
    "DataIngestionStage",
    "ModelTrainingStage",
    "StrategyScoringStage",
    "EnsembleAllocationStage",
    "ReportGenerationStage",
    "ModularPipelineOrchestrator",
]
