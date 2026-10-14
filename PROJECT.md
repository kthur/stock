# Project: Phase 105 (v112 Production Master, Features F495~F499, Release R121)

## Architecture
- 30-Year Individual Stock Universe Multi-Factor Walk-Forward Simulation (1996~2026) across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
- Modular Layers:
  1. Data & Feature Store Layer: `PointInTimeStockUniverse` & `HistoricalStockUniversePipeline` (`trading_system/src/backtest/historical_stock_universe_pipeline.py`) with dynamic filing lag (KRX 45d/90d, US 40d/60d), survivorship bias defense (listing/delisting cohorts, bankruptcy loss realization), and 20-day rolling ADV calculation.
  2. Alpha Factor Scoring & Orthogonalization Layer: `HistoricalStockUniverseBacktester` (`trading_system/src/backtest/historical_stock_universe_backtester.py`) with vectorized 37-strategy factor extraction, `CrossSectionalScoreNormalizer` (Student-t $\nu=4.0$ & Winsorized Gaussian CDF, inactive 0-score block isolation), and `FactorOrthogonalizerEngine` (PCA-ZCA symmetric whitening, top-2 PC preservation, pairwise covariance with PSD repair, 2D regime dynamic weighting with active factor re-normalization and Bayesian coverage shrinkage).
  3. Institutional Portfolio Optimization & Execution Layer: Multi-stock optimizer with strict single-stock $\le 5.0\%$ cap, single-sector $\le 25.0\%$ cap, dual 200-day SMA trend gating (macro + stock), quarterly (60-day) rebalancing, turnover hysteresis bands (3%) with bypass rules, ADV liquidity participation cap $\le 1.5\%$, Gatheral 3/2-power market impact execution, and statutory market frictions (KRX STT, US SEC/FINRA, brokerage, dynamic half-spread).
  4. Execution Runner, Verification & Documentation Layer: `run_30year_stock_universe_backtest.py`, `verify_30year_stock_universe_backtest.py`, 4 official result artifacts in `trading_system/result/`, comprehensive test suite `tests/test_phase105_stock_universe_backtest.py`, and `AGENTS.md`.

## Feature Inventory
Every feature from the Survey phase appears here with its assigned milestone.
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F495.1 | Point-in-Time (PIT) Stock Universe across 5 markets with historical listing/delisting cohorts | M1 | Survey (Explorer 1) |
| 2 | F495.2 | Survivorship Bias Defense with bankruptcy terminal loss realization | M1 | Survey (Explorer 1) |
| 3 | F495.3 | Dynamic Filing Lag Enforcement (KRX 45d/90d, US 40d/60d) preventing lookahead bias | M1 | Survey (Explorer 1) |
| 4 | F495.4 | 30-Year Multi-Stock Vectorized Feature Store (OHLCV, 20d ADV, fundamentals, sector tags) | M1 | Survey (Explorer 1) |
| 5 | F496.1 | Vectorized 37-Strategy Cross-Sectional Factor Scoring on stock panels | M2 | Survey (Explorer 2) |
| 6 | F496.2 | CrossSectionalScoreNormalizer (Student-t / Winsorized CDF + inactive 0-score block isolation) | M2 | Survey (Explorer 2) |
| 7 | F496.3 | PCA-ZCA Whitening & Gram-Schmidt Orthogonalization (top-2 PC preservation, PSD repair) | M2 | Survey (Explorer 2) |
| 8 | F496.4 | 2D Regime Dynamic Weighting with active weight re-normalization & Bayesian shrinkage | M2 | Survey (Explorer 2) |
| 9 | F497.1 | Multi-Stock Portfolio Optimization with strict single-stock cap <= 5.0% | M3 | Survey (Explorer 3) |
| 10 | F497.2 | Single-Sector Concentration Guardrail <= 25.0% with headroom redistribution | M3 | Survey (Explorer 3) |
| 11 | F497.3 | Dual 200-Day SMA Trend Gating (macro index + stock level) & quarterly 60d rebalancing | M3 | Survey (Explorer 3) |
| 12 | F497.4 | Turnover Hysteresis Band (3%) with fresh entry / full liquidation bypass rules | M3 | Survey (Explorer 3) |
| 13 | F498.1 | ADV Liquidity Participation Cap <= 1.5% | M3 | Survey (Explorer 3) |
| 14 | F498.2 | Gatheral 3/2-Power Market Impact Execution & Realistic Statutory Friction Models | M3 | Survey (Explorer 3) |
| 15 | F499.1 | 30-Year Stock Universe Walk-Forward Runner (run_30year_stock_universe_backtest.py) | M4 | Survey (Explorer 3) |
| 16 | F499.2 | Independent Strict Verification Script (verify_30year_stock_universe_backtest.py) | M4 | Survey (Explorer 3) |
| 17 | F499.3 | 4 Official Result Artifacts in trading_system/result/ (report, summary, annual, crisis) | M4 | Survey (Explorer 3) |
| 18 | F499.4 | Comprehensive Test Suite (tests/test_phase105_stock_universe_backtest.py) | M4 | Survey (Explorer 3) |
| 19 | F499.5 | AGENTS.md Release R121 Documentation | M4 | Survey (Explorer 3) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: PIT Stock Universe & Feature Store (F495) | Point-in-Time universe, survivorship bias defense, dynamic filing lag, 20d ADV feature store | none | DONE |
| 2 | M2: 37-Strategy Scoring & Orthogonalization (F496) | Vectorized 37-factor scoring, score normalizer, PCA-ZCA whitening, 2D regime weighting | M1 | IN_PROGRESS |
| 3 | M3: Multi-Stock Optimizer & Liquidity Execution (F497, F498) | 5% stock cap, 25% sector cap, 200d SMA gating, 1.5% ADV cap, 3/2 market impact, frictions | M1, M2 | PLANNED |
| 4 | M4: Runner, Verification, Artifacts, Tests & Docs (F499) | 30-year runner script, verify script, 4 result artifacts, test suite, AGENTS.md update | M1, M2, M3 | PLANNED |

