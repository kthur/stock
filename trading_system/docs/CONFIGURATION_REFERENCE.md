# ⚙️ 환경 변수 완전 참조 (Configuration Reference)

> **Source**: `src/config.py` — `TradingConfig` dataclass  
> **File**: `.env` (프로젝트 루트 및 `trading_system/.env`), 템플릿: `.env.example`

---

## 1. 시스템 및 데이터베이스

| 변수명 | 기본값 | 타입 | 설명 |
|--------|--------|------|------|
| `DB_PATH` | `market_indicators.db` | 경로 | 시장 지표 SQLite DB 경로 (상대/절대) |
| `STOCK_PRICE_DB_PATH` | `stock_prices.db` | 경로 | 주가 캐시 SQLite DB 경로 |
| `STOCK_PRICE_FRESHNESS_DAYS` | `7` | 정수/문자열 | 캐시 유효 기간 (일). 특수값: `none`, `never`, `all`, `-1` → 오프라인 모드 (네트워크 미사용) |
| `DEBUG_MODE` | `False` | bool | 디버그 모드 활성화. `True` 시 학습 샘플을 시장당 3~5개로 제한 |
| `LOG_LEVEL` | `INFO` | 문자열 | 로깅 레벨 (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### 경로 해석 규칙
- 상대 경로 지정 시 `trading_system/` 디렉토리 기준으로 해석됩니다
- 절대 경로 지정 시 그대로 사용됩니다

### 오프라인 모드
`STOCK_PRICE_FRESHNESS_DAYS`를 `none`으로 설정하면 네트워크 요청 없이 로컬 DB 캐시만 사용합니다:
```ini
STOCK_PRICE_FRESHNESS_DAYS=none
```

---

## 2. 데이터 수집 및 추론

| 변수명 | 기본값 | 타입 | 설명 |
|--------|--------|------|------|
| `UPDATE_INTERVAL` | `0` | 정수 | 종목 데이터 수집 간 대기 시간 (초). 0 = 대기 없음 |
| `INFERENCE_TARGET` | `ALL` | 콤마 구분 | 추론 대상 시장 (`SP500,NASDAQ,RUSSELL2000,KOSPI,KOSDAQ,KONEX` 또는 `KRX`, `ALL`) |
| `BACKTEST_YEARS` | `5` | 정수/`all` | 백테스트 기간 (년). `all` = 전체 데이터 |

---

## 3. AI 모델 학습 및 하이퍼파라미터

| 변수명 | 기본값 | 타입 | 설명 |
|--------|--------|------|------|
| `TRAIN_SAMPLE_SP500` | `50` | 정수/`%`/`all` | SP500 학습 종목 수. `all` = 전량, `50%` = 절반 |
| `TRAIN_SAMPLE_KRX` | `50` | 정수/`%`/`all` | KRX(KOSPI+KOSDAQ) 학습 종목 수 |
| `TRAIN_START_DATE` | `2023-01-01` | 날짜 | 학습 데이터 시작일 (YYYY-MM-DD) |
| `TRAIN_SEED` | `42` | 정수/`none` | 학습 데이터 샘플링 시드. `none` = 무작위 |
| `SKIP_TRAINING` | `False` | bool | `True` 시 기존 모델 파일 재사용 (학습 건너뛰기) |

### 학습 샘플 크기 설정 예시
```ini
# 전량 학습 (3,379 종목 전체)
TRAIN_SAMPLE_SP500=all
TRAIN_SAMPLE_KRX=all

# 시장당 100개씩 샘플링
TRAIN_SAMPLE_SP500=100
TRAIN_SAMPLE_KRX=100

# 비율 기반 (SP500의 50%, KRX의 30%)
TRAIN_SAMPLE_SP500=50%
TRAIN_SAMPLE_KRX=30%
```

---

## 4. 브로커 및 실거래 주문 관리

| 변수명 | 기본값 | 타입 | 설명 |
|--------|--------|------|------|
| `BROKER_TYPE` | `KIS` | 문자열 | 브로커 타입 (`KIS` = 한국투자증권, `KIWOOM`, `DAISHIN` 등) |
| `MOCK_TRADING_ENABLED` | `True` | bool | 모의투자 모드 활성화 (`False` 시 실계좌 주문 가능) |
| `REALTIME_TRADE_ENABLED` | `False` | bool | 실시간 자동 주문 활성화 여부 |
| `REALTIME_MAX_ORDER_VALUE_KRW` | `50,000,000` | 정수 | 건당 최대 주문 금액 (원) |
| `KIS_MOCK_APP_KEY` | *(빈 문자열)* | 문자열 | KIS 모의투자 App Key |
| `KIS_MOCK_APP_SECRET` | *(빈 문자열)* | 문자열 | KIS 모의투자 App Secret |
| `KIS_MOCK_ACCOUNT` | *(빈 문자열)* | 문자열 | KIS 모의투자 계좌번호 |
| `KILL_SWITCH` | *(미설정)* | `0`/`1` | 하드웨어 킬 스위치 (1 설정 시 신규 주문 100% 차단) |

---

## 5. AI/LLM API 설정

| 변수명 | 기본값 | 타입 | 설명 |
|--------|--------|------|------|
| `LLM_PROVIDER` | `gemini` | 문자열 | LLM 제공자 (`openai`, `gemini`, `deepseek`) |
| `OPENAI_API_KEY` | *(빈 문자열)* | 문자열 | OpenAI API 키 |
| `OPENAI_MODEL` | `gpt-4o-mini` | 문자열 | OpenAI 모델명 |
| `GEMINI_API_KEY` | *(빈 문자열)* | 문자열 | Google Gemini API 키 |
| `GEMINI_MODEL` | `gemini-1.5-flash` | 문자열 | Gemini 모델명 |
| `DEEPSEEK_API_KEY` | *(빈 문자열)* | 문자열 | DeepSeek API 키 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 문자열 | DeepSeek 모델명 |

> **참고**: LLM API 키가 모두 미설정 시에도 기본 FinBERT 텍스트 감성 엔진 및 31대 전략 파이프라인 예측은 정상 작동합니다.

---

## 6. 텔레그램 알림

| 변수명 | 기본값 | 타입 | 설명 |
|--------|--------|------|------|
| `TELEGRAM_BOT_TOKEN` | *(빈 문자열)* | 문자열 | 텔레그램 봇 토큰 (BotFather에서 발급) |
| `TELEGRAM_CHAT_ID` | *(빈 문자열)* | 문자열 | 파이프라인 알림 수신 대상 채팅방 ID |
| `TELEGRAM_AUTHORIZED_USER_IDS` | *(빈 문자열)* | 콤마 구분 정수 | 봇 명령 허가 사용자 ID 목록 |

---

## 7. 주요 퀀트 & 시스템 상수 일람

| 위치 | 상수 | 값 | 설명 |
|------|------|----|------|
| `config.py` | `ensemble_return_multiplier` | `20.0` | ensemble_score → expected_return 환산 계수 (20일 기준) |
| `config.py` | `min_daily_volume_krx` | `500,000,000.0` | KRX 최소 일평균 거래대금 (5억 원) |
| `config.py` | `min_daily_volume_sp500` | `1,000,000.0` | US 최소 일평균 거래대금 ($1M USD) |
| `config.py` | `slippage_krx_market_order` | `0.005` | KRX 시가 슬리피지 기본값 (0.5%) |
| `run_pipeline.py` | `_CPU_WORKERS` | `os.cpu_count()` | 병렬 작업자 수 |
| `run_pipeline.py` | `_PER_SYMBOL_TIMEOUT` | `30` | 종목당 타임아웃 (초) |
| `run_pipeline.py` | `socket.setdefaulttimeout` | `5` | 소켓 타임아웃 (초) |
| `prediction_model.py` | `fundamental_filing_lag` | `+60 days` | 재무제표 공시 시차 (Lookahead Bias 제거) |
| `prediction_model.py` | `horizons` | `[1,3,5,10,20,60,120,200]` | 예측 horizon |
| `prediction_model.py` | `surge_horizons` | `[1,3,5,20]` | Surge horizon |
| `prediction_model.py` | `surge_threshold` | `0.20` | 급등 임계치 (20%) |
| `prediction_model.py` | `us_etf_lag_shift` | `shift(1)` | Lead-Lag US 섹터 ETF 1일 시차 Shift |
| `ensemble_scorer.py` | 31대 전략 앙상블 | 31개 Factor/Model | Reg, Surge, LL, VCP Rule/ML, LSTM, Stat-Arb, Sector, RIM, Event, MQ, IV, OF, Rev, ARM, CARD, LATR, InstFor, SC, Sent, Neutral, VolT, Micro, Accrual, ShortSq, ValueUp, Trend, Gamma, Insider, Tone, HFT |
| `ensemble_scorer.py` | Microstructure Cost | STT/SEC + Spread + Market Impact | KOSPI 0.15%, KOSDAQ 0.18%, US SEC 0.003%, 동적 스프레드, Kyle 시장충격 |
| `portfolio_allocator.py`| `HRP Ledoit-Wolf delta` | `0.15` | 공분산 행렬 수축 강도 |
| `portfolio_allocator.py`| `Leland buffer bands` | `[0.5%, 5.0%]` | 동적 No-Trade 턴오버 히스테리시스 밴드 |
| `trading_agent.py` | `ATR_LOOKBACK_DAYS` | `14` | ATR 계산 Lookback 기간 |
| `trading_agent.py` | `ATR_MULTIPLIER` | `2.5` | ATR 손절 및 트레일링 스탑 승수 |
| `trading_agent.py` | `CORRELATION_BLOCK_THRESHOLD` | `0.85` | 포트폴리오 상관관계 BLOCK(매수 차단) 임계치 |
| `trading_agent.py` | `CRISIS_RISK_CAP` | `NONE: 2%, WATCH: 1.5%, ACTIVE: 1%, SEVERE: 0%` | 위기 레벨별 단일 종목 최대 리스크 캡 |
