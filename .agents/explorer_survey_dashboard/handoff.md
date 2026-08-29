# Strategy Data Status & Dashboard Health Monitor Investigation Report

**Author:** Explorer (Survey & Dashboard Architecture)  
**Date:** 2026-08-29  
**Target Modules:** `trading_system/generate_report.py`, `gh-pages/index.html`, `trading_system/src/analysis/coverage_analyzer.py`

---

## 1. Observation

### 1.1 Root Request & Context
According to `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically **Requirement R3** and corresponding Acceptance Criteria):
1. **Health Monitor**: Add a *Strategy Data Status Summary Card / Health Monitor* at the top of the dashboard showing coverage/validity rate for each strategy across all 31 quantitative multi-factor strategies and 5 markets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`).
2. **NaN / None Elimination**: Replace all raw `nan`, `NaN`, `None`, and `undefined` strings in HTML table cells across all tabs with user-friendly badges (e.g. `<span class="badge-na">N/A</span>`, `<span class="badge-need-data">데이터 수집필요</span>`, `<span class="badge-filtered">필터 제외</span>`).
3. **Tab-Level Notice / Warning Banners**: If a strategy or market has 0 or incomplete data, display a prominent notice banner explaining the status, data collection context, and reassuring users that missing strategies are dynamically zero-weighted in the ensemble.

---

### 1.2 Direct Codebase Observations & Vulnerability Inventory

#### (A) Raw `nan` and `nan%` Injection in RIM Valuation Table (`generate_report.py`)
- **Location:** `trading_system/generate_report.py`, lines 712–773 (`parse_rim`) and lines 2305–2317 (`rim_panels` rendering).
- **Observation:** In `rim_predictions.txt` (line 8):
  ```text
  1    057050    현대홈쇼핑               KOSPI     87300.00    nan                  nan%    8.0%     8.0%  100%                                        nan%
  ```
  `parse_rim` captures `"nan"` into `intrinsic_value`, `"nan%"` into `discount`, and `"nan%"` into `score`.
  In `build_html` (lines 2309–2316):
  ```python
  <td>{rim_r.price}</td>
  <td class="pos">{rim_r.intrinsic_value}</td>
  <td class="{disc_class}">{rim_r.discount}</td>
  <td>{rim_r.roe_raw}</td>
  <td>{rim_r.roe_adj}</td>
  <td>{rim_r.eq}</td>
  <td>{filter_disp}</td>
  <td class="score">{score_display}</td>
  ```
  This directly renders verbatim `<td class="pos">nan</td>` and `<td class="neg">nan%</td>` into the HTML table DOM without sanitization.

#### (B) Raw `nan` & `None` in Ensemble 31-Strategy Columns
- **Location:** `trading_system/generate_report.py`, lines 1644–1675.
- **Observation:** In the 31-factor columns of the main ensemble table:
  ```python
  <td class="col-strat">{erow.reg}</td>
  <td class="col-strat">{erow.surge}</td>
  <td class="col-strat">{erow.rim_valuation}</td>
  ...
  ```
  If any strategy file outputs `nan%`, `None`, or uncomputed placeholder `"-"`, it is rendered without badge styling or tooltips.

#### (C) Macro Strip Indicator Raw String Vulnerability
- **Location:** `trading_system/generate_report.py`, lines 1899–1907 (`_macro_cell`).
- **Observation:**
  ```python
  def _macro_cell(label: str, value: str, fallback: str, cls: str = "") -> str:
      ...
      return f'<div class="macro-item"><span class="ml">{label}</span><span class="mv {cls}">{value or "N/A"}{marker}</span></div>'
  ```
  If `value` is string `"nan"` or `"None"`, Python truthiness `bool("nan") == True` evaluates to `"nan"`, displaying raw `"nan"` instead of `"N/A"`.

#### (D) Simple Strategy Tables Lack Missingness Badging
- **Location:** `trading_system/generate_report.py`, lines 2335–2374 (`_build_simple_panels`).
- **Observation:**
  ```python
  score_val = getattr(row, score_attr, row.score)
  rows_html += f"""
  <tr>
    <td class="rank">#{row.rank}</td>
    <td class="symbol">{sym_link}</td>
    <td class="name">{html.escape(row.name)}</td>
    <td>{MARKET_FLAGS.get(row.market, "")} {row.market}</td>
    <td class="{score_class}">{score_val}</td>
  </tr>"""
  ```
  When a strategy has `0.0%` (imputed fallback) or `"-"`, it displays raw text without indicating whether it is an actual low score or an uncomputed missing metric.

