# 테스트 인프라 정의서 - TEST INFRA

## 1. 테스트 기본 설계 철학

- **통합 및 유닛 테스트 병행**: 시스템의 개별 수학적 알고리즘(RSI, MACD, Kelly 등)을 검증하는 독립 유닛 테스트와 외부 API, DB, 텔레그램 봇, 비동기 루프 등 실시간 연동을 모사하는 E2E 및 시나리오 테스트를 고루 구성합니다.
- **결정론적 검증 및 격리**: 외부 환경 변수 및 서드파티 라이브러리(yfinance, stable-baselines3, PyQt5 등)의 설치 여부에 따라 테스트가 강제로 실패하지 않도록 Mock 객체 및 `importorskip` 조건부 스킵 처리를 적용하여 안정성을 확보합니다.
- **스트레스 및 한계 상황 검증**: NaN 데이터 유입, 극단적 시세 급락, 대형 주문에 따른 시장 충격(Market Impact), 상관계수 급등 등 복합적 위기 상황에 대한 방어력을 테스트합니다.

---

## 2. 테스트 스위트 구성 및 현황

전체 테스트 스위트는 총 **315개**의 테스트 케이스로 이루어져 있으며, `pytest`를 통해 일괄 수행됩니다.

### 2.1 테스트 실행 환경 및 명령어

```bash
# 가상환경 내에서 전체 315개 테스트 실행
.venv\Scripts\python -m pytest tests/ -v
```

### 2.2 최종 테스트 수행 결과

- **총 테스트 수**: 315개
- **성공 (Passed)**: 313개
- **스킵 (Skipped)**: 2개 (조건부 환경 미구성 등으로 인한 강제 중단 방지용 스킵)
- **수행 속도**: 약 4분 (240초 내외)

---

## 3. 테스트 파일 구성 및 책임 범위

### 3.1 코어 컴포넌트 유닛 테스트

- **[test_system.py](file:///d:/Finance/code/stock/trading_system/tests/test_system.py)**: `StockTradingSystem` 클래스의 메인 루프, 리밸런싱 스케줄링, 9단계 포지션 사이징 파이프라인, 트레일링 스탑의 기본 매매 결정을 검증합니다. (50+ 테스트)
- **[test_risk_manager.py](file:///d:/Finance/code/stock/trading_system/tests/test_risk_manager.py)**: Kelly Criterion, Volatility Targeting, VaR/CVaR, Drawdown 모니터링 등 위험관리 로직을 정밀하게 테스트합니다. (33개 테스트)
- **[test_telegram_bot.py](file:///d:/Finance/code/stock/trading_system/tests/test_telegram_bot.py)**: 텔레그램 봇 명령어 분석기, 가상 메시지 전송 및 명령 파싱 응답 동작을 모사합니다. (17개 테스트)

### 3.2 신규 기능 검증 테스트

- **[test_ml_ensemble.py](file:///d:/Finance/code/stock/trading_system/tests/test_ml_ensemble.py)**: Random Forest와 XGBoost 앙상블 학습(`train`), soft voting 예측(`predict_prob`), HMM 시장 레짐 피처 결합 여부를 검증합니다.
- **[test_mock_trading.py](file:///d:/Finance/code/stock/trading_system/tests/phase6/unit/test_mock_trading.py)**: `mock_trading` 모드 동작 시 실제 주문이 브로커로 전송되는지 여부와 백그라운드 주문 감시 루프(`_monitor_broker_orders`)의 체결 상태 매핑 동작을 Mocking을 통해 완벽하게 검증합니다.
- **[test_indicators.py](file:///d:/Finance/code/stock/trading_system/tests/test_indicators.py)**: RSI, MACD, Bollinger Bands, ATR, ADX 등 시스템 전반에서 쓰이는 보조 지표 계산 함수들의 정합성을 테스트합니다.
- **[test_database.py](file:///d:/Finance/code/stock/trading_system/tests/test_database.py)**: aiosqlite 기반의 3개 비동기 데이터베이스(거래 이력, 자산 내역, AI 예측 내역)의 입출력 및 연결 라이프사이클을 테스트합니다.
- **[test_event_bus.py](file:///d:/Finance/code/stock/trading_system/tests/test_event_bus.py)**: EventBus의 비동기 메시지 발행/구독 구조, fire-and-forget 예외 격리 등을 보장하는지 검증합니다.
- **[test_async_helper.py](file:///d:/Finance/code/stock/trading_system/tests/test_async_helper.py)**: 비동기 호출 타임아웃, 예외 포착 도구 동작을 테스트합니다.
- **[test_macro_stress.py](file:///d:/Finance/code/stock/trading_system/tests/test_macro_stress.py)**: 매크로 데이터 분석 시의 NaN 결측치 유입 및 비정상적 값 처리에 따른 강인성(Robustness)을 검증합니다.

---

**마지막 업데이트**: 2026-06-11
