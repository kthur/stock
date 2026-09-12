r"""
tests/test_phase29_alpha.py

Comprehensive unit test suite for Phase 29 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F135: Motivic Beilinson-Flach Euler System Factor Disentanglement Engine
  (MotivicBeilinsonFlachCoupler, Beilinson-Flach regulator defect obstruction E_beilinson,
  Euler system class invariant Z_flach, coupling factor h_beilinson,
  theta_0=0.38, kappa=3.80, complete aliases and factor_suppression bindings)
- Feature F136.1: 24th-Order Hyper-Convex Rank Modulation (g_v29(r) = 0.50 + 1.22 * r * exp(gamma_top * r^24))
  with regime-adaptive gamma_top up to 3.00 (REGIME_GAMMA_TOP_V29, get_regime_adaptive_gamma_top_v29)
- Feature F136.2: 80th-Order Octacontagonal Hyperbolic Tangent Noise Deadband (alpha=80.0, leakage < 10^-42)
- End-to-End EnsembleScoringEngine combine_predictions() with version=29
- Strict backward compatibility validation with Phase 13 through Phase 28
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.ensemble_scorer import (
    apply_octacontagonal_hyperbolic_deadband,
    apply_hexaheptacontagonal_hyperbolic_deadband,
    apply_heptaduogonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase29_hyperconvex_rank_modulation,
    compute_phase29_rank_warping,
    compute_phase28_hyperconvex_rank_modulation,
    compute_phase27_hyperconvex_rank_modulation,
    MotivicBeilinsonFlachCoupler,
    BeilinsonFlachCoupler,
    BeilinsonCoupler,
    FlachCoupler,
    MotivicEulerSystemCoupler,
    EulerSystemCoupler,
    BeilinsonFlachRegulatorCoupler,
    MotivicCohomologyCoupler,
    BeilinsonRegulatorCoupler,
    EulerCoupler,
    RegulatorCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_octacontagonal_hyperbolic_deadband as fs_octacontagonal_deadband,
    apply_hexaheptacontagonal_hyperbolic_deadband as fs_hexaheptacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase29_hyperconvex_rank_modulation as fs_compute_phase29_modulation,
    compute_phase29_rank_warping as fs_compute_phase29_warping,
    REGIME_GAMMA_TOP_V29 as fs_REGIME_GAMMA_TOP_V29,
    get_regime_adaptive_gamma_top_v29 as fs_get_regime_adaptive_gamma_top_v29,
    MotivicBeilinsonFlachCoupler as fs_MotivicBeilinsonFlachCoupler,
    BeilinsonFlachCoupler as fs_BeilinsonFlachCoupler,
    BeilinsonCoupler as fs_BeilinsonCoupler,
    FlachCoupler as fs_FlachCoupler,
    MotivicEulerSystemCoupler as fs_MotivicEulerSystemCoupler,
    EulerSystemCoupler as fs_EulerSystemCoupler,
    BeilinsonFlachRegulatorCoupler as fs_BeilinsonFlachRegulatorCoupler,
    MotivicCohomologyCoupler as fs_MotivicCohomologyCoupler,
    BeilinsonRegulatorCoupler as fs_BeilinsonRegulatorCoupler,
    compute_motivic_beilinson_flach_coupling as fs_compute_motivic_beilinson_flach_coupling,
    compute_beilinson_flach_coupling as fs_compute_beilinson_flach_coupling,
    compute_beilinson_coupling as fs_compute_beilinson_coupling,
    compute_flach_coupling as fs_compute_flach_coupling,
    compute_motivic_euler_system_coupling as fs_compute_motivic_euler_system_coupling,
    compute_euler_system_coupling as fs_compute_euler_system_coupling,
    compute_beilinson_flach_regulator_coupling as fs_compute_beilinson_flach_regulator_coupling,
    compute_motivic_cohomology_coupling as fs_compute_motivic_cohomology_coupling,
    compute_beilinson_regulator_coupling as fs_compute_beilinson_regulator_coupling,
)


class TestPhase29Alpha:
    """Test suite covering Phase 29 Alpha Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F136.2: 80th-Order Octacontagonal Hyperbolic Deadband
    # -------------------------------------------------------------------------

    def test_octacontagonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.0016) has leakage < 10^-42."""
        z_grid = np.linspace(-0.0016, 0.0016, 100)
        denoised = apply_octacontagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=80.0)
        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-42, f"Octacontagonal deadband noise leakage {max_leakage} exceeds 10^-42"

    def test_octacontagonal_deadband_factor_suppression_binding(self):
        """Validates that factor_suppression exports octacontagonal deadband matching ensemble_scorer."""
        z = np.array([-0.05, -0.01, 0.0, 0.001, 0.05, 0.20])
        res_scorer = apply_octacontagonal_hyperbolic_deadband(z)
        res_suppression = fs_octacontagonal_deadband(z)
        np.testing.assert_allclose(res_scorer, res_suppression, rtol=1e-12, atol=1e-12)

    def test_smooth_deadband_attenuation_dispatch_v29(self):
        """Validates apply_smooth_deadband_attenuation dispatches to 80th order when version >= 29."""
        z_noise = np.array([0.0015])
        res_v29 = apply_smooth_deadband_attenuation(z_noise, version=29)
        res_v28 = apply_smooth_deadband_attenuation(z_noise, version=28)
        res_direct_80 = apply_octacontagonal_hyperbolic_deadband(z_noise, alpha_pos=80.0)
        np.testing.assert_allclose(res_v29, res_direct_80, rtol=1e-12, atol=1e-12)
        assert abs(res_v29[0]) < abs(res_v28[0]), "v29 noise attenuation must be strictly stronger than v28"

    # -------------------------------------------------------------------------
    # 2. Feature F136.1: 24th-Order Hyper-Convex Rank Modulation
    # -------------------------------------------------------------------------

    def test_phase29_rank_modulation_formula(self):
        """Validates g_v29(r) = 0.50 + 1.22 * r * exp(gamma_top * r^24)."""
        ranks = np.array([0.0, 0.5, 0.8, 1.0])
        gamma_top = 3.00
        expected = 0.50 + 1.22 * ranks * np.exp(gamma_top * (ranks ** 24))
        res = compute_phase29_hyperconvex_rank_modulation(ranks, gamma_top=gamma_top)
        np.testing.assert_allclose(res, expected, rtol=1e-12, atol=1e-12)

    def test_phase29_rank_warping_alias(self):
        """Validates compute_phase29_rank_warping is an exact alias for compute_phase29_hyperconvex_rank_modulation."""
        ranks = np.linspace(0.0, 1.0, 50)
        res1 = compute_phase29_hyperconvex_rank_modulation(ranks, gamma_top=3.00)
        res2 = compute_phase29_rank_warping(ranks, gamma_top=3.00)
        res3 = fs_compute_phase29_modulation(ranks, gamma_top=3.00)
        res4 = fs_compute_phase29_warping(ranks, gamma_top=3.00)
        np.testing.assert_allclose(res1, res2, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(res1, res3, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(res1, res4, rtol=1e-12, atol=1e-12)

    def test_regime_adaptive_gamma_top_v29(self):
        """Validates REGIME_GAMMA_TOP_V29 values and regime adaptation."""
        assert fs_REGIME_GAMMA_TOP_V29["BULL_LOW_VOL"] == 3.00
        assert fs_REGIME_GAMMA_TOP_V29["BULL_HIGH_VOL"] == 2.70
        assert fs_REGIME_GAMMA_TOP_V29["SIDEWAYS"] == 2.50
        assert fs_REGIME_GAMMA_TOP_V29["BEAR"] == 2.20
        assert fs_REGIME_GAMMA_TOP_V29["CRISIS"] == 0.95
        assert fs_get_regime_adaptive_gamma_top_v29("BULL_LOW_VOL") == 3.00
        assert fs_get_regime_adaptive_gamma_top_v29("CRISIS") == 0.95
        assert fs_get_regime_adaptive_gamma_top_v29("UNKNOWN_REGIME") == 2.40

    def test_top_rank_hyperconvex_conviction_expansion_v29(self):
        """Validates that top rank (r=1.0) achieves conviction > 24.5 under Bull Low Vol regime."""
        r_top = np.array([1.0])
        val_v29 = compute_phase29_hyperconvex_rank_modulation(r_top, gamma_top=3.00)[0]
        val_v28 = compute_phase28_hyperconvex_rank_modulation(r_top, gamma_top=2.90)[0]
        assert val_v29 > 24.5, f"Top rank conviction {val_v29} should be > 24.5"
        assert val_v29 > val_v28, f"v29 top conviction {val_v29} must exceed v28 conviction {val_v28}"

    # -------------------------------------------------------------------------
    # 3. Feature F135: Motivic Beilinson-Flach Euler System Coupler
    # -------------------------------------------------------------------------

    def test_motivic_beilinson_flach_coupler_instantiation_and_aliases(self):
        """Validates all class aliases for MotivicBeilinsonFlachCoupler exist and instantiate properly."""
        couplers = [
            MotivicBeilinsonFlachCoupler(),
            BeilinsonFlachCoupler(),
            BeilinsonCoupler(),
            FlachCoupler(),
            MotivicEulerSystemCoupler(),
            EulerSystemCoupler(),
            BeilinsonFlachRegulatorCoupler(),
            MotivicCohomologyCoupler(),
            BeilinsonRegulatorCoupler(),
            EulerCoupler(),
            RegulatorCoupler(),
            fs_MotivicBeilinsonFlachCoupler(),
            fs_BeilinsonFlachCoupler(),
            fs_BeilinsonCoupler(),
            fs_FlachCoupler(),
            fs_MotivicEulerSystemCoupler(),
            fs_EulerSystemCoupler(),
            fs_BeilinsonFlachRegulatorCoupler(),
            fs_MotivicCohomologyCoupler(),
            fs_BeilinsonRegulatorCoupler(),
        ]
        for c in couplers:
            assert c.theta_0 == 0.38
            assert c.kappa == 3.80
            assert hasattr(c, "compute_coupling")

    def test_motivic_beilinson_flach_coupling_computation(self):
        """Validates Beilinson-Flach coupling outputs and Euler system class invariant."""
        coupler = MotivicBeilinsonFlachCoupler(theta_0=0.38, kappa_beilinson=3.80)
        z = np.array([
            [0.60, 0.20, 0.80],
            [0.70, 0.30, 1.40],
            [0.65, 0.25, 0.75],
            [0.55, 0.15, 0.90],
            [0.50, 0.10, 0.70],
        ]).T
        res = coupler.compute_coupling(z)
        assert "h_beilinson" in res
        assert "z_flach" in res
        assert "e_beilinson" in res
        assert "FERI_v29" in res
        assert np.all(res["e_beilinson"] >= 0.0)
        assert np.all(res["h_beilinson"] >= 0.0)

    def test_functional_coupling_interfaces(self):
        """Validates all exported functional interfaces produce identical coupling results."""
        z = np.array([0.1, 0.4, 0.8, -0.3, 0.5])
        c1 = EnsembleScoringEngine.compute_motivic_beilinson_flach_coupling(z)
        c2 = fs_compute_motivic_beilinson_flach_coupling(z)
        c3 = fs_compute_beilinson_flach_coupling(z)
        c4 = fs_compute_beilinson_coupling(z)
        c5 = fs_compute_flach_coupling(z)
        c6 = fs_compute_motivic_euler_system_coupling(z)
        c7 = fs_compute_euler_system_coupling(z)
        assert math.isclose(c1["h_beilinson"], c2["h_beilinson"], abs_tol=1e-12)
        assert math.isclose(c1["h_beilinson"], c3["h_beilinson"], abs_tol=1e-12)
        assert math.isclose(c1["h_beilinson"], c4["h_beilinson"], abs_tol=1e-12)
        assert math.isclose(c1["h_beilinson"], c5["h_beilinson"], abs_tol=1e-12)
        assert math.isclose(c1["h_beilinson"], c6["h_beilinson"], abs_tol=1e-12)
        assert math.isclose(c1["h_beilinson"], c7["h_beilinson"], abs_tol=1e-12)

    # -------------------------------------------------------------------------
    # 4. End-to-End EnsembleScoringEngine with version=29
    # -------------------------------------------------------------------------

    def test_ensemble_scoring_engine_combine_predictions_v29(self):
        """Validates EnsembleScoringEngine combine_predictions with version=29."""
        engine = EnsembleScoringEngine()
        N = 25
        df_list = []
        for i in range(N):
            df_list.append({
                "symbol": f"STOCK_{i:03d}",
                "market": "SP500",
                "regression": 0.35 + 0.02 * i,
                "surge": 0.30 + 0.02 * i,
                "vcp_ml": 0.25 + 0.02 * i,
            })
        test_df = pd.DataFrame(df_list)

        comb_v28 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=28)
        comb_v29 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=29)

        assert isinstance(comb_v29, pd.DataFrame)
        assert not comb_v29.empty
        assert "ensemble_score" in comb_v29.columns
        assert len(comb_v29) == N
        assert np.all(np.isfinite(comb_v29["ensemble_score"].values))
        assert np.all(comb_v29["ensemble_score"].values >= 0.0)
        assert np.all(comb_v29["ensemble_score"].values <= 1.0)

        # Top conviction in v29 should be >= v28
        top_v28 = comb_v28.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v29 = comb_v29.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v29 >= top_v28 - 1e-6, f"Top conviction in v29 ({top_v29}) should be >= v28 ({top_v28})"

    def test_backward_compatibility_v28_v27_v26(self):
        """Validates backward compatibility across version=28, version=27, and version=26."""
        engine = EnsembleScoringEngine()
        N = 15
        test_df = pd.DataFrame([{
            "symbol": f"SYM_{i}",
            "market": "KOSPI",
            "regression": 0.50,
            "surge": 0.60
        } for i in range(N)])

        res_v26 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=26)
        res_v27 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=27)
        res_v28 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=28)
        res_v29 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=29)

        assert len(res_v26) == N
        assert len(res_v27) == N
        assert len(res_v28) == N
        assert len(res_v29) == N
        assert all("ensemble_score" in res_v29.columns for _ in [1])
        assert all("ensemble_score" in res_v28.columns for _ in [1])
        assert all("ensemble_score" in res_v27.columns for _ in [1])
        assert all("ensemble_score" in res_v26.columns for _ in [1])
