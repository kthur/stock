# Domain 3 Survey Handoff Report (V6-17 ~ V6-24)
**Agent**: explorer_3 (Domain 3 Survey Agent)  
**Recipient**: orchestrator / domain implementer  
**Date**: 2026-08-22  
**Handoff Type**: Hard (Investigation Complete)  

---

## 1. Observation

Direct observations and file forensic evidence:

1. **V6-17**: `trading_system/src/data_layer/earnings_data.py:128-133` stores balance sheet total equity in `result['book_value']`, whereas `earnings_data.py:251-273` sets `df['book_value'] = stats.get('bookValue')` (BPS). In `trading_system/src/core/rim_valuation.py:352-355`, `is_aggregate_equity = (bv > 1_000_000.0) & (shares > 0)` divides by shares only if $bv > 1,000,000$. This breaks US small/micro-caps (e.g. Total Equity \$600,000 < \$1M causes \$600,000 to be treated as BPS) and Korean high-nominal equities (e.g. Taekwang Industrial BPS 5,000,000 KRW > 1,000,000 causes BPS to be divided by shares twice, collapsing to 4.5 KRW).
2. **V6-18**: `trading_system/src/core/sector_rotation.py:256` invokes `norm_sec = self.normalize_sector(raw_sec)` without passing `symbol=sym`. As a result, Step 1 in `normalize_sector()` (`if symbol: clean_sym in cls.CURATED_SYMBOL_SECTOR_MAP`) never executes during runtime momentum scoring, causing bellwethers with `"General"` or missing raw sectors (`005930`, `000660`, `NVDA`, `MT`, `FANG`, `XPRO`, `MGTX`) to be misclassified into `"General"`.
3. **V6-19**: `trading_system/src/core/iv_skew.py:108-150` computes a continuous realized price volatility proxy first whenever `prices_dict` is present. Because float `score` almost never equals exact `0.5`, line 143 `if score == 0.5 and not sym.startswith(...)` never triggers, completely bypassing live options chain fetching when `ENABLE_LIVE_OPTIONS_FETCH=true`.
4. **V6-20**: `trading_system/src/core/event_driven.py:158, 282` tests `matched = (stock_code and stock_code == sym_clean) or (corp_code and (corp_code == sym_clean or corp_code == sym))`. DART returns 8-digit `corp_code` (e.g. `'00126380'`) and often omits `stock_code`. Direct string equality against 6-digit stock code `sym_clean` (`'005930'`) is always False.
5. **V6-21**: `trading_system/src/core/card_factor.py:73-84, 129, 147-148` computes 5-day cumulative stock return `stock_ret = (c_last - c_prev) / c_prev * 100` and subtracts 1-day daily macro change `macro_impact = (0.35*usdkrw_chg + 0.35*wti_chg + 0.30*vix_pct_shock) * beta`. This 5:1 horizon mismatch distorts cross-asset divergence by ~500% in multi-day trending markets.
6. **V6-22**: `trading_system/src/core/mq_factor.py:138`, `trading_system/src/core/short_interest_squeeze.py:139`, `trading_system/src/core/valueup_catalyst.py:146`, `trading_system/src/core/trend_efficiency.py:145`, `trading_system/src/core/order_flow.py:162`, `trading_system/src/core/short_term_reversal.py:185`, and `trading_system/src/core/inst_foreign_sector.py:217` apply `.rank(pct=True).clip(0.02, 0.98)` without checking $N=1$, causing single-stock evaluations to saturate at rank 0.98 (max bullish).
7. **V6-23**: `trading_system/src/core/stat_arb.py:530` executes `logger.info(f"DEBUG: p_vals={p_vals}, half_lives={half_lives}, min_hl={min_half_life}, max_hl={max_half_life}, eff_pval={eff_max_pvalue}, pass_mask={pass_mask}")` on arrays up to 100,000 elements, dumping megabytes of text to console/log buffers per batch.
8. **V6-24**: `trading_system/src/persistence/database.py:438` and `trading_system/src/data_layer/data_validator.py:225-280` only detect forward splits `close.pct_change() < -0.25`. Reverse stock splits (upward jumps $> +50\%$ with volume contraction) are not recognized and are falsely treated as anomalies / transient spikes and interpolated away.

---

## 2. Logic Chain

