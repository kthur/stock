# Dispatch: Challenger 1 (Adversarial Stress Testing & Numerical Edge Cases)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_challenger_1_gen2

## Original Request
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
d:\Finance\code\stock\ORIGINAL_REQUEST.md

## Worker Handoffs to Challenge
- Worker 1: `d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_m2_core\handoff.md`
- Worker 2: `d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_reports\handoff.md`

## Mission
Empirically stress-test the modified system with adversarial and edge-case inputs:
1. Test `EnsembleScoringEngine.combine_predictions` under degenerate conditions:
   - All zeros, all ones, all NaNs, 99.9% NaNs, extreme outliers ($\pm 10^{9}$), small universes (1, 2, 3, 5, 8 symbols).
   - Verify monotonicity of top-decile spreads and strictly positive scaling without NaN or ZeroDivision.
2. Test `TransformerPredictor` and `LSTMPredictor`:
   - Single sample batch (batch_size=1), 2D vs 3D shapes, dimension mismatches, save/load cycle fidelity.
3. Test benchmark script imports:
   - Repeated imports of benchmark scripts to ensure zero side-effect corruption on `reports/quant_benchmark_comparison.md`.
4. Formulate verdict: **APPROVE** or **REJECT**.
5. Write your report to `d:\Finance\code\stock\.agents\teamwork_preview_challenger_1_gen2\handoff.md`.

## 2026-09-23T13:09:58Z
You are Challenger 1 (Adversarial Stress Testing & Numerical Edge Cases).
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_challenger_1_gen2
Read your dispatch instructions in: d:\Finance\code\stock\.agents\teamwork_preview_challenger_1_gen2\DISPATCH.md
Read the authoritative user request in:
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- d:\Finance\code\stock\ORIGINAL_REQUEST.md
Read the worker handoffs:
- d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_m2_core\handoff.md
- d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_reports\handoff.md

Tasks:
1. Empirically stress-test the modified code under degenerate and adversarial inputs:
   - All zeros, all ones, all NaNs, 99.9% NaNs, extreme outliers, small universes (1, 2, 3, 5, 8).
   - Single sample batch (batch_size=1), 2D vs 3D shapes, and save/load cycle fidelity.
   - Repeated imports of benchmark scripts to ensure zero side-effect corruption on canonical comparison report.
2. Formulate verdict: APPROVE or REJECT.
3. Write your report to `d:\Finance\code\stock\.agents\teamwork_preview_challenger_1_gen2\handoff.md`.
4. Send a message to orchestrator parent when complete.
