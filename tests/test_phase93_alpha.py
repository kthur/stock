"""
tests/test_phase93_alpha.py

Unit test suite for Phase 93 Quantitative Alpha Enhancement (Features F435, F436):
- Feature F435: Asymmetric Decacosidodecagonal (552nd-Order) Hyperbolic Deadband
  (alpha_pos = 552.0, delta_noise = 0.035, noise suppression < 10^-552 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F435: 117th-Order Hyperconvex Rank Modulation
  (g_v93(r) = 0.50 + 3.58 * r * exp(gamma_top * r^117) with REGIME_GAMMA_TOP_V93,
   gamma_top <= 31.00, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F436: Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds Moonshine Monster Whittaker Coupler v93
  (defaults to version=93, kappa_monster_whit=38.00, lambda_monster=0.99999999999999995 [17-nines + 5],
   is_phase93=True, harmony_boost=8.85,
   198th-order chiral oper obstruction, 110th-order topological defect invariant,
   output keys FERI_v93, feri_v93, f_out_93, FERI_v92, feri_v92, f_out_92, etc.).
- Full alias trees for deadband (19 aliases), rank modulation (5 aliases), and coupler across classes and module level.
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

try:
    from trading_system.src.ai.factor_suppression import (
        apply_decacosidodecagonal_hyperbolic_deadband,
        apply_decacosidodecadihedral_hyperbolic_deadband,
        apply_quingentapentacontasagonal_hyperbolic_deadband,
        apply_quingentapentacontadigonal_hyperbolic_deadband,
        apply_pentacentapentacontasagonal_hyperbolic_deadband,
        apply_pentacentapentacontadigonal_hyperbolic_deadband,
        apply_decacosidodeca_hyperbolic_deadband,
        apply_decacosidodecagonal_deadband,
        decacosidodecagonal_deadband,
        decacosidodecagonal_hyperbolic_deadband,
        compute_phase93_deadband,
        apply_phase93_deadband,
        phase93_deadband,
        apply_552nd_order_hyperbolic_deadband,
        apply_552th_order_hyperbolic_deadband,
        apply_552nd_deadband,
        apply_552th_deadband,
        apply_552_deadband,
        apply_hyperbolic_deadband_v93,
        suppress_factor_noise_hyperbolic_v93,
        compute_phase93_hyperconvex_rank_modulation,
        compute_phase93_rank_warping,
        compute_phase93_rank_modulation,
        phase93_rank_modulation,
        phase93_hyperconvex_rank_modulation,
        apply_hyper_convex_rank_modulation_v93,
        REGIME_GAMMA_TOP_V93,
        get_regime_adaptive_gamma_top_v93,
        Phase93FactorSuppressionEngine,
        RegimeFactorSuppressionEngine,
    )
except ImportError:
    import trading_system.src.ai.factor_suppression as _fs

    def _missing_fs(name):
        val = getattr(_fs, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'factor_suppression' has no Phase 93 attribute '{name}'")
        return _callable

    apply_decacosidodecagonal_hyperbolic_deadband = _missing_fs('apply_decacosidodecagonal_hyperbolic_deadband')
    apply_decacosidodecadihedral_hyperbolic_deadband = _missing_fs('apply_decacosidodecadihedral_hyperbolic_deadband')
    apply_quingentapentacontasagonal_hyperbolic_deadband = _missing_fs('apply_quingentapentacontasagonal_hyperbolic_deadband')
    apply_quingentapentacontadigonal_hyperbolic_deadband = _missing_fs('apply_quingentapentacontadigonal_hyperbolic_deadband')
    apply_pentacentapentacontasagonal_hyperbolic_deadband = _missing_fs('apply_pentacentapentacontasagonal_hyperbolic_deadband')
    apply_pentacentapentacontadigonal_hyperbolic_deadband = _missing_fs('apply_pentacentapentacontadigonal_hyperbolic_deadband')
    apply_decacosidodeca_hyperbolic_deadband = _missing_fs('apply_decacosidodeca_hyperbolic_deadband')
    apply_decacosidodecagonal_deadband = _missing_fs('apply_decacosidodecagonal_deadband')
    decacosidodecagonal_deadband = _missing_fs('decacosidodecagonal_deadband')
    decacosidodecagonal_hyperbolic_deadband = _missing_fs('decacosidodecagonal_hyperbolic_deadband')
    compute_phase93_deadband = _missing_fs('compute_phase93_deadband')
    apply_phase93_deadband = _missing_fs('apply_phase93_deadband')
    phase93_deadband = _missing_fs('phase93_deadband')
    apply_552nd_order_hyperbolic_deadband = _missing_fs('apply_552nd_order_hyperbolic_deadband')
    apply_552th_order_hyperbolic_deadband = _missing_fs('apply_552th_order_hyperbolic_deadband')
    apply_552nd_deadband = _missing_fs('apply_552nd_deadband')
    apply_552th_deadband = _missing_fs('apply_552th_deadband')
    apply_552_deadband = _missing_fs('apply_552_deadband')
    apply_hyperbolic_deadband_v93 = _missing_fs('apply_hyperbolic_deadband_v93')
    suppress_factor_noise_hyperbolic_v93 = _missing_fs('suppress_factor_noise_hyperbolic_v93')

    compute_phase93_hyperconvex_rank_modulation = _missing_fs('compute_phase93_hyperconvex_rank_modulation')
    compute_phase93_rank_warping = _missing_fs('compute_phase93_rank_warping')
    compute_phase93_rank_modulation = _missing_fs('compute_phase93_rank_modulation')
    phase93_rank_modulation = _missing_fs('phase93_rank_modulation')
    phase93_hyperconvex_rank_modulation = _missing_fs('phase93_hyperconvex_rank_modulation')
    apply_hyper_convex_rank_modulation_v93 = _missing_fs('apply_hyper_convex_rank_modulation_v93')

    REGIME_GAMMA_TOP_V93 = getattr(_fs, 'REGIME_GAMMA_TOP_V93', {})
    get_regime_adaptive_gamma_top_v93 = _missing_fs('get_regime_adaptive_gamma_top_v93')
    Phase93FactorSuppressionEngine = getattr(_fs, 'Phase93FactorSuppressionEngine', None)
    RegimeFactorSuppressionEngine = getattr(_fs, 'RegimeFactorSuppressionEngine', None)

try:
    from trading_system.src.ai.ensemble_scorer import (
        QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
        Phase93Coupler,
        Phase93WhittakerDrinfeldCoupler,
        Phase93BorcherdsMoonshineCoupler,
        Phase93MonsterWhittakerCoupler,
        compute_phase93_coupling,
        Phase92Coupler,
        Phase91Coupler,
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
    Phase93Coupler = getattr(_es, 'Phase93Coupler', None)
    Phase93WhittakerDrinfeldCoupler = getattr(_es, 'Phase93WhittakerDrinfeldCoupler', None)
    Phase93BorcherdsMoonshineCoupler = getattr(_es, 'Phase93BorcherdsMoonshineCoupler', None)
    Phase93MonsterWhittakerCoupler = getattr(_es, 'Phase93MonsterWhittakerCoupler', None)
    def _missing_coupling(*args, **kwargs):
        comp = getattr(_es, 'compute_phase93_coupling', None)
        if comp is not None:
            return comp(*args, **kwargs)
        raise AttributeError("Module 'ensemble_scorer' has no Phase 93 attribute 'compute_phase93_coupling'")
    compute_phase93_coupling = _missing_coupling
    Phase92Coupler = getattr(_es, 'Phase92Coupler', None)
    Phase91Coupler = getattr(_es, 'Phase91Coupler', None)
    Phase90Coupler = getattr(_es, 'Phase90Coupler', None)
    Phase89Coupler = getattr(_es, 'Phase89Coupler', None)
    Phase88Coupler = getattr(_es, 'Phase88Coupler', None)
    Phase87Coupler = getattr(_es, 'Phase87Coupler', None)
    Phase86Coupler = getattr(_es, 'Phase86Coupler', None)
    Phase85Coupler = getattr(_es, 'Phase85Coupler', None)
    EnsembleScoringEngine = getattr(_es, 'EnsembleScoringEngine', None)


class TestPhase93AlphaEnhancements:
    """Unit test suite for Phase 93 Alpha Enhancements (Features F435, F436)."""

    def test_feature_f436_coupler_properties_v93(self):
        """Verify Borcherds-Moonshine Monster Whittaker Coupler properties for version 93."""
        assert QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler is not None
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=38.00,
            lambda_monster=0.99999999999999995,
            version=93,
        )
        assert coupler.kappa_monster_whit == 38.00
        assert coupler.lambda_monster == 0.99999999999999995
        assert coupler.version == 93
        assert getattr(coupler, "is_phase93", False) is True
        assert coupler.harmony_boost == 8.85

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
        assert 'FERI_v93' in res
        assert 'feri_v93' in res
        assert 'f_out_93' in res
        assert 'FERI_v92' in res
        assert 'feri_v92' in res
        assert 'f_out_92' in res
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

        feri_93 = res['FERI_v93']
        assert len(feri_93) == len(p_df)
        assert np.all(np.isfinite(feri_93))

    def test_feature_f436_coupler_aliases(self):
        """Verify all Phase 93 coupler class aliases and coupling function."""
        assert Phase93Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase93WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase93BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase93MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase92Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase91Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
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
        res = compute_phase93_coupling(p_df)
        assert 'FERI_v93' in res

    def test_feature_f435_deadband_suppression(self):
        """Verify 552nd-order hyperbolic deadband suppresses noise < 10^-552 and preserves signals 100%."""
        # Sub-threshold near-zero noise |z| <= 0.0003 suppressed below 10^-552 (float64 underflow < 1e-300 or 0.0)
        sub_noise = np.array([0.0001, 0.0002, 0.0003, -0.0001, -0.0002, -0.0003])
        denoised = apply_decacosidodecagonal_hyperbolic_deadband(sub_noise, delta_noise=0.035, alpha_pos=552.0)
        for val in denoised:
            assert abs(val) < 1e-300 or val == 0.0

        # Full retention for high-conviction signals |z| >= 0.150
        strong_sig = np.array([0.150, 0.20, 0.50, -0.150, -0.20, -0.50])
        denoised_strong = apply_decacosidodecagonal_hyperbolic_deadband(strong_sig, delta_noise=0.035, alpha_pos=552.0)
        for orig, d in zip(strong_sig, denoised_strong):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test across full spectrum
        grid = np.linspace(0.001, 1.0, 100)
        grid_out = apply_decacosidodecagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=552.0)
        rho, _ = spearmanr(grid, grid_out)
        assert math.isclose(rho, 1.0, rel_tol=1e-5)

    def test_feature_f435_deadband_aliases(self):
        """Verify all 19 aliases of the 552nd-order decacosidodecagonal deadband produce identical output."""
        arr = np.array([0.0002, 0.18, -0.0002, -0.18])
        ref = apply_decacosidodecagonal_hyperbolic_deadband(arr)

        assert np.allclose(apply_decacosidodecadihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quingentapentacontasagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quingentapentacontadigonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacentapentacontasagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacentapentacontadigonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_decacosidodeca_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_decacosidodecagonal_deadband(arr), ref)
        assert np.allclose(decacosidodecagonal_deadband(arr), ref)
        assert np.allclose(decacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(compute_phase93_deadband(arr), ref)
        assert np.allclose(apply_phase93_deadband(arr), ref)
        assert np.allclose(phase93_deadband(arr), ref)
        assert np.allclose(apply_552nd_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_552th_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_552nd_deadband(arr), ref)
        assert np.allclose(apply_552th_deadband(arr), ref)
        assert np.allclose(apply_552_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v93(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v93(arr), ref)
        assert Phase93FactorSuppressionEngine is not None
        assert np.allclose(Phase93FactorSuppressionEngine.apply_decacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert RegimeFactorSuppressionEngine is not None
        assert np.allclose(RegimeFactorSuppressionEngine.apply_decacosidodecagonal_hyperbolic_deadband(arr), ref)

    def test_feature_f435_rank_modulation(self):
        """Verify 117th-order hyperconvex rank modulation expansion and negative signal branch."""
        ranks = np.array([0.0, 0.5, 0.9, 1.0])
        mod = compute_phase93_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")
        assert len(mod) == len(ranks)
        assert np.all(np.diff(mod) > 0)
        assert mod[-1] > 1e7

        # Negative signal test: follows g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.1, -0.2])
        r_neg = np.array([0.2, 0.8])
        mod_neg = compute_phase93_hyperconvex_rank_modulation(r_neg, z_denoised=z_neg)
        assert math.isclose(mod_neg[0], 1.35 - 1.00 * 0.2, rel_tol=1e-5)
        assert math.isclose(mod_neg[1], 1.35 - 1.00 * 0.8, rel_tol=1e-5)

    def test_feature_f435_rank_modulation_regimes(self):
        """Verify regime adaptive gamma table matches REGIME_GAMMA_TOP_V93 with ceiling 31.00."""
        assert isinstance(REGIME_GAMMA_TOP_V93, dict)
        assert len(REGIME_GAMMA_TOP_V93) > 0
        for regime, gamma in REGIME_GAMMA_TOP_V93.items():
            g = get_regime_adaptive_gamma_top_v93(regime)
            assert g == gamma
            assert g <= 31.00
        assert REGIME_GAMMA_TOP_V93.get('BULL_LOW_VOL', 31.00) <= 31.00

    def test_feature_f435_rank_modulation_aliases(self):
        """Verify all aliases of 117th-order rank modulation produce identical results."""
        ranks = np.array([0.1, 0.8])
        ref = compute_phase93_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase93_rank_warping(ranks), ref)
        assert np.allclose(compute_phase93_rank_modulation(ranks), ref)
        assert np.allclose(phase93_rank_modulation(ranks), ref)
        assert np.allclose(phase93_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v93(ranks), ref)
        assert Phase93FactorSuppressionEngine is not None
        assert np.allclose(Phase93FactorSuppressionEngine.compute_phase93_hyperconvex_rank_modulation(ranks), ref)
        assert RegimeFactorSuppressionEngine is not None
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase93_hyperconvex_rank_modulation(ranks), ref)