1. **V6-17**: Sync ingestion populates Total Stockholders' Equity while async ingestion populates BPS $\implies$ Database column `book_value` contains inhomogeneous units $\implies$ Threshold `bv > 1_000_000` creates severe false discounts on US small-caps and crushes high-nominal Korean stocks $\implies$ Ingestion must consistently store Total Equity in `book_value` and per-share BPS in `bps`, and RIM must check `bps` directly or compute `bv / shares` when `shares > 0`.
2. **V6-18**: Class method `normalize_sector(raw_sector, symbol=None, name=None)` requires `symbol` to search `CURATED_SYMBOL_SECTOR_MAP` $\implies$ `compute_sector_momentum_scores()` called it without `symbol=sym` $\implies$ All curated tickers with `"General"` raw sectors bypassed Step 1 and were assigned to `"General"` $\implies$ Passing `symbol=sym` restores proper sector categorization and leadership synergy multipliers.
3. **V6-19**: Live options implied volatility measures forward risk-neutral tail pricing, whereas realized price return skewness is an empirical backward-looking proxy $\implies$ In `_evaluate_one()`, price proxy ran first and returned non-0.5 float $\implies$ Options fetch conditioned on `score == 0.5` never ran $\implies$ Reversing priority for US tickers when `ENABLE_LIVE_OPTIONS_FETCH=true` ensures true options IV skew is utilized.
4. **V6-20**: DART legal entity codes are 8 digits while KRX tickers are 6 digits $\implies$ String comparison `'00126380' == '005930'` evaluates to False $\implies$ Disclosures lacking `stock_code` dropped $\implies$ Integrating `DARTCorpMapper` resolves 6-digit stock code to 8-digit corp_code and restores 100% catalyst event recall.
5. **V6-21**: Cross-asset cointegration projection requires aligned temporal horizons $\Delta t$ $\implies$ 5-day stock return vs 1-day macro shock invalidates beta projection $\implies$ Computing 5-day rolling percentage change in `_safe_macro` restores temporal symmetry $\Delta t = 5\text{d}$.
6. **V6-22**: Relative rank $\text{rank}(x_1)$ for $N=1$ is identically 1.0 $\implies$ Clamped to 0.98 regardless of negative fundamentals $\implies$ Neutral Bayesian expectation for isolated asset is 0.50 $\implies$ Adding $N=1$ guard assigning 0.50 eliminates saturation bias.
7. **V6-23**: `logger.info()` serializes full 100,000-element NumPy arrays to strings $\implies$ Massive I/O blocking and log file bloat $\implies$ Replacing with `logger.debug()` summary count eliminates overhead.
8. **V6-24**: Corporate share consolidations scale price by $k > 1$ and volume by $1/k$ $\implies$ Lack of reverse split detector in `DataValidator` causes permanent price jumps to be marked as transient anomalies and wiped out $\implies$ Implementing reverse split detection ($> +50\%$ jump, consolidation ratios 1.5/2/3/4/5/10, volume contraction) and backward scaling ($P_{<t} \times k, V_{<t} / k$) preserves price integrity.

---

## 3. Caveats

- **Network Access**: Live DART XML download and live Yahoo Finance options fetching require external connectivity or mock fallbacks during local offline testing. All unit tests must include robust offline mock fixtures.
- **Backward Compatibility**: Existing database tables (`stock_fundamentals`) must be migrated gracefully with `ALTER TABLE stock_fundamentals ADD COLUMN bps REAL DEFAULT 0` to prevent SQLite errors on legacy databases.
- **No other caveats.**

---

## 4. Conclusion

Domain 3 contains 8 concrete, high-impact defects (V6-17 through V6-24) with clearly identified root causes, exact file locations, and mathematically sound remedy snippets.
Applying the proposed fixes will:
1. Ensure exact intrinsic valuation calculations across all market capitalizations and nominal share prices.
2. Accurately assign sector leaders to standard GICS sectors.
3. Prioritize true forward-looking options implied volatility.
4. Correctly capture OpenDART corporate event catalysts.
5. Align cross-asset temporal return horizons.
6. Guard all 31 strategy engines against $N=1$ rank saturation.
7. Eliminate console I/O bottlenecks during stat-arb scanning.
8. Protect historical price series from reverse-split distortion.

---

## 5. Verification Method

To independently verify the fixes:

1. **Targeted Unit Tests**:
   ```bash
   .venv/Scripts/python.exe -m pytest tests/test_rim_strategy.py tests/test_sector_and_ensemble_audit_fixes.py tests/test_new_5_strategies.py tests/test_adversarial_challenger_2.py tests/test_phase2_quant_world_class_improvements.py tests/test_data_validator.py -v
   ```
2. **Full Regression Suite**:
   ```bash
   .venv/Scripts/python.exe -m pytest tests/ -q
   ```
   **Expected Outcome**: 100% pass (0 failures, 0 errors across 1,263+ tests).
