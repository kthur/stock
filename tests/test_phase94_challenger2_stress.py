r"""
tests/test_phase94_challenger2_stress.py

Adversarial Stress Test Suite for Phase 94 (v101 Production Master, Features F442, F443):
- Higher-Homology-44 Barycenter Blending: Degenerate weights, extreme values, NaN/Inf, simplex sum, hierarchy.
- 120th-Cumulant Expansion Trans-Singular EVaR: Heavy-tailed returns (Student-t df=2, Cauchy, crashes),
  30-nines xi_monster stability, fat-tailed EVaR bounding Gaussian EVaR.
- KNK-72 Dark Energy DAHA L3 Queue Acceleration: Queue depths in [0, 1e7], acceleration bound in [-1e6, 1e6].
- SmartOrderRouter Version 94: Toxic flow gamma=1.0 maker ratio floor 1e-65.
- Dual-OMS Preemptive Micro-Tick Shading: Threshold boundary h = 6.0e-11 +/- 1e-13, 47-nines precision,
  strict ExecutionOMSEngine and AlmgrenChrissScheduler parity.
"""

import math
import numpy as np
import scipy.stats as stats
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
from trading_system.src.core.fast_lob_engine import FastOrderBookMatchingEngine
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestBarycenterAdversarialStress:
    """Stress tests for Feature F442.1 Higher-Homology-44 Motivic Fisher-Rao Barycenter."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=94)

    def test_barycenter_uniform_hierarchy_and_simplex_sum(self, allocator):
        """Verify simplex sum = 1.0 and CVaR > BL > HERC > RP hierarchy holds under uniform inputs."""
        w_uni = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_phase94_barycenter(w_uni)

        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-6)
        # mu = [9.10, 5.60, 2.55, 11.00] -> cvar > bl > herc > rp
        assert res["cvar"] > res["bl"], f"Expected CVaR > BL, got {res}"
        assert res["bl"] > res["herc"], f"Expected BL > HERC, got {res}"
        assert res["herc"] > res["rp"], f"Expected HERC > RP, got {res}"
        for k, v in res.items():
            assert 0.0 < v < 1.0

    def test_barycenter_all_zeros_regularization(self, allocator):
        """Verify degenerate all-zeros input regularizes into simplex sum = 1.0 and proper hierarchy."""
        w_zeros = {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        res = allocator.compute_phase94_barycenter(w_zeros)

        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-6)
        assert res["cvar"] > res["bl"] > res["herc"] > res["rp"]

    def test_barycenter_single_dominant_model(self, allocator):
        """Verify single 1.0 model regularizes and maintains simplex sum = 1.0."""
        for model in ["bl", "herc", "rp", "cvar"]:
            w = {k: 1.0 if k == model else 0.0 for k in ["bl", "herc", "rp", "cvar"]}
            res = allocator.compute_phase94_barycenter(w)
            assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-6)
            assert res[model] > 0.95

    def test_barycenter_empty_dict_fallback(self, allocator):
        """Verify empty dictionary input gracefully falls back to uniform weights."""
        res = allocator.compute_phase94_barycenter({})
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-6)
        assert res["cvar"] > res["bl"] > res["herc"] > res["rp"]

    def test_barycenter_negative_weights_clipping(self, allocator):
        """Verify negative weights are safely clipped by tau."""
        w_neg = {"bl": -0.5, "herc": 0.25, "rp": 0.25, "cvar": 0.50}
        res = allocator.compute_phase94_barycenter(w_neg)
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-6)
        for v in res.values():
            assert v > 0.0

    def test_barycenter_dictionary_nan_handling(self, allocator):
        """Verify dictionary containing float('nan') regularizes via tau."""
        w_nan = {"bl": float("nan"), "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_phase94_barycenter(w_nan)
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-6)
        for v in res.values():
            assert math.isfinite(v) and v > 0.0


class TestEVaRAdversarialStress:
    """Stress tests for Feature F442.2 120th-Cumulant Expansion Trans-Singular EVaR Risk Measure."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=94)

    def test_evar_student_t_heavy_tail(self, allocator):
        """Verify 120th-Cumulant EVaR on Student-t with df=2 (infinite 2nd+ moments) yields finite positive risk."""
        np.random.seed(42)
        rets_t2 = stats.t.rvs(df=2, loc=0.0005, scale=0.02, size=500)
        res = allocator.compute_phase94_evar(returns=rets_t2)

        assert res["order"] == 120
        assert math.isclose(res["xi_monster"], 1.0, abs_tol=1e-15)
        assert math.isfinite(res["evar"])
        assert res["evar"] > 0.0

    def test_evar_cauchy_extreme_tail(self, allocator):
        """Verify EVaR on Cauchy returns (undefined mean and variance) remains finite and positive."""
        np.random.seed(42)
        rets_cauchy = stats.cauchy.rvs(loc=0.0, scale=0.01, size=500)
        res = allocator.compute_phase94_evar(returns=rets_cauchy)

        assert math.isfinite(res["evar"])
        assert res["evar"] > 0.0

    def test_evar_extreme_market_crash(self, allocator):
        """Verify EVaR under an extreme -99% flash crash event reflects severe tail risk."""
        rets_crash = np.array([0.01] * 40 + [-0.99] + [0.01] * 40)
        res = allocator.compute_phase94_evar(returns=rets_crash)

        assert math.isfinite(res["evar"])
        assert res["evar"] > 0.50, f"Expected EVaR to reflect severe crash, got {res['evar']}"

    def test_evar_fat_tailed_strictly_bounds_gaussian(self, allocator):
        """Verify fat-tailed return distribution (Student-t df=3) EVaR strictly bounds Gaussian EVaR with equal variance."""
        np.random.seed(42)
        target_std = 0.03
        rets_norm = np.random.normal(loc=-0.001, scale=target_std, size=2000)
        rets_fat = stats.t.rvs(df=3, loc=-0.001, scale=target_std * np.sqrt(1.0 / 3.0), size=2000)

        res_norm = allocator.compute_phase94_evar(returns=rets_norm)
        res_fat = allocator.compute_phase94_evar(returns=rets_fat)

        assert math.isfinite(res_norm["evar"]) and math.isfinite(res_fat["evar"])
        assert res_fat["evar"] >= res_norm["evar"], (
            f"Expected fat-tailed EVaR ({res_fat['evar']:.6f}) >= Gaussian EVaR ({res_norm['evar']:.6f})"
        )

    def test_evar_xi_monster_numerical_stability(self, allocator):
        """Verify xi_monster with 30 nines evaluates stably without overflow or precision loss."""
        rets = np.array([0.02, -0.015, 0.03, -0.025, 0.01, -0.005, 0.015, -0.01])
        res = allocator.compute_phase94_evar(
            returns=rets,
            xi_monster=0.99999999999999999999999999999
        )
        assert math.isfinite(res["evar"])
        assert res["evar"] > 0.0

    def test_evar_edge_cases_empty_single_constant_nans(self, allocator):
        """Verify EVaR behavior on empty, single, constant, and NaN/Inf containing arrays."""
        # Empty array
        res_empty = allocator.compute_phase94_evar(returns=np.array([]))
        assert res_empty["evar"] == 0.0

        # Single return
        res_single = allocator.compute_phase94_evar(returns=np.array([0.05]))
        assert res_single["evar"] == 0.0

        # Constant zeros
        res_zeros = allocator.compute_phase94_evar(returns=np.zeros(100))
        assert math.isfinite(res_zeros["evar"]) and res_zeros["evar"] > 0.0

        # Array with NaNs and Infs (cleaned by isfinite filter)
        res_nans = allocator.compute_phase94_evar(returns=np.array([0.01, np.nan, -0.02, np.inf, 0.03]))
        assert math.isfinite(res_nans["evar"]) and res_nans["evar"] > 0.0


