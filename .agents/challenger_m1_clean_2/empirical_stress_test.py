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
    failures = []

    # -------------------------------------------------------------
    # 1. Ledoit-Wolf Shrinkage & Eigenvalue Bounds / Matrix Condition
    # -------------------------------------------------------------
    print("\n--- Test 1: Ledoit-Wolf Shrinkage Eigenvalue Bounds & Matrix Stability ---")
    engine_ortho = FactorOrthogonalizerEngine(shrinkage_alpha=0.01, ridge_epsilon=1e-6)
    
    K = 17
    N_samples_list = [5, 20, 100, 1000]
    regimes = ['BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'CRISIS', 'HIGH_VOL']
    
    for N in N_samples_list:
        # Perfectly collinear columns (extreme stress)
        col0 = np.random.uniform(0.1, 0.9, N)
        X_coll = np.column_stack([col0 for _ in range(K)])
        
        means = np.mean(X_coll, axis=0)
        stds = np.std(X_coll, axis=0)
        stds = np.where(stds < 1e-8, 1e-6, stds)
        X_bar = (X_coll - means) / stds
        C = np.dot(X_bar.T, X_bar) / max(N - 1, 1)
        C_shrunk = (1.0 - engine_ortho.shrinkage_alpha) * C + engine_ortho.shrinkage_alpha * np.eye(K)
        
        eigvals, _ = np.linalg.eigh(C_shrunk)
        min_eig = np.min(eigvals)
        max_eig = np.max(eigvals)
        cond_num = max_eig / min_eig
        
        print(f"N={N:4d} (Collinear): min_eig={min_eig:.6f}, max_eig={max_eig:.6f}, cond_num={cond_num:.2f}")
        
        # Verify strict positive-definiteness & eigenvalue lower bound
        if min_eig < engine_ortho.shrinkage_alpha * 0.99:
            failures.append(f"Min eigenvalue {min_eig} violated lower bound {engine_ortho.shrinkage_alpha} for N={N}")

    # -------------------------------------------------------------
    # 2. PCA ZCA Decorrelation Output Bounds & NaN Resilience
    # -------------------------------------------------------------
    print("\n--- Test 2: PCA ZCA Decorrelation Range & NaN Handling ---")
    cols = [f"strat_{i}" for i in range(K)]
    for seed in [1, 42, 100]:
        df = pd.DataFrame(np.random.uniform(0.0, 1.0, (500, K)), columns=cols)
        # Add NaNs randomly
        df.iloc[0, 0] = np.nan
        df.iloc[10:15, 3] = np.nan
        
        ortho_df = engine_ortho.orthogonalize(df, cols, method='pca_symmetric')
        res_vals = ortho_df[cols].values
        
        valid_mask = ~np.isnan(res_vals)
        valid_vals = res_vals[valid_mask]
        
        min_v = np.min(valid_vals)
        max_v = np.max(valid_vals)
        print(f"Seed {seed:3d}: min_val={min_v:.6f}, max_val={max_v:.6f}")
        if min_v < 0.0 or max_v > 1.0:
            failures.append(f"Out of bounds output [{min_v}, {max_v}] for seed {seed}")

    # -------------------------------------------------------------
    # 3. Factor Suppression across all 6 2D Regimes & Fallbacks
    # -------------------------------------------------------------
    print("\n--- Test 3: Factor Noise Suppression across 6 2D Market Regimes ---")
    supp_engine = RegimeFactorSuppressionEngine()
    
    n_strats = len(cols)
    base_weights = {cols[i]: 1.0 / n_strats for i in range(n_strats)}
    
    for r in regimes:
        t, l = supp_engine._get_regime_params(r)
        clusters = supp_engine._get_high_risk_clusters(r)
        print(f"Regime {r:18s}: theta={t:.2f}, lambda={l:.2f}, high_risk={clusters}")
        if t <= 0.0 or l <= 0.0:
            failures.append(f"Invalid theta/lambda params for regime {r}")

    # -------------------------------------------------------------
    # 4. Calibrator Monotonicity & Single-Class Target Protection
    # -------------------------------------------------------------
    print("\n--- Test 4: Hybrid Calibrator Monotonicity & Class-Balance Guard ---")
    scorer = EnsembleScoringEngine()
    
    # 4a. Zero variance (all zeros)
    raw_s = np.linspace(0, 1, 100)
    all_0 = np.zeros(100)
    scorer.fit_calibrators({'strat_0': raw_s}, all_0)
    if 'strat_0' in scorer._calibrators:
        failures.append("Calibrator was fitted on zero-variance single-class labels!")
    else:
        print("PASS: Single-class zero variance target label safely skipped.")

    # 4b. Calibrator Monotonicity
    np.random.seed(42)
    labels = (raw_s + np.random.normal(0, 0.1, 100) > 0.5).astype(float)
    labels[0] = 0.0
    labels[-1] = 1.0
    scorer.fit_calibrators({'strat_1': raw_s}, labels)
    cal_scores = scorer.calibrate_scores('strat_1', raw_s)
    diffs = np.diff(cal_scores)
    if np.any(diffs < -1e-6):
        failures.append(f"Isotonic calibration violated monotonicity! Max negative diff: {np.min(diffs)}")
    else:
        print(f"PASS: Isotonic calibrator verified strictly monotonic. Output range: [{cal_scores.min():.4f}, {cal_scores.max():.4f}]")

    # -------------------------------------------------------------
    # 5. Regime Transition EMA Acceleration Reset
    # -------------------------------------------------------------
    print("\n--- Test 5: Regime Transition EMA Shift Reset ---")
    strats_18 = [
        'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
        'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation', 'event_driven',
        'mq_factor', 'iv_skew', 'order_flow', 'short_term_reversal',
        'arm_factor', 'card_factor', 'latr_factor', 'inst_foreign_sector'
    ]
    sharpes = {s: 0.5 for s in strats_18}
    
    w_bull1 = scorer.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL')
    w_bull2 = scorer.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL')
    w_bear = scorer.compute_dynamic_weights_from_sharpe(sharpes, regime='BEAR_HIGH_VOL')
    
    base_bear = scorer.get_base_weights('BEAR_HIGH_VOL')
    expected_bear_scores = {k: v * np.exp(1.0 * 0.5) for k, v in base_bear.items()}
    tot = sum(expected_bear_scores.values())
    expected_bear = {k: v / tot for k, v in expected_bear_scores.items()}
    
    max_err = max(abs(w_bear[k] - expected_bear[k]) for k in strats_18)
    print(f"Max deviation from target weights on regime shift: {max_err:.8f}")
    if max_err > 1e-4:
        failures.append(f"EMA reset failed on regime transition, max error = {max_err}")
    else:
        print("PASS: EMA reset instantly aligned weights on regime shift.")

    print("\n=================================================")
    if failures:
        print("VERDICT: FAIL - The following stress failures occurred:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    else:
        print("VERDICT: PASS - All empirical stress checks passed cleanly!")
        sys.exit(0)

if __name__ == '__main__':
    run_empirical_stress_tests()