## Interface Contracts
### historical_stock_universe_pipeline.py (M1) <-> historical_stock_universe_backtester.py (M2, M3)
- `PointInTimeStockUniverse`:
  - `get_active_universe(date: str, market: Optional[str] = None) -> List[str]`: returns list of active symbols at date $t$.
  - `is_delisted(symbol: str, date: str) -> bool`: returns whether symbol has delisted by date $t$.
  - `get_delisting_terminal_loss(symbol: str, date: str) -> float`: returns liquidation salvage value or terminal loss fraction (e.g. -1.0 for bankruptcy).
- `HistoricalStockUniversePipeline`:
  - `get_market_panel(date: str, lookback_days: int = 252) -> pd.DataFrame`: returns multi-index or symbol-keyed DataFrame with OHLCV, 20-day ADV, sector, and causally lagged fundamentals.
  - All fundamental data lagged by statutory delay: KRX 45d/90d, US 40d/60d.
  - Price/volume data causally indexed up to $T-1$.

### historical_stock_universe_backtester.py (M2, M3) <-> run_30year_stock_universe_backtest.py (M4)
- `HistoricalStockUniverseBacktester`:
  - `__init__(config: Optional[TradingConfig] = None, max_stock_weight: float = 0.05, max_sector_weight: float = 0.25, max_adv_participation: float = 0.015, rebalance_freq_days: int = 60)`
  - `run_backtest(start_date: str = '1996-01-01', end_date: str = '2026-08-31') -> Dict[str, Any]`: runs walk-forward backtest.
  - Returns dictionary with:
    - `'summary'`: KPI dictionary (`cagr`, `sharpe`, `sortino`, `max_drawdown`, `calmar`, `active_win_rate`, `total_trades`, `gross_cagr`, `net_cagr`, etc.)
    - `'annual_distribution'`: DataFrame with 31 calendar years (1996~2026) showing annual return, volatility, Sharpe, MDD.
    - `'crisis_breakdown'`: DataFrame with 5 historical crises (1997 IMF, 2000 Dot-com, 2008 GFC, 2020 COVID, 2022 Inflation rate hike) showing duration, benchmark drop, strategy return, and MDD.
    - `'weights_history'`: DataFrame of portfolio weights at each rebalance date, strictly satisfying $\le 5.0\%$ per stock and $\le 25.0\%$ per sector.
    - `'daily_curve'`: Series/DataFrame of daily equity, gross vs net equity, cash ratio, and friction drag.

### verify_30year_stock_universe_backtest.py (M4) <-> Verification Suite
- CLI arguments: `--result-dir trading_system/result --strict`
- Strict assertions:
  1. File Existence & Schema (4 result artifacts)
  2. 31 Annual Distribution Years (1996~2026 unbroken)
  3. 5 Historical Crisis Windows Defense
  4. Single-Stock Weight Cap: $\le 5.0\% + 1e-6$
  5. Single-Sector Weight Cap: $\le 25.0\% + 1e-6$
  6. ADV Liquidity Participation Cap: $\le 1.5\%$
  7. Strict Causality & Dynamic Filing Lag (Zero future leakage)
  8. Survivorship Bias Defense (Delisted cohort loss validation)
  9. Strict KPI Targets:
     - CAGR $\ge 25.0\%$
     - Sharpe $\ge 1.80$
     - Sortino $\ge 2.50$
     - MDD $\ge -18.0\%$ (e.g. $-16\%$ to $-6\%$)
     - Active Rebalance Period Win Rate $\ge 58.0\%$

## Code Layout
- `trading_system/src/backtest/historical_stock_universe_pipeline.py`: Point-in-Time universe & 30-year multi-stock feature store
- `trading_system/src/backtest/historical_stock_universe_backtester.py`: 37-strategy cross-sectional scoring, multi-stock optimizer & liquidity execution
- `trading_system/scripts/run_30year_stock_universe_backtest.py`: 30-year walk-forward runner
- `trading_system/scripts/verify_30year_stock_universe_backtest.py`: Independent strict verification script
- `trading_system/result/`:
  - `quant_benchmark_30year_stock_universe_report.md`
  - `backtest_30year_stock_universe_summary.json`
  - `backtest_30year_stock_universe_annual.csv`
  - `backtest_30year_stock_universe_crisis.csv`
- `tests/test_phase105_stock_universe_backtest.py`: Comprehensive test suite
- `AGENTS.md`: Release R121 documentation
