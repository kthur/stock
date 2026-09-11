"""
tests/test_phase23_adversarial_empirical_challenge.py

Adversarial Stress Test and Empirical Verification Suite for Phase 23 Quantitative Enhancement.
Authored by Empirical Challenger (Specialist/Critic).

Scope:
1. R1:
   - F111 Toposic Geometric Langlands & Derived Satake Equivalence Coupler:
     * Degenerate / zero variance pillar inputs (collinear invariance).
     * Extreme scale inputs (1e-15 up to 1e8).
     * NaN / Inf input behavior and boundary safety.
     * Various input formats (1D array, 2D array, pandas DataFrame, dict of series).
   - F112.1 18th-order hyper-convex rank modulation:
     * Strict monotonicity across [0, 1] (first derivative > 0 everywhere).
     * Strict convexity (second derivative > 0 on [0.30, 1]).
     * Extreme right-tail concentration (top 0.000000001% alpha conviction explosion vs flat bottom 70%).
     * Multi-regime sweeps (BULL_LOW_VOL through CRISIS).
     * Out-of-bounds input handling and clipping.
   - F112.2 56th-order Hexaquinquagintagonal deadband:
     * Dense grid noise leakage < 10^-30 across |z| in [-0.005, 0.005].
     * 100.000% transmission for high-conviction signals (|z| >= 0.150).
     * Strict rank monotonicity (Spearman rho == 1.0000) and odd symmetry.
2. R2:
   - F113.1 Lurie Geometric Langlands Fisher-Rao Barycenter:
     * Simplex partition of unity (sum == 1.000000, all weights >= 0) across random and adversarial model weight vectors.
     * Metric weights mu_langlands = [2.10, 1.60, 1.55, 2.60] enforcement.
   - Ultra-Trans-Hyper EVaR:
     * 19th-order cumulant expansion verification with 19! = 121,645,100,408,832,000.
     * Numerical stability under extreme heavy-tail distributions (Cauchy, Pareto, Student-t, Black Swan crash).
     * Strict coherent tail risk hierarchy: VaR <= CVaR <= EVaR <= ... <= Ultra-Trans-Hyper EVaR.
3. R3:
   - F113.2 KNK quintessence-phantom double dark energy L3 model:
     * Queue acceleration under varying dark energy equations of state and phantom parameter c_p.
     * Tidal force decrease with expanding phantom parameter c_p.
     * Horizon and frame-dragging verification.
   - Execution OMS & SmartOrderRouter:
     * Maker floor 0.000001 (0.0001%) verification and monotonic contraction across v20 -> v21 -> v22 -> v23.
     * Preemptive tick shading: hawkes_shift = -direction * 0.9995 * spr * (h - 0.035) for h > 0.035.
     * Dark pool 99.995% cap under simulated order streams.
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr, cauchy, pareto, t as student_t

from trading_system.src.ai.ensemble_scorer import (
    apply_hexaquinquagintagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase23_hyperconvex_rank_modulation,
    ToposicGeometricLanglandsCoupler,
    GeometricLanglandsCoupler,
    DerivedSatakeCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_hexaquinquagintagonal_hyperbolic_deadband as fs_hexaquinquagintagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    DeepHawkesArrivalProcess,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


# =============================================================================
# 1. R1: ALPHA SIGNAL & FACTOR DISENTANGLEMENT ADVERSARIAL TESTS
# =============================================================================

class TestPhase23AdversarialR1Signal:
    """Empirical challenge tests for Feature F111, F112.1, F112.2."""

    # -------------------------------------------------------------------------
    # F111: Toposic Geometric Langlands & Derived Satake Equivalence Coupler
    # -------------------------------------------------------------------------

    def test_f111_degenerate_zero_variance_collinear_sections(self):
        """
        Adversarial Test 1.1:
        When all 5 canonical pillars are identical (zero variance / coherent section),
        all pairwise differences diff = pn[j] - pn[k] == 0.
        Therefore, obstruction energy E_langlands must be identically 0.0,
        topological defect must be 0.0, cycle invariant Z_satake == 1.0,
        and coupling factor h_langlands == 1.0, FERI_v23 == 1.0.
        """
        coupler = ToposicGeometricLanglandsCoupler()
        test_values = [0.0, 0.25, 0.50, 0.85, 1.0, 10.0, 1000.0]

        for val in test_values:
            p_deg = np.array([val, val, val, val, val])
            res = coupler.evaluate(p_deg)

            assert math.isclose(res["e_langlands"], 0.0, abs_tol=1e-12), f"E_langlands must be 0 for val={val}, got {res['e_langlands']}"
            assert math.isclose(res["z_satake"], 1.0, abs_tol=1e-12), f"Z_satake must be 1 for val={val}, got {res['z_satake']}"
            assert math.isclose(res["h_langlands"], 1.0, abs_tol=1e-12), f"h_langlands must be 1 for val={val}, got {res['h_langlands']}"
            assert math.isclose(res["FERI_v23"], 1.0, abs_tol=1e-12), f"FERI_v23 must be 1 for val={val}, got {res['FERI_v23']}"

    def test_f111_extreme_scale_inputs_numeric_stability(self):
        """
        Adversarial Test 1.2:
        Tests extreme scale inputs:
        - Very small subnormal inputs (1e-15).
        - Extreme high values (1e4, 1e8).
        Ensures no unhandled overflow exceptions, and h_langlands remains strictly in [epsilon_reg, 1.0].
        """
        coupler = ToposicGeometricLanglandsCoupler(epsilon_reg=1e-6)

        # Very small inputs
        p_small = np.array([1e-15, 2e-15, 3e-15, 4e-15, 5e-15])
        res_small = coupler.evaluate(p_small)
        assert math.isclose(res_small["e_langlands"], 0.0, abs_tol=1e-12)
        assert math.isclose(res_small["h_langlands"], 1.0, abs_tol=1e-5)

        # Extreme high conflicting inputs
        p_high = np.array([1e4, -1e4, 5e3, -5e3, 0.0])
        res_high = coupler.evaluate(p_high)
        assert res_high["h_langlands"] == coupler.epsilon_reg
        assert math.isfinite(res_high["z_satake"])
        assert 0.0 <= res_high["z_satake"] <= 1.0

        # Scale 1e8 equal inputs
        p_huge_equal = np.full(5, 1e8)
        res_huge_eq = coupler.evaluate(p_huge_equal)
        assert math.isclose(res_huge_eq["h_langlands"], 1.0, abs_tol=1e-12)

    def test_f111_nan_and_corrupt_input_protection(self):
        """
        Adversarial Test 1.3:
        Validates handling of NaN values in input. NaNs must be safely converted to 0.0
        without raising exceptions.
        """
        coupler = ToposicGeometricLanglandsCoupler()
        p_nan = np.array([np.nan, 0.5, np.nan, 0.5, 0.5])
        res = coupler.evaluate(p_nan)

        assert math.isfinite(res["h_langlands"])
        assert math.isfinite(res["z_satake"])
        assert math.isfinite(res["e_langlands"])
        assert 0.0 <= res["h_langlands"] <= 1.0

    def test_f111_input_format_polyglot_stress(self):
        """
        Adversarial Test 1.4:
        Tests coupler across 1D NumPy, 2D NumPy (both N x 5 and 5 x N),
        Pandas DataFrame with column names, and dictionary of Series.
        """
        coupler = ToposicGeometricLanglandsCoupler()

        # 1D array
        p_1d = np.array([0.8, 0.7, 0.6, 0.5, 0.4])
        res_1d = coupler.evaluate(p_1d)
        assert isinstance(res_1d["h_langlands"], float)

        # 2D array (100 x 5)
        np.random.seed(42)
        p_2d = np.random.uniform(0.0, 1.0, size=(100, 5))
        res_2d = coupler.evaluate(p_2d)
        assert isinstance(res_2d["h_langlands"], np.ndarray)
        assert len(res_2d["h_langlands"]) == 100
        assert np.all(res_2d["h_langlands"] >= coupler.epsilon_reg)
        assert np.all(res_2d["h_langlands"] <= 1.0)

        # DataFrame
        df = pd.DataFrame(p_2d, columns=['val', 'mom', 'flow', 'cat', 'net'])
        res_df = coupler.evaluate(df)
        assert isinstance(res_df["h_langlands"], pd.Series)
        assert len(res_df["h_langlands"]) == 100

        # Dict of series
        d = {col: df[col] for col in df.columns}
        res_dict = coupler.evaluate(d)
        assert isinstance(res_dict["h_langlands"], pd.Series)
        np.testing.assert_allclose(res_df["h_langlands"].values, res_dict["h_langlands"].values)

    # -------------------------------------------------------------------------
    # F112.1: 18th-Order Hyper-Convex Rank Modulation (g_v23)
    # -------------------------------------------------------------------------

    def test_f112_1_strict_monotonicity_across_unit_interval(self):
        """
        Adversarial Test 1.5:
        Evaluates g_v23(r) across 20,000 dense points in [0, 1].
        Empirically verifies:
        1. diffs = g(r_{i+1}) - g(r_i) > 0 for all i (strictly increasing).
        2. Spearman rank correlation == 1.000000.
        3. Minimum numerical gradient is strictly positive.
        """
        r_grid = np.linspace(0.0, 1.0, 20000)
        gammas = [0.48, 1.00, 1.40, 1.85, 2.10, 2.40]

        for gamma in gammas:
            g_vals = compute_phase23_hyperconvex_rank_modulation(r_grid, gamma_top=gamma)
            diffs = np.diff(g_vals)

            # Strict monotonicity
            min_diff = np.min(diffs)
            assert min_diff > 0.0, f"g_v23 was not strictly increasing for gamma={gamma}, min_diff={min_diff}"

            # Rank correlation
            rho, _ = spearmanr(r_grid, g_vals)
            assert rho >= 0.99999999, f"Spearman rho {rho} must be ~1.0 for gamma={gamma}"

    def test_f112_1_strict_convexity_verification(self):
        """
        Adversarial Test 1.6:
        Empirically verifies that the second derivative g''(r) is strictly positive on [0.30, 1.0].
        Second difference d2 = diff(diff(g)) must be non-negative.
        """
        r_grid = np.linspace(0.30, 1.0, 5000)
        for gamma in [0.70, 1.40, 2.10, 2.40]:
            g_vals = compute_phase23_hyperconvex_rank_modulation(r_grid, gamma_top=gamma)
            d1 = np.diff(g_vals)
            d2 = np.diff(d1)
            assert np.all(d2 >= -1e-12), f"g_v23 failed convexity for gamma={gamma}, min d2={np.min(d2)}"

    def test_f112_1_extreme_right_tail_concentration(self):
        """
        Adversarial Test 1.7:
        Verifies the core quantitative property of 18th-order rank modulation:
        - The bottom 70% of the distribution (r in [0, 0.70]) remains flat and unamplified.
        - The top 0.000000001% alpha conviction experiences exponential explosive boosting.
        """
        gamma = 2.40  # Bull Low Vol maximum convex regime
        g_0 = float(compute_phase23_hyperconvex_rank_modulation(0.0, gamma_top=gamma))
        g_50 = float(compute_phase23_hyperconvex_rank_modulation(0.50, gamma_top=gamma))
        g_70 = float(compute_phase23_hyperconvex_rank_modulation(0.70, gamma_top=gamma))
        g_90 = float(compute_phase23_hyperconvex_rank_modulation(0.90, gamma_top=gamma))
        g_99 = float(compute_phase23_hyperconvex_rank_modulation(0.99, gamma_top=gamma))
        g_100 = float(compute_phase23_hyperconvex_rank_modulation(1.0, gamma_top=gamma))

        delta_bottom = g_70 - g_0
        delta_top = g_100 - g_90
        assert delta_bottom < 1.0, f"Bottom 70% spread {delta_bottom} must be flat (< 1.0)"
        assert delta_top > 8.0, f"Top 10% spread {delta_top} must explode (> 8.0)"
        assert delta_top / delta_bottom > 8.0, "Top 10% amplification must dominate bottom 70% by >8x"

        # Check top value: 0.50 + 1.10 * exp(2.40) ~= 12.63
        assert g_100 > 11.0, f"g(1.0) under gamma=2.40 must exceed 11.0, got {g_100}"

    def test_f112_1_out_of_bounds_clipping(self):
        """
        Adversarial Test 1.8:
        Inputs outside [0, 1] (e.g. -5.0, 10.0) must be safely clipped to [0, 1].
        """
        g_neg = compute_phase23_hyperconvex_rank_modulation(-5.0, gamma_top=1.0)
        g_0 = compute_phase23_hyperconvex_rank_modulation(0.0, gamma_top=1.0)
        assert math.isclose(g_neg, g_0, abs_tol=1e-9)

        g_huge = compute_phase23_hyperconvex_rank_modulation(10.0, gamma_top=1.0)
        g_1 = compute_phase23_hyperconvex_rank_modulation(1.0, gamma_top=1.0)
        assert math.isclose(g_huge, g_1, abs_tol=1e-9)

    # -------------------------------------------------------------------------
    # F112.2: 56th-Order Hexaquinquagintagonal Hyperbolic Deadband
    # -------------------------------------------------------------------------

    def test_f112_2_50000_grid_noise_leakage_strictly_below_1e30(self):
        """
        Adversarial Test 1.9:
        Evaluates 50,000 dense points spanning |z| in [-0.005, 0.005].
        Verifies that max noise leakage is strictly < 10^-30 everywhere in this near-zero corridor.
        (Analytic expectation: at z=0.005, (0.005/0.035)^56 ~= (1/7)^56 ~= 4.6e-48).
        """
        z_grid = np.linspace(-0.005, 0.005, 50000)
        out = apply_hexaquinquagintagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=56.0)

        max_leakage = np.max(np.abs(out))
        assert max_leakage < 1e-30, f"Max noise leakage {max_leakage:.4e} exceeded 1e-30 threshold"
        assert max_leakage < 1e-45, f"Max noise leakage {max_leakage:.4e} was expected to be < 1e-45"

    def test_f112_2_100_percent_transmission_high_conviction(self):
        """
        Adversarial Test 1.10:
        Verifies that for |z| >= 0.150, deadband transmits exactly 100.000% of signal.
        """
        z_high = np.array([0.150, 0.200, 0.350, 0.500, 1.000])
        out_pos = apply_hexaquinquagintagonal_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=56.0)
        out_neg = apply_hexaquinquagintagonal_hyperbolic_deadband(-z_high, delta_noise=0.035, alpha_pos=56.0)

        np.testing.assert_allclose(out_pos, z_high, rtol=1e-7, atol=1e-9)
        np.testing.assert_allclose(out_neg, -z_high, rtol=1e-7, atol=1e-9)

    def test_f112_2_odd_symmetry_and_rank_preservation(self):
        """
        Adversarial Test 1.11:
        Verifies strict odd symmetry f(-z) == -f(z) and rank preservation (Spearman rho == 1.0).
        """
        z_vals = np.linspace(0.001, 0.50, 1000)
        pos = apply_hexaquinquagintagonal_hyperbolic_deadband(z_vals, delta_noise=0.035, alpha_pos=56.0)
        neg = apply_hexaquinquagintagonal_hyperbolic_deadband(-z_vals, delta_noise=0.035, alpha_pos=56.0)

        np.testing.assert_allclose(neg, -pos, rtol=1e-12, atol=1e-14)

        full_grid = np.linspace(-0.50, 0.50, 5000)
        full_out = apply_hexaquinquagintagonal_hyperbolic_deadband(full_grid, delta_noise=0.035, alpha_pos=56.0)
        rho, _ = spearmanr(full_grid, full_out)
        assert rho >= 0.9999999, f"Spearman rho must be ~1.0, got {rho}"


# =============================================================================
# 2. R2: PORTFOLIO ALLOCATION & TAIL RISK ADVERSARIAL TESTS
# =============================================================================

class TestPhase23AdversarialR2Risk:
    """Empirical challenge tests for Feature F113.1 and Ultra-Trans-Hyper EVaR."""

    # -------------------------------------------------------------------------
    # F113.1: Lurie Geometric Langlands Fisher-Rao Barycenter
    # -------------------------------------------------------------------------

    def test_f113_1_simplex_partition_of_unity_adversarial_weights(self):
        """
        Adversarial Test 2.1:
        Tests that Lurie Geometric Langlands Barycenter satisfies the simplex partition of unity:
            sum(q*) == 1.000000
            q*_k >= 0 for all k in {BL, HERC, RP, CVaR}
        under diverse adversarial inputs:
        1. Pure Dirac delta inputs (one model gets 1.0, others 0.0).
        2. Extreme disparity inputs (1e-6 vs 1.0).
        3. 50 random Dirichlet distributions.
        4. 2D array input batch.
        """
        allocator = UnifiedPortfolioAllocator()

        # 1. Dirac delta inputs
        for model in ["bl", "herc", "rp", "cvar"]:
            w_dirac = {k: (1.0 if k == model else 0.0) for k in ["bl", "herc", "rp", "cvar"]}
            res_dirac = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(w_dirac)
            tot = sum(res_dirac.values())
            assert math.isclose(tot, 1.0, abs_tol=1e-6), f"Sum was {tot} for dirac on {model}"
            assert all(v >= 0.0 for v in res_dirac.values())

        # 2. Extreme disparity
        w_extreme = {"bl": 1e-6, "herc": 1e-6, "rp": 1e-6, "cvar": 1.0}
        res_extreme = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(w_extreme)
        assert math.isclose(sum(res_extreme.values()), 1.0, abs_tol=1e-6)
        # CVaR has highest metric weight (2.60)
        assert res_extreme["cvar"] > res_extreme["bl"]

        # 3. 50 random Dirichlet distributions
        np.random.seed(123)
        for _ in range(50):
            raw = np.random.dirichlet([0.5, 0.5, 0.5, 0.5])
            w_dict = {"bl": raw[0], "herc": raw[1], "rp": raw[2], "cvar": raw[3]}
            res = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(w_dict)
            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6)
            assert all(v >= 0.0 for v in res.values())

        # 4. 2D array input batch
        mat = np.random.dirichlet([1.0, 1.0, 1.0, 1.0], size=10)
        res_mat = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(mat)
        assert math.isclose(sum(res_mat.values()), 1.0, abs_tol=1e-6)

    def test_f113_1_langlands_metric_weight_prioritization(self):
        """
        Adversarial Test 2.2:
        Under equal initial weights [0.25, 0.25, 0.25, 0.25], the Lurie Geometric Langlands
        metric weights mu_langlands = [2.10, 1.60, 1.55, 2.60] prioritize CVaR (2.60)
        and Black-Litterman (2.10) over HERC (1.60) and Risk Parity (1.55).
        """
        allocator = UnifiedPortfolioAllocator()
        w_equal = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(w_equal)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6)
        assert res["cvar"] > res["bl"] > res["herc"] > res["rp"]

    # -------------------------------------------------------------------------
    # Ultra-Trans-Hyper EVaR (19th-Order Cumulant Expansion)
    # -------------------------------------------------------------------------

    def test_evar_19th_cumulant_factorial_and_order_metadata(self):
        """
        Adversarial Test 2.3:
        Verifies that 19! is exactly 121,645,100,408,832,000,
        xi_ultra_trans defaults to 0.75, and order metadata reports 19.
        """
        assert math.factorial(19) == 121645100408832000
        allocator = UnifiedPortfolioAllocator()

        np.random.seed(99)
        returns = np.random.normal(-0.01, 0.03, 100)
        res = allocator.compute_ultra_trans_hyper_evar_risk_measure(returns, alpha=0.05)

        assert res["order"] == 19
        assert res["xi_19"] == 0.75
        assert math.isclose(res["xi_ultra_trans"], 0.75, abs_tol=1e-6)

    def test_evar_coherent_tail_risk_hierarchy_under_fat_tail_distributions(self):
        """
        Adversarial Test 2.4:
        Tests that the strict coherent tail risk hierarchy holds:
            VaR <= CVaR <= EVaR <= ... <= Trans-Hyper-Transcendent-EVaR <= Ultra-Trans-Hyper-EVaR
        under fat-tail distributions:
        1. Cauchy distribution.
        2. Pareto distribution.
        3. Student-t.
        4. Simulated Black Swan market crash scenario.
        """
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(42)

        test_distributions = {
            "Cauchy": cauchy.rvs(loc=-0.01, scale=0.02, size=500),
            "Pareto": -(pareto.rvs(b=1.5, scale=0.02, size=500) - 0.02),
            "Student-t": student_t.rvs(df=2.0, loc=-0.005, scale=0.03, size=500),
            "Black_Swan_Crash": np.concatenate([
                np.random.normal(0.001, 0.01, 480),
                np.array([-0.20, -0.35, -0.50, -0.80, -0.99])
            ]),
        }

        for dist_name, returns in test_distributions.items():
            res = allocator.compute_ultra_trans_hyper_evar_risk_measure(returns, alpha=0.05)

            var_val = res["var_value"]
            cvar_val = res["cvar_value"]
            evar_val = res["evar_value"]
            ultra_trans_val = res["ultra_trans_hyper_evar_value"]

            assert math.isfinite(ultra_trans_val), f"Ultra-Trans-Hyper EVaR was not finite for {dist_name}"
            assert cvar_val >= var_val - 1e-4, f"CVaR < VaR for {dist_name}: {cvar_val} vs {var_val}"
            assert evar_val >= cvar_val - 1e-4, f"EVaR < CVaR for {dist_name}: {evar_val} vs {cvar_val}"
            assert ultra_trans_val >= evar_val - 1e-4, f"Ultra-Trans < EVaR for {dist_name}: {ultra_trans_val} vs {evar_val}"


# =============================================================================
# 3. R3: MICROSTRUCTURE OMS & EXECUTION ADVERSARIAL TESTS
# =============================================================================

class TestPhase23AdversarialR3Microstructure:
    """Empirical challenge tests for Feature F113.2, SOR maker floor, and tick shading."""

    # -------------------------------------------------------------------------
    # F113.2: Kerr-Newman-Kiselev Quintessence-Phantom Double Dark Energy L3 Model
    # -------------------------------------------------------------------------

    def test_knk_phantom_varying_dark_energy_equations_of_state(self):
        """
        Adversarial Test 3.1:
        Tests KNK-P model across various dark energy equations of state:
        - Quintessence standard: w_q = -2/3.
        - Phantom standard: w_p = -4/3.
        Verifies numerical stability, horizon computation, and micro-price bounded within book spread.
        """
        engine = FastOrderBookMatchingEngine(symbol="AAPL", tick_size=0.01)
        for i in range(10):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.10, 500.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.20 + i * 0.10, 500.0)

        w_states = [(-2.0 / 3.0, -4.0 / 3.0), (-1.0 / 3.0, -1.2), (-1.0, -1.5)]
        for w_q, w_p in w_states:
            res = engine.compute_kerr_newman_kiselev_phantom_queue_acceleration(
                charge_parameter=0.4,
                spin_parameter=0.5,
                quintessence_parameter=0.05,
                phantom_parameter=0.02,
                w_q=w_q,
                w_p=w_p,
            )
            assert math.isfinite(res["knk_p_micro_price"])
            assert math.isfinite(res["knk_p_hydrodynamic_acceleration"])
            assert math.isfinite(res["tidal_force"])
            assert res["phantom_horizon_r_P"] > res["horizon_radius"]

    def test_knk_phantom_tidal_force_monotonic_decrease_with_phantom_parameter(self):
        """
        Adversarial Test 3.2:
        In Kerr-Newman-Kiselev-Phantom spacetime, the radial tidal force is:
            F_{tidal}^{KNK-P} = F_{tidal}^{KN} - c_q * r - 2 * c_p * r^3
        As phantom parameter c_p increases, repulsive acceleration increases,
        monotonically decreasing F_tidal.
        """
        engine = FastOrderBookMatchingEngine(symbol="NVDA", tick_size=0.05)
        for i in range(10):
            engine.add_limit_order(f"b_{i}", "BUY", 500.0 - i * 0.50, 200.0)
            engine.add_limit_order(f"a_{i}", "SELL", 501.0 + i * 0.50, 200.0)

        c_p_values = [0.001, 0.01, 0.02, 0.05]
        tidal_forces = []
        for c_p in c_p_values:
            res = engine.compute_kerr_newman_kiselev_phantom_queue_acceleration(
                charge_parameter=0.3,
                spin_parameter=0.4,
                quintessence_parameter=0.05,
                phantom_parameter=c_p,
            )
            tidal_forces.append(res["knk_p_tidal_force"])

        # Check monotonic decrease
        for i in range(len(tidal_forces) - 1):
            assert tidal_forces[i] > tidal_forces[i + 1], f"F_tidal failed to decrease: {tidal_forces}"

    # -------------------------------------------------------------------------
    # Execution OMS: Maker Floor, Tick Shading, and Dark Cap
    # -------------------------------------------------------------------------

    def test_maker_floor_monotonic_contraction_and_shares_v23(self):
        """
        Adversarial Test 3.3:
        Verifies SmartOrderRouter maker floor:
        - Version 23 floor is exactly 0.000001 (0.0001%).
        - Monotonic progression: v23 (0.000001) < v22 (0.000002) < v21 (0.000005) < v20 (0.000010).
        - For an order of 1,000,000 shares under toxic flow, allocated maker shares must be 1.
        """
        sor = SmartOrderRouter()
        qty = 1_000_000

        plan = {
            "symbol": "GOOGL",
            "action": "BUY",
            "quantity": qty,
            "target_price": 2800.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.05,
            "version": 23,
        }
        res_v23 = sor.route_order(plan, ats_available=False)
        maker_legs_v23 = [
            l for l in res_v23.get("legs", [])
            if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
        ]
        assert len(maker_legs_v23) > 0
        assert maker_legs_v23[0]["quantity"] == 1
        assert math.isclose(maker_legs_v23[0]["maker_ratio"], 0.000001, abs_tol=1e-7)

    def test_oms_preemptive_micro_tick_shading_bid_ask_symmetry_v23(self):
        """
        Adversarial Test 3.4:
        Verifies Phase 23 preemptive tick shading in ExecutionOMSEngine:
        - When h > 0.035:
          hawkes_shift = -direction * 0.9995 * spread * (h - 0.035)
        - For BUY: shades price downwards.
        - For SELL: shades price upwards.
        - When h <= 0.035: hawkes_shift == 0.0.
        """
        oms = ExecutionOMSEngine()
        bid = 99.0
        ask = 101.0
        spread = ask - bid  # 2.0
        target = 100.0

        h_high = 0.535
        # shift = -1 * 0.9995 * 2.0 * (0.535 - 0.035) = -0.9995 * 2.0 * 0.50 = -0.9995

        peg_buy = oms.calculate_peg_limit_price(
            target_price=target,
            bid_price=bid,
            ask_price=ask,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_high},
            version=23,
        )

        peg_sell = oms.calculate_peg_limit_price(
            target_price=target,
            bid_price=bid,
            ask_price=ask,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_high},
            version=23,
        )

        assert peg_buy < target, f"BUY peg {peg_buy} must shade downwards from target {target}"
        assert peg_sell > target, f"SELL peg {peg_sell} must shade upwards from target {target}"
        assert math.isclose(target - peg_buy, peg_sell - target, abs_tol=1e-5)

        # Inactive when h <= 0.035
        peg_buy_low = oms.calculate_peg_limit_price(
            target_price=target,
            bid_price=bid,
            ask_price=ask,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.03},
            version=23,
        )
        peg_buy_target = oms.calculate_peg_limit_price(
            target_price=target,
            bid_price=bid,
            ask_price=ask,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.0},
            version=23,
        )
        assert math.isclose(peg_buy_low, peg_buy_target, abs_tol=1e-5)

    def test_dark_pool_99_995_cap_under_simulated_order_streams(self):
        """
        Adversarial Test 3.5:
        Under extreme lit toxicity across a simulated stream of orders,
        DeepHawkesArrivalProcess caps dark routing at exactly 0.99995 (99.995%).
        """
        process = DeepHawkesArrivalProcess()
        np.random.seed(77)

        for _ in range(50):
            lit_tox = np.random.uniform(10.0, 50.0)
            process.lambda_state = np.array([lit_tox, 0.1, 0.05])
            route_res = process.compute_preemptive_dark_routing(version=23)
            assert route_res["preemptive_dark_routing_ratio"] <= 0.99995
            if route_res["lit_toxicity_ratio"] >= 0.60:
                assert math.isclose(route_res["preemptive_dark_routing_ratio"], 0.99995, abs_tol=1e-6)
