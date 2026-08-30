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
| 5 | 31-Strategy File Merge Alignment | R2 | 5 | 5 | ✓ | ✓ |
| 6 | Core 5-Market Dashboard Parity | R1, R3 | 5 | 5 | ✓ | ✓ |
| 7 | Strategy Parser Enhancements | R1 | 5 | 5 | ✓ | ✓ |
| 8 | Client JavaScript Hardening | R3 | 5 | 5 | ✓ | ✓ |
| 9 | CLI Execution & Parity Test Suite | Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 10 | Zero NaN/Mojibake & Encoding Integrity | Acceptance Criteria | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Test Runner**: `pytest tests/` via `.venv/bin/pytest` or `.venv\Scripts\pytest.exe`.
- **Target Suites**:
  - `tests/test_report_generator_hrp.py`: HRP allocation parsing & HTML inclusion.
  - `tests/test_report_ux_and_rounding.py`: Largest remainder rounding, search universe counter, table headers.
  - `tests/test_challenger2_dashboard_parser_stress.py`: RIM multi-column formats, cell sanitizer against NaN/null/inf, zero unescaped strings.
  - `tests/test_merge_generic_strategies.py`: Multi-market file merging, section headers, fallback handling.
  - `tests/test_generate_report_cli.py`: New CLI execution test with `--result-dir` and `--out`.
  - `tests/test_dashboard_strategy_parity.py`: New 31-strategy 5-market table parity and link integrity tests.
- **Pass / Fail Semantics**: 100% test pass, exit code 0, no regressions.

## Coverage Thresholds
- Tier 1: ≥5 test cases per feature (happy path parsing, standard multi-market rows)
- Tier 2: ≥5 test cases per feature (boundary/corrupt files, 0-row fallback, missing columns, signed NaNs, missing delimiters)
- Tier 3: Pairwise combinations across 5 markets x 31 strategies x 3 file formats
- Tier 4: Real-world workload scenarios (Full pipeline generation -> merge -> HTML report compilation -> HTML DOM structure validation)
