# 프로젝트 명세서 - PROJECT

## 1. 아키텍처 및 핵심 컴포넌트

- **src/analysis/backtest.py**: 백테스트 시뮬레이터 및 수수료/슬리피지/시장 충격 모델링
- **src/analysis/adaptive_optimizer.py**: TPE 샘플러를 이용한 베이지안 파라미터 최적화 및 주기적 재최적화 스케줄링
- **src/analysis/ml_engine.py**: Random Forest + XGBoost 앙상블 모델, HMM 기반 시장 레짐, Optuna 하이퍼파라미터 튜닝
- **src/core/strategy_engine.py**: 9개 신호 가중합 전략 엔진, 레짐별 임계값 자동 전환 및 적응형 신호 가중치
- **src/ai/llm_integration.py**: OpenAI, Gemini 및 DeepSeek(V3, R1) 통합 어댑터
- **trading_system.py**: 메인 통합 시스템 루프 및 9단계 포지션 사이징 파이프라인, 트레일링 스탑, 모의투자 연동 감시 루프
- **src/web/dashboard.py**: Dash 기반 실시간 포트폴리오, 리스크 모니터링 및 성과 속성 차트 제공
- **src/telegram_bot/telegram_bot_engine.py**: 18개 이상의 제어 및 모니터링 명령어를 처리하는 텔레그램 메신저 연동

---

## 2. 개발 마일스톤 및 완료 현황

| # | 마일스톤 | 범위 | 상태 |
|---|----------|------|------|
| 1 | E2E 테스트 스위트 설계 | `tests/` E2E 테스트 기본 설계 및 `TEST_READY.md` 작성 | **DONE** |
| 2 | 매개변수 최적화 및 레짐 탐지 | 그리드 검색 및 레짐 전환 가중치 반영 모듈 완료 | **DONE** |
| 3 | 트레일링 스탑 및 스크리너 | ATR 기반 트레일링 스탑, 종목 스크리너 구현 완료 | **DONE** |
| 4 | Dash 기반 웹 UI | 실시간 PnL, 포트폴리오 가치 추이, 리스크 게이지 UI 구축 완료 | **DONE** |
| 5 | E2E 검증 및 안정화 | adversarial 스트레스 테스트 추가 및 ruff 0 경고 유지 | **DONE** |
| 6 | 모의 투자 연동 | 한국투자증권 및 키움증권 모의투자 API 주문 전송 및 실시간 체결 감시 | **DONE** |
| 7 | 머신러닝 엔진 및 LLM 고도화 | RF+XGBoost 앙상블, HMM 레짐 피처화, Optuna 파라미터 최적화, DeepSeek API 연동 | **DONE** |

---

## 3. 주요 인터페이스 규격

### 3.1 적응형 매개변수 최적화
- `AdaptiveParameterOptimizer.optimize(symbols, lookback_days, n_trials, decay_rate)`: TPE 탐색을 통해 최적 파라미터를 탐색하고 `data/adaptive_params.json`에 영구 저장.

### 3.2 앙상블 ML 예측
- `MLEngine.predict_prob(price_bars)`: Random Forest와 XGBoost의 소프트 보팅 확률을 계산해 다음 시점 상승 확률 예측.
- `MLEngine.optimize_hyperparameters(price_bars, n_trials)`: Optuna 기반 log_loss 최소화 파라미터 자동 튜닝.

### 3.3 LLM 분석 통합
- `LLMEngine.query_investment_opinion(stock_data)`: 설정된 LLM 제공자(DeepSeek, OpenAI, Gemini)에게 주식 재무 및 기술적 보조 정보를 제공하고 구조화된 신호 및 텍스트 획득.

---

## 4. 최종 코드 레이아웃

- `src/analysis/backtest.py`: 백테스트 엔진
- `src/analysis/ml_engine.py`: ML 앙상블 및 HMM 레짐, Optuna
- `src/analysis/adaptive_optimizer.py`: 파라미터 적응 최적화기 및 스케줄러
- `src/core/strategy_engine.py`: 9-신호 하이브리드 전략 엔진
- `src/ai/llm_integration.py`: OpenAI/Gemini/DeepSeek 통합 어댑터
- `trading_system.py`: 메인 트레딩 시스템 구동부 및 모의투자 감시 루프
- `tests/`: 315개 유닛, E2E, 시나리오, 스트레스 테스트 케이스

---

**마지막 업데이트**: 2026-06-11
