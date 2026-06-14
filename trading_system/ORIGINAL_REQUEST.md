# Original User Request

## Initial Request — 2026-06-07T02:45:53Z

주식 트레이딩 시스템의 전체 코드를 검토하고, 실제 동작과 일치하도록 모든 문서를 업데이트합니다. 특히 감성 분석, 강화학습(RL), 자산 배분 등 핵심 알고리즘에 대해 체계적인 설명을 문서에 포함해야 합니다.

Working directory: d:/Finance/code/stock/trading_system
Integrity mode: development

## Requirements

### R1. 코드와 문서 간의 불일치 해소
- `src/` 디렉터리 내의 실제 구현 코드(HMM, Optuna, 텔레그램 연동, 감성 분석, 강화학습, 자산 배분, 실거래 API 등)를 분석합니다.
- 기존 마크다운 문서(`README.md`, `IMPLEMENTATION_GUIDE.md`, `ADVANCED_FEATURES.md` 등)를 수정하여, 소스 코드의 실제 동작 방식과 문서의 설명이 완벽히 일치하도록 만듭니다.

### R2. 핵심 알고리즘에 대한 체계적 설명 작성
- 감성 분석(Sentiment Analysis), 강화학습(RL), 자산 배분(Asset Allocation) 모듈의 작동 원리를 누구나 문서를 통해 이해할 수 있도록 체계적으로 정리합니다.
- 데이터 파이프라인부터 최종 투자 판단(Weight/Score)까지의 흐름을 명확하게 서술합니다.

## Acceptance Criteria

### 문서 업데이트 검증
- [ ] `ADVANCED_FEATURES.md` (또는 신규 문서) 내에 "감성 분석", "강화학습", "자산 배분" 작동 원리를 설명하는 전용 섹션(Section)이 존재해야 합니다.
- [ ] 문서 내에 `src/broker/real_broker.py`를 비롯한 최근 추가 모듈들의 실제 클래스명과 함수 호출 흐름이 정확하게 반영되어 있어야 합니다. (검증 스크립트로 텍스트 포함 여부 확인 가능)
- [ ] 모든 마크다운 파일에 대해 마크다운 문법 오류가 없어야 합니다.

## Follow-up — 2026-06-07T00:02:51Z

`d:\Finance\code\stock\trading_system`에 위치한 Python 기반 트레이딩 시스템의 수익률과 사용성을 개선한다. 백엔드 전략 로직 5가지와 Dash 기반 대시보드 UI 3가지를 개선하여, 시스템이 시장 상황에 적응하며 더 나은 매매 결정을 내릴 수 있도록 한다.

Working directory: d:\Finance\code\stock\trading_system
Integrity mode: development

## Requirements

### R1. 전략 파라미터 자동 최적화 (그리드 서치)
`src/analysis/backtest.py`의 `optimize_parameters()` 메서드와 `src/core/strategy_engine.py`의 `HybridStrategyEngine`을 연결하여, RSI 임계치(buy_threshold, sell_threshold)·이동평균 기간(short/long window) 등 핵심 파라미터를 yfinance 과거 데이터 기반 백테스트로 자동 탐색·최적화하는 기능을 추가한다. 최적화 결과(파라미터, Sharpe Ratio, 수익률)는 JSON 파일로 저장되어야 한다.

### R2. 마켓 레짐 자동 감지 및 전략 전환
현재 시장을 `bull` / `bear` / `sideways` 3가지 레짐으로 분류하는 로직을 구현한다. 레짐 분류는 EMA200 위치·변동성(ATR 비율)·모멘텀(ROC)을 활용한다. 각 레짐에 따라 `HybridStrategyEngine`이 사용하는 전략 가중치(sentiment/technical/ml 등)와 매수·매도 임계치를 자동으로 전환해야 한다.

### R3. 트레일링 스톱 실시간 구현
`trading_system.py`의 실시간 거래 루프에서, 보유 포지션의 최고가 대비 ATR×2 이상 하락 시 자동 매도하는 트레일링 스톱 로직을 추가한다. 포지션별 최고가(high watermark)를 메모리에 유지하고, 시장 데이터 업데이트 시마다 조건을 체크해야 한다.

### R4. 종목 자동 스크리닝
설정 파일(`risk_config.json` 또는 별도 `screener_config.json`)에 스크리닝 조건(최소 거래량, 52주 신고가 대비 위치, RSI 범위, 섹터 필터 등)을 정의하고, yfinance로 후보 종목 풀(예: S&P500 구성 종목 또는 사용자 정의 유니버스)을 자동 스캔하여 조건을 충족하는 상위 종목을 반환하는 `StockScreener` 클래스를 추가한다.

