# Survey Report: Requirement R3 — GitHub Pages Dashboard Metric Consolidation & UX Enhancement

- **Author**: Teamwork Explorer (`teamwork_preview_explorer_survey_3`)
- **Date**: 2026-08-31
- **Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\`
- **Target Subsystem**: `trading_system/generate_report.py`, `trading_system/src/pipeline/reporter.py`, `gh-pages/index.html`

---

## 1. Executive Summary

Requirement **R3 (GitHub Pages Dashboard Metric Consolidation & UX Enhancement)** addresses the visual fragmentation and cognitive load in the current multi-factor stock prediction dashboard. As the trading system expanded to **31 multi-factor strategies across 5 major markets** (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000), related quantitative indicators, risk metrics, coverage statuses, and portfolio execution parameters became scattered across separate headers, strips, accordions, sidebars, and sub-tabs.

This survey establishes the complete blueprint for consolidating fragmented metrics into **3 Core Unified Consolidated Cards**:
1. **Card 1: Market Regime & Risk Gates Console (`🌐 2D Market Regime & Risk Gates`)** — Integrates dual-market 2D regime state (6-regime matrix), macro indicators with fallback badges, Crisis Detector levels, VIX velocity / term structure gating, and dynamic strategy weights / decision rationales into a single macro command center.
2. **Card 2: Strategy Coverage & Missingness Diagnostic Center (`🩺 Strategy Coverage & Data Health Diagnostic Center`)** — Combines 31-strategy health monitor, dynamic progress bars, missingness reason categorizations, symbol-level diagnostics, zero-weight safeguard notices, and combinatorial CPCV / PBO overfitting stress test diagnostics into an interactive data integrity hub.
3. **Card 3: Portfolio Optimization & Execution OMS Command Center (`💼 Portfolio Optimization & Execution OMS`)** — Unifies Hierarchical Risk Parity (HRP) / Black-Litterman asset allocation donut and exposure charts with EVT-GPD CVaR tail risk budgeting, Leland dynamic no-trade buffer bands (±2.5%), closed-loop realized slippage feedback by market (from `trade_logs.db`), and compact sortable execution order tables.

---

## 2. Current Architecture & Metric Fragmentation Analysis

### 2.1 Current File & Component Mapping
- **`trading_system/generate_report.py`**:
  - Primary dashboard generator (~5,159 lines) that parses text prediction files, DB histories, and stress test logs, generating `gh-pages/index.html`.
  - Parses: `ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, `portfolio_allocation.txt`, `backtest_summary.json`, `run_snapshot.json`, and individual strategy files.
  - Implements: `build_html()`, `parse_strategy_coverage_report()`, `build_strategy_health_monitor_html()`, `parse_portfolio_allocation()`, `build_history_section()`, and `largest_remainder_round()`.
- **`trading_system/src/pipeline/reporter.py`**:
  - `PipelineReporter` component invoked by `run_pipeline.py` to write `ensemble_predictions.txt` and `strategy_data_coverage_report.txt`.
- **`gh-pages/index.html`**:
  - The live interactive GitHub Pages dashboard artifact (~5.78 MB, 42,460 lines).

### 2.2 Fragmentation Breakdown Across the 3 Functional Domains

| Functional Domain | Current Scattered Locations | Identified Deficiencies & UX Gaps |
|---|---|---|
| **Market Regime & Risk Gates** | • Top Header (`.header-meta`): US/KR badges<br>• Macro Strip (`.macro-strip`): 8 macro numbers<br>• Sidebar (`.rationale-card`): Text rationale<br>• Tab `#panel-regime`: Matrix & parameters | • User must jump across 4 separate areas to understand the market regime.<br>• Crisis Detector levels (`NONE`/`WATCH`/`ACTIVE`/`SEVERE`) and VIX velocity gating are hidden in log files.<br>• VIX fast shock overrides and target cash ratios are not visually correlated with macro variables. |
| **Strategy Coverage & Health** | • Guide accordion (`.strat-guide-card`)<br>• Health monitor (`.health-monitor-section`)<br>• Milestone 3 CPCV / PBO text in `strategy_data_coverage_report.txt` | • No interactive filtering of health cards by status (Healthy/Partial/Fallback/No Data).<br>• Missingness reasons are shown as raw English codes without clear Korean explanations.<br>• CPCV Overfitting probability (PBO) and macro crisis stress test results are omitted from the UI. |
| **Portfolio & Execution OMS** | • Tab `#panel-portfolio`: HRP donut, market bar, position table<br>• Milestone 4 Slippage report in text files<br>• Allocator EVT-CVaR & Leland bands in Python code | • EVT-GPD CVaR tail risk metrics (95%/99% VaR/CVaR, Clayton copula tail dependence) are absent from dashboard.<br>• Real-time slippage feedback by market (`trade_logs.db`) is not shown.<br>• Leland no-trade buffer bands (`±2.5%`) are not indicated in the position table. |

