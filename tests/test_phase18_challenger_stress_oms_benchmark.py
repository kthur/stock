"""
tests/test_phase18_challenger_stress_oms_benchmark.py

Adversarial Stress Test Suite for Phase 18 Quantitative Enhancement:
- Feature F93.2.1: Kerr-Newman Charged Rotating Spacetime L3 Queue Priority Model
  * Extreme spin regimes (a -> M, a > M, a < 0)
  * Extreme electric charge regimes (Q -> M, Q > M, Q < 0)
  * Cosmic censorship bounds (a^2 + Q^2 <= M^2) and naked singularity prevention
  * Coordinate singularities near horizons and ergosphere boundaries (r -> r_E, theta variation)
  * Uncharged Kerr limit (Q = 0), Reissner-Nordstrom static limit (a = 0, Q > 0), Schwarzschild limit (a = 0, Q = 0)
  * Extreme depth and empty/near-empty book stability
- Feature F93.2.2: SmartOrderRouter Version 18 Stress Testing
  * 100% lit toxicity (gamma_toxic = 1.0 and beyond) with maker floor bounded to exactly 0.00005 (0.005%)
  * Dark venue preemption saturation cap bounded to strictly 0.999 (99.9%)
  * Dynamic anti-gaming MinQty adapting up to 0.9995 (99.95%)
  * Extreme spread books (0.001 bps to 10,000 bps) and zero-depth book resiliency
  * Cross-version floor contraction hierarchy (v18 < v17 < v16 < v15 < v14)
- Feature F93.2.3: Preemptive Micro-Tick Shading Stress Testing
  * Hawkes intensity range h in [0.10, 100.0] under BUY and SELL directions
  * Strict clipping within [p_bid, p_ask] without boundary breaches
  * Threshold gating at h <= 0.10 producing zero shift
  * Numerical and algorithmic consistency between ExecutionOMSEngine and AlmgrenChrissScheduler
- Feature F94: Phase 18 Quantitative Benchmark Engine Perturbation Testing
  * Skewed and perturbed market weights across subset markets
  * Single non-zero weight concentration
  * Zero-weight exception handling
  * Fuzzing of synthetic profiles and metric invariants (Calmar, Sortino, DSR)
  * Markdown report synchronization and generation integrity

Author: Challenger 2 (Microstructure OMS & Benchmark Adversarial Challenger)
"""

import math
import random
import numpy as np
import pytest

from src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    DeepHawkesArrivalProcess,
)
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler

from trading_system.scripts.benchmark_phase18_quant_performance import (
    Phase18QuantBenchmarkEngine,
    compute_aggregate_metrics,
    QuantitativeMetrics,
    BENCHMARK_PROFILES,
    MARKET_WEIGHTS,
    generate_phase18_markdown_report,
)


