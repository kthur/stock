# Comprehensive Architectural Audit & Empirical Investigation: Portfolio Optimization & Execution OMS

**Specialist**: Explorer 1 (Portfolio & OMS Architecture Specialist)  
**Date**: 2026-08-30  
**Scope**:  
1. **Portfolio Optimization**:
   - `src/analysis/portfolio_optimizer.py` (HRP, Black-Litterman, Ledoit-Wolf covariance shrinkage, HERC, portfolio constraints)
   - `src/risk/portfolio_optimizer.py` (Class wrapper)
   - `src/risk/portfolio_allocator.py` (EVT-CVaR tail risk budgeting, Leland dynamic buffer bands, CPPI, Kelly sizing, Sortino downside semi-covariance)
   - `src/risk/risk_manager.py` (Crisis detector, multi-factor macro risk scoring, VIX velocity & term structure gating, hard portfolio circuit breaker)
2. **Execution OMS**:
   - `src/execution/order_manager.py` & `src/execution/oms_engine.py` (ExecutionOMSEngine, 7 Safety Gates + Kill Switch, multi-tier trailing stops)
   - `src/execution/almgren_chriss.py` (AlmgrenChrissScheduler)
   - `src/execution/slippage_feedback.py` (SlippageFeedbackEngine, closed-loop impact adjustment)
   - `src/execution/turnover_optimizer.py` (TurnoverOptimizer, position hysteresis)
3. **Target Test Suites in `tests/`**:
   - `tests/test_portfolio_allocator.py`, `tests/test_portfolio_optimizer_and_oms.py`, `tests/test_black_litterman.py`, `tests/test_hrp_optimizer.py`, `tests/test_order_manager.py`, `tests/test_turnover_optimizer.py`, `tests/test_slippage_feedback.py`, `tests/test_risk_manager.py`, `tests/test_unified_portfolio_engine.py`, `tests/test_adaptive_execution_feedback.py`, `tests/test_challenger_portfolio_stress.py`, `tests/test_confidence_adaptive_kelly.py`, `tests/test_slippage_feedback_sizing.py`, `tests/test_krx_overnight_and_hurdle.py`, `tests/test_precision_timing_engines.py`, `tests/test_v6_adversarial_stress.py`, `tests/test_v6_improvements.py`.

---

## 1. Executive Summary & Architecture Overview

The Stock Trading System features an institutional-grade, multi-layered risk budgeting and autonomous execution engine that bridges predictive alpha signals to live market orders.

