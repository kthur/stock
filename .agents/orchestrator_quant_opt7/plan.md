# Master Plan — Phase 7 Zenith Quantitative Enhancements (v14)

## Objective
Execute the 7th deep quantitative enhancement to further maximize Net Expected Return, Sharpe Ratio, and Information Coefficient (IC) across all 37 diversification strategies in 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

## Scope & Milestones
- **Step 0: Survey & Scoping**:
  - Dispatch 3 parallel Explorers:
    - Explorer 1 (Signal & Noise): Inspect `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, and test files.
    - Explorer 2 (Portfolio & Execution): Inspect `src/risk/unified_portfolio_allocator.py`, `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`.
    - Explorer 3 (Benchmark & Regression Suite): Inspect `trading_system/scripts/benchmark_phase6_quant_performance.py`, `reports/quant_benchmark_comparison_phase6.md`, `tests/test_benchmark_phase6.py`, and general test suite.
  - Synthesize reports into `PROJECT.md` (Feature Inventory, Milestones, Interfaces).

- **Milestone 1: 37대 전략 다변화 알파 신호 비선형 시너지 및 꼬리 신뢰도 7차 극대화**:
  - F47: 5대 기둥(가치, 모멘텀, 수급, 퀄리티, 감성) 교차 텐서 시너지 및 레짐 전이 점프-확산(Jump-Diffusion) 가중치 고도화.
  - F48: 변동성 체제별 마르코프 정상 분포 이탈 페널티 및 적응형 노이즈 데드밴드 미세 조정.
  - Cycle: Explorers(3) -> Worker(1) -> Reviewers(2) -> Challengers(2) -> Auditor(1) -> Gate.

- **Milestone 2: 4-Model 포트폴리오 다변량 코퓰러 배분 및 L3 오더북 체결 마찰비용 최소화 7차 심화**:
  - F49: Black-Litterman, HERC, Risk Parity, EVT-CVaR 4대 배분 모델 간 다변량 꼬리 의존성(Copula Tail Dependency) 기반 동적 신뢰도 틸팅 및 Euler CCVaR 리스크 예산 정밀화.
  - F50: Level-3 오더북 큐 불균형(Queue Imbalance) 및 Bivariate Hawkes 도착 강도 기반 마이크로 가격 페깅과 다크풀/ATS 유동성 포획 고도화.
  - Cycle: Explorers(3) -> Worker(1) -> Reviewers(2) -> Challengers(2) -> Auditor(1) -> Gate.

- **Milestone 3: Phase 7 Zenith 벤치마크 평가 엔진 및 15대 핵심지표 비교 보고서**:
  - F51: `trading_system/scripts/benchmark_phase7_quant_performance.py` 구축, `reports/quant_benchmark_comparison_phase7.md` 및 마스터 리포트 동기화, 단위 테스트 작성.
  - Cycle: Explorers(3) -> Worker(1) -> Reviewers(2) -> Challengers(2) -> Auditor(1) -> Gate.

- **Milestone 4: 전수 2,536+ 테스트 회귀 검증 및 무결성 감사**:
  - F52: 전체 `tests/` 스위트 100% 합격 검증, 0 regression, 최종 감사 확인.

- **Master Handoff & Completion**:
  - Compile comprehensive results, write `handoff.md`, send message to parent.
