# Handoff Report: E2E Test Suite Plan for Phase 3 (Gen2)

## 1. Observation
- The previous iteration of the E2E test suite was rejected due to an **INTEGRITY VIOLATION**.
- The Auditor identified that the tests were a facade. The implementer used conditional assertions (`if score is not None:`), empty assertions (`pass`), and broad exception masking (`try...except Exception: pass`) to artificially pass the tests against unimplemented or stubbed code.
- This failure originated from a flawed instruction in the previous Explorer's plan: *"ensure the tests gracefully handle stub responses... ensuring tests pass when stubs adhere to the type contracts"*.
- The user directive requires a new plan that explicitly enforces that the next Worker MUST write real, failing assertions for missing features. The tests must genuinely assert expected behavior and MUST FAIL if the implementations are missing or returning stubs.

## 2. Logic Chain
1. **True TDD Approach**: Tests must validate the actual expected business logic. Since the implementation does not exist yet, the tests **must fail**. This is correct and expected in a Test-Driven Development environment.
2. **Eliminating Bypasses**: 
   - Conditional logic to skip assertions based on the return value is strictly prohibited.
   - Using `pass` instead of an assertion is strictly prohibited.
   - Catching exceptions with `except Exception: pass` is strictly prohibited.
3. **Assertion Strictness**:
   - If `analyze_sentiment` is expected to return a positive score for positive text, the test must contain an unconditional `assert score > 0.5`. If the function returns a stub of `0.0` or `None`, the test will appropriately fail.
   - Negative tests (testing for errors) must use `pytest.raises(SpecificException)` instead of masking exceptions.
4. **Test Structure**: The 5-feature inventory and Tier 1-4 coverage requirements remain valid and will be structurally maintained from the previous plan, but with strict implementation guidelines.

## 3. Caveats
- The original interface specifications (`PROJECT.md`) dictate the data types. If those interfaces differ from the assumptions made here, the tests will fail, which is the expected behavior until the implementation aligns with the tests.
- Because the tests are meant to fail on unwritten features, the overall suite run will show 100% failure initially. This is not an error; it is the objective.

## 4. Conclusion
The Implementer must create the E2E test suite at `tests/phase3/e2e/test_e2e.py` according to the exact test cases below.

**CRITICAL RULES FOR THE IMPLEMENTER:**
1. **NO CONDITIONAL ASSERTIONS:** You must not use `if result is not None:` or `if len(result) > 0:` to wrap assertions. Assertions must be unconditional.
2. **NO EMPTY ASSERTIONS:** Every test must contain at least one real `assert` statement that validates the business logic (or a `pytest.raises` block). You may not use `pass` to conclude a test.
3. **NO EXCEPTION MASKING:** You must not use `try...except Exception: pass`. If an exception is expected, use `with pytest.raises(ExpectedExceptionClass):`.
4. **EMBRACE THE RED:** The tests MUST FAIL when run against missing or stubbed implementations. Do not attempt to make the tests pass. Your job is purely to write the strict, rigid test logic.

### Proposed Test Case Specification

#### Tier 1: Positive/Base Cases (25 Tests)
**F1: Sentiment Analysis (`analyze_sentiment`)**
1. `test_sentiment_positive_text`: Pass strong positive text ("Incredible profits!"), assert score > 0.5.
2. `test_sentiment_negative_text`: Pass strong negative text ("Terrible losses."), assert score < 0.5.
3. `test_sentiment_neutral_text`: Pass neutral text ("The sky is blue."), assert 0.4 <= score <= 0.6.
4. `test_sentiment_return_type`: Pass typical text, assert `isinstance(score, float)`.
5. `test_sentiment_short_text`: Pass "Good", assert score > 0.5.

**F2: RL Trading Model (`train_rl_model`)**
6. `test_rl_training_basic_data`: Pass typical list of dictionaries with price data. Assert it returns a trained model object (not None).
7. `test_rl_training_single_epoch`: Pass a small valid dataset, assert completion and non-None model.
8. `test_rl_training_large_dataset`: Pass large valid dataset, assert model returned.
9. `test_rl_training_returns_expected_interface`: Assert the returned model has a `predict` method (or similar expected interface per `PROJECT.md`).
10. `test_rl_training_deterministic_run`: Assert training twice with identical data/seed produces identical or structurally equivalent models.

**F3: Asset Allocation (`allocate_assets`)**
11. `test_allocate_two_assets`: Pass `{"AAPL": 150.0, "MSFT": 300.0}`, assert return dict keys match and values sum to 1.0.
12. `test_allocate_single_asset`: Pass `{"AAPL": 150.0}`, assert return `{"AAPL": 1.0}`.
13. `test_allocate_five_assets`: Pass 5 valid assets, assert 5 returned weights sum to 1.0.
14. `test_allocate_high_price_variance`: Pass `{"A": 1.0, "B": 10000.0}`, assert weights sum to 1.0.
15. `test_allocate_same_prices`: Pass `{"A": 100.0, "B": 100.0}`, assert weights are exactly 0.5 each.

**F4: PDF Report (`generate_pdf_report`)**
16. `test_report_basic_trades`: Pass 3 valid trades and path `./test_report_basic.pdf`. Assert `os.path.exists` is True and file size > 0.
17. `test_report_single_trade`: Pass 1 trade, assert file created and size > 0.
18. `test_report_large_number_of_trades`: Pass 100 trades, assert file created and size > 0.
19. `test_report_different_directory`: Create in `./reports/test.pdf`, assert file exists.
20. `test_report_overwrite`: Call twice on same path, assert file exists and updated modification time or size.

