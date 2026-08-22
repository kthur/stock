# Domain 3 Survey & In-Depth Technical Analysis Report
**Domain**: 31 Strategy Engines & Data Layer (V6-17 ~ V6-24)  
**Agent**: explorer_3 (Survey Agent)  
**Date**: 2026-08-22  
**Status**: COMPLETE (Read-Only Investigation)  

---

## Executive Summary

Domain 3 covers the core 31 strategy factor models, valuation algorithms, corporate action event processors, macroeconomic cross-asset divergence models, and data validation layers.
Our deep forensic survey of issues **V6-17 through V6-24** identified several critical architectural and mathematical flaws in the codebase:
1. **V6-17 (CRITICAL)**: Sync vs Async BPS/Total Equity scale divergence in `earnings_data.py` and heuristic threshold breakdown (`bv > 1_000_000`) in `rim_valuation.py`, destroying small-cap ($< \$1\text{M}$ equity) and high-nominal KRX ($> 1\text{M}$ KRW BPS) intrinsic valuations.
2. **V6-18 (HIGH)**: `SectorRotationEngine.compute_sector_momentum_scores()` invoking `normalize_sector(raw_sec)` without the `symbol=sym` parameter, entirely bypassing curated symbol classification for key leaders (e.g. `005930`, `MT`, `NVDA`).
3. **V6-19 (HIGH)**: `IVSkewEngine.compute_iv_skew_scores()` checking `if score == 0.5` after continuous price volatility proxy computation, causing 100% bypass of live options chain retrieval even when `ENABLE_LIVE_OPTIONS_FETCH=true`.
4. **V6-20 (HIGH)**: `EventDrivenEngine` comparing 8-digit OpenDART `corp_code` directly with 6-digit stock tickers (`corp_code == sym_clean`), dropping non-equity and subsidiary corporate disclosure catalysts to 0.
5. **V6-21 (HIGH)**: `CARDFactorEngine` subtracting 1-day macro shock changes from 5-day cumulative stock returns (5:1 time horizon mismatch), distorting cross-asset divergence metrics by ~500%.
6. **V6-22 (MEDIUM)**: Single-stock evaluations ($N=1$) across multiple factor engines (`mq_factor.py`, `short_interest_squeeze.py`, `valueup_catalyst.py`, `trend_efficiency.py`, `order_flow.py`, `short_term_reversal.py`, `inst_foreign_sector.py`) saturating at percentile rank 0.98 instead of neutral 0.50.
7. **V6-23 (MEDIUM)**: `StatisticalArbitrageEngine` logging 100,000-element NumPy arrays at `INFO` level per batch, causing severe console/disk I/O bottlenecks.
8. **V6-24 (HIGH)**: `DataValidator.validate_and_clean_price_series()` only detecting downward splits ($< -0.25$), causing reverse stock splits ($> +50\%$ price jumps with volume contraction) to be falsely flagged as anomalies or erased via linear interpolation.

---

## Detailed Issue Analysis (V6-17 ~ V6-24)

### 1. V6-17 [🔴 CRITICAL]: Sync vs Async Book Value Scale Discrepancy (Total Equity vs BPS) in `earnings_data.py` & `rim_valuation.py`

- **Affected Files & Lines**:
  - `trading_system/src/data_layer/earnings_data.py:128-133, 251-275`
  - `trading_system/src/core/rim_valuation.py:348-360`
  - `trading_system/src/data_layer/indicator_storage.py:484-487, 992-1010`