---

## 3. Blueprint for Consolidated Card 1: Market Regime & Risk Gates

### 3.1 Structural Component Layout
```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🌐 CARD 1: 2D Market Regime & Risk Gates (시장 환경 & 리스크 제어 콘솔)                       │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Top Row: Dual-Market Regime & Crisis Detector Status Badges]                                │
│ 🇺🇸 US: 🟢 BULL_LOW_VOL    🇰🇷 KR: 🟢 BULL_LOW_VOL    ⚡ DECOUPLED (-0.19)   🛡️ Crisis: NONE  │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Middle Grid: Global Macro Indicators & VIX Dynamics (with Fallback Badges & Tooltips)]      │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│ │ S&P 500 20d   │ │ KOSPI 20d     │ │ VIX & Vel.    │ │ USD/KRW FX    │ │ US 10Y (TNX)  │   │
│ │ +0.189% / day │ │ +1.056% / day │ │ 14.50 (-2.1%) │ │ 1,371.84 KRW  │ │ 4.67%         │   │
│ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘   │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│ │ KR 10Y Yield  │ │ WTI Crude Oil │ │ Gold ETF      │ │ Max Allocation│ │ Target Cash   │   │
│ │ 2.83%         │ │ $83.54 / bbl  │ │ $220 [기본값] │ │ 85.0%         │ │ 15.0%         │   │
│ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Risk Defense & Gating Status Bars]                                                         │
│ • VIX Fast Shock Gate: Normal (VIX < 25.0, Threshold: 30.0 / 15% Spike)                     │
│ • Macro Composite Score: 0.18 / 1.00 (Safe) | Drawdown Speed: 0.0%/5d                        │
│ • Intraday Stop-Loss Monitoring: Active (0 Symbols Triggered)                               │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Collapsible 2D Regime Matrix (Left) & Strategy Decision Rationale (Right)]                 │
│ ┌──────────────────────────────────────────────┐ ┌────────────────────────────────────────┐ │
│ │ 6-Regime Direction x Volatility Matrix       │ │ 🧠 AI Strategy Decision Rationale      │ │
│ │ • 🟢 BULL_LOW_VOL  (🇺🇸 US 현재 / 🇰🇷 KR 현재) │ │ • High Momentum & Trend Quality Focus  │ │
│ │ • 🟡 SIDEWAYS_LOW_VOL                        │ │ • Stat-Arb & Mean Reversion Scaled     │ │
│ │ • 🔴 BEAR_HIGH_VOL                           │ │ • Zero-weighting 6 Incomplete Factors  │ │
│ └──────────────────────────────────────────────┘ └────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 HTML/CSS/JS Specification for Card 1
- **CSS Classes**:
  - `.regime-risk-card`: Main card container with surface gradient `#161b22` and border `#30363d`.
  - `.regime-badge-strip`: Flex-wrap strip with high-contrast pills (`.badge-regime-us`, `.badge-regime-kr`, `.badge-crisis-none`, `.badge-crisis-watch`, `.badge-crisis-active`, `.badge-crisis-severe`).
  - `.macro-metric-grid`: Auto-fit CSS Grid (`minmax(140px, 1fr)`) with subtle hover elevation (`transform: translateY(-2px)`).
  - `.gate-status-strip`: Compact status bar showcasing real-time gate pass/fail conditions with pulse indicators (`● Normal`).
- **Interactive Tooltips**:
  - Accessible click/hover tooltips on Decoupling Status, VIX Velocity, and Fallback Badges.
- **Collapsible Toggle**:
  - Interactive accordion for the full 2D Regime Matrix and AI Decision Rationale to preserve vertical screen space on mobile devices.

