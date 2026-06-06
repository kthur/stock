# Observation
- Requirements stated `reportlab` should be appended to `requirements.txt`.
- `tests/phase3/test_broker_reporting.py` needed exception handling for `PermissionError` and `OSError` in the `tearDown` method.
- `src/broker/real_broker.py` needed validation for `qty` (>0) and `side` ("BUY", "SELL").
- `src/utils/report.py` required creating target directories and generating genuine PDFs using `reportlab`.

# Logic Chain
- Editing `requirements.txt` adds `reportlab` as a dependency.
- Adding a `try-except` block in `test_broker_reporting.py` ensures the testing process continues even if file cleanup fails (e.g. if the file is locked).
- Adding validation checks (`qty <= 0`, `side not in ["BUY", "SELL"]`) in `submit_order` ensures valid input data before processing mock orders.
- Modifying `generate_pdf_report` allows it to create directories using `os.makedirs` and a `Canvas` object from `reportlab` ensuring actual PDF structures are written, satisfying integrity requirements.
- Executing `python -m unittest tests.phase3.test_broker_reporting` tests these changes.

# Caveats
No caveats.

# Conclusion
The trading system phase 3 fixes are successfully implemented as requested, avoiding facade implementations and ensuring the use of `reportlab` for valid `.pdf` outputs. 

# Verification Method
Run `python -m unittest tests.phase3.test_broker_reporting` from the project root `d:/Finance/code/stock/trading_system`. Verify `requirements.txt` contains `reportlab`. Verify `generate_pdf_report` functions and `test_report.pdf` has the `%PDF-` header.
