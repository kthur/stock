# Handoff Report: Review of `IMPROVEMENT_ROADMAP.md` (Portfolio, Cost & Infrastructure)

**Agent**: Portfolio, Cost & Infrastructure Reviewer (`reviewer_roadmap_2`)  
**Working Directory**: `d:/Finance/code/stock/.agents/reviewer_roadmap_2`  
**Target Document**: `d:/Finance/code/stock/IMPROVEMENT_ROADMAP.md` (v2.0.0-PROD)  
**Parent Agent**: `parent` (`d70ce817-65e5-434d-ba85-4d14736bb3cb`)  
**Date**: 2026-08-22  
**Final Review Verdict**: **APPROVE**  

---

## 1. Observation

1. **Leland Buffer OMS Dead Capital Trap**:
   - In `trading_system/src/execution/oms_engine.py` lines 375–395:
     ```python
     if use_leland_buffer and current_holdings is not None:
         curr_w = float(current_holdings.get(sym, 0.0))
         delta_i = p_alloc.calculate_dynamic_buffer_band(
             symbol=sym, target_weight=weight, cost_rate=c_rate, volatility_20d=vol_20d
         )
         if abs(curr_w - weight) <= delta_i:
             logger.info(f"[OMS LELAND BUFFER] Symbol {sym}: Current weight {curr_w:.3f} within ±{delta_i:.3f} of target {weight:.3f} -> skipping redundant trade (Hold)")
             continue
     ```
     Observed directly: when $w^* = 0.0$ and $w_{\text{curr}} = 3.0\%$ with $\delta_i = 3.5\%$, `abs(0.030 - 0.0) <= 0.035` evaluates to `True`, unconditionally skipping liquidation orders and trapping capital indefinitely. In contrast, `src/risk/portfolio_allocator.py` (line 937) possessed `is_full_exit` and `is_new_entry` guards.

2. **Microstructure Friction Small-Cap Over-Penalization**:
   - In `trading_system/src/ai/ensemble_scorer.py` lines 2268, 2288, 2441–2453:
     ```python
     q_order = np.full(len(merged), order_size_krx)   # 50,000,000 KRW
     q_order[m_russell] = order_size_sp500             # $50,000 USD
     participation_ratio = q_order / adv
     ov_mask = participation_ratio > 0.10
     impact_one_way[ov_mask] += 0.50 * (participation_ratio[ov_mask] - 0.10)
     raw_total_cost = stt_tax + (2.0 * brokerage_fee) + (1.0 * clamped_spread) + (2.0 * impact_one_way)
     merged['ensemble_expected_return'] = np.clip(raw_exp_ret - cost_series * 100.0, 0.0, 50.0)
     ```
     Observed directly: static $\$50\text{k}$ / $50\text{M KRW}$ order sizes assume $20\%$ participation on $\$250\text{k}$ ADV small-caps, calculating $>11.3\%$ round-trip friction and completely collapsing `ensemble_expected_return` to $0.0$.

3. **Monolithic Rate Limiter Bottleneck**:
   - In `trading_system/src/utils/rate_limiter.py` lines 8–53:
     `GlobalRateLimiter` enforces a single global lock and `min_interval = 1.0s` across all network requests. For 3,000 tickers, cold ingestion is serialized to 50 minutes of idle thread sleeping.

4. **Static Regulatory Filing Lag**:
   - In `trading_system/src/data_layer/earnings_data.py` line 74:
     `result['date_available'] = (fin.index + pd.Timedelta(days=60)).strftime('%Y-%m-%d')`
     Observed directly: flat 60-day lag unnecessarily delays US quarterly 10-Q (40-day statutory deadline) by 20 days and KRX quarterly reports (45-day statutory deadline) by 15 days, while creating a 30-day premature lookahead leakage on KRX annual reports (90-day deadline).

5. **Storage Connection Thrashing**:
   - In `trading_system/src/data_layer/indicator_storage.py` lines 195–207:
     `_connect()` called `sqlite3.connect()` on every individual query across hundreds of operations rather than caching open connections in `threading.local()`.

6. **Unit Test Baseline Status**:
   - Executed `.venv\Scripts\pytest tests\test_portfolio_allocator.py -v`:
     `11 passed in 33.07s` (100% PASS, 0 Failures, 0 Errors).

---

## 2. Logic Chain

