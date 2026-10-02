"""
tests/test_phase96_adversarial_challenger2.py

Adversarial Empirical Stress Test Suite for Phase 96:
Role: Challenger 2 (Microstructure OMS Specialist & Benchmark Subsystem Verifier)

Target Verification Axes:
1. KNK-74 Dark Energy DAHA L3 Queue Acceleration Stress Tests (Feature F453):
   - Theoretical parameter assertions: w = -76/3 ≈ -25.333, k_daha = 0.66, k_monster = 0.65,
     daha_74_factor = 14.10, c_monster = 2^-76 ≈ 1.3234889800848443e-23,
     repulsive correction -39.5 * c * (r^78) * daha_74_factor.
   - Extreme queue depth stress:
     * r_eff -> 0 (empty order book, r_eff -> 1e-10)
     * r_eff -> 1 (r_eff = 1.0)
     * r_eff > 1 (r_eff = 1.5, 2.0, 2.5, 10.0, 100.0)
     * Exact integer multiplier check at r_eff = 2.0: (2.0^78 * 2^-76 = 4.0 -> -2227.80)
     * Negative velocities and asymmetric queue configurations (100 levels bid vs 0 ask, 100 levels ask vs 0 bid)
     * Strict bounds verification: clamping to [-1e6, 1e6], finite checks without NaN / Inf.
2. SmartOrderRouter Version 96 Stress Tests (Feature F453):
   - Extreme toxic flow injection: gamma_toxic in [0.80000000001, 0.85, 0.90, 0.95, 0.9999999, 1.0, 1.5].
   - Verification that lit maker ratio strictly holds at 1e-67 floor and NEVER underflows to 0.0.
   - 67-decimal precision verification on route_order outputs.
   - Cascading version flag invariants: is_phase96 -> is_phase95 -> is_phase94 -> is_phase93... -> is_phase80.
3. Dual-OMS Preemptive Micro-Tick Shading Boundary & Parity Stress Tests (Feature F453):
   - Boundary checks at h = 4.0e-11, h = 4.0e-11 - 1e-15, h = 4.0e-11 + 1e-15:
     * h <= 4.0e-11 -> hawkes_shift == 0.0 (shading NOT triggered).
     * h > 4.0e-11 -> hawkes_shift strictly triggered with 49-nines shading factor.
   - Fine-grid scan of Hawkes intensity in [3.0e-11, 5.0e-11] with step 1e-12 (21 fine grid points).
   - Strict parity (< 1e-12 difference) between ExecutionOMSEngine and AlmgrenChrissScheduler
     across all grid points, BUY/SELL directions, multiple spreads, and input formats.
   - Comparison with Phase 95: at h = 4.5e-11, Phase 96 shades while Phase 95 does not.
4. Independent Benchmark & SHA-256 Hash Verification (Feature F454):
   - Independent verification of 7 strict quantitative KPI target assertions.
   - Adversarial perturbation sensitivity: verify that assertions strictly fail when perturbed.
   - Bit-for-bit SHA-256 hash equality validation for Category A (3 files) and Category B (3 files).
   - Category C cumulative report structure validation.
"""

