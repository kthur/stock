# Reviewer Handoff Report — Milestone 2: Portfolio 4-Model Dynamic Blending & Darkpool/HFT OMS Optimization

**Date**: 2026-09-04
**Reviewer ID**: reviewer_m2_opt3
**Recipient**: parent (b46202ea-01da-4d8b-b60e-9285cbf907d4)
**Verdict**: **APPROVE**

---

## 1. Observation

Direct observations from rigorous code inspection, integrity verification, test suite execution, and adversarial stress testing:

### 1.1 Code Inspection & Integrity Verification
1. **Feature F09: Continuous 4-Model Markov Blending**:
   - Location: `trading_system/src/risk/unified_portfolio_allocator.py:204-301`
   - Function: `UnifiedPortfolioAllocator.compute_dynamic_regime_blend_weights(regime, vix_val, crisis_severity, apply_ema, ema_halflife)`
   - Code verification:
     - Posterior dictionary: iterates over `{regime: prob}`, normalizes by total probability, and computes soft-blended confidence vector $\mathbf{c}(t) = \sum_m \pi_{t, m} \mathbf{c}^{(m)}$.
     - Backward compatibility: maps integers $0 \dots 6$ to canonical regime strings, and handles string regimes with robust prefix matching.
     - Dynamic crisis/volatility tilting:
       ```python
       v_vol = max(v_vol, 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, (vix_f - 20.0) / 3.0)))))
       cvar_boost = 0.20 * v_vol + 0.40 * c_crisis
       rp_boost = 0.10 * v_vol * (1.0 - c_crisis)
       bl_suppress = max(0.0, 1.0 - 0.70 * v_vol - 0.90 * c_crisis)
       blend_cfg["bl"] *= bl_suppress
       blend_cfg["cvar"] += cvar_boost
       blend_cfg["rp"] += rp_boost
       ```
     - 5-day EMA smoothing: when `apply_ema=True`, smoothly interpolates with $\alpha = 1 - e^{-\ln 2 / 5.0} \approx 0.1294$.
     - Normalization: strictly re-normalizes `sum(blend_cfg.values()) == 1.0000` under all input conditions.

2. **Feature F10: Clayton Copula Tail Covariance Integration & Parametric EVT-CVaR**:
   - Locations:
     - `trading_system/src/risk/portfolio_allocator.py:81-131` (`compute_tail_stress_cov`)
     - `trading_system/src/risk/unified_portfolio_allocator.py:302-397` (`calculate_cvar_weights`)
   - Code verification:
     - Estimates Kendall's tau via Greiner's formula $\tau_{est} = \frac{2}{\pi} \arcsin(\rho)$ and joint lower tail coincidence, bounded in $[0.05, 0.80]$.
     - Maps to Clayton parameter $\theta = \frac{2\tau_{eff}}{1 - \tau_{eff}}$ and lower tail dependence $\lambda_L = 2^{-1/\theta} \in [0.10, 0.70]$.
     - Applies Higham spectral projection (`np.linalg.eigh`, clipping eigenvalues to $\ge 10^{-4}$) to guarantee PSD.
     - Blends $\boldsymbol{\Sigma}_{tail} = (1 - \lambda_L)\boldsymbol{\Sigma}_{shrink} + \lambda_L \boldsymbol{\Sigma}_{clayton} + 10^{-5}\mathbf{I}_K$.
     - In `calculate_cvar_weights`: utilizes parametric Student-$t$ EVT-CVaR with heavy-tail expansion multiplier $k_\alpha = 2.40$ (for $\alpha = 0.95, \nu \approx 5$), minimizing $k_\alpha \sqrt{\mathbf{w}^T \boldsymbol{\Sigma}_{tail} \mathbf{w}} - \lambda_\alpha^{eff} \mathbf{w}^T \mathbf{p}_{rets}$ with dynamic alpha tilt dampening ($\lambda_\alpha^{eff} = \lambda_\alpha \cdot \max(0.05, 1 - 0.85 v_{vol} - 0.90 c_{crisis})$). Eliminates small-sample estimation variance for short lookbacks ($T \le 60$).

