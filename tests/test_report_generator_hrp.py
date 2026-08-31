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


def test_parse_portfolio_allocation_overflow_normalization():
    """Verify that an overflowing portfolio (e.g. sum of rows > 100%) is safely re-normalized."""
    overflow_text = """=== Portfolio Allocation Recommendations (Ensemble HRP, Merged Across Markets) ===
Date: 2026-08-10 21:32
Total Capital: 100,000,000 KRW
Target Horizon: 20d

Current Market Regime Detected: BULL
Maximum Total Allocation Allowed: 85.0%

No. Symbol    Name                Market    Return    Volatility  Weight    Amount         
--------------------------------------------------------------------------------------------
1   EA        Electronic Arts     SP500        7.55%      0.16%   80.00%    80,000,000
2   AES       AES Corporation     SP500        7.91%      0.34%   80.00%    80,000,000
3   004080    신흥                  KOSPI        7.62%      0.15%   80.00%    80,000,000
4   034950    한국기업평가              KOSDAQ       6.57%      0.62%   80.00%    80,000,000
5   018120    진로발효                KOSDAQ       7.11%      0.42%   69.88%    69,880,000
--------------------------------------------------------------------------------------------
Allocated Capital: 389.88% (389,880,000)
"""
    data = parse_portfolio_allocation(overflow_text)
    assert data is not None
    assert len(data.rows) == 5

    # Rows should be re-normalized to sum to <= 85.0%
    row_sum = sum(float(r.weight.replace("%", "")) for r in data.rows)
    assert abs(row_sum - 85.0) < 0.1

    # Allocated capital pct should be <= 85.0%
    alloc_pct = float(data.allocated_capital_pct.replace("%", ""))
    assert abs(alloc_pct - 85.0) < 0.1

    # Remaining cash pct should be >= 15.0% and sum to 100.0%
    rem_pct = float(data.remaining_cash_pct.replace("%", ""))
    assert abs(alloc_pct + rem_pct - 100.0) < 0.01


def test_parse_portfolio_allocation_missing_remaining_cash():
    """Verify that if Remaining Cash is missing from input text, it is auto-reconciled."""
    sample_text = """=== Portfolio Allocation Recommendations ===
Date: 2026-08-16 10:22
Total Capital: 100,000,000 KRW
Target Horizon: 20d
Current Market Regime Detected: BULL
Maximum Total Allocation Allowed: 85.0%

No. Symbol    Name                Market    Return    Volatility  Weight    Amount         
--------------------------------------------------------------------------------------------
1   EA        Electronic Arts     SP500        12.99%       0.24%    15.00%    15,000,000
2   057050    현대홈쇼핑               KOSPI        18.57%      89.82%    15.00%    15,000,000
--------------------------------------------------------------------------------------------
Allocated Capital: 30.00% (    30,000,000)
"""
    data = parse_portfolio_allocation(sample_text)
    assert data.allocated_capital_pct == "30.00%"
    assert data.remaining_cash_pct == "70.00%"
    assert data.remaining_cash == "70,000,000"


def test_merge_portfolio_allocation_multi_market(tmp_path):
    """Verify merge_portfolio_allocation re-normalizes 5 market files to <= max_alloc and writes cash balance."""
    try:
        from trading_system.merge_predictions import merge_portfolio_allocation
    except ModuleNotFoundError:
        from merge_predictions import merge_portfolio_allocation

    target_dirs = {}
    markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
    for m in markets:
        m_dir = tmp_path / f"result_{m}"
        m_dir.mkdir(parents=True, exist_ok=True)
        content = f"""=== Portfolio Allocation Recommendations ===
Date: 2026-08-21 21:00
Total Capital: 100,000,000 KRW
Target Horizon: 20d
Current Market Regime Detected: BULL
Maximum Total Allocation Allowed: 85.0%

No. Symbol    Name                Market    Return    Volatility  Weight    Amount         
--------------------------------------------------------------------------------------------
1   SYM_{m}_1 Stock_{m}_1          {m:<10}  8.00%      0.20%    40.00%    40,000,000
2   SYM_{m}_2 Stock_{m}_2          {m:<10}  7.50%      0.25%    38.00%    38,000,000
--------------------------------------------------------------------------------------------
Allocated Capital: 78.00% (    78,000,000)
Remaining Cash   : 22.00% (    22,000,000)
"""
        (m_dir / f"portfolio_allocation_{m}.txt").write_text(content, encoding="utf-8")
        target_dirs[m] = m_dir

    result_dir = tmp_path / "merged_result"
    result_dir.mkdir(parents=True, exist_ok=True)

    merge_portfolio_allocation(result_dir, target_dirs)

    merged_file = result_dir / "portfolio_allocation.txt"
    assert merged_file.exists()
    merged_text = merged_file.read_text(encoding="utf-8")

    # Verify header and consistency
    assert "Allocated Capital:" in merged_text
    assert "Remaining Cash   :" in merged_text

    # Parse with report generator parser
    data = parse_portfolio_allocation(merged_text)
    assert len(data.rows) == 10  # 2 per market * 5 markets

    alloc_f = float(data.allocated_capital_pct.replace("%", ""))
    rem_f = float(data.remaining_cash_pct.replace("%", ""))

    # Allocated capital must be <= 85.0% (not 5 * 78% = 390%)
    assert alloc_f <= 85.01
    assert abs(alloc_f + rem_f - 100.0) < 0.01