class TestKerrNewmanSpacetimeAdversarialStress:
    """Stress tests for Kerr-Newman charged rotating spacetime queue acceleration."""

    def test_kerr_newman_uncharged_limit_reproduces_kerr(self):
        """When charge parameter Q = 0.0, Kerr-Newman metric must reduce to Kerr spacetime."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 50.0, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 50.0, 100.0)

        res_kn = engine.compute_kerr_newman_queue_acceleration(spin_parameter=0.85, charge_parameter=0.0)
        res_kerr = engine.compute_kerr_ergosphere_queue_acceleration(spin_parameter=0.85)

        assert res_kn["kerr_charge_Q"] == 0.0
        assert math.isclose(res_kn["ergosphere_radius"], res_kerr["ergosphere_radius"], abs_tol=1e-4)
        assert math.isclose(res_kn["frame_dragging_omega"], res_kerr["frame_dragging_omega"], abs_tol=1e-4)
        assert math.isclose(res_kn["kerr_mass_M"], res_kerr["kerr_mass_M"], abs_tol=1e-4)

    def test_kerr_newman_static_limit_reissner_nordstrom(self):
        """
        When spin parameter a = 0.0 and charge Q > 0.0 (Reissner-Nordstrom limit):
        Frame-dragging angular velocity omega must strictly vanish (omega = 0.0),
        while electric charge tidal amplification remains active without rotation.
        """
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 50.0, 200.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 50.0, 200.0)

        res = engine.compute_kerr_newman_queue_acceleration(spin_parameter=0.0, charge_parameter=0.40)
        assert res["kerr_spin_a"] == 0.0
        assert res["frame_dragging_omega"] == 0.0
        assert res["kerr_charge_Q"] > 0.0
        assert math.isfinite(res["tidal_force"])
        assert math.isfinite(res["kerr_rotational_acceleration"])

    def test_kerr_newman_schwarzschild_limit(self):
        """When both spin a = 0.0 and charge Q = 0.0 (Schwarzschild limit): omega = 0 and r_E = 2*M."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 50.0, 200.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 50.0, 200.0)

        res = engine.compute_kerr_newman_queue_acceleration(spin_parameter=0.0, charge_parameter=0.0)
        M = res["kerr_mass_M"]
        assert res["kerr_spin_a"] == 0.0
        assert res["kerr_charge_Q"] == 0.0
        assert res["frame_dragging_omega"] == 0.0
        # Ergosphere radius with a=0, Q=0 is M + sqrt(M^2) = 2*M
        assert math.isclose(res["ergosphere_radius"], 2.0 * M, abs_tol=1e-4)

    def test_kerr_newman_extreme_spin_regimes(self):
        """
        Adversarial test across extreme spin parameters a -> M, a = M, a > M (naked singularity candidate),
        and negative spin parameters. Verifies spin parameter is strictly clipped to [0, 0.999 * M].
        """
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 50.0, 200.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 50.0, 200.0)

        extreme_spins = [0.999, 1.0, 1.5, 10.0, 1000.0, -0.999, -1.0, -100.0]
        for spin in extreme_spins:
            res = engine.compute_kerr_newman_queue_acceleration(spin_parameter=spin, charge_parameter=0.20)
            M = res["kerr_mass_M"]
            a = res["kerr_spin_a"]
            q = res["kerr_charge_Q"]

            assert 0.0 <= a <= 0.999 * M + 1e-6
            assert 0.0 <= q <= M
            # Cosmic censorship bound: a^2 + Q^2 <= M^2
            assert (a ** 2 + q ** 2) <= (M ** 2) + 1e-3
            assert res["frame_dragging_omega"] >= 0.0
            assert math.isfinite(res["frame_dragging_omega"])
            assert -100.0 <= res["kerr_rotational_acceleration"] <= 100.0
            assert -1.0 <= res["kerr_accelerated_qi"] <= 1.0
            assert math.isfinite(res["kerr_micro_price"])

    def test_kerr_newman_extreme_charge_regimes(self):
        """
        Adversarial test across extreme charge parameters Q -> M, Q = M, Q > M (overcharged candidate),
        and negative charge parameters. Verifies charge is strictly clamped to max_q <= 0.999 * sqrt(M^2 - a^2).
        """
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 50.0, 200.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70100.0 + i * 50.0, 200.0)

        extreme_charges = [0.999, 1.0, 1.5, 10.0, 1000.0, -0.999, -1.0, -100.0]
        for chg in extreme_charges:
            res = engine.compute_kerr_newman_queue_acceleration(spin_parameter=0.70, charge_parameter=chg)
            M = res["kerr_mass_M"]
            a = res["kerr_spin_a"]
            q = res["kerr_charge_Q"]

            assert 0.0 <= q <= M
            # Cosmic censorship must strictly hold: a^2 + Q^2 <= M^2
            assert (a ** 2 + q ** 2) <= (M ** 2) + 1e-3
            assert math.isfinite(res["tidal_force"])
            assert math.isfinite(res["frame_dragging_omega"])
            assert -100.0 <= res["kerr_rotational_acceleration"] <= 100.0

    def test_kerr_newman_coordinate_singularities_boundary_r_to_rE(self):
        """
        Boundary condition r -> r_E:
        When qi = 0, r_coord = M.
        When a -> M, Q -> 0, theta = 0 (pole), r_E -> M.
        Verify that as r_coord -> r_E, no division by zero or divergence occurs in drag_amp,
        frame_dragging_omega, or tidal_force.
        """
        engine = FastOrderBookMatchingEngine(symbol="005930")
        # Balanced book so qi_l3 = 0.0
        engine.add_limit_order("b1", "BUY", 100.0, 500.0)
        engine.add_limit_order("a1", "SELL", 100.2, 500.0)

        res = engine.compute_kerr_newman_queue_acceleration(spin_parameter=0.999, charge_parameter=0.01, theta=0.0)
        M = res["kerr_mass_M"]
        r = res["coordinate_radius_r"]
        r_E = res["ergosphere_radius"]

        assert math.isclose(r, M, rel_tol=1e-3)
        assert r_E >= r - 1e-4
        assert res["is_in_ergosphere"] is True
        assert math.isfinite(res["frame_dragging_omega"])
        assert math.isfinite(res["tidal_force"])
        assert -100.0 <= res["kerr_rotational_acceleration"] <= 100.0

    def test_kerr_newman_theta_angular_variation_equatorial_vs_polar(self):
        """
        Ergosphere geometry under charge Q:
        At equator (theta = pi/2): cos(theta) = 0 => r_E = M + sqrt(M^2 - Q^2).
        At pole (theta = 0): cos(theta) = 1 => r_E = M + sqrt(M^2 - a^2 - Q^2).
        r_E(equator) >= r_E(pole).
        """
        engine = FastOrderBookMatchingEngine(symbol="NVDA")
        engine.add_limit_order("b1", "BUY", 120.0, 1000.0)
        engine.add_limit_order("a1", "SELL", 120.5, 800.0)

        thetas = [0.0, math.pi / 6.0, math.pi / 4.0, math.pi / 3.0, math.pi / 2.0, -math.pi / 2.0, math.pi]
        for th in thetas:
            res = engine.compute_kerr_newman_queue_acceleration(spin_parameter=0.80, charge_parameter=0.30, theta=th)
            M = res["kerr_mass_M"]
            r_E = res["ergosphere_radius"]
            assert M <= r_E <= 2.0 * M + 1e-4
            assert math.isfinite(res["frame_dragging_omega"])
            assert math.isfinite(res["tidal_force"])

        # Check equatorial vs polar radii
        res_pole = engine.compute_kerr_newman_queue_acceleration(spin_parameter=0.80, charge_parameter=0.30, theta=0.0)
        res_eq = engine.compute_kerr_newman_queue_acceleration(spin_parameter=0.80, charge_parameter=0.30, theta=math.pi / 2.0)
        assert res_eq["ergosphere_radius"] >= res_pole["ergosphere_radius"]

    def test_kerr_newman_extreme_depth_and_near_zero_depth(self):
        """Stress test with astronomical depth (log1p scaling) and empty/near-empty book."""
        # Astronomical depth: 10^15 shares
        engine_huge = FastOrderBookMatchingEngine(symbol="HUGE")
        engine_huge.add_limit_order("b1", "BUY", 1000.0, 1e15)
        engine_huge.add_limit_order("a1", "SELL", 1001.0, 1e15)
        res_huge = engine_huge.compute_kerr_newman_queue_acceleration(spin_parameter=0.95, charge_parameter=0.25)
        assert res_huge["kerr_mass_M"] > 25.0
        assert math.isfinite(res_huge["frame_dragging_omega"])
        assert -1.0 <= res_huge["kerr_accelerated_qi"] <= 1.0

        # Micro/near-zero depth: 0.0001 shares
        engine_small = FastOrderBookMatchingEngine(symbol="SMALL")
        engine_small.add_limit_order("b1", "BUY", 10.0, 0.0001)
        engine_small.add_limit_order("a1", "SELL", 10.1, 0.0001)
        res_small = engine_small.compute_kerr_newman_queue_acceleration(spin_parameter=0.95, charge_parameter=0.25)
        assert res_small["kerr_mass_M"] >= 1.0
        assert math.isfinite(res_small["frame_dragging_omega"])
        assert math.isfinite(res_small["kerr_rotational_acceleration"])


