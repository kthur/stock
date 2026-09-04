## 2026-09-04T09:40:42Z
You are Worker M2 for Phase 5 Deep Quantitative Enhancements (Milestone 2).
Your working directory is: `d:\Finance\code\stock\.agents\worker_m2`

MANDATORY FIRST STEP:
Read the following authoritative files:
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically header `## 2026-09-04T08:36:42Z`)
2. `d:\Finance\code\stock\PROJECT.md`
3. `d:\Finance\code\stock\.agents\orchestrator_quant_opt5\SCOPE.md`
4. `d:\Finance\code\stock\.agents\explorer_survey_2\analysis.md` and `handoff.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write Ownership (Exclusive):
You exclusively own and may modify or create:
- `src/risk/unified_portfolio_allocator.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- `tests/test_phase5_portfolio_execution.py`

Mission:
Implement Milestone 2: Requirement R2 (Features F37 and F38):
1. Feature F37: 4-Model Portfolio Allocation & Capital Efficiency 5th Deepening in `src/risk/unified_portfolio_allocator.py`:
   - Higher-order systematic co-skewness ($s_i^{\text{coskew}} = \frac{E[\tilde{r}_i \tilde{r}_m^2]}{\sigma_i \sigma_m^2}$) and co-kurtosis ($k_i^{\text{cokurt}} = \frac{E[\tilde{r}_i \tilde{r}_m^3]}{\sigma_i \sigma_m^3}$) alpha conviction tilt $\mu_i^{\text{adj}} = \mu_i \cdot (1 + \lambda_{\text{skew}} s_i^{\text{coskew}} - \lambda_{\text{kurt}} (k_i^{\text{cokurt}} - 3))$, where $\lambda_{\text{skew}} = 0.15, \lambda_{\text{kurt}} = 0.05$.
   - Dynamic Cornish-Fisher EVT-CVaR tail expansion $k_\alpha(w) \in [2.05, 3.20]$ adapting to portfolio skewness and kurtosis in `calculate_cvar_weights`.
   - Dynamic Risk Parity Diversification Ratio (DRP-DR) scaling $\delta_{\text{DR}} = \text{clip}(1.0 + 0.40 \frac{DR - 1.30}{0.50}, 0.60, 1.40)$ where $DR = \frac{w^T \sigma}{\sqrt{w^T \Sigma w}}$, scaling HERC and Risk Parity weights in `optimize_multi_model_blend`.
   - Entropy-Weighted Adaptive Target Volatility Scaling under Shannon regime uncertainty $U_{\text{regime}} = H(\pi)/\ln(6)$ scaling target volatility by $(1 - 0.25 U_{\text{regime}})$ and allocation cap by $(1 - 0.20 U_{\text{regime}})$ in `apply_target_volatility_scaling`.
   - Hill/Pickands GPD dynamic tail index ($\hat{\xi} \in [0.05, 0.45]$) in parametric CVaR risk budgeting.

2. Feature F38: Execution Slippage & Friction Cost Minimization 5th Deepening in `src/execution/smart_order_router.py` and `src/execution/oms_engine.py`:
   - Continuous Hawkes toxicity modulation ($\Gamma_{\text{toxic}} = \text{clip}(\frac{\lambda - \bar{\lambda}}{2.5 \bar{\lambda} - \bar{\lambda}}, 0, 1)$) with smooth maker ratio decay: $\text{maker\_ratio} = \text{clip}(0.70 [1 - 0.571 \Gamma_{\text{toxic}}], 0.30, 0.70)$ in `smart_order_router.py`.
   - Darkpool Midpoint Resting with Minimum Quantity (MinQty $\ge 20\%$) and queue-priority fill probability estimation.
   - Volatility- and depth-adaptive L2 OBI micro-price dynamic curvature $\kappa_{\text{eff}} = \text{clip}(1.5 \frac{\sigma}{0.02} / \sqrt{R_{\text{depth}}}, 0.8, 3.0)$ in `oms_engine.py` (`calculate_peg_limit_price`).
   - ADV-adaptive Gatheral slice count $n_{\text{slices}}^* = \text{clip}(\text{round}(3 + 8 \sqrt{\rho_{\text{adv}} / 0.01}), 2, 20)$ with intraday U-shaped volume smile weighting $V_{\text{smile}}(t) = 1.0 + 0.6(2t-1)^2$ in `AlmgrenChrissScheduler`.
   - Granular 5-market spread- and tax-aware Leland dynamic buffer bands in `apply_leland_no_trade_buffers`: KOSDAQ 35.0, KOSPI 25.0, RUSSELL2000 16.0, NASDAQ 7.0, SP500 5.0 bps.

3. Testing & Verification:
   - Create `tests/test_phase5_portfolio_execution.py` covering all F37 and F38 features (co-skewness/kurtosis conviction tilt, Cornish-Fisher expansion, DRP-DR scaling, entropy volatility scaling, continuous Hawkes toxicity decay, MinQty darkpool resting, adaptive OBI curvature, ADV slice smile, and 5-market Leland buffer bands).
   - Run tests: `.venv\Scripts\python.exe -m pytest tests/test_phase5_portfolio_execution.py tests/test_phase4_portfolio_execution.py -v`.
   - Run tests: `.venv\Scripts\python.exe -m pytest tests/test_unified_portfolio_engine.py -v`.
   - Ensure all tests pass with 100% exit code 0.