class TestKNK72DarkEnergyL3QueueStress:
    """Stress tests for Feature F443 Kerr-Newman-Kiselev 72-Dark-Energy DAHA L3 Queue Acceleration."""

    def test_knk72_extreme_queue_depths_remain_finite_and_bounded(self):
        """Verify queue acceleration remains finite in [-1e6, 1e6] across queue depths from 0 to 10^7."""
        queue_depths = [0.0, 1e-15, 0.01, 1.0, 10.0, 100.0, 1e4, 1e6, 1e7]
        for qd in queue_depths:
            engine = FastOrderBookMatchingEngine(symbol="STRESS_SYM")
            for i in range(5):
                engine.add_limit_order(f"b_{i}", "BUY", 100.0 - i, max(0.001, qd))
                engine.add_limit_order(f"a_{i}", "SELL", 101.0 + i, 1.0)
            res = engine.compute_kerr_newman_kiselev_72_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

            accel = res["queue_acceleration"]
            corr = res["knk_72_dark_energy_correction"]
            assert math.isfinite(accel), f"Non-finite acceleration at qd={qd}: {accel}"
            assert math.isfinite(corr), f"Non-finite correction at qd={qd}: {corr}"
            assert -1e6 <= accel <= 1e6, f"Acceleration out of [-1e6, 1e6] bounds at qd={qd}: {accel}"

    def test_knk72_physical_constants_and_state_parameters(self):
        """Verify KNK-72 equation of state w = -74/3, c_monster = 2^-74, daha_72_factor = 13.50."""
        engine = FastOrderBookMatchingEngine(symbol="CONST_TEST")
        engine.add_limit_order("b0", "BUY", 100.0, 10.0)
        engine.add_limit_order("a0", "SELL", 101.0, 10.0)
        res = engine.compute_kerr_newman_kiselev_72_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        assert math.isclose(res["w_dark_energy_72"], -74.0 / 3.0, rel_tol=1e-6)
        assert math.isclose(res["c_monster_72"], 2.0 ** -74, rel_tol=1e-9)
        assert math.isclose(res["daha_72_factor"], 13.50, rel_tol=1e-6)
        assert math.isclose(res["k_daha_72"], 0.64, rel_tol=1e-6)
        assert math.isclose(res["k_monster_72"], 0.63, rel_tol=1e-6)


