# E2E Test Infra: Phase 3 Trading System

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + BVA + Pairwise + Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | Sentiment Analysis | ORIGINAL_REQUEST R1 | 5      | 5      | ✓      |
| 2 | RL Trading Model | ORIGINAL_REQUEST R1 | 5      | 5      | ✓      |
| 3 | Asset Allocation | ORIGINAL_REQUEST R1 | 5      | 5      | ✓      |
| 4 | PDF Report | ORIGINAL_REQUEST R2 | 5      | 5      | ✓      |
| 5 | Broker API | ORIGINAL_REQUEST R2 | 5      | 5      | ✓      |

## Test Architecture
- Test runner: `pytest`
- Test cases directory: `tests/phase3/e2e/`
- Test case format: pytest functions verifying inputs and outputs based on acceptance criteria.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Trade Cycle | F1, F2, F3, F5 | High |
| 2 | End of Day Reporting | F1, F3, F4 | Medium |
| 3 | Emergency Reallocation | F1, F3, F5 | Medium |

## Coverage Thresholds
- Tier 1: ≥5 per feature (25 total)
- Tier 2: ≥5 per feature (25 total)
- Tier 3: pairwise coverage of major feature interactions
- Tier 4: ≥3 realistic application scenarios
