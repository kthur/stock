# Comprehensive Technical Analysis: Domain 2 & Domain 4 (V6-09 ~ V6-16 & V6-25 ~ V6-31)

**Survey Agent**: `explorer_2`  
**Date**: 2026-08-22  
**Target Scope**: 
- **Domain 2: Portfolio & Risk Engineering** (V6-09 ~ V6-16, 8 Tasks)
- **Domain 4: Execution OMS & Transaction Costs** (V6-25 ~ V6-31, 7 Tasks)

---

## 1. Executive Summary & Scope Boundary

This survey report provides the deep-dive architectural, mathematical, and code-level investigation for 15 defect remediation and system enhancement tasks across Domain 2 and Domain 4, as specified in `system_improvement_report_v6.md` and `ORIGINAL_REQUEST.md`.

All 15 tasks have been traced down to their exact source code locations in `trading_system/src/`, their mathematical failure mechanisms analyzed, existing test coverage cataloged across `tests/`, and concrete implementation and verification blueprints established.

---

## 2. Domain 2: Portfolio & Risk Engineering (V6-09 ~ V6-16)

### V6-09 [🔴 CRITICAL]: Leland Dynamic Buffer Band Boundary Collapse ($w_{\text{curr}}=0, w_{\text{targ}}=0$)
- **Affected File & Lines**: `trading_system/src/risk/portfolio_allocator.py:920-960`
- **Component**: `PortfolioAllocator.compute_portfolio_rebalance()` & `calculate_dynamic_buffer_band()`
- **Mathematical Failure Mechanism**:
  Leland buffer bands $[L_i, U_i] = [\max(0.0, w_{\text{targ}} - \delta_i), w_{\text{targ}} + \delta_i]$ are computed with bandwidth $\delta_i = \left(\frac{3 c_i w_{\text{targ}} \sigma_i^2}{4 \gamma}\right)^{1/3} \in [0.005, 0.050]$.
  For small target allocations ($w_{\text{targ}} = 0.012$) where $\delta_i = 0.015$, $L_i = \max(0.0, 0.012 - 0.015) = 0.0$.
  When evaluating an uninvested asset ($w_{\text{curr}} = 0.0$), the condition $L_i \le w_{\text{curr}} \le U_i$ ($0.0 \le 0.0 \le 0.027$) evaluates to `True`, classifying the new position initiation as `HOLD` with `trade_weight = 0.0`. Consequently, no new positions below $\delta_i$ can ever be opened.
  Similarly, for full liquidation ($w_{\text{targ}} = 0.0$), an existing position ($w_{\text{curr}} = 0.008$) falls inside $[0.0, \delta_i]$, trapping the asset in the portfolio indefinitely.
- **Proposed Remedy**:
  1. For small target weights ($w_{\text{targ}} > 0.0$), scale $\delta_i \le 0.40 \cdot w_{\text{targ}}$, ensuring $L_i = 0.60 \cdot w_{\text{targ}} > 0$.
  2. Explicitly bypass no-trade buffer suppression for fresh entries ($w_{\text{curr}} == 0.0 \land w_{\text{targ}} > 0.0$) and full exits ($w_{\text{targ}} == 0.0 \land w_{\text{curr}} > 0.0$).
- **Exact Code Change**:
  ```python
  # portfolio_allocator.py:926
  if w_targ > 0.0:
      delta_i = min(delta_i, w_targ * 0.40)

  L_i = max(0.0, w_targ - delta_i)
  U_i = w_targ + delta_i
  buffer_bands[sym] = (L_i, U_i, delta_i)

  is_new_entry = (w_curr == 0.0 and w_targ > 0.0)
  is_full_exit = (w_targ == 0.0 and w_curr > 0.0)

  if (L_i <= w_curr <= U_i) and not is_new_entry and not is_full_exit:
      new_weights[sym] = w_curr
      skipped_count += 1
      # ...
  ```

---

### V6-10 [🟠 HIGH]: Black-Litterman Piecewise Step Discontinuity & Gradient Explosion in SLSQP
- **Affected File & Lines**: `trading_system/src/analysis/portfolio_optimizer.py:209-221`
- **Component**: `calculate_black_litterman_weights()`
- **Mathematical Failure Mechanism**:
  The SLSQP objective switches conditionally per function evaluation:
  - If $w^T \mu_{\text{BL}} \le r_f$: Quadratic utility maximization $- (w^T \mu - \frac{1}{2} \lambda w^T \Sigma w)$ (unit: return).
  - If $w^T \mu_{\text{BL}} > r_f$: Negative Sharpe ratio $-\frac{w^T \mu - r_f}{\sqrt{w^T \Sigma w}}$ (dimensionless).
  This introduces an artificial step discontinuity of $\Delta f \approx 0.05 \sim 1.0$ across the hyperplane $w^T \mu = r_f$. Finite difference gradient evaluations $\frac{f(w+\epsilon) - f(w)}{\epsilon}$ explode to $\sim 10^8$, breaking the BFGS approximate Hessian matrix and causing SLSQP to abort with line search failure, triggering unintended fallback to Risk Parity.
