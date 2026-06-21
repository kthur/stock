import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class TradingConfig:
    initial_cash: float = 1000000.0
    max_retries: int = 3
    debug_mode: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    mock_trading: bool = os.getenv("MOCK_TRADING_ENABLED", "True").lower() == "true"  # 모의투자 API 연동 활성화 여부
    broker_type: str = os.getenv("BROKER_TYPE", "KIS")
    db_path: str = os.getenv("DB_PATH", "market_indicators.db")
    train_sample_sp500: str = os.getenv("TRAIN_SAMPLE_SP500", "50")
    train_sample_krx: str = os.getenv("TRAIN_SAMPLE_KRX", "50")
    train_start_date: str = os.getenv("TRAIN_START_DATE", "2023-01-01")
    train_seed: str = os.getenv("TRAIN_SEED", "42")
    stock_price_freshness_days: str = os.getenv("STOCK_PRICE_FRESHNESS_DAYS", "7")
    update_interval: str = os.getenv("UPDATE_INTERVAL", "0")
    skip_training: bool = os.getenv("SKIP_TRAINING", "False").lower() == "true"

    # 백테스트 기간 설정 (숫자=년, "all"=전체)
    backtest_years: str = os.getenv("BACKTEST_YEARS", "5")
    # 주가 DB 경로
    stock_price_db_path: str = os.getenv("STOCK_PRICE_DB_PATH", "stock_prices.db")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_authorized_user_ids: str = os.getenv("TELEGRAM_AUTHORIZED_USER_IDS", "")

    # KIS 모의투자 키 설정
    kis_mock_app_key: str = field(default_factory=lambda: os.getenv("KIS_MOCK_APP_KEY", ""))
    kis_mock_app_secret: str = field(default_factory=lambda: os.getenv("KIS_MOCK_APP_SECRET", ""))
    kis_mock_account: str = field(default_factory=lambda: os.getenv("KIS_MOCK_ACCOUNT", ""))

    _parsed_authorized_user_ids: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        self._resolve_db_paths()
        self._parsed_authorized_user_ids = self._parse_authorized_ids()

    def _resolve_db_paths(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for field_name in ('db_path', 'stock_price_db_path'):
            val = getattr(self, field_name)
            if not os.path.isabs(val):
                setattr(self, field_name, os.path.join(base, val))

    def _parse_authorized_ids(self) -> list:
        if not self.telegram_authorized_user_ids.strip():
            return []
        try:
            return [int(uid.strip()) for uid in self.telegram_authorized_user_ids.split(",") if uid.strip()]
        except ValueError:
            return []

    @property
    def parsed_authorized_user_ids(self) -> list:
        return self._parsed_authorized_user_ids

    def resolve_sample_size(self, value: str, universe_size: int) -> int:
        value = value.strip().lower()
        if value == "all":
            return universe_size
        if value.endswith('%'):
            ratio = float(value.rstrip('%')) / 100.0
            return max(1, int(universe_size * ratio))
        return int(value)

    def get_freshness_days(self) -> int:
        val = self.stock_price_freshness_days.strip().lower()
        if val in ("-1", "never", "all", "none"):
            return -1
        return int(val)

    def get_train_seed(self) -> Optional[int]:
        val = self.train_seed.strip().lower()
        if val in ("none", "", "-1"):
            return None
        return int(val)

    def get_update_interval(self) -> int:
        return int(self.update_interval.strip())

    def validate(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError(f"initial_cash must be positive: {self.initial_cash}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative: {self.max_retries}")
        if self.telegram_bot_token and not self.telegram_authorized_user_ids:
            logger.warning("TELEGRAM_BOT_TOKEN set but TELEGRAM_AUTHORIZED_USER_IDS empty")
        if self.openai_api_key:
            logger.info("OpenAI API key configured")
        if not self.openai_api_key and not os.getenv("GOOGLE_API_KEY", ""):
            logger.warning("No LLM API key configured (OpenAI/Gemini) — AI features disabled")
