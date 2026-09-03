# Project: 2nd Deep Quantitative Enhancement (v9 Apex Quant Optimization)

## Architecture
- **5 Global Markets**: KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000
- **37-Strategy Multi-Factor Engine**:
  1. XGBoost Regression, 2. Surge Classifier, 3. Lead-Lag (+1d US Lag), 4. VCP Rule, 5. VCP ML, 6. Strict Causal LSTM, 7. Stat-Arb Cointegration, 8. Sector Rotation, 9. RIM Valuation, 10. Event-Driven, 11. Momentum Quality (MQ), 12. Options IV Skew, 13. Order Flow Imbalance, 14. Short-Term Reversal, 15. Analyst Revision Momentum (ARM), 16. Cross-Asset Regime Divergence (CARD), 17. Liquidity Tail Risk (LATR), 18. Inst & Foreign Sector, 19. Supply Chain, 20. NLP Sentiment Catalyst, 21. Factor Neutralized, 22. Vol Targeting, 23. Microstructure, 24. Accruals Quality, 25. Short Squeeze, 26. Value-Up Catalyst, 27. Trend Efficiency, 28. Gamma Squeeze, 29. Insider Buying, 30. Darkpool & HFT Flow, 31. Earnings Tone Drift, 32. Cross-Asset Spillover, 33. Supply Chain GNN, 34. Range Expansion Breakout, 35. Dual Correction, 36. Index Rebalance, 37. Overnight Gap Reversal.
- **Dynamic Scoring & Factor Orthogonalization**:
  - `CrossSectionalScoreNormalizer`: Percentile Rank / Winsorized Gaussian CDF
  - `FactorSuppressionEngine`: Collinearity penalty & single-stage entropy program
  - `FactorOrthogonalizerEngine`: PCA-ZCA whitening & Dual-Consensus Spectral preservation (PC1 & PC2)
  - `EnsembleScoringEngine`: Bessembinder tail convexity, continuous bilinear synergy kernel, 2D regime-adaptive half-life decay
- **Risk & Portfolio Optimization Layer**:
  - `UnifiedPortfolioAllocator`: 4-Model blend (Black-Litterman + HERC + Risk Parity + EVT-CVaR)
  - Dynamic Alpha Half-Life Convergence Speed ($\theta_i^*$) vs Gatheral 3/2-power liquidity impact penalty
  - Volatility-Normalized Asymmetric Leland Dynamic Buffer Bands ($z_{\text{unrealized}} = u_{\text{ret}} / (\sigma \sqrt{5})$)
- **Execution OMS & Microstructure Layer**:
  - `ExecutionOMSEngine`: End-to-end delta rebalancing ($\Delta Q = Q_{\text{target}} - Q_{\text{current}}$)
  - `AlmgrenChrissScheduler`: Optimal execution tranche slicing with `MIDPOINT_PEG` passive routing
  - 8 Safety Gates, Gate 8 Synthetic Inverse Hedge, Slippage Feedback Loop (`trade_logs.db`)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Pipeline Sequence Rectification | Run raw correlation monitoring and factor suppression BEFORE ZCA orthogonalization to ensure collinearity penalties operate on raw signals | M1 | survey_r1 |
