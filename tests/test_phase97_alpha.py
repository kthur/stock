"""
tests/test_phase97_alpha.py

Unit test suite for Phase 97 Quantitative Alpha Enhancement (Features F455, F456):
- Feature F455: Asymmetric Octacontahexagonal (584th-Order) Hyperbolic Deadband
  (alpha_pos = 584.0, delta_noise = 0.035, noise suppression < 10^-584 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F455: 125th-Order Hyperconvex Rank Modulation
  (g_v97(r) = 0.50 + 3.74 * r * exp(gamma_top * r^125) with REGIME_GAMMA_TOP_V97,
   gamma_top <= 35.00, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F456: Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds Moonshine Monster Whittaker Coupler v97
  (defaults to version=97, kappa_monster_whit=40.40, lambda_monster=0.99999999999999999995 [21-nines: 20 nines + 5],
   is_phase97=True, harmony_boost=10.25,
   206th-order chiral oper obstruction, 118th-order topological defect invariant,
   output keys FERI_v97, feri_v97, f_out_97, FERI_v96, feri_v96, f_out_96, etc.).
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
        apply_octacontahexagonal_hyperbolic_deadband,
        apply_quingentaoctacontatetragonal_hyperbolic_deadband,
        apply_pentacontaoctacontatetragonal_hyperbolic_deadband,
        apply_octacontahexa_hyperbolic_deadband,
        apply_octacontahexagonal_deadband,
        apply_octacontatetragonal_deadband,
        octacontahexagonal_deadband,
        octacontatetragonal_deadband,
        octacontahexagonal_hyperbolic_deadband,
        octacontatetragonal_hyperbolic_deadband,
        compute_phase97_deadband,
        apply_phase97_deadband,
        phase97_deadband,
        apply_584th_order_hyperbolic_deadband,
        apply_584th_deadband,
        apply_584_deadband,
        apply_hyperbolic_deadband_v97,
        suppress_factor_noise_hyperbolic_v97,
        apply_quingentaoctacontahexagonal_hyperbolic_deadband_v97,
        compute_phase97_hyperconvex_rank_modulation,
        compute_125th_order_hyperconvex_rank_modulation,
        compute_phase97_rank_warping,
        compute_phase97_rank_modulation,
        phase97_rank_modulation,
        phase97_hyperconvex_rank_modulation,
        apply_phase97_rank_modulation,
        apply_hyper_convex_rank_modulation_v97,
        REGIME_GAMMA_TOP_V97,
        get_regime_adaptive_gamma_top_v97,
        Phase97FactorSuppressionEngine,
        RegimeFactorSuppressionEngine,
    )
except ImportError:
    import trading_system.src.ai.factor_suppression as _fs

    def _missing_fs(name):
        val = getattr(_fs, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'factor_suppression' has no Phase 97 attribute '{name}'")
        return _callable

    apply_octacontahexagonal_hyperbolic_deadband = _missing_fs('apply_octacontahexagonal_hyperbolic_deadband')
    apply_quingentaoctacontatetragonal_hyperbolic_deadband = _missing_fs('apply_quingentaoctacontatetragonal_hyperbolic_deadband')
    apply_pentacontaoctacontatetragonal_hyperbolic_deadband = _missing_fs('apply_pentacontaoctacontatetragonal_hyperbolic_deadband')
    apply_octacontatetragonal_hyperbolic_deadband = _missing_fs('apply_octacontatetragonal_hyperbolic_deadband')
    apply_octacontahexa_hyperbolic_deadband = _missing_fs('apply_octacontahexa_hyperbolic_deadband')
    apply_octacontahexagonal_deadband = _missing_fs('apply_octacontahexagonal_deadband')
    apply_octacontatetragonal_deadband = _missing_fs('apply_octacontatetragonal_deadband')
    octacontahexagonal_deadband = _missing_fs('octacontahexagonal_deadband')
    octacontatetragonal_deadband = _missing_fs('octacontatetragonal_deadband')
    octacontahexagonal_hyperbolic_deadband = _missing_fs('octacontahexagonal_hyperbolic_deadband')
    octacontatetragonal_hyperbolic_deadband = _missing_fs('octacontatetragonal_hyperbolic_deadband')
    compute_phase97_deadband = _missing_fs('compute_phase97_deadband')
    apply_phase97_deadband = _missing_fs('apply_phase97_deadband')
    phase97_deadband = _missing_fs('phase97_deadband')
    apply_584th_order_hyperbolic_deadband = _missing_fs('apply_584th_order_hyperbolic_deadband')
    apply_584th_deadband = _missing_fs('apply_584th_deadband')
    apply_584_deadband = _missing_fs('apply_584_deadband')
    apply_hyperbolic_deadband_v97 = _missing_fs('apply_hyperbolic_deadband_v97')
    suppress_factor_noise_hyperbolic_v97 = _missing_fs('suppress_factor_noise_hyperbolic_v97')
    apply_quingentaoctacontahexagonal_hyperbolic_deadband_v97 = _missing_fs('apply_quingentaoctacontahexagonal_hyperbolic_deadband_v97')
    compute_phase97_hyperconvex_rank_modulation = _missing_fs('compute_phase97_hyperconvex_rank_modulation')
    compute_125th_order_hyperconvex_rank_modulation = _missing_fs('compute_125th_order_hyperconvex_rank_modulation')
    compute_phase97_rank_warping = _missing_fs('compute_phase97_rank_warping')
    compute_phase97_rank_modulation = _missing_fs('compute_phase97_rank_modulation')
    phase97_rank_modulation = _missing_fs('phase97_rank_modulation')
    phase97_hyperconvex_rank_modulation = _missing_fs('phase97_hyperconvex_rank_modulation')
    apply_phase97_rank_modulation = _missing_fs('apply_phase97_rank_modulation')
    apply_hyper_convex_rank_modulation_v97 = _missing_fs('apply_hyper_convex_rank_modulation_v97')
    REGIME_GAMMA_TOP_V97 = getattr(_fs, 'REGIME_GAMMA_TOP_V97', {})
    get_regime_adaptive_gamma_top_v97 = _missing_fs('get_regime_adaptive_gamma_top_v97')
    Phase97FactorSuppressionEngine = getattr(_fs, 'Phase97FactorSuppressionEngine', None)
    RegimeFactorSuppressionEngine = getattr(_fs, 'RegimeFactorSuppressionEngine', None)

from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    EnsembleScoringEngine,
)

try:
    from trading_system.src.ai.ensemble_scorer import (
        Phase97Coupler,
        Phase97WhittakerDrinfeldCoupler,
        Phase97BorcherdsMoonshineCoupler,
        Phase97MonsterWhittakerCoupler,
        compute_phase97_coupling,
    )
except ImportError:
    import trading_system.src.ai.ensemble_scorer as _es
    def _missing_es(name):
        val = getattr(_es, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'ensemble_scorer' has no Phase 97 attribute '{name}'")
        return _callable
    Phase97Coupler = getattr(_es, 'Phase97Coupler', None)
    Phase97WhittakerDrinfeldCoupler = getattr(_es, 'Phase97WhittakerDrinfeldCoupler', None)
    Phase97BorcherdsMoonshineCoupler = getattr(_es, 'Phase97BorcherdsMoonshineCoupler', None)
    Phase97MonsterWhittakerCoupler = getattr(_es, 'Phase97MonsterWhittakerCoupler', None)
    compute_phase97_coupling = _missing_es('compute_phase97_coupling')


class TestPhase97AlphaEnhancements:
    """Test suite for Phase 97 Alpha Signal Processing and Langlands Monster Whittaker Coupler."""

    def test_feature_f456_coupler_properties_v97(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert coupler.version == 97 or coupler.version >= 97
        assert getattr(coupler, "is_phase97", False) is True
        assert getattr(coupler, "is_phase96", False) is True
        assert getattr(coupler, "is_phase95", False) is True
        assert getattr(coupler, "is_phase94", False) is True
        assert getattr(coupler, "is_phase93", False) is True
        assert getattr(coupler, "is_phase92", False) is True
        assert math.isclose(coupler.kappa_monster_whit, 40.40, abs_tol=1e-5)
        assert coupler.lambda_monster >= 0.999999999999999999
        assert math.isclose(coupler.harmony_boost, 10.25, abs_tol=1e-5)

        # Test forward coupling
        df = pd.DataFrame({
            "p1": [0.10, 0.20, -0.15],
            "p2": [0.12, 0.18, -0.14],
            "p3": [0.11, 0.22, -0.16],
            "p4": [0.09, 0.19, -0.13]
        }, index=["A", "B", "C"])
        res = coupler.couple_signals(df)
        assert isinstance(res, dict)
        assert "FERI_v97" in res or "feri_v97" in res or "f_out_97" in res
        assert "FERI_v96" in res or "feri_v96" in res or "f_out_96" in res
        assert "FERI_v95" in res or "feri_v95" in res or "f_out_95" in res
        assert "FERI_v94" in res or "feri_v94" in res or "f_out_94" in res
        assert "FERI_v93" in res or "feri_v93" in res or "f_out_93" in res

    def test_feature_f456_coupler_aliases(self):
        assert Phase97Coupler is not None
        assert Phase97WhittakerDrinfeldCoupler is not None
        assert Phase97BorcherdsMoonshineCoupler is not None
        assert Phase97MonsterWhittakerCoupler is not None
        coupler = Phase97Coupler()
        assert coupler.version >= 97
        assert coupler.is_phase97 is True

    def test_feature_f455_deadband_suppression(self):
        # Micro noise |z| <= 0.0003 must be suppressed to < 1e-584 (float64 0.0)
        micro_noise = np.array([-0.0003, -0.0001, 0.0, 0.0001, 0.0003])
        denoised = apply_octacontahexagonal_hyperbolic_deadband(micro_noise)
        for val in denoised:
            assert abs(val) < 1e-15 or val == 0.0

        # Conviction signal |z| >= 0.150 preserved with high fidelity
        conviction = np.array([0.150, 0.300, 0.500])
        denoised_conv = apply_octacontahexagonal_hyperbolic_deadband(conviction)
        for orig, d in zip(conviction, denoised_conv):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test
        grid = np.linspace(-1.0, 1.0, 1000)
        out = apply_octacontahexagonal_hyperbolic_deadband(grid)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12)

    def test_feature_f455_deadband_aliases(self):
        aliases = [
            apply_octacontahexagonal_hyperbolic_deadband,
            apply_quingentaoctacontatetragonal_hyperbolic_deadband,
            apply_pentacontaoctacontatetragonal_hyperbolic_deadband,
            apply_octacontahexa_hyperbolic_deadband,
            apply_octacontahexagonal_deadband,
            apply_octacontatetragonal_deadband,
            octacontahexagonal_deadband,
            octacontatetragonal_deadband,
            octacontahexagonal_hyperbolic_deadband,
            octacontatetragonal_hyperbolic_deadband,
            compute_phase97_deadband,
            apply_phase97_deadband,
            phase97_deadband,
            apply_584th_order_hyperbolic_deadband,
            apply_584th_deadband,
            apply_584_deadband,
            apply_hyperbolic_deadband_v97,
            suppress_factor_noise_hyperbolic_v97,
            apply_quingentaoctacontahexagonal_hyperbolic_deadband_v97,
        ]
        test_val = np.array([0.05, 0.10, -0.05])
        base_res = aliases[0](test_val)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_val)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

        assert Phase97FactorSuppressionEngine is not None

    def test_feature_f455_rank_modulation(self):
        # Ranks in [0, 1]
        ranks = np.linspace(0.0, 1.0, 100)
        modulated = compute_phase97_hyperconvex_rank_modulation(ranks, gamma_top=35.00)
        assert len(modulated) == len(ranks)
        # Check strict monotonicity non-decreasing
        assert np.all(np.diff(modulated) >= -1e-12)
        # Check top decile exponential warping: g(1.0) must be massive (> 1e7)
        assert modulated[-1] > 1e7

        # Negative branch test: g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.2] * len(ranks))
        mod_neg = compute_phase97_hyperconvex_rank_modulation(ranks, z_denoised=z_neg)
        assert np.all(np.diff(mod_neg) <= 1e-12)  # decreasing for higher rank

    def test_feature_f455_rank_modulation_regimes(self):
        assert "BULL_LOW_VOL" in REGIME_GAMMA_TOP_V97
        assert REGIME_GAMMA_TOP_V97["BULL_LOW_VOL"] >= 35.00
        gamma_bull = get_regime_adaptive_gamma_top_v97("BULL_LOW_VOL")
        assert gamma_bull >= 35.00
        gamma_crisis = get_regime_adaptive_gamma_top_v97("CRISIS")
        assert gamma_crisis < gamma_bull

    def test_feature_f455_rank_modulation_aliases(self):
        aliases = [
            compute_phase97_hyperconvex_rank_modulation,
            compute_125th_order_hyperconvex_rank_modulation,
            compute_phase97_rank_warping,
            compute_phase97_rank_modulation,
            phase97_rank_modulation,
            phase97_hyperconvex_rank_modulation,
            apply_phase97_rank_modulation,
            apply_hyper_convex_rank_modulation_v97,
        ]
        test_ranks = np.array([0.2, 0.5, 0.8, 0.95])
        base_res = aliases[0](test_ranks, gamma_top=25.0)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_ranks, gamma_top=25.0)
            np.testing.assert_allclose(base_res, res, atol=1e-12)
