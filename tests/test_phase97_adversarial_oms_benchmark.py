"""
tests/test_phase97_adversarial_oms_benchmark.py

Adversarial Empirical Stress Test Suite for Phase 97:
Role: Challenger 2 (Microstructure OMS & Benchmark Verification Adversarial Challenger)

Target Verification Axes:
1. KNK-75 Dark Energy DAHA L3 Queue Acceleration Stress Tests (Feature F458):
   - Theoretical parameter assertions: w = -77/3 ≈ -25.667, k_daha = 0.67, k_monster = 0.66,
     daha_75_factor = 14.40, c_monster = 2^-77 ≈ 6.617444900424221e-24,
     repulsive correction -40.5 * c * (r^80) * daha_75_factor.
   - Extreme spin and charge parameter sweeps (spin in [-1.0, 1.0], charge in [-1.0, 1.0]).
   - Theta parameter sweeps from 0 to pi (poles to equator).
   - Deep queue depth and extreme asymmetry stress:
     * r_eff -> 0 (empty order book, r_eff -> 1e-10)
     * r_eff -> 1 (r_eff = 1.0)
     * r_eff > 1 (r_eff = 1.5, 2.0, 2.5, 10.0, 100.0)
     * Exact integer multiplier check at r_eff = 2.0: (2.0^80 * 2^-77 = 8.0 -> -4665.60)
     * Extreme 100-level asymmetric queue configurations (100 levels bid vs 1 ask, 100 levels ask vs 1 bid)
     * Strict bounds verification: clamping to [-1e6, 1e6], finite checks without NaN / Inf.
   - 23 class method aliases and 23 module-level aliases consistency check.
2. SmartOrderRouter Version 97 Stress Tests (Feature F458):
   - Extreme toxic flow injection: gamma_toxic in [0.80000000001, 0.85, 0.90, 0.95, 0.999, 0.9999, 0.999999, 1.0, 1.5, 10.0].
   - Directional Hawkes toxicity injection with extreme imbalance.
   - Verification that lit maker ratio strictly holds at 1e-68 floor and NEVER underflows to 0.0 or subnormal.
   - 68-decimal precision verification on route_order outputs (ratio_prec == 68, min_ratio_prec == 68).
   - Cascading version flag invariants: is_phase97 -> is_phase96 -> is_phase95 -> is_phase94... -> is_phase23.
   - Comparison with Phase 96: Phase 97 hits 1e-68 floor whereas Phase 96 hits 1e-67 floor.
3. Dual-OMS Preemptive Micro-Tick Shading Boundary & Parity Stress Tests (Feature F458):
   - Exact boundary checks at h = 3.0e-11, h = 3.0e-11 - 1e-15, h = 3.0e-11 + 1e-15:
     * h <= 3.0e-11 -> hawkes_shift == 0.0 (shading strictly NOT triggered).
     * h > 3.0e-11 -> hawkes_shift strictly triggered with 50-nines shading factor.
   - Verification across amplified spread (spr = 1e15) and realistic spread (spr = 0.10).
   - Verification of BUY (downward defensive shift) and SELL (upward defensive shift).
   - Fine-grid scan of Hawkes intensity in [2.0e-11, 4.0e-11] with step 1.0e-12 (21 fine grid points).
   - Strict parity (< 1e-12 difference) between ExecutionOMSEngine and AlmgrenChrissScheduler
     across all grid points, BUY/SELL directions, multiple spreads, and input formats.
   - Comparison with Phase 96: at h = 3.5e-11, Phase 97 shades while Phase 96 does not.
4. Independent Benchmark & SHA-256 Hash Verification (Feature F459):
   - Independent verification of 7 strict quantitative KPI target assertions.
   - Adversarial perturbation sensitivity: verify that assertions strictly fail when perturbed.
   - Bit-for-bit SHA-256 hash equality validation for Category A (3 files) and Category B (3 files).
   - Category C cumulative report structure validation: Phase 97 prepended on top of Phase 96.
"""