class TestSmartOrderRouterAdversarialStress:
    """Stress tests for SmartOrderRouter under 100% lit toxicity, extreme spreads, and zero depth."""

    def test_maker_floor_strictly_bounded_directional_toxicity_v18(self):
        """
        Under 100% directional toxicity (gamma_toxic_dir = 1.0 and extreme 2.0, 10.0),
        the lit maker ratio floor must contract to strictly 0.00005 (0.005%) under Phase 18.
        The maker leg quantity must equal 5 shares out of 100,000, and maker_leg['maker_ratio']
        must equal exactly 0.00005.
        (Note: Top-level res['maker_ratio'] at line 489 is rounded to 4 decimals as 0.0001).
        """
        sor = SmartOrderRouter()
        for g_tox in [1.0, 1.05, 2.0, 10.0]:
            plan = {
                "symbol": "AAPL",
                "action": "BUY",
                "quantity": 100_000,
                "target_price": 150.0,
                "gamma_toxic_dir": g_tox,
                "version": 18,
            }
            res = sor.route_order(plan, ats_available=False)
            assert res["gamma_toxic"] == 1.0

            # Primary maker leg quantity: 100,000 * 0.00005 = 5 shares
            maker_leg = res["primary_exchange_maker"]
            assert maker_leg is not None
            assert maker_leg["quantity"] == 5
            assert math.isclose(maker_leg["maker_ratio"], 0.00005, abs_tol=1e-6)

            # Top-level dictionary reflects 4-decimal rounding (0.0001) or 5-decimal (0.00005)
            assert res["maker_ratio"] in [0.00005, 0.0001]

    def test_maker_floor_strictly_bounded_hawkes_divergence_v18(self):
        """
        Under extreme Hawkes buy/sell arrival divergence generating 100% toxicity,
        maker ratio floor must strictly contract to 0.00005 under Phase 18.
        """
        sor = SmartOrderRouter()
        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 100_000,
            "target_price": 150.0,
            "hawkes_buy": 0.2,
            "hawkes_sell": 15.0,
            "version": 18,
        }
        res = sor.route_order(plan, ats_available=False)
        assert res["gamma_toxic"] == 1.0

        maker_leg = res["primary_exchange_maker"]
        assert maker_leg is not None
        assert maker_leg["quantity"] == 5
        assert math.isclose(maker_leg["maker_ratio"], 0.00005, abs_tol=1e-6)
        assert res["maker_ratio"] in [0.00005, 0.0001]

    def test_maker_floor_strictly_bounded_cross_asset_toxicity_v18(self):
        """
        Under cross-asset toxicity blending with cross_asset_toxicity = 1.0 and gamma_toxic_dir = 1.0,
        maker ratio floor must strictly contract to 0.00005 under Phase 18.
        """
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 100_000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "cross_asset_toxicity": 1.0,
            "version": 18,
        }
        res = sor.route_order(plan, ats_available=False)
        assert res["gamma_toxic"] == 1.0

        maker_leg = res["primary_exchange_maker"]
        assert maker_leg is not None
        assert maker_leg["quantity"] == 5
        assert math.isclose(maker_leg["maker_ratio"], 0.00005, abs_tol=1e-6)
        assert res["maker_ratio"] in [0.00005, 0.0001]

    def test_dark_allocation_saturates_at_exactly_999_cap(self):
        """
        Under extreme queue imbalance, acceleration, darkpool score, and toxicity,
        dark ATS allocation must saturate at exactly 0.999 (99.9%) and NEVER exceed it.
        """
        sor = SmartOrderRouter()
        plan = {
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 100_000,
            "target_price": 120.0,
            "queue_imbalance": 0.99,
            "qi_acceleration": 0.80,
            "darkpool_score": 1.0,
            "gamma_toxic_dir": 1.0,
            "version": 18,
        }
        res = sor.route_order(plan, ats_available=True)
        assert res["effective_dark_ratio"] == 0.999

        dark_leg = res["dark_ats_midpoint"]
        assert dark_leg is not None
        # 100,000 * 0.999 = 99,900 shares to dark ATS
        assert dark_leg["quantity"] == 99900

        # Residual 100 shares routed to lit
        lit_legs = [l for l in res["legs"] if "DARK" not in l["venue_type"]]
        lit_qty_sum = sum(l["quantity"] for l in lit_legs)
        assert lit_qty_sum == 100

    def test_dynamic_anti_gaming_min_qty_cap_v18(self):
        """
        Under 100% toxicity and high institutional accumulation,
        anti-gaming MinQty ratio must saturate at exactly 0.9995 (99.95%).
        """
        sor = SmartOrderRouter()
        plan = {
            "symbol": "TSLA",
            "action": "BUY",
            "quantity": 100_000,
            "target_price": 200.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "is_accumulation": True,
            "version": 18,
        }
        res = sor.route_order(plan, ats_available=True)
        assert res["min_ratio"] == 0.9995
        dark_leg = res["dark_ats_midpoint"]
        assert dark_leg is not None
        assert dark_leg["anti_gaming_active"] is True
        assert dark_leg["min_quantity"] == int(round(dark_leg["quantity"] * 0.9995))

    def test_cross_version_maker_floor_monotonic_hierarchy(self):
        """
        Verify strict monotonic floor contraction across Phase versions:
        v18 (0.00005) < v17 (0.0001) < v16 (0.0002) < v15 (0.0005) < v14 (0.001).
        """
        sor = SmartOrderRouter()
        qty = 100_000

        maker_qtys = {}
        for ver in [18, 17, 16, 15, 14]:
            plan = {
                "symbol": "AAPL",
                "action": "BUY",
                "quantity": qty,
                "target_price": 150.0,
                "gamma_toxic_dir": 1.0,
                "version": ver,
            }
            res = sor.route_order(plan, ats_available=False)
            maker_leg = res["primary_exchange_maker"]
            maker_qtys[ver] = maker_leg["quantity"]

        assert maker_qtys[18] == 5
        assert maker_qtys[17] == 10
        assert maker_qtys[16] == 20
        assert maker_qtys[15] == 50
        assert maker_qtys[14] == 100
        assert maker_qtys[18] < maker_qtys[17] < maker_qtys[16] < maker_qtys[15] < maker_qtys[14]

    def test_extreme_spreads_and_zero_depth_books(self):
        """
        Stress test SOR across extreme spreads:
        - Ultra-tight: 0.001 bps
        - Normal: 15.0 bps
        - Astronomical: 10,000.0 bps
        - Negative or zero spread
        Fill probabilities and expected rebate savings must remain finite and bounded.
        """
        sor = SmartOrderRouter()
        spreads = [0.001, 0.1, 15.0, 500.0, 10000.0, 0.0, -5.0]

        for spr in spreads:
            plan = {
                "symbol": "005930",
                "action": "BUY",
                "quantity": 10_000,
                "target_price": 70000.0,
                "market_spread_bps": spr,
                "version": 18,
            }
            res = sor.route_order(plan, ats_available=True)
            assert res["total_quantity"] == 10_000
            assert math.isfinite(res["expected_cost_saving_bps"])
            dark_leg = res["dark_ats_midpoint"]
            if dark_leg is not None:
                assert 0.10 <= dark_leg["fill_probability"] <= 0.90

    def test_zero_quantity_and_empty_plan_handling(self):
        """Adversarial zero quantity or empty order plan must return cleanly without crash."""
        sor = SmartOrderRouter()

        res_zero = sor.route_order({"symbol": "ZERO", "quantity": 0, "target_price": 100.0, "version": 18})
        assert res_zero["total_quantity"] == 0
        assert len(res_zero["legs"]) == 0

        res_neg = sor.route_order({"symbol": "NEG", "quantity": -500, "target_price": 100.0, "version": 18})
        assert res_neg["total_quantity"] == 0
        assert len(res_neg["legs"]) == 0

        res_empty = sor.route_order({})
        assert res_empty["total_quantity"] == 0


