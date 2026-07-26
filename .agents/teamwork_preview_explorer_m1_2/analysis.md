# Requirement 2 (R2) Codebase Audit & UX Enhancement Architecture Report

## Executive Summary
This report presents a comprehensive codebase audit and technical design for **Requirement 2 (R2): GitHub Pages Dashboard & HRP UX Enhancement**. 

The system's pipeline produces rich multi-strategy predictions and HRP portfolio allocations, but the existing report generator (`trading_system/generate_report.py`) and deployed dashboard (`gh-pages/index.html`) currently lack interactive visualizations, omit the HRP portfolio allocation outputs, and use outdated desktop hyperlinks for stock symbols.

This audit establishes the full evidence chain, identifies technical gaps, and provides concrete specifications for updating `generate_report.py` to deliver responsive Chart.js visualizations, mobile-optimized stock viewer hyperlinks (Naver Finance Mobile for KRX and Yahoo Finance for foreign stocks), interactive HRP allocation charts, and regime performance trend analytics.

---

## 1. Problem Boundary & Evidence Chain

### A. Current File Map & Responsibilities
| File Path | Role / Description |
|---|---|
| `trading_system/generate_report.py` | Python script that parses prediction text files in `trading_system/result/` and outputs `gh-pages/index.html`. |
| `gh-pages/index.html` | Deployed GitHub Pages single-page web dashboard (630 KB, ~12,135 lines generated HTML). |
| `trading_system/result/portfolio_allocation.txt` | Output text file from `run_pipeline.py` containing HRP / Kelly portfolio position sizing results. |
| `trading_system/src/risk/position_sizing.py` | `PortfolioAllocator` class supporting Kelly, Sharpe proxy, and HRP (`use_hrp=True`) allocation. |
| `trading_system/src/analysis/portfolio_optimizer.py` | Implementation of `calculate_hrp_weights` (Hierarchical Risk Parity via single-linkage clustering & recursive bisection). |
| `trading_system/src/analysis/regime_detector.py` | `MarketRegimeDetector` (GMM-based classification into BEAR=0, SIDEWAYS=1, BULL=2). |
| `trading_system/src/ai/ensemble_scorer.py` | `EnsembleScoringEngine` managing dynamic strategy weights per regime. |

### B. Direct Observations & Code Verification

1. **Symbol Links Inspection (`trading_system/generate_report.py:416-424`)**:
   - Observation: Currently uses desktop Naver link `https://finance.naver.com/item/main.naver?code={symbol}` for KRX symbols and `https://m.stock.naver.com/worldstock/stock/{s}.O/total` for foreign stocks.
   - Defect: Desktop Naver link is cumbersome on mobile viewports. For SP500, blindly appending `.O` breaks NYSE/AMEX symbols (e.g. JPM, IBM, BRK.B) on Naver Worldstock.

2. **HRP Portfolio Data Omission (`trading_system/generate_report.py:1012-1017`)**:
   - Observation: `main()` in `generate_report.py` reads `ensemble_predictions.txt`, `surge_predictions.txt`, `vcp_patterns.txt`, `lead_lag_predictions.txt`, `vcp_ml_predictions.txt`, and `pipeline_result.txt`.
   - Defect: It completely skips `portfolio_allocation.txt`! As a result, the dashboard does not show allocation weights, target cash levels, or single-position limits.

3. **Chart Visualizations Absence (`gh-pages/index.html`)**:
   - Observation: Search for `<canvas>` or JavaScript charting libraries in `gh-pages/index.html` yields zero results.
   - Defect: All data is displayed in static HTML tables with basic inline CSS widths. No visual representation of HRP asset weights, cash ratio, or regime performance trends exists.

4. **Regime Representation (`trading_system/generate_report.py:436, 483-489`)**:
   - Observation: Regime is shown as a single static badge (e.g. `🟡 SIDEWAYS`) in header and dynamic weights are shown as plain text lists.
   - Defect: Users cannot inspect historical regime adaptation, strategy weight distributions per regime, or regime performance trade-offs.

---

## 2. Technical Gap Analysis

