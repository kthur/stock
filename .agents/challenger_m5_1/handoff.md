# Empirical Sentiment Lexicon Stress Handoff Report — Milestone 5

**Author**: challenger_m5_1 (Empirical Sentiment Lexicon Stress Challenger 1)
**Date**: 2026-07-31
**Target Module**: `trading_system/src/core/llm_sentiment_engine.py` & `trading_system/src/data_layer/indicator_storage.py`

---

## 1. Observation

### Test Execution Commands & Verbatim Results
1. **Pytest Unit Test Suite Execution**:
   - Command: `.venv\Scripts\python.exe -m pytest trading_system/tests/test_llm_sentiment_engine.py -v`
   - Output:
     ```
     ============================= test session starts =============================
     platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
     rootdir: D:\Finance\code\stock\trading_system
     collected 7 items

     trading_system\tests\test_llm_sentiment_engine.py::test_filing_sentiment_metrics_dataclass PASSED [ 14%]
     trading_system\tests\test_llm_sentiment_engine.py::test_offline_lexicon_korean_dart PASSED [ 28%]
     trading_system\tests\test_llm_sentiment_engine.py::test_offline_lexicon_english_sec PASSED [ 42%]
     trading_system\tests\test_llm_sentiment_engine.py::test_sentiment_formula_exactness PASSED [ 57%]
     trading_system\tests\test_llm_sentiment_engine.py::test_sqlite_cache_integration PASSED [ 71%]
     trading_system\tests\test_llm_sentiment_engine.py::test_event_driven_sentiment_multiplier PASSED [ 85%]
     trading_system\tests\test_llm_sentiment_engine.py::test_m5_sentiment_coverage_report PASSED [100%]

     ============================== 7 passed in 1.45s ==============================
     ```

2. **Empirical Stress Harness Execution**:
   - Command: `.venv\Scripts\python.exe .agents/challenger_m5_1/stress_harness.py`
   - Output:
     ```
     ==========================================================================
           MILESTONE 5 EMPIRICAL STRESS & BOUNDARY TEST HARNESS
     ==========================================================================

     --- Running Suite A: Input Boundaries & Cleanliness ---
       [PASS] Empty string returns default neutral (0.5)
       [PASS] Whitespace-only string returns default neutral (0.5)
       [PASS] Special characters return neutral (0.5)
       [PASS] Non-financial text returns neutral (0.5)
       [PASS] Large text (1MB, ~200k terms) processed in 1.1924s. Tone: 1.0

     --- Running Suite B: High-Density Mixed Terms & Language Detection ---
       EN High Pos Tone: 0.9962, EN High Neg Tone: 0.0035
       EN Equal Mixed Tone: 0.5 (Expected neutral 0.5)
       KR filing with EN header Tone: 0.5
       [BUG Surface] Korean text with English header misidentified as English, missing KR terms!

     --- Running Suite C: Invalid Metadata & SQL Injection Resilience ---
       [PASS] Parameterized SQLite handles SQL injection strings safely without syntax error or table drop
       [PASS] Empty string filing date stored and retrieved properly

     --- Running Suite D: Concurrent SQLite Reads & Writes Stress Test ---
       [RESULT] Executed 2000 concurrent DB ops across 25 threads in 12.472s (160.4 ops/sec)
       [PASS] Zero locking errors under 25 concurrent worker threads!

     ==========================================================================
     SUMMARY: 1 BUG(S)/FAILURES DETECTED:
       - BUG DETECTED: Korean text with English header misclassified as English! Tone=0.5
     ==========================================================================
     ```

### Implementation Inspection Details
- **File Path**: `trading_system/src/core/llm_sentiment_engine.py`
- **Line 157**:
  ```python
  is_english = market in ["SP500", "NASDAQ", "RUSSELL2000"] or any(ord(c) < 128 for c in text[:50] if c.isalpha())
  ```
- **File Path**: `trading_system/src/data_layer/indicator_storage.py`
- **Lines 612-666**:
  SQLite operations for `filing_sentiment_cache` table use parameterized queries `(?)` and `with self._write_lock:`.

---

## 2. Logic Chain

1. **Language Detection Heuristic Failure**:
   - In `llm_sentiment_engine.py` line 157, `is_english` evaluates `any(ord(c) < 128 for c in text[:50] if c.isalpha())`.
   - When a Korean DART disclosure starts with English metadata or headers (e.g. `"DART Official Filing Report for Stock Symbol 005930. 당사는 영업이익증가 및 실적개선으로 흑자전환에 성공하였으며..."`), `text[:50]` contains ASCII alphabetic characters.
   - Therefore `is_english` evaluates to `True` even though `market="KOSPI"`.
   - As a result, the parser executes the English regex matching block (`POS_TERMS_EN` / `NEG_TERMS_EN`) and skips the Korean term count block (`POS_TERMS_KR` / `NEG_TERMS_KR`).
   - Korean positive financial terms ("영업이익증가", "실적개선", "흑자전환") are ignored, resulting in `n_pos = 0` and `n_neg = 0`.
   - The tone score evaluates to default `0.5` (neutral), failing to capture the strong bullish signal.

