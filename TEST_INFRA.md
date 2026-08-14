# E2E Test Infra: Stock Trading System (31-Factor Alpha & 2D Regime Ensemble)

## Test Philosophy
- Opaque-box, requirement-driven, and white-box empirical stress testing.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinatorial Testing + Real-World Workload Testing.

## Feature Inventory & Test Coverage Goals
| # | Feature | Source (Requirement) | Tier 1 (Unit/Feature) | Tier 2 (Boundary/Edge) | Tier 3 (Cross-Factor) | Tier 4 (Workload/E2E) |
|---|---------|----------------------|:---------------------:|:----------------------:|:---------------------:|:---------------------:|
| F1 | Multi-Factor Neutralizer Interface & Imputation | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F2 | Fama-French 5-Factor QR Residualization | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F3 | Pure Alpha $|\rho| < 0.15$ Hard SLA Gate | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F4 | Strategy Alpha Precision & Noise Filtering | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F5 | 2D Regime Dynamic Exponential Sharpe Multipliers | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F6 | Adaptive EMA Smoothing & Downside Risk Defense | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F7 | Microstructure Transaction Cost Deduction | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F8 | Comparative Rolling Backtest Verification | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| F9 | Pytest Full Regression (1,554+ Tests 100% Pass) | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| F10 | Pipeline Execution & GitHub Pages Report Update | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Test Runner**: `.venv\Scripts\python.exe -m pytest tests/ trading_system/tests/ -v`
- **Pass/Fail Semantics**: 100% of discovered tests (1,554+) must PASS with 0 failures, 0 errors.
- **Factor Correlation Gate**: $\max_{k \in \{1..5\}} |\rho(f_k, \text{pure\_alpha})| < 0.15$ verified across full universe.
- **Coverage Requirement**: $\ge 95\%$ valid scores across 3,379 symbols in `strategy_data_coverage_report.txt`.
- **Pipeline Integrity**: `run_pipeline.py` exit code 0, all output files populated, `gh-pages/index.html` updated.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | High-Volatility Market Crash (VIX > 30 Shock) | F5, F6, F7, F9 | High |
| 2 | Small-Cap & Microcap Extreme Missing Fundamentals | F1, F2, F3 | High |
| 3 | Strong Collinear Factor Drift in Bull Market | F2, F3, F4, F5 | High |
| 4 | Multi-Horizon Cross-Market Pipeline Execution (US+KR) | F1, F4, F7, F10 | Extreme |
| 5 | Rolling 5-Year Multi-Factor Comparative Backtest | F8, F9, F10 | High |
