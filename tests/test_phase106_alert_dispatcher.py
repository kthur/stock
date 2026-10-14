"""
test_phase106_alert_dispatcher.py — Test Suite for Multi-Channel Alert & Webhook Dispatcher
(Phase 106 / Feature F503 / Release R122)

Verifies:
1. Zero external imports invariant (strictly no requests, aiohttp, httpx, or urllib3).
2. Module exports and backward compatibility aliases.
3. Placeholder and invalid credential detection for Telegram and Slack.
4. Telegram delivery via mocked HTTP responses (success, HTTP 429, HTTP 500, URLError, Timeout).
5. Slack incoming webhook delivery via mocked HTTP responses (success, HTTP error, URLError, Timeout).
6. Console audit logging, log levels, and Unicode / CP949 fault-tolerance.
7. Dry-run mode behavior and internal telemetry logging.
8. Generic dispatch method with channel filtering and level parsing.
9. Typed event: send_pipeline_summary across 5 global markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
10. Typed event: send_paper_fill_confirmation (BUY/SELL, KRW/USD, slippage, market impact).
11. Typed event: send_circuit_breaker_alert (Flash Crash drop, VIX surge, Trailing Stop, Emergency severity).
12. Comprehensive fault isolation (zero caller exceptions under network failures).
"""

import io
import os
import sys
import json
import socket
import logging
import unittest
from unittest.mock import patch, MagicMock, mock_open
import urllib.error

