import logging
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

# Telegram Mini App Router
mini_app_router = APIRouter()

@mini_app_router.get("/telegram-mini-app")
async def get_telegram_mini_app():
    """Telegram Mini App (Web App)을 위한 뷰 반환"""
    # 텔레그램 미니 앱 규격에 맞춘 모바일 최적화 UI
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Mini App</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--tg-theme-bg-color, #ffffff);
            color: var(--tg-theme-text-color, #000000);
            margin: 0;
            padding: 20px;
        }
        .btn {
            background-color: var(--tg-theme-button-color, #3390ec);
            color: var(--tg-theme-button-text-color, #ffffff);
            border: none;
            padding: 15px 20px;
            width: 100%;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 10px;
        }
        .card {
            background: var(--tg-theme-secondary-bg-color, #f4f4f5);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <h2>📈 Mini Portfolio</h2>
    <div class="card">
        <h3 style="margin-top:0;">Cash: <span id="cash">$1,000,000</span></h3>
        <p>Total Return: <span style="color: green;">+5.2%</span></p>
    </div>
    
    <button class="btn" onclick="buyApple()">Buy AAPL (Market)</button>
    <button class="btn" style="background-color: #e53935;" onclick="sellApple()">Sell AAPL (Market)</button>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        function buyApple() {
            tg.sendData(JSON.stringify({action: "BUY", symbol: "AAPL"}));
            tg.showAlert("AAPL 매수 주문이 텔레그램 봇으로 전송되었습니다!");
        }

        function sellApple() {
            tg.sendData(JSON.stringify({action: "SELL", symbol: "AAPL"}));
            tg.showAlert("AAPL 매도 주문이 텔레그램 봇으로 전송되었습니다!");
        }
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

def init_mini_app(app):
    """FastAPI 앱에 라우터 등록"""
    app.include_router(mini_app_router, prefix="/mini-app")
    logger.info("Telegram Mini App endpoints initialized")
