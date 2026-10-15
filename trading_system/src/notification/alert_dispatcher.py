"""
alert_dispatcher.py — Multi-Channel Alert & Webhook Dispatcher (Phase 106 / R4 / Feature F503)

Provides lightweight, pure standard-library multi-channel notification dispatching
for the trading system across:
1. Telegram Bot API (https://api.telegram.org)
2. Slack Incoming Webhooks (https://hooks.slack.com)
3. Console & Logging Audit Trail (with Windows CP949 / Unicode fault-tolerance)

Zero external package dependencies: strictly built with urllib.request, urllib.parse,
urllib.error, json, logging, and enum. No requests, aiohttp, httpx, or urllib3.

Includes comprehensive fault isolation (catches network timeouts, HTTP 4xx/5xx, socket
errors, and payload serialization errors without raising exceptions or crashing callers)
and placeholder credential detection.
"""

from __future__ import annotations

import os
import sys
import json
import logging
import socket
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Severity levels for trading system notifications."""
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

    @property
    def emoji(self) -> str:
        """Visual emoji indicator for the severity level."""
        _mapping = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.SUCCESS: "✅",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.CRITICAL: "🚨",
            AlertLevel.EMERGENCY: "🔥",
        }
        return _mapping.get(self, "📢")


class ChannelType(str, Enum):
    """Supported communication channels."""
    TELEGRAM = "telegram"
    SLACK = "slack"
    CONSOLE = "console"


# Canonical placeholder tokens that indicate unconfigured or dummy credentials
_PLACEHOLDER_CREDENTIALS = {
    "your_telegram_bot_token_here",
    "your_telegram_user_id_here",
    "your_telegram_chat_id_here",
    "insert_your_bot_token_here",
    "insert_your_chat_id_here",
    "your_slack_webhook_url_here",
    "https://hooks.slack.com/services/xxx/yyy/zzz",
    "https://hooks.slack.com/services/your/webhook/url",
    "changeme",
    "change_me",
    "xxx",
    "test",
    "token",
    "dummy",
    "placeholder",
    "none",
    "null",
    "undefined",
}


class AlertDispatcher:
    """Multi-channel alert and webhook dispatcher with strict fault isolation.

    Attributes:
        telegram_token (str): Telegram Bot API authorization token.
        telegram_chat_id (str): Telegram destination chat / channel identifier.
        slack_webhook_url (str): Slack incoming webhook HTTPS endpoint.
        dry_run (bool): If True, validates and formats messages without network I/O.
        timeout (float): Network request socket timeout in seconds.
        enable_console (bool): Whether to emit structured console audit logs.
        dispatched_history (List[Dict[str, Any]]): Internal telemetry log of dispatched alerts.
    """

    def __init__(
        self,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        slack_webhook_url: Optional[str] = None,
        dry_run: bool = False,
        timeout: float = 10.0,
        enable_console: bool = True,
        logger_name: Optional[str] = None,
    ) -> None:
        self.telegram_token = (
            telegram_token
            if telegram_token is not None
            else os.environ.get("TELEGRAM_BOT_TOKEN", "")
        ).strip()
        self.telegram_chat_id = (
            telegram_chat_id
            if telegram_chat_id is not None
            else os.environ.get("TELEGRAM_CHAT_ID", "")
        ).strip()
        self.slack_webhook_url = (
            slack_webhook_url
            if slack_webhook_url is not None
            else os.environ.get("SLACK_WEBHOOK_URL", "")
        ).strip()

        self.dry_run = bool(dry_run)
        self.timeout = float(timeout)
        self.enable_console = bool(enable_console)
        self.logger = logging.getLogger(logger_name or __name__)
        self.dispatched_history: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Credential Validation & Placeholder Checks
    # -------------------------------------------------------------------------

    def is_telegram_configured(self) -> bool:
        """Determines whether valid, non-placeholder Telegram credentials exist."""
        if not self.telegram_token or not self.telegram_chat_id:
            return False

        token_norm = self.telegram_token.lower()
        chat_norm = self.telegram_chat_id.lower()

        if token_norm in _PLACEHOLDER_CREDENTIALS or chat_norm in _PLACEHOLDER_CREDENTIALS:
            self.logger.debug("[AlertDispatcher] Telegram credentials match placeholder values.")
            return False

        for placeholder in ("your_telegram", "insert_your", "changeme", "change_me"):
            if placeholder in token_norm or placeholder in chat_norm:
                self.logger.debug("[AlertDispatcher] Telegram credentials contain placeholder substring: %s", placeholder)
                return False

        # Valid Telegram bot tokens must contain a colon separator (e.g., '123456789:AA...')
        if ":" not in self.telegram_token:
            self.logger.debug("[AlertDispatcher] Telegram token lacks standard ':' delimiter.")
            return False

        # Prefix prior to colon must be numeric bot user ID
        prefix = self.telegram_token.split(":", 1)[0]
        if not prefix.isdigit():
            self.logger.debug("[AlertDispatcher] Telegram token prefix is not numeric.")
            return False

        return True

    def is_slack_configured(self) -> bool:
        """Determines whether a valid, non-placeholder Slack webhook URL exists."""
        if not self.slack_webhook_url:
            return False

        url_norm = self.slack_webhook_url.lower()

        if url_norm in _PLACEHOLDER_CREDENTIALS:
            self.logger.debug("[AlertDispatcher] Slack webhook URL matches placeholder value.")
            return False

        for placeholder in ("your_slack", "xxx/yyy/zzz", "changeme", "change_me"):
            if placeholder in url_norm:
                self.logger.debug("[AlertDispatcher] Slack webhook URL contains placeholder: %s", placeholder)
                return False

        if not (url_norm.startswith("https://") or url_norm.startswith("http://")):
            self.logger.debug("[AlertDispatcher] Slack webhook URL lacks HTTP/HTTPS scheme.")
            return False

        return True

    def is_console_enabled(self) -> bool:
        """Returns True if console audit logging is active."""
        return self.enable_console

    # -------------------------------------------------------------------------
    # Channel-Specific Deliveries (Fault-Isolated)
    # -------------------------------------------------------------------------

    def _send_telegram(
        self,
        text: str,
        parse_mode: str = "Markdown",
        buttons: Optional[List[List[Dict[str, str]]]] = None,
    ) -> bool:
        """Transmits an alert to Telegram Bot API with complete fault isolation."""
        if not self.is_telegram_configured():
            return False

        if self.dry_run:
            self.logger.debug("[AlertDispatcher:DRY_RUN] Telegram alert validated: %s", text[:80])
            return True

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": self.telegram_chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "StockTradingSystem/Phase106-AlertDispatcher",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                if 200 <= status < 300:
                    self.logger.info("[AlertDispatcher] Telegram alert delivered (status=%s).", status)
                    return True
                self.logger.warning("[AlertDispatcher] Telegram unexpected HTTP status: %s", status)
                return False
        except urllib.error.HTTPError as exc:
            self.logger.warning(
                "[AlertDispatcher] Telegram HTTPError %s: %s (non-fatal, isolated)",
                exc.code,
                exc.reason,
            )
            return False
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            self.logger.warning(
                "[AlertDispatcher] Telegram network/timeout error: %s (non-fatal, isolated)",
                exc,
            )
            return False
        except Exception as exc:
            self.logger.warning(
                "[AlertDispatcher] Telegram unexpected dispatch exception: %s (non-fatal, isolated)",
                exc,
            )
            return False

    def _send_slack(
        self,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Transmits an alert to Slack Incoming Webhook with complete fault isolation."""
        if not self.is_slack_configured():
            return False

        if self.dry_run:
            self.logger.debug("[AlertDispatcher:DRY_RUN] Slack alert validated: %s", text[:80])
            return True

        payload: Dict[str, Any] = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.slack_webhook_url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "StockTradingSystem/Phase106-AlertDispatcher",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                if 200 <= status < 300:
                    self.logger.info("[AlertDispatcher] Slack webhook delivered (status=%s).", status)
                    return True
                self.logger.warning("[AlertDispatcher] Slack unexpected HTTP status: %s", status)
                return False
        except urllib.error.HTTPError as exc:
            self.logger.warning(
                "[AlertDispatcher] Slack HTTPError %s: %s (non-fatal, isolated)",
                exc.code,
                exc.reason,
            )
            return False
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            self.logger.warning(
                "[AlertDispatcher] Slack network/timeout error: %s (non-fatal, isolated)",
                exc,
            )
            return False
        except Exception as exc:
            self.logger.warning(
                "[AlertDispatcher] Slack unexpected dispatch exception: %s (non-fatal, isolated)",
                exc,
            )
            return False

    def _send_console(
        self,
        title: str,
        message: str,
        level: AlertLevel,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Emits structured console and audit log messages with Windows CP949 safety."""
        if not self.enable_console:
            return True

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        header = f"[{ts}] [{level.emoji} {level.value}] {title}"
        full_text = f"{header}\n{message}"
        if data:
            try:
                data_repr = json.dumps(data, ensure_ascii=False, indent=2)
                full_text = f"{full_text}\nData: {data_repr}"
            except Exception:
                full_text = f"{full_text}\nData: {str(data)}"

        # Log through Python logging facility with complete fault isolation
        try:
            encoding = getattr(sys.stderr, "encoding", None) or getattr(sys.stdout, "encoding", None) or "ascii"
            clean_log_text = full_text.encode(encoding, errors="replace").decode(encoding, errors="replace")
            log_method = {
                AlertLevel.INFO: self.logger.info,
                AlertLevel.SUCCESS: self.logger.info,
                AlertLevel.WARNING: self.logger.warning,
                AlertLevel.CRITICAL: self.logger.error,
                AlertLevel.EMERGENCY: self.logger.critical,
            }.get(level, self.logger.info)
            log_method("[AlertDispatcher] %s", clean_log_text)
        except Exception:
            pass

        # Direct safe terminal output for immediate visibility across CP949, UTF-8, ASCII, and non-TTY pipes
        try:
            print(f"\n📢 {full_text}\n")
        except (UnicodeEncodeError, UnicodeError):
            try:
                # Primary fallback: detect console encoding (e.g. CP949, CP932, Latin-1, ASCII)
                # and encode with error replacement to preserve native characters (e.g. Korean Hangul in CP949)
                # Note: prefix must be pure ASCII '[ALERT]' because '📢' cannot be encoded in CP949 or ASCII
                encoding = getattr(sys.stdout, "encoding", None) or "ascii"
                safe_text = full_text.encode(encoding, errors="replace").decode(encoding, errors="replace")
                print(f"\n[ALERT] {safe_text}\n")
            except (UnicodeEncodeError, UnicodeError, LookupError):
                try:
                    # Secondary fallback: pure ASCII sanitization
                    ascii_text = full_text.encode("ascii", errors="replace").decode("ascii")
                    print(f"\n[ALERT] {ascii_text}\n")
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            # Handles BrokenPipeError, OSError, ValueError (closed stream), etc.
            pass

        return True

    # -------------------------------------------------------------------------
    # Generic Dispatch Interface
    # -------------------------------------------------------------------------

    def dispatch(
        self,
        title: str,
        message: str,
        level: Union[str, AlertLevel] = AlertLevel.INFO,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[Union[str, ChannelType]]] = None,
    ) -> Dict[str, bool]:
        """Dispatches an alert to all configured or specified channels.

        Args:
            title: Headline summary of the alert.
            message: Main markdown or plain text body.
            level: Alert severity (INFO, SUCCESS, WARNING, CRITICAL, EMERGENCY).
            data: Optional structured metadata dictionary.
            channels: Optional list of channels to restrict delivery to.

        Returns:
            Dict mapping channel name to boolean delivery status.
            E.g. {"telegram": True, "slack": False, "console": True}
        """
        if isinstance(level, str):
            try:
                level_enum = AlertLevel(level.upper())
            except ValueError:
                level_enum = AlertLevel.INFO
        else:
            level_enum = level

        # Target channels resolution
        if channels is None:
            active_channels = [ChannelType.TELEGRAM, ChannelType.SLACK, ChannelType.CONSOLE]
        else:
            active_channels = []
            for ch in channels:
                try:
                    c_enum = ChannelType(ch if isinstance(ch, str) else ch.value)
                    active_channels.append(c_enum)
                except ValueError:
                    continue

        results: Dict[str, bool] = {}

        # 1. Console Delivery
        if ChannelType.CONSOLE in active_channels:
            try:
                results[ChannelType.CONSOLE.value] = self._send_console(
                    title=title, message=message, level=level_enum, data=data
                )
            except Exception as exc:
                self.logger.warning(
                    "[AlertDispatcher] Console dispatch exception: %s (non-fatal, isolated)",
                    exc,
                )
                results[ChannelType.CONSOLE.value] = False

        # 2. Telegram Delivery
        if ChannelType.TELEGRAM in active_channels:
            telegram_formatted = f"*{level_enum.emoji} {title}*\n\n{message}"
            results[ChannelType.TELEGRAM.value] = self._send_telegram(
                text=telegram_formatted,
                parse_mode="Markdown",
            )

        # 3. Slack Delivery
        if ChannelType.SLACK in active_channels:
            slack_formatted = f"*{level_enum.emoji} {title}*\n\n{message}"
            results[ChannelType.SLACK.value] = self._send_slack(
                text=slack_formatted,
            )

        # Record telemetry history
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "message": message,
            "level": level_enum.value,
            "data": data,
            "results": results,
            "dry_run": self.dry_run,
        }
        self.dispatched_history.append(record)

        return results

    # -------------------------------------------------------------------------
    # Typed Event Emission Methods
    # -------------------------------------------------------------------------

    def send_pipeline_summary(
        self,
        run_id: str,
        duration_sec: float,
        regime_2d: str,
        top_picks_per_market: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        status: str = "SUCCESS",
    ) -> bool:
        """Formats and transmits an end-of-pipeline operational summary.

        Args:
            run_id: Unique pipeline execution identifier.
            duration_sec: Total pipeline duration in elapsed seconds.
            regime_2d: Detected 2D market regime label (e.g. BULL_LOW_VOL).
            top_picks_per_market: Mapping of market to list of top pick dictionaries.
            status: Overall status outcome ('SUCCESS', 'WARNING', 'FAILURE').

        Returns:
            True if at least one delivery channel (including console) succeeded.
        """
        is_success = (status.upper() == "SUCCESS")
        level = AlertLevel.SUCCESS if is_success else AlertLevel.WARNING
        title = f"Trading Pipeline {status.upper()} — Run {run_id}"

        mins = int(duration_sec // 60)
        secs = duration_sec % 60
        duration_str = f"{mins}m {secs:.1f}s" if mins > 0 else f"{secs:.1f}s"

        lines = [
            f"• *Run ID*: `{run_id}`",
            f"• *Status*: `{status.upper()}`",
            f"• *Duration*: `{duration_str}`",
            f"• *2D Market Regime*: `{regime_2d}`",
        ]

        if top_picks_per_market:
            lines.append("\n📊 *Top Conviction Picks by Market*:")
            for market, picks in top_picks_per_market.items():
                lines.append(f"\n*{market}*:")
                if not picks:
                    lines.append("  _(No high-conviction signals generated)_")
                    continue
                for idx, p in enumerate(picks[:5], 1):
                    sym = p.get("symbol", "N/A")
                    name = p.get("name", sym)
                    score = p.get("score", p.get("ensemble_score", 0.0))
                    price = p.get("price", p.get("close", 0.0))
                    target = p.get("target_price", price * 1.15 if price else 0.0)
                    currency = "KRW" if market in ("KOSPI", "KOSDAQ") else "$"
                    price_fmt = f"{price:,.0f} {currency}" if currency == "KRW" else f"${price:,.2f}"
                    target_fmt = f"{target:,.0f} {currency}" if currency == "KRW" else f"${target:,.2f}"
                    lines.append(
                        f"  {idx}. `{sym}` ({name}) | Score: `{score:.3f}` | Price: `{price_fmt}` | Tgt: `{target_fmt}`"
                    )

        lines.append(f"\n🔗 Dashboard: https://kthur.github.io/stock/")
        message = "\n".join(lines)

        data = {
            "run_id": run_id,
            "duration_sec": duration_sec,
            "regime_2d": regime_2d,
            "status": status,
            "market_count": len(top_picks_per_market) if top_picks_per_market else 0,
        }

        res = self.dispatch(title=title, message=message, level=level, data=data)
        return any(res.values())

    def send_paper_fill_confirmation(
        self,
        order_id: str,
        symbol: str,
        market: str,
        action: str,
        ordered_qty: Union[int, float],
        filled_qty: Union[int, float],
        price: float,
        slippage_bps: float,
        net_impact: float,
        gate_passed: Optional[str] = "Gate 1~8 PASS",
        notes: Optional[str] = None,
    ) -> bool:
        """Formats and transmits an autonomous paper-trading execution fill alert.

        Args:
            order_id: Unique order ID in trade_logs.db.
            symbol: Ticker symbol (e.g. 005930, NVDA).
            market: Market venue (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
            action: Order action ('BUY' or 'SELL').
            ordered_qty: Target order quantity.
            filled_qty: Realized fill quantity.
            price: Executed fill price.
            slippage_bps: Execution slippage in basis points.
            net_impact: Total market impact cost deducted.
            gate_passed: Name or description of OMS safety gate clearance.
            notes: Optional execution remarks.

        Returns:
            True if at least one delivery channel (including console) succeeded.
        """
        action_upper = action.upper()
        action_emoji = "🟢" if action_upper == "BUY" else "🔴"
        title = f"Paper Fill: {action_emoji} {action_upper} {symbol} ({market})"

        currency = "KRW" if market in ("KOSPI", "KOSDAQ") else "USD"
        price_fmt = f"{price:,.0f} KRW" if currency == "KRW" else f"${price:,.2f}"
        impact_fmt = f"{net_impact:,.2f} KRW" if currency == "KRW" else f"${net_impact:,.4f}"

        lines = [
            f"• *Order ID*: `{order_id}`",
            f"• *Asset*: `{symbol}` ({market})",
            f"• *Action*: *{action_upper}*",
            f"• *Quantity*: Filled `{filled_qty}` / Ordered `{ordered_qty}`",
            f"• *Execution Price*: `{price_fmt}`",
            f"• *Slippage*: `{slippage_bps:.4f} bps`",
            f"• *Gatheral 3/2 Market Impact*: `{impact_fmt}`",
            f"• *OMS Safety Gate*: `{gate_passed}`",
        ]
        if notes:
            lines.append(f"• *Notes*: {notes}")

        message = "\n".join(lines)
        data = {
            "order_id": order_id,
            "symbol": symbol,
            "market": market,
            "action": action_upper,
            "ordered_qty": ordered_qty,
            "filled_qty": filled_qty,
            "price": price,
            "slippage_bps": slippage_bps,
            "net_impact": net_impact,
            "gate_passed": gate_passed,
        }

        res = self.dispatch(title=title, message=message, level=AlertLevel.SUCCESS, data=data)
        return any(res.values())

    def send_circuit_breaker_alert(
        self,
        trigger_type: str,
        symbol: str,
        trigger_value: float,
        threshold: float,
        action_taken: str,
        severity: str = "CRITICAL",
        current_price: Optional[float] = None,
        peak_price: Optional[float] = None,
    ) -> bool:
        """Formats and transmits an urgent risk circuit breaker trip alert.

        Args:
            trigger_type: Type of circuit breaker (e.g. FLASH_CRASH_DROP, VIX_SURGE, TRAILING_STOP).
            symbol: Ticker symbol or macro indicator identifier.
            trigger_value: Actual metric value that caused the trip (e.g. -7.4% drop, 22.5% VIX spike).
            threshold: Prescribed risk limit that was breached.
            action_taken: Mitigation order issued (e.g. EMERGENCY_LIQUIDATION, GATE8_INVERSE_HEDGE).
            severity: Urgency label ('CRITICAL' or 'EMERGENCY').
            current_price: Optional current asset price.
            peak_price: Optional peak / high-water price.

        Returns:
            True if at least one delivery channel (including console) succeeded.
        """
        sev_upper = severity.upper()
        level = AlertLevel.EMERGENCY if sev_upper == "EMERGENCY" else AlertLevel.CRITICAL
        title = f"RISK CIRCUIT BREAKER TRIGGERED: [{trigger_type}] on {symbol}"

        lines = [
            f"🚨 *URGENT INTRADAY RISK MITIGATION ACTIVATED*",
            f"• *Trigger Event*: `{trigger_type}`",
            f"• *Target Symbol*: `{symbol}`",
            f"• *Observed Value*: `{trigger_value:+.2f}%`",
            f"• *Breached Threshold*: `{threshold:+.2f}%`",
            f"• *Immediate Action*: *{action_taken}*",
            f"• *Severity Rating*: `{sev_upper}`",
        ]
        if current_price is not None:
            lines.append(f"• *Current Price*: `{current_price:,.2f}`")
        if peak_price is not None:
            lines.append(f"• *High Watermark*: `{peak_price:,.2f}`")

        lines.append("\n⚠️ Order sent to Execution OMS for immediate execution priority.")
        message = "\n".join(lines)

        data = {
            "trigger_type": trigger_type,
            "symbol": symbol,
            "trigger_value": trigger_value,
            "threshold": threshold,
            "action_taken": action_taken,
            "severity": sev_upper,
            "current_price": current_price,
            "peak_price": peak_price,
        }

        res = self.dispatch(title=title, message=message, level=level, data=data)
        return any(res.values())


# -----------------------------------------------------------------------------
# Backward Compatibility & Alias Trees
# -----------------------------------------------------------------------------
MultiChannelAlertDispatcher = AlertDispatcher
NotificationDispatcher = AlertDispatcher
MultiChannelNotifier = AlertDispatcher
Phase106AlertDispatcher = AlertDispatcher
