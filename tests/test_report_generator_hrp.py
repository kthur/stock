"""
test_report_generator_hrp.py — Unit tests for generate_report.py HRP and UX enhancements
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure both project root and trading_system directory are in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
ts_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(ts_dir) not in sys.path:
    sys.path.insert(0, str(ts_dir))

try:
    from trading_system.generate_report import (
        EnsembleData,
        EnsembleMarket,
        EnsembleRow,
        PortfolioAllocationData,
        PortfolioRow,
        build_html,
        make_stock_link,
        parse_portfolio_allocation,
    )
except ModuleNotFoundError:
    from generate_report import (
        EnsembleData,
        EnsembleMarket,
        EnsembleRow,
        PortfolioAllocationData,
        PortfolioRow,
        build_html,
        make_stock_link,
        parse_portfolio_allocation,
    )


def test_make_stock_link_krx():
    link_kospi = make_stock_link("005930", "KOSPI")
    assert "https://m.stock.naver.com/domestic/stock/005930/total" in link_kospi
    assert 'class="stock-link"' in link_kospi

    link_kosdaq = make_stock_link("035420", "KOSDAQ")
    assert "https://m.stock.naver.com/domestic/stock/035420/total" in link_kosdaq

    link_nasdaq = make_stock_link("MSFT", "NASDAQ")
    assert "https://finance.yahoo.com/quote/MSFT" in link_nasdaq

    link_russell = make_stock_link("IWM", "RUSSELL2000")
    assert "https://finance.yahoo.com/quote/IWM" in link_russell


def test_make_stock_link_sp500():
    link_sp = make_stock_link("AAPL", "SP500")
    assert "https://finance.yahoo.com/quote/AAPL" in link_sp
    assert 'class="stock-link"' in link_sp

    link_sp_brk = make_stock_link("BRK-B", "SP500")
    assert "https://finance.yahoo.com/quote/BRK-B" in link_sp_brk


def test_parse_portfolio_allocation_valid():
    sample_text = """=== Portfolio Allocation Recommendations (Ensemble Kelly/Sharpe Optimized) ===
Date: 2026-07-24 23:14
Total Capital: 1,000,000,000 KRW/USD
Target Horizon: 20d

Current Market Regime Detected: SIDEWAYS (Code: 1)
Maximum Total Allocation Allowed: 50.0%

No. Symbol    Name                Market    Return    Volatility  Weight    Amount
--------------------------------------------------------------------------------------------
1   007590    동방아그로               KOSPI         5.01%       0.42%     3.33%    33,333,333
2   004080    신흥                  KOSPI         4.21%       0.49%     3.33%    33,333,333
3   AAPL      Apple Inc.           SP500         3.50%       0.30%     3.33%    33,333,333
--------------------------------------------------------------------------------------------
Allocated Capital: 50.00% (   500,000,000)
Remaining Cash   : 50.00% (   500,000,000)
"""
    data = parse_portfolio_allocation(sample_text)
    assert data.date == "2026-07-24 23:14"
    assert data.total_capital == "1,000,000,000 KRW/USD"
    assert data.target_horizon == "20d"
    assert data.regime == "SIDEWAYS"
    assert data.max_allocation == "50.0%"
    assert len(data.rows) == 3

    r1 = data.rows[0]
    assert r1.rank == 1
    assert r1.symbol == "007590"
    assert r1.name == "동방아그로"
    assert r1.market == "KOSPI"
    assert r1.expected_return == "5.01%"
    assert r1.volatility == "0.42%"
    assert r1.weight == "3.33%"
    assert r1.amount == "33,333,333"

    r3 = data.rows[2]
    assert r3.symbol == "AAPL"
    assert r3.market == "SP500"

    assert data.allocated_capital_pct == "50.00%"
    assert data.allocated_capital == "500,000,000"
    assert data.remaining_cash_pct == "50.00%"
    assert data.remaining_cash == "500,000,000"


def test_parse_portfolio_allocation_empty_fallback():
    data = parse_portfolio_allocation("")
    assert data is not None
    assert len(data.rows) > 0
    assert data.allocated_capital_pct != ""
    assert data.remaining_cash_pct != ""


def test_build_html_contains_hrp_and_regime_tabs():
    ensemble = EnsembleData(
        date="2026-07-24",
        regime="SIDEWAYS",
        regime_code=1,
        max_allocation="50.0%",
        sp500_return="1.2%",
        vix="14.5",
        us10y="4.2%",
        weights={"XGBoost Regression": "35%", "Surge Classifier": "15%"},
        markets=[
            EnsembleMarket(
                market="KOSPI",
                rows=[
                    EnsembleRow(1, "005930", "삼성전자", "85%", "5.2%", "40%", "10%", "20%", "15%"),
                ],
            ),
            EnsembleMarket(
                market="SP500",
                rows=[
                    EnsembleRow(1, "AAPL", "Apple", "90%", "6.1%", "20%", "30%", "20%", "20%"),
                ],
            ),
        ],
    )

    port_data = PortfolioAllocationData(
        date="2026-07-24 23:14",
        total_capital="1,000,000,000 KRW/USD",
        target_horizon="20d",
        regime="SIDEWAYS",
        max_allocation="50.0%",
        allocated_capital="500,000,000",
        allocated_capital_pct="50.00%",
        remaining_cash="500,000,000",
        remaining_cash_pct="50.00%",
        rows=[
            PortfolioRow(1, "005930", "삼성전자", "KOSPI", "5.2%", "0.35%", "25.00%", "250,000,000"),
            PortfolioRow(2, "AAPL", "Apple Inc.", "SP500", "6.1%", "0.28%", "25.00%", "250,000,000"),
        ],
    )

    html = build_html(
        ensemble,
        surge_date="2026-07-24",
        surge_sections=[],
        vcp_date="2026-07-24",
        vcp_rows=[],
        lag_date="2026-07-24",
        follower_rows=[],
        leader_rows=[],
        portfolio_data=port_data,
    )

    assert "Portfolio (HRP)" in html
    assert "Regime &amp; Strategy" in html or "Regime & Strategy" in html
    assert "https://m.stock.naver.com/domestic/stock/005930/total" in html
    assert "https://finance.yahoo.com/quote/AAPL" in html
    assert "hrpDonutChart" in html
    assert "marketExposureChart" in html
    assert "SIDEWAYS_LOW_VOL" in html
    assert len(html.encode("utf-8")) > 20000


def test_generated_report_size_and_no_empty_warning():
    try:
        from trading_system.generate_report import main
    except ModuleNotFoundError:
        from generate_report import main

    result_dir = Path("trading_system/result")
    if not result_dir.exists():
        result_dir = Path("result")
    out_file = Path("gh-pages/index.html")

    if result_dir.exists():
        main([])
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert len(content.encode("utf-8")) > 50000
        assert "Stock Prediction Dashboard" in content
        assert "Portfolio (HRP)" in content

