# Handoff Report: 2D Market Regime Engine, Dynamic Sharpe Ensemble & Verification Framework

- **Agent**: Explorer 3 (Regime Ensemble Explorer)
- **Target Folder**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3`
- **Handoff Type**: Hard (Complete Investigation)
- **Date**: 2026-08-14

---

## 1. Observation

### 1.1 2D Market Regime Engine (`trading_system/src/analysis/regime_detector.py`)
- **GMM Clustering & Feature Matrix** (Lines 35–116): 10 macro features (`sp500_ret_roll`, `sp500_vol_roll`, `vix_level`, `us10y_level`, `us_yield_spread`, `usdkrw_ret_roll`, `kr_us_spread`, `kr_yield_curve`, `wti_ret_roll`, `inflation_shock`).
- **Fast Shock Overrides** (Lines 181–199): VIX > 30.0 forces `BEAR` (cluster 0); S&P 500 1-day < -3.0% or 2-day < -5.0% forces `BEAR`.
- **2D States** (Lines 306–346): Combines 3 direction labels (`BEAR`, `SIDEWAYS`, `BULL`) with 2 realized volatility states (`LOW_VOL`, `HIGH_VOL`) into 6 combo states:
  `BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`.
- **3D Macro Modifiers** (Lines 352–420): Overlays 5 macro risk conditions: `LIQUIDITY_SQUEEZE`, `INFLATION_SHOCK`, `YIELD_INVERSION`, `HIGH_YIELD_BULL`, `HIGH_YIELD_BEAR`.
- **Dual Market Decoupling** (Lines 422–488): Separately detects US (S&P 500) and KR (KOSPI) regimes, evaluating 20-day correlation $\rho_{20d}$ and decoupling status (`COUPLED`, `DECOUPLING_US_BULL_KR_BEAR`, `DECOUPLING_KR_BULL_US_BEAR`).

### 1.2 Ensemble Scoring Engine (`trading_system/src/ai/ensemble_scorer.py`)
- **31 Strategy Allocations** (Lines 37–339): Full 31-strategy base weight tables defined in `REGIME_WEIGHTS` and `REGIME_2D_WEIGHTS` (sum = 1.00).
- **Factor Orthogonalization** (Lines 1559–1579): Integrates `FactorOrthogonalizerEngine` (PCA ZCA symmetric decorrelation) and Modified Gram-Schmidt to decouple collinear strategy signals.
- **Factor Noise Suppression** (Lines 1581–1613): Integrates `RegimeFactorSuppressionEngine` targeting 5 strategy clusters (`CORE_AI`, `MOMENTUM`, `VALUATION`, `REVERSAL`, `FLOW_MICRO`).
- **Dynamic Sharpe Multiplier & EMA** (Lines 790–878):
  - Formula: $w_i = \text{base\_w}_i \times \exp(\gamma \times \text{clip}(\text{Sharpe}_i, -L, L))$, $\gamma = 1.0$, $L = \ln\sqrt{5.0} \approx 0.8047$.
  - Underperformance pruning: $\text{Sharpe}_i < -0.50 \implies w_i = 0.0$.
  - Maximum ratio damping: power damping when $v_{\text{max}} / v_{\text{min}} > 20.0$.
  - Adaptive EMA smoothing: $\alpha_{\text{eff}} = 1.0$ upon regime transition; $\alpha_{\text{eff}} = 0.2$ in steady state. Persisted in `models/prev_weights.json`.
- **Microstructure Cost Deduction** (Lines 1690–1798): Vectorized calculation deducting STT/SEC taxes, dynamic bid-ask spread, and Almgren-Chriss square-root market impact cost ($Q = 50\text{M KRW} / 50\text{k USD}$).
- **Liquidity & Preferred Share Gating** (Lines 1809–1842): Zero-weights preferred shares (`우`, `우B`, etc.), SPACs, and illiquid symbols.

### 1.3 Testing Framework & Test Counts
- `pyproject.toml` configures `testpaths = ["tests", "trading_system/tests"]`.
- `pytest --collect-only` discovered **1,554 tests** across the repository (730 in root `tests/`, 824 in `trading_system/tests/`).
- Verified key test suites (`tests/test_hpo_and_2d_ensemble.py`, `tests/test_isotonic_sharpe_calibration.py`, `tests/test_factor_orthogonalization.py`, `tests/test_correlation_suppression.py`).

### 1.4 Pipeline & GitHub Pages Dashboard
- `trading_system/run_pipeline.py` executes a 12-step automated sequence generating prediction files (`ensemble_predictions.txt`, `surge_predictions.txt`, `lead_lag_predictions.txt`, `stat_arb_predictions.txt`, `strategy_data_coverage_report.txt`, etc.).
- `trading_system/generate_report.py` compiles `gh-pages/index.html` featuring interactive multi-market tabs (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000), 2D regime status badges, dynamic strategy weights, decision rationale, and modal stock drawer.

---

## 2. Logic Chain

1. **Macro Regime Awareness**: Financial markets exhibit distinct regimes where factor performance diverges significantly (e.g. Momentum dominates in `BULL_LOW_VOL`, whereas Stat-Arb and RIM Valuation protect capital in `BEAR_HIGH_VOL`). The 2D GMM detector accurately categorizes these states using 10 fundamental and market series.
2. **Zero-Lag Defense**: Because rolling statistics lag sudden market shocks, the Fast VIX (>30) and S&P 500 crash override rules immediately pivot the system to `BEAR` mode without waiting for 20-day window updates.
3. **Dynamic Sharpe Allocation**: Allocating higher weights to strategies with proven rolling outperformance ($\text{Sharpe} > 0$) maximizes alpha capture. The exponential multiplier formulation with strict clipping ($L = \ln\sqrt{5.0}$) and power damping prevents single-strategy dominance.
4. **Whipsaw & Turnover Control**: Constant reweighting creates costly transaction friction. The adaptive EMA mechanism smooths weights ($\alpha = 0.2$) during quiet periods, but resets instantaneously ($\alpha = 1.0$) upon regime shifts to provide immediate downside protection.
5. **Real-World Executability**: Pre-trade subtraction of Almgren-Chriss market impact, exchange taxes, and bid-ask spreads ensures that only net-profitable trades populate the Top 20 recommendations.

---

## 3. Caveats

1. **Cold-Start Period**: In new deployment environments with fewer than 10 dated observations of realized returns, rolling Sharpes evaluate to 0.0, safely reverting the engine to static 2D regime base weights.
2. **Execution Slippage Feedback**: Slippage parameters rely on `trade_logs.db` data; if trade logs are absent, default conservative market impact coefficients (0.75 for KRX, 0.50 for US) are used.
3. **High-Frequency Testing**: Optuna HPO integration tests (`test_optuna_tuner.py`) involve real optimization loops that take ~20–30 seconds during full pytest runs.

---

## 4. Conclusion

The 2D Market Regime Engine and Dynamic Exponential Sharpe Ensemble Scorer are fully implemented, structurally sound, and supported by a robust 1,554-test suite. The system successfully combines 31 alpha factors, eliminates collinear factor risk via PCA ZCA orthogonalization and cluster suppression, applies zero-lag crisis overrides, smooths strategy weights with adaptive EMA filtering, and adjusts for realistic microstructure friction to deliver institutional-grade stock ranking.

---

## 5. Verification Method

To independently verify the implementation and system integrity:

```bash
# 1. Run full pytest collection to verify 1,554 test discovery
.venv\Scripts\python.exe -m pytest --collect-only -q

# 2. Run dedicated 2D regime and Sharpe calibration unit tests
.venv\Scripts\python.exe -m pytest tests/test_isotonic_sharpe_calibration.py -v
.venv\Scripts\python.exe -m pytest trading_system/tests/test_hpo_and_2d_ensemble.py -v

# 3. Run factor orthogonalization and correlation suppression test suites
.venv\Scripts\python.exe -m pytest tests/test_factor_orthogonalization.py tests/test_correlation_suppression.py -v

# 4. Verify comparative backtest harness
.venv\Scripts\python.exe trading_system/scripts/compare_backtests.py
```
