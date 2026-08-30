# Technical Survey Report: R4 (OMS Precision Timing) & R5 (Test Suite & Pipeline Execution)

**Author**: `teamwork_preview_explorer` (Explorer Survey 3)  
**Date**: 2026-08-30  
**Target System**: Stock Trading System (5 Core Markets: SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ)  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_3`  

---

## 1. Executive Summary

This report delivers an exhaustive technical investigation of **Requirement 4 (OMS Precision Timing & Order Generation)** and **Requirement 5 (Test Suite Integrity & CI/CD Pipeline Execution)** for the stock trading system.

Key findings:
1. **Execution OMS Subsystem (`trading_system/src/execution/`)**:
   - Highly mature, institutional-grade architecture comprising 10 core modules: `oms_engine.py` (1,330 lines), `adaptive_router.py`, `cross_impact.py`, `hawkes_vpin.py`, `kill_switch.py`, `slippage_feedback.py`, `smart_order_router.py`, `sor_router.py`, `telegram_notifier.py`, and `turnover_optimizer.py`.
   - Built-in **7 Core Safety Gates & Filter Checks**: Kill Switch (file/env/API), Severe Crisis Gating, Leland Dynamic Buffer Band (no-trade zone), KRX Long-Only Synthetic Short Restriction, KRX ±30% Upper/Lower Limit Lock, Net Alpha Hurdle vs STT & Friction Costs, Dynamic Adverse Opening Gap Filter (-3σ protection), ADV Capacity Capping, VPIN Toxicity Gate, and Opening Gap Overheat / Dip-Buying Filter.
2. **6 Precision Timing & Dynamic Exit Engines**:
   - **Confluence Entry Engine**: Combines ensemble score (40%), VCP compression (30%), volume surge (15%), and L2 orderbook imbalance (15%) with 50-day moving average trend penalty.
   - **3-tier Scale-In Pyramiding**: Stage 1 Probe (30%), Stage 2 Breakout Confirmation (50%), Stage 3 Pullback Support (20%).
   - **4-tier Dynamic Trailing Stop & Profit Taking**: 2D regime-parameterized thresholds, correction-phase adaptation (`TIME_CONSOLIDATION` vs `PRICE_PULLBACK`), Tier 1 (+8% -> 25% TP + Breakeven Free Trade), Tier 2 (+15% -> 50% TP + Chandelier ATR trailing stop), Tier 3 (+25% -> KAMA/50-day MA Runner exit), and Hard ATR Stop Loss.
   - **Signal Exhaustion Exit**: Alpha score collapse (< 0.48) and opportunity cost switching (delta >= 8.0%p).
   - **Order Flow Shock Exit**: Institutional dump (MFI < 25), heavy volume drop (Down day + volume ratio >= 3.5), L2 orderbook sell imbalance (OBI < -0.60).
   - **Time-Stop Exit**: Max stall duration (12 days) within [-2%, +3%] return band.
3. **Pipeline Integration (`trading_system/run_pipeline.py`)**:
   - Order plans generated at line 3868 via `ExecutionOMSEngine.generate_order_plan()`, enriched with actual latest observed close prices, Leland no-trade buffers, and transaction logs persisted to SQLite WAL database `trade_logs.db`.
4. **Test Suite & CI/CD Pipeline (R5)**:
   - **222 test files** across `tests/`, `tests/phase3`, `tests/phase3/e2e`, `tests/phase4/e2e`, and `tests/phase6/unit`.
   - **1,796 total tests collected**.
   - Standard execution command: `$env:PYTHONPATH="trading_system;trading_system/src;."; .venv\Scripts\pytest.exe tests/ -v`.
   - Targeted execution test suite (`test_precision_timing_engines.py`, `test_order_manager.py`, `test_adaptive_router.py`, `test_adaptive_execution_feedback.py`) runs 18/18 tests with 100% pass rate in ~14s.
   - GitHub Actions workflows (`pipeline.yml`, `pytest.yml`, `training.yml`, `weekly_hpo.yml`, `preseed.yml`, `realtime_monitor.yml`) enforce multi-market matrix execution, artifact merging, release tagging, and GitHub Pages deployment.

---

## 2. Architecture of the Execution Subsystem

The execution subsystem is located at `trading_system/src/execution/` (accessible as `src.execution` when `PYTHONPATH` includes `trading_system` and `trading_system/src`).

```
trading_system/src/execution/
├── __init__.py                  # Package exports
├── oms_engine.py                # ExecutionOMSEngine, AlmgrenChrissScheduler, GatheralMarketImpactKernel
├── order_manager.py             # Facade / backward-compatibility aliases
├── adaptive_router.py           # AdaptiveOrderRouter (L2 OBI & Urgency Slicing)
├── cross_impact.py              # CrossAssetImpactEngine (Basket Cross-Impact Matrix Theta = gamma * C_corr)
├── hawkes_vpin.py               # HawkesVPINToxicityGate (Hawkes intensity & VPIN toxicity gate)
├── kill_switch.py               # 3-Tier Kill Switch (File / Env / API) & kill_switch_state.json
├── slippage_feedback.py         # SlippageFeedbackEngine (Closed-loop realized vs expected slippage calibration)
├── smart_order_router.py        # SmartOrderRouter (3-tier ATS/Dark probe, Maker peg, Lit sweeper)
├── sor_router.py                # Smart Order Routing implementation
├── turnover_optimizer.py        # TurnoverOptimizer (Hysteresis buffer & smooth decay)
└── telegram_notifier.py         # Real-time alert & notification engine
```

### Key Modules and Responsibilities

| Module | Core Classes | Primary Responsibility |
|---|---|---|
| `oms_engine.py` | `ExecutionOMSEngine`, `AlmgrenChrissScheduler`, `GatheralMarketImpactKernel` | 7 safety gates, order plan generation, 2D regime timing matrix, precision timing engines, tick rounding (KRX 7-tier grid & US sub-penny/cent), inverse beta hedging, SQLite WAL persistence. |
| `adaptive_router.py` | `AdaptiveOrderRouter` | Computes L2 Orderbook Imbalance (OBI) `[-1, +1]`, modulates Almgren-Chriss hyperbolic decay schedules based on urgency shifts. |
| `cross_impact.py` | `CrossAssetImpactEngine` | Models multi-asset cross-market impact spillovers `Theta = gamma * C_corr` in correlated basket trades and interleaves time-slice execution. |
| `hawkes_vpin.py` | `HawkesVPINToxicityGate` | Hawkes point-process arrival intensity `lambda(t)` and Volume-Synchronized Probability of Toxicity (VPIN); cancels passive pegs during predatory sweeps. |
| `kill_switch.py` | `is_kill_switch_active`, `engage`, `disengage` | 3-tier emergency system halt (file `KILL_SWITCH`, env `KILL_SWITCH=1`, API invocation). |
| `slippage_feedback.py` | `SlippageFeedbackEngine`, `SlippageMetrics` | Closed-loop execution audit querying `trade_logs.db`, computing MAD-filtered realized slippage, updating `market_impact_alpha` and cost scaling factors. |
| `smart_order_router.py` | `SmartOrderRouter` | Multi-venue routing: Tier 1 ATS/Dark midpoint cross probe (40%), Tier 2 primary peg maker (maker rebate capture), Tier 3 lit sweeper (<= 1.5% ADV). |
| `turnover_optimizer.py` | `TurnoverOptimizer` | Position hysteresis filter (5% threshold, min 50k KRW) with smooth decay near threshold, with fresh entries and full liquidations bypassing hysteresis. |

---

## 3. Deep Dive: Precision Timing & Dynamic Exit Engines

All 6 precision timing and dynamic exit engines are implemented inside `ExecutionOMSEngine` in `trading_system/src/execution/oms_engine.py`.

### 3.1. Engine 1: Multi-Timeframe Confluence Entry Engine

- **Method**: `ExecutionOMSEngine.calculate_confluence_entry_score(ensemble_score, vcp_score, volume_surge_ratio, obi_score, price_above_ma50)`
- **Mathematical Specification**:
  $$\text{ens}_c = \text{clip}(\text{ensemble\_score}, 0.0, 1.0)$$
  $$\text{vcp}_c = \text{clip}(\text{vcp\_score}, 0.0, 1.0)$$
  $$\text{vol}_c = \text{clip}\left(\frac{\text{volume\_surge\_ratio} - 1.0}{2.0}, 0.0, 1.0\right)$$
  $$\text{obi}_c = \text{clip}(0.50 + \text{obi\_score} \times 0.50, 0.0, 1.0)$$
  $$\text{Score}_{\text{base}} = 0.40 \cdot \text{ens}_c + 0.30 \cdot \text{vcp}_c + 0.15 \cdot \text{vol}_c + 0.15 \cdot \text{obi}_c$$
  $$\text{Confluence Score} = \begin{cases} \text{Score}_{\text{base}} \times 0.80 & \text{if not price\_above\_ma50} \\ \text{Score}_{\text{base}} & \text{if price\_above\_ma50} \end{cases}$$
- **Entry Gating Condition**:
  $$\text{is\_valid\_entry} = (\text{Confluence Score} \ge 0.65) \land (\text{ens}_c \ge 0.55)$$

### 3.2. Engine 2: 3-Stage Dynamic Scale-In Pyramiding Engine

- **Method**: `ExecutionOMSEngine.generate_scale_in_order_plan(symbol, total_target_shares, current_stage, entry_price, current_price, pivot_price)`
- **Execution Stages**:
  1. **Stage 1 (Probe)**: $30\%$ of total target shares upon initial confluence signal (`action: BUY_PROBE`, `weight_pct: 0.30`).
  2. **Stage 2 (Breakout Confirmation)**: $50\%$ of total target shares when price confirms breakout above pivot level (`action: BUY_BREAKOUT`, `weight_pct: 0.50`).
  3. **Stage 3 (Pullback Support / Pyramid)**: $20\%$ of total target shares on successful pullback support test (`action: BUY_PYRAMID`, `weight_pct: 0.20`).
  4. **Stage > 3**: Full position held (`action: HOLD_FULL`, `allocated_shares: 0`).

### 3.3. Engine 3: 4-Tier Multi-Stage Dynamic Profit-Taking & Trailing Stop

- **Method**: `ExecutionOMSEngine.calculate_trailing_stop_plan(current_holdings, prices_dict, atr_multiplier, profit_take_threshold, regime)`
- **2D Regime Parameterization Matrix (`REGIME_TIMING_MATRIX`)**:
  - `BULL_LOW_VOL`: Entry $\ge 0.65$, TP1 $+8\%$, TP2 $+15\%$, TP3 $+25\%$, SL $1.5\times$ ATR, TS $2.0\times$ ATR, Max Hold 30d.
  - `BULL_HIGH_VOL`: Entry $\ge 0.70$, TP1 $+10\%$, TP2 $+20\%$, TP3 $+35\%$, SL $1.8\times$ ATR, TS $2.5\times$ ATR, Max Hold 20d.
  - `SIDEWAYS_LOW_VOL`: Entry $\ge 0.75$, TP1 $+6\%$, TP2 $+10\%$, TP3 $+15\%$, SL $1.2\times$ ATR, TS $1.5\times$ ATR, Max Hold 10d.
  - `SIDEWAYS_HIGH_VOL`: Entry $\ge 0.80$, TP1 $+5\%$, TP2 $+10\%$, TP3 $+15\%$, SL $1.0\times$ ATR, TS $1.0\times$ ATR, Max Hold 7d.
  - `BEAR_LOW_VOL`: Entry $\ge 0.85$, TP1 $+5\%$, TP2 $+8\%$, TP3 $+12\%$, SL $1.0\times$ ATR, TS $1.0\times$ ATR, Max Hold 5d.
  - `BEAR_HIGH_VOL`: Entry $\ge 0.95$, TP1 $+3\%$, TP2 $+6\%$, TP3 $+10\%$, SL $0.8\times$ ATR, TS $0.8\times$ ATR, Max Hold 3d.
- **Correction-Phase Adaptive Adjustments**:
  - `TIME_CONSOLIDATION`: Tightens stop loss to $\min(\text{sl\_mult}, 0.9)$ and trailing stop to $\min(\text{ts\_mult}, 1.2)$ to instantly cut base breakdown failures.
  - `PRICE_PULLBACK`: Expands stop loss to $\max(\text{sl\_mult}, 1.3)$ to accommodate normal Fibonacci retracement swings.
- **4-Tier Progression**:
  - **Tier 1 ($+8\%$ gain)**: $25\%$ partial take-profit + raise stop loss to breakeven $+0.3\%$ friction ($1.003 \times \text{entry\_p}$) $\rightarrow$ Free Trade status (`BREAKEVEN_PROFIT_LOCK`).
  - **Tier 2 ($+15\%$ gain)**: $50\%$ partial take-profit + Chandelier ATR trailing stop ($\text{High}_{20} - \text{ts\_mult} \times \text{ATR}$) (`CHANDELIER_TRAILING_PROFIT`).
  - **Tier 3 ($+25\%$ gain)**: $25\%$ partial take-profit + KAMA / 50-day moving average trailing lock.
  - **Tier 4 (Runner $25\%$)**: Run position until price drops below trailing stop or breaches 50-day MA (`TIER3_KAMA_RUNNER_EXIT`).
  - **Hard ATR Stop Loss**: If $\text{current\_price} \le \text{entry\_price} - \text{sl\_mult} \times \text{ATR}$, immediate full stop loss (`ATR_STOP_LOSS`).

### 3.4. Engine 4: Signal Decay & Opportunity Cost Switching Exit

- **Method**: `ExecutionOMSEngine.check_signal_exhaustion_exit(current_score, top_candidates_avg_expected_return, holding_expected_return, min_score_threshold=0.48, switching_hurdle=0.08)`
- **Exit Triggers**:
  1. **Alpha Score Collapse**: $\text{current\_score} < 0.48 \rightarrow$ Action `SELL`, reason `ALPHA_SCORE_COLLAPSE`.
  2. **Opportunity Cost Switching**: $\text{top\_candidates\_avg\_expected\_return} - \text{holding\_expected\_return} \ge 0.08 \rightarrow$ Action `SELL`, reason `OPPORTUNITY_COST_SWITCHING`.

### 3.5. Engine 5: Time-Stop / Stalling Momentum Exit

- **Method**: `ExecutionOMSEngine.check_time_stop_exit(days_held, unrealized_return, max_stall_days=12, stall_band=(-0.02, 0.03))`
- **Exit Trigger**: $\text{days\_held} \ge 12 \land -0.02 \le \text{unrealized\_return} \le +0.03 \rightarrow$ Action `SELL`, reason `TIME_STOP_MOMENTUM_STALLED`.

### 3.6. Engine 6: Institutional Order Flow Shock Exit

- **Method**: `ExecutionOMSEngine.check_order_flow_shock_exit(mfi_value=50.0, is_down_day=False, volume_ratio=1.0, obi=0.0)`
- **Shock Flags**:
  1. $\text{MFI} < 25.0$ (Severe institutional cash outflow)
  2. $\text{is\_down\_day} \land \text{volume\_ratio} \ge 3.5$ (High-volume distribution dump)
  3. $\text{OBI} < -0.60$ (Predatory sell-side orderbook sweep)
- **Exit Trigger**: $\ge 2$ shock flags confirmed $\rightarrow$ Action `SELL`, reason `EMERGENCY_ORDER_FLOW_SHOCK`.

---

## 4. Pipeline Integration Touchpoints

### 4.1. Order Plan Generation in `run_pipeline.py`

In `trading_system/run_pipeline.py` (lines 3868–3905):
```python
# ── Execution OMS Order Plan Generation & DB Logging ──
oms_engine = ExecutionOMSEngine(
    db_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trade_logs.db")
)
top_picks_dicts = ensemble_df_merged.head(20).to_dict(orient="records")

