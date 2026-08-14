# Project: Stock Trading System — 31-Factor Alpha & 2D Regime Dynamic Sharpe Optimization

## Architecture
- **Data & Ingestion Layer**: `StockPriceDB` (SQLite WAL mutex), `MarketIndicatorStorage`, `EarningsDataFetcher` (60d filing lag).
- **Strategy Alpha Engines (31 Strategies)**: `src/core/` and `src/ai/` implementing `BaseStrategyEngine`, unified via `StrategyRegistry` and `ml_strategy_adapters.py`.
- **Factor Neutralization & Orthogonalization**: `src/core/multi_factor_neutralizer.py` (Fama-French 5-Factor QR residualization), `src/ai/factor_orthogonalizer.py` (PCA ZCA whitening & Gram-Schmidt), `src/ai/regime_factor_suppression.py` (cluster noise suppression).
- **2D Market Regime & Dynamic Ensemble Engine**: `src/analysis/regime_detector.py` (10-feature GMM, 6 combo states, fast VIX > 30 / S&P crash overrides), `src/ai/ensemble_scorer.py` (Exponential Sharpe Multipliers, adaptive EMA smoothing, Almgren-Chriss microstructure cost models).
- **Portfolio Optimization & Execution OMS**: `src/strategy/quad_factor_optimizer.py`, `src/portfolio/allocator.py` (HRP, Risk Parity, Ledoit-Wolf shrinkage), `trading_system/run_pipeline.py`, `trading_system/generate_report.py` (GitHub Pages `index.html`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Multi-Factor Neutralizer Interface & Imputation | Fix argument binding, column naming (`factor_neutralized_score`), and median imputation for fundamentals in `multi_factor_neutralizer.py` & `run_pipeline.py` | M1 | ORIGINAL_REQUEST §R1 |
| F2 | Fama-French 5-Factor Pure Alpha QR Residualization | Cross-sectional QR decomposition $(I - Q Q^T)y$ across Size, Value, Profitability, Investment, Momentum | M1 | ORIGINAL_REQUEST §R1 |
| F3 | Pure Alpha $|\rho| < 0.15$ Hard SLA Gate | Post-condition verification and secondary Gram-Schmidt deflation ensuring $|\rho| < 0.15$ unconditionally | M1 | ORIGINAL_REQUEST §R1 |
| F4 | Strategy Alpha Precision & Noise Filtering | Fine-tune class balancing, embargoes, and signal thresholds for Surge, VCP, Stat-Arb, Sector Rotation | M1 | ORIGINAL_REQUEST §R1 |
| F5 | 2D Regime Dynamic Exponential Sharpe Multipliers | $w_i = \text{base\_w}_i \cdot \exp(\gamma \cdot \text{clip}(\text{Sharpe}_i, -L, L))$ with underperformance pruning ($\text{Sharpe} < -0.50$) | M2 | ORIGINAL_REQUEST §R2 |
| F6 | Adaptive EMA Smoothing & Downside Risk Defense | $\alpha_{\text{eff}} = 0.2$ in steady state, $\alpha_{\text{eff}} = 1.0$ on regime shift; power ratio damping ($\le 20.0$) | M2 | ORIGINAL_REQUEST §R2 |
| F7 | Microstructure Transaction Cost Deduction | Deduct STT/SEC tax, dynamic bid-ask spread, and Almgren-Chriss market impact ($Q = 50\text{M KRW} / 50\text{k USD}$) | M2 | ORIGINAL_REQUEST §R2 |
| F8 | Comparative Rolling Backtest Verification | Verify Sharpe, annualized return, and MDD across 3,379 symbols via `compare_backtests.py` | M3 | ORIGINAL_REQUEST §R3 |
| F9 | Pytest Full Regression (1,554+ Tests 100% Pass) | Comprehensive execution of all unit, integration, and empirical stress tests in `tests/` and `trading_system/tests/` | M3 | ORIGINAL_REQUEST §R3 |
| F10 | Pipeline Execution & GitHub Pages Report Update | End-to-end `run_pipeline.py` validation, prediction files, coverage reports, and `index.html` generation | M3 | ORIGINAL_REQUEST §R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 31-Strategy Alpha Precision & Pure Alpha Neutralization | F1, F2, F3, F4: Fix Strategy 21 interface, implement QR residualization, secondary deflation gate ($|\rho| < 0.15$), noise filter refinement | none | DONE |
| M2 | 2D Regime Dynamic Weights & Exponential Sharpe Multiplier | F5, F6, F7: Optimize Exponential Sharpe weighting, adaptive EMA smoothing, power damping, microstructure friction | M1 | DONE |
| M3 | Backtest Verification, Full Pytest Regression & Pipeline Validation | F8, F9, F10: Run comparative rolling backtests, 1,554+ pytest suite 100% PASS, execute `run_pipeline.py` & verify `index.html` | M2 | IN_PROGRESS |

## Interface Contracts
### `MultiFactorNeutralizerEngine` ↔ `run_pipeline.py` / `EnsembleScoringEngine`
- `compute_scores(prices_dict: dict | pd.DataFrame, **kwargs) -> pd.DataFrame`:
  - Input: `prices_dict` (symbol -> DataFrame) or `universe` (DataFrame with fundamentals).
  - Output DataFrame columns: `['symbol', 'factor_neutralized_score', 'neutralized_score', 'smb_exposure', 'hml_exposure', 'rmw_exposure', 'cma_exposure', 'umd_exposure']`.
  - Guarantee: $\max_k |\rho(f_k, \text{factor\_neutralized\_score})| < 0.15$.
  - Fallback: Deterministic momentum residualization when raw scores are absent; median imputation per market for missing fundamentals.

### `EnsembleScoringEngine` ↔ `RegimeDetector` & `FactorOrthogonalizerEngine`
- `score_universe(all_predictions: dict, regime_state: str, rolling_sharpes: dict) -> pd.DataFrame`:
  - Input: 31 strategy predictions, 2D regime combo state (`BEAR_LOW_VOL`, etc.), rolling Sharpe dict.
  - Output: Ensembled net alpha scores after Exponential Sharpe weighting, PCA ZCA orthogonalization, cluster suppression, and microstructure transaction costs.

## Code Layout
- `trading_system/src/core/multi_factor_neutralizer.py`: Fama-French 5-Factor QR residualization & pure alpha engine.
- `trading_system/src/ai/factor_orthogonalizer.py`: PCA ZCA symmetric whitening & Modified Gram-Schmidt decorrelation.
- `trading_system/src/ai/regime_factor_suppression.py`: Cluster noise suppression across 5 strategy families.
- `trading_system/src/ai/ensemble_scorer.py`: 31-strategy 2D regime dynamic ensemble scorer.
- `trading_system/src/analysis/regime_detector.py`: 2D GMM Market Regime Detector with fast shock overrides.
- `trading_system/run_pipeline.py`: Master pipeline orchestration.
- `trading_system/generate_report.py`: GitHub Pages `index.html` report compiler.
- `tests/`: 730 unit, integration, and stress tests.
- `trading_system/tests/`: 824 pipeline and component tests.
