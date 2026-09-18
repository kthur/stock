# DISPATCH: Survey Explorer 2 — Risk Allocation & Microstructure OMS

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2

## Role & Mission
You are Survey Explorer 2. Your mission is to explore and analyze the authoritative codebase for Phase 55 Risk Allocation (F248.1, F248.2) and Microstructure OMS (F249.1, F249.2).

## Authoritative Files to Read
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-18T03:36:46Z`)
2. `d:\Finance\code\stock\.agents\orchestrator_quant_phase55_1\DISPATCH.md`
3. `src/risk/unified_portfolio_allocator.py` & `src/risk/portfolio_allocator.py`: Inspect Phase 54 Higher-Homology-4 Fisher-Rao Barycenter ($\mu=[4.40, 3.20, 3.15, 4.95]$), 18 method aliases, 50th-cumulant EVaR ($50! \approx 3.04 \times 10^{64}$), ambiguity tilting under `version >= 54` ($\epsilon_w=0.540, \alpha_{\text{iep}}=3.20$, shifts, contagion damping).
4. `src/core/fast_lob_engine.py`: Inspect Phase 54 KNK 33-dark-energy DAHA L3, 28 aliases, stack frame inspection for `"phase54"`.
5. `src/execution/smart_order_router.py`: Inspect Phase 54 lit maker floor ($1 \times 10^{-26}$), dark ATS cap ($99.99999999999995\%$), anti-gaming MinQty ($99.99999999999995\%$).
6. `src/execution/oms_engine.py` & `src/execution/almgren_chriss.py`: Inspect Phase 54 micro-tick shading activating at $h > 0.000015$.
7. `tests/test_phase54_risk.py` & `tests/test_phase54_oms.py`: Inspect test suites and structure.

## Deliverables
Write a comprehensive report to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\survey_report.md` detailing:
1. Exact locations, line numbers, function names, and existing aliases in `unified_portfolio_allocator.py`, `portfolio_allocator.py`, `fast_lob_engine.py`, `smart_order_router.py`, `oms_engine.py`, and `almgren_chriss.py`.
2. Exact mathematical formulas and parameters required for Phase 55:
   - Higher-Homology-5 Fisher-Rao Barycenter: $\mu_{\text{lmbwdh5}} = [4.50, 3.25, 3.20, 5.05]$, simplex conservation $\sum q_i = 1.0$, 19 delegated method aliases.
   - 51st-cumulant expansion EVaR Tail Risk Measure: $51! \approx 1.55112 \times 10^{66}$, $\xi_{\text{monster}} = 0.9999999999$.
   - Ambiguity tilting in `calculate_weights` under `version >= 55`: $\epsilon_w=0.550, \alpha_{\text{iep}}=3.25$, shifts $(\delta_{\text{bl}} = -10.50, \delta_{\text{herc}} = +6.75, \delta_{\text{rp}} = -11.00, \delta_{\text{cvar}} = +15.70)$, contagion damping $\max(0.0, 1.0 - 10.0 \cdot \lambda_{\text{casc}})$.
   - KNK 34-dark-energy DAHA L3: $w=-12.0, k_{\text{daha}}=0.26, k_{\text{monster}}=0.25, \text{daha\_34\_factor}=4.20, c_{\text{monster}}=0.00000000001220703125$, repulsive acceleration $-18.0 \cdot c_{\text{monster}} \cdot r^{35}$, 28 aliases, stack frame inspection for `"phase55"`.
   - Primary exchange lit maker floor: $1 \times 10^{-27}$ (27 decimals).
   - Preemptive dark ATS routing allocation cap: $99.99999999999998\%$, anti-gaming MinQty: $99.99999999999998\%$.
   - Preemptive micro-tick shading in `oms_engine.py` (both `ExecutionOMSEngine` and `AlmgrenChrissScheduler`) at $h > 0.00001$: $\text{hawkes\_shift} = -\text{direction} \cdot 0.99999999999999 \cdot \text{spread} \cdot (h - 0.00001)$.
3. Required unit test specifications for `tests/test_phase55_risk.py` and `tests/test_phase55_oms.py`.
4. Write `handoff.md` and send completion message back to orchestrator.


## 2026-09-18T03:36:46Z

You are Survey Explorer 2. Your working directory is d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2.
Read your dispatch instructions in d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\DISPATCH.md and the original user request in d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (under header ## 2026-09-18T03:36:46Z).
Explore and analyze the codebase for Phase 55 Risk Allocation (F248.1, F248.2 in unified_portfolio_allocator.py and portfolio_allocator.py) and Microstructure OMS (F249.1, F249.2 in fast_lob_engine.py, smart_order_router.py, oms_engine.py, almgren_chriss.py), comparing with Phase 54 and tests/test_phase54_risk.py, test_phase54_oms.py.
Maintain progress.md with regular liveness timestamps.
Write your full findings to survey_report.md and a self-contained handoff.md in your working directory.
When complete, notify your caller with send_message.