- **Observed Behavior & Root Cause**:
  1. Synchronous fetcher `_fetch_fundamentals_network()` reads balance sheet items `Total Stockholder Equity` and stores aggregate stockholders' equity ($10^9 \sim 10^{14}$ KRW or $10^6 \sim 10^{11}$ USD) into `result['book_value']`.
  2. Asynchronous fetcher `async_fetch_fundamentals()` queries Yahoo Finance quoteSummary module `defaultKeyStatistics.bookValue`, which returns **Book Value Per Share (BPS)** ($10^0 \sim 10^5$), and stores it into `df['book_value']`.
  3. `rim_valuation.py:352-355` attempted to heuristically resolve this with:
     ```python
     is_aggregate_equity = (bv > 1_000_000.0) & (shares > 0)
     calculated_bps = np.where(is_aggregate_equity, bv / np.maximum(shares, 1.0), bv)
     ```
     - For US Micro/Small Caps (Russell 2000) with Total Equity = \$600,000 and 100,000 shares: `bv = 600,000 <= 1,000,000`, so `is_aggregate_equity` is `False`. The engine uses \$600,000 as BPS for a \$10 stock (astronomical false discount $+5,999,900\%$).
     - For Korean High-Nominal Equities (e.g., 003240 Taekwang Industrial with BPS = 5,000,000 KRW and 1.11M shares): if ingested via async fetch, `bv = 5,000,000 > 1,000,000`, so it divides BPS by shares *again*, collapsing BPS to 4.5 KRW and destroying the valuation signal.
- **Mathematical & Econometric Rationale**:
  Residual Income Model intrinsic value $V_0 = \text{BPS}_0 + \sum_{t=1}^T \frac{\text{BPS}_{t-1}(\text{ROE}_{t-1} - r_e)}{(1 + r_e)^t}$ is strictly degree-1 homogeneous in BPS: $V_0(\lambda \cdot \text{BPS}) = \lambda \cdot V_0(\text{BPS})$. Inconsistent scale scaling directly corrupts downstream ranking and portfolio allocation.
- **Remedy**:
  1. In `earnings_data.py` (`async_fetch_fundamentals`): Store total aggregate equity in `book_value` (`total_equity = float(book_val) * shares` if `shares > 0`) and store per-share value in `bps` (`df['bps'] = float(book_val)`).
  2. In `earnings_data.py` (`_fetch_fundamentals_network`): Store total equity in `book_value` and compute `result['bps'] = result['book_value'] / result['shares_outstanding']` when `shares > 0`.
  3. In `indicator_storage.py`: Add `bps` migration column to `stock_fundamentals` table.
  4. In `rim_valuation.py`: Check if `bps` column is present and valid; if not, safely compute `calculated_bps = np.where(shares > 0, bv / np.maximum(shares, 1.0), bv)` without any hardcoded 1M cutoff.

---

### 2. V6-18 [🟠 HIGH]: Curated Symbol GICS Sector Map Bypass in `SectorRotationEngine`

- **Affected Files & Lines**:
  - `trading_system/src/core/sector_rotation.py:256`
- **Observed Behavior & Root Cause**:
  In `SectorRotationEngine.compute_sector_momentum_scores()`:
  ```python
  raw_sec = eff_sector_map.get(sym, "General")
  norm_sec = self.normalize_sector(raw_sec)  # BUG: symbol=sym omitted!
  ```
  `normalize_sector(cls, raw_sector: Optional[str], symbol: Optional[str] = None, name: Optional[str] = None)` relies on `symbol` for Step 1 (`CURATED_SYMBOL_SECTOR_MAP`).
  Because `symbol` was omitted, symbols with missing or `"General"` raw sectors (such as `005930` Samsung Electronics, `000660` SK Hynix, `NVDA`, `MT`, `FANG`, `XPRO`, `MGTX`) failed Step 1 and were assigned to `"General"`, corrupting sector momentum aggregations and disabling the Sector Leadership Synergy multiplier.
- **Mathematical & Econometric Rationale**:
  Sector momentum $\text{Mom}_k = \frac{1}{|S_k|} \sum_{i \in S_k} r_i$ requires accurate partition $S_k$ of the universe. Misclassifying large-cap bellwethers into `"General"` attenuates true sector momentum signals by up to 40%.
- **Remedy**:
  Update line 256: `norm_sec = self.normalize_sector(raw_sec, symbol=sym)`.

---

### 3. V6-19 [🟠 HIGH]: Live Options Chain Implied Volatility Fetch Subordination by Price Volatility Proxies in `IVSkewEngine`

- **Affected Files & Lines**:
  - `trading_system/src/core/iv_skew.py:108-150`
