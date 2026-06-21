# 🧪 테스트 가이드 (Testing Guide)

> **Last Updated**: 2026-06-21  
> **Test Framework**: pytest  
> **추정 커버리지**: ~35-40%

---

## 1. 테스트 디렉토리 구조

```
trading_system/tests/
├── __init__.py
├── phase3/                                    # PyTorch 의존 테스트 (DLL 이슈 가능)
│   ├── __init__.py
│   └── test_phase3_integration.py             # Phase3 통합 테스트
├── phase4/                                    # 오케스트레이터 E2E 테스트
│   ├── __init__.py
│   └── test_phase4_orchestrator.py            # 스케줄러, 상태 관리
├── phase6/                                    # 5전략 파이프라인 테스트
│   ├── __init__.py
│   ├── test_lead_lag.py                       # Lead-Lag 행렬 + 예측
│   ├── test_pipeline_integration.py           # 파이프라인 통합 테스트
│   ├── test_surge_classifier.py               # Surge 분류기 학습/예측
│   └── test_vcp.py                            # VCP 규칙 + ML 패턴
├── test_adversarial_fundamental.py            # 펀더멘탈 적대적 테스트
├── test_async_helper.py                       # 비동기 유틸리티
├── test_database.py                           # SQLite CRUD
├── test_ensemble_lgb_cat.py                   # LGB+Cat 앙상블
├── test_event_bus.py                          # EventBus Pub/Sub
├── test_feature_normalization.py              # 피처 정규화
├── test_feature_normalization_stress.py       # 피처 정규화 스트레스
├── test_fundamental_prediction_adversarial.py # 펀더멘탈 예측 적대적
├── test_indicators.py                         # 기술적 지표
├── test_macro.py                              # 거시경제 피처
├── test_macro_stress.py                       # 거시경제 스트레스
├── test_ml_ensemble.py                        # ML 앙상블 예측
├── test_orchestrator.py                       # 오케스트레이터
├── test_portfolio_risk.py                     # 포트폴리오 리스크
├── test_post_market_scoring.py                # 포스트마켓 스코어링
├── test_risk_enhancements.py                  # 리스크 고도화
├── test_risk_manager.py                       # 리스크 매니저
├── test_screener_dash_challenger.py           # 스크리너 대시보드
├── test_strategy_updates.py                   # 전략 업데이트
├── test_system.py                             # 시스템 통합 (24KB)
├── test_telegram_bot.py                       # 텔레그램 봇
└── test_tuning_and_retry.py                   # 튜닝 및 재시도
```

---

## 2. 테스트 실행 가이드

### 2.1 전체 테스트 (PyTorch DLL 오류 회피)

```powershell
.venv\Scripts\activate
.venv\Scripts\python -m pytest tests/ --ignore=tests/phase3/ -v
```

### 2.2 특정 모듈 단독 실행

```powershell
# 5전략 파이프라인 테스트
.venv\Scripts\python -m pytest tests/phase6/ -v

# ML 모델 테스트
.venv\Scripts\python -m pytest tests/test_ml_ensemble.py tests/test_ensemble_lgb_cat.py -v

# 리스크 관리 테스트
.venv\Scripts\python -m pytest tests/test_risk_manager.py tests/test_risk_enhancements.py tests/test_portfolio_risk.py -v

# 데이터베이스 테스트
.venv\Scripts\python -m pytest tests/test_database.py -v

# 피처 정규화 (일반 + 스트레스)
.venv\Scripts\python -m pytest tests/test_feature_normalization.py tests/test_feature_normalization_stress.py -v
```

### 2.3 커버리지 리포트 (pytest-cov 필요)

```powershell
pip install pytest-cov
.venv\Scripts\python -m pytest tests/ --ignore=tests/phase3/ --cov=src --cov-report=html
```

---

## 3. 컴포넌트별 커버리지 현황

| 컴포넌트 | 테스트 파일 | 커버리지 | 평가 |
|----------|------------|----------|------|
| 피처 정규화 | `test_feature_normalization*.py` (2개) | ~80% | ✅ 우수 |
| 펀더멘탈 처리 | `test_adversarial_fundamental.py`, `test_fundamental_prediction_adversarial.py` | ~70% | ✅ 양호 |
| Surge 분류기 | `phase6/test_surge_classifier.py` | ~65% | ✅ 양호 |
| VCP 탐지 | `phase6/test_vcp.py` | ~60% | ⚠️ 보통 |
| Lead-Lag | `phase6/test_lead_lag.py` | ~60% | ⚠️ 보통 |
| 리스크 관리 | `test_risk_manager.py`, `test_risk_enhancements.py`, `test_portfolio_risk.py` | ~70% | ✅ 양호 |
| 오케스트레이터 | `test_orchestrator.py`, `phase4/test_phase4_orchestrator.py` | ~55% | ⚠️ 보통 |
| EventBus | `test_event_bus.py` | ~70% | ✅ 양호 |
| 데이터베이스 | `test_database.py` | ~40% | ❌ 미흡 |
| **config.py** | *(없음)* | ~0% | ❌ 부재 |
| **backtest.py** | *(없음)* | ~0% | ❌ 부재 |
| **report_generator.py** | *(없음)* | ~0% | ❌ 부재 |
| **formatting.py** | *(없음)* | ~0% | ❌ 부재 |
| **동시성 테스트** | *(없음)* | ~0% | ❌ 부재 |

---

## 4. 테스트 작성 가이드라인

### 4.1 비동기 테스트

```python
import pytest

@pytest.mark.anyio
async def test_async_event_delivery():
    event_bus = EventBus()
    received = []
    
    async def subscriber(data):
        received.append(data)
    
    await event_bus.subscribe("test", subscriber)
    await event_bus.publish("test", {"payload": "hello"})
    assert len(received) == 1
```

### 4.2 외부 API 모킹

```python
from unittest.mock import MagicMock, patch

def test_with_mock_api():
    with patch("src.data_layer.earnings_data.fdr.DataReader") as mock_fdr:
        mock_fdr.return_value = pd.DataFrame({"Close": [100, 105]})
        # 테스트 로직
```

### 4.3 SQLite 테스트 격리

```python
import tempfile
import os

def test_database_operations():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = StockPriceDB(db_path=db_path)
        # 테스트 로직 — tmpdir 자동 정리
```

---

## 5. 주의사항

### 스크래치 테스트 파일

`trading_system/` 루트에 다음 스크래치 테스트 파일들이 있으나, 공식 테스트 스위트에 포함되지 않습니다:

| 파일 | 상태 | 비고 |
|------|------|------|
| `test.py`, `test2.py`, `test3.py`, `test4.py` | 스크래치 | 탐색적 테스트 |
| `test_system.py` | 중복 | `tests/test_system.py`와 별도 버전 |
| `test_api.py` | 네트워크 의존 | API 연결 확인용 |
| `test_m1.py` | 스크래치 | 모델 테스트 |
| `standalone_test.py` | 불필요 | pytest로 대체됨 |

### CI/CD

`.github/workflows/`에 GitHub Actions 워크플로우가 설정되어 있습니다:
- Python 3.11 기반
- `pip install -r requirements.txt`
- `pytest` 실행
- ⚠️ 커버리지 리포팅, 린팅, 타입 검사 미포함
