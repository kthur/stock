# Dispatch: Worker M1 & M2 (Core Trading & ML Predictor Remediation)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_m2_core

## Original Request
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
d:\Finance\code\stock\ORIGINAL_REQUEST.md

## Reference Explorer Reports
- Explorer 1 (Track 1 R1 & R2): `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m0_track1\handoff.md`
- Explorer 2 (Track 2 R4): `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m0_track2\handoff.md`

## Exclusive File Ownership
You have exclusive write ownership over:
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/__init__.py`
- `trading_system/src/ai/transformer_predictor.py`
- `trading_system/src/ai/lstm_predictor.py`
Do NOT edit any files outside of these.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tasks
1. Apply the fixes to `trading_system/src/ai/ensemble_scorer.py`:
   - Line 19181-19184: define `reg_str = regime_str`.
   - Line 19501: change `elif 'BULL' in reg_str` to `elif 'BULL' in regime_str`.
   - Lines 27790-27843: calibrate `get_regime_adaptive_gamma_top` constants for v8, v9, v10 (CRISIS floor 0.20, v8 BULL_LOW_VOL 0.85, etc., as detailed in Explorer 1 handoff).
2. Apply PyTorch mock hardening in `trading_system/src/__init__.py`:
   - Implement missing operators on `DummyTensor` (`__mul__`, `__add__`, `__sub__`, `__truediv__`, `__neg__`, `__pow__`, `shape`, `dim`).
   - Populate `mock_optim.lr_scheduler` (`ReduceLROnPlateau`, `CosineAnnealingLR`) and `mock_nn` (`HuberLoss`, `GELU`, `ModuleDict`, `clip_grad_norm_`).
3. Apply tensor shape handling and checkpoint persistence in `trading_system/src/ai/transformer_predictor.py` and `trading_system/src/ai/lstm_predictor.py`.
4. Run tests to verify:
   - `.venv\Scripts\python.exe -m pytest tests/test_phase5_m1_challenger2_adversarial.py tests/test_phase5_signal_enhancement.py -v`
   - `.venv\Scripts\python.exe -m pytest tests/test_phase6_m1_challenger2_adversarial.py tests/test_phase6_signal_enhancement.py -v`
   - `.venv\Scripts\python.exe -m pytest tests/test_phase7_m1_challenger1_adversarial.py tests/test_phase7_signal_enhancement.py -v`
   - `.venv\Scripts\python.exe -m pytest tests/test_phase8_m1_challenger1_adversarial.py tests/test_phase8_m1_challenger2_empirical.py tests/test_phase8_signal_enhancement.py -v`
   - `.venv\Scripts\python.exe -m pytest tests/test_phase9_signal_enhancement.py tests/test_phase10_signal_enhancement.py -v`
   - `.venv\Scripts\python.exe -m pytest tests/test_transformer_predictor.py tests/test_sprint3_alpha_refactor.py tests/test_v7_returns_maximization.py -v`
5. Write your comprehensive handoff report to `d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_m2_core\handoff.md`.

## 2026-09-23T09:55:26Z
<USER_REQUEST>
You are Worker 1 (Core Trading & ML Predictor Remediation).
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_m2_core
Read your dispatch instructions in: d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_m2_core\DISPATCH.md
Read the authoritative user request in:
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- d:\Finance\code\stock\ORIGINAL_REQUEST.md
Read the reference handoffs:
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m0_track1\handoff.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m0_track2\handoff.md

Your exclusive write ownership:
- trading_system/src/ai/ensemble_scorer.py
- trading_system/src/__init__.py
- trading_system/src/ai/transformer_predictor.py
- trading_system/src/ai/lstm_predictor.py
Do NOT edit any other files.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. In `trading_system/src/ai/ensemble_scorer.py`:
   - Line 19181-19184: define `reg_str = regime_str`.
   - Line 19501: change `elif 'BULL' in reg_str` to `elif 'BULL' in regime_str`.
   - Lines 27790-27843: calibrate `get_regime_adaptive_gamma_top` constants for v8, v9, v10 (CRISIS floor 0.20, v8 BULL_LOW_VOL 0.85, etc., per Explorer 1 handoff).
2. In `trading_system/src/__init__.py`:
   - Harden mock PyTorch (`DummyTensor` arithmetic/attributes, `mock_optim.lr_scheduler`, `mock_nn` classes).
3. In `trading_system/src/ai/transformer_predictor.py` and `trading_system/src/ai/lstm_predictor.py`:
   - Implement 2D/3D tensor shape resilience, batch=1 1D view output, and checkpoint dimension persistence.
4. Execute test commands using `.venv\Scripts\python.exe -m pytest` across Phase 5-10 tests, Transformer, LSTM, and V7 returns maximization tests.
5. Write your complete handoff report to `d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_m2_core\handoff.md`.
6. Send a message to orchestrator parent when complete.
</USER_REQUEST>
