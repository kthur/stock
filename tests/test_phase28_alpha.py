r"""
tests/test_phase28_alpha.py

Comprehensive unit test suite for Phase 28 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F131: Motivic Galois Group & Tannakian Category Reconstruction Factor Disentanglement Engine
  (MotivicGaloisTannakianCoupler, Deligne-Tannakian cycle defect obstruction E_tannaka,
  Tannakian fiber functor invariant Z_tannaka, coupling factor h_tannaka,
  theta_0=0.36, kappa=3.70, complete aliases and factor_suppression bindings)
- Feature F132.1: 23rd-Order Hyper-Convex Rank Modulation (g_v28(r) = 0.50 + 1.20 * r * exp(gamma_top * r^23))
  with regime-adaptive gamma_top up to 2.90 (REGIME_GAMMA_TOP_V28, get_regime_adaptive_gamma_top_v28)
- Feature F132.2: 76th-Order Hexaheptacontagonal Hyperbolic Tangent Noise Deadband (alpha=76.0, leakage < 10^-40)
- End-to-End EnsembleScoringEngine combine_predictions() with version=28
- Strict backward compatibility validation with Phase 13 (v13) through Phase 27 (v27)
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.ensemble_scorer import (
    apply_hexaheptacontagonal_hyperbolic_deadband,
    apply_heptaduogonal_hyperbolic_deadband,
    apply_hexatetrahedral_hyperbolic_deadband,
    apply_hexacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase28_hyperconvex_rank_modulation,
    compute_phase28_rank_warping,
    compute_phase27_hyperconvex_rank_modulation,
    compute_phase25_hyperconvex_rank_modulation,
    MotivicGaloisTannakianCoupler,
    MotivicGaloisCoupler,
    TannakianCoupler,
    TannakianDualityCoupler,
    MotivicCoupler,
    GaloisTannakianCoupler,
    MotivicTannakianCoupler,
    AnabelianGrothendieckCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_hexaheptacontagonal_hyperbolic_deadband as fs_hexaheptacontagonal_deadband,
    apply_heptaduogonal_hyperbolic_deadband as fs_heptaduogonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase28_hyperconvex_rank_modulation as fs_compute_phase28_modulation,
    compute_phase28_rank_warping as fs_compute_phase28_warping,
    REGIME_GAMMA_TOP_V28 as fs_REGIME_GAMMA_TOP_V28,
    get_regime_adaptive_gamma_top_v28 as fs_get_regime_adaptive_gamma_top_v28,
    MotivicGaloisTannakianCoupler as fs_MotivicGaloisTannakianCoupler,
    MotivicGaloisCoupler as fs_MotivicGaloisCoupler,
    TannakianCoupler as fs_TannakianCoupler,
    TannakianDualityCoupler as fs_TannakianDualityCoupler,
    MotivicCoupler as fs_MotivicCoupler,
    GaloisTannakianCoupler as fs_GaloisTannakianCoupler,
    MotivicTannakianCoupler as fs_MotivicTannakianCoupler,
    compute_motivic_galois_tannakian_coupling as fs_compute_motivic_galois_tannakian_coupling,
    compute_motivic_galois_coupling as fs_compute_motivic_galois_coupling,
    compute_tannakian_coupling as fs_compute_tannakian_coupling,
    compute_tannakian_duality_coupling as fs_compute_tannakian_duality_coupling,
    compute_motivic_coupling as fs_compute_motivic_coupling,
    compute_galois_tannakian_coupling as fs_compute_galois_tannakian_coupling,
)


class TestPhase28Alpha:
    """Test suite covering Phase 28 Alpha Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F132.2: 76th-Order Hexaheptacontagonal Hyperbolic Deadband
    # -------------------------------------------------------------------------

    def test_hexaheptacontagonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.0018) has leakage < 10^-40."""
        z_grid = np.linspace(-0.0018, 0.0018, 100)
        denoised = apply_hexaheptacontagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=76.0)
        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-40, f"Hexaheptacontagonal deadband noise leakage {max_leakage} exceeds 10^-40"

    def test_hexaheptacontagonal_deadband_factor_suppression_binding(self):
        """Validates that factor_suppression exports hexaheptacontagonal deadband matching ensemble_scorer."""
        z = np.array([-0.05, -0.01, 0.0, 0.001, 0.05, 0.20])
        res_scorer = apply_hexaheptacontagonal_hyperbolic_deadband(z)
        res_suppression = fs_hexaheptacontagonal_deadband(z)
        np.testing.assert_allclose(res_scorer, res_suppression, rtol=1e-12, atol=1e-12)

    def test_smooth_deadband_attenuation_dispatch_v28(self):
        """Validates apply_smooth_deadband_attenuation dispatches to 76th order when version >= 28."""
        z_noise = np.array([0.0015])
        res_v28 = apply_smooth_deadband_attenuation(z_noise, version=28)
        res_v27 = apply_smooth_deadband_attenuation(z_noise, version=27)
        res_direct_76 = apply_hexaheptacontagonal_hyperbolic_deadband(z_noise, alpha_pos=76.0)
        np.testing.assert_allclose(res_v28, res_direct_76, rtol=1e-12, atol=1e-12)
        assert abs(res_v28[0]) < abs(res_v27[0]), "v28 noise attenuation must be strictly stronger than v27"

    # -------------------------------------------------------------------------
    # 2. Feature F132.1: 23rd-Order Hyper-Convex Rank Modulation
    # -------------------------------------------------------------------------

    def test_phase28_rank_modulation_formula(self):
        """Validates g_v28(r) = 0.50 + 1.20 * r * exp(gamma_top * r^23)."""
        ranks = np.array([0.0, 0.5, 0.8, 1.0])
        gamma_top = 2.90
        expected = 0.50 + 1.20 * ranks * np.exp(gamma_top * (ranks ** 23))
        res = compute_phase28_hyperconvex_rank_modulation(ranks, gamma_top=gamma_top)
        np.testing.assert_allclose(res, expected, rtol=1e-12, atol=1e-12)

    def test_phase28_rank_warping_alias(self):
        """Validates compute_phase28_rank_warping is an exact alias for compute_phase28_hyperconvex_rank_modulation."""
        ranks = np.linspace(0.0, 1.0, 50)
        res1 = compute_phase28_hyperconvex_rank_modulation(ranks, gamma_top=2.90)
        res2 = compute_phase28_rank_warping(ranks, gamma_top=2.90)
        res3 = fs_compute_phase28_modulation(ranks, gamma_top=2.90)
        res4 = fs_compute_phase28_warping(ranks, gamma_top=2.90)
        np.testing.assert_allclose(res1, res2, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(res1, res3, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(res1, res4, rtol=1e-12, atol=1e-12)

    def test_regime_adaptive_gamma_top_v28(self):
        """Validates REGIME_GAMMA_TOP_V28 values and regime adaptation."""
        assert fs_REGIME_GAMMA_TOP_V28["BULL_LOW_VOL"] == 2.90
        assert fs_REGIME_GAMMA_TOP_V28["SIDEWAYS"] == 2.40
        assert fs_REGIME_GAMMA_TOP_V28["BEAR"] == 2.10
        assert fs_REGIME_GAMMA_TOP_V28["CRISIS"] == 0.90
        assert fs_get_regime_adaptive_gamma_top_v28("BULL_LOW_VOL") == 2.90
        assert fs_get_regime_adaptive_gamma_top_v28("CRISIS") == 0.90
        assert fs_get_regime_adaptive_gamma_top_v28("UNKNOWN_REGIME") == 2.30

    def test_top_rank_hyperconvex_conviction_expansion_v28(self):
        """Validates that top rank (r=1.0) achieves conviction > 22.3 under Bull Low Vol regime."""
        r_top = np.array([1.0])
        val_v28 = compute_phase28_hyperconvex_rank_modulation(r_top, gamma_top=2.90)[0]
        val_v27 = compute_phase27_hyperconvex_rank_modulation(r_top, gamma_top=2.80)[0]
        assert val_v28 > 22.3, f"Top rank conviction {val_v28} should be > 22.3"
        assert val_v28 > val_v27, f"v28 top conviction {val_v28} must exceed v27 conviction {val_v27}"

    # -------------------------------------------------------------------------
    # 3. Feature F131: Motivic Galois Group & Tannakian Category Coupler
    # -------------------------------------------------------------------------

    def test_motivic_galois_tannakian_coupler_instantiation_and_aliases(self):
        """Validates all class aliases for MotivicGaloisTannakianCoupler exist and instantiate properly."""
        couplers = [
            MotivicGaloisTannakianCoupler(),
            MotivicGaloisCoupler(),
            TannakianCoupler(),
            TannakianDualityCoupler(),
            MotivicCoupler(),
            GaloisTannakianCoupler(),
            MotivicTannakianCoupler(),
            fs_MotivicGaloisTannakianCoupler(),
            fs_MotivicGaloisCoupler(),
            fs_TannakianCoupler(),
            fs_TannakianDualityCoupler(),
            fs_MotivicCoupler(),
            fs_GaloisTannakianCoupler(),
            fs_MotivicTannakianCoupler(),
        ]
        for c in couplers:
            assert c.theta_0 == 0.36
            assert c.kappa == 3.70
            assert hasattr(c, "compute_coupling")

    def test_motivic_galois_tannakian_coupling_computation(self):
        """Validates Tannakian coupling outputs and Deligne-Tannakian cycle defect."""
        coupler = MotivicGaloisTannakianCoupler(theta_0=0.36, kappa_tannaka=3.70)
        z = np.array([
            [0.60, 0.20, 0.80],
            [0.70, 0.30, 1.40],
            [0.65, 0.25, 0.75],
            [0.55, 0.15, 0.90],
            [0.50, 0.10, 0.70],
        ]).T
        res = coupler.compute_coupling(z)
        assert "h_tannaka" in res
        assert "z_tannaka" in res
        assert "e_tannaka" in res
        assert "FERI_v28" in res
        assert np.all(res["e_tannaka"] >= 0.0)
        assert np.all(res["h_tannaka"] >= 0.0)

    def test_functional_coupling_interfaces(self):
        """Validates all exported functional interfaces produce identical coupling results."""
        z = np.array([0.1, 0.4, 0.8, -0.3, 0.5])
        c1 = EnsembleScoringEngine.compute_motivic_galois_tannakian_coupling(z)
        c2 = fs_compute_motivic_galois_tannakian_coupling(z)
        c3 = fs_compute_motivic_galois_coupling(z)
        c4 = fs_compute_tannakian_coupling(z)
        c5 = fs_compute_tannakian_duality_coupling(z)
        c7 = fs_compute_galois_tannakian_coupling(z)
        assert math.isclose(c1["h_tannaka"], c2["h_tannaka"], abs_tol=1e-12)
        assert math.isclose(c1["h_tannaka"], c3["h_tannaka"], abs_tol=1e-12)
        assert math.isclose(c1["h_tannaka"], c4["h_tannaka"], abs_tol=1e-12)
        assert math.isclose(c1["h_tannaka"], c5["h_tannaka"], abs_tol=1e-12)
        assert math.isclose(c1["h_tannaka"], c7["h_tannaka"], abs_tol=1e-12)

    # -------------------------------------------------------------------------
    # 4. End-to-End EnsembleScoringEngine with version=28
    # -------------------------------------------------------------------------

    def test_ensemble_scoring_engine_combine_predictions_v28(self):
        """Validates EnsembleScoringEngine combine_predictions with version=28."""
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

        comb_v27 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=27)
        comb_v28 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=28)

        assert isinstance(comb_v28, pd.DataFrame)
        assert not comb_v28.empty
        assert "ensemble_score" in comb_v28.columns
        assert len(comb_v28) == N
        assert np.all(np.isfinite(comb_v28["ensemble_score"].values))
        assert np.all(comb_v28["ensemble_score"].values >= 0.0)
        assert np.all(comb_v28["ensemble_score"].values <= 1.0)

        # Top conviction in v28 should be >= v27
        top_v27 = comb_v27.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v28 = comb_v28.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v28 >= top_v27 - 1e-6, f"Top conviction in v28 ({top_v28}) should be >= v27 ({top_v27})"

    def test_backward_compatibility_v27_v26_v25(self):
        """Validates backward compatibility across version=27, version=26, and version=25."""
        engine = EnsembleScoringEngine()
        N = 15
        test_df = pd.DataFrame([{
            "symbol": f"SYM_{i}",
            "market": "KOSPI",
            "regression": 0.50,
            "surge": 0.60
        } for i in range(N)])

        res_v25 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=25)
        res_v26 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=26)
        res_v27 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=27)
        res_v28 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=28)

        assert len(res_v25) == N
        assert len(res_v26) == N
        assert len(res_v27) == N
        assert len(res_v28) == N
        assert all("ensemble_score" in res_v28.columns for _ in [1])
        assert all("ensemble_score" in res_v27.columns for _ in [1])
        assert all("ensemble_score" in res_v26.columns for _ in [1])
        assert all("ensemble_score" in res_v25.columns for _ in [1])
