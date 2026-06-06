# Handoff Report: Phase 3 Broker Reporting Investigation

## 1. Observation
- **Missing Dependency**: Viewed `requirements.txt` (via `view_file` tool). `reportlab` is not listed among the dependencies.
- **Flaky Test Teardown**: Examined `tests/phase3/test_broker_reporting.py` (lines 11-14). The `tearDown` method calls `os.remove(self.pdf_path)` which on Windows will throw a `PermissionError` if the file is still open (e.g., if a previous test or implementation leaves a file handle open).
- **Robustness (RealBroker)**: Examined `src/broker/real_broker.py` (lines 13-24). The `submit_order` method does not validate the `qty` or `side` parameters before proceeding to generate the receipt.
- **Robustness (generate_pdf_report)**: Examined `src/utils/report.py` (lines 1-3). `generate_pdf_report` is currently just a `pass` stub and lacks logic to ensure the destination directory exists before attempting to write a file.

## 2. Logic Chain
1.  **Missing Dependency**: Without `reportlab`, any future implementation of PDF generation will fail with an `ImportError`. Therefore, it must be appended to `requirements.txt`.
2.  **Flaky Test Teardown**: Windows locks open files, causing `os.remove()` to raise a `PermissionError`. By wrapping the removal in a `try...except PermissionError: pass` block, the test teardown can complete gracefully even if a file handle wasn't cleanly closed.
3.  **Robustness (RealBroker)**: Invalid inputs like negative quantity or an invalid side (e.g., "HOLD", "INVALID") could propagate deeper into the system. Throwing a `ValueError` for `qty <= 0` or `side not in ("BUY", "SELL")` at the beginning of `submit_order` prevents this.
4.  **Robustness (generate_pdf_report)**: If `file_path` contains a directory that doesn't exist (e.g., `reports/trade_report.pdf`), writing to it will raise a `FileNotFoundError`. Extracting the directory using `os.path.dirname(file_path)` and calling `os.makedirs(directory, exist_ok=True)` (only if `directory` is not empty) handles this.

## 3. Caveats
- `generate_pdf_report` is completely empty (contains only `pass`). The fix strategy addresses the directory creation requirement, but the actual PDF generation logic with `reportlab` is still needed.
- Catching `PermissionError` in `tearDown` masks the symptom of unclosed file handles. While it fixes the flakiness, the root cause (not closing files) should ideally be avoided in the implementation.

## 4. Conclusion
The failure points identified in the challenge feedback are confirmed. The following fixes should be implemented:

1.  **Append `reportlab` to `requirements.txt`**: Add `reportlab>=4.0.0` (or similar).
2.  **Modify `tests/phase3/test_broker_reporting.py`**:
    ```python
    def tearDown(self):
        if os.path.exists(self.pdf_path):
            try:
                os.remove(self.pdf_path)
            except PermissionError:
                pass
    ```
3.  **Modify `src/broker/real_broker.py`** (`submit_order`):
    ```python
    def submit_order(self, symbol: str, qty: float, side: str) -> dict:
        if not self.connected:
            raise Exception("Broker not connected.")
        if qty <= 0:
            raise ValueError("Quantity must be greater than 0.")
        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be 'BUY' or 'SELL'.")
        # ... rest of function
    ```
4.  **Modify `src/utils/report.py`** (`generate_pdf_report`):
    ```python
    import os
    def generate_pdf_report(trade_data: list, file_path: str):
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        # implementation...
    ```

## 5. Verification Method
1.  Verify dependency: `pip install -r requirements.txt` succeeds and installs `reportlab`.
2.  Verify tests: Run `python -m unittest tests/phase3/test_broker_reporting.py`. It should not fail during `tearDown` with a `PermissionError`.
3.  Verify RealBroker: Add explicit tests in `test_broker_reporting.py` to assert `ValueError` is raised for invalid `qty` and `side`.
4.  Verify PDF generation: Add a test calling `generate_pdf_report` with a nested path (e.g., `temp_dir/report.pdf`) and assert the directory is created successfully.