```
+--------------------------------------------------------------------------------------------------+
|                                31-Strategy Cross-Sectional Alpha                                  |
+--------------------------------------------------------------------------------------------------+
                                               │
                                               ▼
+--------------------------------------------------------------------------------------------------+
|                                   Risk Parity & Covariance Engine                                 |
|  - Ledoit-Wolf Optimal Shrinkage (Spherical Target F = (trace(S)/N)*I, condition clamp <= 1000)   |
|  - Marchenko-Pastur RMT Spectral Denoising (t_obs > N assets)                                    |
|  - Lower-Tail Stressed Joint Covariance & Asymmetric Clayton Copula (lambda_L in [0.10, 0.70])   |
|  - Downside Semi-Covariance (Sigma^-) for Sortino Optimization                                   |
+--------------------------------------------------------------------------------------------------+
                                               │
                                               ▼
+--------------------------------------------------------------------------------------------------+
|                               Portfolio Optimization & Allocation                                |
|  - Hierarchical Risk Parity (HRP): Ward Linkage + Quasi-Diagonalization + Recursive Bisection    |
|  - Return-Tilted HRP (R-HRP): Sharpe-based conviction alpha tilting                              |
|  - Black-Litterman (BL): 2D Regime-Adaptive Bayesian uncertainty (Crisis/Bear/Bull tuning)      |
|  - EVT-CVaR Budgeting: 3-Tier Fallback Hierarchy (POT-GPD -> Student-t/Cornish-Fisher -> Gauss)  |
|  - Continuous Fractional Kelly & Volatility Targeting (Quarter-Kelly, 12% target vol)            |
|  - Leland Dynamic No-Trade Buffer Bands: Transaction drag suppression (0.5% ~ 5.0%)               |
+--------------------------------------------------------------------------------------------------+
                                               │
                                               ▼
+--------------------------------------------------------------------------------------------------+
|                                  Risk Management & Crisis Gating                                  |
|  - 4-Tier Crisis Detection (NONE, WATCH, ACTIVE, SEVERE) via VIX, Drawdown, Volume, Macro CDS/Oil |
|  - VIX Velocity / Rate-of-Change Acceleration Bonus                                              |
|  - Hard Portfolio Circuit Breaker (MDD <= -15%) & Macro Economic Event Window Scaling             |
+--------------------------------------------------------------------------------------------------+
                                               │
                                               ▼
+--------------------------------------------------------------------------------------------------+
|                                Execution OMS & 7 Safety Gates                                    |
|  - Gate 0: Global Kill Switch (`is_kill_switch_active()`)                                        |
|  - Gate 0.5: SEVERE Crisis Mode (Block all BUYs, allow liquidation/hedging)                      |
|  - Gate 0.8: Leland Dynamic Buffer Band Gating (Bypass on new entries & full liquidation)        |
|  - Gate 1: Symbol Format Validation (`_SYMBOL_RE` regex sanitization)                             |
|  - Gate 2: Price Sanity Bounds ($1 ~ 100,000,000 KRW) & Exchange-Specific Tick Size Rounding     |
|  - Gate 7.1: KRX Synthetic Short / Cash Overlay Restriction                                      |
|  - Gate 7.2: KRX Upper/Lower Limit Lock Filter (+-30% price limit protection)                     |
|  - Gate 7.3: KRX STT / Transaction Cost Net Alpha Hurdle Check (Roundtrip + 10 bps margin)       |
|  - Gate 7.4: Dynamic Adverse Opening Gap Filter (-3 sigma shock protection)                      |
|  - Gate 7.5: ADV Capacity Cap (<= 5% ADV) with Multi-Currency Denomination Normalization          |
|  - Gate 7.6: VPIN Order Flow Toxicity Routing (VPIN > 0.70 -> PASSIVE_LIMIT)                     |
|  - Gate 7.7: Opening Gap Overheat Pullback Routing (Gap >= +5% -> DIP_LIMIT @ 1.5% discount)     |
|  - Gate 8: Synthetic Beta Inverse ETF Hedge Overlay in BEAR/CRISIS Regimes                       |
|  - Almgren-Chriss Optimal Slicing & Gatheral Transient Impact Kernel Execution Trajectories       |
|  - Closed-Loop Realized Slippage Feedback (`trade_logs.db` -> Dynamic Microstructure Cost Update)|
+--------------------------------------------------------------------------------------------------+
```

---

## 2. In-Depth Component Analysis & Findings

### Component 1: Portfolio Optimization (`src/analysis/portfolio_optimizer.py` & `src/risk/portfolio_optimizer.py`)