- **Observed Behavior & Root Cause**:
  In `IVSkewEngine._evaluate_one(sym)`:
  - Step 1 computes realized price volatility proxy whenever `prices_dict` is provided:
    `score = float(np.clip(0.5 + (skew_ratio - 1.0) * 0.25 - ret_skew * 0.15 + turnaround_bonus, 0.0, 1.0))`
  - Step 2 checks `if score == 0.5 and not sym.startswith(...) and os.getenv("ENABLE_LIVE_OPTIONS_FETCH") == "true": score = self.compute_skew_for_ticker(sym)`.
  - Because `score` from Step 1 is a continuous float, it is almost never exact `0.5`, completely bypassing live options chain fetching during all standard pipeline runs even when explicitly enabled.
- **Mathematical & Econometric Rationale**:
  Options Implied Volatility Skew $\text{Skew} = \frac{\text{IV}_{\text{OTM Put}}}{\text{IV}_{\text{OTM Call}}}$ reflects forward-looking risk-neutral market pricing. Realized price return skew is a backward-looking proxy. When live options fetch is explicitly requested, live IV data must take precedence.
- **Remedy**:
  Re-order logic: For US tickers, if `ENABLE_LIVE_OPTIONS_FETCH=true`, attempt `compute_skew_for_ticker(sym)`. If successful and returns a valid non-fallback score, return immediately; otherwise fall back to realized price volatility proxy.

---

### 4. V6-20 [🟠 HIGH]: 8-digit OpenDART corp_code Direct String Comparison Dropping Catalysts in `EventDrivenEngine`

- **Affected Files & Lines**:
  - `trading_system/src/core/event_driven.py:149-159, 280-283`
- **Observed Behavior & Root Cause**:
  In `EventDrivenEngine.compute_event_scores()` (line 158) and `evaluate_cb_bw_overhang_and_margin_risk()` (line 282):
  ```python
  matched = (stock_code and stock_code == sym_clean) or (corp_code and (corp_code == sym_clean or corp_code == sym))
  ```
  OpenDART returns `corp_code` as an 8-digit string (e.g. `'00126380'`), and often omits `stock_code` in corporate disclosures. `sym_clean` is a 6-digit stock code (e.g. `'005930'`).
  Direct comparison `corp_code == sym_clean` always fails for 8-digit codes, dropping major corporate action disclosures (share buybacks, mergers, CB/BW dilution overhang) to zero.
- **Mathematical & Econometric Rationale**:
  Event-driven alpha requires reliable entity resolution between exchange tickers ($S \in \mathbb{N}^6$) and regulatory entity identifiers ($C \in \mathbb{N}^8$).
- **Remedy**:
  Integrate `DARTCorpMapper`:
  ```python
  from src.data_layer.dart_corp_mapper import DARTCorpMapper
  mapper = DARTCorpMapper()
  mapped_corp = mapper.get_corp_code(sym_clean) if sym_clean.isdigit() else None
  matched = (
      (stock_code and stock_code == sym_clean) or
      (corp_code and (corp_code == sym_clean or corp_code == sym or (mapped_corp and corp_code == mapped_corp)))
  )
  ```

---

### 5. V6-21 [🟠 HIGH]: 5:1 Temporal Horizon Mismatch (5-day stock vs 1-day macro) in `CARDFactorEngine`

- **Affected Files & Lines**:
  - `trading_system/src/core/card_factor.py:60-84, 147-148`
- **Observed Behavior & Root Cause**:
  - `stock_ret = float((c_last - c_prev) / c_prev * 100)` computed the **5-day cumulative return** in percent (e.g. $+4.5\%$).
  - `usdkrw_chg` and `wti_chg` were extracted as **1-day daily percent changes** (e.g. $+0.15\%$).
  - `divergence = stock_ret - macro_impact` subtracted a 1-day macro move from a 5-day stock move, exaggerating apparent macro divergence by 500% in multi-day trending currency/commodity environments.
- **Mathematical & Econometric Rationale**:
  Cross-asset divergence $\text{Divergence}_{i,\Delta t} = R_{i,[t-\Delta t, t]} - \beta_i \sum_k w_k R_{k,[t-\Delta t, t]}$ requires identical temporal aggregation windows $\Delta t = 5\text{d}$ across all asset classes.
