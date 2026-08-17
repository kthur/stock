"""Phase 5: Dynamic Strategy Registry Architecture Unit Tests."""

import unittest
import pandas as pd
import numpy as np

from src.core.strategy_registry import get_registry, StrategyMeta, StrategyRegistry
from src.core.base_strategy import BaseStrategyEngine
from src.ai.ml_strategy_adapters import RegressionStrategyAdapter, SurgeStrategyAdapter, VCPMLStrategyAdapter
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer


class TestPhase5StrategyRegistry(unittest.TestCase):
    def setUp(self):
        import sys
        from pathlib import Path
        cur_file = Path(__file__).resolve()
        ts_dir = str(cur_file.parent.parent)
        if ts_dir not in sys.path:
            sys.path.insert(0, ts_dir)

        self.registry = get_registry()
        self.registry.auto_discover(["src.core", "src.ai"])

    def test_registry_auto_discovery(self):
        """Test auto-discovery loads all registered strategies."""
        all_strats = self.registry.get_all()
        self.assertGreaterEqual(len(all_strats), 15, "Should auto-discover registered strategies")

        # Verify key strategy IDs exist
        strat_ids = self.registry.get_all_ids()
        self.assertIn("regression", strat_ids)
        self.assertIn("surge", strat_ids)
        self.assertIn("stat_arb", strat_ids)
        self.assertIn("microstructure", strat_ids)
        self.assertIn("sector_rotation", strat_ids)

    def test_standalone_strategy_flag(self):
        """Test standalone strategies (e.g. Microstructure) are marked is_standalone=True."""
        item = self.registry.get("microstructure")
        self.assertIsNotNone(item)
        _, meta = item
        self.assertTrue(meta.is_standalone, "Microstructure should be marked is_standalone=True")

    def test_ml_adapters(self):
        """Test ML strategy adapters inherit BaseStrategyEngine and handle empty models gracefully."""
        reg_adapter = RegressionStrategyAdapter(model_instance=None)
        res_df = reg_adapter.compute_scores(prices_dict={})
        self.assertIn("symbol", res_df.columns)
        self.assertIn("reg_score", res_df.columns)

        surge_adapter = SurgeStrategyAdapter(model_instance=None)
        surge_df = surge_adapter.compute_scores(prices_dict={})
        self.assertIn("symbol", surge_df.columns)
        self.assertIn("surge_score", surge_df.columns)

        vcp_adapter = VCPMLStrategyAdapter(model_instance=None)
        vcp_df = vcp_adapter.compute_scores(prices_dict={})
        self.assertIn("symbol", vcp_df.columns)
        self.assertIn("vcp_ml_score", vcp_df.columns)

    def test_ensemble_dynamic_base_weights(self):
        """Test EnsembleScoringEngine dynamically loads strategy baseline weights."""
        scorer = EnsembleScoringEngine()
        weights = scorer.get_base_weights(regime="SIDEWAYS_LOW_VOL")

        self.assertIn("regression", weights)
        self.assertIn("stat_arb", weights)
        self.assertIn("microstructure", weights)
        self.assertEqual(weights["microstructure"], 0.0, "Microstructure should have 0.0 weight in ensemble")
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=5)

    def test_coverage_analyzer_dynamic_strategies(self):
        """Test StrategyCoverageAnalyzer dynamically pulls registered strategies and score columns."""
        analyzer = StrategyCoverageAnalyzer()
        self.assertGreaterEqual(len(analyzer.strategies), 15)

        sample_df = pd.DataFrame({
            "symbol": ["005930", "000660"],
            "reg_score": [0.8, 0.7],
            "stat_arb_score": [0.5, 0.6],
        })
        rep = analyzer.analyze_coverage(sample_df)
        self.assertIn("total_symbols", rep)
        self.assertEqual(rep["total_symbols"], 2)


if __name__ == "__main__":
    unittest.main()
