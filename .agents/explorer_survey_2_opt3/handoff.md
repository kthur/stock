# Survey Explorer 2 Investigation Report: Milestone 2 (Requirement R2)
**Portfolio 4-Model Dynamic Blending & Darkpool/HFT OMS Execution Optimization**

- **Agent**: Survey Explorer 2 (`.agents/explorer_survey_2_opt3/`)
- **Parent**: `b46202ea-01da-4d8b-b60e-9285cbf907d4`
- **Date/Time**: 2026-09-04T05:55:00+09:00
- **Scope**: Requirement R2 (Portfolio allocation 4-model blending and execution OMS optimization)

---

## 1. Observation

### 1.1 Portfolio Allocation Engine (`unified_portfolio_allocator.py` & `portfolio_allocator.py`)

#### A. Static Discrete Regime Lookup for 4-Model Allocation
In `trading_system/src/risk/unified_portfolio_allocator.py` (lines 40–48), the 4-model blending configuration is defined as a static discrete lookup dictionary:
```python
    REGIME_OPTIMIZER_BLENDS = {
        "BULL_LOW_VOL": {"bl": 0.65, "herc": 0.25, "rp": 0.10, "cvar": 0.00},
        "BULL_HIGH_VOL": {"bl": 0.45, "herc": 0.35, "rp": 0.10, "cvar": 0.10},
        "SIDEWAYS_LOW_VOL": {"bl": 0.25, "herc": 0.45, "rp": 0.20, "cvar": 0.10},
        "SIDEWAYS_HIGH_VOL": {"bl": 0.15, "herc": 0.40, "rp": 0.20, "cvar": 0.25},
        "BEAR_LOW_VOL": {"bl": 0.05, "herc": 0.35, "rp": 0.20, "cvar": 0.40},
        "BEAR_HIGH_VOL": {"bl": 0.00, "herc": 0.20, "rp": 0.10, "cvar": 0.70},
        "CRISIS": {"bl": 0.00, "herc": 0.15, "rp": 0.05, "cvar": 0.80},
    }
```
In line 318 of `optimize_multi_model_blend`:
```python
    regime_key = str(regime).upper() if regime else "BULL_LOW_VOL"
    blend_cfg = self.REGIME_OPTIMIZER_BLENDS.get(regime_key, self.REGIME_OPTIMIZER_BLENDS["SIDEWAYS_LOW_VOL"])
```
- **Direct Observation**: When market regime flickers between states (e.g., `BULL_HIGH_VOL` to `SIDEWAYS_HIGH_VOL`), the Black-Litterman weight drops discontinuously from 0.45 to 0.15, and CVaR weight jumps from 0.10 to 0.25. There is no probability-weighted interpolation or temporal smoothing, causing discrete step-jump portfolio churn and avoidable turnover.

#### B. Architectural Divergence in CVaR / EVT-Tail Risk Modeling
In `trading_system/src/risk/unified_portfolio_allocator.py` (lines 204–290), `calculate_cvar_weights` performs standard sample Rockafellar & Uryasev (2000) linear/SLSQP optimization:
```python
    def obj_cvar(var):
        w = var[:n]
        cvar_part = float(var[n] + (1.0 / ((1.0 - alpha) * T)) * np.sum(var[n + 1:]))
        if has_alpha:
            return cvar_part - float(lambda_alpha * np.dot(w, p_rets))
        return cvar_part
```
- **Direct Observation**: `returns_df` is computed using a 60-day historical lookback window (`T = 60`). With confidence $\alpha = 0.95$, the expected number of tail loss exceedances is $(1 - 0.95) \times 60 = 3$ data points. This creates severe empirical estimation variance and tail-loss instability.
- **Contrast with `portfolio_allocator.py`**: In `trading_system/src/risk/portfolio_allocator.py`:
  * Lines 387–460: `estimate_evt_cvar` implements rigorous Extreme Value Theory (EVT) Peaks-Over-Threshold (POT) Generalized Pareto Distribution (GPD) fitting with Student-$t$ and Cornish-Fisher expansion fallback hierarchy.
  * Lines 59–120: `compute_tail_stress_cov` constructs an asymmetric downside Clayton Copula tail-stressed covariance matrix $\Sigma_{stressed}$ with dynamically estimated lower tail dependence $\lambda_L \in [0.10, 0.70]$.
  * However, `UnifiedPortfolioAllocator` currently does NOT utilize `estimate_evt_cvar` or `compute_tail_stress_cov`, leaving its "EVT-CVaR" component operating on small-sample empirical returns without extreme value tail modeling.