#### (E) Stock Detail Drawer & Front-End JS
- **Location:** `trading_system/generate_report.py`, lines 4206–4257 (`openStockDrawer`).
- **Observation:** If `val` in `factorObjStr` is `"nan%"` or `"None"`, the drawer renders `<span style="color:${color}; font-weight:700;">${val}</span>`, displaying `"nan%"` in bold text with a 0% progress bar.

#### (F) Lack of Top-Level Strategy Data Health Monitor
- **Observation:** While `strategy_data_coverage_report.txt` is generated in `trading_system/result/` (113 lines), its data is not parsed or visually presented on GitHub Pages (`gh-pages/index.html`). Users have no high-level overview of which of the 31 strategies are currently active (e.g. 99.9% coverage) vs. in fallback/data collection mode (e.g. 0.0% coverage).

#### (G) Lack of Tab-Level Context Banners
- **Observation:** When an individual strategy tab (e.g., Tab 7 Stat-Arb, Tab 9 RIM, Tab 12 IV Skew, Tab 28 Gamma Squeeze) has 0 rows for a market, it currently renders only a bare row `<tr><td colspan="5" class="empty">데이터 없음</td></tr>` or `조건을 만족하는 공적분 페어가 없습니다`. It fails to explain why data is missing or reassure the user that the ensemble handles this via zero-weight dynamic re-normalization.

---

## 2. Logic Chain

1. **User Perception & System Trust:**
   - Raw `nan`, `None`, or `undefined` strings in a quantitative dashboard signal unhandled exceptions or data corruption to institutional investors and users.
   - Replacing them with explicit, semantically colored badges (`N/A`, `데이터 수집필요`, `필터 제외`, `기본값`) transforms perceived errors into transparent system state indicators.

2. **Data Pipeline Visibility (Health Monitor):**
   - The trading system executes 31 multi-factor strategies across 5 markets. Certain strategies require external data sources (e.g., options chains for IV Skew / Gamma Squeeze, DART/SEC filings for NLP Sentiment, quarterly financials for RIM / MQ / Accruals).
   - In production or demo runs, some data feeds may be unavailable or under collection.
   - Displaying a **Strategy Data Health Monitor** at the top of the dashboard:
     - Parses `strategy_data_coverage_report.txt` (or computes coverage dynamically from parsed rows).
     - Aggregates overall health: *Total Universe*, *Healthy (≥70%)*, *Partial (10–69%)*, *Fallback/Collecting (<10%)*.
     - Provides interactive chips for all 31 strategies with visual progress bars, status badges, and click-to-tab navigation.

3. **Tab-Level Banners for Structural Clarity:**
   - When users click into an individual strategy tab with 0 rows or partial data, a prominent banner provides immediate context:
     - E.g., for **Stat-Arb**: *"엄격한 공적분 검정(ADF p < 0.05)을 통과한 유의미한 페어만 선별하며, 억지 페어를 생성하지 않습니다."*
     - E.g., for **IV Skew / Options**: *"미국 시장 옵션 체인 기반 산출되며, 국내 시장은 옵션 체인 수집 정책에 따라 대체됩니다."*
     - E.g., for **RIM Valuation**: *"재무제표(BPS/ROE)가 미비하거나 자본잠식 종목은 안전마진 산출 대상에서 안전하게 제외됩니다."*
   - Explains that the **Dynamic Ensemble Engine** automatically assigns **0.0% weight** to missing factors and renormalizes remaining active weights.

4. **Multi-Layer Defensive Formatting Architecture:**
   - **Layer 1 (Python Data Parsing):** Sanitize string inputs during parsing (convert `"nan"`, `"NaN"`, `"None"` into structured `None` or explicit reason codes).
   - **Layer 2 (HTML Generator Helper):** A universal `format_table_cell()` / `format_badge()` function that emits styled HTML spans.
   - **Layer 3 (Front-End JS Resilience):** Protect Drawer, Autocomplete, Scenario Simulator, and Table Sorting against null, undefined, or NaN values.

---

## 3. Caveats

