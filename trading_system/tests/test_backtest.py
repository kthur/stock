import sys
import unittest
import random
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.backtest import PriceBar, BacktestEngine


class TestBacktestEngine(unittest.TestCase):
    """BacktestEngine unit tests"""

    def setUp(self):
        self.engine = BacktestEngine(initial_capital=100000.0, slippage_pct=0.0, market_impact_pct=0.0)
        self.engine.fee_pct = 0.0  # Zero fees for simple math

    def _make_dummy_bars(self, count=100, trend="up"):
        bars = []
        base_time = datetime(2026, 1, 1, 9, 30)
        price = 100.0
        random.seed(42)
        for i in range(count):
            if trend == "up":
                price += 1.0
            elif trend == "down":
                price -= 1.0
            else:
                price += random.choice([-1.0, 1.0])

            bars.append(PriceBar(
                timestamp=base_time + timedelta(days=i),
                open=price - 0.5,
                high=price + 1.0,
                low=price - 1.0,
                close=price,
                volume=1000
            ))
        return bars

    def test_backtest_no_trades(self):
        """Test backtest with always HOLD (no trades executed)"""
        bars = self._make_dummy_bars(50, "up")

        def always_hold_strategy(bars_sub):
            return "HOLD"

        res = self.engine.run_backtest(
            symbol="AAPL",
            price_bars=bars,
            strategy_func=always_hold_strategy
        )

        self.assertEqual(len(res.trades), 0)
        self.assertEqual(res.final_capital, 100000.0)
        self.assertEqual(res.total_return_pct, 0.0)

    def test_backtest_buy_and_hold(self):
        """Test simple BUY and exit at end of backtest"""
        bars = self._make_dummy_bars(10, "up")

        def buy_and_hold_strategy(bars_sub):
            if len(bars_sub) == 1:
                return "BUY"
            return "HOLD"

        res = self.engine.run_backtest(
            symbol="AAPL",
            price_bars=bars,
            strategy_func=buy_and_hold_strategy
        )

        self.assertEqual(len(res.trades), 1)
        trade = res.trades[0]
        self.assertEqual(trade.entry_price, 101.5)  # bar[1] open (next bar execution)
        self.assertEqual(trade.exit_price, 110.0)  # bar[-1] close (exited at end)
        self.assertTrue(res.final_capital > 100000.0)

    def test_backtest_stop_loss(self):
        """Test stop loss trigger on downward trend"""
        bars = self._make_dummy_bars(20, "down")

        def buy_and_hold_strategy(bars_sub):
            if len(bars_sub) == 1:
                return "BUY"
            return "HOLD"

        res = self.engine.run_backtest(
            symbol="AAPL",
            price_bars=bars,
            strategy_func=buy_and_hold_strategy,
            stop_loss_pct=0.05  # 5% Stop Loss
        )

        self.assertEqual(len(res.trades), 1)
        trade = res.trades[0]
        self.assertEqual(trade.exit_reason, "STOP_LOSS")
        self.assertTrue(trade.pnl < 0.0)

    def test_backtest_trailing_stop(self):
        """Test trailing stop triggering when price drops from its peak"""
        # Price goes 100 -> 110 -> 102
        bars = []
        base_time = datetime(2026, 1, 1, 9, 30)
        prices = [100.0, 105.0, 110.0, 102.0, 101.0]
        for i, p in enumerate(prices):
            bars.append(PriceBar(
                timestamp=base_time + timedelta(days=i),
                open=p, high=p + 0.5, low=p - 0.5, close=p, volume=1000
            ))

        def buy_immediately_strategy(bars_sub):
            if len(bars_sub) == 1:
                return "BUY"
            return "HOLD"

        res = self.engine.run_backtest(
            symbol="AAPL",
            price_bars=bars,
            strategy_func=buy_immediately_strategy,
            trailing_stop_pct=0.05  # 5% Trailing Stop
        )
        self.assertEqual(len(res.trades), 1)
        self.assertEqual(res.trades[0].exit_reason, "TRAILING_STOP")

    def test_backtest_take_profit(self):
        """Test partial take profit exit"""
        # Price goes 100 -> 112 -> 115
        bars = []
        base_time = datetime(2026, 1, 1, 9, 30)
        prices = [100.0, 112.0, 115.0]
        for i, p in enumerate(prices):
            bars.append(PriceBar(
                timestamp=base_time + timedelta(days=i),
                open=p, high=p + 0.5, low=p - 0.5, close=p, volume=1000
            ))

        def buy_immediately_strategy(bars_sub):
            if len(bars_sub) == 1:
                return "BUY"
            return "HOLD"

        res = self.engine.run_backtest(
            symbol="AAPL",
            price_bars=bars,
            strategy_func=buy_immediately_strategy,
            take_profit_pct=0.10  # 10% Take Profit
        )
        # Verify that we executed trades
        self.assertTrue(len(res.trades) > 0)

    def test_backtest_scale_in(self):
        """Test scale-in entry (entering in steps)"""
        bars = self._make_dummy_bars(10, "up")

        def scale_in_strategy(bars_sub):
            if len(bars_sub) in (1, 3):
                return "BUY"
            return "HOLD"

        res = self.engine.run_backtest(
            symbol="AAPL",
            price_bars=bars,
            strategy_func=scale_in_strategy,
            scale_in=True
        )
        self.assertTrue(len(res.trades) > 0)

    def test_backtest_short(self):
        """Test short selling simulation"""
        bars = self._make_dummy_bars(10, "down")

        def sell_immediately_strategy(bars_sub):
            if len(bars_sub) == 1:
                return "SELL"
            return "HOLD"

        res = self.engine.run_backtest(
            symbol="AAPL",
            price_bars=bars,
            strategy_func=sell_immediately_strategy,
            allow_short=True
        )
        self.assertTrue(len(res.trades) > 0)
        self.assertEqual(res.trades[0].direction, "SHORT")


    def test_backtest_centralized_market_transaction_costs(self):
        """Test exact centralized rates: KONEX 1.30%, KOSDAQ 1.00%, KOSPI 0.85%, SP500 0.60%"""
        engine = BacktestEngine(initial_capital=100000.0)

        # Check market cost rates
        self.assertAlmostEqual(engine.get_market_cost_rate(market="KONEX"), 0.0130, places=6)
        self.assertAlmostEqual(engine.get_market_cost_rate(market="KOSDAQ"), 0.0100, places=6)
        self.assertAlmostEqual(engine.get_market_cost_rate(market="KOSPI"), 0.0085, places=6)
        self.assertAlmostEqual(engine.get_market_cost_rate(market="SP500"), 0.0060, places=6)

        # Symbol inference
        self.assertAlmostEqual(engine.get_market_cost_rate(symbol="300000.KN"), 0.0130, places=6)
        self.assertAlmostEqual(engine.get_market_cost_rate(symbol="035720.KQ"), 0.0100, places=6)
        self.assertAlmostEqual(engine.get_market_cost_rate(symbol="005930.KS"), 0.0085, places=6)
        self.assertAlmostEqual(engine.get_market_cost_rate(symbol="AAPL"), 0.0060, places=6)

    def test_backtest_metrics_sharpe_mdd_win_rate(self):
        """Test calculation of Sharpe ratio, MDD, win rate, profit factor, and net return"""
        bars = self._make_dummy_bars(50, "up")
        engine = BacktestEngine(initial_capital=100000.0)

        def buy_strategy(bars_sub):
            if len(bars_sub) == 5:
                return "BUY"
            if len(bars_sub) == 25:
                return "SELL"
            return "HOLD"

        res = engine.run_backtest(
            symbol="005930.KS",
            price_bars=bars,
            strategy_func=buy_strategy,
            market="KOSPI"
        )

        # Metrics presence and sanity
        self.assertGreater(len(res.trades), 0)
        self.assertIsNotNone(res.sharpe_ratio)
        self.assertGreaterEqual(res.win_rate, 0.0)
        self.assertLessEqual(res.win_rate, 1.0)
        self.assertGreaterEqual(res.max_drawdown, 0.0)
        self.assertIsNotNone(res.profit_factor)
        self.assertIsNotNone(res.net_return)
        self.assertIsNotNone(res.gross_return)
        self.assertTrue(res.total_fees > 0.0)

    def test_run_ensemble_backtest_with_14_strategy_scores(self):
        """Test BacktestEngine support for dynamic 14-strategy ensemble score inputs"""
        import pandas as pd
        bars = self._make_dummy_bars(30, "up")
        engine = BacktestEngine(initial_capital=100000.0)

        ensemble_df = pd.DataFrame([
            {"symbol": "AAPL", "ensemble_score": 0.75, "ensemble_expected_return": 15.0}
        ])

        res = engine.run_ensemble_backtest(
            symbol="AAPL",
            price_bars=bars,
            ensemble_scores=ensemble_df,
            market="SP500",
            buy_threshold=0.55
        )

        self.assertGreater(len(res.trades), 0)
        self.assertEqual(res.symbol, "AAPL")

    def test_run_multi_factor_portfolio_backtest(self):
        """Test multi-asset portfolio backtest for 14 multi-factor strategies"""
        import pandas as pd
        bars_aapl = self._make_dummy_bars(20, "up")
        bars_msft = self._make_dummy_bars(20, "up")
        engine = BacktestEngine(initial_capital=100000.0)

        ensemble_df = pd.DataFrame([
            {"symbol": "AAPL", "ensemble_score": 0.80},
            {"symbol": "MSFT", "ensemble_score": 0.70}
        ])

        results = engine.run_multi_factor_portfolio_backtest(
            symbols=["AAPL", "MSFT"],
            price_bars_dict={"AAPL": bars_aapl, "MSFT": bars_msft},
            ensemble_scores_df=ensemble_df,
            market_map={"AAPL": "SP500", "MSFT": "SP500"}
        )

        self.assertIn("AAPL", results)
        self.assertIn("MSFT", results)


if __name__ == "__main__":
    unittest.main()

