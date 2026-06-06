import sys
import os
import datetime
import traceback
import uuid

# Add src to path
sys.path.append(os.path.abspath('d:/Finance/code/stock/trading_system/'))

from src.broker.real_broker import RealBroker
from src.utils.report import generate_pdf_report

def test_broker_validation():
    print("--- Testing RealBroker ---")
    broker = RealBroker()
    
    # 1. Connection check
    try:
        broker.submit_order("AAPL", 10.0, "BUY")
        print("FAIL: submit_order succeeded without connect()")
    except Exception as e:
        print(f"PASS: submit_order failed without connect(): {e}")

    broker.connect()
    
    # 2. Invalid inputs
    try:
        # Extreme quantity
        res = broker.submit_order("AAPL", -100, "BUY")
        print(f"WARN: submit_order succeeded with negative qty: {res}")
    except Exception as e:
        print(f"PASS: Negative qty handled: {e}")

    try:
        # Invalid side
        res = broker.submit_order("AAPL", 10, "INVALID_SIDE")
        print(f"WARN: submit_order succeeded with invalid side: {res}")
    except Exception as e:
        print(f"PASS: Invalid side handled: {e}")


def test_pdf_report():
    print("\n--- Testing generate_pdf_report ---")
    
    # 1. Empty data
    try:
        generate_pdf_report([], "empty_report.pdf")
        print("PASS: Empty trade_data handled.")
    except Exception as e:
        print(f"FAIL: Empty trade_data failed: {e}")
        
    # 2. Missing/Invalid fields
    try:
        bad_data = [{"symbol": "AAPL"}, "not a dict"]
        generate_pdf_report(bad_data, "bad_data_report.pdf")
        print("WARN: Invalid trade data types succeeded?")
    except AttributeError as e:
        print(f"PASS: Expected AttributeError on invalid trade dict: {e}")
    except Exception as e:
        print(f"FAIL: Unexpected error on invalid trade dict: {e}")

    # 3. Unicode/Korean Text
    try:
        unicode_data = [{"symbol": "삼성전자", "qty": 100, "side": "BUY"}]
        generate_pdf_report(unicode_data, "unicode_report.pdf")
        print("WARN: Unicode text succeeded. Check if PDF actually renders correctly.")
    except Exception as e:
        print(f"FAIL: Unicode text failed with error: {type(e).__name__}: {e}")

    # 4. Large trade data
    try:
        large_data = []
        for i in range(20000):
            large_data.append({"order_id": str(uuid.uuid4()), "symbol": "AAPL", "qty": 1.0, "side": "BUY"})
        
        start = datetime.datetime.now()
        generate_pdf_report(large_data, "large_report.pdf")
        duration = (datetime.datetime.now() - start).total_seconds()
        print(f"PASS: Large trade data (20,000 items) handled in {duration}s")
    except Exception as e:
        print(f"FAIL: Large trade data failed: {e}")

if __name__ == "__main__":
    test_broker_validation()
    test_pdf_report()
