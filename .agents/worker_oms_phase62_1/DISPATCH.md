## 2026-09-20T05:34:29Z

You are Worker C (Phase 62 Microstructure OMS Specialist) implementing the Microstructure L3 Spacetime Hydrodynamics & Preemptive OMS enhancements (Features F284.1, F284.2).

Your working directory is: d:\Finance\code\stock\.agents\worker_oms_phase62_1
You EXCLUSIVELY OWN and modify:
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- `src/execution/almgren_chriss.py`
(Do NOT touch any other files!)

You MUST read:
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (under ## 2026-09-20T05:25:51Z)
- d:\Finance\code\stock\.agents\orchestrator_quant_phase62_1\DISPATCH.md
- d:\Finance\code\stock\.agents\explorer_risk_oms_phase62_1\handoff.md (Complete architectural blueprint and exact formulas)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. In `src/core/fast_lob_engine.py`:
   - Implement `compute_kerr_newman_kiselev_41_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration` on `FastOrderBookMatchingEngine`:
     * $w = -43/3 \approx -14.333333, k_{\text{daha}} = 0.33, k_{\text{monster}} = 0.32, \text{daha\_41\_factor} = 5.85, c_{\text{monster}} = 9.5367431640625 \times 10^{-14}$.
     * Repulsive acceleration: $-21.5 \cdot c_{\text{monster}} \cdot r^{42} \cdot \text{daha\_41}$.
     * Metric warping: $+ c_{\text{monster}} \cdot r^{44} \cdot \text{daha\_41}$, and $r_{\text{41\_outer}}$ scale with exponent $1/43.0$.
     * Export 28 method aliases on `FastOrderBookMatchingEngine` and `FastLOBEngine`.
   - In `DeepHawkesArrivalProcess.compute_preemptive_dark_routing`:
     * Add `v_int >= 62` and `self.version >= 62`: `cap = 0.9999999999999999995` (19 decimals).
     * Add stack frame caller check `if "phase62" in cname: cap = 0.9999999999999999995`.
2. In `src/execution/smart_order_router.py`:
   - In `_resolve_max_dark_cap`: return `0.9999999999999999995` for $v_{\text{eff}} \ge 62$.
   - Under queue imbalance for Phase 62 (`qi_aligned > 0.00000000005` or `a_aligned > 0.000000000005`), scale `eff_dark_ratio` up to cap `0.9999999999999999995` with increments `+ 0.9995 * qi + 0.8995 * tanh(a)`.
   - Contract lit maker ratio floor down to $1 \times 10^{-34}$ with 34-decimal precision:
     `maker_ratio = float(np.clip(round(0.70 * (1.0 - 0.999999999999999999999999999999986 * gamma_toxic), 46), 1e-34, 0.70))`.
   - Dynamic anti-gaming MinQty: under $\gamma_{\text{toxic}} > 0.0000000000001$ or `is_accum`, scale up to `0.9999999999999999995`.
   - In output dictionary, round `maker_ratio` and `min_ratio` to 34 decimals for $v_{\text{eff}} \ge 62$.
3. In `src/execution/oms_engine.py` (and re-exported in `src/execution/almgren_chriss.py`):
   - In `calculate_peg_limit_price`: for `int(version) >= 62`, implement preemptive micro-tick shading activating strictly at $h > 0.0000015$:
     $$\text{hawkes\_shift} = -\text{direction} \cdot 0.99999999999999995 \cdot \text{spread} \cdot (h - 0.0000015)$$
     (and $0.0$ if $h \le 0.0000015$).
   - Implement identically in both `ExecutionOMSEngine` and `AlmgrenChrissScheduler`.
4. Verify backward compatibility by running:
   `python -m pytest tests/test_phase61_oms.py -v`
   Ensure all tests pass 100%.
5. Document all changes, files modified, and verification results in `d:\Finance\code\stock\.agents\worker_oms_phase62_1\handoff.md`.
6. Report completion to orchestrator via `send_message`.
