"""
tests/test_phase99_alpha.py

Unit test suite for Phase 99 Quantitative Alpha Enhancement (Features F465, F466):
- Feature F465: Sexcentennial (600th-Order) Hyperbolic Deadband
  (alpha_pos = 600.0, delta_noise = 0.035, noise suppression < 10^-600 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F465: 129th-Order Hyper-Convex Rank Modulation
  (g_v99(r) = 0.50 + 3.82 * r * exp(gamma_top * r^129) with REGIME_GAMMA_TOP_V99,
   gamma_top <= 37.00, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F466: Quantum Geometric Langlands Monster Whittaker Coupler Phase 99
  (defaults to version=99, kappa_monster_whit=41.60, lambda_monster=1.0 - 1e-23 [23-nines],
   is_phase99=True, harmony_boost=10.95,
   210th-order chiral oper obstruction, 122nd-order topological defect invariant,
   output keys FERI_v99, feri_v99, f_out_99, FERI_v98, feri_v98, f_out_98, etc.).
- Full alias trees for deadband, rank modulation, and coupler across classes and module level.
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import math
import numpy as np
import pandas as pd
import pytest

try:
    from trading_system.src.ai.factor_suppression import (
        apply_sexcentennial_hyperbolic_deadband,
        apply_sexcentagonal_hyperbolic_deadband,
        apply_hexacosagonal_hyperbolic_deadband,
        apply_hexacosia_hyperbolic_deadband,
        apply_sexcentennial_deadband,
        apply_sexcentagonal_deadband,
        apply_hexacosagonal_deadband,
        sexcentennial_deadband,
        sexcentagonal_deadband,
        hexacosagonal_deadband,
        sexcentennial_hyperbolic_deadband,
        sexcentagonal_hyperbolic_deadband,
        hexacosagonal_hyperbolic_deadband,
        compute_phase99_deadband,
        apply_phase99_deadband,
        phase99_deadband,
        apply_600th_order_hyperbolic_deadband,
        apply_600th_deadband,
        apply_600_deadband,
        apply_hyperbolic_deadband_v99,
        suppress_factor_noise_hyperbolic_v99,
        apply_sexcentennial_hyperbolic_deadband_v99,
        apply_hexacosiahedral_hyperbolic_deadband,
        apply_sexcentennial_dihedral_hyperbolic_deadband,
        apply_sexcentennial_suppression,
        compute_phase99_hyperconvex_rank_modulation,
        compute_129th_order_hyperconvex_rank_modulation,
        compute_phase99_rank_warping,
        compute_phase99_rank_modulation,
        phase99_rank_modulation,
        phase99_hyperconvex_rank_modulation,
        apply_phase99_rank_modulation,
        apply_hyper_convex_rank_modulation_v99,
        apply_129th_order_hyper_convex_rank_modulation,
        REGIME_GAMMA_TOP_V99,
        get_regime_adaptive_gamma_top_v99,
        get_regime_adaptive_gamma_top_phase99,
        get_gamma_top_v99,
        regime_adaptive_gamma_top_v99,
        get_phase99_gamma_top,
        phase99_gamma_top,
        get_gamma_top_phase99,
        adaptive_gamma_top_v99,
        Phase99FactorSuppressionEngine,
        RegimeFactorSuppressionEngine,
    )
except ImportError:
    import trading_system.src.ai.factor_suppression as _fs

    def _missing_fs(name):
        val = getattr(_fs, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'factor_suppression' has no Phase 99 attribute '{name}'")
        return _callable

    apply_sexcentennial_hyperbolic_deadband = _missing_fs('apply_sexcentennial_hyperbolic_deadband')
    apply_sexcentagonal_hyperbolic_deadband = _missing_fs('apply_sexcentagonal_hyperbolic_deadband')
    apply_hexacosagonal_hyperbolic_deadband = _missing_fs('apply_hexacosagonal_hyperbolic_deadband')
    apply_hexacosia_hyperbolic_deadband = _missing_fs('apply_hexacosia_hyperbolic_deadband')
    apply_sexcentennial_deadband = _missing_fs('apply_sexcentennial_deadband')
    apply_sexcentagonal_deadband = _missing_fs('apply_sexcentagonal_deadband')
    apply_hexacosagonal_deadband = _missing_fs('apply_hexacosagonal_deadband')
    sexcentennial_deadband = _missing_fs('sexcentennial_deadband')
    sexcentagonal_deadband = _missing_fs('sexcentagonal_deadband')
    hexacosagonal_deadband = _missing_fs('hexacosagonal_deadband')
    sexcentennial_hyperbolic_deadband = _missing_fs('sexcentennial_hyperbolic_deadband')
    sexcentagonal_hyperbolic_deadband = _missing_fs('sexcentagonal_hyperbolic_deadband')
    hexacosagonal_hyperbolic_deadband = _missing_fs('hexacosagonal_hyperbolic_deadband')
    compute_phase99_deadband = _missing_fs('compute_phase99_deadband')
    apply_phase99_deadband = _missing_fs('apply_phase99_deadband')
    phase99_deadband = _missing_fs('phase99_deadband')
    apply_600th_order_hyperbolic_deadband = _missing_fs('apply_600th_order_hyperbolic_deadband')
    apply_600th_deadband = _missing_fs('apply_600th_deadband')
    apply_600_deadband = _missing_fs('apply_600_deadband')
    apply_hyperbolic_deadband_v99 = _missing_fs('apply_hyperbolic_deadband_v99')
    suppress_factor_noise_hyperbolic_v99 = _missing_fs('suppress_factor_noise_hyperbolic_v99')
    apply_sexcentennial_hyperbolic_deadband_v99 = _missing_fs('apply_sexcentennial_hyperbolic_deadband_v99')
    apply_hexacosiahedral_hyperbolic_deadband = _missing_fs('apply_hexacosiahedral_hyperbolic_deadband')
    apply_sexcentennial_dihedral_hyperbolic_deadband = _missing_fs('apply_sexcentennial_dihedral_hyperbolic_deadband')
    apply_sexcentennial_suppression = _missing_fs('apply_sexcentennial_suppression')
    compute_phase99_hyperconvex_rank_modulation = _missing_fs('compute_phase99_hyperconvex_rank_modulation')
    compute_129th_order_hyperconvex_rank_modulation = _missing_fs('compute_129th_order_hyperconvex_rank_modulation')
    compute_phase99_rank_warping = _missing_fs('compute_phase99_rank_warping')
    compute_phase99_rank_modulation = _missing_fs('compute_phase99_rank_modulation')
    phase99_rank_modulation = _missing_fs('phase99_rank_modulation')
    phase99_hyperconvex_rank_modulation = _missing_fs('phase99_hyperconvex_rank_modulation')
    apply_phase99_rank_modulation = _missing_fs('apply_phase99_rank_modulation')
    apply_hyper_convex_rank_modulation_v99 = _missing_fs('apply_hyper_convex_rank_modulation_v99')
    apply_129th_order_hyper_convex_rank_modulation = _missing_fs('apply_129th_order_hyper_convex_rank_modulation')
    REGIME_GAMMA_TOP_V99 = getattr(_fs, 'REGIME_GAMMA_TOP_V99', {})
    get_regime_adaptive_gamma_top_v99 = _missing_fs('get_regime_adaptive_gamma_top_v99')
    get_regime_adaptive_gamma_top_phase99 = _missing_fs('get_regime_adaptive_gamma_top_phase99')
    get_gamma_top_v99 = _missing_fs('get_gamma_top_v99')
    regime_adaptive_gamma_top_v99 = _missing_fs('regime_adaptive_gamma_top_v99')
    get_phase99_gamma_top = _missing_fs('get_phase99_gamma_top')
    phase99_gamma_top = _missing_fs('phase99_gamma_top')
    get_gamma_top_phase99 = _missing_fs('get_gamma_top_phase99')
    adaptive_gamma_top_v99 = _missing_fs('adaptive_gamma_top_v99')
    Phase99FactorSuppressionEngine = getattr(_fs, 'Phase99FactorSuppressionEngine', None)
    RegimeFactorSuppressionEngine = getattr(_fs, 'RegimeFactorSuppressionEngine', None)

from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    EnsembleScoringEngine,
)

try:
    from trading_system.src.ai.ensemble_scorer import (
        Phase99Coupler,
        Phase99WhittakerDrinfeldCoupler,
        Phase99BorcherdsMoonshineCoupler,
        Phase99MonsterWhittakerCoupler,
        compute_phase99_coupling,
    )
except ImportError:
    import trading_system.src.ai.ensemble_scorer as _es
    def _missing_es(name):
        val = getattr(_es, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'ensemble_scorer' has no Phase 99 attribute '{name}'")
        return _callable
    Phase99Coupler = getattr(_es, 'Phase99Coupler', None)
    Phase99WhittakerDrinfeldCoupler = getattr(_es, 'Phase99WhittakerDrinfeldCoupler', None)
    Phase99BorcherdsMoonshineCoupler = getattr(_es, 'Phase99BorcherdsMoonshineCoupler', None)
    Phase99MonsterWhittakerCoupler = getattr(_es, 'Phase99MonsterWhittakerCoupler', None)
    compute_phase99_coupling = _missing_es('compute_phase99_coupling')


class TestPhase99AlphaEnhancements:
    """Test suite for Phase 99 Alpha Signal Processing and Langlands Monster Whittaker Coupler."""

    def test_feature_f466_coupler_properties_v99(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert coupler.version == 99 or coupler.version >= 99
        assert getattr(coupler, "is_phase99", False) is True
        assert getattr(coupler, "is_phase98", False) is True
        assert getattr(coupler, "is_phase97", False) is True
        assert getattr(coupler, "is_phase96", False) is True
        assert getattr(coupler, "is_phase95", False) is True
        assert getattr(coupler, "is_phase94", False) is True
        assert getattr(coupler, "is_phase93", False) is True
        assert getattr(coupler, "is_phase92", False) is True
        assert math.isclose(coupler.kappa_monster_whit, 41.60, abs_tol=1e-5)
        assert coupler.lambda_monster >= 0.99999999999999999999999
        assert math.isclose(coupler.harmony_boost, 10.95, abs_tol=1e-5)

        # Test forward coupling
        df = pd.DataFrame({
            "p1": [0.10, 0.20, -0.15],
            "p2": [0.12, 0.18, -0.14],
            "p3": [0.11, 0.22, -0.16],
            "p4": [0.09, 0.19, -0.13]
        }, index=["A", "B", "C"])
        res = coupler.couple_signals(df)
        assert isinstance(res, dict)
        assert "FERI_v99" in res or "feri_v99" in res or "f_out_99" in res
        assert "FERI_v98" in res or "feri_v98" in res or "f_out_98" in res
        assert "FERI_v97" in res or "feri_v97" in res or "f_out_97" in res
        assert "FERI_v96" in res or "feri_v96" in res or "f_out_96" in res
        assert "FERI_v95" in res or "feri_v95" in res or "f_out_95" in res
        assert "FERI_v94" in res or "feri_v94" in res or "f_out_94" in res
        assert "FERI_v93" in res or "feri_v93" in res or "f_out_93" in res

    def test_feature_f466_coupler_aliases(self):
        assert Phase99Coupler is not None
        assert Phase99WhittakerDrinfeldCoupler is not None
        assert Phase99BorcherdsMoonshineCoupler is not None
        assert Phase99MonsterWhittakerCoupler is not None
        coupler = Phase99Coupler()
        assert coupler.version >= 99
        assert coupler.is_phase99 is True

    def test_feature_f465_deadband_suppression(self):
        # Micro noise |z| <= 0.0003 must be suppressed to < 1e-600 (float64 0.0)
        micro_noise = np.array([-0.0003, -0.0001, 0.0, 0.0001, 0.0003])
        denoised = apply_sexcentennial_hyperbolic_deadband(micro_noise)
        for val in denoised:
            assert abs(val) < 1e-15 or val == 0.0

        # Conviction signal |z| >= 0.150 preserved with high fidelity
        conviction = np.array([0.150, 0.300, 0.500])
        denoised_conv = apply_sexcentennial_hyperbolic_deadband(conviction)
        for orig, d in zip(conviction, denoised_conv):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test
        grid = np.linspace(-1.0, 1.0, 1000)
        out = apply_sexcentennial_hyperbolic_deadband(grid)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12)

    def test_feature_f465_deadband_aliases(self):
        aliases = [
            apply_sexcentennial_hyperbolic_deadband,
            apply_sexcentagonal_hyperbolic_deadband,
            apply_hexacosagonal_hyperbolic_deadband,
            apply_hexacosia_hyperbolic_deadband,
            apply_sexcentennial_deadband,
            apply_sexcentagonal_deadband,
            apply_hexacosagonal_deadband,
            sexcentennial_deadband,
            sexcentagonal_deadband,
            hexacosagonal_deadband,
            sexcentennial_hyperbolic_deadband,
            sexcentagonal_hyperbolic_deadband,
            hexacosagonal_hyperbolic_deadband,
            compute_phase99_deadband,
            apply_phase99_deadband,
            phase99_deadband,
            apply_600th_order_hyperbolic_deadband,
            apply_600th_deadband,
            apply_600_deadband,
            apply_hyperbolic_deadband_v99,
            suppress_factor_noise_hyperbolic_v99,
            apply_sexcentennial_hyperbolic_deadband_v99,
            apply_hexacosiahedral_hyperbolic_deadband,
            apply_sexcentennial_dihedral_hyperbolic_deadband,
            apply_sexcentennial_suppression,
        ]
        test_val = np.array([0.05, 0.10, -0.05])
        base_res = aliases[0](test_val)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_val)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

        assert Phase99FactorSuppressionEngine is not None

    def test_feature_f465_rank_modulation(self):
        # Ranks in [0, 1]
        ranks = np.linspace(0.0, 1.0, 100)
        modulated = compute_phase99_hyperconvex_rank_modulation(ranks, gamma_top=37.00)
        assert len(modulated) == len(ranks)
        # Check strict monotonicity non-decreasing
        assert np.all(np.diff(modulated) >= -1e-12)
        # Check top decile exponential warping: g(1.0) must be massive (> 1e7)
        assert modulated[-1] > 1e7

        # Negative branch test: g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.2] * len(ranks))
        mod_neg = compute_phase99_hyperconvex_rank_modulation(ranks, z_denoised=z_neg)
        assert np.all(np.diff(mod_neg) <= 1e-12)  # decreasing for higher rank

    def test_feature_f465_rank_modulation_regimes(self):
        assert "BULL_LOW_VOL" in REGIME_GAMMA_TOP_V99
        assert REGIME_GAMMA_TOP_V99["BULL_LOW_VOL"] >= 37.00
        gamma_bull = get_regime_adaptive_gamma_top_v99("BULL_LOW_VOL")
        assert gamma_bull >= 37.00
        gamma_crisis = get_regime_adaptive_gamma_top_v99("CRISIS")
        assert gamma_crisis < gamma_bull

    def test_feature_f465_rank_modulation_aliases(self):
        aliases = [
            compute_phase99_hyperconvex_rank_modulation,
            compute_129th_order_hyperconvex_rank_modulation,
            compute_phase99_rank_warping,
            compute_phase99_rank_modulation,
            phase99_rank_modulation,
            phase99_hyperconvex_rank_modulation,
            apply_phase99_rank_modulation,
            apply_hyper_convex_rank_modulation_v99,
            apply_129th_order_hyper_convex_rank_modulation,
        ]
        test_ranks = np.array([0.2, 0.5, 0.8, 0.95])
        base_res = aliases[0](test_ranks, gamma_top=25.0)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_ranks, gamma_top=25.0)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

    def test_ensemble_scoring_engine_integration(self):
        engine = EnsembleScoringEngine()
        assert hasattr(engine, "Phase99Coupler")
        assert hasattr(engine, "compute_phase99_coupling")
        assert hasattr(engine, "apply_sexcentennial_hyperbolic_deadband")
        assert hasattr(engine, "compute_phase99_hyperconvex_rank_modulation")
        res_deadband = EnsembleScoringEngine.apply_smooth_noise_deadband(0.0001, version=99)
        assert abs(res_deadband) < 1e-12
