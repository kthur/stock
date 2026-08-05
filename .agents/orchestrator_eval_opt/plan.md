# Evaluation & Optimization Plan: Stock Trading System

## Overview
Comprehensive multi-agent evaluation, optimization, verification, and resolution for the Stock Trading System (`d:\Finance\code\stock`).

## Milestones & Strategy

### Phase 0: Parallel Technical Survey
- **Explorer 1 (R1 Focus)**: Investigate `src/ai/ensemble_scorer.py`, `src/ai/prediction_model.py`, and related model fitting code for PCA Symmetric ZCA factor orthogonalization across all 6 regimes and Isotonic Regression calibrators / rolling Sharpe weighting.
- **Explorer 2 (R2 Focus)**: Investigate `generate_report.py`, `src/risk/risk_manager.py`, `trade_logs.db`, and `OMS` engine in `src/` for GICS sector-based stress scenarios, crisis thresholds, order execution tracking, and tracking error calculation.
- **Explorer 3 (R3 Focus)**: Investigate `src/data_layer/indicator_storage.py`, `src/persistence/database.py`, `.github/workflows/`, `index.html`, and `update_dashboard.py` for SQLite WAL locks, GHA timing, mobile (375/414px) / desktop (1920px) responsive layout, sticky table headers, and macro badges.

### Milestone 1: Financial Engineering & Model Optimization (R1)
- Verify & fix PCA Symmetric ZCA factor orthogonalization and correlation suppression under all 6 market regimes.
- Verify & fix Isotonic Regression calibrators and rolling Sharpe weights adaptation.

### Milestone 2: Risk Management & Portfolio Optimization (R2)
- Verify & fix GICS sector-based stress scenarios and crisis level thresholds in `generate_report.py` / `src/risk/`.
- Validate real-time order execution tracking in `trade_logs.db` and tracking error monitoring in OMS engine.

### Milestone 3: Pipeline Resilience & UI/UX Presentation (R3)
- Audit SQLite WAL multi-thread write locks and workflow execution timing for GHA pipeline resilience.
- Verify mobile (375px/414px) and desktop (1920px) rendering, sticky table headers, and macro badges in GitHub Pages report (`index.html` / `update_dashboard.py`).

### Milestone 4: End-to-End System Verification & GHA Artifact Audit
- Clean pytest verification (`.venv\Scripts\python.exe -m pytest tests/ -v`).
- GHA Artifact Verifier execution (`verify_gha_artifacts.py`).
- Final forensic audit and handoff synthesis.
