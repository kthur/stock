# Execution Plan — Stock Trading System Algorithm Optimization

## Overview
Enhance the Stock Trading System's ensemble scoring engine, cost modeling, dynamic re-weighting, and correlation handling.

## Milestones & Strategy

### Milestone 1: Dynamic Re-weighting Scoring for Missing Data (R1)
- Target file: `src/ai/ensemble_scorer.py`
- Objective: Rescale valid strategy weights when specific strategy outputs are missing (e.g. Options IV Skew, DART filings, ARM) so that remaining active strategy weights sum to 1.0 (100%).
- Verification: Unit tests in `tests/test_ensemble_scorer.py` verifying dynamic re-weighting behavior with missing data.

### Milestone 2: Precision Order Book Market Impact Cost Modeling (R2)
- Target files: `src/config.py`, `src/ai/ensemble_scorer.py`
- Objective: Implement order book market impact cost and bid-ask spread modeling considering stock liquidity (turnover, market cap, volatility) and order size hypothesis.
- Verification: pytest for Order Book Market Impact cost calculations (`tests/test_market_impact.py` or updated test suite).

### Milestone 3: Multicollinearity Suppression & Regime Dynamic Ensemble (R3)
- Target files: `src/ai/ensemble_scorer.py`, `src/ai/optuna_tuner.py`, `src/risk/risk_manager.py` (and related regime components)
- Objective: Monitor inter-strategy signal correlations, suppress redundant factor noise under specific 2D market regimes (sideways, trending, high volatility), and optimize predicted returns by integrating Optuna tuner and Regime Scorer.
- Verification: Pytest suite verifying correlation matrix computation, noise suppression, and regime dynamic weighting.

### Milestone 4: End-to-End Pipeline & Integration Verification
- Objective: Execute full pipeline/backtest run cleanly, generating `ensemble_predictions.txt` with top 20 recommendations and decision rationales. Verify all 17 strategies and dynamic re-weighting/cost modeling in full execution.
- Verification: Pipeline execution producing clean logs, output files, and valid predictions. Forensic Audit verification.

## Execution Topology & Iteration Loop
Per milestone:
1. **Explorer**: Analyze codebase, current implementation, missing features, and write technical design proposal.
2. **Worker**: Implement code changes and new unit tests, run build/pytest.
3. **Reviewer & Challenger**: Review implementation, test coverage, edge cases, and run empirical checks.
4. **Forensic Auditor**: Run integrity checks to ensure authentic implementation without dummy facades or hardcoding.
5. **Gate Verification**: Confirm all pass criteria.
