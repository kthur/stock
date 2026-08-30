import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add src and trading_system paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.intraday_stop_loss import IntradayStopLossEngine
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestWorldClassTraderReturnEnhancements(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        self.scorer = EnsembleScoringEngine()
        self.allocator = PortfolioAllocator()
        self.stop_engine = IntradayStopLossEngine(atr_multiplier=2.5)
        self.oms = ExecutionOMSEngine(db_path=":memory:")

    # -------------------------------------------------------------------------
    # 1. EnsembleScoringEngine: Quadruple/Triple Confluence & Alpha Sleeves
    # -------------------------------------------------------------------------
    def test_quadruple_and_triple_confluence_alpha_boost(self):
        """Verify Quadruple and Triple Confluence super-linear alpha boosts."""
        # Create a 10-symbol dataframe
        symbols = [f"SYM_{i:02d}" for i in range(10)]
        df = pd.DataFrame({
            "symbol": symbols,
            "market": ["SP500"] * 10,
            "close": [100.0] * 10,
            "volume": [1000000] * 10,
            # Symbol 0: Quadruple confluence (Valuation + Momentum + Flow + Catalyst)
            "rim_score": [0.85, 0.85, 0.85, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40],
            "mq_score": [0.80, 0.80, 0.40, 0.80, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40],
            "order_flow_score": [0.75, 0.75, 0.75, 0.40, 0.75, 0.40, 0.40, 0.40, 0.40, 0.40],
            "supply_chain_score": [0.70, 0.40, 0.70, 0.70, 0.40, 0.40, 0.40, 0.40, 0.40, 0.40],
            "operating_margin": [0.20] * 10,
            "roe": [0.20] * 10,
        })

        scores_df = self.scorer.calculate_ensemble_score(
            scores_df=df,
            regime="BULL_LOW_VOL"
        )

        self.assertFalse(scores_df.empty)
        self.assertIn("ensemble_score", scores_df.columns)
        self.assertIn("alpha_sleeve", scores_df.columns)

        # Symbol 0 (Quadruple) should have the highest score
        s0_score = float(scores_df[scores_df["symbol"] == "SYM_00"]["ensemble_score"].iloc[0])
        s1_score = float(scores_df[scores_df["symbol"] == "SYM_01"]["ensemble_score"].iloc[0])
        s5_score = float(scores_df[scores_df["symbol"] == "SYM_05"]["ensemble_score"].iloc[0])

        self.assertGreater(s0_score, s1_score)
        self.assertGreater(s1_score, s5_score)
        self.assertGreater(s0_score, 0.50)

        # Verify alpha sleeve values are valid
        valid_sleeves = {"SLOW", "MEDIUM", "FAST"}
        for slv in scores_df["alpha_sleeve"]:
            self.assertIn(slv, valid_sleeves)

    # -------------------------------------------------------------------------
    # 2. PortfolioAllocator: Top-K Concentration & Fractional Kelly Sizing
    # -------------------------------------------------------------------------
    def test_top_k_concentration_eliminates_dilution_drag(self):
        """Verify Top-K concentration focuses capital on top conviction assets and sets tail to 0."""
        # 50 assets
        symbols = [f"STK_{i:02d}" for i in range(50)]
        # Decreasing expected returns from 0.40 down to 0.01
        mu = pd.Series(np.linspace(0.40, 0.01, 50), index=symbols)
        vols = pd.Series(np.full(50, 0.02), index=symbols)

        # Allocate with top_k_concentration=15
        weights = self.allocator.allocate_quarter_kelly(
            expected_returns=mu,
            volatilities=vols,
            max_weight=0.15,
            top_k_concentration=15
        )

        self.assertEqual(len(weights), 50)
        # Sum of weights should be <= 1.0
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)

        # First 15 should have non-zero weights
        for s in symbols[:15]:
            self.assertGreater(weights[s], 0.0)

        # 16th to 50th should be exactly 0.0
        for s in symbols[15:]:
            self.assertEqual(weights[s], 0.0)

    # -------------------------------------------------------------------------
    # 3. IntradayStopLossEngine: Monotonic Ratchet ATR Dynamic Trailing Stop
    # -------------------------------------------------------------------------
    def test_intraday_atr_trailing_stop_ratchet(self):
        """Verify ATR trailing stop ratchets upwards with price and triggers stop only on peak pullback."""
        engine = IntradayStopLossEngine(atr_multiplier=2.5)

        # Step 1: Initial entry at 100 with ATR=2.0 -> stop should be at 100 - 2.5*2 = 95.0
        sig1 = engine.evaluate("AAPL", {"current_price": 100.0, "atr": 2.0})
        self.assertFalse(sig1.triggered)
        self.assertEqual(engine._symbol_stops["AAPL"], 95.0)

        # Step 2: Price rallies to 120 with ATR=2.0 -> stop should ratchet up to 120 - 2.5*2 = 115.0
        sig2 = engine.evaluate("AAPL", {"current_price": 120.0, "atr": 2.0})
        self.assertFalse(sig2.triggered)
        self.assertEqual(engine._symbol_stops["AAPL"], 115.0)

        # Step 3: Price drops slightly to 118 with ATR=2.0 -> stop remains ratcheted at 115.0 (monotonic)
        sig3 = engine.evaluate("AAPL", {"current_price": 118.0, "atr": 2.0})
        self.assertFalse(sig3.triggered)
        self.assertEqual(engine._symbol_stops["AAPL"], 115.0)

        # Step 4: Price crashes to 114 (< 115.0) -> triggers dynamic ATR trailing stop breach
        sig4 = engine.evaluate("AAPL", {"current_price": 114.0, "atr": 2.0})
        self.assertTrue(sig4.triggered)
        self.assertIn("DYNAMIC_ATR_TRAILING_BREACH", sig4.reason)

    # -------------------------------------------------------------------------
    # 4. ExecutionOMSEngine: Midpoint Peg & Almgren-Chriss Slicing
    # -------------------------------------------------------------------------
    def test_midpoint_peg_limit_price_and_almgren_chriss(self):
        """Verify Midpoint Peg limit price calculation and Almgren-Chriss optimal trajectory."""
        # Test Midpoint Peg price: Bid=100.0, Ask=100.20 -> Midpoint=100.10
        peg_price = self.oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=100.0,
            ask_price=100.20,
            spread=0.20,
            alpha_urgency=0.50,
            action="BUY"
        )
        self.assertAlmostEqual(peg_price, 100.10, places=2)

        # Test Almgren-Chriss volume slicing
        slices = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=10000,
            adv=1_000_000.0,
            daily_volatility=0.02,
            strategy_tier="fast",
            n_slices=5
        )
        self.assertEqual(len(slices), 5)
        self.assertEqual(sum(slices), 10000)
        # Front-loaded for positive risk aversion
        self.assertGreaterEqual(slices[0], slices[-1])


if __name__ == "__main__":
    unittest.main()