#### 1.1 Hierarchical Risk Parity (HRP) & Spectral Denoising
- **Distance Metric**: Correlation distance $d_{i,j} = \sqrt{0.5 \cdot (1 - \rho_{i,j})}$. This is a true metric satisfying non-negativity, symmetry, and triangle inequality on $[-1, 1] \to [0, 1]$.
- **Linkage Method**: Defaults to Ward linkage (`method="ward"`), effectively eliminating the chaining artifacts common in single-linkage clustering.
- **Spectral Denoising**: Integrates Marchenko-Pastur Random Matrix Theory (RMT) filtering (`FXAdjustedCovarianceEngine.denoise_covariance_marchenko_pastur`) when $T_{\text{obs}} > N$ and $N \ge 3$.
- **Recursive Bisection & Variance Calculation**:
  - Intra-cluster variance for cluster $c$ is computed using inverse-variance weights $w_c = \frac{\text{diag}(\Sigma_c)^{-1}}{\sum \text{diag}(\Sigma_c)^{-1}}$.
  - Left cluster weight split: $\alpha = 1 - \frac{V_{\text{left}}}{V_{\text{left}} + V_{\text{right}}} = \frac{V_{\text{right}}}{V_{\text{left}} + V_{\text{right}}}$.
  - Robustness guards: $V_{\text{left}} = \max(w_{\text{left}}^T \Sigma_{\text{left}} w_{\text{left}}, 10^{-16})$, and $\alpha$ is strictly clamped to $[0.01, 0.99]$.
- **Return-Tilted HRP (R-HRP)**: Conviction alpha tilting modulates cluster variance by $( \max(\text{Sharpe}, 10^{-4}) )^{\text{alpha\_tilt\_exponent}}$, tilting capital toward higher-Sharpe sub-trees while retaining the hierarchical risk structure.

#### 1.2 Black-Litterman Model
- **Equilibrium Prior**: $\Pi = \delta \Sigma w_{\text{prior}}$ where $\delta = \text{risk\_aversion}$.
- **2D Regime-Adaptive Bayesian Uncertainty**:
  - In `BEAR` or `CRISIS` regimes: $\tau \leftarrow 0.50 \tau$, $\Omega \leftarrow 2.0 \Omega$ (discounts subjective views, anchors to equilibrium prior).
  - In `BULL` regimes: $\tau \leftarrow 1.50 \tau$, $\Omega \leftarrow 0.70 \Omega$ (amplifies high-conviction predictive signals).
- **Meta Conviction Scaling**: $\Omega_{ii} = \frac{\Sigma_{ii} \cdot \omega_{\text{scale}}}{\text{conviction}_i}$, where $\text{conviction}_i \in [0.10, 1.50]$.
- **Tangency vs. Quadratic Utility Optimization**:
  - If $\max(\mu_{BL}) \le r_{f,\text{daily}}$, Sharpe optimization becomes non-convex/degenerate; the engine smoothly switches to quadratic utility maximization: $\max \left( w^T \mu_{BL} - \frac{1}{2} \lambda w^T \Sigma_{BL} w \right)$.
  - Otherwise, maximizes Sharpe ratio with smooth quadratic barrier below $r_f$.
- **Singular Matrix & Fallback Guard**: Wrapped in `try...except` block, automatically falling back to `calculate_risk_parity_weights(cov_matrix)` upon any inversion failure.

#### 1.3 Ledoit-Wolf Shrinkage & Positive Definiteness
- **Shrinkage Formulation**: $\Sigma_{\text{shrunk}} = (1 - \delta)\Sigma + \delta F$, where target $F = \frac{\text{trace}(\Sigma)}{N} I$.
- **Condition Number Clamp**: Eigenvalue decomposition via `np.linalg.eigh(shrunk_cov)` enforces $\lambda_{\min} \ge \max(10^{-8}, 10^{-6} \lambda_{\max})$, clamping condition number $\kappa(\Sigma) \le 1000.0$.

#### 1.4 Portfolio Constraints (`apply_portfolio_constraints`)
- **Single-Stock Cap**: Default 20.0% (`max_single_stock_weight = 0.20`), relaxed to $\max(\text{cap}, 1/N)$ for small universes ($N < 5$) to prevent constraint infeasibility.
- **Sector Cap**: Default 35.0% (`max_sector_weight = 0.35`), relaxed to $\max(\text{cap}, 1 / N_{\text{unique\_sectors}})$.
- **Iterative Redistribution**: Excess weight is proportionally redistributed to unconstrained assets over up to 10 iterations.

---

