"""
PDF Report Generator for trading system backtest results and trade journals.
Uses ReportLab for PDF generation.
"""

import datetime
import os
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ─── Colour palette ──────────────────────────────────────────────────────────
PRIMARY_DARK = colors.HexColor("#1a2744")  # navy
PRIMARY_LIGHT = colors.HexColor("#2d5016")  # dark green (profit)
ACCENT_RED = colors.HexColor("#c0392b")  # loss red
ACCENT_BLUE = colors.HexColor("#2980b9")  # header blue
TABLE_HEADER = colors.HexColor("#2c3e50")
ROW_ALT = colors.HexColor("#ecf0f1")
BORDER = colors.HexColor("#bdc3c7")


def _build_styles():
    """Build and return a dict of Paragraph styles."""
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "TitleStyle",
            parent=base["Title"],
            fontSize=22,
            textColor=PRIMARY_DARK,
            spaceAfter=4,
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleStyle",
            parent=base["Normal"],
            fontSize=11,
            textColor=colors.grey,
            spaceAfter=14,
            alignment=TA_CENTER,
        ),
        "section_header": ParagraphStyle(
            "SectionHeader",
            parent=base["Heading2"],
            fontSize=13,
            textColor=PRIMARY_DARK,
            spaceBefore=14,
            spaceAfter=6,
            borderPad=2,
        ),
        "normal": ParagraphStyle(
            "NormalStyle",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.black,
        ),
        "small": ParagraphStyle(
            "SmallStyle",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.grey,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.white,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.black,
        ),
    }
    return styles


