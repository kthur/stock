"""
Independent Stress-Testing Script for Forensic Audit of Milestone 1.
Author: Forensic Auditor M1-1
Date: 2026-09-04
"""

import sys
import os
sys.path.insert(0, 'trading_system')
sys.path.insert(0, '.')
import numpy as np
import pandas as pd

from src.ai.factor_suppression import RegimeFactorSuppressionEngine
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine


def run_audit_stress_tests():
    print("=== STARTING FORENSIC AUDITOR INDEPENDENT STRESS TESTS ===")

    # -------------------------------------------------------------
    # 1. Stress Test: Calibrated Cutoff Formula theta(R, N)
    # -------------------------------------------------------------
    print("[TEST 1] Stress-testing theta(R, N) bounds and edge cases...")
    engine_supp = RegimeFactorSuppressionEngine()

    # Extreme edge cases
    for n in [None, -5, 0, 1, 2, 3]:
        val = engine_supp.calibrate_cutoff(0.60, n)
        assert val == 0.60, f"Failed for N={n}: got {val}"

    # Verify clamping at 0.35 and 0.85
    assert engine_supp.calibrate_cutoff(0.20, 10000) == 0.35
    assert engine_supp.calibrate_cutoff(0.80, 4) == 0.85
    assert engine_supp.calibrate_cutoff(0.95, 1000) == 0.85

    # Asymptotics: as N -> inf, theta -> theta_0
    theta_inf = engine_supp.calibrate_cutoff(0.60, 100_000_000)
    assert abs(theta_inf - 0.60) < 5e-4, f"Asymptotic theta failed: {theta_inf}"

    print(" -> PASS: theta(R, N) correctly calibrated and bounded.")

    # -------------------------------------------------------------
    # 2. Stress Test: Dual-Consensus Spectral Whitening
    # -------------------------------------------------------------
    print("[TEST 2] Stress-testing Dual-Consensus Whitening under severe rank deficiency...")
    # N=2 assets, K=37 strategies (extreme rank deficiency: K >> N)
    np.random.seed(1234)
    N, K = 2, 37
    cols = [f's_{i}' for i in range(K)]
    data = np.random.uniform(0.1, 0.9, (N, K))
    df = pd.DataFrame(data, columns=cols)
    df['symbol'] = ['A', 'B']

    engine_ortho = FactorOrthogonalizerEngine(preserve_top_k=2)
    res_ortho = engine_ortho.orthogonalize(df, cols, preserve_top_k=2)

    ortho_vals = res_ortho[cols].values
    assert not np.isnan(ortho_vals).any(), "NaN found in rank-deficient orthogonalization!"
    assert not np.isinf(ortho_vals).any(), "Inf found in rank-deficient orthogonalization!"
    assert np.all(ortho_vals >= 0.0) and np.all(ortho_vals <= 1.0), "Out of bounds [0, 1]!"

    # Perfect collinearity test: 37 columns that are identical
    df_identical = pd.DataFrame(np.tile(np.linspace(0.2, 0.8, 20)[:, None], (1, K)), columns=cols)
    df_identical['symbol'] = [f'S_{i}' for i in range(20)]
    res_identical = engine_ortho.orthogonalize(df_identical, cols, preserve_top_k=2)
    assert not np.isnan(res_identical[cols].values).any(), "NaN found on identical columns!"

    print(" -> PASS: Dual-Consensus Whitening survives rank deficiency and collinear singularities.")

    # -------------------------------------------------------------
    # 3. Stress Test: Richards / Bessembinder Convex Power-Law Monotonicity & Symmetry
    # -------------------------------------------------------------
    print("[TEST 3] Stress-testing Richards/Bessembinder Monotonicity & Symmetry across 100,000 points...")
    fine_grid = np.linspace(0.0, 1.0, 100_001)
    scaled = EnsembleScoringEngine.apply_bessembinder_convex_power_law(fine_grid, symmetric=True)

    # Monotonicity check
    diffs = np.diff(scaled)
    assert np.all(diffs >= 0), "Monotonicity violation detected!"

    # Anti-symmetry check around 0.50: scaled(0.5 - d) + scaled(0.5 + d) == 1.0000000
    mid = len(fine_grid) // 2
    left_half = scaled[:mid]
    right_half = scaled[mid+1:]
    reflected_sum = left_half + right_half[::-1]
    max_sym_err = np.max(np.abs(reflected_sum - 1.0))
    assert max_sym_err < 1e-12, f"Symmetry violation: max error {max_sym_err}"

    # Neutral invariance
    assert abs(scaled[mid] - 0.50) < 1e-14, f"Neutral invariance failed: {scaled[mid]}"

    # Bounds check
    assert np.min(scaled) >= 0.0 and np.max(scaled) <= 1.0, "Bounds [0, 1] exceeded!"

    print(" -> PASS: Strict anti-symmetry, rank preservation (rho_s = 1.0), and [0, 1] bounds confirmed.")

    # -------------------------------------------------------------
    # 4. Stress Test: Bilinear Cross-Pillar Synergy Kernel
    # -------------------------------------------------------------
    print("[TEST 4] Stress-testing Bilinear Cross-Pillar Synergy continuity & bounds...")
    # Generate 1000 random asset scores
    np.random.seed(4321)
    N_test = 1000
    all_pillar_cols = [
        'rim_score', 'valueup_catalyst_score', 'accruals_quality_score', 'arm_score',
        'surge_score', 'vcp_ml_score', 'trend_efficiency_score', 'sector_score',
        'range_expansion_score', 'mq_score', 'll_score', 'vcp_rule_score',
        'order_flow_score', 'inst_foreign_sector_score', 'darkpool_score',
        'microstructure_score', 'overnight_gap_score', 'stat_arb_score',
        'event_score', 'sentiment_score', 'short_squeeze_score', 'gamma_squeeze_score',
        'supply_chain_score', 'supply_chain_gnn_score', 'cross_asset_spillover_score',
        'dual_correction_score', 'index_rebalance_score', 'insider_buying_score',
        'earnings_tone_drift_score'
    ]
    df_random = pd.DataFrame(np.random.uniform(0.0, 1.0, (N_test, len(all_pillar_cols))), columns=all_pillar_cols)

    for regime in ['BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'BEAR_HIGH_VOL', 'CRISIS', 'UNKNOWN_REGIME']:
        mult = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_random, regime=regime)
        assert np.all(mult >= 1.000), f"Synergy below 1.0: min={mult.min()}"
        assert np.all(mult <= 1.1000001), f"Synergy exceeded 1.10: max={mult.max()}"
        assert not np.isnan(mult).any(), f"NaN in synergy multiplier for regime {regime}"

    # Check continuity at 0.50 boundary: epsilon perturbations
    df_base = pd.DataFrame({col: [0.50] * 10 for col in all_pillar_cols})
    df_pert = pd.DataFrame({col: [0.50 + 1e-4] * 10 for col in all_pillar_cols})
    mult_base = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_base).iloc[0]
    mult_pert = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_pert).iloc[0]
    assert abs(mult_pert - mult_base) < 1e-4, f"Discontinuity at 0.50: diff = {abs(mult_pert - mult_base)}"

    print(" -> PASS: Synergy kernel continuous, regime-adaptive, and strictly within [1.0, 1.10].")

    # -------------------------------------------------------------
    # 5. Stress Test: 2D Regime Half-Life Scaling across all strategies
    # -------------------------------------------------------------
    print("[TEST 5] Stress-testing 2D Regime Half-Lives across all 37 strategies...")
    regimes = ['BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'CRISIS']
    for reg in regimes:
        hl_map = EnsembleScoringEngine.get_regime_adaptive_half_lives(reg)
        for strat, tau in hl_map.items():
            assert tau >= 0.10, f"Half-life too small ({tau}) for {strat} in {reg}"
            assert np.isfinite(tau), f"Non-finite half-life for {strat} in {reg}"

    # Monotonicity of fast strategies from Bull to Crisis
    hl_bull = EnsembleScoringEngine.get_regime_adaptive_half_lives('BULL_LOW_VOL')
    hl_crisis = EnsembleScoringEngine.get_regime_adaptive_half_lives('CRISIS')
    assert hl_bull['microstructure'] > hl_crisis['microstructure']
    assert hl_bull['order_flow'] > hl_crisis['order_flow']
    assert hl_bull['darkpool'] > hl_crisis['darkpool']
    assert hl_bull['overnight_gap'] > hl_crisis['overnight_gap']

    print(" -> PASS: Half-life mapping is strictly positive, finite, and regime-consistent.")

    print("\n=== ALL FORENSIC AUDITOR ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY! ===")


if __name__ == '__main__':
    run_audit_stress_tests()