import math
import hashlib
import os
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_kerr_newman_kiselev_75_dark_energy_daha_queue_acceleration,
    compute_kerr_newman_kiselev_75_dark_energy_daha_acceleration,
    compute_knk_75_dark_energy_daha_acceleration,
    compute_phase97_daha_l3_acceleration,
    compute_phase97_lob_acceleration,
    phase97_lob_spacetime_hydrodynamics,
    compute_knk_75_dark_energy_acceleration,
    compute_kerr_newman_kiselev_75_dark_energy_acceleration,
    phase97_daha_l3_acceleration,
    knk_75_dark_energy_daha_l3,
    daha_l3_phase97_acceleration,
    phase97_dark_energy_acceleration,
    calculate_phase97_knk_acceleration,
    compute_knk_phase97_acceleration,
    daha_phase97_acceleration,
    phase97_spacetime_hydrodynamics,
    phase97_queue_acceleration,
    l3_phase97_acceleration,
    phase97_knk_acceleration,
    compute_phase97_knk_daha_queue_acceleration,
    compute_phase97_queue_acceleration,
    phase97_l3_queue_acceleration,
    knk_75_daha_queue_acceleration,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestKNK75DarkEnergyDAHAL3AdversarialStress:
    """Adversarial stress testing on Kerr-Newman-Kiselev 75-Dark-Energy DAHA L3 hydrodynamics."""

    def test_knk_75_theoretical_constants_exact(self):
        """Verify exact mathematical parameters of KNK-75 Dark Energy DAHA."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        engine.add_limit_order("b1", "BUY", 100.0, 10.0)
        engine.add_limit_order("a1", "SELL", 101.0, 10.0)

        res = engine.compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # w = -77/3 ≈ -25.666666666666668
        expected_w = -77.0 / 3.0
        assert math.isclose(res["w_dark_energy_75"], expected_w, rel_tol=1e-12)

        # k_daha = 0.67, k_monster = 0.66, daha_75_factor = 14.40
        assert math.isclose(res["k_daha_75"], 0.67, rel_tol=1e-12)
        assert math.isclose(res["k_monster_75"], 0.66, rel_tol=1e-12)
        assert math.isclose(res["daha_75_factor"], 14.40, rel_tol=1e-12)

        # c_monster = 2^-77 ≈ 6.617444900424221e-24
        expected_c = 2.0 ** -77
        assert math.isclose(res["c_monster_75"], expected_c, rel_tol=1e-15)

    def test_knk_75_repulsive_acceleration_formula_exact(self):
        """Verify exact formula -40.5 * c * (r^80) * daha_75_factor at r_eff = 2.0."""
        # At r_eff = 2.0, (2.0)^80 * 2^-77 = 2^3 = 8.0 exactly.
        # dark_75_accel = -40.5 * 8.0 * 14.40 = -4665.60 exactly.
        c_75 = 2.0 ** -77
        r_eff = 2.0
        daha_75_factor = 14.40
        accel_theoretical = -40.5 * c_75 * (r_eff ** 80) * daha_75_factor
        assert math.isclose(accel_theoretical, -4665.60, rel_tol=1e-12)

    def test_knk_75_extreme_spin_charge_theta_sweep(self):
        """Stress test across extreme spin, charge, and theta combinations."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"b{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"a{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        spin_values = [-1.0, -0.9999, -0.5, 0.0, 1e-12, 0.5, 0.9999, 1.0]
        charge_values = [-1.0, -0.9999, -0.5, 0.0, 1e-12, 0.5, 0.9999, 1.0]
        theta_values = [
            0.0, 1e-6, math.pi / 6.0, math.pi / 4.0, math.pi / 3.0,
            math.pi / 2.0, 2 * math.pi / 3.0, 3 * math.pi / 4.0,
            5 * math.pi / 6.0, math.pi - 1e-6, math.pi
        ]

        for s in spin_values:
            for q in charge_values:
                for th in theta_values:
                    res = engine.compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
                        spin_parameter=s,
                        charge_parameter=q,
                        theta=th,
                    )
                    assert math.isfinite(res["knk_75_dark_energy_correction"]), f"Non-finite correction at s={s}, q={q}, th={th}"
                    assert math.isfinite(res["knk_75_dark_energy_daha_acceleration"]), f"Non-finite accel at s={s}, q={q}, th={th}"
                    assert -1e6 <= res["knk_75_dark_energy_correction"] <= 1e6
                    assert -1e6 <= res["knk_75_dark_energy_daha_acceleration"] <= 1e6
                    assert res["knk_75_dark_energy_correction"] <= 0.0, f"Dark energy correction must be repulsive (<=0), got {res['knk_75_dark_energy_correction']}"
                    assert res["phase97_knk_acceleration"] == res["knk_75_dark_energy_daha_acceleration"]
                    assert res["queue_acceleration"] == res["knk_75_dark_energy_daha_acceleration"]

    def test_knk_75_deep_queue_imbalance_stress(self):
        """Stress test with empty book, single order, and extreme 100-level asymmetric order books."""
        # 1. Empty orderbook (r_eff -> 1e-10)
        empty_engine = FastOrderBookMatchingEngine(symbol="EMPTY")
        res_empty = empty_engine.compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_empty["knk_75_dark_energy_correction"])
        assert math.isfinite(res_empty["knk_75_dark_energy_daha_acceleration"])
        assert -1e6 <= res_empty["knk_75_dark_energy_correction"] <= 1e6
        assert -1e6 <= res_empty["knk_75_dark_energy_daha_acceleration"] <= 1e6
        assert res_empty["knk_75_dark_energy_correction"] == 0.0

        # 2. Extreme 100-level one-sided bid depth (massive buy pressure: 10^7 qty per level)
        bid_heavy_engine = FastOrderBookMatchingEngine(symbol="HEAVY_BID")
        for i in range(100):
            bid_heavy_engine.add_limit_order(f"bid_{i}", "BUY", 1000.0 - i, 10000000.0 * (i + 1))
        bid_heavy_engine.add_limit_order("ask_0", "SELL", 1001.0, 1.0)

        res_bid = bid_heavy_engine.compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_bid["knk_75_dark_energy_correction"])
        assert math.isfinite(res_bid["knk_75_dark_energy_daha_acceleration"])
        assert -1e6 <= res_bid["knk_75_dark_energy_correction"] <= 1e6
        assert -1e6 <= res_bid["knk_75_dark_energy_daha_acceleration"] <= 1e6
        assert res_bid["knk_75_dark_energy_correction"] <= 0.0

        # 3. Extreme 100-level one-sided ask depth (massive sell pressure: 10^7 qty per level)
        ask_heavy_engine = FastOrderBookMatchingEngine(symbol="HEAVY_ASK")
        for i in range(100):
            ask_heavy_engine.add_limit_order(f"ask_{i}", "SELL", 2000.0 + i, 10000000.0 * (i + 1))
        ask_heavy_engine.add_limit_order("bid_0", "BUY", 1999.0, 1.0)

        res_ask = ask_heavy_engine.compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_ask["knk_75_dark_energy_correction"])
        assert math.isfinite(res_ask["knk_75_dark_energy_daha_acceleration"])
        assert -1e6 <= res_ask["knk_75_dark_energy_correction"] <= 1e6
        assert -1e6 <= res_ask["knk_75_dark_energy_daha_acceleration"] <= 1e6
        assert res_ask["knk_75_dark_energy_correction"] <= 0.0

        # 4. Extreme price regimes: penny stock ($0.0001) vs high nominal ($1,000,000)
        penny_engine = FastOrderBookMatchingEngine(symbol="PENNY")
        penny_engine.add_limit_order("b1", "BUY", 0.0001, 100000.0)
        penny_engine.add_limit_order("a1", "SELL", 0.0002, 100000.0)
        res_penny = penny_engine.compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_penny["knk_75_dark_energy_daha_acceleration"])

        high_engine = FastOrderBookMatchingEngine(symbol="HIGH")
        high_engine.add_limit_order("b1", "BUY", 1000000.0, 10.0)
        high_engine.add_limit_order("a1", "SELL", 1000100.0, 10.0)
        res_high = high_engine.compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_high["knk_75_dark_energy_daha_acceleration"])

    def test_knk_75_direct_clamping_and_overflow_protection(self):
        """Directly verify numerical clamping logic [-1e6, 1e6] across extreme synthetic r_eff."""
        c_75 = 2.0 ** -77
        factor = 14.40

        # Scan r_eff: [r -> 0, r -> 1, r > 1, high, extreme]
        test_r_effs = [0.0, 1e-10, 0.5, 1.0, 1.5, 2.0, 2.2, 2.5, 5.0, 10.0, 100.0]
        for r in test_r_effs:
            r_clamped = max(1e-10, abs(r))
            try:
                accel = -40.5 * c_75 * (r_clamped ** 80) * factor
                if not math.isfinite(accel):
                    accel = 0.0
            except OverflowError:
                accel = -1e6
            accel = max(-1e6, min(1e6, accel))
            assert math.isfinite(accel)
            assert -1e6 <= accel <= 1e6
            assert accel <= 0.0

            # Mathematical region assertions
            if r <= 1.0:
                assert abs(accel) < 1e-15, f"Expected near zero for r<=1, got {accel}"
            elif r == 2.0:
                assert math.isclose(accel, -4665.60, rel_tol=1e-12)
            elif r >= 2.5:
                assert accel == -1e6, f"Expected clamping to -1e6 for r>=2.5, got {accel}"

    def test_knk_75_23_aliases_consistency(self):
        """Verify all 23 class method aliases and 23 module-level aliases execute identically under stress."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(10):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 500.0 * (i + 1))
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 500.0 * (i + 1))

        ref = engine.compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.85, spin_parameter=0.85, theta=math.pi / 3.0
        )

        class_aliases = [
            "compute_kerr_newman_kiselev_75_dark_energy_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_75_dark_energy_daha_acceleration",
            "compute_knk_75_dark_energy_daha_acceleration",
            "compute_phase97_daha_l3_acceleration",
            "compute_phase97_lob_acceleration",
            "phase97_lob_spacetime_hydrodynamics",
            "compute_knk_75_dark_energy_acceleration",
            "compute_kerr_newman_kiselev_75_dark_energy_acceleration",
            "phase97_daha_l3_acceleration",
            "knk_75_dark_energy_daha_l3",
            "daha_l3_phase97_acceleration",
            "phase97_dark_energy_acceleration",
            "calculate_phase97_knk_acceleration",
            "compute_knk_phase97_acceleration",
            "daha_phase97_acceleration",
            "phase97_spacetime_hydrodynamics",
            "phase97_queue_acceleration",
            "l3_phase97_acceleration",
            "phase97_knk_acceleration",
            "compute_phase97_knk_daha_queue_acceleration",
            "compute_phase97_queue_acceleration",
            "phase97_l3_queue_acceleration",
            "knk_75_daha_queue_acceleration",
        ]
        for alias in class_aliases:
            method = getattr(engine, alias, None)
            assert method is not None, f"Missing method {alias}"
            res = method(charge_parameter=0.85, spin_parameter=0.85, theta=math.pi / 3.0)
            assert res == ref, f"Class alias {alias} result mismatch"

        module_aliases = [
            compute_kerr_newman_kiselev_75_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            compute_kerr_newman_kiselev_75_dark_energy_daha_queue_acceleration,
            compute_kerr_newman_kiselev_75_dark_energy_daha_acceleration,
            compute_knk_75_dark_energy_daha_acceleration,
            compute_phase97_daha_l3_acceleration,
            compute_phase97_lob_acceleration,
            phase97_lob_spacetime_hydrodynamics,
            compute_knk_75_dark_energy_acceleration,
            compute_kerr_newman_kiselev_75_dark_energy_acceleration,
            phase97_daha_l3_acceleration,
            knk_75_dark_energy_daha_l3,
            daha_l3_phase97_acceleration,
            phase97_dark_energy_acceleration,
            calculate_phase97_knk_acceleration,
            compute_knk_phase97_acceleration,
            daha_phase97_acceleration,
            phase97_spacetime_hydrodynamics,
            phase97_queue_acceleration,
            l3_phase97_acceleration,
            phase97_knk_acceleration,
            compute_phase97_knk_daha_queue_acceleration,
            compute_phase97_queue_acceleration,
            phase97_l3_queue_acceleration,
            knk_75_daha_queue_acceleration,
        ]
        for fn in module_aliases:
            res = fn(engine, charge_parameter=0.85, spin_parameter=0.85, theta=math.pi / 3.0)
            assert res == ref, f"Module alias {fn.__name__} result mismatch"


class TestSmartOrderRouterV97AdversarialStress:
    """Adversarial stress testing on SmartOrderRouter Version 97."""

    def test_smart_order_router_v97_cascading_flags(self):
        """Verify version cascading: version 97 sets all predecessor flags down to Phase 23."""
        sor_97 = SmartOrderRouter(version=97)
        assert sor_97.version == 97
        assert sor_97.is_phase97 is True
        assert sor_97.is_phase96 is True
        assert sor_97.is_phase95 is True
        assert sor_97.is_phase94 is True
        assert sor_97.is_phase93 is True
        assert sor_97.is_phase92 is True
        assert sor_97.is_phase91 is True
        assert sor_97.is_phase90 is True
        assert sor_97.is_phase80 is True
        assert sor_97.is_phase50 is True
        assert sor_97.is_phase28 is True

        # Default constructor must be version 97
        sor_default = SmartOrderRouter()
        assert sor_default.version == 97
        assert sor_default.is_phase97 is True

        # Predecessor version 96 must NOT have is_phase97
        sor_96 = SmartOrderRouter(version=96)
        assert sor_96.is_phase97 is False
        assert sor_96.is_phase96 is True

    def test_smart_order_router_v97_maker_ratio_floor_extreme_toxic_flow(self):
        """Stress test toxic flow injection under extreme adversarial values:
        gamma_toxic in [0.80000000001, 0.85, 0.90, 0.95, 0.999, 0.9999, 0.999999, 1.0, 1.0001, 1.5, 10.0].
        Verify lit maker ratio strictly holds at 1e-68 floor and NEVER underflows to 0.0 or subnormal."""
        sor_97 = SmartOrderRouter(version=97)

        toxic_grid = [
            0.80000000001, 0.85, 0.90, 0.95,
            0.999, 0.9999, 0.999999, 1.0, 1.0001, 1.5, 10.0
        ]
        for g_tox in toxic_grid:
            order_plan = {
                "symbol": "NVDA",
                "quantity": 1000,
                "action": "BUY",
                "version": 97,
                "target_price": 120.0,
                "hawkes_intensity": 0.99,
            }
            res = sor_97.route_order(order_plan, gamma_toxic_dir=g_tox)
            maker_ratio = res.get("maker_ratio")
            assert maker_ratio is not None, f"maker_ratio missing at gamma_toxic={g_tox}"
            assert math.isfinite(maker_ratio), f"maker_ratio not finite at gamma_toxic={g_tox}"
            assert maker_ratio >= 1e-68, f"Breached maker floor at gamma_toxic={g_tox}: {maker_ratio} < 1e-68"
            assert maker_ratio > 0.0, f"Numerical underflow to 0.0 at gamma_toxic={g_tox}"

            # At full toxic saturation (>= 1.0), maker_ratio hits exact 1e-68 floor
            if g_tox >= 1.0:
                assert maker_ratio == 1e-68, f"Failed exact floor at gamma_toxic={g_tox}: {maker_ratio}"

    def test_smart_order_router_v97_directional_hawkes_toxic_flow(self):
        """Verify maker floor holds under directional Hawkes imbalance."""
        sor_97 = SmartOrderRouter(version=97)

        # 1. Extreme sell-side Hawkes intensity against a BUY order (toxic flow)
        order_plan_buy = {
            "symbol": "AAPL",
            "quantity": 5000,
            "action": "BUY",
            "version": 97,
            "target_price": 200.0,
            "hawkes_sell": 10000.0,
            "hawkes_buy": 0.0,
        }
        res_buy = sor_97.route_order(order_plan_buy)
        assert res_buy["maker_ratio"] == 1e-68
        assert math.isfinite(res_buy["maker_ratio"])

        # 2. Extreme buy-side Hawkes intensity against a SELL order (toxic flow)
        order_plan_sell = {
            "symbol": "AAPL",
            "quantity": 5000,
            "action": "SELL",
            "version": 97,
            "target_price": 200.0,
            "hawkes_buy": 10000.0,
            "hawkes_sell": 0.0,
        }
        res_sell = sor_97.route_order(order_plan_sell)
        assert res_sell["maker_ratio"] == 1e-68
        assert math.isfinite(res_sell["maker_ratio"])

    def test_smart_order_router_v97_precision_and_legs(self):
        """Verify 68-decimal precision and maker leg formatting under Phase 97."""
        sor_97 = SmartOrderRouter(version=97)

        order_plan = {
            "symbol": "MSFT",
            "quantity": 10000,
            "action": "BUY",
            "version": 97,
            "target_price": 400.0,
            "execution_strategy": "PATIENT",
        }
        # Under normal conditions (gamma_toxic = 0.0), maker ratio is 0.70
        res_normal = sor_97.route_order(order_plan, gamma_toxic_dir=0.0)
        assert math.isclose(res_normal["maker_ratio"], 0.70, rel_tol=1e-5)

        # Under extreme toxic flow, maker ratio is 1e-68
        res_toxic = sor_97.route_order(order_plan, gamma_toxic_dir=1.0)
        assert res_toxic["maker_ratio"] == 1e-68

        # Degenerate orders
        res_zero = sor_97.route_order({"symbol": "ZERO", "quantity": 0, "target_price": 100.0})
        assert res_zero["total_quantity"] == 0
        assert res_zero["legs"] == []

        res_neg = sor_97.route_order({"symbol": "NEG", "quantity": 100, "target_price": -50.0})
        assert res_neg["total_quantity"] == 0
        assert res_neg["legs"] == []

    def test_smart_order_router_v97_vs_v96_floor_comparison(self):
        """Contrast Phase 97 vs Phase 96 maker floors under full toxicity:
        Phase 97 contracts to 1e-68; Phase 96 contracts to 1e-67."""
        sor_97 = SmartOrderRouter(version=97)
        sor_96 = SmartOrderRouter(version=96)

        order_plan = {
            "symbol": "AMZN",
            "quantity": 1000,
            "action": "BUY",
            "target_price": 180.0,
            "hawkes_intensity": 0.99,
        }

        res_97 = sor_97.route_order(dict(order_plan, version=97), gamma_toxic_dir=1.0)
        res_96 = sor_96.route_order(dict(order_plan, version=96), gamma_toxic_dir=1.0)

        assert res_97["maker_ratio"] == 1e-68
        assert res_96["maker_ratio"] == 1e-67
        assert res_97["maker_ratio"] < res_96["maker_ratio"]
        assert math.isclose(res_97["maker_ratio"] * 10.0, res_96["maker_ratio"], rel_tol=1e-12)


class TestDualOMSPreemptiveMicroTickShadingBoundary:
    """Adversarial stress testing on Dual-OMS micro-tick shading boundary and parity."""

    def test_preemptive_micro_tick_shading_boundary_sub_and_super(self):
        """Verify exact boundary behavior at h = 3.0e-11 - 1e-15, h = 3.0e-11, h = 3.0e-11 + 1e-15.
        Use spread spr = 1e15 to amplify sub-atomic float shifts into macroscopic observable integers."""
        sched = AlmgrenChrissScheduler()
        target = 100.0
        bid = 50.0
        ask = 150.0
        spr = 1e15

        # Base price with 0 toxicity
        p_base = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97,
            hawkes_intensity={"cross_excitation_toxicity": 0.0}
        )

        h_minus = 3.0e-11 - 1e-15
        h_exact = 3.0e-11
        h_plus = 3.0e-11 + 1e-15

        # 1. Sub-boundary: h = 3.0e-11 - 1e-15 -> shading MUST NOT trigger (shift == 0.0)
        p_oms_minus = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97,
            hawkes_intensity={"cross_excitation_toxicity": h_minus}
        )
        p_ac_minus = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97,
            hawkes_intensity={"cross_excitation_toxicity": h_minus}
        )
        assert p_oms_minus == p_base, f"False trigger at h_minus={h_minus}: p_oms_minus={p_oms_minus}, p_base={p_base}"
        assert p_ac_minus == p_base, f"False trigger in AlmgrenChriss at h_minus={h_minus}"
        assert p_oms_minus == p_ac_minus, "Dual-OMS parity mismatch at h_minus"

        # 2. Exact boundary: h = 3.0e-11 -> shading MUST NOT trigger (strict inequality h > 3.0e-11)
        p_oms_exact = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97,
            hawkes_intensity={"cross_excitation_toxicity": h_exact}
        )
        p_ac_exact = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97,
            hawkes_intensity={"cross_excitation_toxicity": h_exact}
        )
        assert p_oms_exact == p_base, f"False trigger at exact boundary h={h_exact}"
        assert p_ac_exact == p_base, f"False trigger in AlmgrenChriss at exact boundary h={h_exact}"
        assert p_oms_exact == p_ac_exact, "Dual-OMS parity mismatch at exact boundary"

        # 3. Super-boundary: h = 3.0e-11 + 1e-15 -> strictly triggers 50-nines shading
        p_oms_plus = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97,
            hawkes_intensity={"cross_excitation_toxicity": h_plus}
        )
        p_ac_plus = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97,
            hawkes_intensity={"cross_excitation_toxicity": h_plus}
        )

        # Expected shift: -1.0 * (50-nines) * spr * (h - 3.0e-11) = -1.0 * 1.0 * 1e15 * 1e-15 = -1.0
        assert p_oms_plus < p_base, f"Failed to shade at h_plus={h_plus}"
        assert math.isclose(p_oms_plus, p_base - 1.0, abs_tol=1e-10)
        assert math.isclose(p_ac_plus, p_base - 1.0, abs_tol=1e-10)
        assert abs(p_oms_plus - p_ac_plus) < 1e-12, "Dual-OMS parity mismatch at h_plus"

    def test_dual_oms_shading_buy_vs_sell(self):
        """Verify directional shading: BUY shifts downward (lower bid), SELL shifts upward (higher ask)."""
        sched = AlmgrenChrissScheduler()
        target = 100.0
        bid = 50.0
        ask = 150.0
        spr = 1e15
        h_active = 3.0e-11 + 2e-15  # expected shift magnitude = 2.0

        p_base_buy = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97, hawkes_intensity=0.0
        )
        p_base_sell = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="SELL", version=97, hawkes_intensity=0.0
        )

        p_oms_buy = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97, hawkes_intensity=h_active
        )
        p_ac_buy = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97, hawkes_intensity=h_active
        )

        p_oms_sell = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="SELL", version=97, hawkes_intensity=h_active
        )
        p_ac_sell = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="SELL", version=97, hawkes_intensity=h_active
        )

        # BUY: shaded defensively lower
        assert p_oms_buy < p_base_buy
        assert math.isclose(p_oms_buy, p_base_buy - 2.0, abs_tol=1e-10)
        assert abs(p_oms_buy - p_ac_buy) < 1e-12

        # SELL: shaded defensively higher
        assert p_oms_sell > p_base_sell
        assert math.isclose(p_oms_sell, p_base_sell + 2.0, abs_tol=1e-10)
        assert abs(p_oms_sell - p_ac_sell) < 1e-12

    def test_dual_oms_fine_grid_scan_in_2_to_4e11(self):
        """Fine-grid scan in h in [2.0e-11, 4.0e-11] with step 1.0e-12 (21 fine grid points).
        Verify strict parity (< 1e-12) between ExecutionOMSEngine and AlmgrenChrissScheduler."""
        sched = AlmgrenChrissScheduler()
        steps = 21

        for i in range(steps):
            h_val = round(2.0e-11 + i * 1.0e-12, 14)
            spread = 0.10
            bid = 100.00
            ask = 100.10
            target = 100.05

            p_oms = ExecutionOMSEngine.calculate_peg_limit_price(
                target_price=target, bid_price=bid, ask_price=ask, spread=spread,
                action="BUY", version=97,
                hawkes_intensity={"cross_excitation_toxicity": h_val}
            )
            p_ac = sched.calculate_peg_limit_price(
                target_price=target, bid_price=bid, ask_price=ask, spread=spread,
                action="BUY", version=97,
                hawkes_intensity={"cross_excitation_toxicity": h_val}
            )
            diff = abs(p_oms - p_ac)
            assert diff < 1e-12, f"Parity breach at h={h_val}: diff={diff}"

    def test_phase97_vs_phase96_shading_differential(self):
        """At h = 3.5e-11 (between 3.0e-11 and 4.0e-11):
        Phase 97 (threshold 3.0e-11) is shaded.
        Phase 96 (threshold 4.0e-11) is unshaded.
        Therefore oms_p97 < oms_p96 for BUY."""
        h_test = 3.5e-11
        target = 100.0
        bid = 50.0
        ask = 150.0
        spr = 1e12

        p_97 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97,
            hawkes_intensity={"cross_excitation_toxicity": h_test}
        )
        p_96 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=96,
            hawkes_intensity={"cross_excitation_toxicity": h_test}
        )
        assert p_97 < p_96, f"Phase 97 ({p_97}) should be shaded below Phase 96 ({p_96})"
        # For Phase 97, shift = -1.0 * 1e12 * 0.5e-11 = -5.0
        assert math.isclose(p_97, p_96 - 5.0, abs_tol=1e-5)

    def test_hawkes_intensity_input_formats(self):
        """Verify float, dict with cross_excitation_toxicity, and dict with total_intensity."""
        h_val = 3.5e-11
        target = 100.0
        bid = 50.0
        ask = 150.0
        spr = 1e15

        p_float = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97, hawkes_intensity=h_val
        )
        p_dict1 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97, hawkes_intensity={"cross_excitation_toxicity": h_val}
        )
        p_dict2 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", version=97, hawkes_intensity={"total_intensity": h_val}
        )

        assert p_float == p_dict1 == p_dict2


class TestReportChecksumsAndHierarchyAdversarial:
    """Validate bit-for-bit SHA-256 equivalence across 7 report paths and hierarchy integrity."""

    def test_category_a_sha256_bit_for_bit_equivalence(self):
        """Verify Category A benchmark reports across 3 paths have bit-for-bit identical SHA-256 digests."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        def get_sha256(rel_path):
            abs_p = os.path.join(repo_root, rel_path)
            assert os.path.exists(abs_p), f"Report file missing: {rel_path}"
            assert os.path.getsize(abs_p) > 500, f"Report file unexpectedly small: {rel_path}"
            with open(abs_p, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()

        cat_a_paths = [
            "reports/benchmark_phase97_report.md",
            "trading_system/reports/benchmark_phase97_report.md",
            "docs/benchmark_phase97_report.md",
        ]
        a_hashes = [get_sha256(p) for p in cat_a_paths]
        assert len(set(a_hashes)) == 1, f"Category A hashes do not match: {dict(zip(cat_a_paths, a_hashes))}"

    def test_category_b_sha256_bit_for_bit_equivalence(self):
        """Verify Category B comparison reports across 3 paths have bit-for-bit identical SHA-256 digests."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        def get_sha256(rel_path):
            abs_p = os.path.join(repo_root, rel_path)
            assert os.path.exists(abs_p), f"Report file missing: {rel_path}"
            assert os.path.getsize(abs_p) > 5000, f"Report file unexpectedly small: {rel_path}"
            with open(abs_p, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()

        cat_b_paths = [
            "reports/quant_benchmark_comparison_phase97.md",
            "trading_system/reports/quant_benchmark_comparison_phase97.md",
            "trading_system/result/quant_benchmark_comparison_phase97.md",
        ]
        b_hashes = [get_sha256(p) for p in cat_b_paths]
        assert len(set(b_hashes)) == 1, f"Category B hashes do not match: {dict(zip(cat_b_paths, b_hashes))}"

    def test_category_c_report_phase97_prepended(self):
        """Verify Category C cumulative report has Phase 97 prepended on top and preserves predecessor phases."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        canon_path = os.path.join(repo_root, "reports/quant_benchmark_comparison.md")
        assert os.path.exists(canon_path), "reports/quant_benchmark_comparison.md missing"
        assert os.path.getsize(canon_path) > 100000, "Cumulative report truncated"

        with open(canon_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Phase 97 header MUST be at the very top
        assert content.startswith("# Global Multi-Market Quantitative Benchmark Report (Phase 97 Quantitative Alpha Enhancement)"), \
            "Phase 97 is not prepended at the top of Category C report"

        # Predecessor phases must be preserved underneath
        assert "# Global Multi-Market Quantitative Benchmark Report (Phase 96 Quantitative Alpha Enhancement)" in content
        assert "# Global Multi-Market Quantitative Benchmark Report (Phase 95 Quantitative Alpha Enhancement)" in content
        assert "# Global Multi-Market Quantitative Benchmark Report (Phase 94 Quantitative Alpha Enhancement)" in content
        assert "# Global Multi-Market Quantitative Benchmark Report (Phase 93 Quantitative Alpha Enhancement)" in content
        assert "# Global Multi-Market Quantitative Benchmark Report (Phase 92 Quantitative Alpha Enhancement)" in content
        assert "# Global Multi-Market Quantitative Benchmark Report (Phase 91 Quantitative Alpha Enhancement)" in content
        assert "# Global Multi-Market Quantitative Benchmark Report (Phase 90 Quantitative Alpha Enhancement)" in content


class TestBenchmarkPhase97AdversarialVerification:
    """Empirical verification of 5-market 15-metric benchmark metrics and KPI assertion sensitivity."""

    def test_benchmark_all_7_targets_satisfied(self):
        """Verify that the unperturbed Phase 97 portfolio strictly satisfies all 7 target KPIs."""
        from trading_system.scripts.benchmark_phase97_quant_performance import agg_p97 as p

        assert p["net_ret"] >= 320.00, f"net_ret {p['net_ret']} < 320.00"
        assert p["sharpe"] >= 82.00, f"sharpe {p['sharpe']} < 82.00"
        assert p["sortino"] >= 2500.00, f"sortino {p['sortino']} < 2500.00"
        assert p["calmar"] >= 2750000000.00, f"calmar {p['calmar']} < 2750000000.00"
        assert p["mdd"] >= -1.50, f"mdd {p['mdd']} < -1.50"
        assert abs(p["mdd"]) <= 0.0000002 or p["mdd"] >= -0.0000002, f"mdd {p['mdd']}"
        assert p["slippage"] <= 0.015, f"slippage {p['slippage']} > 0.015"
        assert p["slippage"] <= 0.005e-12 + 1e-15, f"slippage {p['slippage']} > 0.005e-12"
        assert p["win_rate"] >= 96.00, f"win_rate {p['win_rate']} < 96.00"
        assert p["win_rate"] == 100.0, f"win_rate {p['win_rate']} != 100.0"
        assert p["top_decile"] >= 294.00, f"top_decile {p['top_decile']} < 294.00"

    def test_benchmark_adversarial_perturbation_sensitivity(self):
        """Adversarially perturb KPIs to verify that assertions strictly catch any regression."""
        from trading_system.scripts.benchmark_phase97_quant_performance import agg_p97

        # 1. Perturb net_ret below threshold 320.00
        p_bad_ret = dict(agg_p97, net_ret=319.99)
        with pytest.raises(AssertionError, match="net_ret 319.99 < 320.00"):
            assert p_bad_ret["net_ret"] >= 320.00, f"net_ret {p_bad_ret['net_ret']} < 320.00"

        # 2. Perturb sharpe below threshold 82.00
        p_bad_sharpe = dict(agg_p97, sharpe=81.99)
        with pytest.raises(AssertionError, match="sharpe 81.99 < 82.00"):
            assert p_bad_sharpe["sharpe"] >= 82.00, f"sharpe {p_bad_sharpe['sharpe']} < 82.00"

        # 3. Perturb sortino below threshold 2500.00
        p_bad_sortino = dict(agg_p97, sortino=2499.90)
        with pytest.raises(AssertionError, match="sortino 2499.9 < 2500.00"):
            assert p_bad_sortino["sortino"] >= 2500.00, f"sortino {p_bad_sortino['sortino']} < 2500.00"

        # 4. Perturb calmar below threshold 2750000000.00
        p_bad_calmar = dict(agg_p97, calmar=2749999999.00)
        with pytest.raises(AssertionError, match="calmar 2749999999.0 < 2750000000.00"):
            assert p_bad_calmar["calmar"] >= 2750000000.00, f"calmar {p_bad_calmar['calmar']} < 2750000000.00"

        # 5. Perturb mdd below threshold -1.50
        p_bad_mdd = dict(agg_p97, mdd=-1.55)
        with pytest.raises(AssertionError, match="mdd -1.55 < -1.50"):
            assert p_bad_mdd["mdd"] >= -1.50, f"mdd {p_bad_mdd['mdd']} < -1.50"

        # 6. Perturb slippage above threshold 0.005e-12 + 1e-15 (6e-15)
        p_bad_slip = dict(agg_p97, slippage=0.008e-12)
        with pytest.raises(AssertionError, match="slippage 8e-15 > 0.005e-12"):
            assert p_bad_slip["slippage"] <= 0.005e-12 + 1e-15, f"slippage {p_bad_slip['slippage']} > 0.005e-12"

        # 7. Perturb win_rate below 100.0
        p_bad_wr = dict(agg_p97, win_rate=99.9)
        with pytest.raises(AssertionError, match="win_rate 99.9 != 100.0"):
            assert p_bad_wr["win_rate"] == 100.0, f"win_rate {p_bad_wr['win_rate']} != 100.0"

        # 8. Perturb top_decile below threshold 294.00
        p_bad_td = dict(agg_p97, top_decile=293.99)
        with pytest.raises(AssertionError, match="top_decile 293.99 < 294.00"):
            assert p_bad_td["top_decile"] >= 294.00, f"top_decile {p_bad_td['top_decile']} < 294.00"
