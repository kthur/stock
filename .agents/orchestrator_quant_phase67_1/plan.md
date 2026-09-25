# Plan — Phase 67 Quantitative Alpha Enhancement (v74 Production Master, Features F306~F310)

## Phase 0: Survey & Codebase Baseline Exploration
- Dispatch parallel Explorers to inspect Phase 66 implementation in:
  * `trading_system/src/ai/ensemble_scorer.py`
  * `trading_system/src/ai/factor_suppression.py`
  * `trading_system/src/risk/unified_portfolio_allocator.py` & `portfolio_allocator.py`
  * `trading_system/src/core/fast_lob_engine.py`
  * `trading_system/src/execution/smart_order_router.py` & `oms_engine.py`
  * `trading_system/scripts/benchmark_phase66_quant_performance.py` & Phase 66 test suite
- Collect findings on exact signatures, class names, alias patterns, gating flags, and report paths.

## Phase 1: Implementation of Core Milestones
- **M1 (Alpha Specialist)**:
  * `ensemble_scorer.py`: Borcherds-Moonshine Monster Whittaker coupler (κ: 19.90->20.60, λ: 0.999995->0.999998), partition actions 134th/136th, defect invariants 67th/68th, harmony boost 4.75, `FERI_v67`/`f_out_67`, `version >= 67` gating.
  * `factor_suppression.py`: Hyperbolic deadband (α: 336.0->344.0, δ=0.035), rank modulation 65th order, coeff 2.35, `REGIME_GAMMA_TOP_V67`, `get_regime_adaptive_gamma_top_v67`, full alias trees.
- **M2 (Risk Specialist)**:
  * `unified_portfolio_allocator.py` & `portfolio_allocator.py`: Higher-Homology-17 Fisher-Rao barycenter μ -> `[5.70, 3.85, 3.50, 6.40]`.
  * EVaR Cumulant: 66th-cumulant (66! ≈ 5.44e92), ξ_monster=0.99999999999998, regime shifts (`eps_w=0.670`, `delta_bl=-14.00`, `delta_herc=+10.00`, `delta_rp=-14.50`, `delta_cvar=+21.50+9.50*c`, `alpha_iep=3.85`, `contagion_damp=16.0`), alias trees & `is_phase67` gating.
- **M3 (Microstructure & OMS Specialist)**:
  * `fast_lob_engine.py`: KNK-46 DAHA (w = -48/3, k_daha = 0.38, k_monster = 0.37, daha_46_factor = 7.10, c_monster = 2^-48 = 2.9802322387695312e-15), full alias trees.
  * `smart_order_router.py`: Lit maker floor 1e-39, dark ATS cap, anti-gaming MinQty, 39-decimal precision, `is_phase67` flag.
  * `oms_engine.py`: Tick shading threshold `h > 0.0000004`, coeff 20 nines (`0.99999999999999999999`), `version >= 67` gating.

## Phase 2: Benchmarking, Testing & Verification
- **M4 (Benchmark & QA Specialist)**:
  * Create `trading_system/scripts/benchmark_phase67_quant_performance.py` (7 KPI assertions strictly exceeding Phase 66).
  * Generate and sync reports across all 6 specified locations (SHA-256 identical where required).
  * Update `reports/quant_benchmark_comparison.md`.
  * Create 5 test files:
    1. `tests/test_phase67_alpha.py`
    2. `tests/test_phase67_risk.py`
    3. `tests/test_phase67_oms.py`
    4. `tests/test_phase67_adversarial_challenger1.py`
    5. `tests/test_phase67_adversarial_oms_benchmark.py`
  * Run pytest on all Phase 67 tests and Phase 66 regression tests.
  * Run benchmark script.

## Phase 3: Review, Adversarial Stress Testing & Audit
- Dispatch Reviewers, Challengers, and Forensic Auditor.
- Verify zero integrity violations and all review gates pass.

## Phase 4: Documentation & Git
- Update `AGENTS.md` and `PROJECT.md` with Phase 67 entries.
- Git add, commit with message `feat: Phase 67 Quantitative Alpha Enhancement (v74 Production Master, Features F306~F310)`, and push to `origin main`.
- Synthesize results and report completion to parent/sentinel.
