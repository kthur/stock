# Project: Alpha & Return Maximization (Stock Trading System)

## Architecture
The stock trading system operates across 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ) with an institutional multi-factor engine, dynamic 2D/3D market regime ensemble, robust portfolio optimization, and an Execution OMS with precision timing engines.

```
[Market Data / Global Indicators / Fundamentals]
                       │
                       ▼
         [34-Strategy Multi-Factor Engine]
         (Core AI + Momentum + Valuation + Reversal + Flow/Micro + 3 New High-Alpha Engines)
                       │
                       ▼
       [CrossSectionalScoreNormalizer] ──► [FactorOrthogonalizer (PCA-ZCA)]
                       │
                       ▼
       [EnsembleScoringEngine] (Dynamic 2D/3D Regime Weights & Synergy Boosting)
                       │
                       ▼
       [Microstructure Cost Model] ──► Net Expected Return
                       │
                       ▼
  [Portfolio Optimization] (HRP, Black-Litterman, EVT-CVaR, Fractional Kelly, Leland Bands)
                       │
                       ▼
  [Execution OMS Engine] (Confluence Entry, Scale-In Pyramiding, 4-tier Trailing Stop, Shock Exits)
                       │
                       ▼
  [Pipeline Outputs & Reports] (trade_logs.db, ensemble_predictions.txt, GitHub Pages)
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Cross-Asset Spillover Momentum | Macro impulse & lead-lag spillover from global drivers (USD/KRW, TNX, WTI, Gold, DXY, VIX, SOX, S&P) to domestic sectors | M1 | Survey (R1) [DONE] |
| 2 | Supply Chain GNN & Sector Flow | 2-hop graph message passing across global anchor leaders & suppliers with bullwhip shock amplification and institutional sector flow acceleration | M1 | Survey (R1) [DONE] |
| 3 | Intraday Volatility Breakout | NR7 / BB bandwidth squeeze precursor + range expansion trigger (REF >= 1.5) + relative volume (RVOL >= 1.8) + close location value | M1 | Survey (R1) [DONE] |
| 4 | StrategyRegistry Registration | Inherit from BaseStrategyEngine, register via StrategyMeta, auto-discovery in core modules | M1 | Survey (R1) [DONE] |
| 5 | EnsembleScoringEngine Integration | Register 3 new strategies into ALPHA_HORIZON_TIERS, REGIME_2D_WEIGHTS, MACRO_WEIGHT_MODIFIERS, strategy_cols | M2 | Survey (R2) |
| 6 | Normalization & Orthogonalization | Validate CrossSectionalScoreNormalizer, PCA-ZCA whitening, and VIF suppression with 34 strategies | M2 | Survey (R2) |
| 7 | 2D/3D Regime Weight Rebalancing | 6 2D regimes (BULL/SIDEWAYS/BEAR x LOW/HIGH VOL) + 5 3D macro modifiers with strict 1.0 weight sums and convex synergy boosting | M2 | Survey (R2) |
| 8 | Portfolio Optimization Verification | Validate HRP (Hierarchical Risk Parity), Black-Litterman with regime views, Ledoit-Wolf shrinkage, EVT-CVaR, and Fractional Kelly | M3 | Survey (R3) |
| 9 | Precision Net Return & Costs | Vectorized microstructure transaction cost deduction (STT tax, dynamic spread, Kyle impact, horizon amortization) | M3 | Survey (R3) |
| 10 | Leland No-Trade Buffer Bands | Suppress sub-threshold portfolio churn while bypassing new entries and complete liquidations | M3 | Survey (R3) |
| 11 | OMS Precision Timing Engines | Confluence Entry (65% hurdle), 3-tier Scale-In Pyramiding, 4-tier Trailing Stop with 2D regime matrix, Signal Exhaustion, Order Flow Shock, Time-Stop | M4 | Survey (R4) |
| 12 | Pipeline OMS Order Generation | Connect top-20 ensemble picks to generate_order_plan with real price enrichment and SQLite WAL persistence in trade_logs.db | M4 | Survey (R4) |
| 13 | High-Alpha Unit & Integration Tests | Create comprehensive tests for 3 new strategies (test_high_alpha_strategies.py) covering normal inputs, edge cases, missing data fallbacks | M5 | Survey (R5) |
| 14 | Full Test Suite 100% Pass | Verify all 1,790+ tests pass with zero failures via `$env:PYTHONPATH="trading_system;trading_system/src;."; .venv\Scripts\pytest.exe tests/ -v` | M5 | Survey (R5) |
| 15 | GitHub Actions Workflow Alignment | Ensure Daily Pipeline workflow matrix, pytest CI, and artifact generation operate seamlessly | M5 | Survey (R5) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | High-Alpha Strategy Engines | Implement Cross-Asset Spillover, Supply Chain GNN, Range Expansion Breakout, register in StrategyRegistry | none | DONE |
| M2 | Ensemble Meta-Learner & Regimes | Integrate 3 new strategies into EnsembleScoringEngine, normalize, orthogonalize, regime weights | M1 | DONE |
| M3 | Portfolio Optimization & Costs | Verify HRP, Black-Litterman, EVT-CVaR, Fractional Kelly, Leland buffers, net return costs | M2 | DONE |
| M4 | OMS Timing & Pipeline Wiring | Verify OMS precision timing engines, connect run_pipeline.py execution and trade_logs.db | M3 | DONE |
| M5 | Test Integrity & E2E Verification | Create test_high_alpha_strategies.py, run full 1,790+ test suite, verify 100% pass & GHA alignment | M4 | IN_PROGRESS |

## Interface Contracts
### BaseStrategyEngine ↔ StrategyRegistry
```python
class BaseStrategyEngine(ABC):
    @abstractmethod
    def compute_scores(self, prices_dict: Dict[str, pd.DataFrame],
                       fundamentals_dict: Optional[Dict[str, Dict]] = None,
                       indicators_df: Optional[pd.DataFrame] = None,
                       **kwargs) -> pd.DataFrame:
        """Returns DataFrame indexed by symbol with score in [0.0, 1.0]."""
