# Test Suite Inventory & Execution Readiness: 6th System Improvements (V6-01 ~ V6-35)

**Document Date**: 2026-08-22  
**Test Suite Lead**: `test_writer_gen2` (E2E & Regression Test Suite Lead)  
**Target Codebase**: `kthur/stock` (`d:\Finance\code\stock`)  
**Status**: ✅ **TEST SUITE READY — 100% PASS (45/45 TESTS PASSED)**

---

## 1. Test Runner Command

To execute the complete 4-Tier test suite covering all 35 improvements (V6-01 ~ V6-35):

```bash
# Run the complete 4-tier V6 regression test suite
.venv\Scripts\python.exe -m pytest tests/test_v6_improvements.py -v

# Quiet mode
.venv\Scripts\python.exe -m pytest tests/test_v6_improvements.py -q
```

---

## 2. Test Architecture & 4-Tier Systematic Structure

The test suite is structured across 4 systematic tiers to guarantee exhaustive unit, boundary, interaction, and end-to-end multi-market coverage:

| Tier | Category | Test Class / Count | Scope & Focus |
|---|---|---|---|
| **Tier 1** | **Direct Feature Tests** | `TestTier1DirectFeatures` (35 Tests) | 1:1 direct verification of each individual fix (V6-01 through V6-35) across AI/ML, Portfolio, 31 Strategies, Execution OMS, and Pipeline Infrastructure. |
| **Tier 2** | **Boundary & Corner Cases** | `TestTier2BoundaryAndCornerCases` (5 Tests) | Degenerate $N=1$ single-stock cross-sections, extreme FX volatility ($\ge 2000$ USD/KRW), full portfolio liquidation ($w_{\text{targ}}=0$), zero/single-share slicing in Almgren-Chriss, and singular collinear covariance matrices in Black-Litterman. |
| **Tier 3** | **Cross-Feature Interactions** | `TestTier3CrossFeatureInteractions` (3 Tests) | Hierarchical Risk Parity (HRP) feeding into Leland dynamic buffer bands, 2D market regime interacting with exponential decay filtering & factor suppression, and Execution OMS FX conversion with Almgren-Chriss & Gate 7 net-alpha hurdles. |
| **Tier 4** | **End-to-End Multi-Market Realistic Workflows** | `TestTier4EndToEndRealisticWorkflows` (2 Tests) | Full 5-market multi-asset pipeline simulation (KOSPI, KOSDAQ, S&P 500, NASDAQ, Russell 2000) under decoupled regimes, and GitHub Pages release JSON snapshot artifact generation. |

---

## 3. Comprehensive Test Inventory Checklist (V6-01 ~ V6-35)

### Domain 1: AI/ML & Prediction Integrity (V6-01 ~ V6-08)
- [x] **V6-01** (`test_v6_01_lstm_training_target_transform_sharpe_homomorphism`): Verifies `_prepare_lstm_data` applies `transform_sharpe` to ensure log1p target homomorphism across tree models and causal LSTM regressors.
- [x] **V6-02** (`test_v6_02_exponential_decay_filter_column_alias_mapping`): Verifies `apply_exponential_decay_filter` maps score column aliases to canonical half-life keys across fast (`microstructure`), slow (`rim_valuation`), and metadata columns.
- [x] **V6-03** (`test_v6_03_dual_regime_weights_decoupling_and_suppression`): Verifies `combine_predictions` applies linear US weights and decoupled Korean suppression penalty ratios without squaring or cross-contamination.
- [x] **V6-04** (`test_v6_04_predict_lstm_market_partitioned_evaluation`): Verifies `predict_lstm` partitions symbols by market and routes evaluation through market-specific LSTM models.
- [x] **V6-05** (`test_v6_05_lead_lag_fallback_1day_normalized_scaling`): Verifies `predict_lead_lag` fallback computes 1-day return mapped into $[0.05, 0.95]$ rather than multi-year cumulative gains.
- [x] **V6-06** (`test_v6_06_optuna_bear_utility_and_alpha_decay_bounds`): Verifies Optuna switches to quadratic utility $\mu - 0.5 \lambda \sigma^2$ under negative expected returns, and `AlphaDecayTracker` applies iterative bounded simplex projection.
- [x] **V6-07** (`test_v6_07_lead_lag_hpo_evaluates_k_symbols_and_validation_split`): Verifies `tune_strategy_3_lead_lag` evaluates all $K = \min(\text{leaders\_count}, N)$ symbols and measures out-of-sample persistence on validation splits.
- [x] **V6-08** (`test_v6_08_meta_ensemble_learner_column_permutation_invariance`): Verifies `MetaEnsembleLearner` projects weights by feature names and reindexes DataFrames to prevent column permutation corruption.

