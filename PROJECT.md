# Project: Candidate Alpha Factors Expansion & Institutional Integration (Release R186+ / Phase 197)

## Architecture
The system operates as an institutional multi-factor, multi-model automated quantitative trading and execution platform covering 3,379 symbols across 5 major markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000). This project integrates the 6 recommended candidate alpha factor models from `docs/research/new_alpha_factors_feasibility_report.md` into the active production pipeline and backtesting engine:
1. `src/core/`: 6 standalone factor engines subclassing `BaseStrategyEngine` and decorated with `@register_strategy(StrategyMeta(...))` producing continuous scores bounded in `[0.05, 0.95]` with neutral baseline `0.50`:
   - `SM-01`: `StealthAccumulationEngine` (`stealth_accumulation.py`, `stealth_accumulation_score`)
   - `MF-01`: `VPINToxicityEngine` (`vpin_toxicity.py`, `vpin_toxicity_score`)
   - `AD-04`: `MacroStressSpilloverEngine` (`macro_stress_spillover.py`, `macro_stress_spillover_score`)
   - `FM-01`: `SUESURDecayEngine` (`sue_sur_decay.py`, `sue_sur_decay_score`)
   - `SM-05`: `SentimentDivergenceEngine` (`sentiment_divergence.py`, `sentiment_divergence_score`)
   - `FM-02`: `FCFVelocityEngine` (`fcf_velocity.py`, `fcf_velocity_score`)
2. `src/pipeline/strategy_executor.py`: Parallel evaluation via `ThreadPoolExecutor`, `STRATEGY_SCORE_COLUMNS` updated to 44 strategies, `StrategySpec` definitions with exception isolation and fallback handling, and atomic prediction report generation.
3. `src/ai/ensemble_scorer.py`: Strategy catalog expansion to 44 strategies, assignment to `ALPHA_HORIZON_TIERS`, recalibration of `REGIME_WEIGHTS` and `REGIME_2D_WEIGHTS` strictly summing to `1.0000` across all regimes, dynamic score normalization and PCA-ZCA whitening.
4. `src/backtest/historical_stock_universe_backtester.py`: Integration of 44 canonical score columns, closed-form causal historical proxies using strictly past data ($T-1$), zero synthetic row injection (`synthetic_rows == 0`).
5. Dual-tree parity: 100% SHA-256 bit-for-bit parity maintained between `src/` and `trading_system/src/`.
6. Tri-directory synchronization: 9 synchronized benchmark artifacts across `benchmarks/30year/`, `trading_system/result/30year/`, and `trading_system/result/`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | SM-01 Stealth Accumulation | Barclay-Warner medium-tier trade clustering with 10d exponential drift | M1 | Feasibility §2.2 |
| 2 | MF-01 Order Flow Toxicity | Volume-clock adverse selection (VPIN) with BVC volume splitting and crisis de-risking | M1 | Feasibility §2.1 |
| 3 | AD-04 Macro Stress Spillover | Cross-currency FX basis swap acceleration, 5Y sovereign CDS velocity, and stress beta firewall | M1 | Feasibility §2.4 |
| 4 | FM-01 SUE/SUR Memory Decay | 4-quarter SUE & SUR exponential memory decay kernel with statutory filing lag | M1 | Feasibility §2.3 |
| 5 | SM-05 Sentiment Divergence | Retail vs Institutional net flow spread interacted with 14d RSI overextension | M1 | Feasibility §2.2 |
| 6 | FM-02 FCF Yield Velocity/Accel | Floored EV ($EV \ge 0.20 \text{MCAP}$), 1st derivative (velocity) & 2nd derivative (acceleration) of FCF yield | M1 | Feasibility §2.3 |
| 7 | Strategy Executor Integration | Concurrent execution of 44 strategies in `AlphaStrategyExecutor` with `StrategySpec` entries | M1 | Architecture Survey |
| 8 | Prediction Reporter & Disk Output | Atomic text prediction reports and per-market partitions (`<name>_<market>.txt`) | M1 | Architecture Survey |
| 9 | Ensemble Scorer & Regime Weights | 44 strategies across 3 horizon tiers, `REGIME_2D_WEIGHTS` summing strictly to 1.0000 | M1 | Architecture Survey |
| 10 | Strategy Coverage & Orthogonalizer | Dynamic strategy discovery in `StrategyCoverageAnalyzer` and PCA-ZCA whitening | M1 | Architecture Survey |
| 11 | 30-Year Backtester Causal Proxies | Closed-form causal proxies strictly up to $T-1$, `CANONICAL_37_COLUMNS` expanded to 44 | M1 | Architecture Survey |
| 12 | 30-Year Benchmark Walk-Forward | Verified benchmark run: Net CAGR $\ge 98.49\%$, Sharpe $\ge 5.12$, Sortino $\ge 9.62$, MDD $\le -14.00\%$, `synthetic_rows == 0` | M1 | Benchmark Survey |
| 13 | Tri-Directory Sync | Identical 9 artifacts synchronized across `benchmarks/30year/`, `trading_system/result/30year/`, `trading_system/result/` | M1 | Benchmark Survey |
| 14 | Dual-Tree Parity Sync | 100% SHA-256 bit-for-bit parity across all modules between `src/` and `trading_system/src/` | M1 | Benchmark Survey |
| 15 | Unit, E2E & Master Regression Tests | Unit tests for 6 factors, `test_37strategies_e2e.py`, `verify_production_master.py` 100% PASS | M1 | Benchmark Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 6 Candidate Alpha Factors Implementation, Integration & 30-Year Benchmark Validation | Full implementation of SM-01, MF-01, AD-04, FM-01, SM-05, FM-02, pipeline/ensemble integration, 30-year benchmark walk-forward, tri-directory sync, dual-tree parity, and regression testing | none | IN_PROGRESS |

