import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.ai.factor_suppression import RegimeFactorSuppressionEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine

def run_empirical_stress_tests():
    print("=== EMPIRICAL STRESS TEST SUITE FOR MILESTONE 1 ===")
    results = {}

    # Test 1: Ledoit-Wolf Shrinkage & Condition Number under Extreme Collinearity
    print("\n--- Test 1: Ledoit-Wolf Shrinkage & Matrix Condition Bounds ---")
    try:
        ortho_engine = FactorOrthogonalizerEngine(shrinkage_alpha=0.01, ridge_epsilon=1e-6)
        # Create 100 samples x 18 strategies with extreme multi-collinearity
        np.random.seed(42)
        base_signal = np.random.uniform(0.1, 0.9, 100)
        # Duplicate signal with tiny noise (collinearity > 0.999999)
        X_data = {f"strat_{i}": base_signal + np.random.normal(0, 1e-7, 100) for i in range(18)}
        df_collinear = pd.DataFrame(X_data)
        cols = list(df_collinear.columns)

        # Calculate raw covariance matrix condition number
        X_raw = df_collinear.to_numpy()
        means = np.mean(X_raw, axis=0)
        stds = np.std(X_raw, axis=0)
        X_bar = (X_raw - means) / stds
        C_raw = np.dot(X_bar.T, X_bar) / 99.0
        eig_raw = np.linalg.eigvalsh(C_raw)
        cond_raw = eig_raw[-1] / max(eig_raw[0], 1e-15)

        # Compute shrunk correlation matrix condition number
        C_shrunk = (1.0 - 0.01) * C_raw + 0.01 * np.eye(18)
        eig_shrunk = np.linalg.eigvalsh(C_shrunk)
        cond_shrunk = eig_shrunk[-1] / eig_shrunk[0]

        df_ortho = ortho_engine.orthogonalize(df_collinear, cols)

        pass_cond = cond_shrunk <= 1000.0 and not df_ortho.isna().any().any()
        pass_bounds = (df_ortho.min().min() >= 0.0) and (df_ortho.max().max() <= 1.0)

        print(f"Raw Matrix Condition Number: {cond_raw:.2e}")
        print(f"Shrunk Matrix Condition Number: {cond_shrunk:.2f} (Bound <= 1000: {cond_shrunk <= 1000.0})")
        print(f"Orthogonalized output shape: {df_ortho.shape}, bounds [0, 1]: {pass_bounds}")

        results["Test 1: Matrix Condition & Bounds"] = "PASS" if (pass_cond and pass_bounds) else "FAIL"
    except Exception as e:
        print(f"Test 1 FAILED with exception: {e}")
        results["Test 1: Matrix Condition & Bounds"] = f"FAIL ({e})"

    # Test 2: Factor Suppression Parameter Mapping across 6 Regimes + CRISIS/HIGH_VOL
    print("\n--- Test 2: Factor Suppression Mappings & Penalties across 6 Regimes + Aliases ---")
    try:
        supp_engine = RegimeFactorSuppressionEngine()
        regimes_to_check = [
            'BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS_LOW_VOL',
            'SIDEWAYS_HIGH_VOL', 'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
            'CRISIS', 'HIGH_VOL'
        ]

        all_params_valid = True
        for reg in regimes_to_check:
            theta, lam = supp_engine._get_regime_params(reg)
            clusters = supp_engine._get_high_risk_clusters(reg)
            print(f"Regime '{reg}': theta={theta:.2f}, lambda={lam:.2f}, High-Risk Clusters={clusters}")
            if reg == 'CRISIS' and (theta != 0.50 or lam != 2.00 or 'FLOW_MICRO' not in clusters):
                all_params_valid = False
            elif reg == 'HIGH_VOL' and (theta != 0.55 or lam != 1.50 or 'FLOW_MICRO' not in clusters):
                all_params_valid = False

        # Test penalty calculation with 100% correlated momentum strategies
        strats = ['surge', 'vcp_ml', 'sector_rotation', 'arm_factor', 'rim_valuation']
        corr_matrix = pd.DataFrame(np.ones((5, 5)), index=strats, columns=strats)
        penalties_crisis = supp_engine.compute_penalties(corr_matrix, 'CRISIS', theta=0.50, lambda_penalty=2.0)

        # Momentum strategies should receive heavy dampening in CRISIS
        pass_crisis_dampening = penalties_crisis['surge'] < 0.5

        results["Test 2: Factor Suppression Mappings"] = "PASS" if (all_params_valid and pass_crisis_dampening) else "FAIL"
    except Exception as e:
        print(f"Test 2 FAILED with exception: {e}")
        results["Test 2: Factor Suppression Mappings"] = f"FAIL ({e})"

    # Test 3: Calibration Class-Balance Protection under Zero-Variance Targets
    print("\n--- Test 3: Calibrator Zero-Variance & Class Balance Protection ---")
    try:
        ensemble = EnsembleScoringEngine()
        raw_scores = np.linspace(0.1, 0.9, 100)
        zero_labels = np.zeros(100)  # All 0 target labels (single class)

        ensemble.fit_calibrators({'regression': raw_scores}, zero_labels)
        has_cal = 'regression' in ensemble._calibrators

        calibrated_scores = ensemble.calibrate_scores('regression', raw_scores)
        preserved_scores = np.allclose(calibrated_scores, raw_scores)

        print(f"Calibrator fitted for single-class target? {has_cal} (Expected: False)")
        print(f"Raw scores preserved untouched? {preserved_scores} (Expected: True)")

        results["Test 3: Calibrator Class-Balance Protection"] = "PASS" if (not has_cal and preserved_scores) else "FAIL"
    except Exception as e:
        print(f"Test 3 FAILED with exception: {e}")
        results["Test 3: Calibrator Class-Balance Protection"] = f"FAIL ({e})"

    # Test 4: Dynamic Weight Transition Acceleration on Regime Shift
    print("\n--- Test 4: EMA Weight Smoothing Regime Shift Reset ---")
    try:
        ensemble = EnsembleScoringEngine(alpha_smoothing=0.2)
        strategies = list(ensemble.REGIME_2D_WEIGHTS['BULL_LOW_VOL'].keys())
        fake_sharpes = {s: 0.5 for s in strategies}

        # Call 1: BULL_LOW_VOL
        w1 = ensemble.compute_dynamic_weights_from_sharpe(fake_sharpes, regime='BULL_LOW_VOL')
        
        # Call 2: BEAR_HIGH_VOL (Regime shift from BULL_LOW_VOL -> BEAR_HIGH_VOL)
        w2 = ensemble.compute_dynamic_weights_from_sharpe(fake_sharpes, regime='BEAR_HIGH_VOL')

        # Check target weights for BEAR_HIGH_VOL without EMA lag
        base_bear = ensemble.get_base_weights('BEAR_HIGH_VOL')
        scores_bear = {k: v * np.exp(1.0 * 0.5) for k, v in base_bear.items()}
        tot_bear = sum(scores_bear.values())
        target_bear = {k: v / tot_bear for k, v in scores_bear.items()}

        max_diff = max(abs(w2[s] - target_bear[s]) for s in strategies)
        pass_ema_reset = max_diff < 1e-5

        print(f"Regime transition detected? _prev_regime = {ensemble._prev_regime}")
        print(f"Max weight difference from un-lagged target BEAR_HIGH_VOL: {max_diff:.2e} (Expected < 1e-5)")

        results["Test 4: EMA Regime Shift Acceleration"] = "PASS" if pass_ema_reset else "FAIL"
    except Exception as e:
        print(f"Test 4 FAILED with exception: {e}")
        results["Test 4: EMA Regime Shift Acceleration"] = f"FAIL ({e})"

    # Test 5: Numerical Stability & Cold-Start Seed Weights across 6 Regimes
    print("\n--- Test 5: Convergence & Seed Weights across 6 Regimes ---")
    try:
        regimes_6 = ['BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BEAR_LOW_VOL', 'BEAR_HIGH_VOL']
        empty_sharpes = {s: 0.0 for s in ensemble.REGIME_2D_WEIGHTS['BULL_LOW_VOL'].keys()}
        all_regimes_pass = True

        for r in regimes_6:
            eng = EnsembleScoringEngine()
            w = eng.compute_dynamic_weights_from_sharpe(empty_sharpes, regime=r)
            if len(w) != 18 or not np.isclose(sum(w.values()), 1.0):
                all_regimes_pass = False
            print(f"Regime '{r}': total weight sum = {sum(w.values()):.6f}, TOP strategy = {max(w, key=w.get)} ({w[max(w, key=w.get)]:.4f})")

        results["Test 5: 6-Regime Convergence & Seeds"] = "PASS" if all_regimes_pass else "FAIL"
    except Exception as e:
        print(f"Test 5 FAILED with exception: {e}")
        results["Test 5: 6-Regime Convergence & Seeds"] = f"FAIL ({e})"

    # Summary
    print("\n=================== SUMMARY ===================")
    all_pass = True
    for test_name, status in results.items():
        print(f"{test_name}: {status}")
        if status != "PASS":
            all_pass = False

    if all_pass:
        print("\nALL EMPIRICAL STRESS TESTS PASSED SUCCESSFULLY!")
    else:
        print("\nSOME EMPIRICAL STRESS TESTS FAILED!")

if __name__ == '__main__':
    run_empirical_stress_tests()
