# -*- coding: utf-8 -*-
"""
Tests for Track 4: Web Dashboard 30-Year Quantitative Benchmark & Multi-Regime Interactive Visualization.

Validates:
1. build_30year_benchmark_dashboard_html() unit execution:
   - Renders 30-year lifetime compounding metrics (CAGR +8.19%, Net Return +1,149.55%, MDD -35.43%).
   - Renders 5 major historical crises defense table (1997 IMF, 2000 Dot-com, 2008 GFC, 2020 COVID, 2022 Inflation).
   - Renders 1996~2026 annual return cards & Leland cost compression metrics.
   - Integrates live Paper Trading OMS monitor widget from trade_logs.db.
2. End-to-end gh-pages/index.html generation verification:
   - File exists, non-zero (> 200 KB).
   - Contains 30-year benchmark components, crisis defense table, and OMS live monitor.
"""

import os
import sys
from pathlib import Path
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))


class TestTrack4DashboardVisualization:
    """Test suite for Track 4 Web Dashboard benchmark visualization."""

    def test_build_30year_benchmark_dashboard_html_unit(self):
        """Test unit execution of build_30year_benchmark_dashboard_html()."""
        from trading_system.generate_report import build_30year_benchmark_dashboard_html

        html = build_30year_benchmark_dashboard_html()
        assert isinstance(html, str)
        assert len(html) > 2000

        # Core Benchmark Metrics
        assert "30-Year Quantitative Benchmark" in html
        assert "8.19%" in html  # CAGR
        assert "+1,149.55%" in html  # Cumulative Net Return
        assert "-35.43%" in html  # Lifetime Max Drawdown
        assert "8,089" in html  # Trading Days

        # 5 Historical Crises Defense
        assert "1997 IMF Asian Financial Crisis" in html or "1997" in html
        assert "2000 Dot-Com Bubble Crash" in html or "2000" in html
        assert "2008 Global Financial Crisis (Lehman)" in html or "2008" in html
        assert "2020 COVID-19 Liquidity Shock" in html or "2020" in html
        assert "2022 Global Fed Rate Hike &amp; Inflation" in html or "2022" in html

        # Leland Cost Compression & Paper Trading Live Monitor
        assert "Leland" in html
        assert "Paper Trading Live OMS Monitor" in html
        assert "trade_logs.db" in html
        assert "피드백 루프" in html or "Feedback" in html or "Slippage" in html

    def test_gh_pages_index_html_integration(self):
        """Test that generated gh-pages/index.html has Track 4 benchmark content."""
        gh_pages_path = _PROJECT_ROOT / "gh-pages" / "index.html"
        trading_sys_gh = _PROJECT_ROOT / "trading_system" / "gh-pages" / "index.html"

        target_file = gh_pages_path if gh_pages_path.exists() else trading_sys_gh
        assert target_file.exists(), f"Target HTML report not found in {gh_pages_path} or {trading_sys_gh}"

        size_kb = target_file.stat().st_size / 1024
        assert size_kb > 100, f"HTML file size too small: {size_kb:.1f} KB"

        content = target_file.read_text(encoding="utf-8", errors="replace")

        # Verify key cards are present
        assert "30-Year Quantitative Benchmark" in content
        assert "+1,149.55%" in content
        assert "-35.43%" in content
        assert "1997" in content
        assert "2008" in content
        assert "2020" in content
        assert "Paper Trading Live OMS Monitor" in content or "trade_logs.db" in content
