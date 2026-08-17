"""
telegram_notifier.py — Institutional Signal Alert Card Notifier for Telegram

Formats and dispatches high-conviction TOP 5 signal recommendation cards containing:
- Symbol, Name, Market, Current Price
- Estimated Target Price & Stop Loss (-5.0% Risk Boundary)
- 23-Strategy Ensemble Score & Decision Rationale Attribution
- 2D Regime Status and Direct Link to GitHub Pages Dashboard
"""

from __future__ import annotations

import logging
import os
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

GH_PAGES_URL = "https://kthur.github.io/stock/"


class TelegramNotifier:
    """Institutional Signal Card Telegram Notifier."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None) -> None:
        self.token = (token or os.environ.get("TELEGRAM_BOT_TOKEN", "")).strip()
        self.chat_id = (chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")).strip()

    # Placeholder values must never activate notifications: reporting "SUCCESS"
    # while alerts silently never fire is worse than no notifications at all.
    _PLACEHOLDER_VALUES = {
        'your_telegram_bot_token_here',
        'your_telegram_user_id_here',
        'your_telegram_chat_id_here',
        'insert_your_bot_token_here',
        'changeme', 'change_me', 'xxx', 'test', 'token', 'dummy',
    }

    def is_enabled(self) -> bool:
        """Returns True only when token and chat_id look like REAL credentials.

        Placeholder values (e.g. 'your_telegram_bot_token_here', 'xxx') or token
        strings that do not look like Telegram bot tokens are treated as
        unconfigured - otherwise the pipeline reports 'SUCCESS' notifications
        while alerts silently never fire for real failures.
        """
        if not (self.token and self.chat_id):
            return False
        token_norm = str(self.token).strip().lower()
        chat_norm = str(self.chat_id).strip().lower()
        if token_norm in self._PLACEHOLDER_VALUES or chat_norm in self._PLACEHOLDER_VALUES:
            logger.warning("[TelegramNotifier] Credentials look like placeholders - notifications DISABLED.")
            return False
        # Telegram bot tokens look like '123456789:AA...' (digits before the colon)
        if ":" not in self.token:
            logger.warning("[TelegramNotifier] TELEGRAM_BOT_TOKEN does not look like a real bot token (no ':') - notifications DISABLED.")
            return False
        return True

    def send_message(self, text: str, parse_mode: str = "Markdown", buttons: Optional[List[List[Dict[str, str]]]] = None) -> bool:
        if not self.is_enabled():
            logger.debug("[TelegramNotifier] Token or chat_id missing. Notification skipped.")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if buttons:
            payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})

        try:
            data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
                if response.status == 200:
                    logger.info("[TelegramNotifier] Signal card sent successfully.")
                    return True
        except Exception as e:
            logger.warning("[TelegramNotifier] Failed to send Telegram message: %s", e)
        return False

    def send_top_recommendations_card(self, ensemble_df: pd.DataFrame, regime_name: str = "SIDEWAYS_LOW_VOL",
                                       date_str: Optional[str] = None, top_n: int = 5) -> bool:
        """Format and dispatch TOP N signal cards to Telegram.

        Args:
            ensemble_df: Combined 23-strategy prediction DataFrame.
            regime_name: Current 2D market regime label.
            date_str: Forecast date string.
            top_n: Number of top conviction stocks to display.

        Returns:
            True if message was sent successfully.
        """
        if ensemble_df is None or ensemble_df.empty:
            logger.warning("[TelegramNotifier] Empty ensemble_df provided for notification.")
            return False

        if "ensemble_score" not in ensemble_df.columns:
            logger.warning("[TelegramNotifier] 'ensemble_score' column missing in ensemble_df.")
            return False

        import math
        top_df = ensemble_df.sort_values(by="ensemble_score", ascending=False).head(top_n)

        from datetime import datetime
        dt_str = date_str or datetime.now().strftime("%Y-%m-%d %H:%M KST")

        border = "━━━━━━━━━━━━━━━━━━━━━━"
        lines = [
            f"🚀 *[31-Strategy Multi-Factor TOP {top_n} Signals]*",
            f"📅 Date: `{dt_str}` | Regime: `{regime_name}`",
            border,
        ]

        def _safe_float(val, default: float = 0.0) -> float:
            try:
                f = float(val)
                return f if math.isfinite(f) else default
            except (ValueError, TypeError):
                return default

        for rank, (_, row) in enumerate(top_df.iterrows(), 1):
            sym = str(row["symbol"]).strip()
            name = str(row.get("name", sym)).strip()
            mkt = str(row.get("market", "KRX")).strip()
            score = _safe_float(row["ensemble_score"]) * 100.0

            close_val = _safe_float(row.get("close", row.get("Close", 0.0)))
            price_str = f"{close_val:,.0f} KRW" if mkt in ("KOSPI", "KOSDAQ") and close_val > 0 else (f"${close_val:,.2f}" if close_val > 0 else "N/A")

            # Risk boundaries (Target +15%, Stop Loss -5%)
            tp_val = close_val * 1.15 if close_val > 0 else 0.0
            sl_val = close_val * 0.95 if close_val > 0 else 0.0
            tp_str = f"{tp_val:,.0f}" if mkt in ("KOSPI", "KOSDAQ") and tp_val > 0 else (f"${tp_val:,.2f}" if tp_val > 0 else "N/A")
            sl_str = f"{sl_val:,.0f}" if mkt in ("KOSPI", "KOSDAQ") and sl_val > 0 else (f"${sl_val:,.2f}" if sl_val > 0 else "N/A")

            lines.append(f"*{rank}. {name} ({sym})* [{mkt}]")
            lines.append(f"  • *Score*: `{score:.1f}%` | *Price*: `{price_str}`")
            lines.append(f"  • 🎯 *Target*: `{tp_str}` (+15%) | 🛡️ *Stop*: `{sl_str}` (-5%)")

            # Strategy attribution breakdown
            strat_contribs = []
            contrib_keys = [
                ("supply_chain_score", "🔗SC"),
                ("sentiment_score", "🧠Sent"),
                ("factor_neutralized_score", "🛡️FN"),
                ("vol_target_score", "🎯VT"),
                ("microstructure_score", "⚡HFT"),
                ("accruals_score", "📊Accrual"),
                ("short_squeeze_score", "🔥Sq"),
                ("valueup_score", "💎ValUp"),
                ("trend_efficiency_score", "📈KER"),
            ]
            for col_k, label in contrib_keys:
                if col_k in row and pd.notna(row[col_k]):
                    v = _safe_float(row[col_k])
                    if v > 0:
                        strat_contribs.append(f"{label}:{v*100:.0f}%")

            if strat_contribs:
                lines.append(f"  • *Attribution*: `{' | '.join(strat_contribs[:4])}`")
            lines.append("")

        lines.append(border)
        lines.append("📊 *Full 31-Strategy Dashboard available on GitHub Pages*")

        card_text = "\n".join(lines)
        buttons = [[{"text": "🌐 Open HTML Dashboard", "url": GH_PAGES_URL}]]

        return self.send_message(card_text, parse_mode="Markdown", buttons=buttons)
