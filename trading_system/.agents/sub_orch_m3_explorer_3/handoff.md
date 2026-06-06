# Handoff Report: Milestone 3 (Broker & Reporting) Strategy

## Observation
- `PROJECT.md` and `SCOPE.md` outline Milestone 3 requirements: implementing a `RealBroker` interface with `connect()` and `submit_order()` methods, and a PDF generation function `generate_pdf_report(trade_data: list, file_path: str)`.
- The target files for implementation are:
  - `src/broker/real_broker.py`
  - `src/utils/report.py`
  - `tests/phase3/test_broker_reporting.py`
- A review of `requirements.txt` reveals no PDF generation libraries (such as `reportlab` or `fpdf`) are currently installed.

## Logic Chain
1. **`src/broker/real_broker.py` Strategy**:
   - Define a `RealBroker` class.
   - Implement `connect(self) -> bool` to simulate establishing a connection (e.g., returning `True` and setting an internal connected flag).
   - Implement `submit_order(self, symbol: str, qty: int, side: str) -> dict` to simulate placing a dummy order, returning a mock receipt/status.
2. **`src/utils/report.py` Strategy**:
   - Define `generate_pdf_report(trade_data: list, file_path: str)`.
   - Given the lack of a PDF library in `requirements.txt`, the simplest approach to fulfill the Acceptance Criteria is to mock the PDF generation by writing string representations of the `trade_data` directly to the `file_path`.
   - Alternatively, the implementer can choose to add a lightweight library like `fpdf2` or `reportlab` to `requirements.txt` if a proper PDF file format is strictly required. For a mock milestone, a dummy text-based `.pdf` file is typically acceptable.
3. **`tests/phase3/test_broker_reporting.py` Strategy**:
   - Write a test `test_real_broker_connect()` to verify that `connect()` sets the expected state or returns `True`.
   - Write a test `test_real_broker_submit_order()` to assert that an order given dummy parameters returns a successful receipt.
   - Write a test `test_generate_pdf_report(tmp_path)` using `pytest`'s temporary directory fixture. Pass mock `trade_data` to the function, generate the PDF in the temporary path, and assert that `os.path.exists(file_path)` is `True` and the file is not empty.

## Caveats
- The `RealBroker` implementation will be a mock. No actual broker API (e.g., Kiwoom or Korea Investment) credentials or endpoints are provided.
- The structure/format of the generated PDF is undefined. The strategy assumes a minimal mock representation is sufficient unless instructed otherwise.

## Conclusion
The implementer should proceed with creating the class structure for `RealBroker`, a basic file-writing stub for `generate_pdf_report`, and comprehensive unit tests checking the mocked behavior and file creation.

## Verification Method
- Execute `pytest tests/phase3/test_broker_reporting.py` to independently verify the broker logic and report generation. The tests should pass and confirm the file is created on the filesystem.
