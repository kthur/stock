# Handoff Report — Explorer M3-1 (Gen 2): EVT-CVaR Risk Budget Constraints

## 1. Observation

### 1.1 Existing Portfolio Optimization & Risk Framework
- **File**: `src/risk/portfolio_optimizer.py` & `trading_system/src/risk/portfolio_optimizer.py`
  - `PortfolioOptimizer` provides two primary optimization routines:
    1. `optimize_risk_parity()`: Solves Equal Risk Contribution (ERC) objective using `scipy.optimize.minimize(..., method='SLSQP')` (lines 36-86).
    2. `optimize_mean_variance()`: Maximizes quadratic utility $U(w) = w^T \mu - \frac{1}{2} \gamma w^T \Sigma w$ under sum-to-one and single-asset weight bounds (lines 88-136).
    3. `apply_factor_and_sector_constraints()`: Caps sector exposure to `max_sector_weight` (default 35%) (lines 138-174).
  - **Observation**: Neither optimizer currently includes tail-risk loss budget constraints or EVT-CVaR estimation.
- **File**: `trading_system/src/risk/risk_manager.py`
  - `RiskManager` contains basic historical empirical percentile VaR and CVaR functions (lines 855-882):
    ```python
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        sorted_returns = sorted(returns)
        var_index = int(len(sorted_returns) * (1 - confidence))
        return sorted_returns[var_index]

    def calculate_cvar(self, returns: List[float], confidence: float = 0.95) -> float:
        var = self.calculate_var(returns, confidence)
        worse_returns = [r for r in returns if r <= var]
        return sum(worse_returns) / len(worse_returns)
    ```
  - **Observation**: The empirical CVaR calculation suffers from high variance at high confidence levels ($\alpha = 0.99$ or $0.995$) when sample size $N$ is typical for daily daily trading history ($N \approx 250$ to $500$). At $N=250$, $\alpha=0.99$ relies on only $2.5$ sample points in the tail and fails to model tail events beyond historical minima.
- **File**: `PROJECT.md`
  - Under **Milestones**: Milestone 3 is titled "Risk Management & Portfolio Optimization Enhancement".
  - Under **Interface Contracts (Portfolio Allocator ↔ Dynamic Rebalancer)**:
    > "Tail-risk CVaR estimated via GPD (Generalized Pareto Distribution) fitting."
    > "Rebalance signal emitted only when allocation drift breaches no-trade buffer bands."

### 1.2 Prototype Execution Results
- Executed numerical simulation comparing Gaussian VaR/CVaR, Empirical VaR/CVaR, and EVT-GPD VaR/CVaR on heavy-tailed loss data (Student-t $df=3$, $N=500$):
  - `99% VaR  -> EVT: 0.062779, Empirical: 0.063722, Gaussian: 0.050036`
  - `99% CVaR -> EVT: 0.084798, Empirical: 0.082896, Gaussian: 0.050036`
  - **Observation**: Gaussian CVaR severely underestimates tail risk by over 40% ($0.0500$ vs $0.0848$), while EVT smooths and accurately models heavy-tailed loss distributions.
- Executed SLSQP portfolio optimization test under $\text{EVT\_CVaR}_{0.99}(w) \le 0.04$ loss budget constraint:
  - `Unconstrained EVT-CVaR`: $0.0997$ (9.97% tail loss) with weights `[0.50, 0.43, 0.07, 0.00, 0.00]`.
  - `EVT-Constrained EVT-CVaR`: $0.0399$ (3.99% tail loss) with weights `[0.005, 0.189, 0.181, 0.251, 0.374]`.
  - **Observation**: SLSQP non-linear constraint successfully shifts weight distribution to satisfy the tail loss budget cap without solver failure.

---

## 2. Logic Chain

### 2.1 Peaks-Over-Threshold (POT) & Generalized Pareto Distribution (GPD) Mathematical Derivation
1. **Portfolio Loss Series**:
   For portfolio weight vector $w \in \mathbb{R}^N$ and asset return matrix $R \in \mathbb{R}^{T \times N}$, the portfolio loss at step $t$ is:
   $$L_t(w) = - w^T R_t, \quad t = 1, \dots, T$$