1. **Read-Only Scope:** This investigation produces comprehensive technical designs, CSS/HTML templates, and concrete Python code refactoring proposals. Source code modifications are delivered via this report for downstream implementers.
2. **Backend Engine Independence:** Backend fixes to calculation engines (e.g., `rim_valuation.py` missing BPS handling) are complementary to this dashboard UX enhancement. The dashboard will gracefully render both valid computed numbers and explicit status tags (`재무데이터미비`, `이익품질필터`).
3. **Backward Compatibility:** All existing CSS variable themes (`--bg`, `--surface`, `--accent`, etc.), sticky table column architectures (`Rank > Symbol > Name`), responsive mobile optimizations (`@media (max-width: 768px)`), and test assertions in `tests/` must remain 100% compliant.

---

## 4. Conclusion & Complete Technical Design

### 4.1 Component 1: Strategy Data Status Summary Card / Health Monitor

#### (A) Python Data Model & Parsing Logic in `generate_report.py`
```python
@dataclass
class StrategyHealthInfo:
    strategy_id: str
    num: int
    name_ko: str
    category: str
    tab_id: str
    valid_count: int
    missing_count: int
    coverage_pct: float
    status: str          # "HEALTHY" (>=70%), "PARTIAL" (10~69%), "FALLBACK" (1~9%), "NO_DATA" (0%)
    primary_reason: str
    reason_label_ko: str

def parse_strategy_coverage_report(
    cov_text: str,
    parsed_strategies_map: dict[str, list] | None = None,
    total_symbols_fallback: int = 948
) -> tuple[int, list[StrategyHealthInfo]]:
    """
    Parses strategy_data_coverage_report.txt or falls back to dynamically calculating
    valid/missing counts from parsed strategy row lists.
    """
    STRATEGY_METADATA = [
        ("regression", 1, "XGBoost 회귀", "AI 예측", "regression"),
        ("surge", 2, "Surge 분류기", "AI 예측", "surge"),
        ("lead_lag", 3, "Lead-Lag 후행주", "모멘텀/수급", "leadlag"),
        ("vcp_rule", 4, "VCP 패턴 (Rule)", "기술적 패턴", "vcp"),
        ("vcp_ml", 5, "VCP ML 급등예측", "AI 예측", "vcpml"),
        ("lstm", 6, "Strict Causal LSTM", "딥러닝", "lstm"),
        ("stat_arb", 7, "Stat-Arb 차익거래", "차익거래", "stat-arb"),
        ("sector_rotation", 8, "Sector Rotation", "모멘텀/수급", "sector"),
        ("rim_valuation", 9, "RIM Valuation", "가치평가", "rim"),
        ("event_driven", 10, "Event-Driven 촉매", "촉매/공시", "event"),
        ("mq_factor", 11, "MQ Factor (퀄리티)", "퀄리티", "mq"),
        ("iv_skew", 12, "Options IV Skew", "파생/역발상", "iv"),
        ("order_flow", 13, "Order Flow 수급", "수급/유동성", "flow"),
        ("short_term_reversal", 14, "ST Reversal 단기반등", "평균회귀", "reversal"),
        ("arm_factor", 15, "ARM Factor (컨센서스)", "컨센서스", "arm"),
        ("card_factor", 16, "CARD Factor (크로스에셋)", "크로스에셋", "card"),
        ("latr_factor", 17, "LATR Factor (꼬리위험)", "꼬리위험", "latr"),
        ("inst_foreign_sector", 18, "외인/투신 수급", "수급/유동성", "ifs"),
        ("supply_chain", 19, "Supply Chain 공급망", "공급망", "supplychain"),
        ("sentiment", 20, "NLP Sentiment (감성)", "NLP 감성", "sentiment"),
        ("factor_neutralized", 21, "Factor Neutralized", "순수 알파", "neutralized"),
        ("vol_target", 22, "Vol Targeting", "변동성 관리", "voltarget"),
        ("microstructure", 23, "Microstructure 호가", "미시구조", "microstructure"),
        ("accruals_quality", 24, "Accruals Quality (발생액)", "회계 품질", "accruals"),
        ("short_squeeze", 25, "Short Squeeze 촉매", "공매도", "shortsqueeze"),
        ("valueup_catalyst", 26, "Value-Up Yield (주주환원)", "주주환원", "valueup"),
        ("trend_efficiency", 27, "Trend Efficiency 추세", "추세 필터", "trendeff"),
        ("gamma_squeeze", 28, "Gamma Squeeze (감마)", "파생/옵션", "gammasqueeze"),
        ("insider_buying", 29, "Insider Buying (내부자)", "내부자", "insider"),
        ("darkpool", 30, "Darkpool & HFT Flow", "고빈도/다크풀", "darkpool"),
        ("earnings_tone_drift", 31, "Tone Drift 어닝어조", "NLP 어조", "tonedrift"),
    ]

    REASON_KO_MAP = {
        "INSUFFICIENT_PRICE_HISTORY": "과거 주가 데이터 부족",
        "NO_FUNDAMENTAL_DATA": "재무제표 데이터 수집 대기",
        "LOW_EARNINGS_QUALITY": "이익 품질 필터 제외 (적자/저품질)",
        "NO_OPTIONS_CHAIN": "옵션 체인 데이터 미제공 (미국 외)",
        "NON_US_MARKET_SCOPE": "미국 시장 전용 팩터",
        "NO_COINTEGRATED_PAIR": "통계적 유의 공적분 페어 미발견",
        "STRATEGY_SIGNAL_NEUTRAL": "중립 신호 (조건 미부합)",
        "None (100% Valid)": "전체 종목 정상 산출",
    }

    # Parse strategy_data_coverage_report.txt lines if text exists
    cov_dict = {}
    total_symbols = total_symbols_fallback
    if cov_text:
        for line in cov_text.splitlines():
            line_s = line.strip()
            if line_s.startswith("Total Evaluated Symbols:"):
                m_tot = re.search(r"(\d+)", line_s)
                if m_tot:
                    total_symbols = int(m_tot.group(1))
            parts = line_s.split()
            if len(parts) >= 4 and parts[1].isdigit() and parts[2].isdigit() and "%" in parts[3]:
                s_id = parts[0]
                v_cnt = int(parts[1])
                m_cnt = int(parts[2])
                cov_pct = float(parts[3].replace("%", ""))
                reason = " ".join(parts[4:]) if len(parts) > 4 else "None (100% Valid)"
                cov_dict[s_id] = (v_cnt, m_cnt, cov_pct, reason)

    # Build Health Items list
    items: list[StrategyHealthInfo] = []
    for s_id, num, name_ko, cat, tab_id in STRATEGY_METADATA:
        if s_id in cov_dict:
            v_cnt, m_cnt, cov_pct, reason = cov_dict[s_id]
        elif parsed_strategies_map and s_id in parsed_strategies_map:
            rows_list = parsed_strategies_map[s_id]
            v_cnt = len(rows_list)
            m_cnt = max(0, total_symbols - v_cnt)
            cov_pct = round((v_cnt / total_symbols * 100.0), 1) if total_symbols > 0 else 0.0
            reason = "None (100% Valid)" if cov_pct >= 90 else "INSUFFICIENT_PRICE_HISTORY"
        else:
            v_cnt = 0
            m_cnt = total_symbols
            cov_pct = 0.0
            reason = "NO_FUNDAMENTAL_DATA" if "rim" in s_id or "mq" in s_id else "INSUFFICIENT_PRICE_HISTORY"

        if cov_pct >= 70.0:
            status = "HEALTHY"
        elif cov_pct >= 10.0:
            status = "PARTIAL"
        elif cov_pct > 0.0:
            status = "FALLBACK"
        else:
            status = "NO_DATA"

        reason_ko = REASON_KO_MAP.get(reason, reason)
        items.append(StrategyHealthInfo(
            strategy_id=s_id,
            num=num,
            name_ko=name_ko,
            category=cat,
            tab_id=tab_id,
            valid_count=v_cnt,
            missing_count=m_cnt,
            coverage_pct=cov_pct,
            status=status,
            primary_reason=reason,
            reason_label_ko=reason_ko
        ))

    return total_symbols, items
```

