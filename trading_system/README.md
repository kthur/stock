# 주식 트레이딩 시스템 (Stock Trading System)

Python으로 구현된 완전한 알고리즘 트레이딩 시스템입니다.

## 시스템 개요

```
MarketData / News
      │
      ▼
 EventBus ──────────────────────────────────────────┐
      │                                              │
      ▼                                              ▼
HybridStrategyEngine                         RiskManager
  ├─ 기술 지표 (RSI/MACD/EMA/BB)    30%        │
  ├─ ML 앙상블 (RF+XGBoost 50:50)   30%        │
  ├─ 뉴스 감성 (NLP)                20%        │
  ├─ LLM 분석 (OpenAI/Gemini/DeepSeek) 10%    │
  ├─ RL Agent                        10%        │
  ├─ Cash Ratio (VIX 기반)            8%        │
  └─ Macro (VIX+환율+유가+금리+DXY)   8%        │
      │                                              │
      ▼                                              │
 레짐별 동적 임계값 적용                              │
 (strong_bull / weak_bull / weak_bear / strong_bear)  │
      │                                              │
      ▼                                              │
 포지션 사이징 9단계 파이프라인 ◄────────────────────┘
 (Kelly → Volatility → Confidence → Crisis → Macro →
  Earnings → IR → Multi-TF → Market Impact)
      │
      ▼
 OrderManagementSystem
  ├─ 단일 주문: 진입 + Stop Loss + ATR 3단계 Take Profit
  └─ 분산 주문: 0.5% 이상 시 3분할 분산 매수/매도
      │
      ▼
 KiwoomConnector / MultiBrokerManager (7개 증권사)
```

---

## 빠른 시작 (Quick Start)

### 1. 설치

```bash
cd trading_system

# 가상환경 생성 (권장)
python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # macOS/Linux

pip install -r requirements.txt
```

### 2. 환경 설정

```bash
# .env.example 을 복사하여 .env 파일 생성
copy .env.example .env      # Windows
cp .env.example .env        # macOS/Linux
```

`.env` 파일에서 사용할 LLM 제공자와 API 키를 설정하세요:

```ini
# LLM 제공자 선택: openai / gemini / deepseek
LLM_PROVIDER=deepseek

# DeepSeek (https://platform.deepseek.com/api_keys)
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
DEEPSEEK_MODEL=deepseek-chat          # 또는 deepseek-reasoner (R1)

# OpenAI (LLM_PROVIDER=openai 사용 시)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini

# Google Gemini (LLM_PROVIDER=gemini 사용 시)
GEMINI_API_KEY=AIzaSy-xxxxxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-1.5-pro

# 텔레그램 봇 (선택)
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 3. 기본 실행

```bash
# 전체 테스트 실행 (315개 - 313 pass, 2 skip, 약 4분 소요)
.venv\Scripts\python -m pytest tests/ -v

# 시스템 데모 실행
python test_system.py
```

---

## 사용법 (Usage)

### 기본 시스템 초기화

```python
import asyncio
from trading_system import StockTradingSystem

# 기본 초기화 (100만원, 시뮬레이션 모드)
system = StockTradingSystem(initial_cash=1_000_000)

# 상태 확인
status = system.get_trading_status()
print(f"현금: {status['cash']:,}원")
print(f"포지션: {status['positions']}")
print(f"총 자산: {status['portfolio_value']:,}원")
```

### 하루 거래 시뮬레이션

```python
async def main():
    system = StockTradingSystem(initial_cash=10_000_000)

    # 단일 종목 하루 시뮬레이션 (뉴스 + 시세 + 전략 + 주문 자동 실행)
    await system.simulate_trading_day(symbol="AAPL")
    await system.simulate_trading_day(symbol="005930.KS")  # 삼성전자

    # 성과 리포트
    report = system.get_risk_report()
    print(f"드로다운: {report['drawdown']:.2%}")
    print(f"위기 레벨: {report['risk_level']}")

asyncio.run(main())
```

### LLM 제공자별 초기화

```python
from src.ai import LLMEngine