class TestSmartOrderRouterToxicFlowStress:
    """Stress tests for Feature F443 SmartOrderRouter version 94 Lit maker floor."""

    def test_maker_ratio_floor_under_extreme_toxic_flow(self):
        """Verify maker ratio floor never breaches 1e-65 under toxic flow gamma_toxic >= 1.0."""
        sor = SmartOrderRouter(version=94)
        assert sor.is_phase94 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 1000,
            "action": "BUY",
            "version": 94,
            "target_price": 150.0,
            "hawkes_intensity": 0.99,
        }

        for gamma in [0.81, 0.90, 0.95, 0.99, 1.00, 1.20, 2.00]:
            res = sor.route_order(order_plan, gamma_toxic_dir=gamma)
            maker_ratio = res["maker_ratio"]
            assert maker_ratio >= 1e-65, f"Maker ratio breached 1e-65 at gamma={gamma}: {maker_ratio}"
            if gamma >= 1.0:
                assert maker_ratio == 1e-65, f"Expected exact floor 1e-65 at gamma={gamma}, got {maker_ratio}"


class TestDualOMSTickShadingBoundaryStress:
    """Stress tests for Feature F443 Dual-OMS Preemptive Micro-Tick Shading at boundary h = 6.0e-11 +/- 1e-13."""

    def test_tick_shading_strict_boundary_activation_and_parity(self):
        """Verify strict activation at h > 6.0e-11 and exact mathematical parity between ExecutionOMSEngine and AlmgrenChrissScheduler."""
        sched = AlmgrenChrissScheduler()
        h_threshold = 6.0e-11
        delta = 1.0e-13

        h_sub = h_threshold - delta    # 5.99e-11
        h_exact = h_threshold          # 6.00e-11
        h_super = h_threshold + delta  # 6.01e-11

        target = 100.0
        bid = 99.95
        ask = 100.05

        # Unshaded baseline
        p_base = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, action="BUY", version=94,
            hawkes_intensity={"cross_excitation_toxicity": 0.0}
        )

        # 1. Sub-threshold (5.99e-11): must remain completely unshaded
        p_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, action="BUY", version=94,
            hawkes_intensity={"cross_excitation_toxicity": h_sub}
        )
        s_sub = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, action="BUY", version=94,
            hawkes_intensity={"cross_excitation_toxicity": h_sub}
        )
        assert math.isclose(p_sub, p_base, abs_tol=1e-15), "Sub-threshold price altered unexpectedly"
        assert math.isclose(p_sub, s_sub, rel_tol=1e-14), "Dual-OMS parity violated below threshold"

        # 2. Exact threshold (6.00e-11): condition h > 6.0e-11 is False, unshaded
        p_exact = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, action="BUY", version=94,
            hawkes_intensity={"cross_excitation_toxicity": h_exact}
        )
        s_exact = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, action="BUY", version=94,
            hawkes_intensity={"cross_excitation_toxicity": h_exact}
        )
        assert math.isclose(p_exact, p_base, abs_tol=1e-15), "Exact-threshold price altered unexpectedly"
        assert math.isclose(p_exact, s_exact, rel_tol=1e-14), "Dual-OMS parity violated at exact threshold"

        # 3. Super-threshold (6.01e-11): activates 47-nines shading
        p_super_buy = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, action="BUY", version=94,
            hawkes_intensity={"cross_excitation_toxicity": h_super}
        )
        s_super_buy = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, action="BUY", version=94,
            hawkes_intensity={"cross_excitation_toxicity": h_super}
        )
        # BUY price must be shaded downward
        assert p_super_buy < p_base, "BUY price was not shaded downward above threshold"
        assert math.isclose(p_super_buy, s_super_buy, rel_tol=1e-14), "Dual-OMS parity violated above threshold (BUY)"

        # SELL price must be shaded upward
        p_super_sell = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, action="SELL", version=94,
            hawkes_intensity={"cross_excitation_toxicity": h_super}
        )
        s_super_sell = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, action="SELL", version=94,
            hawkes_intensity={"cross_excitation_toxicity": h_super}
        )
        assert p_super_sell > p_base, "SELL price was not shaded upward above threshold"
        assert math.isclose(p_super_sell, s_super_sell, rel_tol=1e-14), "Dual-OMS parity violated above threshold (SELL)"
