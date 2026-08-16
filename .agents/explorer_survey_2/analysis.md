# Comprehensive Investigation & Survey Report: R2 (Portfolio Asset Allocation & Microstructure Execution)

**Author**: Explorer 2 (Portfolio Allocation & Microstructure Execution Specialist)  
**Date**: 2026-08-15  
**Target Architecture**: Multi-Factor Portfolio Optimization, Tail Risk Budgeting, Microstructure Friction Cost Modeling & OMS Execution  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_2`  

---

## Executive Summary

This investigation surveys and assesses the implementation status, mathematical correctness, architectural integrity, and test verification of **Requirement 2 (R2: Portfolio Asset Allocation & Microstructure Execution)** within the 31-strategy quantitative trading system (`kthur/stock`).

### Core Findings Summary:
1. **Hierarchical Risk Parity (HRP) & Covariance Shrinkage**: Fully implemented and validated using Marcos Lopez de Prado's algorithm. Distance matrix computation $d_{i,j} = \sqrt{0.5(1 - \rho_{i,j})}$, single-linkage clustering, quasi-diagonalization, recursive bisection, and Ledoit-Wolf covariance shrinkage ($\delta=0.15$) are mathematically sound. Iterative single-stock (10%) and sector (25%) bounding preserves risk-parity properties without inducing synthetic zero-variance distortion.
2. **EVT-CVaR Tail Risk Loss Budgeting**: Implemented via Extreme Value Theory (EVT) Peaks-Over-Threshold (POT) Generalized Pareto Distribution (GPD) fitting. Employs a robust **3-Tier Fallback Hierarchy** (EVT-GPD $\to$ Cornish-Fisher Expansion $\to$ Empirical/Gaussian CVaR). Non-linear SLSQP optimization enforces $\text{EVT\_CVaR}_\alpha(w) \le \text{max\_cvar}$ alongside semi-variance downside penalties.
3. **Microstructure Friction Cost Modeling**: Directional Securities Transaction Tax (STT: KOSPI 0.15%, KOSDAQ 0.18%, KONEX 0.08%), US SEC regulatory fees (0.00278%~0.003%), brokerage commissions (KRX 0.030%, US 0.005%), dynamic bid-ask half-spreads ($S_i \propto \text{base} \times (\text{ADV}_{\text{ref}}/\text{ADV})^{0.25} \times (\sigma/\sigma_0)^{0.5}$), and square-root market impact ($\text{Impact} \propto \gamma \sigma_{\text{daily}} \sqrt{\text{Order}/\text{ADV}}$ with over-participation penalties) are integrated into net expected return calculations across `ensemble_scorer.py` and `portfolio_allocator.py`.
4. **Dynamic Leland Buffer Bands & Turnover Optimization**: Optimal no-trade buffer bands $\delta_i = \left[ \frac{3 c_i w_i \sigma_i}{2 \gamma} \right]^{1/3}$ reduce transaction cost drag by $\ge 60.0\%$ compared to fixed daily rebalancing. Hysteresis thresholds in `turnover_optimizer.py` suppress small churn rebalancing.
5. **Execution OMS Engine & Real-Time Closed-Loop Slippage Feedback**: `ExecutionOMSEngine` logs actionable order plans and realized executions to `trade_logs.db` under SQLite WAL mode with 6 live-money safety gates (Severe crisis suppression, kill switch, ticker regex sanitization, price bounds validation, lot rounding, order status lifecycle). Real-time realized slippage feedback dynamically updates `cost_scaling_factor` and `realized_market_impact_alpha` in `ensemble_scorer.py`.
6. **Quad-Factor Neutral QP Optimizer & Multi-Factor Style Neutralization**: Solves convex quadratic programming under beta, size, volatility, and momentum neutrality bounds ($|f_k^T w| \le 0.05$) and sector caps ($\le 0.25$) using CVXPY/OSQP with analytical SciPy SLSQP fallbacks. Cross-sectional QR regression decomposition in Strategy 21 (`multi_factor_neutralizer.py`) guarantees $|\rho| < 0.15$ with secondary Gram-Schmidt deflation.
7. **Test Verification**: 38/38 unit and integration tests across 8 test suites passed 100% in 15.12s.

---

## 1. Portfolio Asset Allocation & Risk Budgeting

### 1.1 Hierarchical Risk Parity (HRP)
- **Primary Source**: `trading_system/src/analysis/portfolio_optimizer.py` (`calculate_hrp_weights`) and `trading_system/src/risk/position_sizing.py` (`PortfolioAllocator.allocate`).
- **Mathematical Specification**:
  1. **Correlation Distance Matrix**:
     $$d_{i,j} = \sqrt{\frac{1}{2}(1 - \rho_{i,j})}, \quad \text{where } \rho_{i,j} = \frac{\Sigma_{i,j}}{\sigma_i \sigma_j}$$
  2. **Hierarchical Tree Clustering**: Single linkage clustering via `scipy.cluster.hierarchy.linkage(dist_condensed, method='single')`.
  3. **Quasi-Diagonalization**: Reorders the covariance matrix by sorting tree leaf nodes to place highly correlated assets adjacent to each other.
  4. **Recursive Bisection**: Recursively splits clusters into $C_{left}$ and $C_{right}$, computing cluster variances using inverse-variance weights:
     $$V_{left} = w_{left}^T \Sigma_{left} w_{left}, \quad w_{left} = \frac{\text{diag}(\Sigma_{left})^{-1}}{\sum \text{diag}(\Sigma_{left})^{-1}}$$
     $$\alpha = 1 - \frac{V_{left}}{V_{left} + V_{right} + 10^{-12}}$$
     $$w[C_{left}] \leftarrow w[C_{left}] \times \alpha, \quad w[C_{right}] \leftarrow w[C_{right}] \times (1 - \alpha)$$
  5. **Covariance Pre-Shrinkage**: Shrinks raw covariance towards diagonal variance target ($\delta = 0.15$) to prevent clustering distortion from short-sample noise:
     $$\Sigma_{\text{shrunk}} = (1 - 0.15) \Sigma + 0.15 \, \text{diag}(\text{diag}(\Sigma))$$
  6. **Iterative Single-Stock and Sector Bounds**: `apply_portfolio_constraints()` iteratively caps single stock weights at $\le 10.0\%$ and sector weights at $\le 25.0\%$ while redistributing excess weight without inducing zero-variance distortion.

### 1.2 Extreme Value Theory (EVT-GPD POT) CVaR Loss Budgeting
- **Primary Source**: `trading_system/src/risk/portfolio_allocator.py` (`estimate_evt_cvar`, `optimize_with_evt_cvar_constraint`).
- **Mathematical Specification**:
  - **Threshold Selection**: $u = \text{quantile}(\text{losses}, 0.90)$, where $\text{losses} = -R$. Exceedances $y_i = L_i - u > 0$.
  - **GPD Fitting (POT)**: Fits Generalized Pareto Distribution $G_{\xi, \beta}(y) = 1 - (1 + \xi y / \beta)^{-1/\xi}$ with fixed location 0.
  - **Analytical EVT VaR & CVaR**:
    $$\text{VaR}_\alpha = u + \frac{\beta}{\xi} \left[ \left(\frac{N}{N_u}(1 - \alpha)\right)^{-\xi} - 1 \right]$$
    $$\text{CVaR}_\alpha = \frac{\text{VaR}_\alpha + \beta - \xi u}{1 - \xi}$$
  - **3-Tier Fallback Hierarchy**:
    - **Tier 1 (EVT-GPD)**: Triggered when $N_u \ge 15$, $u > -10^{-6}$, GPD parameters converge ($\beta > 10^{-8}, \xi < 0.95$, clamped to $\xi \le 0.50$).
    - **Tier 2 (Cornish-Fisher Expansion)**: Tail-adjusted expansion utilizing sample skewness $S$ and excess kurtosis $K$:
      $$z_{cf} = z_\alpha + \frac{S}{6}(z_\alpha^2 - 1) + \frac{K}{24}(z_\alpha^3 - 3z_\alpha) - \frac{S^2}{36}(2z_\alpha^3 - 5z_\alpha)$$
      $$\text{VaR}_{cf} = \mu_L + \sigma_L z_{cf}, \quad \text{CVaR}_{cf} = \mu_L + \sigma_L \frac{\phi(z_{cf})}{1 - \alpha} \left[ 1 + \frac{S}{6}z_{cf}^3 + \frac{K}{24}(z_{cf}^4 - 2z_{cf}^2 - 1) \right]$$
    - **Tier 3 (Empirical / Gaussian Quantile)**: Used when $N < 10$ or numerical exceptions occur ($\text{CVaR}_{\text{gauss}} = \mu_L + \sigma_L \frac{\phi(z_\alpha)}{1 - \alpha}$).
  - **Non-linear SLSQP Optimization**:
    $$\min_w - \left( \mu^T w - \frac{1}{2} \gamma \left( 0.6 w^T \Sigma_{\text{LW}} w + 0.4 \, \mathbb{E}[\min(0, w^T R)^2] \right) \right)$$
    $$\text{s.t. } \text{EVT\_CVaR}_\alpha(w) \le \text{max\_cvar}, \quad \sum_{i=1}^n w_i = 1.0, \quad 0 \le w_i \le w_{\max}$$

### 1.3 Fractional Kelly & Volatility Targeting
- **Primary Source**: `trading_system/src/risk/portfolio_allocator.py` (`allocate_quarter_kelly`, `allocate_volatility_targeted_kelly`).
- **Mathematical Specification**:
  - **Quarter-Kelly Allocation**: $w_{\text{raw}, i} = \frac{1}{4} \frac{\mu_i}{\sigma_i^2}$.
  - **Conviction Boost Profile**:
    - Top 5% ($\ge p_{95}$): $\times 1.16$ ultra conviction boost
    - Top 10% ($p_{90} \le w < p_{95}$): $\times 1.12$ super conviction boost
    - Top 25% ($p_{75} \le w < p_{90}$): $\times 1.08$ premium boost
    - Lower tail ($< p_{25}$): $\times 0.92$ attenuation
  - **Volatility Targeting Scaling**:
    $$\sigma_{\text{port}} = \sqrt{252} \sum_{i=1}^n w_i \sigma_i, \quad \text{vol\_scale} = \text{clip}\left( \frac{\sigma_{\text{target}}}{\sigma_{\text{port}}}, 0.40, 1.25 \right)$$
    $$w_i^{\text{scaled}} = \text{clip}(w_i \times \text{vol\_scale}, 0.0, w_{\max})$$

### 1.4 Quad-Factor Neutral QP Portfolio Risk Optimizer
- **Primary Source**: `src/strategy/quad_factor_optimizer.py` and `trading_system/src/risk/portfolio_optimizer.py`.
- **Formulation**:
  $$\min_w \frac{1}{2} w^T \Sigma w - \lambda \mu^T w + \gamma \|w - w_0\|_2^2$$
  $$\text{s.t.} \quad \sum_{i=1}^n w_i = 1.0, \quad 0 \le w_i \le w_{\max} \quad (0.10)$$
  $$|f_k^T w| \le \epsilon_k \quad (0.05 \text{ for standardized Beta, Size, Volatility, Momentum})$$
  $$\sum_{i \in \text{Sector}_k} w_i \le \text{max\_sector\_weight} \quad (0.25)$$
- **Solver Execution**: OSQP via CVXPY with seamless fallback to SciPy SLSQP (using exact analytical Jacobians: $\nabla f(w) = \Sigma w - \lambda \mu + 2\gamma(w - w_0)$).
- **3-Tier Infeasibility Fallback**: Relaxed factor tolerances ($\times 2.0$) $\to$ Sector-constrained Mean-Variance $\to$ Bounded Equal-Weighting.

---

## 2. Microstructure Friction Costs & Net Return Sizing

### 2.1 Statutory Tax & Regulatory Exchange Fee Structure
| Market | Side | Statutory Tax (STT) | Regulatory Exchange Fee | Brokerage Commission | Total Fixed Friction |
|---|---|---|---|---|---|
| **KOSPI** | BUY | 0.00% | 0.000% | 0.030% (0.0003) | **0.030%** (3.0 bps) |
| **KOSPI** | SELL | **0.15%** (0.0015) | 0.000% | 0.030% (0.0003) | **0.180%** (18.0 bps) |
| **KOSDAQ** | BUY | 0.00% | 0.000% | 0.030% (0.0003) | **0.030%** (3.0 bps) |
| **KOSDAQ** | SELL | **0.18%** (0.0018) | 0.000% | 0.030% (0.0003) | **0.210%** (21.0 bps) |
| **KONEX** | SELL | **0.08%** (0.0008) | 0.000% | 0.030% (0.0003) | **0.110%** (11.0 bps) |
| **SP500 / NASDAQ / RUSSELL2000** | BUY | 0.00% | 0.000% | 0.005% (0.00005) | **0.005%** (0.5 bps) |
| **SP500 / NASDAQ / RUSSELL2000** | SELL | 0.00% | **0.00278%~0.003%** (SEC) | 0.005% (0.00005) | **0.008%** (0.8 bps) |

### 2.2 Dynamic Bid-Ask Spread Model
- **Formula**:
  $$S_i = \text{base\_spread} \times \left( \frac{\text{ADV}_{\text{ref}}}{\max(\text{ADV}_i, \text{ADV}_{\min})} \right)^{0.25} \times \left( \frac{\sigma_i}{\sigma_0} \right)^{0.50}$$
- **Parameters by Market**:
  - KOSPI: base 0.06% (0.0006), clamped to [0.02%, 1.50%], $\text{ADV}_{\text{ref}} = 1\text{B KRW}$
  - KOSDAQ: base 0.10% (0.0010), clamped to [0.03%, 2.50%], $\text{ADV}_{\text{ref}} = 1\text{B KRW}$
  - NASDAQ: base 0.03% (0.0003), clamped to [0.01%, 0.80%], $\text{ADV}_{\text{ref}} = \$1\text{M USD}$
  - RUSSELL2000: base 0.08% (0.0008), clamped to [0.02%, 1.50%], $\text{ADV}_{\text{ref}} = \$500\text{K USD}$
  - SP500: base 0.02% (0.0002), clamped to [0.01%, 0.50%], $\text{ADV}_{\text{ref}} = \$1\text{M USD}$

### 2.3 Square-Root Market Impact (Almgren-Chriss / Kyle's Lambda Proxy)
- **Formula**:
  $$\text{Impact}_{\text{one-way}} = \gamma \times \sigma_i \times \left( \frac{Q_{\text{order}}}{\text{ADV}_i} \right)^\alpha$$
  $$\text{If } \frac{Q_{\text{order}}}{\text{ADV}_i} > 0.10, \quad \text{Impact} \leftarrow \text{Impact} + 0.50 \times \left( \frac{Q_{\text{order}}}{\text{ADV}_i} - 0.10 \right)$$
- **Coefficients**: $\gamma_{\text{KRX}} = 0.75, \gamma_{\text{US}} = 0.50$, default $\alpha = 0.50$ (dynamically updated via realized slippage feedback).

### 2.4 Net Expected Return Deduction
- **Calculation in `ensemble_scorer.py`**:
  $$\text{Total Cost Rate} = \text{Tax} + \text{Brokerage} + 1.0 \times S_i + 2.0 \times \text{Impact}_{\text{one-way}}$$
  $$\text{Expected Net Return (\%)} = \text{clip}\left( \text{Raw Expected Return} - (\text{Total Cost Rate} \times \text{Scaling Factor}) \times 100.0, 0.0, 50.0 \right)$$

---

## 3. Dynamic Rebalancing & Turnover Suppression

### 3.1 Leland Dynamic No-Trade Buffer Bands
- **Primary Source**: `trading_system/src/risk/portfolio_allocator.py` (`calculate_dynamic_buffer_band`, `compute_portfolio_rebalance`).
- **Mathematical Derivation**:
  Balancing expected utility loss from allocation tracking error against transaction friction yields the optimal no-trade half-width:
  $$\delta_i = \left[ \frac{3 \, c_i \, w_i^* \, \sigma_i}{2 \gamma} \right]^{1/3}$$
  clamped to $[\delta_{\text{floor}}, \delta_{\text{cap}}] = [0.5\%, 5.0\%]$.
- **Execution Rules**:
  - **Inside Band** ($w_{\text{current}} \in [w_i^* - \delta_i, w_i^* + \delta_i]$): Action `HOLD`, trade weight $= 0.0$.
  - **Lower Breach** ($w_{\text{current}} < w_i^* - \delta_i$): Action `BUY`, executes to boundary $L_i = w_i^* - \delta_i$ (boundary mode) or $w_i^*$ (target mode).
  - **Upper Breach** ($w_{\text{current}} > w_i^* + \delta_i$): Action `SELL`, executes to boundary $U_i = w_i^* + \delta_i$ or $w_i^*$.
- **Empirical Cost Reduction**:
  Validated in `TestRebalancingBenchmark` over 250 daily steps: **achieves 62.4% transaction cost reduction** vs fixed daily rebalancing.

---

## 4. Execution OMS Engine & Closed-Loop Slippage Monitoring

### 4.1 Order Management System (OMS) Architecture
- **Primary Source**: `trading_system/src/execution/oms_engine.py`.
- **Database Schema (`trade_logs.db`)**:
  - `order_plans`: `order_id (PK)`, `symbol`, `name`, `market`, `action`, `target_weight`, `target_amount`, `target_price`, `quantity`, `status`, `created_at`.
  - `execution_logs`: `execution_id (PK AUTO)`, `order_id (FK)`, `symbol`, `target_price`, `executed_price`, `slippage_bps`, `executed_volume`, `executed_at`.

### 4.2 6 Live-Money Safety Gates
1. **Severe Crisis Gating**: If `crisis_level == "SEVERE"`, skips 100% of order plan generation.
2. **Kill Switch Gating**: `KILL_SWITCH` file / `KILL_SWITCH=true` env var / `kill_switch.engage()` blocks all order generation.
3. **Ticker Regex Validation**: `^[A-Z0-9][A-Z0-9.\-^]*$` sanitizes input, rejecting corrupt dict strings (e.g. `"{'is_vcp': False...}"`).
4. **Price Bounds Sanitization**: Rejects non-finite, $\le 0$, or out-of-bounds prices ($[1.0, 100,000,000]$ KRW).
5. **Lot Size Rounding**: KRX orders rounded to 10-share lots (`(qty // 10) * 10`); sub-lot orders dropped.
6. **Execution Lifecycle**: Tracks cumulative volume and updates status `PENDING` $\to$ `PARTIALLY_FILLED` $\to$ `EXECUTED`.

### 4.3 Closed-Loop Realized Slippage Feedback
- **Primary Source**: `trading_system/src/execution/slippage_feedback.py`.
- **Feedback Mechanism**:
  - Calculates realized slippage in basis points:
    $$\text{slippage\_bps} = \text{sign} \times \left( \frac{P_{\text{exec}} - P_{\text{target}}}{P_{\text{target}}} \right) \times 10,000$$
  - Estimates empirical market impact exponent $\alpha$ via log-linear regression $\log(\text{slippage}) \sim \alpha \log(\text{Order Size})$.
  - Calibrates $\text{cost\_scaling\_factor} = \text{clip}(\text{avg\_slippage\_bps} / 5.0, 0.50, 3.00)$.
  - Injects updated parameters into `ensemble_scorer.py` via `update_microstructure_costs()`.

---

## 5. Sector & Factor Neutrality Constraints

### 5.1 Regime-Adaptive Sector Concentration Caps
- **Implementation**: `portfolio_allocator.py` (`apply_sector_and_factor_constraints`) and `portfolio_optimizer.py`.
- **Rules**:
  - **BEAR / SIDEWAYS Regimes**: Strict **25.0% maximum sector cap** to prevent drawdown clustering.
  - **BULL Regime**: Dynamic relaxation to **35.0% sector cap** allowing high-momentum industry concentration.
  - **Rank-Preserving Proportional Redistribution**: Iteratively scales down over-concentrated sectors and redistributes excess capital proportionally to compliant sectors.

### 5.2 Multi-Factor Style Neutralization (Strategy 21)
- **Primary Source**: `trading_system/src/core/multi_factor_neutralizer.py`.
- **Mechanism**:
  1. Standardizes Fama-French 5 factors across market groups: Size ($SMB = \ln(\text{Cap})$), Value ($HML = 1/PBR$ or $E/P$), Profitability ($RMW = ROE$), Investment ($CMA = \Delta \text{Assets}$), Momentum ($UMD = 12M-1M$).
  2. Projects raw signal $y$ onto factor subspace via QR decomposition: $X = [1, Z]$, $Q R = X$, $y_{\text{proj}} = Q Q^T y$, $\text{residual} = y - y_{\text{proj}}$.
  3. **Hard SLA Deflation Gate**: Secondary Gram-Schmidt orthogonalization guarantees cross-sectional Pearson $|\rho| < 0.15$ against all 5 style factors.

---

## 6. Test Suite Status & Empirical Verification

### 6.1 Test Execution Results
All test suites relating to R2 were executed via `.venv\Scripts\python.exe -m pytest -v`:

| Test File | Total Items | Passed | Status |
|---|---|---|---|
| `tests/test_portfolio_allocator.py` | 11 | 11 | ✅ 100% Passed |
| `tests/test_portfolio_risk.py` | 3 | 3 | ✅ 100% Passed |
| `tests/test_hrp_optimizer.py` | 4 | 4 | ✅ 100% Passed |
| `tests/test_black_litterman.py` | 2 | 2 | ✅ 100% Passed |
| `tests/test_kelly_sizing.py` | 2 | 2 | ✅ 100% Passed |
| `trading_system/tests/test_portfolio_optimizer_and_oms.py` | 9 | 9 | ✅ 100% Passed |
| `trading_system/tests/test_slippage_feedback.py` | 7 | 7 | ✅ 100% Passed |
| **Combined Core R2 Suite** | **38** | **38** | **✅ 100% Passed (15.12s)** |

---

## 7. Observations & Recommendations

1. **Architecture Coherence**:
   - The dual implementation of `PortfolioAllocator` across `src/risk/portfolio_allocator.py` (EVT-CVaR, Leland bands, microstructure) and `src/risk/position_sizing.py` (Top-down market budgets, Kelly/HRP, Black-Litterman) is well-delineated.
   - `portfolio_optimizer.py` successfully bridges QuadFactorOptimizer and Mean-Variance with EVT-CVaR constraints.
2. **Microstructure Alignment**:
   - Both `microstructure.py` and `portfolio_allocator.py` have consistent statutory STT rates (KOSPI 0.15%, KOSDAQ 0.18%, KONEX 0.08%, US SEC 0.003%).
   - Dynamic bid-ask half-spread and square-root market impact correctly incorporate ADV and daily volatility.
3. **Execution Readiness**:
   - Live-money safety gates in `ExecutionOMSEngine` (Severe crisis kill switch, corrupt ticker validation, price sanity bounds, lot size rounding) provide comprehensive risk mitigation against erroneous broker execution.

---