def test_dashboard_html_ux_fixes():
    """Verify Bug fixes and UX enhancements in generated dashboard HTML."""
    ensemble = EnsembleData(
        date="2026-08-21",
        regime="BULL_LOW_VOL",
        regime_code=0,
        max_allocation="85.0%",
        sp500_return="0.8%",
        vix="13.2",
        us10y="4.1%",
        weights={"XGBoost Regression": "20%", "Surge Classifier": "15%"},
        markets=[
            EnsembleMarket(
                market="KOSPI",
                rows=[
                    EnsembleRow(i, f"0059{i:02d}", f"종목_{i}", "85%", "+5.2%", "40%", "10%", "20%", "15%")
                    for i in range(1, 35)
                ],
            ),
        ],
    )

    port_data = PortfolioAllocationData(
        date="2026-08-21 21:00",
        total_capital="100,000,000 KRW",
        target_horizon="20d",
        regime="BULL_LOW_VOL",
        max_allocation="85.0%",
        allocated_capital="80,000,000",
        allocated_capital_pct="80.00%",
        remaining_cash="20,000,000",
        remaining_cash_pct="20.00%",
        rows=[
            PortfolioRow(1, "005930", "삼성전자", "KOSPI", "+5.2%", "0.35%", "80.00%", "80,000,000"),
        ],
    )

    html = build_html(
        ensemble,
        surge_date="2026-08-21",
        surge_sections=[],
        vcp_date="2026-08-21",
        vcp_rows=[],
        lag_date="2026-08-21",
        follower_rows=[],
        leader_rows=[],
        portfolio_data=port_data,
        preloaded_backtest_table_html='<tr><td>🏆 31대 동적 가중 앙상블 (Ensemble)</td><td class="pos">2.68</td><td class="neg">-6.4%</td><td>74.2%</td><td class="pos">+38.6%</td></tr>',
        backtest_chart_labels_json='["2021-Q1","2026-Q3"]',
        backtest_chart_ensemble_json='[0.0,462.8]',
        backtest_chart_sp500_json='[0.0,128.4]',
        backtest_chart_kospi_json='[0.0,30.5]',
    )

    # 1. Search input duplicate icon check: placeholder should not have leading 🔍
    assert 'placeholder="종목명 또는 종목코드 실시간 검색...' in html
    assert 'placeholder="🔍 종목명' not in html

    # 2. Search Autocomplete dropdown check
    assert 'id="search-autocomplete-dropdown"' in html

    # 3. View mode toggle (Table / Card view) check
    assert 'id="btn-view-table"' in html
    assert 'id="btn-view-card"' in html
    assert 'class="stock-cards-wrap"' in html
    assert 'class="stock-card"' in html

    # 4. Up to 100 rows rendered check (here 34 rows are passed, all 34 should be rendered)
    assert "005934" in html

    # 5. Preloaded Backtest Returns Chart and multi-strategy walk-forward table check
    assert 'id="backtestReturnsChart"' in html
    assert ("34대 동적 가중 앙상블 (Ensemble)" in html) or ("31대 동적 가중 앙상블 (Ensemble)" in html)
    assert ("34대 전략 역사적 벤치마크 백테스트 성과" in html) or ("31대 전략 역사적 벤치마크 백테스트 성과" in html)



