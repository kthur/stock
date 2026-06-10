# 수익률 극대화 및 안정화 구현 계획 (Phase 7)

본 계획은 기존에 완료된 글로벌 매크로 분석(Phase 6)을 바탕으로, 프로젝트의 실질적인 **기대 수익률을 극대화**하고 **하방 리스크(Drawdown)를 방어**하기 위한 아키텍처 및 로직 고도화 방안을 담고 있습니다.

## User Review Required

> [!IMPORTANT]  
> **수급 데이터 확보 방안 확인**: 한국 시장의 경우 외국인/기관 순매수 수급 데이터를 실시간으로 가져오기 위해 `pykrx` 라이브러리 등 별도의 데이터 소스가 필요할 수 있습니다. (현재 yfinance는 수급 정보를 제공하지 않음) 이에 대한 라이브러리 추가가 괜찮으신지 검토가 필요합니다.
>
> **스타일 로테이션 도입**: 단순 개별 종목 분석을 넘어, '성장주 vs 가치주' / '대형주 vs 중소형주' 로테이션 전략을 시스템에 도입하여 거시 경제 환경(금리, 환율)에 따라 주도 테마를 스위칭하는 기능을 포함하고자 합니다. 승인해주시면 반영하겠습니다.

## Open Questions

- 서버 재시작으로 인해 기존 서브에이전트(리스크 패리티 팀)의 작업이 일부만 반영된 상태입니다. 중단된 **리스크 패리티 최적화** 및 **VIX Risk-Off 스위치** 연동을 본 계획에 포함하여 완전히 마무리할까요?
- 대시보드에 추가적으로 확인하고 싶으신 수익률 관련 시각화 지표(예: 전략별 샤프 지수, 스타일 로테이션 상태 게이지 등)가 있으신가요?

## Proposed Changes

### 1. 머신러닝 예측 엔진 초고도화 (LightGBM & XGBoost 앙상블)

기존 `macro_predictor.py`의 RandomForest를 넘어서, 대용량 정형 데이터와 시계열 분석에 최적화된 **LightGBM / XGBoost 앙상블 모델**로 전면 업그레이드합니다. 

#### [MODIFY] [macro_predictor.py](file:///d:/Finance/code/stock/trading_system/src/analysis/macro_predictor.py)
- `XGBRegressor` 및 `LGBMRegressor` 도입
- 두 모델의 예측값을 가중 평균(Ensemble)하여 기대 초과수익률의 예측 오차(MSE) 최소화
- **신규 피처 연동**: 외국인/기관 수급 지표(가능한 데이터 소스 활용), 10년물-2년물 장단기 금리차, 환율 변동성 등

### 2. 스타일 로테이션 (Style Rotation) 모듈 신설

시장 환경(금리/환율/VIX)에 따라 가장 유리한 주식 스타일(성장/가치/대형/중소형)을 판별하여 스크리닝 유니버스와 포트폴리오 비중을 동적으로 조정합니다.

#### [NEW] [style_rotator.py](file:///d:/Finance/code/stock/trading_system/src/analysis/style_rotator.py)
- 현재 거시 레짐(Macro Regime) 판단: 인플레이션 상승/하락, 금리 상승/하락 구간 식별
- 레짐에 따른 최적 팩터(Factor) 점수 부여 로직 구현

### 3. VIX 동적 스위치 및 포트폴리오 리스크 패리티 (마무리 통합)

중단되었던 포트폴리오 안정화 작업을 완수하고 실시간 시스템에 연결합니다.

#### [MODIFY] [portfolio_optimizer.py](file:///d:/Finance/code/stock/trading_system/src/analysis/portfolio_optimizer.py)
- `calculate_risk_parity_weights` 최적화 로직의 안정성 검증 (완료된 부분 점검)
- 각 종목별 상관관계 기반 공분산 행렬 연동

#### [MODIFY] [trading_system.py](file:///d:/Finance/code/stock/trading_system/trading_system.py)
- **VIX Risk-Off 스위치**: VIX가 25, 30 등 임계값을 넘을 때 포지션 한도를 즉시 30% 이하로 축소 및 현금화 (방어력 극대화)
- 실시간 리스크 패리티 비중에 맞춘 자산 재분배(Rebalancing) 로직 추가

### 4. Kelly Criterion 실시간 연동 (동적 포지션 사이징)

#### [MODIFY] [risk_manager.py](file:///d:/Finance/code/stock/trading_system/src/core/risk_manager.py)
- 백테스트에서 얻은 실제 승률(Win Rate)과 손익비(Profit Factor)를 가져와 켈리 공식으로 베팅 사이즈를 결정
- 고정 5% 손절 / 10% 익절 비율을 **ATR 기반 동적 손절/익절**로 변환하여 수익을 끝까지 추적(Trailing Stop 효과)

### 5. 대시보드 (수익률 / 리스크 시각화)

#### [MODIFY] [dashboard.py](file:///d:/Finance/code/stock/trading_system/src/web/dashboard.py)
- **자산 배분 파이 차트**: 리스크 패리티가 적용된 현재 포트폴리오의 비중 현황
- **VIX & Risk 상태 게이지**: 현재 시스템이 'Risk-On(공격투자)'인지 'Risk-Off(안전제일)'인지 직관적으로 보여주는 UI 추가

## Verification Plan

### Automated Tests
- `pytest tests/test_macro_predictor.py`: XGBoost/LightGBM 모델의 학습 및 추론 파이프라인 무결성 검증
- `pytest tests/test_portfolio_risk.py`: 리스크 패리티 최적화 함수 및 VIX 임계치에 따른 포지션 축소 플래그 검증

### Manual Verification
- 대시보드 `run_dashboard.py` 실행 후 'Global Macro' 또는 'Portfolio' 탭에서 새로 추가된 파이/게이지 차트 렌더링 확인
- S&P 500 및 KOSPI 모의 데이터 주입 시, VIX 급등 구간에서 포지션 사이즈가 축소되는지(Risk-Off 동작) 터미널 로그로 확인
