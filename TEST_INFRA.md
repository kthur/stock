# E2E Test Infra: Release R185 (Phase 195 Institutional Master)

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + BVA + Pairwise + Workload Testing.
- Strict causal verification, zero synthetic rows, dual-tree cryptographic parity, capital preservation ($W_{\text{net}} \le W_{\text{gross}}$), and dashboard file-size containment.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | F959 Symplectic Hamiltonian Phase-Space Flow | ORIGINAL_REQUEST & PROJECT.md | 5 | 5 | ✓ |
| 2 | F960 Higher-Order Simplicial Sheaf Laplacian | ORIGINAL_REQUEST & PROJECT.md | 5 | 5 | ✓ |
| 3 | F961 Non-Equilibrium Statistical Mechanics | ORIGINAL_REQUEST & PROJECT.md | 5 | 5 | ✓ |
| 4 | F962 Sedecuple (16-Pillar) ZCA & Phase 195 Coupler | ORIGINAL_REQUEST & PROJECT.md | 5 | 5 | ✓ |
| 5 | F963 Cross-Border Resonant Dynamic Leverage | ORIGINAL_REQUEST & PROJECT.md | 5 | 5 | ✓ |
| 6 | F964 30-Year Benchmark Elevation (Net CAGR >= 94.00%) | ORIGINAL_REQUEST & PROJECT.md | 5 | 5 | ✓ |
| 7 | F965 Tri-Directory Invariant (`synthetic_rows == 0` int) | ORIGINAL_REQUEST & PROJECT.md | 5 | 5 | ✓ |
| 8 | F966 Dashboard HTML File-Size (< 1 MB) | ORIGINAL_REQUEST & PROJECT.md | 5 | 5 | ✓ |
| 9 | F967 Dual-Tree SHA-256 Bit-for-Bit Parity (372+ files) | ORIGINAL_REQUEST & PROJECT.md | 5 | 5 | ✓ |
| 10 | F968 Master Production Certification (39/39 Backtest) | ORIGINAL_REQUEST & PROJECT.md | 5 | 5 | ✓ |

## Test Architecture
- Test runner: `pytest -q tests/test_e2e_release_r185.py`
- Test case format: Pytest unit & integration test classes (`TestTier1FeatureCoverage`, `TestTier2BoundaryCornerCases`, `TestTier3CrossFeatureInteractions`, `TestTier4RealWorldScenarios`)
- Directory layout:
  - `tests/test_e2e_release_r185.py` (Main E2E test file)
  - `TEST_READY.md` (Signal artifact upon full test suite completion)

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full 30-Year Compounding Backtest Simulation (1996–2026, 8000 days) | F963, F964, F965 | High |
| 2 | Historical Crisis Stress Defense (1997, 2000, 2008, 2020, 2022) | F962, F963, F964 | High |
| 3 | East Asian Cross-Border Value-Chain Shock Propagation | F959, F960, F961, F962 | High |
| 4 | High-Volatility Regime Collapse & Emergency De-leveraging | F963, F968 | Medium |
| 5 | Full Production Verification Pipeline & Invariant Guardrail Suite | F965, F966, F967, F968 | High |

## Coverage Thresholds
- Tier 1: >=5 per feature (50 test assertions)
- Tier 2: >=5 per feature (50 test assertions)
- Tier 3: Pairwise coverage of major feature interactions (20 test assertions)
- Tier 4: >=5 realistic application scenarios (10 scenario assertions)
- Total: >= 130 test assertions
