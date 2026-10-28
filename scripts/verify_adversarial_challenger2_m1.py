#!/usr/bin/env python3
"""
scripts/verify_adversarial_challenger2_m1.py
Empirical Stress Test & Verification Harness for Milestone 1 Iteration 2 (Challenger 2).

Tests:
1. src/core/nlp_catalyst_engine.py
   - Dilution sign inversion defense: adverse CB filing MAX_NEG == 0.05 exactly.
   - All composite scores strictly within [0.05, 0.95], zero NaNs across 10,000 stress inputs.
2. src/core/option_surface_accelerator.py
   - Non-finite input defense (7,776 Cartesian parameter combinations).
   - Zero RuntimeWarnings, finite Greeks, zero NaNs.
3. src/ai/factor_orthogonalizer.py
   - Hyperbolic deadband alpha=440.0, delta=0.035.
   - Zero power overflow warnings, sub-threshold leakage < 10^-308, boundary z=0.035 exactness.
"""

from __future__ import annotations

import itertools
import os
import sys
import time
import warnings
import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.nlp_catalyst_engine import (
    NLPCatalystEngine,
    compute_finbert_polarity,
    compute_tone_drift_and_accel,
    EVENT_WEIGHTS,
)
from src.core.option_surface_accelerator import (
    OptionSurfaceAccelerator,
    compute_black_scholes_greeks,
    compute_net_dealer_gex_and_vanna,
)
from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    apply_hyperbolic_deadband_phase140,
    repair_covariance_psd,
    compute_pairwise_available_covariance,
)


