## 2026-09-03T00:48:12Z

You are Explorer Track B for the 37-Strategy Trading System Integrity & Operational Audit.
Your working directory is: d:\Finance\code\stock\.agents\explorer_track_b
Make sure to initialize your BRIEFING.md, progress.md, and write your final findings to d:\Finance\code\stock\.agents\explorer_track_b\audit_report.md and handoff.md.

Read the authoritative user request at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (header ## 2026-09-03T00:46:54Z).

Scope of Track B:
Strategies 20-37, Score Normalization, ZCA Whitening, Suppression & Dynamic Ensemble:
1. Strategies 20-37 Logic & Data Ingestion:
   - Strategy 20: NLP Sentiment Catalyst (`src/core/llm_sentiment_engine.py`)
   - Strategy 21: Factor Neutralized (`src/core/factor_neutralized.py`)
   - Strategy 22: Dynamic Volatility Targeting (`src/core/vol_target.py`)
   - Strategy 23: Microstructure Imbalance (`src/core/microstructure.py`)
   - Strategy 24: Accruals Quality Anomaly (`src/core/accruals_quality.py`)
   - Strategy 25: Short Squeeze & Days-to-Cover (`src/core/short_squeeze.py`)
   - Strategy 26: Value-Up & Shareholder Yield (`src/core/value_up.py`)
   - Strategy 27: Kaufman Trend Efficiency (`src/core/trend_efficiency.py`)
   - Strategy 28: Gamma Squeeze (`src/core/gamma_squeeze.py`)
   - Strategy 29: Insider Buying (`src/core/insider_buying.py`)
   - Strategy 30: Darkpool & HFT Flow (`src/core/darkpool_tracker.py`)
   - Strategy 31: Earnings Tone Drift (`src/core/tone_drift.py`)
   - Strategy 32: Cross-Asset Spillover Momentum (`src/core/cross_asset_spillover.py`)
   - Strategy 33: Supply Chain GNN (`src/core/supply_chain_gnn.py`)
   - Strategy 34: Range Expansion Breakout (`src/core/range_expansion_breakout.py`)
   - Strategy 35: Dual Correction (`src/core/dual_correction.py` or inspect location)
   - Strategy 36: Index Rebalance Structural Flow (`src/core/index_rebalance.py` or inspect location)
   - Strategy 37: Overnight Gap Reversal (`src/core/overnight_gap.py` or inspect location)
2. Normalization, Orthogonalization, Suppression & Ensemble Scoring:
   - `src/ai/score_normalizer.py` (CrossSectionalScoreNormalizer: Percentile Rank vs Winsorized Gaussian CDF [0, 1])
   - `src/ai/factor_orthogonalizer.py` (FactorOrthogonalizerEngine: PCA-ZCA symmetric whitening & Gram-Schmidt decorrelation)
   - `src/ai/factor_suppression.py` (FactorSuppressionEngine: VIF & 2D regime noise suppression)
   - `src/ai/ensemble_scorer.py` (EnsembleScoringEngine: 37-strategy dynamic weights, 1D/2D regime weights matrix, missing strategy zero-weighting, micro-cost deduction)
   - `src/analysis/coverage_analyzer.py` (StrategyCoverageAnalyzer: 37-strategy data coverage and missingness)

Thoroughly examine the actual source code for:
- 37-strategy weight matrix normalization: verify whether weight vectors across all 1D and 2D regimes strictly sum to 1.0000 and cover all 37 strategies without missing or stale keys.
- ZCA whitening numerical stability: condition number checking, singular covariance handling, regularizing epsilon, eigenvalue thresholding.
- CrossSectionalScoreNormalizer: behavior under sparse universes (< 5 stocks), all-identical scores, extreme outliers, NaN handling.
- Missingness zero-weighting & renormalization: verify mathematical correctness when strategies have missing data for specific symbols.
- Microstructure friction costs deduction: STT (KRX), SEC fee (US), half-spread, and Gatheral 3/2 power market impact deduction order and scaling.

In your final report `audit_report.md`:
Structure each issue as:
[현황 및 문제점] (Cite exact file path, class/function, line numbers, and actual code snippet)
[정량적/공학적 개선 방안] (Mathematical/logical rationale, proposed algorithmic fix)
[수정 대상 파일] (Exact file and function)
[검증 방안] (Targeted unit/integration test design and acceptance criteria)

Prioritize issues by Critical / High / Medium. Send message when complete.