- **Proposed Remedy**:
  Determine the formulation globally at problem level before calling `minimize`:
  If $\max_i \mu_{\text{BL}, i} \le r_f$, excess return is impossible across the entire simplex $\sum w_i = 1$; execute pure Quadratic Utility Maximization.
  Otherwise, evaluate Sharpe ratio with a smooth quadratic penalty function below $r_f$, ensuring $C^1$ continuity everywhere.
- **Exact Code Change**:
  ```python
  # portfolio_optimizer.py:207
  lambda_aversion = 2.5
  all_negative_excess = bool(np.max(mu_bl) <= risk_free_rate)

  def objective(w):
      w = np.asarray(w)
      port_ret = float(w @ mu_bl)
      port_var = float(w @ cov_bl @ w)
      port_vol = float(np.sqrt(max(1e-8, port_var)))

      if all_negative_excess:
          return - (port_ret - 0.5 * lambda_aversion * port_var)
      else:
          excess = port_ret - risk_free_rate
          return - excess / port_vol if excess > 0 else (0.5 * lambda_aversion * port_var - excess * 10.0)
  ```

---

### V6-11 [🟠 HIGH]: EVT-POT Quantile Inversion ($u \le q_\alpha$) & Non-Regular GPD Shape Bounds ($\xi \ge -0.5$)
- **Affected File & Lines**: `trading_system/src/risk/portfolio_allocator.py:341-344, 383-395`
- **Component**: `PortfolioAllocator.estimate_evt_cvar()`
- **Mathematical Failure Mechanism**:
  In quiet market regimes with mild positive mean returns, $u = \max(q_{0.90}, \mu_L + 1.5\sigma_L)$ can exceed $q_\alpha$ (e.g. $u > q_{0.95}$).
  When $u > VaR_\alpha$, the tail exceedance ratio $\text{tail\_ratio} = \frac{N}{n_u}(1 - \alpha) > 1.0$.
  Substituting into $VaR_\alpha = u + \frac{\beta}{\xi}(\text{tail\_ratio}^{-\xi} - 1)$ yields $VaR_\alpha < u$, extrapolating backwards into the center of the distribution where GPD does not hold.
  Furthermore, $\xi$ was only bounded from above `min(xi, 0.50)` without a lower bound $\xi \ge -0.50$, violating the regularity condition for maximum likelihood estimation of GPD parameters (Smith 1985).
- **Proposed Remedy**:
  Cap threshold $u \le \text{quantile}(\text{losses}, \min(0.92, \alpha - 0.02))$ and clamp shape parameter $\xi \in [-0.50, 0.50]$.
- **Exact Code Change**:
  ```python
  # portfolio_allocator.py:341
  u_quantile = float(np.quantile(losses, quantile_threshold))
  u_volatility = float(np.mean(losses) + 1.5 * sigma_l)
  u_max_allowed = float(np.quantile(losses, min(0.92, confidence - 0.02)))
  u = min(max(u_quantile, u_volatility), u_max_allowed)
  exceedances = losses[losses > u] - u

  # portfolio_allocator.py:383
  if beta > 1e-8 and xi < 0.95 and np.isfinite(xi) and np.isfinite(beta):
      xi_clamped = float(np.clip(xi, -0.50, 0.50))
      tail_ratio = (N / n_u) * (1.0 - confidence)
      # ...
  ```

---

### V6-12 [🟠 HIGH]: Rockafellar-Uryasev Convex CVaR L1 Smoothing & Vectorized Constraint Callbacks
- **Affected File & Lines**: `trading_system/src/risk/portfolio_allocator.py:1381-1408`
- **Component**: `PortfolioAllocator.optimize_rockafellar_uryasev_cvar()`
- **Mathematical Failure Mechanism**:
  1. The objective function contains an explicit non-smooth L1 turnover penalty $|w_i - w_{\text{prev}, i}|$ whose gradient jumps between $+1$ and $-1$, causing SLSQP line-search breakdowns with `Positive directional derivative for linesearch`.
  2. Auxiliary linear CVaR constraints $u_t + r_t^T w + \alpha \ge 0$ were constructed as $T$ separate scalar constraint dictionaries in a loop, generating $>6,000$ Python callbacks per iteration and causing timeout.