3. **Feature F11: Dark-Pool Adjusted Gatheral 3/2-Power Market Impact**:
   - Location: `trading_system/src/risk/unified_portfolio_allocator.py:640-675` (`optimize_multi_model_blend`)
   - Code verification:
     - Extracts dark pool scores: $\phi_{dark} = \min(0.60, 1.2 \cdot \max(0, \text{darkpool\_score}))$.
     - Instantaneous impact parameter: $\kappa_{eff} = \kappa_0(1 - \phi_{dark})$ clipped $\ge 0.20$.
     - Closed-form optimal convergence velocity:
       $$\theta_{impact, i}^* = \left(\frac{\alpha_i^{daily} + \lambda_{\alpha, i}}{1.5 \kappa_{eff, i} \sigma_i}\right)^2 \cdot \frac{ADV_i}{\Delta Trades_i}$$
     - Higher off-exchange liquidity reduces lit friction and accelerates portfolio position convergence.

4. **Feature F12: Dynamic Dark Probing & 3-Tier Multi-Venue SOR Routing**:
   - Locations:
     - `trading_system/src/execution/smart_order_router.py:60-145` (`route_order`)
     - `trading_system/src/execution/oms_engine.py:80, 110-145, 960-1090` (`generate_order_plan`)
   - Code verification:
     - Dark probe ratio scales from base 40% up to 70% when `is_accumulation=True` or `darkpool_score >= 0.60`.
     - 3-tier child order generation:
       - Tier 1: ATS / Dark Pool Midpoint ($Q_{dark} = \lfloor Q_{tot} \cdot \delta_{dark} \rfloor$).
       - Tier 2: Primary Peg / Maker Leg ($Q_{maker} = \lfloor Q_{rem} \cdot 0.70 \rfloor$).
       - Tier 3: Lit Sweeper ($Q_{lit} = Q_{rem} - Q_{maker}$).
       - Exact conservation: $Q_{dark} + Q_{maker} + Q_{lit} \equiv Q_{tot}$.
     - Expected cost savings: calculates half-spread savings + maker rebates in bps (`expected_cost_saving_bps`).
     - Integration in `ExecutionOMSEngine`: instantiated as `self.sor`, automatic database migration for `order_plans` (`sor_routing TEXT`, `expected_cost_saving_bps REAL`), attached to order plans and tranches.

5. **Feature F13: Orderbook Imbalance (OBI) Midpoint Peg Pricing**:
   - Locations:
     - `trading_system/src/execution/oms_engine.py:904-914, 977-986, 1362-1393` (`ExecutionOMSEngine.calculate_peg_limit_price`)
     - `trading_system/src/execution/oms_engine.py:1795-1826` (`AlmgrenChrissScheduler.calculate_peg_limit_price`)
   - Code verification:
     - Non-linear formula: $P_{peg} = P_{mid} + 0.5 \cdot \text{spread} \cdot \tanh(\kappa \cdot \text{OBI})$ with $\kappa = 1.5$.
     - Leans towards ask for buy orders when buy queue dominates ($\text{OBI} > 0$) to secure execution; leans towards bid when selling flow dominates ($\text{OBI} < 0$) to capture spread.
     - Strictly bounded in $[P_{bid}, P_{ask}]$.

### 1.2 Integrity Audit
- Searched codebase for hardcoded expected outputs, dummy facades, and test cheat bypasses: zero occurrences.
- All algorithms execute genuine closed-form convex optimization, spectral matrix projections, non-linear hyperbolic pricing, and real order routing.

### 1.3 Test Suite Execution
- Executed full 9-suite portfolio and execution regression test suite:
  ```
  .venv\Scripts\pytest.exe tests/test_m2_quant_enhancements.py tests/test_portfolio_allocator.py tests/test_unified_portfolio_engine.py tests/test_portfolio_optimizer_and_oms.py tests/test_m2_portfolio_execution.py tests/test_smart_router.py tests/test_tier0_apex_quant_enhancements.py tests/test_phase3_phase4_hmm_copula_oms.py tests/test_sigmoid_smooth_cvar.py -v
  ```
  **Result**: 87 passed in 15.44s (100% pass rate).
- Executed custom adversarial stress test suite (`.agents/reviewer_m2_opt3/test_adversarial_m2.py`):
  - Tested empty dicts, all-zero probabilities, negative probabilities, unknown regime strings, invalid integers, NaN/inf VIX values, extreme crisis severities ($99.0$), constant/zero-variance returns, singular covariance matrices, NaN/inf darkpool scores, odd lot order quantities, and extreme OBI values ($\pm 100.0$).
  **Result**: ALL ADVERSARIAL CHECKS PASSED SUCCESSFULLY.

---

## 2. Logic Chain

