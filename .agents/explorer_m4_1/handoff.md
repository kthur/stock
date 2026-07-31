# Technical Architecture Specification & Implementation Plan: Milestone 4 (R4: Closed-Loop Realized Slippage Execution Feedback)

**Author:** `explorer_m4_1` (Technical Architecture Explorer)  
**Date:** 2026-07-31  
**Milestone:** Milestone 4 (R4: Closed-Loop Realized Slippage Execution Feedback)  
**Target Modules:**
- Primary implementation: `trading_system/src/execution/slippage_feedback.py`
- Root forwarder: `src/execution/slippage_feedback.py`
- Engine integration: `trading_system/src/ai/ensemble_scorer.py`
- Pipeline integration: `trading_system/run_pipeline.py`
- Unit test suites: `trading_system/tests/test_slippage_feedback.py` & `tests/test_slippage_feedback.py`

---

## 1. Observation

### Codebase Inspection & Evidence Base

1. **OMS Engine & Execution Schema** (`trading_system/src/execution/oms_engine.py:25-53, 113-145`):
   - `ExecutionOMSEngine` manages order plans (`order_plans` table) and execution records (`execution_logs` table) in SQLite `trade_logs.db`.
   - Table Schema `order_plans`:
     ```sql
     CREATE TABLE IF NOT EXISTS order_plans (
         order_id TEXT PRIMARY KEY,
         symbol TEXT NOT NULL,
         name TEXT,
         market TEXT,
         action TEXT NOT NULL,
         target_weight REAL NOT NULL,
         target_amount REAL NOT NULL,
         target_price REAL NOT NULL,
         status TEXT NOT NULL,
         created_at TEXT NOT NULL
     )
     ```
   - Table Schema `execution_logs`:
     ```sql
     CREATE TABLE IF NOT EXISTS execution_logs (
         execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
         order_id TEXT NOT NULL,
         symbol TEXT NOT NULL,
         target_price REAL NOT NULL, -- Decision price P_decision
         executed_price REAL NOT NULL, -- Executed price P_executed
         slippage_bps REAL NOT NULL, -- Calculated in OMS as ((executed_price - target_price) / target_price) * 10000.0
         executed_volume INTEGER NOT NULL,
         executed_at TEXT NOT NULL,
         FOREIGN KEY (order_id) REFERENCES order_plans (order_id)
     )
     ```

2. **Microstructure Cost Modeling in `EnsembleScoringEngine`** (`trading_system/src/ai/ensemble_scorer.py:1052-1151`):
   - `EnsembleScoringEngine.calculate_ensemble_score()` computes net expected returns by deducting total microstructure execution costs (`total_cost_pct`).
   - Cost components:
     $$\text{total\_cost\_pct} = \text{stt\_tax} + \text{brokerage\_fee} + \text{clamped\_spread} + (2.0 \times \text{impact\_one\_way})$$
   - Spread model: $\text{dynamic\_spread} = \text{base\_spread} \times (\text{adv\_ratio}^{0.25}) \times (\text{vol\_ratio}^{0.50})$, clamped to $[\text{spread\_min}, \text{spread\_max}]$.
   - Square-root market impact model: $\text{impact\_one\_way} = \text{impact\_coeff} \times \text{volatility} \times \sqrt{\text{participation\_ratio}}$.
   - Return adjustment:
     $$\text{ensemble\_expected\_return} = (\text{raw\_exp\_ret} - \text{cost\_series} \times 100.0).\text{clip}(0.0, 50.0)$$

3. **Pipeline Orchestration** (`trading_system/run_pipeline.py:1761, 2320, 2558-2561`):
   - Line 1761: `scorer = EnsembleScoringEngine(config=cfg)` instantiates the scoring engine.
   - Line 2320: `ensemble_df = scorer.calculate_ensemble_score(...)` executes ensemble prediction scoring.
   - Line 2558-2561: Strategy Data Coverage report and Milestone 3 CPCV stress test report are saved to `strategy_data_coverage_report.txt`.
   - Line 2609-2614: `ExecutionOMSEngine` generates order plans and writes to `trade_logs.db`.

4. **Forwarder Pattern** (`src/risk/portfolio_optimizer.py:1-12`):
   - Clean re-export pattern used across the codebase to allow imports from both `src.*` and `trading_system.src.*`.

