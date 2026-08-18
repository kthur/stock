import os
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "trading_system"))
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
from src.config import TradingConfig
from src.data_layer.global_market import GLOBAL_INDICES, FX_PAIRS, GlobalMarketClient
from src.core.supply_chain import LEAD_CUSTOMER_MAP, SupplyChainEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine
from run_pipeline import format_canonical_yf_symbol, _MARKET_SUFFIX_MAP


class TestMultiMarketExpansion(unittest.TestCase):
    """Test suite for global multi-market expansion (China, Japan, India, Europe, Vietnam, Taiwan, Australia, Brazil, etc.)"""

    def test_ticker_formatting_across_markets(self):
        """Test that format_canonical_yf_symbol produces valid yfinance tickers for all international exchanges."""
        # Korea
        self.assertEqual(format_canonical_yf_symbol("005930", "KOSPI"), "005930.KS")
        self.assertEqual(format_canonical_yf_symbol("035720", "KOSDAQ"), "035720.KQ")
        self.assertEqual(format_canonical_yf_symbol("005930.KS", "KOSPI"), "005930.KS")

        # US
        self.assertEqual(format_canonical_yf_symbol("AAPL", "SP500"), "AAPL")
        self.assertEqual(format_canonical_yf_symbol("BRK.B", "SP500"), "BRK-B")

        # China (SSE, SZSE)
        self.assertEqual(format_canonical_yf_symbol("600519", "CHINA_SSE"), "600519.SS")
        self.assertEqual(format_canonical_yf_symbol("002594", "CHINA_SZSE"), "002594.SZ")

        # Japan (TSE)
        self.assertEqual(format_canonical_yf_symbol("7203", "JAPAN_TSE"), "7203.T")
        self.assertEqual(format_canonical_yf_symbol("7203.T", "JAPAN_TSE"), "7203.T")

        # India (NSE)
        self.assertEqual(format_canonical_yf_symbol("RELIANCE", "INDIA_NSE"), "RELIANCE.NS")
        self.assertEqual(format_canonical_yf_symbol("RELIANCE.NS", "INDIA_NSE"), "RELIANCE.NS")

        # Europe (STOXX / DAX / Euronext / LSE)
        self.assertEqual(format_canonical_yf_symbol("SAP.DE", "EUROPE_STOXX"), "SAP.DE")
        self.assertEqual(format_canonical_yf_symbol("MC.PA", "EUROPE_STOXX"), "MC.PA")
        self.assertEqual(format_canonical_yf_symbol("ASML.AS", "EUROPE_STOXX"), "ASML.AS")
        self.assertEqual(format_canonical_yf_symbol("AZN.L", "EUROPE_STOXX"), "AZN.L")

        # Vietnam (HOSE)
        self.assertEqual(format_canonical_yf_symbol("VNM", "VIETNAM_HOSE"), "VNM.VN")
        self.assertEqual(format_canonical_yf_symbol("VNM.VN", "VIETNAM_HOSE"), "VNM.VN")

        # Taiwan (TWSE)
        self.assertEqual(format_canonical_yf_symbol("2330", "TAIWAN_TWSE"), "2330.TW")

        # Australia (ASX)
        self.assertEqual(format_canonical_yf_symbol("BHP", "AUSTRALIA_ASX"), "BHP.AX")

        # Brazil (B3)
        self.assertEqual(format_canonical_yf_symbol("VALE3", "BRAZIL_B3"), "VALE3.SA")

        # Hong Kong (HKEX)
        self.assertEqual(format_canonical_yf_symbol("700", "HKEX"), "0700.HK")
        self.assertEqual(format_canonical_yf_symbol("0700.HK", "HKEX"), "0700.HK")

        # Singapore (SGX)
        self.assertEqual(format_canonical_yf_symbol("D05", "SINGAPORE_SGX"), "D05.SI")

        # Canada (TSX)
        self.assertEqual(format_canonical_yf_symbol("RY", "CANADA_TSX"), "RY.TO")

    def test_global_macro_indices_and_fx(self):
        """Test that GLOBAL_INDICES and FX_PAIRS include all new target countries."""
        # Key Global Indices
        self.assertIn("^N225", GLOBAL_INDICES)     # Japan
        self.assertIn("000300.SS", GLOBAL_INDICES) # China CSI 300
        self.assertIn("^NSEI", GLOBAL_INDICES)     # India Nifty 50
        self.assertIn("^STOXX50E", GLOBAL_INDICES) # Europe STOXX 50
        self.assertIn("^TWII", GLOBAL_INDICES)     # Taiwan TAIEX
        self.assertIn("^AXJO", GLOBAL_INDICES)     # Australia ASX 200
        self.assertIn("^BVSP", GLOBAL_INDICES)     # Brazil Bovespa
        self.assertIn("^STI", GLOBAL_INDICES)      # Singapore STI
        self.assertIn("^GSPTSE", GLOBAL_INDICES)   # Canada TSX

        # Key FX Pairs
        self.assertIn("USDKRW=X", FX_PAIRS)
        self.assertIn("USDJPY=X", FX_PAIRS)
        self.assertIn("USDCNY=X", FX_PAIRS)
        self.assertIn("USDINR=X", FX_PAIRS)
        self.assertIn("USDVND=X", FX_PAIRS)
        self.assertIn("USDTWD=X", FX_PAIRS)
        self.assertIn("USDAUD=X", FX_PAIRS)
        self.assertIn("USDBRL=X", FX_PAIRS)
        self.assertIn("USDHKD=X", FX_PAIRS)
        self.assertIn("USDSGD=X", FX_PAIRS)

    def test_global_supply_chain_nodes(self):
        """Test global semiconductor and tech hardware supply chain relationships."""
        self.assertIn("2330.TW", LEAD_CUSTOMER_MAP)
        self.assertIn("NVDA", LEAD_CUSTOMER_MAP["2330.TW"])
        self.assertIn("8035.T", LEAD_CUSTOMER_MAP)
        self.assertIn("2330.TW", LEAD_CUSTOMER_MAP["8035.T"])
        self.assertIn("ASML.AS", LEAD_CUSTOMER_MAP)
        self.assertIn("BHP.AX", LEAD_CUSTOMER_MAP)
        self.assertIn("VALE3.SA", LEAD_CUSTOMER_MAP)

    def test_microstructure_friction_multi_market(self):
        """Test that ensemble scorer computes proper market-specific friction costs."""
        cfg = TradingConfig()
        scorer = EnsembleScoringEngine(config=cfg)

        test_data = pd.DataFrame([
            {'symbol': '005930', 'name': 'Samsung', 'market': 'KOSPI', 'close': 80000.0, 'volume': 10000000.0, 'reg_score': 0.8},
            {'symbol': 'AAPL', 'name': 'Apple', 'market': 'SP500', 'close': 200.0, 'volume': 50000000.0, 'reg_score': 0.8},
            {'symbol': '7203.T', 'name': 'Toyota', 'market': 'JAPAN_TSE', 'close': 3000.0, 'volume': 20000000.0, 'reg_score': 0.8},
            {'symbol': '600519.SS', 'name': 'Moutai', 'market': 'CHINA_SSE', 'close': 1600.0, 'volume': 5000000.0, 'reg_score': 0.8},
            {'symbol': '2330.TW', 'name': 'TSMC', 'market': 'TAIWAN_TWSE', 'close': 1000.0, 'volume': 30000000.0, 'reg_score': 0.8},
            {'symbol': 'BHP.AX', 'name': 'BHP', 'market': 'AUSTRALIA_ASX', 'close': 40.0, 'volume': 8000000.0, 'reg_score': 0.8},
        ])

        res = scorer.combine_predictions(reg_df=test_data)
        self.assertIn('ensemble_score', res.columns)
        self.assertIn('ensemble_expected_return', res.columns)
        self.assertEqual(len(res), 6)
        # Verify scores are bounded and positive
        self.assertTrue((res['ensemble_score'] >= 0.0).all())
        self.assertTrue((res['ensemble_score'] <= 1.0).all())
        self.assertTrue((res['ensemble_expected_return'] >= 0.0).all())


if __name__ == "__main__":
    unittest.main()
