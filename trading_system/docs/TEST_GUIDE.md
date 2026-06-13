# 🧪 주식 자동매매 시스템 테스트 가이드 (Testing Guide)

본 설명서는 시스템의 비동기 이벤트 루프 테스트 기법, 단위/통합 테스트 구조, 모의 거래(Mock Trading) 테스트 케이스 명세 및 로컬 Windows 환경에서의 실행 가이드를 설명합니다.

---

## 1. 테스트 스위트 구조 (Test Directory Mapping)

테스트 코드는 개발 단계별(Phase 4, Phase 6 등) 및 컴포넌트별로 체계적으로 격리되어 설계되었습니다:

```
trading_system/tests/
├── phase4/                   # E2E 통합 테스트
│   └── e2e/
│       └── test_e2e.py       # 시세 수집부터 주문 집행까지의 전체 파이프라인 E2E 시나리오 테스트
├── phase6/                   # 모의 및 단위 연동 테스트
│   └── unit/
│       └── test_mock_trading.py # SimulatedBroker의 잔고 검증, 슬리피지 연산, 백그라운드 오더 폴링 테스트
├── test_async_helper.py      # 비동기 유틸리티 함수 검증
├── test_database.py          # SQLite DB 테이블 생성 및 영속성 트랜잭션 무결성 검증
├── test_event_bus.py         # Thread-safe 이벤트 버스의 Pub/Sub 비동기 전달 검증
├── test_indicators.py        # 볼린저 밴드, ATR 등 보조지표 수학적 정합성 테스트
├── test_macro.py             # 거시경제 피처 및 한도 정책 연동 검증
├── test_macro_stress.py      # 극단적 한계 상황(결측 데이터, 이상치 등) 입력 대응 스트레스 테스트
├── test_ml_ensemble.py       # Random Forest + XGBoost 소프트 보팅 가중치 예측 정확도 및 API 로드 테스트
├── test_orchestrator.py      # 오케스트레이터 CLI 구동 및 백그라운드 스케줄러 검증
├── test_portfolio_risk.py    # 자산 배분 비중 제한 검증
├── test_risk_enhancements.py # 변동성 조절 Kelly 및 regime-adaptive trailing stop 검증
├── test_risk_manager.py      # 손절/익절 조건 및 포트폴리오 서킷 브레이커 검증
├── test_screener_dash_challenger.py # 대시보드 백테스트 스캐너 API 응답성 테스트
├── test_system.py            # 시스템 통합 엔진 코어 기능 단위 테스트
└── test_telegram_bot.py      # 텔레그램 명령어 수신 모킹 테스트
```

---

## 2. Windows 로컬 테스트 실행 가이드

로컬 머신(Windows) 환경의 그래픽 드라이버(CUDA) 혹은 인텔 MKL 라이브러리 손상 등의 사유로 `torch` 라이브러리가 로드되지 않는 문제(`WinError 1114`)에 직면할 경우, 다음 명령어를 통해 문제 구역을 무시하고 전체 245개 핵심 로직 테스트를 정상 실행할 수 있습니다.

### 2.1 전체 핵심 테스트 실행 (PyTorch DLL 오류 회피)
반드시 가상환경 활성화 상태에서 `python -m pytest` 형태로 실행하여 프로젝트 `src` 경로를 path에 포함하십시오.
```powershell
# 가상환경 활성화
.venv\Scripts\activate

# phase3 테스트(PyTorch DLL 오류 발생 구역)를 제외한 전체 테스트 수행
.venv\Scripts\python -m pytest tests/ --ignore=tests/phase3/
```

### 2.2 특정 테스트 모듈 단독 실행
특정 알고리즘이나 기능만 타겟하여 고속 검증할 때 사용합니다:
```powershell
# 1. 머신러닝 앙상블 기능 테스트
.venv\Scripts\python -m pytest tests/test_ml_ensemble.py -v

# 2. 리스크 매니저 통제 로직 및 신규 변동성 스케일링 테스트
.venv\Scripts\python -m pytest tests/test_risk_manager.py -v
.venv\Scripts\python -m pytest tests/test_risk_enhancements.py -v

# 3. 오케스트레이터 및 백그라운드 스케줄러 테스트
.venv\Scripts\python -m pytest tests/test_orchestrator.py -v

# 4. 모의 거래 엔진 테스트
.venv\Scripts\python -m pytest tests/phase6/unit/test_mock_trading.py -v
```

---

## 3. 비동기 이벤트 루프 및 Mocking 팁

자동매매 엔진은 대시보드와 비동기 큐(`asyncio`), 스레드(`threading`)가 혼재되어 있으므로 테스트 시 다음 원칙을 준수하여 작성되었습니다.

### 3.1 `pytest.mark.anyio` 또는 `pytest-asyncio` 활용
비동기 코루틴(coroutine)을 직접 테스트해야 하는 경우, 테스트 데코레이터와 `anyio` 백엔드를 지정합니다:
```python
import pytest

@pytest.mark.anyio
async def test_async_event_delivery():
    event_bus = EventBus()
    received_events = []
    
    async def subscriber(data):
        received_events.append(data)
        
    await event_bus.subscribe("test_topic", subscriber)
    await event_bus.publish("test_topic", {"payload": "hello"})
    
    assert len(received_events) == 1
    assert received_events[0]["payload"] == "hello"
```

### 3.2 Mock을 이용한 외부 API 차단
실제 OpenAI, Gemini 또는 DeepSeek API 통신 없이 비즈니스 로직을 검증하도록 `unittest.mock`을 적극 활용합니다.
```python
from unittest.mock import MagicMock, patch

def test_llm_opinion_fallback():
    # LLMEngine의 API 호출부를 모킹하여 더미 응답 데이터 고정 반환
    with patch("src.ai.llm_integration.LLMEngine._call_gemini_api") as mock_api:
        mock_api.return_value = '{"recommendation": "BUY", "sentiment": "긍정적", "confidence": 80, "target_price": 150}'
        
        engine = LLMEngine(provider="gemini", api_key="dummy")
        opinion = engine.query_investment_opinion({"symbol": "AAPL", "price": 130})
        
        assert opinion.recommendation == "BUY"
        assert opinion.confidence == 0.8
```
위와 같이 외부 입출력을 격리(Isolation)함으로써 로컬 네트워크 상태와 무관하게 100% 재현 가능한 독립 테스트 환경을 유지합니다.
