# E2E Test Infra: Stock Trading System

## Test Philosophy
- Opaque-box, requirement-driven. Verifies correct end-to-end processing of stock data pipelines, model training, prediction accuracy, and report generation without requiring details of internal helper routines.
- Methodology: Category-Partition (testing equivalence partitions of inputs), Boundary Value Analysis (boundary cases for windows, dimensions, parameters), Pairwise Interaction (combining strategies with market regimes and allocation policies), and Real-World Workload Testing (simulating daily pipeline execution, regime shifts, and multi-market sweeps).

## Feature Inventory
We map the 5 consolidated predictive strategies as features (F1-F5) and the 3 support modules as auxiliary features (F6-F8).

| # | Feature | Source (requirement) | Tier 1 (Happy Path) | Tier 2 (Boundary) | Tier 3 (Pairwise) |
|---|---------|---------------------|:-------------------:|:-----------------:|:-----------------:|
| 1 | XGBoost Regressor | AGENTS.md §1 / R6   | 5                   | 5                 | ✓                 |
| 2 | Surge Classifier | AGENTS.md §2 / R6   | 5                   | 5                 | ✓                 |
| 3 | Lead-Lag Follower | AGENTS.md §3 / R6   | 5                   | 5                 | ✓                 |
| 4 | VCP Pattern Detector | AGENTS.md §4 / R6   | 5                   | 5                 | ✓                 |
| 5 | VCP ML Predictor | AGENTS.md §5 / R6   | 5                   | 5                 | ✓                 |
| 6 | GMM Regime Detector | AGENTS.md R5/R6     | ✓                   | ✓                 | ✓                 |
| 7 | Dynamic Ensemble Scorer | AGENTS.md R6        | ✓                   | ✓                 | ✓                 |
| 8 | Portfolio Position Sizer | AGENTS.md R5/R6     | ✓                   | ✓                 | ✓                 |

## Test Architecture
- **Test Runner**: `.venv\Scripts\pytest.exe` executed on Windows from the workspace root.
- **Invocation**: `.venv\Scripts\pytest trading_system\tests\test_e2e_consolidated.py -v` (with option `-s` to view printed outputs).
- **Pass/Fail Semantics**: Standard pytest exit codes (0 = all tests pass, non-zero = failures). Each test case asserts specific output structures, prediction values range validity, file presence, or state transitions.
- **Test Case Format**: 
  - Input: Mocked databases (`stock_prices.db`, `market_indicators.db`) and custom generated dataframes representing specific market behavior (e.g. contracting ranges for VCP, lead-lag offsets).
  - Expected Output: Verified model prediction ranges, SQLite insertions in `ai_predictions.db`, and generated text reports (`pipeline_result.txt`, `vcp_patterns.txt`, etc.).
- **Directory Layout**:
  - `trading_system/tests/test_e2e_consolidated.py` - Single consolidated E2E and integration test file.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity | Description |
|---|----------|--------------------|------------|-------------|
| 1 | Daily Pipeline Run | F1, F2, F3, F4, F5, F6, F7, F8 | High | Executes `run_pipeline.py` with mock databases, confirming DB synchronization and all 5 strategy files are output. |
| 2 | Macro Regime Crash Shock | F6, F7, F8 | Medium | Simulates sudden index drop (e.g., -10%) and VIX spike. Verifies GMM detects BEAR regime and restricts portfolio limits to 20%. |
| 3 | Offline Cache-Only Run | F1, F2, F5 | Medium | Disconnects online fetching via patching, sets freshness constraint, and verifies execution completes using local DB caches. |
| 4 | Multi-Market Segment Sweeps | F1, F2, F5 | High | Evaluates multi-market model training (SP500, KOSPI, KOSDAQ, KONEX) to verify correct models are loaded and mapped. |
| 5 | Extreme Volatility & Contraction | F4, F5 | Medium | Simulates rapid market swings followed by tight consolidation to verify VCP rule-based scoring reacts accurately under extreme data. |

## Coverage Thresholds
- Tier 1 (Feature Coverage): ≥5 tests per strategy (F1-F5) -> Total ≥25 test cases.
- Tier 2 (Boundary & Corner Cases): ≥5 tests per strategy -> Total ≥25 test cases.
- Tier 3 (Cross-Feature Combinations): Pairwise interactions of features (e.g. Regime & Kelly, Regressor & Surge feature consistency) -> Total ≥5 test cases.
- Tier 4 (Real-World Application Scenarios): ≥5 realistic workload test cases.
- **Minimum expected tests: 60 test cases**
