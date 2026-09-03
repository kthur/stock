# E2E Test Infra: Dashboard Strategy Data & UI Integrity

## Test Philosophy
- Opaque-box, requirement-driven testing covering dashboard strategy data parsing, multi-market table rendering, schema synchronization, interactive UI/filtering, and CLI execution.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing.

## Feature Inventory & Test Mapping
| # | Feature | Requirement | Tier 1 (Happy) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Workload) |
|---|---------|-------------|:--------------:|:-----------------:|:-----------------:|:-----------------:|
| 1 | Strategy Proxy Fallback Scoring | R1, R2 | 5 | 5 | ✓ | ✓ |
| 2 | Pipeline Strategy Report Saving | R1, R2 | 5 | 5 | ✓ | ✓ |
| 3 | Robust Market Discovery in Merger | R2 | 5 | 5 | ✓ | ✓ |
| 4 | Ensemble Section Header Sync | R2 | 5 | 5 | ✓ | ✓ |
| 5 | 37-Strategy File Merge Alignment | R2, R14 | 5 | 5 | ✓ | ✓ |
| 6 | Core 5-Market Dashboard Parity | R1, R3 | 5 | 5 | ✓ | ✓ |
| 7 | Strategy Parser Enhancements | R1 | 5 | 5 | ✓ | ✓ |
| 8 | Client JavaScript Hardening | R3 | 5 | 5 | ✓ | ✓ |
| 9 | CLI Execution & Parity Test Suite | Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 10 | Zero NaN/Mojibake & Encoding Integrity | Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 11 | Unified Portfolio Allocator (BL+HERC+RP+CVaR) | R15 | 5 | 5 | ✓ | ✓ |
| 12 | OMS Gate 8 Synthetic Inverse Hedge Overlay | R15 | 5 | 5 | ✓ | ✓ |
| 13 | V8 System Integrity & Defect Remediation | V8 Audit | 5 | 5 | ✓ | ✓ |
| 14 | World-Class Trader Return Enhancements | World-Class Upgrade | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Test Runner**: `pytest tests/` via `.venv/bin/pytest` or `.venv\Scripts\pytest.exe`.
- **Target Suites**:
  - `tests/test_v8_remediation.py`: 43 critical/high/medium defect remediation verification.
  - `tests/test_world_class_quant_enhancements.py`: Continuous Kelly, factor neutralizer, tick sizes, turnover penalties.
  - `tests/test_world_class_trader_return_enhancements.py`: Midpoint peg, intraday ATR trailing stop ratchet, confluence alpha boost.
  - `tests/test_v7_returns_maximization.py`: Return maximization, VIF threshold, capitulation overrides.
  - `tests/test_v6_improvements.py`: 4-Tier regression tests across 35 architectural items.
  - `tests/test_v6_adversarial_stress.py`: Adversarial extreme boundary conditions and single-stock N=1 tests.
  - `tests/test_report_generator_hrp.py`: Unified portfolio allocation parsing & HTML inclusion.
  - `tests/test_report_ux_and_rounding.py`: Largest remainder rounding, search universe counter, table headers.
  - `tests/test_challenger2_dashboard_parser_stress.py`: Multi-column formats, cell sanitizer against NaN/null/inf, zero unescaped strings.
  - `tests/test_merge_generic_strategies.py`: Multi-market file merging across all 37 strategies.
  - `tests/test_verify_gha_artifacts.py`: GHA pipeline artifact and canonical order validation.
- **Pass / Fail Semantics**: 100% test pass (2,130 collected test items), exit code 0, zero regressions.

## Coverage Thresholds
- Tier 1: ≥5 test cases per feature (happy path parsing, standard multi-market rows)
- Tier 2: ≥5 test cases per feature (boundary/corrupt files, 0-row fallback, missing columns, signed NaNs, missing delimiters)
- Tier 3: Pairwise combinations across 5 markets x 37 strategies x 3 file formats
- Tier 4: Real-world workload scenarios (Full pipeline generation -> 37-strategy merge -> HTML report compilation -> HTML DOM validation)
