import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add src and trading_system paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.card_factor import CARDFactorEngine
from src.core.mq_factor import MQFactorEngine
from src.core.rim_valuation import RIMValuationEngine
from src.core.supply_chain import SupplyChainEngine
from src.analysis.regime_detector import MarketRegimeDetector


class TestPhase2QuantWorldClassImprovements(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        # Helper to generate dummy price data
        self.symbols = ["005930", "000660", "AAPL", "NVDA"]
        self.prices_dict = {}
        for s in self.symbols:
            dates = pd.date_range(end="2026-08-18", periods=60, freq="B")
            prices = 100.0 + np.cumsum(np.random.normal(0, 1.5, size=len(dates)))
            self.prices_dict[s] = pd.DataFrame({
                "Date": dates,
                "Open": prices * 0.99,
                "High": prices * 1.02,
                "Low": prices * 0.98,
                "Close": prices,
                "Volume": np.random.randint(10000, 500000, size=len(dates))
            })

    # -------------------------------------------------------------------------
    # 1. CARDFactorEngine: Multi-Asset Unit Scale & Universal Sector Betas
    # -------------------------------------------------------------------------
    def test_card_factor_gics_and_krx_sector_betas(self):
        """Verify CARDFactorEngine resolves GICS and KRX sectors and handles standardized macro units."""
        engine = CARDFactorEngine()
        sector_map = {
            "005930": "반도체",
            "000660": "전기전자",
            "AAPL": "Information Technology",
            "NVDA": "Semiconductor"
        }
        indicator_df = pd.DataFrame({
            "usdkrw_change": [0.5, 1.2],
            "wti_change": [-1.0, 2.5],
            "vix_raw": [18.0, 26.0]
        })

        scores_df = engine.compute_scores(
            prices_dict=self.prices_dict,
            indicators_df=indicator_df,
            sector_map=sector_map
        )

        self.assertFalse(scores_df.empty)
        self.assertEqual(len(scores_df), len(self.symbols))
        self.assertIn("card_score", scores_df.columns)
        for val in scores_df["card_score"]:
            self.assertTrue(0.0 <= val <= 1.0)

    def test_card_factor_5day_macro_temporal_alignment(self):
        """V6-21: Verify CARDFactorEngine calculates 5-day rolling macro changes when indicator_df has >= 5 rows."""
        engine = CARDFactorEngine()
        # Macro dataframe with 10 rows: USDKRW daily change 0.2% per day -> 5-day sum = 1.0%
        macro_df = pd.DataFrame({
            "usdkrw_change": [0.2] * 10,
            "wti_change": [0.5] * 10,
            "vix_raw": [20.0] * 10
        })

        scores_df = engine.compute_scores(
            prices_dict=self.prices_dict,
            indicators_df=macro_df
        )

        self.assertFalse(scores_df.empty)
        self.assertEqual(len(scores_df), len(self.symbols))
        for val in scores_df["card_score"]:
            self.assertTrue(0.0 <= val <= 1.0)


    # -------------------------------------------------------------------------
    # 2. MQFactorEngine: Universal Ingestion of fundamentals_dict
    # -------------------------------------------------------------------------
    def test_mq_factor_fundamentals_dict_ingestion(self):
        """Verify MQFactorEngine extracts metrics from fundamentals_dict without explicit features_df."""
        engine = MQFactorEngine()
        fundamentals_dict = {
            "005930": {"operating_margin": 0.18, "roe": 0.15, "eps_growth_1y": 0.25},
            "000660": {"operating_margin": 0.28, "roe": 0.22, "eps_growth_1y": 0.45},
            "AAPL": {"operating_margin": 0.30, "roe": 0.80, "eps_growth_1y": 0.15},
            "NVDA": {"operating_margin": 0.55, "roe": 0.90, "eps_growth_1y": 1.20},
        }

        # Call with fundamentals_dict only (features_df is None)
        scores_df = engine.compute_scores(
            prices_dict=self.prices_dict,
            fundamentals_dict=fundamentals_dict
        )

        self.assertFalse(scores_df.empty)
        self.assertEqual(len(scores_df), len(self.symbols))
        self.assertIn("mq_score", scores_df.columns)
        for val in scores_df["mq_score"]:
            self.assertTrue(0.0 <= val <= 1.0)
        # NVDA with massive ROE, margin and momentum should rank highest
        nvda_score = float(scores_df[scores_df["symbol"] == "NVDA"]["mq_score"].iloc[0])
        self.assertGreater(nvda_score, 0.60)

    # -------------------------------------------------------------------------
    # 3. RIMValuationEngine: Dynamic Input Reconstruction
    # -------------------------------------------------------------------------
    def test_rim_valuation_input_reconstruction(self):
        """Verify RIMValuationEngine builds valuation DataFrame from fundamentals_dict & prices_dict."""
        engine = RIMValuationEngine()
        fundamentals_dict = {
            "005930": {"bps": 55000.0, "roe": 0.14, "operating_income": 40000000, "net_income": 35000000, "market": "KOSPI"},
            "000660": {"bps": 95000.0, "roe": 0.22, "operating_income": 20000000, "net_income": 18000000, "market": "KOSPI"},
            "AAPL": {"bps": 5.0, "roe": 0.85, "operating_income": 120000, "net_income": 100000, "market": "SP500"},
            "NVDA": {"bps": 20.0, "roe": 0.70, "operating_income": 80000, "net_income": 70000, "market": "SP500"},
        }

        scores_df = engine.compute_scores(
            prices_dict=self.prices_dict,
            fundamentals_dict=fundamentals_dict
        )

        self.assertFalse(scores_df.empty)
        self.assertEqual(len(scores_df), len(self.symbols))
        self.assertIn("rim_score", scores_df.columns)
        for val in scores_df["rim_score"].dropna():
            self.assertTrue(0.0 <= val <= 1.0)

    # -------------------------------------------------------------------------
    # 4. SupplyChainEngine: Universal Universe Fallback
    # -------------------------------------------------------------------------
    def test_supply_chain_universe_fallback(self):
        """Verify SupplyChainEngine auto-constructs symbol universe when universe is omitted."""
        engine = SupplyChainEngine()
        scores_df = engine.compute_scores(prices_dict=self.prices_dict)

        self.assertFalse(scores_df.empty)
        self.assertEqual(len(scores_df), len(self.symbols))
        self.assertIn("supply_chain_score", scores_df.columns)
        for val in scores_df["supply_chain_score"]:
            self.assertTrue(0.0 <= val <= 1.0)

    # -------------------------------------------------------------------------
    # 5. MarketRegimeDetector: Forward-Looking VIX Hybrid Volatility
    # -------------------------------------------------------------------------
    def test_regime_detector_vix_forward_looking_high_vol(self):
        """Verify MarketRegimeDetector detects HIGH_VOL when VIX >= 20.0 even with low realized return std."""
        detector = MarketRegimeDetector()
        # Create stable SP500 with zero volatility but high VIX
        dates = pd.date_range(end="2026-08-18", periods=40, freq="B")
        ind_df = pd.DataFrame({
            "sp500_change": [0.01] * 40,
            "vix_raw": [24.5] * 40
        }, index=dates)

        res = detector.predict_2d_regime(ind_df)
        self.assertEqual(res["volatility_label"], "HIGH_VOL")
        self.assertIn("HIGH_VOL", res["combo_label"])


if __name__ == "__main__":
    unittest.main()