### Component 2: Tail Risk & Dynamic Allocation (`src/risk/portfolio_allocator.py`)

#### 2.1 Extreme Value Theory (EVT-CVaR) Budgeting
- **3-Tier Fallback Hierarchy**:
  - **Tier 1 (POT-GPD)**: Generalized Pareto Distribution fitted to losses exceeding threshold $u$. Integrates the Ferro-Segers (2003) extremal index $\theta \in [0.25, 1.0]$ to adjust for volatility clustering:
    $$\text{VaR}_\alpha = u + \frac{\beta}{\xi}\left[\left(\frac{N}{N_u}\frac{1-\alpha}{\theta}\right)^{-\xi} - 1\right], \quad \text{CVaR}_\alpha = \frac{\text{VaR}_\alpha + \beta - \xi u}{1 - \xi}$$
    The shape parameter $\xi$ is clamped to $[-0.50, 0.50]$ to guarantee finite mean and variance.
  - **Tier 2 (Cornish-Fisher & Student-t)**: Closed-form Student-$t$ distribution fit ($df > 2.0$) or 4th-moment Cornish-Fisher expansion adjusted for skewness and kurtosis.
  - **Tier 3 (Empirical Quantile / Gaussian Parametric)**: Activated when sample size $N < 10$.
- **Continuous Sigmoid Blending Kernel**:
  $$\lambda_{\text{GPD}} = \frac{1}{1 + e^{-0.5 (N_u - N_{\text{min\_tail}})}}$$
  Smoothly interpolates between Tier 1 and Tier 2 around $N_u = 15$, completely eliminating step discontinuities at sample boundaries.

#### 2.2 Lower-Tail Dependence & Asymmetric Clayton Copula
- Blends standard covariance with $10\text{th percentile}$ lower-tail joint covariance.
- Dynamically estimates the empirical Clayton lower-tail dependence coefficient $\lambda_L \in [0.10, 0.70]$ from cross-sectional simultaneous crash co-exceedance rates.
- Eigendecomposition spectral projection enforces strict positive semi-definiteness ($c_{\text{evals}} \ge 10^{-4}$).

#### 2.3 Leland Dynamic No-Trade Buffer Bands
- Optimal no-trade bandwidth for transaction cost suppression:
  $$\delta_i = \left( \frac{3 k c_i w_i^2}{2 \gamma \sigma_i^2} \right)^{1/3}$$
- Clamped between $\delta_{\text{floor}} = 0.005$ (50 bps) and $\delta_{\text{cap}} = 0.050$ (500 bps).
- **V6-09 Hardening**: Explicit bypass logic ensures fresh entries ($w_{\text{curr}} = 0$) and full liquidations ($w_{\text{target}} = 0$) are never blocked by the buffer bands.

#### 2.4 Capital Preservation Engines
- **CPPI Engine**: Floor $= \text{Peak\_NAV} \cdot (1 - \text{MDD\_limit})$, Cushion $= \max(0, \frac{\text{NAV} - \text{Floor}}{\text{NAV}})$, Target Exposure $= \min(0.85, 3.5 \times \text{Cushion})$.
- **Fractional Kelly Sizing**: Continuous Quarter-Kelly ($w_i = 0.25 \frac{\mu_i - r_f}{\sigma_i^2}$) combined with target volatility scaling (annualized target vol = 12%).

---

### Component 3: Risk Management & Crisis Gating (`src/risk/risk_manager.py`)

#### 3.1 CrisisDetector & Multi-Factor Macro Scoring
- **4 Crisis Levels**: `NONE`, `WATCH`, `ACTIVE`, `SEVERE`.
- **Composite Score Formula**:
  $$\text{Composite} = 0.25 \cdot \text{Score}_{\text{VIX}} + 0.25 \cdot \text{Score}_{\text{DD}} + 0.15 \cdot \text{Score}_{\text{Vol}} + 0.10 \cdot \text{Score}_{\text{Trend}} + 0.25 \cdot \text{Score}_{\text{Macro}}$$
