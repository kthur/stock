# ⚙️ 환경 변수 완전 참조 (Configuration Reference)

> **Source**: `src/config.py` — `TradingConfig` dataclass  
> **File**: `.env` (프로젝트 루트), 템플릿: `.env.example`

---

## 1. 시스템 및 데이터베이스

| 변수명 | 기본값 | 타입 | 설명 |
|--------|--------|------|------|
| `DB_PATH` | `market_indicators.db` | 경로 | 시장 지표 SQLite DB 경로 (상대/절대) |
| `STOCK_PRICE_DB_PATH` | `stock_prices.db` | 경로 | 주가 캐시 SQLite DB 경로 |
| `STOCK_PRICE_FRESHNESS_DAYS` | `7` | 정수/문자열 | 캐시 유효 기간 (일). 특수값: `none`, `never`, `all`, `-1` → 오프라인 모드 (네트워크 미사용) |
| `DEBUG_MODE` | `False` | bool | 디버그 모드 활성화. `True` 시 학습 샘플을 시장당 5개로 제한 |
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

## 2. 데이터 수집

| 변수명 | 기본값 | 타입 | 설명 |
|--------|--------|------|------|
| `UPDATE_INTERVAL` | `0` | 정수 | 종목 데이터 수집 간 대기 시간 (초). 0 = 대기 없음 |
| `INFERENCE_TARGET` | `SP500,KRX` | 콤마 구분 | 추론 대상 시장 |
| `BACKTEST_YEARS` | `5` | 정수/`all` | 백테스트 기간 (년). `all` = 전체 데이터 |

---

## 3. AI 모델 학습

| 변수명 | 기본값 | 타입 | 설명 |
|--------|--------|------|------|
| `TRAIN_SAMPLE_SP500` | `50` | 정수/`%`/`all` | SP500 학습 종목 수. `all` = 전량, `50%` = 절반 |
| `TRAIN_SAMPLE_KRX` | `50` | 정수/`%`/`all` | KRX(KOSPI+KOSDAQ+KONEX) 학습 종목 수 |
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

### 디버그 모드
`DEBUG_MODE=True` 설정 시 위 샘플 크기가 **시장당 5개**로 자동 오버라이드됩니다.

---

## 4. 브로커 설정

| 변수명 | 기본값 | 타입 | 설명 |
|--------|--------|------|------|
| `BROKER_TYPE` | `KIS` | 문자열 | 브로커 타입 (`KIS` = 한국투자증권) |
| `MOCK_TRADING_ENABLED` | `True` | bool | 모의투자 모드 활성화 |
| `KIS_MOCK_APP_KEY` | *(빈 문자열)* | 문자열 | KIS 모의투자 App Key |
| `KIS_MOCK_APP_SECRET` | *(빈 문자열)* | 문자열 | KIS 모의투자 App Secret |
| `KIS_MOCK_ACCOUNT` | *(빈 문자열)* | 문자열 | KIS 모의투자 계좌번호 |

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

> **참고**: LLM API 키가 모두 미설정 시 AI 분석 기능이 비활성화되지만 파이프라인 예측은 정상 작동합니다.

---

## 6. 텔레그램 알림

| 변수명 | 기본값 | 타입 | 설명 |
|--------|--------|------|------|
| `TELEGRAM_BOT_TOKEN` | *(빈 문자열)* | 문자열 | 텔레그램 봇 토큰 (BotFather에서 발급) |
| `TELEGRAM_AUTHORIZED_USER_IDS` | *(빈 문자열)* | 콤마 구분 정수 | 봇 명령 허가 사용자 ID 목록 |

### 텔레그램 봇 설정 방법
1. Telegram에서 @BotFather에게 `/newbot` 명령으로 봇 생성
2. 발급된 토큰을 `TELEGRAM_BOT_TOKEN`에 설정
3. 자신의 Telegram User ID를 `TELEGRAM_AUTHORIZED_USER_IDS`에 설정

```ini
TELEGRAM_BOT_TOKEN=123456789:ABCdefGh...
TELEGRAM_AUTHORIZED_USER_IDS=12345678,87654321
```

---

## 7. 하드코딩된 상수 (코드 내 고정값)

아래 값들은 `.env`로 설정할 수 없으며, 코드 수정이 필요합니다:

| 위치 | 상수 | 값 | 설명 |
|------|------|----|------|
| `run_pipeline.py` L15 | `_CPU_WORKERS` | `os.cpu_count()` | 병렬 작업자 수 |
| `run_pipeline.py` L16 | `_PER_SYMBOL_TIMEOUT` | `30` | 종목당 타임아웃 (초) |
| `run_pipeline.py` L27 | `socket.setdefaulttimeout` | `5` | 소켓 타임아웃 (초) |
| `prediction_model.py` L142 | `horizons` | `[1,5,10,20,30,60,120,200]` | 예측 horizon |
| `prediction_model.py` L143 | `surge_horizons` | `[1,3,5,20]` | Surge horizon |
| `prediction_model.py` L144 | `surge_threshold` | `0.20` | 급등 임계치 (20%) |
| `prediction_model.py` L1784 | Lead-Lag leaders | `nlargest(50)` | 시총 상위 leader 수 |
| `orchestrator.py` L395 | 수집 시각 | `15:45` | 일일 지표 수집 시각 |
| `orchestrator.py` L401 | 스코어링 시각 | `16:30` | 포스트마켓 스코어링 시각 |
| `orchestrator.py` L407 | 학습 시각 | `일요일 01:00` | 주간 모델 재학습 시각 |
