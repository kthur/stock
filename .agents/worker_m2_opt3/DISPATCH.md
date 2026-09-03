## 2026-09-04T07:05:04Z

You are Worker M2 for Milestone 2 (Portfolio 4-Model Dynamic Blending & Darkpool/HFT OMS Optimization) of the 3rd Deep Quantitative Enhancement.
Working directory: d:\Finance\code\stock\.agents\worker_m2_opt3

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY INPUTS (Read these files thoroughly before modifying code):
- ORIGINAL_REQUEST.md: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- PROJECT.md: d:\Finance\code\stock\.agents\orchestrator_quant_opt3\PROJECT.md
- Survey Explorer 2 Blueprint (Requirement R2): d:\Finance\code\stock\.agents\explorer_survey_2_opt3\handoff.md

EXCLUSIVE WRITE OWNERSHIP (You own only these files):
- trading_system/src/risk/unified_portfolio_allocator.py
- trading_system/src/risk/portfolio_allocator.py
- trading_system/src/execution/oms_engine.py
- trading_system/src/execution/smart_order_router.py
- tests/test_m2_quant_enhancements.py

TASKS TO EXECUTE (Features F09 - F14):
1. F09: Continuous 4-Model Markov Blending in `UnifiedPortfolioAllocator` (`unified_portfolio_allocator.py`):
   - Update `optimize_multi_model_blend` to support `regime` being a dictionary of posterior probabilities $\boldsymbol{\pi}_t = \{\text{regime}: p\}$ as well as strings/ints.
   - Compute blended confidence weights: $\mathbf{c}(t) = \sum_m \pi_{t, m} \mathbf{c}^{(m)}$ where $\mathbf{c}^{(m)}$ is the vector $[w_{\text{bl}}, w_{\text{herc}}, w_{\text{rp}}, w_{\text{cvar}}]^T$ from `REGIME_OPTIMIZER_BLENDS`.
   - Ensure normalized sum $= 1.0000$. Ensure backward compatibility with string regimes.
   - Dynamically tilt towards EVT-CVaR and Risk Parity in high volatility / crisis regimes.
2. F10: Clayton Copula Tail Covariance Integration in `PortfolioAllocator` & `UnifiedPortfolioAllocator`:
   - In `portfolio_allocator.py`: ensure `compute_tail_stress_cov` dynamically estimates lower tail dependence $\lambda_L = 2^{-1/\theta} \in [0.10, 0.70]$ and returns blended stress covariance $\boldsymbol{\Sigma}_{\text{tail}} = (1-\lambda_L)\boldsymbol{\Sigma}_{\text{shrink}} + \lambda_L \boldsymbol{\Sigma}_{\text{clayton}}$.
   - In `unified_portfolio_allocator.py`: update `calculate_cvar_weights` to use the tail-stressed covariance when available or compute parametric EVT-CVaR returns distribution, preventing extreme sample underestimation with short lookback windows.
3. F11: Dark-Pool Adjusted Gatheral 3/2-Power Market Impact in `UnifiedPortfolioAllocator`:
   - In `unified_portfolio_allocator.py` (lines 460-498), adapt impact parameter $\kappa_{\text{eff}} = \kappa_0 \cdot (1.0 - \phi_{\text{dark}})$, where $\phi_{\text{dark}} = \min(0.60, 1.2 \cdot \text{darkpool\_score})$ is the off-exchange / ATS liquidity fraction.
   - Closed-form optimal convergence velocity $\theta_{\text{impact}}^*$ incorporates $\kappa_{\text{eff}}$, allowing larger tranche sizing when dark pool liquidity is available without increasing market impact.
4. F12: Dynamic Dark Probing & 3-Tier Multi-Leg SOR Routing in `SmartOrderRouter` & `ExecutionOMSEngine`:
   - In `smart_order_router.py`: enhance `route_order` to dynamically scale dark pool allocation based on `darkpool_score` (from 40% up to 70% when institutional block accumulation is detected), with remaining quantity allocated 70% to primary peg maker and residual to lit sweeper.
   - In `oms_engine.py`: in `generate_order_plan()`, invoke `SmartOrderRouter.route_order()` for each tranche or order to attach multi-venue routing legs (`sor_routing`) and calculate expected cost savings in basis points (`expected_cost_saving_bps`).
5. F13: Orderbook Imbalance (OBI) Midpoint Peg Pricing in `ExecutionOMSEngine` (`oms_engine.py`):
   - In `generate_order_plan` / peg pricing, calculate adjusted midpoint limit price:
     $P_{\text{peg}} = P_{\text{mid}} + \frac{1}{2} \cdot \text{spread} \cdot \tanh(\kappa \cdot \text{OBI})$
     where $\text{OBI} \in [-1.0, 1.0]$. Positive OBI shifts peg towards ask for buy orders to ensure fill; negative OBI shifts peg towards bid to capture spread.
6. F14: Comprehensive Unit and Integration Tests:
   - Create `tests/test_m2_quant_enhancements.py` testing all features (F09, F10, F11, F12, F13).
   - Verify 100% test pass rate on new tests and existing portfolio/OMS suites:
     `.venv\Scripts\pytest.exe tests/test_m2_quant_enhancements.py -v`
     `.venv\Scripts\pytest.exe tests/test_unified_portfolio_allocator.py tests/test_portfolio_allocator.py tests/test_oms_engine.py tests/test_smart_order_router.py -v`
7. Report:
   - Write comprehensive report to `d:\Finance\code\stock\.agents\worker_m2_opt3\handoff.md`.