- **Macro Boosters**:
  - **CDS 5Y Risk Spike Booster**: CDS $> 100$ bps boosts $\text{Score}_{\text{Macro}} \ge 0.85$; CDS $> 150$ bps triggers standalone `SEVERE` crisis level.
  - **Geopolitical Oil Shock Booster**: 3-day oil return $> 8.0\%$ boosts $\text{Score}_{\text{Macro}} \ge 0.75$.
- **VIX Acceleration Bonus**: 5-day rate-of-change $\Delta \text{VIX} / \text{VIX}_{-5}$ adds up to $+0.30$ to the VIX score.
- **Fail-Safe Missing VIX Baseline**: Missing or corrupted VIX defaults to a defensive `WATCH` score (0.35).
- **State Persistence & Thread Safety**: Protected by `threading.Lock()` and atomic JSON file replacement (`tmp_p.replace(p)`).

#### 3.2 Portfolio Circuit Breaker
- Hard portfolio-level max drawdown threshold (default $-15\%$). Triggers emergency cash liquidation if breached.

#### 3.3 Economic Calendar Risk Scaler
- Defensive exposure scaling ($[0.50, 1.00]$) applied during high-volatility event windows (FOMC, CPI, NFP).

---

### Component 4: Execution OMS & 7 Safety Gates (`src/execution/oms_engine.py`)

#### 4.1 OMS 7-Safety Gates Verification Matrix

| Gate | Description | Trigger Condition | Action / Safeguard | Verification Status |
|---|---|---|---|---|
| **Gate 0** | Global Kill Switch | `is_kill_switch_active() == True` | Immediately aborts all order plan generation. | **VERIFIED** |
| **Gate 0.5** | Severe Crisis Gating | `crisis_level == "SEVERE"` | Drops all BUY orders; converts holdings to SELL/liquidation. | **VERIFIED** |
| **Gate 0.8** | Leland Dynamic Buffer Band | $\|w_{\text{curr}} - w_{\text{target}}\| \le \delta_i$ | Skips redundant rebalancing trades. Bypassed for fresh entries & full exits. | **VERIFIED** |
| **Gate 1** | Symbol Sanitization | Corrupted string, `{`, `:`, `'`, spaces, non-regex | Drops malformed symbols via `_SYMBOL_RE.match()`. | **VERIFIED** |
| **Gate 2** | Price Sanity & Tick Rounding | $P < 1.0$ or $P > 10^8$ or NaN/missing | Rejects missing/stale prices. Rounds to KRX tiered ticks or US penny/sub-penny. | **VERIFIED** |
| **Gate 7.1** | KRX Short Prohibition | Action `SELL_SHORT` on KRX | Converted to synthetic `CASH_OVERLAY` (`HEDGE_FLAG`). | **VERIFIED** |
| **Gate 7.2** | Upper/Lower Limit Lock | 1D return $\ge +29.5\%$ or $\le -29.5\%$ on KRX | Rejects BUY on upper lock (+30%); queues `PASSIVE_LIMIT` SELL on lower lock (-30%). Only applied to KRX. | **VERIFIED** |
| **Gate 7.3** | Net Alpha Cost Hurdle | $\text{ExpRet}_{\text{net}} \le \text{Friction} + 10\text{ bps}$ | Drops trade if expected alpha cannot overcome roundtrip STT + spread + market impact. | **VERIFIED** |
| **Gate 7.4** | Adverse Opening Gap | 1D Gap $\le -3.0 \sigma_{\text{vol}}$ | Drops toxic opening collapse orders (exempts mean-reversion). | **VERIFIED** |
| **Gate 7.5** | ADV Capacity Cap | Order Amount $> 5\%$ ADV | Caps order value to $\le 5\%$ ADV in local currency (USD for US, KRW for KRX) and updates base portfolio target amount. | **VERIFIED** |
| **Gate 7.6** | VPIN Flow Toxicity | VPIN $> 0.70$ or Spread $> 100$ bps | Routes BUY to `PASSIVE_LIMIT` (maker order); routes SELL to `FAST_VWAP` (rapid liquidation). | **VERIFIED** |
| **Gate 7.7** | Opening Gap Overheat | 1D Opening Gap $\ge +5.0\%$ | Routes BUY to `DIP_LIMIT` at 1.5% discount pullback limit price. | **VERIFIED** |
| **Gate 8** | Inverse ETF Hedge Overlay | `regime_label in ("BEAR", "CRISIS")` | Generates synthetic inverse hedge order plan (`BUY_HEDGE`). | **VERIFIED** |