| 2 | Dual-Consensus Spectral Whitening | Upgrade PCA-ZCA whitening to preserve both PC1 (Market Trend) and PC2 (Value/Quality) leading eigenvalues | M1 | survey_r1 |
| 3 | Bessembinder Tail Convex Boost | Activate and integrate symmetric Richards/Bessembinder convex power-law scaling in `combine_predictions` for top/bottom decile spread expansion | M1 | survey_r1 |
| 4 | Bilinear Cross-Pillar Synergy Kernel | Replace step-function multi-pillar bonuses with smooth bilinear continuous synergy kernel on mutually exclusive strategy clusters | M1 | survey_r1 |
| 5 | 2D Regime Half-Life Decay | Modulate strategy signal half-lives $\tau_k(R) = \tau_k^{(0)} \cdot \kappa(R)$ by 2D market regime (accelerate in high-vol, persist in low-vol bull) | M1 | survey_r1 |
| 6 | Statistically Calibrated Suppression | Calibrate factor suppression cutoffs $\theta(R, N) = \theta_0(R) + 1.645/\sqrt{N-3}$ and apply Marchenko-Pastur spectral flooring | M1 | survey_r1 |
| 7 | Dynamic Half-Life Convergence ($\theta_i^*$) | Closed-form optimal convergence velocity balancing perishable alpha decay against Gatheral 3/2-power market impact | M2 | survey_r2 |
| 8 | Cash Buffer for Constrained Weight | Route unallocated liquidity-constrained capital to cash buffer rather than distorting other asset weights via re-normalization | M2 | survey_r2 |
| 9 | Volatility-Normalized Leland Buffers | Standardize asymmetric Leland no-trade buffers using continuous Z-scores $z = u_{\text{ret}} / (\sigma \sqrt{5})$ with boundary rebalancing | M2 | survey_r2 |
| 10 | OMS Delta Rebalancing | Enforce $\Delta Q = Q_{\text{target}} - Q_{\text{current}}$ in OMS order planning to prevent redundant re-buying of existing buffer-held positions | M2 | survey_r2 |
| 11 | Almgren-Chriss Slicing & Midpoint Peg | Wire Almgren-Chriss tranche trajectory into OMS order generation with `MIDPOINT_PEG` passive routing to eliminate spread costs | M2 | survey_r2 |
| 12 | 2,183+ Regression Test Suite | Verify 100% pass rate with 0 regressions across all unit and integration tests via `.venv\Scripts\pytest tests/ -v` | M3 | survey_r3 |
| 13 | 5-Market Quantitative Benchmark | Execute simulation across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000 and calculate Net Expected Return, Sharpe, IC, MDD, Turnover, Drag | M3 | survey_r3 |
| 14 | 3-Tier Before/After Comparison Table | Generate authoritative Markdown comparison tables in `reports/quant_benchmark_comparison.md` and project reports | M3 | survey_r3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Alpha Top-Decile Spread & Dynamic Orthogonalization | Features 1, 2, 3, 4, 5, 6: `ensemble_scorer.py`, `factor_orthogonalizer.py`, `factor_suppression.py`, `score_normalizer.py` | none | DONE (120 unit/integration + 26 stress tests passed; gate passed) |
| M2 | Portfolio Allocation Convergence & Leland Buffer Execution | Features 7, 8, 9, 10, 11: `unified_portfolio_allocator.py`, `portfolio_allocator.py`, `oms_engine.py`, `almgren_chriss.py` | M1 | PLANNED |
| M3 | Comprehensive Test Verification & Quantitative Benchmark Table | Features 12, 13, 14: `tests/`, `benchmark_quant_performance.py`, `reports/quant_benchmark_comparison.md` | M1, M2 | PLANNED |

## Interface Contracts
### `FactorSuppressionEngine` ↔ `FactorOrthogonalizerEngine` ↔ `EnsembleScoringEngine`
- Raw score matrix $S \in \mathbb{R}^{N \times K}$ passed to `update_correlation(S)` before whitening.
- Correlation matrix $C_{\text{raw}}$ used to compute suppression penalties $P \in \mathbb{R}^K$.
- Suppressed scores passed to `_pca_zca_symmetric` with `preserve_top_k=2` (PC1 and PC2 eigenvalues preserved).
- Output matrix maintains dimensions, finite values, and valid cross-sectional rankings.

### `UnifiedPortfolioAllocator` ↔ `ExecutionOMSEngine`
- Allocator calculates target weights $w^*_i$ and applies dynamic convergence speed $\theta_i^*$: $w_{t+1, i} = w_{t, i} + \theta_i^* (w^*_i - w_{t, i})$.
- Volatility-normalized Leland buffer checks $w_{t+1, i}$ against $L_i \le w_{t, i} \le U_i$.
- Output dataframe contains `target_weight`, `current_weight`, `delta_weight`, and `target_shares`.
- OMS `generate_order_plan` receives `current_holdings` and executes orders ONLY for non-zero delta quantities $|\Delta Q| > 0$.
- Tranches sliced via `AlmgrenChrissScheduler.compute_trajectory()` with execution tags (`MIDPOINT_PEG`, `AGGRESSIVE_TAKER`).

## Code Layout
- `trading_system/src/ai/ensemble_scorer.py`: Scoring, 2D regime weighting, Bessembinder convexity, synergy kernel, net return calculation
- `trading_system/src/ai/factor_orthogonalizer.py`: PCA-ZCA whitening, dual-consensus spectral preservation
- `trading_system/src/ai/factor_suppression.py`: Factor correlation suppression, dynamic thresholding
- `trading_system/src/ai/score_normalizer.py`: Cross-sectional normalization
- `trading_system/src/risk/unified_portfolio_allocator.py`: 4-Model allocation, half-life convergence, Leland buffers
- `trading_system/src/risk/portfolio_allocator.py`: EVT-CVaR, Ledoit-Wolf shrinkage, Leland bands
- `trading_system/src/execution/oms_engine.py`: Order plan generation, delta rebalancing, safety gates
- `trading_system/src/execution/almgren_chriss.py`: Optimal execution trajectory scheduler
- `trading_system/scripts/benchmark_quant_performance.py`: 5-market benchmarking, metrics, 3-tier Markdown tables
- `tests/`: 2,183 unit and integration tests
