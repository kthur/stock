import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# 로컬 .env 파일 자동 탐색 및 로드
# trading_system/ 폴더 기준 혹은 그 상위 경로의 .env 탐색
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


@dataclass
class TradingConfig:
    initial_cash: float = 1000000.0
    max_retries: int = 3
    debug_mode: bool = os.getenv("DEBUG_MODE", "True").lower() == "true"
    
    # API 및 토큰 설정 주입
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
