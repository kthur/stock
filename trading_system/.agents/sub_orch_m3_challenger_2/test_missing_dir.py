import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))
from utils.report import generate_pdf_report

def test_missing_dir():
    print("Testing missing directory...")
    report_path = os.path.join(os.path.dirname(__file__), "nonexistent_dir", "test_dir.pdf")
    try:
        generate_pdf_report([{"symbol": "AAPL", "qty": 10}], report_path)
        print("FAILED: Created missing directory successfully (wait, this is a pass if we expect it, but standard reportlab doesn't).")
    except Exception as e:
        print(f"PASSED: Exception on missing directory. {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_missing_dir()