# Ensure project root and trading_system are on sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TRADING_SYSTEM_DIR = os.path.join(_PROJECT_ROOT, "trading_system")
for p in (_PROJECT_ROOT, _TRADING_SYSTEM_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.notification.alert_dispatcher import (
    AlertDispatcher,
    MultiChannelAlertDispatcher,
    NotificationDispatcher,
    MultiChannelNotifier,
    Phase106AlertDispatcher,
    AlertLevel,
    ChannelType,
)
import src.notification as notification_pkg


class TestPhase106AlertDispatcher(unittest.TestCase):
    """Comprehensive test suite for Phase 106 AlertDispatcher."""

    def setUp(self):
        """Set up standard test fixtures."""
        self.valid_telegram_token = "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
        self.valid_telegram_chat = "987654321"
        self.valid_slack_webhook = "https://hooks.slack.com/services/unit-test/mock-channel/fixture-token"

    # =========================================================================
    # 1. Zero External Dependency Invariant
    # =========================================================================

    def test_01_zero_external_dependencies_invariant(self):
        """Verifies strictly zero external HTTP packages are imported by alert_dispatcher."""
        import src.notification.alert_dispatcher as mod

        forbidden = ["requests", "aiohttp", "httpx", "urllib3"]
        mod_file = mod.__file__
        with open(mod_file, "r", encoding="utf-8") as f:
            content = f.read()

        for pkg in forbidden:
            # Check source text does not import forbidden packages
            self.assertNotIn(f"import {pkg}", content, f"Forbidden import '{pkg}' found in {mod_file}")
            self.assertNotIn(f"from {pkg}", content, f"Forbidden from-import '{pkg}' found in {mod_file}")

    # =========================================================================
    # 2. Package Re-Exports & Aliases
    # =========================================================================

    def test_02_package_exports_and_aliases(self):
        """Verifies all required classes, aliases, and enums are exported."""
        expected_exports = [
            "AlertDispatcher",
            "MultiChannelAlertDispatcher",
            "NotificationDispatcher",
            "MultiChannelNotifier",
            "Phase106AlertDispatcher",
            "AlertLevel",
            "ChannelType",
        ]
        for exp in expected_exports:
            self.assertTrue(hasattr(notification_pkg, exp), f"Missing export: {exp}")

        self.assertIs(MultiChannelAlertDispatcher, AlertDispatcher)
        self.assertIs(NotificationDispatcher, AlertDispatcher)
        self.assertIs(MultiChannelNotifier, AlertDispatcher)
        self.assertIs(Phase106AlertDispatcher, AlertDispatcher)

    # =========================================================================
    # 3. Credential Validation & Placeholder Handling
    # =========================================================================

    def test_03_telegram_placeholder_detection(self):
        """Verifies detection of placeholder Telegram tokens and chat IDs."""
        placeholders = [
            ("your_telegram_bot_token_here", "12345678"),
            ("123456:valid_token", "your_telegram_chat_id_here"),
            ("changeme", "123456"),
            ("xxx", "xxx"),
            ("dummy", "dummy"),
            ("test", "test"),
            ("", "123456"),
            ("123456", ""),
            (None, None),
        ]
        for token, chat_id in placeholders:
            dispatcher = AlertDispatcher(telegram_token=token, telegram_chat_id=chat_id, enable_console=False)
            self.assertFalse(
                dispatcher.is_telegram_configured(),
                f"Failed to reject placeholder Telegram credentials: token={token}, chat_id={chat_id}",
            )

    def test_04_telegram_token_format_validation(self):
        """Verifies non-standard Telegram token format without colon is rejected."""
        dispatcher = AlertDispatcher(telegram_token="invalid_token_without_colon", telegram_chat_id="123456")
        self.assertFalse(dispatcher.is_telegram_configured())

        dispatcher_non_digit = AlertDispatcher(telegram_token="abc:def_token", telegram_chat_id="123456")
        self.assertFalse(dispatcher_non_digit.is_telegram_configured())

        dispatcher_valid = AlertDispatcher(telegram_token=self.valid_telegram_token, telegram_chat_id=self.valid_telegram_chat)
        self.assertTrue(dispatcher_valid.is_telegram_configured())

    def test_05_slack_placeholder_and_format_validation(self):
        """Verifies Slack webhook placeholder and URL format checks."""
        invalid_urls = [
            "",
            None,
            "your_slack_webhook_url_here",
            "https://hooks.slack.com/services/xxx/yyy/zzz",
            "https://hooks.slack.com/services/your/webhook/url",
            "ftp://hooks.slack.com/services/123",
            "changeme",
        ]
        for url in invalid_urls:
            dispatcher = AlertDispatcher(slack_webhook_url=url, enable_console=False)
            self.assertFalse(
                dispatcher.is_slack_configured(),
                f"Failed to reject invalid Slack webhook URL: {url}",
            )

        dispatcher_valid = AlertDispatcher(slack_webhook_url=self.valid_slack_webhook)
        self.assertTrue(dispatcher_valid.is_slack_configured())

    # =========================================================================
    # 4. Telegram Delivery Tests (Mocked Network)
    # =========================================================================

    @patch("urllib.request.urlopen")
    def test_06_telegram_delivery_success(self, mock_urlopen):
        """Verifies successful Telegram dispatch sends correct JSON payload to endpoint."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        dispatcher = AlertDispatcher(
            telegram_token=self.valid_telegram_token,
            telegram_chat_id=self.valid_telegram_chat,
            enable_console=False,
        )

        ok = dispatcher._send_telegram(text="Test Alert Message", parse_mode="Markdown")
        self.assertTrue(ok)
        self.assertTrue(mock_urlopen.called)

        req = mock_urlopen.call_args[0][0]
        self.assertIn("api.telegram.org", req.full_url)
        self.assertIn(self.valid_telegram_token, req.full_url)

        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["chat_id"], self.valid_telegram_chat)
        self.assertEqual(body["text"], "Test Alert Message")
        self.assertEqual(body["parse_mode"], "Markdown")

    @patch("urllib.request.urlopen")
    def test_07_telegram_http_error_fault_isolation(self, mock_urlopen):
        """Verifies Telegram HTTP 429/500 errors are safely trapped without crashing."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.telegram.org",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=io.BytesIO(b'{"ok":false,"error_code":429}'),
        )

        dispatcher = AlertDispatcher(
            telegram_token=self.valid_telegram_token,
            telegram_chat_id=self.valid_telegram_chat,
            enable_console=False,
        )

        # Must return False and not raise
        ok = dispatcher._send_telegram("Message during rate limit")
        self.assertFalse(ok)

    @patch("urllib.request.urlopen")
    def test_08_telegram_network_timeout_fault_isolation(self, mock_urlopen):
        """Verifies Telegram network timeout / URLError is safely caught."""
        mock_urlopen.side_effect = urllib.error.URLError("Connection timed out")

        dispatcher = AlertDispatcher(
            telegram_token=self.valid_telegram_token,
            telegram_chat_id=self.valid_telegram_chat,
            enable_console=False,
            timeout=5.0,
        )

        ok = dispatcher._send_telegram("Message during network timeout")
        self.assertFalse(ok)

    # =========================================================================
    # 5. Slack Delivery Tests (Mocked Network)
    # =========================================================================

    @patch("urllib.request.urlopen")
    def test_09_slack_delivery_success(self, mock_urlopen):
        """Verifies successful Slack webhook dispatch sends JSON to target webhook URL."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        dispatcher = AlertDispatcher(
            slack_webhook_url=self.valid_slack_webhook,
            enable_console=False,
        )

        ok = dispatcher._send_slack(text="Slack notification test")
        self.assertTrue(ok)
        self.assertTrue(mock_urlopen.called)

        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, self.valid_slack_webhook)

        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["text"], "Slack notification test")

    @patch("urllib.request.urlopen")
    def test_10_slack_http_error_fault_isolation(self, mock_urlopen):
        """Verifies Slack HTTP 500 error is safely caught without exception."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url=self.valid_slack_webhook,
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=io.BytesIO(b"server error"),
        )

        dispatcher = AlertDispatcher(
            slack_webhook_url=self.valid_slack_webhook,
            enable_console=False,
        )

        ok = dispatcher._send_slack(text="Message during Slack outage")
        self.assertFalse(ok)

    @patch("urllib.request.urlopen")
    def test_11_slack_socket_timeout_fault_isolation(self, mock_urlopen):
        """Verifies socket.timeout is safely trapped during Slack dispatch."""
        mock_urlopen.side_effect = socket.timeout("Socket timed out")

        dispatcher = AlertDispatcher(
            slack_webhook_url=self.valid_slack_webhook,
            enable_console=False,
        )

        ok = dispatcher._send_slack(text="Message during socket timeout")
        self.assertFalse(ok)

    # =========================================================================
    # 6. Console Audit Logging & Unicode Safety
    # =========================================================================

    def test_12_console_audit_logging_and_unicode_safety(self):
        """Verifies console logging handles Korean and special Unicode characters safely."""
        dispatcher = AlertDispatcher(enable_console=True)

        korean_title = "파이프라인 실행 요약 [삼성전자/SK하이닉스/현대차]"
        korean_msg = "KOSPI 2D 레짐: BULL_LOW_VOL. 37대 다변화 전략 알파 스코어 산출 완료."

        # Should execute cleanly without UnicodeEncodeError
        ok = dispatcher._send_console(
            title=korean_title,
            message=korean_msg,
            level=AlertLevel.SUCCESS,
            data={"market": "KOSPI", "symbols": ["005930", "000660", "005380"]},
        )
        self.assertTrue(ok)

    def test_13_console_disabled_setting(self):
        """Verifies console output can be disabled via enable_console=False."""
        dispatcher = AlertDispatcher(enable_console=False)
        self.assertFalse(dispatcher.is_console_enabled())
        ok = dispatcher._send_console(title="Test", message="Test", level=AlertLevel.INFO)
        self.assertTrue(ok)

    # =========================================================================
    # 7. Dry-Run Mode & Telemetry Tracking
    # =========================================================================

    def test_14_dry_run_mode_behavior(self):
        """Verifies dry-run mode validates alerts without performing actual network I/O."""
        dispatcher = AlertDispatcher(
            telegram_token=self.valid_telegram_token,
            telegram_chat_id=self.valid_telegram_chat,
            slack_webhook_url=self.valid_slack_webhook,
            dry_run=True,
            enable_console=False,
        )

        # In dry run mode, both configured channels return True without calling urlopen
        res = dispatcher.dispatch(
            title="Dry Run Test",
            message="Validating payload formatting in dry run mode",
            level=AlertLevel.INFO,
        )
        self.assertTrue(res.get("telegram", False))
        self.assertTrue(res.get("slack", False))
        self.assertTrue(res.get("console", False))

        self.assertEqual(len(dispatcher.dispatched_history), 1)
        history_item = dispatcher.dispatched_history[0]
        self.assertEqual(history_item["title"], "Dry Run Test")
        self.assertTrue(history_item["dry_run"])

    # =========================================================================
    # 8. Generic Dispatch Method & Level Parsing
    # =========================================================================

    def test_15_dispatch_channel_filtering_and_level_normalization(self):
        """Verifies dispatch restricts to specified channels and normalizes string levels."""
        dispatcher = AlertDispatcher(dry_run=True, enable_console=True)

        # Dispatch only to console
        res = dispatcher.dispatch(
            title="Console Only",
            message="Restricted channel test",
            level="warning",
            channels=[ChannelType.CONSOLE],
        )
        self.assertIn("console", res)
        self.assertNotIn("telegram", res)
        self.assertNotIn("slack", res)

        # Test level string fallback
        res_invalid_level = dispatcher.dispatch(
            title="Unknown Level",
            message="Fallback test",
            level="NON_EXISTENT_LEVEL",
            channels=[ChannelType.CONSOLE],
        )
        self.assertTrue(res_invalid_level.get("console", False))

    # =========================================================================
    # 9. Typed Event: Pipeline Execution Summary across 5 Markets
    # =========================================================================

    def test_16_send_pipeline_summary_formatting_5_markets(self):
        """Verifies send_pipeline_summary formats data across all 5 markets."""
        dispatcher = AlertDispatcher(dry_run=True, enable_console=True)

        mock_picks = {
            "KOSPI": [
                {"symbol": "005930", "name": "삼성전자", "score": 0.912, "price": 75000.0, "target_price": 86250.0},
                {"symbol": "000660", "name": "SK하이닉스", "score": 0.887, "price": 180000.0, "target_price": 207000.0},
            ],
            "KOSDAQ": [
                {"symbol": "247540", "name": "에코프로비엠", "score": 0.845, "price": 195000.0, "target_price": 224250.0},
            ],
            "SP500": [
                {"symbol": "NVDA", "name": "NVIDIA", "score": 0.935, "price": 128.50, "target_price": 147.78},
                {"symbol": "AAPL", "name": "Apple", "score": 0.890, "price": 225.00, "target_price": 258.75},
            ],
            "NASDAQ": [
                {"symbol": "MSFT", "name": "Microsoft", "score": 0.905, "price": 420.00, "target_price": 483.00},
            ],
            "RUSSELL2000": [
                {"symbol": "SMCI", "name": "Super Micro", "score": 0.820, "price": 45.00, "target_price": 51.75},
            ],
        }

        ok = dispatcher.send_pipeline_summary(
            run_id="PIPE-20261014-001",
            duration_sec=142.5,
            regime_2d="BULL_LOW_VOL",
            top_picks_per_market=mock_picks,
            status="SUCCESS",
        )
        self.assertTrue(ok)

        self.assertTrue(len(dispatcher.dispatched_history) >= 1)
        last_event = dispatcher.dispatched_history[-1]
        self.assertIn("PIPE-20261014-001", last_event["title"])
        self.assertIn("KOSPI", last_event["message"])
        self.assertIn("SP500", last_event["message"])
        self.assertIn("005930", last_event["message"])
        self.assertIn("NVDA", last_event["message"])
        self.assertIn("2m 22.5s", last_event["message"])

    def test_17_send_pipeline_summary_with_empty_picks(self):
        """Verifies send_pipeline_summary operates cleanly with empty picks."""
        dispatcher = AlertDispatcher(dry_run=True, enable_console=True)

        ok = dispatcher.send_pipeline_summary(
            run_id="PIPE-EMPTY-002",
            duration_sec=45.2,
            regime_2d="CRISIS_HIGH_VOL",
            top_picks_per_market={},
            status="WARNING",
        )
        self.assertTrue(ok)

        last_event = dispatcher.dispatched_history[-1]
        self.assertEqual(last_event["level"], AlertLevel.WARNING.value)

    # =========================================================================
    # 10. Typed Event: Paper Fill Confirmation
    # =========================================================================

    def test_18_send_paper_fill_confirmation_buy_krw(self):
        """Verifies send_paper_fill_confirmation formats BUY order for KRW market."""
        dispatcher = AlertDispatcher(dry_run=True, enable_console=True)

        ok = dispatcher.send_paper_fill_confirmation(
            order_id="ORD-KRX-20261014-101",
            symbol="005930",
            market="KOSPI",
            action="BUY",
            ordered_qty=100,
            filled_qty=100,
            price=75200.0,
            slippage_bps=0.4500,
            net_impact=15200.0,
            gate_passed="Gate 1~8 ALL PASS",
            notes="Almgren-Chriss TWAP 5 tranches complete",
        )
        self.assertTrue(ok)

        last_event = dispatcher.dispatched_history[-1]
        self.assertIn("BUY", last_event["title"])
        self.assertIn("005930", last_event["title"])
        self.assertIn("75,200 KRW", last_event["message"])
        self.assertIn("0.4500 bps", last_event["message"])
        self.assertIn("Almgren-Chriss", last_event["message"])

    def test_19_send_paper_fill_confirmation_sell_usd(self):
        """Verifies send_paper_fill_confirmation formats SELL order for US market."""
        dispatcher = AlertDispatcher(dry_run=True, enable_console=True)

        ok = dispatcher.send_paper_fill_confirmation(
            order_id="ORD-US-20261014-202",
            symbol="NVDA",
            market="SP500",
            action="SELL",
            ordered_qty=50,
            filled_qty=50,
            price=128.45,
            slippage_bps=0.1200,
            net_impact=0.4520,
            gate_passed="Gate 8 Hedge Rebalance",
        )
        self.assertTrue(ok)

        last_event = dispatcher.dispatched_history[-1]
        self.assertIn("SELL", last_event["title"])
        self.assertIn("NVDA", last_event["title"])
        self.assertIn("$128.45", last_event["message"])
        self.assertIn("$0.4520", last_event["message"])

    # =========================================================================
    # 11. Typed Event: Circuit Breaker Alert
    # =========================================================================

    def test_20_send_circuit_breaker_flash_crash(self):
        """Verifies send_circuit_breaker_alert formats flash-crash drop events."""
        dispatcher = AlertDispatcher(dry_run=True, enable_console=True)

        ok = dispatcher.send_circuit_breaker_alert(
            trigger_type="FLASH_CRASH_DROP",
            symbol="005930",
            trigger_value=-7.45,
            threshold=-7.00,
            action_taken="EMERGENCY_LIQUIDATION",
            severity="CRITICAL",
            current_price=69500.0,
            peak_price=75200.0,
        )
        self.assertTrue(ok)

        last_event = dispatcher.dispatched_history[-1]
        self.assertEqual(last_event["level"], AlertLevel.CRITICAL.value)
        self.assertIn("FLASH_CRASH_DROP", last_event["message"])
        self.assertIn("-7.45%", last_event["message"])
        self.assertIn("-7.00%", last_event["message"])
        self.assertIn("EMERGENCY_LIQUIDATION", last_event["message"])
        self.assertIn("69,500.00", last_event["message"])

    def test_21_send_circuit_breaker_vix_surge_emergency(self):
        """Verifies send_circuit_breaker_alert formats VIX surge with EMERGENCY level."""
        dispatcher = AlertDispatcher(dry_run=True, enable_console=True)

        ok = dispatcher.send_circuit_breaker_alert(
            trigger_type="VIX_SURGE",
            symbol="^VIX",
            trigger_value=24.80,
            threshold=20.00,
            action_taken="GATE8_INVERSE_HEDGE_OVERLAY",
            severity="EMERGENCY",
        )
        self.assertTrue(ok)

        last_event = dispatcher.dispatched_history[-1]
        self.assertEqual(last_event["level"], AlertLevel.EMERGENCY.value)
        self.assertIn("VIX_SURGE", last_event["message"])
        self.assertIn("+24.80%", last_event["message"])
        self.assertIn("GATE8_INVERSE_HEDGE_OVERLAY", last_event["message"])

    # =========================================================================
    # 12. General Fault Isolation & Non-Crashing Guarantee
    # =========================================================================

    def test_22_arbitrary_unhandled_exception_fault_isolation(self):
        """Verifies dispatcher never raises exceptions even if internal network fails arbitrarily."""
        with patch("urllib.request.urlopen", side_effect=RuntimeError("Unexpected low-level network failure")):
            dispatcher = AlertDispatcher(
                telegram_token=self.valid_telegram_token,
                telegram_chat_id=self.valid_telegram_chat,
                slack_webhook_url=self.valid_slack_webhook,
                enable_console=True,
            )

            # Must not raise RuntimeError
            res = dispatcher.dispatch(
                title="Stress Test Failure",
                message="Testing robustness under arbitrary network exceptions",
                level=AlertLevel.CRITICAL,
            )
            self.assertFalse(res.get("telegram", True))
            self.assertFalse(res.get("slack", True))
            self.assertTrue(res.get("console", False))

    # =========================================================================
    # 13. Adversarial Console & Code Page Encoding Resilience (CP949 / ASCII)
    # =========================================================================

    def test_23_windows_cp949_terminal_encoding_fallback(self):
        """Verifies console logging on Windows CP949 safely falls back without UnicodeEncodeError."""
        class MockCP949Stream:
            encoding = "cp949"
            def __init__(self):
                self.buffer = []
            def write(self, s):
                s.encode("cp949")
                self.buffer.append(s)
            def flush(self):
                pass

        old_stdout = sys.stdout
        try:
            stream = MockCP949Stream()
            sys.stdout = stream
            dispatcher = AlertDispatcher(dry_run=True, enable_console=True)
            res = dispatcher.dispatch(
                title="파이프라인 실행 요약 [삼성전자]",
                message="KOSPI 2D 레짐: BULL_LOW_VOL. 37대 전략 완료. 📢 ✅ 🚀",
                level=AlertLevel.SUCCESS,
            )
            self.assertTrue(res.get("console", False))
            output = "".join(stream.buffer)
            self.assertIn("[ALERT]", output)
            self.assertIn("삼성전자", output)
            self.assertNotIn("\U0001f4e2", output)
        finally:
            sys.stdout = old_stdout

    def test_24_ascii_only_console_fallback(self):
        """Verifies console logging on ASCII-only consoles degrades gracefully to pure ASCII."""
        class MockASCIIStream:
            encoding = "ascii"
            def __init__(self):
                self.buffer = []
            def write(self, s):
                s.encode("ascii")
                self.buffer.append(s)
            def flush(self):
                pass

        old_stdout = sys.stdout
        try:
            stream = MockASCIIStream()
            sys.stdout = stream
            dispatcher = AlertDispatcher(dry_run=True, enable_console=True)
            res = dispatcher.dispatch(
                title="Emergency Alert Title",
                message="Korean 한글 text and emoji 📢 🔥 🚨",
                level=AlertLevel.EMERGENCY,
            )
            self.assertTrue(res.get("console", False))
            output = "".join(stream.buffer)
            self.assertIn("[ALERT]", output)
            self.assertNotIn("\U0001f4e2", output)
            output.encode("ascii")
        finally:
            sys.stdout = old_stdout

    def test_25_broken_pipe_and_os_error_resilience(self):
        """Verifies console delivery traps BrokenPipeError and OSError without crashing."""
        class MockBrokenPipeStream:
            encoding = "utf-8"
            def write(self, s):
                raise BrokenPipeError("Broken pipe simulated")
            def flush(self):
                pass

        old_stdout = sys.stdout
        try:
            sys.stdout = MockBrokenPipeStream()
            dispatcher = AlertDispatcher(dry_run=True, enable_console=True)
            res = dispatcher.dispatch(
                title="Pipe Error Isolation",
                message="Testing non-fatal handling of broken pipes",
                level=AlertLevel.WARNING,
            )
            self.assertTrue(res.get("console", False))
        finally:
            sys.stdout = old_stdout

    def test_26_unrecognized_encoding_and_none_encoding_resilience(self):
        """Verifies console delivery handles unknown codecs and None stream encoding cleanly."""
        class MockUnrecognizedCodecStream:
            encoding = "unrecognized_codec_xyz_999"
            def __init__(self):
                self.buffer = []
            def write(self, s):
                self.buffer.append(s)
            def flush(self):
                pass

        class MockNoneEncodingStream:
            encoding = None
            def __init__(self):
                self.buffer = []
            def write(self, s):
                self.buffer.append(s)
            def flush(self):
                pass

        old_stdout = sys.stdout
        try:
            sys.stdout = MockUnrecognizedCodecStream()
            dispatcher = AlertDispatcher(dry_run=True, enable_console=True)
            res1 = dispatcher.dispatch("Codec Test", "LookupError fallback test", level=AlertLevel.INFO)
            self.assertTrue(res1.get("console", False))

            sys.stdout = MockNoneEncodingStream()
            res2 = dispatcher.dispatch("None Enc Test", "None encoding stream test", level=AlertLevel.INFO)
            self.assertTrue(res2.get("console", False))
        finally:
            sys.stdout = old_stdout

    def test_27_all_typed_events_under_cp949_console(self):
        """Verifies send_pipeline_summary, send_paper_fill_confirmation, and send_circuit_breaker_alert under CP949."""
        class MockCP949Stream:
            encoding = "cp949"
            def __init__(self):
                self.buffer = []
            def write(self, s):
                s.encode("cp949")
                self.buffer.append(s)
            def flush(self):
                pass

        old_stdout = sys.stdout
        try:
            stream = MockCP949Stream()
            sys.stdout = stream
            dispatcher = AlertDispatcher(dry_run=True, enable_console=True)

            mock_picks = {
                "KOSPI": [{"symbol": "005930", "name": "삼성전자", "score": 0.95, "price": 75000.0, "target_price": 86000.0}],
                "SP500": [{"symbol": "NVDA", "name": "NVIDIA", "score": 0.98, "price": 130.0, "target_price": 150.0}],
            }
            ok_summary = dispatcher.send_pipeline_summary(
                run_id="PIPE-CP949-001",
                duration_sec=75.4,
                regime_2d="BULL_LOW_VOL",
                top_picks_per_market=mock_picks,
                status="SUCCESS",
            )
            self.assertTrue(ok_summary)

            ok_fill = dispatcher.send_paper_fill_confirmation(
                order_id="ORD-KRX-CP949-01",
                symbol="005930",
                market="KOSPI",
                action="BUY",
                ordered_qty=100,
                filled_qty=100,
                price=75200.0,
                slippage_bps=0.45,
                net_impact=15000.0,
                gate_passed="Gate 1~8 ALL PASS",
            )
            self.assertTrue(ok_fill)

            ok_cb = dispatcher.send_circuit_breaker_alert(
                trigger_type="FLASH_CRASH_DROP",
                symbol="005930",
                trigger_value=-7.45,
                threshold=-7.00,
                action_taken="EMERGENCY_LIQUIDATION",
                severity="CRITICAL",
                current_price=69500.0,
                peak_price=75200.0,
            )
            self.assertTrue(ok_cb)

            output = "".join(stream.buffer)
            self.assertIn("[ALERT]", output)
            self.assertIn("삼성전자", output)
            self.assertNotIn("\U0001f4e2", output)
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    unittest.main()
