# DISPATCH Log

## 2026-08-22T01:31:51+09:00

You are worker_m5 (Domain 4 Implementation Worker: V6-25 ~ V6-31).
Your working directory is: d:\Finance\code\stock\.agents\worker_m5\

Tasks:
- V6-25: Fix Cross-Market Currency Denominator Mismatch (KRW/USD 1,350x position explosion on US equities and Gate 8 inverse hedges) in order_manager.py / oms_engine.py using usdkrw_rate.
- V6-26: Fix Return Scale Ambiguity in OMS Safety Gates 7.2 & 7.4 in order_manager.py / oms_engine.py with automatic dimensionless return scale normalization ($/100.0$ if $|c| > 1.0$).
- V6-27: Fix Almgren-Chriss slicing residual underflow and non-negative tranche rounding in order_manager.py / oms_engine.py.
- V6-28: Remove Friction Cost Double-Deduction in OMS Gate 7.3 for ensemble_expected_return.
- V6-29: Exempt full liquidations ({targ}=0$) and fresh entries ({curr}=0$) from turnover hysteresis deadlock in 	urnover_optimizer.py.
- V6-30: Fix Slippage Sign Inversion for BUY_HEDGE and protect SQLite connection leak with 	ry...finally: conn.close() in src/execution/slippage_feedback.py.
- V6-31: Fix SmartOrderRouter ATS residual misrouting & duplicate order flooding on Nextrade ATS in smart_router.py / sor_router.py.