def _metrics_table(data: dict, styles: dict) -> Table:
    """Build the performance metrics table."""
    import math
    def _to_int(v, d=0):
        try:
            f = float(v)
            return int(f) if math.isfinite(f) else d
        except (ValueError, TypeError):
            return d

    init_cap = _to_int(data.get("initial_capital", 0))
    fin_cap = _to_int(data.get("final_capital", 0))
    tot_fees = _to_int(data.get("total_fees", 0))

    rows = [
        ["Metric", "Value"],
        ["Symbol", str(data.get("symbol", "N/A"))],
        ["Period", f"{data.get('start_date', '?')} → {data.get('end_date', '?')}"],
        ["Initial Capital", f"₩{init_cap:,}"],
        ["Final Capital", f"₩{fin_cap:,}"],
        ["Total Return", str(data.get("total_return_pct", "N/A"))],
        ["Win Rate", str(data.get("win_rate", "N/A"))],
        ["Max Drawdown", str(data.get("max_drawdown", "N/A"))],
        ["Profit Factor", str(data.get("profit_factor", "N/A"))],
        ["Sharpe Ratio", str(data.get("sharpe_ratio", "N/A"))],
        ["Total Fees", f"₩{tot_fees:,}"],
        ["Total Trades", str(data.get("trades_count", "N/A"))],
    ]

    col_widths = [7 * cm, 8 * cm]
    tbl = Table(rows, colWidths=col_widths)
    tbl.setStyle(
        TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                # Data rows
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                # Grid
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return tbl


def _trades_table(trades: List[dict], styles: dict) -> Optional[Table]:
    """Build the trade list table. Returns None if no trades."""
    if not trades:
        return None

    header = ["Date", "Direction", "Qty", "Entry", "Exit", "P&L"]
    rows = [header]

    for trade in trades:
        pnl = trade.get("pnl", 0)
        pnl_str = f"₩{int(pnl):+,}"
        rows.append(
            [
                str(trade.get("exit_date", "?")),
                str(trade.get("direction", "?")),
                str(trade.get("quantity", "?")),
                f"₩{int(trade.get('entry_price', 0)):,}",
                f"₩{int(trade.get('exit_price', 0)):,}",
                pnl_str,
            ]
        )

    col_widths = [3 * cm, 2.5 * cm, 2 * cm, 3 * cm, 3 * cm, 3 * cm]
    tbl = Table(rows, colWidths=col_widths)

    # Build per-row styles for P&L colouring
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    # Colour P&L column by profit/loss
    for row_idx, trade in enumerate(trades, start=1):
        pnl = trade.get("pnl", 0)
        col = PRIMARY_LIGHT if pnl >= 0 else ACCENT_RED
        style_cmds.append(("TEXTCOLOR", (5, row_idx), (5, row_idx), col))

    tbl.setStyle(TableStyle(style_cmds))
    return tbl


# ─── PDFReportGenerator class ─────────────────────────────────────────────────


class PDFReportGenerator:
    """Generates PDF reports for backtest results and trade journals."""

    def __init__(self, page_size=letter):
        self.page_size = page_size
        self._styles = _build_styles()

    # ------------------------------------------------------------------
    def generate_report(self, data: dict, output_path: str) -> str:
        """
        Generate a backtest report PDF.

        Args:
            data: Backtest results dict (see generate_backtest_pdf for keys).
            output_path: Absolute path for the output PDF file.

        Returns:
            output_path on success.
        """
        return generate_backtest_pdf(data, output_path)

    # ------------------------------------------------------------------
    def generate_trade_journal(self, trades: List[dict], output_path: str) -> str:
        """
        Generate a trade journal PDF listing all trades.

        Args:
            trades: List of trade dicts with keys:
                    exit_date, direction, quantity, entry_price, exit_price, pnl
            output_path: Absolute path for the output PDF file.

        Returns:
            output_path on success.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=self.page_size,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = self._styles
        story = []

        # Title
        story.append(Paragraph("Trade Journal", styles["title"]))
        story.append(
            Paragraph(
                f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                styles["subtitle"],
            )
        )
        story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_BLUE, spaceAfter=12))

        story.append(Paragraph(f"Total Trades: {len(trades)}", styles["normal"]))
        story.append(Spacer(1, 8))

        tbl = _trades_table(trades, styles)
        if tbl:
            story.append(tbl)
        else:
            story.append(Paragraph("No trades to display.", styles["normal"]))

        doc.build(story)
        return output_path


# ─── Top-level function ───────────────────────────────────────────────────────


def generate_backtest_pdf(data: dict, output_path: str = "report.pdf") -> str:
    """
    Generate a comprehensive backtest report PDF.

    Args:
        data: Dict containing backtest results. Expected keys:
            symbol, start_date, end_date, initial_capital, final_capital,
            total_return_pct, win_rate, max_drawdown, profit_factor,
            sharpe_ratio, total_fees, trades_count, trades (list of dicts).
        output_path: Path where the PDF will be saved.

    Returns:
        output_path on success.
    """
    # Ensure output directory exists
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = _build_styles()
    story = []

    # ── Title block ──────────────────────────────────────────────────
    symbol = data.get("symbol", "Portfolio")
    story.append(Paragraph(f"Backtest Report — {symbol}", styles["title"]))
    story.append(
        Paragraph(
            f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles["subtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT_BLUE, spaceAfter=14))

    # ── Performance Metrics ──────────────────────────────────────────
    story.append(Paragraph("Performance Metrics", styles["section_header"]))
    story.append(_metrics_table(data, styles))
    story.append(Spacer(1, 16))

    # ── Trade List ───────────────────────────────────────────────────
    trades = data.get("trades", [])
    story.append(Paragraph(f"Trade List ({len(trades)} trades)", styles["section_header"]))

    tbl = _trades_table(trades, styles)
    if tbl:
        story.append(tbl)
    else:
        story.append(Paragraph("No trades recorded.", styles["normal"]))

    story.append(Spacer(1, 16))

    # ── Footer note ──────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=8))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "This report is generated by the automated trading system backtest engine. "
            "Past performance does not guarantee future results.",
            styles["small"],
        )
    )

    doc.build(story)
    return output_path
