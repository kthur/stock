import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.risk.portfolio_allocator import PortfolioAllocator
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.core.opening_auction_arbitrage import OpeningAuctionArbitrageEngine, OPENING_AUCTION_META
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.core.strategy_registry import StrategyRegistry


class TestReturnMaximizationApex(unittest.TestCase):

    def setUp(self):
        self.allocator = PortfolioAllocator()
        self.opening_arb = OpeningAuctionArbitrageEngine()
        self.orthogonalizer = FactorOrthogonalizerEngine()

    # -------------------------------------------------------------------------
    # 1. Higher-Order Cumulant Expansion Kelly Sizing (Skewness & Kurtosis)
    # -------------------------------------------------------------------------
    def test_higher_order_cumulant_kelly_skew_boost(self):
        """Verify that positive return skewness safely boosts optimal Kelly weight."""
        np.random.seed(42)
        symbols = ["SURGE_WINNER", "NORMAL_STOCK", "FAT_TAIL_CRASH"]
        
        # Simulated returns:
        # 1. SURGE_WINNER: strongly right-skewed (+6% spikes)
        r_surge = np.concatenate([np.full(50, 0.005), np.full(10, 0.06)])
        # 2. NORMAL_STOCK: symmetric Gaussian
        r_normal = np.linspace(-0.015, 0.025, 60)
        # 3. FAT_TAIL_CRASH: strongly left-skewed with heavy negative crash spikes (-6% drops)
        r_crash = np.concatenate([np.full(50, 0.015), np.full(10, -0.06)])

        returns_df = pd.DataFrame({
            "SURGE_WINNER": r_surge,
            "NORMAL_STOCK": r_normal,
            "FAT_TAIL_CRASH": r_crash
        })

        expected_returns = pd.Series([0.20, 0.20, 0.20], index=symbols)

        # 1. Standard Quarter-Kelly weights
        base_weights = self.allocator.allocate_quarter_kelly(
            expected_returns=expected_returns,
            volatilities=returns_df.std(),
            max_weight=0.60
        )

        # 2. Higher-Order Cumulant Kelly weights
        higher_weights = self.allocator.allocate_higher_order_cumulant_kelly(
            expected_returns=expected_returns,
            returns_df=returns_df,
            max_weight=0.60
        )

        # Higher-Order Kelly should boost the right-skewed SURGE_WINNER relative to base
        self.assertGreater(higher_weights["SURGE_WINNER"], base_weights["SURGE_WINNER"])
        # Higher-Order Kelly should penalize FAT_TAIL_CRASH
        self.assertLess(higher_weights["FAT_TAIL_CRASH"], higher_weights["SURGE_WINNER"])
        self.assertAlmostEqual(sum(higher_weights.values()), 1.0, places=4)

    # -------------------------------------------------------------------------
    # 2. Kaufman Efficiency (KER) Dynamic Alpha Switching
    # -------------------------------------------------------------------------
    def test_ker_dynamic_alpha_switching(self):
        """Verify KER dynamically switches weights between trend and mean-reversion alphas."""
        base_weights = {
            "regression": 0.20,
            "range_expansion_breakout": 0.20,
            "short_term_reversal": 0.20,
            "stat_arb": 0.20,
            "rim_valuation": 0.20
        }

        # Case A: High KER (0.70) -> Strong Directional Trend
        trend_weights = EnsembleScoringEngine.apply_ker_dynamic_alpha_switching(
            strategy_weights=base_weights,
            ker_value=0.70
        )
        self.assertGreater(trend_weights["range_expansion_breakout"], base_weights["range_expansion_breakout"])
        self.assertLess(trend_weights["short_term_reversal"], base_weights["short_term_reversal"])
        self.assertAlmostEqual(sum(trend_weights.values()), 1.0, places=4)

        # Case B: Low KER (0.15) -> Choppy Mean-Reverting Chop
        reversal_weights = EnsembleScoringEngine.apply_ker_dynamic_alpha_switching(
            strategy_weights=base_weights,
            ker_value=0.15
        )
        self.assertGreater(reversal_weights["short_term_reversal"], base_weights["short_term_reversal"])
        self.assertLess(reversal_weights["range_expansion_breakout"], base_weights["range_expansion_breakout"])
        self.assertAlmostEqual(sum(reversal_weights.values()), 1.0, places=4)

    # -------------------------------------------------------------------------
    # 3. Bessembinder Convex Power-Law Alpha Sizing
    # -------------------------------------------------------------------------
    def test_bessembinder_convex_power_law(self):
        """Verify Bessembinder power law amplifies 90th+ percentile winners while preserving bounds."""
        scores = np.linspace(0.10, 0.95, 50)
        boosted = EnsembleScoringEngine.apply_bessembinder_convex_power_law(
            scores=scores,
            top_percentile=90.0,
            power_gamma=1.60,
            max_boost=0.50
        )

        self.assertEqual(len(boosted), 50)
        self.assertTrue((boosted >= 0.0).all() and (boosted <= 1.0).all())
        
        # Highest score should have received a boost
        p90_idx = int(50 * 0.90)
        self.assertGreater(boosted[-1], scores[-1])
        # Lower half scores should be untouched
        self.assertEqual(boosted[10], scores[10])

    # -------------------------------------------------------------------------
    # 4. Opening Auction Arbitrage Engine (Strategy 35)
    # -------------------------------------------------------------------------
    def test_opening_auction_arbitrage_engine(self):
        """Verify Strategy 35 detects overnight opening gap dislocation and computes alpha score."""
        dates = pd.date_range("2026-08-01", periods=10)
        prices_dict = {
            "005930": pd.DataFrame({"Close": np.linspace(70000, 72000, 10)}, index=dates),
            "000660": pd.DataFrame({"Close": np.linspace(120000, 125000, 10)}, index=dates)
        }

        # US Tech exploded overnight (+3.5% NVDA)
        us_returns = {"NVDA": 0.035, "SPY": 0.015, "AAPL": 0.020, "TSLA": 0.010}
        
        # Pre-market indicative quote for 005930 lagged behind (flat indicative open)
        indicative_opens = {"005930": 72000.0} # Dislocation = positive (undervalued auction)

        scores = self.opening_arb.compute_opening_auction_scores(
            prices_dict=prices_dict,
            us_overnight_returns=us_returns,
            indicative_opens_dict=indicative_opens,
            usdkrw_overnight_return=0.002
        )

        self.assertIn("005930", scores)
        self.assertIn("000660", scores)
        # 005930 should have high alpha score due to unpriced overnight jump
        self.assertGreater(scores["005930"], 0.70)
        self.assertTrue(0.0 <= scores["005930"] <= 1.0)

        # Check registration in StrategyRegistry
        reg = StrategyRegistry()
        self.assertIsNotNone(reg.get("opening_auction_arbitrage"))

    # -------------------------------------------------------------------------
    # 5. Pure Idiosyncratic Alpha Residualization
    # -------------------------------------------------------------------------
    def test_pure_idiosyncratic_alpha_extraction(self):
        """Verify that factor orthogonalizer strips market beta and sector co-movements."""
        np.random.seed(42)
        n_stocks = 30
        symbols = [f"STOCK_{i:02d}" for i in range(n_stocks)]
        
        # Sector assignments
        sectors = pd.Series(
            ["Technology" if i < 10 else ("Finance" if i < 20 else "Healthcare") for i in range(n_stocks)],
            index=symbols
        )
        market_betas = pd.Series(np.random.uniform(0.7, 1.4, n_stocks), index=symbols)
        
        # Raw scores with high sector bias (Technology scores inflated by 0.3)
        raw_scores = pd.Series(np.random.uniform(0.3, 0.7, n_stocks), index=symbols)
        for s in symbols[:10]:
            raw_scores[s] += 0.25

        res = self.orthogonalizer.extract_pure_idiosyncratic_alpha(
            scores=raw_scores,
            market_beta=market_betas,
            sector_series=sectors
        )

        self.assertIn("pure_scores", res)
        self.assertIn("r_squared", res)
        self.assertIn("idiosyncratic_ratio", res)
        self.assertEqual(len(res["pure_scores"]), n_stocks)
        self.assertTrue((res["pure_scores"] >= 0.0).all() and (res["pure_scores"] <= 1.0).all())
        # Systematic factors should explain some variance (R2 > 0)
        self.assertGreater(res["r_squared"], 0.05)


if __name__ == "__main__":
    unittest.main()