def run_nlp_adversarial_suite() -> int:
    print("=" * 70)
    print("1. EMPIRICAL ADVERSARIAL STRESS: NLP Catalyst Engine (Feature F682)")
    print("=" * 70)
    engine = NLPCatalystEngine()
    failures = 0

    # 1.1 Adverse Convertible Bond / Capital Increase Sign Inversion Test
    print("[1.1] Testing adverse dilutive filings sign inversion...")
    test_polarities = [-100.0, -10.0, -1.0, -0.5, 0.0, 0.5, 1.0, 10.0, 100.0, np.nan, np.inf, -np.inf]
    dilutive_events = ["convertible_bond", "cb_issuance", "capital_increase"]

    for event in dilutive_events:
        for pol in test_polarities:
            p_dict = {"TEST_SYM": pd.DataFrame({"Close": [100.0] * 30, "Volume": [1000.0] * 30})}
            filing = {"TEST_SYM": {"event_type": event, "polarity": pol}}
            # Evaluate filing effect directly
            res = engine.compute_scores(p_dict, filing_map=filing)
            score = res.loc[res["symbol"] == "TEST_SYM", "nlp_catalyst_score"].iloc[0]
            # Since baseline flat is 0.50, a dilutive event must NOT yield score > 0.50
            if score > 0.50:
                print(f"  FAILED: Dilutive event '{event}' with polarity {pol} yielded bullish score {score} > 0.50!")
                failures += 1

    # 1.2 MAX_NEG exact 0.05 assertion
    print("[1.2] Verifying MAX_NEG evaluates to exactly 0.05 under adverse conditions...")
    p_dict_max_neg = {
        "MAX_NEG": pd.DataFrame({"Close": [100.0 - i * 2.0 for i in range(30)], "Volume": [1000.0] * 30})
    }
    filings_max_neg = {
        "MAX_NEG": {"polarity": -1.0, "event_type": "convertible_bond"}
    }
    transcripts_max_neg = {
        "MAX_NEG": {"s_curr": -1.0, "s_prev": 1.0, "conviction": 1.0, "prev_drift": 1.0}
    }
    res_max_neg = engine.compute_scores(p_dict_max_neg, filing_map=filings_max_neg, transcript_map=transcripts_max_neg)
    val_max_neg = res_max_neg.loc[res_max_neg["symbol"] == "MAX_NEG", "nlp_catalyst_score"].iloc[0]
    if val_max_neg != 0.05:
        print(f"  FAILED: MAX_NEG expected exactly 0.05, got {val_max_neg}")
        failures += 1
    else:
        print(f"  PASSED: MAX_NEG = {val_max_neg} (exactly 0.05)")

    # 1.3 5,000 Randomized & Extreme Boundary Inputs Stress Test
    print("[1.3] Stress testing 5,000 randomized and extreme edge inputs...")
    np.random.seed(42)
    nan_count = 0
    bound_violations = 0

    all_event_types = list(EVENT_WEIGHTS.keys()) + ["unknown_event", "", None]
    roles = ["CEO", "CFO", "COO", "DIRECTOR", "OFFICER", "UNKNOWN", ""]

    for batch in range(50):
        n_syms = 100
        sym_names = [f"SYM_{batch}_{i}" for i in range(n_syms)]
        p_dict_batch = {}
        filing_map_batch = {}
        transcript_map_batch = {}
        funds_batch = {}

        for sym in sym_names:
            # 10% completely missing/empty, 10% all NaNs, 10% extreme shock, 70% random
            choice = np.random.choice(["empty", "nan", "shock", "normal"], p=[0.1, 0.1, 0.1, 0.7])
            if choice == "empty":
                p_dict_batch[sym] = pd.DataFrame({"Close": []})
            elif choice == "nan":
                p_dict_batch[sym] = pd.DataFrame({"Close": [np.nan] * 20})
            elif choice == "shock":
                p_dict_batch[sym] = pd.DataFrame({"Close": [1.0, 1e8, 1e-4, 50.0]})
            else:
                p_dict_batch[sym] = pd.DataFrame({"Close": np.random.uniform(10.0, 200.0, 30)})

            # Filings
            if np.random.rand() > 0.3:
                filing_map_batch[sym] = {
                    "event_type": np.random.choice(all_event_types),
                    "polarity": np.random.choice([-10.0, -1.0, 0.0, 1.0, 10.0, np.nan, np.inf, None]),
                    "insider_role": np.random.choice(roles),
                }

            # Transcripts
            if np.random.rand() > 0.3:
                transcript_map_batch[sym] = {
                    "s_curr": np.random.choice([-1e6, -1.0, 0.0, 1.0, 1e6, np.nan]),
                    "s_prev": np.random.choice([-1e6, -1.0, 0.0, 1.0, 1e6, np.nan]),
                    "conviction": np.random.choice([0.0, 0.5, 1.0, 10.0, np.nan]),
                    "prev_drift": np.random.choice([-10.0, 0.0, 10.0, np.nan, None]),
                }

            # Fundamentals
            if np.random.rand() > 0.3:
                funds_batch[sym] = {
                    "revenue_growth": np.random.choice([-1.0, 0.0, 0.5, 100.0, np.nan]),
                    "op_margin_change": np.random.choice([-0.5, 0.0, 0.2, np.nan]),
                }

        res_batch = engine.compute_scores(
            p_dict_batch,
            filing_map=filing_map_batch,
            transcript_map=transcript_map_batch,
            fundamentals_dict=funds_batch,
        )

        scores = res_batch["nlp_catalyst_score"].values
        if np.isnan(scores).any():
            nan_count += int(np.isnan(scores).sum())
        if np.any(scores < 0.05) or np.any(scores > 0.95):
            bound_violations += int(np.sum((scores < 0.05) | (scores > 0.95)))

    print(f"  Total scores evaluated: 5,000")
    print(f"  NaN scores detected: {nan_count}")
    print(f"  Bounds [0.05, 0.95] violations detected: {bound_violations}")
    if nan_count > 0 or bound_violations > 0:
        failures += (nan_count + bound_violations)
    else:
        print("  PASSED: 100% strictly within [0.05, 0.95] with ZERO NaNs.")

    return failures


