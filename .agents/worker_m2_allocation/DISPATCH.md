# DISPATCH: Worker M2 (Phase 8 Allocation & Execution Architecture)

## Working Directory
`d:\Finance\code\stock\.agents\worker_m2_allocation`

## Master Reference Files
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Section ## 2026-09-05T02:15:24Z)
- `d:\Finance\code\stock\.agents\explorer_m2_survey\handoff.md` (Exact technical blueprint, equations, and code blocks)
- `d:\Finance\code\stock\AGENTS.md`

## File Ownership (Exclusive)
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/oms_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `tests/test_phase8_portfolio_execution.py`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tasks & Specifications
1. **Feature F53 (Multivariate R-Vine Copula & Information Entropy Parity)** in `unified_portfolio_allocator.py`:
   - Implement `compute_rvine_tail_cascade_metrics(self, returns: np.ndarray, tail_quantile: float = 0.05) -> Dict[str, Any]` modeling 3-tier tree copulas ($T_1, T_2, T_3$) via Clayton $h$-functions.
   - In `compute_information_theoretic_blend_weights`: Add `version >= 8` branch with Information Entropy Parity (IEP) shifting weights toward equal weighting ($0.25$) modulated by cascade contagion, and R-Vine cascade tilting ($\text{bl}: -0.90$, $\text{herc}: +0.30 - 0.40 \lambda_{T2}$, $\text{rp}: -1.25$, $\text{cvar}: +1.65$).
   - In `optimize_multi_model_blend`: Add automated R-Vine cascade metrics calculation when `version >= 8`.
   - Implement R-Vine safety-weighted residual risk headroom redistribution in Euler CCVaR budget enforcement.
2. **Feature F54.1 (Level-3 Queue Imbalance Acceleration $d^2\text{QI}/dt^2$)** in `fast_lob_engine.py`:
   - In `FastOrderBookMatchingEngine`: Maintain `_qi_history = deque(maxlen=20)` with timestamps and calculate 1st derivative velocity $v_{QI}$ and 2nd derivative acceleration $a_{QI} = d^2\text{QI}/dt^2$.
   - Calculate predictive accelerated micro-price: $QI_{\text{pred}} = \text{clip}(QI_{L3}^* + \tau_{\text{lead}} v_{QI} + 0.5 \tau_{\text{lead}}^2 a_{QI}, -1.0, 1.0)$ with $\tau_{\text{lead}} = 0.10$.
3. **Feature F54.2 (Cross-Asset Toxicity & Accelerated Peg Shading)** in `oms_engine.py`:
   - In `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`:
   - Add parameters `qi_acceleration: Optional[float] = None, cross_asset_toxicity: Optional[float] = None, version: int = 7`.
   - Compute composite toxicity $\gamma_{\text{composite}} = 0.65 \gamma_{\text{loc}} + 0.35 \gamma_{\text{cross}}$.
   - Apply accelerated peg shift $a_{\text{shift}} = \text{direction} \cdot 0.20 \cdot \text{spr} \cdot \tanh(0.80 a_{QI}) \cdot \max(0, 1 - 0.90 \gamma_{\text{composite}})$.
   - Maintain 100% bit-level parity between `ExecutionOMSEngine` and `AlmgrenChrissScheduler`.
4. **Feature F54.3 (SmartOrderRouter ATS Preemption & Contraction)** in `smart_order_router.py`:
   - Add parameters `qi_acceleration: Optional[float] = None, cross_asset_toxicity: Optional[float] = None`.
   - Expand lit preemption to dark ATS up to 85% when $QI > 0.40$ or $a_{QI} > 0.20$.
   - Contract maker ratio floor to 0.05 under extreme toxicity $\gamma_{\text{toxic}} > 0.80$.
   - Expand anti-gaming MinQty cap to 0.75 (75%).
5. **Unit Tests Creation & Verification**:
   - Create `tests/test_phase8_portfolio_execution.py` implementing all 10 test cases detailed in `explorer_m2_survey/handoff.md`.
   - Run tests using `.venv\Scripts\python.exe -m pytest tests/test_phase8_portfolio_execution.py tests/test_phase7_portfolio_execution.py -v`.
   - Ensure 100% tests pass with 0 regressions.
6. Write completion report to `d:\Finance\code\stock\.agents\worker_m2_allocation\handoff.md`.

## 2026-09-05T02:22:07Z
You are Worker M2 (Phase 8 Allocation & Execution Architecture).
Your working directory is: d:\Finance\code\stock\.agents\worker_m2_allocation

MANDATORY FIRST STEP: Read ORIGINAL_REQUEST.md at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Also read your dispatch instructions at:
d:\Finance\code\stock\.agents\worker_m2_allocation\DISPATCH.md
And read the detailed technical survey report at:
d:\Finance\code\stock\.agents\explorer_m2_survey\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership (Exclusive):
- trading_system/src/risk/unified_portfolio_allocator.py
- trading_system/src/core/fast_lob_engine.py
- trading_system/src/execution/oms_engine.py
- trading_system/src/execution/smart_order_router.py
- tests/test_phase8_portfolio_execution.py

Execute the tasks in DISPATCH.md:
1. Implement F53 (Multivariate R-Vine Copula & Information Entropy Parity) in `unified_portfolio_allocator.py`.
2. Implement F54.1 (Level-3 Queue Imbalance Acceleration) in `fast_lob_engine.py`.
3. Implement F54.2 (Cross-Asset Toxicity & Accelerated Peg Shading) in `oms_engine.py` maintaining 100% bit-level parity between `ExecutionOMSEngine` and `AlmgrenChrissScheduler`.
4. Implement F54.3 (SmartOrderRouter ATS Preemption & Contraction) in `smart_order_router.py`.
5. Create comprehensive unit tests in `tests/test_phase8_portfolio_execution.py`.
6. Run tests via `.venv\Scripts\python.exe -m pytest tests/test_phase8_portfolio_execution.py tests/test_phase7_portfolio_execution.py -v`.
7. Write your handoff report to `d:\Finance\code\stock\.agents\worker_m2_allocation\handoff.md`.
8. Send a message to the orchestrator with your completion summary and handoff path.

