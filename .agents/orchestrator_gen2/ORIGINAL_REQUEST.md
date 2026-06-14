# Original User Request

## 2026-06-12T06:04:30Z

Modify all stock price prediction-related modules, engines, and pipelines to incorporate market capitalization, trading volume, and floating shares, using overall market benchmarks to predict prices. Update system documentation accordingly.
Specifically:
R1. Calculate stock-level market cap and floating shares, floating value, and market-level baseline metrics.
R2. Modify prediction modules (OnDevicePredictionModel, training scripts, macro_predictor.py) to incorporate new normalized features.
R3. Update HybridStrategyEngine and post_market_scoring.py to use updated models and incorporate volume/floating value features.
R4. Update documentation and implement/update unit and integration tests.
Ensure you communicate progress by updating your progress.md regularly and inform me when all milestones are complete.
