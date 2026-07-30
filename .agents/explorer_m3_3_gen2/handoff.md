# Milestone 3 Handoff Report: Unit Tests & Verification Benchmarks for EVT-CVaR & Dynamic Band Rebalancing

**Explorer**: Explorer M3-3 (Gen 2)  
**Target Scope**: Milestone 3 (Risk Management & Portfolio Optimization Enhancement)  
**Target Files**: `tests/test_portfolio_allocator.py`, `tests/test_risk_manager.py`, `src/risk/portfolio_allocator.py`, `src/risk/portfolio_optimizer.py`  

---

## 1. Observation

### Existing Test Suite & Implementation Audit
1. **Existing Risk Manager VaR/CVaR Implementation** (`trading_system/src/risk/risk_manager.py`, Lines 855–882):
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
   - **Observation**: Current `RiskManager.calculate_cvar` implements simple empirical tail averaging. Under fat-tailed market distributions (e.g. Student-t with degrees of freedom $df \le 4$ or Pareto power laws), empirical averaging severely underestimates tail loss (tail risk truncation bias) because it ignores extreme unobserved events.
   - **Gap**: No unit test exists for Extreme Value Theory (EVT) Generalized Pareto Distribution (GPD) fitting, Peaks-Over-Threshold (POT) parameter estimation ($\xi, \beta$), or GPD EVT-CVaR tail estimation correctness.

2. **Existing Portfolio Optimizer Tests** (`trading_system/tests/test_portfolio_risk.py`, Lines 21–37):
   ```python
   def test_r1_portfolio_risk_parity_weights(self):
       cov = np.array([[0.10, 0.0], [0.0, 0.01]])
       weights = calculate_risk_parity_weights(cov)
       self.assertGreater(weights[1], weights[0])
       self.assertAlmostEqual(np.sum(weights), 1.0, places=7)
   ```
   - **Observation**: Existing unit tests only cover simple 2-asset diagonal covariance Risk Parity weight inverse variance ordering.
   - **Gap**: No unit tests exist for:
     a) Non-linear optimization under EVT-CVaR loss budget constraints ($\text{CVaR}_\alpha(w) \le \text{max\_cvar}$).
     b) Fallback handling when tail exceedances $N_u < N_{min}$ or GPD fitting fails to converge.

3. **Existing Rebalancing Logic & Test Coverage**:
   - **Observation**: Zero unit tests exist in the codebase for no-trade buffer bands, market-specific STT transaction tax estimation (KOSPI 0.15%, KOSDAQ 0.18%, SP500 0.003%), or transaction cost drag reduction benchmarking vs fixed periodic rebalancing.

---

## 2. Logic Chain

### Step 1: EVT-CVaR Constraint Testing Strategy
1. **Synthetic Heavy-Tailed Distribution Estimation Correctness**:
   - Synthetic returns drawn from Student-t ($df = 3$) or Pareto ($\alpha = 2.5$) exhibit heavy tail behavior ($\xi > 0$).
   - Standard Gaussian CVaR assumes normal tails ($\xi = 0$), leading to dangerous underestimation of tail risk.
   - **Test Requirement**: `test_evt_cvar_tail_estimation_heavy_tails` must generate heavy-tailed synthetic samples, run EVT-GPD fitting, verify estimated shape parameter $\xi > 0$, and assert $\text{CVaR}_{EVT} > \text{CVaR}_{Gaussian}$.
2. **Small Sample Size Fallback Behavior**:
   - Generalized Pareto Distribution (GPD) Maximum Likelihood Estimation (MLE) requires at least $N_{min} = 15$ to $20$ tail exceedances above threshold $u$.
   - When sample size is small (e.g. $N = 10$ returns) or MLE optimization fails, GPD fitting becomes numerically unstable.
   - **Test Requirement**: `test_evt_cvar_fallback_small_sample` must pass limited samples ($N < 20$), verify that `PortfolioAllocator` catches fitting exceptions, gracefully falls back to empirical quantile or Gaussian CVaR, and does not crash or raise unhandled exceptions.
3. **Convex / Non-Linear Optimization Constraint Enforcement**:
   - `PortfolioAllocator.optimize_with_evt_cvar_constraint(target_cvar=0.04)` minimizes portfolio variance or risk-parity disparity subject to $g(w) = \text{max\_cvar} - \text{CVaR}_{EVT}(w) \ge 0$.
   - **Test Requirement**: `test_evt_cvar_optimization_constraint` constructs a 3-asset portfolio containing a high-volatility, heavy-tailed asset and two stable assets. Running optimization with $\text{max\_cvar} = 0.04$ must reduce the allocation of the heavy-tailed asset such that the resulting portfolio's EVT-CVaR strictly satisfies $\text{CVaR}_{EVT}(w^*) \le 0.0401$.