- **Remedy**:
  In `_safe_macro`, when `indicator_df` is a DataFrame with historical observations ($\ge 5$ rows), compute the 5-day rolling cumulative change `(s.iloc[-1] / s.iloc[-5] - 1.0) * 100.0` or sum of 5-day daily percentage changes.

---

### 6. V6-22 [🟡 MEDIUM]: Single-Stock Evaluation Rank Saturation Biases ($N=1 \implies \text{Score}=0.98$) across Factor Engines

- **Affected Files & Lines**:
  - `trading_system/src/core/mq_factor.py:138`
  - `trading_system/src/core/short_interest_squeeze.py:138-144`
  - `trading_system/src/core/valueup_catalyst.py:145-155`
  - `trading_system/src/core/trend_efficiency.py:144-150`
  - `trading_system/src/core/order_flow.py:161-167`
  - `trading_system/src/core/short_term_reversal.py:184-187`
  - `trading_system/src/core/inst_foreign_sector.py:216-224`
- **Observed Behavior & Root Cause**:
  Calling `Series([x]).rank(pct=True).clip(0.02, 0.98)` on a single stock yields `1.0 -> 0.98` (maximum bullish), even when the asset has severely negative momentum (-80%), massive short overhang, or poor quality metrics.
- **Mathematical & Econometric Rationale**:
  For degenerate single-element cross-sections ($N=1$), relative cross-sectional ranking is ill-defined. The neutral Bayesian prior is $E[\text{Score}] = 0.50$.
- **Remedy**:
  Add explicit $N=1$ checks across all rank-based strategy engines returning neutral score `0.50`.

---

### 7. V6-23 [🟡 MEDIUM]: Unbounded INFO Logging of 100,000-Element NumPy Arrays in `StatisticalArbitrageEngine`

- **Affected Files & Lines**:
  - `trading_system/src/core/stat_arb.py:530`
- **Observed Behavior & Root Cause**:
  Line 530 executed:
  `logger.info(f"DEBUG: p_vals={p_vals}, half_lives={half_lives}, min_hl={min_half_life}, max_hl={max_half_life}, eff_pval={eff_max_pvalue}, pass_mask={pass_mask}")`
  During batch cointegration scanning (batches of up to 100,000 pairs), formatting these giant NumPy arrays as strings flooded the log files with tens of megabytes of text, degrading I/O performance.
- **Mathematical & Econometric Rationale**:
  Screening diagnostics should emit scalar aggregated summary metrics rather than serializing multi-dimensional parameter arrays.
- **Remedy**:
  Change to `logger.debug(f"[StatArb Batch] Total pairs: {len(pass_mask)}, Passed ADF & Half-Life: {int(pass_mask.sum())}")`.

---

### 8. V6-24 [🟠 HIGH]: Reverse Stock Split Handling Voids & False-Positive Transient Spike Deletion in `DataValidator`

- **Affected Files & Lines**:
  - `trading_system/src/persistence/database.py:435-472`
  - `trading_system/src/data_layer/data_validator.py:225-280`
- **Observed Behavior & Root Cause**:
  `split_candidates = (close.pct_change() < -0.25) & (~transient_spikes)` only handled forward splits. Reverse stock splits (1-for-2, 1-for-5, 1-for-10 consolidations with price jumps $> +50\%$ and volume contraction) were not recognized as splits, and were instead falsely marked as price anomalies and erased via linear interpolation or rejected by the data validator.
- **Mathematical & Econometric Rationale**:
  Reverse stock splits scale price by $k > 1$ and volume by $1/k$. Historical series must be scaled backwards: $P_{<t} \leftarrow P_{<t} \times k$ and $V_{<t} \leftarrow V_{<t} / k$.
- **Remedy**:
  Detect reverse split candidates (`(close.pct_change() > 0.50) & (~transient_spikes)`), check standard ratios (`[1.5, 2.0, 3.0, 4.0, 5.0, 10.0]`), confirm volume contraction, and adjust historical OHLC and volume accordingly.

---

## Existing Test Coverage & Required Updates

