# Track C Handoff Report: Risk Management, Portfolio Optimization, Execution OMS & Test Blindspots

## 1. Observation

Direct code observations from source inspection and test runs:

1. **US Stocks Share Multiplier Bug in `unified_portfolio_allocator.py:494-506`**:
   - `alloc_amt = row.allocation_amount` (KRW currency, e.g. 5,000,000 KRW).
   - `px = latest_prices[i]` (USD currency for US equities, e.g. $150.0 for AAPL).
   - `raw_shares = int(alloc_amt // px)` evaluates to `int(5,000,000 // 150) = 33,333` shares instead of 24 shares.
   - `allocate()` signature lacks `usdkrw_rate` parameter, inflating US equities share counts by $1,350\times$.

2. **Black-Litterman Horizon Mismatch in `portfolio_optimizer.py:202-255`**:
   - `horizon_cov = cov_matrix` is daily covariance ($\Sigma \sim 10^{-4}$).
   - `Pi = risk_aversion * (horizon_cov @ w_eq)` is daily implied return ($\Pi \approx 0.0004$).
   - `Q` is passed from 20-day horizon returns (`ensemble_expected_return`, $\sim 5.0\%$).
   - In Markowitz quadratic utility `0.5 * lambda * w @ cov_bl @ w - w @ (mu_bl - rf_daily)`, the return term ($\sim 0.050$) dominates the daily variance term ($\sim 0.0005$) by $100:1$, collapsing optimization into a linear corner solution.
   - `if np.nanmean(np.abs(Q)) > 0.50: Q = Q / 100.0` creates a 100-fold discontinuity at the 0.50 boundary.

3. **CVaR Bound Infeasibility on Small N in `unified_portfolio_allocator.py:136-166`**:
   - `bounds = [(0.0, self.max_single_weight) for _ in range(n)]` with `sum(w) == 1.0`.
   - For $n \le 4$ and `max_single_weight = 0.20`, $\sum_{i=1}^n w_i \le 0.80 < 1.0$, rendering the feasible region empty and causing SLSQP to fail 100% of the time and fall back to inverse volatility.

4. **USD Account Buffer Band Deadlock in `turnover_optimizer.py:75` and `portfolio_allocator.py:1297-1299`**:
   - `min_rebalance_delta_krw = 50000.0` is hardcoded in KRW.
   - In USD accounts ($100,000 USD capital), $10,000 USD rebalances satisfy `$10,000 < 50,000`, causing permanent `HOLD`.
   - In `portfolio_allocator.py`, `min_weight_delta = 50,000 / 100,000 = 0.50`, causing a 50% buffer band that suppresses all rebalances.

5. **Stateless CrisisDetector in `run_pipeline.py:3698-3705`**:
   - `crisis_detector = CrisisDetector(risk_mgr)` is created freshly every cycle without calling `load_state()`.
   - `_vix_history`, `_dd_history`, and macro histories remain at length 1.
   - `vix_roc = 0.0`, `dd_speed = 0.0`, and macro Z-scores remain 0.0 perpetually. `save_state()` is never invoked, leaving `models/crisis_state.json` uncreated.

6. **Gate 8 Inverse Hedge Asset Selection Bias in `oms_engine.py:768-773`**:
   - `first_market = str(top_predictions[0].get("market", "KOSPI")) if top_predictions else "KOSPI"`.
   - Entire portfolio hedge instrument (`114800` vs `SH` vs `PSQ`) is selected exclusively by the market of the #1 ranked prediction.

7. **Slippage Feedback Single-Trade Parameter Explosion in `slippage_feedback.py:186-222`**:
   - When sample count $N=1$, a single 50 bps execution causes `cost_scaling_factor` to jump immediately to the 8.0x maximum cap.

8. **Test Suite Failure in `tests/test_institutional_portfolio_construction.py:193`**:
   - Running `.venv\Scripts\python.exe -m pytest tests/test_institutional_portfolio_construction.py -v` failed:
     `FAILED tests/test_institutional_portfolio_construction.py::TestUnifiedPortfolioAllocatorEndToEnd::test_end_to_end_allocate - assert 1 == 10`
   - Due to KRX lot size updated to 1 in code while test still asserted 10.

