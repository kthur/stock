# DISPATCH: Microstructure OMS Specialist Worker (Phase 54)

## Working Directory
d:\Finance\code\stock\.agents\worker_phase54_oms

## Mission
Implement Phase 54 Microstructure L3 Spacetime Hydrodynamics & Preemptive OMS (Features F244.1, F244.2).

## Exclusive Write Ownership
You EXCLUSIVELY own and may modify:
- `trading_system/src/core/fast_lob_engine.py` (or `src/core/fast_lob_engine.py`)
- `trading_system/src/execution/smart_order_router.py` (or `src/execution/smart_order_router.py`)
- `trading_system/src/execution/oms_engine.py` (or `src/execution/oms_engine.py`)
- `trading_system/src/execution/almgren_chriss.py` (or `src/execution/almgren_chriss.py`)
You MUST NOT modify any other files.

## Technical Requirements & Specifications
Follow the survey report at: `d:\Finance\code\stock\.agents\explorer_phase54_oms\handoff.md`

### 1. F244.1: Kerr-Newman-Kiselev 33-Dark-Energy DAHA L3 Spacetime Hydrodynamics
- In `fast_lob_engine.py`:
  - Implement function/method:
    `compute_kerr_newman_kiselev_33_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration`
    - Parameters: $w = -35.0/3.0 \approx -11.666666666666666$
    - $k_{\text{daha}} = 0.25, k_{\text{monster}} = 0.24, \text{daha\_33\_factor} = 3.98$
    - $c_{\text{monster}} = 0.0000000000244140625$ ($2^{-35}$)
    - Repulsive tidal acceleration: $- 17.5 \cdot c_{\text{monster}} \cdot (r_{\text{coord}}^{34}) \cdot \text{daha\_33\_factor}$
    - Horizon scale exponent: $(1.0 / 35.0)$
    - Warping terms: $m_{\text{mass}}^{36}$, $r_{\text{coord}}^{36}$, charge $r_{\text{coord}}^{33}$
  - Expose all 28 method aliases on `FastOrderBookMatchingEngine` and module level.
  - In `compute_preemptive_dark_routing`:
    - Version >= 54 resolves `cap = 0.9999999999999995`
    - Stack frame inspection for `"phase54"` sets `is_p54 = True` resolving `cap = 0.9999999999999995`.

### 2. F244.2: Lit Maker Floor Contraction & Preemptive Micro-Tick Shading
- In `smart_order_router.py`:
  - Version >= 54 sets `self.is_phase54 = True`
  - Max dark cap: `0.9999999999999995` (15 nines then 5)
  - Lit maker floor contracted down to $1 \times 10^{-26}$ (`0.00000000000000000000000001`) with 26-decimal precision rounding.
  - Formula factor: `0.99999999999999999999999986` (24 nines then 86)
  - Anti-gaming MinQty cap: `0.9999999999999995`
- In `oms_engine.py` (both `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`):
  - Preemptive micro-tick shading activating at $h > 0.000015$:
    $$\text{hawkes\_shift} = -\text{direction} \cdot 0.99999999999998 \cdot \text{spread} \cdot (h - 0.000015)$$

### 3. Verification & Testing
- Run test suite: `.venv\Scripts\pytest.exe tests/test_phase53_oms.py tests/test_phase53_adversarial_oms_benchmark.py` to ensure zero regression.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Output your handoff report to: `d:\Finance\code\stock\.agents\worker_phase54_oms\handoff.md`.

## 2026-09-18T02:04:53Z
You are the Microstructure OMS Specialist Worker for Phase 54 Quantitative Alpha Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase54_oms
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Read your dispatch instructions at: d:\Finance\code\stock\.agents\worker_phase54_oms\DISPATCH.md
Read the technical specification handoff at: d:\Finance\code\stock\.agents\explorer_phase54_oms\handoff.md

EXCLUSIVE WRITE OWNERSHIP:
You EXCLUSIVELY own and may modify:
- `trading_system/src/core/fast_lob_engine.py` (or `src/core/fast_lob_engine.py`)
- `trading_system/src/execution/smart_order_router.py` (or `src/execution/smart_order_router.py`)
- `trading_system/src/execution/oms_engine.py` (or `src/execution/oms_engine.py`)
- `trading_system/src/execution/almgren_chriss.py` (or `src/execution/almgren_chriss.py`)
You MUST NOT modify any other files.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement Features F244.1 and F244.2:
1. F244.1: Kerr-Newman-Kiselev 33-dark-energy DAHA L3 Spacetime Hydrodynamics in fast_lob_engine.py (w = -35/3, k_daha = 0.25, k_monster = 0.24, daha_33_factor = 3.98, c_monster = 0.0000000000244140625, repulsive acceleration -17.5 * c * r^34, 28 aliases, dark cap 0.9999999999999995, stack frame inspection for "phase54").
2. F244.2: Lit maker floor contracted down to 1e-26 with 26-decimal precision in smart_order_router.py, max dark cap 0.9999999999999995, anti-gaming MinQty 0.9999999999999995. Preemptive micro-tick shading in oms_engine.py and almgren_chriss.py activating at h > 0.000015:
   hawkes_shift = -direction * 0.99999999999998 * spread * (h - 0.000015)

Verify by running:
`.venv\Scripts\pytest.exe tests/test_phase53_oms.py tests/test_phase53_adversarial_oms_benchmark.py`
Document commands, code changes, and test results in `d:\Finance\code\stock\.agents\worker_phase54_oms\handoff.md`.
Send a completion message when finished.
