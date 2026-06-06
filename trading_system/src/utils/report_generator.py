import os
from datetime import datetime
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    pass

class ReportGenerator:
    """백테스트 및 거래 내역의 PDF 리포트 생성기"""
    
    @staticmethod
    def generate_backtest_report(data: dict, output_path: str = "backtest_report.pdf") -> str:
        """백테스트 결과를 PDF로 저장"""
        try:
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter
            
            c.setFont("Helvetica-Bold", 20)
            c.drawString(50, height - 50, f"Backtest Report: {data.get('symbol', 'UNKNOWN')}")
            
            c.setFont("Helvetica", 12)
            y_pos = height - 100
            
            # 메타 데이터 출력
            c.drawString(50, y_pos, f"Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            y_pos -= 20
            c.drawString(50, y_pos, f"Test Period: {data.get('start_date', '')} ~ {data.get('end_date', '')}")
            y_pos -= 30
            
            # 성과 지표 출력
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y_pos, "Performance Metrics")
            c.setFont("Helvetica", 12)
            y_pos -= 20
            
            metrics = [
                ("Total Return", data.get('total_return_pct', '0%')),
                ("Win Rate", data.get('win_rate', '0%')),
                ("Max Drawdown", data.get('max_drawdown', '0%')),
                ("Profit Factor", str(data.get('profit_factor', 0))),
                ("Sharpe Ratio", str(data.get('sharpe_ratio', 0))),
                ("Total Trades", str(data.get('trades_count', 0)))
            ]
            
            for key, val in metrics:
                c.drawString(70, y_pos, f"{key}: {val}")
                y_pos -= 20
                
            c.save()
            return output_path
        except Exception as e:
            print(f"PDF generation error: {e}")
            return ""