#### C. Gatheral 3/2-Power Market Impact Closed-Form Convergence
In `unified_portfolio_allocator.py` (lines 460–498):
```python
    # Gatheral impact parameter (kappa = 1.0)
    kappa = 1.0

    # Closed-Form Optimal Convergence Velocity:
    # theta_impact* = ((daily_alpha + lambda_alpha) / (1.5 * kappa * vols))^2 * (ADV / delta_trades)
    theta_impact = np.ones(n, dtype=float)
    active_mask = (delta_trades > 1e-6) & (gap_adv_ratios > 1e-6)
    if np.any(active_mask):
        numerator = daily_alpha[active_mask] + lambda_alpha[active_mask]
        denominator = 1.5 * kappa * vols[active_mask]
        trade_scaling = 1.0 / gap_adv_ratios[active_mask]
        theta_impact[active_mask] = ((numerator / denominator) ** 2) * trade_scaling
```
- **Direct Observation**: The impact parameter $\kappa = 1.0$ is held completely static. It does not account for off-exchange, dark pool, or ATS midpoint liquidity availability, where price impact is dramatically lower.

#### D. Volatility-Normalized Asymmetric Leland No-Trade Buffer Bands
In `unified_portfolio_allocator.py` (lines 555–626 and lines 71–101):
- Leland half-width: $\Delta_i = \left(\frac{3}{4} \frac{c_i w_i (1-w_i) \sigma_{ann}^2}{\gamma}\right)^{1/3}$ clipped to $[0.005, 0.035]$.
- Continuous Z-score: $z = \frac{u_{ret}}{\sigma_{20d}\sqrt{5}}$.
- Smooth runner expansion ($z > 0$): upper band multiplier scales $1.0 \to 1.8\times$.
- Smooth laggard tightening ($z < 0$): lower band multiplier scales $1.0 \to 0.6\times$.
- Boundary rebalancing: rebalances only to $L_i$ or $U_i$ upon breach.
- Bypass condition: $w_{curr} \le 10^{-4}$ or $w_{target} \le 10^{-4}$.

---

### 1.2 Execution OMS Engine (`oms_engine.py`, `smart_order_router.py`, `hft_engine.py`)

#### A. Disconnect Between OMS Order Planning and Smart Order Router (SOR)
In `trading_system/src/execution/oms_engine.py` (lines 896–955):
- `ExecutionOMSEngine.generate_order_plan` slices large orders into tranches via `AlmgrenChrissScheduler.compute_trajectory`, tagging early tranches as `MIDPOINT_PEG` and the final tranche as `AGGRESSIVE_TAKER`.
- In `trading_system/src/execution/smart_order_router.py` (lines 20–127), `SmartOrderRouter.route_order` defines a 3-tier multi-venue routing architecture:
  * Tier 1: ATS / Nextrade / Dark Pool Midpoint Cross Probe (`DARK_ATS_MIDPOINT`, `MIDPOINT_IOC`, default 40% qty, captures half-spread saving: `market_spread_bps / 2.0`).
  * Tier 2: Primary Peg Maker Resting Orders (`PRIMARY_EXCHANGE_MAKER`, `PRIMARY_PEG_LIMIT`, 70% of residual qty, captures maker rebate +2.5 bps).
  * Tier 3: Lit Exchange Sweeper (`LIT_EXCHANGE_SWEEPER`, `LIMIT_IOC` or `MARKET_OR_VWAP`, pays taker fee -1.5 bps).
- **Direct Observation**: In `run_pipeline.py` (lines 4148–4180), `oms_engine.generate_order_plan` is invoked, but `SmartOrderRouter` is never called. As a result, order plans generated by OMS contain Almgren-Chriss time slices, but lack multi-venue dark/maker/sweeper venue allocations and lack estimated cost savings in basis points.

