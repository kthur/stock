# Original User Request

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
