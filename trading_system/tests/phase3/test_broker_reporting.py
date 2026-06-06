import unittest
import os
from src.broker.real_broker import RealBroker
from src.utils.report import generate_pdf_report

class TestBrokerReporting(unittest.TestCase):
    def setUp(self):
        self.broker = RealBroker()
        self.pdf_path = "test_report.pdf"

    def tearDown(self):
        if os.path.exists(self.pdf_path):
            try:
                os.remove(self.pdf_path)
            except (PermissionError, OSError):
                pass

    def test_broker_connect(self):
        self.assertFalse(self.broker.connected)
        result = self.broker.connect()
        self.assertTrue(result)
        self.assertTrue(self.broker.connected)

    def test_broker_submit_order_without_connect(self):
        with self.assertRaises(Exception):
            self.broker.submit_order("AAPL", 10, "BUY")

    def test_broker_submit_order(self):
        self.broker.connect()
        receipt = self.broker.submit_order("AAPL", 10, "BUY")
        self.assertIn("order_id", receipt)
        self.assertEqual(receipt["symbol"], "AAPL")
        self.assertEqual(receipt["qty"], 10)
        self.assertEqual(receipt["side"], "BUY")
        self.assertEqual(receipt["status"], "FILLED")

    def test_generate_pdf_report(self):
        trade_data = [
            {"symbol": "AAPL", "qty": 10, "side": "BUY", "price": 150.0},
            {"symbol": "GOOGL", "qty": 5, "side": "SELL", "price": 2800.0}
        ]
        generate_pdf_report(trade_data, self.pdf_path)
        
        self.assertTrue(os.path.exists(self.pdf_path))
        self.assertGreater(os.path.getsize(self.pdf_path), 0)
        
        # Verify it's a valid PDF by checking the header
        with open(self.pdf_path, 'rb') as f:
            header = f.read(5)
            self.assertEqual(header, b'%PDF-')

if __name__ == '__main__':
    unittest.main()
