# Original User Request

## Initial Request — 2026-06-07T12:29:33Z

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

## Follow-up — 2026-06-07T22:47:57+09:00

미국/한국 시장 대표 지수, 환율, 국채 금리 및 VIX 변동성 데이터를 연계 분석하여 과거 시차 상관관계를 도출하고, 이를 바탕으로 머신러닝 예측 모델을 통해 전체 시장 대비 초과 수익률이 예측되는 최우수 종목들을 선별하여 대시보드에 시각화합니다.

Working directory: d:\Finance\code\stock\trading_system
Integrity mode: benchmark

---

## Requirements

### R1. 글로벌 거시 지표 시차 상관관계 분석 엔진
미국 지수(S&P 500, Nasdaq), 한국 지수(KOSPI, KOSDAQ), 원/달러 환율(USDKRW=X), 미국 10년 국채 금리(^TNX), VIX 변동성 지수(^VIX) 데이터를 yfinance로 로드하여, 글로벌 지수/환율 변동이 한국/미국 주식 시장에 미치는 리드-랙(Lead-Lag) 효과 및 최대 5영업일 시차 상관관계(Cross-Correlation with Lags)를 산출하는 통계 모듈을 추가한다.

### R2. 거시 피처 기반 머신러닝 예측 모델 구축
수집된 매크로 변수들(지수 변동률, 환율 변동률, 국채 금리, VIX 및 이들의 Lagged 데이터)을 입력 특성(Feature)으로 정의하고, 개별 종목의 벤치마크 대비 초과 기대수익률을 타겟으로 하여 다음 기간의 상대 수익률을 학습 및 추론하는 머신러닝 모델(예: Random Forest Regressor 등) 학습 파이프라인을 구축한다.

### R3. 글로벌 아웃퍼폼 종목 자동 스크리너
KOSPI 200 구성 종목과 S&P 500 구성 종목의 과거 주가 데이터를 수집한 뒤, 학습 완료된 머신러닝 예측 모델에 입력하여 향후 시장(각각 KOSPI / S&P500) 대비 기대 초과수익률이 가장 우수한 상위 10개 종목을 한국과 미국 시장 각각 선별하여 결과를 반환하는 스크리너 모듈을 구현한다.

### R4. Dash 대시보드 연동 및 시각화
기존 `src/web/dashboard.py` 파일의 Dash 애플리케이션 레이아웃에 'Global Macro' 탭을 추가하고 아래 요소를 구현한다:
- **글로벌 매크로 상관관계 히트맵**: 지수, 환율, 금리, VIX 간의 교차 시차 상관관계를 나타내는 대화형 Plotly 히트맵 그래프.
- **아웃퍼폼 추천 종목 카드 및 테이블**: 머신러닝 모델이 선정한 한국(KOSPI) 및 미국(S&P 500) 추천 탑 10 종목의 정보와 예측 기대수익률을 비교 시각화하는 표와 카드 컴포넌트.

---

## Acceptance Criteria

### 상관관계 분석 및 모델 (R1, R2)
- [ ] `src/analysis/macro_analyzer.py` 또는 유사한 모듈에 `calculate_cross_correlation(indices_data, lags=5)` 형태의 메서드가 존재하고 정상 작동함
- [ ] `src/analysis/macro_predictor.py` 또는 유사한 예측 모듈이 존재하며, `train_model(features, targets)` 및 `predict_outperformers()` 메서드를 통해 머신러닝 추론을 완료함
- [ ] 학습된 모델의 평가 지표(MSE, R2 Score 등) 및 분석 결과가 `data/macro_model_metrics.json` 형태로 캐싱됨

### 종목 스크리닝 (R3)
- [ ] `StockScreener` 클래스 또는 별도 매크로 스크리너에 `screen_global_outperformers() -> Dict[str, List[Dict]]`와 같은 진입점이 구현됨
- [ ] 해당 스크리닝 메서드 호출 시 한국(KOSPI) 및 미국(S&P 500) 각각 정확히 10개의 최우수 예측 종목 목록을 반환함
- [ ] 반환된 종목 딕셔너리에 `ticker`, `expected_excess_return`, `correlation_to_exchange_rate` 키가 포함됨

