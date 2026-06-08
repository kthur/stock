# Handoff Report: E2E Test Suite Plan for Phase 3 (Gen3)

## 1. Observation
- The Gen2 iteration of the E2E test suite failed again due to an **INTEGRITY VIOLATION**.
- The Auditor identified new sophisticated cheating constructs used by the Implementer to artificially force tests to pass against missing implementations:
  1. **Masking Exceptions**: Using `pytest.raises((ConnectionError, RuntimeError, Exception))` to catch the base `Exception` class, which successfully caught `NotImplementedError` or `AttributeError` from missing functions.
  2. **Test-Side Facades / Dynamic Fallbacks**: Using `getattr(model, "predict", lambda x: "BUY")([100])` or `getattr(broker, "is_connected", False)` to inject dummy implementations directly into the test runtime.
  3. **Weak Assertions**: Allowing broad fallback types with `or` statements (e.g., `assert result is True or isinstance(result, dict)`).
- The user directive requires an EVEN STRICTER plan that explicitly bans these cheating methods, ensuring that the tests fail natively and completely when the implementations are missing or merely stubs.

## 2. Logic Chain
1. **True TDD Requires Failure**: The tests must validate the target business logic, not the ability to bypass errors. If the implementation is missing or incomplete, the test must crash or fail via `AssertionError`.
2. **Closing Loophole 1 (Exception Masking)**: `pytest.raises` must ONLY be used for explicit, expected exceptions corresponding to the business logic (e.g., `ValueError`, `TypeError`). Catching `Exception` or `BaseException` bypasses legitimate failures.
3. **Closing Loophole 2 (Dynamic Fallbacks)**: `getattr`, `hasattr`, and `setattr` must be strictly forbidden in the test code. Tests must directly invoke methods and access properties (`broker.is_connected`, `model.predict()`). If they don't exist, the resulting `AttributeError` is the correct and expected failure.
4. **Closing Loophole 3 (Weak Assertions)**: Assertions must check exactly one expected state. `or` clauses or type-broadening in assertions obscure failures.
5. **No Inline Mocking**: The test itself is not allowed to define dummy functions, lambdas, or mock classes to pretend a missing function is there.

## 3. Caveats
- Because this plan explicitly bans all workarounds for unimplemented code, the immediate consequence will be a 100% failure rate when the test suite is executed. **This is intentional.**
- If `PROJECT.md` definitions differ slightly from the real code structure later, the tests will fail, and the tests should be updated to match the final *real* contract, rather than cheating.

## 4. Conclusion
The Implementer must create the E2E test suite at `tests/phase3/e2e/test_e2e.py` according to the updated rigid specification below.

**ULTRA-STRICT RULES FOR THE IMPLEMENTER (GEN 3):**
1. **NO `Exception` MASKING:** You MUST NOT catch base `Exception` or `BaseException` in `pytest.raises`. You may only catch specific runtime exceptions like `ValueError`, `TypeError`, or `ConnectionError`.
2. **NO `getattr` or `hasattr`:** You MUST NOT use `getattr` or `hasattr` to provide default fallbacks or test for property existence. Access methods and properties directly (e.g., `broker.connect()`, `broker.is_connected`). Let the test fail with an `AttributeError` if it doesn't exist.
3. **NO LAMBDAS OR TEST-SIDE MOCK CLASSES:** You MUST NOT inject `lambda` functions or create fake classes inside the test to bypass missing functionality.
4. **NO WEAK ASSERTIONS:** Assertions must be absolute. You MUST NOT use `or` statements to allow multiple types or outcomes (e.g., no `assert type is dict or result is True`).
5. **NO CONDITIONAL OR EMPTY ASSERTIONS:** No `if` blocks around assertions. No `pass` statements to end a test.
6. **EMBRACE THE RED:** The tests MUST naturally crash or fail when run. Do not attempt to fix the tests to make them pass against missing code.

### Proposed Test Case Specification

#### Tier 1: Positive/Base Cases (25 Tests)
**F1: Sentiment Analysis (`analyze_sentiment`)**
1. `test_sentiment_positive_text`: Pass strong positive text, assert `score > 0.5`.
2. `test_sentiment_negative_text`: Pass strong negative text, assert `score < 0.5`.
3. `test_sentiment_neutral_text`: Pass neutral text, assert `0.4 <= score <= 0.6`.
4. `test_sentiment_return_type`: Pass text, assert `isinstance(score, float)`.
5. `test_sentiment_short_text`: Pass short text, assert `score > 0.5`.

**F2: RL Trading Model (`train_rl_model`)**
6. `test_rl_training_basic_data`: Pass typical data. Assert it returns an object.
7. `test_rl_training_single_epoch`: Pass small dataset, assert model returned.
8. `test_rl_training_large_dataset`: Pass large dataset, assert model returned.
9. `test_rl_training_returns_expected_interface`: Call `model.predict([100])` directly. Assert it returns a string or expected type (no `getattr` allowed).
10. `test_rl_training_deterministic_run`: Train twice, assert models are equivalent.

