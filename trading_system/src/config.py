import json
import logging
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

logger = logging.getLogger(__name__)


# Declarative Market Cost & Properties Registry
MARKET_COST_REGISTRY = {
    'KOSPI': {'spread_bps': 0.0006, 'stt': 0.0015, 'brokerage': 0.0003, 'aliases': ('KRX',)},
    'KOSDAQ': {'spread_bps': 0.0010, 'stt': 0.0018, 'brokerage': 0.0003, 'aliases': ()},
    'NASDAQ': {'spread_bps': 0.0003, 'stt': 0.00003, 'brokerage': 0.00005, 'aliases': ()},
    'RUSSELL2000': {'spread_bps': 0.0008, 'stt': 0.00003, 'brokerage': 0.00005, 'aliases': ('RUSSELL',)},
    'SP500': {'spread_bps': 0.0002, 'stt': 0.00003, 'brokerage': 0.00005, 'aliases': ('S&P500', 'NYSE', 'US', 'AMEX')},
    'CHINA_SSE': {'spread_bps': 0.0008, 'stt': 0.0005, 'brokerage': 0.0005, 'aliases': ('CHINA', 'SSE', 'CSI300')},
    'CHINA_SZSE': {'spread_bps': 0.0008, 'stt': 0.0005, 'brokerage': 0.0005, 'aliases': ('SZSE',)},
    'JAPAN_TSE': {'spread_bps': 0.0004, 'stt': 0.0, 'brokerage': 0.0005, 'aliases': ('JAPAN', 'TSE', 'NIKKEI', 'TOPIX')},
    'INDIA_NSE': {'spread_bps': 0.0008, 'stt': 0.0010, 'brokerage': 0.0005, 'aliases': ('INDIA', 'NSE', 'NIFTY50')},
    'INDIA_BSE': {'spread_bps': 0.0008, 'stt': 0.0010, 'brokerage': 0.0005, 'aliases': ('BSE', 'SENSEX')},
    'EUROPE_STOXX': {'spread_bps': 0.0005, 'stt': 0.0010, 'brokerage': 0.0005, 'aliases': ('EUROPE', 'STOXX', 'DAX', 'FTSE', 'CAC')},
    'VIETNAM_HOSE': {'spread_bps': 0.0020, 'stt': 0.0015, 'brokerage': 0.0010, 'aliases': ('VIETNAM', 'HOSE', 'VN30', 'HNX')},
    'TAIWAN_TWSE': {'spread_bps': 0.0006, 'stt': 0.0030, 'brokerage': 0.0005, 'aliases': ('TAIWAN', 'TWSE', 'TAIEX')},
    'AUSTRALIA_ASX': {'spread_bps': 0.0005, 'stt': 0.0, 'brokerage': 0.0005, 'aliases': ('AUSTRALIA', 'ASX', 'ASX200')},
    'BRAZIL_B3': {'spread_bps': 0.0015, 'stt': 0.0, 'brokerage': 0.0010, 'aliases': ('BRAZIL', 'B3', 'IBOVESPA')},
    'HKEX': {'spread_bps': 0.0006, 'stt': 0.0010, 'brokerage': 0.0005, 'aliases': ('HONGKONG', 'HANGSENG')},
    'SINGAPORE_SGX': {'spread_bps': 0.0006, 'stt': 0.0, 'brokerage': 0.0005, 'aliases': ('SINGAPORE', 'SGX', 'STI')},
    'CANADA_TSX': {'spread_bps': 0.0004, 'stt': 0.0, 'brokerage': 0.0005, 'aliases': ('CANADA', 'TSX')},
}

def _build_market_lookup_table():
    registry = {k: dict(v) for k, v in MARKET_COST_REGISTRY.items()}
    env_costs = os.environ.get("MARKET_COSTS_JSON")
    if env_costs:
        try:
            custom_costs = json.loads(env_costs)
            for mkt, cfg in custom_costs.items():
                if mkt in registry and isinstance(cfg, dict):
                    registry[mkt].update(cfg)
                elif isinstance(cfg, dict):
                    registry[mkt] = cfg
        except Exception as e:
            logger.warning(f"Failed to parse MARKET_COSTS_JSON: {e}")

    lookup = {}
    for canonical, info in registry.items():
        lookup[canonical] = info
        for alias in info.get('aliases', ()):
            lookup[alias] = info
    return lookup

_MARKET_LOOKUP = _build_market_lookup_table()


def _get_env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _get_env_bool(key: str, default: bool) -> bool:
    if key in os.environ:
        return os.environ[key].lower() in ("true", "1", "yes", "y")
    return default


def _get_env_int(key: str, default: int) -> int:
    if key in os.environ:
        try:
            return int(os.environ[key])
        except ValueError:
            logger.warning(f"Invalid {key} in env, keeping default {default}")
    return default