# DeepSeek (V3 / R1)
llm_ds = LLMEngine(provider="deepseek")                         # .env에서 키 자동 로드
llm_r1 = LLMEngine(provider="deepseek", model="deepseek-reasoner")  # R1 모델

# OpenAI
llm_oai = LLMEngine(provider="openai", model="gpt-4o")

# Google Gemini
llm_gem = LLMEngine(provider="gemini", model="gemini-1.5-pro")

# 투자 의견 조회
opinion = llm_ds.query_investment_opinion({
    "symbol": "AAPL",
    "price": 210.5,
    "pe_ratio": 28.5,
    "pb_ratio": 45.2,
    "roe": 160.0,
    "earnings_growth": 12.0,
    "revenue_growth": 8.0,
    "dividend_yield": 0.5,
    "industry": "Technology",
    "market_cap": 3_200_000_000_000,
})
print(f"추천: {opinion.recommendation}")    # BUY / HOLD / SELL
print(f"신뢰도: {opinion.confidence:.0%}")
print(f"목표가: {opinion.target_price:,.2f}")
print(f"근거: {opinion.reasoning}")

# 여러 종목 일괄 조회
opinions = llm_ds.batch_query_stocks([
    {"symbol": "NVDA", "price": 900.0, "pe_ratio": 70.0, ...},
    {"symbol": "005930.KS", "price": 78000, "pe_ratio": 12.0, ...},
])
```

### ML 앙상블 모델 직접 사용

```python
from src.analysis.ml_engine import MLEngine

ml = MLEngine()  # RandomForest + XGBoost 50:50 앙상블

# 학습 (최소 100개 PriceBar 필요)
from src.analysis.backtest import PriceBar
price_bars = [...]  # PriceBar 리스트
trained = ml.train(price_bars)
print(f"학습 완료: {trained}")

# 예측 (0.0 ~ 1.0, 0.5 기준으로 상승/하락 판단)
prob = ml.predict_prob(price_bars)
print(f"상승 확률: {prob:.2%}")
```

### 리스크 관리

```python
from src.risk import RiskManager

risk = RiskManager()

# Kelly Criterion 기반 포지션 사이징
qty = risk.calculate_position_sizing(
    symbol="AAPL",
    entry_price=210.0,
    stop_loss_price=200.0,   # ATR 기반 자동 계산 또는 수동 지정
    win_rate=0.55,
    win_loss_ratio=1.8,
)
print(f"권장 수량: {qty}주")

# 위기 평가 (VIX + 거시지표 융합)
risk.evaluate_crisis(
    vix=28.5,
    positions=system.portfolio.positions,
    daily_volume_ratio=1.2,
    market_data_cache=system.market_data_cache,
    usdkrw=1380.0,
    oil=85.0,
    tnx=4.5,
    dxy=106.0,
)
print(f"위기 레벨: {risk.crisis_detector.crisis_level.value}")

# 위험 리포트
report = system.get_risk_report()
```

### 백테스트

```python
from src.analysis.backtest import BacktestEngine, PriceBar
from datetime import datetime

engine = BacktestEngine()

# PriceBar 데이터 준비
bars = [
    PriceBar(datetime(2024, 1, i+1), 100+i, 102+i, 99+i, 101+i, 1_000_000)
    for i in range(252)
]

# 내장 전략으로 백테스트
result = engine.run_backtest("AAPL", bars, strategy_name="RSI")
print(f"수익률: {result.total_return:.2%}")
print(f"Sharpe: {result.sharpe_ratio:.2f}")
print(f"최대 낙폭: {result.max_drawdown:.2%}")

