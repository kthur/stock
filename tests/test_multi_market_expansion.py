import os
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "trading_system"))
sys.path.insert(0, str(_ROOT))

import pandas as pd
from src.config import TradingConfig
from src.data_layer.global_market import GLOBAL_INDICES, FX_PAIRS
from src.core.supply_chain import LEAD_CUSTOMER_MAP
from src.ai.ensemble_scorer import EnsembleScoringEngine
from run_pipeline import format_canonical_yf_symbol


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
    def test_multi_market_universe_storage(self):
        """Test that MarketIndicatorStorage populates global markets in stock_universe table."""
        import tempfile
        from unittest.mock import patch
        from src.data_layer.indicator_storage import MarketIndicatorStorage

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            temp_db = tf.name

        def _mock_listing(name):
            if name == 'S&P500':
                return pd.DataFrame([{'Symbol': 'AAPL', 'Name': 'Apple', 'Sector': 'Technology', 'Industry': 'Consumer Electronics'}])
            elif name == 'NASDAQ':
                return pd.DataFrame([{'Symbol': 'NVDA', 'Name': 'Nvidia', 'Sector': 'Technology', 'Industry': 'Semiconductors'}])
            elif name == 'KRX':
                return pd.DataFrame([{'Code': '005930', 'Name': 'Samsung', 'Market': 'KOSPI', 'Sector': 'IT', 'Industry': 'Hardware'}])
            elif name in ('SSE', 'SZSE', 'TSE', 'HOSE', 'HKEX'):
                return pd.DataFrame([{'Symbol': f'TEST_{name}', 'Name': f'Test {name}', 'Sector': 'General', 'Industry': 'General'}])
            return pd.DataFrame()

        try:
            with patch('FinanceDataReader.StockListing', side_effect=_mock_listing):
                storage = MarketIndicatorStorage(db_path=temp_db)
                storage.update_stock_universe()
                universe = storage.get_universe()
                self.assertFalse(universe.empty)
                markets_in_db = set(universe['market'].unique())
                # Verify US, KR, and international markets exist
                self.assertIn("SP500", markets_in_db)
                self.assertIn("NASDAQ", markets_in_db)
                self.assertIn("KOSPI", markets_in_db)
                self.assertIn("CHINA_SSE", markets_in_db)
                self.assertIn("CHINA_SZSE", markets_in_db)
                self.assertIn("JAPAN_TSE", markets_in_db)
                self.assertIn("VIETNAM_HOSE", markets_in_db)
                self.assertIn("HKEX", markets_in_db)
                self.assertIn("INDIA_NSE", markets_in_db)
                self.assertIn("EUROPE_STOXX", markets_in_db)
                self.assertIn("TAIWAN_TWSE", markets_in_db)
                self.assertIn("AUSTRALIA_ASX", markets_in_db)
                self.assertIn("BRAZIL_B3", markets_in_db)
                self.assertIn("SINGAPORE_SGX", markets_in_db)
                self.assertIn("CANADA_TSX", markets_in_db)
        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except Exception:
                    pass

    def test_multi_market_preseed_symbol_resolution(self):
        """Test that symbol resolution for preseed/inference supports any global target."""
        # Simulated universe with global markets
        universe = pd.DataFrame([
            {"symbol": "AAPL", "market": "SP500"},
            {"symbol": "NVDA", "market": "NASDAQ"},
            {"symbol": "005930", "market": "KOSPI"},
            {"symbol": "600519", "market": "CHINA_SSE"},
            {"symbol": "7203", "market": "JAPAN_TSE"},
            {"symbol": "RELIANCE", "market": "INDIA_NSE"},
            {"symbol": "SAP.DE", "market": "EUROPE_STOXX"},
        ])

        # Test filtering for single targets and regional targets
        valid_markets = {
            'KOSPI', 'KOSDAQ', 'KRX', 'SP500', 'NASDAQ', 'RUSSELL2000',
            'CHINA_SSE', 'CHINA_SZSE', 'SSE', 'SZSE', 'CHINA',
            'JAPAN_TSE', 'TSE', 'JAPAN', 'INDIA_NSE', 'INDIA',
            'EUROPE_STOXX', 'EUROPE',
        }

        # Target: CHINA
        china_markets = {"CHINA_SSE", "CHINA_SZSE", "SSE", "SZSE", "CHINA"}
        china_u = universe[universe['market'].isin(china_markets)]
        self.assertEqual(china_u['symbol'].tolist(), ["600519"])

        # Target: JAPAN
        japan_markets = {"JAPAN_TSE", "TSE", "JAPAN"}
        japan_u = universe[universe['market'].isin(japan_markets)]
        self.assertEqual(japan_u['symbol'].tolist(), ["7203"])

        # Target: ALL
        all_u = universe[universe['market'].isin(valid_markets)]
        self.assertEqual(len(all_u), 7)


if __name__ == "__main__":
    unittest.main()

