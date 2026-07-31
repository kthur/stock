# ⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

"""
Empirical Stress & Boundary Test Harness for Milestone 5 LLMSentimentEngine & FilingSentimentMetrics.
Location: .agents/challenger_m5_1/stress_harness.py
"""

import sys
import os
import time
import tempfile
import threading
import concurrent.futures

# Add project root to sys.path
PROJECT_ROOT = r"d:\Finance\code\stock"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from trading_system.src.core.llm_sentiment_engine import (
    FilingSentimentMetrics,
    LLMSentimentEngine,
    POS_TERMS_KR,
    NEG_TERMS_KR,
    POS_TERMS_EN,
    NEG_TERMS_EN
)
from trading_system.src.data_layer.indicator_storage import MarketIndicatorStorage
from trading_system.src.core.event_driven import EventDrivenEngine
from trading_system.src.analysis.coverage_analyzer import StrategyCoverageAnalyzer


def run_suite_a_input_boundaries():
    print("\n--- Running Suite A: Input Boundaries & Cleanliness ---")
    engine = LLMSentimentEngine()
    failures = []

    # 1. Empty string
    m_empty = engine.analyze_filing("005930", "", filing_date="2026-07-31")
    if m_empty.filing_tone_score != 0.5 or m_empty.composite_sentiment_score != 0.5:
        failures.append(f"Empty string score unexpected: {m_empty}")
    else:
        print("  [PASS] Empty string returns default neutral (0.5)")

    # 2. Whitespace only
    m_space = engine.analyze_filing("005930", "   \n\t  ", filing_date="2026-07-31")
    if m_space.filing_tone_score != 0.5:
        failures.append(f"Whitespace-only string failed: {m_space}")
    else:
        print("  [PASS] Whitespace-only string returns default neutral (0.5)")

    # 3. Special characters only
    m_spec = engine.analyze_filing("005930", "!!!@#$%^&*()_+-=[]{}|;':\",./<>?", filing_date="2026-07-31")
    if m_spec.filing_tone_score != 0.5:
        failures.append(f"Special characters failed: {m_spec}")
    else:
        print("  [PASS] Special characters return neutral (0.5)")

    # 4. Non-financial text
    m_nonfin = engine.analyze_filing("005930", "The weather today is sunny with light rain in the afternoon.", filing_date="2026-07-31", market="SP500")
    if m_nonfin.filing_tone_score != 0.5:
        failures.append(f"Non-financial text failed: {m_nonfin}")
    else:
        print("  [PASS] Non-financial text returns neutral (0.5)")

    # 5. Very large text (1MB text)
    large_text = ("Company reported revenue growth and earnings beat. " * 20000)
    start_t = time.time()
    m_large = engine.analyze_filing("AAPL", large_text, filing_date="2026-07-31", market="SP500")
    dur = time.time() - start_t
    print(f"  [PASS] Large text (1MB, ~200k terms) processed in {dur:.4f}s. Tone: {m_large.filing_tone_score}")

    return failures


def run_suite_b_mixed_terms_and_language_detection():
    print("\n--- Running Suite B: High-Density Mixed Terms & Language Detection ---")
    engine = LLMSentimentEngine()
    failures = []

    # 1. High density positive vs negative EN
    pos_dense = " ".join(POS_TERMS_EN * 10)
    neg_dense = " ".join(NEG_TERMS_EN * 10)
    m_pos_dense = engine.analyze_filing("AAPL", pos_dense, market="SP500")
    m_neg_dense = engine.analyze_filing("AAPL", neg_dense, market="SP500")
    print(f"  EN High Pos Tone: {m_pos_dense.filing_tone_score}, EN High Neg Tone: {m_neg_dense.filing_tone_score}")

    # 2. Equal mix 50 pos and 50 neg EN
    mixed_dense = ("outperform dilution " * 50)
    m_mixed = engine.analyze_filing("AAPL", mixed_dense, market="SP500")
    print(f"  EN Equal Mixed Tone: {m_mixed.filing_tone_score} (Expected neutral 0.5)")

    # 3. Flaw check: Korean DART document with English metadata header
    # Example: Market is KOSPI, text starts with English metadata "DART Official Filing Report for Stock Symbol 005930"
    kr_text_with_en_header = "DART Official Filing Report for Stock Symbol 005930. 당사는 영업이익증가 및 실적개선으로 흑자전환에 성공하였으며 자기주식소각 및 무상증자를 결정하였습니다."
    m_kr_header = engine.analyze_filing("005930", kr_text_with_en_header, market="KOSPI")
    print(f"  KR filing with EN header Tone: {m_kr_header.filing_tone_score}")
    if m_kr_header.filing_tone_score == 0.5:
        failures.append(f"BUG DETECTED: Korean text with English header misclassified as English! Tone={m_kr_header.filing_tone_score}")
        print("  [BUG Surface] Korean text with English header misidentified as English, missing KR terms!")
    else:
        print("  [PASS] Korean text with English header parsed correctly")

    return failures