# 전략 목록
strategies = engine.list_strategies()
# → ['MA', 'RSI', 'MACD', 'BOLLINGER', 'BUFFETT', 'DALIO', 'TREND', ...]
```

### 웹 대시보드 실행

```bash
python run_dashboard.py
# → http://localhost:8050 에서 실시간 포트폴리오 모니터링
```

### 텔레그램 봇 실행

```bash
# .env에 TELEGRAM_BOT_TOKEN 설정 후:
python telegram_bot_runner.py
```

**텔레그램 명령어:**

| 명령어 | 설명 |
|-------|------|
| `/status` | 현재 포트폴리오 현황 |
| `/portfolio` | 포지션 상세 |
| `/buy AAPL 10` | AAPL 10주 매수 |
| `/sell AAPL 5` | AAPL 5주 매도 |
| `/report` | 오늘 손익 리포트 |
| `/risk` | 위험 관리 현황 |
| `/stop` | 자동 매매 일시 정지 |

---

## 핵심 컴포넌트

### 1. 데이터 레이어 (Data Layer)
- **MarketDataHandler**: 실시간 시세 데이터 수신 및 관리, 과거 데이터 조회
- **NLPEngine**: 뉴스 텍스트 분석 및 감정 점수 계산 (-1.0 ~ 1.0)
- **AlternativeDataClient**: VIX, 공포/탐욕 지수, 시장 레짐 탐지
- **DarkPoolTracker**: 다크풀 활동 및 고래 움직임 추적

### 2. 자산 관리 (Asset Management)
- **PortfolioManager**: 실시간 포트폴리오 가치 계산, 포지션/현금 관리
- **AccountSyncAgent**: 증권사 계좌와 자동 동기화
- **QuantumPortfolioOptimizer**: 평균-분산 최적화, 리스크 패리티

### 3. 전략 엔진 (Strategy Engine)
- **HybridStrategyEngine**: 기술적 분석 + 감정 분석 + ML/RL + LLM 통합
- **OptimizationEngine**: 슬리피지/손익 기반 파라미터 자동 튜닝
- **InvestorStrategyEngine**: 워렌 버핏, 피터 린치, 찰리 멍거 등 유명 투자자 전략 구현
- **AdaptiveParameterOptimizer**: 백테스트 기반 전략 파라미터 자동 최적화

### 4. 주문 관리 (Order Management System)
- **OrderManagementSystem**: 주문 생성/제출/체결/취소, 미체결 모니터링
- **자동 손절/익절**: 진입 시 ATR 기반 Stop Loss + 3단계 Take Profit 자동 생성
- **분산 주문**: 큰 주문을 3분할로 나눠 시장 충격 최소화
- **실시간 체결 감시**: 시장 데이터 업데이트 시 손절/익절 자동 발동

### 5. 위험 관리 (Risk Management)
- **RiskManager**: 동적 포지션 사이징 (Kelly Criterion), VaR/CVaR, Drawdown 모니터링
- **CrisisDetector**: VIX + 거시경제 지표(환율/유가/금리/달러) 융합 4단계 위기 탐지
- **위기 대응**: 단계별 현금 비중 목표 (10%→85%), 신규 매수 차단, 자동 청산
- **상관관계 리스크**: 포트폴리오 내 고상관 종목 집중도 감지

### 6. AI/LLM 엔진

| 제공자 | 환경변수 | 기본 모델 | 비고 |
|--------|---------|----------|------|
| **OpenAI** | `OPENAI_API_KEY` | `gpt-4o-mini` | GPT-4o 등 지원 |
| **Google Gemini** | `GEMINI_API_KEY` | `gemini-1.5-pro` | |
| **DeepSeek** | `DEEPSEEK_API_KEY` | `deepseek-chat` | R1(`deepseek-reasoner`) 지원 |

- API 키 없이도 시뮬레이션 모드로 동작 (PER/성장률 기반 규칙)
- 3회 자동 재시도 (Exponential Backoff)
- JSON 응답 파싱 + 마크다운 코드블록 자동 제거

### 7. ML 앙상블 (Machine Learning)
- **RandomForest + XGBoost**: 50:50 소프트 보팅 앙상블
- **24개 피처**: RSI, MACD, 볼린저밴드, ATR, 거래량, 모멘텀, 52주 고점 등
- **타깃**: 다음봉 0.5% 초과 상승(1) / 하락(0) 이진 분류
- **자동 재학습**: 20번 거래마다 자동 재학습
- **HMM 시장 레짐**: hmmlearn 설치 시 3상태 Hidden Markov Model 추가

### 8. 백테스팅 & 분석
- **BacktestEngine**: 과거 데이터 기반 전략 검증, 수수료/슬리피지/시장충격 모델링
- **AdvancedStatistics**: Sharpe/Sortino/Calmar Ratio, VaR/CVaR, Hurst Exponent
- **파라미터 최적화**: 그리드 서치 + 교차검증

### 9. 웹 대시보드 & 알림
- **WebDashboard**: Dash 기반 실시간 모니터링 (`http://localhost:8050`)
- **TelegramBotEngine**: 거래 알림, 포트폴리오 조회, 명령어 기반 제어
- **RESTful API**: `/api/portfolio`, `/api/performance`, `/api/orders`, `/api/health`

