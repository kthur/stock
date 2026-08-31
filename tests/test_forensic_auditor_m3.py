"""
tests/test_forensic_auditor_m3.py — Forensic Integrity and Adversarial Stress Test for Milestone 3

Covers:
1. Absence of hardcoded data / fake facades: Dynamic data injection reflection test.
2. Card 1 (Market Regime & Risk Gates Console) data integrity and fallback tracking.
3. Card 2 (Strategy Coverage & Health Diagnostic Center) dynamic metrics, status filters, and 31 health cards.
4. Card 3 (Portfolio Optimization & Execution OMS Command Center) Leland buffer tags, allocations, EVT-CVaR, and slippage feedback.
5. Canonical 31-Strategy Tab ordering (1..31) and panel integrity.
6. Edge case & Adversarial input stress testing (all NaNs, empty inputs, extreme scores, unicode, corrupt rows).
"""

from __future__ import annotations

import re
import json
import pytest
from pathlib import Path
from trading_system.generate_report import (
    EnsembleData,
    EnsembleMarket,
    EnsembleRow,
    PortfolioAllocationData,
    PortfolioRow,
    StrategyHealthInfo,
    build_html,
    build_strategy_health_monitor_html,
    parse_portfolio_allocation,
    parse_strategy_coverage_report,
    format_metric_cell,
    largest_remainder_round,
)


class TestForensicDataAuthenticity:
    """Forensic Check: Ensure generate_report authentically renders parsed model data without hardcoded bypass."""

    def test_dynamic_portfolio_data_reflection(self):
        """Verify custom dynamic portfolio inputs are directly reflected in the HTML without hardcoding."""
        unique_symbol = "DYNAMIC_SYM_999"
        unique_name = "Dynamic Corp Authentic"
        unique_capital = "777,888,999 KRW"
        unique_return = "+42.7%"
        unique_weight = "14.25%"

        port_data = PortfolioAllocationData(
            date="2026-09-01 12:34",
            total_capital=unique_capital,
            target_horizon="20d",
            regime="BULL_LOW_VOL",
            max_allocation="85.0%",
            allocated_capital="100,000,000",
            allocated_capital_pct="85.00%",
            remaining_cash="15,000,000",
            remaining_cash_pct="15.00%",
            rows=[
                PortfolioRow(1, unique_symbol, unique_name, "KOSPI", unique_return, "0.15%", unique_weight, "14,250,000"),
            ],
        )

        ensemble = EnsembleData(date="2026-09-01", regime="BULL_LOW_VOL")
        html = build_html(
            ensemble=ensemble,
            surge_date="2026-09-01",
            surge_sections=[],
            vcp_date="2026-09-01",
            vcp_rows=[],
            lag_date="2026-09-01",
            follower_rows=[],
            leader_rows=[],
            portfolio_data=port_data,
        )

        assert unique_symbol in html
        assert unique_name in html
        assert unique_capital in html
        assert unique_return in html
        assert unique_weight in html
        # First 10 items get BUY (New Entry) tag
        assert "BUY (New Entry)" in html

    def test_dynamic_macro_regime_reflection_and_fallbacks(self):
        """Verify Card 1 dynamically renders distinct regime states, decoupling, and detects fallbacks."""
        ensemble = EnsembleData(
            date="2026-09-01",
            us_regime="BEAR_HIGH_VOL",
            kr_regime="SIDEWAYS_LOW_VOL",
            decoupling_status="DECOUPLING_ACTIVE",
            decoupling_corr="0.12",
            vix="34.50",  # Custom non-fallback
            sp500_return="-3.50%",
            max_allocation="30.0%",
            decision_rationale="[Regime Assessment]\n• VIX fast shock active\n- Base Allocation: 30%",
        )

        html = build_html(
            ensemble=ensemble,
            surge_date="2026-09-01",
            surge_sections=[],
            vcp_date="2026-09-01",
            vcp_rows=[],
            lag_date="2026-09-01",
            follower_rows=[],
            leader_rows=[],
        )

        assert "BEAR_HIGH_VOL" in html
        assert "SIDEWAYS_LOW_VOL" in html
        assert "DECOUPLING_ACTIVE" in html
        assert "34.50" in html
        assert "30.0%" in html
        assert "목표 현금비중" in html
        assert "70.0%" in html  # 100 - 30.0%
        assert "VIX fast shock active" in html


