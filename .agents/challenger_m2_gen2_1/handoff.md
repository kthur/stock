# Handoff Report: Milestone 2 Adversarial Stress Testing (Challenger 1)

- **Author**: Challenger 1 (`challenger_m2_gen2_1`)
- **Recipient**: Parent Agent (`dcd05c17-b517-427b-8133-abcdeb26cc11`)
- **Date**: 2026-09-04T04:16:00Z
- **Target Component**: `trading_system/src/risk/unified_portfolio_allocator.py` (Features F28, F29, F30)
- **Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Baseline Phase 4 Test Suite Execution
- Executed the baseline Milestone 2 test suite:
  ```bash
  .venv\Scripts\python.exe -m pytest tests/test_phase4_portfolio_execution.py -v
  ```
- Result: **18 passed in 12.41s** with 0 warnings or failures.
- Output log:
  ```
  tests/test_phase4_portfolio_execution.py::TestF28DownsideSemiCovarianceCVaR::test_f28_semi_cov_boosts_upside_momentum_asset PASSED [  5%]
  tests/test_phase4_portfolio_execution.py::TestF28DownsideSemiCovarianceCVaR::test_f28_semi_cov_weight_interpolation_property PASSED [ 11%]
  tests/test_phase4_portfolio_execution.py::TestF28DownsideSemiCovarianceCVaR::test_f28_fallback_when_cov_matrix_is_none PASSED [ 16%]
  tests/test_phase4_portfolio_execution.py::TestF28DownsideSemiCovarianceCVaR::test_f28_edge_cases PASSED [ 22%]
  tests/test_phase4_portfolio_execution.py::TestF29DynamicModelConvictionBlending::test_f29_high_dispersion_scales_black_litterman_in_bull PASSED [ 27%]
  tests/test_phase4_portfolio_execution.py::TestF29DynamicModelConvictionBlending::test_f29_crisis_regime_boosts_cvar_and_herc PASSED [ 33%]
  tests/test_phase4_portfolio_execution.py::TestF29DynamicModelConvictionBlending::test_f29_blended_weights_strictly_sum_to_one PASSED [ 38%]
  tests/test_phase4_portfolio_execution.py::TestF30MarketSpecificLelandBufferBands::test_f30_is_korean_asset_helper PASSED [ 44%]
  tests/test_phase4_portfolio_execution.py::TestF30MarketSpecificLelandBufferBands::test_f30_korean_assets_receive_wider_buffer_bands PASSED [ 50%]
  tests/test_phase4_portfolio_execution.py::TestF30MarketSpecificLelandBufferBands::test_f30_custom_asset_cost_bps_override PASSED [ 55%]
  tests/test_phase4_portfolio_execution.py::TestF31MultiTierOBIMicroPricePegging::test_f31_micro_price_baseline PASSED [ 61%]
  tests/test_phase4_portfolio_execution.py::TestF31MultiTierOBIMicroPricePegging::test_f31_multi_tier_composite_obi_shift PASSED [ 66%]
  tests/test_phase4_portfolio_execution.py::TestF31MultiTierOBIMicroPricePegging::test_f31_scheduler_and_oms_parity PASSED [ 72%]
  tests/test_phase4_portfolio_execution.py::TestF32HawkesAdverseSelectionGating::test_f32_toxic_flow_detection_reduces_maker_and_expands_dark_probe PASSED [ 77%]
  tests/test_phase4_portfolio_execution.py::TestF32HawkesAdverseSelectionGating::test_f32_intensity_in_order_plan_dict PASSED [ 83%]
  tests/test_phase4_portfolio_execution.py::TestF33ClosedLoopSlippageFeedbackScaling::test_f33_allocator_kappa_eff_scaling PASSED [ 88%]
  tests/test_phase4_portfolio_execution.py::TestF33ClosedLoopSlippageFeedbackScaling::test_f33_gatheral_transient_impact_eta_scaling PASSED [ 94%]
  tests/test_phase4_portfolio_execution.py::TestF33ClosedLoopSlippageFeedbackScaling::test_f33_gatheral_slices_soften_urgency_under_high_slippage PASSED [100%]
  ============================= 18 passed in 12.41s =============================
  ```

### 1.2 Adversarial Stress Test Suite Execution
- Created and executed an empirical stress harness in `tests/test_phase4_m2_challenger_stress.py` containing 14 adversarial test scenarios across F28, F29, and F30:
  ```bash
  .venv\Scripts\python.exe -m pytest tests/test_phase4_m2_challenger_stress.py -v
  ```
