"""
tests/test_dashboard_3cards.py — Verification Suite for Consolidated 3 Dashboard Cards

Empirically validates that Card 1, Card 2, and Card 3 in both generate_report.py
and gh-pages/index.html contain all required sub-components:
- Card 1: 2D Market Regime, Crisis Detector, VIX Velocity & Term Structure, Macro indicators.
- Card 2: 31 Strategy Health Monitor, Missingness Reasons, CPCV/PBO Stress Test, click-to-jump buttons.
- Card 3: HRP Donut, Market Exposure, EVT-CVaR Tail Risk, Leland Buffer Bands, Slippage Feedback.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
import pytest

from trading_system.generate_report import (
    main as generate_report_main,
    build_html,
    build_strategy_health_monitor_html,
    StrategyHealthInfo,
    EnsembleData,
    PortfolioAllocationData,
    PortfolioRow,
)

INDEX_HTML_PATH = Path("gh-pages/index.html")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures & Helpers
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def index_html_content() -> str:
    """Load current gh-pages/index.html if available, or generate a fresh one."""
    if INDEX_HTML_PATH.exists():
        return INDEX_HTML_PATH.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_html = Path(tmp_dir) / "index.html"
        generate_report_main(["--result-dir", "trading_system/result", "--out", str(out_html)])
        return out_html.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Card 1: Market Regime & Risk Gates Console
# ─────────────────────────────────────────────────────────────────────────────

class TestCard1MarketRegimeRiskGates:
    """Card 1 Sub-components: 2D Market Regime, Crisis Detector, VIX Velocity & Term Structure, Macro Grid."""

    def test_card1_container_and_header(self, index_html_content: str):
        assert "regime-risk-card" in index_html_content
        assert "2D Market Regime &amp; Risk Gates" in index_html_content or "2D Market Regime & Risk Gates" in index_html_content
        assert "regime-risk-header" in index_html_content
        assert "regime-risk-body" in index_html_content

    def test_card1_2d_market_regime_matrix(self, index_html_content: str):
        # 6-Regime Dynamic Matrix
        assert "6-Regime Dynamic Matrix" in index_html_content or "6-레짐 매트릭스" in index_html_content
        assert "BULL_LOW_VOL" in index_html_content
        assert "BEAR_HIGH_VOL" in index_html_content
        assert "SIDEWAYS_LOW_VOL" in index_html_content
        # US & KR regime badges
        assert "badge-regime-us" in index_html_content or "US:" in index_html_content
        assert "badge-regime-kr" in index_html_content or "KR:" in index_html_content

    def test_card1_crisis_detector(self, index_html_content: str):
        # Crisis Detector badge & composite indicators
        assert "badge-crisis" in index_html_content or "Crisis:" in index_html_content
        assert "Macro Composite Score" in index_html_content
        assert "Drawdown Speed" in index_html_content

    def test_card1_vix_velocity_and_term_structure(self, index_html_content: str):
        # VIX Fast Shock Gate & VIX Term Structure/Spike
        assert "VIX Fast Shock Gate" in index_html_content
        assert "VIX 공포지수" in index_html_content or "VIX" in index_html_content
        assert "Spike" in index_html_content or "Fast Shock" in index_html_content

    def test_card1_macro_indicators_grid(self, index_html_content: str):
        # 10 tiles in Macro Grid
        assert "macro-grid" in index_html_content
        assert "S&amp;P 500 20d Ret" in index_html_content or "S&P 500 20d Ret" in index_html_content
        assert "KOSPI 20d Ret" in index_html_content
        assert "USD/KRW 환율" in index_html_content or "USD/KRW" in index_html_content
        assert "US 10Y 국채금리" in index_html_content or "US 10Y" in index_html_content
        assert "KR 10Y 국채금리" in index_html_content or "KR 10Y" in index_html_content
        assert "WTI 국제유가" in index_html_content or "WTI" in index_html_content
        assert "GLD ETF" in index_html_content or "GLD" in index_html_content
        assert "최대허용배분" in index_html_content
        assert "목표 현금비중" in index_html_content


# ─────────────────────────────────────────────────────────────────────────────
# 2. Card 2: Strategy Coverage & Data Health Diagnostic Center
# ─────────────────────────────────────────────────────────────────────────────

class TestCard2StrategyCoverageAndHealthCenter:
    """Card 2 Sub-components: 31 Strategy Health Monitor, Missingness Reasons, CPCV/PBO Stress Test, Click-to-Jump."""

    def test_card2_container_and_header(self, index_html_content: str):
        assert "health-monitor-section" in index_html_content
        assert "Strategy Data Health Monitor" in index_html_content
        assert "health-summary-pills" in index_html_content

    def test_card2_31_strategy_health_monitor_cards(self, index_html_content: str):
        # Health grid containing cards for strategies
        assert "health-grid" in index_html_content
        health_cards = re.findall(r'<div class="health-card"[^>]*>', index_html_content)
        assert len(health_cards) in (31, 34), f"Expected 31 or 34 health cards, found {len(health_cards)}"

    def test_card2_click_to_jump_buttons(self, index_html_content: str):
        # Click to jump functionality
        assert 'onclick="switchTabById(' in index_html_content
        # Dynamic filter buttons for health status
        assert "filterHealthCards('healthy')" in index_html_content
        assert "filterHealthCards('partial')" in index_html_content
        assert "filterHealthCards('fallback')" in index_html_content
        assert "filterHealthCards('nodata')" in index_html_content
        assert "filterHealthCards('all')" in index_html_content

    def test_card2_missingness_reasons_breakdown(self, index_html_content: str):
        assert "health-reasons-breakdown" in index_html_content
        assert "INSUFFICIENT_PRICE_HISTORY" in index_html_content
        assert "NO_FUNDAMENTAL_DATA" in index_html_content
        assert "NON_US_MARKET_SCOPE" in index_html_content
        assert "NO_COINTEGRATED_PAIR" in index_html_content

    def test_card2_cpcv_pbo_stress_test_section(self, index_html_content: str):
        assert "cpcv-stress-section" in index_html_content
        assert "CPCV 과적합 진단" in index_html_content
        assert "PBO:" in index_html_content
        assert "CPCV Combinatorial Folds" in index_html_content
        assert "Purge / Embargo" in index_html_content
        assert "2008_CRISIS" in index_html_content
        assert "2020_COVID" in index_html_content
        assert "2022_FED_HIKE" in index_html_content


# ─────────────────────────────────────────────────────────────────────────────
# 3. Card 3: Portfolio Optimization & Execution OMS Command Center
# ─────────────────────────────────────────────────────────────────────────────

class TestCard3PortfolioOptimizationAndExecutionOMS:
    """Card 3 Sub-components: HRP Donut, Market Exposure, EVT-CVaR Tail Risk, Leland Buffer Bands, Slippage Feedback."""

    def test_card3_container_in_portfolio_panel(self, index_html_content: str):
        assert 'id="panel-portfolio"' in index_html_content
        assert "HRP Risk Parity" in index_html_content

    def test_card3_hrp_donut_and_market_exposure_charts(self, index_html_content: str):
        assert '<canvas id="hrpDonutChart"></canvas>' in index_html_content
        assert '<canvas id="marketExposureChart"></canvas>' in index_html_content
        assert "HRP Risk Parity Allocation Weights" in index_html_content
        assert "Market Exposure Allocation" in index_html_content

    def test_card3_evt_cvar_tail_risk_budgeting(self, index_html_content: str):
        assert "EVT-GPD Tail Risk Budgeting" in index_html_content
        assert "95% Parametric VaR / CVaR" in index_html_content
        assert "99% Extreme Value GPD CVaR" in index_html_content
        assert "Clayton Copula" in index_html_content
        assert "Tail Risk Loss Budget" in index_html_content

    def test_card3_leland_buffer_bands_and_cost_model(self, index_html_content: str):
        assert "Leland No-Trade Buffer Bands" in index_html_content
        assert "Dynamic No-Trade Band" in index_html_content
        assert "Rebalance Bypass" in index_html_content
        assert "Friction Costs Applied" in index_html_content
        assert "Almgren-Chriss Optimal Slicing" in index_html_content

    def test_card3_closed_loop_slippage_feedback_and_oms(self, index_html_content: str):
        assert "Execution OMS &amp; Closed-Loop Realized Slippage Map" in index_html_content or "Execution OMS & Closed-Loop Realized Slippage Map" in index_html_content
        assert "OMS 7-Safety Gates" in index_html_content
        assert "KOSPI" in index_html_content
        assert "KOSDAQ" in index_html_content
        assert "SP500" in index_html_content
        assert "NASDAQ" in index_html_content
        assert "RUSSELL2000" in index_html_content
        assert "bps" in index_html_content
        assert "HRP Risk Parity Position Allocation &amp; Execution Orders" in index_html_content or "HRP Risk Parity Position Allocation & Execution Orders" in index_html_content
