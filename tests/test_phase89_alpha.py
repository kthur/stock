"""
tests/test_phase89_alpha.py

Unit test suite for Phase 89 Quantitative Alpha Enhancement (Features F415, F416):
- Feature F415: Asymmetric Hexacosidodecagonal (520th-Order) Hyperbolic Deadband
  (alpha_pos = 520.0, delta_noise = 0.035, noise suppression < 10^-520 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F415: 109th-Order Hyperconvex Rank Modulation
  (g_v89(r) = 0.50 + 3.42 * r * exp(gamma_top * r^109) with REGIME_GAMMA_TOP_V89,
   gamma_top <= 26.20, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F416: Borcherds-Moonshine Monster Whittaker Coupler v89
  (defaults to version=89, kappa_monster_whit=35.60, lambda_monster=0.999999999999995,
   is_phase89=True, harmony_boost=7.45, 190th-order chiral oper obstruction, 102nd-order topological defect invariant,
   output keys FERI_v89, feri_v89, f_out_89, FERI_v88, feri_v88, f_out_88).
- Full alias trees for deadband, rank modulation, and coupler across classes and module level.
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

try:
    from trading_system.src.ai.factor_suppression import (
        apply_hexacosidodecagonal_hyperbolic_deadband,
        apply_hexacosidodecadihedral_hyperbolic_deadband,
        apply_quingentaicosagonal_hyperbolic_deadband,
        apply_pentacentaicosagonal_hyperbolic_deadband,
        apply_hexacosidodeca_hyperbolic_deadband,
        apply_hexacosidodecagonal_deadband,
        hexacosidodecagonal_deadband,
        hexacosidodecagonal_hyperbolic_deadband,
        compute_phase89_deadband,
        apply_phase89_deadband,
        phase89_deadband,
        apply_520th_order_hyperbolic_deadband,
        apply_520th_deadband,
        apply_520_deadband,
        apply_hyperbolic_deadband_v89,
        suppress_factor_noise_hyperbolic_v89,
        compute_phase89_hyperconvex_rank_modulation,
        compute_phase89_rank_warping,
        compute_phase89_rank_modulation,
        phase89_rank_modulation,
        phase89_hyperconvex_rank_modulation,
        apply_hyper_convex_rank_modulation_v89,
        REGIME_GAMMA_TOP_V89,
        get_regime_adaptive_gamma_top_v89,
        Phase89FactorSuppressionEngine,
        RegimeFactorSuppressionEngine,
    )
except ImportError:
    import trading_system.src.ai.factor_suppression as _fs

    def _missing_fs(name):
        val = getattr(_fs, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'factor_suppression' has no Phase 89 attribute '{name}'")
        return _callable

    apply_hexacosidodecagonal_hyperbolic_deadband = _missing_fs('apply_hexacosidodecagonal_hyperbolic_deadband')
    apply_hexacosidodecadihedral_hyperbolic_deadband = _missing_fs('apply_hexacosidodecadihedral_hyperbolic_deadband')
    apply_quingentaicosagonal_hyperbolic_deadband = _missing_fs('apply_quingentaicosagonal_hyperbolic_deadband')
    apply_pentacentaicosagonal_hyperbolic_deadband = _missing_fs('apply_pentacentaicosagonal_hyperbolic_deadband')
    apply_hexacosidodeca_hyperbolic_deadband = _missing_fs('apply_hexacosidodeca_hyperbolic_deadband')
    apply_hexacosidodecagonal_deadband = _missing_fs('apply_hexacosidodecagonal_deadband')
    hexacosidodecagonal_deadband = _missing_fs('hexacosidodecagonal_deadband')
    hexacosidodecagonal_hyperbolic_deadband = _missing_fs('hexacosidodecagonal_hyperbolic_deadband')
    compute_phase89_deadband = _missing_fs('compute_phase89_deadband')
    apply_phase89_deadband = _missing_fs('apply_phase89_deadband')
    phase89_deadband = _missing_fs('phase89_deadband')
    apply_520th_order_hyperbolic_deadband = _missing_fs('apply_520th_order_hyperbolic_deadband')
    apply_520th_deadband = _missing_fs('apply_520th_deadband')
    apply_520_deadband = _missing_fs('apply_520_deadband')
    apply_hyperbolic_deadband_v89 = _missing_fs('apply_hyperbolic_deadband_v89')
    suppress_factor_noise_hyperbolic_v89 = _missing_fs('suppress_factor_noise_hyperbolic_v89')

    compute_phase89_hyperconvex_rank_modulation = _missing_fs('compute_phase89_hyperconvex_rank_modulation')
    compute_phase89_rank_warping = _missing_fs('compute_phase89_rank_warping')
    compute_phase89_rank_modulation = _missing_fs('compute_phase89_rank_modulation')
    phase89_rank_modulation = _missing_fs('phase89_rank_modulation')
    phase89_hyperconvex_rank_modulation = _missing_fs('phase89_hyperconvex_rank_modulation')
    apply_hyper_convex_rank_modulation_v89 = _missing_fs('apply_hyper_convex_rank_modulation_v89')

    REGIME_GAMMA_TOP_V89 = getattr(_fs, 'REGIME_GAMMA_TOP_V89', {})
    get_regime_adaptive_gamma_top_v89 = _missing_fs('get_regime_adaptive_gamma_top_v89')
    Phase89FactorSuppressionEngine = getattr(_fs, 'Phase89FactorSuppressionEngine', None)
    RegimeFactorSuppressionEngine = getattr(_fs, 'RegimeFactorSuppressionEngine', None)

try:
    from trading_system.src.ai.ensemble_scorer import (
        QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
        Phase89Coupler,
        Phase89WhittakerDrinfeldCoupler,
        Phase89BorcherdsMoonshineCoupler,
        Phase89MonsterWhittakerCoupler,
        compute_phase89_coupling,
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
    Phase89Coupler = getattr(_es, 'Phase89Coupler', None)
    Phase89WhittakerDrinfeldCoupler = getattr(_es, 'Phase89WhittakerDrinfeldCoupler', None)
    Phase89BorcherdsMoonshineCoupler = getattr(_es, 'Phase89BorcherdsMoonshineCoupler', None)
    Phase89MonsterWhittakerCoupler = getattr(_es, 'Phase89MonsterWhittakerCoupler', None)
    def _missing_coupling(*args, **kwargs):
        comp = getattr(_es, 'compute_phase89_coupling', None)
        if comp is not None:
            return comp(*args, **kwargs)
        raise AttributeError("Module 'ensemble_scorer' has no Phase 89 attribute 'compute_phase89_coupling'")
    compute_phase89_coupling = _missing_coupling
    Phase88Coupler = getattr(_es, 'Phase88Coupler', None)
    Phase87Coupler = getattr(_es, 'Phase87Coupler', None)
    Phase86Coupler = getattr(_es, 'Phase86Coupler', None)
    Phase85Coupler = getattr(_es, 'Phase85Coupler', None)
    EnsembleScoringEngine = getattr(_es, 'EnsembleScoringEngine', None)


class TestPhase89AlphaEnhancements:
    """Unit test suite for Phase 89 Alpha Enhancements (Features F415, F416)."""

    def test_feature_f416_coupler_properties_v89(self):
        """Verify Borcherds-Moonshine Monster Whittaker Coupler properties for version 89."""
        assert QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler is not None
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=35.60,
            lambda_monster=0.999999999999995,
            version=89,
        )
        assert coupler.kappa_monster_whit == 35.60
        assert coupler.lambda_monster == 0.999999999999995
        assert coupler.version == 89
        assert getattr(coupler, "is_phase89", False) is True
        assert coupler.harmony_boost == 7.45

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
        assert 'FERI_v89' in res
        assert 'feri_v89' in res
        assert 'f_out_89' in res
        assert 'FERI_v88' in res
        assert 'feri_v88' in res
        assert 'f_out_88' in res
        assert 'FERI_v87' in res
        assert 'feri_v87' in res
        assert 'f_out_87' in res

        feri_89 = res['FERI_v89']
        assert len(feri_89) == len(p_df)
        assert np.all(np.isfinite(feri_89))

    def test_feature_f416_coupler_aliases(self):
        """Verify all Phase 89 coupler class aliases and coupling function."""
        assert Phase89Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase89WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase89BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase89MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
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
        res = compute_phase89_coupling(p_df)
        assert 'FERI_v89' in res

    def test_feature_f415_deadband_suppression(self):
        """Verify 520th-order hyperbolic deadband suppresses noise < 10^-520 and preserves signals 100%."""
        # Sub-threshold near-zero noise |z| <= 0.0003 suppressed below 10^-520 (float64 underflow < 1e-300 or 0.0)
        sub_noise = np.array([0.0001, 0.0002, 0.0003, -0.0001, -0.0002, -0.0003])
        denoised = apply_hexacosidodecagonal_hyperbolic_deadband(sub_noise, delta_noise=0.035, alpha_pos=520.0)
        for val in denoised:
            assert abs(val) < 1e-300 or val == 0.0

        # Full retention for high-conviction signals |z| >= 0.150
        strong_sig = np.array([0.150, 0.20, 0.50, -0.150, -0.20, -0.50])
        denoised_strong = apply_hexacosidodecagonal_hyperbolic_deadband(strong_sig, delta_noise=0.035, alpha_pos=520.0)
        for orig, d in zip(strong_sig, denoised_strong):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test across full spectrum
        grid = np.linspace(0.001, 1.0, 100)
        grid_out = apply_hexacosidodecagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=520.0)
        rho, _ = spearmanr(grid, grid_out)
        assert math.isclose(rho, 1.0, rel_tol=1e-5)

    def test_feature_f415_deadband_aliases(self):
        """Verify all 17 aliases of the 520th-order hexacosidodecagonal deadband produce identical output."""
        arr = np.array([0.0002, 0.18, -0.0002, -0.18])
        ref = apply_hexacosidodecagonal_hyperbolic_deadband(arr)

        assert np.allclose(apply_hexacosidodecadihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quingentaicosagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacentaicosagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_hexacosidodeca_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_hexacosidodecagonal_deadband(arr), ref)
        assert np.allclose(hexacosidodecagonal_deadband(arr), ref)
        assert np.allclose(hexacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(compute_phase89_deadband(arr), ref)
        assert np.allclose(apply_phase89_deadband(arr), ref)
        assert np.allclose(phase89_deadband(arr), ref)
        assert np.allclose(apply_520th_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_520th_deadband(arr), ref)
        assert np.allclose(apply_520_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v89(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v89(arr), ref)
        assert Phase89FactorSuppressionEngine is not None
        assert np.allclose(Phase89FactorSuppressionEngine.apply_hexacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert RegimeFactorSuppressionEngine is not None
        assert np.allclose(RegimeFactorSuppressionEngine.apply_hexacosidodecagonal_hyperbolic_deadband(arr), ref)

    def test_feature_f415_rank_modulation(self):
        """Verify 109th-order hyperconvex rank modulation expansion and negative signal branch."""
        ranks = np.array([0.0, 0.5, 0.9, 1.0])
        mod = compute_phase89_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")
        assert len(mod) == len(ranks)
        assert np.all(np.diff(mod) > 0)
        assert mod[-1] > 1e7

        # Negative signal test: follows g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.1, -0.2])
        r_neg = np.array([0.2, 0.8])
        mod_neg = compute_phase89_hyperconvex_rank_modulation(r_neg, z_denoised=z_neg)
        assert math.isclose(mod_neg[0], 1.35 - 1.00 * 0.2, rel_tol=1e-5)
        assert math.isclose(mod_neg[1], 1.35 - 1.00 * 0.8, rel_tol=1e-5)

    def test_feature_f415_rank_modulation_regimes(self):
        """Verify regime adaptive gamma table matches REGIME_GAMMA_TOP_V89 with ceiling 26.20."""
        assert isinstance(REGIME_GAMMA_TOP_V89, dict)
        assert len(REGIME_GAMMA_TOP_V89) > 0
        for regime, gamma in REGIME_GAMMA_TOP_V89.items():
            g = get_regime_adaptive_gamma_top_v89(regime)
            assert g == gamma
            assert g <= 26.20
        assert REGIME_GAMMA_TOP_V89['BULL_LOW_VOL'] == 26.20
        assert REGIME_GAMMA_TOP_V89['BULL_HIGH_VOL'] == 22.00
        assert REGIME_GAMMA_TOP_V89['SIDEWAYS'] == 17.55
        assert REGIME_GAMMA_TOP_V89['BEAR'] == 8.80
        assert REGIME_GAMMA_TOP_V89['BEAR_HIGH_VOL'] == 4.40
        assert REGIME_GAMMA_TOP_V89['PANIC'] == 2.10
        assert REGIME_GAMMA_TOP_V89['CRISIS'] == 2.10
        assert REGIME_GAMMA_TOP_V89['RECOVERY'] == 22.00

    def test_feature_f415_rank_modulation_aliases(self):
        """Verify all aliases of 109th-order rank modulation produce identical results."""
        ranks = np.array([0.1, 0.8])
        ref = compute_phase89_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase89_rank_warping(ranks), ref)
        assert np.allclose(compute_phase89_rank_modulation(ranks), ref)
        assert np.allclose(phase89_rank_modulation(ranks), ref)
        assert np.allclose(phase89_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v89(ranks), ref)
        assert Phase89FactorSuppressionEngine is not None
        assert np.allclose(Phase89FactorSuppressionEngine.compute_phase89_hyperconvex_rank_modulation(ranks), ref)
        assert RegimeFactorSuppressionEngine is not None
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase89_hyperconvex_rank_modulation(ranks), ref)
