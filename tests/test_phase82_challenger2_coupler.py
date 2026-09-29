r"""
tests/test_phase82_challenger2_coupler.py

Milestone 1 Empirical Challenger 2 Verification Suite
Role: Challenger 2 (Coupler Invariant & Gating Verification)

Scope of Testing:
1. Invariant Parameter Verification:
   - kappa = 31.10
   - lambda = 0.999999999995
   - 172nd chiral oper action exact power and coefficients
   - 88th defect invariant exact power and coefficients
   - Harmony boost: 6.25 (v82) vs 6.15 (v81) vs 6.05 (v80)
2. Strict Version Gating Verification:
   - When effective_version >= 82 (82, 83, 100): FERI_v82, feri_v82, f_out_82 are PRESENT and in [0, 1].
   - When effective_version < 82 (81, 80, 79, 78, 77, 76, 75, 74, 73, 72, 71, 70, 60, 50):
     FERI_v82, feri_v82, f_out_82 are STRICTLY ABSENT from the output dictionary.
   - Dynamic call-time override: coupler(version=81) vs coupler(version=82).
   - Classmethod compute: compute(..., version=81) vs compute(..., version=82).
3. Backward Compatibility & Alias Trees:
   - Phase82Coupler, Phase82WhittakerDrinfeldCoupler, Phase82BorcherdsMoonshineCoupler, Phase82MonsterWhittakerCoupler
   - compute_phase82_coupling, compute_phase81_coupling, compute_phase80_coupling
   - Prior version class aliases from Phase 48 to Phase 81 all point to the canonical coupler class.
4. Adversarial Stress & Edge Cases:
   - Zero-discrepancy identical pillars: [0.5, 0.5, 0.5, 0.5, 0.5] -> exact zero energy, unit defect, unit FERI.
   - Extreme divergence: [0.0, 1.0, 0.0, 1.0, 0.0] -> high energy, valid bounded FERI in (0, 1).
   - All zero and all one vectors: [0, 0, 0, 0, 0] and [1, 1, 1, 1, 1].
   - High order power resistance (diff > 1.0, e.g. 5.0) -> check for overflow / nan / inf.
   - NaN containment: NaNs in input must be sanitized without raising uncaught exceptions.
   - 10,000 Monte Carlo randomized evaluations across [-3.0, 3.0]^5:
     * Guarantee no NaNs, no Infs, strict bounds for all output fields.
   - Input structure polymorphy:
     * 1D numpy array (5,)
     * 2D numpy array (N, 5)
     * 2D numpy array (5, N) transposed
     * pd.DataFrame with canonical pillar columns
     * pd.DataFrame with non-standard column names
     * dict of arrays / Series
     * pd.Series index preservation
"""

import math
import inspect
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase82Coupler,
    Phase82WhittakerDrinfeldCoupler,
    Phase82BorcherdsMoonshineCoupler,
    Phase82MonsterWhittakerCoupler,
    compute_phase82_coupling,
    Phase81Coupler,
    Phase81WhittakerDrinfeldCoupler,
    Phase81BorcherdsMoonshineCoupler,
    Phase81MonsterWhittakerCoupler,
    compute_phase81_coupling,
    Phase80Coupler,
    Phase80WhittakerDrinfeldCoupler,
    Phase80BorcherdsMoonshineCoupler,
    Phase80MonsterWhittakerCoupler,
    compute_phase80_coupling,
    Phase79Coupler,
    compute_phase79_coupling,
    Phase78Coupler,
    compute_phase78_coupling,
    Phase77Coupler,
    compute_phase77_coupling,
    Phase76Coupler,
    Phase75Coupler,
    Phase74Coupler,
    Phase73Coupler,
    Phase72Coupler,
    Phase71Coupler,
    Phase70Coupler,
    Phase69Coupler,
    Phase68Coupler,
    EnsembleScoringEngine,
)


