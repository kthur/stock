# Milestone 1: Feature Engineering Logic Implementation Report

## Overview
We have successfully implemented the Fallback Metadata and Market Normalization logic inside the AI prediction module as specified in `SCOPE.md`.

## Changes Made
1. **`trading_system/src/ai/prediction_model.py`**:
   - Added imports: `hashlib` and `numpy as np`.
   - Implemented `FallbackMetadataDict` inheriting from `dict` which loads real values for 16 key benchmarks (US and KR) and dynamically returns deterministic mock metadata (`shares_outstanding` and `floating_shares` generated via `md5` hashing of the ticker symbol) for other symbols. Suffixes (such as `.KS` or `.KQ`) are stripped before lookups.
   - Instantiated `FALLBACK_METADATA` as a global instance of `FallbackMetadataDict`.
   - Added the method `apply_market_normalization(self, prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]` to the `OnDevicePredictionModel` class. The method:
     - Separates stock tickers into regional groups: **US** vs **KR**. Cleaned tickers with all-digit symbols or tickers with `.KS`/`.KQ` suffix are classified as **KR**; other tickers are classified as **US**.
     - Calculates stock-level `market_cap` (= Close * shares_outstanding) and `floating_value` (= Close * floating_shares, falling back to Close * Volume when `floating_shares` is <= 0 or NaN).
     - Aligns dates across all stocks in each regional group using series alignment (`.add(..., fill_value=0.0)`) and computes the daily baseline total sums for `market_cap`, `floating_value`, and `Volume`.
     - Calculates normalized features: `norm_market_cap` (= stock market_cap / daily regional total market_cap), `norm_floating_value` (= stock floating_value / daily regional total floating_value), and `norm_volume` (= stock Volume / daily regional total Volume).
     - Safeguards against division-by-zero or empty total sums by returning 0.0.
     - Preserves and returns empty or missing DataFrames from `prices_dict`.

2. **`trading_system/tests/test_feature_normalization.py`**:
   - Created a comprehensive set of unit tests in `TestFeatureNormalization` covering:
     - Pre-configured key benchmark values.
     - Suffix cleaning functionality (`AAPL.O`, `005930.KS`, `000660.KQ`).
     - Dynamic mock metadata generation, value range constraints, and determinism.
     - Regional split between US (e.g. AAPL, MSFT) and KR (e.g. 005930.KS) stocks.
     - Stock-level market cap and floating value calculations.
     - Floating value fallback logic for NaN/negative values.
     - Cross-sectional normalization against regional baseline totals.
     - Division-by-zero protection.
     - Empty inputs or None dataframes.

## Verification
- Ran local pytest on the new unit test file:
  `pytest tests/test_feature_normalization.py` -> **4 passed in 15.58s**.
- Ran the full test suite in `trading_system` to verify no regressions:
  `pytest` -> **318 passed, 2 skipped, 4 warnings in 2:17**.