```

### EnsembleScoringEngine ↔ StrategyRegistry
- EnsembleScoringEngine dynamically discovers all registered strategies via `StrategyRegistry.get_all_ids()`.
- Strategy columns mapped via `strategy_cols` dictionary.
- All scores normalized to $[0.0, 1.0]$ via `CrossSectionalScoreNormalizer`.

### PortfolioAllocator ↔ ExecutionOMSEngine
- Portfolio weights converted to target share quantities.
- Leland dynamic buffer bands applied to filter turnover: $|w_{\text{target}} - w_{\text{current}}| > \Delta_i$.
- ExecutionOMSEngine processes orders through 7 safety gates, Confluence Entry, and Almgren-Chriss sizing.

## Code Layout
- Strategy implementations: `trading_system/src/core/`
  - `trading_system/src/core/cross_asset_spillover.py`
  - `trading_system/src/core/supply_chain_gnn.py`
  - `trading_system/src/core/range_expansion_breakout.py`
  - `trading_system/src/core/base_strategy.py`
  - `trading_system/src/core/strategy_registry.py`
- AI & Ensemble: `trading_system/src/ai/`
  - `trading_system/src/ai/ensemble_scorer.py`
  - `trading_system/src/ai/score_normalizer.py`
  - `trading_system/src/ai/factor_orthogonalizer.py`
  - `trading_system/src/ai/factor_suppression.py`
- Portfolio & Risk: `trading_system/src/analysis/`, `trading_system/src/risk/`
  - `trading_system/src/analysis/portfolio_optimizer.py`
  - `trading_system/src/risk/portfolio_allocator.py`
  - `trading_system/src/risk/position_sizing.py`
- Execution & OMS: `trading_system/src/execution/`
  - `trading_system/src/execution/oms_engine.py`
  - `trading_system/src/execution/order_manager.py`
- Pipeline Orchestration: `trading_system/run_pipeline.py`
- Tests: `tests/`
