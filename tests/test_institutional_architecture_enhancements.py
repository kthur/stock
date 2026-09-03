import unittest
import numpy as np
import pandas as pd

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.execution.smart_order_router import SmartOrderRouter
from src.core.opening_auction_arbitrage import OpeningAuctionArbitrageEngine
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer
from src.config import MARKET_COST_REGISTRY


class TestInstitutionalArchitectureEnhancements(unittest.TestCase):
    """
    Unit tests for institutional architecture enhancements:
    - FX matrix alignment without lookahead bias
    - Multi-venue Global Smart Order Routing
    - Opening auction arbitrage symbol mapping
    - Transaction cost registry consistency
    - Coverage analyzer dynamic registry auto-discovery
    """

    def setUp(self):
        self.allocator = UnifiedPortfolioAllocator()
        self.sor = SmartOrderRouter()
        self.auction_engine = OpeningAuctionArbitrageEngine()
        self.coverage_analyzer = StrategyCoverageAnalyzer()

    def test_fx_matrix_alignment_causality(self):
        """Verify compute_returns_matrix aligns FX series without backward lookahead leakage."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        prices_dict = {
            "AAPL": pd.DataFrame({"Close": [150.0 + i for i in range(20)]}, index=dates),
            "005930.KS": pd.DataFrame({"Close": [70000.0 + i * 500 for i in range(20)]}, index=dates),
        }
        # FX series starts 5 days later
        fx_series = pd.Series([1350.0 + i for i in range(15)], index=dates[5:])

        returns_df, valid_syms = self.allocator.compute_returns_matrix(
            symbols=["AAPL", "005930.KS"],
            prices_dict=prices_dict,
            lookback=20,
            fx_series=fx_series,
            base_currency="KRW"
        )
        self.assertIn("AAPL", valid_syms)
        self.assertIn("005930.KS", valid_syms)
        self.assertFalse(returns_df.empty)
        self.assertFalse(returns_df.isna().any().any())

    def test_smart_order_router_global_destinations(self):
        """Verify SmartOrderRouter correctly routes orders across global exchanges."""
        kr_dest = self.sor.determine_destination("005930.KS", market="KOSPI")
        self.assertEqual(kr_dest["market_region"], "KRX")
        self.assertEqual(kr_dest["primary_broker"], "korea_investment")
        self.assertEqual(kr_dest["venue"], "KRX_ATS_NEXTRADE")

        us_dest = self.sor.determine_destination("NVDA", market="NASDAQ")
        self.assertEqual(us_dest["market_region"], "US")
        self.assertEqual(us_dest["primary_broker"], "interactive_brokers")
        self.assertEqual(us_dest["venue"], "US_SMART_DMA")

        jp_dest = self.sor.determine_destination("7203.T", market="JAPAN_TSE")
        self.assertEqual(jp_dest["market_region"], "JP")
        self.assertEqual(jp_dest["venue"], "TSE_DIRECT")

        hk_dest = self.sor.determine_destination("0700.HK", market="HKEX")
        self.assertEqual(hk_dest["market_region"], "HK")
        self.assertEqual(hk_dest["venue"], "HKEX_DIRECT")

        eu_dest = self.sor.determine_destination("SAP.DE", market="EUROPE_STOXX")
        self.assertEqual(eu_dest["market_region"], "EU")
        self.assertEqual(eu_dest["venue"], "EURONEXT_XETRA")

        ca_dest = self.sor.determine_destination("SHOP.TO", market="CANADA_TSX")
        self.assertEqual(ca_dest["market_region"], "CA")
        self.assertEqual(ca_dest["venue"], "TSX_DIRECT")

    def test_opening_auction_arbitrage_symbol_mapping(self):
        """Verify OpeningAuctionArbitrageEngine correctly resolves semiconductor theme for .KS symbols."""
        us_returns = {"NVDA": 0.04, "SPY": 0.01, "AAPL": 0.02, "TSLA": 0.03}
        gap_plain = self.auction_engine.compute_expected_opening_gap(us_returns, usdkrw_overnight_return=0.005, symbol="005930")
        gap_suffix = self.auction_engine.compute_expected_opening_gap(us_returns, usdkrw_overnight_return=0.005, symbol="005930.KS")
        self.assertEqual(gap_plain, gap_suffix, "Plain symbol and .KS symbol must compute identical expected opening gaps")
        self.assertGreater(gap_suffix, 0.03, "Semiconductor high beta must drive opening gap above 3%")

    def test_market_cost_registry_tax_rates(self):
        """Verify STT and transaction cost parameters in MARKET_COST_REGISTRY."""
        self.assertEqual(MARKET_COST_REGISTRY["KOSPI"]["stt"], 0.0015)
        self.assertEqual(MARKET_COST_REGISTRY["KOSDAQ"]["stt"], 0.0015)
        self.assertEqual(MARKET_COST_REGISTRY["NASDAQ"]["stt"], 0.00003)
        self.assertEqual(MARKET_COST_REGISTRY["SP500"]["stt"], 0.00003)

    def test_coverage_analyzer_registered_strategy_count(self):
        """Verify StrategyCoverageAnalyzer dynamically discovers all 37 non-standalone strategies."""
        self.assertEqual(self.coverage_analyzer.strategy_count, 37)
        self.assertNotIn("opening_auction_arbitrage", self.coverage_analyzer.strategies)
        self.assertIn("dual_correction", self.coverage_analyzer.strategies)
        self.assertIn("index_rebalance", self.coverage_analyzer.strategies)
        self.assertIn("overnight_gap_reversal", self.coverage_analyzer.strategies)


if __name__ == "__main__":
    unittest.main()
