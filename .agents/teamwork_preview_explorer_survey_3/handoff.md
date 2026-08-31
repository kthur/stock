# 5-Component Handoff Report: R3 Dashboard Metric Consolidation & UX Enhancement

- **Author**: Teamwork Explorer (`teamwork_preview_explorer_survey_3`)
- **Recipient**: Parent Caller (`parent`, `b672d6c7-56c6-40df-9cff-af49d8b4ec1c`)
- **Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\`
- **Date**: 2026-08-31T23:54:00+09:00 (UTC: 2026-08-31T14:54:00Z)
- **Handoff Type**: Hard (Task Complete)

---

## 1. Observation

1. **Dashboard Generator Structure (`trading_system/generate_report.py`)**:
   - `generate_report.py:2200-2319`: Renders the macro strip (`.macro-strip` and `.macro-grid`) containing 8 macro indicators (`S&P500 20d Ret`, `VIX`, `USD/KRW`, `US 10Y`, `KR 10Y`, `WTI`, `Gold`, `최대허용배분`) and Decoupling tooltip.
   - `generate_report.py:2231-2255`: Renders the AI Strategy Decision Rationale accordion (`.rationale-card`).
   - `generate_report.py:1484-1554`: Renders the `build_strategy_health_monitor_html()` section with summary pills (Healthy/Partial/Fallback/No Data) and 31 health cards.
   - `generate_report.py:2320-2358`: Builds the HRP portfolio table rows and computes donut/bar chart weights.
   - `generate_report.py:3400-3407`: Defines main system tabs: `#tab-ensemble`, `#tab-portfolio`, `#tab-backtest`, `#tab-regime`, `#tab-scenario`, `#tab-history`.
   - `generate_report.py:3551-3604`: Renders `#panel-regime` with US/KR dynamic weights and the 2D Market Regime Dynamic Matrix.
   - `generate_report.py:3727-3762`: Defines the 31 canonical strategy tab buttons.
   - `generate_report.py:4690-4819`: Implements the sliding Stock Drawer modal displaying detailed 31-factor decomposition.

2. **Underlying Data Layers & Outputs**:
   - `trading_system/result/strategy_data_coverage_report.txt:1-117`: Contains 37 evaluated strategy coverage rows, Milestone 3 CPCV Combinatorial Folds & Overfitting PBO (0.00%) + Historical Stress Test Scenarios (2008 Crisis, 2020 COVID, 2022 Fed Hike), Milestone 4 Closed-Loop Slippage report (`trade_logs.db` average 5.0 bps, market slippage map), and Milestone 5 NLP sentiment metrics.
   - `trading_system/portfolio_allocation.txt:1-29`: Outputs HRP / Kelly optimized portfolio allocations, market regime, total capital, target horizon (20d), weight %, and remaining cash.
   - `trading_system/ensemble_predictions.txt:1-132`: Contains Executive Market Summary, 2D regime code, global macro indicator basis, applied strategy weights, and Top 20 picks per market.

3. **Verification Command & Result**:
   - Ran unit test suite: `.venv\Scripts\pytest tests/test_report_generator_hrp.py tests/test_report_ux_and_rounding.py -v`
   - Result: `23 passed in 19.25s (100% PASS)`.

---

## 2. Logic Chain

1. **Premise (From Observation 1 & 2)**: Currently, related market indicators, risk gates, strategy coverage, and portfolio execution metrics are split across `.header-meta`, `.macro-strip`, `.strat-guide-card`, `.health-monitor-section`, `.strategy-sidebar`, and multiple tab panels (`#panel-portfolio`, `#panel-regime`).
2. **Inference**: Grouping these scattered metrics into 3 Target Consolidated Cards directly aligns with Requirement R3 and drastically reduces user cognitive friction without altering the underlying data calculation pipeline:
   - **Card 1: Market Regime & Risk Gates** consolidates dual-market 2D regime badges, Crisis Detector levels, VIX velocity / term structure gating, macro indicators, and decision rationale into a unified top-tier console.
   - **Card 2: Strategy Coverage & Missingness Diagnosis** consolidates the 31-strategy health monitor, dynamic status filtering, missingness reason categorizations, symbol diagnostics, and Milestone 3 CPCV/PBO stress testing into an interactive data integrity center.
   - **Card 3: Portfolio Optimization & Execution OMS** consolidates HRP/Black-Litterman allocations, EVT-CVaR tail risk budgeting, Leland dynamic no-trade buffer bands (±2.5%), and Milestone 4 closed-loop realized slippage feedback into a unified execution command center.
3. **Inference**: Standardizing tab sequences in canonical numerical order (1. Regression ~ 31. Tone Drift) satisfies Requirement R2 while seamlessly integrating with the consolidated cards and stock drawer modal.
4. **Validation (From Observation 3)**: All existing report generator tests (`test_report_generator_hrp.py` and `test_report_ux_and_rounding.py`) pass without failure, confirming the stability of existing HTML generator interfaces.

---

## 3. Caveats

- **Investigation Boundary**: This survey investigated the reporting and visualization layer (`trading_system/generate_report.py`, `src/pipeline/reporter.py`, and `gh-pages/index.html`) as well as the underlying data outputs (`strategy_data_coverage_report.txt`, `portfolio_allocation.txt`, `ensemble_predictions.txt`). Core model training scripts and data seeding pipelines (R1) were examined for data interfaces but are surveyed independently.
- **Assumptions**: Assumed that `strategy_data_coverage_report.txt` and `portfolio_allocation.txt` continue to be generated by `run_pipeline.py` / `reporter.py` with standard section headers.
- **Alternative Interpretations**: Considered keeping `#panel-regime` as a standalone tab; concluded that consolidating its core information directly into Card 1 while keeping the full matrix collapsible within Card 1 offers vastly superior UX density.

---

## 4. Conclusion

Requirement R3 can be implemented cleanly in `trading_system/generate_report.py` by structuring the dashboard layout around the 3 Target Consolidated Cards. All necessary quantitative inputs (2D regime, Crisis Detector, VIX dynamics, 31-strategy health/coverage, CPCV/PBO stress tests, HRP allocations, EVT-CVaR metrics, Leland buffer bands, and real-time slippage maps) are already computed by backend engines and output to result text files or SQLite DBs.

The detailed design specification, HTML/CSS structure, responsive rules, and interaction patterns have been documented in `survey_report.md`.

---

## 5. Verification Method

To independently verify the findings of this survey:
1. **Inspect Survey Report**:
   - File path: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\survey_report.md`
2. **Execute Unit Tests**:
   ```bash
   .venv\Scripts\pytest tests/test_report_generator_hrp.py tests/test_report_ux_and_rounding.py -v
   ```
   *Expected outcome: 23 passed in ~20s.*
3. **Inspect Existing Dashboard**:
   - View `gh-pages/index.html` lines 500-650 to verify current macro strip and health monitor layout.