#### 4.2 Slicing Schedulers & Execution Trajectories
- **Almgren-Chriss Scheduler (`AlmgrenChrissScheduler`)**:
  - Hyperbolic schedule: $\tau(t) = \frac{\sinh(\kappa(1-t))}{\sinh(\kappa)}$.
  - Safe reconciliation of integer rounding discrepancies without producing negative tranches.
- **Gatheral Transient Impact Kernel (`GatheralMarketImpactKernel`)**:
  - Power-law decay kernel $G(t) = \frac{\eta}{(t + \tau_0)^{\alpha}}$.
  - Generates non-linear optimal slice trajectories minimizing transient impact and timing risk.

#### 4.3 Closed-Loop Slippage Feedback (`src/execution/slippage_feedback.py`)
- Reads historical executions from `trade_logs.db`.
- Calculates signed basis-point slippage (BUY: $P_{\text{exec}} > P_{\text{target}}$ is adverse; SELL: $P_{\text{exec}} < P_{\text{target}}$ is adverse).
- Computes empirical market impact scaling multipliers per market (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) and feeds back into `EnsembleScoringEngine` and `PortfolioAllocator`.

#### 4.4 Turnover Optimizer (`src/execution/turnover_optimizer.py`)
- Position hysteresis threshold (`turnover_threshold_pct = 0.05`) and minimum delta (50,000 KRW).
- Smooth decay transition between $1.0\times$ and $1.5\times$ threshold prevents bang-bang rebalance oscillation.
- Bypasses threshold for full liquidation ($w_{\text{target}} = 0$) and fresh entries ($w_{\text{curr}} = 0$).

---

## 3. Empirical Test Verification Results

All unit, integration, stress, and adversarial tests covering Portfolio Optimization and Execution OMS were run directly with `pytest`:

```
1. Baseline Portfolio & Risk Test Suite:
   .venv\Scripts\pytest tests/test_portfolio_allocator.py tests/test_portfolio_optimizer_and_oms.py tests/test_black_litterman.py tests/test_hrp_optimizer.py tests/test_order_manager.py tests/test_turnover_optimizer.py tests/test_slippage_feedback.py tests/test_risk_manager.py -v
   --> 86 passed in 21.17s (100% Pass)

2. Extended Portfolio, Microstructure & Timing Test Suite:
   .venv\Scripts\pytest tests/test_unified_portfolio_engine.py tests/test_adaptive_execution_feedback.py tests/test_challenger_portfolio_stress.py tests/test_confidence_adaptive_kelly.py tests/test_slippage_feedback_sizing.py tests/test_krx_overnight_and_hurdle.py tests/test_precision_timing_engines.py -v
   --> 67 passed in 87.45s (100% Pass)

3. V6 Improvements & Adversarial Stress Suite:
   .venv\Scripts\pytest tests/test_v6_adversarial_stress.py tests/test_v6_improvements.py -v
   --> 57 passed in 56.91s (100% Pass)

TOTAL: 210 targeted test cases passed with 100% pass rate.
```

---

## 4. Strengths, Weaknesses, and Concrete Hardening Recommendations

