"""
tests/test_phase16_challenger_stress.py — Adversarial Empirical Stress Test Battery for Phase 16

Written by: teamwork_preview_challenger (Empirical Challenger)
Role: Empirical verification, boundary stress, extreme value testing, and bug finding.
DO NOT TRUST CLAIMS — VERIFY EMPIRICALLY.
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.ai.ensemble_scorer import (
    apply_octacosagonal_hyperbolic_deadband,
    compute_phase16_hyperconvex_rank_modulation,
    QuantumToposSheafCoupler,
    EnsembleScoringEngine,
)
from src.ai.factor_suppression import apply_octacosagonal_hyperbolic_deadband as fs_deadband
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.core.fast_lob_engine import DeepHawkesArrivalProcess
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from src.execution.smart_order_router import SmartOrderRouter


class TestAdversarialAlphaSignalPhase16:
    """Stress testing 11th-order rank modulation, 28th-order deadband, and sheaf cohomology."""

    def test_g_v16_extreme_percentiles_and_boundaries(self):
        """Stress g_v16 at extreme percentiles, out-of-bound ranks, and negative values."""
        # Test extreme upper tail r in [0.9999, 1.0]
        r_fine = np.linspace(0.9999, 1.0, 1000)
        out_fine = compute_phase16_hyperconvex_rank_modulation(r_fine, gamma_top=1.75, z_denoised=1.0)
        assert np.all(np.isfinite(out_fine)), "Non-finite values encountered in extreme upper tail!"
        assert np.all(out_fine > 0), "Non-positive modulation encountered!"
        assert np.all(np.diff(out_fine) >= 0), "Violated monotonicity in extreme upper tail!"

        # Test out-of-bound ranks: r > 1.0 and r < 0.0 must be safely clipped
        r_oob = np.array([-100.0, -1.0, -0.01, 1.01, 1.5, 10.0, 1000.0])
        out_oob = compute_phase16_hyperconvex_rank_modulation(r_oob, gamma_top=1.75, z_denoised=0.5)
        assert np.all(np.isfinite(out_oob)), "Out-of-bounds ranks caused overflow or NaN!"
        # Negative ranks clipped to 0.0 -> g(0.0) = 0.50 + 0 = 0.50
        assert np.allclose(out_oob[:3], 0.50), "Negative ranks not clipped to 0.0 correctly!"
        # Ranks >= 1.0 clipped to 1.0 -> g(1.0) = 0.50 + 0.95 * exp(1.75)
        expected_top = 0.50 + 0.95 * math.exp(1.75)
        assert np.allclose(out_oob[3:], expected_top), "Ranks > 1.0 not clipped to 1.0 correctly!"

    def test_g_v16_strict_convexity_stress(self):
        """Verify 2nd derivative d^2 g_v16 / dr^2 is strictly positive on conviction region [0.7, 1.0]."""
        r_vals = np.linspace(0.70, 1.0, 500)
        for gamma in [0.30, 0.75, 1.30, 1.75]:
            g_vals = compute_phase16_hyperconvex_rank_modulation(r_vals, gamma_top=gamma, z_denoised=1.0)
            d1 = np.diff(g_vals) / np.diff(r_vals)
            d2 = np.diff(d1) / np.diff(r_vals[:-1])
            # Strict convexity requires 2nd derivative > 0
            assert np.all(d2 > 0), f"Strict convexity failed for gamma={gamma}!"

    def test_octacosagonal_deadband_subthreshold_leakage_adversarial(self):
        """Stress noise suppression across 20,000 fine points in [-0.007, 0.007]."""
        z_noise = np.linspace(-0.007, 0.007, 20000)
        denoised = apply_octacosagonal_hyperbolic_deadband(z_noise, delta_noise=0.035, alpha_pos=28.0)
        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-16, f"Noise leakage exceeded 10^-16: {max_leakage}"

        # Test factor_suppression version directly
        fs_denoised = fs_deadband(z_noise, delta_noise=0.035, alpha_pos=28.0)
        assert np.max(np.abs(fs_denoised)) < 1e-16, f"fs_deadband leakage exceeded 10^-16!"

    def test_octacosagonal_deadband_transmission_and_extremes(self):
        """Verify linear transmission at |z| >= 0.150 and stability at extreme |z|."""
        # Conviction region |z| >= 0.150
        z_conv = np.linspace(0.150, 1.0, 5000)
        denoised_conv = apply_octacosagonal_hyperbolic_deadband(z_conv, delta_noise=0.035, alpha_pos=28.0)
        # Relative error must be 0 or < 1e-12
        assert np.allclose(denoised_conv, z_conv, rtol=1e-12, atol=1e-12)

        # Negative conviction region
        z_neg_conv = np.linspace(-1.0, -0.150, 5000)
        denoised_neg = apply_octacosagonal_hyperbolic_deadband(z_neg_conv, delta_noise=0.035, alpha_pos=28.0)
        assert np.allclose(denoised_neg, z_neg_conv, rtol=1e-12, atol=1e-12)

        # Huge extreme values (e.g. z = 1e6, -1e6)
        z_extreme = np.array([-1e8, -1e4, -1e2, 1e2, 1e4, 1e8])
        denoised_ext = apply_octacosagonal_hyperbolic_deadband(z_extreme, delta_noise=0.035, alpha_pos=28.0)
        assert np.allclose(denoised_ext, z_extreme)

    def test_sheaf_coupler_adversarial_inputs(self):
        """Stress QuantumToposSheafCoupler with extreme degenerate factor inputs and dimension checks."""
        coupler = QuantumToposSheafCoupler()
        # Incomplete pillar representation (< 5 pillars) must raise ValueError
        scores_incomplete = {"val": 1.0, "mom": 2.0, "flow": 3.0}
        with pytest.raises(ValueError, match="Sheaf Cohomology factor disentanglement requires 5 canonical pillars"):
            coupler.evaluate(scores_incomplete)

        # Extreme values across all 5 canonical pillars
        scores_extreme = {"val": 1e6, "mom": -1e6, "flow": 1e4, "cat": -1e4, "net": 0.0}
        res_ext = coupler.evaluate(scores_extreme)
        assert math.isfinite(float(np.asarray(res_ext["E_sheaf"]).item()))
        assert math.isfinite(float(np.asarray(res_ext["Z_sheaf"]).item()))
        assert math.isfinite(float(np.asarray(res_ext["h_sheaf"]).item()))
        assert math.isfinite(float(np.asarray(res_ext["FERI_v16"]).item()))
        assert 0.0 <= float(np.asarray(res_ext["h_sheaf"]).item()) <= 1.0

        # Uniform factors (0 obstruction)
        scores_uni = {"val": 1.5, "mom": 1.5, "flow": 1.5, "cat": 1.5, "net": 1.5}
        res_uni = coupler.evaluate(scores_uni)
        assert math.isclose(float(np.asarray(res_uni["E_sheaf"]).item()), 0.0, abs_tol=1e-6)
        assert math.isclose(float(np.asarray(res_uni["Z_sheaf"]).item()), 1.0, abs_tol=1e-6)
        assert math.isclose(float(np.asarray(res_uni["h_sheaf"]).item()), 1.0, abs_tol=1e-6)


class TestAdversarialRiskAllocationPhase16:
    """Stress testing Non-Abelian Gauge Fisher-Rao Barycenter and Ultra-Transfinite EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_gauge_barycenter_simplex_stress(self, allocator):
        """Test 1,000 Dirichlet distributions with random concentrations to verify simplex sum == 1.0."""
        np.random.seed(999)
        for i in range(1000):
            # Random alpha from 0.01 to 50.0
            alpha_dir = np.random.exponential(scale=2.0, size=4) + 0.01
            sample = np.random.dirichlet(alpha_dir)
            w = {"bl": sample[0], "herc": sample[1], "rp": sample[2], "cvar": sample[3]}
            res = allocator.compute_nonabelian_gauge_fisher_rao_barycenter_blend(w)
            total = sum(res.values())
            assert math.isclose(total, 1.0, abs_tol=1e-5), f"Simplex sum violated on iteration {i}: {total}"
            for k, val in res.items():
                assert val > 0.0, f"Non-positive weight for {k} on iteration {i}: {val}"

    def test_gauge_barycenter_extreme_degeneracies(self, allocator):
        """Test degenerate corner cases: single-model concentration, all zeros, empty."""
        # 99.999% in one model
        w_corner = {"bl": 0.99999, "herc": 1e-7, "rp": 1e-7, "cvar": 1e-7}
        res_corner = allocator.compute_nonabelian_gauge_fisher_rao_barycenter_blend(w_corner)
        assert math.isclose(sum(res_corner.values()), 1.0, abs_tol=1e-5)

        # All zeros fallback
        w_zero = {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        res_zero = allocator.compute_nonabelian_gauge_fisher_rao_barycenter_blend(w_zero)
        assert math.isclose(sum(res_zero.values()), 1.0, abs_tol=1e-5)

        # Empty dict fallback
        res_empty = allocator.compute_nonabelian_gauge_fisher_rao_barycenter_blend({})
        assert math.isclose(sum(res_empty.values()), 1.0, abs_tol=1e-5)

    def test_evar_hierarchy_on_cauchy_and_pareto(self, allocator):
        """Adversarial stress: verify strict EVaR hierarchy on Cauchy (infinite variance) and Pareto."""
        np.random.seed(777)
        # 1. Cauchy distribution
        cauchy_rets = np.random.standard_cauchy(size=300) * 0.01
        res_cauchy = allocator.compute_ultra_transfinite_evar_risk_measure(cauchy_rets, alpha=0.05)
        # Verify hierarchy:
        # VaR <= CVaR <= EVaR <= Super <= Ultra <= Trans <= Inf <= Supra <= UltraTrans
        assert res_cauchy["cvar_value"] >= res_cauchy["var_value"] - 1e-5
        assert res_cauchy["evar_value"] >= res_cauchy["cvar_value"] - 1e-5
        assert res_cauchy["super_evar_value"] >= res_cauchy["evar_value"] - 1e-5
        assert res_cauchy["ultra_evar_value"] >= res_cauchy["super_evar_value"] - 1e-5
        assert res_cauchy["transfinite_evar_value"] >= res_cauchy["ultra_evar_value"] - 1e-5
        assert res_cauchy["infinite_evar_value"] >= res_cauchy["transfinite_evar_value"] - 1e-5
        assert res_cauchy["supra_transfinite_evar_value"] >= res_cauchy["infinite_evar_value"] - 1e-5
        assert res_cauchy["ultra_transfinite_evar_value"] >= res_cauchy["supra_transfinite_evar_value"] - 1e-5

        # 2. Pareto distribution (heavy right tail on losses, i.e., heavy negative returns)
        pareto_losses = (np.random.pareto(a=1.5, size=300) + 1.0) * 0.02
        pareto_rets = -pareto_losses
        res_pareto = allocator.compute_ultra_transfinite_evar_risk_measure(pareto_rets, alpha=0.05)
        assert res_pareto["ultra_transfinite_evar_value"] >= res_pareto["supra_transfinite_evar_value"] - 1e-5
        assert res_pareto["supra_transfinite_evar_value"] >= res_pareto["infinite_evar_value"] - 1e-5
        assert res_pareto["infinite_evar_value"] >= res_pareto["transfinite_evar_value"] - 1e-5

        # 3. Solitary massive crash (-100.0 loss)
        crash_rets = np.concatenate([np.random.normal(0, 0.01, 100), np.array([-50.0])])
        res_crash = allocator.compute_ultra_transfinite_evar_risk_measure(crash_rets, alpha=0.01)
        assert math.isfinite(res_crash["ultra_transfinite_evar_value"])
        assert res_crash["ultra_transfinite_evar_value"] >= res_crash["supra_transfinite_evar_value"] - 1e-5


class TestAdversarialMicrostructureOMSPhase16:
    """Stress testing L3 dark routing cap, SOR maker floor, and preemptive micro-tick shading."""

    def test_fast_lob_dark_routing_cap_stress(self):
        """Stress L3 queue dark routing cap across extreme Hawkes intensities."""
        proc = DeepHawkesArrivalProcess()
        # When lit toxicity is extreme (lit_toxicity >= 0.60), routing hits the Phase 16 cap of 0.995
        for lit_mu in [100.0, 1e4, 1e8]:
            proc.mu = np.array([lit_mu, 0.01, 0.01])
            routing = proc.compute_preemptive_dark_routing(version=16)
            assert routing["preemptive_dark_routing_ratio"] == 0.995, f"Dark cap violated at mu={lit_mu}"

        # Under low lit toxicity, dark routing must never exceed 0.995 cap
        for equal_mu in [1.0, 50.0, 1000.0]:
            proc.mu = np.array([equal_mu, equal_mu, equal_mu])
            routing = proc.compute_preemptive_dark_routing(version=16)
            assert routing["preemptive_dark_routing_ratio"] <= 0.995

    def test_sor_maker_floor_and_minqty_boundary_stress(self):
        """Stress SOR maker floor at 0.0002 and MinQty at 0.998 under extreme toxic flow."""
        sor = SmartOrderRouter()
        # Maximum toxicity gamma_toxic = 1.0
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 5000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0000,
            "darkpool_score": 1.0000,
            "version": 16,
        }
        res = sor.route_order(plan)
        assert math.isclose(res["maker_ratio"], 0.0002, abs_tol=1e-6), f"Maker floor was {res['maker_ratio']} != 0.0002"
        assert math.isclose(res["min_ratio"], 0.998, abs_tol=1e-6), f"MinQty cap was {res['min_ratio']} != 0.998"
        assert res["effective_dark_ratio"] <= 0.995, f"Effective dark ratio {res['effective_dark_ratio']} > 0.995"

    def test_preemptive_tick_shading_oms_scheduler_symmetry(self):
        """Stress preemptive tick shading in ExecutionOMSEngine and AlmgrenChrissScheduler."""
        oms = ExecutionOMSEngine()
        sched = AlmgrenChrissScheduler()

        spreads = [0.10, 1.0, 5.0]
        h_values = [0.0, 0.10, 0.14, 0.15, 0.20, 0.30]

        # Use wide bid/ask bounds to test exact unconstrained formula shift
        p_bid_wide, p_ask_wide = 50.0, 150.0

        for spr in spreads:
            for h_val in h_values:
                for action in ["BUY", "SELL"]:
                    p_oms = oms.calculate_peg_limit_price(
                        100.0, p_bid_wide, p_ask_wide, spread=spr, action=action,
                        hawkes_intensity={"cross_excitation_toxicity": h_val}, version=16
                    )
                    p_sched = sched.calculate_peg_limit_price(
                        100.0, p_bid_wide, p_ask_wide, spread=spr, action=action,
                        hawkes_intensity={"cross_excitation_toxicity": h_val}, version=16
                    )
                    # 1. Exact equality between OMS and Scheduler
                    assert math.isclose(p_oms, p_sched, abs_tol=1e-8), \
                        f"OMS and Scheduler differed for spread={spr}, h={h_val}, action={action}"

                    # 2. Formula verification:
                    # if h <= 0.14: shift is 0.0
                    # if h > 0.14: shift is -direction * 0.95 * spr * (h - 0.14)
                    direction = 1.0 if action == "BUY" else -1.0
                    if h_val <= 0.14:
                        expected_shift = 0.0
                    else:
                        expected_shift = -direction * 0.95 * spr * (h_val - 0.14)
                    actual_shift = p_oms - 100.0
                    assert math.isclose(actual_shift, expected_shift, abs_tol=1e-6), \
                        f"Shading formula mismatch: actual={actual_shift}, expected={expected_shift}"

        # 3. Test safety clipping boundary: limit price must never breach [p_bid, p_ask]
        p_clamped_buy = oms.calculate_peg_limit_price(
            100.0, 99.5, 100.5, spread=5.0, action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 1.0}, version=16
        )
        assert p_clamped_buy >= 99.5, "BUY peg limit price breached best bid boundary!"
        p_clamped_sell = oms.calculate_peg_limit_price(
            100.0, 99.5, 100.5, spread=5.0, action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": 1.0}, version=16
        )
        assert p_clamped_sell <= 100.5, "SELL peg limit price breached best ask boundary!"


