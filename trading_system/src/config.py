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
    initial_cash: float = 100_000_000.0
    max_retries: int = 3
    debug_mode: bool = False
    mock_trading: bool = True  # 모의투자 API 연동 활성화 여부
    broker_type: str = "KIS"
    db_path: str = "market_indicators.db"
    train_sample_sp500: int = 50
    train_sample_krx: int = 50
    train_start_date: str = "2023-01-01"
    train_seed: int = 42
    stock_price_freshness_days: int = 7
    update_interval: int = 0
    skip_training: bool = False
    skip_inference: bool = False
    fundamental_cache_expiry_days: int = 90

    # 백테스트 기간 설정 (숫자=년)
    backtest_years: int = 5

    # 주가 DB 경로
    stock_price_db_path: str = "stock_prices.db"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    telegram_bot_token: str = ""
    telegram_authorized_user_ids: str = ""

    # KIS 모의투자 키 설정
    kis_mock_app_key: str = ""
    kis_mock_app_secret: str = ""
    kis_mock_account: str = ""

    # DART 공시 API 키 (OpenDART)
    dart_api_key: str = ""

    # 한국은행 ECOS API 키
    ecos_api_key: str = ""

    # VCP 실시간 돌파 파라미터
    vcp_near_pivot_pct: float = 0.02       # Pivot 돌파 허용 여유 (2%)
    vcp_min_score_threshold: float = 50.0  # VCP 패턴 최소 점수 임계값
    vcp_volume_surge_ratio: float = 1.50   # 돌파 확인 거래량 비율 (평균 대비 150%)

    # 감성 메타 필터 파라미터
    sentiment_risk_threshold: float = 0.70  # 이 이상이면 블랙리스트 등록
    sentiment_crawl_naver_news: bool = True  # 네이버 금융 뉴스 크롤링 활성화

    # 앙상블 스코어 및 거래비용/유동성/슬리피지 파라미터
    ensemble_return_multiplier: float = 20.0  # ensemble_score → expected_return 환산 계수
    min_daily_volume_krx: float = 5_000_000_000.0  # KRX 최소 일평균 거래대금 (50억원)
    min_daily_volume_sp500: float = 1_000_000.0   # SP500 최소 일평균 거래량 (100만 주)
    slippage_krx_market_order: float = 0.005      # KRX 시가 슬리피지 (0.5%)

    # Order Book Market Impact & Bid-Ask Spread Cost Parameters (R2)
    order_size_krx: float = 50_000_000.0        # KRX 기본 주문 금액 가설 (5천만원)
    order_size_sp500: float = 50_000.0          # SP500 기본 주문 금액 가설 ($50,000)
    market_impact_coeff_krx: float = 0.75       # KRX 시장 충격 Square-Root 계수 Y
    market_impact_coeff_sp500: float = 0.50     # SP500 시장 충격 Square-Root 계수 Y
    base_spread_kospi: float = 0.0006           # KOSPI 기준 스프레드 (0.06%)
    base_spread_kosdaq: float = 0.0010          # KOSDAQ 기준 스프레드 (0.10%)
    base_spread_nasdaq: float = 0.0003          # NASDAQ 기준 스프레드 (0.03%)
    base_spread_russell2000: float = 0.0008     # RUSSELL2000 기준 스프레드 (0.08%)
    base_spread_sp500: float = 0.0002           # SP500 기준 스프레드 (0.02%)
    default_volatility_krx: float = 0.020       # KRX 기본 일일 변동성 (2.0%)
    default_volatility_sp500: float = 0.015     # SP500 기본 일일 변동성 (1.5%)

    # 포트폴리오 자본금 단일 소스 (KRW, GHA/OMS/HRP 모두 여기에서 읽음)
    portfolio_capital_krw: float = 100_000_000.0  # 1억 원

    # 실시간 장중 모니터링 (realtime_monitor.py)
    realtime_interval_min: int = 15          # 폴링 간격 (분)
    realtime_dry_run: bool = True            # 실매매 없이 모의 실행
    realtime_stop_loss_pct: float = -0.04    # 진입 대비 손절 임계
    realtime_take_profit_pct: float = 0.08   # 진입 대비 익절 임계
    realtime_vix_threshold: float = 28.0     # VIX 위기 임계
    realtime_usdkrw_threshold: float = 1450.0  # USD/KRW 위기 임계
    realtime_max_order_value_krw: float = 50_000_000.0  # 주문 금액 상한
    realtime_signal_reversal_threshold: float = -0.03   # 신호 보정 역행 임계 (시가 대비)
    realtime_trade_enabled: bool = False                # 실매매 활성화 (env: REALTIME_TRADE_ENABLED)
    kiwoom_account: str = ""                 # 키움 계좌번호 (실매매 시)
    realtime_state_db: str = "realtime_state.db"  # 장중 상태 DB

    _parsed_authorized_user_ids: list = field(default_factory=list, init=False, repr=False)


    def __post_init__(self):
        # Override fields with env variables if set in os.environ
        # This ensures dynamic env evaluation at instantiation time
        if "DEBUG_MODE" in os.environ:
            self.debug_mode = os.environ["DEBUG_MODE"].lower() == "true"
        if "MOCK_TRADING_ENABLED" in os.environ:
            self.mock_trading = os.environ["MOCK_TRADING_ENABLED"].lower() == "true"
        if "BROKER_TYPE" in os.environ:
            self.broker_type = os.environ["BROKER_TYPE"]
        if "DB_PATH" in os.environ:
            self.db_path = os.environ["DB_PATH"]
        if "TRAIN_SAMPLE_SP500" in os.environ:
            self.train_sample_sp500 = os.environ["TRAIN_SAMPLE_SP500"]
        if "TRAIN_SAMPLE_KRX" in os.environ:
            self.train_sample_krx = os.environ["TRAIN_SAMPLE_KRX"]
        if "TRAIN_START_DATE" in os.environ:
            self.train_start_date = os.environ["TRAIN_START_DATE"]
        if "TRAIN_SEED" in os.environ:
            self.train_seed = os.environ["TRAIN_SEED"]
        if "STOCK_PRICE_FRESHNESS_DAYS" in os.environ:
            self.stock_price_freshness_days = os.environ["STOCK_PRICE_FRESHNESS_DAYS"]
        if "UPDATE_INTERVAL" in os.environ:
            self.update_interval = os.environ["UPDATE_INTERVAL"]
        if "SKIP_TRAINING" in os.environ:
            self.skip_training = os.environ["SKIP_TRAINING"].lower() == "true"
        if "SKIP_INFERENCE" in os.environ:
            self.skip_inference = os.environ["SKIP_INFERENCE"].lower() == "true"
        if "FUNDAMENTAL_CACHE_EXPIRY_DAYS" in os.environ:
            try:
                self.fundamental_cache_expiry_days = int(os.environ["FUNDAMENTAL_CACHE_EXPIRY_DAYS"])
            except ValueError:
                logger.warning("Invalid FUNDAMENTAL_CACHE_EXPIRY_DAYS in env, keeping default")
        if "BACKTEST_YEARS" in os.environ:
            self.backtest_years = os.environ["BACKTEST_YEARS"]
        if "STOCK_PRICE_DB_PATH" in os.environ:
            self.stock_price_db_path = os.environ["STOCK_PRICE_DB_PATH"]
        if "OPENAI_API_KEY" in os.environ:
            self.openai_api_key = os.environ["OPENAI_API_KEY"]
        if "OPENAI_MODEL" in os.environ:
            self.openai_model = os.environ["OPENAI_MODEL"]
        if "TELEGRAM_BOT_TOKEN" in os.environ:
            self.telegram_bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
        if "TELEGRAM_AUTHORIZED_USER_IDS" in os.environ:
            self.telegram_authorized_user_ids = os.environ["TELEGRAM_AUTHORIZED_USER_IDS"]
        if "KIS_MOCK_APP_KEY" in os.environ:
            self.kis_mock_app_key = os.environ["KIS_MOCK_APP_KEY"]
        if "KIS_MOCK_APP_SECRET" in os.environ:
            self.kis_mock_app_secret = os.environ["KIS_MOCK_APP_SECRET"]
        if "KIS_MOCK_ACCOUNT" in os.environ:
            self.kis_mock_account = os.environ["KIS_MOCK_ACCOUNT"]
        if "DART_API_KEY" in os.environ:
            self.dart_api_key = os.environ["DART_API_KEY"]
        if "ECOS_API_KEY" in os.environ:
            self.ecos_api_key = os.environ["ECOS_API_KEY"]
        elif "KOREABANK_ECOS_KEY" in os.environ:
            self.ecos_api_key = os.environ["KOREABANK_ECOS_KEY"]
        if "VCP_NEAR_PIVOT_PCT" in os.environ:
            try:
                self.vcp_near_pivot_pct = float(os.environ["VCP_NEAR_PIVOT_PCT"])
            except ValueError:
                pass
        if "VCP_MIN_SCORE_THRESHOLD" in os.environ:
            try:
                self.vcp_min_score_threshold = float(os.environ["VCP_MIN_SCORE_THRESHOLD"])
            except ValueError:
                pass
        if "VCP_VOLUME_SURGE_RATIO" in os.environ:
            try:
                self.vcp_volume_surge_ratio = float(os.environ["VCP_VOLUME_SURGE_RATIO"])
            except ValueError:
                pass
        if "SENTIMENT_RISK_THRESHOLD" in os.environ:
            try:
                self.sentiment_risk_threshold = float(os.environ["SENTIMENT_RISK_THRESHOLD"])
            except ValueError:
                pass
        if "ENSEMBLE_RETURN_MULTIPLIER" in os.environ:
            try:
                self.ensemble_return_multiplier = float(os.environ["ENSEMBLE_RETURN_MULTIPLIER"])
            except ValueError:
                pass
        if "ORDER_SIZE_KRX" in os.environ:
            try:
                self.order_size_krx = float(os.environ["ORDER_SIZE_KRX"])
            except ValueError:
                pass
        if "ORDER_SIZE_SP500" in os.environ:
            try:
                self.order_size_sp500 = float(os.environ["ORDER_SIZE_SP500"])
            except ValueError:
                pass
        if "MARKET_IMPACT_COEFF_KRX" in os.environ:
            try:
                self.market_impact_coeff_krx = float(os.environ["MARKET_IMPACT_COEFF_KRX"])
            except ValueError:
                pass
        if "MARKET_IMPACT_COEFF_SP500" in os.environ:
            try:
                self.market_impact_coeff_sp500 = float(os.environ["MARKET_IMPACT_COEFF_SP500"])
            except ValueError:
                pass
        if "BASE_SPREAD_KOSPI" in os.environ:
            try:
                self.base_spread_kospi = float(os.environ["BASE_SPREAD_KOSPI"])
            except ValueError:
                pass
        if "BASE_SPREAD_KOSDAQ" in os.environ:
            try:
                self.base_spread_kosdaq = float(os.environ["BASE_SPREAD_KOSDAQ"])
            except ValueError:
                pass
        if "BASE_SPREAD_NASDAQ" in os.environ:
            try:
                self.base_spread_nasdaq = float(os.environ["BASE_SPREAD_NASDAQ"])
            except ValueError:
                pass
        if "BASE_SPREAD_RUSSELL2000" in os.environ:
            try:
                self.base_spread_russell2000 = float(os.environ["BASE_SPREAD_RUSSELL2000"])
            except ValueError:
                pass
        if "BASE_SPREAD_SP500" in os.environ:
            try:
                self.base_spread_sp500 = float(os.environ["BASE_SPREAD_SP500"])
            except ValueError:
                pass
        if "DEFAULT_VOLATILITY_KRX" in os.environ:
            try:
                self.default_volatility_krx = float(os.environ["DEFAULT_VOLATILITY_KRX"])
            except ValueError:
                pass
        if "DEFAULT_VOLATILITY_SP500" in os.environ:
            try:
                self.default_volatility_sp500 = float(os.environ["DEFAULT_VOLATILITY_SP500"])
            except ValueError:
                pass
        if "PORTFOLIO_CAPITAL_KRW" in os.environ:
            try:
                self.portfolio_capital_krw = float(os.environ["PORTFOLIO_CAPITAL_KRW"])
            except ValueError:
                pass
        if "REALTIME_INTERVAL_MIN" in os.environ:
            try:
                self.realtime_interval_min = int(os.environ["REALTIME_INTERVAL_MIN"])
            except ValueError:
                pass
        if "REALTIME_DRY_RUN" in os.environ:
            self.realtime_dry_run = os.environ["REALTIME_DRY_RUN"].lower() not in ("false", "0", "no")
        if "REALTIME_STOP_LOSS_PCT" in os.environ:
            try:
                self.realtime_stop_loss_pct = float(os.environ["REALTIME_STOP_LOSS_PCT"])
            except ValueError:
                pass
        if "REALTIME_TAKE_PROFIT_PCT" in os.environ:
            try:
                self.realtime_take_profit_pct = float(os.environ["REALTIME_TAKE_PROFIT_PCT"])
            except ValueError:
                pass
        if "REALTIME_VIX_THRESHOLD" in os.environ:
            try:
                self.realtime_vix_threshold = float(os.environ["REALTIME_VIX_THRESHOLD"])
            except ValueError:
                pass
        if "REALTIME_USDKRW_THRESHOLD" in os.environ:
            try:
                self.realtime_usdkrw_threshold = float(os.environ["REALTIME_USDKRW_THRESHOLD"])
            except ValueError:
                pass
        if "REALTIME_MAX_ORDER_VALUE_KRW" in os.environ:
            try:
                self.realtime_max_order_value_krw = float(os.environ["REALTIME_MAX_ORDER_VALUE_KRW"])
            except ValueError:
                pass
        if "REALTIME_SIGNAL_REVERSAL_THRESHOLD" in os.environ:
            try:
                self.realtime_signal_reversal_threshold = float(os.environ["REALTIME_SIGNAL_REVERSAL_THRESHOLD"])
            except ValueError:
                pass
        if "REALTIME_TRADE_ENABLED" in os.environ:
            self.realtime_trade_enabled = os.environ["REALTIME_TRADE_ENABLED"].lower() in ("true", "1", "yes")
        if "KIWOOM_ACCOUNT" in os.environ:
            self.kiwoom_account = os.environ["KIWOOM_ACCOUNT"]
        if "REALTIME_STATE_DB" in os.environ:
            self.realtime_state_db = os.environ["REALTIME_STATE_DB"]

        self._resolve_db_paths()
        self._parsed_authorized_user_ids = self._parse_authorized_ids()
        self.validate()

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
        return self._parse_authorized_ids()

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