def _get_env_float(key: str, default: float) -> float:
    if key in os.environ:
        try:
            v = float(os.environ[key])
            if math.isfinite(v):
                return v
        except ValueError:
            logger.warning(f"Invalid {key} in env, keeping default {default}")
    return default


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
    backtest_years: float = 5.0

    # 주가 DB 경로
    stock_price_db_path: str = "stock_prices.db"

    openai_api_key: str = field(default="", repr=False)
    openai_model: str = "gpt-4o-mini"
    telegram_bot_token: str = field(default="", repr=False)
    telegram_authorized_user_ids: str = field(default="", repr=False)

    # KIS 모의투자 키 설정
    kis_mock_app_key: str = field(default="", repr=False)
    kis_mock_app_secret: str = field(default="", repr=False)
    kis_mock_account: str = field(default="", repr=False)

    # DART 공시 API 키 (OpenDART)
    dart_api_key: str = field(default="", repr=False)

    # 한국은행 ECOS API 키
    ecos_api_key: str = field(default="", repr=False)

    # FRED API 키 (St. Louis Federal Reserve Economic Data)
    fred_api_key: str = field(default="", repr=False)

    # VCP 실시간 돌파 파라미터
    vcp_near_pivot_pct: float = 0.02       # Pivot 돌파 허용 여유 (2%)
    vcp_min_score_threshold: float = 50.0  # VCP 패턴 최소 점수 임계값
    vcp_volume_surge_ratio: float = 1.50   # 돌파 확인 거래량 비율 (평균 대비 150%)

    # 감성 메타 필터 파라미터
    sentiment_risk_threshold: float = 0.70  # 이 이상이면 블랙리스트 등록
    sentiment_crawl_naver_news: bool = True  # 네이버 금융 뉴스 크롤링 활성화

    # 앙상블 스코어 및 거래비용/유동성/슬리피지 파라미터
    ensemble_return_multiplier: float = 20.0  # ensemble_score → expected_return 환산 계수
    min_daily_volume_krx: float = 500_000_000.0   # KRX 최소 일평균 거래대금 (5억원)
    min_daily_volume_sp500: float = 1_000_000.0   # US 최소 일평균 거래대금 ($1M USD)
    slippage_krx_market_order: float = 0.0015     # KRX 시가 슬리피지 (0.15%)

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
    base_spread_china: float = 0.0008           # CHINA (SSE/SZSE) 기준 스프레드 (0.08%)
    base_spread_japan: float = 0.0004           # JAPAN (TSE) 기준 스프레드 (0.04%)
    base_spread_india: float = 0.0008           # INDIA (NSE/BSE) 기준 스프레드 (0.08%)
    base_spread_europe: float = 0.0005          # EUROPE (STOXX/DAX/FTSE) 기준 스프레드 (0.05%)
    base_spread_vietnam: float = 0.0020         # VIETNAM (HOSE) 기준 스프레드 (0.20%)
    base_spread_taiwan: float = 0.0006          # TAIWAN (TWSE) 기준 스프레드 (0.06%)
    base_spread_australia: float = 0.0005       # AUSTRALIA (ASX) 기준 스프레드 (0.05%)
    base_spread_brazil: float = 0.0015          # BRAZIL (B3) 기준 스프레드 (0.15%)
    base_spread_hkex: float = 0.0006            # HONG KONG (HKEX) 기준 스프레드 (0.06%)
    base_spread_singapore: float = 0.0006       # SINGAPORE (SGX) 기준 스프레드 (0.06%)
    base_spread_canada: float = 0.0004          # CANADA (TSX) 기준 스프레드 (0.04%)
    default_volatility_krx: float = 0.020       # KRX 기본 일일 변동성 (2.0%)
    default_volatility_sp500: float = 0.015     # SP500 기본 일일 변동성 (1.5%)
    default_volatility_global: float = 0.018    # 글로벌 기본 일일 변동성 (1.8%)

    # 포트폴리오 자본금 단일 소스 (KRW / USD, GHA/OMS/HRP 모두 여기에서 읽음)
    portfolio_capital_krw: float = 100_000_000.0  # 1억 원
    portfolio_capital_usd: float = 100_000.0      # $100,000 USD
    twap_execution_slices: int = 4                # TWAP 분할 주문 분할수 (Market Impact 완화)

    # Net Alpha Hurdle Rate & Price Limit Parameters (OMS Safety Gate #7)
    oms_net_alpha_safety_margin: float = 0.0010  # 0.10% KRX 안전 마진
    oms_limit_up_lock_threshold: float = 0.295   # 29.5% 이상 시 상한가 잠금으로 간주


    # 실시간 장중 모니터링 (realtime_monitor.py)
    realtime_interval_min: int = 15          # 폴링 간격 (분)
    realtime_dry_run: bool = True            # 실매매 없이 모의 실행
    realtime_stop_loss_pct: float = -0.08    # 진입 대비 손절 임계 (-8%)
    realtime_take_profit_pct: float = 0.08   # 진입 대비 익절 임계
    realtime_vix_threshold: float = 28.0     # VIX 위기 임계
    realtime_usdkrw_threshold: float = 1450.0  # USD/KRW 위기 임계
    realtime_max_order_value_krw: float = 50_000_000.0  # 주문 금액 상한
    realtime_signal_reversal_threshold: float = -0.03   # 신호 보정 역행 임계 (시가 대비)
    realtime_trade_enabled: bool = False                # 실매매 활성화 (env: REALTIME_TRADE_ENABLED)
    kiwoom_account: str = ""                 # 키움 계좌번호 (실매매 시)
    realtime_state_db: str = "realtime_state.db"  # 장중 상태 DB

    _parsed_authorized_user_ids: list = field(default_factory=list, init=False, repr=False)

    # "KIS" (한국투자증권 별칭) → "KOREA_INVESTMENT"로 정규화 (BrokerType enum 명칭과 일치)
    _BROKER_TYPE_ALIASES = {"KIS": "KOREA_INVESTMENT"}

    def _normalize_broker_type(self, value: str) -> str:
        """BrokerType enum 멤버명으로 정규화. 인식 불가 값이면 명시적 오류로 fail-fast.

        실거래 시점(주문 접수)이 아니라 설정 로드 시점에 검증해,
        잘못된 BROKER_TYPE 설정이 조용히 무시되고 키움 커넥터가 대신 실행되는
        사고(실제 계좌 주문)를 원천 차단한다.

        MOCK_TRADING_ENABLED=True(GHA 예측 파이프라인)에서는 BROKER_TYPE=DUMMY/MOCK 이
        정상적인 설정이다 - 실제 주문 라우팅이 없으므로 허용한다.
        """
        try:
            from src.broker.multi_broker_manager import BrokerType
        except Exception:
            return value
        norm = str(value).strip().upper()
        if norm in self._BROKER_TYPE_ALIASES:
            norm = self._BROKER_TYPE_ALIASES[norm]
        if self.mock_trading and norm in ("DUMMY", "MOCK"):
            return norm.lower()
        if not hasattr(BrokerType, norm):
            raise ValueError(
                f"Invalid BROKER_TYPE={value!r}. Valid values: {', '.join(BrokerType.__members__)} "
                f"(alias: KIS -> KOREA_INVESTMENT; DUMMY/MOCK allowed only when MOCK_TRADING_ENABLED=True)"
            )
        return BrokerType[norm].value

    def __post_init__(self):
        # Override fields with env variables dynamically using structured helpers
        self.debug_mode = _get_env_bool("DEBUG_MODE", self.debug_mode)
        self.mock_trading = _get_env_bool("MOCK_TRADING_ENABLED", self.mock_trading)
        if "BROKER_TYPE" in os.environ:
            self.broker_type = os.environ["BROKER_TYPE"]
        self.broker_type = self._normalize_broker_type(self.broker_type)

        self.db_path = _get_env_str("DB_PATH", self.db_path)
        if "TRAIN_SAMPLE_SP500" in os.environ:
            val = os.environ["TRAIN_SAMPLE_SP500"].strip()
            if val.lower() == "all":
                self.train_sample_sp500 = "all"
            else:
                try:
                    self.train_sample_sp500 = int(val)
                except ValueError:
                    self.train_sample_sp500 = val
        if "TRAIN_SAMPLE_KRX" in os.environ:
            val = os.environ["TRAIN_SAMPLE_KRX"].strip()
            if val.lower() == "all":
                self.train_sample_krx = "all"
            else:
                try:
                    self.train_sample_krx = int(val)
                except ValueError:
                    self.train_sample_krx = val
        self.train_start_date = _get_env_str("TRAIN_START_DATE", self.train_start_date)
        self.train_seed = _get_env_int("TRAIN_SEED", self.train_seed)
        self.stock_price_freshness_days = _get_env_int("STOCK_PRICE_FRESHNESS_DAYS", self.stock_price_freshness_days)
        self.update_interval = _get_env_int("UPDATE_INTERVAL", self.update_interval)
        self.skip_training = _get_env_bool("SKIP_TRAINING", self.skip_training)
        self.skip_inference = _get_env_bool("SKIP_INFERENCE", self.skip_inference)
        self.fundamental_cache_expiry_days = _get_env_int("FUNDAMENTAL_CACHE_EXPIRY_DAYS", self.fundamental_cache_expiry_days)

        if "BACKTEST_YEARS" in os.environ:
            try:
                self.backtest_years = float(os.environ["BACKTEST_YEARS"]) if "." in os.environ["BACKTEST_YEARS"] else int(os.environ["BACKTEST_YEARS"])
            except ValueError:
                logger.warning("Invalid BACKTEST_YEARS in env, keeping default")

        self.stock_price_db_path = _get_env_str("STOCK_PRICE_DB_PATH", self.stock_price_db_path)
        self.openai_api_key = _get_env_str("OPENAI_API_KEY", self.openai_api_key)
        self.openai_model = _get_env_str("OPENAI_MODEL", self.openai_model)
        self.telegram_bot_token = _get_env_str("TELEGRAM_BOT_TOKEN", self.telegram_bot_token)
        self.telegram_authorized_user_ids = _get_env_str("TELEGRAM_AUTHORIZED_USER_IDS", self.telegram_authorized_user_ids)
        self.kis_mock_app_key = _get_env_str("KIS_MOCK_APP_KEY", self.kis_mock_app_key)
        self.kis_mock_app_secret = _get_env_str("KIS_MOCK_APP_SECRET", self.kis_mock_app_secret)
        self.kis_mock_account = _get_env_str("KIS_MOCK_ACCOUNT", self.kis_mock_account)
        self.dart_api_key = _get_env_str("DART_API_KEY", self.dart_api_key)

        ecos_val = os.environ.get("ECOS_API_KEY") or os.environ.get("KOREABANK_ECOS_KEY")
        if ecos_val:
            self.ecos_api_key = ecos_val
        self.fred_api_key = _get_env_str("FRED_API_KEY", self.fred_api_key)

        # Quantitative & VCP thresholds
        self.vcp_near_pivot_pct = _get_env_float("VCP_NEAR_PIVOT_PCT", self.vcp_near_pivot_pct)
        self.vcp_min_score_threshold = _get_env_float("VCP_MIN_SCORE_THRESHOLD", self.vcp_min_score_threshold)
        self.vcp_volume_surge_ratio = _get_env_float("VCP_VOLUME_SURGE_RATIO", self.vcp_volume_surge_ratio)
        self.sentiment_risk_threshold = _get_env_float("SENTIMENT_RISK_THRESHOLD", self.sentiment_risk_threshold)
        self.ensemble_return_multiplier = _get_env_float("ENSEMBLE_RETURN_MULTIPLIER", self.ensemble_return_multiplier)
        self.min_daily_volume_krx = _get_env_float("MIN_DAILY_VOLUME_KRX", self.min_daily_volume_krx)
        self.min_daily_volume_sp500 = _get_env_float("MIN_DAILY_VOLUME_SP500", self.min_daily_volume_sp500)
        self.slippage_krx_market_order = _get_env_float("SLIPPAGE_KRX_MARKET_ORDER", self.slippage_krx_market_order)
        self.order_size_krx = _get_env_float("ORDER_SIZE_KRX", self.order_size_krx)
        self.order_size_sp500 = _get_env_float("ORDER_SIZE_SP500", self.order_size_sp500)
        self.market_impact_coeff_krx = _get_env_float("MARKET_IMPACT_COEFF_KRX", self.market_impact_coeff_krx)
        self.market_impact_coeff_sp500 = _get_env_float("MARKET_IMPACT_COEFF_SP500", self.market_impact_coeff_sp500)

        # Baseline Spreads
        self.base_spread_kospi = _get_env_float("BASE_SPREAD_KOSPI", self.base_spread_kospi)
        self.base_spread_kosdaq = _get_env_float("BASE_SPREAD_KOSDAQ", self.base_spread_kosdaq)
        self.base_spread_nasdaq = _get_env_float("BASE_SPREAD_NASDAQ", self.base_spread_nasdaq)
        self.base_spread_russell2000 = _get_env_float("BASE_SPREAD_RUSSELL2000", self.base_spread_russell2000)
        self.base_spread_sp500 = _get_env_float("BASE_SPREAD_SP500", self.base_spread_sp500)
        self.base_spread_china = _get_env_float("BASE_SPREAD_CHINA", self.base_spread_china)
        self.base_spread_japan = _get_env_float("BASE_SPREAD_JAPAN", self.base_spread_japan)
        self.base_spread_india = _get_env_float("BASE_SPREAD_INDIA", self.base_spread_india)
        self.base_spread_europe = _get_env_float("BASE_SPREAD_EUROPE", self.base_spread_europe)
        self.base_spread_vietnam = _get_env_float("BASE_SPREAD_VIETNAM", self.base_spread_vietnam)
        self.base_spread_taiwan = _get_env_float("BASE_SPREAD_TAIWAN", self.base_spread_taiwan)
        self.base_spread_australia = _get_env_float("BASE_SPREAD_AUSTRALIA", self.base_spread_australia)
        self.base_spread_brazil = _get_env_float("BASE_SPREAD_BRAZIL", self.base_spread_brazil)
        self.base_spread_hkex = _get_env_float("BASE_SPREAD_HKEX", self.base_spread_hkex)
        self.base_spread_singapore = _get_env_float("BASE_SPREAD_SINGAPORE", self.base_spread_singapore)
        self.base_spread_canada = _get_env_float("BASE_SPREAD_CANADA", self.base_spread_canada)
        self.default_volatility_krx = _get_env_float("DEFAULT_VOLATILITY_KRX", self.default_volatility_krx)
        self.default_volatility_sp500 = _get_env_float("DEFAULT_VOLATILITY_SP500", self.default_volatility_sp500)
        self.default_volatility_global = _get_env_float("DEFAULT_VOLATILITY_GLOBAL", self.default_volatility_global)

        # Net Alpha & Price Limit Parameters
        self.oms_net_alpha_safety_margin = _get_env_float("OMS_NET_ALPHA_SAFETY_MARGIN", self.oms_net_alpha_safety_margin)
        self.oms_limit_up_lock_threshold = _get_env_float("OMS_LIMIT_UP_LOCK_THRESHOLD", self.oms_limit_up_lock_threshold)

        # Capital & Realtime Trading parameters
        cap_val = os.environ.get("PORTFOLIO_CAPITAL_KRW") or os.environ.get("INITIAL_CASH")
        if cap_val:
            try:
                c_flt = float(cap_val)
                if math.isfinite(c_flt) and c_flt > 0:
                    self.portfolio_capital_krw = c_flt
                    self.initial_cash = c_flt
            except ValueError:
                pass

        self.realtime_interval_min = _get_env_int("REALTIME_INTERVAL_MIN", getattr(self, "realtime_interval_min", 5))
        if "REALTIME_DRY_RUN" in os.environ:
            self.realtime_dry_run = os.environ["REALTIME_DRY_RUN"].lower() not in ("false", "0", "no")
        self.realtime_stop_loss_pct = _get_env_float("REALTIME_STOP_LOSS_PCT", getattr(self, "realtime_stop_loss_pct", 0.03))
        self.realtime_take_profit_pct = _get_env_float("REALTIME_TAKE_PROFIT_PCT", getattr(self, "realtime_take_profit_pct", 0.07))
        self.realtime_vix_threshold = _get_env_float("REALTIME_VIX_THRESHOLD", getattr(self, "realtime_vix_threshold", 30.0))
        self.realtime_usdkrw_threshold = _get_env_float("REALTIME_USDKRW_THRESHOLD", getattr(self, "realtime_usdkrw_threshold", 1450.0))
        self.realtime_max_order_value_krw = _get_env_float("REALTIME_MAX_ORDER_VALUE_KRW", getattr(self, "realtime_max_order_value_krw", 10_000_000.0))
        self.realtime_signal_reversal_threshold = _get_env_float("REALTIME_SIGNAL_REVERSAL_THRESHOLD", getattr(self, "realtime_signal_reversal_threshold", 0.35))
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
        for field_name in ('db_path', 'stock_price_db_path', 'realtime_state_db'):
            val = getattr(self, field_name, None)
            if val and not os.path.isabs(val):
                setattr(self, field_name, os.path.join(base, val))

    def _parse_authorized_ids(self) -> list:
        if not self.telegram_authorized_user_ids.strip():
            return []
        res = []
        for uid in self.telegram_authorized_user_ids.split(","):
            uid = uid.strip()
            if not uid:
                continue
            try:
                res.append(int(uid))
            except ValueError:
                logger.warning(f"Invalid Telegram user ID ignored: {uid!r}")
        return res

    @property
    def parsed_authorized_user_ids(self) -> list:
        return self._parse_authorized_ids()

    def resolve_sample_size(self, value: Any, universe_size: int) -> int:
        val = str(value).strip().lower()
        if val == "all":
            return universe_size
        if val.endswith('%'):
            ratio = float(val.rstrip('%')) / 100.0
            return max(1, int(universe_size * ratio))
        return int(val)

    def get_freshness_days(self) -> int:
        val = str(self.stock_price_freshness_days).strip().lower()
        if val in ("-1", "never", "all", "none"):
            return -1
        return int(val)

    def get_train_seed(self) -> Optional[int]:
        val = str(self.train_seed).strip().lower()
        if val in ("none", "", "-1"):
            return None
        return int(val)

    def get_update_interval(self) -> int:
        return int(str(self.update_interval).strip())

    def get_base_spread(self, market: str) -> float:
        """Return baseline bid-ask spread ratio for a given market from declarative registry."""
        mkt = str(market).strip().upper()
        # Direct override attributes take precedence for core markets
        if mkt in ('KOSPI', 'KRX'):
            return self.base_spread_kospi
        if mkt == 'KOSDAQ':
            return self.base_spread_kosdaq
        if mkt == 'NASDAQ':
            return self.base_spread_nasdaq
        if mkt in ('RUSSELL2000', 'RUSSELL'):
            return self.base_spread_russell2000
        if mkt in ('SP500', 'S&P500', 'NYSE', 'US'):
            return self.base_spread_sp500

        info = _MARKET_LOOKUP.get(mkt)
        if info and 'spread_bps' in info:
            return float(info['spread_bps'])
        return self.base_spread_sp500

    def get_stt_tax(self, market: str) -> float:
        """Return sell-side securities transaction tax (STT) / Stamp duty for a given market."""
        mkt = str(market).strip().upper()
        info = _MARKET_LOOKUP.get(mkt)
        if info and 'stt' in info:
            return float(info['stt'])
        return 0.0001

    def get_brokerage_fee(self, market: str) -> float:
        """Return one-way estimated brokerage fee ratio for a given market."""
        mkt = str(market).strip().upper()
        info = _MARKET_LOOKUP.get(mkt)
        if info and 'brokerage' in info:
            return float(info['brokerage'])
        if mkt in ('KOSPI', 'KOSDAQ', 'KRX'):
            return 0.0003
        if mkt in ('SP500', 'NASDAQ', 'RUSSELL2000', 'US'):
            return 0.00005
        if mkt in ('VIETNAM', 'VIETNAM_HOSE', 'HOSE', 'BRAZIL', 'BRAZIL_B3'):
            return 0.0010
        return 0.0005

    def get_market_currency(self, market: str) -> str:
        """Return base currency for a given market."""
        mkt = str(market).strip().upper()
        if mkt in ('KOSPI', 'KOSDAQ', 'KRX'):
            return 'KRW'
        if mkt in ('SP500', 'NASDAQ', 'RUSSELL2000', 'US', 'NYSE', 'AMEX'):
            return 'USD'
        if mkt in ('CHINA', 'CHINA_SSE', 'CHINA_SZSE', 'SSE', 'SZSE', 'CSI300'):
            return 'CNY'
        if mkt in ('JAPAN', 'JAPAN_TSE', 'TSE', 'NIKKEI', 'TOPIX'):
            return 'JPY'
        if mkt in ('INDIA', 'INDIA_NSE', 'INDIA_BSE', 'NSE', 'BSE', 'NIFTY50'):
            return 'INR'
        if mkt in ('EUROPE', 'EUROPE_STOXX', 'STOXX', 'DAX', 'CAC'):
            return 'EUR'
        if mkt in ('FTSE', 'UK'):
            return 'GBP'
        if mkt in ('VIETNAM', 'VIETNAM_HOSE', 'HOSE', 'VN30'):
            return 'VND'
        if mkt in ('TAIWAN', 'TAIWAN_TWSE', 'TWSE', 'TAIEX'):
            return 'TWD'
        if mkt in ('AUSTRALIA', 'AUSTRALIA_ASX', 'ASX'):
            return 'AUD'
        if mkt in ('BRAZIL', 'BRAZIL_B3', 'B3'):
            return 'BRL'
        if mkt in ('HKEX', 'HONGKONG'):
            return 'HKD'
        if mkt in ('SINGAPORE', 'SINGAPORE_SGX', 'SGX'):
            return 'SGD'
        if mkt in ('CANADA', 'CANADA_TSX', 'TSX'):
            return 'CAD'
        return 'USD'

    def get_market_flag(self, market: str) -> str:
        """Return country flag emoji for a given market."""
        mkt = str(market).strip().upper()
        flags = {
            'KOSPI': '🇰🇷', 'KOSDAQ': '🇰🇷', 'KRX': '🇰🇷',
            'SP500': '🇺🇸', 'NASDAQ': '🇺🇸', 'RUSSELL2000': '🇺🇸', 'US': '🇺🇸',
            'CHINA_SSE': '🇨🇳', 'CHINA_SZSE': '🇨🇳', 'SSE': '🇨🇳', 'SZSE': '🇨🇳', 'CHINA': '🇨🇳',
            'JAPAN_TSE': '🇯🇵', 'TSE': '🇯🇵', 'JAPAN': '🇯🇵', 'NIKKEI': '🇯🇵',
            'INDIA_NSE': '🇮🇳', 'INDIA_BSE': '🇮🇳', 'NSE': '🇮🇳', 'BSE': '🇮🇳', 'INDIA': '🇮🇳',
            'EUROPE_STOXX': '🇪🇺', 'EUROPE': '🇪🇺', 'STOXX': '🇪🇺', 'DAX': '🇩🇪', 'FTSE': '🇬🇧', 'CAC': '🇫🇷',
            'VIETNAM_HOSE': '🇻🇳', 'HOSE': '🇻🇳', 'VIETNAM': '🇻🇳',
            'TAIWAN_TWSE': '🇹🇼', 'TWSE': '🇹🇼', 'TAIWAN': '🇹🇼',
            'AUSTRALIA_ASX': '🇦🇺', 'ASX': '🇦🇺', 'AUSTRALIA': '🇦🇺',
            'BRAZIL_B3': '🇧🇷', 'B3': '🇧🇷', 'BRAZIL': '🇧🇷',
            'HKEX': '🇭🇰', 'HONGKONG': '🇭🇰',
            'SINGAPORE_SGX': '🇸🇬', 'SGX': '🇸🇬', 'SINGAPORE': '🇸🇬',
            'CANADA_TSX': '🇨🇦', 'TSX': '🇨🇦', 'CANADA': '🇨🇦',
        }
        return flags.get(mkt, '🌐')

    def get_country_risk_free_rate(self, market: str) -> float:
        """Return baseline 10Y sovereign risk-free rate for a given market."""
        mkt = str(market).strip().upper()
        rates = {
            'KOSPI': 0.033, 'KOSDAQ': 0.033, 'KRX': 0.033,
            'SP500': 0.040, 'NASDAQ': 0.040, 'RUSSELL2000': 0.040, 'US': 0.040,
            'CHINA_SSE': 0.022, 'CHINA_SZSE': 0.022, 'SSE': 0.022, 'SZSE': 0.022, 'CHINA': 0.022,
            'JAPAN_TSE': 0.012, 'TSE': 0.012, 'JAPAN': 0.012, 'NIKKEI': 0.012,
            'INDIA_NSE': 0.068, 'INDIA_BSE': 0.068, 'NSE': 0.068, 'BSE': 0.068, 'INDIA': 0.068,
            'EUROPE_STOXX': 0.024, 'EUROPE': 0.024, 'STOXX': 0.024, 'DAX': 0.024, 'CAC': 0.030,
            'FTSE': 0.040, 'UK': 0.040,
            'VIETNAM_HOSE': 0.030, 'HOSE': 0.030, 'VIETNAM': 0.030,
            'TAIWAN_TWSE': 0.016, 'TWSE': 0.016, 'TAIWAN': 0.016,
            'AUSTRALIA_ASX': 0.042, 'ASX': 0.042, 'AUSTRALIA': 0.042,
            'BRAZIL_B3': 0.115, 'B3': 0.115, 'BRAZIL': 0.115,
            'HKEX': 0.038, 'HONGKONG': 0.038,
            'SINGAPORE_SGX': 0.028, 'SGX': 0.028, 'SINGAPORE': 0.028,
            'CANADA_TSX': 0.034, 'TSX': 0.034, 'CANADA': 0.034,
        }
        return rates.get(mkt, 0.040)

    def get_country_risk_premium(self, market: str) -> float:
        """Return Country Risk Premium (CRP, Damodaran standard) for a given market."""
        mkt = str(market).strip().upper()
        crp_map = {
            'KOSPI': 0.005, 'KOSDAQ': 0.005, 'KRX': 0.005,
            'SP500': 0.000, 'NASDAQ': 0.000, 'RUSSELL2000': 0.000, 'US': 0.000,
            'CHINA_SSE': 0.009, 'CHINA_SZSE': 0.009, 'SSE': 0.009, 'SZSE': 0.009, 'CHINA': 0.009,
            'JAPAN_TSE': 0.000, 'TSE': 0.000, 'JAPAN': 0.000,
            'INDIA_NSE': 0.020, 'INDIA_BSE': 0.020, 'NSE': 0.020, 'INDIA': 0.020,
            'EUROPE_STOXX': 0.002, 'EUROPE': 0.002, 'DAX': 0.000, 'FTSE': 0.003,
            'VIETNAM_HOSE': 0.035, 'HOSE': 0.035, 'VIETNAM': 0.035,
            'TAIWAN_TWSE': 0.006, 'TWSE': 0.006, 'TAIWAN': 0.006,
            'AUSTRALIA_ASX': 0.000, 'ASX': 0.000, 'AUSTRALIA': 0.000,
            'BRAZIL_B3': 0.032, 'B3': 0.032, 'BRAZIL': 0.032,
            'HKEX': 0.006, 'HONGKONG': 0.006,
            'SINGAPORE_SGX': 0.000, 'SGX': 0.000, 'SINGAPORE': 0.000,
            'CANADA_TSX': 0.000, 'TSX': 0.000, 'CANADA': 0.000,
        }
        return crp_map.get(mkt, 0.005)

    def get_country_base_erp(self, market: str) -> float:
        """Return base Equity Risk Premium (ERP) for a given market."""
        mkt = str(market).strip().upper()
        if mkt in ('SP500', 'NASDAQ', 'RUSSELL2000', 'US', 'JAPAN', 'JAPAN_TSE', 'TSE', 'SINGAPORE', 'SINGAPORE_SGX', 'SGX', 'AUSTRALIA', 'AUSTRALIA_ASX', 'ASX', 'CANADA', 'CANADA_TSX', 'TSX'):
            return 0.050
        if mkt in ('INDIA', 'INDIA_NSE', 'NSE', 'VIETNAM', 'VIETNAM_HOSE', 'HOSE', 'BRAZIL', 'BRAZIL_B3', 'B3'):
            return 0.065
        return 0.055

    def get_market_timezone(self, market: str) -> str:
        """Return primary timezone string for a given market."""
        mkt = str(market).strip().upper()
        tz_map = {
            'KOSPI': 'Asia/Seoul', 'KOSDAQ': 'Asia/Seoul', 'KRX': 'Asia/Seoul',
            'SP500': 'America/New_York', 'NASDAQ': 'America/New_York', 'RUSSELL2000': 'America/New_York', 'US': 'America/New_York',
            'CHINA_SSE': 'Asia/Shanghai', 'CHINA_SZSE': 'Asia/Shanghai', 'SSE': 'Asia/Shanghai', 'SZSE': 'Asia/Shanghai', 'CHINA': 'Asia/Shanghai',
            'JAPAN_TSE': 'Asia/Tokyo', 'TSE': 'Asia/Tokyo', 'JAPAN': 'Asia/Tokyo',
            'INDIA_NSE': 'Asia/Kolkata', 'INDIA_BSE': 'Asia/Kolkata', 'NSE': 'Asia/Kolkata', 'INDIA': 'Asia/Kolkata',
            'EUROPE_STOXX': 'Europe/Paris', 'EUROPE': 'Europe/Paris', 'STOXX': 'Europe/Paris', 'DAX': 'Europe/Berlin', 'FTSE': 'Europe/London', 'CAC': 'Europe/Paris',
            'VIETNAM_HOSE': 'Asia/Ho_Chi_Minh', 'HOSE': 'Asia/Ho_Chi_Minh', 'VIETNAM': 'Asia/Ho_Chi_Minh',
            'TAIWAN_TWSE': 'Asia/Taipei', 'TWSE': 'Asia/Taipei', 'TAIWAN': 'Asia/Taipei',
            'AUSTRALIA_ASX': 'Australia/Sydney', 'ASX': 'Australia/Sydney', 'AUSTRALIA': 'Australia/Sydney',
            'BRAZIL_B3': 'America/Sao_Paulo', 'B3': 'America/Sao_Paulo', 'BRAZIL': 'America/Sao_Paulo',
            'HKEX': 'Asia/Hong_Kong', 'HONGKONG': 'Asia/Hong_Kong',
            'SINGAPORE_SGX': 'Asia/Singapore', 'SGX': 'Asia/Singapore', 'SINGAPORE': 'Asia/Singapore',
            'CANADA_TSX': 'America/Toronto', 'TSX': 'America/Toronto', 'CANADA': 'America/Toronto',
        }
        return tz_map.get(mkt, 'UTC')

    def get_max_country_weight(self, market: str) -> float:
        """Return maximum portfolio allocation weight cap for a given country (default 35%)."""
        return float(os.getenv("MAX_COUNTRY_WEIGHT", "0.35"))

    def validate(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError(f"initial_cash must be positive: {self.initial_cash}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative: {self.max_retries}")
        if self.min_daily_volume_krx < 0:
            logger.warning(f"min_daily_volume_krx should be non-negative: {self.min_daily_volume_krx}")
        if self.min_daily_volume_sp500 < 0:
            logger.warning(f"min_daily_volume_sp500 should be non-negative: {self.min_daily_volume_sp500}")
        if self.vcp_near_pivot_pct < 0:
            logger.warning(f"vcp_near_pivot_pct should be non-negative: {self.vcp_near_pivot_pct}")
        if self.vcp_min_score_threshold < 0:
            logger.warning(f"vcp_min_score_threshold should be non-negative: {self.vcp_min_score_threshold}")
        if self.vcp_volume_surge_ratio < 0:
            logger.warning(f"vcp_volume_surge_ratio should be non-negative: {self.vcp_volume_surge_ratio}")
        if self.fred_api_key:
            logger.info("FRED API key configured (St. Louis Federal Reserve Data active)")
        if self.ecos_api_key:
            logger.info("Bank of Korea ECOS API key configured")
        if self.dart_api_key:
            logger.info("DART API key configured")
        if self.openai_api_key:
            logger.info("OpenAI API key configured")
        if not self.openai_api_key and not os.getenv("GOOGLE_API_KEY", ""):
            logger.warning("No LLM API key configured (OpenAI/Gemini) — AI features disabled")
        from datetime import datetime
        try:
            datetime.strptime(self.train_start_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"train_start_date '{self.train_start_date}' must be in YYYY-MM-DD format")