- **Proposed Remedy**:
  1. Replace L1 norm with Pseudo-Huber smoothing: $\phi_\epsilon(w - w_{\text{prev}}) = \sqrt{(w - w_{\text{prev}})^2 + 10^{-6}}$, restoring $C^2$ differentiability.
  2. Vectorize $T$ linear CVaR constraints into a single array-valued constraint: $\mathbf{u} + R \mathbf{w} + \alpha \mathbf{1} \ge \mathbf{0}$.
- **Exact Code Change**:
  ```python
  # portfolio_allocator.py:1386
  risk_term = float(w.T @ cov_mat @ w)
  smooth_diff = np.sqrt((w - w_prev_vec) ** 2 + 1e-6)
  turnover_term = float(np.sum((c_vec + turnover_penalty_l1) * smooth_diff))
  cvar_val = float(alpha + cvar_coef * np.sum(u))

  # portfolio_allocator.py:1403
  constraints = [
      {'type': 'eq', 'fun': lambda x: np.sum(x[:N]) - 1.0},
      {'type': 'ineq', 'fun': lambda x: x[N + 1:N + 1 + T] + (r_mat @ x[:N]) + x[N]}
  ]
  ```

---

### V6-13 [🟠 HIGH]: CrisisDetector Recovery Latch Suppressing Defensive WATCH State Haircuts
- **Affected File & Lines**: `trading_system/src/risk/risk_manager.py:282-284, 418-434`
- **Component**: `CrisisDetector._check_recovery()` & `get_crisis_position_multiplier()`
- **Mathematical Failure Mechanism**:
  During recovery mode, `self._recovery_days` increments up to 20. However, once `_recovery_days >= 20`, `self._recovery_mode` was **never reset to `False`**.
  If market risk later escalates to `CrisisLevel.WATCH` (which requires a 30% defensive haircut, multiplier 0.70), `if self._recovery_mode:` evaluates to `True` with progress = 1.0, returning $0.15 + 0.85(1.0) = 1.00$ (100% full capacity), bypassing the 0.70 multiplier.
- **Proposed Remedy**:
  1. Reset `self._recovery_mode = False` and `self._recovery_days = 0` when `_recovery_days >= 20`.
  2. Gate recovery multiplier logic strictly on `self.crisis_level == CrisisLevel.NONE`.
- **Exact Code Change**:
  ```python
  # risk_manager.py:282
  if self._recovery_mode:
      self._recovery_days = (self._recovery_days or 0) + 1
      if self._recovery_days >= 20:
          self._recovery_mode = False
          self._recovery_days = 0

  # risk_manager.py:431
  base = multipliers.get(self.crisis_level, 1.0)
  if self._recovery_mode and self.crisis_level == CrisisLevel.NONE:
      progress = min(1.0, (self._recovery_days or 1) / 20.0)
      return 0.15 + (1.0 - 0.15) * progress
  return base
  ```

---

### V6-14 [🟠 HIGH]: Primary Missing Reason Frequency Selector Distortion
- **Affected File & Lines**: `trading_system/src/analysis/coverage_analyzer.py:220-226`
- **Component**: `StrategyCoverageAnalyzer.generate_coverage_report()`
- **Mathematical Failure Mechanism**:
  `top_reason` was extracted via `list(reasons.keys())[0] if reasons else "None (100% Valid)"`. Because dictionary insertion order is fixed (`INSUFFICIENT_PRICE_HISTORY` is checked before `NO_FUNDAMENTAL_DATA`), if 1 stock is missing price history and 150 stocks are missing quarterly filings, the report shows `INSUFFICIENT_PRICE_HISTORY` as the primary reason, severely distorting data audit visibility.
- **Proposed Remedy**:
  Extract the statistical mode of the missing reason distribution:
  `top_reason = max(reasons, key=reasons.get) if reasons else "None (100% Valid)"`.
- **Exact Code Change**:
  ```python
  # coverage_analyzer.py:224
  reasons = s_info.get('reasons', {})
  top_reason = max(reasons, key=reasons.get) if reasons else "None (100% Valid)"
  lines.append(f"{s_name:<22}{v_cnt:<15}{m_cnt:<15}{cov:>6.1f}%          {top_reason:<30}")
  ```

---

### V6-15 [🟡 MEDIUM]: Downside Co-Semivariance Equicorrelation Shrinkage Erasing Negative Hedging
- **Affected File & Lines**: `trading_system/src/risk/portfolio_allocator.py:151-157`
- **Component**: `PortfolioAllocator.compute_downside_semi_cov()`
- **Mathematical Failure Mechanism**:
  The regularizing target matrix was computed as `reg_target = np.outer(diag_stds, diag_stds) * 0.5; np.fill_diagonal(reg_target, np.diag(blended_semi))`.
  This sets off-diagonal elements to $+0.50$ correlation, which artificially shrinks negative covariances of hedging assets (inverse ETFs `114800`/`PSQ`, cash proxies, gold) towards $+0.50$, destroying negative hedging benefits during downside risk optimization.
