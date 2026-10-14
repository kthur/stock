"""
tests/test_phase103_adversarial_challenger2.py

Adversarial Verification and Empirical Stress Testing Suite for Phase 103:
- Quantum Geometric Langlands Monster Whittaker Coupler Phase 103 (F486)
- Extreme Factor Clipping Overflow Defense in [-1000.0, 1000.0]
- 218th-Order Chiral Oper Defect Complex & 130th-Order Topological Defect Invariant Evaluation
- Complete Version Gating & Backward Compatibility (v48 through v103)
- combine_predictions Integration with Phase 103 Deadband and Rank Modulation
- Isotonic PAVA & Monotonicity Regularizer Stress Testing
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_sexcentoduotrigesimal_hyperbolic_deadband,
    compute_phase103_hyperconvex_rank_modulation,
    REGIME_GAMMA_TOP_V103,
    get_regime_adaptive_gamma_top_v103,
)

from trading_system.src.ai.ensemble_scorer import (
    EnsembleScoringEngine,
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    compute_phase103_coupling,
    FERI_v103,
    feri_v103,
    f_out_103,
)

from trading_system.src.ai.prediction_model import (
    isotonic_pava,
    regularize_multi_horizon_monotonicity,
    compute_cross_sectional_relative_rank_features,
)


class TestPhase103AdversarialCouplerAndAlpha:
    """Adversarial stress-testing suite for Phase 103 Alpha, Coupler, and Ensemble Integration."""

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Coupler Numerical Overflow Defense with Extreme Inputs [-1000.0, 1000.0]
    # ─────────────────────────────────────────────────────────────────────────
    def test_coupler_numerical_overflow_defense_extreme_inputs(self):
        """Stress-test coupler with extreme factor inputs in [-1000.0, 1000.0]."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=103)

        # Adversarial corner cases
        corner_cases = [
            [1000.0, -1000.0, 1000.0, -1000.0, 1000.0],
            [-1000.0, -1000.0, -1000.0, -1000.0, -1000.0],
            [1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
            [300.0, -300.0, 300.0, -300.0, 0.0],
            [300.0001, -300.0001, 50.0, -50.0, 25.0],
            [999.999, -999.999, 500.0, -500.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
        ]
        
        # Add 500 randomly sampled rows uniformly in [-1000.0, 1000.0]
        np.random.seed(42)
        random_extreme = np.random.uniform(-1000.0, 1000.0, size=(500, 5))
        all_inputs = np.vstack([np.array(corner_cases), random_extreme])

        df_extreme = pd.DataFrame(all_inputs, columns=["val", "mom", "flow", "cat", "net"])
        res = coupler.couple_signals(df_extreme)

        assert isinstance(res, dict)
        assert "FERI_v103" in res
        assert "feri_v103" in res
        assert "f_out_103" in res

        feri_vals = res["FERI_v103"].values if isinstance(res["FERI_v103"], pd.Series) else np.asarray(res["FERI_v103"])
        h_vals = res["h_monster_whit"].values if isinstance(res["h_monster_whit"], pd.Series) else np.asarray(res["h_monster_whit"])
        z_vals = res["z_monster_whit"].values if isinstance(res["z_monster_whit"], pd.Series) else np.asarray(res["z_monster_whit"])
        e_vals = res["e_monster_whit"].values if isinstance(res["e_monster_whit"], pd.Series) else np.asarray(res["e_monster_whit"])

        # Strict finite assertions
        assert np.all(np.isfinite(feri_vals)), "FERI_v103 contains non-finite values (NaN or Inf)!"
        assert np.all(np.isfinite(h_vals)), "h_monster_whit contains non-finite values!"
        assert np.all(np.isfinite(z_vals)), "z_monster_whit contains non-finite values!"
        assert np.all(np.isfinite(e_vals)), "e_monster_whit contains non-finite values!"

        # Domain bounds
        assert np.all(feri_vals > 0.0), "FERI_v103 must be strictly positive!"
        assert np.all(feri_vals <= 1.0), "FERI_v103 must not exceed 1.0!"
        assert np.all(h_vals >= 1e-6), "h_monster_whit must respect epsilon_reg floor!"
        assert np.all(h_vals <= 1.0), "h_monster_whit must not exceed 1.0!"
        assert np.all(z_vals > 0.0), "z_monster_whit must be strictly positive!"
        assert np.all(z_vals <= 1.0), "z_monster_whit must not exceed 1.0!"
        assert np.all(e_vals >= 0.0), "e_monster_whit must be non-negative!"

        # When all pillars are identical, defect and obstruction must be exactly 0, FERI == 1.0
        identical_idx = [1, 2, 6]  # [-1000, ...], [1000, ...], [0, ...]
        for idx in identical_idx:
            assert math.isclose(feri_vals[idx], 1.0, abs_tol=1e-7), f"Identical pillars at row {idx} did not yield FERI=1.0"
            assert math.isclose(e_vals[idx], 0.0, abs_tol=1e-7)
            assert math.isclose(z_vals[idx], 1.0, abs_tol=1e-7)

    def test_coupler_pathological_nan_and_inf_resilience(self):
        """Stress-test coupler with pathological NaN, +Inf, -Inf, and extreme float representations."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=103)

        pathological_data = np.array([
            [np.nan, 10.0, -10.0, 0.0, 5.0],
            [np.inf, -np.inf, np.nan, 1000.0, -1000.0],
            [1e300, -1e300, 1e200, 0.0, np.nan],
            [-np.inf, -np.inf, -np.inf, -np.inf, -np.inf],
        ])

        res = coupler.couple_signals(pathological_data)
        feri_vals = np.asarray(res["FERI_v103"])

        assert np.all(np.isfinite(feri_vals)), "Pathological NaN/Inf inputs caused non-finite FERI_v103!"
        assert np.all(feri_vals > 0.0)
        assert np.all(feri_vals <= 1.0)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Invariant Evaluation: 218th Chiral Oper & 130th Topological Defect
    # ─────────────────────────────────────────────────────────────────────────
    def test_invariant_218th_order_chiral_oper_defect_evaluation(self):
        """Empirically verify activation and contribution of 218th-order chiral oper defect complex."""
        coupler103 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=103)
        coupler102 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=102)

        assert coupler103.is_phase103 is True
        assert coupler102.is_phase103 is False

        # Input designed to maximize diff_safe up to ceiling of 25.0
        p_test = np.array([[25.0, 0.0, 0.0, 0.0, 0.0]])
        res103 = coupler103.couple_signals(p_test)
        res102 = coupler102.couple_signals(p_test)

        e_103 = float(res103["e_monster_whit"][0])
        e_102 = float(res102["e_monster_whit"][0])

        # The 218th-order term adds (1/218) * (lambda_conformal * 4e-33) * (25.0 ** 218)
        # Scaled by omega weights across all pairs involving pillar 0
        assert e_103 > e_102, "Phase 103 obstruction energy must exceed Phase 102 due to 218th-order term!"
        e_diff = e_103 - e_102
        assert e_diff > 1e265, f"Expected massive finite higher-order energy contribution, got {e_diff}"
        assert math.isfinite(e_103), "Obstruction energy e_monster_whit must be strictly finite!"

    def test_invariant_130th_order_topological_defect_evaluation(self):
        """Empirically verify activation and contribution of 130th-order topological defect invariant."""
        coupler103 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=103)
        coupler102 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=102)

        # Input designed to maximize asymmetric difference with pn_safe up to 50.0
        p_test = np.array([[50.0, 0.0, 0.0, 0.0, 0.0]])
        res103 = coupler103.couple_signals(p_test)
        res102 = coupler102.couple_signals(p_test)

        z_103 = float(res103["z_monster_whit"][0])
        z_102 = float(res102["z_monster_whit"][0])

        # The 130th-order term adds (lambda_vertex * 1e-36) * (50.0 ** 130 - 0.0)
        # Since z = 1 / (1 + defect), higher defect strictly decreases z_monster_whit
        assert z_103 < z_102, "Phase 103 topological invariant z must be strictly smaller than Phase 102 due to 130th-order defect!"
        assert z_103 > 0.0, "z_monster_whit must remain strictly positive!"
        assert math.isfinite(z_103), "z_monster_whit must be finite!"

        # Theoretical scaling: 50^130 / 50^128 = 50^2 = 2500 factor between v103 defect and v102 defect
        # Since defect >> 1, z ≈ 1 / defect, so z_102 / z_103 ≈ 2500
        ratio = z_102 / z_103
        assert math.isclose(ratio, 2500.0, rel_tol=1e-2), f"Expected defect scaling ratio ≈ 2500.0, got {ratio}"

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Coupler Version Gating & Backward Compatibility down to v48
    # ─────────────────────────────────────────────────────────────────────────
    def test_coupler_version_gating_and_backward_compatibility_v48_to_v103(self):
        """Verify version=103 gating and backward compatibility down to v48."""
        p_test = np.array([[0.15, 0.25, -0.10, 0.05, 0.30]])

        # Test version 103 properties
        coupler103 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=103)
        assert coupler103.version >= 103
        assert coupler103.is_phase103 is True
        assert math.isclose(coupler103.kappa_monster_whit, 44.00, abs_tol=1e-5)
        assert coupler103.lambda_monster >= 0.999999999999999999999999999  # 27-nines
        assert math.isclose(coupler103.harmony_boost, 12.35, abs_tol=1e-5)

        res103 = coupler103.couple_signals(p_test)
        assert "FERI_v103" in res103
        assert "feri_v103" in res103
        assert "f_out_103" in res103
        assert "FERI_v102" in res103
        assert "FERI_v48" in res103

        # Test version 102 properties and negative version gating
        coupler102 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=102)
        assert coupler102.is_phase103 is False
        assert math.isclose(coupler102.kappa_monster_whit, 43.40, abs_tol=1e-5)
        assert math.isclose(coupler102.harmony_boost, 12.00, abs_tol=1e-5)

        res102 = coupler102.couple_signals(p_test)
        assert "FERI_v103" not in res102, "FERI_v103 must NOT be emitted when version=102!"
        assert "feri_v103" not in res102
        assert "f_out_103" not in res102
        assert "FERI_v102" in res102
        assert "FERI_v48" in res102

        # Comprehensive version sweep from v48 to v103
        version_checkpoints = [48, 50, 55, 60, 66, 70, 73, 74, 80, 86, 90, 95, 98, 100, 101, 102, 103]
        for v in version_checkpoints:
            c_v = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=v)
            r_v = c_v.couple_signals(p_test)
            assert f"FERI_v{v}" in r_v, f"Missing FERI_v{v} for version {v}"
            if v < 103:
                assert "FERI_v103" not in r_v, f"FERI_v103 erroneously present for version {v}!"
            assert "FERI_v48" in r_v, f"FERI_v48 backward compatibility broken for version {v}"

    # ─────────────────────────────────────────────────────────────────────────
    # 4. combine_predictions Integration with Phase 103 Engine
    # ─────────────────────────────────────────────────────────────────────────
    def test_combine_predictions_phase103_deadband_and_rank_modulation(self):
        """Empirically test combine_predictions triggering Phase 103 deadband, rank modulation, and coupler."""
        engine = EnsembleScoringEngine()

        # Adversarial prediction batch:
        # 1. Micro noise in deadband: |z| <= 0.0003
        # 2. Strong conviction positive signals
        # 3. Strong conviction negative signals
        reg_df = pd.DataFrame({
            "symbol": [f"SYM_{i}" for i in range(25)],
            "predicted_return": [
                0.0001, -0.0002, 0.00005, -0.00015, 0.0003, # micro noise
                0.20, 0.35, 0.50, 0.80, 1.20, 2.00, 3.50,   # high conviction positive
                -0.20, -0.35, -0.50, -0.80, -1.20, -2.00,    # high conviction negative
                0.05, 0.08, 0.10, 0.12, 0.14, 0.16, 0.18    # moderate positive
            ],
            "market": ["SP500"] * 25
        })

        out103 = engine.combine_predictions(reg_df=reg_df, version=103)
        out102 = engine.combine_predictions(reg_df=reg_df, version=102)

        assert not out103.empty
        assert len(out103) == 25
        assert "ensemble_expected_return" in out103.columns
        assert "net_expected_return" in out103.columns

        # Verify output is sorted descending by expected return
        exp_rets_103 = out103["ensemble_expected_return"].values
        diffs = np.diff(exp_rets_103)
        assert np.all(diffs <= 1e-9), "combine_predictions must sort assets descending by expected return!"

        # Top asset in v103 must have stronger hyper-convex rank modulation boost than v102
        top_ret_103 = out103["ensemble_expected_return"].iloc[0]
        top_ret_102 = out102["ensemble_expected_return"].iloc[0]
        assert top_ret_103 > top_ret_102, f"Phase 103 top decile boost ({top_ret_103}) should exceed Phase 102 ({top_ret_102})!"

        # All values finite
        assert np.all(np.isfinite(out103["ensemble_expected_return"].values))
        assert np.all(np.isfinite(out103["net_expected_return"].values))

        # Gate 8 inverse hedge support: minimum expected return allows negative returns down to -50.0
        min_ret_103 = out103["ensemble_expected_return"].min()
        assert min_ret_103 >= -50.0, f"Expected return clipped below -50.0: {min_ret_103}"

    def test_combine_predictions_adversarial_degenerate_inputs(self):
        """Stress-test combine_predictions with degenerate inputs (empty, singletons, extreme returns)."""
        engine = EnsembleScoringEngine()

        # Empty DataFrame
        empty_df = pd.DataFrame(columns=["symbol", "predicted_return", "market"])
        out_empty = engine.combine_predictions(reg_df=empty_df, version=103)
        assert out_empty.empty

        # Singleton DataFrame
        singleton_df = pd.DataFrame({"symbol": ["AAPL"], "predicted_return": [0.25], "market": ["SP500"]})
        out_single = engine.combine_predictions(reg_df=singleton_df, version=103)
        assert len(out_single) == 1
        assert np.isfinite(out_single["ensemble_expected_return"].iloc[0])

        # Extreme returns [-1000.0, 1000.0]
        extreme_df = pd.DataFrame({
            "symbol": ["A", "B", "C", "D", "E"],
            "predicted_return": [1000.0, -1000.0, 500.0, -500.0, 0.0],
            "market": ["SP500"] * 5
        })
        out_extreme = engine.combine_predictions(reg_df=extreme_df, version=103)
        assert len(out_extreme) == 5
        assert np.all(np.isfinite(out_extreme["ensemble_expected_return"].values))

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Isotonic PAVA & Multi-Horizon Monotonicity Stress Testing
    # ─────────────────────────────────────────────────────────────────────────
    def test_adversarial_isotonic_pava_stress(self):
        """Adversarial stress-test of isotonic PAVA projection under extreme inversions."""
        # Worst-case strictly decreasing array of 1,000 points
        strictly_decreasing = np.linspace(100.0, -100.0, 1000)
        proj = isotonic_pava(strictly_decreasing)

        assert len(proj) == 1000
        assert np.all(np.diff(proj) >= -1e-12), "PAVA projection failed to enforce non-decreasing sequence!"
        # In strictly decreasing sequence, uniform weights mean all points collapse to global mean
        expected_mean = float(np.mean(strictly_decreasing))
        assert math.isclose(proj[0], expected_mean, abs_tol=1e-9)
        assert math.isclose(proj[-1], expected_mean, abs_tol=1e-9)

        # Extreme oscillating zig-zag
        zigzag = np.array([1.0, 0.0, 1.0, 0.0, 1.0, 0.0] * 50)
        proj_zz = isotonic_pava(zigzag)
        assert np.all(np.diff(proj_zz) >= -1e-12)
        assert math.isclose(proj_zz[0], 0.5, abs_tol=1e-9)
        assert math.isclose(proj_zz[-1], 0.5, abs_tol=1e-9)

    def test_adversarial_multi_horizon_monotonicity_stress(self):
        """Adversarial stress-test of multi-horizon monotonicity regularizer."""
        df_inverted = pd.DataFrame({
            "symbol": [f"STOCK_{i}" for i in range(100)],
            "surge_1d": np.random.uniform(0.70, 0.95, size=100),
            "surge_3d": np.random.uniform(0.50, 0.69, size=100),
            "surge_5d": np.random.uniform(0.30, 0.49, size=100),
            "surge_20d": np.random.uniform(0.05, 0.29, size=100),
        })

        out = regularize_multi_horizon_monotonicity(df_inverted, horizons=[1, 3, 5, 20])
        for idx in range(len(out)):
            p1 = out.loc[idx, "surge_1d"]
            p3 = out.loc[idx, "surge_3d"]
            p5 = out.loc[idx, "surge_5d"]
            p20 = out.loc[idx, "surge_20d"]
            assert p1 <= p3 + 1e-9
            assert p3 <= p5 + 1e-9
            assert p5 <= p20 + 1e-9
            assert 0.0 <= p1 <= 1.0
            assert 0.0 <= p20 <= 1.0

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Deadband Extreme Exponent Stress Testing
    # ─────────────────────────────────────────────────────────────────────────
    def test_adversarial_deadband_exact_zero_and_symmetry(self):
        """Stress-test 632nd-order hyperbolic deadband exact zero threshold and odd symmetry."""
        # 1. Exact zero in [-0.0003, 0.0003]
        micro_grid = np.linspace(-0.0003, 0.0003, 1000)
        out_zero = apply_sexcentoduotrigesimal_hyperbolic_deadband(micro_grid)
        for val in out_zero:
            assert val == 0.0, f"Micro noise leaked through deadband: {val}"

        # 2. Odd symmetry f(-z) == -f(z) across range [-10.0, 10.0]
        test_z = np.linspace(0.001, 10.0, 500)
        pos_out = apply_sexcentoduotrigesimal_hyperbolic_deadband(test_z)
        neg_out = apply_sexcentoduotrigesimal_hyperbolic_deadband(-test_z)
        np.testing.assert_allclose(pos_out, -neg_out, atol=1e-12)

        # 3. Extreme value |z| = 1000.0
        ext_pos = apply_sexcentoduotrigesimal_hyperbolic_deadband(1000.0)
        ext_neg = apply_sexcentoduotrigesimal_hyperbolic_deadband(-1000.0)
        assert math.isclose(ext_pos, 1000.0, rel_tol=1e-6)
        assert math.isclose(ext_neg, -1000.0, rel_tol=1e-6)
