import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))
from utils.report import generate_pdf_report

def test_newlines():
    print("Testing newlines in trade data...")
    report_path = os.path.join(os.path.dirname(__file__), "test_newlines.pdf")
    try:
        generate_pdf_report([{"symbol": "AAPL\nMSFT", "qty": 10}], report_path)
        print("WARN: Generated report with newlines. Reportlab drawString does not handle newlines properly.")
    except Exception as e:
        print(f"FAILED: Exception on newlines. {e}")

if __name__ == "__main__":
    test_newlines()
