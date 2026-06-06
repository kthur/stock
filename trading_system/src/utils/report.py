import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def generate_pdf_report(trade_data: list, file_path: str):
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    c = canvas.Canvas(file_path, pagesize=letter)
    c.drawString(100, 750, "Trade Report")
    
    y = 700
    for trade in trade_data:
        text = f"Symbol: {trade.get('symbol', '')}, Qty: {trade.get('qty', 0)}, Side: {trade.get('side', '')}, Price: {trade.get('price', 0.0)}"
        c.drawString(100, y, text)
        y -= 20
        
    c.save()
