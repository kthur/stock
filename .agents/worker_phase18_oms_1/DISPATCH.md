## 2026-09-06T08:24:14Z

You are Worker R3 (Microstructure OMS Specialist) for Phase 18 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase18_oms_1
You MUST read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md before starting work.
Also review the handoff reports from:
- d:\Finance\code\stock\.agents\explorer_phase18_arch_1\handoff.md
- d:\Finance\code\stock\.agents\spec_miner_phase18_1\handoff.md
Project guidelines: d:\Finance\code\stock\AGENTS.md

WRITE OWNERSHIP:
You exclusively own:
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- `tests/test_phase18_microstructure_oms.py`
DO NOT edit files outside this scope!

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

YOUR TASKS:
1. Feature F93.2.1: In `fast_lob_engine.py`, implement `compute_kerr_newman_queue_acceleration`:
   - Incorporate net order flow charge $Q$, spin $a$, horizon/ergosphere $r_E(\theta)$, frame-dragging angular velocity $\omega_{\text{drag}}$, and tidal force $F_{\text{tidal}}$ into queue acceleration and micro-price calculation.
   - Update `get_optimal_preemptive_dark_allocation` caller detection for `"phase18"` setting cap to $0.999$.
2. Feature F93.2.2: In `smart_order_router.py`, implement Phase 18 routing logic (`is_phase18 = (v_eff >= 18)`):
   - Preemptive dark ATS routing cap elevated to $99.9\%$ (`0.999`).
   - Lit maker floor contracted to `0.00005` ($0.005\%$) via $0.70 \cdot (1.0 - 0.9999286 \cdot \gamma_{\text{toxic}})$.
   - Dynamic anti-gaming MinQty scaled to $99.95\%$ (`0.9995`).
3. Feature F93.2.3: In `oms_engine.py` (`ExecutionOMSEngine` and `AlmgrenChrissScheduler`), implement preemptive micro-tick shading:
   - When Hawkes intensity $h > 0.10$ for `version >= 18`:
     $\text{hawkes_shift} = -\text{direction} \cdot 0.99 \cdot \text{spread} \cdot (h - 0.10)$.
4. Create comprehensive unit tests in `tests/test_phase18_microstructure_oms.py` verifying Kerr-Newman queue physics, dark routing limits, maker floor, anti-gaming MinQty, and micro-tick shading.
5. Run tests via `.venv\Scripts\pytest.exe -p no:cov tests/test_phase18_microstructure_oms.py -v` (and existing OMS tests). Ensure all pass!
6. Write a complete handoff report to `d:\Finance\code\stock\.agents\worker_phase18_oms_1\handoff.md` and send a completion message to parent.
