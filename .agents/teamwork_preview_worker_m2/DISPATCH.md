## 2026-09-03T12:07:19Z
You are a Worker agent (teamwork_preview_worker) implementing Milestone 2 / Requirement 2 (R2) & OMS Fixes.
Your identity: Portfolio Allocator & Cost Worker (Worker M2)
Your working directory: d:\Finance\code\stock\.agents\teamwork_preview_worker_m2
Parent conversation ID: 9f89ea60-abb5-4468-88df-62eb0473f19b

MANDATORY FIRST STEP:
Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md, d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\handoff.md, and d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\handoff.md.

EXCLUSIVE WRITE OWNERSHIP (You may only modify these files):
- src/risk/unified_portfolio_allocator.py
- src/analysis/portfolio_optimizer.py
- src/risk/portfolio_allocator.py
- src/execution/turnover_optimizer.py
- src/execution/oms_engine.py
- trading_system/run_pipeline.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

TASK OBJECTIVES:
1. CRIT-01: Multi-Currency FX Translation in `src/risk/unified_portfolio_allocator.py:479-506, 674-703`:
   - In `allocate()`, accept `base_currency: str = "KRW"` and `usd_krw: float = 1350.0`.
   - In share calculation: `eff_price = px * usd_krw if (is_us and base_currency == 'KRW') else (px / usd_krw if (is_krx and base_currency == 'USD') else px)`.
   - `raw_shares = int(allocated_capital / eff_price) if eff_price > 0 else 0`.
   - In `trading_system/run_pipeline.py:4072-4081`, forward `base_currency="KRW"` and `usd_krw=float(usdkrw_report)`.
2. CRIT-02: Black-Litterman Horizon vs Covariance Scaling in `src/analysis/portfolio_optimizer.py:143-265` & `src/risk/unified_portfolio_allocator.py`:
   - In `calculate_black_litterman_weights()`, convert view returns to daily scale: `Q_daily = Q_decimal / float(eff_horizon)` with automatic scale detection (percent vs decimal).
   - In `UnifiedPortfolioAllocator.allocate()`, pass `view_horizon=self.target_horizon` to `calculate_black_litterman_weights()`.
3. CRIT-06: Small Universe (N <= 4) CVaR Bound in `src/risk/unified_portfolio_allocator.py:171-176`:
   - Set degree-of-freedom bound: `max_w = min(1.0, max(self.max_single_weight, 1.0 / max(n - 1, 1)))`.
4. CRIT-07: Currency-Adaptive Minimum Trade Threshold in `src/execution/turnover_optimizer.py:70-87` & `src/risk/portfolio_allocator.py:1304-1314`:
   - Adaptive threshold: `min_rebalance_delta = 50.0 if is_usd else 50_000.0`.
5. HIGH-15: Cornish-Fisher VaR fallback to Expected Shortfall in `src/risk/portfolio_allocator.py:670-699`:
   - Integrate empirical tail mean beyond VaR: `cvar_val = float(np.mean(tail_losses))`.
6. HIGH-16: Gatheral 3/2-Power Market Impact & 5% ADV Bound:
   - In `unified_portfolio_allocator.py`, add 5% ADV hard liquidity participation constraint: `abs(w_i - w_curr_i) <= (0.05 * ADV_i) / V_port`.
7. MED-12: HERC dynamic weight caps in `src/analysis/portfolio_optimizer.py:574-583, 658-664`:
   - Delegate `max_single_stock_weight` and `max_sector_weight` from `UnifiedPortfolioAllocator`.
8. Asymmetric Leland No-Trade Buffer Bands in `unified_portfolio_allocator.py:405-468` & `portfolio_allocator.py:1220-1375`:
   - In `unified_portfolio_allocator.py:427`, fix volatility formula to Delta_i proportional to (c * sigma_ann^2 / gamma)^(1/3).
   - Apply asymmetric multipliers: 1.8x for winners (>= +8%), 0.6x for laggards (<= -3%).
   - Explicitly bypass buffer for fresh entries (w_curr == 0) and full exits (w_target == 0).
9. Active Regression Fix in `src/execution/oms_engine.py:716-725`:
   - In liquidation SELL orders for existing positions, use `current_holdings[sym]["quantity"]` directly rather than dividing currency-converted capital by price, ensuring unannotated test symbols liquidate properly.
10. Verification:
    - Run tests using `.venv\Scripts\python.exe -m pytest tests/test_institutional_portfolio_construction.py tests/test_portfolio_optimizer_and_oms.py tests/test_turnover_optimizer.py tests/test_position_lifecycle_optimization.py tests/test_v8_remediation.py -v`.
    - Ensure 100% pass with 0 failures.
11. Write detailed handoff report to `d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\handoff.md`.
Update `progress.md` with timestamps and test results. Send completion message to parent.
