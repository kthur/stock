import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai.meta_learner import NonLinearMetaLearner
from src.core.index_rebalance import IndexRebalanceEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.execution.oms_engine import ExecutionOMSEngine


class TestApexTierQuantEnhancements(unittest.TestCase):

    def setUp(self):
        self.meta_learner = NonLinearMetaLearner(n_estimators=20, max_depth=3)
        self.rebalance_engine = IndexRebalanceEngine()
        self.allocator = PortfolioAllocator()
        self.ensemble = EnsembleScoringEngine()
        self.oms = ExecutionOMSEngine(db_path=":memory:")

    # -------------------------------------------------------------------------
    # 1. Non-Linear Monotonic GBDT Meta-Learner
    # -------------------------------------------------------------------------
    def test_nonlinear_meta_learner_fit_predict(self):
        """Verify NonLinearMetaLearner captures synergies with monotonic ranking outputs."""
        np.random.seed(42)
        N = 100
        # 3 factors: order_flow, valuation, momentum
        f1 = np.random.uniform(0, 1, N)
        f2 = np.random.uniform(0, 1, N)
        f3 = np.random.uniform(0, 1, N)
        # Target with non-linear synergy (f1 * f2)
        y = 0.3 * f1 + 0.3 * f2 + 0.4 * (f1 * f2) + np.random.normal(0, 0.05, N)

        df_X = pd.DataFrame({"order_flow": f1, "valuation": f2, "momentum": f3})
        self.meta_learner.fit(df_X, y)

        preds = self.meta_learner.predict(df_X)
        self.assertEqual(len(preds), N)
        self.assertTrue((preds >= 0.0).all() and (preds <= 1.0).all())

        # Synergy extraction
        synergies = self.meta_learner.extract_factor_synergies(df_X, top_k=2)
        self.assertGreater(len(synergies), 0)
        self.assertIn("synergy_score", synergies[0])

    # -------------------------------------------------------------------------
    # 2. Structural Index Rebalance Pre-Positioning Alpha Engine
    # -------------------------------------------------------------------------
    def test_index_rebalance_structural_flows(self):
        """Verify IndexRebalanceEngine flags inclusion/exclusion candidates with passive flows."""
        universe = pd.DataFrame({
            "symbol": ["005930", "NEW_LARGE_CAP", "DISTRESSED_SMALL"],
            "name": ["삼성전자", "신규편입유력주", "퇴출위기주"],
            "market": ["KOSPI", "KOSPI", "KOSPI"],
            "market_cap": [450_000_000_000_000, 8_000_000_000_000, 300_000_000_000],
            "trading_value": [1_000_000_000_000, 150_000_000_000, 1_000_000_000]
        })

        scores_df = self.rebalance_engine.compute_scores(universe=universe)
        self.assertEqual(len(scores_df), 3)
        self.assertIn("index_rebalance_score", scores_df.columns)
        self.assertIn("predicted_flow_krw", scores_df.columns)

        # Check window logic
        window_info = self.rebalance_engine.is_near_rebalance_window()
        self.assertIn("in_window", window_info)
        self.assertIn("target_index", window_info)

    # -------------------------------------------------------------------------
    # 3. Extreme Value Clayton Copula Tail Risk Calibration
    # -------------------------------------------------------------------------
    def test_clayton_copula_tail_risk(self):
        """Verify Clayton Copula tail dependence penalizes extreme crash co-movement."""
        np.random.seed(42)
        T = 100
        # Stock A and B crash together in lower tail (extreme co-dependence)
        market_crash = np.random.normal(0, 0.02, T)
        market_crash[market_crash < -0.03] *= 2.0

        ret_A = market_crash + np.random.normal(0, 0.005, T)
        ret_B = market_crash + np.random.normal(0, 0.005, T)
        ret_C = np.random.normal(0.001, 0.015, T)  # Independent

        df_rets = pd.DataFrame({"A": ret_A, "B": ret_B, "C": ret_C})
        weights = {"A": 0.33, "B": 0.33, "C": 0.34}

        tail_adj_weights = PortfolioAllocator.compute_clayton_copula_tail_risk_weights(
            target_weights=weights,
            returns_df=df_rets,
            theta=2.5,
            tail_penalty_strength=0.80
        )

        self.assertEqual(len(tail_adj_weights), 3)
        self.assertAlmostEqual(sum(tail_adj_weights.values()), 1.0, places=4)
        # Independent stock C should receive higher weight relative to co-crashing A & B
        self.assertGreater(tail_adj_weights["C"], tail_adj_weights["A"])

    # -------------------------------------------------------------------------
    # 4. Multi-Horizon Exponential Convolutional Decay Filter
    # -------------------------------------------------------------------------
    def test_exponential_decay_filter(self):
        """Verify apply_exponential_decay_filter smooths slow factors while keeping fast ones agile."""
        prev = pd.DataFrame({
            "symbol": ["005930", "000660"],
            "microstructure": [0.80, 0.20],  # Fast half-life (0.5d)
            "rim_valuation": [0.90, 0.30]    # Slow half-life (45d)
        })
        curr = pd.DataFrame({
            "symbol": ["005930", "000660"],
            "microstructure": [0.20, 0.80],  # Rapidly flipped
            "rim_valuation": [0.50, 0.50]    # Moderate move
        })

        filtered = EnsembleScoringEngine.apply_exponential_decay_filter(
            current_scores=curr,
            previous_scores=prev
        )

        self.assertEqual(len(filtered), 2)
        # Fast microstructure (0.5d) should adapt almost completely to current score (0.20 -> near 0.20)
        filt_micro_005930 = filtered.loc[filtered["symbol"] == "005930", "microstructure"].iloc[0]
        self.assertLess(filt_micro_005930, 0.40)

        # Slow rim_valuation (45d) should retain strong memory of previous score (0.90 -> smoothed above 0.80)
        filt_rim_005930 = filtered.loc[filtered["symbol"] == "005930", "rim_valuation"].iloc[0]
        self.assertGreater(filt_rim_005930, 0.80)

    # -------------------------------------------------------------------------
    # 5. Adaptive Midpoint Pegged Limit Order Routing
    # -------------------------------------------------------------------------
    def test_midpoint_pegged_limit_order_routing(self):
        """Verify calculate_peg_limit_price and MIDPOINT_PEG routing in OMS."""
        # 1. Price calculation
        peg_price = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=70000.0,
            bid_price=69900.0,
            ask_price=70100.0,
            spread=200.0,
            alpha_urgency=0.50,
            action="BUY"
        )
        self.assertEqual(peg_price, 70000.0) # Midpoint = (69900 + 70100) / 2 = 70000

        # 2. OMS plan routing with slow alpha (avg half-life >= 25d)
        preds = [{
            "symbol": "005930",
            "name": "삼성전자",
            "market": "KOSPI",
            "close_price": 70000.0,
            "target_price": 70000.0,
            "expected_return": 12.0,
            "adv": 500_000_000_000.0,
            "rim_valuation": 0.85, # 45d half life
            "value_up": 0.80       # 60d half life
        }]
        plans = self.oms.generate_order_plan(
            top_predictions=preds,
            portfolio_weights={"005930": 0.20},
            total_capital=100_000_000.0
        )

        self.assertGreater(len(plans), 0)
        self.assertEqual(plans[0]["execution_strategy"], "MIDPOINT_PEG")


if __name__ == "__main__":
    unittest.main()