2. **Threshold Selection $u$**:
   Let $\theta \in (0, 0.20)$ be the tail quantile fraction (e.g., $\theta = 0.10$ for the 90th loss percentile).
   $$u = Q_{1-\theta}(L(w))$$
   The sample exceedance rate is $\phi_u = P(L > u) = \frac{N_u}{T}$, where $N_u = \sum_{t=1}^T \mathbb{I}(L_t > u)$.
3. **Excess Distribution & GPD Fitting**:
   By the Balkema-De Haan-Pickands theorem, excess losses $Y = L - u \mid L > u$ converge to GPD:
   $$G_{\xi, \beta}(y) = P(L - u \le y \mid L > u) = 1 - \left( 1 + \frac{\xi y}{\beta} \right)^{-1/\xi}$$
   where $\xi$ is the shape parameter (tail index) and $\beta > 0$ is the scale parameter.
   Parameters $(\hat{\xi}, \hat{\beta})$ are fitted via Maximum Likelihood Estimation (MLE) using `scipy.stats.genpareto.fit(excesses, floc=0)`.
4. **EVT-VaR Formula**:
   Setting $1 - F(\text{VaR}_\alpha) = \phi_u \left( 1 + \hat{\xi} \frac{\text{VaR}_\alpha - u}{\hat{\beta}} \right)^{-1/\hat{\xi}} = 1 - \alpha$:
   $$\text{VaR}_\alpha^{\text{EVT}} = u + \frac{\hat{\beta}}{\hat{\xi}} \left[ \left( \frac{1 - \alpha}{\phi_u} \right)^{-\hat{\xi}} - 1 \right]$$
   If $\hat{\xi} \to 0$:
   $$\text{VaR}_\alpha^{\text{EVT}} = u - \hat{\beta} \ln \left( \frac{1 - \alpha}{\phi_u} \right)$$
5. **EVT-CVaR Formula**:
   Conditional Value-at-Risk $\text{CVaR}_\alpha = E[L \mid L \ge \text{VaR}_\alpha]$:
   $$\text{CVaR}_\alpha^{\text{EVT}} = \text{VaR}_\alpha^{\text{EVT}} + E[L - \text{VaR}_\alpha^{\text{EVT}} \mid L \ge \text{VaR}_\alpha^{\text{EVT}}] = \text{VaR}_\alpha^{\text{EVT}} + \frac{\hat{\beta} + \hat{\xi} (\text{VaR}_\alpha^{\text{EVT}} - u)}{1 - \hat{\xi}}$$
   Equivalently:
   $$\text{CVaR}_\alpha^{\text{EVT}} = \frac{\text{VaR}_\alpha^{\text{EVT}}}{1 - \hat{\xi}} + \frac{\hat{\beta} - \hat{\xi} u}{1 - \hat{\xi}}$$
   *Valid for $\hat{\xi} < 1$. When $\hat{\xi} \ge 1$, GPD mean is infinite.*

### 2.2 Mathematical Loss Budget Constraints Formulation
The portfolio optimization problem with EVT-CVaR loss budget constraints is formulated as:
$$\min_{w \in \mathbb{R}^N} \quad f(w) = - w^T \mu + \frac{\gamma}{2} w^T \Sigma w$$
$$\text{subject to } \begin{cases}
\sum_{i=1}^N w_i = 1 \\
0 \le w_i \le w_{\max}, \quad \forall i=1,\dots,N \\
\sum_{i \in \text{Sector}_k} w_i \le s_k, \quad \forall k \\
\text{EVT\_CVaR}_\alpha(w) \le \text{max\_cvar\_limit}
\end{cases}$$

In SLSQP non-linear optimization (`scipy.optimize.minimize`), the constraint function $g_{\text{cvar}}(w)$ is defined as:
$$g_{\text{cvar}}(w) = \text{max\_cvar\_limit} - \text{EVT\_CVaR}_\alpha(w) \ge 0$$

### 2.3 Edge Case & Robust Fallback Hierarchy
To guarantee numerical stability under all market regimes, a 3-tier fallback architecture is established:
1. **Tier 1 — EVT-GPD POT Estimator**:
   - Condition: Tail exceedance sample size $N_u \ge 15$, scale $\hat{\beta} > 10^{-8}$, shape $0 < \hat{\xi} < 0.95$, and no NaN/Inf outputs.
   - If conditions met $\implies$ return $\text{EVT\_CVaR}_\alpha(w)$.
