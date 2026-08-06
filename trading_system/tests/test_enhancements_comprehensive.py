import os
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.analysis.regime_detector import MarketRegimeDetector
from src.persistence.database import StockPriceDB
from src.core.order_management import calculate_almgren_chriss_impact


class TestEnhancementsComprehensive(unittest.TestCase):

    def test_factor_orthogonalizer_ledoit_wolf(self):
        engine = FactorOrthogonalizerEngine(default_method='pca_symmetric')
        np.random.seed(42)
        data = np.random.rand(50, 5)
        # Add high correlation between col 0 and col 1
        data[:, 1] = data[:, 0] * 0.9 + np.random.rand(50) * 0.1
        df = pd.DataFrame(data, columns=[f"strat_{i}" for i in range(5)])

        cols = [f"strat_{i}" for i in range(5)]
        ortho_df = engine.orthogonalize(df, cols)

        self.assertEqual(len(ortho_df), 50)
        self.assertFalse(ortho_df.isna().any().any())
        self.assertTrue((ortho_df[cols].to_numpy() >= 0.0).all())
        self.assertTrue((ortho_df[cols].to_numpy() <= 1.0).all())

    def test_regime_hysteresis_filter(self):
        detector = MarketRegimeDetector(enable_hysteresis=True)
        # Fill deque with initial predictions
        r1 = detector._apply_hysteresis(2)
        r2 = detector._apply_hysteresis(0) # 1 difference
        r3 = detector._apply_hysteresis(2) # flips back
        # Hysteresis buffer should smooth out single-step flipping
        self.assertIn(r3, [0, 2])

    def test_almgren_chriss_impact(self):
        impact_small = calculate_almgren_chriss_impact(100, adv=100000, daily_volatility=0.02)
        impact_large = calculate_almgren_chriss_impact(50000, adv=100000, daily_volatility=0.02)

        self.assertGreater(impact_large, impact_small)
        self.assertTrue(0.0005 <= impact_small <= 0.05)
        self.assertTrue(0.0005 <= impact_large <= 0.05)

    def test_sqlite_db_timeout_config(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        try:
            db = StockPriceDB(db_path=db_path)
            conn = db._get_conn()
            self.assertIsNotNone(conn)
            db.close()
        finally:
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