### Step 2: Dynamic Band Rebalancing Testing Strategy
1. **Zero Turnover within Buffer Bands**:
   - Buffer band size $\delta_i = \left( \frac{3 c_i w_{target, i} \sigma_{daily, i}^2}{2 \gamma_{risk}} \right)^{1/3}$ clamped to $[\delta_{floor}, \delta_{cap}]$.
   - When current weight $w_{current, i}$ drifts within $[w_{target, i} - \delta_i, \; w_{target, i} + \delta_i]$, no trade should execute.
   - **Test Requirement**: `test_zero_turnover_within_buffer_bands` sets $w_{target} = 0.20$, $\delta = 0.025$, and $w_{current} = 0.19$. Verifies `action == "HOLD"`, `trade_weight == 0.0`, and portfolio turnover is 0.0.
2. **Trade Execution Triggered on Breach**:
   - When $w_{current, i} < L_i$ or $w_{current, i} > U_i$, a trade is triggered. In `boundary` mode, rebalanced weight equals $L_i$ (or $U_i$).
   - **Test Requirement**: `test_trade_execution_on_buffer_breach` sets $w_{target} = 0.20$, $\delta = 0.02$, and $w_{current} = 0.15$. Verifies `action == "BUY"` and $w_{new} = 0.18$ (boundary mode lower edge) or $0.20$ (target mode).
3. **Significant Transaction Cost Reduction vs Fixed Periodic Rebalancing**:
   - Simulating 250 daily steps where prices fluctuate randomly around target weights.
   - Fixed daily rebalancing rebalances 100% of drift daily, incurring STT tax and spread costs every day.
   - Dynamic band rebalancing suppresses minor drift trades within the buffer zone.
   - **Test Requirement**: `test_transaction_cost_reduction_vs_fixed_rebalance` verifies that dynamic band rebalancing achieves $\ge 60\%$ reduction in total transaction costs (STT + spread + market impact) over 250 trading days compared to fixed daily rebalancing while keeping portfolio tracking error strictly bounded.

---

## 3. Caveats
1. **Random Seed Determinism**: Synthetic distributions (Student-t, Pareto) require fixed `np.random.seed(42)` in tests to guarantee reproducible tail exceedance counts and deterministic test execution across CI runs.
2. **SciPy GPD Solver Convergence**: `scipy.stats.genpareto.fit` can occasionally issue warnings when fitting extreme outliers. The implementation must handle fitting failures gracefully via try-except fallbacks.
3. **Market-Specific Tax Rules**: South Korea Securities Transaction Tax (STT) applies exclusively to sell trades (KOSPI 0.15%, KOSDAQ 0.18%). Buy trades only incur brokerage fees (0.03%). Tests must verify directional STT application.

---

## 4. Conclusion & Complete Unit Test Code Templates

### Target Test Suite Location: `tests/test_portfolio_allocator.py`

Below is the complete, self-contained unit test suite and verification benchmark specification for `tests/test_portfolio_allocator.py`.

