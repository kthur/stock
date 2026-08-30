# Handoff Report: Portfolio & OMS Architecture Investigation

**Agent**: Explorer 1 (Portfolio & OMS Architecture Specialist)  
**Date**: 2026-08-30  
**Status**: Task Complete (Hard Handoff)  
**Detailed Analysis**: `d:\Finance\code\stock\.agents\explorer_portfolio_oms\analysis.md`

---

## 1. Observation

1. **Portfolio Optimization Implementation**:
   - `src/analysis/portfolio_optimizer.py`:
     - Line 11: `calculate_risk_parity_weights` implements Formulation B (Log-barrier optimization: $\min 0.5 x^T \Sigma x - \sum \ln(x)$), falling back to Formulation A (SLSQP), Inverse-Volatility ($1/\sigma_i$), and Equal Weighting ($1/n$).
     - Line 130: `calculate_black_litterman_weights` implements 2D Regime-Adaptive Bayesian uncertainty scaling (in `BEAR`/`CRISIS`, $\tau \times 0.5$, $\Omega \times 2.0$; in `BULL`, $\tau \times 1.5$, $\Omega \times 0.70$), with quadratic utility fallback when all excess returns $\le r_{f,\text{daily}}$.
     - Line 269: `shrink_covariance_matrix` computes analytical Ledoit-Wolf shrinkage to spherical target $F = \frac{\text{trace}(\Sigma)}{N} I$ with condition number clamping $\kappa(\Sigma) \le 1000.0$.
     - Line 348: `calculate_hrp_weights` implements Lopez de Prado's HRP with Ward linkage, Marchenko-Pastur RMT spectral denoising, and Sharpe-based Return-Tilted HRP (R-HRP).
     - Line 614: `apply_portfolio_constraints` enforces single-stock caps (20%), sector caps (35%), and factor exposure caps with dynamic relaxation for small universes ($N < 5$).
   - `src/risk/portfolio_allocator.py`:
     - Line 387: `estimate_evt_cvar` implements a 3-Tier Fallback Hierarchy (Tier 1 POT-GPD with Ferro-Segers extremal index $\theta \in [0.25, 1.0]$, Tier 2 Cornish-Fisher/Student-t, Tier 3 Empirical/Gaussian for $N < 10$), smoothly joined by a sigmoid blending kernel:
       $$\lambda_{\text{GPD}} = \frac{1}{1 + e^{-0.5 (N_u - N_{\text{min\_tail}})}}$$
     - Line 59: `compute_tail_stress_cov` blends $10\text{th percentile}$ lower-tail joint covariance and asymmetric Clayton Copula lower-tail dependence with spectral PSD projection.
     - Line 122: `compute_downside_semi_cov` computes downside semi-covariance ($\Sigma^-$) for Sortino optimization.
     - Line 416 & line 692: `PortfolioAllocator` implements Leland dynamic buffer bands ($\delta_i \in [0.005, 0.050]$) and $L_1/L_2$ turnover regularization.
   - `src/risk/risk_manager.py`:
     - Line 113: `CrisisDetector` computes 4 crisis levels (`NONE`, `WATCH`, `ACTIVE`, `SEVERE`) using a composite of VIX (25%), Drawdown (25%), Volume (15%), Trend (10%), Macro (USDKRW, Oil shock, TNX, DXY, CDS 5Y) (25%) with dynamic VIX acceleration bonus and hard MDD circuit breaker ($-15\%$).

