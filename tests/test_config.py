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
        self.assertEqual(cfg.initial_cash, 100000000.0)
        self.assertTrue(cfg.mock_trading)
        # "KIS" alias is normalized to the BrokerType enum member value
        self.assertEqual(cfg.broker_type, "korea_investment")
        self.assertFalse(cfg.skip_training)
        self.assertEqual(cfg.fundamental_cache_expiry_days, 90)

    def test_env_overrides(self):
        """Test configuration parsed from env variables"""
        os.environ["DEBUG_MODE"] = "True"
        os.environ["MOCK_TRADING_ENABLED"] = "False"
        os.environ["BROKER_TYPE"] = "kiwoom"
        os.environ["TRAIN_SAMPLE_SP500"] = "20"
        os.environ["SKIP_TRAINING"] = "True"
        os.environ["FUNDAMENTAL_CACHE_EXPIRY_DAYS"] = "45"

        cfg = TradingConfig()
        self.assertTrue(cfg.debug_mode)
        self.assertFalse(cfg.mock_trading)
        self.assertEqual(cfg.broker_type, "kiwoom")
        self.assertEqual(cfg.train_sample_sp500, 20)
        self.assertTrue(cfg.skip_training)
        self.assertEqual(cfg.fundamental_cache_expiry_days, 45)

    def test_invalid_broker_type_raises(self):
        """Invalid BROKER_TYPE must fail fast at config load, not at trade time."""
        os.environ["BROKER_TYPE"] = "BOGUS_BROKER"
        with self.assertRaises(ValueError):
            TradingConfig()

    def test_dummy_broker_allowed_in_mock_mode(self):
        """BROKER_TYPE=DUMMY/MOCK is legitimate for GHA mock prediction runs."""
        os.environ["BROKER_TYPE"] = "DUMMY"
        os.environ["MOCK_TRADING_ENABLED"] = "True"
        self.assertEqual(TradingConfig().broker_type, "dummy")
        os.environ["BROKER_TYPE"] = "MOCK"
        self.assertEqual(TradingConfig().broker_type, "mock")

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

    def test_international_market_config(self):
        """Test international market cost models, currency mappings, and flag indicators."""
        cfg = TradingConfig()
        # Verify spreads
        self.assertAlmostEqual(cfg.get_base_spread("CHINA_SSE"), 0.0008)
        self.assertAlmostEqual(cfg.get_base_spread("JAPAN_TSE"), 0.0004)
        self.assertAlmostEqual(cfg.get_base_spread("INDIA_NSE"), 0.0008)
        self.assertAlmostEqual(cfg.get_base_spread("EUROPE_STOXX"), 0.0005)
        self.assertAlmostEqual(cfg.get_base_spread("VIETNAM_HOSE"), 0.0020)
        self.assertAlmostEqual(cfg.get_base_spread("TAIWAN_TWSE"), 0.0006)
        self.assertAlmostEqual(cfg.get_base_spread("AUSTRALIA_ASX"), 0.0005)
        self.assertAlmostEqual(cfg.get_base_spread("BRAZIL_B3"), 0.0015)
        self.assertAlmostEqual(cfg.get_base_spread("HKEX"), 0.0006)
        self.assertAlmostEqual(cfg.get_base_spread("SINGAPORE_SGX"), 0.0006)
        self.assertAlmostEqual(cfg.get_base_spread("CANADA_TSX"), 0.0004)

        # Verify taxes
        self.assertAlmostEqual(cfg.get_stt_tax("KOSPI"), 0.0015)
        self.assertAlmostEqual(cfg.get_stt_tax("KOSDAQ"), 0.0018)
        self.assertAlmostEqual(cfg.get_stt_tax("CHINA_SSE"), 0.0005)
        self.assertAlmostEqual(cfg.get_stt_tax("JAPAN_TSE"), 0.0)
        self.assertAlmostEqual(cfg.get_stt_tax("INDIA_NSE"), 0.0010)
        self.assertAlmostEqual(cfg.get_stt_tax("TAIWAN_TWSE"), 0.0030)
        self.assertAlmostEqual(cfg.get_stt_tax("HKEX"), 0.0010)

        # Verify currencies
        self.assertEqual(cfg.get_market_currency("KOSPI"), "KRW")
        self.assertEqual(cfg.get_market_currency("SP500"), "USD")
        self.assertEqual(cfg.get_market_currency("CHINA_SSE"), "CNY")
        self.assertEqual(cfg.get_market_currency("JAPAN_TSE"), "JPY")
        self.assertEqual(cfg.get_market_currency("INDIA_NSE"), "INR")
        self.assertEqual(cfg.get_market_currency("EUROPE_STOXX"), "EUR")
        self.assertEqual(cfg.get_market_currency("VIETNAM_HOSE"), "VND")
        self.assertEqual(cfg.get_market_currency("TAIWAN_TWSE"), "TWD")
        self.assertEqual(cfg.get_market_currency("AUSTRALIA_ASX"), "AUD")
        self.assertEqual(cfg.get_market_currency("BRAZIL_B3"), "BRL")
        self.assertEqual(cfg.get_market_currency("HKEX"), "HKD")
        self.assertEqual(cfg.get_market_currency("SINGAPORE_SGX"), "SGD")
        self.assertEqual(cfg.get_market_currency("CANADA_TSX"), "CAD")

        # Verify flags
        self.assertEqual(cfg.get_market_flag("KOSPI"), "🇰🇷")
        self.assertEqual(cfg.get_market_flag("SP500"), "🇺🇸")
        self.assertEqual(cfg.get_market_flag("CHINA_SSE"), "🇨🇳")
        self.assertEqual(cfg.get_market_flag("JAPAN_TSE"), "🇯🇵")
        self.assertEqual(cfg.get_market_flag("INDIA_NSE"), "🇮🇳")
        self.assertEqual(cfg.get_market_flag("EUROPE_STOXX"), "🇪🇺")
        self.assertEqual(cfg.get_market_flag("VIETNAM_HOSE"), "🇻🇳")
        self.assertEqual(cfg.get_market_flag("TAIWAN_TWSE"), "🇹🇼")
        self.assertEqual(cfg.get_market_flag("AUSTRALIA_ASX"), "🇦🇺")
        self.assertEqual(cfg.get_market_flag("BRAZIL_B3"), "🇧🇷")
        self.assertEqual(cfg.get_market_flag("HKEX"), "🇭🇰")
        self.assertEqual(cfg.get_market_flag("SINGAPORE_SGX"), "🇸🇬")
        self.assertEqual(cfg.get_market_flag("CANADA_TSX"), "🇨🇦")

    def test_market_costs_json_override(self):
        """V6-32: Test MARKET_COSTS_JSON environment parsing via _build_market_lookup_table without NameError."""
        import json
        from src.config import _build_market_lookup_table
        custom_costs = {
            "KOSPI": {"spread_bps": 0.0003, "stt": 0.0010},
            "CUSTOM_MKT": {"spread_bps": 0.0015, "stt": 0.0020, "brokerage": 0.0005, "aliases": ["CMKT"]}
        }
        os.environ["MARKET_COSTS_JSON"] = json.dumps(custom_costs)
        lookup = _build_market_lookup_table()
        self.assertAlmostEqual(lookup["KOSPI"]["spread_bps"], 0.0003)
        self.assertAlmostEqual(lookup["KOSPI"]["stt"], 0.0010)
        self.assertIn("CUSTOM_MKT", lookup)
        self.assertIn("CMKT", lookup)
        self.assertAlmostEqual(lookup["CMKT"]["spread_bps"], 0.0015)

    def test_liquidity_and_oms_env_overrides(self):
        """V6-35: Test environment variable overrides for liquidity, friction and OMS safety parameters."""
        os.environ["MIN_DAILY_VOLUME_KRX"] = "800000000.0"
        os.environ["MIN_DAILY_VOLUME_SP500"] = "2500000.0"
        os.environ["SLIPPAGE_KRX_MARKET_ORDER"] = "0.0025"
        os.environ["OMS_NET_ALPHA_SAFETY_MARGIN"] = "0.0015"
        os.environ["OMS_LIMIT_UP_LOCK_THRESHOLD"] = "0.298"
        os.environ["BASE_SPREAD_CHINA"] = "0.0012"
        os.environ["DEFAULT_VOLATILITY_GLOBAL"] = "0.022"

        cfg = TradingConfig()
        self.assertAlmostEqual(cfg.min_daily_volume_krx, 800000000.0)
        self.assertAlmostEqual(cfg.min_daily_volume_sp500, 2500000.0)
        self.assertAlmostEqual(cfg.slippage_krx_market_order, 0.0025)
        self.assertAlmostEqual(cfg.oms_net_alpha_safety_margin, 0.0015)
        self.assertAlmostEqual(cfg.oms_limit_up_lock_threshold, 0.298)
        self.assertAlmostEqual(cfg.base_spread_china, 0.0012)
        self.assertAlmostEqual(cfg.default_volatility_global, 0.022)


if __name__ == "__main__":
    unittest.main()
