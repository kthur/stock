"""
tests/test_phase94_alpha.py

Unit test suite for Phase 94 Quantitative Alpha Enhancement (Features F440, F441):
- Feature F440: Asymmetric Hendecacosidodecagonal (560th-Order) Hyperbolic Deadband
  (alpha_pos = 560.0, delta_noise = 0.035, noise suppression < 10^-560 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F440: 119th-Order Hyperconvex Rank Modulation
  (g_v94(r) = 0.50 + 3.62 * r * exp(gamma_top * r^119) with REGIME_GAMMA_TOP_V94,
   gamma_top <= 32.00, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F441: Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds Moonshine Monster Whittaker Coupler v94
  (defaults to version=94, kappa_monster_whit=38.60, lambda_monster=0.99999999999999999 [18-nines],
   is_phase94=True, harmony_boost=9.20,
   200th-order chiral oper obstruction, 112th-order topological defect invariant,
   output keys FERI_v94, feri_v94, f_out_94, FERI_v93, feri_v93, f_out_93, etc.).
- Full alias trees for deadband (24 aliases), rank modulation (6 aliases), and coupler across classes and module level.
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

try:
    from trading_system.src.ai.factor_suppression import (
        apply_hendecacosidodecagonal_hyperbolic_deadband,
        apply_hendecacosidodecadihedral_hyperbolic_deadband,
        apply_undecacosidodecagonal_hyperbolic_deadband,
        apply_undecacosidodecadihedral_hyperbolic_deadband,
        apply_quingentahexacontasagonal_hyperbolic_deadband,
        apply_pentacentahexacontasagonal_hyperbolic_deadband,
        apply_quingentahexacontadigonal_hyperbolic_deadband,
        apply_pentacentahexacontadigonal_hyperbolic_deadband,
        apply_hendecacosidodeca_hyperbolic_deadband,
        apply_undecacosidodeca_hyperbolic_deadband,
        apply_hendecacosidodecagonal_deadband,
        apply_undecacosidodecagonal_deadband,
        hendecacosidodecagonal_deadband,
        undecacosidodecagonal_deadband,
        hendecacosidodecagonal_hyperbolic_deadband,
        undecacosidodecagonal_hyperbolic_deadband,
        compute_phase94_deadband,
        apply_phase94_deadband,
        phase94_deadband,
        apply_560th_order_hyperbolic_deadband,
        apply_560th_deadband,
        apply_560_deadband,
        apply_hyperbolic_deadband_v94,
        suppress_factor_noise_hyperbolic_v94,
        compute_phase94_hyperconvex_rank_modulation,
        compute_phase94_rank_warping,
        compute_phase94_rank_modulation,
        phase94_rank_modulation,
        phase94_hyperconvex_rank_modulation,
        apply_hyper_convex_rank_modulation_v94,
        REGIME_GAMMA_TOP_V94,
        get_regime_adaptive_gamma_top_v94,
        Phase94FactorSuppressionEngine,
        RegimeFactorSuppressionEngine,
    )
except ImportError:
    import trading_system.src.ai.factor_suppression as _fs

    def _missing_fs(name):
        val = getattr(_fs, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'factor_suppression' has no Phase 94 attribute '{name}'")
        return _callable

    apply_hendecacosidodecagonal_hyperbolic_deadband = _missing_fs('apply_hendecacosidodecagonal_hyperbolic_deadband')
    apply_hendecacosidodecadihedral_hyperbolic_deadband = _missing_fs('apply_hendecacosidodecadihedral_hyperbolic_deadband')
    apply_undecacosidodecagonal_hyperbolic_deadband = _missing_fs('apply_undecacosidodecagonal_hyperbolic_deadband')
    apply_undecacosidodecadihedral_hyperbolic_deadband = _missing_fs('apply_undecacosidodecadihedral_hyperbolic_deadband')
    apply_quingentahexacontasagonal_hyperbolic_deadband = _missing_fs('apply_quingentahexacontasagonal_hyperbolic_deadband')
    apply_pentacentahexacontasagonal_hyperbolic_deadband = _missing_fs('apply_pentacentahexacontasagonal_hyperbolic_deadband')
    apply_quingentahexacontadigonal_hyperbolic_deadband = _missing_fs('apply_quingentahexacontadigonal_hyperbolic_deadband')
    apply_pentacentahexacontadigonal_hyperbolic_deadband = _missing_fs('apply_pentacentahexacontadigonal_hyperbolic_deadband')
    apply_hendecacosidodeca_hyperbolic_deadband = _missing_fs('apply_hendecacosidodeca_hyperbolic_deadband')
    apply_undecacosidodeca_hyperbolic_deadband = _missing_fs('apply_undecacosidodeca_hyperbolic_deadband')
    apply_hendecacosidodecagonal_deadband = _missing_fs('apply_hendecacosidodecagonal_deadband')
    apply_undecacosidodecagonal_deadband = _missing_fs('apply_undecacosidodecagonal_deadband')
    hendecacosidodecagonal_deadband = _missing_fs('hendecacosidodecagonal_deadband')
    undecacosidodecagonal_deadband = _missing_fs('undecacosidodecagonal_deadband')
    hendecacosidodecagonal_hyperbolic_deadband = _missing_fs('hendecacosidodecagonal_hyperbolic_deadband')
    undecacosidodecagonal_hyperbolic_deadband = _missing_fs('undecacosidodecagonal_hyperbolic_deadband')
    compute_phase94_deadband = _missing_fs('compute_phase94_deadband')
    apply_phase94_deadband = _missing_fs('apply_phase94_deadband')
    phase94_deadband = _missing_fs('phase94_deadband')
    apply_560th_order_hyperbolic_deadband = _missing_fs('apply_560th_order_hyperbolic_deadband')
    apply_560th_deadband = _missing_fs('apply_560th_deadband')
    apply_560_deadband = _missing_fs('apply_560_deadband')
    apply_hyperbolic_deadband_v94 = _missing_fs('apply_hyperbolic_deadband_v94')
    suppress_factor_noise_hyperbolic_v94 = _missing_fs('suppress_factor_noise_hyperbolic_v94')

    compute_phase94_hyperconvex_rank_modulation = _missing_fs('compute_phase94_hyperconvex_rank_modulation')
    compute_phase94_rank_warping = _missing_fs('compute_phase94_rank_warping')
    compute_phase94_rank_modulation = _missing_fs('compute_phase94_rank_modulation')
    phase94_rank_modulation = _missing_fs('phase94_rank_modulation')
    phase94_hyperconvex_rank_modulation = _missing_fs('phase94_hyperconvex_rank_modulation')
    apply_hyper_convex_rank_modulation_v94 = _missing_fs('apply_hyper_convex_rank_modulation_v94')

    REGIME_GAMMA_TOP_V94 = getattr(_fs, 'REGIME_GAMMA_TOP_V94', {})
    get_regime_adaptive_gamma_top_v94 = _missing_fs('get_regime_adaptive_gamma_top_v94')
    Phase94FactorSuppressionEngine = getattr(_fs, 'Phase94FactorSuppressionEngine', None)
    RegimeFactorSuppressionEngine = getattr(_fs, 'RegimeFactorSuppressionEngine', None)

try:
    from trading_system.src.ai.ensemble_scorer import (
        QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
        Phase94Coupler,
        Phase94WhittakerDrinfeldCoupler,
        Phase94BorcherdsMoonshineCoupler,
        Phase94MonsterWhittakerCoupler,
        compute_phase94_coupling,
        Phase93Coupler,
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
    Phase94Coupler = getattr(_es, 'Phase94Coupler', None)
    Phase94WhittakerDrinfeldCoupler = getattr(_es, 'Phase94WhittakerDrinfeldCoupler', None)
    Phase94BorcherdsMoonshineCoupler = getattr(_es, 'Phase94BorcherdsMoonshineCoupler', None)
    Phase94MonsterWhittakerCoupler = getattr(_es, 'Phase94MonsterWhittakerCoupler', None)
    def _missing_coupling(*args, **kwargs):
        comp = getattr(_es, 'compute_phase94_coupling', None)
        if comp is not None:
            return comp(*args, **kwargs)
        raise AttributeError("Module 'ensemble_scorer' has no Phase 94 attribute 'compute_phase94_coupling'")
    compute_phase94_coupling = _missing_coupling
    Phase93Coupler = getattr(_es, 'Phase93Coupler', None)
    Phase92Coupler = getattr(_es, 'Phase92Coupler', None)
    Phase91Coupler = getattr(_es, 'Phase91Coupler', None)
    Phase90Coupler = getattr(_es, 'Phase90Coupler', None)
    Phase89Coupler = getattr(_es, 'Phase89Coupler', None)
    Phase88Coupler = getattr(_es, 'Phase88Coupler', None)
    Phase87Coupler = getattr(_es, 'Phase87Coupler', None)
    Phase86Coupler = getattr(_es, 'Phase86Coupler', None)
    Phase85Coupler = getattr(_es, 'Phase85Coupler', None)
    EnsembleScoringEngine = getattr(_es, 'EnsembleScoringEngine', None)


class TestPhase94AlphaEnhancements:
    """Unit test suite for Phase 94 Alpha Enhancements (Features F440, F441)."""

    def test_feature_f441_coupler_properties_v94(self):
        """Verify Borcherds-Moonshine Monster Whittaker Coupler properties for version 94."""
        assert QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler is not None
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(
            kappa_monster_whit=38.60,
            lambda_monster=0.99999999999999999,
            version=94,
        )
        assert coupler.kappa_monster_whit == 38.60
        assert coupler.lambda_monster == 0.99999999999999999
        assert coupler.version == 94
        assert getattr(coupler, "is_phase94", False) is True
        assert coupler.harmony_boost == 9.20

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
        assert 'FERI_v94' in res
        assert 'feri_v94' in res
        assert 'f_out_94' in res
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

        feri_94 = res['FERI_v94']
        assert len(feri_94) == len(p_df)
        assert np.all(np.isfinite(feri_94))

    def test_feature_f441_coupler_aliases(self):
        """Verify all Phase 94 coupler class aliases and coupling function."""
        assert Phase94Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase94WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase94BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase94MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase93Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
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
        res = compute_phase94_coupling(p_df)
        assert 'FERI_v94' in res

    def test_feature_f440_deadband_suppression(self):
        """Verify 560th-order hyperbolic deadband suppresses noise < 10^-560 and preserves signals 100%."""
        # Sub-threshold near-zero noise |z| <= 0.0003 suppressed below 10^-560 (float64 underflow < 1e-300 or 0.0)
        sub_noise = np.array([0.0001, 0.0002, 0.0003, -0.0001, -0.0002, -0.0003])
        denoised = apply_hendecacosidodecagonal_hyperbolic_deadband(sub_noise, delta_noise=0.035, alpha_pos=560.0)
        for val in denoised:
            assert abs(val) < 1e-300 or val == 0.0

        # Full retention for high-conviction signals |z| >= 0.150
        strong_sig = np.array([0.150, 0.20, 0.50, -0.150, -0.20, -0.50])
        denoised_strong = apply_hendecacosidodecagonal_hyperbolic_deadband(strong_sig, delta_noise=0.035, alpha_pos=560.0)
        for orig, d in zip(strong_sig, denoised_strong):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test across full spectrum
        grid = np.linspace(0.001, 1.0, 100)
        grid_out = apply_hendecacosidodecagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=560.0)
        rho, _ = spearmanr(grid, grid_out)
        assert math.isclose(rho, 1.0, rel_tol=1e-5)

    def test_feature_f440_deadband_aliases(self):
        """Verify all 24 aliases of the 560th-order hendecacosidodecagonal deadband produce identical output."""
        arr = np.array([0.0002, 0.18, -0.0002, -0.18])
        ref = apply_hendecacosidodecagonal_hyperbolic_deadband(arr)

        assert np.allclose(apply_hendecacosidodecadihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_undecacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_undecacosidodecadihedral_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quingentahexacontasagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacentahexacontasagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_quingentahexacontadigonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_pentacentahexacontadigonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_hendecacosidodeca_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_undecacosidodeca_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_hendecacosidodecagonal_deadband(arr), ref)
        assert np.allclose(apply_undecacosidodecagonal_deadband(arr), ref)
        assert np.allclose(hendecacosidodecagonal_deadband(arr), ref)
        assert np.allclose(undecacosidodecagonal_deadband(arr), ref)
        assert np.allclose(hendecacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(undecacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert np.allclose(compute_phase94_deadband(arr), ref)
        assert np.allclose(apply_phase94_deadband(arr), ref)
        assert np.allclose(phase94_deadband(arr), ref)
        assert np.allclose(apply_560th_order_hyperbolic_deadband(arr), ref)
        assert np.allclose(apply_560th_deadband(arr), ref)
        assert np.allclose(apply_560_deadband(arr), ref)
        assert np.allclose(apply_hyperbolic_deadband_v94(arr), ref)
        assert np.allclose(suppress_factor_noise_hyperbolic_v94(arr), ref)
        assert Phase94FactorSuppressionEngine is not None
        assert np.allclose(Phase94FactorSuppressionEngine.apply_hendecacosidodecagonal_hyperbolic_deadband(arr), ref)
        assert RegimeFactorSuppressionEngine is not None
        assert np.allclose(RegimeFactorSuppressionEngine.apply_hendecacosidodecagonal_hyperbolic_deadband(arr), ref)

    def test_feature_f440_rank_modulation(self):
        """Verify 119th-order hyperconvex rank modulation expansion and negative signal branch."""
        ranks = np.array([0.0, 0.5, 0.9, 1.0])
        mod = compute_phase94_hyperconvex_rank_modulation(ranks, regime="BULL_LOW_VOL")
        assert len(mod) == len(ranks)
        assert np.all(np.diff(mod) > 0)
        assert mod[-1] > 1e7

        # Negative signal test: follows g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.1, -0.2])
        r_neg = np.array([0.2, 0.8])
        mod_neg = compute_phase94_hyperconvex_rank_modulation(r_neg, z_denoised=z_neg)
        assert math.isclose(mod_neg[0], 1.35 - 1.00 * 0.2, rel_tol=1e-5)
        assert math.isclose(mod_neg[1], 1.35 - 1.00 * 0.8, rel_tol=1e-5)

    def test_feature_f440_rank_modulation_regimes(self):
        """Verify regime adaptive gamma table matches REGIME_GAMMA_TOP_V94 with ceiling 32.00."""
        assert isinstance(REGIME_GAMMA_TOP_V94, dict)
        assert len(REGIME_GAMMA_TOP_V94) > 0
        for regime, gamma in REGIME_GAMMA_TOP_V94.items():
            g = get_regime_adaptive_gamma_top_v94(regime)
            assert g == gamma
            assert g <= 32.00
        assert REGIME_GAMMA_TOP_V94.get('BULL_LOW_VOL', 32.00) <= 32.00
        assert math.isclose(REGIME_GAMMA_TOP_V94['BULL_LOW_VOL'], 32.00, rel_tol=1e-5)

    def test_feature_f440_rank_modulation_aliases(self):
        """Verify all aliases of 119th-order rank modulation produce identical results."""
        ranks = np.array([0.1, 0.8])
        ref = compute_phase94_hyperconvex_rank_modulation(ranks)
        assert np.allclose(compute_phase94_rank_warping(ranks), ref)
        assert np.allclose(compute_phase94_rank_modulation(ranks), ref)
        assert np.allclose(phase94_rank_modulation(ranks), ref)
        assert np.allclose(phase94_hyperconvex_rank_modulation(ranks), ref)
        assert np.allclose(apply_hyper_convex_rank_modulation_v94(ranks), ref)
        assert Phase94FactorSuppressionEngine is not None
        assert np.allclose(Phase94FactorSuppressionEngine.compute_phase94_hyperconvex_rank_modulation(ranks), ref)
        assert RegimeFactorSuppressionEngine is not None
        assert np.allclose(RegimeFactorSuppressionEngine.compute_phase94_hyperconvex_rank_modulation(ranks), ref)