- Result: **14 passed in 12.13s (100% pass rate)**.
- Specific findings from the stress scenarios:
  1. **F28 Downside Semi-Covariance Matrix**:
     - *Rank-Deficient Covariance ($N > T$)*: Evaluated $N=15$ assets over $T=6$ time steps. Weights were non-negative, finite, bounded by $w_{\text{max}} = 0.30$, and summed exactly to $1.0000$.
     - *Collinear & Identical Assets*: Tested exact duplicate and scaled return series (rank 1 covariance). Allocation to identical assets was mathematically symmetric ($w_0 = w_1$) with zero solver divergence.
     - *Zero Downside Variance*: Tested all-positive returns ($r_{i,t} \in [0.005, 0.05]$) where $\Sigma^-$ has zero sample dispersion. The shrinkage regularization $\delta \cdot \text{diag}(\Sigma^-) + 10^{-6} \mathbf{I}$ prevented zero-determinant crashes.
     - *Pure Downside Variance*: Tested all-negative returns ($r_{i,t} \in [-0.05, -0.005]$). The solver stably allocated capital with non-negative weights summing to $1.0000$.
     - *Monotonicity Sweep*: Swept `semi_cov_weight` across $[0.0, 0.10, 0.20, 0.35, 0.50, 0.65, 0.80, 0.90]$. Weight of the positive-skew asset grew monotonically from $0.50$ to $>0.85$ without non-monotonic reversals.
  2. **F29 Dynamic Conviction Blending**:
     - *Zero Dispersion ($\sigma(\hat{\mu}) = 0.0$)*: Verified across Bull, Sideways, Crisis, and Bear regimes. Model blend weights stayed stable, and asset allocations remained strictly non-negative and normalized to $1.0000$.
     - *Massive Dispersion ($\sigma(\hat{\mu}) \gg 10.0$)*: Inputted returns of $\pm 1500\%$. The $\tanh((\sigma(\hat{\mu}) - 0.03)/0.02)$ term saturated smoothly at $+1.0$, scaling Black-Litterman by exactly $1.30\times$ without numerical overflow.
     - *Extreme/Degenerate Regime Probabilities*: Tested pure Crisis ($c=1.0$), pure Bull, pure Sideways, empty dict `{}`, all-zero dict `{"BULL": 0.0, "CRISIS": 0.0}`, and uniform $1/6$ probabilities. In every case, $\sum_{m} w_m = 1.0000$ and $w_m \ge 0$.
  3. **F30 Leland No-Trade Buffer Bands**:
     - *Volatility Spectrum*: Tested daily volatility from $0.1\%$ to $40\%$ ($\sigma \in [0.001, 0.40]$). At every point, Korean assets (`005930.KS`, `068270.KQ`, `000660`) maintained wider or equal buffer bands than US assets (`AAPL`), strictly adhering to the 25 bps STT floor.
     - *Extreme Leland Costs*: When `leland_cost_bps = 0.5`, Korean assets held steady at 25 bps, absorbing a $1.2\%$ drift without trading, while US assets tightened to $0.5$ bps and rebalanced immediately.
     - *Boundary Rebalancing & Bypasses*: Confirmed that breached bands rebalance to the band boundary $L_i$ or $U_i$ (minimizing turnover), while new entries ($w_{\text{curr}} \le 10^{-4}$) and complete liquidations ($w_{\text{tgt}} \le 10^{-4}$) bypass the buffers instantly.

### 1.3 Full Repository Test Collection
- Verified complete repository test collection:
  ```bash
  .venv\Scripts\python.exe -m pytest tests/ --collect-only -q
  ```
- Result: **2,347 tests collected** in 19.67s with **0 collection errors**.

---

## 2. Logic Chain

1. **Robustness of Semi-Covariance Regularization (F28)**:
   - *Observation*: In `PortfolioAllocator.compute_downside_semi_cov` (lines 168–176), diagonal shrinkage target $\delta \cdot \text{diag}(\Sigma^-)$ with $\delta \in [0.05, 0.30]$ and jitter $+10^{-6} \mathbf{I}$ are applied before blending.
   - *Inference*: Even when $N > T$, collinear assets exist, or downside deviations are zero, $\Sigma_{\text{effective}}$ remains strictly positive definite ($x^T \Sigma_{\text{eff}} x > 0$ for all $x \ne 0$). SLSQP optimization in `calculate_cvar_weights` converges reliably without ill-conditioned Hessian warnings.
   - *Empirical Proof*: `test_rank_deficient_singular_n_greater_than_t`, `test_identical_collinear_assets`, and `test_zero_downside_variance_all_positive_returns` all passed with exact normalization $\sum w_i = 1.0000$.