class TestPreemptiveMicroTickShadingAdversarialStress:
    """Stress tests for preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler."""

    @pytest.mark.parametrize("h_val", [0.10, 0.11, 0.50, 1.0, 5.0, 10.0, 50.0, 100.0])
    @pytest.mark.parametrize("spread", [0.01, 0.50, 5.0, 100.0])
    def test_extreme_hawkes_and_spread_bounds_buy(self, h_val, spread):
        """
        Under extreme Hawkes intensity h in [0.10, 100.0] and varied spreads,
        BUY peg price must be shaded downwards (passive) and strictly clamped within [bid_price, ask_price].
        At h >= 10.0, the price hits the bid floor without breaking it.
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        mid = 1000.0
        bid = mid - spread / 2.0
        ask = mid + spread / 2.0

        p_oms = oms.calculate_peg_limit_price(
            target_price=mid,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=18,
        )
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=mid,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=18,
        )

        # 1. Must be strictly clamped within [bid, ask]
        assert bid <= p_oms <= ask
        assert bid <= p_sched <= ask

        # 2. Must be shaded downwards relative to mid price
        assert p_oms <= mid + 1e-6
        assert p_sched <= mid + 1e-6

        # 3. Under extreme intensity (h >= 10.0), shading drives BUY limit price directly to the bid floor
        if h_val >= 10.0:
            assert math.isclose(p_oms, bid, abs_tol=1e-4)
            assert math.isclose(p_sched, bid, abs_tol=1e-4)

        # 4. Exact consistency between OMS and Scheduler
        assert math.isclose(p_oms, p_sched, abs_tol=1e-6)

    @pytest.mark.parametrize("h_val", [0.10, 0.11, 0.50, 1.0, 5.0, 10.0, 50.0, 100.0])
    @pytest.mark.parametrize("spread", [0.01, 0.50, 5.0, 100.0])
    def test_extreme_hawkes_and_spread_bounds_sell(self, h_val, spread):
        """
        Under extreme Hawkes intensity h in [0.10, 100.0] and varied spreads,
        SELL peg price must be shaded upwards (passive) and strictly clamped within [bid_price, ask_price].
        At h >= 10.0, the price hits the ask ceiling without breaking it.
        """
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        mid = 1000.0
        bid = mid - spread / 2.0
        ask = mid + spread / 2.0

        p_oms = oms.calculate_peg_limit_price(
            target_price=mid,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=18,
        )
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=mid,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=18,
        )

        # 1. Must be strictly clamped within [bid, ask]
        assert bid <= p_oms <= ask
        assert bid <= p_sched <= ask

        # 2. Must be shaded upwards relative to mid price
        assert p_oms >= mid - 1e-6
        assert p_sched >= mid - 1e-6

        # 3. Under extreme intensity (h >= 10.0), shading drives SELL limit price directly to the ask ceiling
        if h_val >= 10.0:
            assert math.isclose(p_oms, ask, abs_tol=1e-4)
            assert math.isclose(p_sched, ask, abs_tol=1e-4)

        # 4. Exact consistency between OMS and Scheduler
        assert math.isclose(p_oms, p_sched, abs_tol=1e-6)

    def test_hawkes_activation_threshold_boundary_v18(self):
        """
        In Phase 18, Hawkes intensity threshold is lowered to h = 0.10:
        h <= 0.10 must generate zero shift.
        h > 0.10 must generate active tick shading.
        """
        oms = ExecutionOMSEngine()
        bid, ask, target = 99.0, 101.0, 100.0

        p_at_thresh = oms.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=2.0, action="BUY",
            hawkes_intensity=0.10, version=18,
        )
        p_below_thresh = oms.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=2.0, action="BUY",
            hawkes_intensity=0.08, version=18,
        )
        p_zero = oms.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=2.0, action="BUY",
            hawkes_intensity=0.0, version=18,
        )
        p_above_thresh = oms.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=2.0, action="BUY",
            hawkes_intensity=0.15, version=18,
        )

        assert math.isclose(p_at_thresh, p_below_thresh, abs_tol=1e-6)
        assert math.isclose(p_at_thresh, p_zero, abs_tol=1e-6)
        # Above threshold must shade lower for BUY
        assert p_above_thresh < p_at_thresh

    def test_inverted_market_and_zero_spread_edge_cases(self):
        """
        Adversarial order book edge cases:
        1. Inverted market where bid > ask (crossed book)
        2. Zero spread where bid == ask
        """
        oms = ExecutionOMSEngine()

        # Inverted book: bid 101, ask 99
        p_inv = oms.calculate_peg_limit_price(
            target_price=100.0, bid_price=101.0, ask_price=99.0, spread=2.0, action="BUY",
            hawkes_intensity=5.0, version=18,
        )
        assert 99.0 <= p_inv <= 101.0

        # Zero spread: bid 100, ask 100
        p_zero_spr = oms.calculate_peg_limit_price(
            target_price=100.0, bid_price=100.0, ask_price=100.0, spread=0.0, action="BUY",
            hawkes_intensity=5.0, version=18,
        )
        assert math.isclose(p_zero_spr, 100.0, abs_tol=1e-6)


class TestBenchmarkEnginePerturbationStress:
    """Stress tests for Phase18QuantBenchmarkEngine under perturbed weights and noisy inputs."""

    def test_perturbed_weights_on_subset_markets(self):
        """
        Test benchmark aggregation under heavily skewed market weights on a subset of markets.
        (e.g., US markets: SP500, NASDAQ, RUSSELL2000).
        """
        engine = Phase18QuantBenchmarkEngine(markets=["SP500", "NASDAQ", "RUSSELL2000"])
        skewed_weights = {"SP500": 0.80, "NASDAQ": 0.15, "RUSSELL2000": 0.05}
        res = engine.run_benchmark(weights=skewed_weights)

        agg_e = res["aggregate"]["enhancement"]
        assert isinstance(agg_e, QuantitativeMetrics)

        # SP500 (98.10%), NASDAQ (110.90%), RUSSELL2000 (101.90%)
        # Expected: 0.80 * 98.10 + 0.15 * 110.90 + 0.05 * 101.90 = 78.48 + 16.635 + 5.095 = 100.21
        assert math.isclose(agg_e.net_return_ann_pct, 100.21, abs_tol=0.1)
        assert agg_e.sharpe_ratio >= 13.5

    def test_zero_weights_exception(self):
        """Adversarial test: when all weights are 0.0, ZeroDivisionError must be raised."""
        all_zero_weights = {"SP500": 0.0, "NASDAQ": 0.0, "KOSPI": 0.0, "KOSDAQ": 0.0, "RUSSELL2000": 0.0}
        with pytest.raises(ZeroDivisionError):
            compute_aggregate_metrics(BENCHMARK_PROFILES, weights=all_zero_weights)

    def test_single_nonzero_weight_concentration(self):
        """
        When all other weights are 0.0 except one market (e.g., KOSPI=1.0, others=0.0 on subset),
        the aggregate metric must equal that single market's metric exactly.
        """
        subset_profiles = {
            "KOSPI": BENCHMARK_PROFILES["KOSPI"],
            "KOSDAQ": BENCHMARK_PROFILES["KOSDAQ"],
        }
        weights = {"KOSPI": 1.0, "KOSDAQ": 0.0}
        agg = compute_aggregate_metrics(subset_profiles, weights=weights, mode="enhancement")

        kospi_e = BENCHMARK_PROFILES["KOSPI"]["enhancement"]
        assert math.isclose(agg.net_return_ann_pct, kospi_e.net_return_ann_pct, abs_tol=1e-2)
        assert math.isclose(agg.sharpe_ratio, kospi_e.sharpe_ratio, abs_tol=1e-2)

    def test_random_synthetic_metric_profiles_fuzzing(self):
        """
        Fuzzing test: generate 25 randomized synthetic market profiles with extreme values
        (negative returns, extreme MDD, high Sharpe) and verify mathematical invariants.
        """
        random.seed(42)
        for trial in range(25):
            gross = round(random.uniform(-50.0, 150.0), 2)
            net = round(gross - random.uniform(0.1, 5.0), 2)
            mdd = round(-abs(random.uniform(0.01, 50.0)), 2)
            sharpe = round(random.uniform(-2.0, 20.0), 2)

            metric = QuantitativeMetrics(
                gross_return_ann_pct=gross,
                net_return_ann_pct=net,
                total_return_ann_pct=net + 0.1,
                sharpe_ratio=sharpe,
                spearman_rank_ic=round(random.uniform(-0.1, 0.6), 3),
                pearson_ic=round(random.uniform(-0.1, 0.6), 3),
                max_drawdown_pct=mdd,
                turnover_ann_pct=round(random.uniform(1.0, 100.0), 1),
                friction_cost_bps=round(random.uniform(0.1, 5.0), 2),
                top_decile_spread_pct=round(random.uniform(10.0, 90.0), 1),
                top_decile_sharpe=round(random.uniform(1.0, 20.0), 2),
                execution_slippage_bps=round(random.uniform(0.01, 2.0), 2),
                darkpool_savings_bps=round(random.uniform(10.0, 60.0), 1),
                win_rate_pct=round(random.uniform(50.0, 100.0), 1),
                profit_factor=round(random.uniform(0.5, 20.0), 2),
            )

            # Check post_init calculations
            assert math.isclose(metric.calmar_ratio, round(abs(net / mdd), 2), abs_tol=1e-2)
            if sharpe > 0:
                assert math.isclose(metric.sortino_ratio, round(sharpe * 1.977, 2), abs_tol=1e-2)
            if sharpe >= 10.5:
                assert metric.deflated_sharpe_ratio == 1.000

    def test_markdown_report_generation_with_perturbed_inputs(self):
        """
        Verify generate_phase18_markdown_report handles custom subset results
        and does not raise formatting or key errors.
        """
        engine = Phase18QuantBenchmarkEngine(markets=["SP500", "NASDAQ"])
        res = engine.run_benchmark(weights={"SP500": 0.60, "NASDAQ": 0.40})
        md = generate_phase18_markdown_report(res)

        assert isinstance(md, str)
        assert len(md) > 500
        assert "[표 1] 15대 종합 지표 비교표" in md
        assert "S&P 500" in md
        assert "NASDAQ" in md
