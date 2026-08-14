# Orchestration Plan: Factor Neutralization & 2D Regime Dynamic Sharpe Ensemble

## Project Goal
Enhance 31-factor alpha strategies for 3,379 symbols (KOSPI, KOSDAQ, KONEX, SP500, NASDAQ, RUSSELL2000), enforce Fama-French 5-factor pure alpha neutralization (|rho| < 0.15), and optimize 2D regime dynamic weights using Exponential Sharpe Multipliers with EMA smoothing.

## Phases

### Phase 0: Survey & Architecture Mapping
- [ ] Spawn 3 Explorers in parallel to map:
  - Explorer 1: 31 Strategy engines (`src/core/`, `src/ai/`, noise filtering, signal precision).
  - Explorer 2: Factor Neutralizer (`src/core/factor_neutralized.py`, Gram-Schmidt, 5-Factor constraints).
  - Explorer 3: 2D Regime Engine & Ensemble (`src/ai/ensemble_scorer.py`, `src/risk/`, tests, backtest runner).
- [ ] Aggregate findings into `PROJECT.md` and `TEST_INFRA.md`.

### Phase 1: Milestone 1 — Alpha Scoring & Factor Neutralization
- [ ] Explorers -> Worker -> Reviewers -> Challengers -> Auditor -> Gate
- [ ] Verify noise filtering in key strategies (Surge, VCP, Stat-Arb, Sector Rotation).
- [ ] Verify Gram-Schmidt orthogonalization and pure alpha residual correlation constraint |rho| < 0.15.

### Phase 2: Milestone 2 — 2D Regime & Dynamic Exponential Sharpe Multiplier
- [ ] Explorers -> Worker -> Reviewers -> Challengers -> Auditor -> Gate
- [ ] Implement Exponential Sharpe Multiplier with EMA smoothing across 6 2D market regimes.
- [ ] Verify downside risk defense during high-volatility/bear regimes.

### Phase 3: Milestone 3 — Backtest, Pytest Regression & Pipeline Validation
- [ ] Execute rolling backtest over 3,379 symbols.
- [ ] Run 818+ pytest tests ensuring 100% PASS.
- [ ] Run `run_pipeline.py` and verify `index.html` report generation.

### Phase 4: Final Milestone & Human Report
- [ ] Adversarial coverage hardening.
- [ ] Generate comprehensive final report and notify sentinel.
