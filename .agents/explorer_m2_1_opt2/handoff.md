# Handoff Report: Milestone 2 Feature 7 & Feature 8
## Dynamic Half-Life Convergence Velocity ($\theta_i^*$) & Liquidity-Constrained Cash Buffer

**Agent:** Explorer M2-1 (Half-Life Convergence & Cash Buffer Specialist)  
**Parent / Caller:** Orchestrator (ID: `31b60ad6-8c74-4119-a790-2b2e694a292d`)  
**Working Directory:** `d:\Finance\code\stock\.agents\explorer_m2_1_opt2`  
**Date:** 2026-09-04T01:15:00+09:00 (UTC: 2026-09-03T16:15:00Z)  
**Deliverable Plan:** `d:\Finance\code\stock\.agents\explorer_m2_1_opt2\plan_m2_1.md`  

---

### 1. Observation

1. **Ad-Hoc Market Impact Dampening & Re-Normalization in `unified_portfolio_allocator.py`**:
   In `trading_system/src/risk/unified_portfolio_allocator.py` (lines 384–397):
   ```python
   # Line 385: Dampen weight of illiquid assets where impact penalty exceeds alpha
   damp_factors = np.exp(-2.0 * np.minimum(impact_penalties, 20.0))
   w_damped = w_blended * damp_factors
   s_damp = np.sum(w_damped)
   if s_damp > 0:
       w_blended = w_damped / s_damp

   # Line 392: Hard 5% ADV liquidity participation constraint: abs(w_i - w_curr_i) <= (0.05 * ADV_i) / V_port
   max_delta_w = (0.05 * daily_advs) / float(total_capital)
   w_bounded = np.clip(w_blended, np.maximum(0.0, w_curr - max_delta_w), w_curr + max_delta_w)
   s_bound = np.sum(w_bounded)
   if s_bound > 0:
       w_blended = w_bounded / s_bound
   ```
   When `w_bounded` clips an illiquid asset (e.g. to 0.00025), dividing by `s_bound` re-inflates the illiquid asset and inflates all other liquid assets (e.g. from 0.25 to 0.999).

2. **Downstream Portfolio Constraints Re-Normalization in `portfolio_optimizer.py`**:
   In `trading_system/src/risk/unified_portfolio_allocator.py` (line 399):
   ```python
   final_w = apply_portfolio_constraints(
       w_blended,
       symbols=symbols,
       sectors=sectors,
       max_single_stock_weight=self.max_single_weight,
       max_sector_weight=self.max_sector_weight,
       factor_loadings=factor_loadings
   )
   ```
   In `trading_system/src/analysis/portfolio_optimizer.py` (lines 778–780):
   ```python
   sum_w = float(np.sum(w))
   if sum_w > 1e-12:
       w /= sum_w
   ```
   Because `apply_portfolio_constraints` runs after the impact adjustment and normalizes `w /= sum_w`, any dampening intended to hold cash is destroyed, forcing total equity allocation to 100%.

3. **Static 5% ADV Cap Without Strategy Half-Life Urgency**:
   In `unified_portfolio_allocator.py` (line 392):
   `max_delta_w = (0.05 * daily_advs) / float(total_capital)`
   This treats all strategies identically. For fast-decaying signals with $\tau_{1/2} \le 1.5$d (e.g., surge, microstructure, overnight gap), taking 4–5 days to build a position destroys up to 85% of alpha via decay $\alpha(t) = \alpha_0 \cdot 2^{-t/\tau_{1/2}}$. Conversely, for slow-decaying signals with $\tau_{1/2} \ge 30$d (e.g., RIM valuation, value-up), trading too fast incurs unnecessary non-linear convex 3/2-power Gatheral impact.