1. **Continuous Markov Blending (F09)**:
   - Discrete regime jumps cause sudden shifts in target weights, generating artificial portfolio turnover and incurring market friction. By taking posterior distributions $\boldsymbol{\pi}_t$, the allocator performs smooth convex combinations.
   - Dynamic volatility and crisis tilting dampens return-seeking models (Black-Litterman) while elevating tail-risk models (EVT-CVaR and Risk Parity). Strict sum-to-1 normalization is mathematically guaranteed via explicit post-tilt re-normalization.

2. **Clayton Copula Lower Tail Dependence & Parametric EVT-CVaR (F10)**:
   - Lower tail dependence $\lambda_L = 2^{-1/\theta}$ derived from Kendall's $\tau$ correctly captures asymmetric downside co-crashes.
   - Projecting to the nearest positive semi-definite matrix via spectral eigenvalue clipping ($\ge 10^{-4}$) and adding $10^{-5}\mathbf{I}$ prevents solver degeneracy.
   - Using parametric Student-$t$ EVT-CVaR with tail expansion factor $k_\alpha = 2.40$ solves the empirical CVaR sample-sparsity problem under short estimation windows ($T \le 60$), where $\alpha=0.95$ observes only 3 tail realizations.

3. **Dark-Pool Adjusted Gatheral 3/2-Power Market Impact (F11)**:
   - Off-exchange / dark liquidity matches at the midpoint, avoiding lit book market impact. Modulating $\kappa_{eff} = \kappa_0(1 - \phi_{dark})$ allows higher trading velocity $\theta^*$ without exceeding liquidity risk budgets.

4. **Dynamic Dark Probing & 3-Tier Multi-Venue SOR Routing (F12)**:
   - Routing 40%–70% of flow to ATS midpoint first captures spread savings and conceals institutional intent.
   - Residual 70% maker / 30% lit sweeper splits ensure liquidity capture while guaranteeing exact conservation of the parent order quantity.

5. **Orderbook Imbalance (OBI) Midpoint Peg Pricing (F13)**:
   - The non-linear $\tanh(\kappa \cdot \text{OBI})$ mapping provides a bounded, smooth, monotonic adjustment to the midpoint price. Orders adjust dynamically based on queue pressure, preventing adverse selection while capturing half-spread savings.

---

## 3. Caveats

1. **Single-Step vs Full Multi-Period Convergence**:
   - When `optimize_multi_model_blend` runs with `current_weights` and `advs`, it yields intermediate weights $w_{curr} + \theta^*(w_{blend} - w_{curr})$. Full portfolio allocation subsequently applies target volatility scaling and cash drag elimination in `UnifiedPortfolioAllocator.allocate()`. This is intended design and mathematically sound.
2. **ATS Disablement Fallback**:
   - In venues or market sessions where alternative trading systems (ATS) are unavailable (`ats_available=False`), the SOR gracefully routes 100% of order volume through primary exchange maker and taker channels without throwing exceptions.

---

## 4. Conclusion

The implementation of Milestone 2 (Features F09 - F13) satisfies all requirements from `PROJECT.md` and `ORIGINAL_REQUEST.md`:
- Genuine mathematical modeling without hardcoding or facades.
- Zero integrity violations detected.
- 100% test pass rate across all 87 unit and integration tests.
- Full robustness verified across extreme adversarial edge cases.

**Verdict: APPROVE**

---

## 5. Verification Method

To independently reproduce the review findings:

1. **Run Full 9-Suite Test Suite**:
   ```bash
   .venv\Scripts\pytest.exe tests/test_m2_quant_enhancements.py tests/test_portfolio_allocator.py tests/test_unified_portfolio_engine.py tests/test_portfolio_optimizer_and_oms.py tests/test_m2_portfolio_execution.py tests/test_smart_router.py tests/test_tier0_apex_quant_enhancements.py tests/test_phase3_phase4_hmm_copula_oms.py tests/test_sigmoid_smooth_cvar.py -v
   ```
   *Expected output*: `87 passed in ~15s`

2. **Run Dedicated Milestone 2 Unit Test Suite**:
   ```bash
   .venv\Scripts\pytest.exe tests/test_m2_quant_enhancements.py -v
   ```
   *Expected output*: `13 passed in ~6s`

3. **Run Adversarial Stress Test Suite**:
   ```bash
   .venv\Scripts\python.exe .agents/reviewer_m2_opt3/test_adversarial_m2.py
   ```
   *Expected output*: `ALL ADVERSARIAL CHECKS PASSED SUCCESSFULLY!`
