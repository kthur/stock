# Original User Request

## 2026-08-22T06:05:43Z

<USER_REQUEST>
31대 다변화 전략 주식 자동매매 및 예측 시스템의 종합 진단 보고서에서 도출된 P0(수익률 직접 저해), P1(예측 왜곡), P2(시스템 안정성) 이슈 전반을 전면 수정하고, 단일 통합 테스트 슈트(1,124+ 테스트) 100% 통과 및 파이프라인 무결성을 달성합니다.

Working directory: d:/Finance/code/stock
Integrity mode: demo

## Requirements

### R1. 31대 전략 점수 스케일 정규화 및 앙상블 왜곡 해소
- 31개 전략의 출력 점수(회귀 수익률, 분류 확률, 공적분 Z-Score, 가치평가 할인율 등) 간 스케일 불일치를 해소하기 위해 Cross-Sectional Percentile Rank / Winsorized Z-Score 정규화 엔진을 구축하고 앙상블 스코어러에 적용한다.
- 데이터 결측이나 산출 불가 전략에 대해 임의의 기본값(0.5 등)으로 왜곡하지 않고, 해당 종목에서 해당 전략 가중치를 0으로 배제한 뒤 활성 전략 가중치를 자동 재정규화(Re-normalization)한다.

### R2. 데이터 파이프라인 정밀화 (Filing Lag, 층화 샘플링, Stat-Arb 노이즈 제거)
- 펀더멘탈 데이터의 일률적 60일 지연(Filing Lag)을 시장별 규정(KRX 45일, US 40일) 및 공시 확인 시 즉시 반영 가능한 동적 윈도우로 개편하여 분기 실적 모멘텀을 적시에 반영한다.
- 모델 학습 데이터 샘플링(`prepare_training_data`) 시 단순 `random.sample()`을 제거하고, 시가총액 분위수 및 시장/섹터별 층화 샘플링(Stratified Sampling)을 적용하여 표본 대표성을 확보한다.
- Stat-Arb 모듈에서 공적분 페어가 없을 때 생성되던 인위적인 가짜 BENCHMARK 페어(상관계수 0.85, 베타 1.0) 생성을 완전 제거하고, 통계적으로 유의미한 실제 공적분 신호만 파이프라인에 전달한다.

### R3. 시스템 안정성, 타임아웃 및 예외 처리 강화
- 모듈 최상단의 5초 전역 소켓 타임아웃(`socket.setdefaulttimeout(5)`)을 안전하게 제거하고, yfinance/FRED/ECOS 등 외부 데이터 소스별 개별 적응형 타임아웃 및 지수 백오프 재시도를 적용한다.
- `FallbackMetadataDict` 등 메타데이터 조회 시 무효 티커에 대한 무분별한 NaN 반환 및 다운스트림 NaN 전파를 방지하는 방어적 필터링을 구축한다.
- VIX Override 등 위기 방어 로직이 정상적인 반등 모멘텀을 과도하게 차단하지 않도록 VIX 변화율 및 기간구조(Term Structure)를 고려한 정밀 완충 로직을 적용한다.

### R4. 전수 테스트 및 무결성 검증
- 모든 수정 사항에 대해 `.venv/Scripts/pytest tests/ -v`를 실행하여 기존 1,124+개 테스트 슈트 전체 100% PASS(0 Failures, 0 Errors)를 검증한다.
- 데이터 누수(Lookahead Bias) 및 하위 호환성 침해 여부를 회귀 테스트를 통해 점검한다.

## Acceptance Criteria

### Strategy & Ensemble Quality
- [ ] 31개 전략의 입력 점수가 통일된 분포로 정규화되어 특정 전략의 분산 차이로 인한 앙상블 왜곡이 발생하지 않는다.
- [ ] Stat-Arb 파일 및 앙상블 출력에 가짜 페어 데이터가 전혀 포함되지 않으며 유효한 공적분 페어만 집계된다.
- [ ] Filing lag 시장별 동적 적용 및 층화 샘플링이 작동하여 실적 데이터 반영도와 학습 데이터 대표성이 개선된다.
- [ ] 데이터 결측 전략 발생 시 자동 가중치 재분배가 정상 동작한다.