---

## 4. Blueprint for Consolidated Card 2: Strategy Coverage & Missingness Diagnosis

### 4.1 Structural Component Layout
```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🩺 CARD 2: Strategy Coverage & Missingness Diagnosis (31대 전략 커버리지 & 결측 진단 센터) │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Health Summary Header & Interactive Filter Pills]                                          │
│ Total Universe: 948 종목 (KOSPI/KOSDAQ/SP500/NASDAQ/RUSSELL2000) | Avg Coverage: 78.9%     │
│ [🟢 Healthy (21)]   [🟡 Partial (2)]   [🟠 Fallback (2)]   [🔴 Need Data (6)]   [All (31)]   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Data Integrity Safeguard Notice]                                                           │
│ 💡 결측/수집대기 전략은 앙상블 엔진에서 자동 제로 가중치(0.0%) 처리 및 활성 전략으로       │
│    자동 재정규화되어 포트폴리오 왜곡을 원천 방지합니다.                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [31-Strategy Interactive Health & Coverage Grid (Click Card -> Smooth Tab Jump)]            │
│ ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐                  │
│ │ 1. XGBoost 회귀 🟢   │ │ 2. Surge 분류기 🟢   │ │ 9. RIM Valuation 🔴  │                  │
│ │ [██████████] 100.0%  │ │ [██████████] 100.0%  │ │ [          ] 0.0%    │                  │
│ │ 유효 948 / 결측 0    │ │ 유효 948 / 결측 0    │ │ 유효 0 / 결측 948    │                  │
│ │ 🏷️ 전체 정상 산출    │ │ 🏷️ 전체 정상 산출    │ │ 🏷️ 재무제표 수집대기 │                  │
│ └──────────────────────┘ └──────────────────────┘ └──────────────────────┘                  │
│ (... 31 strategy cards dynamically filtered by active status pill ...)                      │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Missingness Reason Distribution & Symbol Diagnostics]                                      │
│ • 과거 주가 데이터 부족 (INSUFFICIENT_PRICE_HISTORY): 신규 상장주 / 60일 미만 (64건)        │
│ • 재무제표 공시 대기 (NO_FUNDAMENTAL_DATA): 동적 Filing Lag (KRX 45d, US 40d) 대기 (948건) │
│ • 미국 시장 전용 팩터 (NON_US_MARKET_SCOPE): 한국 시장 옵션 체인 미제공 (KOSPI/KOSDAQ)     │
│ • 공적분 페어 미발견 (NO_COINTEGRATED_PAIR): 통계적 유의 공적분 페어 없음 (p > 0.05)        │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Milestone 3: Model Stress Testing & Overfitting Diagnostics (CPCV & PBO)]                  │
│ • Probability of Backtest Overfitting (PBO): 0.00% (Overfitted: False, 15 Folds)            │
│ • 2008 금융위기 Stress: MDD 217.3%, 95% CVaR -7.89% (FAIL)                                  │
│ • 2020 코로나 Stress: MDD 130.2%, 95% CVaR -13.33% (FAIL)                                   │
│ • Position Capacity Multiplier: 0.75x (Stress-Gated Protection Applied)                     │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 HTML/CSS/JS Specification for Card 2
- **Dynamic Status Filter JS**:
  - `filterHealthCards(status)`: Filters the 31 cards in `.health-grid` by clicking summary pills (`all`, `healthy`, `partial`, `fallback`, `nodata`).
- **Direct Tab Jump Navigation**:
  - `switchTabById(tabId)`: Smoothly transitions the active tab to the chosen strategy and scrolls the strategy panel into view.
- **Progress Bar Styling**:
  - Multi-tier color coding: Green (`#2ea043` for $\ge 70\%$), Yellow (`#d29922` for $10\sim 69\%$), Blue (`#38bdf8` for $1\sim 9\%$), Red (`#f85149` for $0\%$).
- **CPCV Stress Test Section**:
  - Compact data table displaying historical macro stress scenarios with VaR/CVaR numbers and capacity multiplier status.

---

## 5. Blueprint for Consolidated Card 3: Portfolio Optimization & Execution OMS

