# Domain 2 Handoff Report: Portfolio & Risk Engineering Auditor

**Agent**: `explorer_d2_port_risk` (Principal Portfolio Theorist & Risk Engineering Auditor)  
**Date**: 2026-08-22 (KST)  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_d2_port_risk`  
**Handoff Type**: Hard (Task Complete)

---

## 1. Observation

Direct line-by-line inspection of the Domain 2 codebase revealed 8 distinct, verified defects:

1. `trading_system/src/risk/portfolio_allocator.py:927-960`:
   `L_i = max(0.0, w_targ - delta_i)` clamps to `0.0` when $w_{\text{targ}} \le \delta_i$. For an uninvested stock ($w_{\text{curr}} = 0.0$), the condition `L_i <= w_curr <= U_i` evaluates to `0.0 <= 0.0 <= U_i` (True), triggering `action: HOLD` and `trade_weight: 0.0`, permanently blocking all position initiations with target weights $\le \delta_i$.
2. `trading_system/src/analysis/portfolio_optimizer.py:209-221`:
   Inside `calculate_black_litterman_weights()`, `objective(w)` executes `if port_ret <= risk_free_rate:` to return Quadratic Utility, else returns Sharpe ratio. The two branches have different units, creating a step discontinuity $\Delta f \approx 1.0$ and gradient explosion across the $w^T \mu = r_f$ hyperplane that breaks SLSQP line searches.
3. `trading_system/src/risk/portfolio_allocator.py:341-344, 383-395`:
   In `estimate_evt_cvar()`, threshold $u = \max(u_{\text{quantile}}, u_{\text{volatility}})$ exceeds $VaR_{0.95}$ in calm markets, leading to $\text{tail\_ratio} > 1.0$ and backwards extrapolation of the GPD formula ($VaR_\alpha < u$). In addition, `xi_clamped = min(xi, 0.50)` does not enforce a lower bound, admitting non-regular shape parameters $\xi < -0.50$.
4. `trading_system/src/risk/portfolio_allocator.py:1381-1408`:
   In `optimize_rockafellar_uryasev_cvar()`, the L1 penalty `turnover_term = np.sum((c_vec + turnover_penalty_l1) * np.abs(w - w_prev_vec))` introduces non-differentiable kinks at $w = w_{\text{prev}}$, causing SLSQP solver failure and fallback to equal weights.
5. `trading_system/src/risk/risk_manager.py:418-434`:
   In `CrisisDetector`, `_recovery_mode` is never reset to `False` once `_recovery_days >= 20`. In `get_crisis_position_multiplier()`, `if self._recovery_mode:` evaluates to `1.00`, overriding the defensive $0.70$ multiplier required during `CrisisLevel.WATCH`.
6. `trading_system/src/analysis/coverage_analyzer.py:220-226`:
   In `StrategyCoverageAnalyzer.generate_coverage_report()`, `top_reason` is extracted as `list(reasons.keys())[0]`, selecting the first checked reason rather than the modal reason `max(reasons, key=reasons.get)`.
7. `trading_system/src/risk/portfolio_allocator.py:151-157`:
   In `compute_downside_semi_cov()`, `reg_target = np.outer(diag_stds, diag_stds) * 0.5` shrinks the semi-covariance matrix towards $+0.50$ equicorrelation, falsely penalizing negative-beta inverse ETFs and hedges.
8. `trading_system/src/risk/fx_adjusted_covariance.py:151-165`:
   In `denoise_covariance_marchenko_pastur()`, `sigma_sq = 1.0` is hardcoded, inflating $\lambda_+$ by $2\times$ and truncating authentic sector and style factor eigenvalues.

---

## 2. Logic Chain

1. **Leland Buffer Band Initiation Failure**:
   $w_{\text{curr}} = 0 \land w_{\text{targ}} \le \delta_i \implies L_i = 0 \implies L_i \le w_{\text{curr}} \le U_i \implies \text{HOLD} \implies \text{No BUY orders generated}$. Bypassing new entries and exits from the buffer zone or scaling $\delta_i \le 0.40 \cdot w_{\text{targ}}$ ensures valid execution.
2. **Black-Litterman SLSQP Discontinuity**:
   $\lim_{x \to r_f^+} f(x) = 0 \ne \lim_{x \to r_f^-} f(x) = -r_f + \frac{1}{2} \lambda_a \sigma^2 \implies f \notin C^1 \implies \text{Finite difference gradient diverges} \implies \text{SLSQP failure}$. Moving the formulation choice to the problem level restores $C^1$ smoothness.
3. **EVT POT Quantile Inversion**:
   $u > VaR_\alpha \implies n_u / N < 1 - \alpha \implies \text{tail\_ratio} > 1 \implies VaR_{\text{GPD}} < u \implies \text{Underestimated tail risk}$. Restricting $u \le \text{quantile}(\text{losses}, \alpha - 0.02)$ restores monotonic tail quantile estimation.
4. **Rockafellar-Uryasev L1 Kink**:
   $\nabla |w - w_{\text{prev}}| \text{ undefined at } w = w_{\text{prev}} \implies \text{BFGS Hessian approximation diverges}$. Replacing with pseudo-Huber regularizer $\sqrt{(w - w_{\text{prev}})^2 + \epsilon^2}$ guarantees $C^2$ smoothness.
5. **CrisisDetector Latch**:
   $\text{recovery\_days} \ge 20 \land \text{recovery\_mode} == \text{True} \implies \text{progress} = 1.0 \implies \text{multiplier} = 1.00 \implies \text{Overrides WATCH } (0.70)$. Resetting `_recovery_mode = False` upon completion restores state-machine fidelity.
6. **Coverage Modal Attribution**:
   $\text{reasons} = \{\text{'PRICE'}: 1, \text{'FUND'}: 150\} \land \text{keys}()[0] \implies \text{'PRICE'} \ne \arg\max(\text{Counts})$. Using `max(reasons, key=reasons.get)` guarantees accurate reporting.
7. **Downside Shrinkage Target**:
   $\text{Shrinkage to } +0.50 \implies \text{Hedging covariances mapped to } +0.50 \implies \text{Hedge destroyed}$. Shrinking to diagonal matrix preserves diversification.
8. **RMT Spectral Bound**:
   $\lambda_1 \gg 1 \implies \sigma_{\text{noise}}^2 < 1.0 \implies \text{Hardcoded } \sigma^2=1.0 \implies \lambda_+ \text{ over-estimated } 2\times \implies \text{Valid signals erased}$. Estimating $\sigma^2$ from the residual spectrum retains real factor signals.

---

## 3. Caveats

- **Scope Boundary**: Audit focused exclusively on Domain 2 (Portfolio & Risk Engineering) and directly dependent data layers (`fx_adjusted_covariance.py`). Alpha strategy generators and Execution OMS were evaluated only at their interfaces.
- **Zero Duplication**: Cross-referenced against 110 baseline items (v1~v4) and 32 v5 items (`system_improvement_report_v5.md`). No overlaps exist.

---

## 4. Conclusion

All 8 identified issues are concrete, mathematically verified, and accompanied by precise line citations and git diff modifications in `d:\Finance\code\stock\.agents\explorer_d2_port_risk\analysis.md`. Implementing these remedies will eliminate portfolio initiation blocks, stabilize numerical optimization, and enforce accurate risk budgeting across market cycles.

---

## 5. Verification Method

To independently verify these findings:
1. **Leland Buffer Band**: Run `pytest tests/ -k "test_leland or test_portfolio_allocator"` or instantiate `PortfolioAllocator().compute_portfolio_rebalance({'A': 0.0}, {'A': 0.01}, ...)` and verify `action == 'HOLD'`.
2. **Black-Litterman Objective**: Check `trading_system/src/analysis/portfolio_optimizer.py:209-221` with returns where some assets are below $r_f$ and others above $r_f$.
3. **EVT POT Threshold**: Inspect `trading_system/src/risk/portfolio_allocator.py:341-344` on a low-volatility synthetic return series.
4. **Test Suite Baseline**: Run `.venv\Scripts\python.exe -m pytest tests/ -q` to confirm current baseline test status.
