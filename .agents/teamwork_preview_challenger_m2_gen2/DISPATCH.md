# Challenger M2 Gen 2 Dispatch: 2D Regime & Sharpe Weighting Empirical Stress

## Objective
Adversarially stress-test the 2D Regime Engine and Dynamic Exponential Sharpe Multiplier in `trading_system/src/ai/ensemble_scorer.py`:
- Rapid regime switching (BULL -> BEAR -> SIDEWAYS) verifying $\alpha = 1.0$ weight realignment.
- Extreme strategy Sharpe inputs (+5.0, -4.0) verifying clipping at $[-0.8047, +0.8047]$ and pruning at $< -0.50$.
- Extreme ratio power damping (> 20.0).
- Microstructure friction deduction on low-liquidity and penny stocks.

## Instructions
1. Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `TEST_INFRA.md`.
2. Write and execute stress test scripts, verify that all assertions pass without exception.
3. Report your verdict (APPROVE or REQUEST_CHANGES) in `handoff.md`.
