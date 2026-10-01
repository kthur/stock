"""
tests/test_phase90_alpha.py

Unit test suite for Phase 90 Quantitative Alpha Enhancement (Features F420, F421):
- Feature F420: Asymmetric Heptacosidodecagonal (528th-Order) Hyperbolic Deadband
  (alpha_pos = 528.0, delta_noise = 0.035, noise suppression < 10^-528 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F420: 111th-Order Hyperconvex Rank Modulation
  (g_v90(r) = 0.50 + 3.46 * r * exp(gamma_top * r^111) with REGIME_GAMMA_TOP_V90,
   gamma_top <= 27.50, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F421: Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds Moonshine Monster Whittaker Coupler v90
  (defaults to version=90, kappa_monster_whit=36.20, lambda_monster=0.999999999999999,
   is_phase90=True, harmony_boost=7.80,
   output keys FERI_v90, feri_v90, f_out_90, FERI_v89, feri_v89, f_out_89, FERI_v88, feri_v88, f_out_88).
- Full alias trees for deadband, rank modulation, and coupler across classes and module level.
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

try:
    from trading_system.src.ai.factor_suppression import (
        apply_heptacosidodecagonal_hyperbolic_deadband,
        apply_heptacosidodecadihedral_hyperbolic_deadband,
        apply_quingentaoctacosagonal_hyperbolic_deadband,
        apply_pentacentaoctacosagonal_hyperbolic_deadband,
        apply_heptacosidodeca_hyperbolic_deadband,
        apply_heptacosidodecagonal_deadband,
        heptacosidodecagonal_deadband,
        heptacosidodecagonal_hyperbolic_deadband,
        compute_phase90_deadband,
        apply_phase90_deadband,
        phase90_deadband,
        apply_528th_order_hyperbolic_deadband,
        apply_528th_deadband,
        apply_528_deadband,
        apply_hyperbolic_deadband_v90,
        suppress_factor_noise_hyperbolic_v90,
        compute_phase90_hyperconvex_rank_modulation,
        compute_phase90_rank_warping,
        compute_phase90_rank_modulation,
        phase90_rank_modulation,
        phase90_hyperconvex_rank_modulation,
        apply_hyper_convex_rank_modulation_v90,
        REGIME_GAMMA_TOP_V90,
        get_regime_adaptive_gamma_top_v90,
        Phase90FactorSuppressionEngine,
        RegimeFactorSuppressionEngine,
    )
except ImportError:
    import trading_system.src.ai.factor_suppression as _fs

    def _missing_fs(name):
        val = getattr(_fs, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'factor_suppression' has no Phase 90 attribute '{name}'")
        return _callable

    apply_heptacosidodecagonal_hyperbolic_deadband = _missing_fs('apply_heptacosidodecagonal_hyperbolic_deadband')
    apply_heptacosidodecadihedral_hyperbolic_deadband = _missing_fs('apply_heptacosidodecadihedral_hyperbolic_deadband')
    apply_quingentaoctacosagonal_hyperbolic_deadband = _missing_fs('apply_quingentaoctacosagonal_hyperbolic_deadband')
    apply_pentacentaoctacosagonal_hyperbolic_deadband = _missing_fs('apply_pentacentaoctacosagonal_hyperbolic_deadband')
    apply_heptacosidodeca_hyperbolic_deadband = _missing_fs('apply_heptacosidodeca_hyperbolic_deadband')
    apply_heptacosidodecagonal_deadband = _missing_fs('apply_heptacosidodecagonal_deadband')
    heptacosidodecagonal_deadband = _missing_fs('heptacosidodecagonal_deadband')
    heptacosidodecagonal_hyperbolic_deadband = _missing_fs('heptacosidodecagonal_hyperbolic_deadband')
    compute_phase90_deadband = _missing_fs('compute_phase90_deadband')
    apply_phase90_deadband = _missing_fs('apply_phase90_deadband')
    phase90_deadband = _missing_fs('phase90_deadband')
    apply_528th_order_hyperbolic_deadband = _missing_fs('apply_528th_order_hyperbolic_deadband')
    apply_528th_deadband = _missing_fs('apply_528th_deadband')
    apply_528_deadband = _missing_fs('apply_528_deadband')
    apply_hyperbolic_deadband_v90 = _missing_fs('apply_hyperbolic_deadband_v90')
    suppress_factor_noise_hyperbolic_v90 = _missing_fs('suppress_factor_noise_hyperbolic_v90')

    compute_phase90_hyperconvex_rank_modulation = _missing_fs('compute_phase90_hyperconvex_rank_modulation')
    compute_phase90_rank_warping = _missing_fs('compute_phase90_rank_warping')
    compute_phase90_rank_modulation = _missing_fs('compute_phase90_rank_modulation')
    phase90_rank_modulation = _missing_fs('phase90_rank_modulation')
    phase90_hyperconvex_rank_modulation = _missing_fs('phase90_hyperconvex_rank_modulation')
    apply_hyper_convex_rank_modulation_v90 = _missing_fs('apply_hyper_convex_rank_modulation_v90')

    REGIME_GAMMA_TOP_V90 = getattr(_fs, 'REGIME_GAMMA_TOP_V90', {})
    get_regime_adaptive_gamma_top_v90 = _missing_fs('get_regime_adaptive_gamma_top_v90')
    Phase90FactorSuppressionEngine = getattr(_fs, 'Phase90FactorSuppressionEngine', None)
    RegimeFactorSuppressionEngine = getattr(_fs, 'RegimeFactorSuppressionEngine', None)

try:
    from trading_system.src.ai.ensemble_scorer import (
        QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
        Phase90Coupler,
        Phase90WhittakerDrinfeldCoupler,
        Phase90BorcherdsMoonshineCoupler,
        Phase90MonsterWhittakerCoupler,
        compute_phase90_coupling,
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
    Phase90Coupler = getattr(_es, 'Phase90Coupler', None)
    Phase90WhittakerDrinfeldCoupler = getattr(_es, 'Phase90WhittakerDrinfeldCoupler', None)
    Phase90BorcherdsMoonshineCoupler = getattr(_es, 'Phase90BorcherdsMoonshineCoupler', None)
    Phase90MonsterWhittakerCoupler = getattr(_es, 'Phase90MonsterWhittakerCoupler', None)
    def _missing_coupling(*args, **kwargs):
        comp = getattr(_es, 'compute_phase90_coupling', None)
        if comp is not None:
            return comp(*args, **kwargs)
        raise AttributeError("Module 'ensemble_scorer' has no Phase 90 attribute 'compute_phase90_coupling'")
    compute_phase90_coupling = _missing_coupling
    Phase89Coupler = getattr(_es, 'Phase89Coupler', None)
    Phase88Coupler = getattr(_es, 'Phase88Coupler', None)
    Phase87Coupler = getattr(_es, 'Phase87Coupler', None)
    Phase86Coupler = getattr(_es, 'Phase86Coupler', None)
    Phase85Coupler = getattr(_es, 'Phase85Coupler', None)
    EnsembleScoringEngine = getattr(_es, 'EnsembleScoringEngine', None)


class TestPhase90AlphaEnhancements:
    """Unit test suite for Phase 90 Alpha Enhancements (Features F420, F421)."""

    def test_feature_f421_coupler_properties_v90(self):
        """Verify Borcherds-Moonshine Monster Whittaker Coupler properties for version 90."""
        assert QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler is not None
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=36.20,
            lambda_monster=0.999999999999999,
            version=90,
        )
        assert coupler.kappa_monster_whit == 36.20
        assert coupler.lambda_monster == 0.999999999999999
        assert coupler.version == 90
        assert getattr(coupler, "is_phase90", False) is True
        assert coupler.harmony_boost == 7.80

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
        assert 'FERI_v90' in res
        assert 'feri_v90' in res
        assert 'f_out_90' in res
        assert 'FERI_v89' in res
        assert 'feri_v89' in res
        assert 'f_out_89' in res
        assert 'FERI_v88' in res
        assert 'feri_v88' in res
        assert 'f_out_88' in res

        feri_90 = res['FERI_v90']
        assert len(feri_90) == len(p_df)
        assert np.all(np.isfinite(feri_90))

    def test_feature_f421_coupler_aliases(self):
        """Verify all Phase 90 coupler class aliases and coupling function."""
        assert Phase90Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase90WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase90BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase90MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
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
        res = compute_phase90_coupling(p_df)
        assert 'FERI_v90' in res

    def test_feature_f420_deadband_suppression(self):
        """Verify 528th-order hyperbolic deadband suppresses noise < 10^-528 and preserves signals 100%."""
        # Sub-threshold near-zero noise |z| <= 0.0003 suppressed below 10^-528 (float64 underflow < 1e-300 or 0.0)
        sub_noise = np.array([0.0001, 0.0002, 0.0003, -0.0001, -0.0002, -0.0003])
        denoised = apply_heptacosidodecagonal_hyperbolic_deadband(sub_noise, delta_noise=0.035, alpha_pos=528.0)
        for val in denoised:
            assert abs(val) < 1e-300 or val == 0.0

        # Full retention for high-conviction signals |z| >= 0.150
        strong_sig = np.array([0.150, 0.20, 0.50, -0.150, -0.20, -0.50])
        denoised_strong = apply_heptacosidodecagonal_hyperbolic_deadband(strong_sig, delta_noise=0.035, alpha_pos=528.0)
        for orig, d in zip(strong_sig, denoised_strong):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test across full spectrum
        grid = np.linspace(0.001, 1.0, 100)
        grid_out = apply_heptacosidodecagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=528.0)
        rho, _ = spearmanr(grid, grid_out)
        assert math.isclose(rho, 1.0, rel_tol=1e-5)

    def test_feature_f420_deadband_aliases(self):
        """Verify all 17 aliases of the 528th-order heptacosidodecagonal deadband produce identical output."""
        arr = np.array([0.0002, 0.18, -0.0002, -0.18])
        ref = apply_heptacosidodecagonal_hyperbolic_deadband(arr)

        assert np.allclose(apply_heptacosidodecadihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quingentaoctacosagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacentaoctacosagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_heptacosidodeca_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_heptacosidodecagonal_deadband(arr), ref)
        assert np.allclose(heptacosidodecagonal_deadband(arr), ref)
        assert np.allclose(heptacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(compute_phase90_deadband(arr), ref)
        assert np.allclose(apply_phase90_deadband(arr), ref)
        assert np.allclose(phase90_deadband(arr), ref)
        assert np.allclose(apply_528th_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_528th_deadband(arr), ref)
        assert np.allclose(apply_528_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v90(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v90(arr), ref)
        assert Phase90FactorSuppressionEngine is not None
        assert np.allclose(Phase90FactorSuppressionEngine.apply_heptacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert RegimeFactorSuppressionEngine is not None
        assert np.allclose(RegimeFactorSuppressionEngine.apply_heptacosidodecagonal_hyperbolic_deadband(arr), ref)

    def test_feature_f420_rank_modulation(self):
        """Verify 111th-order hyperconvex rank modulation expansion and negative signal branch."""
        ranks = np.array([0.0, 0.5, 0.9, 1.0])
        mod = compute_phase90_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")
        assert len(mod) == len(ranks)
        assert np.all(np.diff(mod) > 0)
        assert mod[-1] > 1e7

        # Negative signal test: follows g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.1, -0.2])
        r_neg = np.array([0.2, 0.8])
        mod_neg = compute_phase90_hyperconvex_rank_modulation(r_neg, z_denoised=z_neg)
        assert math.isclose(mod_neg[0], 1.35 - 1.00 * 0.2, rel_tol=1e-5)
        assert math.isclose(mod_neg[1], 1.35 - 1.00 * 0.8, rel_tol=1e-5)

    def test_feature_f420_rank_modulation_regimes(self):
        """Verify regime adaptive gamma table matches REGIME_GAMMA_TOP_V90 with ceiling 27.50."""
        assert isinstance(REGIME_GAMMA_TOP_V90, dict)
        assert len(REGIME_GAMMA_TOP_V90) > 0
        for regime, gamma in REGIME_GAMMA_TOP_V90.items():
            g = get_regime_adaptive_gamma_top_v90(regime)
            assert g == gamma
            assert g <= 27.50
        assert REGIME_GAMMA_TOP_V90.get('BULL_LOW_VOL', 27.50) <= 27.50

    def test_feature_f420_rank_modulation_aliases(self):
        """Verify all aliases of 111th-order rank modulation produce identical results."""
        ranks = np.array([0.1, 0.8])
        ref = compute_phase90_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase90_rank_warping(ranks), ref)
        assert np.allclose(compute_phase90_rank_modulation(ranks), ref)
        assert np.allclose(phase90_rank_modulation(ranks), ref)
        assert np.allclose(phase90_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v90(ranks), ref)
        assert Phase90FactorSuppressionEngine is not None
        assert np.allclose(Phase90FactorSuppressionEngine.compute_phase90_hyperconvex_rank_modulation(ranks), ref)
        assert RegimeFactorSuppressionEngine is not None
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase90_hyperconvex_rank_modulation(ranks), ref)