- **Proposed Remedy**:
  Use standard Ledoit-Wolf diagonal variance shrinkage target $\mathbf{T} = \text{diag}(\Sigma^-)$, shrinking covariances towards zero (independence) without positive bias.
- **Exact Code Change**:
  ```python
  # portfolio_allocator.py:151
  diag_stds = np.sqrt(np.maximum(np.diag(blended_semi), 1e-8))
  reg_target = np.diag(np.diag(blended_semi))
  np.fill_diagonal(reg_target, np.diag(blended_semi))
  ```

---

### V6-16 [🟡 MEDIUM]: RMT Marchenko-Pastur Residual Eigenvalue Noise Variance Over-Shrinking
- **Affected File & Lines**: `trading_system/src/risk/fx_adjusted_covariance.py:151-165`
- **Component**: `FXAdjustedCovarianceEngine.denoise_covariance_marchenko_pastur()`
- **Mathematical Failure Mechanism**:
  Residual noise variance $\sigma^2$ was hardcoded as `sigma_sq = 1.0`.
  In equity markets, the market mode ($\lambda_1$) accounts for $40\% \sim 70\%$ of the correlation trace. The actual residual noise variance is $\sigma_{\text{noise}}^2 = \frac{N - \lambda_1}{N - 1} \approx 0.35 \sim 0.60$.
  Hardcoding $\sigma^2 = 1.0$ inflates the Marchenko-Pastur upper bound $\lambda_+ = \sigma^2 (1 + \sqrt{1/q})^2$ by up to $2\times$, erroneously truncating genuine factor eigenvalues ($\lambda \in [1.2, 2.5]$) as noise.
- **Proposed Remedy**:
  Estimate $\sigma^2$ dynamically from residual eigenvalues excluding the market mode ($\lambda_1$):
  $\sigma^2 = \text{clip}\left(\frac{1}{N-1}\sum_{i=2}^N \lambda_i, 0.10, 1.0\right)$.
- **Exact Code Change**:
  ```python
  # fx_adjusted_covariance.py:153
  sigma_sq = float(np.mean(eigenvals[1:])) if len(eigenvals) > 1 else 1.0
  sigma_sq = max(0.10, min(1.0, sigma_sq))
  lambda_plus = sigma_sq * (1.0 + np.sqrt(1.0 / q)) ** 2 * float(noise_spread_factor)
  ```

---

## 3. Domain 4: Execution OMS & Transaction Costs (V6-25 ~ V6-31)