### 10. 증권사 연동 (Multi-Broker)
- **7개 증권사 지원**: 키움, 대신, 한화, 한국투자, 미래에셋, NH, LS
- **MultiBrokerManager**: 통합 인터페이스, 동시 연결 및 전환 지원

---

## 디렉토리 구조

```
trading_system/
├── docs/                    # 시스템 관련 문서 보관 폴더
│   ├── ADVANCED_FEATURES.md # 고급 기능 상세
│   ├── ALGORITHMS.md        # 알고리즘 상세 정의서
│   ├── IMPLEMENTATION_GUIDE.md # 구현 가이드
│   ├── ORIGINAL_REQUEST.md  # 원본 요구사항 문서
│   ├── PHASE7_IMPLEMENTATION_PLAN.md # Phase 7 구현 계획서
│   ├── PROJECT.md           # 프로젝트 명세서
│   ├── TEST_INFRA.md        # 테스트 인프라 정의서
│   └── TEST_READY.md        # 테스트 준비 요약서
├── src/
│   ├── data_layer/          # 시장 데이터 & NLP
│   ├── core/                # 자산관리, 전략, 주문관리
│   ├── persistence/         # SQLite 데이터 저장소
│   ├── risk/                # 위험 관리 (CrisisDetector + 거시지표)
│   ├── analysis/            # 백테스트, 통계, ML 앙상블
│   ├── web/                 # 웹 대시보드
│   ├── utils/               # 유틸리티 (EventBus, 지표 계산)
│   ├── broker/              # 7개 증권사 연동
│   ├── strategy/            # 유명 투자자 전략 & 자산 배분
│   ├── ai/                  # LLM (OpenAI/Gemini/DeepSeek) & RL
│   └── telegram_bot/        # 텔레그램 봇
├── tests/                   # pytest 테스트 (315개 - 313 pass, 2 skip)
├── trading_system.py        # 메인 통합 시스템
├── .env.example             # 환경 설정 템플릿
├── requirements.txt         # 의존성 목록
└── README.md                # 이 파일 (본 문서)
```

## 신호 파이프라인 상세

### 신호 융합 흐름

```
combined_score = Σ(signal_score × weight) / Σ(active_weights)
    ↓
Style Rotation 보정 (× 0.85 + style_score × 0.15)
    ↓
Consensus Multiplier (60%+ 동의 → 증폭, 30%- 동의 → 감쇠)
    ↓
레짐별 동적 임계값:
  strong_bull:  BUY > 0.48 / SELL < 0.38
  weak_bull:    BUY > 0.52 / SELL < 0.42  (기본값)
  weak_bear:    BUY > 0.62 / SELL < 0.45
  strong_bear:  BUY > 0.70 / SELL < 0.50
```

### 포지션 사이징 9단계

| 단계 | 조정 | 설명 |
|-----|------|------|
| 1 | Kelly Criterion | 승률/손익비 기반 기본 수량 산출 |
| 2 | Conservative Ramp | 초기 30% → 10건 후 100% 점진 확대 |
| 3 | Volatility Targeting | 연 15% 변동성 목표 유지 |
| 4 | Confidence | 신뢰도 비례 (0.5 + conf × 0.5) |
| 5 | Crisis Cash | 위기 시 최소 25% 배율 |
| 6 | Macro Score | macro < 0.3 시 추가 축소 |
| 7 | Earnings Guard | 실적 발표 5일 이내 → 50% 축소 |
| 8 | Information Ratio | 0.7x ~ 1.5x 조정 |
| 9 | Market Impact | 일거래량 5% 초과 시 강제 클램프 |