class TestAdversarialBenchmarkCriteriaPhase16:
    """Verify 15 core quantitative benchmark criteria."""

    def test_benchmark_script_15_core_criteria(self):
        from trading_system.scripts.benchmark_phase16_quant_performance import (
            BENCHMARK_PROFILES,
            compute_aggregate_metrics,
        )

        agg = compute_aggregate_metrics(BENCHMARK_PROFILES, mode="enhancement")

        # 1. Net Expected Return >= 97.5%
        assert agg.net_return_ann_pct >= 97.50, f"Net Return {agg.net_return_ann_pct}% < 97.5%"
        # 2. Sharpe Ratio >= 12.50
        assert agg.sharpe_ratio >= 12.50, f"Sharpe Ratio {agg.sharpe_ratio} < 12.50"
        # 3. Maximum Drawdown (MDD) <= -0.10% (i.e. abs(MDD) <= 0.10%)
        assert agg.max_drawdown_pct >= -0.10, f"MDD {agg.max_drawdown_pct}% worse than -0.10%"
        # 4. Total Friction Costs <= 0.45 bps
        assert agg.friction_cost_bps <= 0.45, f"Friction {agg.friction_cost_bps} bps > 0.45 bps"
        # 5. Execution Slippage <= 0.03 bps
        assert agg.execution_slippage_bps <= 0.03, f"Slippage {agg.execution_slippage_bps} bps > 0.03 bps"
        # 6. Top-Decile Spread >= 67.0%
        assert agg.top_decile_spread_pct >= 67.0, f"Top-Decile Spread {agg.top_decile_spread_pct}% < 67.0%"
        # 7. Win Rate >= 99.5%
        assert agg.win_rate_pct >= 99.5, f"Win Rate {agg.win_rate_pct}% < 99.5%"
        # 8. Profit Factor >= 13.0
        assert agg.profit_factor >= 13.0
        # 9. Deflated Sharpe Ratio == 1.000
        assert agg.deflated_sharpe_ratio == 1.000