### R5. 대시보드 개선 — 전략 성과 비교, 실시간 P&L, 백테스트 뷰어
기존 `src/web/dashboard.py` (Dash 기반)에 아래 3개 탭/섹션을 추가 또는 개선한다:
- **전략 성과 비교**: 전략별(MA/RSI/MACD/앙상블/볼린저) 누적 수익률 비교 차트
- **실시간 포지션 현황 & P&L**: 현재 보유 종목·평균단가·평가손익·수익률을 실시간(폴링) 테이블로 표시
- **백테스트 결과 뷰어**: 종목·기간·전략을 선택하면 에쿼티 커브·최대낙폭·거래 내역 히트맵을 시각화

## Acceptance Criteria

### 자동 최적화 (R1)
- [ ] `python -c "from src.analysis.backtest import BacktestEngine; b = BacktestEngine(); result = b.optimize_parameters('AAPL', bars, {'short_window': [10,20], 'long_window': [40,50]}); assert 'best_params' in result"` 실행 성공
- [ ] 최적화 결과가 JSON 파일로 저장됨 (경로: `data/optimized_params.json` 또는 유사)
- [ ] 저장된 JSON에 `best_params`, `best_return`, `sharpe_ratio` 키 포함

### 마켓 레짐 (R2)
- [ ] `HybridStrategyEngine` 또는 별도 클래스에 `detect_regime(price_bars) -> Literal["bull","bear","sideways"]` 메서드 존재
- [ ] bull 레짐에서 technical_weight가 기본값보다 높아짐 (검증: 반환된 가중치 딕셔너리 비교)
- [ ] bear 레짐에서 sell_threshold가 기본값(0.45)보다 낮아짐 (더 민감하게 매도)

### 트레일링 스톱 (R3)
- [ ] `TradingSystem` 클래스 또는 헬퍼에 `_check_trailing_stop(symbol, current_price)` 또는 동등한 메서드 존재
- [ ] 모의 포지션(진입가 100, ATR=2, 최고가 115)에서 현재가 110일 때 → 스톱 발동하지 않음
- [ ] 모의 포지션(진입가 100, ATR=2, 최고가 115)에서 현재가 110 - 4(= 106) 이하일 때 → 매도 신호 반환

### 종목 스크리너 (R4)
- [ ] `StockScreener` 클래스가 `src/` 어딘가에 존재하고 `screen(universe: List[str]) -> List[str]` 메서드를 가짐
- [ ] 더미 조건(최소 거래량 0, RSI 범위 0~100)으로 실행 시 입력 유니버스 전체 반환
- [ ] 실제 조건 설정 파일(`screener_config.json` 또는 `risk_config.json`)이 존재하고 조건 키가 문서화됨

### 대시보드 개선 (R5)
- [ ] `run_dashboard.py` 실행 시 오류 없이 Dash 서버가 기동됨 (`import` + `app.server` 접근 성공)
- [ ] 대시보드 레이아웃에 전략 성과 비교·포지션 현황·백테스트 뷰어 관련 Dash 컴포넌트(탭 또는 섹션 ID)가 존재함
- [ ] 백테스트 뷰어에서 종목·전략 드롭다운 선택 시 에쿼티 커브 그래프가 렌더링됨 (콜백 함수 존재)

## Follow-up — 2026-06-07T20:50:20Z

글로벌 매크로 예측 시스템 상에서 선별된 아웃퍼폼 종목들의 포트폴리오 안정성과 수익률을 극대화하기 위해 리스크 패리티 비중 최적화, VIX 연동형 Risk-Off 스위치, 그리고 외국인/기관 수급 피처 기반의 LightGBM/XGBoost 예측 엔진 고도화를 수행하고 이를 대시보드에 시각화합니다.

Working directory: d:\Finance\code\stock\trading_system
Integrity mode: benchmark

---

## Requirements

### R1. 포트폴리오 리스크 패리티(Risk Parity) 비중 최적화
스크리너가 선정한 한국/미국 탑 10 아웃퍼폼 종목들 간의 공분산(Covariance) 및 개별 변동성을 활용하여, 포트폴리오 내 각 종목의 위험 기여도를 균등하게 배분하는 리스크 패리티 자산 배분 모듈을 구현한다. 최종 포트폴리오의 총 변동성을 최소화하는 방향으로 비중을 산출해야 한다.

