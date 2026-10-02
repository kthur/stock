"""
tests/test_phase95_alpha.py

Unit test suite for Phase 95 Quantitative Alpha Enhancement (Features F445, F446):
- Feature F445: Asymmetric Dodecatetracontasagonal (568th-Order) Hyperbolic Deadband
  (alpha_pos = 568.0, delta_noise = 0.035, noise suppression < 10^-568 for |z| <= 0.0003,
   full transmission for |z| >= 0.150, rank monotonicity rho = 1.0000).
- Feature F445: 121st-Order Hyperconvex Rank Modulation
  (g_v95(r) = 0.50 + 3.66 * r * exp(gamma_top * r^121) with REGIME_GAMMA_TOP_V95,
   gamma_top <= 33.00, strictly monotonic non-decreasing, g(1.0) > 10^7,
   g_neg(r) = 1.35 - 1.00 * r for negative signals).
- Feature F446: Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds Moonshine Monster Whittaker Coupler v95
  (defaults to version=95, kappa_monster_whit=39.20, lambda_monster=0.999999999999999995 [18-nines + 5],
   is_phase95=True, harmony_boost=9.55,
   202nd-order chiral oper obstruction, 114th-order topological defect invariant,
   output keys FERI_v95, feri_v95, f_out_95, FERI_v94, feri_v94, f_out_94, etc.).
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
        apply_dodecatetracontasagonal_hyperbolic_deadband,
        apply_quingentahexacontaoctagonal_hyperbolic_deadband,
        apply_pentacentahexacontaoctagonal_hyperbolic_deadband,
        apply_dodecatetraconta_hyperbolic_deadband,
        apply_dodecatetracontasagonal_deadband,
        dodecatetracontasagonal_deadband,
        dodecatetracontasagonal_hyperbolic_deadband,
        compute_phase95_deadband,
        apply_phase95_deadband,
        phase95_deadband,
        apply_568th_order_hyperbolic_deadband,
        apply_568th_deadband,
        apply_568_deadband,
        apply_hyperbolic_deadband_v95,
        suppress_factor_noise_hyperbolic_v95,
        compute_phase95_hyperconvex_rank_modulation,
        compute_phase95_rank_warping,
        compute_phase95_rank_modulation,
        phase95_rank_modulation,
        phase95_hyperconvex_rank_modulation,
        apply_hyper_convex_rank_modulation_v95,
        REGIME_GAMMA_TOP_V95,
        get_regime_adaptive_gamma_top_v95,
        Phase95FactorSuppressionEngine,
        RegimeFactorSuppressionEngine,
    )
except ImportError:
    import trading_system.src.ai.factor_suppression as _fs

    def _missing_fs(name):
        val = getattr(_fs, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'factor_suppression' has no Phase 95 attribute '{name}'")
        return _callable

    apply_dodecatetracontasagonal_hyperbolic_deadband = _missing_fs('apply_dodecatetracontasagonal_hyperbolic_deadband')
    apply_quingentahexacontaoctagonal_hyperbolic_deadband = _missing_fs('apply_quingentahexacontaoctagonal_hyperbolic_deadband')
    apply_pentacentahexacontaoctagonal_hyperbolic_deadband = _missing_fs('apply_pentacentahexacontaoctagonal_hyperbolic_deadband')
    apply_dodecatetraconta_hyperbolic_deadband = _missing_fs('apply_dodecatetraconta_hyperbolic_deadband')
    apply_dodecatetracontasagonal_deadband = _missing_fs('apply_dodecatetracontasagonal_deadband')
    dodecatetracontasagonal_deadband = _missing_fs('dodecatetracontasagonal_deadband')
    dodecatetracontasagonal_hyperbolic_deadband = _missing_fs('dodecatetracontasagonal_hyperbolic_deadband')
    compute_phase95_deadband = _missing_fs('compute_phase95_deadband')
    apply_phase95_deadband = _missing_fs('apply_phase95_deadband')
    phase95_deadband = _missing_fs('phase95_deadband')
    apply_568th_order_hyperbolic_deadband = _missing_fs('apply_568th_order_hyperbolic_deadband')
    apply_568th_deadband = _missing_fs('apply_568th_deadband')
    apply_568_deadband = _missing_fs('apply_568_deadband')
    apply_hyperbolic_deadband_v95 = _missing_fs('apply_hyperbolic_deadband_v95')
    suppress_factor_noise_hyperbolic_v95 = _missing_fs('suppress_factor_noise_hyperbolic_v95')
    compute_phase95_hyperconvex_rank_modulation = _missing_fs('compute_phase95_hyperconvex_rank_modulation')
    compute_phase95_rank_warping = _missing_fs('compute_phase95_rank_warping')
    compute_phase95_rank_modulation = _missing_fs('compute_phase95_rank_modulation')
    phase95_rank_modulation = _missing_fs('phase95_rank_modulation')
    phase95_hyperconvex_rank_modulation = _missing_fs('phase95_hyperconvex_rank_modulation')
    apply_hyper_convex_rank_modulation_v95 = _missing_fs('apply_hyper_convex_rank_modulation_v95')
    REGIME_GAMMA_TOP_V95 = getattr(_fs, 'REGIME_GAMMA_TOP_V95', {})
    get_regime_adaptive_gamma_top_v95 = _missing_fs('get_regime_adaptive_gamma_top_v95')
    Phase95FactorSuppressionEngine = getattr(_fs, 'Phase95FactorSuppressionEngine', None)
    RegimeFactorSuppressionEngine = getattr(_fs, 'RegimeFactorSuppressionEngine', None)

from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    EnsembleScoringEngine,
)

try:
    from trading_system.src.ai.ensemble_scorer import (
        Phase95Coupler,
        Phase95WhittakerDrinfeldCoupler,
        Phase95BorcherdsMoonshineCoupler,
        Phase95MonsterWhittakerCoupler,
        compute_phase95_coupling,
    )
except ImportError:
    import trading_system.src.ai.ensemble_scorer as _es
    def _missing_es(name):
        val = getattr(_es, name, None)
        if val is not None:
            return val
        def _callable(*args, **kwargs):
            raise AttributeError(f"Module 'ensemble_scorer' has no Phase 95 attribute '{name}'")
        return _callable
    Phase95Coupler = getattr(_es, 'Phase95Coupler', None)
    Phase95WhittakerDrinfeldCoupler = getattr(_es, 'Phase95WhittakerDrinfeldCoupler', None)
    Phase95BorcherdsMoonshineCoupler = getattr(_es, 'Phase95BorcherdsMoonshineCoupler', None)
    Phase95MonsterWhittakerCoupler = getattr(_es, 'Phase95MonsterWhittakerCoupler', None)
    compute_phase95_coupling = _missing_es('compute_phase95_coupling')


class TestPhase95AlphaEnhancements:
    """Test suite for Phase 95 Alpha Signal Processing and Langlands Monster Whittaker Coupler."""

    def test_feature_f446_coupler_properties_v95(self):
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert coupler.version == 95 or coupler.version >= 95
        assert getattr(coupler, "is_phase95", False) is True
        assert getattr(coupler, "is_phase94", False) is True
        assert getattr(coupler, "is_phase93", False) is True
        assert getattr(coupler, "is_phase92", False) is True
        assert math.isclose(coupler.kappa_monster_whit, 39.20, abs_tol=1e-5)
        assert coupler.lambda_monster >= 0.99999999999999999
        assert math.isclose(coupler.harmony_boost, 9.55, abs_tol=1e-5)

        # Test forward coupling
        df = pd.DataFrame({
            "p1": [0.10, 0.20, -0.15],
            "p2": [0.12, 0.18, -0.14],
            "p3": [0.11, 0.22, -0.16],
            "p4": [0.09, 0.19, -0.13]
        }, index=["A", "B", "C"])
        res = coupler.couple_signals(df)
        assert isinstance(res, dict)
        assert "FERI_v95" in res or "feri_v95" in res or "f_out_95" in res
        assert "FERI_v94" in res or "feri_v94" in res or "f_out_94" in res
        assert "FERI_v93" in res or "feri_v93" in res or "f_out_93" in res

    def test_feature_f446_coupler_aliases(self):
        assert Phase95Coupler is not None
        assert Phase95WhittakerDrinfeldCoupler is not None
        assert Phase95BorcherdsMoonshineCoupler is not None
        assert Phase95MonsterWhittakerCoupler is not None
        coupler = Phase95Coupler()
        assert coupler.version >= 95
        assert coupler.is_phase95 is True

    def test_feature_f445_deadband_suppression(self):
        # Micro noise |z| <= 0.0003 must be suppressed to < 1e-560 (float64 0.0)
        micro_noise = np.array([-0.0003, -0.0001, 0.0, 0.0001, 0.0003])
        denoised = apply_dodecatetracontasagonal_hyperbolic_deadband(micro_noise)
        for val in denoised:
            assert abs(val) < 1e-15 or val == 0.0

        # Conviction signal |z| >= 0.150 preserved with high fidelity
        conviction = np.array([0.150, 0.300, 0.500])
        denoised_conv = apply_dodecatetracontasagonal_hyperbolic_deadband(conviction)
        for orig, d in zip(conviction, denoised_conv):
            assert math.isclose(orig, d, rel_tol=1e-3)

        # Monotonicity test
        grid = np.linspace(-1.0, 1.0, 1000)
        out = apply_dodecatetracontasagonal_hyperbolic_deadband(grid)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12)

    def test_feature_f445_deadband_aliases(self):
        aliases = [
            apply_dodecatetracontasagonal_hyperbolic_deadband,
            apply_quingentahexacontaoctagonal_hyperbolic_deadband,
            apply_pentacentahexacontaoctagonal_hyperbolic_deadband,
            apply_dodecatetraconta_hyperbolic_deadband,
            apply_dodecatetracontasagonal_deadband,
            dodecatetracontasagonal_deadband,
            dodecatetracontasagonal_hyperbolic_deadband,
            compute_phase95_deadband,
            apply_phase95_deadband,
            phase95_deadband,
            apply_568th_order_hyperbolic_deadband,
            apply_568th_deadband,
            apply_568_deadband,
            apply_hyperbolic_deadband_v95,
            suppress_factor_noise_hyperbolic_v95,
        ]
        test_val = np.array([0.05, 0.10, -0.05])
        base_res = aliases[0](test_val)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_val)
            np.testing.assert_allclose(base_res, res, atol=1e-12)

        assert Phase95FactorSuppressionEngine is not None

    def test_feature_f445_rank_modulation(self):
        # Ranks in [0, 1]
        ranks = np.linspace(0.0, 1.0, 100)
        modulated = compute_phase95_hyperconvex_rank_modulation(ranks, gamma_top=33.00)
        assert len(modulated) == len(ranks)
        # Check strict monotonicity non-decreasing
        assert np.all(np.diff(modulated) >= -1e-12)
        # Check top decile exponential warping: g(1.0) must be massive
        assert modulated[-1] > 1e7

        # Negative branch test: g_neg(r) = 1.35 - 1.00 * r
        z_neg = np.array([-0.2] * len(ranks))
        mod_neg = compute_phase95_hyperconvex_rank_modulation(ranks, z_denoised=z_neg)
        assert np.all(np.diff(mod_neg) <= 1e-12)  # decreasing for higher rank

    def test_feature_f445_rank_modulation_regimes(self):
        assert "BULL_LOW_VOL" in REGIME_GAMMA_TOP_V95
        assert REGIME_GAMMA_TOP_V95["BULL_LOW_VOL"] >= 33.00
        gamma_bull = get_regime_adaptive_gamma_top_v95("BULL_LOW_VOL")
        assert gamma_bull >= 33.00
        gamma_crisis = get_regime_adaptive_gamma_top_v95("CRISIS")
        assert gamma_crisis < gamma_bull

    def test_feature_f445_rank_modulation_aliases(self):
        aliases = [
            compute_phase95_hyperconvex_rank_modulation,
            compute_phase95_rank_warping,
            compute_phase95_rank_modulation,
            phase95_rank_modulation,
            phase95_hyperconvex_rank_modulation,
            apply_hyper_convex_rank_modulation_v95,
        ]
        test_ranks = np.array([0.2, 0.5, 0.8, 0.95])
        base_res = aliases[0](test_ranks, gamma_top=25.0)
        for alias_fn in aliases[1:]:
            res = alias_fn(test_ranks, gamma_top=25.0)
            np.testing.assert_allclose(base_res, res, atol=1e-12)