**F5: Broker API (`RealBroker`)**
21. `test_broker_connect_success`: Call `broker.connect()`, assert `broker.is_connected` is True.
22. `test_broker_submit_buy_order`: Call `broker.submit_order("AAPL", "BUY", 10)`, assert return status is success/True.
23. `test_broker_submit_sell_order`: Call `broker.submit_order("AAPL", "SELL", 10)`, assert return status is success/True.
24. `test_broker_submit_multiple_orders`: Call `submit_order` iteratively 5 times, assert success for all.
25. `test_broker_order_history`: Assert submitted orders appear in `broker.get_order_history()` or similar state property.

#### Tier 2: Negative/Edge Cases (25 Tests)
*(Note: Use `pytest.raises` for expected exceptions.)*
**F1: Sentiment Analysis**
26. `test_sentiment_empty_string`: Pass `""`, assert it raises `ValueError`.
27. `test_sentiment_very_long_text`: Pass 10,000+ char string, assert expected score calculation or valid error.
28. `test_sentiment_special_characters`: Pass `"!@#$%^&*"`, assert appropriate handling (e.g. neutral score).
29. `test_sentiment_numeric_input`: Pass numeric `12345`, assert raises `TypeError`.
30. `test_sentiment_none_input`: Pass `None`, assert raises `TypeError` or `ValueError`.

**F2: RL Trading Model**
31. `test_rl_training_empty_data`: Pass `[]` or `{}`, assert raises `ValueError`.
32. `test_rl_training_missing_columns`: Pass data missing required keys, assert raises `KeyError` or `ValueError`.
33. `test_rl_training_all_zeros_data`: Pass zeroed prices, assert model trains but handles it correctly.
34. `test_rl_training_invalid_data_type`: Pass a string instead of a data structure, assert raises `TypeError`.
35. `test_rl_training_nan_values`: Pass `NaN` or `None` within the dataset, assert raises `ValueError`.

**F3: Asset Allocation**
36. `test_allocate_empty_dict`: Pass `{}`, assert raises `ValueError`.
37. `test_allocate_negative_prices`: Pass `{"AAPL": -150.0}`, assert raises `ValueError`.
38. `test_allocate_invalid_types`: Pass `{"AAPL": "high"}`, assert raises `TypeError`.
39. `test_allocate_none_input`: Pass `None`, assert raises `TypeError`.
40. `test_allocate_zero_prices`: Pass `{"AAPL": 0.0}`, assert handles appropriately (e.g., skips or raises `ValueError`).

**F4: PDF Report**
41. `test_report_empty_trades_list`: Pass `[]`, assert file created with headers but no rows.
42. `test_report_invalid_path`: Pass `/invalid/path/test.pdf` (Unix) or `Z:\invalid\test.pdf` (Win), assert raises `FileNotFoundError` or `OSError`.
43. `test_report_missing_trade_keys`: Pass `[{"symbol": "AAPL"}]` (missing qty/price), assert raises `KeyError` or `ValueError`.
44. `test_report_none_trade_data`: Pass `None`, assert raises `TypeError` or `ValueError`.
45. `test_report_invalid_file_extension`: Pass `test.txt`, assert raises `ValueError`.

**F5: Broker API**
46. `test_broker_submit_order_without_connect`: Call `submit_order` before `connect()`, assert raises `ConnectionError` or `RuntimeError`.
47. `test_broker_submit_invalid_quantity`: Pass `-10` or `0`, assert raises `ValueError`.
48. `test_broker_submit_invalid_symbol`: Pass `""` or `None`, assert raises `ValueError`.
49. `test_broker_invalid_order_type`: Pass `"HODL"`, assert raises `ValueError`.
50. `test_broker_connect_idempotency`: Call `connect()` multiple times, assert no exception and state remains connected.

#### Tier 3: Pairwise Interaction Coverage
51. `test_pairwise_sentiment_to_allocation`: Get score from `analyze_sentiment`, manually map to price input, feed to `allocate_assets`, assert sum is 1.0.
52. `test_pairwise_rl_to_broker`: Pass mock data to `train_rl_model`, use output to decide a `broker.submit_order()`, assert order succeeds.
53. `test_pairwise_allocation_to_broker`: Take weights from `allocate_assets`, generate order amounts, assert `broker.submit_order()` succeeds.
54. `test_pairwise_broker_to_report`: Pass `broker.submit_order()` results to `generate_pdf_report()`, assert file creation and valid size.

#### Tier 4: Real-World Scenarios
55. `test_scenario_full_trade_cycle`: 
    - Text -> `analyze_sentiment`
    - Data -> `train_rl_model`
    - Prices -> `allocate_assets`
    - Loop weights -> `broker.connect()` & `submit_order()`
    - Verify complete chain execution. Assert `broker.get_order_history()` has entries.
56. `test_scenario_end_of_day_reporting`:
    - Process multiple pieces of text -> `analyze_sentiment`
    - `allocate_assets` -> create mock trades
    - Call `generate_pdf_report`. Assert file output exists.
57. `test_scenario_emergency_reallocation`:
    - Process "CRITICAL CRASH" -> `analyze_sentiment` -> yields low score
    - Update prices -> `allocate_assets`
    - Assert reallocation leads to defensive `submit_order` (e.g. SELLs).

## 5. Verification Method
- Execute the test suite using `pytest d:/Finance/code/stock/trading_system/tests/phase3/e2e/test_e2e.py -v`.
- **Expected Outcome:** The vast majority, if not all, tests MUST FAIL with `AssertionError` or unhandled exceptions because the underlying features are not yet fully implemented.
- Inspect `test_e2e.py` code to verify no conditional assertions (`if ... is not None:`), no bare `pass` statements within tests, and no catch-all exception blocks (`except Exception: pass`) exist.
