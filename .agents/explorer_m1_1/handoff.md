# Handoff Report: Intraday Microstructure & Dynamic Stop-Loss Engine (Milestone 1 / R1)

## 1. Observation

- **Project Environment**: Windows OS, Python environment located at `.venv\Scripts\python.exe` (or `.venv/bin/python`).
- **Existing Architecture**:
  - `trading_system/src/risk/risk_manager.py`: Contains `RiskManager` (line 311) and `CrisisDetector` (line 75). `RiskManager` provides daily portfolio-level risk scaling, ATR stops (`calculate_atr_based_stop` at line 378), Kelly position sizing (`calculate_kelly_fraction` at line 627), and risk level assessment (`calculate_risk_level` at line 829).
  - `trading_system/run_pipeline.py`: Main orchestration pipeline. Risk monitoring phase is at lines 2445-2464:
    ```python
    # ── RiskManager & CrisisDetector Integration ──
    from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
    risk_mgr = RiskManager()
    crisis_detector = CrisisDetector(risk_mgr)
    crisis_lvl = crisis_detector.evaluate(...)
    ```
  - Unit tests location: `trading_system/tests/` (e.g., `trading_system/tests/test_risk_manager.py`).
- **Required New Files**:
  - `trading_system/src/risk/intraday_stop_loss.py` (with bridge in `src/risk/intraday_stop_loss.py`)
  - `trading_system/tests/test_intraday_stop_loss.py`
- **Specification Deliverable**: Detailed technical design saved at `d:\Finance\code\stock\.agents\explorer_m1_1\analysis.md`.

---

## 2. Logic Chain

1. **Observation 1 (Existing RiskManager)**: `RiskManager` evaluates daily macro crisis level via `CrisisDetector` and daily ATR stops, but currently lacks streaming intraday order book / price-volume momentum tracking.
2. **Observation 2 (Pipeline Execution)**: `run_pipeline.py` integrates `RiskManager` during Step 10 after signal generation. Without intraday stop-loss evaluation, candidate stocks experiencing intraday panic or sharp intraday drops (> -4%) could still be assigned capital allocation.
3. **Reasoning Step A**: Creating `IntradayStopLossEngine` in `trading_system/src/risk/intraday_stop_loss.py` provides real-time peak-to-trough drop tracking (-4% threshold default), volume spike panic acceleration detection (> 3.0x 20-min volume SMA with negative return), and dynamic ATR trailing stop calculation.
4. **Reasoning Step B**: Adding `evaluate_intraday_stop_loss()` and `check_intraday_risk()` to `RiskManager` connects the intraday stop-loss engine with macro crisis scaling (e.g., tightening drop thresholds when `CrisisLevel` is `ACTIVE` or `SEVERE`).
5. **Reasoning Step C**: Integrating `risk_mgr.check_intraday_risk()` into `run_pipeline.py` ensures that any asset breaching intraday risk thresholds is immediately flagged, setting expected returns to negative/zero and creating a risk alert.
6. **Reasoning Step D**: A comprehensive unit test suite in `trading_system/tests/test_intraday_stop_loss.py` verifies all trigger conditions (-4% peak drop, volume spike panic, normal movement pass, dynamic ATR breach, and `RiskManager` integration).

---

## 3. Caveats

- **Intraday Data Availability**: In live trading, streaming minute/second order book data requires real-time websocket/REST subscriptions (e.g. Korea Investment & Securities WS or Daishin CYBOS). In offline pipeline mode (`run_pipeline.py`), intraday data is evaluated using the latest available intraday DataFrame or price dictionary cache.
- **Volume SMA Sensitivity**: For low-liquidity assets, sudden small volume jumps can produce high volume ratios. The engine guards against false positives by requiring a negative return or price drop alongside the volume spike (`panic_volume_ratio >= 3.0` AND `instant_return < 0.0`).

---

## 4. Conclusion

The technical design specification for Milestone 1 (R1) is complete and documented in `d:\Finance\code\stock\.agents\explorer_m1_1\analysis.md`. 

Key deliverables ready for implementation:
1. `IntradayStopLossEngine` class & `StopLossResult` dataclass in `trading_system/src/risk/intraday_stop_loss.py`.
2. `RiskManager` integration methods (`evaluate_intraday_stop_loss`, `check_intraday_risk`) in `trading_system/src/risk/risk_manager.py`.
3. Pipeline risk phase integration in `trading_system/run_pipeline.py`.
4. Full test suite design in `trading_system/tests/test_intraday_stop_loss.py`.

---

## 5. Verification Method

To verify the implementation once coded:
1. Run pytest on the new unit test file:
   ```bash
   .venv/bin/pytest trading_system/tests/test_intraday_stop_loss.py -v
   ```
2. Verify full test suite regression:
   ```bash
   .venv/bin/pytest trading_system/tests/ -v
   ```
3. Inspect `analysis.md` and `handoff.md` in `d:\Finance\code\stock\.agents\explorer_m1_1\`.
4. Invalidation conditions: Any test failure in `test_intraday_stop_loss.py` or regression in `test_risk_manager.py`.