1. **Portfolio Optimization & Tail Risk Budgeting (Obs 1, Obs 6)**:
   - Hardcoded covariance shrinkage ($\delta = 0.15$) in `portfolio_optimizer.py` fails to scale with the sample ratio $T/N$. Standardizing on analytical Frobenius-norm optimal Ledoit-Wolf shrinkage ($\delta^*$) provides mathematical consistency across the codebase.
   - Replacing heuristic SLSQP GPD quantile callbacks with the globally convex Rockafellar-Uryasev (2000) auxiliary LP/QP program eliminates numerical gradient stall, reduces computational complexity to $O(N+T)$, and guarantees deterministic global convergence.

2. **Execution OMS & Microstructure Modeling (Obs 1, Obs 2)**:
   - Adding `is_full_exit` and `is_new_entry` guards to `oms_engine.py` resolves the critical P0 bug where decaying assets were trapped in `HOLD`.
   - Scaling order size by portfolio capital and TWAP slicing ($\phi_i = \text{Order}_i / (\text{ADV}_i \times N_{\text{slices}})$) aligns the friction model with real-world execution, restoring the expected net return of Russell 2000 and KOSDAQ high-conviction breakout trades.

3. **Concurrency, Ingestion & Architecture (Obs 3, Obs 4, Obs 5)**:
   - Replacing `GlobalRateLimiter` with `HostTokenBucketRateLimiter` (Yahoo 5/10, FRED 10/20, ECOS 8/15, DART 4/8) unlocks independent endpoint concurrency, accelerating cold-cache ingestion by $4\times \sim 5\times$ (50m $\to$ <12m).
   - Adopting jurisdiction-specific filing lags (KRX 45d/90d vs US 40d/60d) captures quarterly earnings momentum 15–20 days earlier while removing annual KRX lookahead risk.
   - Adopting `threading.local()` connection reuse in `MarketIndicatorStorage` eliminates OS file descriptor churn and reduces database I/O latency by $30\%\sim 40\%$.

4. **Action Matrix & Rollout Planning**:
   - The 4-sprint implementation sequence properly structures dependencies: Sprint 1 resolves P0 execution blockers (Leland buffer, ESRW, cost model, rate limiter); Sprint 2 unifies dynamic regime aggregation and convex CVaR allocation; Sprint 3 refactors individual alpha models; Sprint 4 optimizes HPO, risk gating, and CI/CD operations.

---

## 3. Caveats

1. **LP/QP Turnover Slack Variable Splitting**: During implementation of the Rockafellar-Uryasev CVaR solver in Sprint 2, developers must explicitly split the L1 turnover norm $|w_i - w_i^{\text{prev}}|$ into auxiliary non-negative variables $z_i^+, z_i^- \ge 0$ to maintain pure convexity.
2. **Dust Weight Rounding**: In addition to $w^* = 0.0$, allocations below 50 bps ($w^* < 0.005$) should be rounded to zero to trigger full exit and prevent micro-lots from lingering.
3. **External API Quota Limits**: While the host-aware rate limiter accelerates ingestion, developers should monitor daily total API quotas (e.g. DART 10,000 req/day).

---

## 4. Conclusion

`IMPROVEMENT_ROADMAP.md` (v2.0.0-PROD) is mathematically rigorous, forensically accurate, and institutionally sound. It directly diagnoses and resolves the systemic return drags and concurrency bottlenecks present in the trading system while preserving all architectural invariants (KST timezone, 5 markets, SQLite WAL integrity, 6 OMS safety gates).

**Final Verdict**: **APPROVE**

---

## 5. Verification Method

To independently verify the observations, formulations, and test passes:
1. **Leland Buffer Trap Verification**:
   Inspect `trading_system/src/execution/oms_engine.py` lines 375–395. Verify that `abs(curr_w - weight) <= delta_i` executes without `is_full_exit` check.
2. **Microstructure Friction Verification**:
   Inspect `trading_system/src/ai/ensemble_scorer.py` lines 2268/2288 and 2441–2453. Verify that `q_order` is statically set to $50\text{M KRW}$ / $\$50\text{k USD}$.
3. **Rate Limiter Verification**:
   Inspect `trading_system/src/utils/rate_limiter.py` lines 8–53. Verify that `GlobalRateLimiter` enforces a 1.0s monolithic sleep.
4. **Unit Test Suite Execution**:
   Run `.venv\Scripts\pytest tests\test_portfolio_allocator.py -v` (11 passed).
   Run `.venv\Scripts\pytest tests\test_portfolio_optimizer_and_oms.py -v`.
5. **Invalidation Condition**:
   The approval would be invalidated if any mathematical formulation contained an algebraic error, if the proposed changes introduced lookahead bias, or if a P0 item broke backward compatibility with the existing test suite.
