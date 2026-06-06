import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))
from utils.report import generate_pdf_report

def test_pagination():
    print("Testing pagination with 10,000 trades...")
    report_path = os.path.join(os.path.dirname(__file__), "test_pagination.pdf")
    data = [{"symbol": f"SYM{i}", "qty": 10} for i in range(10000)]
    try:
        generate_pdf_report(data, report_path)
        print("PASSED: Handled 10,000 trades.")
    except Exception as e:
        print(f"FAILED: Exception on large trade data. {e}")

if __name__ == "__main__":
    test_pagination()