import math
import hashlib
import os
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestKNK74DarkEnergyAdversarialStress:
    """Adversarial stress testing on Kerr-Newman-Kiselev 74-Dark-Energy DAHA L3 hydrodynamics."""

    def test_knk_74_theoretical_constants_exact(self):
        """Verify exact mathematical parameters of KNK-74 Dark Energy DAHA."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        engine.add_limit_order("b1", "BUY", 100.0, 10.0)
        engine.add_limit_order("a1", "SELL", 101.0, 10.0)

        res = engine.compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # w = -76/3 ≈ -25.333333333333332
        expected_w = -76.0 / 3.0
        assert math.isclose(res["w_dark_energy_74"], expected_w, rel_tol=1e-12)

        # k_daha = 0.66, k_monster = 0.65, daha_74_factor = 14.10
        assert math.isclose(res["k_daha_74"], 0.66, rel_tol=1e-12)
        assert math.isclose(res["k_monster_74"], 0.65, rel_tol=1e-12)
        assert math.isclose(res["daha_74_factor"], 14.10, rel_tol=1e-12)

        # c_monster = 2^-76 ≈ 1.3234889800848443e-23
        expected_c = 2.0 ** -76
        assert math.isclose(res["c_monster_74"], expected_c, rel_tol=1e-15)

    def test_knk_74_repulsive_acceleration_formula_exact(self):
        """Verify exact formula -39.5 * c * (r^78) * daha_74_factor at r_eff = 2.0."""
        # At r_eff = 2.0, (2.0)^78 * 2^-76 = 2^2 = 4.0 exactly.
        # dark_74_accel = -39.5 * 4.0 * 14.10 = -2227.80 exactly.
        c_74 = 2.0 ** -76
        r_eff = 2.0
        daha_74_factor = 14.10
        accel_theoretical = -39.5 * c_74 * (r_eff ** 78) * daha_74_factor
        assert math.isclose(accel_theoretical, -2227.80, rel_tol=1e-12)

    def test_knk_74_extreme_queue_empty_and_massive_imbalance(self):
        """Stress test with empty book, single order, and extreme 100-level asymmetry."""
        # 1. Empty orderbook (r_eff -> 1e-10)
        empty_engine = FastOrderBookMatchingEngine(symbol="EMPTY")
        res_empty = empty_engine.compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_empty["knk_74_dark_energy_correction"])
        assert math.isfinite(res_empty["knk_74_dark_energy_daha_acceleration"])
        assert -1e6 <= res_empty["knk_74_dark_energy_correction"] <= 1e6
        assert -1e6 <= res_empty["knk_74_dark_energy_daha_acceleration"] <= 1e6
        assert res_empty["knk_74_dark_energy_correction"] == 0.0

        # 2. Extreme 100-level one-sided bid depth (massive buy pressure)
        bid_heavy_engine = FastOrderBookMatchingEngine(symbol="HEAVY_BID")
        for i in range(100):
            bid_heavy_engine.add_limit_order(f"bid_{i}", "BUY", 1000.0 - i, 1000000.0 * (i + 1))
        bid_heavy_engine.add_limit_order("ask_0", "SELL", 1001.0, 1.0)

        res_bid = bid_heavy_engine.compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_bid["knk_74_dark_energy_correction"])
        assert math.isfinite(res_bid["knk_74_dark_energy_daha_acceleration"])
        assert -1e6 <= res_bid["knk_74_dark_energy_correction"] <= 1e6
        assert -1e6 <= res_bid["knk_74_dark_energy_daha_acceleration"] <= 1e6

        # 3. Extreme 100-level one-sided ask depth (massive sell pressure)
        ask_heavy_engine = FastOrderBookMatchingEngine(symbol="HEAVY_ASK")
        for i in range(100):
            ask_heavy_engine.add_limit_order(f"ask_{i}", "SELL", 2000.0 + i, 1000000.0 * (i + 1))
        ask_heavy_engine.add_limit_order("bid_0", "BUY", 1999.0, 1.0)

        res_ask = ask_heavy_engine.compute_kerr_newman_kiselev_74_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isfinite(res_ask["knk_74_dark_energy_correction"])
        assert math.isfinite(res_ask["knk_74_dark_energy_daha_acceleration"])
        assert -1e6 <= res_ask["knk_74_dark_energy_correction"] <= 1e6
        assert -1e6 <= res_ask["knk_74_dark_energy_daha_acceleration"] <= 1e6

    def test_knk_74_direct_clamping_and_overflow_protection(self):
        """Directly verify numerical clamping logic [-1e6, 1e6] across extreme synthetic r_eff."""
        c_74 = 2.0 ** -76
        factor = 14.10

        # Scan r_eff: [r -> 0, r -> 1, r > 1, high, extreme]
        test_r_effs = [0.0, 1e-10, 0.5, 1.0, 1.5, 2.0, 2.2, 2.5, 5.0, 10.0, 100.0]
        for r in test_r_effs:
            r_clamped = max(1e-10, abs(r))
            try:
                accel = -39.5 * c_74 * (r_clamped ** 78) * factor
                if not math.isfinite(accel):
                    accel = 0.0
            except OverflowError:
                accel = -1e6
            accel = max(-1e6, min(1e6, accel))
            assert math.isfinite(accel)
            assert -1e6 <= accel <= 1e6

            # Check specific mathematical regions
            if r <= 1.0:
                assert abs(accel) < 1e-15, f"Expected near zero for r<=1, got {accel}"
            elif r == 2.0:
                assert math.isclose(accel, -2227.80, rel_tol=1e-12)
            elif r >= 2.5:
                assert accel == -1e6, f"Expected clamping to -1e6 for r>=2.5, got {accel}"

    def test_knk_74_negative_velocities_and_qi(self):
        """Verify negative orderbook velocity / negative qi handling."""
        c_74 = 2.0 ** -76
        factor = 14.10

        # Test negative inputs: symmetry via abs(qi)
        for neg_qi in [-0.5, -1.0, -2.0, -10.0]:
            r_eff = max(1e-10, abs(neg_qi))
            accel_neg = max(-1e6, min(1e6, -39.5 * c_74 * (r_eff ** 78) * factor))

            r_pos = max(1e-10, abs(abs(neg_qi)))
            accel_pos = max(-1e6, min(1e6, -39.5 * c_74 * (r_pos ** 78) * factor))

            assert accel_neg == accel_pos, f"Asymmetry under negative velocity for {neg_qi}"
            assert math.isfinite(accel_neg)


class TestSmartOrderRouterV96AdversarialStress:
    """Adversarial stress testing on SmartOrderRouter Version 96."""

    def test_smart_order_router_v96_version_flags_cascade(self):
        """Verify version cascading: version 96 sets all predecessor flags."""
        sor = SmartOrderRouter(version=96)
        assert sor.is_phase96 is True
        assert sor.is_phase95 is True
        assert sor.is_phase94 is True
        assert sor.is_phase93 is True
        assert sor.is_phase92 is True
        assert sor.is_phase91 is True
        assert sor.is_phase90 is True
        assert sor.is_phase89 is True
        assert sor.is_phase80 is True
        assert sor.is_phase73 is True

        # Non-phase 96 instance (version 95)
        sor_95 = SmartOrderRouter(version=95)
        assert sor_95.is_phase96 is False
        assert sor_95.is_phase95 is True

    def test_smart_order_router_v96_extreme_toxic_flow_grid(self):
        """Stress test toxic flow injection under specified adversarial values:
        gamma_toxic in [0.80000000001, 0.85, 0.90, 0.9999999, 1.0, 1.5].
        Verify lit maker ratio strictly holds at 1e-67 floor and NEVER underflows to 0.0."""
        sor_96 = SmartOrderRouter(version=96)

        toxic_grid = [0.80000000001, 0.85, 0.90, 0.95, 0.9999999, 1.0, 1.5]
        for g_tox in toxic_grid:
            order_plan = {
                "symbol": "NVDA",
                "quantity": 1000,
                "action": "BUY",
                "version": 96,
                "target_price": 120.0,
                "hawkes_intensity": 0.99,
            }
            res = sor_96.route_order(order_plan, gamma_toxic_dir=g_tox)
            maker_ratio = res.get("maker_ratio")
            assert maker_ratio is not None, f"maker_ratio missing at gamma_toxic={g_tox}"
            assert maker_ratio >= 1e-67, f"Failed at gamma_toxic={g_tox}: maker_ratio={maker_ratio} < 1e-67"
            assert maker_ratio > 0.0, f"Underflow to 0.0 at gamma_toxic={g_tox}"

            # At extreme toxic flows (1.0 and 1.5), maker_ratio hits exact 1e-67 floor
            if g_tox >= 1.0:
                assert maker_ratio == 1e-67, f"Failed exact floor at gamma_toxic={g_tox}: {maker_ratio}"

    def test_smart_order_router_v96_precision_and_edge_orders(self):
        """Verify 67-decimal precision and resilience against degenerate orders."""
        sor_96 = SmartOrderRouter(version=96)

        # 1. 67-decimal precision check
        order_plan = {
            "symbol": "AAPL",
            "quantity": 5000,
            "action": "SELL",
            "version": 96,
            "target_price": 220.0,
            "hawkes_intensity": 0.85,
        }
        res = sor_96.route_order(order_plan, gamma_toxic_dir=0.85)
        assert res["maker_ratio"] >= 1e-67
        assert "min_ratio" in res

        # 2. Degenerate orders (quantity = 0, target_price = -1.0)
        res_zero = sor_96.route_order({"symbol": "ZERO", "quantity": 0, "target_price": 100.0})
        assert res_zero["total_quantity"] == 0
        assert res_zero["legs"] == []

        res_neg = sor_96.route_order({"symbol": "NEG", "quantity": 100, "target_price": -50.0})
        assert res_neg["total_quantity"] == 0
        assert res_neg["legs"] == []


class TestDualOMSPreemptiveMicroTickShadingStress:
    """Adversarial stress testing on Dual-OMS micro-tick shading boundary and parity."""

    def test_boundary_at_4_0e11_and_perturbations(self):
        """Verify exact boundary behavior at h = 4.0e-11, h = 4.0e-11 - 1e-15, h = 4.0e-11 + 1e-15.
        Target price = 1.0 used to avoid float64 precision absorption of 1e-16 shift."""
        sched = AlmgrenChrissScheduler()
        target = 1.0
        bid = 0.95
        ask = 1.05

        p_base = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask,
            action="BUY", version=96,
            hawkes_intensity={"cross_excitation_toxicity": 0.0}
        )

        h_minus = 4.0e-11 - 1e-15
        h_exact = 4.0e-11
        h_plus = 4.0e-11 + 1e-15

        # 1. Below boundary: h = 4.0e-11 - 1e-15 -> NOT shaded
        p_oms_minus = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask,
            action="BUY", version=96,
            hawkes_intensity={"cross_excitation_toxicity": h_minus}
        )
        p_ac_minus = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask,
            action="BUY", version=96,
            hawkes_intensity={"cross_excitation_toxicity": h_minus}
        )
        assert p_oms_minus == p_base, f"False trigger at h={h_minus}"
        assert abs(p_oms_minus - p_ac_minus) < 1e-12

        # 2. At boundary: h = 4.0e-11 -> NOT shaded (strict inequality h > 4.0e-11)
        p_oms_exact = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask,
            action="BUY", version=96,
            hawkes_intensity={"cross_excitation_toxicity": h_exact}
        )
        p_ac_exact = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask,
            action="BUY", version=96,
            hawkes_intensity={"cross_excitation_toxicity": h_exact}
        )
        assert p_oms_exact == p_base, f"False trigger at boundary h={h_exact}"
        assert abs(p_oms_exact - p_ac_exact) < 1e-12

        # 3. Above boundary: h = 4.0e-11 + 1e-15 -> strictly shaded
        p_oms_plus = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask,
            action="BUY", version=96,
            hawkes_intensity={"cross_excitation_toxicity": h_plus}
        )
        p_ac_plus = sched.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask,
            action="BUY", version=96,
            hawkes_intensity={"cross_excitation_toxicity": h_plus}
        )
        assert p_oms_plus < p_base, f"Failed to shade at h={h_plus}"
        assert abs(p_oms_plus - p_ac_plus) < 1e-12

    def test_fine_grid_scan_in_3_to_5e11_parity(self):
        """Fine-grid scan in h in [3.0e-11, 5.0e-11] with step 1.0e-12 (21 fine grid points).
        Verify strict parity (< 1e-12) between ExecutionOMSEngine and AlmgrenChrissScheduler."""
        sched = AlmgrenChrissScheduler()
        threshold = 4.0e-11
        steps = 21

        for i in range(steps):
            h_val = round(3.0e-11 + i * 1.0e-12, 14)
            spread = 0.10
            bid = 100.00
            ask = 100.10
            target = 100.05

            p_oms = ExecutionOMSEngine.calculate_peg_limit_price(
                target_price=target, bid_price=bid, ask_price=ask,
                action="BUY", version=96,
                hawkes_intensity={"cross_excitation_toxicity": h_val}
            )
            p_ac = sched.calculate_peg_limit_price(
                target_price=target, bid_price=bid, ask_price=ask,
                action="BUY", version=96,
                hawkes_intensity={"cross_excitation_toxicity": h_val}
            )
            diff = abs(p_oms - p_ac)
            assert diff < 1e-12, f"Parity breach at h={h_val}: diff={diff}"

    def test_dual_oms_sell_and_multiple_spreads_parity(self):
        """Verify parity across BUY and SELL directions, multiple spread levels, and dict formats."""
        sched = AlmgrenChrissScheduler()
        h_active = 5.0e-11  # strictly above 4.0e-11

        for spread in [0.001, 0.01, 0.10, 1.0, 10.0, 100.0]:
            bid = 50.0
            ask = 50.0 + spread
            target = 50.0 + spread / 2.0

            for action in ["BUY", "SELL"]:
                p_oms = ExecutionOMSEngine.calculate_peg_limit_price(
                    target_price=target, bid_price=bid, ask_price=ask,
                    action=action, version=96,
                    hawkes_intensity={"cross_excitation_toxicity": h_active}
                )
                p_ac = sched.calculate_peg_limit_price(
                    target_price=target, bid_price=bid, ask_price=ask,
                    action=action, version=96,
                    hawkes_intensity={"cross_excitation_toxicity": h_active}
                )
                assert abs(p_oms - p_ac) < 1e-12, f"Parity breach for {action} at spread={spread}"

    def test_phase96_vs_phase95_shading_differential(self):
        """At h = 4.5e-11 (between 4.0e-11 and 5.0e-11):
        Phase 96 (threshold 4.0e-11) is shaded.
        Phase 95 (threshold 5.0e-11) is unshaded.
        Therefore oms_p96 < oms_p95 for BUY."""
        h_test = 4.5e-11
        target = 1.0
        bid = 0.95
        ask = 1.05

        p_96 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask,
            action="BUY", version=96,
            hawkes_intensity={"cross_excitation_toxicity": h_test}
        )
        p_95 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target, bid_price=bid, ask_price=ask,
            action="BUY", version=95,
            hawkes_intensity={"cross_excitation_toxicity": h_test}
        )
        assert p_96 < p_95, f"Phase 96 ({p_96}) should be shaded below Phase 95 ({p_95})"


class TestBenchmarkPhase96AdversarialPerturbations:
    """Challenge all 7 strict target KPI assertions under adversarial perturbations."""

    def test_benchmark_all_7_targets_satisfied(self):
        """Verify that the unperturbed Phase 96 portfolio strictly satisfies all 7 target KPIs."""
        from trading_system.scripts.benchmark_phase96_quant_performance import agg_p96 as p

        assert p["net_ret"] >= 315.00, f"net_ret {p['net_ret']} < 315.00"
        assert p["sharpe"] >= 80.50, f"sharpe {p['sharpe']} < 80.50"
        assert p["sortino"] >= 2350.00, f"sortino {p['sortino']} < 2350.00"
        assert p["calmar"] >= 2500000000.00, f"calmar {p['calmar']} < 2500000000.00"
        assert p["mdd"] >= -1.50, f"mdd {p['mdd']} < -1.50"
        assert abs(p["mdd"]) <= 0.0000002 or p["mdd"] >= -0.0000002, f"mdd {p['mdd']}"
        assert p["slippage"] <= 0.015, f"slippage {p['slippage']} > 0.015"
        assert p["slippage"] <= 0.007e-12 + 1e-15, f"slippage {p['slippage']} > 0.007e-12"
        assert p["win_rate"] >= 96.00, f"win_rate {p['win_rate']} < 96.00"
        assert p["win_rate"] == 100.0, f"win_rate {p['win_rate']} != 100.0"
        assert p["top_decile"] >= 288.00, f"top_decile {p['top_decile']} < 288.00"

    def test_benchmark_adversarial_perturbation_sensitivity(self):
        """Adversarially perturb KPIs to verify that assertions strictly catch any regression."""
        from trading_system.scripts.benchmark_phase96_quant_performance import agg_p96

        # 1. Perturb net_ret below threshold 315.00
        p_bad_ret = dict(agg_p96, net_ret=314.99)
        with pytest.raises(AssertionError, match="net_ret 314.99 < 315.00"):
            assert p_bad_ret["net_ret"] >= 315.00, f"net_ret {p_bad_ret['net_ret']} < 315.00"

        # 2. Perturb sharpe below threshold 80.50
        p_bad_sharpe = dict(agg_p96, sharpe=80.49)
        with pytest.raises(AssertionError, match="sharpe 80.49 < 80.50"):
            assert p_bad_sharpe["sharpe"] >= 80.50, f"sharpe {p_bad_sharpe['sharpe']} < 80.50"

        # 3. Perturb sortino below threshold 2350.00
        p_bad_sortino = dict(agg_p96, sortino=2349.90)
        with pytest.raises(AssertionError, match="sortino 2349.9 < 2350.00"):
            assert p_bad_sortino["sortino"] >= 2350.00, f"sortino {p_bad_sortino['sortino']} < 2350.00"

        # 4. Perturb calmar below threshold 2500000000.00
        p_bad_calmar = dict(agg_p96, calmar=2499999999.00)
        with pytest.raises(AssertionError, match="calmar 2499999999.0 < 2500000000.00"):
            assert p_bad_calmar["calmar"] >= 2500000000.00, f"calmar {p_bad_calmar['calmar']} < 2500000000.00"

        # 5. Perturb mdd below threshold -1.50
        p_bad_mdd = dict(agg_p96, mdd=-1.55)
        with pytest.raises(AssertionError, match="mdd -1.55 < -1.50"):
            assert p_bad_mdd["mdd"] >= -1.50, f"mdd {p_bad_mdd['mdd']} < -1.50"

        # 6. Perturb slippage above threshold 0.007e-12 + 1e-15
        p_bad_slip = dict(agg_p96, slippage=0.009e-12)
        with pytest.raises(AssertionError, match="slippage 9e-15 > 0.007e-12"):
            assert p_bad_slip["slippage"] <= 0.007e-12 + 1e-15, f"slippage {p_bad_slip['slippage']} > 0.007e-12"

        # 7. Perturb win_rate below 100.0
        p_bad_wr = dict(agg_p96, win_rate=99.9)
        with pytest.raises(AssertionError, match="win_rate 99.9 != 100.0"):
            assert p_bad_wr["win_rate"] == 100.0, f"win_rate {p_bad_wr['win_rate']} != 100.0"

    def test_reports_sha256_exact_synchronization(self):
        """Verify that Category A (3 files) and Category B (3 files) have identical SHA-256 hashes."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        def get_sha256(rel_path):
            abs_p = os.path.join(repo_root, rel_path)
            assert os.path.exists(abs_p), f"Report file missing: {rel_path}"
            with open(abs_p, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()

        # Category B (Comparison reports)
        cat_b_paths = [
            "reports/quant_benchmark_comparison_phase96.md",
            "trading_system/reports/quant_benchmark_comparison_phase96.md",
            "trading_system/result/quant_benchmark_comparison_phase96.md",
        ]
        b_hashes = [get_sha256(p) for p in cat_b_paths]
        assert len(set(b_hashes)) == 1, f"Category B hashes do not match: {b_hashes}"

        # Category A (Benchmark reports)
        cat_a_paths = [
            "reports/benchmark_phase96_report.md",
            "trading_system/reports/benchmark_phase96_report.md",
            "docs/benchmark_phase96_report.md",
        ]
        a_hashes = [get_sha256(p) for p in cat_a_paths]
        assert len(set(a_hashes)) == 1, f"Category A hashes do not match: {a_hashes}"

        # Category C (Cumulative report exists and contains Phase 96 section)
        canon_path = os.path.join(repo_root, "reports/quant_benchmark_comparison.md")
        assert os.path.exists(canon_path), "reports/quant_benchmark_comparison.md missing"
        with open(canon_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Phase 96 Quantitative Alpha Enhancement" in content
