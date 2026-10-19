from datetime import datetime
from typing import Any, Dict

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    pass


class ReportGenerator:
    """백테스트 및 거래 내역 리포트 생성"""

    @staticmethod
    def generate_text_report(data: Dict[str, Any]) -> str:
        """콘솔/텍스트 리포트 생성"""
        if not data or not isinstance(data, dict):
            return "No data available for report generation."
        import math
        def _sf(v, d=0.0):
            try:
                f = float(v)
                return f if math.isfinite(f) else d
            except (ValueError, TypeError):
                return d

        lines = []
        lines.append("=" * 55)
        lines.append(f"  백테스트 리포트: {data.get('symbol', 'UNKNOWN')}")
        lines.append("=" * 55)
        lines.append(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  기간: {data.get('start_date', '')} ~ {data.get('end_date', '')}")
        lines.append(f"  초기 자본: ${_sf(data.get('initial_capital', 0)):,.0f}")
        lines.append(f"  최종 자본: ${_sf(data.get('final_capital', 0)):,.0f}")
        lines.append("-" * 55)
        lines.append("  [성과 지표]")
        lines.append(f"  총 수익률:    {data.get('total_return_pct', '0%')}")
        lines.append(f"  승률:         {data.get('win_rate', '0%')}")
        lines.append(f"  최대 낙폭:    {data.get('max_drawdown', '0%')}")
        lines.append(f"  Profit Factor: {_sf(data.get('profit_factor', 0)):.2f}")
        lines.append(f"  Sharpe Ratio:  {_sf(data.get('sharpe_ratio', 0)):.2f}")
        lines.append(f"  총 수수료:     ${_sf(data.get('total_fees', 0)):,.2f}")
        lines.append(f"  총 거래:       {int(_sf(data.get('trades_count', 0)))}건")
        lines.append("=" * 55)

        trades = data.get("trades", [])
        if trades:
            lines.append("\n  [거래 내역 (최근 10건)]")
            lines.append(f"  {'일자':<12} {'방향':<8} {'수량':<6} {'진입가':<10} {'종가':<10} {'손익':<10}")
            lines.append("  " + "-" * 56)
            for t in trades[-10:]:
                date_str = (
                    t.get("exit_date", "")[:10]
                    if isinstance(t.get("exit_date"), str)
                    else str(t.get("exit_date", ""))[:10]
                )
                pnl = t.get("pnl", 0)
                pnl_str = f"${pnl:+,.0f}" if isinstance(pnl, (int, float)) else str(pnl)
                lines.append(
                    "  {} {} {} ${:<7,.0f} ${:<7,.0f} {}".format(
                        date_str.ljust(12),
                        t.get("direction", "LONG").ljust(8),
                        str(t.get("quantity", 0)).ljust(6),
                        t.get("entry_price", 0),
                        t.get("exit_price", 0),
                        pnl_str.ljust(10),
                    )
                )
        return "\n".join(lines)

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

            c.drawString(50, y_pos, f"Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            y_pos -= 20
            c.drawString(50, y_pos, f"Test Period: {data.get('start_date', '')} ~ {data.get('end_date', '')}")
            y_pos -= 30

            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y_pos, "Performance Metrics")
            c.setFont("Helvetica", 12)
            y_pos -= 20

            metrics = [
                ("Total Return", data.get("total_return_pct", "0%")),
                ("Win Rate", data.get("win_rate", "0%")),
                ("Max Drawdown", data.get("max_drawdown", "0%")),
                ("Profit Factor", str(data.get("profit_factor", 0))),
                ("Sharpe Ratio", str(data.get("sharpe_ratio", 0))),
                ("Total Fees", f"${data.get('total_fees', 0):,.2f}"),
                ("Total Trades", str(data.get("trades_count", 0))),
            ]

            for key, val in metrics:
                c.drawString(70, y_pos, f"{key}: {val}")
                y_pos -= 20

            c.save()
            return output_path
        except Exception as e:
            print(f"PDF generation error: {e}")
            return ""

    @staticmethod
    def generate_plotly_interactive_report(data: dict, output_html_path: str = "interactive_report.html") -> str:
        """Plotly 기반 인터랙티브 HTML 리포트 생성 (HRP 자산배분 & 3D 레짐 시각화)"""
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    "HRP Portfolio Allocation (%)",
                    "Strategy Sharpe Ratios",
                    "Cumulative Portfolio Return Trend",
                    "Macro Regime Distribution"
                ),
                specs=[[{"type": "domain"}, {"type": "bar"}],
                       [{"type": "xy"}, {"type": "pie"}]]
            )

            # 1. Allocation Pie
            hrp_alloc = data.get("hrp_allocation", {"Tech": 30, "Finance": 25, "Healthcare": 20, "Cash": 25})
            fig.add_trace(
                go.Pie(labels=list(hrp_alloc.keys()), values=list(hrp_alloc.values()), name="Allocation"),
                row=1, col=1
            )

            # 2. Strategy Sharpe Ratios
            sharpes = data.get("strategy_sharpes", {"Regression": 1.2, "Surge": 1.5, "VCP_ML": 1.4, "Stat_Arb": 0.9})
            fig.add_trace(
                go.Bar(x=list(sharpes.keys()), y=list(sharpes.values()), marker_color="royalblue", name="Sharpe"),
                row=1, col=2
            )

            # 3. Cumulative Return
            returns_trend = data.get("cumulative_returns", [1.0, 1.02, 1.05, 1.04, 1.08, 1.12])
            fig.add_trace(
                go.Scatter(y=returns_trend, mode="lines+markers", name="Cumulative Return", line=dict(color="firebrick")),
                row=2, col=1
            )

            # 4. Macro Regime Distribution
            regimes = data.get("regime_distribution", {"BULL_LOW_VOL": 45, "SIDEWAYS_HIGH_VOL": 35, "BEAR_HIGH_VOL": 20})
            fig.add_trace(
                go.Pie(labels=list(regimes.keys()), values=list(regimes.values()), name="Regimes", hole=0.3),
                row=2, col=2
            )

            fig.update_layout(height=700, title_text=f"Stock Trading System Interactive Dashboard - {data.get('symbol', 'Portfolio')}", showlegend=False)
            fig.write_html(output_html_path)
            return output_html_path
        except Exception as e:
            print(f"Plotly HTML generation error: {e}")
            return ""