### Domain 2: Portfolio & Risk Engineering (V6-09 ~ V6-16)
- [x] **V6-09** (`test_v6_09_leland_buffer_band_new_entry_and_full_exit_bypass`): Verifies `compute_portfolio_rebalance` scales $\delta_i \le 0.40 w_{\text{targ}}$ for small targets and bypasses buffer suppression for fresh entries ($w_{\text{curr}}=0$) and full liquidations ($w_{\text{targ}}=0$).
- [x] **V6-10** (`test_v6_10_black_litterman_c1_smoothness_under_all_negative_excess`): Verifies Black-Litterman optimization achieves $C^1$ smoothness and converges without gradient explosion when excess returns are negative.
- [x] **V6-11** (`test_v6_11_evt_pot_cvar_threshold_ceiling_and_regular_shape`): Verifies `estimate_evt_cvar` caps threshold $u \le q_\alpha$ and clamps shape parameter $\xi \in [-0.50, 0.50]$.
- [x] **V6-12** (`test_v6_12_rockafellar_uryasev_cvar_pseudo_huber_and_vector_constraints`): Verifies `optimize_rockafellar_uryasev_cvar` uses Pseudo-Huber smoothing and vectorized CVaR constraints for robust SLSQP convergence.
- [x] **V6-13** (`test_v6_13_crisis_detector_recovery_reset_and_watch_haircut`): Verifies `CrisisDetector` auto-resets recovery mode after 20 days and applies defensive 0.70 position haircut upon re-entering WATCH.
- [x] **V6-14** (`test_v6_14_coverage_analyzer_modal_frequency_missing_reason`): Verifies `StrategyCoverageAnalyzer` extracts the statistical mode of missing reasons rather than dictionary insertion order.
- [x] **V6-15** (`test_v6_15_downside_semi_cov_diagonal_shrinkage_preserves_hedges`): Verifies `compute_downside_semi_cov` uses diagonal variance target $\mathbf{T} = \text{diag}(\Sigma^-)$, preserving negative covariance of hedging assets.
- [x] **V6-16** (`test_v6_16_rmt_dynamic_noise_variance_estimation`): Verifies `denoise_covariance_marchenko_pastur` estimates residual noise variance $\sigma^2$ dynamically from non-market eigenvalues.

### Domain 3: 31 Strategy Engines & Data Layer (V6-17 ~ V6-24)
- [x] **V6-17** (`test_v6_17_rim_valuation_bps_scale_homogeneity`): Verifies RIM valuation handles small-cap equity ($<\$1\text{M}$) and high-nominal KRX BPS ($>1\text{M}$ KRW) with scale homogeneity.
- [x] **V6-18** (`test_v6_18_sector_rotation_curated_symbol_mapping`): Verifies `SectorRotationEngine` passes `symbol=sym` to resolve curated leaders (`005930`, `NVDA`).
- [x] **V6-19** (`test_v6_19_iv_skew_live_options_prioritization`): Verifies `IVSkewEngine` prioritizes live options chain lookup when `ENABLE_LIVE_OPTIONS_FETCH=true`.
- [x] **V6-20** (`test_v6_20_event_driven_dart_8digit_corp_code_resolution`): Verifies `EventDrivenEngine` resolves 8-digit OpenDART `corp_code` to 6-digit tickers via `DARTCorpMapper`.
- [x] **V6-21** (`test_v6_21_card_factor_5day_macro_temporal_alignment`): Verifies `CARDFactorEngine` computes 5-day rolling macro shocks matching 5-day cumulative stock returns.
- [x] **V6-22** (`test_v6_22_single_stock_n1_neutral_score_guards`): Verifies factor engines return neutral 0.50 score for single-stock ($N=1$) degenerate inputs.
- [x] **V6-23** (`test_v6_23_stat_arb_summary_logging_performance`): Verifies `StatisticalArbitrageEngine` runs cointegration scanning without dumping raw 100k arrays at INFO level.
- [x] **V6-24** (`test_v6_24_reverse_stock_split_adjustment_and_volume_contraction`): Verifies `StockPriceDB` detects reverse splits ($> +50\%$ price jumps with volume contraction) and scales historical OHLC backwards.

