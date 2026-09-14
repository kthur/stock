# DISPATCH: Challenger 2 (Adversarial Stress Testing: OMS & Benchmark - Phase 41)

## Target Scope
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
- `trading_system/scripts/benchmark_phase41_quant_performance.py`
- Authoritative Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (header `## 2026-09-14T10:14:28Z`)

## Adversarial Stress Testing Objectives
1. **LOB Hydrodynamics Stress Testing (F185.2)**:
   - Test `compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_trigonometric_queue_acceleration` under empty orderbook, extreme spread, crossed book, and massive order volume.
   - Test DeepHawkes arrival process with infinite arrival rates, testing dark routing cap 0.99999999995.
2. **SmartOrderRouter & OMS Stress Testing**:
   - Stress test maker floor contraction with order size $10^{15}$ and $\gamma_{\text{toxic}} = 1.0$, asserting maker allocation is exactly contracted to $1 \times 10^{-13}$.
   - Stress test dynamic anti-gaming MinQty with extreme order flow toxicity.
   - Stress test dual-engine preemptive tick shading with extreme Hawkes toxicity $h = 50.0$ and wide spread $spr = 100.0$, verifying identical outputs from both engines.
3. **Benchmark Script Adversarial Check**:
   - Verify that baseline values match Phase 40 exactly, target values meet all 6 criteria, and script runs with exit code 0.
4. Record explicit verdict (`APPROVE` or `REJECT`) in `d:\Finance\code\stock\.agents\challenger_phase41_2\handoff.md`.

## 2026-09-14T10:41:07Z
You are Challenger 2 for Phase 41 Quant Enhancement (Adversarial Stress Testing: OMS & Benchmark).
Your working directory is d:\Finance\code\stock\.agents\challenger_phase41_2.
You MUST read:
1. d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (header ## 2026-09-14T10:14:28Z)
2. d:\Finance\code\stock\.agents\challenger_phase41_2\DISPATCH.md
3. Source code in:
   - trading_system/src/core/fast_lob_engine.py
   - trading_system/src/execution/smart_order_router.py
   - trading_system/src/execution/oms_engine.py
   - trading_system/scripts/benchmark_phase41_quant_performance.py

Perform adversarial stress testing on Microstructure OMS (F185.2) and Benchmark (F186):
- Extreme orderbook conditions, toxic Hawkes spikes, large order quantities, maker floor $10^{-13}$ adherence, benchmark numerical bounds.
Write your stress testing harness/script, execute it with .venv\Scripts\python.exe, and report your empirical findings and explicit verdict (APPROVE or REJECT) in d:\Finance\code\stock\.agents\challenger_phase41_2\handoff.md.
Send a message back when done.