#### B. Unused Dark Pool & HFT Orderbook Signals in Execution Urgency
- In `trading_system/src/data_layer/darkpool_tracker.py` (Strategy #30), `DarkPoolTrackerEngine` produces `darkpool_score`, `dark_pool_ratio`, `is_accumulation`, and `block_trade_net_usd`.
- In `trading_system/src/core/hft_engine.py` (Strategy #23), `MicrostructureImbalanceEngine` produces `microstructure_score`, `overnight_gap_edge`, and `bid_ask_imbalance`.
- In `trading_system/src/execution/adaptive_router.py`, `compute_orderbook_imbalance` calculates $OBI \in [-1.0, 1.0]$.
- **Direct Observation**: In `oms_engine.py` (lines 857–869), only `vpin` and `spread` are checked for Gate 7.6. The engine does NOT check whether high dark pool block accumulation is present to dynamically increase dark probing from 40% to 70%, nor does it feed $OBI$ into `AlmgrenChrissScheduler.calculate_peg_limit_price`.

---

### 1.3 Existing Test Suite Status
Executed test commands:
1. `.venv\Scripts\python.exe -m pytest tests/test_m2_portfolio_execution.py -v`:
   - **Result**: 12 passed in 15.29s (100% pass rate).
2. `.venv\Scripts\python.exe -m pytest tests/test_portfolio_allocator.py -v`:
   - **Result**: 13 passed in 17.67s (100% pass rate).
3. `.venv\Scripts\python.exe -m pytest tests/test_portfolio_optimizer_and_oms.py -v`:
   - **Result**: 11 passed in 14.02s (100% pass rate).
4. `tests/test_smart_router.py`: Unit tests for `src/execution/sor_router.py` (3 tests passed).
5. `tests/test_adaptive_router.py`: Unit tests for OBI and adaptive schedule (2 tests passed).

---

## 2. Logic Chain & Proposed Design

### 2.1 Logic Chain: From Problem to Quantitative Solution
1. **Observation 1.1.A** shows that discrete regime dictionary lookup induces discontinuous weight adjustments upon regime boundary crossing.
   $\implies$ **Step 1**: Interpolate 4-model weights continuously using Markov transition probabilities $[p_{bull}, p_{sideways}, p_{bear}]$, continuous volatility shock intensity $v_{vol}$, and crisis severity $c_{crisis}$, smoothed temporally with a 5-day EMA.
2. **Observation 1.1.B** shows that 60-day sample empirical CVaR collapses due to having only 3 tail observations at 95% confidence.
   $\implies$ **Step 2**: Augment `UnifiedPortfolioAllocator` with the EVT-GPD Peaks-Over-Threshold and Student-$t$/Cornish-Fisher parametric formulation, and inject Clayton Copula lower-tail stressed covariance $\Sigma_{stressed}$ during high volatility and crisis regimes.
3. **Observation 1.1.C** shows that Gatheral impact parameter $\kappa = 1.0$ ignores off-exchange/dark liquidity availability.
   $\implies$ **Step 3**: Introduce dark-pool-adjusted effective impact parameter $\kappa_{eff, i} = \kappa_0 (1 - 0.75 \delta_{dark, i})$, allowing stocks with heavy dark liquidity to converge faster to target weights without price distortion.
4. **Observation 1.2.A & 1.2.B** show that OMS order planning omits the 3-tier SOR execution legs and fails to adapt dark probing ratios to Strategy #30 dark pool accumulation.
   $\implies$ **Step 4**: Dynamically modulate dark probe ratio $\delta_{dark} \in [0.10, 0.75]$ based on Strategy #30, modulate Almgren-Chriss midpoint peg pricing based on Strategy #23 $OBI$, and attach structured 3-tier SOR routing payloads to every order plan in OMS.

---

### 2.2 Detailed Mathematical Formulations for Milestone 2

#### Equation 1: Continuous 2D / Markov Regime Blending Weights
Given Markov regime probabilities $p = (p_{bull}, p_{sideways}, p_{bear}) \in \Delta^2$, realized VIX level, and crisis indicator $c_{crisis} \in [0, 1]$:
$$
v_{vol} = \frac{1}{1 + \exp\left(-\frac{\text{VIX} - 20.0}{3.0}\right)} \in [0, 1]
$$
Raw model weights are formulated as continuous functions:
$$
\begin{aligned}
w_{BL}^{raw} &= p_{bull} \cdot (1 - v_{vol}) \cdot (1 - c_{crisis}) \cdot \exp(0.5 \cdot \text{Sharpe}_{20d}) \\
w_{HERC}^{raw} &= \left[p_{sideways} + 0.40 p_{bull} v_{vol} + 0.30 p_{bear} (1 - v_{vol})\right] \cdot (1 - 0.70 c_{crisis}) \\
w_{RP}^{raw} &= 0.10 + 0.15 \cdot (1 - c_{crisis}) \cdot v_{vol} \\
w_{CVaR}^{raw} &= \max\left(0.02, 0.60 p_{bear} + 0.30 v_{vol} + 0.85 c_{crisis}\right)
\end{aligned}
$$
Normalized weights:
$$
w_m^*(t) = \frac{w_m^{raw}(t)}{\sum_{j \in \{BL, HERC, RP, CVaR\}} w_j^{raw}(t)}, \quad \sum_{m} w_m^*(t) = 1.0000
$$
Temporal EMA smoothing with half-life $H_{blend} = 5$ days ($\alpha_{blend} = 1 - e^{-\ln 2 / 5} \approx 0.1294$):
$$
\bar{w}_m(t) = \alpha_{blend} w_m^*(t) + (1 - \alpha_{blend}) \bar{w}_m(t-1)
$$

#### Equation 2: Clayton Copula Tail-Stressed Covariance Injection
When $v_{vol} > 0.40$ or $p_{bear} + c_{crisis} > 0.30$, covariance matrix $\Sigma$ is blended with tail covariance $\Sigma_{tail}$:
$$
\Sigma_{stressed} = (1 - k_{eff}) \Sigma_{base} + k_{eff} \Sigma_{tail}, \quad k_{eff} = \min(0.50, 0.20 + 0.30 v_{vol})
$$
Lower-tail dependence coefficient $\lambda_L \in [0.10, 0.70]$ derived from cross-sectional joint crash frequency:
$$
C_{asym} = (1 - \lambda_L) C_{base} + \lambda_L \mathbf{1}\mathbf{1}^T
$$
Projected to the PSD cone via Higham spectral eigenvalue clipping:
$$
\Sigma_{final} = \text{diag}(\sigma) \cdot \text{Proj}_{PSD}(C_{asym}) \cdot \text{diag}(\sigma)
$$

#### Equation 3: Regime-Modulated Alpha-Tilt Intensity in CVaR
In `calculate_cvar_weights`, replace static $\lambda_\alpha = 0.50$ with:
$$
\lambda_\alpha(R) = \lambda_0 \times \max\left(0.05, 1.0 - 0.85 v_{vol} - 0.90 c_{crisis}\right)
$$
In high-volatility crash states, alpha tilt diminishes to 0.05, preventing directional chasing and enforcing pure tail loss minimization.

#### Equation 4: Dynamic Dark Pool Probing Ratio ($\delta_{dark}$)
From Strategy #30 (`darkpool_tracker`) signals:
$$
\delta_{dark, i} = \text{clip}\left(0.30 + 0.40 \cdot \text{darkpool\_score}_i + 0.15 \cdot \mathbb{I}_{\{is\_accum, i\}}, 0.10, 0.75\right)
$$
Effective Gatheral impact parameter for portfolio convergence velocity:
$$
\kappa_{eff, i} = \kappa_0 \times \left(1.0 - 0.75 \cdot \delta_{dark, i}\right)
$$
Optimal convergence velocity:
$$
\theta_{impact, i}^* = \left(\frac{\alpha_i^{daily} + \lambda_{\alpha, i}}{1.5 \kappa_{eff, i} \sigma_i}\right)^2 \times \frac{ADV_i}{\Delta Trades_i}
$$

#### Equation 5: HFT Microstructure & OBI-Driven Midpoint Peg Pricing
In `AlmgrenChrissScheduler.calculate_peg_limit_price`:
$$
\text{urgency} = \text{clip}\left(0.50 + 0.35 \cdot OBI \cdot \text{side\_sign} - 0.25 \cdot \text{toxicity}, 0.05, 0.95\right)
$$
where $\text{side\_sign} = +1$ for BUY and $-1$ for SELL.
For BUY:
$$
P_{peg} = P_{bid} + \text{urgency} \times (P_{ask} - P_{bid})
$$
For SELL:
$$
P_{peg} = P_{ask} - \text{urgency} \times (P_{ask} - P_{bid})
$$

---

## 3. Caveats & Risks

1. **ATS / Dark Pool Availability Constraints in KRX**:
   - South Korea's Nextrade (NXT) ATS launched in early 2025/2026. While operational for major KOSPI/KOSDAQ names, certain small-cap stocks still trade exclusively on the primary KRX lit book.
   - *Mitigation*: Fallback logic in `SmartOrderRouter.determine_destination` routes 100% to `KRX` lit book if `ats_available=False` or if the stock is not ATS-eligible.
2. **Computational Overhead of Copula Spectral Projections**:
   - Performing Higham PSD projection and SLSQP optimization on large universes ($N > 100$) can increase runtime.
   - *Mitigation*: The portfolio optimization pipeline runs on the top $N=30$ candidate assets (as specified in `run_pipeline.py` line 4086), keeping matrix dimensions $30 \times 30$, where eigendecomposition completes in $< 2$ milliseconds.
3. **Backward Compatibility**:
   - The test suite contains 2,182+ tests across `tests/`. Any modifications to method signatures in `UnifiedPortfolioAllocator` or `ExecutionOMSEngine` must support default parameters and keyword arguments to guarantee 0 regressions.

---

## 4. Conclusion & Concrete Action Plan for Implementation (Milestone 2)

### 4.1 Concrete Action Plan

| Task ID | Component | Target File | Modification Details |
|---|---|---|---|
| **M2-01** | Dynamic 4-Model Regime Blending | `src/risk/unified_portfolio_allocator.py` | Add `compute_dynamic_regime_blend_weights(regime, vix_val, crisis_severity)` computing continuous $[w_{BL}, w_{HERC}, w_{RP}, w_{CVaR}]$ with 5-day EMA smoothing. |
| **M2-02** | EVT Tail Covariance & Dynamic Alpha Tilt | `src/risk/unified_portfolio_allocator.py` | Inject `compute_tail_stress_cov` Clayton copula tail covariance in high-vol/crisis regimes; modulate $\lambda_\alpha(R)$ in `calculate_cvar_weights`. |
| **M2-03** | Dark-Pool-Adjusted Gatheral Impact | `src/risk/unified_portfolio_allocator.py` | Update Gatheral impact parameter $\kappa_{eff, i} = \kappa_0(1 - 0.75 \delta_{dark, i})$ based on Strategy #30 dark pool features. |
| **M2-04** | Dynamic Dark Probing & SOR Leg Attachment | `src/execution/oms_engine.py` | In `generate_order_plan`, compute dynamic $\delta_{dark, i} \in [0.10, 0.75]$ and invoke `SmartOrderRouter.route_order` to attach 3-tier SOR routing legs (`DARK_ATS_MIDPOINT`, `PRIMARY_EXCHANGE_MAKER`, `LIT_EXCHANGE_SWEEPER`) and `expected_cost_saving_bps`. |
| **M2-05** | HFT OBI Midpoint Peg Pricing | `src/execution/oms_engine.py` | In `AlmgrenChrissScheduler.calculate_peg_limit_price`, incorporate $OBI$ and microstructure toxicity into dynamic urgency pricing. |
| **M2-06** | Dedicated M2 Test Suite Expansion | `tests/test_m2_portfolio_execution.py` | Add unit/integration tests for: 1) Continuous Markov blend weight smoothing, 2) Tail-stressed copula covariance in CVaR, 3) Dynamic dark pool probing ratio scaling, 4) 3-tier SOR leg generation and cost savings tracking in order plans. |

---

## 5. Verification Method

### 5.1 Independent Execution Commands
```powershell
# 1. Run Milestone 2 specific tests
.venv\Scripts\python.exe -m pytest tests/test_m2_portfolio_execution.py -v

# 2. Run core portfolio allocator & optimizer tests
.venv\Scripts\python.exe -m pytest tests/test_portfolio_allocator.py tests/test_portfolio_optimizer_and_oms.py -v

# 3. Run smart order router & adaptive router tests
.venv\Scripts\python.exe -m pytest tests/test_smart_router.py tests/test_adaptive_router.py -v

# 4. Verify full regression suite compatibility
.venv\Scripts\python.exe -m pytest tests/ -k "portfolio or oms or router" -v
```

### 5.2 Invalidation Conditions
- Any test in `test_m2_portfolio_execution.py`, `test_portfolio_allocator.py`, or `test_portfolio_optimizer_and_oms.py` failing.
- Discontinuous step jump in 4-model weights exceeding 15% across adjacent regime transition steps.
- Dark pool probing ratio exceeding bounds $[0.10, 0.75]$ or producing negative tranche quantities.
- Missing `sor_routing` payload or corrupted JSON structure in `trade_logs.db`.
