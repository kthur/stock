"""Telegram Bot Live Runner"""

import os
import asyncio
import logging
from typing import Callable
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
from trading_system import StockTradingSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TelegramBotRunner")


def _make_handler(system: StockTradingSystem) -> Callable:
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return
        user_id = update.effective_user.id
        text = update.message.text
        logger.info(f"Telegram live message received from user {user_id}: {text}")
        response = system.process_telegram_message(user_id, text)
        await update.message.reply_text(response, parse_mode="Markdown")
    return handle_message


async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set.")
        return

    logger.info("Initializing live Telegram Bot client...")

    system = StockTradingSystem()
    system.start_telegram_bot()

    application = Application.builder().token(token).build()
    application.add_handler(MessageHandler(filters.TEXT, _make_handler(system)))

    logger.info("Connecting Telegram Bot notifications to EventBus...")

    async def on_order_status_event(order):
        stats = system.get_telegram_bot_stats()
        users = stats.get('users', {})
        for user_id in users:
            try:
                event_type = "order_placed"
                if order.status.value == "EXECUTED":
                    event_type = "order_filled"
                elif order.status.value == "CANCELLED":
                    event_type = "order_cancelled"
                msg = system.send_telegram_notification(user_id, event_type, {
                    'symbol': order.symbol,
                    'quantity': order.quantity,
                    'price': order.price
                })
                logger.info(f"Pushing event alert to user {user_id} via Telegram API...")
                await application.bot.send_message(chat_id=user_id, text=msg)
            except Exception as e:
                logger.error(f"Failed to push telegram alert to {user_id}: {e}")

    system.event_bus.subscribe("order_status", on_order_status_event)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    logger.info("=" * 60)
    logger.info("Telegram Bot daemon successfully started in polling mode.")
    logger.info("Press Ctrl+C to terminate the daemon.")
    logger.info("=" * 60)

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        logger.info("Shutting down Telegram Bot daemon...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Telegram Bot daemon terminated.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
