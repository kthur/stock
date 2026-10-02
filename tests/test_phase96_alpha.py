"""
tests/test_phase96_alpha.py

Unit test suite for Phase 96 Quantitative Alpha Enhancement (Features F450, F451):
- Feature F450: Asymmetric Pentacontahexagonal (576th-Order) Hyperbolic Deadband
  (alpha_pos = 576.0, delta_noise = 0.035, noise suppression < 10^-576 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F450: 123rd-Order Hyperconvex Rank Modulation
  (g_v96(r) = 0.50 + 3.70 * r * exp(gamma_top * r^123) with REGIME_GAMMA_TOP_V96,
   gamma_top <= 34.00, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F451: Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds Moonshine Monster Whittaker Coupler v96
  (defaults to version=96, kappa_monster_whit=39.80, lambda_monster=0.9999999999999999995 [20-nines: 19 nines + 5],
   is_phase96=True, harmony_boost=9.90,
   204th-order chiral oper obstruction, 116th-order topological defect invariant,
   output keys FERI_v96, feri_v96, f_out_96, FERI_v95, feri_v95, f_out_95, etc.).
- Full alias trees for deadband, rank modulation, and coupler across classes and module level.
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
        apply_pentacontahexagonal_hyperbolic_deadband,
        apply_quingentaoctacontahexagonal_hyperbolic_deadband,
        apply_pentacontaoctacontahexagonal_hyperbolic_deadband,
        apply_pentacontahexa_hyperbolic_deadband,
        apply_pentacontahexagonal_deadband,
        pentacontahexagonal_deadband,
        pentacontahexagonal_hyperbolic_deadband,
        compute_phase96_deadband,
        apply_phase96_deadband,
        phase96_deadband,
        apply_576th_order_hyperbolic_deadband,
        apply_576th_deadband,
        apply_576_deadband,
        apply_hyperbolic_deadband_v96,
        suppress_factor_noise_hyperbolic_v96,
        compute_phase96_hyperconvex_rank_modulation,
        compute_123rd_order_hyperconvex_rank_modulation,
        compute_phase96_rank_warping,
        compute_phase96_rank_modulation,
        phase96_rank_modulation,
        phase96_hyperconvex_rank_modulation,
        apply_phase96_rank_modulation,
        apply_hyper_convex_rank_modulation_v96,
        REGIME_GAMMA_TOP_V96,
        get_regime_adaptive_gamma_top_v96,
        Phase96FactorSuppressionEngine,
        RegimeFactorSuppressionEngine,
    )
except ImportError:
    import trading_system.src.ai.factor_suppression as _fs

    def _missing_fs(name):
        val = getattr(_fs, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'factor_suppression' has no Phase 96 attribute '{name}'")
        return _callable

    apply_pentacontahexagonal_hyperbolic_deadband = _missing_fs('apply_pentacontahexagonal_hyperbolic_deadband')
    apply_quingentaoctacontahexagonal_hyperbolic_deadband = _missing_fs('apply_quingentaoctacontahexagonal_hyperbolic_deadband')
    apply_pentacontaoctacontahexagonal_hyperbolic_deadband = _missing_fs('apply_pentacontaoctacontahexagonal_hyperbolic_deadband')
    apply_pentacontahexa_hyperbolic_deadband = _missing_fs('apply_pentacontahexa_hyperbolic_deadband')
    apply_pentacontahexagonal_deadband = _missing_fs('apply_pentacontahexagonal_deadband')
    pentacontahexagonal_deadband = _missing_fs('pentacontahexagonal_deadband')
    pentacontahexagonal_hyperbolic_deadband = _missing_fs('pentacontahexagonal_hyperbolic_deadband')
    compute_phase96_deadband = _missing_fs('compute_phase96_deadband')
    apply_phase96_deadband = _missing_fs('apply_phase96_deadband')
    phase96_deadband = _missing_fs('phase96_deadband')
    apply_576th_order_hyperbolic_deadband = _missing_fs('apply_576th_order_hyperbolic_deadband')
    apply_576th_deadband = _missing_fs('apply_576th_deadband')
    apply_576_deadband = _missing_fs('apply_576_deadband')
    apply_hyperbolic_deadband_v96 = _missing_fs('apply_hyperbolic_deadband_v96')
    suppress_factor_noise_hyperbolic_v96 = _missing_fs('suppress_factor_noise_hyperbolic_v96')
    compute_phase96_hyperconvex_rank_modulation = _missing_fs('compute_phase96_hyperconvex_rank_modulation')
    compute_123rd_order_hyperconvex_rank_modulation = _missing_fs('compute_123rd_order_hyperconvex_rank_modulation')
    compute_phase96_rank_warping = _missing_fs('compute_phase96_rank_warping')
    compute_phase96_rank_modulation = _missing_fs('compute_phase96_rank_modulation')
    phase96_rank_modulation = _missing_fs('phase96_rank_modulation')
    phase96_hyperconvex_rank_modulation = _missing_fs('phase96_hyperconvex_rank_modulation')
    apply_phase96_rank_modulation = _missing_fs('apply_phase96_rank_modulation')
    apply_hyper_convex_rank_modulation_v96 = _missing_fs('apply_hyper_convex_rank_modulation_v96')
    REGIME_GAMMA_TOP_V96 = getattr(_fs, 'REGIME_GAMMA_TOP_V96', {})
    get_regime_adaptive_gamma_top_v96 = _missing_fs('get_regime_adaptive_gamma_top_v96')
    Phase96FactorSuppressionEngine = getattr(_fs, 'Phase96FactorSuppressionEngine', None)
    RegimeFactorSuppressionEngine = getattr(_fs, 'RegimeFactorSuppressionEngine', None)

from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    EnsembleScoringEngine,
)

try:
    from trading_system.src.ai.ensemble_scorer import (
        Phase96Coupler,
        Phase96WhittakerDrinfeldCoupler,
        Phase96BorcherdsMoonshineCoupler,
        Phase96MonsterWhittakerCoupler,
        compute_phase96_coupling,
    )
except ImportError:
    import trading_system.src.ai.ensemble_scorer as _es
    def _missing_es(name):
        val = getattr(_es, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'ensemble_scorer' has no Phase 96 attribute '{name}'")
        return _callable
    Phase96Coupler = getattr(_es, 'Phase96Coupler', None)
    Phase96WhittakerDrinfeldCoupler = getattr(_es, 'Phase96WhittakerDrinfeldCoupler', None)
    Phase96BorcherdsMoonshineCoupler = getattr(_es, 'Phase96BorcherdsMoonshineCoupler', None)
    Phase96MonsterWhittakerCoupler = getattr(_es, 'Phase96MonsterWhittakerCoupler', None)
    compute_phase96_coupling = _missing_es('compute_phase96_coupling')


class TestPhase96AlphaEnhancements:
    """Test suite for Phase 96 Alpha Signal Processing and Langlands Monster Whittaker Coupler."""

    def test_feature_f451_coupler_properties_v96(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert coupler.version == 96 or coupler.version >= 96
        assert getattr(coupler, "is_phase96", False) is True
        assert getattr(coupler, "is_phase95", False) is True
        assert getattr(coupler, "is_phase94", False) is True
        assert getattr(coupler, "is_phase93", False) is True
        assert getattr(coupler, "is_phase92", False) is True
        assert math.isclose(coupler.kappa_monster_whit, 39.80, abs_tol=1e-5)
        assert coupler.lambda_monster >= 0.999999999999999999
        assert math.isclose(coupler.harmony_boost, 9.90, abs_tol=1e-5)

        # Test forward coupling
        df = pd.DataFrame({
            "p1": [0.10, 0.20, -0.15],
            "p2": [0.12, 0.18, -0.14],
            "p3": [0.11, 0.22, -0.16],
            "p4": [0.09, 0.19, -0.13]
        }, index=["A", "B", "C"])
        res = coupler.couple_signals(df)
        assert isinstance(res, dict)
        assert "FERI_v96" in res or "feri_v96" in res or "f_out_96" in res
        assert "FERI_v95" in res or "feri_v95" in res or "f_out_95" in res
        assert "FERI_v94" in res or "feri_v94" in res or "f_out_94" in res
        assert "FERI_v93" in res or "feri_v93" in res or "f_out_93" in res

    def test_feature_f451_coupler_aliases(self):
        assert Phase96Coupler is not None
        assert Phase96WhittakerDrinfeldCoupler is not None
        assert Phase96BorcherdsMoonshineCoupler is not None
        assert Phase96MonsterWhittakerCoupler is not None
        coupler = Phase96Coupler()
        assert coupler.version >= 96
        assert coupler.is_phase96 is True

    def test_feature_f450_deadband_suppression(self):
        # Micro noise |z| <= 0.0003 must be suppressed to < 1e-576 (float64 0.0)
        micro_noise = np.array([-0.0003, -0.0001, 0.0, 0.0001, 0.0003])
        denoised = apply_pentacontahexagonal_hyperbolic_deadband(micro_noise)
        for val in denoised:
            assert abs(val) < 1e-15 or val == 0.0

        # Conviction signal |z| >= 0.150 preserved with high fidelity
        conviction = np.array([0.150, 0.300, 0.500])
        denoised_conv = apply_pentacontahexagonal_hyperbolic_deadband(conviction)
        for orig, d in zip(conviction, denoised_conv):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test
        grid = np.linspace(-1.0, 1.0, 1000)
        out = apply_pentacontahexagonal_hyperbolic_deadband(grid)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12)

    def test_feature_f450_deadband_aliases(self):
        aliases = [
            apply_pentacontahexagonal_hyperbolic_deadband,
            apply_quingentaoctacontahexagonal_hyperbolic_deadband,
            apply_pentacontaoctacontahexagonal_hyperbolic_deadband,
            apply_pentacontahexa_hyperbolic_deadband,
            apply_pentacontahexagonal_deadband,
            pentacontahexagonal_deadband,
            pentacontahexagonal_hyperbolic_deadband,
            compute_phase96_deadband,
            apply_phase96_deadband,
            phase96_deadband,
            apply_576th_order_hyperbolic_deadband,
            apply_576th_deadband,
            apply_576_deadband,
            apply_hyperbolic_deadband_v96,
            suppress_factor_noise_hyperbolic_v96,
        ]
        test_val = np.array([0.05, 0.10, -0.05])
        base_res = aliases[0](test_val)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_val)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

        assert Phase96FactorSuppressionEngine is not None

    def test_feature_f450_rank_modulation(self):
        # Ranks in [0, 1]
        ranks = np.linspace(0.0, 1.0, 100)
        modulated = compute_phase96_hyperconvex_rank_modulation(ranks, gamma_top=34.00)
        assert len(modulated) == len(ranks)
        # Check strict monotonicity non-decreasing
        assert np.all(np.diff(modulated) >= -1e-12)
        # Check top decile exponential warping: g(1.0) must be massive (> 1e7)
        assert modulated[-1] > 1e7

        # Negative branch test: g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.2] * len(ranks))
        mod_neg = compute_phase96_hyperconvex_rank_modulation(ranks, z_denoised=z_neg)
        assert np.all(np.diff(mod_neg) <= 1e-12)  # decreasing for higher rank

    def test_feature_f450_rank_modulation_regimes(self):
        assert "BULL_LOW_VOL" in REGIME_GAMMA_TOP_V96
        assert REGIME_GAMMA_TOP_V96["BULL_LOW_VOL"] >= 34.00
        gamma_bull = get_regime_adaptive_gamma_top_v96("BULL_LOW_VOL")
        assert gamma_bull >= 34.00
        gamma_crisis = get_regime_adaptive_gamma_top_v96("CRISIS")
        assert gamma_crisis < gamma_bull

    def test_feature_f450_rank_modulation_aliases(self):
        aliases = [
            compute_phase96_hyperconvex_rank_modulation,
            compute_123rd_order_hyperconvex_rank_modulation,
            compute_phase96_rank_warping,
            compute_phase96_rank_modulation,
            phase96_rank_modulation,
            phase96_hyperconvex_rank_modulation,
            apply_phase96_rank_modulation,
            apply_hyper_convex_rank_modulation_v96,
        ]
        test_ranks = np.array([0.2, 0.5, 0.8, 0.95])
        base_res = aliases[0](test_ranks, gamma_top=25.0)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_ranks, gamma_top=25.0)
            np.testing.assert_allclose(base_res, res, atol=1e-12)
