import sys
import os

# Add src to path
sys.path.append(os.path.abspath('d:/Finance/code/stock/trading_system/'))
from src.utils.report import generate_pdf_report

long_symbol = "A" * 150
trade_data = [{"symbol": long_symbol, "qty": 100, "side": "BUY"}]
generate_pdf_report(trade_data, "long_text_report.pdf")
print("Long text PDF generated.")
