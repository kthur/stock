# 🧪 테스트 가이드 (Testing Guide)

> **Last Updated**: 2026-09-03 (KST)  
> **Test Framework**: pytest (2,182+ tests 100% pass)  
> **Test Suite Root**: `tests/`

---

## 1. 통합 테스트 디렉토리 구조 & 4-Tier 체계

모든 테스트 스위트는 프로젝트 루트의 `tests/` 디렉토리 아래로 단일 통합 관리되며, 4단계(Tier 1 Happy, Tier 2 Boundary, Tier 3 Pairwise, Tier 4 Workload) 계층 구조와 정밀 적대적(Adversarial) 스트레스 테스트를 포괄합니다:

```
tests/
├── test_fast_lob_engine.py                         # Fast LOB 제로카피 링버퍼, L3 호가 매칭, Hawkes 강도 검증
├── test_fix_and_ibkr_broker.py                     # FIX 4.4 DMA 프로토콜 세션 및 Interactive Brokers 커넥터 검증
├── test_rl_execution_agent.py                     # 강화학습(RL) 기반 동적 최적 주문 슬라이싱 에이전트 검증
├── test_system_architecture_fixes.py               # KOSDAQ STT 0.15%, .bfill 룩어헤드 제거, OMS 알파 반감기 라우팅 등 검증
├── test_v8_remediation.py                         # V8 시스템 정밀 감사 43개 결함 완결 검증
├── test_world_class_quant_enhancements.py         # 연속 켈리, 팩터 중립화, 호가단위 그리드, 회전율 MVO
├── test_world_class_trader_return_enhancements.py # 미드포인트 페그, 장중 ATR 트레일링 스탑 래칫, Top-K 압축
├── test_v7_returns_maximization.py                # 수익률 극대화 24개 항목 직교 검증
├── test_v6_improvements.py                        # 4-Tier 통합 V6 회귀 테스트 (35개 항목 직교 검증)
├── test_v6_adversarial_stress.py                  # 적대적 극단값/단일종목 N=1/FX 폭등 스트레스 테스트
├── test_score_normalizer.py                       # 37대 전략 횡단면 정규화(Percentile/CDF) 검증
├── test_network_hardening.py                      # 소켓 타임아웃 락 제거 및 지터 백오프 재시도 검증
├── test_fast_cointegration.py                     # Stat-Arb 고속 공적분 및 순수 유의 페어 선별 검증
├── test_e2e_consolidated.py                       # 37대 전략 엔드투엔드 파이프라인 통합
├── test_ensemble_lgb_cat.py                       # LightGBM + CatBoost + XGBoost 앙상블
├── test_factor_orthogonalization.py               # PCA-ZCA Whitening & Gram-Schmidt 직교화
├── test_factor_suppression.py                     # VIF 및 2D 레짐 팩터 억제 엔진
├── test_feature_normalization.py                  # 시계열 피처 정규화 및 결측치 방어
├── test_fundamental_prediction_adversarial.py     # 시장별 동적 Filing Lag (KRX 45d, US 40d) 검증
├── test_hpo_and_2d_ensemble.py                    # 2D 레짐 및 Optuna 전방수익률 최적화
├── test_hrp_optimizer.py                          # HRP, Ledoit-Wolf 공분산 축소 & Black-Litterman
├── test_portfolio_allocator.py                    # EVT-CVaR & Leland 버퍼 밴드 (진입/청산 바이패스)
├── test_portfolio_optimizer_and_oms.py            # 8대 주문 안전 게이트 & Almgren-Chriss 트랜치
├── test_risk_manager.py                           # CrisisDetector VIX 속도/기간구조 완충 제어
├── test_slippage_feedback.py                      # 실체결 슬리피지 피드백 루프 (`trade_logs.db`)
├── test_strategy_correlation_monitor.py           # 37대 전략 간 상관계수 모니터링
├── test_dart_corp_mapper.py                       # DART 고유번호 매핑 및 공시 추출
├── test_database_concurrency.py                   # 동시성 다중 쓰기/읽기 뮤텍스 락 검증
├── test_merge_generic_strategies.py               # 37대 전략 다중 시장 파일 병합 검증
├── test_verify_gha_artifacts.py                   # GHA 산출물 검증 및 37대 정규 전략 순서 검증
└── test_pipeline_integration.py                   # 전체 5개 시장 파이프라인 통합 무결성
```

