"""
test_modular_pipeline.py — Unit tests for Modular Pipeline Package (DataFetcher, Trainer, Predictor, Reporter, Orchestrator)
"""

import os
import tempfile
import unittest
from pathlib import Path
import pandas as pd

from src.pipeline import (
    PipelineContext,
    PipelineDataFetcher,
    PipelinePredictor,
    PipelineReporter,
    ModularPipelineOrchestrator,
)
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

    def test_data_fetcher_build_map(self):
        fetcher = PipelineDataFetcher()
        universe = pd.DataFrame([
            {"symbol": "AAPL", "market": "SP500"},
            {"symbol": "005930", "market": "KOSPI"},
        ])
        m_map = fetcher.build_symbol_market_map(universe)
        self.assertEqual(m_map.get("AAPL"), "SP500")
        self.assertEqual(m_map.get("005930"), "KOSPI")

    def test_predictor_empty_inputs(self):
        predictor = PipelinePredictor()
        results = predictor.run_all_strategy_inference(
            symbols=["AAPL"],
            prices_dict={},
            indicator_df=pd.DataFrame(),
            universe=pd.DataFrame(),
            prediction_model=None,
            vcp_ml_predictor=None,
        )
        self.assertIsInstance(results, dict)

    def test_reporter_export(self):
        reporter = PipelineReporter()
        with tempfile.TemporaryDirectory() as tmp_dir:
            ens_df = pd.DataFrame([{"symbol": "AAPL", "name": "Apple", "ensemble_score": 85.0, "ensemble_expected_return": 12.5}])
            files = reporter.export_text_predictions(
                output_dir=Path(tmp_dir),
                ensemble_df=ens_df,
                coverage_report_text="Coverage: 100%",
                market_label="TEST"
            )
            self.assertEqual(len(files), 2)
            self.assertTrue(files[0].exists())

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
