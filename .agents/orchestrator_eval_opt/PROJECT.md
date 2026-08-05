# Project: Stock Trading System Evaluation & Optimization

## Architecture
Multi-factor stock trading and prediction system covering 3,379 symbols across 6 markets (KOSPI, KOSDAQ, KONEX, SP500, NASDAQ, RUSSELL2000) using an 18-strategy ensemble engine, 2D regime detection, RiskManager gating, Isotonic calibration, ZCA orthogonalization, Risk Parity OMS engine, and GitHub Pages dashboard reporting.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | PCA ZCA Orthogonalization | Verify PCA Symmetric ZCA factor orthogonalization and correlation suppression under all 6 market regimes; apply Ledoit-Wolf shrinkage & CRISIS mapping | M1 | R1 |
| 2 | Isotonic & Rolling Sharpe Adaptation | Ensure Isotonic Regression calibrators and rolling Sharpe weights seamlessly adapt without signal degradation; add class balance guard & regime shift EMA reset | M1 | R1 |
| 3 | GICS Stress & Crisis Thresholds | Verify GICS sector-based stress scenarios and crisis level thresholds in generate_report.py / risk_manager.py | M2 | R2 |
| 4 | Execution & Tracking Error in OMS | Validate real-time order execution tracking in trade_logs.db and tracking error monitoring in OMS engine | M2 | R2 |
| 5 | SQLite WAL & GHA Execution Timing | Audit SQLite WAL multi-thread write locks and workflow execution timing for GHA pipeline resilience | M3 | R3 |
| 6 | Mobile/Desktop Dashboard UI & Badges | Verify mobile (375px/414px) and desktop (1920px) rendering, sticky table headers, and macro badges in index.html / update_dashboard.py | M3 | R3 |
| 7 | Full Test Suite Clean Pass | All unit and integration tests pass cleanly via pytest | M4 | Acceptance |
| 8 | GHA Artifact Verification | verify_gha_artifacts.py confirms 100% valid non-zero data across all 18 strategy panels and 5 markets | M4 | Acceptance |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 0 | Phase 0: Survey | Codebase mapping across R1, R2, R3 | None | DONE |
| 1 | M1: Financial Eng & Model Opt | PCA ZCA orthogonalization, Ledoit-Wolf shrinkage, Isotonic/Sharpe adaptation, regime shift EMA, new test suite | M0 | DONE |
| 2 | M2: Risk Mgmt & Portfolio Opt | GICS stress, crisis thresholds, trade_logs.db, OMS tracking error verification & test hardening | M0, M1 | IN_PROGRESS |
| 3 | M3: Pipeline Resilience & UI/UX | SQLite WAL locks, GHA timing, Mobile/Desktop UI, sticky headers verification | M0 | PLANNED |
| 4 | M4: System E2E & Artifact Audit | Pytest suite pass & verify_gha_artifacts.py 100% check | M1, M2, M3 | PLANNED |

## Code Layout
- `trading_system/src/ai/factor_orthogonalizer.py`: PCA ZCA orthogonalization engine, Ledoit-Wolf shrinkage
- `trading_system/src/ai/factor_suppression.py`: Regime factor noise suppression & CRISIS/HIGH_VOL parameter mapping
- `trading_system/src/ai/ensemble_scorer.py`: EnsembleScoringEngine, Isotonic calibration class balance guard, EMA weight smoothing regime shift acceleration
- `trading_system/src/risk/risk_manager.py`: RiskManager & CrisisDetector, crisis level thresholds
- `generate_report.py`: GICS sector-based stress scenarios and report generation
- `trading_system/src/execution/oms.py` & `src/execution/`: Execution OMS Engine, trade_logs.db tracking, tracking error, slippage feedback
- `trading_system/src/data_layer/indicator_storage.py` & `src/persistence/database.py`: SQLite WAL manager, lock mutexes
- `update_dashboard.py` & `index.html`: GitHub Pages dashboard generation & UI layout
- `verify_gha_artifacts.py`: GHA Artifact Verifier
- `tests/test_isotonic_sharpe_calibration.py`: New comprehensive test suite for Isotonic calibration and rolling Sharpe weighting
- `tests/test_risk_manager.py`, `tests/test_risk_enhancements.py`, `tests/test_portfolio_risk.py`, `tests/test_portfolio_allocator.py`, `tests/test_portfolio_optimizer_and_oms.py`: Risk and OMS test suites