# Enrich with latest observed close price (avoiding 1.0 fallback)
_last_close_map = {}
if 'infer_data_dict' in locals() and infer_data_dict:
    for _sym, _sdf in infer_data_dict.items():
        try:
            _cl = _sdf['Close']
            if isinstance(_cl, pd.DataFrame):
                _cl = _cl.iloc[:, 0]
            _last_close_map[str(_sym)] = float(_cl.iloc[-1])
        except Exception:
            continue
for _pick in top_picks_dicts:
    _p_sym = _pick.get('symbol')
    if _pick.get('close_price') is None and _p_sym is not None:
        _pick['close_price'] = _last_close_map.get(str(_p_sym), _pick.get('close'))

_crisis_lvl_str = getattr(crisis_lvl, 'value', str(crisis_lvl)) if ('crisis_lvl' in locals() and crisis_lvl is not None) else "NORMAL"
p_weights = ensemble_df_merged['portfolio_weight'] if 'portfolio_weight' in ensemble_df_merged.columns else pd.Series(0.05, index=ensemble_df_merged.index)
weight_dict = dict(zip(ensemble_df_merged['symbol'], p_weights))
curr_holdings = oms_engine.get_current_holdings_from_db()

order_plans = oms_engine.generate_order_plan(
    top_picks_dicts,
    weight_dict,
    total_capital=cfg.portfolio_capital_krw,
    crisis_level=_crisis_lvl_str,
    current_holdings=curr_holdings,
    use_leland_buffer=True
)
logger.info(f"[OMS ENGINE] Generated & saved {len(order_plans)} order execution plans to trade_logs.db")
```

### 4.2. 7 Safety Gates Enforced During Order Generation

When `generate_order_plan` executes:
1. **Kill Switch Gate**: Blocks all order creation if `KILL_SWITCH` file exists, `KILL_SWITCH=1` env is set, or `kill_switch.engage()` is active.
2. **Crisis Level Gate**: `SEVERE` crisis cancels all `BUY` orders and forces liquidation `SELL` orders; `ACTIVE`/`WATCH`/`RECOVERY` regimes scale capital via continuous multipliers ($0.15$ to $1.00$).
3. **Leland Dynamic Buffer Band (No-Trade Zone)**: If current weight is within $[w_i^* - \Delta_i, w_i^* + \Delta_i]$, order creation is skipped (holding position without transaction drag). New entries and complete liquidations bypass the buffer.
4. **KRX Long-Only Synthetic Short Filter**: KRX stocks cannot short-sell; short signals are converted to `CASH_OVERLAY` with `HEDGE_FLAG` status.
5. **KRX $\pm 30\%$ Limit Lock Gate**: Stocks locked at upper limit ($+29.5\%$) skip buy execution; stocks locked at lower limit ($-29.5\%$) route to passive limit sell for liquidity unfreezing.
6. **Net Alpha Transaction Cost Hurdle**: Expected return must exceed buy + sell friction costs ($STT + \text{Spread} + \text{Slippage}$) $+ 0.10\%$ safety margin.
7. **Adverse Opening Gap Protection**: Rejects opening buys if gap is below $-3\sigma$ ($<-3 \times \text{vol}_{20d}$).
8. **ADV Capacity Capping**: Maximum order size capped at $5\%$ of 20-day ADV.
9. **VPIN Toxicity & Opening Gap Overheat Gating**: If VPIN $>0.70$, routes to `PASSIVE_LIMIT` (buy) or `FAST_VWAP` (sell); if open gap $>+5\%$, routes to `DIP_LIMIT` at $1.5\%$ discount.
10. **Synthetic Beta Inverse Hedge Overlay**: In Bear/Crisis regimes, automatically allocates inverse index ETF orders (`BUY_HEDGE`) scaled to portfolio beta.

---

## 5. Test Suite & CI/CD Pipeline Investigation (R5)

### 5.1. Test Suite Statistics

- **Total Test Files**: 222 Python test files.
- **Directories**:
  - `tests/` (root test files)
  - `tests/phase3/` & `tests/phase3/e2e/`
  - `tests/phase4/e2e/`
  - `tests/phase6/unit/`
- **Total Test Count**: **1,796 tests collected**.

### 5.2. Pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
norecursedirs = [".venv", ".git", "build", "dist"]
pythonpath = ["trading_system", "."]
addopts = "-v --tb=short"
markers = [
    "slow: marks tests as slow (deselect with '-m not slow')",
    "unit: marks tests as fast unit tests",
    "integration: marks tests requiring external APIs or DB",
    "adversarial: marks stress/adversarial tests",
]
```

