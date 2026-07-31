"""
Empirical Stress Test Harness for Milestone 3 (CPCVStressTester & Historical Stress Testing).
Tests 5 key challenge dimensions:
1. Zero volatility return series.
2. NaN and Inf values injected into return series/DataFrame.
3. Extremely short input series (< 6 bars).
4. Large matrices (100 strategy return columns x 5000 bars).
5. Zero overlap verification across all 15 splits for N=6, k=2.
"""

import os
import sys
import time
import traceback

# Ensure root directory and trading_system directory are on sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ts_dir = os.path.join(root_dir, "trading_system")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if ts_dir not in sys.path:
    sys.path.insert(0, ts_dir)

import numpy as np
import pandas as pd
from src.ai.cpcv_stress_tester import (
    CPCVStressTester,
    StressTestReport,
    run_historical_stress_test,
)


def run_all_stress_tests():
    results = {}
    print("=" * 70)
    print("STARTING EMPIRICAL STRESS TEST SUITE FOR MILESTONE 3")
    print("=" * 70)

    # -------------------------------------------------------------
    # Test 1: Zero Volatility Return Series
    # -------------------------------------------------------------
    print("\n--- [Test 1] Zero Volatility Return Series ---")
    try:
        tester = CPCVStressTester(n_splits=6, n_test_splits=2)
        zero_matrix = np.zeros((300, 5))
        zero_df = pd.DataFrame(zero_matrix, columns=[f"strat_{i}" for i in range(5)])
        
        pbo_res = tester.compute_pbo(zero_df)
        print(f"PBO on Zero Matrix: pbo={pbo_res['pbo']}, is_overfitted={pbo_res['is_overfitted']}, n_combos={pbo_res['n_combinations']}")
        
        zero_series = pd.Series(np.zeros(300))
        stress_res = run_historical_stress_test(zero_series, scenario="2008_CRISIS")
        print(f"Stress Test on Zero Series: mdd={stress_res.mdd}, sharpe={stress_res.stress_sharpe}, pass={stress_res.pass_flag}")
        
        results["test_1_zero_volatility"] = {
            "status": "PASS",
            "pbo": pbo_res["pbo"],
            "stress_mdd": stress_res.mdd,
            "stress_sharpe": stress_res.stress_sharpe,
        }
    except Exception as e:
        print(f"FAILED Test 1: {e}")
        traceback.print_exc()
        results["test_1_zero_volatility"] = {"status": "FAIL", "error": str(e)}

    # -------------------------------------------------------------
    # Test 2: NaN and Inf Injections
    # -------------------------------------------------------------
    print("\n--- [Test 2] NaN and Inf Values Injected ---")
    try:
        tester = CPCVStressTester(n_splits=6, n_test_splits=2)
        
        # Matrix with NaN and Inf
        nan_inf_matrix = np.random.randn(300, 4) * 0.01
        nan_inf_matrix[10, 0] = np.nan
        nan_inf_matrix[20, 1] = np.inf
        nan_inf_matrix[30, 2] = -np.inf
        nan_inf_df = pd.DataFrame(nan_inf_matrix, columns=["col_normal", "col_nan", "col_posinf", "col_neginf"])
        
        print("Testing compute_pbo on DataFrame with NaN/Inf...")
        pbo_res = tester.compute_pbo(nan_inf_df)
        print(f"PBO with NaN/Inf DF: pbo={pbo_res['pbo']}, logits_len={len(pbo_res['logits'])}")
        print(f"PBO Logits sample: {pbo_res['logits'][:3]}")

        print("Testing compute_pbo on raw ndarray with NaN/Inf...")
        pbo_arr_res = tester.compute_pbo(nan_inf_matrix)
        print(f"PBO with NaN/Inf ndarray: pbo={pbo_arr_res['pbo']}")
        
        print("Testing run_historical_stress_test on Series with NaN/Inf...")
        s_nan = pd.Series([0.01, np.nan, -0.02, np.nan, 0.01] * 50)
        s_inf = pd.Series([0.01, np.inf, -0.02, -np.inf, 0.01] * 50)
        s_all_nan = pd.Series([np.nan] * 100)
        
        st_nan = run_historical_stress_test(s_nan, scenario="2008_CRISIS")
        st_inf = run_historical_stress_test(s_inf, scenario="2008_CRISIS")
        st_all_nan = run_historical_stress_test(s_all_nan, scenario="2008_CRISIS")
        
        print(f"Stress result s_nan: mdd={st_nan.mdd:.4f}, sharpe={st_nan.stress_sharpe:.4f}")
        print(f"Stress result s_inf: mdd={st_inf.mdd:.4f}, sharpe={st_inf.stress_sharpe:.4f}")
        print(f"Stress result s_all_nan: mdd={st_all_nan.mdd:.4f}, sharpe={st_all_nan.stress_sharpe:.4f}")
        
        results["test_2_nan_inf"] = {
            "status": "PASS",
            "pbo_df": pbo_res["pbo"],
            "st_nan_mdd": st_nan.mdd,
            "st_inf_mdd": st_inf.mdd,
            "st_all_nan_mdd": st_all_nan.mdd,
        }
    except Exception as e:
        print(f"FAILED Test 2: {e}")
        traceback.print_exc()
        results["test_2_nan_inf"] = {"status": "FAIL", "error": str(e)}

    # -------------------------------------------------------------
    # Test 3: Extremely Short Input Series (< 6 bars)
    # -------------------------------------------------------------
    print("\n--- [Test 3] Extremely Short Input Series ---")
    short_results = {}
    tester = CPCVStressTester(n_splits=6, n_test_splits=2)
    for n in range(0, 6):
        print(f"\n--- Testing length N = {n} ---")
        # 1. PBO
        mat = np.random.randn(n, 3) if n > 0 else np.empty((0, 3))
        try:
            res_pbo = tester.compute_pbo(mat)
            print(f"PBO (N={n}): pbo={res_pbo['pbo']}, combos={res_pbo['n_combinations']}")
            pbo_status = f"OK (pbo={res_pbo['pbo']})"
        except Exception as e:
            print(f"PBO (N={n}) EXCEPTION: {type(e).__name__}: {e}")
            pbo_status = f"EXCEPTION: {type(e).__name__}: {e}"

        # 2. Historical Stress Test
        s_short = pd.Series(np.random.randn(n)) if n > 0 else pd.Series([], dtype=float)
        try:
            res_st = run_historical_stress_test(s_short, scenario="2008_CRISIS")
            print(f"Stress Test (N={n}): mdd={res_st.mdd:.4f}, sharpe={res_st.stress_sharpe}")
            st_status = f"OK (sharpe={res_st.stress_sharpe})"
        except Exception as e:
            print(f"Stress Test (N={n}) EXCEPTION: {type(e).__name__}: {e}")
            st_status = f"EXCEPTION: {type(e).__name__}: {e}"
            
        short_results[f"N_{n}"] = {"pbo": pbo_status, "stress": st_status}

    results["test_3_short_series"] = short_results

    # -------------------------------------------------------------
    # Test 4: Large Matrices (100 columns x 5000 bars)
    # -------------------------------------------------------------
    print("\n--- [Test 4] Large Matrix Performance & Correctness (100 x 5000) ---")
    try:
        t0 = time.time()
        large_mat = np.random.randn(5000, 100) * 0.01
        large_df = pd.DataFrame(large_mat, columns=[f"strat_{i}" for i in range(100)])
        t_gen = time.time() - t0
        
        t0 = time.time()
        tester = CPCVStressTester(n_splits=6, n_test_splits=2)
        pbo_large = tester.compute_pbo(large_df)
        t_pbo = time.time() - t0
        
        t0 = time.time()
        st_large = run_historical_stress_test(large_df, scenario="2008_CRISIS")
        t_st = time.time() - t0
        
        print(f"Generation time: {t_gen:.4f}s")
        print(f"PBO time (100x5000): {t_pbo:.4f}s, pbo={pbo_large['pbo']:.4f}, n_combos={pbo_large['n_combinations']}")
        print(f"Stress Test time (100x5000): {t_st:.4f}s, total reports={len(st_large)}")
        
        results["test_4_large_matrix"] = {
            "status": "PASS",
            "pbo_time_sec": t_pbo,
            "stress_time_sec": t_st,
            "pbo": pbo_large["pbo"],
            "n_reports": len(st_large),
        }
    except Exception as e:
        print(f"FAILED Test 4: {e}")
        traceback.print_exc()
        results["test_4_large_matrix"] = {"status": "FAIL", "error": str(e)}

    # -------------------------------------------------------------
    # Test 5: Zero Overlap Assertion Across All 15 Splits (N=6, k=2)
    # -------------------------------------------------------------
    print("\n--- [Test 5] Zero Overlap Verification Across All 15 Splits ---")
    try:
        n_samples = 600
        n_splits = 6
        n_test_splits = 2
        purge = 5
        embargo = 10
        
        tester = CPCVStressTester(
            n_splits=n_splits,
            n_test_splits=n_test_splits,
            purge_window=purge,
            embargo_window=embargo,
        )
        
        data = np.random.randn(n_samples, 5)
        folds = tester.generate_purged_folds(data)
        
        print(f"Generated {len(folds)} folds.")
        assert len(folds) == 15, f"Expected 15 folds, got {len(folds)}"
        
        block_bounds = np.linspace(0, n_samples, n_splits + 1, dtype=int)
        
        overlap_failures = []
        for fold_idx, (train_idx, test_idx, test_blocks) in enumerate(folds):
            train_set = set(train_idx)
            test_set = set(test_idx)
            
            # Compute explicit purge and embargo sets
            purge_set = set()
            embargo_set = set()
            
            for b in test_blocks:
                start_b = block_bounds[b]
                end_b = block_bounds[b + 1]
                
                # Purge indices before start_b
                p_indices = set(range(max(0, start_b - purge), start_b))
                purge_set.update(p_indices)
                
                # Embargo indices after end_b
                e_indices = set(range(end_b, min(n_samples, end_b + embargo)))
                embargo_set.update(e_indices)
            
            # Check 1: Train ∩ Test == ∅
            train_test_overlap = train_set.intersection(test_set)
            if train_test_overlap:
                overlap_failures.append(f"Fold {fold_idx}: Train ∩ Test overlap! count={len(train_test_overlap)}")
                
            # Check 2: Train ∩ Purge == ∅
            train_purge_overlap = train_set.intersection(purge_set)
            if train_purge_overlap:
                overlap_failures.append(f"Fold {fold_idx}: Train ∩ Purge overlap! count={len(train_purge_overlap)}")

            # Check 3: Train ∩ Embargo == ∅
            train_embargo_overlap = train_set.intersection(embargo_set)
            if train_embargo_overlap:
                overlap_failures.append(f"Fold {fold_idx}: Train ∩ Embargo overlap! count={len(train_embargo_overlap)}")

            # Check 4: Exact partition completeness
            all_indices = set(range(n_samples))
            excluded_set = test_set.union(purge_set).union(embargo_set)
            expected_train = all_indices - excluded_set
            
            if train_set != expected_train:
                overlap_failures.append(f"Fold {fold_idx}: Train set mismatch with expected_train! diff_len={len(train_set ^ expected_train)}")
                
        if overlap_failures:
            print("FAILED Test 5 Overlap Checks:")
            for fail in overlap_failures:
                print(f"  - {fail}")
            results["test_5_zero_overlap"] = {"status": "FAIL", "failures": overlap_failures}
        else:
            print("ALL 15 splits passed zero overlap and exact purging/embargo partitioning!")
            results["test_5_zero_overlap"] = {"status": "PASS", "n_splits_verified": len(folds)}
            
    except Exception as e:
        print(f"FAILED Test 5: {e}")
        traceback.print_exc()
        results["test_5_zero_overlap"] = {"status": "FAIL", "error": str(e)}

    print("\n" + "=" * 70)
    print("STRESS TEST SUMMARY RESULTS")
    print("=" * 70)
    for k, v in results.items():
        print(f"{k}: {v}")
    
    return results


if __name__ == "__main__":
    run_all_stress_tests()