```
[Pipeline Execution]
       │
       ├─► ensemble_predictions.txt
       ├─► surge_predictions.txt
       ├─► vcp_patterns.txt
       ├─► lead_lag_predictions.txt
       ├─► vcp_ml_predictions.txt
       ├─► pipeline_result.txt
       └─► portfolio_allocation.txt ───┐ [GAP 1: UNPARSED BY GENERATE_REPORT]
                                       │
                                       ▼
                       [generate_report.py]
                                       │
                                       ├─► [GAP 2: Desktop KRX Links & Broken SP500 .O Links]
                                       ├─► [GAP 3: No Interactive Charts (Chart.js / Canvas)]
                                       └─► [GAP 4: No Regime Strategy Weight Matrix]
                                       │
                                       ▼
                             [gh-pages/index.html]
```

---

## 3. Detailed Technical Design for R2 Enhancements

### A. Mobile-Optimized Stock Hyperlinks (`make_stock_link`)
Replace the current implementation with smart market-aware link generation:
- **KRX (KOSPI, KOSDAQ, KONEX)**: Direct to Naver Finance Mobile item page `https://m.stock.naver.com/item/main.nhn?code={symbol}`. This URL cleanly renders on mobile devices and auto-redirects on desktop.
- **SP500 / US Stocks**: Direct to Yahoo Finance `https://finance.yahoo.com/quote/{symbol_formatted}`, automatically replacing dots with hyphens (e.g., `BRK.B` -> `BRK-B`).

**Updated Code Specification**:
```python
def make_stock_link(symbol: str, market: str) -> str:
    clean_sym = str(symbol).strip()
    if market in ['KOSPI', 'KOSDAQ', 'KONEX'] or clean_sym.isdigit():
        return f'<a href="https://m.stock.naver.com/item/main.nhn?code={clean_sym}" target="_blank" class="stock-link" rel="noopener">{clean_sym}</a>'
    else:
        yf_sym = clean_sym.replace('.', '-')
        return f'<a href="https://finance.yahoo.com/quote/{yf_sym}" target="_blank" class="stock-link" rel="noopener" title="Yahoo Finance">{clean_sym}</a>'
```

---

### B. HRP Portfolio Allocation Parser & Data Model
Add dataclasses and parser for `portfolio_allocation.txt`:

```python
@dataclass
class PortfolioRow:
    rank: int
    symbol: str
    name: str
    market: str
    expected_return: str
    volatility: str
    weight: str
    amount: str

@dataclass
class PortfolioData:
    date: str = ""
    total_capital: str = ""
    target_horizon: str = ""
    regime: str = "UNKNOWN"
    max_allocation: str = ""
    allocated_weight: str = ""
    allocated_amount: str = ""
    cash_weight: str = ""
    cash_amount: str = ""
    rows: list[PortfolioRow] = field(default_factory=list)

def parse_portfolio_allocation(text: str) -> PortfolioData:
    data = PortfolioData()
    if not text:
        return data

    in_table = False
    for line in text.splitlines():
        line_s = line.strip()
        if not line_s:
            continue
        m = re.match(r"Date:\s*(.+)", line_s)
        if m: data.date = m.group(1).strip()
        m = re.match(r"Total Capital:\s*(.+)", line_s)
        if m: data.total_capital = m.group(1).strip()
        m = re.match(r"Target Horizon:\s*(.+)", line_s)
        if m: data.target_horizon = m.group(1).strip()
        m = re.match(r"Current Market Regime Detected:\s*(\w+)", line_s)
        if m: data.regime = m.group(1)
        m = re.match(r"Maximum Total Allocation Allowed:\s*(.+)", line_s)
        if m: data.max_allocation = m.group(1).strip()
        m = re.match(r"Allocated Capital:\s*([-\d.]+%)\s*\((.+)\)", line_s)
        if m:
            data.allocated_weight = m.group(1)
            data.allocated_amount = m.group(2).strip()
        m = re.match(r"Remaining Cash\s*:\s*([-\d.]+%)\s*\((.+)\)", line_s)
        if m:
            data.cash_weight = m.group(1)
            data.cash_amount = m.group(2).strip()

        if line_s.startswith("No.") and "Symbol" in line_s:
            in_table = True
            continue
        if in_table and line_s.startswith("---"):
            continue
        if in_table and not line_s.startswith("Allocated Capital"):
            m_row = re.match(r"^(\d+)\s+(\S+)\s+(.+?)\s+([A-Z0-9]+)\s+([-\d.]+%)\s+([-\d.]+%)\s+([-\d.]+%)\s+([\d,]+)$", line_s)
            if m_row:
                data.rows.append(PortfolioRow(
                    rank=int(m_row.group(1)),
                    symbol=m_row.group(2),
                    name=m_row.group(3).strip(),
                    market=m_row.group(4),
                    expected_return=m_row.group(5),
                    volatility=m_row.group(6),
                    weight=m_row.group(7),
                    amount=m_row.group(8)
                ))
    return data
```