2. **Input Boundary Robustness**:
   - Empty text (`""`), whitespace-only (`"   "`), special characters (`"!@#$"`), and non-financial text safely fall back to `0.5` neutral scores without raising `ValueError` or `ZeroDivisionError`.
   - Very large disclosures (~1MB, ~200,000 terms) are processed in ~1.19 seconds without memory leak or buffer overflow.

3. **Database Concurrency & Injection Resilience**:
   - `save_filing_sentiment` and `get_filing_sentiment` use parameterized binding (`?`), preventing SQL injection attacks when malicious or unusual symbol / filing ID strings are stored.
   - Stress testing 2,000 concurrent DB operations across 25 parallel threads executed with zero database locking errors (160.4 ops/sec).

---

## 3. Caveats

- Primary LLM (`snunlp/KR-FinBert` / `ProsusAI/finbert`) was evaluated under offline / fallback mode (`use_primary_llm=False`), which safely defaulted to `_score_offline_lexicon`. Remote model weight download was not tested due to `CODE_ONLY` network isolation constraints.
- Korean text language detection was tested with ASCII headers in `text[:50]`. Texts with English headers located beyond character index 50 do not trigger this heuristic bug if index 1-50 contains Hangul characters (`ord(c) > 128`).

---

## 4. Conclusion

- **Overall Status**: **PASSED WITH 1 HIGH-PRIORITY HEURISTIC BUG FINDING**.
- The sentiment engine and cache layer are highly robust against invalid inputs, boundary conditions, SQL injection, and high-concurrency SQLite access.
- **Actionable Fix Recommendation**:
  Modify `llm_sentiment_engine.py` line 157 to test for explicit Korean Hangul characters or rely primarily on `market`:
  ```python
  # Recommended fix: check for Hangul characters (\uac00-\ud7a3) or market designation
  has_hangul = any('\uac00' <= c <= '\ud7a3' for c in text[:200])
  is_english = market in ["SP500", "NASDAQ", "RUSSELL2000"] or (not has_hangul and any(ord(c) < 128 for c in text[:50] if c.isalpha()))
  ```

---

## 5. Verification Method

To independently verify all findings and test suites:

1. **Run Pytest Suite**:
   ```bash
   .venv\Scripts\python.exe -m pytest trading_system/tests/test_llm_sentiment_engine.py -v
   ```
2. **Run Empirical Stress Harness**:
   ```bash
   .venv\Scripts\python.exe .agents/challenger_m5_1/stress_harness.py
   ```
3. **Invalidation Condition**:
   If `stress_harness.py` reports 0 failures and parses Korean text with English headers with `filing_tone_score > 0.5`, the language detection bug has been resolved.

---

## Adversarial Challenge Report

### Challenge Summary
**Overall Risk Assessment**: **MEDIUM**

### Challenges

#### [High] Challenge 1: Language Detection Heuristic Flaw on Korean Filings with English Headers
- **Assumption challenged**: The assumption that `any(ord(c) < 128 for c in text[:50] if c.isalpha())` accurately determines whether text is English.
- **Attack scenario**: A Korean DART disclosure starting with English system headers or stock metadata (e.g. `"DART Official Filing Report for Stock Symbol 005930. 당사는 영업이익증가 및 실적개선으로 흑자전환에 성공하였습니다."`).
- **Blast radius**: The engine misclassifies Korean filings as English, skipping Korean dictionary terms and returning false neutral scores (0.5 tone score) for highly positive or negative Korean corporate disclosures.
- **Mitigation**: Update language detection to check for presence of Korean Hangul range (`'\uac00' <= c <= '\ud7a3'`) or prioritize the `market` parameter.

### Stress Test Results

| Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|
| Empty string / Whitespace / Special Chars | Return neutral score (0.5) | Returned 0.5 tone & composite score | **PASS** |
| 1MB Large Text (~200k terms) | Fast execution without failure | Processed in 1.19s, tone=1.0 | **PASS** |
| High-Density Mixed EN Terms | Neutral score (0.5) for balanced pos/neg | Returned 0.5 tone score | **PASS** |
| SQL Injection in symbol / filing_id | Parameterized execution without error | Safely stored and retrieved | **PASS** |
| SQLite Concurrent Read/Write (25 threads, 2000 ops) | Zero locking errors | 0 errors, 160.4 ops/sec | **PASS** |
| Korean filing with English header | Correct Korean term matching (tone > 0.5) | Misclassified as EN, tone=0.5 | **FAIL (BUG)** |

### Unchallenged Areas
- Transformer model inference latency when `use_primary_llm=True` with GPU hardware (out of scope due to `CODE_ONLY` network isolation).
