# DISPATCH — Worker M1 Remediation (Milestone 1 Iteration 2)

**Role**: Quantitative Signal Implementer
**Working Directory**: `d:\Finance\code\stock\.agents\worker_m1_2\`
**Authoritative Reference**: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (see ## 2026-09-04T13:40:12Z)
**Failure Report**:
Reviewer 1 and Challenger 1 reported:
In `trading_system/src/ai/ensemble_scorer.py` inside `compute_quint_pillar_tensor_synergy` (around lines 4560–4590):
```python
elif 'BEAR_LOW_VOL' in reg_str or 'BEAR' in reg_str:
    ...
elif 'BEAR_HIGH_VOL' in reg_str:
    ...
```
Because `'BEAR'` in `'BEAR_HIGH_VOL'` is `True`, `'BEAR_HIGH_VOL'` is shadowed and becomes unreachable dead code. This incorrectly assigns `BEAR_HIGH_VOL` a synergy cap of `0.085` instead of `0.045`, causing an assertion failure in `tests/test_phase6_m1_challenger1_adversarial.py`.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
- `src/ai/ensemble_scorer.py`
- `src/ai/factor_suppression.py`
- `tests/test_phase6_signal_enhancement.py`
- `tests/test_phase6_m1_challenger1_adversarial.py`

## Instructions
1. In `src/ai/ensemble_scorer.py`, inspect all regime string matching branches in `compute_quint_pillar_tensor_synergy` (and any other methods).
2. Ensure specific conditions (`'BEAR_HIGH_VOL'`, `'BEAR_LOW_VOL'`, `'BULL_HIGH_VOL'`, `'BULL_LOW_VOL'`, `'SIDEWAYS_HIGH_VOL'`, `'SIDEWAYS_LOW_VOL'`) strictly precede generic fallbacks (`'BEAR'`, `'BULL'`, `'SIDEWAYS'`).
3. Move `elif 'BEAR_HIGH_VOL' in reg_str:` to precede `elif 'BEAR_LOW_VOL' in reg_str or 'BEAR' in reg_str:`.
4. Run all tests:
   `$env:PYTHONPATH="trading_system;trading_system/src;."; .venv\Scripts\pytest.exe tests/test_phase6_signal_enhancement.py tests/test_phase6_m1_challenger1_adversarial.py tests/test_phase5_signal_enhancement.py tests/test_phase4_signal_enhancement.py -v`
5. Verify 100% pass rate.
6. Write handoff report in `d:\Finance\code\stock\.agents\worker_m1_2\handoff.md`.