### 5.3. Execution Command & Verified Execution

- **Official Execution Command**:
  ```powershell
  $env:PYTHONPATH="trading_system;trading_system/src;."; .venv\Scripts\pytest.exe tests/ -v
  ```
- **Targeted Test Execution Sample**:
  - Command: `.venv\Scripts\pytest.exe tests/test_precision_timing_engines.py tests/test_order_manager.py tests/test_adaptive_router.py tests/test_adaptive_execution_feedback.py -v`
  - Result: **18 passed in 14.21s (100% Pass Rate)**.

### 5.4. GitHub Actions CI/CD Pipeline Alignment

The repository maintains 6 automated GitHub Actions workflows under `.github/workflows/`:

1. **`pytest.yml` (CI / Testing & Security Audit)**:
   - Runs on push/PR to `main`/`master` on Ubuntu with Python 3.12 and `uv`.
   - Runs `mypy` type checking across `trading_system/src`.
   - Runs `ruff` linting and `bandit` security vulnerability audits.
   - Runs unit tests with coverage tracking (`coverage.xml` artifact).
2. **`pipeline.yml` (Daily Multi-Market Pipeline)**:
   - Scheduled cron at 11:30 UTC Mon-Fri (`30 11 * * 1-5`).
   - Matrix execution across 5 core markets: `SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ` (or all 16 global markets).
   - Generates all 31 strategy predictions, ensemble prediction file, coverage report, and DB files.
   - Merge job (`merge_predictions.py`, `generate_run_snapshot.py`) compiles unified output.
   - Creates GitHub Release (`vYYYY-MM-DD`) and deploys HTML dashboard to GitHub Pages.
