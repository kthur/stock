# Execution Plan — Price Prediction Feature Upgrades

## Objective
Modify all stock price prediction-related modules, engines, and pipelines to incorporate market capitalization, trading volume, and floating shares, using overall market benchmarks to predict prices.

## Plan Steps
1. **Phase 1: Codebase Exploration**
   - Spawn a `teamwork_preview_explorer` subagent to locate and analyze:
     - Feature engineering and data collection pipelines.
     - `OnDevicePredictionModel` and its training scripts.
     - `macro_predictor.py`.
     - `HybridStrategyEngine`.
     - `post_market_scoring.py`.
     - Existing tests and documentation.
     - Available market indices or benchmark metrics.
   - Collect and synthesize explorer findings.

2. **Phase 2: Planning & Decomposition**
   - Refine `PROJECT.md` at project root to update/re-partition milestones for these new requirements.
   - Create interface contracts and code layouts in `PROJECT.md`.
   - Setup E2E Testing Track to create opaque-box E2E test cases covering the new features (Tier 1-4).
   - Setup Implementation Track to execute the milestones sequentially or in parallel.

3. **Phase 3: Execution of Milestones**
   - Milestone 1: Feature Engineering (market cap, volume, floating shares/value, market normalization).
   - Milestone 2: Model Updates (OnDevicePredictionModel, training scripts, macro_predictor).
   - Milestone 3: Strategy & Scoring Updates (HybridStrategyEngine, post_market_scoring).
   - Milestone 4: Documentation & Test Updates.
   - Run the Explorer -> Worker -> Reviewer -> Challenger -> Auditor loop for each milestone.

4. **Phase 4: Verification & Audit**
   - Run full test suite, verify 100% pass.
   - Run Challenger testing to verify correctness.
   - Run Forensic Auditor to ensure clean verdict (no cheating, authentic implementation).
