# Handoff Report: E2E Test Suite Plan for Phase 3

## 1. Observation
- `TEST_INFRA.md` requires an opaque-box, requirement-driven test suite for Phase 3. 
- The required feature inventory includes: 
  - F1: Sentiment Analysis (`analyze_sentiment(text: str) -> float`)
  - F2: RL Trading Model (`train_rl_model(data)`)
  - F3: Asset Allocation (`allocate_assets(prices_dict: dict) -> dict`)
  - F4: PDF Report (`generate_pdf_report(trade_data: list, file_path: str)`)
  - F5: Broker API (`RealBroker.connect()`, `RealBroker.submit_order(...)`)
- Test Coverage Thresholds specified:
  - **Tier 1:** ≥5 positive/base cases per feature.
  - **Tier 2:** ≥5 negative/edge cases per feature.
  - **Tier 3:** Pairwise coverage of major feature interactions.
  - **Tier 4:** ≥3 realistic application scenarios (Full Trade Cycle, End of Day Reporting, Emergency Reallocation).
- `PROJECT.md` details the interface contracts.
- **Note:** `ORIGINAL_REQUEST.md` was missing in the workspace, but `TEST_INFRA.md` and `PROJECT.md` provide sufficient requirements and interface definitions to deduce the necessary test specifications.

## 2. Logic Chain
1.  **Test Philosophy:** As requested, tests must be opaque-box. We do not mock internal logic of the target functions; we interact purely with the public interfaces. When the implementation is incomplete, we assume the inputs and outputs will follow the types specified in `PROJECT.md` (e.g., returning floats, dictionaries, creating physical files).
2.  **Tier 1 & 2 Planning (Equivalence Class & BVA):** For each feature, we define 5 positive cases (happy paths, boundary typicals) and 5 negative cases (invalid data, structural anomalies). 
3.  **Tier 3 Planning (Pairwise):** We map the sequential flow of data from one interface to another. E.g., Sentiment output -> Allocation input; Allocation output -> Broker submit_order.
4.  **Tier 4 Planning (Workload/Scenarios):** We follow the exact scenarios outlined in `TEST_INFRA.md`.
5.  **pytest Conventions:** Test files will be placed in `tests/phase3/e2e/test_e2e.py`. Features should be logically grouped using classes or prefixes (e.g., `TestSentimentAnalysis`). We plan the exact function names to be implemented by the worker.

## 3. Caveats
- `ORIGINAL_REQUEST.md` was not found in the provided directory. The plan relies exclusively on `TEST_INFRA.md` and `PROJECT.md`.
- Expected data formats for `train_rl_model(data)` and `RealBroker.submit_order(...)` are loosely defined in `PROJECT.md`. The tests assume basic Python types (e.g., dictionaries or dataframes for RL, and basic primitive args for orders).
- The worker will need to import the functions directly from `src.*`.

## 4. Conclusion
The proposed structure for `tests/phase3/e2e/test_e2e.py` is fully detailed in the below test case specification. The implementer should create the `test_e2e.py` file using standard pytest parameterization and fixtures where appropriate, adhering exactly to these proposed cases.

### Proposed Test Case Specification for `tests/phase3/e2e/test_e2e.py`

#### Tier 1: Positive/Base Cases (25 Tests)
**F1: Sentiment Analysis (`analyze_sentiment`)**
1. `test_sentiment_positive_text`: Pass strong positive text, assert score > 0.5.
2. `test_sentiment_negative_text`: Pass strong negative text, assert score < 0.5.
3. `test_sentiment_neutral_text`: Pass neutral/factual text, assert score ~ 0.5.
4. `test_sentiment_mixed_text`: Pass mixed text, assert float return type.
5. `test_sentiment_short_text`: Pass single word ("Good"), assert valid score.

**F2: RL Trading Model (`train_rl_model`)**
6. `test_rl_training_basic_data`: Pass typical market data dict/list, assert successful run.
7. `test_rl_training_single_epoch`: Pass small dataset, assert completion.
8. `test_rl_training_large_dataset`: Pass large dataset, assert completion without memory errors.
9. `test_rl_training_returns_none_or_model`: Assert the return type is handled correctly (model or None).
10. `test_rl_training_deterministic_run`: Run twice with identical data/seed, check if behavior is stable.

**F3: Asset Allocation (`allocate_assets`)**
11. `test_allocate_two_assets`: `{"AAPL": 150, "MSFT": 300}`, assert weights sum to 1.0.
12. `test_allocate_single_asset`: `{"AAPL": 150}`, assert weight is 1.0.
13. `test_allocate_five_assets`: Pass 5 distinct assets, assert all keys present and weights sum to 1.0.
14. `test_allocate_high_price_variance`: `{"A": 1, "B": 10000}`, assert valid distribution.
15. `test_allocate_same_prices`: `{"A": 100, "B": 100}`, assert equal distribution (0.5 each).