2. **Execution OMS & 7 Safety Gates Implementation**:
   - `src/execution/oms_engine.py` (exposed via `src/execution/order_manager.py`):
     - Line 298: Gate 0 (Kill Switch) aborts all order generation if active.
     - Line 303: Gate 0.5 (Severe Crisis) blocks BUY orders, converting positions to liquidation.
     - Line 398: Gate 0.8 (Leland No-Trade Buffer Bands) skips redundant trades when $|w_{\text{curr}} - w_{\text{target}}| \le \delta_i$, with explicit bypass for fresh entries and full exits.
     - Line 378: Gate 1 (Symbol Sanitization) validates symbols against regex `_SYMBOL_RE`.
     - Line 445: Gate 2 (Price Sanity & Tick Rounding) validates prices in $[1.0, 100,000,000.0]$ and rounds to KRX tiered tick sizes (1, 5, 10, 50, 100, 500, 1,000 KRW) or US penny/sub-penny.
     - Line 454: Gate 7.1 converts KRX short signals to synthetic `CASH_OVERLAY` (`HEDGE_FLAG`).
     - Line 465: Gate 7.2 rejects BUY orders for KRX stocks locked at $+30\%$ upper limit; queues `PASSIVE_LIMIT` liquidation for $-30\%$ lower limit.
     - Line 485: Gate 7.3 drops BUY orders whose net expected alpha $\le \text{roundtrip friction} + 10\text{ bps}$.
     - Line 534: Gate 7.4 drops BUY orders with opening gap $\le -3.0 \sigma_{\text{vol}}$ (exempting mean-reversion).
     - Line 573: Gate 7.5 caps single order value to $\le 5\%$ ADV in local currency (USD for US, KRW for KRX) and updates base portfolio amount.
     - Line 641: Gate 7.6 routes high VPIN toxicity ($> 0.70$) BUY orders to `PASSIVE_LIMIT` maker orders and SELL orders to `FAST_VWAP`.
     - Line 658: Gate 7.7 routes overheated opening gap ($\ge +5.0\%$) BUY orders to `DIP_LIMIT` (1.5% discount pullback).
     - Line 697: Gate 8 inserts synthetic beta inverse ETF hedge orders (`BUY_HEDGE`) in BEAR/CRISIS regimes.
     - Line 1178: `AlmgrenChrissScheduler` computes hyperbolic slicing with non-negative integer tranche reconciliation.
     - Line 752: `record_execution` tracks directional basis-point slippage in `trade_logs.db` and updates `SlippageFeedbackEngine`.
     - `src/execution/turnover_optimizer.py`: Position hysteresis threshold (5%) with smooth decay transition.

3. **Test Execution Results**:
   - `tests/test_portfolio_allocator.py` + `tests/test_portfolio_optimizer_and_oms.py` + `tests/test_black_litterman.py` + `tests/test_hrp_optimizer.py` + `tests/test_order_manager.py` + `tests/test_turnover_optimizer.py` + `tests/test_slippage_feedback.py` + `tests/test_risk_manager.py`: **86 passed in 21.17s**
   - `tests/test_unified_portfolio_engine.py` + `tests/test_adaptive_execution_feedback.py` + `tests/test_challenger_portfolio_stress.py` + `tests/test_confidence_adaptive_kelly.py` + `tests/test_slippage_feedback_sizing.py` + `tests/test_krx_overnight_and_hurdle.py` + `tests/test_precision_timing_engines.py`: **67 passed in 87.45s**
   - `tests/test_v6_adversarial_stress.py` + `tests/test_v6_improvements.py`: **57 passed in 56.91s**
   - **Total**: **210 targeted portfolio & OMS test cases executed, 210 passed (100% pass rate)**.

---

## 2. Logic Chain

1. **Covariance Conditioning & Numerical Stability**:
   - Sample covariance matrices frequently suffer from rank deficiency ($N > T$) or ill-conditioning in financial markets.
   - Ledoit-Wolf shrinkage towards spherical target $F = \frac{\text{trace}(\Sigma)}{N} I$ combined with eigenvalue floor $\lambda_{\min} \ge \max(10^{-8}, 10^{-6} \lambda_{\max})$ guarantees that $\kappa(\Sigma) \le 1000.0$ and $\Sigma$ is strictly positive definite.
   - Therefore, quadratic forms $w^T \Sigma w$ and linear systems $\Sigma x = b$ are numerically stable across all optimizers (HRP, Black-Litterman, Risk Parity, SLSQP).