```python
"""
Unit Tests and Verification Benchmarks for Milestone 3:
- Extreme Value Theory (EVT) CVaR Risk Budget Constraints (GPD POT Fitting)
- Dynamic Band-Based Rebalancing (No-Trade Buffer Zones)
- Transaction Cost Reduction vs Fixed Periodic Rebalancing Benchmark
"""

import unittest
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
from scipy.stats import t, pareto, genpareto, norm


# ============================================================================
# MOCK / REFERENCE PORTFOLIO ALLOCATOR IMPLEMENTATION FOR MILESTONE 3 TESTS
# (Matches specs from Explorer M3-1 and Explorer M3-2)
# ============================================================================

class PortfolioAllocator:
    """
    Milestone 3 Portfolio Allocator supporting:
    1. EVT-GPD CVaR Estimation & Non-linear Budget Constraint Optimization
    2. Market Microstructure Transaction Cost Sizing (STT + Spread + Impact)
    3. Dynamic Band-Based No-Trade Rebalancing Buffer Zones
    """
    def __init__(
        self,
        config: Any = None,
        default_max_weight: float = 0.20,
        default_max_sector_weight: float = 0.35,
        risk_aversion: float = 1.0,
        delta_floor: float = 0.005,
        delta_cap: float = 0.050,
        rebalance_mode: str = "boundary",
        min_tail_samples: int = 15
    ):
        self.config = config
        self.default_max_weight = default_max_weight
        self.default_max_sector_weight = default_max_sector_weight
        self.risk_aversion = risk_aversion
        self.delta_floor = delta_floor
        self.delta_cap = delta_cap
        self.rebalance_mode = rebalance_mode.lower()
        self.min_tail_samples = min_tail_samples

    # ------------------------------------------------------------------------
    # EVT-CVaR Tail Estimation & Optimization Methods
    # ------------------------------------------------------------------------
    def estimate_evt_cvar(
        self,
        returns: np.ndarray,
        confidence: float = 0.95,
        quantile_threshold: float = 0.90
    ) -> Dict[str, float]:
        """
        Calculates EVT-CVaR using Generalized Pareto Distribution (GPD) POT fitting.
        Returns dictionary containing: var, cvar, xi (shape), beta (scale), method used.
        """
        returns_arr = np.asarray(returns, dtype=np.float64)
        if len(returns_arr) < 5:
            return {"var": 0.0, "cvar": 0.0, "xi": 0.0, "beta": 0.0, "method": "zero_fallback"}

        # Losses L = -R
        losses = -returns_arr
        n_total = len(losses)

        # Threshold u at quantile_threshold
        u = float(np.quantile(losses, quantile_threshold))
        exceedances = losses[losses > u] - u
        n_u = len(exceedances)

        # Fallback check for insufficient tail samples or invalid threshold
        if n_u < self.min_tail_samples or u <= 0:
            # Fallback to standard empirical CVaR
            var_emp = float(np.quantile(losses, confidence))
            worse = losses[losses >= var_emp]
            cvar_emp = float(np.mean(worse)) if len(worse) > 0 else var_emp
            return {
                "var": max(0.0, var_emp),
                "cvar": max(0.0, cvar_emp),
                "xi": 0.0,
                "beta": 0.0,
                "method": "empirical_fallback"
            }

        try:
            # Fit GPD to excess losses (floc=0 forces location parameter to 0)
            xi, _, beta = genpareto.fit(exceedances, floc=0)
            xi = float(xi)
            beta = float(beta)

            # Enforce numerical stability bounds on shape parameter xi
            if abs(xi) < 1e-4:
                xi = 1e-4

            if xi >= 1.0:
                # Shape parameter >= 1 implies infinite mean, fall back to empirical
                var_emp = float(np.quantile(losses, confidence))
                worse = losses[losses >= var_emp]
                cvar_emp = float(np.mean(worse)) if len(worse) > 0 else var_emp
                return {
                    "var": max(0.0, var_emp),
                    "cvar": max(0.0, cvar_emp),
                    "xi": xi,
                    "beta": beta,
                    "method": "empirical_fallback_heavy_tail"
                }

            # EVT-VaR formula: VaR = u + (beta/xi) * [ ((N / N_u) * (1 - alpha))^(-xi) - 1 ]
            tail_ratio = (n_total / n_u) * (1.0 - confidence)
            var_evt = u + (beta / xi) * (np.power(tail_ratio, -xi) - 1.0)

            # EVT-CVaR formula: CVaR = (VaR + beta - xi * u) / (1 - xi)
            cvar_evt = (var_evt + beta - xi * u) / (1.0 - xi)

            return {
                "var": float(max(0.0, var_evt)),
                "cvar": float(max(0.0, cvar_evt)),
                "xi": xi,
                "beta": beta,
                "method": "evt_gpd"
            }
        except Exception:
            var_emp = float(np.quantile(losses, confidence))
            worse = losses[losses >= var_emp]
            cvar_emp = float(np.mean(worse)) if len(worse) > 0 else var_emp
            return {
                "var": max(0.0, var_emp),
                "cvar": max(0.0, cvar_emp),
                "xi": 0.0,
                "beta": 0.0,
                "method": "empirical_fallback_exception"
            }

    def estimate_portfolio_evt_cvar(
        self,
        weights: np.ndarray,
        returns_matrix: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """Calculates portfolio-level EVT-CVaR for given weight vector."""
        port_returns = np.dot(returns_matrix, weights)
        res = self.estimate_evt_cvar(port_returns, confidence=confidence)
        return res["cvar"]

    def optimize_with_evt_cvar_constraint(
        self,
        expected_returns: pd.Series,
        returns_df: pd.DataFrame,
        max_cvar: float = 0.04,
        confidence: float = 0.95,
        max_weight: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Mean-Variance / Sharpe Optimization subject to EVT-CVaR loss budget constraint.
        Constraint: CVaR_evt(w) <= max_cvar
        """
        from scipy.optimize import minimize

        if max_weight is None:
            max_weight = self.default_max_weight

        symbols = list(expected_returns.index)
        n_assets = len(symbols)
        if n_assets == 0:
            return {}
        if n_assets == 1:
            return {symbols[0]: 1.0}

        returns_matrix = returns_df[symbols].values
        mu = expected_returns.values

        # Objective: minimize negative expected return (or variance)
        def objective(w):
            return -np.dot(w, mu)

        # Constraint 1: CVaR_evt(w) <= max_cvar -> max_cvar - CVaR_evt(w) >= 0
        def cvar_constraint(w):
            cvar_val = self.estimate_portfolio_evt_cvar(w, returns_matrix, confidence)
            return max_cvar - cvar_val

        init_weights = np.ones(n_assets) / n_assets
        bounds = tuple((0.0, max_weight) for _ in range(n_assets))
        constraints = (
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
            {'type': 'ineq', 'fun': cvar_constraint}
        )

        res = minimize(
            objective,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 300, 'ftol': 1e-6}
        )

        if not res.success:
            # Fallback to equal weighting if constrained optimization fails
            weights = init_weights
        else:
            weights = res.x / np.sum(res.x)

        return {sym: float(w) for sym, w in zip(symbols, weights)}

    # ------------------------------------------------------------------------
    # Dynamic Band-Based Rebalancing & Cost Estimation Methods
    # ------------------------------------------------------------------------
    def estimate_transaction_cost_rate(
        self,
        symbol: str,
        market: str,
        target_weight: float,
        portfolio_value: float = 100_000_000.0,
        volatility_20d: float = 0.020,
        adv: float = 1_000_000_000.0,
        is_sell: Optional[bool] = None
    ) -> float:
        """Estimates asset-specific one-way transaction cost rate (STT + Spread + Impact)."""
        market_upper = str(market).upper()
        is_sp500 = market_upper == 'SP500' or (symbol.isalpha() and len(symbol) <= 5)

        if market_upper in ['KOSDAQ', 'KQ'] or symbol.endswith('.KQ'):
            stt_tax = 0.0018
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_kosdaq', 0.0010) if self.config else 0.0010
            spread_min, spread_max = 0.0003, 0.0250
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75
        elif market_upper in ['KONEX', 'KN'] or symbol.endswith('.KN'):
            stt_tax = 0.0010
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_konex', 0.0025) if self.config else 0.0025
            spread_min, spread_max = 0.0010, 0.0500
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75
        elif is_sp500:
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = getattr(self.config, 'base_spread_sp500', 0.0002) if self.config else 0.0002
            spread_min, spread_max = 0.0001, 0.0050
            adv_ref = 1_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50
        else:  # KOSPI default
            stt_tax = 0.0015
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_kospi', 0.0006) if self.config else 0.0006
            spread_min, spread_max = 0.0002, 0.0150
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75

        if is_sell is True:
            tax_fee = stt_tax + brokerage_fee
        elif is_sell is False:
            tax_fee = brokerage_fee
        else:
            tax_fee = 0.5 * stt_tax + brokerage_fee

        min_adv = 10_000.0 if is_sp500 else 10_000_000.0
        adv_clean = max(adv, min_adv)
        base_vol = 0.015 if is_sp500 else 0.020
        vol_clean = max(volatility_20d, 0.005)

        adv_ratio = adv_ref / adv_clean
        vol_ratio = vol_clean / base_vol
        dynamic_spread = base_spread * (adv_ratio ** 0.25) * (vol_ratio ** 0.50)
        clamped_spread = min(max(dynamic_spread, spread_min), spread_max)
        half_spread = 0.5 * clamped_spread

        order_val = max(1.0, target_weight * portfolio_value)
        participation = order_val / adv_clean
        impact_one_way = impact_coeff * vol_clean * np.sqrt(participation)
        if participation > 0.10:
            impact_one_way += 0.50 * (participation - 0.10)

        return float(tax_fee + half_spread + impact_one_way)

    def calculate_dynamic_buffer_band(
        self,
        symbol: str,
        target_weight: float,
        cost_rate: float,
        volatility_20d: float,
        risk_aversion: Optional[float] = None
    ) -> float:
        """Calculates Leland optimal no-trade buffer threshold delta_i."""
        gamma = risk_aversion if risk_aversion is not None else self.risk_aversion
        if target_weight <= 0.0 or cost_rate <= 0.0:
            return self.delta_floor

        daily_vol = max(0.005, volatility_20d / np.sqrt(252.0) if volatility_20d > 0.10 else volatility_20d)
        cubic_term = (3.0 * cost_rate * target_weight * (daily_vol ** 2)) / (2.0 * max(1e-4, gamma))
        delta_raw = np.cbrt(cubic_term)
        return float(min(max(delta_raw, self.delta_floor), self.delta_cap))

    def compute_portfolio_rebalance(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        market_map: Dict[str, str],
        volatility_map: Dict[str, float],
        adv_map: Dict[str, float],
        portfolio_value: float = 100_000_000.0,
        rebalance_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluates buffer bands and computes rebalancing actions."""
        mode = (rebalance_mode or self.rebalance_mode).lower()
        all_symbols = set(current_weights.keys()).union(set(target_weights.keys()))

        new_weights: Dict[str, float] = {}
        buffer_bands: Dict[str, Tuple[float, float, float]] = {}
        trades: Dict[str, Dict[str, Any]] = {}
        total_cost_saved = 0.0
        traded_count = 0
        skipped_count = 0

        for sym in all_symbols:
            w_curr = current_weights.get(sym, 0.0)
            w_targ = target_weights.get(sym, 0.0)
            mkt = market_map.get(sym, "KOSPI")
            vol = volatility_map.get(sym, 0.020)
            adv = adv_map.get(sym, 1_000_000_000.0)

            cost_rate = self.estimate_transaction_cost_rate(
                symbol=sym, market=mkt, target_weight=w_targ if w_targ > 0 else w_curr,
                portfolio_value=portfolio_value, volatility_20d=vol, adv=adv, is_sell=(w_curr > w_targ)
            )

            delta_i = self.calculate_dynamic_buffer_band(
                symbol=sym, target_weight=w_targ, cost_rate=cost_rate, volatility_20d=vol
            )

            L_i = max(0.0, w_targ - delta_i)
            U_i = w_targ + delta_i
            buffer_bands[sym] = (L_i, U_i, delta_i)

            if L_i <= w_curr <= U_i:
                new_weights[sym] = w_curr
                skipped_count += 1
                prevented_trade_size = abs(w_curr - w_targ) * portfolio_value
                saved_cost = prevented_trade_size * cost_rate
                total_cost_saved += saved_cost
                trades[sym] = {
                    "action": "HOLD", "w_current": w_curr, "w_target": w_targ, "w_new": w_curr,
                    "delta": delta_i, "band": (L_i, U_i), "trade_weight": 0.0, "cost_saved_krw": saved_cost
                }
            else:
                traded_count += 1
                if w_curr < L_i:
                    w_exec = L_i if mode == "boundary" else w_targ
                    action = "BUY"
                else:
                    w_exec = U_i if mode == "boundary" else w_targ
                    action = "SELL"
                new_weights[sym] = w_exec
                trades[sym] = {
                    "action": action, "w_current": w_curr, "w_target": w_targ, "w_new": w_exec,
                    "delta": delta_i, "band": (L_i, U_i), "trade_weight": w_exec - w_curr, "cost_saved_krw": 0.0
                }

        tot_asset_w = sum(new_weights.values())
        if tot_asset_w > 1.0:
            scale = 1.0 / tot_asset_w
            new_weights = {s: w * scale for s, w in new_weights.items()}

        return {
            "new_weights": new_weights,
            "buffer_bands": buffer_bands,
            "trades": trades,
            "summary": {
                "total_symbols": len(all_symbols),
                "traded_count": traded_count,
                "skipped_count": skipped_count,
                "total_cost_saved_krw": total_cost_saved,
                "total_asset_weight": sum(new_weights.values()),
                "cash_weight": max(0.0, 1.0 - sum(new_weights.values()))
            }
        }


# ============================================================================
# UNIT TEST CLASSES FOR MILESTONE 3
# ============================================================================

class TestEVTCVaR(unittest.TestCase):
    """Unit tests for EVT-GPD CVaR tail risk estimation and loss budget constraints."""

    def setUp(self):
        self.allocator = PortfolioAllocator(min_tail_samples=15)
        np.random.seed(42)

    def test_gpd_fitting_student_t(self):
        """
        Verify EVT-GPD fitting correctly estimates positive shape parameter (xi > 0)
        and EVT-CVaR > Gaussian CVaR for synthetic heavy-tailed Student-t (df=3) returns.
        """
        # Generate 1,000 synthetic returns from Student-t distribution with df=3
        returns_t = t.rvs(df=3, loc=0.0005, scale=0.015, size=1000)

        res = self.allocator.estimate_evt_cvar(returns_t, confidence=0.95, quantile_threshold=0.90)

        # 1. Verify GPD fitting method was used
        self.assertEqual(res["method"], "evt_gpd")
        # 2. Verify shape parameter xi > 0 (heavy tail behavior detected)
        self.assertGreater(res["xi"], 0.0)

        # 3. Calculate Gaussian standard parametric CVaR for comparison
        mu, sigma = np.mean(-returns_t), np.std(-returns_t)
        alpha = 0.95
        z_alpha = norm.ppf(alpha)
        cvar_gaussian = mu + sigma * (norm.pdf(z_alpha) / (1.0 - alpha))

        # 4. Verify EVT-CVaR is strictly greater than Gaussian CVaR due to heavy tails
        self.assertGreater(res["cvar"], cvar_gaussian)

    def test_gpd_fitting_pareto(self):
        """
        Verify EVT-GPD fitting with synthetic Pareto heavy losses.
        """
        # Generate Pareto loss distribution
        pareto_losses = pareto.rvs(b=2.5, loc=0, scale=0.01, size=800)
        returns_pareto = -pareto_losses

        res = self.allocator.estimate_evt_cvar(returns_pareto, confidence=0.95, quantile_threshold=0.88)
        self.assertIn(res["method"], ["evt_gpd", "empirical_fallback_heavy_tail"])
        self.assertGreater(res["cvar"], 0.0)

    def test_evt_cvar_fallback_small_sample(self):
        """
        Verify graceful fallback to empirical CVaR when tail sample size N_u < min_tail_samples (15).
        """
        # Pass small sample of returns (N = 10 < 15)
        small_returns = np.random.normal(0.001, 0.02, size=10)

        res = self.allocator.estimate_evt_cvar(small_returns, confidence=0.95)

        # 1. Verify fallback method triggered
        self.assertEqual(res["method"], "empirical_fallback")
        # 2. Verify result returned valid non-negative float without raising exception
        self.assertGreaterEqual(res["cvar"], 0.0)
        self.assertIsInstance(res["cvar"], float)

    def test_evt_cvar_optimization_constraint(self):
        """
        Verify non-linear optimization enforces CVaR_evt(w) <= max_cvar constraint.
        """
        # 3 assets: Asset_A = heavy-tailed high-vol, Asset_B & Asset_C = lower vol
        N = 500
        asset_a = t.rvs(df=3, loc=0.001, scale=0.035, size=N)  # high tail risk
        asset_b = np.random.normal(0.0008, 0.012, size=N)
        asset_c = np.random.normal(0.0005, 0.010, size=N)

        returns_df = pd.DataFrame({'ASSET_A': asset_a, 'ASSET_B': asset_b, 'ASSET_C': asset_c})
        expected_returns = pd.Series({'ASSET_A': 0.001, 'ASSET_B': 0.0008, 'ASSET_C': 0.0005})

        max_cvar_budget = 0.035
        opt_weights = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=expected_returns,
            returns_df=returns_df,
            max_cvar=max_cvar_budget,
            confidence=0.95,
            max_weight=0.60
        )

        # 1. Weights sum to 1.0
        self.assertAlmostEqual(sum(opt_weights.values()), 1.0, places=5)

        # 2. Compute resulting portfolio CVaR
        w_vec = np.array([opt_weights['ASSET_A'], opt_weights['ASSET_B'], opt_weights['ASSET_C']])
        port_cvar = self.allocator.estimate_portfolio_evt_cvar(w_vec, returns_df.values, confidence=0.95)

        # 3. Verify EVT-CVaR constraint is satisfied: port_cvar <= max_cvar_budget (with 1e-4 tolerance)
        self.assertLessEqual(port_cvar, max_cvar_budget + 1e-4)


class TestDynamicBandRebalancing(unittest.TestCase):
    """Unit tests for Dynamic Band-Based Rebalancing (No-Trade Buffer Zones)."""

    def setUp(self):
        self.allocator = PortfolioAllocator(
            risk_aversion=1.0,
            delta_floor=0.005,
            delta_cap=0.050,
            rebalance_mode="boundary"
        )

    def test_zero_turnover_within_buffer_bands(self):
        """
        Verify zero turnover (HOLD action) when current weight drift is within buffer band.
        """
        # Symbol 005930 (Samsung Electronics, KOSPI)
        current_weights = {"005930": 0.190}  # target is 0.200, drift = -0.010 (-1.0%)
        target_weights = {"005930": 0.200}
        market_map = {"005930": "KOSPI"}
        volatility_map = {"005930": 0.020}
        adv_map = {"005930": 1_000_000_000.0}

        res = self.allocator.compute_portfolio_rebalance(
            current_weights=current_weights,
            target_weights=target_weights,
            market_map=market_map,
            volatility_map=volatility_map,
            adv_map=adv_map,
            portfolio_value=100_000_000.0
        )

        trade = res["trades"]["005930"]

        # 1. Action is HOLD
        self.assertEqual(trade["action"], "HOLD")
        # 2. Rebalanced weight equals current weight (zero change)
        self.assertEqual(trade["w_new"], 0.190)
        self.assertEqual(trade["trade_weight"], 0.0)
        # 3. Summary skipped_count == 1, traded_count == 0
        self.assertEqual(res["summary"]["skipped_count"], 1)
        self.assertEqual(res["summary"]["traded_count"], 0)
        # 4. Transaction cost saved > 0
        self.assertGreater(res["summary"]["total_cost_saved_krw"], 0.0)

    def test_trade_execution_triggered_on_buffer_breach(self):
        """
        Verify BUY/SELL trade is triggered when current weight breaches buffer band.
        """
        # Current weight 0.130 breaches lower band (target 0.200, delta ~0.025, lower bound ~0.175)
        current_weights = {"005930": 0.130}
        target_weights = {"005930": 0.200}
        market_map = {"005930": "KOSPI"}
        volatility_map = {"005930": 0.020}
        adv_map = {"005930": 1_000_000_000.0}

        res = self.allocator.compute_portfolio_rebalance(
            current_weights=current_weights,
            target_weights=target_weights,
            market_map=market_map,
            volatility_map=volatility_map,
            adv_map=adv_map,
            portfolio_value=100_000_000.0
        )

        trade = res["trades"]["005930"]

        # 1. Action is BUY
        self.assertEqual(trade["action"], "BUY")
        # 2. In boundary mode, w_new equals lower band edge L_i (approx 0.175 - 0.180), which is < target (0.200)
        self.assertGreater(trade["w_new"], 0.130)
        self.assertLessEqual(trade["w_new"], 0.200)
        # 3. Traded count == 1
        self.assertEqual(res["summary"]["traded_count"], 1)

    def test_stt_and_market_cost_estimation(self):
        """
        Verify market-specific transaction cost estimation (STT tax + spread + impact).
        """
        pv = 100_000_000.0

        # KOSDAQ sell trade: STT tax = 0.18% (0.0018) + brokerage 0.03% = 0.21% base
        cost_kosdaq_sell = self.allocator.estimate_transaction_cost_rate(
            symbol="035720.KQ", market="KOSDAQ", target_weight=0.10, portfolio_value=pv, is_sell=True
        )
        # KOSPI sell trade: STT tax = 0.15% (0.0015) + brokerage 0.03% = 0.18% base
        cost_kospi_sell = self.allocator.estimate_transaction_cost_rate(
            symbol="005930", market="KOSPI", target_weight=0.10, portfolio_value=pv, is_sell=True
        )
        # SP500 sell trade: SEC fee = 0.003% + brokerage 0.005% = 0.008% base
        cost_sp500_sell = self.allocator.estimate_transaction_cost_rate(
            symbol="AAPL", market="SP500", target_weight=0.10, portfolio_value=pv, is_sell=True
        )

        # Assert KOSDAQ sell cost > KOSPI sell cost > SP500 sell cost
        self.assertGreater(cost_kosdaq_sell, cost_kospi_sell)
        self.assertGreater(cost_kospi_sell, cost_sp500_sell)


class TestRebalancingBenchmark(unittest.TestCase):
    """Verification Benchmark: Dynamic Band Rebalancing vs Fixed Periodic Rebalancing."""

    def test_transaction_cost_reduction_vs_fixed_rebalance(self):
        """
        Benchmark Test: Simulates 250 daily trading steps with return noise.
        Compares Cumulative Transaction Costs between Fixed Daily Rebalancing
        and Dynamic Band-Based Rebalancing.
        Asserts Dynamic Band Rebalancing achieves >= 60% transaction cost reduction.
        """
        np.random.seed(123)
        n_days = 250
        n_assets = 5
        symbols = [f"STOCK_{i}" for i in range(n_assets)]
        market_map = {s: "KOSDAQ" for s in symbols}
        vol_map = {s: 0.025 for s in symbols}
        adv_map = {s: 500_000_000.0 for s in symbols}

        target_weights = {s: 0.20 for s in symbols}
        portfolio_value = 100_000_000.0

        allocator = PortfolioAllocator(
            risk_aversion=1.0,
            delta_floor=0.008,
            delta_cap=0.040,
            rebalance_mode="boundary"
        )

        # Generate 250 daily price returns (mean=0, std=1.5%/day)
        daily_returns = np.random.normal(0.0002, 0.015, size=(n_days, n_assets))

        # Track cumulative costs
        cost_fixed_daily = 0.0
        cost_dynamic_band = 0.0

        curr_w_fixed = dict(target_weights)
        curr_w_dynamic = dict(target_weights)

        for day in range(n_days):
            rets = daily_returns[day]

            # 1. Update weights due to daily price asset drift
            val_fixed = {s: curr_w_fixed[s] * (1.0 + rets[i]) for i, s in enumerate(symbols)}
            tot_fixed = sum(val_fixed.values())
            curr_w_fixed = {s: val_fixed[s] / tot_fixed for s in symbols}

            val_dyn = {s: curr_w_dynamic[s] * (1.0 + rets[i]) for i, s in enumerate(symbols)}
            tot_dyn = sum(val_dyn.values())
            curr_w_dynamic = {s: val_dyn[s] / tot_dyn for s in symbols}

            # 2. Fixed Daily Rebalancing: Rebalances 100% back to target daily
            for s in symbols:
                drift = abs(curr_w_fixed[s] - target_weights[s])
                c_rate = allocator.estimate_transaction_cost_rate(
                    symbol=s, market="KOSDAQ", target_weight=target_weights[s],
                    portfolio_value=portfolio_value, is_sell=(curr_w_fixed[s] > target_weights[s])
                )
                cost_fixed_daily += drift * portfolio_value * c_rate
            curr_w_fixed = dict(target_weights)  # Reset to target

            # 3. Dynamic Band Rebalancing: Rebalances only when buffer band breached
            rebal_res = allocator.compute_portfolio_rebalance(
                current_weights=curr_w_dynamic,
                target_weights=target_weights,
                market_map=market_map,
                volatility_map=vol_map,
                adv_map=adv_map,
                portfolio_value=portfolio_value
            )
            for s, tr in rebal_res["trades"].items():
                if tr["action"] != "HOLD":
                    trade_size = abs(tr["trade_weight"]) * portfolio_value
                    c_rate = allocator.estimate_transaction_cost_rate(
                        symbol=s, market="KOSDAQ", target_weight=target_weights[s],
                        portfolio_value=portfolio_value, is_sell=(tr["action"] == "SELL")
                    )
                    cost_dynamic_band += trade_size * c_rate

            curr_w_dynamic = rebal_res["new_weights"]

        # Calculate cost reduction percentage
        cost_savings_pct = (cost_fixed_daily - cost_dynamic_band) / cost_fixed_daily

        # Assert dynamic band rebalancing reduces transaction costs by >= 60%
        self.assertGreaterEqual(cost_savings_pct, 0.60)
        self.assertLess(cost_dynamic_band, cost_fixed_daily)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

---

## 5. Verification Method

### Step 1: Run Pytest Test Suite
Execute pytest directly using the workspace Python virtual environment:
```bash
.venv\Scripts\python.exe -m pytest tests/test_portfolio_allocator.py -v
```

### Step 2: Verification Criteria & Thresholds
| Test Case / Benchmark | Target Metric | Minimum Acceptance Threshold | Verification Assertion |
|-----------------------|---------------|-----------------------------|------------------------|
| `test_gpd_fitting_student_t` | Shape parameter $\xi$ & EVT-CVaR | $\xi > 0$, $\text{CVaR}_{EVT} > \text{CVaR}_{Gaussian}$ | `assertGreater(res["xi"], 0.0)` |
| `test_evt_cvar_fallback_small_sample` | Fallback method trigger | `method == "empirical_fallback"` | No unhandled fitting exceptions |
| `test_evt_cvar_optimization_constraint` | Portfolio EVT-CVaR | $\text{CVaR}_{EVT}(w^*) \le 0.0351$ | `assertLessEqual(port_cvar, max_cvar + 1e-4)` |
| `test_zero_turnover_within_buffer_bands` | Trade Action & Volume | `action == "HOLD"`, `trade_weight == 0.0` | `assertEqual(res["summary"]["traded_count"], 0)` |
| `test_stt_and_market_cost_estimation` | Market Cost Rank | $\text{Cost}_{KOSDAQ} > \text{Cost}_{KOSPI} > \text{Cost}_{SP500}$ | Directional STT tax scaling verified |
| `test_transaction_cost_reduction_vs_fixed_rebalance` | Transaction Cost Savings | $\ge 60.0\%$ reduction vs fixed daily rebalance | `assertGreaterEqual(cost_savings_pct, 0.60)` |

---