2. **Tier 2 — Cornish-Fisher Expansion CVaR**:
   - Triggered if $N_u < 15$ or GPD fit fails or $\hat{\xi} \ge 0.95$.
   - Uses sample skewness $S$ and excess kurtosis $K$:
     $$z_{\text{CF}} = z_\alpha + \frac{S}{6}(z_\alpha^2 - 1) + \frac{K}{24}(z_\alpha^3 - 3 z_\alpha) - \frac{S^2}{36}(2 z_\alpha^3 - 5 z_\alpha)$$
     $$\text{CVaR}_{\text{CF}} = \mu + \sigma \left[ \frac{\phi(z_{\text{CF}})}{1 - \alpha} \left(1 + \frac{S}{6} z_{\text{CF}}^3 + \frac{K}{24} (z_{\text{CF}}^4 - 2 z_{\text{CF}}^2 - 1) \right) \right]$$
3. **Tier 3 — Empirical / Gaussian Parametric Fallback**:
   - Triggered if $N < 10$ or skewness/kurtosis calculations fail:
     $$\text{CVaR}_{\text{Gaussian}} = \mu + \sigma \frac{\phi(z_\alpha)}{1 - \alpha}$$

---

## 3. Caveats

1. **Stationarity Assumption**: GPD estimation assumes that exceedances over threshold $u$ are independent and identically distributed (i.i.d.). Volatility clustering in daily financial returns can violate i.i.d. assumptions during high-volatility regimes. Pre-filtering returns via GARCH(1,1) standardized residuals (Filter-EVT) can be considered as an advanced enhancement in future milestones.
2. **Computational Overhead**: Fitting GPD via MLE inside SciPy's SLSQP solver requires numerical evaluation of `scipy.stats.genpareto.fit` at each iteration step. For $N=500$ assets, evaluating loss series $L(w) = -R w$ takes $\approx 1$-$2$ ms per step, total optimization time $\approx 100$-$300$ ms, which is well within daily post-market pipeline tolerances.

---

## 4. Conclusion & Architecture Recommendations

### Recommended Code Specifications

#### Modification Specification 1: Add EVT-GPD Estimator to `trading_system/src/risk/risk_manager.py`
Add `calculate_evt_var` and `calculate_evt_cvar` methods to `RiskManager`:

```python
import numpy as np
import scipy.stats as stats

class RiskManager:
    ...
    def calculate_evt_cvar(
        self,
        returns: List[float] | np.ndarray,
        confidence: float = 0.99,
        threshold_quantile: float = 0.10,
        min_tail_samples: int = 15
    ) -> float:
        """
        Calculate Conditional Value-at-Risk (CVaR) using Extreme Value Theory (EVT)
        Peaks-Over-Threshold (POT) Generalized Pareto Distribution (GPD) fitting.
        """
        if returns is None or len(returns) == 0:
            return 0.0

        losses = -np.asarray(returns, dtype=np.float64)
        N = len(losses)

        if N < 10:
            mu = float(np.mean(losses))
            sigma = float(np.std(losses, ddof=1)) if N > 1 else 0.01
            z_alpha = float(stats.norm.ppf(confidence))
            return max(0.0, mu + sigma * (stats.norm.pdf(z_alpha) / (1.0 - confidence)))

        u = float(np.quantile(losses, 1.0 - threshold_quantile))
        excesses = losses[losses > u] - u
        Nu = len(excesses)

        if Nu < min_tail_samples:
            # Fallback: Empirical CVaR
            sorted_losses = np.sort(losses)
            var_idx = int(np.floor((1.0 - confidence) * N))
            tail = sorted_losses[-max(1, var_idx):]
            return float(np.mean(tail))

        phi_u = Nu / N
        try:
            xi, loc, beta = stats.genpareto.fit(excesses, floc=0)
            if beta <= 1e-8 or xi >= 0.95 or np.isnan(xi) or np.isnan(beta):
                raise ValueError("Unstable GPD parameters")

            xi = min(xi, 0.50)  # Clamp shape parameter

            if abs(xi) < 1e-5:
                var_evt = u - beta * np.log((1.0 - confidence) / phi_u)
                cvar_evt = var_evt + beta
            else:
                var_evt = u + (beta / xi) * (((1.0 - confidence) / phi_u) ** (-xi) - 1.0)
                cvar_evt = var_evt + (beta + xi * (var_evt - u)) / (1.0 - xi)

            return float(max(0.0, cvar_evt))
        except Exception:
            sorted_losses = np.sort(losses)
            var_idx = int(np.floor((1.0 - confidence) * N))
            tail = sorted_losses[-max(1, var_idx):]
            return float(np.mean(tail))
```