2. **Tail-Risk Modeling & Continuity**:
   - Standard VaR/CVaR assumes normality, underestimating kurtosis and crash contagion.
   - EVT POT-GPD with Ferro-Segers extremal index $\theta$ properly models fat tails and volatility clustering.
   - Sigmoid blending between POT-GPD and Cornish-Fisher/Student-t prevents discrete step jumps in risk budgets across sample sizes, ensuring stable weight rebalancing.

3. **Transaction Drag & Turnover Control**:
   - Frequent minor portfolio adjustments generate excessive transaction friction (STT tax, bid-ask spread, market impact).
   - Leland dynamic no-trade buffer bands ($\delta_i \in [0.005, 0.050]$) and turnover hysteresis suppress redundant rebalancing while explicitly bypassing fresh position entries ($w_{\text{curr}} = 0$) and full exits ($w_{\text{target}} = 0$).

4. **Execution Safety Gate Completeness**:
   - Automated trading systems without execution gates risk catastrophic order misrouting, flash crash slippage, and limit-lock traps.
   - The 7 Safety Gates systematically eliminate these failure modes:
     - Upper/lower limit locks protect against illiquidity traps.
     - VPIN toxicity routing prevents adverse selection.
     - ADV capacity capping in local currency prevents market impact blowout.
     - Tick size rounding ensures exchange compliance.

---

## 3. Caveats

- **Scope Boundary**: Investigation was conducted as read-only. Source code was analyzed and tested without applying modifications.
- **External Broker Integration**: Live broker API calls (e.g. KIS/EBEST API) were tested via simulated fixtures and SQLite DB execution logs (`trade_logs.db`).
- **SLSQP Execution Time**: Large universe ($N=50$, $T=252$) non-linear SLSQP EVT-CVaR optimization takes 1-2 seconds per call; the fallback to Cornish-Fisher QP ensures robustness if SLSQP iterations are constrained.

---

## 4. Conclusion

1. **State of Implementation**: The Portfolio Optimization and Execution OMS architecture is robust, mathematically rigorous, and protected by comprehensive safety gates. All 210 targeted test cases pass with 100% success.
2. **Key Quality-of-Life Recommendations**:
   - **W-1**: Clean up `locals()` check in `apply_portfolio_constraints` line 512.
   - **W-2**: Add cross-module docstrings distinguishing `src/analysis/portfolio_optimizer.py` (functional) and `src/risk/portfolio_optimizer.py` (class wrapper).
   - **W-3**: Implement adaptive iteration limits in `optimize_with_evt_cvar_constraint` to accelerate batch backtests.
   - **W-4**: Cap ADV floor to $\min(\text{max\_adv\_ratio} \cdot \text{ADV}, \max(\text{adv\_floor}, 0.50 \cdot \text{ADV}))$ for illiquid micro-caps.
   - **W-5**: Scale default fallback ATR in `calculate_trailing_stop_plan` with `volatility_20d` when prices dict has $< 14$ rows.

---

## 5. Verification Method

To independently reproduce and verify all results:

```bash
# 1. Run Baseline Portfolio & Risk Test Suite (86 tests)
.venv\Scripts\pytest tests/test_portfolio_allocator.py tests/test_portfolio_optimizer_and_oms.py tests/test_black_litterman.py tests/test_hrp_optimizer.py tests/test_order_manager.py tests/test_turnover_optimizer.py tests/test_slippage_feedback.py tests/test_risk_manager.py -v

# 2. Run Extended Portfolio & Stress Test Suite (67 tests)
.venv\Scripts\pytest tests/test_unified_portfolio_engine.py tests/test_adaptive_execution_feedback.py tests/test_challenger_portfolio_stress.py tests/test_confidence_adaptive_kelly.py tests/test_slippage_feedback_sizing.py tests/test_krx_overnight_and_hurdle.py tests/test_precision_timing_engines.py -v

# 3. Run V6 Improvements & Adversarial Stress Suite (57 tests)
.venv\Scripts\pytest tests/test_v6_adversarial_stress.py tests/test_v6_improvements.py -v
```

All commands must exit with code 0 and 0 failures.
