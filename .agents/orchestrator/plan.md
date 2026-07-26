# Project Plan: Stock Trading System Autonomous Enhancement

## Architecture & Goals
Target: 3,379 symbols (SP500, KOSPI, KOSDAQ, KONEX) across 5 strategies:
1. Regression
2. Surge Classifier
3. Lead-Lag Matrix
4. VCP Rule Pattern Detector
5. VCP ML Predictor

Enhancement Scope:
- **R1: AI Model Precision & Auto-tuning**
  - Optuna HPO framework integration for all 5 strategies.
  - 2D regime + rolling Sharpe dynamic ensemble weighting.
- **R2: GitHub Pages Dashboard & HRP UX Enhancement**
  - HRP (Hierarchical Risk Parity) asset allocation weight visualizer in `gh-pages/index.html`.
  - Regime performance trends chart.
  - Mobile-friendly hyperlinks to Naver Finance (KRX symbols) and Yahoo Finance / Finviz (SP500 symbols).
- **R3: KIS Automated Trading Safety & ATR Trailing Stop**
  - ATR (Average True Range) dynamic trailing stop mechanism for order execution.
  - Portfolio exposure limit controls (max allocation %, sector cap, risk budget).
  - Pre-order validation and execution safety guards.

## Milestones & Execution Plan

### Milestone 1: Exploration & Gap Analysis
- **Goal**: Audit existing codebase, identify missing pieces for R1, R2, R3, run baseline tests (`pytest trading_system/tests/ -v` and `verify_gha_artifacts.py`).
- **Agents**: 3 Explorers (teamwork_preview_explorer).
- **Deliverables**: Detailed gap reports and architecture blueprints for M2, M3, M4.

### Milestone 2: R1 - AI Model Precision & Dynamic Ensemble
- **Goal**: Implement Optuna HPO tuning for 5 strategies and 2D regime + rolling Sharpe dynamic ensemble weighting.
- **Agents**: Worker -> Reviewer -> Challenger.
- **Deliverables**: Optuna integration scripts/modules, regime Sharpe ensemble logic, updated model training/inference scripts.

### Milestone 3: R2 - GitHub Pages & HRP UX Enhancement
- **Goal**: Add HRP allocation chart, regime trend visualizations, and symbol hyperlinks (Naver/Foreign) to `generate_report.py` and `gh-pages/index.html`.
- **Agents**: Worker -> Reviewer -> Challenger.
- **Deliverables**: Updated `generate_report.py`, HRP visualizer, mobile links.

### Milestone 4: R3 - KIS Automated Trading Safety & ATR Trailing Stop
- **Goal**: Implement ATR dynamic trailing stop, portfolio exposure limits, order safety checks in KIS execution module.
- **Agents**: Worker -> Reviewer -> Challenger.
- **Deliverables**: KIS execution engine updates, ATR trailing stop module, risk limit rules, test suite.

### Milestone 5: E2E Verification & Forensic Integrity Audit
- **Goal**: Run complete verification: `pytest trading_system/tests/ -v` (100% pass), `verify_gha_artifacts.py` (✅ PASSED), 0% NaN/Null, clean audit from Forensic Auditor.
- **Agents**: Challenger -> Forensic Auditor (`teamwork_preview_auditor`).
- **Deliverables**: Verification logs, Auditor CLEAN verdict.