### Stability & Verification
- [ ] `pytest tests/ -v` 실행 시 전체 테스트가 100% 성공(PASS)한다.
- [ ] 파이프라인 스모크 실행 시 소켓 타임아웃 오류 및 NaN 크래시 없이 정상 완료된다.
</USER_REQUEST>

## 2026-08-22T08:00:05Z

<USER_REQUEST>
Perform an end-to-end quantitative, algorithmic, and architectural audit of the entire stock trading codebase (`d:\Finance\code\stock`) to diagnose all bottlenecks limiting investment returns (Sharpe, Calmar, Net Alpha) and operational stability across 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ), and produce an exhaustive, actionable improvement report with concrete mathematical formulas, code refactor proposals, and prioritized execution steps.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. 31-Strategy Alpha Engine & Predictive Signal Diagnostic
- Audit all 31 alpha and multi-factor strategies (XGBoost regression, Surge classifier, Lead-Lag 2-tier, VCP Rule/ML, Strict Causal LSTM, Stat-Arb cointegration, Sector Rotation, RIM, Event-Driven, MQ Factor, IV Skew, Order Flow Imbalance, Short-Term Reversal, ARM, CARD, LATR, Microstructure, Accruals Quality, Short Squeeze, Value-Up, Trend Efficiency, Gamma Squeeze, Insider Buying, Tone Drift, Darkpool HFT, etc.).
- Identify factor decay, lookahead risks, horizon mismatches (1d~200d), sample weighting biases, feature collinearity, and regime-conditional breakdown.

### R2. Factor Orthogonalization & Dynamic Regime Ensemble Audit
- Examine the `FactorOrthogonalizerEngine` (PCA-ZCA symmetric whitening, Gram-Schmidt decorrelation), `FactorSuppressionEngine` (VIF & 2D regime noise filtering), and `EnsembleScoringEngine`.
- Evaluate how multi-factor signals are combined across 6 macro/market regimes (Bull/Bear/Sideways x High/Low Vol), identifying signal dilution or cancellation issues.

### R3. Portfolio Optimization, Tail Risk Budgeting & Cost Modeling
- Review `PortfolioOptimizer` (HRP, Ledoit-Wolf shrinkage) and `PortfolioAllocator` (EVT-CVaR extreme value tail risk budgeting, Leland no-trade dynamic buffer bands).
- Audit the microstructure transaction cost model (STT tax, SEC fees, bid-ask spread, Kyle's lambda market impact) and slippage feedback loop (`trade_logs.db`) for unrealistic friction over-penalization or under-penalization.

### R4. Pipeline Operations, Concurrency, and Data Ingestion Stability
- Audit `trading_system/run_pipeline.py`, `MarketIndicatorStorage`, `StockPriceDB` (SQLite WAL mode and write mutexes), async fundamental data fetching (60-day filing lag), float32 memory optimizations, and CI/CD GitHub Actions 5-matrix workflow.
- Identify concurrency bottlenecks, rate-limiting risks, data missingness root causes, and pipeline runtime optimization vectors.

### R5. Comprehensive Improvement Report & Actionable Implementation Roadmap
- Produce a detailed, high-quality technical report (`IMPROVEMENT_ROADMAP.md` or comprehensive report) containing:
  1. Executive Summary & Core Bottleneck Assessment
  2. Strategy-by-Strategy Alpha Enhancement Proposals (with explicit mathematical formulas & feature additions)
  3. Ensemble & Portfolio Construction Enhancements
  4. Operational Architecture & Execution OMS Optimizations
  5. Prioritized Action Matrix (Critical / High / Medium / Low) with estimated Sharpe/return impact and implementation complexity.

## Acceptance Criteria

### Diagnostic Depth & Coverage
- [ ] Complete diagnostic coverage of all 31 strategies and system layers without omitting any core factor or execution component.
- [ ] Explicit identification of return drags (e.g. signal dilution, friction miscalibration, regime lag, missing data handling).

### Technical Rigor & Actionability
- [ ] Every proposed improvement includes clear technical rationale, concrete mathematical formulation or pseudocode, and targeted files.
- [ ] Preserves all existing system constraints (KST timezone, 5-market multi-asset universe, SQLite WAL integrity, 6 OMS safety gates).
- [ ] Generates a structured markdown report ready for implementation by engineering and quant teams.
</USER_REQUEST>
