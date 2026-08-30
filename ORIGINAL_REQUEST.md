# Original User Request

## Initial Request — 2026-08-30T07:01:22+09:00

You are the Project Orchestrator for the stock trading system.

Your mission is to diagnose and remediate core system weaknesses across the entire stock prediction and trading pipeline:
1. Portfolio Optimization (HRP, Ledoit-Wolf Shrinkage, CVaR, Black-Litterman) and OMS 7-Safety Gate execution hardening.
2. Pipeline run speed, memory footprints, and parallel execution efficiency across 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).
3. Conduct full audit of 31+ multi-factor strategy engines (src/core/, src/ai/) for robust missing-data exception handling and fallback resilience.
4. Stabilize backtest engines and GitHub Actions CI workflow consistency.

Reference:
- User request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- Project rules: d:\Finance\code\stock\AGENTS.md
- Working directory for your metadata: d:\Finance\code\stock\.agents\orchestrator_hardening

Decompose the work into clear milestones, spawn specialists/workers/reviewers as needed, maintain plan.md and progress.md in your directory, run tests using `.venv/bin/pytest tests/ -v` (or `.venv\Scripts\pytest tests/ -v`), and ensure 100% test pass rate and clean pipeline execution before claiming completion.

## 2026-08-30T00:55:44Z

This is a single self-contained project with focused implementation; keep it small and focused.
31대 다변화 전략 주식 자동매매 및 예측 시스템의 **수익률 극대화(Alpha Generation)**와 **데이터 정확성 및 정합성(Data Accuracy & Coverage)**을 전면 감사하고, 식별된 결함과 개선점을 엔드투엔드로 구현 및 검증하는 프로젝트.

Working directory: `d:\Finance\code\stock`
Integrity mode: development

## Requirements

### R1. 31대 전략 데이터 정확성 및 결측/폴백 전면 정상화 (Data Accuracy & Fallback Hardening)
- 31대 전략 전수 데이터 수집 및 피처 추출 파이프라인에서 데이터 정렬, 결측치, 단위 불일치, 동적 Filing Lag(KRX 45d, US 40d) 적용 상태를 전수 감사하고 비정상 NaN/0% 커버리지 전략(`card_factor`, `accruals_quality`, `inst_foreign_sector`, `vcp_ml`, `lstm`, `sentiment`, `earnings_tone_drift` 등)을 정상화한다.
- 실시간 수급, 재무제표, 매크로 지표 미수신 시에도 왜곡 없는 정밀 휴리스틱/프록시 데이터 폴백을 구성하여 `strategy_data_coverage_report.txt`의 유효 커버리지를 100%로 끌어올린다.

### R2. 예측 모델 알파 고도화 및 시장별 최적화 (Return Maximization & Alpha Enhancement)
- 예측 모델의 횡단면 랭킹 정확도(Top Decile Information Coefficient)를 극대화하고, 시장별 특성(SP500/NASDAQ/RUSSELL2000/KOSPI/KOSDAQ)에 맞춘 하이퍼파라미터 및 손실 함수(비대칭 리스크 페널티)를 최적화한다.
- 31대 전략 동적 가중치 배분(음수 Sharpe 데드락 방지 바닥 가중치), 팩터 직교화(PCA-ZCA/ESRW 로버스트 중앙값 임퓨테이션), 미시구조 거래비용 호라이즌 상각 모델을 정밀화하여 순수 알파 기여도를 극대화한다.

### R3. 포트폴리오 최적화 및 주문 집행 정밀도 (Portfolio Optimization & Execution OMS)
- HRP, Ledoit-Wolf 공분산 축소, EVT-CVaR 꼬리위험 예산 배분 및 Leland 동적 노-트레이드 버퍼 밴드를 점검하여 슬리피지와 불필요한 회전율(Churning)을 최소화한다.
- 7대 주문 안전 게이트 및 Almgren-Chriss 분할 집행 로직의 주문 수량/가격 산출 정밀도를 검증한다.

### R4. 워크포워드 백테스트 엔진 실측 검증 (Walk-Forward Backtest Verification)
- `WalkForwardBacktestEngine`을 실행하여 5대 시장 및 통합 포트폴리오의 CAGR, Sharpe Ratio, MDD, Calmar Ratio를 측정하고 개선 효과를 실증한다.

## Acceptance Criteria

### Data & Strategy Signal Quality
- [ ] 31대 전략 전체(`pipeline_result.txt`, `surge_predictions.txt`, `card_factor_predictions.txt`, `lstm_predictions.txt`, `stat_arb_predictions.txt`, `arm_factor_predictions.txt`, `darkpool_predictions.txt` 등)가 결측 없이 정상 유효 점수를 출력할 것.
- [ ] `strategy_data_coverage_report.txt`에서 비정상적인 0% 커버리지 또는 전량 NaN 전략이 0건일 것.

### Portfolio & Execution OMS Integrity
- [ ] `portfolio_allocation.txt` 및 포트폴리오 최적화기가 개별 종목 가중치 상한 및 섹터 제약 조건을 엄격히 준수할 것.
- [ ] OMS 7대 안전 게이트와 트레일링 스탑 계산이 정상 작동할 것.

### Automated Test & Backtest Verification
- [ ] `tests/` 디렉토리 내 단위 및 통합 테스트 스위트가 100% 통과할 것.
- [ ] `generate_report.py`를 통한 GitHub Pages 대시보드(`gh-pages/index.html`)가 오류 없이 정상 생성될 것.
- [ ] 워크포워드 백테스트 결과가 베이스라인 대비 향상된 위험조정 수익률(Sharpe $\ge 1.50$)을 기록할 것.

