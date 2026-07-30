# Deep-Dive Analysis of Milestone 3 Implementation

## 1. Scope & Objective
Milestone 3 focuses on Tail-Risk EVT-CVaR Loss Budget Constraints:
- Peaks-Over-Threshold (POT) GPD fitting via `scipy.stats.genpareto`.
- 3-tier fallback hierarchy (EVT-GPD -> Cornish-Fisher -> Empirical/Gaussian CVaR).
- Non-linear SLSQP optimization under EVT-CVaR loss budget constraint (`EVT_CVaR(w) <= max_cvar_limit`).
- Dynamic band-based rebalancing (Leland optimal buffer zones) & microstructure transaction cost sizing.

## 2. Implementation Verification

### A. EVT-GPD Fitting & Mathematical Formulation (`estimate_evt_cvar`)
- **Loss Conversion**: `losses = -returns_arr` correctly maps asset/portfolio return to loss distribution.
- **Threshold Selection**: `u = float(np.quantile(losses, quantile_threshold))` (default 90th percentile).
- **Exceedances Calculation**: `exceedances = losses[losses > u] - u`.
- **GPD Parameter Fitting**: `xi, _, beta = genpareto.fit(exceedances, floc=0)` fixes location at 0, fitting shape $\xi$ and scale $\beta$.
- **CVaR Closed-Form Formula**:
  - Tail ratio: $\frac{N}{n_u} (1 - \alpha)$.
  - $VaR_{evt} = u + \frac{\beta}{\xi} \left( \left( \frac{N}{n_u} (1 - \alpha) \right)^{-\xi} - 1 \right)$.
  - $CVaR_{evt} = \frac{VaR_{evt} + \beta - \xi u}{1 - \xi}$.
  - Gumbel limit ($|\xi| < 10^{-4}$): $VaR_{evt} = u - \beta \ln(\text{tail\_ratio})$, $CVaR_{evt} = VaR_{evt} + \beta$.
- **Clamping & Safety**:
  - $\xi$ is clamped to 0.50 max for tail index stability ($1 - \xi > 0.50$ prevents infinite variance/mean issues).
  - Validation checks: `beta > 1e-8`, `xi < 0.95`, non-NaN checks.

### B. 3-Tier Fallback Hierarchy
1. **Tier 1 (EVT-GPD)**: Triggered when $n_u \ge \text{min\_tail\_samples}$ (15) and GPD optimization converges safely.
2. **Tier 2 (Cornish-Fisher Expansion)**: Triggered when GPD fails or exceedance count is low. Computes skewness $S$ and excess kurtosis $K$, applying higher-moment quantile expansion to correct Gaussian VaR/CVaR.
3. **Tier 3 (Empirical / Small-N Gaussian)**: Triggered when $N < 10$ or Cornish-Fisher yields invalid values. Computes sample empirical CVaR or small-sample parametric Gaussian CVaR.

### C. SLSQP Non-linear Constraint Optimization
- `optimize_with_evt_cvar_constraint` in `PortfolioAllocator`:
  - Objective: $-(E[R] - \frac{1}{2} \gamma \sigma^2_p)$
  - Inequality constraint: $g(w) = \text{max\_cvar} - \text{EVT\_CVaR}(w) \ge 0$
  - Equality constraint: $\sum w_i = 1.0$
  - Bounds: $w_i \in [0, \text{max\_weight}]$
- `optimize_mean_variance` in `PortfolioOptimizer`:
  - Integrates `allocator.estimate_portfolio_evt_cvar` into SLSQP constraint list when `max_cvar_limit` is set.

### D. Dynamic Band-Based Rebalancing & Microstructure Costs
- **Leland Buffer Zone**: $\delta_i = \left( \frac{3 c_i w_i \sigma_i}{2 \gamma} \right)^{1/3}$, clamped to $[\delta_{\text{floor}}, \delta_{\text{cap}}]$.
- **Cost Structure ($c_i$)**:
  - Market-specific STT tax + brokerage fee (KOSPI 0.15%, KOSDAQ 0.18%, KONEX 0.10%, SP500 0.003%).
  - Dynamic spread: $S_i = \text{base\_spread} \times (ADV_{ref} / ADV_i)^{0.25} \times (\sigma_i / \sigma_0)^{0.50}$.
  - Square-root market impact: $\text{impact} = \gamma_{\text{impact}} \sigma_i \sqrt{\frac{\text{OrderVal}}{ADV_i}}$.
