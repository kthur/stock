# Original User Request

## Initial Request — 2026-07-04T12:20:41+09:00

주식 자동매매 예측 시스템(`d:/Finance/code/stock`)의 전체 코드베이스와 GitHub Actions 워크플로우를
대상으로 운영 버그, 로직 오류, 설정 불일치를 포괄적으로 검토하고, 발견된 모든 문제를 직접 수정한다.

Working directory: d:/Finance/code/stock
Integrity mode: development

---

## 시스템 배경

5개 전략을 병행 운영하는 통합 파이프라인:

| 전략 | 코드 위치 | 출력 파일 |
|------|-----------|----------|
| XGBoost 회귀 | `src/ai/prediction_model.py` | `pipeline_result.txt` |
| Surge 분류기 | `src/ai/prediction_model.py` | `surge_predictions.txt` |
| Lead-Lag | `src/ai/prediction_model.py` | `lead_lag_predictions.txt` |
| VCP 규칙 기반 | `src/ai/vcp_detector.py` | `vcp_patterns.txt` |
| VCP ML | `src/ai/vcp_ml_predictor.py` | `vcp_ml_predictions.txt` |

주요 파일:
- `trading_system/run_pipeline.py` — 전체 파이프라인 오케스트레이션
- `trading_system/src/ai/prediction_model.py` — 회귀 + surge + lead-lag 모델
- `trading_system/src/ai/vcp_ml_predictor.py` — VCP ML (XGB/LGB/CatBoost 앙상블)
- `trading_system/src/data_layer/` — 데이터 로딩, 피처 엔지니어링, DB
- `.github/workflows/` — preseed.yml, pipeline.yml, training.yml, ci.yml, pytest.yml

---

## Requirements

### R1. GitHub Actions 워크플로우 안정성 검토 및 수정

`preseed.yml`, `pipeline.yml`, `training.yml`, `ci.yml`, `pytest.yml` 5개 워크플로우 파일 전체를 검토하여:
- 캐시 키 불일치, 아티팩트 업로드/다운로드 경로 오류, 환경변수 누락 등을 수정한다.
- `merge-and-release` 잡의 릴리즈 생성 및 자산 업로드 로직이 안정적으로 동작하는지 확인한다.
- `SKIP_TRAINING` 조건부 설정이 모델 캐시 히트 여부에 따라 올바르게 작동하는지 검증한다.

### R2. XGBoost/LightGBM/CatBoost 예측 모델 로직 검토 및 수정

`prediction_model.py`의 `load_models()`, `_predict_regression()`, `_predict_surge()` 메서드를 검토하여:
- 모델이 없을 때 예측값이 `0.0` 기본값으로 조용히 실패하는 경우, 명확한 경고 로그를 추가한다.
- 앙상블 가중치 로딩 시 키 타입 불일치(int vs str horizon key)로 인한 잘못된 가중치 적용 여부를 확인하고 수정한다.
- `market` 키의 대소문자 불일치 (`KOSPI` vs `kospi`)가 모델 조회 시 발생하는지 확인하고 수정한다.

### R3. VCP ML 패턴 감지 로직 검토 및 수정

`vcp_ml_predictor.py`의 `predict()` 메서드를 검토하여:
- 마켓 태그 대소문자 처리가 모든 코드 경로에서 일관되게 처리되는지 확인한다.
- Platt Scaling 보정 계수 로딩, 앙상블 가중치 조회 경로에서의 누락 케이스를 확인하고 수정한다.

### R4. 데이터 로딩 및 피처 엔지니어링 검토

`src/data_layer/`, `src/ai/feature_engineering.py`를 검토하여:
- `ALL_FEATURES` 23개 피처가 inference 시에도 훈련 시와 동일한 순서와 방식으로 생성되는지 확인한다.
- 스케일러 로딩(`load_scaler`) 시 파일 미존재 케이스가 graceful하게 처리되는지 확인한다.
- 전역 지표(VIX, TNX 등) 데이터가 누락될 때 파이프라인이 중단되지 않고 처리되는지 확인한다.

### R5. 출력 파일 포맷 및 내용 정확성 검토

각 전략의 출력 파일 생성 코드를 검토하여:
- `pipeline_result.txt`: horizon별 수익률이 `0.0`이 아닌 실제 예측값으로 채워지는지 확인한다.
- `surge_predictions.txt`: surge 확률이 `[0, 1]` 범위를 벗어나지 않는지 확인한다.
- `vcp_ml_predictions.txt`: 마켓별 TOP 10 정렬이 올바른지 확인한다.
- 파일이 비어있거나 모두 0인 경우 명확한 경고를 출력하는 로직이 있는지 확인하고, 없으면 추가한다.

---

## Acceptance Criteria

### GitHub Actions
- [ ] `pipeline.yml`의 모든 matrix job이 `success` 결론으로 완료될 수 있는 구조
- [ ] `merge-and-release` job이 안정적으로 동작하는 구조
- [ ] 모델 캐시 미스 시 훈련이 자동으로 수행됨 (`SKIP_TRAINING=False`)

### 예측 모델
- [ ] `load_models()` 실행 후 로드된 XGB/LGB/CatBoost 모델 수가 로그에 출력됨
- [ ] 모델이 없는 market/horizon에 대해 `WARNING` 레벨 로그가 출력됨
- [ ] 앙상블 가중치 키 타입 불일치로 인해 기본값(`0.4/0.3/0.3`)이 항상 사용되는 버그가 없음

### VCP ML
- [ ] `KOSPI`, `SP500` 등 대문자 market 태그로도 모델과 보정계수가 올바르게 조회됨
- [ ] 모든 마켓에서 예측값이 `0.0`이 아닌 유효한 확률값으로 출력됨

### 출력 파일
- [ ] `pipeline_result.txt`의 수익률 컬럼에 `0.0`만 있는 경우 파이프라인 로그에 경고가 출력됨
- [ ] 출력 파일이 존재하고 비어있지 않음
