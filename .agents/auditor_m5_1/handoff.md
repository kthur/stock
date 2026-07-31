# Forensic Integrity Audit Report — Milestone 5

**Work Product**: LLM/NLP DART & SEC Filing Sentiment Engine (Milestone 5)
**Profile**: General Project
**Verdict**: CLEAN

---

## 1. Observation

Direct code & empirical observations:

1. **Core Implementation (`trading_system/src/core/llm_sentiment_engine.py`)**:
   - `FilingSentimentMetrics` dataclass defined with `symbol`, `filing_date`, `filing_tone_score`, `catalyst_surprise_score`, `composite_sentiment_score`, `confidence_score`, `source_type`.
   - Dictionaries: `POS_TERMS_KR` (15 terms), `NEG_TERMS_KR` (15 terms), `SURPRISE_HIGH_KR` (5 terms), `SURPRISE_LOW_KR` (5 terms), `POS_TERMS_EN` (13 terms), `NEG_TERMS_EN` (14 terms), `SURPRISE_HIGH_EN` (5 terms), `SURPRISE_LOW_EN` (5 terms).
   - Dual Architecture: `_score_primary_llm` uses HuggingFace `snunlp/KR-FinBert` / `ProsusAI/finbert` when configured. If unavailable or disabled, gracefully falls back to `_score_offline_lexicon`.
   - Scoring formulas implemented:
     `S_tone = clip(0.5 + (N_pos - N_neg)/(2 * (N_pos + N_neg + 1)), 0.0, 1.0)`
     `composite_sentiment_score = 0.6 * S_tone + 0.4 * S_surprise`

2. **SQLite DB Storage (`trading_system/src/data_layer/indicator_storage.py`)**:
   - Table `filing_sentiment_cache` schema created with composite primary key `(symbol, filing_date, filing_id)`.
   - `get_filing_sentiment()` (lines 602–638) queries cached records ordered by `created_at DESC`.
   - `save_filing_sentiment()` (lines 640–666) performs thread-safe `INSERT OR REPLACE INTO filing_sentiment_cache` using `self._write_lock`.

3. **Event-Driven Integration (`trading_system/src/core/event_driven.py`)**:
   - `incorporate_filing_sentiment()` (lines 71–94) applies formula:
     `intensity_delta = (composite_sentiment_score - 0.5) * 2.0 * confidence_score`
     `multiplier = 1.0 + np.clip(intensity_delta * 0.5, -0.5, 0.5)`  -> bounds [0.5, 1.5]
     `adjusted_score = np.clip(base_catalyst_score * multiplier, 0.0, 1.0)`
   - `compute_event_scores()` accepts `sentiment_map` and applies multiplier adjustments to candidates.

4. **Pipeline Orchestration (`trading_system/run_pipeline.py`)**:
   - Lines 1981–1999: Instantiates `LLMSentimentEngine`, calls `batch_analyze_filings(eff_filings)` on DART filings, and passes `sentiment_map` into `EventDrivenEngine.compute_event_scores`.
   - Lines 2605–2610: Invokes `coverage_analyzer.generate_m5_sentiment_report(m5_metrics, kst_now_str=kst_now_str)` and appends to `strategy_data_coverage_report.txt`.

5. **Root Forwarder (`src/core/llm_sentiment_engine.py`)**:
   - Re-exports `FilingSentimentMetrics` and `LLMSentimentEngine` from `trading_system.src.core.llm_sentiment_engine`.

6. **Test Suite Execution**:
   - Executed `.venv\Scripts\python.exe -m pytest trading_system/tests/test_llm_sentiment_engine.py tests/test_llm_sentiment_engine.py -v`.
   - Test results: 8 passed out of 8 tests in 2.38 seconds.

---

## 2. Logic Chain

1. **AST & Static Analysis**:
   - Inspected `trading_system/src/core/llm_sentiment_engine.py`. Verified that sentiment scores are calculated dynamically from text inputs and dictionary terms. No constant return values, mocked outputs, or pre-canned responses exist.
   - Inspected `indicator_storage.py`. Verified parameterized SQLite queries and thread-lock synchronization.
   - Inspected `event_driven.py`. Verified multiplier formula and strict clipping bounds [0.5, 1.5] for multiplier and [0.0, 1.0] for adjusted event scores.
   - Inspected `run_pipeline.py`. Verified end-to-end integration into Strategy 10 execution and coverage report output.

2. **Integrity Violations Audit**:
   - Prohibited Pattern 1 (Hardcoded test results): None found.
   - Prohibited Pattern 2 (Facade implementations): None found. Logic is genuinely implemented and executed.
   - Prohibited Pattern 3 (Fabricated verification outputs): None found.
   - Prohibited Pattern 4 (Self-certifying tests): None found. Test suite uses independent, synthesized inputs.
   - Prohibited Pattern 5 (Execution delegation bypasses): None found.

3. **Behavioral & Runtime Verification**:
   - Execution of pytest suite resulted in 8/8 tests passing, covering dataclass conversion, Korean DART parsing, English SEC parsing, exact formula calculation, SQLite DB caching hit/miss, sentiment multiplier scaling/clamping, report formatting, and root forwarder re-exports.

---

## 3. Caveats

- In offline/CODE_ONLY mode without downloaded model weights, `_score_primary_llm` safely catches transformers exception and falls back to `_score_offline_lexicon` with `confidence_score=0.7`. This is by design and handles offline constraints robustly.
- No caveats.

---

## 4. Conclusion

The Milestone 5 (LLM/NLP DART & SEC Filing Sentiment Engine) implementation is authentic, rigorous, fully tested, and cleanly integrated across all target files.

**Final Verdict**: `CLEAN`

---

## 5. Verification Method

To independently re-verify this audit verdict:

1. Run the test suite:
   ```bash
   .venv\Scripts\python.exe -m pytest trading_system/tests/test_llm_sentiment_engine.py tests/test_llm_sentiment_engine.py -v
   ```
2. Confirm 8 tests pass without warnings or errors.
3. Inspect target files for hardcoded values:
   - `trading_system/src/core/llm_sentiment_engine.py`
   - `trading_system/src/data_layer/indicator_storage.py`
   - `trading_system/src/core/event_driven.py`
   - `trading_system/run_pipeline.py`
