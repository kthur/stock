import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import TradingConfig


class TestTradingConfig(unittest.TestCase):
    """TradingConfig unit tests"""

    def setUp(self):
        # Save env to restore later
        self.original_env = dict(os.environ)

    def tearDown(self):
        # Restore original env
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_default_config(self):
        """Test default config values"""
        cfg = TradingConfig()
        self.assertEqual(cfg.initial_cash, 1000000.0)
        self.assertTrue(cfg.mock_trading)
        self.assertEqual(cfg.broker_type, "KIS")
        self.assertFalse(cfg.skip_training)
        self.assertEqual(cfg.fundamental_cache_expiry_days, 90)

    def test_env_overrides(self):
        """Test configuration parsed from env variables"""
        os.environ["DEBUG_MODE"] = "True"
        os.environ["MOCK_TRADING_ENABLED"] = "False"
        os.environ["BROKER_TYPE"] = "MOCK"
        os.environ["TRAIN_SAMPLE_SP500"] = "20"
        os.environ["SKIP_TRAINING"] = "True"
        os.environ["FUNDAMENTAL_CACHE_EXPIRY_DAYS"] = "45"

        cfg = TradingConfig()
        self.assertTrue(cfg.debug_mode)
        self.assertFalse(cfg.mock_trading)
        self.assertEqual(cfg.broker_type, "MOCK")
        self.assertEqual(cfg.train_sample_sp500, "20")
        self.assertTrue(cfg.skip_training)
        self.assertEqual(cfg.fundamental_cache_expiry_days, 45)

    def test_resolve_sample_size(self):
        """Test resolved sample size formatting"""
        cfg = TradingConfig()
        self.assertEqual(cfg.resolve_sample_size("10", 100), 10)
        self.assertEqual(cfg.resolve_sample_size("all", 100), 100)
        self.assertEqual(cfg.resolve_sample_size("10%", 200), 20)
        self.assertEqual(cfg.resolve_sample_size("15%", 100), 15)

    def test_get_freshness_days(self):
        """Test freshness day resolution"""
        cfg = TradingConfig()
        cfg.stock_price_freshness_days = "7"
        self.assertEqual(cfg.get_freshness_days(), 7)
        cfg.stock_price_freshness_days = "none"
        self.assertEqual(cfg.get_freshness_days(), -1)
        cfg.stock_price_freshness_days = "never"
        self.assertEqual(cfg.get_freshness_days(), -1)

    def test_validate_cash_raises_error(self):
        """Test invalid configurations throw errors during validate()"""
        cfg = TradingConfig()
        cfg.initial_cash = -500.0
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_retries_raises_error(self):
        cfg = TradingConfig()
        cfg.max_retries = -1
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_parse_authorized_ids(self):
        """Test parsing of telegram authorized user IDs"""
        cfg = TradingConfig()
        cfg.telegram_authorized_user_ids = "12345, 67890"
        self.assertEqual(cfg.parsed_authorized_user_ids, [12345, 67890])

        cfg.telegram_authorized_user_ids = "invalid, ids"
        self.assertEqual(cfg.parsed_authorized_user_ids, [])

    def test_get_train_seed(self):
        """Test seed parsing configurations"""
        cfg = TradingConfig()
        cfg.train_seed = "1234"
        self.assertEqual(cfg.get_train_seed(), 1234)
        cfg.train_seed = "none"
        self.assertIsNone(cfg.get_train_seed())
        cfg.train_seed = ""
        self.assertIsNone(cfg.get_train_seed())
        cfg.train_seed = "-1"
        self.assertIsNone(cfg.get_train_seed())

    def test_get_update_interval(self):
        """Test update interval parsing"""
        cfg = TradingConfig()
        cfg.update_interval = "60"
        self.assertEqual(cfg.get_update_interval(), 60)
        cfg.update_interval = "invalid"
        with self.assertRaises(ValueError):
            cfg.get_update_interval()

    def test_validate_warnings(self):
        """Test validate method logic and warning paths"""
        cfg = TradingConfig()
        cfg.telegram_bot_token = "token"
        cfg.telegram_authorized_user_ids = ""
        # Should execute without errors but trigger warnings
        cfg.validate()

    def test_nasdaq_russell2000_config(self):
        """Test NASDAQ and RUSSELL2000 spread defaults and env overrides"""
        cfg = TradingConfig()
        self.assertEqual(cfg.base_spread_nasdaq, 0.0003)
        self.assertEqual(cfg.base_spread_russell2000, 0.0008)
        self.assertFalse(hasattr(cfg, "base_spread_konex"))

        os.environ["BASE_SPREAD_NASDAQ"] = "0.0005"
        os.environ["BASE_SPREAD_RUSSELL2000"] = "0.0012"
        cfg_env = TradingConfig()
        self.assertEqual(cfg_env.base_spread_nasdaq, 0.0005)
        self.assertEqual(cfg_env.base_spread_russell2000, 0.0012)


if __name__ == "__main__":
    unittest.main()