### Key Strengths
1. **Mathematical Rigor**: Implementation of Lopez de Prado's HRP with Ward linkage and spectral Marchenko-Pastur denoising, Rockafellar-Uryasev convex CVaR, Ferro-Segers extremal index clustering, and Almgren-Chriss / Gatheral optimal execution trajectories.
2. **Defensive Multi-Layer Safeguards**: 7 Safety Gates plus global kill switch, pre-trade ADV capacity capping, tick size rounding, directional slippage tracking, and dynamic Leland no-trade buffer bands.
3. **Resilience to Degenerate Inputs**: Graceful fallbacks across all optimizers for $N=1$, all-negative returns, singular/collinear covariance matrices, infinite/NaN inputs, and extreme volatility scenarios.

### Identified Potential Weaknesses & Hardening Recommendations

| # | Component | Observation / Risk | Concrete Hardening Recommendation | Priority |
|---|---|---|---|---|
| **W-1** | `src/analysis/portfolio_optimizer.py` | `apply_portfolio_constraints` line 512 references `sectors=sectors if 'sectors' in locals() else None`. In Python, `locals()` inside a function always contains its parameter names (as keys mapped to `None` if not provided), so the check evaluates to `None` when `sectors` is `None`. While working as intended, a direct `sectors=sectors` is cleaner and avoids reliance on `locals()`. | Replace `sectors=sectors if 'sectors' in locals() else None` with direct `sectors=sectors`. | Low |
| **W-2** | `src/risk/portfolio_optimizer.py` vs `src/analysis/portfolio_optimizer.py` | Two files named `portfolio_optimizer.py` exist in the codebase (`src/analysis/` with functional APIs and `src/risk/` with the class `PortfolioOptimizer`). While both work and tests cover both, developers could inadvertently import the wrong one. | Add a clear cross-module docstring in both files indicating the canonical usage (`src/analysis/portfolio_optimizer.py` for HRP/BL/HERC functions used by pipeline; `src/risk/portfolio_optimizer.py` for OOP wrapper). | Low |
| **W-3** | `src/risk/portfolio_allocator.py` | In `optimize_with_evt_cvar_constraint`, when $T=252$ days and $N=50$ assets, the auxiliary variable formulation has $N + 1 + T = 303$ variables, taking up to 1-2 seconds with SciPy SLSQP. Under extreme infeasible constraints, it attempts up to 100 iterations before falling back to Cornish-Fisher QP. | Set an adaptive iteration limit based on problem dimension: `maxiter = min(60, max(20, int(1500 / max(N + T, 1))))` to accelerate optimization time during backtesting and batch execution. | Medium |
| **W-4** | `src/execution/oms_engine.py` | Gate 7.5 ADV capacity cap applies a floor of $10,000 USD for US equities and 10,000,000 KRW for KRX. For ultra-small cap / penny stock regimes where ADV is under $5,000 USD, this could allocate above 100% of daily volume if ADV is near zero. | Cap `max_adv_amount = min(max_adv_ratio * adv_val, max(adv_floor, 0.50 * adv_val))` to prevent exceeding 50% ADV even on illiquid micro-caps. | Low |
| **W-5** | `src/execution/oms_engine.py` | In `calculate_trailing_stop_plan`, if `prices_dict` is not provided or contains less than 14 rows, ATR defaults to `curr_p * 0.02` (2%). | For high-volatility meme or crypto-adjacent equities, default ATR fallback could scale with `volatility_20d` from `current_holdings` if available (`curr_p * max(0.02, vol_20d)`). | Low |

---

## 5. Conclusion

The Portfolio Optimization and Execution OMS architecture is mathematically sound, highly resilient to edge cases, and thoroughly protected by institutional-grade safety gates. All 210 targeted unit, integration, stress, and adversarial tests pass with 100% success. The identified recommendations (W-1 ~ W-5) represent low-risk, high-efficiency quality-of-life hardening opportunities for subsequent milestones.
