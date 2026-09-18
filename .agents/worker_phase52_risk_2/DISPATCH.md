## 2026-09-17T22:21:19Z

You are a Worker subagent (Risk Allocation Specialist / Risk Engineer).
Your working directory is: d:\Finance\code\stock\.agents\worker_phase52_risk_2
Your parent is orchestrator_quant_phase52_1 (conversation ID: 46733a4d-78af-48ef-a7e9-0d1f432c1874).

MANDATORY: You MUST read the authoritative user request at:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-17T18:14:52Z)
and your dispatch context at:
`d:\Finance\code\stock\.agents\orchestrator_quant_phase52_1\DISPATCH.md`
before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You EXCLUSIVELY own:
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `tests/test_phase52_risk.py`
Do NOT edit any other production files.

Read your technical blueprint and findings:
- `d:\Finance\code\stock\.agents\explorer_phase52_risk\analysis.md`
- `d:\Finance\code\stock\.agents\explorer_phase52_risk\handoff.md`

Your tasks:
1. Implement Requirement R2 (Features F233.1, F233.2) in `trading_system/src/risk/unified_portfolio_allocator.py` and `trading_system/src/risk/portfolio_allocator.py`:
   - Feature F233.1: Implement Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology Fisher-Rao Barycenter Blending on Riemannian probability simplex:
     * Metric curvature mu_lmbwdh2 = [4.20, 3.10, 3.05, 4.75] across {1: BL, 2: HERC, 3: RP, 4: CVaR}
     * Simplex conservation (sum q_i = 1.0) and ordering CVaR > BL > HERC > RP
     * Export all 18 higher-homology method aliases on `UnifiedPortfolioAllocator` and delegate via `@staticmethod` on `PortfolioAllocator`.
   - Ambiguity Tilting in `calculate_weights` and `compute_information_theoretic_blend_weights` under `version >= 52`:
     * is_phase52 = int(version) >= 52, default eps_w = 0.520, alpha_iep = 3.10
     * Regime shifts: delta_bl = -9.75 * eps_w - 5.30 * u_entropy^2, delta_herc = +6.00 * eps_w + 4.20 * u_entropy, delta_rp = -10.25 * eps_w, delta_cvar = +14.50 * eps_w + 6.00 * c_crisis
     * Scale delta_l[k] *= (1.0 + 0.21 * alpha_iep) and post-softmax dispatch to higher-homology barycenter.
   - Feature F233.2: Implement 48th-cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure:
     * 48! ~ 1.2413915592536073e61, xi_monster = 0.999999999
     * Bounding catastrophic downside risk under Student-t and heavy-tailed shocks
     * Export 18 EVaR aliases and delegate on `PortfolioAllocator`.
   - Maintain 100% backward compatibility for Phase 1~51 gated by `version >= 52`.
2. Implement comprehensive unit test suite in `tests/test_phase52_risk.py` following Section 5 of `explorer_phase52_risk/analysis.md`.
3. Execute the tests using `.venv\Scripts\python.exe -m pytest tests/test_phase52_risk.py -v`.
4. Execute the regression tests: `.venv\Scripts\python.exe -m pytest tests/test_phase51_risk.py tests/test_phase50_risk.py -v`.
5. Document all code changes, test commands, and exact outputs in `d:\Finance\code\stock\.agents\worker_phase52_risk_2\handoff.md` and report back.