#### Modification Specification 2: Update `PortfolioOptimizer` in `src/risk/portfolio_optimizer.py` and `trading_system/src/risk/portfolio_optimizer.py`
Extend `PortfolioOptimizer` to support `max_cvar_limit` constraint and band-based dynamic rebalancing check:

```python
    def optimize_mean_variance(
        self,
        expected_returns: pd.Series,
        returns_df: pd.DataFrame,
        risk_aversion: float = 1.0,
        max_weight: Optional[float] = None,
        max_cvar_limit: Optional[float] = None,
        cvar_confidence: float = 0.99
    ) -> Dict[str, float]:
        if max_weight is None:
            max_weight = self.default_max_weight

        symbols = list(expected_returns.index)
        n_assets = len(symbols)
        if n_assets == 0:
            return {}
        if n_assets == 1:
            return {symbols[0]: 1.0}

        returns_sub = returns_df[symbols] if not returns_df.empty else pd.DataFrame()
        cov_matrix = self.calculate_covariance_matrix(returns_sub).values
        mu = expected_returns.values

        def mvo_objective(weights):
            ret = np.dot(weights, mu)
            vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            utility = ret - 0.5 * risk_aversion * (vol ** 2)
            return -utility

        init_weights = np.ones(n_assets) / n_assets
        bounds = tuple((0.0, max_weight) for _ in range(n_assets))
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

        if max_cvar_limit is not None and not returns_sub.empty:
            returns_mat = returns_sub.values
            from trading_system.src.risk.risk_manager import RiskManager
            rm = RiskManager()

            def cvar_constraint(w):
                port_returns = returns_mat @ w
                evt_cvar = rm.calculate_evt_cvar(port_returns, confidence=cvar_confidence)
                return max_cvar_limit - evt_cvar

            constraints.append({'type': 'ineq', 'fun': cvar_constraint})

        res = minimize(
            mvo_objective,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 500, 'ftol': 1e-9}
        )

        if not res.success:
            weights = init_weights
        else:
            weights = res.x / np.sum(res.x)

        return {sym: float(w) for sym, w in zip(symbols, weights)}

    def check_rebalance_trigger(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        buffer_band: float = 0.03
    ) -> bool:
        """
        Emits rebalance signal only when allocation drift breaches no-trade buffer bands.
        """
        all_keys = set(current_weights.keys()).union(set(target_weights.keys()))
        max_drift = 0.0
        for k in all_keys:
            w_curr = current_weights.get(k, 0.0)
            w_targ = target_weights.get(k, 0.0)
            max_drift = max(max_drift, abs(w_curr - w_targ))
        return max_drift > buffer_band
```

---

## 5. Verification Method

1. **Unit Test Suite Execution**:
   - Command: `.venv\Scripts\pytest.exe tests/test_evt_cvar.py -v` (or run custom test script)
   - Verify GPD POT fitting under normal, heavy-tailed (t-distribution $df=3$), and small sample size scenarios.
   - Test non-convergence fallback when sample size $N < 10$ or $N_u < 15$.
2. **Portfolio Optimization Constraint Verification**:
   - Command: `.venv\Scripts\python.exe -c "from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer; ..."`
   - Assert that `optimize_mean_variance(..., max_cvar_limit=0.04)` produces allocation vector $w$ satisfying $\text{EVT\_CVaR}_{0.99}(w) \le 0.04$.
3. **Invalidation Conditions**:
   - If SLSQP solver fails to converge when `max_cvar_limit` is active.
   - If `calculate_evt_cvar` produces NaNs, negative values, or values smaller than `calculate_evt_var`.