---

## 2. Logic Chain

### Step-by-Step Technical Design & Architecture

```
                                 [ SQLite trade_logs.db ]
                                 (execution_logs JOIN order_plans)
                                             │
                                             ▼
                             [ SlippageFeedbackEngine ]
                       calculate_realized_slippage(window_days=30)
                                             │
                                             ▼
                                    [ SlippageMetrics ]
                      ┌──────────────────────┴──────────────────────┐
                      │ avg_slippage_bps                    : float │
                      │ market_impact_alpha                 : float │
                      │ market_slippage_map                 : dict  │
                      │ sample_count                        : int   │
                      │ cost_scaling_factor                 : float │
                      └──────────────────────┬──────────────────────┘
                                             │
                                             ▼
                             [ EnsembleScoringEngine ]
                        update_microstructure_costs(slippage_metrics)
                                             │
                                             ▼
                                [_get_cost_pct Adjustment]
                    cost_series = cost_series * cost_scaling_factor
                    impact_one_way uses empirical market_impact_alpha
                                             │
                                             ▼
                                [ run_pipeline.py Step 11 ]
                 Append [MILESTONE 4: CLOSED-LOOP REALIZED SLIPPAGE REPORT]
                           to strategy_data_coverage_report.txt
```

### Technical Specifications for Modules

#### A. Structured Data Class `SlippageMetrics`
**Location:** `trading_system/src/execution/slippage_feedback.py`

```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class SlippageMetrics:
    """
    Structured container for realized execution slippage and transaction cost metrics.
    """
    avg_slippage_bps: float
    market_impact_alpha: float
    market_slippage_map: Dict[str, float] = field(default_factory=dict)
    sample_count: int = 0
    cost_scaling_factor: float = 1.0
```

#### B. Closed-Loop Feedback Engine `SlippageFeedbackEngine`
**Location:** `trading_system/src/execution/slippage_feedback.py`

- **Constructor**: `__init__(self, db_path: str = "trade_logs.db", window_days: int = 30, default_slippage_bps: float = 5.0)`
- **Primary Method**: `calculate_realized_slippage(self, db_path: Optional[str] = None, window_days: Optional[int] = None) -> SlippageMetrics`

**Calculation Logic & Mathematical Specifications**:
1. **DB Connection & Fallback Handling**:
   - Target DB path resolves `db_path or self.db_path`.
   - If DB file does not exist, table `execution_logs` is missing, or query yields 0 rows:
     - Return default baseline:
       - `avg_slippage_bps = 5.0`
       - `market_impact_alpha = 0.50`
       - `market_slippage_map = {'KOSPI': 5.0, 'KOSDAQ': 5.0, 'SP500': 5.0, 'NASDAQ': 5.0, 'RUSSELL2000': 5.0, 'KONEX': 5.0}`
       - `sample_count = 0`
       - `cost_scaling_factor = 1.0`

2. **SQL Query & Time Filtering**:
   - Filter execution records within the lookback window `window_days`:
     ```sql
     SELECT 
         e.execution_id,
         e.order_id,
         e.symbol,
         e.target_price,
         e.executed_price,
         e.slippage_bps,
         e.executed_volume,
         e.executed_at,
         p.market,
         p.target_amount
     FROM execution_logs e
     LEFT JOIN order_plans p ON e.order_id = p.order_id
     WHERE e.executed_at >= ?
     ```
     where parameter `?` is cutoff timestamp string `(datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d %H:%M:%S")`.

3. **Per-Execution Realized Slippage Computation**:
   $$\text{Realized Slippage (bps)} = \frac{|P_{\text{executed}} - P_{\text{decision}}|}{P_{\text{decision}}} \times 10,000$$
   where $P_{\text{decision}} = \text{target\_price}$ and $P_{\text{executed}} = \text{executed\_price}$.

