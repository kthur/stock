"""
test_modular_pipeline.py — Unit tests for Modular Pipeline Orchestrator and Unified DB Engine
"""

import os
import unittest
import pandas as pd

from src.pipeline.stages import PipelineContext, DataStage, TrainingStage, InferenceStage, EnsembleStage
from src.pipeline.orchestrator import ModularPipelineOrchestrator, ReportingStage
from src.persistence.unified_db import UnifiedDBEngine, PostgresConfig


class TestModularPipeline(unittest.TestCase):

    def test_pipeline_context_init(self):
        ctx = PipelineContext()
        self.assertIsNone(ctx.config)
        self.assertEqual(len(ctx.trained_models), 0)

    def test_orchestrator_execution(self):
        ctx = PipelineContext()
        ctx.indicators_df = pd.DataFrame([{"vix": 15.0, "us10y": 4.2}])
        orchestrator = ModularPipelineOrchestrator()
        result_ctx = orchestrator.run(ctx)
        self.assertIsNotNone(result_ctx)
        self.assertEqual(len(result_ctx.indicators_df), 1)

    def test_unified_db_sqlite_fallback(self):
        os.environ["DB_ENGINE"] = "sqlite"
        engine = UnifiedDBEngine("test_indicators.db")
        self.assertEqual(engine.engine_type, "sqlite")
        conn = engine.get_connection()
        self.assertIsNotNone(conn)
        engine.release_connection(conn)

    def test_postgres_config(self):
        config = PostgresConfig()
        self.assertEqual(config.port, 5432)
        self.assertIn("postgresql://", config.connection_string())


if __name__ == "__main__":
    unittest.main()