---

## 주요 기능

### 자동 손절/익절 시스템
- **ATR 기반 동적 레벨**: 변동성(ATR) 적응형 손절/익절 가격 자동 계산
- **3단계 Take Profit**: 33% / 33% / 34% 분할 익절 (ATR 1.5x / 3.0x / 5.0x)
- **레짐 적응**: 강세장일수록 더 넓은 ATR 배수 적용 (최대 8%)
- **트레일링 스탑**: 4% 트레일링 (strong_bull에서 8%)
- **텔레그램 알림**: 발동 시 실시간 알림 전송

### 거시경제 지표 연동 (Macro Integration)
- **5대 거시지표 융합**: VIX(30%), USD/KRW(20%), WTI(20%), 10Y 금리(15%), DXY(15%)
- **위기 탐지**: 4단계 (NONE → CAUTION → WARNING → SEVERE)
- **자동 대응**: 위기 레벨별 신규 매수 차단 → 포지션 청산
- **회복 모드**: 위기 종료 후 20일 점진적 포지션 재확대

### 감성 분석 (Sentiment Analysis)
- **기본 구현**: `SentimentAnalyzer` — 금융 사전(lexicon) 기반 자체 분석
- **LLM 보완**: OpenAI / Gemini / **DeepSeek** 기반 구조화된 감성 도출
- **신호 통합**: 감성 점수(-1.0 ~ 1.0) → `HybridStrategyEngine` 20% 가중치 반영

### 강화 학습 (Reinforcement Learning)
- **PPO 모델**: `stable-baselines3` 기반 (`src/ai/rl_trading.py`)
- **DQN 에이전트**: 자체 PyTorch 구현 (`src/ai/rl_trader.py`)
- **휴리스틱 RL**: 과거 성공/실패 기록 기반 동적 임계값 조정

### 자산 배분 (Asset Allocation)
- **3가지 전략**: `equal_weight`, `risk_parity`, `momentum`
- **결측치 처리**: NaN/Inf 필터링, 가중치 합 1.0 정확 보장

---

## 데이터 흐름

### 1. 시세 및 뉴스 흐름
```
증권사 API → MarketDataHandler ──┐
네이버 뉴스 → NLPEngine ─────────┤  → HybridStrategyEngine → 매매 신호
AlternativeDataClient → 시장레짐 ──┘
```

### 2. 자동 손절/익절 체결
```
시장 데이터 업데이트 → _on_market_data 콜백
                    → check_and_trigger_stop_orders()
                    → 발동된 주문 즉시 시장가 체결
                    → 포트폴리오 업데이트 + 텔레그램 알림
```

### 3. 매매 실행 흐름
```
전략 엔진 → OrderManagementSystem → 진입 주문
                    ↓
            ATR 기반 Stop Loss 자동 생성
            3단계 Take Profit 자동 생성
                    ↓
            증권사 API → 체결 → PortfolioManager
                    ↓
            TradeLogger (로그 + DB 저장)
```

### 4. 피드백 및 최적화
```
TradeLogger → AdaptiveParameterOptimizer → HybridStrategyEngine (파라미터 자동 조정)
           → MLEngine (20번 거래마다 자동 재학습)
```

---

## 로깅

모든 주요 이벤트는 로깅됩니다:
- **INFO**: 시스템 초기화, 주문 체결, 손절/익절 발동
- **DEBUG**: 시세 업데이트, 데이터 캐싱, Macro 지표
- **WARNING**: 미체결 주문, 고슬리피지, 손절 발동, 위기 감지
- **ERROR**: 주문 실패, API 오류

```bash
# 로그 레벨 조정 (.env)
LOG_LEVEL=DEBUG   # 상세 로그
LOG_LEVEL=INFO    # 기본값
LOG_LEVEL=WARNING # 경고 이상만
```

---

## 라이선스

MIT License

## 기여

이슈 및 풀 리퀘스트 환영합니다!