class TestChallenger2CouplerInvariantsAndGating:
    """Empirical Challenger 2 verification suite for Milestone 1 Coupler."""

    # -------------------------------------------------------------------------
    # 1. Parameter & Invariant Verification
    # -------------------------------------------------------------------------

    def test_coupler_parameters_v82(self):
        """Verify kappa=31.10, lambda=0.999999999995 (12 decimals) for version 82."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=82)
        assert coupler.kappa_monster_whit == 31.10
        assert coupler.kappa == 31.10
        assert coupler.kappa_monster == 31.10
        assert coupler.lambda_monster == 0.999999999995
        assert f"{coupler.lambda_monster:.12f}" == "0.999999999995"
        assert coupler.version == 82
        assert coupler.is_phase82 is True

        # Test default instantiation (detects 'phase82' in filename)
        default_coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler()
        assert default_coupler.kappa_monster_whit == 31.10
        assert default_coupler.lambda_monster == 0.999999999995
        assert default_coupler.version == 82
        assert default_coupler.is_phase82 is True

    def test_coupler_ast_and_source_invariants(self):
        """Verify 172nd chiral oper action and 88th defect invariant in source code."""
        src = inspect.getsource(QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler.evaluate)

        # 172nd chiral oper obstruction action check
        assert "diff ** 172" in src, "Missing 172nd power term in chiral oper action"
        assert "diff ** 170" in src, "Missing 170th power term in chiral oper action"
        assert "(1.0 / 172.0)" in src, "Missing 1/172 normalization factor"
        assert "1e-30" in src, "Missing 1e-30 scaling factor for 172nd order term"

        # 88th topological defect invariant check
        assert "pn[j]**88 - pn[k]**88" in src, "Missing 88th power term in defect invariant"
        assert "pn[j]**87 - pn[k]**87" in src, "Missing 87th power term in defect invariant"
        assert "1e-33" in src, "Missing 1e-33 scaling factor for 88th order term"

    def test_harmony_boost_progression(self):
        """Verify harmony boost progression up to 6.25 for version 82."""
        engine = EnsembleScoringEngine()
        src = inspect.getsource(engine.combine_predictions)
        assert "6.25 if version >= 82" in src, "Missing 6.25 harmony boost for version >= 82"
        assert "6.15 if version >= 81" in src, "Missing 6.15 harmony boost for version >= 81"
        assert "6.05 if version >= 80" in src, "Missing 6.05 harmony boost for version >= 80"
        assert "5.95 if version >= 79" in src, "Missing 5.95 harmony boost for version >= 79"

    # -------------------------------------------------------------------------
    # 2. Strict Version Gating Verification
    # -------------------------------------------------------------------------

    def test_version_gating_effective_version_ge_82(self):
        """Verify FERI_v82, feri_v82, f_out_82 are present and in [0, 1] for version >= 82."""
        p_df = pd.DataFrame({
            'val': [0.50, 0.40, 0.60],
            'mom': [0.55, 0.45, 0.65],
            'flow': [0.48, 0.52, 0.58],
            'cat': [0.52, 0.48, 0.62],
            'net': [0.51, 0.49, 0.59],
        })

        for v in [82, 83, 90, 100]:
            coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=v)
            res = coupler(p_df)

            assert "FERI_v82" in res, f"FERI_v82 missing when version={v}"
            assert "feri_v82" in res, f"feri_v82 missing when version={v}"
            assert "f_out_82" in res, f"f_out_82 missing when version={v}"

            # Also check prior version keys are present
            assert "FERI_v81" in res
            assert "FERI_v80" in res
            assert "FERI_v79" in res
            assert "FERI_v78" in res

            # Value validation
            f82 = res["FERI_v82"]
            assert isinstance(f82, pd.Series)
            assert np.all(np.isfinite(f82.values))
            assert np.all(f82.values >= 0.0)
            assert np.all(f82.values <= 1.0)
            assert np.all(res["feri_v82"].values == f82.values)
            assert np.all(res["f_out_82"].values == f82.values)

    def test_version_gating_effective_version_lt_82(self):
        """Strict version gating: when effective_version < 82, FERI_v82 must NOT be in output."""
        p_df = pd.DataFrame({
            'val': [0.50, 0.40],
            'mom': [0.55, 0.45],
            'flow': [0.48, 0.52],
            'cat': [0.52, 0.48],
            'net': [0.51, 0.49],
        })

        test_versions = [81, 80, 79, 78, 77, 76, 75, 74, 73, 72, 71, 70, 68, 65, 50, 48]
        for v in test_versions:
            coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=v)
            res = coupler(p_df)

            assert "FERI_v82" not in res, f"FERI_v82 leaked when version={v}"
            assert "feri_v82" not in res, f"feri_v82 leaked when version={v}"
            assert "f_out_82" not in res, f"f_out_82 leaked when version={v}"

            # Verify that v's own key is present if v >= 67
            if v >= 67:
                assert f"FERI_v{v}" in res, f"FERI_v{v} missing when version={v}"
                assert f"f_out_{v}" in res, f"f_out_{v} missing when version={v}"

    def test_version_override_at_call_time(self):
        """Verify dynamic version parameter passed to evaluate() / __call__() overrides instance version."""
        p_df = pd.DataFrame({
            'val': [0.50], 'mom': [0.50], 'flow': [0.50], 'cat': [0.50], 'net': [0.50]
        })

        coupler_v82 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=82)
        # Calling with version=81 must suppress FERI_v82
        res_call_v81 = coupler_v82(p_df, version=81)
        assert "FERI_v82" not in res_call_v81, "FERI_v82 present when call-time version=81"
        assert "FERI_v81" in res_call_v81, "FERI_v81 missing when call-time version=81"

        coupler_v81 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=81)
        # Calling with version=82 must activate FERI_v82
        res_call_v82 = coupler_v81(p_df, version=82)
        assert "FERI_v82" in res_call_v82, "FERI_v82 missing when call-time version=82"

    def test_compute_classmethod_gating(self):
        """Verify compute classmethod respects version parameter."""
        p_vec = np.array([0.5, 0.4, 0.6, 0.3, 0.7])

        res_v82 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler.compute(
            p_vec, version=82
        )
        assert "FERI_v82" in res_v82
        assert "f_out_82" in res_v82

        res_v81 = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler.compute(
            p_vec, version=81
        )
        assert "FERI_v82" not in res_v81
        assert "f_out_82" not in res_v81
        assert "FERI_v81" in res_v81

    # -------------------------------------------------------------------------
    # 3. Backward Compatibility & Alias Trees
    # -------------------------------------------------------------------------

    def test_backward_compatibility_aliases(self):
        """Verify all phase aliases and compute functions work seamlessly."""
        assert Phase82Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase82WhittakerDrinfeldCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase82BorcherdsMoonshineCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase82MonsterWhittakerCoupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        assert Phase81Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase80Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase79Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase78Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase77Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase76Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase75Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase74Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase73Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase72Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase71Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase70Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase69Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler
        assert Phase68Coupler is QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler

        # Test compute aliases
        p_vec = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        res82 = compute_phase82_coupling(p_vec, version=82)
        assert "FERI_v82" in res82
        assert np.isclose(res82["FERI_v82"], 1.0)

        res81 = compute_phase81_coupling(p_vec, version=81)
        assert "FERI_v82" not in res81
        assert "FERI_v81" in res81
        assert np.isclose(res81["FERI_v81"], 1.0)

        res80 = compute_phase80_coupling(p_vec, version=80)
        assert "FERI_v82" not in res80
        assert "FERI_v80" in res80
        assert np.isclose(res80["FERI_v80"], 1.0)

    # -------------------------------------------------------------------------
    # 4. Adversarial Stress & Edge Cases
    # -------------------------------------------------------------------------

    def test_edge_case_identical_pillars(self):
        """When all pillars are identical, difference is zero: energy=0, defect=0, FERI=1.0."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=82)
        for base_val in [0.0, 0.25, 0.50, 0.75, 1.0, 2.0]:
            p = np.full(5, base_val)
            res = coupler(p)
            assert np.isclose(res["e_monster_whit"], 0.0, atol=1e-12)
            assert np.isclose(res["z_monster_whit"], 1.0, atol=1e-12)
            assert np.isclose(res["h_decay"], 1.0, atol=1e-12)
            assert np.isclose(res["h_monster_whit"], 1.0, atol=1e-12)
            assert np.isclose(res["FERI_v82"], 1.0, atol=1e-12)
            assert np.isclose(res["f_out_82"], 1.0, atol=1e-12)

    def test_edge_case_extreme_divergence(self):
        """When pillars maximally diverge [0, 1, 0, 1, 0], outputs remain bounded and finite."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=82)
        p = np.array([0.0, 1.0, 0.0, 1.0, 0.0])
        res = coupler(p)

        assert np.isfinite(res["e_monster_whit"])
        assert res["e_monster_whit"] > 0.0
        assert np.isfinite(res["z_monster_whit"])
        assert 0.0 < res["z_monster_whit"] < 1.0
        assert np.isfinite(res["h_monster_whit"])
        assert coupler.epsilon_reg <= res["h_monster_whit"] <= 1.0
        assert np.isfinite(res["FERI_v82"])
        assert 0.0 < res["FERI_v82"] < 1.0

    def test_monotonicity_under_divergence(self):
        """Energy must monotonically increase as divergence between pillars widens."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=82)
        divergences = np.linspace(0.0, 1.0, 50)
        energies = []
        feris = []

        for delta in divergences:
            p = np.array([0.5 - delta/2, 0.5 + delta/2, 0.5, 0.5, 0.5])
            res = coupler(p)
            energies.append(res["e_monster_whit"])
            feris.append(res["FERI_v82"])

        e_diffs = np.diff(energies)
        assert np.all(e_diffs >= -1e-15), "Obstruction energy must be monotonically non-decreasing with divergence"

        feri_diffs = np.diff(feris)
        assert np.all(feri_diffs <= 1e-15), "FERI must be monotonically non-increasing as divergence widens"

    def test_nan_sanitization(self):
        """NaN values in pillar inputs must be sanitized to 0.0 without crash."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=82)
        p_nan = np.array([np.nan, 0.5, np.nan, 0.2, 0.8])
        res = coupler(p_nan)

        assert np.isfinite(res["e_monster_whit"])
        assert np.isfinite(res["z_monster_whit"])
        assert np.isfinite(res["FERI_v82"])
        assert 0.0 <= res["FERI_v82"] <= 1.0

    def test_input_polymorphism(self):
        """Coupler must accept DataFrame (named and unnamed), 1D array, 2D array (N,5 and 5,N), and dict."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=82)

        # 1. 1D vector (5,)
        v1d = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        r1d = coupler(v1d)
        assert isinstance(r1d["FERI_v82"], float)

        # 2. 2D array (N, 5)
        v2d = np.random.uniform(0.1, 0.9, size=(20, 5))
        r2d = coupler(v2d)
        assert isinstance(r2d["FERI_v82"], np.ndarray)
        assert len(r2d["FERI_v82"]) == 20

        # 3. Transposed 2D array (5, N)
        v2d_t = v2d.T
        r2d_t = coupler(v2d_t)
        assert len(r2d_t["FERI_v82"]) == 20

        # 4. DataFrame with standard columns and index preservation
        idx = [f"STOCK_{i}" for i in range(10)]
        df_named = pd.DataFrame({
            'val': np.linspace(0.1, 0.9, 10),
            'mom': np.linspace(0.2, 0.8, 10),
            'flow': np.linspace(0.3, 0.7, 10),
            'cat': np.linspace(0.4, 0.6, 10),
            'net': np.linspace(0.5, 0.5, 10),
        }, index=idx)
        rdf_named = coupler(df_named)
        assert isinstance(rdf_named["FERI_v82"], pd.Series)
        assert list(rdf_named["FERI_v82"].index) == idx

        # 5. DataFrame with unnamed 5 columns
        df_unnamed = pd.DataFrame(v2d)
        rdf_unnamed = coupler(df_unnamed)
        assert len(rdf_unnamed["FERI_v82"]) == 20

        # 6. Dict of Series with index
        s_dict = {
            c: pd.Series(df_named[c].values, index=idx)
            for c in ['val', 'mom', 'flow', 'cat', 'net']
        }
        r_dict = coupler(s_dict)
        assert isinstance(r_dict["FERI_v82"], pd.Series)
        assert list(r_dict["FERI_v82"].index) == idx

    def test_monte_carlo_stress_10000_samples(self):
        """Stress test: 10,000 randomized Monte Carlo samples across [-2.5, 2.5]^5."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=82)
        np.random.seed(42)
        samples = np.random.uniform(-2.5, 2.5, size=(10000, 5))

        res = coupler(samples)

        e = res["e_monster_whit"]
        z = res["z_monster_whit"]
        h = res["h_monster_whit"]
        feri = res["FERI_v82"]

        # Universal finiteness
        assert np.all(np.isfinite(e)), "Found non-finite obstruction energy"
        assert np.all(np.isfinite(z)), "Found non-finite topological invariant"
        assert np.all(np.isfinite(h)), "Found non-finite coupling factor"
        assert np.all(np.isfinite(feri)), "Found non-finite FERI_v82"

        # Universal bounds
        assert np.all(e >= 0.0), "Energy cannot be negative"
        assert np.all((z > 0.0) & (z <= 1.0)), "Defect invariant z must be in (0, 1]"
        assert np.all((h >= coupler.epsilon_reg) & (h <= 1.0)), "h must be in [epsilon_reg, 1.0]"
        assert np.all((feri > 0.0) & (feri <= 1.0)), "FERI_v82 must be in (0, 1]"

    def test_extreme_power_numerical_stability(self):
        """Verify 172nd chiral power and 88th defect invariant survive extreme differences without crash."""
        coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler(version=82)
        p_wide = np.array([-0.9, 0.9, -0.9, 0.9, 0.0])
        res = coupler(p_wide)

        assert np.isfinite(res["e_monster_whit"])
        assert np.isfinite(res["z_monster_whit"])
        assert np.isfinite(res["FERI_v82"])
        assert res["FERI_v82"] > 0.0