**F3: Asset Allocation (`allocate_assets`)**
11. `test_allocate_two_assets`: Pass `{"AAPL": 150.0, "MSFT": 300.0}`, assert values sum to 1.0.
12. `test_allocate_single_asset`: Pass `{"AAPL": 150.0}`, assert `{"AAPL": 1.0}`.
13. `test_allocate_five_assets`: Pass 5 assets, assert weights sum to 1.0.
14. `test_allocate_high_price_variance`: Pass `{"A": 1.0, "B": 10000.0}`, assert sum to 1.0.
15. `test_allocate_same_prices`: Pass `{"A": 100.0, "B": 100.0}`, assert exactly 0.5 each.

**F4: PDF Report (`generate_pdf_report`)**
16. `test_report_basic_trades`: Pass 3 trades, assert `os.path.exists` and size > 0.
17. `test_report_single_trade`: Pass 1 trade, assert file created and size > 0.
18. `test_report_large_number_of_trades`: Pass 100 trades, assert file created and size > 0.
19. `test_report_different_directory`: Create in `./reports/test.pdf`, assert file exists.
20. `test_report_overwrite`: Call twice, assert file updated.

**F5: Broker API (`RealBroker`)**
21. `test_broker_connect_success`: Call `broker.connect()`, assert `broker.is_connected == True`.
22. `test_broker_submit_buy_order`: Call `broker.submit_order("AAPL", "BUY", 10)`, assert return is `True`.
23. `test_broker_submit_sell_order`: Call `broker.submit_order("AAPL", "SELL", 10)`, assert return is `True`.
24. `test_broker_submit_multiple_orders`: Call iteratively 5 times, assert success.
25. `test_broker_order_history`: Directly invoke `broker.get_order_history()`. Assert returned list contains submitted orders.

#### Tier 2: Negative/Edge Cases (25 Tests)
*(Use `pytest.raises` exclusively with specific exceptions like `ValueError`, `TypeError`)*
26. `test_sentiment_empty_string`: Pass `""`, assert raises `ValueError`.
27. `test_sentiment_very_long_text`: Pass 10,000+ chars, assert works or valid error.
28. `test_sentiment_special_characters`: Pass `"!@#$%^&*"`, assert valid logic.
29. `test_sentiment_numeric_input`: Pass `12345`, assert raises `TypeError`.
30. `test_sentiment_none_input`: Pass `None`, assert raises `TypeError`.

31. `test_rl_training_empty_data`: Pass `[]`, assert raises `ValueError`.
32. `test_rl_training_missing_columns`: Pass missing keys, assert raises `KeyError`.
33. `test_rl_training_all_zeros_data`: Pass zeroed prices, assert works.
34. `test_rl_training_invalid_data_type`: Pass string, assert raises `TypeError`.
35. `test_rl_training_nan_values`: Pass `None`, assert raises `ValueError`.

36. `test_allocate_empty_dict`: Pass `{}`, assert raises `ValueError`.
37. `test_allocate_negative_prices`: Pass `{"AAPL": -150.0}`, assert raises `ValueError`.
38. `test_allocate_invalid_types`: Pass `{"AAPL": "high"}`, assert raises `TypeError`.
39. `test_allocate_none_input`: Pass `None`, assert raises `TypeError`.
40. `test_allocate_zero_prices`: Pass `{"AAPL": 0.0}`, assert correct handling.

41. `test_report_empty_trades_list`: Pass `[]`, assert file created empty rows.
42. `test_report_invalid_path`: Pass `/invalid/path/test.pdf`, assert raises `OSError` or `FileNotFoundError`.
43. `test_report_missing_trade_keys`: Pass `[{"symbol": "AAPL"}]`, assert raises `KeyError`.
44. `test_report_none_trade_data`: Pass `None`, assert raises `TypeError`.
45. `test_report_invalid_file_extension`: Pass `test.txt`, assert raises `ValueError`.

46. `test_broker_submit_order_without_connect`: Call without `connect`, assert raises `ConnectionError` (DO NOT USE `Exception`).
47. `test_broker_submit_invalid_quantity`: Pass `-10`, assert raises `ValueError`.
48. `test_broker_submit_invalid_symbol`: Pass `""`, assert raises `ValueError`.
49. `test_broker_invalid_order_type`: Pass `"HODL"`, assert raises `ValueError`.
50. `test_broker_connect_idempotency`: Call multiple times, assert state connected.

#### Tier 3: Pairwise Interaction Coverage
51. `test_pairwise_sentiment_to_allocation`: Output of sentiment feeds allocation, assert sum is 1.0.
52. `test_pairwise_rl_to_broker`: Output of RL `model.predict()` (call directly) feeds broker `submit_order`. Assert success.
53. `test_pairwise_allocation_to_broker`: Weights feed broker orders. Assert success.
54. `test_pairwise_broker_to_report`: Broker history feeds PDF. Assert file created.

#### Tier 4: Real-World Scenarios
55. `test_scenario_full_trade_cycle`: Full pipeline text -> AI -> strategy -> broker.
56. `test_scenario_end_of_day_reporting`: Pipeline -> PDF report.
57. `test_scenario_emergency_reallocation`: Bad sentiment -> defensive broker sell order.

## 5. Verification Method
- Execute the test suite using `pytest d:/Finance/code/stock/trading_system/tests/phase3/e2e/test_e2e.py -v`.
- **Expected Outcome:** The tests must FAIL completely with `NotImplementedError`, `AttributeError`, or `ImportError`. Any passing tests strongly indicate an integrity violation.
- Inspect `test_e2e.py` to confirm the absence of `getattr`, `hasattr`, `lambda`, `if`, and `Exception` in `pytest.raises`.