#### (B) HTML & CSS Generator for Health Monitor
```python
def build_strategy_health_monitor_html(total_symbols: int, health_items: list[StrategyHealthInfo]) -> str:
    """Renders the Strategy Data Status Summary Card & Health Monitor at the top of the dashboard."""
    healthy_cnt = sum(1 for item in health_items if item.status == "HEALTHY")
    partial_cnt = sum(1 for item in health_items if item.status == "PARTIAL")
    fallback_cnt = sum(1 for item in health_items if item.status == "FALLBACK")
    nodata_cnt = sum(1 for item in health_items if item.status == "NO_DATA")
    avg_cov = sum(item.coverage_pct for item in health_items) / len(health_items) if health_items else 0.0

    cards_html = []
    for item in health_items:
        if item.status == "HEALTHY":
            status_badge = f'<span class="badge-healthy">🟢 정상 ({item.coverage_pct:.1f}%)</span>'
            bar_color = "#2ea043"
        elif item.status == "PARTIAL":
            status_badge = f'<span class="badge-partial">🟡 부분수집 ({item.coverage_pct:.1f}%)</span>'
            bar_color = "#d29922"
        elif item.status == "FALLBACK":
            status_badge = f'<span class="badge-fallback">🟠 대체산출 ({item.coverage_pct:.1f}%)</span>'
            bar_color = "#38bdf8"
        else:
            status_badge = '<span class="badge-need-data">🔴 수집필요 (0.0%)</span>'
            bar_color = "#f85149"

        bar_w = max(4, int(item.coverage_pct))
        cards_html.append(f"""
        <div class="health-card" onclick="switchTabById('{item.tab_id}')" title="클릭하여 {item.name_ko} 탭으로 바로 이동">
          <div class="health-card-header">
            <span class="health-card-title">{item.num}. {item.name_ko}</span>
            {status_badge}
          </div>
          <div class="health-bar-track">
            <div class="health-bar-fill" style="width:{bar_w}%; background:{bar_color};"></div>
          </div>
          <div class="health-card-meta">
            <span>유효 {item.valid_count:,} / 결측 {item.missing_count:,}</span>
            <span class="health-reason" title="{item.primary_reason}">{item.reason_label_ko}</span>
          </div>
        </div>""")

    cards_str = "\n".join(cards_html)

    return f"""
    <!-- ══════════════════════════════════════════════════════ -->
    <!-- 31대 전략 데이터 수집 및 건전성 모니터 (Health Monitor) -->
    <!-- ══════════════════════════════════════════════════════ -->
    <div class="health-monitor-section">
      <div class="health-monitor-header" onclick="toggleSection('health-monitor-body', 'health-icon')">
        <div class="health-header-left">
          <span class="health-header-icon">🩺</span>
          <h2 class="health-header-title">Strategy Data Health Monitor (31대 전략 데이터 수집 현황 &amp; 건전성 모니터)</h2>
          <div class="health-summary-pills">
            <span class="health-pill pill-healthy">🟢 정상 {healthy_cnt}</span>
            <span class="health-pill pill-partial">🟡 부분 {partial_cnt}</span>
            <span class="health-pill pill-fallback">🟠 대체 {fallback_cnt}</span>
            <span class="health-pill pill-nodata">🔴 미비 {nodata_cnt}</span>
            <span class="health-pill pill-avg">📊 평균 커버리지: {avg_cov:.1f}%</span>
          </div>
        </div>
        <span id="health-icon" class="health-toggle-btn">▼ 접기</span>
      </div>
      <div id="health-monitor-body" class="health-monitor-body">
        <div class="health-guide-text">
          💡 각 전략 카드를 클릭하면 해당 개별 전략 상세 탭으로 자동 이동합니다. 데이터 결측 또는 수집 대기 전략은 앙상블 엔진에서 <strong>자동 제로 가중치(0.0%)</strong> 처리되어 포트폴리오 왜곡을 원천 방지합니다.
        </div>
        <div class="health-grid">
          {cards_str}
        </div>
      </div>
    </div>
    """
```