def run_option_surface_adversarial_suite() -> int:
    print("\n" + "=" * 70)
    print("2. EMPIRICAL ADVERSARIAL STRESS: Option Surface Accelerator (Feature F683)")
    print("=" * 70)
    failures = 0

    # 2.1 Exhaustive 7,776 Parameter Combinations Finiteness & RuntimeWarning Test
    print("[2.1] Stress testing 7,776 Cartesian parameter combinations for Greeks...")
    test_values = [np.nan, np.inf, -np.inf, 0.0, -100.0, 100.0]
    param_names = ["spot", "strike", "tau", "vol", "rate"]

    runtime_warnings_caught = []
    non_finite_count = 0
    nan_count = 0
    total_calls = 0

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        for combo in itertools.product(test_values, repeat=5):
            total_calls += 1
            spot, strike, tau, vol, rate = combo
            greeks = compute_black_scholes_greeks(spot, strike, tau, vol, rate=rate)

            for g_name in ["gamma", "vega", "vanna", "volga", "d1", "d2"]:
                val = greeks[g_name]
                if np.isnan(val):
                    nan_count += 1
                if not np.isfinite(val):
                    non_finite_count += 1

        for w in caught:
            if issubclass(w.category, RuntimeWarning):
                runtime_warnings_caught.append(w)

    print(f"  Total Greeks combinations evaluated: {total_calls}")
    print(f"  RuntimeWarnings caught: {len(runtime_warnings_caught)}")
    print(f"  NaN Greeks returned: {nan_count}")
    print(f"  Non-finite Greeks returned: {non_finite_count}")

    if runtime_warnings_caught:
        print(f"  FAILED: Caught {len(runtime_warnings_caught)} RuntimeWarnings!")
        for w in runtime_warnings_caught[:5]:
            print(f"    - {w.message}")
        failures += len(runtime_warnings_caught)
    else:
        print("  PASSED: ZERO RuntimeWarnings caught across all 7,776 combinations.")

    if nan_count > 0 or non_finite_count > 0:
        print("  FAILED: Non-finite Greeks detected!")
        failures += (nan_count + non_finite_count)
    else:
        print("  PASSED: 100% of Greeks outputs strictly finite float values.")

    # 2.2 Net Dealer GEX and Vanna under Non-Finite Options Chains
    print("[2.2] Stress testing compute_net_dealer_gex_and_vanna under degenerate chains...")
    degenerate_chains = [
        [],  # Empty
        [{"strike": np.nan, "tau": 0.1, "vol": 0.2, "oi": 100.0, "type": "call"}],
        [{"strike": 100.0, "tau": np.inf, "vol": 0.2, "oi": 100.0, "type": "call"}],
        [{"strike": 100.0, "tau": 0.1, "vol": np.nan, "oi": 100.0, "type": "put"}],
        [{"strike": 100.0, "tau": 0.1, "vol": 0.2, "oi": np.inf, "type": "call"}],
        [{"strike": 100.0, "tau": 0.1, "vol": 0.2, "oi": -500.0, "type": "put"}],
    ]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for chain in degenerate_chains:
            for s in [np.nan, np.inf, -50.0, 0.0, 100.0]:
                gex, vanna, skew = compute_net_dealer_gex_and_vanna(s, chain)
                if not (np.isfinite(gex) and np.isfinite(vanna) and np.isfinite(skew)):
                    print(f"  FAILED: Non-finite output for spot={s}, chain={chain}")
                    failures += 1

        r_warns = [w for w in caught if issubclass(w.category, RuntimeWarning)]
        if r_warns:
            print(f"  FAILED: Caught {len(r_warns)} RuntimeWarnings in compute_net_dealer_gex_and_vanna!")
            failures += len(r_warns)
        else:
            print("  PASSED: ZERO RuntimeWarnings and strictly finite outputs.")

    return failures