4. **Market-Wise Slippage Mapping**:
   - Group execution records by `market` (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`, `KONEX`).
   - If `market` column in `order_plans` is NULL or empty, infer market using symbol suffix/format:
     - Numeric 6-digit ending in `.KS` or without suffix $\rightarrow$ `KOSPI`
     - Ending in `.KQ` $\rightarrow$ `KOSDAQ`
     - Alpha symbol 1-5 chars $\rightarrow$ `SP500` / `NASDAQ`
   - Calculate mean realized slippage (bps) per market. Fallback missing markets to overall mean or `default_slippage_bps`.

5. **Order Size Tiering & Empirical Market Impact Alpha**:
   - Notional order value $V_{\text{order}} = \text{executed\_volume} \times \text{executed\_price}$.
   - Tiers: Small ($V < 10\text{M KRW}$ / $\$10\text{k}$), Medium ($10\text{M} \le V \le 50\text{M KRW}$ / $\$10\text{k}-\$50\text{k}$), Large ($V > 50\text{M KRW}$ / $\$50\text{k}$).
   - Estimate log-linear empirical impact alpha:
     $$\alpha_{\text{impact}} = \frac{\ln(\text{Slippage}_{\text{Large}} / \text{Slippage}_{\text{Small}})}{\ln(\text{Size}_{\text{Large}} / \text{Size}_{\text{Small}})}$$
     clamped strictly to $[0.30, 1.00]$ (fallback to default $0.50$ when tier sample variance is insufficient).

6. **Dynamic Cost Scaling Factor**:
   $$S_{\text{cost}} = \max\left(0.50, \min\left(3.00, \frac{\text{avg\_slippage\_bps}}{\text{default\_slippage\_bps}}\right)\right)$$
   For example, if baseline is $5.0$ bps and realized execution slippage averages $10.0$ bps, $S_{\text{cost}} = 2.00x$, doubling microstructure penalties in the scoring engine.

---

#### C. EnsembleScoringEngine Integration
**Location:** `trading_system/src/ai/ensemble_scorer.py`

1. **Attributes Added to `EnsembleScoringEngine.__init__`**:
   ```python
   self.slippage_metrics: Optional[Any] = None
   self.cost_scaling_factor: float = 1.0
   self.realized_market_impact_alpha: float = 0.50
   self.market_slippage_bps_map: Dict[str, float] = {}
   ```

2. **Method `update_microstructure_costs`**:
   ```python
   def update_microstructure_costs(self, slippage_metrics: Any) -> None:
       """
       Dynamically updates microstructure cost parameters based on realized execution logs.
       """
       self.slippage_metrics = slippage_metrics
       if slippage_metrics is not None:
           self.cost_scaling_factor = max(0.50, min(3.00, float(getattr(slippage_metrics, 'cost_scaling_factor', 1.0))))
           self.realized_market_impact_alpha = float(getattr(slippage_metrics, 'market_impact_alpha', 0.50))
           self.market_slippage_bps_map = dict(getattr(slippage_metrics, 'market_slippage_map', {}))
           logger.info(
               f"[SLIPPAGE FEEDBACK] Updated microstructure costs: cost_scaling_factor={self.cost_scaling_factor:.2f}x, "
               f"impact_alpha={self.realized_market_impact_alpha:.4f}, avg_slippage={getattr(slippage_metrics, 'avg_slippage_bps', 5.0):.2f}bps "
               f"(sample_count={getattr(slippage_metrics, 'sample_count', 0)})"
           )
   ```

3. **Cost Calculation Adjustment in `_get_cost_pct(row)`**:
   - In `_get_cost_pct`, when `self.realized_market_impact_alpha != 0.50`, participation ratio exponent uses `self.realized_market_impact_alpha` instead of fixed $\sqrt{x} = x^{0.50}$:
     $$\text{impact\_one\_way} = \text{impact\_coeff} \times \text{volatility} \times (\text{participation\_ratio}^{\text{realized\_market\_impact\_alpha}})$$
   - Total microstructure cost percentage is scaled dynamically by `self.cost_scaling_factor`:
     $$\text{total\_cost\_pct} = (\text{stt\_tax} + \text{brokerage\_fee} + \text{clamped\_spread} + 2.0 \times \text{impact\_one\_way}) \times \text{self.cost\_scaling\_factor}$$
   - This ensures that if live execution slippage increases, candidate stock net expected returns drop, automatically deprioritizing illiquid or high-slippage assets during portfolio scoring.

---

#### D. Pipeline & Risk Report Integration
**Location:** `trading_system/run_pipeline.py`

1. **Execution Feedback Trigger in Step 11** (around line 1762):
   ```python
   # ── Milestone 4: Closed-Loop Realized Slippage Execution Feedback ─────────
   try:
       from src.execution.slippage_feedback import SlippageFeedbackEngine
       db_path_trade = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trade_logs.db")
       slippage_engine = SlippageFeedbackEngine(db_path=db_path_trade, window_days=30, default_slippage_bps=5.0)
       slippage_metrics = slippage_engine.calculate_realized_slippage()
       scorer.update_microstructure_costs(slippage_metrics)
   except Exception as _m4_e:
       logger.warning(f"[MILESTONE 4] Slippage feedback integration skipped: {_m4_e}")
       slippage_metrics = None
   ```

2. **Report Block Generation & Output Appending** (around line 2560):
   ```python
   # Build Milestone 4 Report Block
   if 'slippage_metrics' in locals() and slippage_metrics is not None:
       m4_map = slippage_metrics.market_slippage_map
       m4_text_lines = [
           "================================================================================",
           "[MILESTONE 4: CLOSED-LOOP REALIZED SLIPPAGE REPORT]",
           "================================================================================",
           f"Evaluation Time (KST): {kst_now_str}",
           "Database Path: trade_logs.db",
           "Analysis Window: 30 days",
           f"Total Execution Samples Analyzed: {slippage_metrics.sample_count}",
           f"Overall Realized Average Slippage: {slippage_metrics.avg_slippage_bps:.2f} bps",
           f"Empirical Market Impact Alpha: {slippage_metrics.market_impact_alpha:.4f}",
           f"Dynamic Cost Scaling Factor: {slippage_metrics.cost_scaling_factor:.2f}x",
           "",
           "--- Realized Slippage Map by Market ---",
           f"  - KOSPI      : {m4_map.get('KOSPI', 5.0):.2f} bps",
           f"  - KOSDAQ     : {m4_map.get('KOSDAQ', 5.0):.2f} bps",
           f"  - SP500      : {m4_map.get('SP500', 5.0):.2f} bps",
           f"  - NASDAQ     : {m4_map.get('NASDAQ', 5.0):.2f} bps",
           f"  - RUSSELL2000: {m4_map.get('RUSSELL2000', 5.0):.2f} bps",
           f"  - KONEX      : {m4_map.get('KONEX', 5.0):.2f} bps",
           "================================================================================\n"
       ]
       m4_report_str = "\n".join(m4_text_lines)
   else:
       m4_report_str = ""

   # Write to strategy_data_coverage_report.txt
   cov_output_path = os.path.join(result_dir, "strategy_data_coverage_report.txt")
   with open(cov_output_path, "w", encoding="utf-8") as f_cov:
       f_cov.write(cov_report_text + "\n\n" + m3_report_str + "\n\n" + m4_report_str)
   ```

---

#### E. Root Re-export Forwarder File
**Location:** `src/execution/slippage_feedback.py`

```python
"""
Slippage Feedback Module (Forwarder):
Re-exports SlippageFeedbackEngine and SlippageMetrics from trading_system.src.execution.slippage_feedback.
"""

try:
    from trading_system.src.execution.slippage_feedback import (
        SlippageFeedbackEngine,
        SlippageMetrics,
    )
except ImportError:
    from src.execution.slippage_feedback import (
        SlippageFeedbackEngine,
        SlippageMetrics,
    )

__all__ = ["SlippageFeedbackEngine", "SlippageMetrics"]
```

---

#### F. Comprehensive Unit Testing Plan
**Test Suite Paths:**
- `trading_system/tests/test_slippage_feedback.py`
- `tests/test_slippage_feedback.py`

**Test Cases**:
1. `test_slippage_metrics_dataclass_defaults`:
   - Verify initialization of `SlippageMetrics` with default parameters.
2. `test_empty_or_missing_db_graceful_fallback(tmp_path)`:
   - Pass non-existent DB path to `SlippageFeedbackEngine`.
   - Assert `sample_count == 0`, `cost_scaling_factor == 1.0`, `avg_slippage_bps == 5.0`.
3. `test_realized_slippage_calculation_single_and_multi_orders(tmp_path)`:
   - Create SQLite DB with `order_plans` and `execution_logs`.
   - Insert execution log: `target_price = 10000`, `executed_price = 10010` (+10 bps slippage).
   - Execute `calculate_realized_slippage()`.
   - Assert `avg_slippage_bps == 10.0`, `sample_count == 1`, `cost_scaling_factor == 2.0`.
4. `test_market_grouping_and_alpha_tiering(tmp_path)`:
   - Insert records for KOSPI (target 50000, exec 50050 -> 10 bps), KOSDAQ (target 10000, exec 10030 -> 30 bps), SP500 (target 100, exec 100.02 -> 2 bps).
   - Verify `market_slippage_map['KOSPI'] == 10.0`, `market_slippage_map['KOSDAQ'] == 30.0`, `market_slippage_map['SP500'] == 2.0`.
5. `test_ensemble_scorer_cost_update_integration()`:
   - Instantiate `EnsembleScoringEngine`.
   - Compute baseline score on mock candidate DataFrame.
   - Call `scorer.update_microstructure_costs(SlippageMetrics(avg_slippage_bps=15.0, market_impact_alpha=0.60, market_slippage_map={}, sample_count=10, cost_scaling_factor=3.0))`.
   - Re-compute score.
   - Assert `ensemble_expected_return` decreases due to 3.0x microstructure cost penalty scaling factor.
6. `test_forwarder_imports()`:
   - Import `SlippageFeedbackEngine` and `SlippageMetrics` from both `src.execution.slippage_feedback` and `trading_system.src.execution.slippage_feedback`.
   - Assert both imports resolve to the same underlying classes.

---

## 3. Caveats

1. **Execution DB Missingness / Cold Start**:
   - On clean installations or dry runs, `trade_logs.db` may not exist yet or `execution_logs` may be empty.
   - `SlippageFeedbackEngine` is explicitly engineered with defensive `try...except sqlite3.OperationalError` blocks and handles missing tables/files gracefully by returning standard baseline metrics ($5.0\text{ bps}$, $1.0\text{x}$ scaling).

2. **Currency Standardization in Order Size Tiers**:
   - KRX stocks (KOSPI/KOSDAQ) operate in KRW (notional $\approx 10\text{M}-100\text{M KRW}$), whereas US stocks (SP500/NASDAQ) operate in USD (notional $\approx \$1\text{k}-\$100\text{k}$).
   - Order size tier classification in `SlippageFeedbackEngine` accounts for market currency when computing alpha or uses relative participation ratio $\frac{Q_{\text{order}}}{\text{ADV}}$.

3. **ISO Date Formatting in SQLite Query**:
   - Timestamps in `execution_logs` are recorded via `strftime("%Y-%m-%d %H:%M:%S")`.
   - String cutoff comparison `executed_at >= cutoff_str` is used instead of SQLite native `datetime('now')` to prevent timezone mismatch between local KST system time and UTC.

---

## 4. Conclusion

The technical architecture for **Milestone 4 (R4: Closed-Loop Realized Slippage Execution Feedback)** is completely specified, mathematically rigorous, and ready for immediate implementation.

By creating `SlippageFeedbackEngine`, integrating `update_microstructure_costs()` into `EnsembleScoringEngine`, adding the pipeline trigger in `run_pipeline.py`, and implementing forwarders and pytest suites, the trading system achieves closed-loop feedback: live execution slippage directly adjusts future asset selection and portfolio allocation.

---

## 5. Verification Method

### Independent Verification Steps

1. **Unit Test Execution**:
   Run the pytest command to verify all new unit tests pass:
   ```bash
   .venv/bin/pytest trading_system/tests/test_slippage_feedback.py tests/test_slippage_feedback.py -v
   ```
   *Expected result:* All test cases pass with 100% success rate.

2. **Full Pipeline Test Run**:
   Run the integrated pipeline command:
   ```bash
   .venv/bin/python trading_system/run_pipeline.py
   ```
   *Expected result:* Pipeline completes successfully, logs `[SLIPPAGE FEEDBACK] Updated microstructure costs...`, and outputs `[MILESTONE 4: CLOSED-LOOP REALIZED SLIPPAGE REPORT]` inside `trading_system/strategy_data_coverage_report.txt`.

3. **Report Verification Inspection**:
   Inspect `trading_system/strategy_data_coverage_report.txt` to confirm presence of `[MILESTONE 4: CLOSED-LOOP REALIZED SLIPPAGE REPORT]` block with correct metrics.

---
*End of Report.*
