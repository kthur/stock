# Explorer M2 Dispatch: 2D Regime Dynamic Weights & Exponential Sharpe Multiplier Design

## Objective
Analyze the exact implementation and verification requirements for Milestone 2:
1. `trading_system/src/ai/ensemble_scorer.py`:
   - Verify and optimize the 31-strategy weight matrix for all 6 2D market regime combo states:
     `BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`.
   - Exponential Sharpe Multiplier formulation:
     $$w_i = \text{base\_w}_i \cdot \exp(\gamma \cdot \text{clip}(\text{Sharpe}_i, -L, L))$$
     with underperformance pruning ($\text{Sharpe}_i < -0.50 \implies w_i = 0.0$), power ratio damping ($\le 20.0$), and persistence in `models/prev_weights.json`.
   - Adaptive EMA smoothing: $\alpha_{\text{eff}} = 0.20$ in steady state, $\alpha_{\text{eff}} = 1.0$ on regime shift to provide zero-lag downside protection.
   - Verification of Microstructure transaction cost deduction (STT, SEC, dynamic bid-ask spread, Kyle/Almgren-Chriss market impact).
2. `trading_system/src/analysis/regime_detector.py`:
   - Fast shock overrides (VIX > 30, S&P crash -3% 1d / -5% 2d) and US/KR decoupling analysis.
3. Test suite design & verification:
   - Run and audit `tests/test_isotonic_sharpe_calibration.py`, `trading_system/tests/test_hpo_and_2d_ensemble.py`, and create any additional stress tests needed for 2D regime weighting.

## Inputs
- `d:\Finance\code\stock\ORIGINAL_REQUEST.md`
- `d:\Finance\code\stock\PROJECT.md`
- `d:\Finance\code\stock\TEST_INFRA.md`
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/analysis/regime_detector.py`

## Deliverables
- Detailed design in `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2\analysis.md`.
- Handoff report in `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2\handoff.md`.
