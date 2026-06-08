# Milestone 2 Review Report

## Review Summary

**Verdict**: APPROVE

Overall quality of the Milestone 2 implementation is excellent. The code changes in `src/analysis/backtest.py` and `src/core/strategy_engine.py` are structurally sound, functionally correct, and robust. All 21 E2E tests targetting R1 and R2 passed cleanly. 

There are no integrity violations (e.g. hardcoded test expectations or dummy facade implementations). The grid-search parameter optimizer and the market regime detector are implemented with real trading logic and mathematical metrics.

We note one Major design limitation regarding global parameter caching cross-talk and a potential zero-division edge case in `_calc_ema`.

---

## Findings

### [Major] Finding 1: Global Cache Cross-Talk (Cache Collision)
- **What**: Caching of optimized parameters does not partition by symbol or strategy name.
- **Where**: `src/analysis/backtest.py` lines 928-944 (caching load) and lines 975-983 (caching save).
- **Why**: The cache file `data/optimized_params.json` stores a single flat JSON structure. If the optimizer runs for symbol "AAPL" with strategy "RSI", it overwrites `data/optimized_params.json`. If it is subsequently run for "MSFT" with strategy "MA" and those parameter ranges share key names, the cached parameters from the previous run will be returned directly. This will lead to cross-talk where one stock/strategy uses the cached parameters of another stock/strategy.
- **Suggestion**: Change the cache structure to store keys nested by symbol and strategy name, e.g.:
  ```json
  {
      "AAPL": {
          "MA": {
              "best_params": { ... },
              "best_return": 12.34
          }
      }
  }
  ```
  Or save the metadata (`symbol`, `strategy_name`) in the flat cache file and verify they match the query parameters before returning cached values.

### [Minor] Finding 2: Zero-Division Risk in `_calc_ema` for Empty Data
- **What**: Potential `ZeroDivisionError` when `_calc_ema` is called with empty data.
- **Where**: `src/analysis/backtest.py` lines 114-115.
- **Why**: 
  ```python
  if len(data) < period:
      return [sum(data) / len(data)] * len(data)
  ```
  If `data` is empty, `len(data)` is 0, which is less than any `period >= 1`. The expression `sum(data) / len(data)` will evaluate to `0.0 / 0`, raising a `ZeroDivisionError`.
- **Suggestion**: Add a safeguard at the start of `_calc_ema`:
  ```python
  if not data:
      return []
  ```

---

## Verified Claims

- **Grid-search Parameter Optimization** → Verified via code execution and logic analysis. The code correctly executes backtests across all generated parameter combinations and selects the one with the highest return → **PASS**
- **Parameter Caching** → Verified via `test_r1_caching_happy_path`. The code correctly reads/writes to `data/optimized_params.json` and skips grid-search if parameters are cached → **PASS**
- **Metric Division Safeguards** → Verified via code inspection of `_calculate_sharpe_ratio`, `_calculate_max_drawdown`, and `detect_regime` which all check for non-zero denominators → **PASS**
- **Market Regime Detection** → Verified via `test_r2_detect_regime_bull`, `test_r2_detect_regime_bear`, and `test_r2_detect_regime_sideways`. The code correctly compares the 50-day EMA and 200-day EMA to determine market trend → **PASS**
- **Baseline Weight Tracking and Normalization** → Verified via `test_r2_weight_adaptation_bounds`. Baseline weights are restored before adjustments, and weight sums are normalized to exactly `1.0` → **PASS**

---

## Coverage Gaps

- **Multiple-symbol concurrent caching** — risk level: **Medium** — recommendation: Investigate/Fix the cache structure to support multi-symbol/multi-strategy scopes.
- **High-frequency regime transitions** — risk level: **Low** — recommendation: Accept risk (regime updates are calculated on daily bars, so frequency is limited).

---

## Unverified Items

- *None* — All requirements and assertions were verified.

---

## Challenge Summary (Adversarial Review)

**Overall risk assessment**: MEDIUM

While the system is robust and free from integrity violations, a key architectural weakness lies in the flat structure of the parameter caching file.

## Challenges

### [High] Challenge 1: Cache Hijacking across Symbols / Strategies
- **Assumption challenged**: The parameter optimizer assumes that `data/optimized_params.json` only contains parameters relevant to the current optimization task.
- **Attack scenario**: 
  1. Optimize "AAPL" using the "MA" strategy (e.g., param ranges for `short_window` and `long_window`). This gets written to `optimized_params.json`.
  2. Run optimizer for "MSFT" using the "MA" strategy.
  3. The optimizer checks the cache, finds keys `short_window` and `long_window` in the cache file, and immediately returns AAPL's optimized parameters for MSFT without running a backtest.
- **Blast radius**: Significant degradation in trading system performance as all symbols will end up sharing the optimized parameters of whichever symbol was optimized first.
- **Mitigation**: Partition cache by symbol and strategy, or store `symbol` and `strategy_name` inside the cache file and validate them.

### [Medium] Challenge 2: Instant Trend Whipsaws
- **Assumption challenged**: The 50-day vs 200-day EMA ratio is a stable indicator of market regime.
- **Attack scenario**: In highly volatile markets, the ratio `ema50 / ema200` may fluctuate rapidly around the `1.02` and `0.98` boundaries. This triggers frequent adjustments to `technical_weight` (+0.15 in bull, -0.05 in bear), causing transaction costs and portfolio rebalancing churn.
- **Blast radius**: Reduced performance due to transaction fee drag.
- **Mitigation**: Add a hysteresis band or a minimum regime duration parameter to prevent regime flipping.

---

## Stress Test Results

- **Empty price bars** → Throws `ValueError` in optimizer → **PASS**
- **Negative capital/bankruptcy** → Handled safely by metrics safeguards → **PASS**
- **Zero-period indicators** → Handled safely by `max(1, period)` bounds → **PASS**