## Interface Contracts
### 1. Alpha Factor Engines (`src/core/`)
- Base class: `BaseStrategyEngine` (`src/core/base_strategy.py`)
- Decorator: `@register_strategy(StrategyMeta(...))` (`src/core/strategy_registry.py`)
- Methods:
  - `compute_scores(prices_dict, fundamentals_dict=None, indicators_df=None, **kwargs) -> pd.DataFrame / ScoreDataFrame`
  - `calculate_scores(symbols=None, prices_dict=None, **kwargs) -> pd.DataFrame`
- Score Column & Values:
  - `stealth_accumulation_score` $\in [0.05, 0.95]$, baseline $0.50$
  - `vpin_toxicity_score` $\in [0.05, 0.95]$, baseline $0.50$
  - `macro_stress_spillover_score` $\in [0.05, 0.95]$, baseline $0.50$
  - `sue_sur_decay_score` $\in [0.05, 0.95]$, baseline $0.50$
  - `sentiment_divergence_score` $\in [0.05, 0.95]$, baseline $0.50$
  - `fcf_velocity_score` $\in [0.05, 0.95]$, baseline $0.50$
- Output text files:
  - `stealth_accumulation_predictions.txt`
  - `vpin_toxicity_predictions.txt`
  - `macro_stress_spillover_predictions.txt`
  - `sue_sur_decay_predictions.txt`
  - `sentiment_divergence_predictions.txt`
  - `fcf_velocity_predictions.txt`

### 2. Strategy Executor (`src/pipeline/strategy_executor.py`)
- `STRATEGY_SCORE_COLUMNS`: Contains all 44 active strategy keys mapped to score columns.
- `_build_default_strategy_specs()`: 44 `StrategySpec` definitions with evaluator closures.
- Exception isolation: Any failing strategy is caught, logged, and filled via `_ensure_complete_strategy_df` with neutral/momentum fallback.

### 3. Ensemble Scorer (`src/ai/ensemble_scorer.py`)
- `ALPHA_HORIZON_TIERS`:
  - `slow`: 14 strategies (added `sue_sur_decay`, `fcf_velocity`)
  - `medium`: 21 strategies (added `stealth_accumulation`, `sentiment_divergence`)
  - `fast`: 9 strategies (added `vpin_toxicity`, `macro_stress_spillover`)
  - Total: 44 strategies
- `REGIME_WEIGHTS` and `REGIME_2D_WEIGHTS`:
  - Reallocated across 44 strategies such that $\sum_{i=1}^{44} w_i = 1.0000$ strictly for every regime.
- `calculate_ensemble_score()` & `combine_predictions()`: Accepts 44 strategy DataFrames, performs cross-sectional score normalization, and PCA-ZCA whitening.

### 4. Backtester (`src/backtest/historical_stock_universe_backtester.py`)
- `CANONICAL_37_COLUMNS` / `CANONICAL_44_COLUMNS`: Contains all 44 strategy score columns.
- `compute_cross_sectional_factor_scores()`: Computes causal historical proxies strictly up to $T-1$, guaranteeing `synthetic_rows == 0`.

### 5. Benchmark Performance Guardrails
- `benchmarks/30year/status.json`:
  - `synthetic_rows: 0` (native int)
  - `metrics.net_cagr_pct >= 98.49`
  - `metrics.sharpe_ratio >= 5.12`
  - `metrics.sortino_ratio >= 9.62`
  - `metrics.max_drawdown_pct >= -14.00` and `<= 0.0`
  - `metrics.active_win_rate_pct >= 93.80`
  - `verification_status: "PASSED"`

## Code Layout
- `src/core/`: Quantitative feature engines (`stealth_accumulation.py`, `vpin_toxicity.py`, `macro_stress_spillover.py`, `sue_sur_decay.py`, `sentiment_divergence.py`, `fcf_velocity.py`)
- `src/pipeline/`: Strategy executor (`strategy_executor.py`), prediction reporter (`prediction_reporter.py`)
- `src/ai/`: Ensemble engine (`ensemble_scorer.py`), factor orthogonalizer (`factor_orthogonalizer.py`)
- `src/analysis/`: Strategy coverage analyzer (`coverage_analyzer.py`), portfolio optimizer (`portfolio_optimizer.py`)
- `src/backtest/`: 30-year backtester (`historical_stock_universe_backtester.py`, `historical_stock_universe_pipeline.py`)
- `trading_system/src/`: Mirrored dual-tree directory (100% SHA-256 parity)
- `benchmarks/30year/`: 30-year official benchmark artifacts (`status.json`, `stock_universe_summary.json`, etc.)
- `trading_system/result/`: Production pipeline and mirrored benchmark artifacts
- `trading_system/result/30year/`: Mirrored 30-year benchmark artifacts
- `tests/`: Pytest regression suites (`test_37strategies_e2e.py`, `verify_production_master.py`, factor unit tests)
