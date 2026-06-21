import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.telegram_bot.bot_engine import TelegramBotEngine


def _make_ts_mock(has_global=True, has_rs=True):
    """Create a mock trading system with the attributes needed by bot commands."""
    ts = MagicMock()

    # global_market mock
    if has_global:
        ts.global_market = MagicMock()
        ts.global_market.get_summary.return_value = {
            "indices": {
                "^GSPC": {"name": "S&P 500", "price": 5400.0, "change_pct": 0.5},
                "^KS11": {"name": "KOSPI", "price": 2800.0, "change_pct": -0.3},
                "^N225": {"name": "Nikkei", "price": 39000.0, "change_pct": 1.2},
            },
            "fx_rates": {
                "USDKRW": {"name": "USD/KRW", "rate": 1320.0, "change_pct": 0.1},
                "EURUSD": {"name": "EUR/USD", "rate": 1.08, "change_pct": -0.05},
            },
            "updated_at": "2026-06-08T12:00:00",
        }
    else:
        ts.global_market = None

    # relative_strength mock
    if has_rs:
        ts.relative_strength = MagicMock()
        ts.relative_strength.rank_symbols.return_value = [
            {
                "rank": 1, "symbol": "AAPL", "composite_score": 1.23,
                "alpha": 0.0005, "relative_strength_pct": 8.5,
                "correlation": 0.85, "beta": 1.2,
            },
            {
                "rank": 2, "symbol": "MSFT", "composite_score": 0.95,
                "alpha": 0.0003, "relative_strength_pct": 5.2,
                "correlation": 0.72, "beta": 1.05,
            },
        ]
    else:
        ts.relative_strength = None

    # portfolio
    ts.portfolio = MagicMock()
    ts.portfolio.positions = {}
    ts.portfolio.cash = 1_000_000

    return ts


class TestTelegramBotGlobalCommand(unittest.TestCase):
    """Telegram /global command tests"""

    def setUp(self):
        self.bot = TelegramBotEngine(trading_system=_make_ts_mock())

    def test_global_returns_market_data(self):
        response = self.bot.process_message(12345, "/global")
        self.assertIn("S&P 500", response)
        self.assertIn("KOSPI", response)
        self.assertIn("Nikkei", response)
        self.assertIn("USD/KRW", response)
        self.assertIn("EUR/USD", response)
        self.assertIn("5,400", response)

    def test_global_shows_positive_negative_arrows(self):
        response = self.bot.process_message(12345, "/global")
        # S&P 500 up 0.5% -> should show positive sign
        self.assertIn("+0.50%", response)
        # KOSPI down -0.3% -> should show negative sign
        self.assertIn("-0.30%", response)

    def test_global_without_module_returns_error(self):
        bot = TelegramBotEngine(trading_system=_make_ts_mock(has_global=False))
        response = bot.process_message(12345, "/global")
        self.assertIn("사용할 수 없습니다", response)

    def test_global_without_trading_system(self):
        bot = TelegramBotEngine()
        response = bot.process_message(12345, "/global")
        self.assertIn("사용할 수 없습니다", response)


class TestTelegramBotScreenCommand(unittest.TestCase):
    """Telegram /screen command tests"""

    def setUp(self):
        ts = _make_ts_mock()
        ts.portfolio.positions = {"AAPL": MagicMock(), "MSFT": MagicMock()}
        self.bot = TelegramBotEngine(trading_system=ts)

    def test_screen_returns_rankings(self):
        response = self.bot.process_message(12345, "/screen")
        self.assertIn("AAPL", response)
        self.assertIn("MSFT", response)
        self.assertIn("1.23", response)  # composite score

    def test_screen_with_custom_symbols(self):
        ts = _make_ts_mock()
        ts.portfolio.positions = {}
        bot = TelegramBotEngine(trading_system=ts)
        bot.process_message(12345, "/screen GOOGL,NVDA")
        ts.relative_strength.rank_symbols.assert_called_with(
            ["GOOGL", "NVDA"], top_n=15, min_correlation=0.0,
        )

    def test_screen_with_min_corr_filter(self):
        ts = _make_ts_mock()
        ts.portfolio.positions = {}
        bot = TelegramBotEngine(trading_system=ts)
        bot.process_message(12345, "/screen AAPL,MSFT 0.3")
        ts.relative_strength.rank_symbols.assert_called_with(
            ["AAPL", "MSFT"], top_n=15, min_correlation=0.3,
        )

    def test_screen_without_module_returns_error(self):
        bot = TelegramBotEngine(trading_system=_make_ts_mock(has_rs=False))
        response = bot.process_message(12345, "/screen AAPL")
        self.assertIn("사용할 수 없습니다", response)

    def test_screen_no_symbols_fallback_to_positions(self):
        ts = _make_ts_mock()
        ts.portfolio.positions = {"AAPL": MagicMock(), "MSFT": MagicMock()}
        bot = TelegramBotEngine(trading_system=ts)
        response = bot.process_message(12345, "/screen")
        self.assertIn("AAPL", response)
        self.assertIn("MSFT", response)

    def test_screen_no_positions_no_args(self):
        bot = TelegramBotEngine(trading_system=_make_ts_mock())
        response = bot.process_message(12345, "/screen")
        self.assertIn("스크리닝할 종목이 없습니다", response)

    def test_screen_passes_min_corr_to_rank_symbols(self):
        ts = _make_ts_mock()
        ts.portfolio.positions = {}
        bot = TelegramBotEngine(trading_system=ts)
        bot.process_message(12345, "/screen AAPL,MSFT 0.5")
        ts.relative_strength.rank_symbols.assert_called_with(
            ["AAPL", "MSFT"], top_n=15, min_correlation=0.5,
        )


class TestTelegramBotGeneral(unittest.TestCase):
    """General Telegram bot tests"""

    def setUp(self):
        self.bot = TelegramBotEngine()

    def test_unknown_command(self):
        response = self.bot.process_message(12345, "/nonexistent")
        self.assertIn("알 수 없는 명령어", response)

    def test_process_message_tracks_user(self):
        self.bot.process_message(100, "/start")
        self.assertIn(100, self.bot.subscribed_users)

    def test_process_message_counts_commands(self):
        self.bot.process_message(100, "/help")
        self.assertEqual(self.bot.subscribed_users[100]["command_count"], 1)

    def test_get_stats(self):
        stats = self.bot.get_stats()
        self.assertIn("is_running", stats)
        self.assertIn("total_commands", stats)

    def test_simulation_mode_when_no_token(self):
        self.assertTrue(self.bot.simulation_mode)

    def test_start_stop(self):
        self.bot.start()
        self.assertTrue(self.bot.is_running)
        self.bot.stop()
        self.assertFalse(self.bot.is_running)


if __name__ == "__main__":
    unittest.main(verbosity=2)