---

## 2. Logic Chain

1. **From Observation 1 to Real-World Over-Allocation Risk**:
   - `allocation_amount` in KRW divided by USD price without currency conversion directly produces $1,350\times$ more shares than intended.
   - A $3,700 USD allocation results in 33,333 shares ($5,000,000 USD). If an execution broker receives this order, it will either fail margin checks or severely over-leverage the account.

2. **From Observation 2 to Optimization Breakdown**:
   - In Markowitz utility, equating 20-day returns with 1-day variance destroys the risk-return trade-off. The optimization degenerates from a quadratic diversification program to a linear ranking selector, completely subverting the purpose of covariance estimation (Ledoit-Wolf / RMT).

3. **From Observation 3 to Solvers Crashing in Small Universes**:
   - When screening filters narrow candidate stocks to 3 or 4 names, the equality constraint $\sum w_i = 1.0$ violates the domain bound $w_i \le 0.20$.
   - The solver cannot find any feasible starting or ending point, forcing an unhandled fallback to simple inverse volatility.

4. **From Observation 4 to US Account Rebalance Freezes**:
   - In `TurnoverOptimizer`, applying a 50,000 unit threshold to USD amounts treats $50,000 USD as the minimum rebalance size.
   - Any portfolio adjustment below $50,000 is marked `HOLD`. In `PortfolioAllocator`, a 50% buffer band is enforced, freezing portfolio management.

5. **From Observation 5 to Macro Defensive Blindness**:
   - Because `CrisisDetector` is instantiated without history, rate-of-change and acceleration terms that detect sudden panic spikes are completely disabled. The system behaves as if the market has been static, delaying crisis downscaling.

---

## 3. Caveats

1. **Execution Broker Integration**:
   - The audit focused on the core codebase (`src/risk/`, `src/execution/`, `src/analysis/`). External broker APIs (e.g. Kiwoom OpenAPI, Korea Investment Securities KIS, Interactive Brokers) were examined via local OMS interfaces; real broker connectivity was not tested in live market hours.
2. **Optuna Strategy Hyperparameters**:
   - HPO configurations for multi-factor horizon weights were verified for mathematical consistency, but empirical backtests across multi-year tick datasets require separate long-duration runs.
3. **No Other Uncovered Areas**:
   - All 4 core areas specified in the Track C prompt (Portfolio Optimization, Macro Risk, Execution OMS 8 Gates, and Comprehensive Test Suite) were thoroughly audited.

---

## 4. Conclusion

The quantitative core and architecture of the 37-strategy system are exceptionally sophisticated (incorporating Rockafellar-Uryasev CVaR, Black-Litterman, Leland buffer bands, and Almgren-Chriss scheduling). However, **cross-currency unit scaling (USD vs KRW), time-horizon alignment (20d vs 1d), and pipeline state persistence** contain 5 critical defects that undermine live trading reliability.

Implementing the 14 structured remediations in `audit_report.md` will restore mathematical rigor, prevent over-allocation disasters, and ensure seamless end-to-end execution across Korean and US equity markets.

---

## 5. Verification Method

To independently verify all findings and test suite behavior:

1. **Verify KRX lot size test failure**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_institutional_portfolio_construction.py -v
   ```
   *Expected result*: Fails at line 193 with `assert 1 == 10`.

2. **Verify Core Track C Suite (88 passing baseline)**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_portfolio_allocator.py tests/test_portfolio_optimizer_and_oms.py tests/test_black_litterman.py tests/test_order_manager.py tests/test_slippage_feedback.py tests/test_risk_manager.py tests/test_turnover_optimizer.py -v
   ```
   *Expected result*: 88 passed.

3. **Verify Adversarial Stress Suite (30 passing)**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_challenger_portfolio_stress.py -v
   ```
   *Expected result*: 30 passed.

4. **Verify US Share Count Defect in Code**:
   Inspect `trading_system/src/risk/unified_portfolio_allocator.py` lines 494-506, confirming `raw_shares = int(alloc_amt // px)` divides KRW `alloc_amt` by USD `px` without dividing by `usdkrw_rate`.
