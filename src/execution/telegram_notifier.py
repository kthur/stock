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
from typing import Dict, List, Any, Optional, Union
import pandas as pd

logger = logging.getLogger(__name__)

GH_PAGES_URL = "https://kthur.github.io/stock/"


class TelegramNotifier:
    """Institutional Signal Card Telegram Notifier."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None) -> None:
        self.token = (token or os.environ.get("TELEGRAM_BOT_TOKEN", "")).strip()
        self.chat_id = (chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")).strip()

    def is_enabled(self) -> bool:
        return bool(self.token and self.chat_id)

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
            with urllib.request.urlopen(req, timeout=10) as response:
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

        top_df = ensemble_df.sort_values(by="ensemble_score", ascending=False).head(top_n)

        from datetime import datetime
        dt_str = date_str or datetime.now().strftime("%Y-%m-%d %H:%M KST")

        border = "━━━━━━━━━━━━━━━━━━━━━━"
        lines = [
            f"🚀 *[23-Strategy Multi-Factor TOP {top_n} Signals]*",
            f"📅 Date: `{dt_str}` | Regime: `{regime_name}`",
            border,
        ]

        for rank, (_, row) in enumerate(top_df.iterrows(), 1):
            sym = str(row["symbol"]).strip()
            name = str(row.get("name", sym)).strip()
            mkt = str(row.get("market", "KRX")).strip()
            score = float(row["ensemble_score"]) * 100.0

            close_val = float(row.get("close", row.get("Close", 0.0)))
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
            if "supply_chain_score" in row and pd.notna(row["supply_chain_score"]) and float(row["supply_chain_score"]) > 0:
                strat_contribs.append(f"🔗SC:{float(row['supply_chain_score'])*100:.0f}%")
            if "sentiment_score" in row and pd.notna(row["sentiment_score"]) and float(row["sentiment_score"]) > 0:
                strat_contribs.append(f"🧠Sent:{float(row['sentiment_score'])*100:.0f}%")
            if "factor_neutralized_score" in row and pd.notna(row["factor_neutralized_score"]) and float(row["factor_neutralized_score"]) > 0:
                strat_contribs.append(f"🛡️FN:{float(row['factor_neutralized_score'])*100:.0f}%")
            if "vol_target_score" in row and pd.notna(row["vol_target_score"]) and float(row["vol_target_score"]) > 0:
                strat_contribs.append(f"🎯VT:{float(row['vol_target_score'])*100:.0f}%")
            if "microstructure_score" in row and pd.notna(row["microstructure_score"]) and float(row["microstructure_score"]) > 0:
                strat_contribs.append(f"⚡HFT:{float(row['microstructure_score'])*100:.0f}%")

            if strat_contribs:
                lines.append(f"  • *Attribution*: `{' | '.join(strat_contribs[:4])}`")
            lines.append("")

        lines.append(border)
        lines.append("📊 *Full 23-Strategy Dashboard available on GitHub Pages*")

        card_text = "\n".join(lines)
        buttons = [[{"text": "🌐 Open HTML Dashboard", "url": GH_PAGES_URL}]]

        return self.send_message(card_text, parse_mode="Markdown", buttons=buttons)