---

### C. Dashboard UX Layout & Interactive Chart Architecture

Two new top-level dashboard tabs will be added:
1. `💼 Portfolio (HRP)` — Displays the HRP position sizing recommendations table, key allocation summary metrics (Allocated Capital vs Remaining Cash), and interactive charts:
   - **HRP Allocation Donut Chart**: Visualizes individual stock weights vs cash reserve.
   - **Market Exposure Bar Chart**: Visualizes total capital allocation aggregated by market (`KOSPI`, `KOSDAQ`, `KONEX`, `SP500`, `CASH`).
2. `🌐 Regime & Strategy` — Displays market regime metrics, strategy weight allocation matrix, and interactive regime charts:
   - **Strategy Weight Breakdown Chart**: Dynamic bar/radar chart showing strategy weights across `BULL`, `SIDEWAYS`, and `BEAR` regimes.
   - **Regime Parameter Reference Table**: Clarifies maximum total allocation caps and strategy focus for each regime.

#### Chart Rendering Strategy
In corporate / GitHub Pages environments, include Chart.js via CDN in `<head>`:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
```
With an embedded pure Canvas rendering script as a fallback if Chart.js is not loaded, ensuring 100% reliability regardless of network conditions.

**HTML/JS Embedding Design**:
```html
<!-- Chart Container Grid -->
<div class="chart-grid">
  <div class="chart-card">
    <h3>💼 HRP Target Portfolio Weights</h3>
    <div class="chart-container">
      <canvas id="hrpWeightChart"></canvas>
    </div>
  </div>
  <div class="chart-card">
    <h3>🌐 Market Asset Allocation</h3>
    <div class="chart-container">
      <canvas id="marketAllocChart"></canvas>
    </div>
  </div>
</div>
```

---

## 4. Verification Plan

### A. Execution Commands
To verify report generation and dashboard output:
```bash
# 1. Run report generator
.venv/bin/python trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html

# 2. Check file existence and size
ls -lh gh-pages/index.html

# 3. Validate HTML syntax & contents
.venv/bin/python -c "
text = open('gh-pages/index.html', encoding='utf-8').read()
assert 'm.stock.naver.com' in text, 'Naver mobile links missing'
assert 'finance.yahoo.com' in text, 'Yahoo Finance links missing'
assert 'hrpWeightChart' in text, 'HRP chart canvas missing'
assert 'Portfolio (HRP)' in text, 'HRP tab missing'
print('SUCCESS: All R2 verification checks passed!')
"
```

### B. Invalidation Conditions
The verification will fail if:
1. `portfolio_allocation.txt` parsing errors occur or produce empty table rows.
2. SP500 links retain hardcoded `.O` suffixes that fail resolution on Yahoo Finance.
3. Interactive chart canvases fail to render or break tab layout on mobile screen widths (<768px).

---

## 5. Conclusion & Actionable Summary for Implementer
All 4 gaps in R2 have been audited and fully designed. The implementation requires modifications **only** in `trading_system/generate_report.py` to:
1. Update `make_stock_link` for Naver Mobile KRX + Yahoo Finance SP500 links.
2. Add `parse_portfolio_allocation` and pass `portfolio_allocation.txt` data to `build_html`.
3. Add `Portfolio (HRP)` and `Regime & Strategy` tabs to `build_html` with Chart.js canvas elements.
4. Add client-side JavaScript for interactive Donut/Bar charts and responsive mobile layout.