3. **`training.yml` (Model Training Pipeline)**:
   - Weekly scheduled run on Saturdays (`30 11 * * 6`).
   - Retrains XGBoost, Surge, Lead-Lag, VCP ML, LSTM models and caches artifacts in `trading_system/models`.
4. **`weekly_hpo.yml`**: Optuna hyperparameter optimization.
5. **`preseed.yml`**: Preseeds historical market indicators and price DB caches.
6. **`realtime_monitor.yml`**: Intraday monitoring and alert daemon.

---

## 6. Recommendations & Extension Opportunities for R1–R4

1. **Intraday Volatility & Range Expansion Signals**:
   - New breakout alpha signals can feed directly into `ExecutionOMSEngine.calculate_confluence_entry_score` as high-volatility momentum components.
2. **Cross-Asset Spillover & Supply Chain Momentum Integration**:
   - Upstream lead-lag and supply chain signals can be integrated with `CrossAssetImpactEngine` to ensure coordinated tranche execution without co-exhaustion slippage.
3. **Real-time Hawkes VPIN & OBI Dynamic Router Binding**:
   - In live intraday trading mode, connect `AdaptiveOrderRouter.generate_adaptive_schedule` and `HawkesVPINToxicityGate` directly to broker order execution endpoints to auto-adjust tranche pacing in real time.

---