**F4: PDF Report (`generate_pdf_report`)**
16. `test_report_basic_trades`: Pass list of 3 basic trades, assert file created.
17. `test_report_single_trade`: Pass 1 trade, assert file created.
18. `test_report_large_number_of_trades`: Pass 100 trades, assert file created.
19. `test_report_file_creation_path`: Create in `./reports/test.pdf`, assert `os.path.exists`.
20. `test_report_overwrite`: Call twice on same path, assert no errors.

**F5: Broker API (`RealBroker`)**
21. `test_broker_connect_success`: Call `connect()`, assert success.
22. `test_broker_submit_buy_order`: Call `submit_order("AAPL", "BUY", 10)`, assert success.
23. `test_broker_submit_sell_order`: Call `submit_order("AAPL", "SELL", 10)`, assert success.
24. `test_broker_submit_multiple_orders`: Call `submit_order` iteratively 5 times.
25. `test_broker_submit_limit_order`: If supported, submit with specific price limit.

#### Tier 2: Negative/Edge Cases (25 Tests)
**F1: Sentiment Analysis**
26. `test_sentiment_empty_string`: Pass `""`, expect handled default or specific error.
27. `test_sentiment_very_long_text`: Pass 10,000+ char string.
28. `test_sentiment_special_characters`: Pass `"!@#$%^&*"`.
29. `test_sentiment_numeric_input`: Pass numeric type `12345` (expect TypeError) or `"12345"`.
30. `test_sentiment_none_input`: Pass `None`, expect TypeError/ValueError.

**F2: RL Trading Model**
31. `test_rl_training_empty_data`: Pass `[]` or `{}`.
32. `test_rl_training_missing_columns`: Pass data missing required price fields.
33. `test_rl_training_all_zeros_data`: Pass zeroed prices.
34. `test_rl_training_invalid_data_type`: Pass a string instead of data structure.
35. `test_rl_training_nan_values`: Pass `NaN` or `None` within the dataset.

**F3: Asset Allocation**
36. `test_allocate_empty_dict`: Pass `{}`, expect `{}` or ValueError.
37. `test_allocate_negative_prices`: Pass `{"AAPL": -150}`, expect error or zero weight.
38. `test_allocate_invalid_types`: Pass `{"AAPL": "high"}`, expect TypeError.
39. `test_allocate_none_input`: Pass `None`.
40. `test_allocate_zero_prices`: Pass `{"AAPL": 0}`.

**F4: PDF Report**
41. `test_report_empty_trades_list`: Pass `[]`, assert file still created with headers.
42. `test_report_invalid_path`: Pass `/invalid/path/test.pdf` (Unix) or `Z:\invalid\test.pdf` (Win), expect FileNotFoundError/OSError.
43. `test_report_missing_trade_keys`: Pass `[{"symbol": "AAPL"}]` (missing qty/price).
44. `test_report_none_trade_data`: Pass `None`.
45. `test_report_invalid_file_extension`: Pass `test.txt`.

**F5: Broker API**
46. `test_broker_submit_order_without_connect`: Call `submit_order` before `connect()`.
47. `test_broker_submit_invalid_quantity`: Pass `-10` or `0`.
48. `test_broker_submit_invalid_symbol`: Pass `""` or `None`.
49. `test_broker_invalid_order_type`: Pass `"HODL"`.
50. `test_broker_connect_idempotency`: Call `connect()` multiple times.

#### Tier 3: Pairwise Interaction Coverage
51. `test_pairwise_sentiment_to_allocation`: Get score from `analyze_sentiment`, map it to artificial prices, feed to `allocate_assets`.
52. `test_pairwise_rl_to_broker`: Take hypothetical output from RL model data, use it to dictate a `RealBroker.submit_order()` call.
53. `test_pairwise_allocation_to_broker`: Output weights from `allocate_assets` -> multiply by capital -> `submit_order()`.
54. `test_pairwise_broker_to_report`: Record args sent to `submit_order()` in a list, pass list to `generate_pdf_report()`.

#### Tier 4: Real-World Scenarios
55. `test_scenario_full_trade_cycle`: 
    - Text -> `analyze_sentiment`
    - Data -> `train_rl_model`
    - Prices -> `allocate_assets`
    - Loop weights -> `RealBroker.connect()` & `submit_order()`
    - Verify complete chain execution safely.
56. `test_scenario_end_of_day_reporting`:
    - Process multiple pieces of text -> `analyze_sentiment`
    - Calculate `allocate_assets`
    - Assume mock trades generated
    - Call `generate_pdf_report`
    - Verify file output.
57. `test_scenario_emergency_reallocation`:
    - Process "CRITICAL CRASH" text -> `analyze_sentiment`
    - Pass crashed prices to `allocate_assets`
    - Verify immediate defensive order generation via `RealBroker`.

## 5. Verification Method
- The Implementer should write the tests in `tests/phase3/e2e/test_e2e.py`.
- Run `pytest tests/phase3/e2e/test_e2e.py -v`.
- If the implementations for `src` modules are purely skeletons, ensure the tests gracefully handle stub responses (e.g., if a stub returns `0.0` or `{}` or simply `pass`), ensuring tests pass when stubs adhere to the type contracts from `PROJECT.md`.
