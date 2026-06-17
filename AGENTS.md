# Stock Trading System

## Project Overview

통합 주식 자동매매 및 예측 시스템. 3,379개 종목(한국 KOSPI/KOSDAQ/KONEX + 미국 SP500)을 대상으로 4개 전략을 병행 운영:

| # | 전략 | 방식 | 출력 |
|---|------|------|------|
| **1** | XGBoost 회귀 | 8개 horizon(1~200d) 예상수익률 | `pipeline_result.txt` |
| **2** | Surge 분류기 | 4개 horizon(1/3/5/20d) 20%↑ 확률 | `surge_predictions.txt` |
| **3** | Lead-Lag | 시총 TOP50 leader 상관관계 기반 후행 종목 | `lead_lag_predictions.txt` |
| **4** | VCP 패턴 | 변동성 수축 + 거래량 감소 + 고점 근접 규칙 | `vcp_patterns.txt` |
| **5** | VCP ML | KOSPI/KOSDAQ/KONEX/SP500 시장별 XGBClassifier | `vcp_ml_predictions.txt` |

## Pipeline

`run_pipeline.py` 실행 순서:

```
1. Load config (TradingConfig)
2. Fetch global indicators (VIX, TNX, USDKRW, etc.)
3. Store market indicators
4. Load/update stock universe (3379 symbols)
5. Fetch indicator history (train + inference)
6. Prepare training data (ThreadPoolExecutor + fundamental fetch)
7. Train:
   a. Regression (per market: sp500/kospi/kosdaq/konex)
   b. Surge classifier (per market)
   c. Lead-Lag matrix
   d. VCP ML (per market)
8. Fetch inference fundamentals (background)
9. Fetch inference price data (ALL symbols)
10. Predict:
    a. Regression + Surge (shared feature computation)
    b. VCP rule-based pattern detection
    c. Lead-Lag inference
    d. VCP ML inference
11. Save predictions to DB
12. Save 5 output files
```

## Architecture

### Key Files

| Path | 목적 |
|------|------|
| `trading_system/run_pipeline.py` | 통합 파이프라인 오케스트레이션 |
| `src/ai/prediction_model.py` | OnDevicePredictionModel: 회귀 + surge + lead-lag |
| `src/ai/vcp_detector.py` | 규칙 기반 VCP 패턴 검출 |
| `src/ai/vcp_ml_predictor.py` | 시장별 VCP XGBoost surge 분류기 |
| `src/data_layer/indicator_storage.py` | MarketIndicatorStorage: 지표/펀더멘탈 DB |
| `src/data_layer/earnings_data.py` | Rate-limit retry + progress logging fundamental fetch |
| `src/persistence/database.py` | StockPriceDB: OHLCV 캐시 |
| `src/config.py` | TradingConfig (.env 기반 설정) |

### Markets

market 컬럼 값: `SP500`, `KOSPI`, `KOSDAQ`, `KONEX` (FinanceDataReader 원본 그대로 저장)

### Pipeline 출력 파일

`trading_system/` 하위에 생성:

| 파일 | 전략 | 내용 |
|------|------|------|
| `pipeline_result.txt` | 회귀 | 종목별 horizon별 예상수익률 |
| `surge_predictions.txt` | Surge | Horizon별 20%↑ 확률 TOP20 |
| `lead_lag_predictions.txt` | Lead-Lag | Leader 움직임 기반 follower 점수 |
| `vcp_patterns.txt` | VCP 규칙 | 변동성 수축 패턴 발견 종목 |
| `vcp_ml_predictions.txt` | VCP ML | 시장별 VCP 기반 surge 확률 TOP10 |

### Features (ALL_FEATURES = 23개)

- Returns: `ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`
- Moving averages: `sma_20`, `dist_sma_20`
- Volatility: `vol_20d`
- Normalized: `norm_market_cap`, `norm_floating_value`, `norm_volume`
- Fundamentals: `operating_margin`, `net_profit_margin`, `eps_yield`, `revenue_to_market_cap`, `dividend_yield`, `eps_growth_1y`, `revenue_growth_1y`
- Global: `vix_change`, `us10y`, `usdkrw_change`, `sp500_change`, `dxy_change`, `wti_change`, `kospi_change`, `kosdaq_change`

### VCP Features (11개)

`range_5v20`, `range_10v20`, `range_20v40`, `range_40v60`, `vol_20v60`, `dist_ma50`, `dist_ma200`, `range_pos_10d`, `range_pos_20d`, `atr_14d_norm`, `monotonic`, `vcp_score`

## Constraints

### XGBoost 2.1.4
- `XGBRegressor._estimator_type` 누락 버그
- `model.get_booster().save_model()` 사용
- `save_model()` 호출시 `_get_type()` → `TypeError` 가능

### 데이터
- `stock_prices.db`: 255MB, 3388 symbols (training cache)
- Universe 3379 symbols, DB 3388 symbols, overlap 3376
- `STOCK_PRICE_FRESHNESS_DAYS=none`: offline cache-only
- 한국 시장: 거래정지(Volume=0) + 관리종목(KRX-ADMINISTRATIVE) → display에서 제외 (DB 저장은 유지)

### 모델 학습
- 전략1(회귀): `TRAIN_SAMPLE_SP500=all`, `TRAIN_SAMPLE_KRX=all` → 3379개 전량
- 전략2(Surge): `surge_horizons=[1,3,5,20]`, `surge_threshold=0.20`, `min_child_weight=10`, `max_delta_step=5`, `scale_pos_weight ≤ 500`
- 전략3(Lead-Lag): 시총 상위 50개 leader, lag-1 correlation
- 전략5(VCP ML): 4 markets × 4 horizons = 16 XGBClassifiers

## Setup

```bash
# Virtual env
python3 -m venv .venv && source .venv/bin/activate
pip install -r trading_system/requirements.txt

# Run pipeline
.venv/bin/python trading_system/run_pipeline.py

# Run tests
.venv/bin/pytest tests/ -v
```

## Python Env

모든 Python 작업은 반드시 `.venv/bin/python` 사용:

```bash
# Always use .venv
.venv/bin/python trading_system/run_pipeline.py
.venv/bin/pytest tests/ -v
.venv/bin/pip install <package>
```

## CRITICAL: models/ files

`trading_system/models/` 아래 `.json` 파일들은 매 파이프라인 실행마다 재생성되는 XGBoost 모델 파일입니다.
이 파일들은 절대 commit/push하지 마세요.

## Original Requirements History

| 요청 | 날짜 | 설명 |
|------|------|------|
| R1 | 2025-06-12 | Post-market scoring + dashboard |
| R2 | 2025-06-12 | 시가총액/거래량/유동주식 feature engineering |
| R3 | 2025-06-12 | 펀더멘탈(매출/영업이익/배당) + 12-feature 모델 |
| R4 | 2025-06-13 | Orchestrator daemon + Telegram alert |
| R5 | 2025-06-13 | Risk management 고도화 + backtest report |
| R6 | 이후 | 통합 파이프라인 + 4전략 + VCP ML |

## Performance

OPTIMIZATION_REPORT.md 참조. 주요 병목:
- 중복 `fetch_historical_data()` 호출 → `TechnicalCache`로 해결
- 동기식 Event Callback → async 전환
- Portfolio Value 중복 계산 → 1회 계산 후 전파
- 예상 효과: Order latency 4.7x, Tick 처리 16x 개선
