import os
from src.utils.report import generate_pdf_report

def test_generate_pdf_report_many_trades():
    trades = []
    for i in range(100):
        trades.append({"symbol": f"SYM{i}", "qty": 10, "side": "BUY", "price": 100.0})

    output_file = "test_large_report.pdf"
    if os.path.exists(output_file):
        os.remove(output_file)

    generate_pdf_report(trades, output_file)
    print("Generated large report.")

test_generate_pdf_report_many_trades()