---

## 2. 테스트 실행 가이드

### 2.1 전체 테스트 스위트 실행

```powershell
# 가상환경 활성화 후 전체 테스트 실행 (2,182개 테스트)
.venv\Scripts\python -m pytest tests/ -v --tb=short

# 빠른 요약 실행
.venv\Scripts\python -m pytest tests/ -q
```

### 2.2 특정 영역별 단독 실행

```powershell
# 초저지연 실행 엔진 & 브로커 연동 테스트
.venv\Scripts\python -m pytest tests/test_fast_lob_engine.py tests/test_fix_and_ibkr_broker.py tests/test_rl_execution_agent.py -v

# 엔터프라이즈 아키텍처 결함 해결 검증
.venv\Scripts\python -m pytest tests/test_system_architecture_fixes.py -v

# V8 시스템 결함 완결 검증 (43개 결함)
.venv\Scripts\python -m pytest tests/test_v8_remediation.py -v

# 월드클래스 퀀트 & 트레이더 수익률 향상 테스트
.venv\Scripts\python -m pytest tests/test_world_class_quant_enhancements.py tests/test_world_class_trader_return_enhancements.py -v

# V6 고도화 4-Tier 핵심 테스트 (45개 항목)
.venv\Scripts\python -m pytest tests/test_v6_improvements.py -v

# 적대적 스트레스 및 경계조건 테스트
.venv\Scripts\python -m pytest tests/test_v6_adversarial_stress.py tests/test_feature_normalization_stress.py -v

# 횡단면 점수 정규화 및 앙상블 스코어러
.venv\Scripts\python -m pytest tests/test_score_normalizer.py tests/test_regime_ensemble.py -v

# 포트폴리오 최적화 (UnifiedPortfolioAllocator, HRP, Black-Litterman, EVT-CVaR, Leland Bands)
.venv\Scripts\python -m pytest tests/test_hrp_optimizer.py tests/test_portfolio_allocator.py tests/test_turnover_optimizer.py -v

# 8대 주문 안전 게이트 (Gate 8 합성 인버스 헤지 포함)
.venv\Scripts\python -m pytest tests/test_portfolio_optimizer_and_oms.py -v

# 37대 전략 산출물 정합성 검증
.venv\Scripts\python -m pytest tests/test_verify_gha_artifacts.py tests/test_merge_generic_strategies.py -v
```

### 2.3 커버리지 리포트 생성

```powershell
.venv\Scripts\python -m pytest tests/ --cov=trading_system/src --cov-report=html
```

---

## 3. 핵심 테스트 검증 기준 (SLA Gates)

1. **Pass Rate**: 2,182개 이상의 테스트가 **100% PASS** (0 failures, 0 errors).
2. **Lookahead Bias 원천 차단**: 재무 데이터는 시장별 법정 시차(KRX 45일, US 40일) 및 실공시일(`filing_date`)이 우선 적용되며, 포트폴리오 수익률 시계열에 `.bfill()` 역방향 참조가 원천 배제됨.
3. **횡단면 정규화 보장**: 37개 전략 신호가 `CrossSectionalScoreNormalizer`를 통해 균일한 분산의 $[0.0, 1.0]$ 범위로 변환되며 결측 시 가중치 0 자동 재정규화.
4. **직교화 SLA Gate**: 순수 알파 팩터와 Fama-French 5-Factor 간 최대 상관계수 $\|\rho\| < 0.15$ 통과.
5. **동시성 무결성**: 멀티스레드 동시 읽기/쓰기 중 SQLite `database is locked` 예외 발생 0건.
6. **8대 주문 안전 게이트**: `CrisisLevel.SEVERE`, `KILL_SWITCH` 활성, 비정상 가격/수량, 순알파 음수 시 신규 매수 차단 및 Gate 8 인버스 헤지 정상 연동.
