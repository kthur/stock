# Scope: Quantitative Trading System Optimization (R1, R2, R3)

## Architecture
- **Strategy & Alpha Layer**: `src/ai/ensemble_scorer.py`, `src/ai/score_normalizer.py`, `src/ai/factor_orthogonalizer.py`, `src/ai/factor_suppression.py`, `src/core/*`, `src/ai/prediction_model.py`.
- **Portfolio Optimization & Cost Layer**: `src/risk/unified_portfolio_allocator.py`, `src/analysis/portfolio_optimizer.py`, `src/risk/portfolio_allocator.py`, `src/execution/turnover_optimizer.py`, `src/execution/oms_engine.py`, `src/execution/slippage_feedback.py`.
- **Pipeline & Reporting Layer**: `trading_system/run_pipeline.py`, `src/pipeline/reporter.py`, `trading_system/generate_report.py`.
- **Verification & Test Suite**: `tests/` (1,900+ / 2,130+ automated tests).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | Multi-Horizon Alpha Half-Life & Decay | 멀티호라이즌(1d~200d) 가중치 반감기 및 감쇠 함수 정밀화로 단기 노이즈 억제 및 중장기 추세 알파 보존 | M1 | ORIGINAL_REQUEST R1 |
| F02 | Cross-Sectional Normalization Scaling | Winsorized Gaussian CDF [0.05, 0.95] 및 섹터 중립 랭킹 스케일 정밀화로 상위 1% 알파 종목 식별력 제고 | M1 | ORIGINAL_REQUEST R1 |
| F03 | 37-Strategy Regime Adaptive Weights & IC Boosting | 2D 레짐(6개 국면) 매트릭스 결합 가중치 정밀화 및 Löwdin 대칭 직교화 보정으로 상관 노이즈 억제 및 IC/Rank-IC 극대화 | M1 | ORIGINAL_REQUEST R1 |
| F04 | Critical Strategy Defect Remediation | v8 플랜 상의 CRIT-03(LSTM), CRIT-04(RIM), CRIT-09(결측 직교화), CRIT-10(Darkpool), CRIT-11(ZCA PC1), CRIT-12(CARD VIX 부호) 등 신호 결함 전수 해결 | M1 | system_improvement_plan_v8 |
| F05 | Multi-Currency US FX Price Scaling (CRIT-01) | UnifiedPortfolioAllocator 내 미국 주식 배분 시 KRW/USD 환율 변환 적용하여 1,350배 과대 주문 방지 | M2 | system_improvement_plan_v8 / R2 |
| F06 | Black-Litterman Horizon & Covariance Scaling (CRIT-02) | BL 20일 전망수익률과 일별 공분산의 시계열 단위 불일치 해소(연율화/일별 정합화)로 코너해 붕괴 방지 | M2 | system_improvement_plan_v8 / R2 |
| F07 | 4-Model Optimization Regime Blending & Solvers | BL + HERC + RP + EVT-CVaR 4-Model 자산배분 안정화, 소규모 유니버스($N \le 4$) CVaR 상한 제약 완화(CRIT-06) 및 HERC 동적 캡 | M2 | ORIGINAL_REQUEST R2 |
| F08 | Gatheral 3/2-Power Market Impact & Friction Cost Optimization | Gatheral 3/2승 시장충격, STT/SEC 및 슬리피지 피드백 반영 순예상수익률 극대화 및 USD 계좌 버퍼 밴드 버그(CRIT-07) 수정 | M2 | ORIGINAL_REQUEST R2 |
| F09 | Asymmetric Leland No-Trade Buffer Bands | 진입/청산 비대칭 버퍼 밴드 최적화로 불필요한 턴오버 및 거래비용 손실 최소화 | M2 | ORIGINAL_REQUEST R2 |
| F10 | Comprehensive Test Suite 100% Pass (0 Regression) | 1,900+ 전수 단위/통합 테스트 100% 통과 보장 (HIGH-01 KRX 1주 단언 포함) | M3 | Acceptance Criteria |
| F11 | Quantitative Performance Benchmark Table | 개선 전후 기대수익률, 샤프 비율, 정보 비율(IC), MDD, 거래비용 절감 효과 정량 비교 마크다운 표 산출 | M3 | ORIGINAL_REQUEST R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 37대 전략 신호 품질 및 예측력(Alpha) 극대화 | F01, F02, F03, F04: 신호 예측력(IC/Rank-IC), 감쇠(Half-life), 정규화 스케일, 핵심 신호 결함 보정 | none | IN_PROGRESS |
| M2 | 포트폴리오 최적 배분 및 순예상수익률 최적화 | F05, F06, F07, F08, F09: BL/HERC/RP/CVaR 앙상블, FX 스케일, 3/2승 충격비용, 비대칭 Leland 버퍼 | M1 | PLANNED |
| M3 | 전수 검증 및 성과 정량 비교표 산출 | F10, F11: 1,900+ 테스트 100% 통과 검증, 전후 정량 비교 표 작성 및 최종 보고 | M1, M2 | PLANNED |

## Interface Contracts
### Alpha Signals ↔ Score Normalizer ↔ Ensemble Scorer
- 각 전략 엔진(1~37): `raw_score` 반환 (결측 시 `np.nan` 반환하여 드롭아웃/재정규화 트리거)
- `CrossSectionalScoreNormalizer`: [0.05, 0.95] Winsorized CDF 정규화 스코어 [0.0, 1.0] 출력
- `EnsembleScoringEngine`: 2D 레짐 가중치 행렬, Löwdin 상관 페널티, 가중치 감쇠 적용 후 `combined_score` 및 `net_expected_return` 출력

### Ensemble Scorer ↔ UnifiedPortfolioAllocator ↔ OMS
- `UnifiedPortfolioAllocator.allocate()`: `predictions_df`, `prices_dict`, `base_currency`, `usd_krw` 수신 -> multi-model blending (BL, HERC, RP, CVaR) -> `weight`, `allocation_amount`, `shares`, `lot_size` 출력
- `ExecutionOMSEngine`: 8대 안전 게이트 및 Almgren-Chriss 트랜치 분할 적용 주문 생성