class TestConsolidatedCard1:
    """Card 1: Market Regime & Risk Gates Console Forensic Audit."""

    def test_card1_structure_and_classes(self):
        ensemble = EnsembleData(date="2026-09-01")
        html = build_html(
            ensemble=ensemble,
            surge_date="2026-09-01",
            surge_sections=[],
            vcp_date="2026-09-01",
            vcp_rows=[],
            lag_date="2026-09-01",
            follower_rows=[],
            leader_rows=[],
        )

        assert 'class="regime-risk-card"' in html
        assert 'class="regime-risk-header"' in html
        assert 'class="regime-badge-strip"' in html
        assert 'badge-regime-us' in html
        assert 'badge-regime-kr' in html
        assert 'badge-crisis-none' in html
        assert 'class="macro-grid"' in html
        assert 'class="gate-status-strip"' in html
        assert 'VIX Fast Shock Gate' in html
        assert 'Macro Composite Score' in html
        assert 'Intraday Stop-Loss' in html
        assert '6-Regime Dynamic Matrix' in html


class TestConsolidatedCard2:
    """Card 2: Strategy Coverage & Data Health Diagnostic Center Forensic Audit."""

    def test_card2_metrics_and_status_filtering(self):
        items = [
            StrategyHealthInfo("regression", 1, "XGBoost 회귀", "AI", "regression", 100, 0, 100.0, "HEALTHY", "None", "정상"),
            StrategyHealthInfo("surge", 2, "Surge 분류기", "AI", "surge", 80, 20, 80.0, "PARTIAL", "INSUFFICIENT_PRICE_HISTORY", "주가부족"),
            StrategyHealthInfo("lead_lag", 3, "Lead-Lag", "통계", "leadlag", 50, 50, 50.0, "FALLBACK", "FALLBACK_MODEL", "기본모델"),
            StrategyHealthInfo("rim_valuation", 9, "RIM Valuation", "가치", "rim", 0, 100, 0.0, "NO_DATA", "NO_FUNDAMENTAL_DATA", "재무미비"),
        ]

        html = build_strategy_health_monitor_html(100, items)

        # Verify summary pills counts
        assert "🟢 정상 1" in html
        assert "🟡 부분 1" in html
        assert "🟠 대체 1" in html
        assert "🔴 미비 1" in html
        assert "전체 (All 4)" in html
        assert "평균 커버리지: 57.5%" in html

        # Verify card data-status attributes for JavaScript filtering
        assert 'data-status="healthy"' in html
        assert 'data-status="partial"' in html
        assert 'data-status="fallback"' in html
        assert 'data-status="no_data"' in html

        # Verify Diagnostics and Stress Test section
        assert "주요 데이터 결측 사유 및 진단" in html
        assert "CPCV 과적합 진단 &amp; 거시위기 스트레스 테스트" in html
        assert "PBO: 0.00%" in html
        assert "2008 금융위기" in html
        assert "2020 코로나 쇼크" in html
        assert "2022 금리 인상" in html


class TestConsolidatedCard3:
    """Card 3: Portfolio Optimization & Execution OMS Command Center Forensic Audit."""

    def test_card3_leland_and_oms_elements(self):
        rows = [
            PortfolioRow(i, f"SYM_{i:02d}", f"Stock_{i}", "KOSPI", "+5.0%", "0.20%", "5.0%", "5,000,000")
            for i in range(1, 16)
        ]
        port_data = PortfolioAllocationData(
            date="2026-09-01",
            total_capital="100,000,000 KRW",
            target_horizon="20d",
            regime="BULL_LOW_VOL",
            max_allocation="85.0%",
            allocated_capital="75,000,000",
            allocated_capital_pct="75.00%",
            remaining_cash="25,000,000",
            remaining_cash_pct="25.00%",
            rows=rows,
        )

        ensemble = EnsembleData(date="2026-09-01")
        html = build_html(
            ensemble=ensemble,
            surge_date="2026-09-01",
            surge_sections=[],
            vcp_date="2026-09-01",
            vcp_rows=[],
            lag_date="2026-09-01",
            follower_rows=[],
            leader_rows=[],
            portfolio_data=port_data,
        )

        # Panel header & Summary metrics
        assert 'id="panel-portfolio"' in html
        assert "포트폴리오 예상수익률" in html
        assert "실현 변동성 (Vol)" in html
        assert "Sharpe Ratio" in html

        # Leland Execution status tags
        assert "🟢 BUY (New Entry)" in html
        assert "🟡 HOLD (Within &plusmn;2.5%)" in html

        # EVT-CVaR & Leland buffer band panels
        assert "EVT-GPD Tail Risk Budgeting" in html
        assert "Leland No-Trade Buffer Bands &amp; Cost Model" in html
        assert "Almgren-Chriss Optimal Slicing Active" in html

        # Closed-Loop Realized Slippage map
        assert "Execution OMS &amp; Closed-Loop Realized Slippage Map" in html
        assert "OMS 7-Safety Gates: <span class=\"badge-healthy\">🟢 PASSED" in html
        assert "KOSPI" in html
        assert "KOSDAQ" in html
        assert "SP500" in html
        assert "NASDAQ" in html
        assert "RUSSELL2000" in html


