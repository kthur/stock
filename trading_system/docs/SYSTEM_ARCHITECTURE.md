# 주식 자동매매 시스템 전체 구조 및 알고리즘 명세서

> **Version**: 6.5 (Production Standard)  
> **Last Updated**: 2026-08-22 (KST)  
> **Python**: 3.10+  
> **Database**: SQLite (WAL & Thread-safe Write Mutex)

> [!IMPORTANT]
> 이 문서는 현재 운영 중인 통합 프로덕션 아키텍처를 설명합니다:
> - **31대 다변화 파이프라인 아키텍처** (`run_pipeline.py`): 31대 ML/시계열DL/규칙/수급/옵션/이벤트/공급망/FinBERT감성/Fama-French 5-Factor/변동성타겟팅/미시구조 팩터 전략 앙상블, 횡단면 점수 정규화(`CrossSectionalScoreNormalizer`), 2D 시장 레짐 판정, 포트폴리오 최적화(HRP, Black-Litterman & EVT-CVaR), 실전 미시구조 거래비용 모델 및 RiskManager 위기 제어 파이프라인
> - **이벤트 기반 자율 매매 및 Execution OMS** (`trading_system.py`, `src/execution/`): 7대 주문 안전 게이트, Almgren-Chriss 최적 집행 트랜치 스케줄러, 실시간 오더북 및 체결 슬리피지 피드백 엔진 (`trade_logs.db`)

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [31대 전략 파이프라인 아키텍처](#2-31대-전략-파이프라인-아키텍처)
3. [이벤트 기반 자율 매매 아키텍처](#3-이벤트-기반-자율-매매-아키텍처)
4. [설치 및 설정](#4-설치-및-설정)
5. [실행 방법](#5-실행-방법)
6. [핵심 모듈별 동작 구조](#6-핵심-모듈별-동작-구조)
7. [전략 엔진 상세](#6-전략-엔진-상세)
8. [기술적 지표 목록](#7-기술적-지표-목록)
9. [리스크 관리](#8-리스크-관리)
10. [포지션 사이징](#9-포지션-사이징)
11. [머신러닝/딥러닝](#10-머신러닝딥러닝)
12. [포트폴리오 최적화](#11-포트폴리오-최적화)
13. [시장 레짐 및 스타일 로테이션](#12-시장-레짐-및-스타일-로테이션)
14. [브로커 연동](#13-브로커-연동)
15. [텔레그램 봇 명령어](#14-텔레그램-봇-명령어)
16. [데이터베이스 스키마](#15-데이터베이스-스키마)
17. [테스트](#16-테스트)
18. [전체 파라미터 일람](#17-전체-파라미터-일람)

---

## 1. 프로젝트 개요

### 1.1 목적

한국 주식(KOSPI, KOSDAQ) 및 미국 주식(S&P 500, NASDAQ, RUSSELL 2000) 5대 시장을 대상으로 하는 **기관급 통합 정량적(Quantitative) 트레이딩 및 AI 예측 시스템**입니다.
실시간 매크로/펀더멘탈/시세 수집 → 31대 알파 팩터 산출 → 횡단면 점수 정규화(`CrossSectionalScoreNormalizer`) → 통계적 직교화 및 2D 레짐 앙상블 → HRP/Black-Litterman/EVT-CVaR 포트폴리오 최적화 → 거래비용 차감 → 7대 안전 게이트 & Almgren-Chriss 주문 실행 → 슬리피지 피드백 루프의 전 과정을 완전 자동화합니다.

### 1.2 핵심 특징

| 특징 | 설명 |
|------|------|
| **31대 다변화 전략** | GBDT 회귀/분류, 시계열 LSTM, 공적분 차익거래, 펀더멘탈(RIM/발생액/밸류업), 수급/오더북, 옵션 IV/Gamma, 감성(FinBERT), Fama-French 중립화 등 다각화 |
| **횡단면 점수 정규화** | `CrossSectionalScoreNormalizer` (Percentile Rank / Winsorized Gaussian CDF $[0, 1]$ 매핑) 및 결측 전략 동적 제로 가중치 재정규화 |
| **통계적 위생 (Hygiene)** | PCA-ZCA 대칭 화이트닝 & Gram-Schmidt 직교화, VIF 팩터 노이즈 억제 |
| **2D 시장 레짐 동적 앙상블** | 6대 국면(Bull/Sideways/Bear x Low/High Vol) 실시간 판정 및 전략 가중치 동적 재할당 |
| **포트폴리오 최적화** | Hierarchical Risk Parity (HRP) + Ledoit-Wolf 공분산 축소 + Black-Litterman $C^1$ 스무딩 + EVT-CVaR 꼬리위험 예산 + Leland No-Trade 버퍼 밴드 |
| **실전 미시구조 거래비용** | 한국 STT(0.15%/0.18%), 미국 SEC 수수료, 동적 스프레드, Kyle/Almgren-Chriss 제곱근 시장충격 차감 |
| **Execution OMS & 피드백** | 7대 안전 게이트(Severe 위기 차단, 킬 스위치 등) + Almgren-Chriss 트랜치 스케줄러 + `trade_logs.db` 실체결 슬리피지 파라미터 적응 루프 |
| **데이터 무결성** | 시장별 법정 Filing Lag(KRX 45일, US 40일/실공시일 우선), 층화 샘플링(Stratified Sampling), 적응형 타임아웃 & 지터 백오프 |
| **SQLite WAL 동시성 보호** | WAL 저널 모드, busy_timeout 5,000ms, `threading.Lock()` 쓰기 뮤텍스 완비 |

---

## 2. 31대 전략 파이프라인 아키텍처

**Source**: `run_pipeline.py`

### 2.1 전체 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    run_pipeline.py                              │
│              execute_prediction_pipeline()                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
    ┌────────────────────▼───────────────────┐
    │  1. TradingConfig (.env 로드)           │
    └────────────────────┬───────────────────┘
                         │
    ┌────────────────────▼───────────────────┐
    │  2. GlobalMarketClient                 │
    │     VIX, TNX, USDKRW, SP500, DXY,     │
    │     WTI, Gold, KOSPI, KOSDAQ 수집       │
    │     (적응형 타임아웃 8s/15s + 지터 백오프)│
    └────────────────────┬───────────────────┘
                         │
    ┌────────────────────▼───────────────────┐
    │  3. MarketIndicatorStorage             │
    │     지표 DB 저장 (market_indicators.db) │
    └────────────────────┬───────────────────┘
                         │
    ┌────────────────────▼───────────────────┐
    │  4. 종목 유니버스 로드                  │
    │     KOSPI/KOSDAQ/SP500/NASDAQ/         │
    │     RUSSELL2000 5대 시장               │
    └────────────────────┬───────────────────┘
                         │
    ┌────────────────────▼───────────────────┐
    │  5-6. 학습 데이터 준비 (층화 샘플링)   │
    │   Market x Sector x Cap 층화 샘플링     │
    │   + 동적 Filing Lag (KRX 45d, US 40d)  │
    │   + float32 메모리 다운캐스팅           │
    └────────────────────┬───────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │ 7a. 회귀│    │7b. Surge │    │7c.Lead-Lag│
    │ 학습    │    │ 분류기   │    │ 행렬      │
    │ (시장별)│    │ (시장별) │    │ (+1d US) │
    └─────────┘    └──────────┘    └──────────┘
         └───────────────┼───────────────┘
                         │
    ┌────────────────────▼───────────────────┐
    │  7d. VCP ML 분류기 / LSTM 학습          │
    │  7e. Isotonic & Platt 확률 보정기 학습 │
    └────────────────────┬───────────────────┘
                         │
    ┌────────────────────▼───────────────────┐
    │  8-9. 추론 데이터 수집 (전 종목)         │
    │       ThreadPoolExecutor 병렬 처리      │
    └────────────────────┬───────────────────┘
                         │
    ┌────────────────────▼───────────────────┐
    │  10. 31대 알파 전략 예측 및 스코어링     │
    │      회귀 + Surge + VCP + LSTM + StatArb│
    │      + Sector + RIM + Event + MQ + IV   │
    │      + OF + Reversal + ARM + CARD + LATR│
    │      + InstFor + SupplyChain + Sentiment│
    │      + Neutral + VolT + Micro + Accrual │
    │      + ShortSq + ValueUp + Trend + Gamma│
    │      + Insider + ToneDrift + Darkpool   │
    └────────────────────┬───────────────────┘
                         │
    ┌────────────────────▼───────────────────┐
    │  11. 횡단면 정규화 & 2D 레짐 앙상블     │
    │      CrossSectionalScoreNormalizer      │
    │      + 결측 전략 제로 가중치 재정규화   │
    │      + PCA-ZCA Whitening & Gram-Schmidt │
    │      + 미시구조 거래비용 차감           │
    │      + HRP, Black-Litterman & EVT-CVaR  │
    │      + Leland No-Trade 버퍼 밴드 필터   │
    └────────────────────┬───────────────────┘
                         │
    ┌────────────────────▼───────────────────┐
    │  12. 결과 영속화 및 대시보드 리포트 생성 │
    │   ai_predictions.db + TXT 리포트 생성  │
    │   + gh-pages/index.html 생성 (KST)     │
    └─────────────────────────────────────────┘
```

### 2.2 스레딩 모델 및 리소스 제어

| 컨텍스트 | 방식 | 용도 |
|----------|------|------|
| 데이터 수집 | `ThreadPoolExecutor(max_workers=32)` | 네트워크 I/O 병렬 fetch, 소스별 적응형 타임아웃(8s/15s) |
| 피처 계산 | `ThreadPoolExecutor(max_workers=CPU*2)` | CPU 바운드 기술적 지표 & 피처 추출 |
| 펀더멘탈 수집 | `threading.Thread` (백그라운드) | 동적 Filing Lag 적용 비동기 배치 수집 |

| 모델 학습 | `ProcessPoolExecutor` / `ThreadPoolExecutor` | 시장별 GBDT / ML 독립 훈련 |
| DB 동시성 제어 | `threading.Lock()` 쓰기 뮤텍스 | SQLite WAL 모드 다중 스레드 충돌 원천 방지 |

### 2.3 주요 출력 파일

| 파일 | 전략 | 내용 |
|------|------|------|
| `ensemble_predictions.txt` | 31대 동적 앙상블 | 31대 전략 동적 앙상블 TOP 100 및 Decision Rationale (KST) |
| `strategy_data_coverage_report.txt` | 데이터 결측 분석 | 31대 전략별 데이터 커버리지 및 6대 결측 사유 분석 |
| `pipeline_result.txt` | XGBoost 회귀 | 시장별 TOP 종목, 8개 horizon별 예상수익률 요약 |
| `surge_predictions.txt` | Surge 분류기 | 4개 horizon별 20%↑ 급등 확률 TOP20 |
| `lead_lag_predictions.txt` | Lead-Lag 시차 | Leader-Follower 상관 점수 (+1d US Lag Shift) |
| `vcp_patterns.txt` | VCP 패턴 규칙 | Mark Minervini 변동성 수축 패턴 검출 종목 |
| `vcp_ml_predictions.txt` | VCP ML | 시장별 VCP 기반 surge 확률 TOP10 |
| `stat_arb_predictions.txt` | Stat-Arb | Log 주가 공적분 잔차 Z-score 차익거래 페어 |
| `inst_foreign_sector_predictions.txt` | Inst & Foreign | 기관/외인 60일 누적 수급 가속도 & 주도주 상관성 |
| `supply_chain_predictions.txt` | Supply Chain | 전방 대형주 시차 온기 전이 점수 |
| `sentiment_predictions.txt` | Sentiment | FinBERT 텍스트 감성 촉매 스코어 |
| `factor_neutralized_predictions.txt` | Factor Neutral | Fama-French 5-Factor 중립 순수 알파 |
| `vol_target_predictions.txt` | Vol Targeting | 동적 변동성 타겟팅 리스크 파리티 점수 |
| `microstructure_predictions.txt` | Microstructure | 호가 불균형 & 종가 오버나이트 갭 점수 |


---

## 3. 이벤트 기반 아키텍처 (레거시)

**Source**: `trading_system.py` (약 2,186줄)

### 3.1 전체 구조

```
┌────────────────────────────────────────────────────────────────────┐
│                        StockTradingSystem                          │
│  (trading_system.py - 2186 lines, 메인 오케스트레이터)              │
└────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼────────────────────────────┐
          ▼                         ▼                            ▼
   ┌─────────────┐         ┌───────────────┐          ┌─────────────────┐
   │  EventBus   │◄────────│  SystemFactory │          │  외부 데이터      │
   │  (Pub/Sub)  │────────►│  (DI 컨테이너)  │          │  yfinance        │
   └─────────────┘         └───────────────┘          │  FinanceDataReader│
          │                                            └─────────────────┘
   ┌──────┼──────┐
   ▼      ▼      ▼
┌─────┐ ┌─────┐ ┌──────────┐
│전략  │ │리스크│ │주문/체결 │
│엔진  │ │관리  │ │시스템    │
└─────┘ └─────┘ └──────────┘
   │                      │
   ▼                      ▼
┌──────────┐      ┌──────────────┐
│  AI/ML   │      │  MultiBroker │
│  엔진    │      │  Manager     │
└──────────┘      └──────┬───────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        ┌────────┐ ┌────────┐ ┌────────┐
        │Simulated│ │ Kiwoom │ │  KIS   │ ...
        └────────┘ └────────┘ └────────┘

┌─────────────────────────────────────────────────────────────┐
│ 사용자 인터페이스                                            │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Plotly Dash  │  │  Telegram Bot    │  │  PDF Reports  │ │
│  │ localhost:5000│  │  20개 명령어     │  │               │ │
│  └──────────────┘  └──────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 이벤트 흐름

```
MarketDataHandler ──"market_data"──▶ EventBus ──▶ StrategyEngine
NLPEngine         ──"news_sentiment"─▶ EventBus ──▶ StrategyEngine
StrategyEngine    ──"strategy_signal"▶ EventBus ──▶ RiskManager → OMS
OMS               ──"order_status"──▶ EventBus ──▶ Dashboard / Telegram
Portfolio         ──"account_sync"──▶ EventBus ──▶ Dashboard
```

### 2.3 의존성 주입 (DI)

`SystemFactory.create_default_components()`가 모든 컴포넌트를 생성하고 `StockTradingSystem`에 주입합니다:

```
EventBus, MarketDataHandler, NLPEngine, PortfolioManager,
AccountSyncAgent, HybridStrategyEngine, OptimizationEngine,
OrderManagementSystem, TradeLogger, AssetHistoryDB, RiskManager,
BacktestEngine, AdvancedStatistics, ErrorHandler, BrokerConnector,
MultiBrokerManager, InvestorStrategyEngine, LLMEngine,
GlobalMarketClient, RelativeStrengthAnalyzer
```

---

## 3. 설치 및 설정

### 3.1 설치

```bash
cd trading_system
pip install -r requirements.txt
```

### 3.2 환경 변수 (.env)

```
# 트레이딩 설정
MOCK_TRADING_ENABLED=true
BROKER_TYPE=KIS
DB_PATH=market_indicators.db
TRAIN_SAMPLE_SP500=all
TRAIN_SAMPLE_KRX=all

# LLM API 키 (택1)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
LLM_PROVIDER=openai

# 텔레그램
TELEGRAM_BOT_TOKEN=...
TELEGRAM_AUTHORIZED_USER_IDS=123456,789012

# 한국투자증권 (KIS) 모의
KIS_MOCK_APP_KEY=...
KIS_MOCK_APP_SECRET=...
KIS_MOCK_ACCOUNT=...
```

### 3.3 설정 파일

`risk_config.json` — 위험 관리 기본값 (stop_loss_pct, position_size_pct 등)

---

## 4. 실행 방법

### 4.1 대시보드 실행

```bash
python run_dashboard.py
```
- Plotly Dash 웹 서버 on http://localhost:5000
- 탭: Strategy Performance / Real-time P&L / Backtest Viewer / Global Macro

### 4.2 AI 예측 파이프라인 실행

```bash
python run_pipeline.py
```
- S&P 500 + KRX 전체 종목 대상
- XGBoost 1/5/10/20/30/60일 예측
- 결과 DB 저장 + 콘솔 출력

### 4.3 개별 예측 스크립트

```bash
python scripts/predict_best_stock.py
```

### 4.4 텔레그램 봇 실행

```bash
python telegram_bot_runner.py
```
또는 시스템 내에서 `system.start_telegram_bot()` 호출

### 4.5 최적화 실행

```bash
python update_optimize.py
```
- Adaptive Parameter Optimizer 기반 Bayesian 최적화

### 4.6 시스템 테스트

```bash
python -m pytest tests/
```

### 4.7 코드 품질 검사

```bash
ruff check src/
mypy src/
```

---

## 5. 핵심 모듈별 동작 구조

### 5.1 StockTradingSystem (trading_system.py)

**메인 오케스트레이터**. 전체 시스템을 초기화하고 이벤트 콜백을 등록합니다.

| 메서드 | 설명 |
|--------|------|
| `__init__` | DI 기반 초기화, 30+ 컴포넌트 설정 |
| `_setup_callbacks` | EventBus 리스너 등록 (market_data, news, strategy_signal 등) |
| `simulate_trading_day(symbol)` | 하루 단위 거래 시뮬레이션 |
| `_on_market_data(data)` | 가격 캐싱, 손절/익절 체크, 트레일링 스탑, 시간 기반 청산, 리밸런싱 |
| `_on_strategy_signal(result)` | 신호 수신 → `_create_and_submit_order` 호출 |
| `_create_and_submit_order(...)` | 전 주문 파이프라인: 레짐 감지 → 가격 신선도 → max 포지션 → ATR SL/TP → Kelly → 위기 평가 |
| `run_prediction_pipeline()` | XGBoost 예측 파이프라인 실행 (Telegram /predict) |
| `start_dashboard()` | WebDashboard 실행 |

### 5.2 HybridStrategyEngine (src/core/strategy_engine.py)

**9개 신호 가중 투표 엔진**.

| 단계 | 상세 |
|------|------|
| 1. 레짐 감지 | EMA50/200 + ADX + ROC → 4개 레짐 분류 |
| 2. 기술 지표 계산 | RSI, MACD, EMA, BB, ADX |
| 3. 9개 신호 스코어링 | 각 신호별 0~1 점수 산출 |
| 4. 가중 투표 | `score = Σ(weight_i × signal_i)` |
| 5. 레짐 임계값 적용 | 레짐별 buy_threshold/sell_threshold로 판별 |

#### 5.2.1 거래량 확장 모멘텀 및 유동성 패널티

기술 지표 종합 점수(`combined`) 계산 시, 시장의 거래량 급증(Volume Expansion)과 유동성(Liquidity)을 반영한 동적 조정이 이루어집니다:

1. **거래량 확장 보너스/패널티 (Volume Expansion Bonus/Penalty)**:
   - 최소 20일 이상의 거래량 데이터가 존재할 때 활성화됩니다.
   - **조건**: 5일 거래량 SMA가 20일 거래량 SMA의 1.5배를 초과하는 경우 (`volume_5sma > 1.5 * volume_20sma`)
   - **조정**:
     - 가격 추세가 긍정적일 경우: 기술 지표 종합 점수에 **+0.05** 보너스를 부여 (`combined += 0.05`)
       - *가격 추세 긍정 조건*: `(EMA20 > EMA50 if len(closes) >= 50 else False) or (MACD Histogram > 0)`
     - 가격 추세가 부정적일 경우: 기술 지표 종합 점수에 **-0.05** 패널티를 부여 (`combined -= 0.05`)
       - *가격 추세 부정 조건*: `(EMA20 < EMA50 if len(closes) >= 50 else False) or (MACD Histogram < 0)`
   - 조정 후 종합 점수는 `[0.0, 1.0]` 범위로 클램핑(Capping)됩니다.

2. **낮은 유동 주식 가치 패널티 (Low Floating Value Liquidity Penalty)**:
   - 유동 주식수(`floating_shares`) 정보가 제공되는 경우 활성화됩니다.
   - **유동 가치 계산**: $\text{floating\_value} = \text{Close} \times \text{floating\_shares}$
   - **시장별 임계값(Threshold)**:
     - 현재 주가(Close) > 1000.0 (원화 기반 한국 주식 기준): **10,000,000,000.0** (100억 원)
     - 현재 주가(Close) <= 1000.0 (달러 기반 미국 주식 기준): **10,000,000.0** (1,000만 달러)
   - **조정**: 계산된 유동 주식 가치가 해당 임계값보다 낮은 경우, 유동성 리스크 회피를 위해 종합 점수를 최대 **0.4**로 강제 제한(Cap)합니다: `combined = min(combined, 0.4)`


### 5.3 RiskManager (src/risk/risk_manager.py)

**리스크 평가 및 포지션 사이징**을 담당합니다.

| 기능 | 상세 |
|------|------|
| ATR 기반 손절/익절 | `stop = entry - ATR × multiplier`, `target = entry + ATR × multiplier` |
| Kelly Criterion | `f* = W - (1-W)/R` (Half-Kelly 기본) |
| VIX Risk-Off | VIX > 30 → cap 15%, > 25 → 30%, > 20 → 50% |
| 위기 감지 | 5개 요소 융합 점수 (VIX 25% + DD 25% + Volume 15% + Trend 10% + Macro 25%) |
| 낙폭 노출 제한 | DD < 5% → 100%, < 10% → 75%, < 15% → 50%, < 20% → 25% |

### 5.4 OrderManagementSystem (src/core/order_management.py)

**주문 생명주기 관리**.

```
CREATE → PENDING → SUBMITTED → PARTIALLY_FILLED → FILLED
                                        → CANCELLED
                                        → REJECTED
                    → EXPIRED
```

### 5.5 BacktestEngine (src/analysis/backtest.py)

**백테스트 엔진** (1611 lines). OHLCV 데이터 기반 전략 검증.

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `initial_capital` | 1,000,000 | 초기 자본 |
| `slippage_pct` | 0.001 (0.1%) | 슬리피지 |
| `market_impact_pct` | 0.0005 (0.05%) | 시장 충격 |
| `fee_pct` | 0.001 (0.1%) | 수수료 |

**지원 전략 함수**: MA, RSI, MACD, Trend Following, Bollinger, Momentum Breakout, Ensemble(MA+RSI+MACD), ML+RSI, Buffett Proxy, Lynch Proxy, Dalio Proxy

**최적화 방법**:
| 방법 | 설명 |
|------|------|
| Grid Search | 전체 파라미터 조합 탐색 |
| Walk-Forward | Train/Test 윈도우 분할 최적화 |
| Monte Carlo Robustness | 1000회 PnL 셔플 검증 |
| Recency-Weighted Score | `Sharpe_norm×0.40 + (1-MDD_norm)×0.30 + WinRate×0.15 + PF_norm×0.15` |

### 5.6 Autonomous Trading Agent (src/ai/trading_agent.py)

**자동 트레이딩 에이전트**. 오케스트레이터 데몬 및 파이프라인에서 신호를 처리하여 실제 매매 주문을 수행하고 계좌 자산을 보호합니다. 5대 핵심 운영 규칙 및 4가지 퀀트 고도화 알고리즘이 탑재되어 있습니다.

* **5대 핵심 규칙**:
  1. **Rule 1 (위험 관리)**: 단일 거래당 자본의 최대 2%로 리스크 제한 (Kelly 비중 기반 수량 조절).
  2. **Rule 2 (데이터 처리)**: 최근 1시간 뉴스 감성이 부정적(< -0.2)이거나 시장 공포 지표(VIX > 30.0) 발생 시 신규 매수 전면 차단.
  3. **Rule 3 (통계적 우위)**: 최근 90일 거래 횟수 5회 이상 시 승률 55% 이상 및 기댓값(Edge) > 0 일 때만 시그널 허용. 데이터 부족 시 디폴트 priors 사용.
  4. **Rule 4 (보고 의무)**: 매수/매도 실행 전, 거래 방향/수량/진입가/손절가/익절가 및 판단의 상세 근거가 기재된 요약 보고서를 Telegram으로 알림.
  5. **Rule 5 (비상 대응)**: 지수(KOSPI, S&P500 등)가 당일 변동성 5% 이상으로 급변 시, 모든 미체결 주문을 취소하고 보유 중인 모든 포지션을 즉시 시장가 청산하여 100% 현금 보유.
* **4대 퀀트 고도화**:
  1. **Q1 (동적 ATR 트레일링 스탑)**: 고정 -5% 손절선을 대체하여, 진입 이후 최고가 대비 `ATR(14) × 2.5` 수준으로 손절선을 유연하게 상향 조정. 고정 익절선(15%)은 병행 유지.
  2. **Q2 (상관관계 기반 분산)**: 신규 매수 시 기존 보유 종목들과 최근 60영업일 일간 수익률의 Pearson 상관계수를 계산. 0.85 이상 시 진입 차단(`BLOCK`), 0.70 이상 시 비중 절반 축소(`HALVE`).
  3. **Q3 (동적 위기 리스크 캡)**: VIX 기반 복합 위기 레벨에 따라 단일 거래 리스크 한도를 축소 (`NONE`: 2%, `WATCH`: 1.5%, `ACTIVE`: 1%, `SEVERE`: 신규 매수 전면 차단).
  4. **Q4 (실제 매매비용/슬리피지 내재화)**: PnL 계산 시 매수 수수료(0.015%) 및 슬리피지(0.2%), 매도 거래세/수수료(0.255%) 및 슬리피지(0.2%)를 포함한 Net PnL 산출 (매수가 × 1.00215, 매도가 × 0.99545 적용).

### 5.7 Trade Journal (src/data_layer/trade_journal.py)

**거래 기록 및 통계 저장소 (SQLite)**. `trade_logs.db` 데이터베이스에 모든 주문 및 실현 손익 기록을 저장하고, 평단가(Average Price), 활성 포지션(Active Positions), 당일 실현 손익(Daily PnL), 승률(Win Rate), 평균 손익비(Win-Loss Ratio) 등 성능 지표를 분석합니다.

### 5.8 News Sentiment Fetcher (src/ai/news_sentiment_fetcher.py)

**뉴스 감성 분석 수집기**. Google News RSS 피드를 `urllib` 및 `ElementTree`로 파싱하고 `SentimentAnalyzer`를 통해 감성 점수(-1 ~ +1)를 산출합니다. 1시간의 인메모리 캐싱 기법을 내장하여 불필요한 네트워크 API 호출 및 지연을 방어합니다.

---

## 6. 전략 엔진 상세

### 6.1 9개 신호 가중 투표

| 신호 | 기본 가중치 | 설명 |
|------|------------|------|
| Sentiment | 0.20 | 뉴스 감성 -1~1 → 0~1 매핑 |
| Technical | 0.30 | RSI(25%) + MACD(30%) + EMA(25%) + BB(15%) + Trend(5%) |
| ML | 0.30 | RandomForest + XGBoost 앙상블 예측 확률 |
| RL | 0.10 | Adaptive heuristic (VIX/RSI/MACD/추세) |
| Darkpool | 0.00 | 다크풀 누적 = 매수 신호 |
| LLM | 0.10 | OpenAI/Gemini/DeepSeek 투자 분석 |
| Global Market | 0.00 | 상승 지수 비율 |
| Cash Ratio | 0.08 | 실제 현금 vs VIX 기반 목표 현금 |
| Macro | 0.08 | VIX(30%) + USDKRW(20%) + Oil(20%) + TNX(15%) + DXY(15%) |

### 6.2 기술 신호 세부 점수

**RSI 점수** (25%):
- RSI < 25 → 1.0 (강한 매수)
- RSI < 35 → 0.7
- RSI > 65 → 0.0 (매도)
- RSI > 75 → 0.0

**MACD 점수** (30%):
- MACD > 0 AND 히스토그램 상승 → 1.0
- MACD 골든크로스 → 0.8
- MACD 데드크로스 → 0.2
- MACD < 0 AND 하락 → 0.0

**EMA 점수** (25%):
- EMA20 > EMA50 (골든크로스) → 0.8
- EMA20 < EMA50 (데드크로스) → 0.2

**Bollinger Band 점수** (15%):
- 하한선 근접 → 0.7
- 상한선 근접 → 0.3

**추세 바이어스** (5%):
- 추세 상승 → +0.3
- 추세 하락 → -0.3

### 6.3 레짐별 임계값

| 레짐 | Buy Threshold | Sell Threshold | Min Buy Votes | Position % | Cash Target |
|------|:------------:|:--------------:|:-------------:|:----------:|:-----------:|
| Strong Bull | 0.48 | 0.38 | 1 | 100% | 10% |
| Weak Bull | 0.52 | 0.42 | 1 | 80% | 20% |
| Weak Bear | 0.62 | 0.45 | 2 | 50% | 40% |
| Strong Bear | 0.70 | 0.50 | 3 | 25% | 70% |

### 6.4 유명 투자자 전략 (famous_investors.py)

#### Buffett (가치 투자)

| 조건 | 점수 |
|------|:----:|
| PER < 15 | +1.0 |
| PER 15~20 | +0.5 |
| PBR < 1.0 | +1.0 |
| PBR 1.0~2.0 | +0.5 |
| ROE > 15% | +1.0 |
| ROE 10~15% | +0.5 |
| 부채비율 < 30% | +1.0 |
| 부채비율 30~50% | +0.5 |
| 배당수익률 > 2% | +1.0 |

`Confidence > 0.7 → BUY, > 0.4 → HOLD, else → SELL`

#### Lynch (성장 투자)

| 조건 | 점수 |
|------|:----:|
| EPS 성장률 > 25% | +1.5 |
| EPS 성장률 15~25% | +1.0 |
| 매출 성장률 > 20% | +1.0 |
| 매출 성장률 10~20% | +0.5 |
| PEG < 1.0 | +1.0 |
| PEG 1.0~2.0 | +0.5 |
| 업종 평균 초과 성장 | +1.0 |

#### Minerva (모멘텀)

| 조건 | 점수 |
|------|:----:|
| 52주 수익률 > 50% | +1.5 |
| 52주 수익률 > 20% | +1.0 |
| 6개월 수익률 > 20% | +1.0 |
| RSI 50~70 | +1.0 |
| 모멘텀 점수 > 70 | +1.0 |
| 거래량 증가 > 20% | +0.5 |

#### Dividend (배당 투자)

| 조건 | 점수 |
|------|:----:|
| 배당수익률 > 4% | +1.5 |
| 배당수익률 2.5~4% | +1.0 |
| 배당 성장률 > 10% | +1.0 |
| 연속 배당 20년+ | +1.5 |
| 연속 배당 10년+ | +1.0 |
| 배당성향 < 60% | +1.0 |
| FCF 양수 | +0.5 |

### 6.5 컨센서스 시스템

4개 전략 + AI (LLM) 의견 통합:
- AI 가중치: 1.5x (투자자 전략보다 50% 가중)
- `buy_count >= 60%` → 강한 매수
- `buy_count >= 40%` → 매수
- `buy_count >= 30%` → 보유

---

## 7. 기술적 지표 목록

### 7.1 핵심 지표 (src/utils/indicators.py)

| 지표 | 파라미터 | 용도 |
|------|----------|------|
| SMA | 10, 20, 50, 60 | 이동평균 |
| EMA | 12, 20, 26, 50, 200 | 지수이동평균 |
| MACD | Fast=12, Slow=26, Signal=9 | 추세 추종 |
| ATR | 14 | 변동성/손절 거리 |
| RSI | 14 (Wilder) | 과매수/과매도 |

### 7.2 ML 엔진 피처 (24개)

| 카테고리 | 피처 | 계산식 |
|----------|------|--------|
| 수익률 | ret_1, ret_5, ret_20 | `close.pct_change(n)` |
| 이동평균 거리 | sma_10_dist, sma_50_dist | `(close - SMA) / SMA` |
| RSI | rsi_14, rsi_5 | Wilder RSI |
| 변동성 | volatility_10 | `ret_1.rolling(10).std()` |
| MACD | macd, macd_signal, macd_hist_norm | `EMA12 - EMA26`, 정규화 |
| Bollinger | bb_upper_dist, bb_lower_dist, bb_width | ±2σ, 폭/중심 |
| ATR | atr_14 | ATR(14) / close |
| 거래량 | volume_change, log_volume_ratio | 변화율, 로그비율 |
| 갭 | gap_pct | `(open - prev_close) / prev_close` |
| 일중범위 | intraday_range | `(high - low) / close` |
| 모멘텀 | roc_10, roc_20 | 변화율 |
| 돌파 | higher_high, higher_low | 고점/저점 갱신 |
| 52주 | distance_from_52w_high | `(max_252 - close) / close` |
| HMM | hmm_regime | GaussianHMM(3 states) |

### 7.3 On-Device XGBoost 피처 (9개)

| 피처 | 설명 |
|------|------|
| ret_1d | 1일 수익률 |
| ret_5d | 5일 수익률 |
| ret_20d | 20일 수익률 |
| ret_60d | 60일 수익률 |
| dist_sma_20 | `close / SMA20 - 1` |
| vol_20d | 20일 변동성 (20일 일일 수익률의 표준편차) |
| norm_market_cap | 지역 시장별 정규화된 시가총액 |
| norm_floating_value | 지역 시장별 정규화된 유동 시가총액 |
| norm_volume | 지역 시장별 정규화된 거래량 |


---

## 8. 리스크 관리

### 8.1 위기 감지 시스템 (CrisisDetector)

5가지 요소를 융합한 **복합 위기 점수** (0.0 ~ 1.0):

| 요소 | 가중치 | 세부 기준 |
|------|:------:|-----------|
| VIX | 25% | `(vix - 15) / 40 + surge_bonus`, VIX 상승률 추가 |
| 낙폭 (DD) | 25% | `DD / 0.20 + speed_bonus`, 하락 속도 추가 |
| 거래량 급증 | 15% | `(vol_ratio - 1) / 2`, threshold 3x |
| 추세 붕괴 | 10% | EMA20 < EMA50 비율 |
| 거시경제 | 25% | USDKRW + Oil + TNX + DXY |

**위기 등급**:
| 점수 | 등급 | 현금 목표 | 포지션 승수 | 스탑 승수 | 신규 매수 | 청산 |
|:----:|:----:|:---------:|:----------:|:---------:|:---------:|:----:|
| < 0.25 | NONE | 10% | 1.0x | 1.0x | 허용 | No |
| >= 0.25 | WATCH | 30% | 0.7x | 0.8x | 허용 | No |
| >= 0.50 | ACTIVE | 60% | 0.4x | 0.6x | 허용 | No |
| >= 0.75 | SEVERE | 85% | 0.15x | 0.4x | 차단 | 3일 후 |

### 8.2 손절/익절 시스템

**ATR 기반 동적 손절/익절**:
```
stop_distance  = ATR × stop_multiplier(regime)
target_distance = ATR × target_multiplier(regime)
```

**레짐별 ATR 승수**:
| 레짐 | Stop | Target | Trail |
|------|:----:|:------:|:-----:|
| Strong Bull | 3.0 | 5.0 | 8% |
| Weak Bull | 2.5 | 4.0 | 6% |
| Weak Bear | 1.5 | 2.5 | 4% |
| Strong Bear | 1.0 | 2.0 | 3% |

**ADX 조정**:
- ADX > 30 → stop/target × 1.2 (강한 추세 = 넓은 범위)
- ADX < 20 → stop/target × 0.8 (약한 추세 = 좁은 범위)

**3단계 익절 (Take Profit Tiers)**:
| 단계 | ATR 배수 | 매도 비율 |
|:----:|:--------:|:---------:|
| 1 | 3.0× ATR | 33% |
| 2 | 5.0× ATR | 33% |
| 3 | 8.0× ATR | 34% |

### 8.3 추세 추종 오버라이드

2026-06-12 변경사항: 기술 신호에 추세 추종 로직 추가
- EMA20 > EMA50 AND price > SMA200 → buy_score 강화
- EMA20 < EMA50 AND RSI < 50 → sell_score 강화

---

## 9. 포지션 사이징

### 9.1 Kelly Criterion

```
kelly = win_rate - (1 - win_rate) / win_loss_ratio
half_kelly = kelly / 2
clamp(half_kelly, 0.01, max_position_size_pct)
```

### 9.2 Robust Kelly (고급)

```python
confidence = min(1.0, n_trades / 50)
adjusted = raw_kelly × confidence × 0.25  # Quarter Kelly
if consecutive_losses >= 3: adjusted *= 0.5
if consecutive_losses >= 5: adjusted *= 0.5
if consecutive_losses >= 7: adjusted *= 0.25
if consecutive_losses >= 10: adjusted = 0.0
```

### 9.3 전체 사이징 파이프라인

```
1. Kelly Criterion → base_qty
2. VIX Risk-Off Cap → min(base, portfolio × vix_cap)
3. 위기 포지션 승수 → base × crisis_mult
4. 변동성 스케일링 → base × vol_scaler [0.25, 2.0]
5. Conservative Ramp (첫 10트레이트) → base × (0.3 + n×0.07)
6. 신뢰도 조정 → base × (0.5 + confidence × 0.5)
7. 낙폭 노출 제한 → base × dd_limit
8. Max Position Size 캡 → min(base, portfolio × 0.25)
```

### 9.4 VIX Position Cap

| VIX | Position Cap |
|:---:|:------------:|
| > 30 | 15% |
| > 25 | 30% |
| > 20 | 50% |
| ≤ 20 | 100% |

---

## 10. 머신러닝/딥러닝

### 10.1 On-Device XGBoost (prediction_model.py)

**위치**: `src/ai/prediction_model.py`
**목적**: 클라우드 API 의존 없이 로컬에서 주가 방향 예측

**모델 설정**:
```python
XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, n_jobs=-1)
```

**8개 예측 Horizon**:
- 1일, 5일, 10일, 20일, 30일, 60일, 120일, 200일

**Feature (12개)**: 
- `ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`, `dist_sma_20`, `vol_20d`
- `norm_market_cap`, `norm_floating_value`, `norm_volume` (지역 시장별로 정규화된 피처)
- `operating_margin`, `revenue_to_market_cap`, `dividend_yield` (펀더멘탈 기반 피처)

**Target**: `close.shift(-h) / close - 1` (forward return)

**지역 시장 정규화 및 통화 분리 로직 (Regional Market Normalization & Currency Separation)**:
- 국가/통화 간 합산 오류(예: USD + KRW)를 방지하기 위해 미국(US)과 한국(KR) 시장을 분리하여 정규화합니다.
- KR 시장 분류 조건: 종목 코드가 숫자이거나 `.KS` / `.KQ` 접미사 포함 시 한국 시장으로 분류하며, 그 외에는 미국 시장으로 분류합니다.
- 계산 공식:
  - $\text{market\_cap} = \text{Close} \times \text{shares\_outstanding}$
  - $\text{floating\_value} = \text{Close} \times \text{floating\_shares}$ (유동 주식수 누락/무효 시 $\text{Close} \times \text{Volume}$으로 대체)
  - 지역 시장별 총합: $\text{total\_market\_cap} = \sum \text{market\_cap}$, $\text{total\_floating\_value} = \sum \text{floating\_value}$, $\text{total\_volume} = \sum \text{Volume}$
  - 피처 정규화 공식:
    - $\text{norm\_market\_cap} = \frac{\text{market\_cap}}{\text{total\_market\_cap}}$
    - $\text{norm\_floating\_value} = \frac{\text{floating\_value}}{\text{total\_floating\_value}}$
    - $\text{norm\_volume} = \frac{\text{Volume}}{\text{total\_volume}}$

**파이프라인** (`run_pipeline.py`):
1. FinanceDataReader로 S&P 500 + KRX 유니버스 로드
2. 샘플링 (설정 가능, 기본 50+50)
3. 2023-01-01부터 학습 데이터 fetch
4. XGBoost 8개 모델 학습
5. 전체 종목 (약 2800개) inference 데이터 fetch
6. 예측 실행 → DB 저장 → Telegram 포맷 반환


### 10.2 ML Ensemble (ml_engine.py)

**위치**: `src/analysis/ml_engine.py`

**모델**: `RandomForestClassifier` + `XGBClassifier` (Soft Voting 50:50)

**Target**: `1 if forward_ret > 0.005, 0 if forward_ret < -0.005, else NaN`

**Feature (24개)**: section 7.2 참조

**Hyperparameter Optimization**: Optuna with TimeSeriesSplit(3)

### 10.3 Adaptive RL (rl_engine.py)

**위치**: `src/analysis/rl_engine.py`

**Policy**:
```
if vix > vix_buy AND rsi < rsi_buy:      → BUY (prob 0.8)
elif vix < vix_sell AND rsi > rsi_sell:  → SELL (prob 0.8)
elif trend > trend_buy AND macd > 0:      → BUY (prob 0.7)
else:                                      → HOLD (prob 0.6)
```

**Threshold Adaptation**: 매 20회 액션마다 성과에 따라 VIX/RSI 임계값 ±5% 조정

### 10.4 PPO (stable-baselines3)

**위치**: `src/ai/rl_trading.py`

**알고리즘**: CustomPPO (PPO 확장) with MlpPolicy
**환경**: TradingEnv (Gymnasium) — [price, balance, holdings] → 3 actions
**학습**: 10 epochs, n_steps=64, batch_size=64

### 10.5 DQN (PyTorch)

**위치**: `src/ai/rl_trader.py`

**네트워크**: QNetwork [3 → 64 → 64 → 3]
**하이퍼파라미터**: lr=1e-3, gamma=0.99, epsilon 1.0→0.05 (decay 500)
**손실함수**: SmoothL1Loss (Huber)
**Target Network**: 50 steps마다 업데이트

### 10.6 LLM 통합 (llm_integration.py)

**위치**: `src/ai/llm_integration.py`

**Provider** (환경변수 `LLM_PROVIDER`로 선택):
| Provider | 기본 모델 | API |
|----------|-----------|-----|
| openai | gpt-4o-mini | `openai.OpenAI` |
| gemini | gemini-1.5-flash | `google.generativeai` |
| deepseek | deepseek-chat | OpenAI 호환 |

**파라미터**: temperature=0.7, max_tokens=1024, retry=3 (exponential backoff)

**Simulation Fallback**: API 미연결 시 PER/EPS 성장률 기반 휴리스틱

### 10.7 감성 분석

**SentimentAnalyzer** (src/ai/sentiment.py):
- 100+ 긍정어, 120+ 부정어, 28 강조어, 30 부정어
- Bigram + unigram 매칭, negation window=4, intensifier window=2
- 점수 정규화: tanh 유사, compound score [-1.0, 1.0]

**NLPEngine** (src/data_layer/nlp_engine.py):
- 15개 긍정 키워드 + 14개 부정 키워드 기반 단순 매칭
- 주로 한글 뉴스 감성 분석용

---

## 11. 포트폴리오 최적화

### 11.1 Risk Parity (ERC — Equal Risk Contribution)

**최적화 목적**:
```
minimize Σ(RC_i - target_risk / n)²
s.t. Σ w_i = 1, w_i ≥ 0
```

**알고리즘 캐스케이드**:
1. Log-barrier (L-BFGS-B): minimize `0.5 × x'Σx - Σlog(x)`
2. Direct RC variance (SLSQP)
3. Inverse volatility (`1/σᵢ`)
4. Equal weight (1/n)

### 11.2 Mean-Variance (QuantumPortfolioOptimizer)

**해석해** (inverse covariance):
```
w = Σ⁻¹ × μ / (1' × Σ⁻¹ × μ)
```

Regularization: condition number > 1e12 시 적용

### 11.3 Adaptive Parameter Optimizer

**위치**: `src/analysis/adaptive_optimizer.py`

**TPE Sampler** (Tree-structured Parzen Estimator):
- Latin Hypercube Sampling (첫 10 trials)
- 이후 TPE: top 25% good / bottom 75% bad 분리, `p_good / p_bad` 비율 최대화

**Objective (Recency-Weighted)**:
```
score = Sharpe_norm × 0.40
      + (1 - MDD_norm) × 0.30
      + WinRate × 0.15
      + ProfitFactor_norm × 0.15
```

**최적화 파라미터 공간**:
| 파라미터 | 탐색 범위 |
|----------|-----------|
| Regime Thresholds | 4개 레짐 × buy/sell 각 3~4개 값 |
| Signal Weights | 6개 신호 × 3~4개 값 |
| ATR Multipliers | 4개 레짐 × stop/target 각 3개 값 |
| trail_pct | [0.03, 0.04, 0.05, 0.06, 0.08, 0.10] |
| max_holding_days | [15, 20, 25, 30, 40] |
| max_position_size_pct | [0.15, 0.20, 0.25, 0.30, 0.35] |
| take_profit_tiers | 3개 variation |

**OptimizationScheduler**:
- 체크 간격: 7일
- 트리거: regime_change, sharpe_decline > 20%, drawdown > 10%, VIX spike > 1.5x

---

## 12. 시장 레짐 및 스타일 로테이션

### 12.1 레짐 감지 (HybridStrategyEngine)

EMA50/200 크로스 + ADX + ROC로 4개 레짐 분류:

```
if EMA50 > EMA200 AND ADX > 25 AND ROC20 > 0.03 → strong_bull
elif EMA50 > EMA200 → weak_bull
elif EMA50 < EMA200 AND ADX > 25 AND ROC20 < -0.03 → strong_bear
else → weak_bear
```

### 12.2 스타일 로테이션 (StyleRotator)

**레짐 감지 조건**:
| 조건 | 레짐 |
|------|------|
| VIX > 25 | DEFENSIVE |
| TNX change > +2% | INFLATION_RISING |
| TNX change < -2% | RATE_CUTTING |
| else | EXPANSION |

**스타일 선호도**:
| 레짐 | GROWTH | VALUE | LARGE_CAP | SMALL_CAP |
|------|:------:|:-----:|:---------:|:---------:|
| DEFENSIVE | 0.5 | 1.5 | 1.5 | 0.5 |
| INFLATION_RISING | 0.7 | 1.3 | 1.2 | 0.8 |
| RATE_CUTTING | 1.4 | 0.8 | 0.9 | 1.3 |
| EXPANSION | 1.2 | 0.9 | 1.1 | 1.0 |

### 12.3 HMM 레짐 (GaussianHMM)

**MLEngine** 내장: 3개 은닉 상태 (Regime 0: 안정상승, Regime 1: 횡보, Regime 2: 패닉)

**Observation**: [daily_return, volatility_10] 2차원

**용도**: Feature `hmm_regime`으로 ML 모델 입력

---

## 13. 브로커 연동

### 13.1 지원 브로커

| 브로커 | 클래스 | 파일 |
|--------|--------|------|
| 키움증권 | KiwoomConnector | `broker/kiwoom.py` |
| 한국투자증권 | KoreaInvestmentConnector | `broker/korea_investment.py` |
| 대신증권 | DaishinConnector | `broker/daishin.py` |
| NH농협증권 | NHConnector | `broker/nh.py` |
| 한화증권 | HanwhaConnector | `broker/hanwha.py` |
| LS증권 | LSConnector | `broker/ls.py` |
| 미래에셋증권 | MiraeAssetConnector | `broker/miraeasset.py` |
| 모의매매 | SimulatedBroker | `broker/simulated_broker.py` |

### 13.2 MultiBrokerManager

**모든 브로커를 통합 관리**하는 오케스트레이터 (`MultiBrokerManager`):
- `connect(broker_type, account)`
- `disconnect(broker_type)`
- `place_order(code, qty, price, type, broker)`
- `get_stock_quote(code)`
- `get_all_account_info()`

### 13.3 Kiwoom 아키텍처

키움증권 OpenAPI는 32비트 ActiveX 기반이므로, **ZeroMQ IPC 브릿지** 구조 사용:
- `kiwoom_server.py`: 32비트 프로세스, 키움 서버와 직접 통신
- `kiwoom.py`: 64비트 메인 프로세스, ZMQ 소켓으로 서버와 통신

---

## 14. 텔레그램 봇 명령어

### 14.1 명령어 목록

| 명령어 | 파라미터 | 설명 |
|--------|----------|------|
| `/start` | - | 환영 메시지 |
| `/status` | - | 거래 현황 (현금, 포지션, 주문) |
| `/portfolio` | - | 포트폴리오 개요 |
| `/positions` | - | 포지션 상세 |
| `/orders` | - | 미체결 주문 현황 |
| `/performance` | - | 성과 통계 (수익률, 승률, 낙폭) |
| `/risk` | - | 위험 보고서 |
| `/strategy [NAME]` | 전략명 (선택) | 전략 조회/변경 |
| `/analyze SYMBOL` | 티커 (필수) | AI 주식 분석 |
| `/news` | - | 시장 뉴스 개요 |
| `/global` | - | 글로벌 지수 + 환율 |
| `/screen [SYM] [CORR]` | 티커, 상관계수 (선택) | 상대강도 스크리닝 |
| `/predict` | - | XGBoost 예측 파이프라인 실행 |
| `/dashboard` | - | 대시보드 URL 표시 |
| `/buy SYM QTY [PRICE]` | 종목, 수량, 가격 (선택) | 매수 주문 |
| `/sell SYM QTY [PRICE]` | 종목, 수량, 가격 (선택) | 매도 주문 |
| `/cancel ORDER_ID` | 주문 ID (필수) | 주문 취소 |
| `/brokers` | - | 증권사 연결 상태 |
| `/connect BROKER ACCT` | 증권사명, 계좌 | 증권사 연결 |
| `/help` | - | 도움말 |

### 14.2 자동 알림

| 이벤트 | 조건 |
|--------|------|
| daily_loss_3pct | 일일 손실 3% 도달 |
| drawdown_10pct | 낙폭 10% 돌파 |
| crisis_detected | VIX > 30 |
| consecutive_loss_5 | 5연패 |
| consecutive_loss_10 | 10연패 → 거래 중단 |
| regime_change | 시장 레짐 변경 |
| take_profit_hit | 익절 실행 |
| stop_loss_hit | 손절 실행 |

### 14.3 보안

- **Rate Limit**: 10회/10초 (사용자별)
- **인증된 사용자**: `TELEGRAM_AUTHORIZED_USER_IDS` 환경변수로 제한
- **제한 명령어**: buy, sell, cancel, portfolio, positions, orders, connect, risk, strategy

---

## 15. 데이터베이스 스키마

### 15.1 trade_logs.db

**orders**:
| 컬럼 | 타입 | 설명 |
|------|------|------|
| order_id | TEXT PK | 주문 ID |
| symbol | TEXT | 종목 |
| order_type | TEXT | BUY/SELL |
| quantity | INTEGER | 수량 |
| price | REAL | 가격 |
| status | TEXT | PENDING/FILLED/CANCELLED |
| filled_quantity | INTEGER | 체결 수량 |
| created_at | TIMESTAMP | 생성 시간 |
| executed_at | TIMESTAMP | 체결 시간 |

**executions**:
| 컬럼 | 타입 |
|------|------|
| id | INTEGER PK AUTOINCREMENT |
| order_id | TEXT FK |
| symbol | TEXT |
| quantity | INTEGER |
| price | REAL |
| executed_at | TIMESTAMP |

### 15.2 asset_history.db

**asset_snapshots**: 포트폴리오 스냅샷 이력

### 15.3 market_indicators.db

**global_indicators**:
| 컬럼 | 타입 |
|------|------|
| date | TEXT PK |
| symbol | TEXT PK |
| name | TEXT |
| price | REAL |
| change_pct | REAL |

**stock_universe**:
| 컬럼 | 타입 |
|------|------|
| symbol | TEXT PK |
| name | TEXT |
| market | TEXT (SP500/KRX) |

**stock_fundamentals**:
| 컬럼 | 타입 | 설명 |
|------|------|------|
| symbol | TEXT | 종목 (Primary Key) |
| date | TEXT | 보고 일자 (Primary Key) |
| revenue | REAL | 매출액 |
| operating_income | REAL | 영업이익 |
| dividend_per_share | REAL | 주당 배당금 |

**ai_predictions**:
| 컬럼 | 타입 |
|------|------|
| date | TEXT PK |
| symbol | TEXT PK |
| horizon | INT PK |
| expected_return | REAL |

### 15.4 ai_predictions.db

동일 스키마의 `ai_predictions` 테이블

### 15.5 trade_logs.db

**trade_journal**:
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 일련번호 |
| timestamp | TEXT | 거래 일시 (YYYY-MM-DD HH:MM:SS) |
| symbol | TEXT | 종목 코드 |
| side | TEXT | 거래 방향 (BUY, SELL, CANCEL) |
| quantity | INTEGER | 거래 수량 |
| price | REAL | 거래 체결 단가 |
| reason | TEXT | 진입/청산 사유 (예: TP, SL, Sentiment 등) |
| ensemble_score | REAL | 진입 시점의 앙상블 예상 수익률 |
| sentiment_score | REAL | 진입 시점의 뉴스 감성 점수 |
| regime | TEXT | 진입 시점의 시장 레짐 |
| stop_loss | REAL | 설정된 손절 단가 |
| take_profit | REAL | 설정된 익절 단가 |
| pnl | REAL | 매도 시 실현된 손익 (거래 수수료/세금/슬리피지 차감된 Net PnL) |
| status | TEXT | 주문 상태 (기본 'EXECUTED') |

---

## 16. 테스트

### 16.1 테스트 파일

| 파일 | 테스트 대상 |
|------|------------|
| `tests/test_system.py` | 통합 시스템 |
| `tests/test_telegram_bot.py` | 텔레그램 봇 |
| `tests/test_portfolio_risk.py` | 포트폴리오/리스크 |
| `tests/test_database.py` | 데이터베이스 |
| `tests/test_indicators.py` | 기술 지표 계산 |
| `tests/test_async_helper.py` | 비동기 헬퍼 |
| `tests/test_event_bus.py` | 이벤트 버스 |
| `tests/test_ml_ensemble.py` | ML 앙상블 |
| `tests/test_macro.py` | 거시경제 분석 |
| `tests/test_macro_stress.py` | 거시경제 스트레스 테스트 |
| `tests/test_risk_manager.py` | 리스크 매니저 단위 |
| `tests/test_screener_dash_challenger.py` | 스크리너 |
| `tests/test_trading_agent.py` | 오토 트레이딩 에이전트 & 4대 고도화 및 5대 규칙 |

### 16.2 실행

```bash
# 전체 테스트
python -m pytest tests/ -v

# 특정 테스트
python -m pytest tests/test_system.py -v

# 코드 품질
ruff check src/
mypy src/
```

---

## 17. 전체 파라미터 일람

### 17.1 TradingConfig (.env)

| 파라미터 | 기본값 | 환경변수 |
|----------|--------|----------|
| initial_cash | 1,000,000 | - |
| mock_trading | true | MOCK_TRADING_ENABLED |
| broker_type | "KIS" | BROKER_TYPE |
| db_path | "market_indicators.db" | DB_PATH |
| train_sample_size | 50 | TRAIN_SAMPLE_SIZE |
| openai_api_key | "" | OPENAI_API_KEY |
| openai_model | "gpt-4o-mini" | OPENAI_MODEL |
| llm_provider | "openai" | LLM_PROVIDER |
| telegram_bot_token | "" | TELEGRAM_BOT_TOKEN |

### 17.2 StockTradingSystem

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| min_trade_value_pct | 0.001 (0.1%) | 최소 거래 비율 |
| distributed_threshold_pct | 0.005 (0.5%) | 분산 주문 임계값 |
| trail_pct | 0.04 (4%) | 트레일링 스탑 거리 |
| correlation_limit_pct | 0.40 (40%) | 상관 쌍 최대 비율 |
| target_annual_volatility | 0.15 (15%) | 목표 연간 변동성 |
| max_portfolio_drawdown_pct | 0.20 (20%) | 최대 낙폭 |
| rebalance_interval_hours | 168.0 (7일) | 리밸런싱 주기 |
| max_concurrent_positions | 12 | 최대 동시 포지션 |
| max_holding_days | 30 | 최대 보유 일수 |
| max_data_age_seconds | 300.0 (5분) | 가격 신선도 한계 |
| max_daily_loss_pct | 0.03 (3%) | 일일 손실 한도 |
| state_save_interval_seconds | 3600.0 (1시간) | 상태 저장 주기 |

### 17.3 RiskManager

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| max_loss_per_trade_pct | 0.02 (2%) | 거래당 최대 손실 |
| max_portfolio_loss_pct | 0.10 (10%) | 포트폴리오 최대 손실 |
| max_position_size_pct | 0.25 (25%) | 최대 포지션 비중 |
| default_stop_loss_pct | 0.05 (5%) | 기본 손절 |
| default_take_profit_pct | 0.15 (15%) | 기본 익절 |
| max_drawdown_allowed | 0.20 (20%) | 최대 허용 낙폭 |
| atr_multiplier_stop | 2.0 | ATR 손절 승수 |
| atr_multiplier_target | 3.0 | ATR 익절 승수 |
| volatility_scaling | True | 변동성 스케일링 |
| target_annual_volatility | 0.15 | 목표 연간 변동성 |

### 17.4 Telegram Bot

| 파라미터 | 기본값 |
|----------|--------|
| Rate window | 10초 |
| Max calls per window | 10회 |

### 17.5 XGBoost (On-Device)

| 파라미터 | 기본값 |
|----------|--------|
| n_estimators | 100 |
| max_depth | 5 |
| learning_rate | 0.1 |
| Horizons | [1, 5, 10, 20, 30, 60]일 |

### 17.6 DQN Agent

| 파라미터 | 기본값 |
|----------|--------|
| learning_rate | 1e-3 |
| gamma | 0.99 |
| epsilon_start | 1.0 |
| epsilon_end | 0.05 |
| epsilon_decay | 500 |
| batch_size | 32 |
| target_update_freq | 50 |

### 17.7 LLM

| 파라미터 | 기본값 |
|----------|--------|
| temperature | 0.7 |
| max_tokens | 1024 |
| retry_attempts | 3 |
| AI consensus weight | 1.5x |

### 17.8 Crisis Scoring

| 요소 | 가중치 |
|------|:------:|
| VIX | 25% |
| Drawdown | 25% |
| Volume Spike | 15% |
| Trend Breakdown | 10% |
| Macro (FX/Oil/Rates/DXY) | 25% |

### 17.9 Autonomous Trading Agent

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `ATR_LOOKBACK_DAYS` | 14 | ATR 계산을 위한 과거 일수 |
| `ATR_MULTIPLIER` | 2.5 | ATR 손절 및 트레일링 스탑 승수 |
| `CORRELATION_LOOKBACK_DAYS` | 60 | Pearson 상관계수용 과거 영업일 수 |
| `CORRELATION_BLOCK_THRESHOLD` | 0.85 | 상관계수 BLOCK(진입 차단) 임계값 |
| `CORRELATION_HALVE_THRESHOLD` | 0.70 | 상관계수 HALVE(비중 절반) 임계값 |
| `CRISIS_RISK_CAP (NONE)` | 0.02 (2.0%) | 정상 상태 단일 거래 리스크 한도 |
| `CRISIS_RISK_CAP (WATCH)` | 0.015 (1.5%) | 주의 상태 단일 거래 리스크 한도 |
| `CRISIS_RISK_CAP (ACTIVE)` | 0.01 (1.0%) | 위기 상태 단일 거래 리스크 한도 |
| `CRISIS_RISK_CAP (SEVERE)` | 0.00 (0.0%) | 심각 상태 신규 매수 차단 |
| `FEES_AND_TAXES (BUY)` | 0.215% | 매수 수수료(0.015%) + 슬리피지(0.2%) |
| `FEES_AND_TAXES (SELL)` | 0.455% | 매도 수수료/거래세(0.255%) + 슬리피지(0.2%) |

---

> **문서 이력**
> - 2026-08-22: v6.5 — 6차 고도화 완결 (V6-01~V6-35, F01~F10): 31대 전략 횡단면 점수 정규화(`CrossSectionalScoreNormalizer`), 결측 전략 동적 제로 가중치 재정규화, 시장별 법정 Filing Lag(KRX 45d, US 40d), 층화 샘플링(Stratified Sampling), 적응형 타임아웃 & 지터 백오프, VIX 기간구조 완충 게이팅, Almgren-Chriss 최적 집행 스케줄러, 7대 주문 안전 게이트 및 1,569+ 전수 테스트 100% 통과 반영
> - 2026-08-17: v5.0 — 31대 전략 다변화 확장 (Supply Chain, FinBERT Sentiment, Style Neutralizer, Vol Target, Microstructure, Accruals, Short Squeeze, Value-Up, Trend Eff, Gamma Squeeze, Insider Buying, Tone Drift, Darkpool HFT), HRP 및 EVT-CVaR 포트폴리오 최적화, Leland No-Trade 버퍼 밴드, 단일 `tests/` 통합(1,124+ 테스트)
> - 2026-06-27: v4.0 — 자율 주식 거래 에이전트(Autonomous Trading Agent) 도입, 5대 규칙 적용 및 4대 퀀트 고도화(ATR 트레일링 스탑, 상관관계 분산, 위기 리스크 캡, 실효 비용 내재화) 반영
> - 2026-06-21: v3.0 — 펀더멘탈 데이터 캐싱, WAL 및 Thread Lock 동시성 해결 등 Known Issues 개선 반영
> - 2026-06-12: v2.0 — 추세 추종 오버라이드, XGBoost 예측 시스템, 텔레그램 /predict /dashboard 추가 반영
> - 초기 작성: v1.0

