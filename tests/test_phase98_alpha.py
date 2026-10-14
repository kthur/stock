"""
tests/test_phase98_alpha.py

Unit test suite for Phase 98 Quantitative Alpha Enhancement (Features F460, F461):
- Feature F460: Asymmetric Enneacontadigonal (592th-Order) Hyperbolic Deadband
  (alpha_pos = 592.0, delta_noise = 0.035, noise suppression < 10^-592 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F460: 127th-Order Hyperconvex Rank Modulation
  (g_v98(r) = 0.50 + 3.78 * r * exp(gamma_top * r^127) with REGIME_GAMMA_TOP_V98,
   gamma_top <= 36.00, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F461: Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds Moonshine Monster Whittaker Coupler v98
  (defaults to version=98, kappa_monster_whit=41.00, lambda_monster=0.9999999999999999999995 [22-nines: 21 nines + 5],
   is_phase98=True, harmony_boost=10.60,
   208th-order chiral oper obstruction, 120th-order topological defect invariant,
   output keys FERI_v98, feri_v98, f_out_98, FERI_v97, feri_v97, f_out_97, etc.).
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
        apply_enneacontadigonal_hyperbolic_deadband,
        apply_nonacontadigonal_hyperbolic_deadband,
        apply_quingentaenneacontadigonal_hyperbolic_deadband,
        apply_pentacontaenneacontadigonal_hyperbolic_deadband,
        apply_quingentanonacontadigonal_hyperbolic_deadband,
        apply_pentacontanonacontadigonal_hyperbolic_deadband,
        apply_enneacontadihedral_hyperbolic_deadband,
        apply_nonacontadihedral_hyperbolic_deadband,
        apply_enneacontaduohedral_hyperbolic_deadband,
        apply_nonaconta_hyperbolic_deadband,
        apply_enneaconta_hyperbolic_deadband,
        apply_enneacontadigonal_deadband,
        apply_nonacontadigonal_deadband,
        enneacontadigonal_deadband,
        nonacontadigonal_deadband,
        enneacontadigonal_hyperbolic_deadband,
        nonacontadigonal_hyperbolic_deadband,
        compute_phase98_deadband,
        apply_phase98_deadband,
        phase98_deadband,
        apply_592th_order_hyperbolic_deadband,
        apply_592th_deadband,
        apply_592_deadband,
        apply_hyperbolic_deadband_v98,
        suppress_factor_noise_hyperbolic_v98,
        apply_quingentaenneacontadigonal_hyperbolic_deadband_v98,
        compute_phase98_hyperconvex_rank_modulation,
        compute_127th_order_hyperconvex_rank_modulation,
        compute_phase98_rank_warping,
        compute_phase98_rank_modulation,
        phase98_rank_modulation,
        phase98_hyperconvex_rank_modulation,
        apply_phase98_rank_modulation,
        apply_hyper_convex_rank_modulation_v98,
        REGIME_GAMMA_TOP_V98,
        get_regime_adaptive_gamma_top_v98,
        Phase98FactorSuppressionEngine,
        RegimeFactorSuppressionEngine,
    )
except ImportError:
    import trading_system.src.ai.factor_suppression as _fs

    def _missing_fs(name):
        val = getattr(_fs, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'factor_suppression' has no Phase 98 attribute '{name}'")
        return _callable

    apply_enneacontadigonal_hyperbolic_deadband = _missing_fs('apply_enneacontadigonal_hyperbolic_deadband')
    apply_nonacontadigonal_hyperbolic_deadband = _missing_fs('apply_nonacontadigonal_hyperbolic_deadband')
    apply_quingentaenneacontadigonal_hyperbolic_deadband = _missing_fs('apply_quingentaenneacontadigonal_hyperbolic_deadband')
    apply_pentacontaenneacontadigonal_hyperbolic_deadband = _missing_fs('apply_pentacontaenneacontadigonal_hyperbolic_deadband')
    apply_quingentanonacontadigonal_hyperbolic_deadband = _missing_fs('apply_quingentanonacontadigonal_hyperbolic_deadband')
    apply_pentacontanonacontadigonal_hyperbolic_deadband = _missing_fs('apply_pentacontanonacontadigonal_hyperbolic_deadband')
    apply_enneacontadihedral_hyperbolic_deadband = _missing_fs('apply_enneacontadihedral_hyperbolic_deadband')
    apply_nonacontadihedral_hyperbolic_deadband = _missing_fs('apply_nonacontadihedral_hyperbolic_deadband')
    apply_enneacontaduohedral_hyperbolic_deadband = _missing_fs('apply_enneacontaduohedral_hyperbolic_deadband')
    apply_nonaconta_hyperbolic_deadband = _missing_fs('apply_nonaconta_hyperbolic_deadband')
    apply_enneaconta_hyperbolic_deadband = _missing_fs('apply_enneaconta_hyperbolic_deadband')
    apply_enneacontadigonal_deadband = _missing_fs('apply_enneacontadigonal_deadband')
    apply_nonacontadigonal_deadband = _missing_fs('apply_nonacontadigonal_deadband')
    enneacontadigonal_deadband = _missing_fs('enneacontadigonal_deadband')
    nonacontadigonal_deadband = _missing_fs('nonacontadigonal_deadband')
    enneacontadigonal_hyperbolic_deadband = _missing_fs('enneacontadigonal_hyperbolic_deadband')
    nonacontadigonal_hyperbolic_deadband = _missing_fs('nonacontadigonal_hyperbolic_deadband')
    compute_phase98_deadband = _missing_fs('compute_phase98_deadband')
    apply_phase98_deadband = _missing_fs('apply_phase98_deadband')
    phase98_deadband = _missing_fs('phase98_deadband')
    apply_592th_order_hyperbolic_deadband = _missing_fs('apply_592th_order_hyperbolic_deadband')
    apply_592th_deadband = _missing_fs('apply_592th_deadband')
    apply_592_deadband = _missing_fs('apply_592_deadband')
    apply_hyperbolic_deadband_v98 = _missing_fs('apply_hyperbolic_deadband_v98')
    suppress_factor_noise_hyperbolic_v98 = _missing_fs('suppress_factor_noise_hyperbolic_v98')
    apply_quingentaenneacontadigonal_hyperbolic_deadband_v98 = _missing_fs('apply_quingentaenneacontadigonal_hyperbolic_deadband_v98')
    compute_phase98_hyperconvex_rank_modulation = _missing_fs('compute_phase98_hyperconvex_rank_modulation')
    compute_127th_order_hyperconvex_rank_modulation = _missing_fs('compute_127th_order_hyperconvex_rank_modulation')
    compute_phase98_rank_warping = _missing_fs('compute_phase98_rank_warping')
    compute_phase98_rank_modulation = _missing_fs('compute_phase98_rank_modulation')
    phase98_rank_modulation = _missing_fs('phase98_rank_modulation')
    phase98_hyperconvex_rank_modulation = _missing_fs('phase98_hyperconvex_rank_modulation')
    apply_phase98_rank_modulation = _missing_fs('apply_phase98_rank_modulation')
    apply_hyper_convex_rank_modulation_v98 = _missing_fs('apply_hyper_convex_rank_modulation_v98')
    REGIME_GAMMA_TOP_V98 = getattr(_fs, 'REGIME_GAMMA_TOP_V98', {})
    get_regime_adaptive_gamma_top_v98 = _missing_fs('get_regime_adaptive_gamma_top_v98')
    Phase98FactorSuppressionEngine = getattr(_fs, 'Phase98FactorSuppressionEngine', None)
    RegimeFactorSuppressionEngine = getattr(_fs, 'RegimeFactorSuppressionEngine', None)

from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    EnsembleScoringEngine,
)

try:
    from trading_system.src.ai.ensemble_scorer import (
        Phase98Coupler,
        Phase98WhittakerDrinfeldCoupler,
        Phase98BorcherdsMoonshineCoupler,
        Phase98MonsterWhittakerCoupler,
        compute_phase98_coupling,
    )
except ImportError:
    import trading_system.src.ai.ensemble_scorer as _es
    def _missing_es(name):
        val = getattr(_es, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'ensemble_scorer' has no Phase 98 attribute '{name}'")
        return _callable
    Phase98Coupler = getattr(_es, 'Phase98Coupler', None)
    Phase98WhittakerDrinfeldCoupler = getattr(_es, 'Phase98WhittakerDrinfeldCoupler', None)
    Phase98BorcherdsMoonshineCoupler = getattr(_es, 'Phase98BorcherdsMoonshineCoupler', None)
    Phase98MonsterWhittakerCoupler = getattr(_es, 'Phase98MonsterWhittakerCoupler', None)
    compute_phase98_coupling = _missing_es('compute_phase98_coupling')


class TestPhase98AlphaEnhancements:
    """Test suite for Phase 98 Alpha Signal Processing and Langlands Monster Whittaker Coupler."""

    def test_feature_f461_coupler_properties_v98(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert coupler.version == 98 or coupler.version >= 98
        assert getattr(coupler, "is_phase98", False) is True
        assert getattr(coupler, "is_phase97", False) is True
        assert getattr(coupler, "is_phase96", False) is True
        assert getattr(coupler, "is_phase95", False) is True
        assert getattr(coupler, "is_phase94", False) is True
        assert getattr(coupler, "is_phase93", False) is True
        assert getattr(coupler, "is_phase92", False) is True
        assert math.isclose(coupler.kappa_monster_whit, 41.00, abs_tol=1e-5)
        assert coupler.lambda_monster >= 0.999999999999999999
        assert math.isclose(coupler.harmony_boost, 10.60, abs_tol=1e-5)

        # Test forward coupling
        df = pd.DataFrame({
            "p1": [0.10, 0.20, -0.15],
            "p2": [0.12, 0.18, -0.14],
            "p3": [0.11, 0.22, -0.16],
            "p4": [0.09, 0.19, -0.13]
        }, index=["A", "B", "C"])
        res = coupler.couple_signals(df)
        assert isinstance(res, dict)
        assert "FERI_v98" in res or "feri_v98" in res or "f_out_98" in res
        assert "FERI_v97" in res or "feri_v97" in res or "f_out_97" in res
        assert "FERI_v96" in res or "feri_v96" in res or "f_out_96" in res
        assert "FERI_v95" in res or "feri_v95" in res or "f_out_95" in res
        assert "FERI_v94" in res or "feri_v94" in res or "f_out_94" in res
        assert "FERI_v93" in res or "feri_v93" in res or "f_out_93" in res

    def test_feature_f461_coupler_aliases(self):
        assert Phase98Coupler is not None
        assert Phase98WhittakerDrinfeldCoupler is not None
        assert Phase98BorcherdsMoonshineCoupler is not None
        assert Phase98MonsterWhittakerCoupler is not None
        coupler = Phase98Coupler()
        assert coupler.version >= 98
        assert coupler.is_phase98 is True

    def test_feature_f460_deadband_suppression(self):
        # Micro noise |z| <= 0.0003 must be suppressed to < 1e-592 (float64 0.0)
        micro_noise = np.array([-0.0003, -0.0001, 0.0, 0.0001, 0.0003])
        denoised = apply_enneacontadigonal_hyperbolic_deadband(micro_noise)
        for val in denoised:
            assert abs(val) < 1e-15 or val == 0.0

        # Conviction signal |z| >= 0.150 preserved with high fidelity
        conviction = np.array([0.150, 0.300, 0.500])
        denoised_conv = apply_enneacontadigonal_hyperbolic_deadband(conviction)
        for orig, d in zip(conviction, denoised_conv):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test
        grid = np.linspace(-1.0, 1.0, 1000)
        out = apply_enneacontadigonal_hyperbolic_deadband(grid)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12)

    def test_feature_f460_deadband_aliases(self):
        aliases = [
            apply_enneacontadigonal_hyperbolic_deadband,
            apply_nonacontadigonal_hyperbolic_deadband,
            apply_quingentaenneacontadigonal_hyperbolic_deadband,
            apply_pentacontaenneacontadigonal_hyperbolic_deadband,
            apply_quingentanonacontadigonal_hyperbolic_deadband,
            apply_pentacontanonacontadigonal_hyperbolic_deadband,
            apply_enneacontadihedral_hyperbolic_deadband,
            apply_nonacontadihedral_hyperbolic_deadband,
            apply_enneacontaduohedral_hyperbolic_deadband,
            apply_nonaconta_hyperbolic_deadband,
            apply_enneaconta_hyperbolic_deadband,
            apply_enneacontadigonal_deadband,
            apply_nonacontadigonal_deadband,
            enneacontadigonal_deadband,
            nonacontadigonal_deadband,
            enneacontadigonal_hyperbolic_deadband,
            nonacontadigonal_hyperbolic_deadband,
            compute_phase98_deadband,
            apply_phase98_deadband,
            phase98_deadband,
            apply_592th_order_hyperbolic_deadband,
            apply_592th_deadband,
            apply_592_deadband,
            apply_hyperbolic_deadband_v98,
            suppress_factor_noise_hyperbolic_v98,
            apply_quingentaenneacontadigonal_hyperbolic_deadband_v98,
        ]
        test_val = np.array([0.05, 0.10, -0.05])
        base_res = aliases[0](test_val)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_val)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

        assert Phase98FactorSuppressionEngine is not None

    def test_feature_f460_rank_modulation(self):
        # Ranks in [0, 1]
        ranks = np.linspace(0.0, 1.0, 100)
        modulated = compute_phase98_hyperconvex_rank_modulation(ranks, gamma_top=36.00)
        assert len(modulated) == len(ranks)
        # Check strict monotonicity non-decreasing
        assert np.all(np.diff(modulated) >= -1e-12)
        # Check top decile exponential warping: g(1.0) must be massive (> 1e7)
        assert modulated[-1] > 1e7

        # Negative branch test: g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.2] * len(ranks))
        mod_neg = compute_phase98_hyperconvex_rank_modulation(ranks, z_denoised=z_neg)
        assert np.all(np.diff(mod_neg) <= 1e-12)  # decreasing for higher rank

    def test_feature_f460_rank_modulation_regimes(self):
        assert "BULL_LOW_VOL" in REGIME_GAMMA_TOP_V98
        assert REGIME_GAMMA_TOP_V98["BULL_LOW_VOL"] >= 36.00
        gamma_bull = get_regime_adaptive_gamma_top_v98("BULL_LOW_VOL")
        assert gamma_bull >= 36.00
        gamma_crisis = get_regime_adaptive_gamma_top_v98("CRISIS")
        assert gamma_crisis < gamma_bull

    def test_feature_f460_rank_modulation_aliases(self):
        aliases = [
            compute_phase98_hyperconvex_rank_modulation,
            compute_127th_order_hyperconvex_rank_modulation,
            compute_phase98_rank_warping,
            compute_phase98_rank_modulation,
            phase98_rank_modulation,
            phase98_hyperconvex_rank_modulation,
            apply_phase98_rank_modulation,
            apply_hyper_convex_rank_modulation_v98,
        ]
        test_ranks = np.array([0.2, 0.5, 0.8, 0.95])
        base_res = aliases[0](test_ranks, gamma_top=25.0)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_ranks, gamma_top=25.0)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

    def test_ensemble_scoring_engine_integration(self):
        engine = EnsembleScoringEngine()
        assert hasattr(engine, "Phase98Coupler")
        assert hasattr(engine, "compute_phase98_coupling")
        assert hasattr(engine, "apply_enneacontadigonal_hyperbolic_deadband")
        assert hasattr(engine, "compute_phase98_hyperconvex_rank_modulation")
        res_deadband = EnsembleScoringEngine.apply_smooth_noise_deadband(0.0001, version=98)
        assert abs(res_deadband) < 1e-12
