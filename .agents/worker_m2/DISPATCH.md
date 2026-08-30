## 2026-08-30T13:49:15Z
Milestone 2: Ensemble Meta-Learner & Dynamic 2D/3D Regime Weighting Enhancement.
Assignee: teamwork_preview_worker (worker_m2)
Working Directory: d:\Finance\code\stock\.agents\worker_m2
Authoritative Original Request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Project Blueprint: d:\Finance\code\stock\PROJECT.md
Survey Specification: d:\Finance\code\stock\.agents\explorer_survey_2\survey_report.md
Project Rules: d:\Finance\code\stock\AGENTS.md

Task Requirements:
1. Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md, PROJECT.md, and d:\Finance\code\stock\.agents\explorer_survey_2\survey_report.md.
2. In `trading_system/src/ai/ensemble_scorer.py`:
   - Register the 3 new high-alpha strategy keys (`cross_asset_spillover`, `supply_chain_gnn`, `range_expansion_breakout`) and their score columns (`cross_asset_spillover_score`, `supply_chain_gnn_score`, `range_expansion_score`) into:
     - `ALPHA_HORIZON_TIERS` (assign appropriately: e.g. `cross_asset_spillover` in medium/fast, `supply_chain_gnn` in medium, `range_expansion_breakout` in fast).
     - `REGIME_WEIGHTS` (1D regime base weights: BULL, SIDEWAYS, BEAR).
     - `REGIME_2D_WEIGHTS` (all 6 2D regimes: BEAR_LOW_VOL, BEAR_HIGH_VOL, SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL, BULL_LOW_VOL, BULL_HIGH_VOL). Verify strict 1.000 sum invariant.
     - `MACRO_WEIGHT_MODIFIERS` (3D macro modifiers).
     - `strategy_cols` and `STRATEGY_SCORE_COLS`.
   - Ensure synergy boosting and confluence rules seamlessly incorporate the new signals.
3. Validate and verify that `CrossSectionalScoreNormalizer`, `FactorOrthogonalizerEngine` (PCA-ZCA whitening), and `RegimeFactorSuppressionEngine` cleanly process the expanded 34-strategy matrix.
4. Run verification tests:
   `$env:PYTHONPATH="trading_system;trading_system/src;."; .venv\Scripts\pytest.exe tests/test_advanced_ensemble_features.py tests/test_regime_ensemble.py tests/test_adversarial_ensemble_scorer_challenger.py tests/test_r1_high_alpha_strategies.py -v`
5. Write your complete implementation and verification report to `d:\Finance\code\stock\.agents\worker_m2\handoff.md`.
6. Send a message to parent when complete.
