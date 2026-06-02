"""
Telegram Bot Live Runner - 텔레그램 API 연동 백그라운드 데몬
"""

import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
from trading_system import StockTradingSystem

# 로깅 구성
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TelegramBotRunner")

# 전역 시스템 인스턴스
system: StockTradingSystem = None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """모든 텍스트 메시지 및 명령어 수신 핸들러"""
    if not update.message or not update.message.text:
        return
        
    user_id = update.effective_user.id
    text = update.message.text
    
    logger.info(f"Telegram live message received from user {user_id}: {text}")
    
    # 메인 트레이딩 시스템 메시지 프로세서 호출
    response = system.process_telegram_message(user_id, text)
    
    # 응답 발송 (마크다운 포맷 지원)
    await update.message.reply_text(response, parse_mode="Markdown")


async def main():
    global system
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error(
            "TELEGRAM_BOT_TOKEN 환경 변수가 설정되어 있지 않습니다.\n"
            "실제 텔레그램 API 연동을 하려면 '.env' 파일 혹은 환경 변수에 토큰을 설정해 주세요.\n"
            "예시: export TELEGRAM_BOT_TOKEN=\"your_token_here\""
        )
        return
        
    logger.info("Initializing live Telegram Bot client (python-telegram-bot)...")
    
    # python-telegram-bot 애플리케이션 빌드
    application = Application.builder().token(token).build()
    
    # 텍스트 필터 핸들러 등록 (모든 명령어나 일반 채팅 메시지를 일괄 바인딩)
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # 메인 트레이딩 시스템 초기화 및 기동
    system = StockTradingSystem()
    system.start_telegram_bot()
    
    logger.info("Connecting Telegram Bot notifications to EventBus...")
    
    # 주문 상태 변경 이벤트를 구독하여 실시간 푸시 발송
    async def on_order_status_event(order):
        stats = system.get_telegram_bot_stats()
        users = stats.get('users', {})
        
        # 봇에 접근했던 모든 대화방(사용자)에 알림 발송
        for user_id in users:
            try:
                # 주문 상태에 따른 템플릿 정보 생성
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

    # 시스템의 중앙 이벤트 버스에 주문 상태 알림 핸들러 바인딩
    system.event_bus.subscribe("order_status", on_order_status_event)
    
    # 클라이언트 및 updater 초기화
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("=" * 60)
    logger.info("Telegram Bot daemon successfully started in polling mode.")
    logger.info("Press Ctrl+C to terminate the daemon.")
    logger.info("=" * 60)
    
    # 데몬 유지
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down Telegram Bot daemon...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Telegram Bot daemon terminated.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
