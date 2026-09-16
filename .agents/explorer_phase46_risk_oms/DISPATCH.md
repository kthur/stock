# DISPATCH: Phase 46 Risk & OMS Technical Exploration (Explorer 2)

## Identity & Role
- Subagent Type: `teamwork_preview_explorer`
- Working Directory: `d:\Finance\code\stock\.agents\explorer_phase46_risk_oms`
- Mission: Deep technical survey of Risk Allocation & Microstructure OMS architecture for Phase 46

## Inputs & Authoritative Documents
- Original Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-16T08:29:02Z)
- Orchestrator Plan: `d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1\plan.md`
- Key Files to Investigate:
  - `trading_system/src/risk/unified_portfolio_allocator.py`
  - `trading_system/src/risk/portfolio_allocator.py`
  - `trading_system/src/core/fast_lob_engine.py`
  - `trading_system/src/execution/smart_order_router.py`
  - `trading_system/src/execution/oms_engine.py`
  - `tests/test_phase45_risk.py`, `tests/test_phase45_oms.py`

## Specific Investigation Tasks
1. Map Phase 45 F201.1:
   - `compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend` under weights $\mu_{\text{lkmw}} = [3.50, 2.70, 2.65, 4.05]$.
   - 41st-order cumulant expansion EVaR ($41! \approx 3.345 \times 10^{49}$, $\xi_{\text{km}}=0.9999998$) in `unified_portfolio_allocator.py` and `portfolio_allocator.py`.
   - Ambiguity tilting vector, R-vine cascade, exit barycenter refinement, version branching `version >= 45`.
2. Specify exact requirements for Phase 46 F205.1:
   - Lurie-Borcherds-Whittaker Motivic Fisher-Rao manifold barycenter blending with weights $\mu_{\text{lbw}} = [3.60, 2.75, 2.70, 4.15]$ for `["bl", "herc", "rp", "cvar"]`.
   - 42nd-order cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Beilinson-W-Algebra-Virasoro-Kac-Moody-Borcherds EVaR tail risk budgeting ($42! \approx 1.405 \times 10^{51}$, $\xi_{\text{borch}} = 0.9999999$).
   - Strict lower bound guarantee $EVaR_{42} \ge EVaR_{41}$, MDD $\le -0.00001\%$, Sharpe $\ge 30.95$ (target: 30.98).
3. Map Phase 45 F201.2:
   - KNK 24-Dark-Energy DAHA L3 hydrodynamics ($w = -26/3$, $k_{\text{daha}} = 0.16$, `daha_24_factor = 2.21`, radial metric power 27) in `fast_lob_engine.py`.
   - Lit maker floor $1 \times 10^{-17}$, darkpool routing 99.9999999998% ATS cap, Anti-Gaming MinQty 99.99999999995% in `smart_order_router.py`.
   - Preemptive tick shading factor $-0.99999999998 \cdot \text{spread} \cdot (h - 0.0002)$ in `oms_engine.py`.
4. Specify exact requirements for Phase 46 F205.2:
   - KNK 25-Dark-Energy PCQTGBDDDDHKMAEETUVWX ($w = -27/3 = -9.0$, $k_{\text{daha}} = 0.17$, `daha_25_factor = 2.38`) DAHA L3 orderbook hydrodynamic model in `fast_lob_engine.py`.
   - Lit maker floor $1 \times 10^{-18}$ ($0.000000000000000001$), darkpool routing 99.99999999995% ATS cap, Anti-Gaming MinQty 99.99999999998% in `smart_order_router.py`.
   - Preemptive tick shading factor $-0.99999999999 \cdot \text{spread} \cdot (h - 0.00015)$ in `oms_engine.py` reducing slippage to $\le 0.00000125\text{ bps}$ and friction to $\le 0.0000015\text{ bps}$.
5. Detail all classmethod/module aliases, delegation patterns, and float64 subnormal handling.

## Output Requirements
Write your detailed findings to `d:\Finance\code\stock\.agents\explorer_phase46_risk_oms\report.md` and a summary `handoff.md`. Send a completion message when done.