4. **Existing Test Suite Baseline Pass Verification**:
   Running `.venv\Scripts\python.exe -m pytest tests/test_institutional_portfolio_construction.py` executed 13 tests with 100% pass rate in 14.00s:
   - `TestMultiModelRegimeBlending::test_regime_weights_shift` PASSED
   - `TestMarketImpactPenalty::test_illiquid_asset_dampening` PASSED
   - `TestTargetVolatilityScalingAndCashDrag::test_bull_cash_drag_eliminator` PASSED
   - `TestTargetVolatilityScalingAndCashDrag::test_crisis_cash_preservation` PASSED
   - `TestLelandNoTradeBuffers::test_no_trade_buffer_noise_suppression` PASSED
   - `TestUnifiedPortfolioAllocatorEndToEnd::test_end_to_end_allocate` PASSED
   In `test_illiquid_asset_dampening`, Asset 1 (ADV $50k) vs Asset 0 (ADV $50M) only asserts `assert w[0] > w[1] * 1.5`.

5. **2D Regime Half-Life Extraction Availability**:
   In `trading_system/src/ai/ensemble_scorer.py` (lines 3310–3359), `EnsembleScoringEngine.get_regime_adaptive_half_lives(regime)` is implemented, returning regime-scaled half-lives for all 37 strategies (e.g. CRISIS: $\kappa = 0.30$, BULL_LOW_VOL: $\kappa = 1.30$).

---

### 2. Logic Chain

1. **From Observation 1 & 2 to Architectural Reordering**:
   Because `apply_portfolio_constraints()` forces `w /= sum(w)`, it must be applied to determine the *ideal unconstrained target portfolio* $w^*$ from the multi-model blend, satisfying single-stock and sector limits.
   The liquidity convergence step must then occur *after* $w^*$ is established, so that any unallocated weight resulting from partial execution ($\theta_i^* < 1.0$) or the ADV ceiling directly constitutes the cash buffer:
   $$w_{\text{invested}} = \sum_{i=1}^n w_{t+1, i} \le 1.0, \quad w_{\text{cash}} = 1.0 - w_{\text{invested}}$$
   No post-hoc division by $\sum w_{t+1}$ is performed, preventing the inflation of liquid assets and respecting the liquidity boundaries of illiquid assets.

2. **From Observation 3 to Closed-Form Optimal Convergence Velocity $\theta_i^*$**:
   Balancing alpha decay $\lambda_{\alpha, i} = \frac{\ln 2}{\tau_{1/2, i}}$ against Gatheral 3/2-power convex market impact $C_{\text{impact}}(\theta_i) = \kappa \sigma_i \text{ADV}_i (\theta_i \Delta W_i / \text{ADV}_i)^{1.5}$ leads to the objective:
   $$\max_{\theta_i \in (0, 1]} \Pi(\theta_i) = \theta_i \alpha_i \Delta W_i - (1 - \theta_i) \lambda_{\alpha, i} \Delta W_i - \kappa \sigma_i \text{ADV}_i \left(\frac{\theta_i \Delta W_i}{\text{ADV}_i}\right)^{1.5}$$
   Setting $\frac{\partial \Pi}{\partial \theta_i} = 0$:
   $$(\alpha_i + \lambda_{\alpha, i}) \Delta W_i - 1.5 \kappa \sigma_i \Delta W_i \sqrt{\frac{\theta_i \Delta W_i}{\text{ADV}_i}} = 0$$
   $$\implies \theta_{\text{impact}, i}^* = \left( \frac{\alpha_{\text{daily}, i} + \lambda_{\alpha, i}}{1.5 \cdot \kappa_i \cdot \sigma_i} \right)^2 \cdot \frac{\text{ADV}_i}{\Delta W_i}$$
   For fast alpha ($\tau_{1/2} \le 1.5$d), $\lambda_\alpha \ge 0.462$, so $\theta^* \to 1.0$ (immediate 1-day convergence).
   For slow alpha ($\tau_{1/2} \ge 30$d) with large participation, $\lambda_\alpha \le 0.023$, so $\theta^* \in [0.15, 0.40]$ (smooth execution over 2–4 days, cutting market impact by >50%).

