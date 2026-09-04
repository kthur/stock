# Scope: Phase 4 Quantitative Trading System Enhancement

## Architecture
- **Signal Quality & Alpha Spread (R1)**: `src/ai/ensemble_scorer.py`, `src/ai/score_normalizer.py`, `src/ai/factor_orthogonalizer.py`, `src/ai/factor_suppression.py`, `src/ai/prediction_model.py`.
- **Portfolio Allocation & Execution (R2)**: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `src/core/fast_lob_engine.py`, `src/execution/almgren_chriss.py`, `src/execution/turnover_optimizer.py`, `src/execution/slippage_feedback.py`.
- **Benchmark Evaluation & Reports (R3)**: `trading_system/scripts/benchmark_phase4_quant_performance.py`, `reports/quant_benchmark_comparison_phase4.md`, `trading_system/result/quant_benchmark_comparison_phase4.md`, `reports/quant_benchmark_comparison.md`.
- **Testing & Verification**: Single unified `tests/` directory with 2,295+ baseline tests + new Phase 4 unit/integration tests.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F21 | Top-Decile Spread 0.833 Alpha Ceiling Unlock | Remove premature [-0.5, 0.5] clipping before power expansion in `combine_predictions` to restore top 5% convexity | M1 | Explorer 2 / ORIGINAL_REQUEST R1 |
| F22 | NaN-Aware & Softplus Smooth Convex Boost | Use asset's own mean rather than 0.0 for NaNs and replace Heaviside step at 0.60 with continuous sigmoid/softplus gate | M1 | Explorer 2 / ORIGINAL_REQUEST R1 |
| F23 | Tri-Linear Synergy Kernel & Full 6-Regime Coupling | Add tri-linear confluence ($\Xi_{tri}$) and differentiate LOW_VOL vs HIGH_VOL across all 6 regimes in `compute_bilinear_cross_pillar_synergy` | M1 | Explorer 2 / ORIGINAL_REQUEST R1 |
| F24 | Sideways 2D Regime Weight Rebalancing | Trim whipsaw momentum false breakouts (surge, vcp_ml) and reallocate to stat_arb, dual_correction, reversal, vol_target in sideways regimes | M1 | Explorer 2 / ORIGINAL_REQUEST R1 |
| F25 | Single-Stock KER Dynamic Alpha Switching | Activate `apply_ker_dynamic_alpha_switching` in `combine_predictions` to tilt trend vs reversal based on Kaufman efficiency | M1 | Explorer 2 / ORIGINAL_REQUEST R1 |
| F26 | Strategy-Class Asymmetric Half-Life Filtering | Accelerate decay for momentum in sideways regimes (tau * 0.50) while extending in bull regimes (tau * 1.35) in `get_regime_adaptive_half_lives` | M1 | Explorer 2 / ORIGINAL_REQUEST R1 |
| F27 | Regime-Adaptive Bessembinder Tail Thresholds | Parameterize `u_thresh` by 2D regime (0.45 in Bull Low Vol to 0.70 in Sideways High Vol) in Bessembinder convex scaling | M1 | Explorer 2 / ORIGINAL_REQUEST R1 |
| F28 | Downside Semi-Covariance (Sortino) EVT-CVaR Optimization | Blend `compute_downside_semi_cov` into `calculate_cvar_weights` to penalize downside risk while preserving upside momentum | M2 | Explorer 3 / ORIGINAL_REQUEST R2 |
| F29 | Dynamic Model Conviction & Return-Dispersion Blending | Modulate BL vs HERC/CVaR blend dynamically based on cross-sectional alpha dispersion in `optimize_multi_model_blend` | M2 | Explorer 3 / ORIGINAL_REQUEST R2 |
| F30 | Market-Specific STT & Fee Aware Leland Buffers | Adapt Leland buffer cost sizing by asset/market (25 bps KRX for STT, 3.5-8 bps US) to suppress Korean churn by 35%+ | M2 | Explorer 3 / ORIGINAL_REQUEST R2 |
| F31 | Multi-Tier L2 OBI & Micro-Price Pegging | Enhance `calculate_peg_limit_price` with volume-weighted micro-price and composite multi-tier OBI (1, 5, 10 levels) | M2 | Explorer 3 / ORIGINAL_REQUEST R2 |
| F32 | Hawkes Arrival Intensity Adverse Selection Gating | Gate primary maker leg allocations in `SmartOrderRouter.route_order` when Hawkes arrival intensity spikes | M2 | Explorer 3 / ORIGINAL_REQUEST R2 |
| F33 | Closed-Loop Empirical Slippage Feedback Scaling | Dynamically scale Gatheral impact coefficient $\kappa_{\text{eff}}$ using realized execution slippage from `trade_logs.db` | M2 | Explorer 3 / ORIGINAL_REQUEST R2 |
| F34 | Phase 4 Benchmark Performance Engine & Reports | Build `benchmark_phase4_quant_performance.py` and generate comprehensive comparison tables for all 5 markets across Phase 3 vs Phase 4 | M3 | Explorer 1 / ORIGINAL_REQUEST R3 |
| F35 | Full Test Suite (2,295+) & Phase 4 Verification | Ensure 100% test pass on all existing 2,295+ tests and new Phase 4 test suite, with forensic audit verification | M4 | ORIGINAL_REQUEST Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 37-Strategy Dynamic Signal Quality & Top Alpha (R1) | F21, F22, F23, F24, F25, F26, F27 | none | DONE |
| M2 | Portfolio Allocation & Execution Friction Optimization (R2) | F28, F29, F30, F31, F32, F33 | M1 | IN_PROGRESS |
| M3 | Benchmark Engine & Multi-Market Reports (R3) | F34 | M1, M2 | PLANNED |
| M4 | 100% Test Suite Pass & Forensic Integrity Audit | F35 | M1, M2, M3 | PLANNED |

## Interface Contracts
### `ensemble_scorer.py` ↔ Pipeline
- `combine_predictions`: Maintains backward-compatible signatures; returns DataFrame with `ensemble_score`, `expected_net_return`, `confidence`.
- `apply_top_decile_convex_boost`: Smooth sigmoid gating preserves input Series index and bounds within [0.0, 1.0].
- `REGIME_2D_WEIGHTS`: Sum of all 37 strategy weights strictly equals 1.0000 across all regimes.

### `unified_portfolio_allocator.py` ↔ OMS
- `calculate_cvar_weights`: Defaults `use_downside_semi_cov=True`, `semi_cov_weight=0.35`, preserving existing arguments.
- `apply_leland_no_trade_buffers`: Retains default parameter behavior; accepts optional `symbols` or `asset_cost_bps`.
- `calculate_peg_limit_price`: Retains all existing parameters and defaults, adding optional `micro_price` and `multi_obi`.