class TestCanonical31StrategyTabs:
    """Verify strictly canonical 1..31 tab and panel ordering."""

    def test_canonical_tab_sequence_1_to_31(self):
        ensemble = EnsembleData(date="2026-09-01")
        html = build_html(
            ensemble=ensemble,
            surge_date="2026-09-01",
            surge_sections=[],
            vcp_date="2026-09-01",
            vcp_rows=[],
            lag_date="2026-09-01",
            follower_rows=[],
            leader_rows=[],
        )

        expected_tabs = [
            "1. Regression", "2. Surge", "3. Lead-Lag", "4. VCP Rule", "5. VCP ML",
            "6. Strict LSTM", "7. Stat-Arb", "8. Sector Rotation", "9. RIM Valuation",
            "10. Event-Driven", "11. MQ Factor", "12. Options IV Skew", "13. Order Flow",
            "14. ST Reversal", "15. ARM Factor", "16. CARD Factor", "17. LATR Factor",
            "18. 외인/투신 수급", "19. Supply Chain", "20. NLP Sentiment",
            "21. Factor Neutralized", "22. Vol Targeting", "23. Microstructure",
            "24. Accruals Quality", "25. Short Squeeze", "26. Value-Up Yield",
            "27. Trend Efficiency", "28. Gamma Squeeze", "29. Insider Buying",
            "30. Darkpool &amp; HFT", "31. Tone Drift"
        ]

        # Extract the Row 2 navigation bar specifically
        row2_match = re.search(r'<div class="row2-wrapper">.*?<nav class="tabs">(.*?)</nav>', html, re.DOTALL)
        assert row2_match is not None, "Could not find Row 2 navigation bar"
        nav_html = row2_match.group(1)

        last_pos = -1
        for tab_label in expected_tabs:
            assert tab_label in nav_html, f"Missing canonical tab in nav: {tab_label}"
            pos = nav_html.find(tab_label)
            assert pos > last_pos, f"Tab {tab_label} is out of order (found at {pos}, last at {last_pos})"
            last_pos = pos


class TestAdversarialStressAndEdgeCases:
    """Stress testing: Ensure generate_report gracefully handles corrupted, empty, or extreme data."""

    def test_empty_and_corrupt_portfolio_allocation(self):
        empty_data = parse_portfolio_allocation("")
        assert empty_data is not None
        assert empty_data.total_capital != ""

        corrupt_text = "Corrupted random junk without header\n--- invalid line ---\n"
        corrupt_data = parse_portfolio_allocation(corrupt_text)
        assert corrupt_data is not None

    def test_extreme_and_nan_values_in_metrics(self):
        assert "badge-na" in format_metric_cell(float('nan'))
        assert "badge-na" in format_metric_cell("NaN")
        assert "badge-na" in format_metric_cell("null")
        assert "+9999.0%" in format_metric_cell("+9999.0%", kind="return")

    def test_largest_remainder_round_adversarial(self):
        # 31 extreme heterogeneous values
        weights = [1.0] * 30 + [70.0]
        res = largest_remainder_round(weights, target_sum=100.0, decimals=1)
        assert round(sum(res), 1) == 100.0
        assert len(res) == 31
