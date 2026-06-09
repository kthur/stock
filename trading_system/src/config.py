import logging
import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / '.env'
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

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_authorized_user_ids: str = os.getenv("TELEGRAM_AUTHORIZED_USER_IDS", "")

    _parsed_authorized_user_ids: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        self._parsed_authorized_user_ids = self._parse_authorized_ids()

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

    def validate(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError(f"initial_cash must be positive: {self.initial_cash}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative: {self.max_retries}")
        if self.telegram_bot_token and not self.telegram_authorized_user_ids:
            logger.warning("TELEGRAM_BOT_TOKEN set but TELEGRAM_AUTHORIZED_USER_IDS empty")
