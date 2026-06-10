import os

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_pdf_report(trade_data: list, file_path: str):
    if trade_data is None:
        raise TypeError("trade_data cannot be None")
    if not isinstance(trade_data, list):
        raise TypeError("trade_data must be a list")
    if not file_path.endswith(".pdf"):
        raise ValueError("File path must end with .pdf")

    for trade in trade_data:
        if not isinstance(trade, dict):
            raise TypeError("Trade item must be a dictionary")
        for key in ["symbol", "qty", "price"]:
            if key not in trade:
                raise KeyError(f"Missing required key: {key}")

    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    c = canvas.Canvas(file_path, pagesize=letter)
    c.drawString(100, 750, "Trade Report")

    y = 700
    for trade in trade_data:
        text = (
            f"Symbol: {trade.get('symbol', '')}, "
            f"Qty: {trade.get('qty', 0)}, "
            f"Side: {trade.get('side', '')}, "
            f"Price: {trade.get('price', 0.0)}"
        )
        c.drawString(100, y, text)
        y -= 20

    c.save()