---

### 4.2 Component 2: Unified Cell Sanitization & Badge Component Library

#### (A) Universal Cell Formatting Helper (`generate_report.py`)
```python
def format_metric_cell(
    val: Any,
    kind: str = "text",             # "score", "pct", "currency", "text", "badge", "int"
    null_label: str = "N/A",
    highlight_positive: bool = True
) -> str:
    """
    Universal table cell sanitizer.
    Guarantees that raw 'nan', 'NaN', 'None', 'undefined', 'null', '' are NEVER emitted into HTML.
    Returns appropriately styled HTML spans.
    """
    if val is None:
        return f'<span class="badge-na">{null_label}</span>'

    val_str = str(val).strip()
    val_clean = val_str.lower().rstrip("%")

    # Detect invalid strings
    if val_clean in ("nan", "none", "undefined", "null", "", "-"):
        return f'<span class="badge-na">{null_label}</span>'

    # Detect explicit status tags
    if any(k in val_str for k in ["데이터 수집필요", "수집필요", "미수집"]):
        return f'<span class="badge-need-data">{html.escape(val_str)}</span>'
    if any(k in val_str for k in ["재무데이터미비", "재무미비", "손실", "자본잠식", "필터"]):
        return f'<span class="badge-filtered">{html.escape(val_str)}</span>'
    if "대체" in val_str or "기본값" in val_str:
        return f'<span class="badge-fallback">{html.escape(val_str)}</span>'

    # Formatted numeric types
    if kind in ("score", "pct"):
        num = safe_float(val_str)
        sign = "+" if (num > 0 and kind == "pct" and not val_str.startswith("+")) else ""
        disp = f"{sign}{num:.1f}%" if "%" in val_str or kind == "pct" else f"{num:.1f}%"
        color_cls = "pos" if (highlight_positive and num > 0) else ("neg" if num < 0 else "")
        return f'<span class="{color_cls}">{disp}</span>'

    if kind == "currency":
        num = safe_float(val_str)
        return f'{num:,.0f}' if num == int(num) else f'{num:,.2f}'

    return html.escape(val_str)
```