### 대시보드 시각화 (R4)
- [ ] `run_dashboard.py` 실행 시 오류 없이 Dash 서버가 기동되어야 함
- [ ] 대시보드 UI에 ID가 `global-macro-tab` 혹은 이와 동등한 신규 탭 요소가 식별됨
- [ ] 대시보드 레이아웃 내에 상관관계 히트맵을 렌더링하는 Plotly `dcc.Graph`와 추천 종목 데이터를 테이블로 표시하는 Dash DataTable 컴포넌트가 존재함

## Follow-up — 2026-06-09T14:44:38Z

Enhance the Machine Learning model ensemble (specifically combining Random Forest and XGBoost using a weighted average/soft voting approach) within the trading system to improve overall return performance.

Working directory: d:\Finance\code\stock\trading_system
Integrity mode: development

## Requirements

### R1. Random Forest + XGBoost 앙상블 모델 구현
- `ml_engine.py` 내의 단일 모델을 `scikit-learn`의 Random Forest Regressor/Classifier와 `xgboost` 모델을 함께 사용하는 구조로 개편합니다.
- 두 모델의 개별 예측값을 소프트 보팅(Soft Voting / 가중 평균) 방식으로 융합하여 0.0 ~ 1.0 범위의 최종 `ml_score`를 도출합니다.

### R2. 테스트 통합 및 성능 검증
- 기존 33개의 pytest 테스트가 깨지지 않고 정상 통과해야 합니다.
- 앙상블 학습(`train`) 및 예측(`predict`) 프로세스를 검증하기 위한 신규 pytest 테스트 케이스를 생성하여 검증을 수행합니다.

## Acceptance Criteria

### 머신러닝 앙상블 모델 성능 및 동작 검증
- [ ] Random Forest와 XGBoost 두 모델 모두가 학습 데이터를 활용해 학습이 정상 완료되어야 합니다.
- [ ] 앙상블 결과로 출력되는 `ml_score`가 유효한 실수 범위(0.0 ~ 1.0)에 존재해야 합니다.
- [ ] 전체 pytest 테스트 케이스가 오류 없이 통과해야 합니다.


## Follow-up — 2026-06-10T16:14:28+09:00

Enhance the Machine Learning model ensemble (specifically combining Random Forest and XGBoost using a weighted average/soft voting approach) within the trading system to improve overall return performance.

Working directory: d:\Finance\code\stock\trading_system
Integrity mode: development

## Requirements

### R1. Random Forest + XGBoost 앙상블 모델 구현
- `ml_engine.py` 내의 단일 모델을 `scikit-learn`의 Random Forest Regressor/Classifier와 `xgboost` 모델을 함께 사용하는 구조로 개편합니다.
- 두 모델의 개별 예측값을 소프트 보팅(Soft Voting / 가중 평균) 방식으로 융합하여 0.0 ~ 1.0 범위의 최종 `ml_score`를 도출합니다.

### R2. 테스트 통합 및 성능 검증
- 기존 33개의 pytest 테스트가 깨지지 않고 정상 통과해야 합니다.
- 앙상블 학습(`train`) 및 예측(`predict`) 프로세스를 검증하기 위한 신규 pytest 테스트 케이스를 생성하여 검증을 수행합니다.

## Acceptance Criteria

### 머신러닝 앙상블 모델 성능 및 동작 검증
- [ ] Random Forest와 XGBoost 두 모델 모두가 학습 데이터를 활용해 학습이 정상 완료되어야 합니다.
- [ ] 앙상블 결과로 출력되는 `ml_score`가 유효한 실수 범위(0.0 ~ 1.0)에 존재해야 합니다.
- [ ] 전체 pytest 테스트 케이스가 오류 없이 통과해야 합니다.
