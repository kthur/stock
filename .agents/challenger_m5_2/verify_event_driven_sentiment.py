import os
import sys
import numpy as np
import pytest

# Ensure root import path
sys.path.insert(0, r"d:\Finance\code\stock")

from trading_system.src.core.event_driven import EventDrivenEngine

class DummyMetrics:
    def __init__(self, composite_sentiment_score=0.5, confidence_score=1.0):
        self.composite_sentiment_score = composite_sentiment_score
        self.confidence_score = confidence_score

def run_tests():
    engine = EventDrivenEngine()
    print("=== STARTING EMPIRICAL VERIFICATION FOR EVENT DRIVEN SENTIMENT ===")
    
    failures = []
    
    # 1. Output score bounding [0.0, 1.0]
    print("\n--- Testing Requirement 1: Score Bounding [0.0, 1.0] ---")
    base_scores = [-10.0, -1.0, -0.01, 0.0, 0.1, 0.5, 0.9, 1.0, 1.01, 2.0, 10.0, 100.0]
    comp_scores = [-2.0, -0.5, 0.0, 0.1, 0.5, 0.9, 1.0, 1.5, 2.0]
    conf_scores = [-1.0, 0.0, 0.5, 1.0, 2.0]
    
    bounded_pass_count = 0
    total_bound_tests = 0
    for b in base_scores:
        for comp in comp_scores:
            for conf in conf_scores:
                total_bound_tests += 1
                m = DummyMetrics(comp, conf)
                res = engine.incorporate_filing_sentiment("TEST", b, m)
                if not isinstance(res, float):
                    failures.append(f"Return type not float: {type(res)} for b={b}, comp={comp}, conf={conf}")
                if np.isnan(res):
                    failures.append(f"Return value is NaN for b={b}, comp={comp}, conf={conf}")
                elif res < 0.0 or res > 1.0:
                    failures.append(f"Out of bounds output: {res} for b={b}, comp={comp}, conf={conf}")
                else:
                    bounded_pass_count += 1
                    
    print(f"Score Bounding Tests: {bounded_pass_count}/{total_bound_tests} PASSED")
    
    # 2. Monotonicity & Multiplier range [0.5x, 1.5x]
    print("\n--- Testing Requirement 2: Monotonicity & Multiplier Bounds ---")
    base = 0.5
    
    # Positive sentiment (comp > 0.5) monotonicity test
    comp_pos_grid = np.linspace(0.5, 1.0, 51)
    prev_score = -1.0
    pos_monotonic = True
    for comp in comp_pos_grid:
        m = DummyMetrics(comp, 1.0)
        res = engine.incorporate_filing_sentiment("TEST", base, m)
        mult = res / base
        if comp == 0.5 and not pytest.approx(mult, abs=1e-6) == 1.0:
            failures.append(f"At comp=0.5, multiplier is {mult}, expected 1.0")
        if comp == 1.0 and not pytest.approx(mult, abs=1e-6) == 1.5:
            failures.append(f"At comp=1.0, multiplier is {mult}, expected 1.5")
        if res < prev_score:
            pos_monotonic = False
            failures.append(f"Positive monotonicity violated: comp={comp}, res={res} < prev={prev_score}")
        prev_score = res
    print(f"Positive sentiment monotonicity check (comp 0.5 -> 1.0, mult 1.0x -> 1.5x): {'PASSED' if pos_monotonic else 'FAILED'}")

    # Negative sentiment (comp < 0.5) monotonicity test
    comp_neg_grid = np.linspace(0.5, 0.0, 51)
    prev_score = 999.0
    neg_monotonic = True
    for comp in comp_neg_grid:
        m = DummyMetrics(comp, 1.0)
        res = engine.incorporate_filing_sentiment("TEST", base, m)
        mult = res / base
        if comp == 0.0 and not pytest.approx(mult, abs=1e-6) == 0.5:
            failures.append(f"At comp=0.0, multiplier is {mult}, expected 0.5")
        if res > prev_score:
            neg_monotonic = False
            failures.append(f"Negative monotonicity violated: comp={comp}, res={res} > prev={prev_score}")
        prev_score = res
    print(f"Negative sentiment monotonicity check (comp 0.5 -> 0.0, mult 1.0x -> 0.5x): {'PASSED' if neg_monotonic else 'FAILED'}")

    # 3. Zero Confidence Exact 1.0x Multiplier
    print("\n--- Testing Requirement 3: Zero Confidence Exact 1.0x Multiplier ---")
    zero_conf_pass = True
    for comp in np.linspace(0.0, 1.0, 21):
        m = DummyMetrics(comp, 0.0)
        for b in [0.1, 0.4, 0.6, 0.8, 1.0]:
            res = engine.incorporate_filing_sentiment("TEST", b, m)
            expected = min(1.0, max(0.0, b))
            if not pytest.approx(res, abs=1e-7) == expected:
                zero_conf_pass = False
                failures.append(f"Zero confidence failure: b={b}, comp={comp}, conf=0.0 yielded {res}, expected {expected}")
    print(f"Zero confidence 1.0x multiplier check: {'PASSED' if zero_conf_pass else 'FAILED'}")

    # 4. Deep Edge Cases & Adversarial Inputs
    print("\n--- Testing Requirement 4: Edge Cases & Adversarial Stress Tests ---")
    
    # None sentiment_metrics
    res_none = engine.incorporate_filing_sentiment("TEST", 0.7, None)
    if res_none != 0.7:
        failures.append(f"sentiment_metrics=None yielded {res_none}, expected 0.7")

    # None sentiment_metrics with out-of-bound base score
    res_none_oob = engine.incorporate_filing_sentiment("TEST", 1.5, None)
    print(f"Notice: sentiment_metrics=None with base_score=1.5 returns {res_none_oob} (unclipped base score)")

    # Dict metric instead of object (e.g. if dict passed by mistake)
    dict_metric = {"composite_sentiment_score": 0.9, "confidence_score": 1.0}
    res_dict = engine.incorporate_filing_sentiment("TEST", 0.5, dict_metric)
    print(f"Dict metric handling: comp=0.9 passed as dict yielded {res_dict} (getattr returned default 0.5 -> mult 1.0x)")

    # Extreme base score saturation clipping check
    res_sat_pos = engine.incorporate_filing_sentiment("TEST", 0.9, DummyMetrics(1.0, 1.0))
    # 0.9 * 1.5 = 1.35 -> clipped to 1.0
    if res_sat_pos != 1.0:
        failures.append(f"Base score saturation failed: 0.9 * 1.5 yielded {res_sat_pos}, expected 1.0")

    res_sat_neg = engine.incorporate_filing_sentiment("TEST", 0.0, DummyMetrics(0.0, 1.0))
    # 0.0 * 0.5 = 0.0 -> clipped to 0.0
    if res_sat_neg != 0.0:
        failures.append(f"Base score saturation failed: 0.0 * 0.5 yielded {res_sat_neg}, expected 0.0")

    # NaN handling
    nan_metric = DummyMetrics(np.nan, 1.0)
    res_nan = engine.incorporate_filing_sentiment("TEST", 0.5, nan_metric)
    print(f"NaN composite sentiment score result: {res_nan}")
    if np.isnan(res_nan):
        failures.append(f"NaN input produced NaN output: {res_nan}")

    print("\n=== SUMMARY OF EMPIRICAL VERIFICATION ===")
    if failures:
        print(f"TOTAL FAILURES DETECTED: {len(failures)}")
        for idx, f in enumerate(failures, 1):
            print(f"  {idx}. {f}")
    else:
        print("ALL CRITICAL ASSERTIONS PASSED PERFECTLY!")

if __name__ == "__main__":
    run_tests()
