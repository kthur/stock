import sys
import os

# Append the current working directory to sys.path
sys.path.insert(0, os.getcwd())

from src.utils.report import generate_pdf_report
from src.broker.real_broker import RealBroker

def test_pagination_bug():
    print("Testing pagination bug...")
    trade_data = [{"symbol": f"SYM{i}", "qty": 10, "side": "BUY", "price": 100} for i in range(50)]
    pdf_path = os.path.join(os.getcwd(), ".agents", "sub_orch_m3_challenger_4", "test_pagination.pdf")
    generate_pdf_report(trade_data, pdf_path)
    print(f"Generated {pdf_path}. Check if it has 1 page and text is cut off.")

def test_missing_price_in_receipt():
    print("Testing missing price in receipt...")
    broker = RealBroker()
    broker.connect()
    receipt = broker.submit_order("AAPL", 10, "BUY")
    print(f"Receipt: {receipt}")
    if "price" not in receipt:
        print("Bug: 'price' is missing from the order receipt.")

def test_no_balance_update():
    print("Testing balance update...")
    broker = RealBroker()
    broker.connect()
    initial_balance = broker.get_balance()["cash"]
    broker.submit_order("AAPL", 10, "BUY")
    final_balance = broker.get_balance()["cash"]
    print(f"Initial: {initial_balance}, Final: {final_balance}")
    if initial_balance == final_balance:
        print("Bug: Balance is not updated after submitting an order.")

def test_side_validation():
    print("Testing side validation...")
    broker = RealBroker()
    broker.connect()
    try:
        broker.submit_order("AAPL", 10, "buy")  # Lowercase
        print("Bug: side validation is case-sensitive but does not convert or accept lowercase.")
    except ValueError as e:
        print(f"Caught ValueError: {e}")

if __name__ == "__main__":
    test_pagination_bug()
    test_missing_price_in_receipt()
    test_no_balance_update()
    test_side_validation()
