## 2026-08-22T01:26:37+09:00

You are explorer_2 (Survey Agent for Domain 2 & Domain 4).
Your working directory is: d:\Finance\code\stock\.agents\explorer_2\

Mandatory inputs to read:
1. d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
2. d:\Finance\code\stock\system_improvement_report_v6.md (Sections on Domain 2: V6-09 ~ V6-16, Domain 4: V6-25 ~ V6-31)
3. d:\Finance\code\stock\AGENTS.md

Your Task:
1. Investigate all files and code locations for Domain 2 (V6-09 ~ V6-16) and Domain 4 (V6-25 ~ V6-31):
   - V6-09: Leland Dynamic Buffer Band Boundary Collapse ($w_curr=0, w_targ=0$) in `src/risk/portfolio_allocator.py`
   - V6-10: Black-Litterman Piecewise Step Discontinuity & Gradient Explosion in `src/analysis/portfolio_optimizer.py`
   - V6-11: EVT-POT Quantile Inversion ($u \le q_\alpha$) and Non-Regular GPD Shape Bounds ($\xi \ge -0.5$) in `src/risk/portfolio_allocator.py`
   - V6-12: Rockafellar-Uryasev Convex CVaR L1 Smoothing & Vectorized Constraint Callbacks in `src/risk/portfolio_allocator.py`
   - V6-13: CrisisDetector Recovery Latch Suppressing WATCH Defensive Haircuts in `src/risk/risk_manager.py`
   - V6-14: Primary Missing Reason Frequency Selector Distortion in `src/analysis/coverage_analyzer.py`
   - V6-15: Downside Co-semivariance Equicorrelation Shrinkage Erasing Negative Hedging in `src/analysis/portfolio_optimizer.py`
   - V6-16: RMT Marchenko-Pastur Residual Eigenvalue Noise Variance Over-Shrinking in `src/analysis/portfolio_optimizer.py`
   - V6-25: Cross-Market Currency Denominator Mismatch (KRW/USD 1,350x position explosion) in `src/execution/order_manager.py`
   - V6-26: Return Scale Ambiguity in OMS Safety Gates 7.2 & 7.4 in `src/execution/order_manager.py`
   - V6-27: Almgren-Chriss Slicing Residual Underflow & Non-Negative Tranches in `src/execution/order_manager.py`
   - V6-28: Friction Cost Double-Deduction in OMS Gate 7.3 in `src/execution/order_manager.py`
   - V6-29: Turnover Hysteresis Deadlock Trapping Liquidated Positions in `src/analysis/portfolio_optimizer.py` (or `TurnoverOptimizer`)
   - V6-30: Slippage Sign Inversion for BUY_HEDGE & SQLite Connection Leak in `src/execution/slippage_feedback.py`
   - V6-31: SmartOrderRouter ATS Residual Misrouting & Duplicate Order Flooding in `src/execution/smart_router.py`
2. Identify existing test coverage in `tests/` for Domain 2 and Domain 4, and specify what tests need updates or new test cases.
3. Provide a concrete implementation and verification plan.
4. Write your findings to `d:\Finance\code\stock\.agents\explorer_2\analysis.md` and `handoff.md`.
5. Send a completion message back with summary of findings.
