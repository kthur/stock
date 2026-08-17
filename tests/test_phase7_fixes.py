import unittest
import numpy as np
import pandas as pd
from trading_system.src.config import TradingConfig
from trading_system.src.ai.optuna_tuner import OptunaStrategyTuner
from trading_system.src.execution.oms_engine import ExecutionOMSEngine
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
from trading_system.src.core.latr_factor import LATRFactorEngine
from trading_system.src.core.order_flow import OrderFlowEngine
from trading_system.src.core.event_driven import EventDrivenEngine


class TestPhase7Fixes(unittest.TestCase):

    def test_optuna_tuner_gap_and_52w_high(self):
        tuner = OptunaStrategyTuner()
        dates = pd.date_range("2023-01-01", periods=100)
        np.random.seed(42)
        close = np.random.randn(100).cumsum() + 100
        df = pd.DataFrame({
            "High": close + 2.0,
            "Low": close - 2.0,
            "Close": close
        }, index=dates)
        res = tuner.tune_strategy_4_vcp_rule(prices_dict={"TEST": df}, n_trials=2)
        self.assertIsInstance(res, dict)

    def test_telegram_authorized_ids_parsing(self):
        config = TradingConfig()
        config.telegram_authorized_user_ids = "12345, INVALID, 67890"
        parsed = config.parsed_authorized_user_ids
        self.assertEqual(parsed, [12345, 67890])

    def test_portfolio_allocator_sector_renormalization(self):
        allocator = PortfolioAllocator()
        weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
        sector_map = {"AAPL": "TECH", "MSFT": "TECH", "GOOGL": "COMM"}
        res = allocator.apply_sector_and_factor_constraints(
            weights, sector_map, max_sector_cap=0.4
        )
        self.assertAlmostEqual(sum(res.values()), 1.0, places=5)

    def test_latr_factor_target_drawdown_config(self):
        engine = LATRFactorEngine(target_drawdown=0.20)
        self.assertEqual(engine.target_drawdown, 0.20)
        dates = pd.date_range("2023-01-01", periods=60)
        df = pd.DataFrame({"Close": np.linspace(100, 80, 60), "Volume": [1000]*60}, index=dates)
        scores = engine.compute_scores({"TEST": df})
        self.assertIn("TEST", scores)

    def test_order_flow_vwap_deviation(self):
        engine = OrderFlowEngine()
        dates = pd.date_range("2023-01-01", periods=30)
        df = pd.DataFrame({"Close": np.linspace(10, 20, 30), "Volume": np.linspace(100, 500, 30)}, index=dates)
        scores_df = engine.compute_scores({"TEST": df})
        self.assertFalse(scores_df.empty)
        self.assertIn("order_flow_score", scores_df.columns)

    def test_event_driven_configurable_weights(self):
        class DummyConfig:
            event_weights = {"A": 0.99}
        engine = EventDrivenEngine(config=DummyConfig())
        self.assertEqual(engine.event_weights["A"], 0.99)


if __name__ == "__main__":
    unittest.main()