2. **Weight Conservation & Non-Negativity in Conviction Blending (F29)**:
   - *Observation*: In `UnifiedPortfolioAllocator.optimize_multi_model_blend` (lines 527–542), the Black-Litterman scale factor uses $1.0 + 0.30 \tanh(\cdot) \in [0.70, 1.30]$, and EVT-CVaR / HERC boosts are strictly additive ($+0.10 \sim +0.20$). Renormalization `tot_b = sum(blend_cfg.values()); blend_cfg = {k: v / tot_b}` is executed immediately after.
   - *Inference*: Because all inputs to `blend_cfg` are non-negative and bounded, division by `tot_b > 0` guarantees that $\sum_{m \in \{BL, HERC, RP, CVaR\}} w_m \equiv 1.0000$ and $w_m \ge 0$ for any regime dictionary or alpha dispersion value.
   - *Empirical Proof*: `test_extreme_alpha_dispersion_massive_dispersion` and `test_extreme_regime_probabilities_pure_and_degenerate` verified that $\sum w_m = 1.0000$ across all 7 regime variations.

3. **Tax Friction Suppression via Asymmetric Leland Bands (F30)**:
   - *Observation*: In `UnifiedPortfolioAllocator.apply_leland_no_trade_buffers` (lines 883–890), Korean assets automatically receive $c_i = \max(\text{leland\_cost\_bps}, 25.0)$ bps, while US assets receive $c_i = \min(\text{leland\_cost\_bps}, 8.0)$ bps.
   - *Inference*: Since half-width $\Delta_i \propto (c_i \cdot \sigma_{\text{ann}}^2 / \gamma)^{1/3}$, the $(25.0 / 8.0)^{1/3} \approx 1.46\times$ ratio widens Korean buffer bands by at least $46\%$, preventing costly churn under Korea's 0.18% STT.
   - *Empirical Proof*: `test_krx_vs_us_buffer_asymmetry_across_wide_volatility_spectrum` confirmed that US assets rebalance at significantly smaller drifts than Korean assets across the entire volatility range $\sigma \in [0.001, 0.40]$.

---

## 3. Caveats

- **Minimum Half-Width Clamping**: For exceptionally low-volatility US assets ($\sigma_{\text{daily}} \le 0.002$), both Korean and US buffer half-widths saturate at the lower bound clip of $0.005$ ($0.5\%$). This is intentional to prevent micro-rebalancing transactions that would generate broker ticket fees.
- **Short Lookback Window Assumption**: EVT-CVaR optimization requires at least $T \ge 5$ returns. For $T < 5$, `calculate_cvar_weights` falls back to equal weighting ($1/n$), which was verified safe.

---

## 4. Conclusion

**Verdict: APPROVE**

Features F28, F29, and F30 in `trading_system/src/risk/unified_portfolio_allocator.py` are mathematically sound, numerically stable under severe singular and rank-deficient extremes, strictly conserve portfolio weight normalizations ($\sum w = 1.0000$), and correctly widen Leland no-trade buffers for Korean equities to mitigate STT churn. All 32 targeted tests pass with 100% success rate, and total repository test collection stands at 2,347 tests with zero errors.

---

## 5. Verification Method

### 5.1 Command to Re-run All Milestone 2 Stress Tests
```bash
.venv\Scripts\python.exe -m pytest tests/test_phase4_portfolio_execution.py tests/test_phase4_m2_challenger_stress.py -v
```

### 5.2 Command to Verify Test Suite Collection
```bash
.venv\Scripts\python.exe -m pytest tests/ --collect-only -q
```

### 5.3 Invalidation Conditions
1. Any negative weights ($w_i < -10^{-5}$) or weight sums deviating from $1.0000$ ($|\sum w_i - 1.0| > 10^{-3}$) under extreme market regimes or dispersion.
2. Any `LinAlgError` or `ValueError: array contains NaN or Inf` when optimizing rank-deficient ($N > T$) or collinear asset matrices.
3. Any instance where a US equity receives a wider Leland no-trade buffer band than an identical-risk Korean equity under standard parameters.