### 5.1 Structural Component Layout
```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 💼 CARD 3: Portfolio Optimization & Execution OMS (포트폴리오 최적화 & 실행 OMS)            │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Portfolio Executive Summary Metrics Strip]                                                 │
│ Total Capital: 1,000,000,000 KRW/USD | Target Horizon: 20D | Allocated: 85.0% (850M)        │
│ Remaining Cash: 15.0% (150M) | Expected Return: +38.6% | Volatility: 12.4% | Sharpe: 2.68   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Allocation Visualizations: Donut & Exposure Charts]                                        │
│ ┌──────────────────────────────────────────────┐ ┌────────────────────────────────────────┐ │
│ │ 📊 HRP Risk Parity Allocation Weights        │ │ 🌐 Market Exposure Breakdown           │ │
│ │ [ Donut Chart: Top Stocks + Remaining Cash ] │ │ [ Bar Chart: KOSPI/KOSDAQ/US/CASH ]    │ │
│ └──────────────────────────────────────────────┘ └────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Tail Risk EVT-CVaR & Leland Buffer Bands Panel]                                            │
│ ┌──────────────────────────────────────────────┐ ┌────────────────────────────────────────┐ │
│ │ 🛡️ EVT-GPD Tail Risk Budgeting               │ │ ⚙️ Leland No-Trade Buffer Bands & Cost  │ │
│ │ • 95% Parametric VaR / CVaR: -4.12% / -5.84% │ │ • Dynamic Band: ±2.50% No-Trade Band   │ │
│ │ • 99% Extreme Value GPD CVaR: -9.51%         │ │ • Rebalance Bypass: New/Exit Active    │ │
│ │ • Clayton Copula Lower Tail (λL): 0.32       │ │ • STT / SEC / Spread Friction: Applied │ │
│ └──────────────────────────────────────────────┘ └────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [Milestone 4: Real-time Closed-Loop Slippage Feedback & OMS Engine]                         │
│ • OMS 7 Safety Gates: 🟢 PASSED (Spread, Liquidity, Stale, Circuit, MDD, Size, Limit)      │
│ • Realized Average Slippage: 5.0 bps (30D trade_logs.db analysis)                           │
│ • Market Slippage Map: KOSPI 5.0bps | KOSDAQ 8.0bps | SP500 3.0bps | NASDAQ 4.0bps          │
│ • Execution Algorithm: Almgren-Chriss Optimal Slicing & TWAP/VWAP Scheduler                 │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ [HRP Position Allocation & Execution Orders Table]                                          │
│ Rank | Symbol | Name      | Market | Exp. Return | Volatility | Weight % | Capital | Leland Band │
│ #1   | 0131D0 | 키움스팩2호 | KOSDAQ | +1125.1%    | 0.19%      | 5.67%    | 56.7M   | 🟢 BUY (New) │
│ #2   | 048830 | 엔피케이   | KOSDAQ | +1063.4%    | 0.24%      | 5.67%    | 56.7M   | 🟢 BUY (New) │
│ ...                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 HTML/CSS/JS Specification for Card 3
- **Chart.js Integration**:
  - `hrpDonutChart`: Interactive doughnut chart rendering position weights with remaining cash clearly highlighted.
  - `marketExposureChart`: Bar chart showing cross-market exposure breakdown (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000, CASH).
- **Leland Band Status Tags**:
  - Table badges: `🟢 BUY (New Entry)`, `🟡 HOLD (Within ±2.5% Band)`, `🔄 REBALANCE (Drift Exceeded)`, `🔴 EXIT (Full Liquidation)`.
- **OMS 7-Safety Gates Visual Badges**:
  - Real-time safety validation indicator badges for spread, liquidity, stale data, circuit breaker, drawdown limit, position size cap, and order price limit.

---

## 6. Responsive Styling, Badges, Tooltips & 31-Strategy Tab UX

### 6.1 Responsive Breakpoints & CSS Architecture
1. **Desktop ($> 1200\text{ px}$)**:
   - Max width: `1600px`, centered container with `padding: 24px 32px`.
   - 2-column and 3-column CSS Grid layouts for macro strips, risk matrices, and charts.
2. **Tablet ($768\text{ px} \sim 1199\text{ px}$)**:
   - 2-column layouts for charts and health cards.
   - Horizontal scrolling tables (`.table-wrap`) with sticky header row (`th { position: sticky; top: 0; }`).
3. **Mobile ($< 768\text{ px}$)**:
   - Single-column card stacking.
   - Sticky navigation tab bar with horizontal smooth swipe (`overflow-x: auto; -webkit-overflow-scrolling: touch;`).
   - Compact table cells with abbreviated metric labels and touch-friendly targets ($\ge 44\text{ px}$).

### 6.2 Canonical 31-Strategy Standard Tab Sequence
To fulfill Requirement R2 and guarantee consistency with R3, the strategy tabs are arranged in strictly canonical numerical order:

```
[1. Regression] [2. Surge] [3. Lead-Lag] [4. VCP Rule] [5. VCP ML] [6. Strict LSTM]
[7. Stat-Arb] [8. Sector Rotation] [9. RIM Valuation] [10. Event-Driven] [11. MQ Factor]
[12. Options IV Skew] [13. Order Flow] [14. ST Reversal] [15. ARM Factor] [16. CARD Factor]
[17. LATR Factor] [18. Inst & Foreign] [19. Supply Chain] [20. NLP Sentiment]
[21. Factor Neutralized] [22. Vol Targeting] [23. Microstructure] [24. Accruals Quality]
[25. Short Squeeze] [26. Value-Up Yield] [27. Trend Efficiency] [28. Gamma Squeeze]
[29. Insider Buying] [30. Darkpool & HFT] [31. Tone Drift]
```

### 6.3 Interactive Stock Drawer Modal
- When a user clicks any stock row in the 31-Ensemble table, Scenario Simulator, or Portfolio table, `#stock-drawer` smoothly slides in from the right edge.
- Displays:
  - Header: Stock Code, Korean Name, Market Flag, Naver/Yahoo external link.
  - Scores: 31-Strategy Ensemble Score & 20D Expected Return.
  - 31-Factor Decomposition: Bar chart or compact grid showing normalized percentile scores across all 31 individual strategies.
  - Mobile gesture: Swipe right to dismiss (`touchstart`, `touchmove`, `touchend` event handlers).