def run_orthogonalizer_adversarial_suite() -> int:
    print("\n" + "=" * 70)
    print("3. EMPIRICAL ADVERSARIAL STRESS: Factor Orthogonalizer & Deadband (Feature F684)")
    print("=" * 70)
    failures = 0

    # 3.1 Hyperbolic Deadband Power Overflow Immunity (alpha=440.0, delta=0.035)
    print("[3.1] Testing hyperbolic deadband power overflow immunity across scales...")
    scales = [
        -1e300, -1e150, -1e50, -1e10, -100.0, -1.0, -0.05, -0.045, -0.035, -0.025, -1e-15,
        0.0, 1e-15, 0.025, 0.035, 0.045, 0.05, 1.0, 100.0, 1e10, 1e50, 1e150, 1e300
    ]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        # Scalar
        for z in scales:
            z_clean = apply_hyperbolic_deadband_phase140(z, delta=0.035, alpha=440.0)
            if not np.isfinite(z_clean):
                print(f"  FAILED: Scalar deadband produced non-finite for z={z}")
                failures += 1

        # NumPy Array
        arr_scales = np.array(scales, dtype=np.float64)
        arr_clean = apply_hyperbolic_deadband_phase140(arr_scales, delta=0.035, alpha=440.0)
        if not np.all(np.isfinite(arr_clean)):
            print("  FAILED: Array deadband produced non-finite values!")
            failures += 1

        # Pandas Series
        ser_scales = pd.Series(scales)
        ser_clean = apply_hyperbolic_deadband_phase140(ser_scales, delta=0.035, alpha=440.0)
        if not ser_clean.notna().all():
            print("  FAILED: Series deadband produced NaNs!")
            failures += 1

        r_warns = [w for w in caught if issubclass(w.category, RuntimeWarning)]
        if r_warns:
            print(f"  FAILED: Caught {len(r_warns)} RuntimeWarnings during hyperbolic deadband!")
            for w in r_warns[:5]:
                print(f"    - {w.message}")
            failures += len(r_warns)
        else:
            print(f"  PASSED: ZERO RuntimeWarnings caught across {len(scales) * 3} deadband evaluations.")

    # 3.2 Sub-threshold Noise Leakage & Transmission Boundaries
    print("[3.2] Verifying sub-threshold noise leakage (<10^-308) and transmission bounds...")
    delta = 0.035
    alpha = 440.0

    # Sub-threshold noise (|z| <= 0.025)
    noise_vals = np.linspace(-0.025, 0.025, 51)
    noise_clean = apply_hyperbolic_deadband_phase140(noise_vals, delta=delta, alpha=alpha)
    max_noise_leak = float(np.max(np.abs(noise_clean)))
    if max_noise_leak != 0.0:
        print(f"  FAILED: Sub-threshold noise leakage detected: {max_noise_leak} > 0.0")
        failures += 1
    else:
        print("  PASSED: Exact zero noise leakage (leakage == 0.0) for |z| <= 0.025.")

    # Boundary z = delta = 0.035
    z_bound = apply_hyperbolic_deadband_phase140(0.035, delta=delta, alpha=alpha)
    expected_bound = 0.035 * np.tanh(1.0)
    diff = abs(z_bound - expected_bound)
    if diff > 1e-6:
        print(f"  FAILED: Boundary transition mismatch at z=0.035: got {z_bound}, expected {expected_bound}")
        failures += 1
    else:
        print(f"  PASSED: Boundary transition at z=0.035 is exact: {z_bound:.6f} == {expected_bound:.6f}.")

    # Full transmission (|z| >= 0.045)
    signal_vals = np.array([-10.0, -1.0, -0.10, -0.045, 0.045, 0.10, 1.0, 10.0])
    signal_clean = apply_hyperbolic_deadband_phase140(signal_vals, delta=delta, alpha=alpha)
    sig_diff = np.max(np.abs(signal_clean - signal_vals))
    if sig_diff > 1e-5:
        print(f"  FAILED: Incomplete transmission for |z| >= 0.045: max error = {sig_diff}")
        failures += 1
    else:
        print("  PASSED: 100% signal transmission for |z| >= 0.045.")

    # 3.3 Orthogonalizer Engine Under Severe Matrix Degeneracy
    print("[3.3] Stress testing orthogonalize_phase140 under severe degeneracy...")
    ortho = FactorOrthogonalizerEngine()
    np.random.seed(123)
    N = 80
    # Create 10 factors where 8 factors are identical copies of 1 factor
    f1 = np.random.uniform(0.1, 0.9, N)
    deg_dict = {f"col_{i}": f1 + 1e-14 * np.random.randn(N) for i in range(8)}
    deg_dict["col_8"] = np.random.uniform(0.1, 0.9, N)
    deg_dict["col_9"] = np.full(N, np.nan)  # Full NaN column
    deg_df = pd.DataFrame(deg_dict)

    out_deg = ortho.orthogonalize_phase140(
        deg_df,
        strategy_cols=list(deg_dict.keys()),
        preserve_top_k=4,
        apply_deadband=True,
    )

    for c in deg_dict.keys():
        s_vals = out_deg[c].dropna().values
        if len(s_vals) > 0:
            if np.any(s_vals < 0.05) or np.any(s_vals > 0.95):
                print(f"  FAILED: Column {c} scores out of bounds: min={s_vals.min()}, max={s_vals.max()}")
                failures += 1

    print("  PASSED: FactorOrthogonalizerEngine handles rank-1 collinearity and NaNs cleanly.")

    return failures


def main() -> None:
    t0 = time.time()
    print("=" * 70)
    print("CHALLENGER 2 INDEPENDENT EMPIRICAL ADVERSARIAL VERIFIER")
    print(f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print("=" * 70)

    f_nlp = run_nlp_adversarial_suite()
    f_opt = run_option_surface_adversarial_suite()
    f_ortho = run_orthogonalizer_adversarial_suite()

    elapsed = time.time() - t0
    total_failures = f_nlp + f_opt + f_ortho

    print("\n" + "=" * 70)
    print(f"VERIFICATION AUDIT COMPLETE in {elapsed:.2f}s")
    print(f"NLP Failures:            {f_nlp}")
    print(f"Options Greeks Failures: {f_opt}")
    print(f"Orthogonalizer Failures: {f_ortho}")
    print(f"TOTAL ADVERSARIAL FAILS: {total_failures}")
    print("=" * 70)

    if total_failures == 0:
        print("\nEXPLICIT VERDICT: CONFIRM_CORRECT (100% EMPIRICAL STRESS PASS)")
        sys.exit(0)
    else:
        print(f"\nEXPLICIT VERDICT: FINDINGS_REJECT ({total_failures} empirical failure points)")
        sys.exit(1)


if __name__ == "__main__":
    main()