### V6-25 [🔴 CRITICAL]: Cross-Market Currency Denominator Mismatch in ExecutionOMSEngine
- **Affected File & Lines**: `trading_system/src/execution/oms_engine.py:325-340, 500-504, 573-585`
- **Component**: `ExecutionOMSEngine.generate_order_plan()` & Gate 8 Inverse Hedge
- **Microstructure Failure Mechanism**:
  `total_capital` is supplied in KRW (e.g. 100,000,000 KRW). Target amount is $100M \times 0.05 = 5,000,000$ KRW.
  For US equities (`SP500`, `NASDAQ`, `RUSSELL2000`), `target_price` is quoted in USD (e.g. `$150.00` for AAPL).
  The order quantity was calculated as: `raw_quantity = int(target_amount // target_price) = 5,000,000 // 150 = 33,333 shares`.
  Purchasing 33,333 shares of AAPL costs **$5,000,000 USD** (~6.75 billion KRW), causing a **1,350x position explosion**!
  The identical bug occurred in Gate 8 inverse ETF hedging with `PSQ`/`SH` ($30M KRW // $15 USD = 2,000,000 shares = $30M USD).
- **Proposed Remedy**:
  1. Add `usdkrw_rate: float = 1350.0` parameter to `generate_order_plan()`.
  2. For non-KRX equities and global inverse hedges, convert KRW target amount to USD before share calculation:
     $$\text{effective\_target\_amount} = \begin{cases} \text{target\_amount}, & \text{if KRX} \\ \frac{\text{target\_amount}}{\text{fx\_rate}}, & \text{if US / Global} \end{cases}$$
- **Exact Code Change**:
  ```python
  # oms_engine.py:277
  def generate_order_plan(
      ...,
      usdkrw_rate: float = 1350.0,
      **kwargs
  ) -> List[Dict[str, Any]]:
      # ...
      try:
          fx_rate = float(usdkrw_rate) if (usdkrw_rate is not None and math.isfinite(float(usdkrw_rate)) and float(usdkrw_rate) > 0) else 1350.0
      except (ValueError, TypeError):
          fx_rate = 1350.0

      # oms_engine.py:500
      effective_target_amount = target_amount if is_krx else (target_amount / fx_rate)
      raw_quantity = int(effective_target_amount // target_price) if target_price > 0 else 0

      # oms_engine.py:580
      h_amount_local = h_amount if str(first_market).upper() in ["KOSPI", "KOSDAQ", "KRX"] or str(h_sym).isdigit() else (h_amount / fx_rate)
      raw_h_qty = int(h_amount_local // hedge_price) if hedge_price > 0 else 0
  ```

---

### V6-26 [🔴 CRITICAL]: Return Scale Ambiguity in OMS Safety Gates 7.2 & 7.4
- **Affected File & Lines**: `trading_system/src/execution/oms_engine.py:426-437, 479-487`
- **Component**: `ExecutionOMSEngine.generate_order_plan()` Gates 7.2 & 7.4
- **Microstructure Failure Mechanism**:
  Upstream data components compute `change_pct` in percentage format (e.g. `+5.2` for $+5.2\%$).
  Gate 7.2 evaluated `c_flt >= 0.295` directly. When `change_pct = 5.2`, `5.2 >= 0.295` evaluates to `True`, logging a false-positive upper-limit lock warning (`locked at upper limit (+520.00%)`) and dropping buy orders for **all winning stocks with daily gains $> +0.295\%$**!
  Similarly, Gate 7.4 evaluated `gap_ret = -1.0 <= -3.0 * 0.02 = -0.06`, falsely discarding normal $-1.0\%$ pullbacks as toxic $-100\%$ adverse gap shocks.
- **Proposed Remedy**:
  Perform automatic dimensionless return normalization across all OMS gates:
  $$c_{\text{norm}} = \begin{cases} \frac{c}{100.0}, & \text{if } |c| > 1.0 \\ c, & \text{otherwise} \end{cases}$$
- **Exact Code Change**:
  ```python
  # oms_engine.py:426 (Gate 7.2)
  change_pct = pred.get("change_pct") or pred.get("daily_return")
  if change_pct is not None:
      raw_c = float(change_pct)
      c_norm = raw_c / 100.0 if abs(raw_c) > 1.0 else raw_c
      if c_norm >= 0.295 and action == "BUY":
          logger.warning(f"[OMS GATE 7] {sym} locked at upper limit (+{c_norm:.2%}), skipping buy execution.")
          continue
      elif c_norm <= -0.295:
          logger.warning(f"[OMS GATE 7] {sym} locked at lower limit ({c_norm:.2%}) - complete liquidity freeze; skipping new entry...")
          continue

  # oms_engine.py:480 (Gate 7.4)
  vol_20d = float(pred.get("volatility_20d", 0.02) or 0.02)
  raw_gap = float(change_pct or 0.0)
  gap_ret = raw_gap / 100.0 if abs(raw_gap) > 1.0 else raw_gap
  if action == "BUY" and gap_ret <= -3.0 * max(vol_20d, 0.015):
      logger.warning(f"[OMS GATE 7.4] {sym} adverse gap {gap_ret:.2%} <= -3sigma, skipping toxic order flow.")
      continue
  ```

---

### V6-27 [🟠 HIGH]: Almgren-Chriss Slicing Residual Underflow & Non-Negative Tranches
- **Affected File & Lines**: `trading_system/src/execution/oms_engine.py:767-789`
- **Component**: `AlmgrenChrissScheduler.compute_trajectory()`
- **Microstructure Failure Mechanism**:
  1. `eta = 0.5 * (max(daily_volatility, 0.01) / max(adv, 1.0))` with `adv` in currency ($10^9$ KRW) produced $\eta \approx 10^{-11}$, causing $\kappa = \sqrt{\lambda \sigma^2 / \eta} > 20$, which forces $96.5\%$ of volume into slice 1.
  2. Rounding reconciliation `diff_total = total_quantity - int(np.sum(alloc)); alloc[-1] += diff_total` can subtract more than `alloc[-1]`, generating a negative order slice (e.g. `alloc[-1] = -2`), which causes broker API rejection or accidental short selling.
- **Proposed Remedy**:
  1. Standardize temporary impact parameter $\eta = 0.5 \cdot \max(\sigma_{\text{daily}}, 0.01)$ and clamp $\kappa \in [0.01, 3.0]$.
  2. Reconcile integer rounding discrepancies incrementally while guaranteeing $\forall i, \text{alloc}_i \ge 0$.
- **Exact Code Change**:
  ```python
  # oms_engine.py:767
  eta = 0.5 * max(daily_volatility, 0.01)
  kappa = float(np.clip(np.sqrt(lambda_urg * (daily_volatility ** 2) / max(eta, 1e-8)), 0.01, 3.0))
  # ...
  # oms_engine.py:786
  diff_total = total_quantity - int(np.sum(alloc))
  if diff_total > 0:
      for i in range(diff_total):
          alloc[i % n_slices] += 1
  elif diff_total < 0:
      rem = abs(diff_total)
      for i in range(n_slices - 1, -1, -1):
          sub = min(alloc[i], rem)
          alloc[i] -= sub
          rem -= sub
          if rem <= 0:
              break
  return [int(x) for x in alloc]
  ```

---

### V6-28 [🟠 HIGH]: Friction Cost Double-Deduction in OMS Gate 7.3
- **Affected File & Lines**: `trading_system/src/execution/oms_engine.py:440-476`, `trading_system/src/ai/ensemble_scorer.py:2373`
- **Component**: `ExecutionOMSEngine.generate_order_plan()` Gate 7.3
- **Microstructure Failure Mechanism**:
  `ensemble_scorer.py:2373` already deducts round-trip friction costs (STT tax, spread, brokerage, market impact) to produce net return in `ensemble_expected_return`.
  In OMS Gate 7.3, when `expected_return` was absent, `oms_engine` took `ensemble_expected_return` and tested `exp_ret_frac < (friction_cost + safety_margin)`.
  This enforced a $200\%$ friction cost penalty ($2 \times \text{cost} + \text{margin}$), causing false-positive rejections of profitable alpha signals.
- **Proposed Remedy**:
  Distinguish gross vs net expected return:
  If gross `expected_return` is present, hurdle = `friction_cost + safety_margin`.
  If only net `ensemble_expected_return` is present, hurdle = `safety_margin`.
- **Exact Code Change**:
  ```python
  # oms_engine.py:469
  safety_margin = 0.0010  # 0.10% safety margin
  if "expected_return" in pred and pred["expected_return"] is not None:
      raw_exp_ret = float(pred["expected_return"])
      exp_ret_frac = raw_exp_ret / 100.0 if abs(raw_exp_ret) > 1.0 else raw_exp_ret
      hurdle = friction_cost + safety_margin
  else:
      raw_exp_ret = float(pred.get("ensemble_expected_return", 0.0) or 0.0)
      exp_ret_frac = raw_exp_ret / 100.0 if abs(raw_exp_ret) > 1.0 else raw_exp_ret
      hurdle = safety_margin

  if exp_ret_frac < hurdle:
      logger.info(f"[OMS GATE 7] {sym} net alpha {exp_ret_frac:.4%} < hurdle ({hurdle:.4%}), skipping.")
      continue
  ```

---

### V6-29 [🟠 HIGH]: Turnover Hysteresis Deadlock Trapping Liquidated Positions
- **Affected File & Lines**: `trading_system/src/execution/turnover_optimizer.py:58-86`
- **Component**: `TurnoverOptimizer.optimize_allocations()`
- **Microstructure Failure Mechanism**:
  When a stock is dropped from the target portfolio (`raw_w = 0.0`), if the current holding is small (`curr_w = 0.04 < 0.05 threshold`), `weight_delta < self.turnover_threshold_pct` evaluates to `True`.
  The method sets `final_w = curr_w = 0.04` and `action = "HOLD"`.
  The full liquidation signal is completely blocked, and the position remains trapped in the portfolio indefinitely.
- **Proposed Remedy**:
  Exempt full position liquidations (`raw_w == 0.0 \land curr_w > 0.0`) and fresh new entries (`curr_w == 0.0 \land raw_w > 0.0`) from turnover hysteresis damping.
- **Exact Code Change**:
  ```python
  # turnover_optimizer.py:71
  is_full_exit = (raw_w == 0.0 and curr_w > 0.0)
  is_fresh_entry = (curr_w == 0.0 and raw_w > 0.0)
  if not is_full_exit and not is_fresh_entry and (weight_delta < self.turnover_threshold_pct or amount_delta < self.min_rebalance_delta_krw):
      final_w = curr_w
      action = "HOLD"
      total_turnover_reduced += amount_delta
  else:
      final_w = raw_w
      action = "BUY" if raw_w > curr_w else "SELL"
  ```

---

### V6-30 [🟡 MEDIUM]: Slippage Sign Inversion for BUY_HEDGE Orders & SQLite Connection Leak
- **Affected File & Lines**: `trading_system/src/execution/slippage_feedback.py:70-135, 105`
- **Component**: `SlippageFeedbackEngine.calculate_realized_slippage()`
- **Microstructure Failure Mechanism**:
  1. `sign = 1.0 if str(act).strip().upper() in ["BUY", "LONG"] else -1.0` evaluated to `-1.0` for Gate 8 inverse hedge orders (`action = "BUY_HEDGE"`). When execution price exceeded target price (adverse slippage), the calculation recorded negative slippage (price improvement), inverting the feedback loop.
  2. `conn.close()` was placed inside `try:` without `finally:`, leaking SQLite connections on database query exceptions.
- **Proposed Remedy**:
  1. Match all buy variations: `(act_str.startswith("BUY") or act_str in ["LONG", "BUY_HEDGE"])`.
  2. Protect database connection closure with a guaranteed `finally: conn.close()` block.
- **Exact Code Change**:
  ```python
  # slippage_feedback.py:70
  conn = sqlite3.connect(self.db_path, timeout=30.0)
  conn.execute("PRAGMA journal_mode = WAL;")
  conn.execute("PRAGMA busy_timeout = 30000;")
  try:
      cursor = conn.cursor()
      # ...
      act_str = str(act).strip().upper()
      sign = 1.0 if (act_str.startswith("BUY") or act_str in ["LONG", "BUY_HEDGE"]) else -1.0
      slip_bps = sign * ((pe - pt) / pt) * 10000.0
      # ...
  finally:
      conn.close()
  ```

---

### V6-31 [🟡 MEDIUM]: SmartOrderRouter ATS Residual Misrouting & Duplicate Order Flooding
- **Affected File & Lines**: `trading_system/src/execution/sor_router.py:67-108`
- **Component**: `SmartOrderRouter.route_order()`
- **Microstructure Failure Mechanism**:
  When sorting venues by effective price, if an alternative trading venue (e.g. Nextrade ATS `NXT`) had the best price for 50 shares, `sorted_venues[0]` was `NXT`.
  Residual volume (950 shares) was assigned to `primary_v = sorted_venues[0]` (NXT again!), creating duplicate allocations to the ATS far exceeding available depth.
- **Proposed Remedy**:
  1. Specifically identify the lit exchange primary venue (`is_primary=True` or `venue_id in ("PRIMARY", "KRX", "NYSE", "NASDAQ")`).
  2. Merge residual quantity into existing primary venue allocation record if already present.
- **Exact Code Change**:
  ```python
  # sor_router.py:99
  if remaining_qty > 0 and sorted_venues:
      primary_v = next((v for v in sorted_venues if v.get("is_primary") or str(v.get("venue_id", "")).upper() in ["PRIMARY", "KRX", "NYSE", "NASDAQ"]), sorted_venues[0])
      p_id = str(primary_v.get("venue_id") or "PRIMARY")
      fallback_price = _get_float(primary_v, "ask_price" if is_buy else "bid_price", 0.0)
      
      merged = False
      for alloc in allocations:
          if alloc["venue_id"] == p_id:
              alloc["allocated_quantity"] += remaining_qty
              merged = True
              break
      if not merged:
          allocations.append({
              "venue_id": p_id,
              "symbol": clean_symbol,
              "action": act,
              "allocated_quantity": remaining_qty,
              "target_price": max(0.0, fallback_price)
          })
  ```

---

## 4. Existing Test Coverage & Verification Strategy

### 4.1 Existing Test Inventory for Domain 2 & Domain 4

| Task | Domain | Target Source File | Existing Test Files in `tests/` |
|------|--------|-------------------|---------------------------------|
| **V6-09** | 2 | `src/risk/portfolio_allocator.py` | `tests/test_portfolio_allocator.py` (`TestDynamicBandRebalancing`), `tests/test_challenger_portfolio_stress.py` |
| **V6-10** | 2 | `src/analysis/portfolio_optimizer.py` | `tests/test_black_litterman.py`, `tests/test_adversarial_challenger_1.py` |
| **V6-11** | 2 | `src/risk/portfolio_allocator.py` | `tests/test_portfolio_allocator.py` (`TestEVTCVaR`), `tests/test_sigmoid_smooth_cvar.py` |
| **V6-12** | 2 | `src/risk/portfolio_allocator.py` | `tests/test_unified_portfolio_engine.py`, `tests/test_world_class_quant_enhancements.py` |
| **V6-13** | 2 | `src/risk/risk_manager.py` | `tests/test_risk_manager.py`, `tests/test_challenger_m1_2.py` |
| **V6-14** | 2 | `src/analysis/coverage_analyzer.py` | `tests/test_kst_and_coverage_reasoning.py`, `tests/test_r3_coverage_and_universe.py` |
| **V6-15** | 2 | `src/risk/portfolio_allocator.py` | `tests/test_portfolio_allocator.py`, `tests/test_six_structural_improvements.py` |
| **V6-16** | 2 | `src/risk/fx_adjusted_covariance.py` | `tests/test_portfolio_optimizer_and_oms.py`, `tests/test_world_class_quant_enhancements.py` |
| **V6-25** | 4 | `src/execution/oms_engine.py` | `tests/test_portfolio_optimizer_and_oms.py`, `tests/test_phase3_phase4_hmm_copula_oms.py` |
| **V6-26** | 4 | `src/execution/oms_engine.py` | `tests/test_portfolio_optimizer_and_oms.py`, `tests/test_krx_overnight_and_hurdle.py` |
| **V6-27** | 4 | `src/execution/oms_engine.py` | `tests/test_portfolio_optimizer_and_oms.py`, `tests/test_apex_tier_quant_enhancements.py` |
| **V6-28** | 4 | `src/execution/oms_engine.py` | `tests/test_krx_overnight_and_hurdle.py`, `tests/test_adaptive_execution_feedback.py` |
| **V6-29** | 4 | `src/execution/turnover_optimizer.py` | `tests/test_institutional_next_level.py` |
| **V6-30** | 4 | `src/execution/slippage_feedback.py` | `tests/test_slippage_feedback.py`, `tests/test_adaptive_execution_feedback.py` |
| **V6-31** | 4 | `src/execution/sor_router.py` | `tests/test_phase9_verification.py` |

### 4.2 Test Updates & New Test Cases Needed

1. **V6-09**: Add test `test_dynamic_buffer_band_new_entry_and_full_exit_bypass` in `tests/test_portfolio_allocator.py` to assert $w_{\text{curr}}=0 \implies \text{BUY}$ and $w_{\text{targ}}=0 \implies \text{SELL}$.
2. **V6-10**: Add test `test_black_litterman_all_negative_excess_returns` in `tests/test_black_litterman.py` asserting smooth convergence when views $\le r_f$.
3. **V6-11**: Add test `test_evt_cvar_quiet_regime_threshold_ceiling` in `tests/test_portfolio_allocator.py` asserting $u \le q_\alpha$ and regular $\xi \in [-0.5, 0.5]$.
4. **V6-12**: Add test `test_rockafellar_uryasev_cvar_speed_and_smoothness` with $T=120$ scenarios verifying vector constraint execution under 50ms.
5. **V6-13**: Add test `test_crisis_detector_recovery_reset_and_subsequent_watch_haircut` in `tests/test_risk_manager.py` verifying 20-day recovery auto-reset and subsequent 0.70 WATCH multiplier.
6. **V6-14**: Add test in `tests/test_kst_and_coverage_reasoning.py` verifying modal frequency missing reason selection.
7. **V6-15**: Add test in `tests/test_portfolio_allocator.py` verifying diagonal shrinkage preserves negative semi-covariance off-diagonals.
8. **V6-16**: Add test in `tests/test_portfolio_optimizer_and_oms.py` verifying dynamic residual noise variance estimation.
9. **V6-25**: Add test in `tests/test_portfolio_optimizer_and_oms.py` verifying US equity ($150 USD) quantity calculation uses currency conversion (e.g. 5M KRW / 1350 = ~24 shares, not 33,333 shares).
10. **V6-26**: Add test in `tests/test_portfolio_optimizer_and_oms.py` verifying percentage vs decimal return scale normalization in Gates 7.2 & 7.4.
11. **V6-27**: Add test for `AlmgrenChrissScheduler.compute_trajectory` verifying non-negative tranches on small and odd quantities.
12. **V6-28**: Add test verifying single friction cost deduction for net `ensemble_expected_return`.
13. **V6-29**: Add test for `TurnoverOptimizer` asserting full liquidation bypasses hysteresis.
14. **V6-30**: Add test for `BUY_HEDGE` slippage sign and exception safety in `tests/test_slippage_feedback.py`.
15. **V6-31**: Add test for `SmartOrderRouter` ATS residual merging to primary venue in `tests/test_phase9_verification.py`.

---

## 5. Risk Assessment & Architectural Invariants

- **Simplex Invariants**: $\sum w_i = 1.0$ must hold strictly after Black-Litterman, Rockafellar-Uryasev, and TurnoverOptimizer rebalancing.
- **Safety Gate Supremacy**: OMS Safety Gates (Kill Switch, SEVERE Crisis Gating, Limit Lock, Adverse Gap) must never be weakened or bypassed.
- **Currency Isolation**: KRW vs USD currency boundaries must be rigorously respected between upstream signal generation (percentage returns) and downstream order execution (local exchange currency).
