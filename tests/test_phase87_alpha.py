"""
tests/test_phase87_alpha.py

Unit test suite for Phase 87 Quantitative Alpha Enhancement (Features F405, F406):
- Feature F405: Asymmetric Pentacosiatetragonal (504th-Order) Hyperbolic Deadband
  (alpha_pos = 504.0, delta_noise = 0.035, noise suppression < 10^-504 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F405: 105th-Order Hyperconvex Rank Modulation
  (g_v87(r) = 0.50 + 3.34 * r * exp(gamma_top * r^105) with REGIME_GAMMA_TOP_V87,
   strictly monotonic non-decreasing, g(1.0) > 10^7).
- Feature F406: Borcherds-Moonshine Monster Whittaker Coupler v87
  (defaults to version=87, kappa=34.40, lambda=0.99999999999995, 186th-order chiral oper obstruction,
   98th-order defect invariant, harmony boost 6.75 when h > 0.65, output keys FERI_v87, feri_v87, f_out_87).
- Full alias trees for deadband, rank modulation, and coupler across classes and module level.
"""

import pytest
import math
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from trading_system.src.ai.factor_suppression import (
    apply_pentacosiatetragonal_hyperbolic_deadband,
    apply_pentacosiatetradihedral_hyperbolic_deadband,
    apply_quingentatetragonal_hyperbolic_deadband,
    apply_pentacentatetragonal_hyperbolic_deadband,
    apply_pentacosiatetra_hyperbolic_deadband,
    apply_pentacosiatetragonal_deadband,
    pentacosiatetragonal_deadband,
    pentacosiatetragonal_hyperbolic_deadband,
    compute_phase87_deadband,
    apply_phase87_deadband,
    phase87_deadband,
    apply_504th_order_hyperbolic_deadband,
    apply_504th_deadband,
    apply_504_deadband,
    apply_hyperbolic_deadband_v87,
    suppress_factor_noise_hyperbolic_v87,
    compute_phase87_hyperconvex_rank_modulation,
    compute_phase87_rank_warping,
    compute_phase87_rank_modulation,
    phase87_rank_modulation,
    phase87_hyperconvex_rank_modulation,
    apply_hyper_convex_rank_modulation_v87,
    REGIME_GAMMA_TOP_V87,
    get_regime_adaptive_gamma_top_v87,
    Phase87FactorSuppressionEngine,
    RegimeFactorSuppressionEngine,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase87Coupler,
    Phase87WhittakerDrinfeldCoupler,
    Phase87BorcherdsMoonshineCoupler,
    Phase87MonsterWhittakerCoupler,
    compute_phase87_coupling,
    Phase86Coupler,
    Phase85Coupler,
    Phase84Coupler,
    EnsembleScoringEngine,
)


class TestPhase87AlphaEnhancements:
    def test_feature_f406_coupler_properties_v87(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=34.40,
            lambda_monster=0.99999999999995,
            version=87,
        )
        assert coupler.kappa_monster_whit == 34.40
        assert coupler.lambda_monster == 0.99999999999995
        assert coupler.version == 87
        assert coupler.is_phase87 is True
        assert coupler.harmony_boost == 6.75

        p_df = pd.DataFrame({
            'val': [0.50, 0.45, 0.10],
            'mom': [0.50, 0.55, 0.90],
            'flow': [0.50, 0.50, 0.20],
            'cat': [0.50, 0.60, 0.80],
            'net': [0.50, 0.40, 0.05],
        })

        res = coupler(p_df)
        assert 'h_monster_whit' in res
        assert 'z_monster_whit' in res
        assert 'e_monster_whit' in res
        assert 'FERI_v87' in res
        assert 'feri_v87' in res
        assert 'f_out_87' in res
        assert 'FERI_v86' in res
        assert 'feri_v86' in res
        assert 'f_out_86' in res

        feri_87 = res['FERI_v87']
        assert len(feri_87) == len(p_df)
        assert np.all(np.isfinite(feri_87))

    def test_feature_f406_coupler_aliases(self):
        assert Phase87Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase87WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase87BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase87MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase86Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase85Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase84Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        p_df = pd.DataFrame({
            'val': [0.50, 0.45],
            'mom': [0.50, 0.55],
            'flow': [0.50, 0.50],
            'cat': [0.50, 0.60],
            'net': [0.50, 0.40],
        })
        res = compute_phase87_coupling(p_df)
        assert 'FERI_v87' in res

    def test_feature_f405_deadband_suppression(self):
        # Sub-threshold near-zero noise |z| <= 0.0003 suppressed below 10^-504 (float64 underflow < 1e-300 or 0.0)
        sub_noise = np.array([0.0001, 0.0002, 0.0003, -0.0001, -0.0002, -0.0003])
        denoised = apply_pentacosiatetragonal_hyperbolic_deadband(sub_noise, delta_noise=0.035)
        for val in denoised:
            assert abs(val) < 1e-300 or val == 0.0

        # Full retention for high-conviction signals |z| >= 0.150
        strong_sig = np.array([0.150, 0.20, 0.50, -0.150, -0.20, -0.50])
        denoised_strong = apply_pentacosiatetragonal_hyperbolic_deadband(strong_sig, delta_noise=0.035)
        for orig, d in zip(strong_sig, denoised_strong):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test across full spectrum
        grid = np.linspace(0.001, 1.0, 100)
        grid_out = apply_pentacosiatetragonal_hyperbolic_deadband(grid, delta_noise=0.035)
        rho, _ = spearmanr(grid, grid_out)
        assert math.isclose(rho, 1.0, rel_tol=1e-5)

    def test_feature_f405_deadband_aliases(self):
        arr = np.array([0.0002, 0.18, -0.0002, -0.18])
        ref = apply_pentacosiatetragonal_hyperbolic_deadband(arr)

        assert np.allclose(apply_pentacosiatetradihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quingentatetragonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacentatetragonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacosiatetra_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacosiatetragonal_deadband(arr), ref)
        assert np.allclose(pentacosiatetragonal_deadband(arr), ref)
        assert np.allclose(pentacosiatetragonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(compute_phase87_deadband(arr), ref)
        assert np.allclose(apply_phase87_deadband(arr), ref)
        assert np.allclose(phase87_deadband(arr), ref)
        assert np.allclose(apply_504th_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_504th_deadband(arr), ref)
        assert np.allclose(apply_504_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v87(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v87(arr), ref)
        assert np.allclose(Phase87FactorSuppressionEngine.apply_pentacosiatetragonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.apply_pentacosiatetragonal_hyperbolic_deadband(arr), ref)

    def test_feature_f405_rank_modulation(self):
        ranks = np.array([0.0, 0.5, 0.9, 1.0])
        mod = compute_phase87_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")
        assert len(mod) == len(ranks)
        assert np.all(np.diff(mod) > 0)
        assert mod[-1] > 1e7

    def test_feature_f405_rank_modulation_regimes(self):
        for regime, gamma in REGIME_GAMMA_TOP_V87.items():
            g = get_regime_adaptive_gamma_top_v87(regime)
            assert g == gamma
            assert g <= 23.50

    def test_feature_f405_rank_modulation_aliases(self):
        ranks = np.array([0.1, 0.8])
        ref = compute_phase87_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase87_rank_warping(ranks), ref)
        assert np.allclose(compute_phase87_rank_modulation(ranks), ref)
        assert np.allclose(phase87_rank_modulation(ranks), ref)
        assert np.allclose(phase87_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v87(ranks), ref)
        assert np.allclose(Phase87FactorSuppressionEngine.compute_phase87_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase87_hyperconvex_rank_modulation(ranks), ref)