### Domain 4: Execution OMS & Friction Costs (V6-25 ~ V6-31)
- [x] **V6-25** (`test_v6_25_oms_currency_denominator_us_and_global_hedging`): Verifies `ExecutionOMSEngine` converts KRW target capital to USD for US equities and global hedges, preventing 1,350x position explosions.
- [x] **V6-26** (`test_v6_26_oms_return_scale_normalization_gates_7_2_and_7_4`): Verifies OMS Gates 7.2 & 7.4 normalize percent vs decimal return notation, preventing false limit-lock drops.
- [x] **V6-27** (`test_v6_27_almgren_chriss_slicing_non_negative_tranches`): Verifies `AlmgrenChrissScheduler` clamps $\kappa \in [0.01, 3.0]$ and guarantees non-negative tranches summing to total quantity.
- [x] **V6-28** (`test_v6_28_oms_gate_7_3_single_friction_deduction`): Verifies OMS Gate 7.3 does not double-deduct friction when input alpha is already net expected return.
- [x] **V6-29** (`test_v6_29_turnover_optimizer_full_liquidation_and_entry_bypass`): Verifies `TurnoverOptimizer` bypasses turnover hysteresis damping for full liquidations ($w_{\text{targ}}=0$) and fresh entries ($w_{\text{curr}}=0$).
- [x] **V6-30** (`test_v6_30_slippage_feedback_buy_hedge_sign_and_db_lifecycle`): Verifies `SlippageFeedbackEngine` treats `BUY_HEDGE` as positive buy direction and wraps SQLite connection in `finally`.
- [x] **V6-31** (`test_v6_31_smart_order_router_primary_venue_residual_consolidation`): Verifies `SmartOrderRouter` merges residual quantities into primary exchange allocations without ATS duplication.

### Domain 5: Pipeline Orchestration & Infrastructure (V6-32 ~ V6-35)
- [x] **V6-32** (`test_v6_32_config_market_costs_json_parsing`): Verifies `src/config.py` parses `MARKET_COSTS_JSON` environment variables without `NameError: name 'json' is not defined`.
- [x] **V6-33** (`test_v6_33_pipeline_lifecycle_db_lock_and_status_tracking`): Verifies pipeline lifecycle registers `status='FAILED'` and releases DB locks on unhandled exceptions.
- [x] **V6-34** (`test_v6_34_run_snapshot_text_fallback_regex_parser`): Verifies `generate_snapshot` regex text fallback parser extracts ranks, symbols, names, scores, and factors accurately.
- [x] **V6-35** (`test_v6_35_config_environment_variable_and_kst_alignment`): Verifies `TradingConfig` parses liquidity/friction environment variables and aligns indicator dates with KST (UTC+9).

---

## 4. Test Execution Summary

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Finance\code\stock
configfile: pyproject.toml
plugins: anyio-4.14.0, dash-2.18.2, cov-7.1.0, github-actions-annotate-failures-0.4.2
collected 45 items

tests\test_v6_improvements.py ............................................. [100%]

============================= 45 passed in 28.00s =============================
```