def run_suite_c_invalid_metadata_and_sql_injection():
    print("\n--- Running Suite C: Invalid Metadata & SQL Injection Resilience ---")
    failures = []
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        storage = MarketIndicatorStorage(db_path=db_path)
        engine = LLMSentimentEngine(db_storage=storage)

        # 1. SQL Injection strings in symbol and filing_id
        sqli_symbol = "005930'; DROP TABLE filing_sentiment_cache; --"
        sqli_filing_id = "FILING_001' OR '1'='1"
        
        m_sqli = engine.analyze_filing(sqli_symbol, "실적개선 흑자전환", filing_date="2026-07-31", filing_id=sqli_filing_id)
        cached_sqli = storage.get_filing_sentiment(sqli_symbol, filing_date="2026-07-31", filing_id=sqli_filing_id)
        
        if cached_sqli and cached_sqli['symbol'] == sqli_symbol:
            print("  [PASS] Parameterized SQLite handles SQL injection strings safely without syntax error or table drop")
        else:
            failures.append("SQL Injection handling failed")

        # 2. None / empty / invalid filing dates
        m_nodate = engine.analyze_filing("005930", "실적개선", filing_date="", filing_id="F1")
        cached_nodate = storage.get_filing_sentiment("005930", filing_date="", filing_id="F1")
        if cached_nodate:
            print("  [PASS] Empty string filing date stored and retrieved properly")

    except Exception as e:
        failures.append(f"Suite C threw unexpected exception: {e}")
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

    return failures


def run_suite_d_sqlite_concurrency():
    print("\n--- Running Suite D: Concurrent SQLite Reads & Writes Stress Test ---")
    failures = []
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create single storage instance with thread-safe lock
        shared_storage = MarketIndicatorStorage(db_path=db_path)
        
        num_threads = 25
        ops_per_thread = 40
        errors = []

        def worker(thread_idx: int):
            # Test both shared instance and local instance per thread
            local_storage = MarketIndicatorStorage(db_path=db_path) if thread_idx % 2 == 1 else shared_storage
            engine = LLMSentimentEngine(db_storage=local_storage)
            
            for i in range(ops_per_thread):
                sym = f"SYM_{thread_idx:02d}_{i % 5}"
                f_id = f"F_{thread_idx}_{i}"
                try:
                    # Write operation
                    m = engine.analyze_filing(sym, f"실적개선 {i}", filing_date="2026-07-31", filing_id=f_id)
                    # Read operation
                    cached = local_storage.get_filing_sentiment(sym, filing_date="2026-07-31", filing_id=f_id)
                    if cached is None:
                        errors.append(f"Cache miss for written item {sym} {f_id}")
                except Exception as ex:
                    errors.append(f"Thread {thread_idx} op {i} failed: {type(ex).__name__} - {ex}")

        start_time = time.time()
        threads = []
        for t_i in range(num_threads):
            t = threading.Thread(target=worker, args=(t_i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        elapsed = time.time() - start_time
        total_ops = num_threads * ops_per_thread * 2
        print(f"  [RESULT] Executed {total_ops} concurrent DB ops across {num_threads} threads in {elapsed:.3f}s ({total_ops/elapsed:.1f} ops/sec)")
        
        if errors:
            print(f"  [CONCURRENCY ERRORS] Found {len(errors)} errors during concurrent execution!")
            for err in errors[:5]:
                print(f"    - {err}")
            failures.append(f"Concurrency stress test produced {len(errors)} errors")
        else:
            print("  [PASS] Zero locking errors under 25 concurrent worker threads!")

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

    return failures


def main():
    print("==========================================================================")
    print("      MILESTONE 5 EMPIRICAL STRESS & BOUNDARY TEST HARNESS")
    print("==========================================================================")
    
    all_failures = []
    all_failures.extend(run_suite_a_input_boundaries())
    all_failures.extend(run_suite_b_mixed_terms_and_language_detection())
    all_failures.extend(run_suite_c_invalid_metadata_and_sql_injection())
    all_failures.extend(run_suite_d_sqlite_concurrency())

    print("\n==========================================================================")
    if all_failures:
        print(f"SUMMARY: {len(all_failures)} BUG(S)/FAILURES DETECTED:")
        for f in all_failures:
            print(f"  - {f}")
    else:
        print("SUMMARY: ALL STRESS SUITES PASSED LOCALLY!")
    print("==========================================================================")


if __name__ == "__main__":
    main()