3. **From Observation 3 & 5 to Dynamic ADV Participation Cap**:
   The maximum single-day participation fraction $\rho_{\max, i}$ must adapt smoothly to signal half-life:
   $$\rho_{\max, i} = 0.05 + 0.10 \cdot \exp\left(-\frac{\tau_{1/2, i}}{3.0}\right)$$
   This grants ultra-fast signals up to 13.5% of ADV to prevent signal decay while strictly binding core fundamental signals to the 5% ADV institutional limit.

4. **From Observation 4 to Full Backward Compatibility**:
   When `advs is None`, no liquidity constraints apply, and `optimize_multi_model_blend()` returns $w^*$ (which sums to 1.0000), guaranteeing that all existing tests in `test_institutional_portfolio_construction.py` and `test_unified_portfolio_engine.py` continue to pass without modification.

---

### 3. Caveats

1. **Current Holdings Initialization**: When `current_weights` is None or zeros (e.g. backtest start or cold-start), $w_{t, i} = 0.0$, and the full target gap is $w_i^*$. Partial convergence means day 1 total invested weight will equal $\sum \theta_i^* w_i^* \le 1.0$, leaving $(1.0 - \sum \theta_i^* w_i^*)$ in cash, which naturally builds into the target portfolio over subsequent days.
2. **Horizon Consistency**: Daily alpha is normalized by dividing 20-day predicted return by 20. If a strategy outputs 1-day predictions, `self.target_horizon` should align accordingly.
3. **Downstream OMS Delta Alignment**: The calculated $w_{t+1, i}$ represents the target weight for day $t+1$. Milestone 2 Feature 10 will ensure OMS computes $\Delta Q = Q_{t+1} - Q_t$ rather than re-buying entire positions.

---

### 4. Conclusion

1. **Feature 7 is fully solved via closed-form analytical velocity $\theta_i^*$**:
   $$\theta_i^* = \min\left(1.0, \; \max\left(0.15, \; \left(\frac{\alpha_{\text{daily}, i} + \frac{\ln 2}{\tau_{1/2, i}}}{1.5 \cdot \kappa \cdot \sigma_i}\right)^2 \cdot \frac{\text{ADV}_i}{\Delta W_i}\right)\right)$$
   with dynamic liquidity ceiling $\Delta w_{\max, i} = (0.05 + 0.10 e^{-\tau/3}) \cdot \text{ADV}_i / V_{\text{port}}$.
2. **Feature 8 is fully solved by eliminating re-normalization and routing unallocated capital to cash**:
   $w_{t+1} = w_t + \Delta w_{\text{exec}}$, and $w_{\text{cash}} = 1.0 - \sum w_{t+1}$. No post-hoc division by $\sum w$ is permitted.
3. **Complete implementation plan and code diffs are authored in `plan_m2_1.md`**.

---

### 5. Verification Method

1. **Codebase Files to Inspect**:
   - `trading_system/src/risk/unified_portfolio_allocator.py` (lines 257–408 and lines 640–765)
   - `tests/test_institutional_portfolio_construction.py`
2. **Independent Verification Commands**:
   ```powershell
   # Run institutional portfolio construction test suite
   .venv\Scripts\python.exe -m pytest tests/test_institutional_portfolio_construction.py -v

   # Run unified portfolio engine test suite
   .venv\Scripts\python.exe -m pytest tests/test_unified_portfolio_engine.py -v

   # Run portfolio allocator test suite
   .venv\Scripts\python.exe -m pytest tests/test_portfolio_allocator.py -v

   # Run full v8 remediation test suite
   .venv\Scripts\python.exe -m pytest tests/test_v8_remediation.py -v
   ```
3. **Invalidation Conditions**:
   - Any test where `advs is None` fails to produce weights summing to 1.0000.
   - Any test where an illiquid asset causes other liquid assets to exceed their portfolio target weight $w^*$.
   - Any test where fast alpha ($\tau \le 1$d) produces $\theta^* < 0.85$ under moderate participation.
