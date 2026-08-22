# Domain 3 Handoff Report: 31-Strategy Engines & Data Layer

**Auditor / Agent**: Chief Quantitative Strategy & Financial Econometrics Auditor (Domain 3: 31-Strategy Engines & Data Layer)  
**Target Scope**: `trading_system/src/core/` (Strategy 01 ~ 31), `trading_system/src/data_layer/`, `trading_system/src/persistence/`  
**Report Version**: v6.0 Candidate Tasks (V6-17 ~ V6-24)  
**Date**: 2026-08-22 (KST)  

---

## 1. Observation

Direct line-by-line inspection across the 31 strategy engines and data persistence modules identified 8 distinct, verified defects:

1. **`src/data_layer/earnings_data.py:128-133, 251-259` & `src/core/rim_valuation.py:351-355`**:
   - `_fetch_fundamentals_network` stores Total Stockholders' Equity in `book_value` ($10^9 \sim 10^{14}$), while `async_fetch_fundamentals` stores Book Value Per Share (BPS) ($10^0 \sim 10^5$).
   - `rim_valuation.py` lines 353-354 uses `is_aggregate_equity = (bv > 1_000_000.0) & (shares > 0)`.
   - Small-cap US equities ($bv \le 1,000,000$) use Total Equity as BPS (+5,999,900% false discount); high-priced Korean equities ($bv > 1,000,000$ in async mode) divide BPS by shares twice, collapsing BPS to 0.001 KRW.

2. **`src/core/sector_rotation.py:256`**:
   - `norm_sec = self.normalize_sector(raw_sec)` is called without `symbol=sym`.
   - Step 1 of `normalize_sector` (`cls.CURATED_SYMBOL_SECTOR_MAP`) is bypassed, classifying major equities (005930, 000660, NVDA, MT, FANG) as `"General"`.

3. **`src/core/iv_skew.py:108-147`**:
   - In `_evaluate_one(sym)`, in-memory price volatility proxy calculates `score = np.clip(0.5 + ...)` first.
   - The subsequent check `if score == 0.5 and ...: score = self.compute_skew_for_ticker(sym)` is never entered when price data exists, completely bypassing live options chain IV calculations.

4. **`src/core/event_driven.py:149-158, 280-283`**:
   - `matched = (stock_code and stock_code == sym_clean) or (corp_code and (corp_code == sym_clean or corp_code == sym))` compares 8-digit DART `corp_code` to 6-digit stock ticker `sym_clean`.
   - Disclosures with missing `stock_code` (subsidiary/holding filings) fail to match, zeroing event catalysts and CB/BW overhang risk traps.

5. **`src/core/card_factor.py:73-84, 129-148`**:
   - `stock_ret` is a 5-day return ($T$ vs $T-5$), whereas `usdkrw_chg` and `wti_chg` are 1-day daily changes ($\Delta \text{FX}_{1d}$).
   - `divergence = stock_ret - macro_impact` subtracts 1-day macro shocks from 5-day equity moves, distorting cross-asset alpha by 5x.

6. **`src/core/mq_factor.py:138`, `src/core/short_interest_squeeze.py:139-140`, `src/core/valueup_catalyst.py:146-147`, `src/core/trend_efficiency.py:145-146`**:
   - Cross-sectional percentile rank `Series.rank(pct=True).clip(0.02, 0.98)` on single-stock evaluations ($N=1$) returns `1.0 \implies 0.98` (max bullish score), even for deeply unprofitable or crashing assets.

7. **`src/core/stat_arb.py:530`**:
   - `logger.info(f"DEBUG: p_vals={p_vals}, half_lives={half_lives}, ...")` serializes 100,000-element NumPy arrays to INFO logs on every batch run.

8. **`src/persistence/database.py:426, 455-471`**:
   - `DataValidator` only checks forward splits ($P_t / P_{t-1} < -0.25$).
   - Reverse stock splits ($P_t / P_{t-1} \in [1.5, 2.0, 3.0, 5.0, 10.0]$) trigger the $>0.65$ jump anomaly detector and are erased via linear interpolation.

---

## 2. Logic Chain

1. **V6-17**: Inconsistent definitions of `book_value` in data fetchers $\to$ heuristics-based BPS derivation $\to$ threshold failure on micro caps & high-price stocks $\to$ extreme RIM valuation distortion.
2. **V6-18**: Omission of `symbol` parameter in caller $\to$ bypass of curated dictionary lookup $\to$ misclassification into `"General"` sector $\to$ muted sector momentum and lost leadership synergy.
3. **V6-19**: Fallback proxy executed before primary data source $\to$ continuous floating-point score prevents neutral branch trigger $\to$ live options IV chain bypassed.
4. **V6-20**: DART 8-digit identifier directly checked against 6-digit exchange ticker $\to$ string equality always False when `stock_code` empty $\to$ corporate event signals dropped.
5. **V6-21**: Asymmetric horizon inputs ($\Delta t = 5\text{d}$ vs $\Delta t = 1\text{d}$) in linear factor model $\to$ scale mismatch in residual $\to$ spurious cross-asset divergence scores.
6. **V6-22**: Degenerate cross-section rank behavior ($N=1 \implies \text{pct\_rank}=1.0$) $\to$ upper-bound clamping $\to$ false max-conviction signal for single candidate checks.
7. **V6-23**: Verbose array formatting inside batch loop at INFO severity $\to$ I/O blocking and multi-megabyte log generation.
8. **V6-24**: One-sided split detection $\to$ upward jump from reverse split flagged as data error $\to$ interpolation erases legitimate price history.

---

## 3. Caveats

- **External Data Availability**: Testing live options chain retrieval (`iv_skew.py`, `gamma_squeeze.py`) in offline environments relies on mock fixtures or recorded test parquets.
- **DART XML Cache**: DART corporate code resolution requires `dart_corp_codes.json` or live OpenDART XML downloads for complete corporate code coverage.
- **Scope Isolation**: These findings focus strictly on Domain 3 strategy engines and persistence. Interactions with Portfolio Allocator (Domain 2) and Execution OMS (Domain 4) rely on standard DataFrame interfaces.

---

## 4. Conclusion

All 8 identified defects are 100% novel, non-overlapping with historical v1~v5 items, mathematically substantiated, and verified against the actual repository source code. Concrete before/after git diffs have been documented in `analysis.md` and are ready for inclusion in `system_improvement_report_v6.md`.

---

## 5. Verification Method

1. **Full Test Suite Execution**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/ -q
   ```
2. **Targeted Domain 3 Strategy Tests**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_rim_valuation.py tests/test_sector_rotation.py tests/test_iv_skew.py tests/test_event_driven.py tests/test_card_factor.py tests/test_database.py -v
   ```
3. **Inspect Implementation Analysis**:
   - Review `d:\Finance\code\stock\.agents\explorer_d3_strategies\analysis.md` for complete mathematical rationales and before/after code snippets.