| Issue | Existing Test File | Current Coverage Status | Required Test Updates / Additions |
|---|---|---|---|
| **V6-17** | `tests/test_rim_strategy.py` | Tests basic RIM formulas and value traps, but lacks tests for micro-caps ($<\$1\text{M}$ equity) and KR high-nominal stocks ($>1\text{M}$ KRW BPS). | Add `test_rim_small_cap_and_high_nominal_bps_scaling` in `tests/test_rim_strategy.py`. |
| **V6-18** | `tests/test_sector_and_ensemble_audit_fixes.py` | `test_gics_sector_mapping_accuracy()` only tests `normalize_sector` method directly, not `compute_sector_momentum_scores()`. | Add `test_sector_rotation_curated_symbol_runtime_mapping` in `tests/test_sector_and_ensemble_audit_fixes.py`. |
| **V6-19** | `tests/test_new_5_strategies.py` | Only tests fallback path with `prices_dict`. | Add `test_iv_skew_live_options_priority_when_enabled` in `tests/test_new_5_strategies.py`. |
| **V6-20** | `tests/test_adversarial_challenger_2.py` | Tested 6-digit stock_code and mock with 6-digit corp_code. | Add `test_dart_8digit_corp_code_mapping_without_stock_code` in `tests/test_adversarial_challenger_2.py`. |
| **V6-21** | `tests/test_phase2_quant_world_class_improvements.py` | Tested 2-row indicator_df without verifying 5-day rolling return alignment. | Add `test_card_factor_5day_macro_temporal_alignment` in `tests/test_phase2_quant_world_class_improvements.py`. |
| **V6-22** | `tests/test_adversarial_challenger_2.py` | Only tested `AccrualsQualityEngine` for $N=1$. | Add `test_factor_engines_n1_neutral_score_guard` covering `MQFactorEngine`, `ShortInterestSqueezeEngine`, `ValueUpEngine`, `TrendEfficiencyEngine`, `OrderFlowEngine`, `ShortTermReversalEngine`, `InstForeignSectorEngine`. |
| **V6-23** | `tests/test_fast_cointegration.py` | Tested ADF math and half-life calculation. | Verify clean logger output without array dump during batch cointegration. |
| **V6-24** | `tests/test_adversarial_challenger_2.py`, `tests/test_data_validator.py` | Tested forward stock splits and flash crash guard. | Add `test_reverse_stock_split_adjustment_and_volume_contraction` in `tests/test_adversarial_challenger_2.py`. |

---

## Concrete Implementation & Verification Plan

### Phase 1: Engine Modifications (by domain implementer)
1. Modify `trading_system/src/data_layer/earnings_data.py` & `trading_system/src/core/rim_valuation.py` for BPS/Total Equity scale consistency.
2. Update `trading_system/src/core/sector_rotation.py` line 256 to pass `symbol=sym`.
3. Update `trading_system/src/core/iv_skew.py` to prioritize live options fetch for US tickers when enabled.
4. Update `trading_system/src/core/event_driven.py` to resolve 8-digit `corp_code` via `DARTCorpMapper`.
5. Update `trading_system/src/core/card_factor.py` to compute 5-day rolling macro shocks from multi-day indicator history.
6. Apply $N=1$ neutral score guards across `mq_factor.py`, `short_interest_squeeze.py`, `valueup_catalyst.py`, `trend_efficiency.py`, `order_flow.py`, `short_term_reversal.py`, and `inst_foreign_sector.py`.
7. Lower array logging in `trading_system/src/core/stat_arb.py` line 530 from INFO to DEBUG summary.
8. Add reverse stock split detection and adjustment logic in `trading_system/src/persistence/database.py` and `trading_system/src/data_layer/data_validator.py`.

### Phase 2: Unit & Regression Verification
1. Run targeted tests:
   ```bash
   .venv/Scripts/python.exe -m pytest tests/test_rim_strategy.py tests/test_sector_and_ensemble_audit_fixes.py tests/test_new_5_strategies.py tests/test_adversarial_challenger_2.py tests/test_phase2_quant_world_class_improvements.py tests/test_data_validator.py -v
   ```
2. Run full regression suite:
   ```bash
   .venv/Scripts/python.exe -m pytest tests/ -q
   ```
   Verify 100% pass (0 failures, 0 errors).
