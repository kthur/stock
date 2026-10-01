"""
tests/test_phase91_alpha.py

Unit test suite for Phase 91 Quantitative Alpha Enhancement (Features F425, F426):
- Feature F425: Asymmetric Octacosidodecagonal (536th-Order) Hyperbolic Deadband
  (alpha_pos = 536.0, delta_noise = 0.035, noise suppression < 10^-536 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F425: 113th-Order Hyperconvex Rank Modulation
  (g_v91(r) = 0.50 + 3.50 * r * exp(gamma_top * r^113) with REGIME_GAMMA_TOP_V91,
   gamma_top <= 28.80, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F426: Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds Moonshine Monster Whittaker Coupler v91
  (defaults to version=91, kappa_monster_whit=36.80, lambda_monster=0.9999999999999995,
   is_phase91=True, harmony_boost=8.15,
   output keys FERI_v91, feri_v91, f_out_91, FERI_v90, feri_v90, f_out_90, FERI_v89, feri_v89, f_out_89, FERI_v88, feri_v88, f_out_88).
- Full alias trees for deadband, rank modulation, and coupler across classes and module level.
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

try:
    from trading_system.src.ai.factor_suppression import (
        apply_octacosidodecagonal_hyperbolic_deadband,
        apply_octacosidodecadihedral_hyperbolic_deadband,
        apply_quingentatriacontasagonal_hyperbolic_deadband,
        apply_pentacentatriacontasagonal_hyperbolic_deadband,
        apply_octacosidodeca_hyperbolic_deadband,
        apply_octacosidodecagonal_deadband,
        octacosidodecagonal_deadband,
        octacosidodecagonal_hyperbolic_deadband,
        compute_phase91_deadband,
        apply_phase91_deadband,
        phase91_deadband,
        apply_536th_order_hyperbolic_deadband,
        apply_536th_deadband,
        apply_536_deadband,
        apply_hyperbolic_deadband_v91,
        suppress_factor_noise_hyperbolic_v91,
        compute_phase91_hyperconvex_rank_modulation,
        compute_phase91_rank_warping,
        compute_phase91_rank_modulation,
        phase91_rank_modulation,
        phase91_hyperconvex_rank_modulation,
        apply_hyper_convex_rank_modulation_v91,
        REGIME_GAMMA_TOP_V91,
        get_regime_adaptive_gamma_top_v91,
        Phase91FactorSuppressionEngine,
        RegimeFactorSuppressionEngine,
    )
except ImportError:
    import trading_system.src.ai.factor_suppression as _fs

    def _missing_fs(name):
        val = getattr(_fs, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'factor_suppression' has no Phase 91 attribute '{name}'")
        return _callable

    apply_octacosidodecagonal_hyperbolic_deadband = _missing_fs('apply_octacosidodecagonal_hyperbolic_deadband')
    apply_octacosidodecadihedral_hyperbolic_deadband = _missing_fs('apply_octacosidodecadihedral_hyperbolic_deadband')
    apply_quingentatriacontasagonal_hyperbolic_deadband = _missing_fs('apply_quingentatriacontasagonal_hyperbolic_deadband')
    apply_pentacentatriacontasagonal_hyperbolic_deadband = _missing_fs('apply_pentacentatriacontasagonal_hyperbolic_deadband')
    apply_octacosidodeca_hyperbolic_deadband = _missing_fs('apply_octacosidodeca_hyperbolic_deadband')
    apply_octacosidodecagonal_deadband = _missing_fs('apply_octacosidodecagonal_deadband')
    octacosidodecagonal_deadband = _missing_fs('octacosidodecagonal_deadband')
    octacosidodecagonal_hyperbolic_deadband = _missing_fs('octacosidodecagonal_hyperbolic_deadband')
    compute_phase91_deadband = _missing_fs('compute_phase91_deadband')
    apply_phase91_deadband = _missing_fs('apply_phase91_deadband')
    phase91_deadband = _missing_fs('phase91_deadband')
    apply_536th_order_hyperbolic_deadband = _missing_fs('apply_536th_order_hyperbolic_deadband')
    apply_536th_deadband = _missing_fs('apply_536th_deadband')
    apply_536_deadband = _missing_fs('apply_536_deadband')
    apply_hyperbolic_deadband_v91 = _missing_fs('apply_hyperbolic_deadband_v91')
    suppress_factor_noise_hyperbolic_v91 = _missing_fs('suppress_factor_noise_hyperbolic_v91')

    compute_phase91_hyperconvex_rank_modulation = _missing_fs('compute_phase91_hyperconvex_rank_modulation')
    compute_phase91_rank_warping = _missing_fs('compute_phase91_rank_warping')
    compute_phase91_rank_modulation = _missing_fs('compute_phase91_rank_modulation')
    phase91_rank_modulation = _missing_fs('phase91_rank_modulation')
    phase91_hyperconvex_rank_modulation = _missing_fs('phase91_hyperconvex_rank_modulation')
    apply_hyper_convex_rank_modulation_v91 = _missing_fs('apply_hyper_convex_rank_modulation_v91')

    REGIME_GAMMA_TOP_V91 = getattr(_fs, 'REGIME_GAMMA_TOP_V91', {})
    get_regime_adaptive_gamma_top_v91 = _missing_fs('get_regime_adaptive_gamma_top_v91')
    Phase91FactorSuppressionEngine = getattr(_fs, 'Phase91FactorSuppressionEngine', None)
    RegimeFactorSuppressionEngine = getattr(_fs, 'RegimeFactorSuppressionEngine', None)

try:
    from trading_system.src.ai.ensemble_scorer import (
        QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
        Phase91Coupler,
        Phase91WhittakerDrinfeldCoupler,
        Phase91BorcherdsMoonshineCoupler,
        Phase91MonsterWhittakerCoupler,
        compute_phase91_coupling,
        Phase90Coupler,
        Phase89Coupler,
        Phase88Coupler,
        Phase87Coupler,
        Phase86Coupler,
        Phase85Coupler,
        EnsembleScoringEngine,
    )
except ImportError:
    import trading_system.src.ai.ensemble_scorer as _es
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler = getattr(
        _es, 'QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler', None
    )
    Phase91Coupler = getattr(_es, 'Phase91Coupler', None)
    Phase91WhittakerDrinfeldCoupler = getattr(_es, 'Phase91WhittakerDrinfeldCoupler', None)
    Phase91BorcherdsMoonshineCoupler = getattr(_es, 'Phase91BorcherdsMoonshineCoupler', None)
    Phase91MonsterWhittakerCoupler = getattr(_es, 'Phase91MonsterWhittakerCoupler', None)
    def _missing_coupling(*args, **kwargs):
        comp = getattr(_es, 'compute_phase91_coupling', None)
        if comp is not None:
            return comp(*args, **kwargs)
        raise AttributeError("Module 'ensemble_scorer' has no Phase 91 attribute 'compute_phase91_coupling'")
    compute_phase91_coupling = _missing_coupling
    Phase90Coupler = getattr(_es, 'Phase90Coupler', None)
    Phase89Coupler = getattr(_es, 'Phase89Coupler', None)
    Phase88Coupler = getattr(_es, 'Phase88Coupler', None)
    Phase87Coupler = getattr(_es, 'Phase87Coupler', None)
    Phase86Coupler = getattr(_es, 'Phase86Coupler', None)
    Phase85Coupler = getattr(_es, 'Phase85Coupler', None)
    EnsembleScoringEngine = getattr(_es, 'EnsembleScoringEngine', None)


class TestPhase91AlphaEnhancements:
    """Unit test suite for Phase 91 Alpha Enhancements (Features F425, F426)."""

    def test_feature_f426_coupler_properties_v91(self):
        """Verify Borcherds-Moonshine Monster Whittaker Coupler properties for version 91."""
        assert QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler is not None
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=36.80,
            lambda_monster=0.9999999999999995,
            version=91,
        )
        assert coupler.kappa_monster_whit == 36.80
        assert coupler.lambda_monster == 0.9999999999999995
        assert coupler.version == 91
        assert getattr(coupler, "is_phase91", False) is True
        assert coupler.harmony_boost == 8.15

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
        assert 'FERI_v91' in res
        assert 'feri_v91' in res
        assert 'f_out_91' in res
        assert 'FERI_v90' in res
        assert 'feri_v90' in res
        assert 'f_out_90' in res
        assert 'FERI_v89' in res
        assert 'feri_v89' in res
        assert 'f_out_89' in res
        assert 'FERI_v88' in res
        assert 'feri_v88' in res
        assert 'f_out_88' in res

        feri_91 = res['FERI_v91']
        assert len(feri_91) == len(p_df)
        assert np.all(np.isfinite(feri_91))

    def test_feature_f426_coupler_aliases(self):
        """Verify all Phase 91 coupler class aliases and coupling function."""
        assert Phase91Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase91WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase91BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase91MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase90Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase89Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase88Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase87Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase86Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase85Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        p_df = pd.DataFrame({
            'val': [0.50, 0.45],
            'mom': [0.50, 0.55],
            'flow': [0.50, 0.50],
            'cat': [0.50, 0.60],
            'net': [0.50, 0.40],
        })
        res = compute_phase91_coupling(p_df)
        assert 'FERI_v91' in res

    def test_feature_f425_deadband_suppression(self):
        """Verify 536th-order hyperbolic deadband suppresses noise < 10^-536 and preserves signals 100%."""
        # Sub-threshold near-zero noise |z| <= 0.0003 suppressed below 10^-536 (float64 underflow < 1e-300 or 0.0)
        sub_noise = np.array([0.0001, 0.0002, 0.0003, -0.0001, -0.0002, -0.0003])
        denoised = apply_octacosidodecagonal_hyperbolic_deadband(sub_noise, delta_noise=0.035, alpha_pos=536.0)
        for val in denoised:
            assert abs(val) < 1e-300 or val == 0.0

        # Full retention for high-conviction signals |z| >= 0.150
        strong_sig = np.array([0.150, 0.20, 0.50, -0.150, -0.20, -0.50])
        denoised_strong = apply_octacosidodecagonal_hyperbolic_deadband(strong_sig, delta_noise=0.035, alpha_pos=536.0)
        for orig, d in zip(strong_sig, denoised_strong):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test across full spectrum
        grid = np.linspace(0.001, 1.0, 100)
        grid_out = apply_octacosidodecagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=536.0)
        rho, _ = spearmanr(grid, grid_out)
        assert math.isclose(rho, 1.0, rel_tol=1e-5)

    def test_feature_f425_deadband_aliases(self):
        """Verify all 17 aliases of the 536th-order octacosidodecagonal deadband produce identical output."""
        arr = np.array([0.0002, 0.18, -0.0002, -0.18])
        ref = apply_octacosidodecagonal_hyperbolic_deadband(arr)

        assert np.allclose(apply_octacosidodecadihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quingentatriacontasagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacentatriacontasagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_octacosidodeca_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_octacosidodecagonal_deadband(arr), ref)
        assert np.allclose(octacosidodecagonal_deadband(arr), ref)
        assert np.allclose(octacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(compute_phase91_deadband(arr), ref)
        assert np.allclose(apply_phase91_deadband(arr), ref)
        assert np.allclose(phase91_deadband(arr), ref)
        assert np.allclose(apply_536th_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_536th_deadband(arr), ref)
        assert np.allclose(apply_536_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v91(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v91(arr), ref)
        assert Phase91FactorSuppressionEngine is not None
        assert np.allclose(Phase91FactorSuppressionEngine.apply_octacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert RegimeFactorSuppressionEngine is not None
        assert np.allclose(RegimeFactorSuppressionEngine.apply_octacosidodecagonal_hyperbolic_deadband(arr), ref)

    def test_feature_f425_rank_modulation(self):
        """Verify 113th-order hyperconvex rank modulation expansion and negative signal branch."""
        ranks = np.array([0.0, 0.5, 0.9, 1.0])
        mod = compute_phase91_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")
        assert len(mod) == len(ranks)
        assert np.all(np.diff(mod) > 0)
        assert mod[-1] > 1e7

        # Negative signal test: follows g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.1, -0.2])
        r_neg = np.array([0.2, 0.8])
        mod_neg = compute_phase91_hyperconvex_rank_modulation(r_neg, z_denoised=z_neg)
        assert math.isclose(mod_neg[0], 1.35 - 1.00 * 0.2, rel_tol=1e-5)
        assert math.isclose(mod_neg[1], 1.35 - 1.00 * 0.8, rel_tol=1e-5)

    def test_feature_f425_rank_modulation_regimes(self):
        """Verify regime adaptive gamma table matches REGIME_GAMMA_TOP_V91 with ceiling 28.80."""
        assert isinstance(REGIME_GAMMA_TOP_V91, dict)
        assert len(REGIME_GAMMA_TOP_V91) > 0
        for regime, gamma in REGIME_GAMMA_TOP_V91.items():
            g = get_regime_adaptive_gamma_top_v91(regime)
            assert g == gamma
            assert g <= 28.80
        assert REGIME_GAMMA_TOP_V91.get('BULL_LOW_VOL', 28.80) <= 28.80

    def test_feature_f425_rank_modulation_aliases(self):
        """Verify all aliases of 113th-order rank modulation produce identical results."""
        ranks = np.array([0.1, 0.8])
        ref = compute_phase91_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase91_rank_warping(ranks), ref)
        assert np.allclose(compute_phase91_rank_modulation(ranks), ref)
        assert np.allclose(phase91_rank_modulation(ranks), ref)
        assert np.allclose(phase91_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v91(ranks), ref)
        assert Phase91FactorSuppressionEngine is not None
        assert np.allclose(Phase91FactorSuppressionEngine.compute_phase91_hyperconvex_rank_modulation(ranks), ref)
        assert RegimeFactorSuppressionEngine is not None
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase91_hyperconvex_rank_modulation(ranks), ref)
