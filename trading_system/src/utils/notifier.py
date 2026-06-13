import logging
import os

import aiohttp

logger = logging.getLogger(__name__)


class NotificationSystem:
    """Telegram 및 Discord 웹훅 기반 알림 시스템"""

    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    async def send_telegram(self, message: str):
        if not self.telegram_token or not self.telegram_chat_id:
            missing = []
            if not self.telegram_token:
                missing.append("TELEGRAM_BOT_TOKEN")
            if not self.telegram_chat_id:
                missing.append("TELEGRAM_CHAT_ID")
            logger.warning(f"Telegram alert skipped: missing config ({', '.join(missing)}). Redirecting to log/console.")
            logger.info(f"[TELEGRAM FALLBACK ALERT] {message}")
            try:
                print(f"📢 [Telegram Fallback Alert]: {message}")
            except UnicodeEncodeError:
                # Handle CP949/other console encoding limitations gracefully
                safe_msg = message.encode('ascii', errors='replace').decode('ascii')
                print(f"[Telegram Fallback Alert]: {safe_msg}")
            return

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "HTML"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(f"Failed to send Telegram message: {resp.status}")
        except Exception as e:
            logger.error(f"Telegram Notification Error: {e}")

    async def send_discord(self, message: str):
        if not self.discord_webhook_url:
            return

        payload = {"content": message}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook_url, json=payload) as resp:
                    if resp.status not in (200, 204):
                        logger.warning(f"Failed to send Discord message: {resp.status}")
        except Exception as e:
            logger.error(f"Discord Notification Error: {e}")

    async def broadcast(self, title: str, message: str):
        """설정된 모든 채널로 메시지 전송"""
        formatted_message = f"<b>{title}</b>\n\n{message}"
        await self.send_telegram(formatted_message)

        discord_message = f"**{title}**\n\n{message}"
        await self.send_discord(discord_message)
