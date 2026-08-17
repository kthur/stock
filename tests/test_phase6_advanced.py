"""Phase 6 Advanced Quantitative Systems Unit Tests."""

import unittest
import pandas as pd
import numpy as np

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.core.hft_engine import MicrostructureImbalanceEngine
from src.risk.risk_manager import CrisisDetector, CrisisLevel
from src.pipeline.reporter import PipelineReporter
from src.core.strategy_registry import get_registry


class TestPhase6AdvancedSystems(unittest.TestCase):
    def setUp(self):
        self.registry = get_registry()
        self.registry.auto_discover(["src.core", "src.ai"])

    def test_strategy_correlation_penalty(self):
        """Test Gram-Schmidt style correlation penalty down-weights highly collinear strategy pairs."""
        scorer = EnsembleScoringEngine()
        initial_weights = {
            "regression": 0.50,
            "surge": 0.50,
        }

        # Create dummy scores DataFrame with high correlation (r > 0.9)
        np.random.seed(42)
        base = np.random.randn(100)
        scores_df = pd.DataFrame({
            "reg_score": base + np.random.randn(100) * 0.01,
            "surge_score": base + np.random.randn(100) * 0.01,
        })

        penalized_weights = scorer.apply_correlation_orthogonalization_penalty(
            initial_weights,
            scores_df=scores_df,
            correlation_threshold=0.65,
            penalty_factor=0.5,
        )

        self.assertEqual(len(penalized_weights), 2)
        self.assertAlmostEqual(sum(penalized_weights.values()), 1.0, places=5)
        # One of the two collinear strategies should be down-weighted
        self.assertNotEqual(penalized_weights["regression"], 0.50)

    def test_hft_friction_deduction(self):
        """Test MicrostructureImbalanceEngine includes friction deduction and outputs valid columns."""
        engine = MicrostructureImbalanceEngine()
        dummy_universe = pd.DataFrame([{"symbol": "005930", "name": "삼성전자", "market": "KOSPI"}])
        dummy_prices = {
            "005930": pd.DataFrame({
                "high": [70000, 71000, 72000, 73000, 74000],
                "low": [69000, 70000, 71000, 72000, 73000],
                "close": [69500, 70500, 71500, 72500, 73800],
                "volume": [1000000, 1200000, 1100000, 1300000, 2000000],
            })
        }

        res_df = engine.compute_scores(df_prices=dummy_prices, universe=dummy_universe)
        self.assertIn("microstructure_score", res_df.columns)
        self.assertIn("estimated_friction", res_df.columns)
        score_val = res_df.iloc[0]["microstructure_score"]
        self.assertGreaterEqual(score_val, 0.0)
        self.assertLessEqual(score_val, 1.0)

    def test_macro_crisis_soft_gating(self):
        """Test CrisisDetector target cash allocation ratio per crisis level."""
        detector = CrisisDetector()

        detector.crisis_level = CrisisLevel.NONE
        self.assertEqual(detector.get_target_cash_ratio(), 0.0)

        detector.crisis_level = CrisisLevel.WATCH
        self.assertEqual(detector.get_target_cash_ratio(), 0.15)

        detector.crisis_level = CrisisLevel.ACTIVE
        self.assertEqual(detector.get_target_cash_ratio(), 0.35)

        detector.crisis_level = CrisisLevel.SEVERE
        self.assertEqual(detector.get_target_cash_ratio(), 0.50)

    def test_pipeline_reporter_dynamic_count(self):
        """Test PipelineReporter dynamically retrieves StrategyRegistry strategy count."""
        reporter = PipelineReporter()
        count = self.registry.get_strategy_count()
        self.assertGreaterEqual(count, 15)


if __name__ == "__main__":
    unittest.main()
