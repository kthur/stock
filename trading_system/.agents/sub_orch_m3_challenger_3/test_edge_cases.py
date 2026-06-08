import os
import sys
from src.utils.report import generate_pdf_report
from src.broker.real_broker import RealBroker

def test_report_edge_cases():
    print("Testing report edge cases...")
    
    try:
        generate_pdf_report(None, "test.pdf")
        print("Report None: SUCCESS (Unexpected)")
    except Exception as e:
        print(f"Report None: FAILED with {type(e).__name__}: {e}")
        
    try:
        generate_pdf_report(["not_a_dict"], "test.pdf")
        print("Report invalid type: SUCCESS (Unexpected)")
    except Exception as e:
        print(f"Report invalid type: FAILED with {type(e).__name__}: {e}")

def test_broker_edge_cases():
    print("Testing broker edge cases...")
    broker = RealBroker()
    broker.connect()
    
    try:
        broker.submit_order("AAPL", "10", "BUY")
        print("Broker string qty: SUCCESS (Unexpected)")
    except Exception as e:
        print(f"Broker string qty: FAILED with {type(e).__name__}: {e}")
        
    try:
        broker.submit_order("AAPL", None, "BUY")
        print("Broker None qty: SUCCESS (Unexpected)")
    except Exception as e:
        print(f"Broker None qty: FAILED with {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_report_edge_cases()
    test_broker_edge_cases()