---

## 7. Implementation Roadmap & Verification Plan

### 7.1 Proposed Code Modifications in `trading_system/generate_report.py`
1. **Refactor `build_html()`**:
   - Replace disconnected `.macro-strip`, `.header-meta`, and `#panel-regime` fragments with unified **Card 1: Market Regime & Risk Gates Console**.
   - Enhance `build_strategy_health_monitor_html()` to render **Card 2: Strategy Coverage & Missingness Diagnostic Center** with interactive status filtering and CPCV/PBO stress testing tables.
   - Refactor `#panel-portfolio` into **Card 3: Portfolio Optimization & Execution OMS Command Center** incorporating EVT-CVaR metrics, Leland buffer band tags, and Milestone 4 closed-loop slippage maps.
2. **Synchronize Canonical 31-Strategy Sequence**:
   - Align strategy lists in `STRATEGY_METADATA`, table headers, tab navigation, and stock drawer factor dictionaries.
3. **Preserve Regression Safety & Test Compatibility**:
   - Ensure all existing assertions in `test_report_generator_hrp.py` and `test_report_ux_and_rounding.py` remain 100% compliant.

### 7.2 Verification Protocol
- **Unit Test Execution**:
  ```bash
  .venv/Scripts/pytest tests/test_report_generator_hrp.py tests/test_report_ux_and_rounding.py -v
  ```
- **Full Test Suite Run**:
  ```bash
  .venv/Scripts/pytest tests/ -v
  ```
- **Dashboard Artifact Generation**:
  ```bash
  .venv/Scripts/python trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html
  ```
- **Verification Script**:
  ```bash
  .venv/Scripts/python -c "import html; assert open('gh-pages/index.html', encoding='utf-8').read().count('health-card') >= 31"
  ```

---

## 8. Conclusion

The proposed layout consolidation transforms the dashboard from a collection of fragmented panels into a high-density, professional quantitative trading console. By grouping related indicators into the 3 Target Consolidated Cards, users gain immediate situational awareness of market regime and risk gates (Card 1), full transparency into strategy data coverage and missingness (Card 2), and complete visibility into portfolio optimization and execution OMS parameters (Card 3).
