## 2026-07-31T09:43:10Z
Task: Implement Milestone 1 (R1): Intraday Microstructure & Dynamic Stop-Loss Engine.

Follow technical specifications in `d:\Finance\code\stock\.agents\explorer_m1_1\analysis.md`:

1. Create `trading_system/src/risk/intraday_stop_loss.py`:
   - Implement `IntradayStopLossEngine` and `StopLossResult` dataclass.
   - Features:
     - Real-time intraday order book / price momentum tracking.
     - Peak-to-trough drop detection (-4% threshold default, configurable).
     - Volume spike panic acceleration detection (volume ratio >= 3.0x 20-min rolling SMA AND instant return < 0.0).
     - Dynamic trailing ATR/volatility stop threshold.
     - Alert creation & liquidation recommendation.
   - Also create a bridge file at `src/risk/intraday_stop_loss.py` if needed for top-level package resolution.

2. Update `trading_system/src/risk/risk_manager.py`:
   - Add `evaluate_intraday_stop_loss(symbol, intraday_df)` and `check_intraday_risk(symbol, intraday_df)` to `RiskManager`.
   - Tighten drop thresholds when macro `CrisisLevel` is elevated (`ACTIVE` or `SEVERE`).

3. Update `trading_system/run_pipeline.py`:
   - Integrate `RiskManager.check_intraday_risk` into the pipeline risk phase (Step 10).

4. Create unit tests in `trading_system/tests/test_intraday_stop_loss.py`:
   - Test -4% peak-to-trough price drop trigger.
   - Test volume spike panic acceleration trigger.
   - Test normal price movement passing cleanly.
   - Test dynamic ATR trailing stop.
   - Test `RiskManager` integration.

5. Execute tests:
   - Run `.venv\Scripts\python.exe -m pytest trading_system/tests/test_intraday_stop_loss.py -v` (or `.venv/bin/pytest ...`).
   - Run `.venv\Scripts\python.exe -m pytest trading_system/tests/ -v` to ensure zero regressions.

Deliverables:
1. Write detailed implementation report to `d:\Finance\code\stock\.agents\worker_m1_1\changes.md`.
2. Write self-contained handoff report to `d:\Finance\code\stock\.agents\worker_m1_1\handoff.md` with build and test command outputs.
3. Notify parent with `send_message`.