### R2. VIX 지수 연동형 동적 자산 배분(Risk-Off) 스위치
실시간 및 과거 VIX 변동성 데이터를 모니터링하여 VIX가 사전 정의된 임계값(예: 25 이상)을 초과할 경우, 포트폴리오의 주식 자산 노출도를 동적으로 낮추고(예: 전체 투자금의 30% 수준으로 감축) 안전 자산(현금) 비중을 자동으로 확대하는 Risk-Off 모듈을 포지션 사이징 엔진에 통합한다.

### R3. 수급 데이터 연동 및 머신러닝 모델(LightGBM/XGBoost) 고도화
기존 RandomForest 예측 모델을 대용량 tabular 및 시계열 분석에 강한 LightGBM 또는 XGBoost 모델로 업그레이드한다. 피처에 종목별 최근 N일간의 외국인 및 기관 순매수 거래량(수급 지표)을 반영하여 매크로 변화 시 기대 초과수익률의 예측 오차(MSE)를 추가로 개선한다.

### R4. Dash 대시보드 자산 배분 시각화 확장
기존 'Global Macro' 탭 내에 아래 시각화 구성 요소를 추가한다:
- **포트폴리오 비중 원형 차트**: 한국 및 미국 탑 10 종목의 리스크 패리티 최적 투자 비중을 시각화하는 Plotly Pie 차트.
- **실시간 자산 노출도(주식 vs 현금) 게이지**: VIX 지수 수준에 따른 현재 자산 배분 상태(주식 투자 노출률 vs 현금 보존률)를 한눈에 보여주는 게이지 차트 혹은 바 차트.

---

## Acceptance Criteria

### 비중 최적화 및 리스크 관리 (R1, R2)
- [ ] `src/analysis/portfolio_optimizer.py` 또는 유사한 경로에 `calculate_risk_parity_weights(cov_matrix)` 형태의 최적화 메서드가 구현됨
- [ ] 산출된 종목별 비중의 합이 정확히 1.0(100%)을 만족하며, 고변동성 종목의 비중이 저변동성 종목 대비 통계적으로 작게 산출되는 균등 리스크 기여 분포를 확인함
- [ ] VIX가 30일 때 `check_risk_off_signal()` 호출 시 주식 최대 노출도 제한(예: 30% 이하) 플래그가 반환됨

### 수급 피처 및 ML 모델 고도화 (R3)
- [ ] `src/analysis/macro_predictor.py`에 LightGBM 또는 XGBoost 모델 인터페이스가 추가되고 정상 학습됨
- [ ] 종목 데이터 프레임에 외국인/기관 순매수량이 피처 열로 추가되어 학습에 활용됨
- [ ] 신규 모델의 검증 메트릭이 기존 RandomForest 대비 예측 오차(MSE)가 개선되거나 동등한 수준을 기록함

### 대시보드 컴포넌트 추가 (R4)
- [ ] `run_dashboard.py` 실행 시 오류 없이 Dash 서버가 기동됨
- [ ] 대시보드 'Global Macro' 탭 내에 포트폴리오 비중을 렌더링하는 Plotly Pie 차트(`dcc.Graph` ID가 `portfolio-weights-pie` 또는 동등)가 존재함
- [ ] 게이지 차트 혹은 노출도 컴포넌트가 존재하여 VIX 변동에 따른 동적 자산 노출 상태를 정상 렌더링함

## Follow-up — 2026-06-11T01:41:13Z

Implement a multi-horizon stock return prediction feature that forecasts and ranks expected stock returns for 5, 10, 15, and 20-day horizons using machine learning models trained on historical market data.

Working directory: d:\Finance\code\stock\trading_system
Integrity mode: development

## Requirements

### R1. Historical Data & Multi-Horizon Feature Engineering
- Retrieve historical daily stock data for the active market stock universe (US and KR symbols).
- Compute technical indicators and features, and calculate forward returns for 5-day, 10-day, 15-day, and 20-day horizons to serve as training targets.

### R2. Machine Learning Forecasting Models
- Build machine learning regressor models (such as Random Forest and XGBoost) tailored for forecasting returns over each horizon (5, 10, 15, 20 days).
- Evaluate model prediction accuracy and scale output values to represent percentage expected returns.

### R3. Rankings and Dashboard Visualization
- Rank the stock universe by highest expected returns for each of the 4 prediction horizons.
- Expose the prediction and ranking results in the Web Dashboard (e.g. by adding a new "AI Forecasts" tab with tabular ranking lists) to make it easy for users to find top performers.

## Acceptance Criteria

### Prediction and Ranking Verification
- [ ] The model generates predicted returns for 5, 10, 15, and 20-day horizons.
- [ ] Results are ranked by return and displayed on the dashboard's "AI Forecasts" tab.
- [ ] New unit tests verify the data pipeline, training process, and forecasting outputs.
