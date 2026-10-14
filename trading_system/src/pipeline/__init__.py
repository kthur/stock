"""
Pipeline Modular Architecture Package
Decomposes the monolithic pipeline into cleanly separated execution stages.
Supports both stage-based orchestrators and component fetchers/trainers/predictors/reporters.
"""

from __future__ import annotations

try:
    from src.pipeline.stages import PipelineContext, BaseStage, DataStage, TrainingStage, InferenceStage, EnsembleStage, ReportingStage
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
    from src.pipeline.strategy_executor import (
        AlphaStrategyExecutor,
        PipelineStrategyContext,
        StrategySpec,
        StrategyExecutionResult,
    )
    from src.pipeline.prediction_reporter import (
        save_strategy_predictions_report,
        slice_top_dataframe,
        get_target_markets_to_save,
        format_prediction_line,
    )
except ImportError:
    from trading_system.src.pipeline.stages import PipelineContext, BaseStage, DataStage, TrainingStage, InferenceStage, EnsembleStage, ReportingStage
    from trading_system.src.pipeline.data_fetcher import PipelineDataFetcher
    from trading_system.src.pipeline.trainer import PipelineTrainer
    from trading_system.src.pipeline.predictor import PipelinePredictor
    from trading_system.src.pipeline.reporter import PipelineReporter

    from trading_system.src.pipeline.data_ingestion import DataIngestionStage
    from trading_system.src.pipeline.model_training import ModelTrainingStage
    from trading_system.src.pipeline.strategy_scoring import StrategyScoringStage
    from trading_system.src.pipeline.ensemble_allocation import EnsembleAllocationStage
    from trading_system.src.pipeline.report_generation import ReportGenerationStage
    from trading_system.src.pipeline.orchestrator import ModularPipelineOrchestrator
    from trading_system.src.pipeline.strategy_executor import (
        AlphaStrategyExecutor,
        PipelineStrategyContext,
        StrategySpec,
        StrategyExecutionResult,
    )
    from trading_system.src.pipeline.prediction_reporter import (
        save_strategy_predictions_report,
        slice_top_dataframe,
        get_target_markets_to_save,
        format_prediction_line,
    )


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
    "AlphaStrategyExecutor",
    "PipelineStrategyContext",
    "StrategySpec",
    "StrategyExecutionResult",
    "save_strategy_predictions_report",
    "slice_top_dataframe",
    "get_target_markets_to_save",
    "format_prediction_line",
]
