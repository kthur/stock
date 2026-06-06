import sys
import os

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))

from broker.real_broker import RealBroker
from utils.report import generate_pdf_report
import traceback

def test_broker():
    print("--- Testing RealBroker ---")
    broker = RealBroker()
    broker.connect()
    
    try:
        # Negative quantity
        res = broker.submit_order("AAPL", -10.0, "BUY")
        print(f"FAILED: Allowed negative quantity. Result: {res}")
    except Exception as e:
        print(f"PASSED: Negative quantity rejected. {e}")

    try:
        # Invalid side
        res = broker.submit_order("AAPL", 10.0, "HOLD")
        print(f"FAILED: Allowed invalid side 'HOLD'. Result: {res}")
    except Exception as e:
        print(f"PASSED: Invalid side rejected. {e}")

    try:
        # Zero quantity
        res = broker.submit_order("AAPL", 0, "BUY")
        print(f"FAILED: Allowed zero quantity. Result: {res}")
    except Exception as e:
        print(f"PASSED: Zero quantity rejected. {e}")

def test_report():
    print("\n--- Testing generate_pdf_report ---")
    report_path = os.path.join(os.path.dirname(__file__), "test_report.pdf")
    
    # 1. Extremely long string (no text wrapping)
    long_str = "A" * 200
    try:
        generate_pdf_report([{"symbol": long_str, "qty": 10}], report_path)
        print("WARN: Generated report with extremely long string (check visually for cutoff).")
    except Exception as e:
        print(f"ERROR: Failed on long string. {e}")
        
    # 2. Special characters/Unicode
    try:
        generate_pdf_report([{"symbol": "한글/🚀/테스트", "qty": 10}], report_path)
        print("WARN: Generated report with unicode (check if font supports it, reportlab default Helvetica usually doesn't and raises error).")
    except Exception as e:
        print(f"PASSED: Exception on unsupported font characters. {e}")

    # 3. Invalid file path (directory)
    try:
        generate_pdf_report([{"symbol": "AAPL"}], os.path.dirname(__file__))
        print("FAILED: Allowed writing to a directory path instead of a file.")
    except Exception as e:
        print(f"PASSED: Handled invalid file path. {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_broker()
    test_report()
