## 2026-07-30T01:39:23Z
You are Worker 2 assigned to Requirement 3 (R3: Multicollinearity Suppression & Regime Dynamic Ensemble).
Working directory: D:\Finance\code\stock\.agents\worker_r3_1

Read the exploration findings and specifications from:
- D:\Finance\code\stock\.agents\explorer_r3_1\analysis_r3.md
- D:\Finance\code\stock\.agents\explorer_r3_1\handoff.md

Your Tasks:
1. Create `src/ai/correlation_monitor.py` (`StrategyCorrelationMonitor`):
   - Implement daily cross-sectional Spearman rank correlation matrix $R_{ij} \in \mathbb{R}^{17 \times 17}$ across the 17 strategies.
   - Implement VIF calculation and Effective Strategy Count ($N_{\text{eff}}$).
2. Create `src/ai/factor_suppression.py` (`RegimeFactorSuppressionEngine`):
   - Implement 2D regime-specific correlation factor noise dampening penalty $P_i(R)$ targeting false breakout noise in SIDEWAYS regimes and anti-trend noise in BULL regimes.
3. Integrate into `src/ai/ensemble_scorer.py` and `src/ai/optuna_tuner.py`:
   - Incorporate correlation monitoring and factor noise suppression into the 2D regime dynamic ensemble scoring pipeline in `EnsembleScoringEngine`.
   - Update `OptunaStrategyTuner` in `src/ai/optuna_tuner.py` to tune correlation thresholds $\theta(R)$ and penalty intensity $\lambda(R)$.
4. Create unit tests `tests/test_correlation_suppression.py` testing Spearman matrix computation, VIF, regime factor noise suppression, and ensemble scoring integration.
5. Run tests with `.venv\Scripts\python.exe -m pytest tests/test_correlation_suppression.py -v`.
6. Report build/test results, implementation details, and save handoff to `D:\Finance\code\stock\.agents\worker_r3_1\handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
