"""
tests/test_symbol_inspector.py
Unit and Integration Tests for Symbol Inspector & Exclusion Diagnostics.
"""

import os
import sys
import subprocess
from pathlib import Path
import unittest
import pandas as pd
import numpy as np

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
if str(_root / "trading_system") not in sys.path:
    sys.path.insert(0, str(_root / "trading_system"))

from src.analysis.symbol_inspector import SymbolInspector, SymbolDiagnosticResult


class TestSymbolInspector(unittest.TestCase):
    """Tests 4-stage exclusion diagnostic engine and CLI inspector."""

    def setUp(self):
        self.inspector = SymbolInspector()

    def test_normalize_symbol(self):
        """Verify symbol normalization and market detection."""
        sym_krx, mkt_krx = SymbolInspector.normalize_symbol("005930.KS")
        self.assertEqual(sym_krx, "005930")
        self.assertEqual(mkt_krx, "KOSPI")

        sym_short, mkt_short = SymbolInspector.normalize_symbol("5930")
        self.assertEqual(sym_short, "005930")

        sym_us, mkt_us = SymbolInspector.normalize_symbol("tsla")
        self.assertEqual(sym_us, "TSLA")
        self.assertEqual(mkt_us, "US")

    def test_inspect_unlisted_symbol(self):
        """Verify that an unlisted symbol is correctly diagnosed as UNIVERSE_NOT_LISTED."""
        res = self.inspector.inspect_symbol("NON_EXISTENT_CO_99999")
        self.assertFalse(res.universe_passed)
        self.assertEqual(res.primary_exclusion_stage, "UNIVERSE")
        self.assertEqual(res.primary_exclusion_reason, "UNIVERSE_NOT_LISTED")
        self.assertIn("등록되어 있지 않습니다", res.detailed_explanation)

    def test_inspect_short_price_history(self):
        """Verify that insufficient price bars (<20) yields INSUFFICIENT_PRICE_HISTORY."""
        fake_u = pd.DataFrame([{
            "symbol": "FAKE_NEW_IPO", "name": "신규상장주", "market": "KOSPI", "sector": "IT", "industry": "Software"
        }])
        res = self.inspector.inspect_symbol("FAKE_NEW_IPO", universe_df=fake_u)
        self.assertTrue(res.universe_passed)
        self.assertFalse(res.price_passed)
        self.assertEqual(res.primary_exclusion_stage, "PRICE")
        self.assertEqual(res.primary_exclusion_reason, "INSUFFICIENT_PRICE_HISTORY")

    def test_inspect_strategy_missing_reasons(self):
        """Verify specific missing factor reason tagging."""
        fake_u = pd.DataFrame([{
            "symbol": "005930", "name": "삼성전자", "market": "KOSPI", "sector": "전기전자", "industry": "반도체"
        }])
        fake_ens = pd.DataFrame([{
            "symbol": "005930",
            "reg_score": 0.65,
            "surge_score": 0.70,
            "stat_arb_score": np.nan,
            "iv_skew_score": np.nan,
            "darkpool_score": np.nan,
            "ensemble_score": 0.58,
            "total_friction_cost": 0.0035,
        }])
        fake_prices = {
            "005930": pd.DataFrame({
                "Close": [70000.0] * 30,
                "Volume": [1000000] * 30
            })
        }
        res = self.inspector.inspect_symbol("005930", universe_df=fake_u, ensemble_df=fake_ens, prices_dict=fake_prices)
        self.assertTrue(res.universe_passed)
        self.assertTrue(res.price_passed)
        self.assertEqual(res.strategy_count_total, 37)
        self.assertGreater(res.strategy_count_valid, 0)
        
        # Check specific reason classifications for Korean stock
        self.assertIn("NO_OPTIONS_CHAIN (한국/옵션 미상장 종목)", res.strategy_factors['iv_skew'].missing_reason)
        self.assertIn("NON_US_MARKET_SCOPE (다크풀 데이터는 미국 시장 전용)", res.strategy_factors['darkpool'].missing_reason)
        self.assertIn("NO_COINTEGRATED_PAIR", res.strategy_factors['stat_arb'].missing_reason)

    def test_format_text_report(self):
        """Verify text report rendering."""
        diag = SymbolDiagnosticResult(
            symbol="005930",
            normalized_symbol="005930",
            name="삼성전자",
            market="KOSPI",
            sector="전기전자",
            universe_passed=True,
            universe_reason="정상 상장 종목",
            price_passed=True,
            price_reason="정상 주가 시계열",
            fundamentals_available=True,
            fundamentals_reason="재무제표 데이터 적재 완료",
            strategy_count_valid=30,
            strategy_count_total=37,
            strategy_coverage_pct=81.1,
            ensemble_scored=True,
            ensemble_score=0.62,
            expected_return_20d=0.025,
            estimated_friction_cost=0.0035,
            net_expected_return=0.0215,
            is_in_portfolio=True,
            portfolio_weight=0.08,
            target_action="BUY",
            primary_exclusion_stage="INCLUDED",
            primary_exclusion_reason="PORTFOLIO_ACTIVE",
            detailed_explanation="포트폴리오 편입 (BUY, 8.00%)"
        )
        report = self.inspector.format_text_report(diag)
        self.assertIn("종목 정밀 진단 리포트", report)
        self.assertIn("삼성전자", report)
        self.assertIn("PASS", report)
        self.assertIn("포트폴리오 편입", report)

    def test_generate_batch_diagnostics(self):
        """Verify batch diagnostics map generation."""
        fake_u = pd.DataFrame([
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"},
            {"symbol": "INVALID_X", "name": "미상장", "market": "KOSPI"},
        ])
        fake_orders = pd.DataFrame([
            {"symbol": "005930", "action": "BUY", "target_weight": 0.10}
        ])
        batch = self.inspector.generate_batch_diagnostics(universe_df=fake_u, order_plans_df=fake_orders)
        self.assertEqual(batch["total_symbols_evaluated"], 2)
        self.assertIn("005930", batch["diagnostics"])
        self.assertIn("INVALID_X", batch["diagnostics"])
        self.assertTrue(batch["diagnostics"]["005930"]["verdict"]["is_included"])
        self.assertFalse(batch["diagnostics"]["INVALID_X"]["verdict"]["is_included"])

    def test_cli_execution(self):
        """Verify CLI inspect_symbol.py subprocess execution."""
        script_path = str(_root / "trading_system" / "inspect_symbol.py")
        res = subprocess.run(
            [sys.executable, script_path, "005930"],
            capture_output=True,
            text=True,
            cwd=str(_root),
            encoding="utf-8"
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("종목 정밀 진단 리포트", res.stdout)
        self.assertIn("005930", res.stdout)


if __name__ == "__main__":
    unittest.main()
