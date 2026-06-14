## 2026-06-12T07:46:42Z
You are a teamwork_preview_worker. Your identity is: Worker M3.
Your working directory is d:\Finance\code\stock\.agents\worker_m3_gen2.
Your task is to implement Milestone 3 (Strategy/Scoring updates) as specified in SCOPE.md (d:\Finance\code\stock\.agents\orchestrator_gen2\SCOPE.md).

Specifically:
1. Modify trading_system/src/core/strategy_engine.py (HybridStrategyEngine):
   - Update _compute_technical_indicators(self, price_bars: list, volume_bars: list = None, floating_shares: float = None) -> Dict.
   - Calculate 5-day volume SMA and 20-day volume SMA.
   - If 5-day volume SMA > 1.5 * 20-day volume SMA (volume expansion):
     - If price trend is positive (e.g. EMA20 > EMA50 or MACD > 0), add a volume bonus of +0.05 to the score.
     - If price trend is negative, subtract a volume penalty of -0.05.
   - Add a liquidity/floating value penalty: Calculate daily floating value. If the asset's floating value is extremely low (indicating high manipulation risk and low liquidity), cap the technical score or decrease the allocation confidence.
   - Update target allocations / position sizing rules to scale down targets for assets with low norm_volume or norm_floating_value.
2. Modify trading_system/scripts/post_market_scoring.py:
   - Pre-fetch all historical prices for the stock universe first into a prices_dict = {symbol: df}.
   - Apply OnDevicePredictionModel.apply_market_normalization(prices_dict) to compute normalized features cross-sectionally.
   - In the universe scoring loop, use the pre-computed, normalized features to call prediction_model.predict_current using the updated 9-feature model.
   - Call strategy_engine._compute_technical_indicators(closes, volumes, floating_shares) passing volume and floating shares.
   - Calculate the composite score, sort, rank, and store the post-market rankings to the database.
3. Test post-market scoring script execution and strategy engine logic using pytest. Make sure all tests pass without errors.
4. Write your implementation report to d:\Finance\code\stock\.agents\worker_m3_gen2\changes.md and send a completion message to c9741707-d639-4b47-b772-6d9392f7597f.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
