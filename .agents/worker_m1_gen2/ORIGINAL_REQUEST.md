## 2026-06-12T06:18:08Z

You are a teamwork_preview_worker. Your identity is: Worker M1.
Your working directory is d:\Finance\code\stock\.agents\worker_m1_gen2.
Your task is to implement the feature engineering logic for Milestone 1 (Feature Engineering) as specified in SCOPE.md (d:\Finance\code\stock\.agents\orchestrator_gen2\SCOPE.md).

Specifically:
1. Open and study trading_system/src/ai/prediction_model.py and related files to see how data is structured.
2. Implement the FallbackMetadataDict class and the FALLBACK_METADATA global singleton in trading_system/src/ai/prediction_model.py (or a shared utility, but prediction_model.py is recommended so it can be imported cleanly). It should contain real values for key benchmarks (AAPL, MSFT, GOOGL, GOOG, AMZN, TSLA, NVDA, META, 005930, 000660, 005380, 000270, 035420, 035720, 068270, 207940) and dynamically return deterministic mock metadata for any other ticker using a seed or md5 hash of the ticker symbol. Ensure it supports cleaning ticker suffixes (like ".KS" or ".KQ") during lookups.
3. Implement the apply_market_normalization(self, prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame] method in the OnDevicePredictionModel class (or a top-level helper in that module if more appropriate, but must be accessible). It must:
   - Separate stocks into regional groups (US vs KR) based on symbols to avoid currency mismatch between USD and KRW.
   - For each stock, calculate daily stock-level market_cap (= Close * shares_outstanding) and floating_value (= Close * floating_shares, with a fallback of Close * Volume if floating_shares is unavailable or <= 0).
   - Align dates across all stocks in each regional group and compute daily baseline total sums for market_cap, floating_value, and Volume.
   - Calculate normalized stock features: norm_market_cap (= stock market_cap / daily regional total market_cap), norm_floating_value (= stock floating_value / daily regional total floating_value), and norm_volume (= stock Volume / daily regional total Volume).
   - Protect against division-by-zero or empty totals by returning 0.0.
   - Return the updated prices_dict.
4. Run python builds and pytest tests in trading_system to verify that there are no syntax or import errors. Write a new unit test in trading_system/tests/test_feature_normalization.py to verify that apply_market_normalization and FallbackMetadataDict work correctly.
5. Write your implementation report to d:\Finance\code\stock\.agents\worker_m1_gen2\changes.md and send a completion message to c9741707-d639-4b47-b772-6d9392f7597f.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