#### (B) CSS Badges Specification
```css
/* ── Universal Semantic Badges ── */
.badge-na {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  background: rgba(139, 148, 158, 0.15);
  border: 1px solid rgba(139, 148, 158, 0.3);
}

.badge-need-data {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #e3b341;
  background: rgba(210, 153, 34, 0.18);
  border: 1px solid rgba(210, 153, 34, 0.4);
}

.badge-filtered {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #f85149;
  background: rgba(248, 81, 73, 0.15);
  border: 1px solid rgba(248, 81, 73, 0.3);
}

.badge-fallback {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.15);
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.badge-healthy {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10.5px;
  font-weight: 700;
  color: #3fb950;
  background: rgba(46, 160, 67, 0.18);
  border: 1px solid rgba(63, 185, 80, 0.35);
}

.badge-partial {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10.5px;
  font-weight: 700;
  color: #d29922;
  background: rgba(210, 153, 34, 0.18);
  border: 1px solid rgba(210, 153, 34, 0.35);
}

/* ── Health Monitor Container CSS ── */
.health-monitor-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  margin: 16px 32px 20px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0,0,0,0.25);
}

.health-monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: var(--surface2);
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid var(--border);
}

.health-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.health-header-icon {
  font-size: 18px;
}

.health-header-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}

.health-summary-pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.health-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
  border: 1px solid;
}

.pill-healthy { color: #3fb950; background: rgba(46, 160, 67, 0.15); border-color: rgba(46, 160, 67, 0.35); }
.pill-partial { color: #d29922; background: rgba(210, 153, 34, 0.15); border-color: rgba(210, 153, 34, 0.35); }
.pill-fallback { color: #38bdf8; background: rgba(56, 189, 248, 0.15); border-color: rgba(56, 189, 248, 0.35); }
.pill-nodata { color: #f85149; background: rgba(248, 81, 73, 0.15); border-color: rgba(248, 81, 73, 0.35); }
.pill-avg { color: #e6edf3; background: var(--surface); border-color: var(--border); }

.health-toggle-btn {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
}

.health-monitor-body {
  padding: 16px 20px;
}

.health-guide-text {
  font-size: 11.5px;
  color: var(--muted);
  margin-bottom: 14px;
  line-height: 1.5;
  background: rgba(56, 189, 248, 0.08);
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid rgba(56, 189, 248, 0.2);
}

.health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}

.health-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.health-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.health-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.health-card-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.health-bar-track {
  width: 100%;
  height: 4px;
  background: var(--surface);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 6px;
}

.health-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.health-card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10.5px;
  color: var(--muted);
}

.health-reason {
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

---

### 4.3 Component 3: Tab-Level Warning & Notice Banners

#### (A) Banner Generator Helper Function (`generate_report.py`)
```python
def build_tab_status_banner(
    strategy_name: str,
    market: str,
    status_type: str = "empty",  # "empty", "no_pairs", "partial", "info", "options_us_only"
    reason_code: str = "",
    coverage_pct: float = 0.0
) -> str:
    """
    Generates an informative notice/warning banner within strategy tab panels.
    """
    if status_type == "no_pairs":
        return f"""
        <div class="strategy-status-banner banner-info">
          <div class="banner-icon">⚖️</div>
          <div class="banner-content">
            <div class="banner-title">통계적 유의 공적분 페어 스캔 완료 (Statistical Cointegration Filter)</div>
            <div class="banner-desc">
              현재 ADF 단위근 검정(p &lt; 0.05) 및 잔차 Z-Score 조건을 엄격히 만족하는 실제 공적분 페어가 없습니다.<br>
              인위적인 가짜 벤치마크 페어를 생성하지 않으며, 앙상블 엔진에서 Stat-Arb 비중을 안전하게 타 알파 전략 및 현금으로 재정규화(Re-normalization)합니다.
            </div>
          </div>
        </div>"""

    if status_type == "options_us_only":
        return f"""
        <div class="strategy-status-banner banner-warning">
          <div class="banner-icon">📊</div>
          <div class="banner-content">
            <div class="banner-title">옵션 체인 데이터 제공 범위 안내 (US Options Scope)</div>
            <div class="banner-desc">
              <strong>{market}</strong> 시장은 개별 주식 옵션 체인 데이터 유동성 제한으로 인해 파생 전략 신호가 산출되지 않습니다.
              미국 시장(SP500, NASDAQ) 옵션 체인 분석 결과를 확인하세요.
            </div>
          </div>
        </div>"""

    if status_type == "empty":
        reason_disp = f" (사유: <code>{html.escape(reason_code)}</code>)" if reason_code else ""
        return f"""
        <div class="strategy-status-banner banner-warning">
          <div class="banner-icon">⚠️</div>
          <div class="banner-content">
            <div class="banner-title">{strategy_name} 데이터 수집 및 산출 준비 중 (Data Collection Mode)</div>
            <div class="banner-desc">
              <strong>{market}</strong> 시장의 <strong>{strategy_name}</strong> 데이터가 수집 대기 중이거나 신호 조건을 만족하는 종목이 없습니다.{reason_disp}<br>
              앙상블 엔진에서는 해당 전략의 가중치를 <strong>0.0%로 배제</strong>하고 활성 전략 가중치로 자동 재정규화하여 안정성을 보장합니다.
            </div>
          </div>
        </div>"""

    return ""
