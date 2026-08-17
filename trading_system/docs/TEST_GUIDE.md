# 🧪 테스트 가이드 (Testing Guide)

> **Last Updated**: 2026-08-17 (KST)  
> **Test Framework**: pytest (1,124+ tests 100% pass)  
> **Test Suite Root**: `tests/`

---

## 1. 통합 테스트 디렉토리 구조

모든 테스트 스위트는 프로젝트 루트의 `tests/` 디렉토리 아래로 단일 통합 관리됩니다:

```
tests/
├── phase3/                                    # 통합 E2E 테스트 스위트
│   └── e2e/
│       └── test_e2e.py
├── test_adversarial_ensemble_scorer_challenger.py # 적대적 앙상블 스코어러 검증
├── test_adversarial_fundamental.py            # 극단 결측 펀더멘탈 적대적 테스트
├── test_alt_data_features.py                  # 얼터너티브 데이터 및 미시구조 피처
├── test_async_helper.py                       # 비동기 동시성 유틸리티
├── test_backtest.py                           # 백테스트 엔진 (SL, TP, 트레일링 스탑)
├── test_black_litterman.py                    # Black-Litterman 포트폴리오 최적화
├── test_config.py                             # TradingConfig 파라미터 및 경계조건 검증
├── test_cpcv_stress_tester.py                 # Combinatorial Purged CV 검증
├── test_dart_corp_mapper.py                   # DART 고유번호 매핑 및 공시 추출
├── test_database.py                           # SQLite WAL 및 StockPriceDB CRUD
├── test_database_concurrency.py               # 동시성 다중 쓰기/읽기 뮤텍스 락 검증
├── test_data_validator.py                     # 거시지표 경계값 및 이상치 필터 검증
├── test_e2e_consolidated.py                   # 31대 전략 엔드투엔드 파이프라인 통합
├── test_ensemble_lgb_cat.py                   # LightGBM + CatBoost + XGBoost 앙상블
├── test_event_bus.py                          # EventBus Pub/Sub 이벤트 전달
├── test_factor_suppression.py                 # VIF 및 2D 레짐 팩터 억제 엔진
├── test_feature_normalization.py              # 시계열 피처 정규화
├── test_feature_normalization_stress.py       # 극단값/NaN 피처 정규화 스트레스
├── test_fundamental_prediction_adversarial.py # 재무제표 60일 Filing Lag 검증
├── test_hpo_and_2d_ensemble.py                # 2D 레짐 및 Optuna 전방수익률 최적화
├── test_hrp_optimizer.py                      # HRP 및 Ledoit-Wolf 공분산 축소
├── test_indicators.py                         # 기술적 지표 (ATR, RSI, MACD, EMA 등)
├── test_kelly_sizing.py                       # Volatility-Adjusted Kelly Sizing
├── test_kis_safety_and_atr.py                 # 브로커 주문 안전장치 및 ATR
├── test_lead_lag_index.py                     # 2-Tier Lead-Lag 시차 상관행렬
├── test_llm_sentiment_engine.py               # FinBERT 공시/뉴스 텍스트 감성 분석
├── test_lstm_predictor.py                     # Strict Causal LSTM 시계열 모델
├── test_macro.py                              # 글로벌 거시경제 피처
├── test_macro_stress.py                       # VIX/환율 급등 매크로 스트레스 테스트
├── test_microstructure_features.py            # 호가 불균형 & 마이크로스프레드
├── test_ml_ensemble.py                        # OnDevicePredictionModel 앙상블
├── test_orchestrator.py                       # 오케스트레이터 데몬 및 스케줄러
├── test_portfolio_allocator_full.py           # EVT-CVaR & Leland 버퍼 밴드
├── test_portfolio_risk.py                     # 포트폴리오 리스크 및 집중도 제약
├── test_post_market_scoring.py                # 장 마감 후 포스트마켓 스코어링
├── test_quad_factor_optimizer.py              # Quad-Factor 중립 QP 최적화
├── test_risk_manager.py                       # CrisisDetector 4단계 위기 제어
├── test_screener_dash_challenger.py           # 스크리너 및 대시보드 챌린저
├── test_sector_rotation.py                    # 업종 상대 모멘텀 & 순환매
├── test_slippage_feedback.py                  # 실체결 슬리피지 피드백 루프
├── test_stat_arb.py                           # Log 가격 공적분 잔차 차익거래
├── test_strategy_coverage_analyzer.py         # 31대 전략 결측 및 커버리지 분석
├── test_system.py                             # 시스템 전체 통합 검증
├── test_telegram_bot.py                       # 텔레그램 봇 명령어 및 알림
└── test_vcp_ml.py                             # Mark Minervini VCP 규칙 및 ML
```

---

## 2. 테스트 실행 가이드

### 2.1 전체 테스트 스위트 실행

```powershell
# 가상환경 활성화 후 전체 테스트 실행
.venv\Scripts\python -m pytest tests/ -v --tb=short
```

### 2.2 특정 영역별 단독 실행

```powershell
# 31대 퀀트 전략 및 앙상블 스코어러 테스트
.venv\Scripts\python -m pytest tests/test_e2e_consolidated.py tests/test_hpo_and_2d_ensemble.py -v

# 포트폴리오 최적화 (HRP, EVT-CVaR, Leland Bands)
.venv\Scripts\python -m pytest tests/test_hrp_optimizer.py tests/test_portfolio_allocator_full.py tests/test_quad_factor_optimizer.py -v

# 리스크 관리 & CrisisDetector
.venv\Scripts\python -m pytest tests/test_risk_manager.py tests/test_macro_stress.py -v

# 데이터베이스 WAL 및 동시성 락
.venv\Scripts\python -m pytest tests/test_database.py tests/test_database_concurrency.py -v

# 피처 엔지니어링 & 60일 Filing Lag
.venv\Scripts\python -m pytest tests/test_feature_normalization.py tests/test_fundamental_prediction_adversarial.py -v
```

### 2.3 커버리지 리포트 생성

```powershell
.venv\Scripts\python -m pytest tests/ --cov=trading_system/src --cov-report=html
```

---

## 3. 핵심 테스트 검증 기준 (SLA Gates)

1. **Pass Rate**: 1,124개 이상의 테스트가 **100% PASS** (0 failures, 0 errors).
2. **Lookahead Bias 차단**: 재무 데이터는 공시일 기준 `+60일`, 미국 매크로 ETF는 `+1일` 시차가 엄격히 적용되는지 검증.
3. **직교화 SLA Gate**: 순수 알파 팩터와 Fama-French 5-Factor 간 최대 상관계수 $\|\rho\| < 0.15$ 통과.
4. **동시성 무결성**: 32개 멀티스레드 동시 읽기/쓰기 중 SQLite `database is locked` 예외 발생 0건.
5. **6대 주문 안전 게이트**: `CrisisLevel.SEVERE` 및 `KILL_SWITCH` 활성 시 신규 매수 주문 100% 차단.
