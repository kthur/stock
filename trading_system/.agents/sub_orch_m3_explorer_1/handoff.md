# Handoff Report - Milestone 3 Strategy

## Observation
- **Requirements**: `PROJECT.md` and `SCOPE.md` require implementing `RealBroker` with `connect()` and `submit_order()`, and a PDF generation function from mock trade data (`generate_pdf_report`). 
- **Target Files**: `src/broker/real_broker.py`, `src/utils/report.py`, and `tests/phase3/test_broker_reporting.py`.
- **Environment Context**:
  - `src/broker` directory does not currently exist and must be created.
  - `reportlab` is installed and available for PDF generation.
  - `pytest` is not available, but `unittest` is used for existing tests (`tests/test_system.py`).

## Logic Chain
1. **`src/broker/real_broker.py`**:
   - Create the directory `src/broker`.
   - Implement `RealBroker` class containing `__init__` (to manage connection state), `connect()` (to mock API connection establishment), and `submit_order(symbol, order_type, quantity, price)` (to mock an order submission returning a status dict).
2. **`src/utils/report.py`**:
   - Implement `generate_pdf_report(trade_data: list, file_path: str)`.
   - Use `reportlab.pdfgen.canvas` to create a basic PDF. It will iterate over `trade_data` (expected to be a list of dicts with keys like 'symbol', 'price', 'quantity', 'status') and draw strings onto the document, saving it to `file_path`.
3. **`tests/phase3/test_broker_reporting.py`**:
   - Use `unittest` framework to ensure consistency.
   - Test `RealBroker` connection state and order submission returns.
   - Test `generate_pdf_report` by providing mock trade data, verifying the `.pdf` file is created on the disk, and then cleaning up the generated file.

## Caveats
- The `RealBroker` implementation is a mock skeleton for Milestone 3. Actual broker API logic (e.g., Kiwoom or Korea Investment) will be required later.
- The `generate_pdf_report` implementation will be basic. Handling multi-page pagination for very large `trade_data` lists might be necessary for production, but a simple list rendering will suffice for the milestone.

## Conclusion
A full strategy is ready to implement Milestone 3. The implementation focuses on building the skeletons and mock data processing for `RealBroker` and PDF reporting, verifiable through `unittest` test suites.

## Verification Method
Run the following command after implementation:
`python -m unittest tests/phase3/test_broker_reporting.py`
The output should indicate that all tests pass and no dangling test files remain.