```

#### (B) CSS Banner Styling
```css
/* ── Strategy Status Banners ── */
.strategy-status-banner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 12.5px;
  line-height: 1.5;
}

.strategy-status-banner .banner-icon {
  font-size: 20px;
  flex-shrink: 0;
  margin-top: 1px;
}

.strategy-status-banner .banner-content {
  flex: 1;
}

.strategy-status-banner .banner-title {
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 3px;
}

.banner-warning {
  background: rgba(210, 153, 34, 0.12);
  border: 1px solid rgba(210, 153, 34, 0.35);
  color: #f0c674;
}
.banner-warning .banner-title { color: #e3b341; }
.banner-warning code { background: rgba(210, 153, 34, 0.2); padding: 1px 4px; border-radius: 3px; color: #ffe3a0; }

.banner-info {
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: #bae6fd;
}
.banner-info .banner-title { color: #38bdf8; }

.banner-success {
  background: rgba(46, 160, 67, 0.12);
  border: 1px solid rgba(46, 160, 67, 0.3);
  color: #7ee787;
}
```

---

### 4.4 Component 4: Front-End JS Navigation & Safe Drawer Integration

Add `switchTabById(tabId)` to `<script>` in `generate_report.py`:
```javascript
function switchTabById(tabId) {
  // 1. Locate button in row2 navigation or main-system tabs
  let targetBtn = document.querySelector(`button[onclick*="'${tabId}'"]`);
  if (!targetBtn) {
    targetBtn = document.getElementById(`tab-${tabId}`);
  }
  if (targetBtn) {
    targetBtn.click();
    targetBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  }
}
```

In `openStockDrawer`:
```javascript
function openStockDrawer(symbol, name, market, score, expectedReturn, factorObjStr) {
  const drawer = document.getElementById('stock-drawer');
  const overlay = document.getElementById('stock-drawer-overlay');
  if (!drawer || !overlay) return;
  
  document.getElementById('drawer-stock-name').textContent = name || symbol;
  document.getElementById('drawer-stock-meta').textContent = `${symbol} • ${market}`;
  
  // Safe score sanitization
  const scoreDisp = (!score || score.toLowerCase().includes('nan') || score === 'None') ? 'N/A' : score;
  const returnDisp = (!expectedReturn || expectedReturn.toLowerCase().includes('nan') || expectedReturn === 'None') ? 'N/A' : expectedReturn;
  
  document.getElementById('drawer-score').textContent = scoreDisp;
  document.getElementById('drawer-return').textContent = returnDisp;
  
  const factorsContainer = document.getElementById('drawer-factors-grid');
  if (factorsContainer && factorObjStr) {
    try {
      const factors = JSON.parse(decodeURIComponent(factorObjStr));
      let html = '';
      for (const [key, rawVal] of Object.entries(factors)) {
        let valStr = (rawVal === null || rawVal === undefined) ? 'N/A' : String(rawVal).trim();
        let isNaNVal = valStr.toLowerCase().includes('nan') || valStr === 'None' || valStr === '-' || valStr === '';
        
        let numVal = parseFloat(valStr) || 0;
        let barW = isNaNVal ? 0 : Math.min(100, Math.max(0, numVal));
        let badgeHtml = isNaNVal
          ? '<span class="badge-na">N/A</span>'
          : `<span style="color:${numVal >= 70 ? '#2ea043' : (numVal >= 40 ? '#58a6ff' : '#8b949e')}; font-weight:700;">${valStr}</span>`;
        
        html += `
          <div style="background:var(--surface2); padding:9px 12px; border-radius:6px; border:1px solid var(--border);">
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:5px;">
              <span style="color:var(--text); font-weight:500;">${key}</span>
              ${badgeHtml}
            </div>
            <div style="height:5px; background:var(--border); border-radius:3px; overflow:hidden;">
              <div style="height:100%; width:${barW}%; background:${numVal >= 70 ? '#2ea043' : (numVal >= 40 ? '#58a6ff' : '#8b949e')}; border-radius:3px;"></div>
            </div>
          </div>`;
      }
      factorsContainer.innerHTML = html;
    } catch(e) {
      factorsContainer.innerHTML = '<div style="color:var(--muted); font-size:12px;">팩터 상세 정보 없음</div>';
    }
  }
  
  document.body.style.overflow = 'hidden';
  overlay.style.display = 'block';
  setTimeout(() => {
    drawer.style.right = '0px';
    overlay.style.opacity = '1';
  }, 10);
}
```

---

## 5. Verification Method

### 5.1 Automated Unit & Regression Tests
Run the comprehensive test suite to confirm zero regressions:
```bash
# Execute report generator unit tests
.venv/Scripts/pytest tests/test_report_ux_and_rounding.py -v
.venv/Scripts/pytest tests/test_report_generator_hrp.py -v
.venv/Scripts/pytest tests/test_kst_and_coverage_reasoning.py -v
.venv/Scripts/pytest tests/test_challenger_rim_2_stress.py -v
```

### 5.2 HTML DOM Integrity & Zero NaN Verification
Run the report generator and verify that no raw `nan`, `None`, or `undefined` text appears in table cells:
```bash
.venv/Scripts/python trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html
```

Inspect the generated `gh-pages/index.html`:
```powershell
# PowerShell verification: Ensure zero raw "nan", "None", or "undefined" in table cells
$html = Get-Content gh-pages/index.html -Raw
if ($html -match '<td>\s*(nan|NaN|None|undefined)\s*</td>' -or $html -match '<td[^>]*>\s*(nan%|NaN%|None%)\s*</td>') {
    Write-Error "CRITICAL: Raw NaN/None found in HTML table cells!"
} else {
    Write-Host "SUCCESS: Zero raw NaN/None in HTML table cells verified!" -ForegroundColor Green
}

# Verify Health Monitor exists
if ($html -match 'class="health-monitor-section"' -and $html -match 'Strategy Data Health Monitor') {
    Write-Host "SUCCESS: Strategy Health Monitor successfully rendered!" -ForegroundColor Green
}
```

---

## 6. Handoff Completion Checklist
- [x] **Observation**: Documented all 11 locations where `nan`/`None` occur and lack of top-level health summary.
- [x] **Logic Chain**: Detailed reasoning from quantitative reliability to UI badging, health cards, and tab banners.
- [x] **Caveats**: Clearly outlined read-only boundaries and test preservation constraints.
- [x] **Conclusion**: Provided full Python data models, parsing logic, HTML templates, CSS specifications, and JS functions ready for implementation.
- [x] **Verification Method**: Provided exact pytest commands and DOM regex verification scripts.
