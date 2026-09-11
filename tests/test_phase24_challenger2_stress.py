"""
tests/test_phase24_challenger2_stress.py

Adversarial Empirical Stress Test Suite for Phase 24 Microstructure OMS & Benchmark:
Challenger 2 (Microstructure OMS & Benchmark)

Adversarial Stress Dimensions:
1. Microstructure OMS Stress:
   - Extreme Hawkes arrival intensity spikes (h >> 0.030, h = 100.0, h = 10^6, h = 0.0, negative h, NaN/Inf).
   - Extreme toxicity (gamma_toxic = 1.0, 0.9999999, 0.0) verifying lit maker floor never drops below 0.0000005.
   - Dark pool ATS routing 99.998% under order size fragmentation, small orders, odd lots, and share conservation.
   - Dynamic anti-gaming MinQty 99.9995% under order size fragmentation and adverse selection.
   - KNK Quintessence-Phantom-Tachyon L3 orderbook hydrodynamics with extreme radial distances (r -> 0, r -> inf),
     singularity prevention, frame dragging, and triple dark energy repulsive tidal forces.
2. Benchmark Engine Stress:
   - Audit continuous baseline values vs Phase 23 actual results verbatim.
   - Verify all 6 quantitative thresholds pass mathematically with positive safety margins.
   - Verify tri-path markdown synchronization across:
     * reports/quant_benchmark_comparison_phase24.md
     * trading_system/result/quant_benchmark_comparison_phase24.md
     * reports/quant_benchmark_comparison.md
"""

import math
import subprocess
import sys
from pathlib import Path
import numpy as np
import pytest

from src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    DeepHawkesArrivalProcess,
)
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from trading_system.scripts.benchmark_phase24_quant_performance import (
    MARKET_DATA,
    agg_bl,
    agg_p24,
)


class TestHawkesArrivalIntensitySpikesAndClampingAdversarial:
    """Adversarial stress testing of Hawkes arrival intensity spikes and preemptive tick shading."""

    def test_hawkes_extreme_spikes_clamping_buy_direction(self):
        """
        Under extreme Hawkes arrival intensity (h >> 0.030 up to 10^6),
        preemptive tick shading for BUY must drive peg price down towards bid floor,
        but must strictly NEVER breach below bid floor min(p_bid, p_ask).
        """
        oms = ExecutionOMSEngine()
        sched = AlmgrenChrissScheduler()

        p_bid = 95.0
        p_ask = 105.0
        p_target = 100.0
        spr = p_ask - p_bid  # 10.0

        extreme_h_values = [0.03000001, 0.035, 0.10, 1.0, 10.0, 50.0, 100.0, 1000.0, 1e6]
        prev_peg_oms = 100.0

        for h in extreme_h_values:
            peg_oms = oms.calculate_peg_limit_price(
                target_price=p_target,
                bid_price=p_bid,
                ask_price=p_ask,
                spread=spr,
                action="BUY",
                hawkes_intensity=h,
                version=24,
            )
            peg_sched = sched.calculate_peg_limit_price(
                target_price=p_target,
                bid_price=p_bid,
                ask_price=p_ask,
                spread=spr,
                action="BUY",
                hawkes_intensity=h,
                version=24,
            )

            # Strict bounds enforcement
            assert p_bid <= peg_oms <= p_ask, f"Peg OMS {peg_oms} breached bounds [{p_bid}, {p_ask}] at h={h}"
            assert p_bid <= peg_sched <= p_ask, f"Peg Sched {peg_sched} breached bounds [{p_bid}, {p_ask}] at h={h}"
            assert math.isclose(peg_oms, peg_sched, abs_tol=1e-6), f"Mismatch between OMS and Scheduler at h={h}"

            # Monotonic downward shading for BUY
            assert peg_oms <= prev_peg_oms + 1e-9, f"Non-monotonic peg price: {peg_oms} > {prev_peg_oms} at h={h}"
            prev_peg_oms = peg_oms

            # When unclipped, check exact formula
            raw_peg = p_target - 0.9998 * spr * (h - 0.030)
            if raw_peg >= p_bid:
                assert math.isclose(peg_oms, raw_peg, abs_tol=1e-6)
            else:
                assert math.isclose(peg_oms, p_bid, abs_tol=1e-6), "Peg price must be clamped exactly to bid price"

        # At h = 10^6, peg price must be pinned precisely to p_bid
        assert math.isclose(prev_peg_oms, p_bid, abs_tol=1e-6)

    def test_hawkes_extreme_spikes_clamping_sell_direction(self):
        """
        Under extreme Hawkes arrival intensity (h >> 0.030 up to 10^6),
        preemptive tick shading for SELL must drive peg price up towards ask ceiling,
        but must strictly NEVER breach above ask ceiling max(p_bid, p_ask).
        """
        oms = ExecutionOMSEngine()
        sched = AlmgrenChrissScheduler()

        p_bid = 95.0
        p_ask = 105.0
        p_target = 100.0
        spr = p_ask - p_bid  # 10.0

        extreme_h_values = [0.03000001, 0.035, 0.10, 1.0, 10.0, 50.0, 100.0, 1000.0, 1e6]
        prev_peg_oms = 100.0

        for h in extreme_h_values:
            peg_oms = oms.calculate_peg_limit_price(
                target_price=p_target,
                bid_price=p_bid,
                ask_price=p_ask,
                spread=spr,
                action="SELL",
                hawkes_intensity=h,
                version=24,
            )
            peg_sched = sched.calculate_peg_limit_price(
                target_price=p_target,
                bid_price=p_bid,
                ask_price=p_ask,
                spread=spr,
                action="SELL",
                hawkes_intensity=h,
                version=24,
            )

            # Strict bounds enforcement
            assert p_bid <= peg_oms <= p_ask, f"Peg OMS {peg_oms} breached bounds [{p_bid}, {p_ask}] at h={h}"
            assert p_bid <= peg_sched <= p_ask, f"Peg Sched {peg_sched} breached bounds [{p_bid}, {p_ask}] at h={h}"
            assert math.isclose(peg_oms, peg_sched, abs_tol=1e-6), f"Mismatch between OMS and Scheduler at h={h}"

            # Monotonic upward shading for SELL
            assert peg_oms >= prev_peg_oms - 1e-9, f"Non-monotonic peg price: {peg_oms} < {prev_peg_oms} at h={h}"
            prev_peg_oms = peg_oms

            # When unclipped, check exact formula
            raw_peg = p_target + 0.9998 * spr * (h - 0.030)
            if raw_peg <= p_ask:
                assert math.isclose(peg_oms, raw_peg, abs_tol=1e-6)
            else:
                assert math.isclose(peg_oms, p_ask, abs_tol=1e-6), "Peg price must be clamped exactly to ask price"

        # At h = 10^6, peg price must be pinned precisely to p_ask
        assert math.isclose(prev_peg_oms, p_ask, abs_tol=1e-6)

    def test_hawkes_boundary_and_sub_threshold_invariance(self):
        """At h <= 0.030 or non-finite inputs, hawkes_shift must be exactly zero."""
        oms = ExecutionOMSEngine()
        p_target = 100.0

        sub_threshold_values = [0.030, 0.0299999, 0.025, 0.01, 0.0, -0.05, -100.0]
        for h in sub_threshold_values:
            peg_buy = oms.calculate_peg_limit_price(
                target_price=p_target,
                bid_price=99.0,
                ask_price=101.0,
                action="BUY",
                hawkes_intensity=h,
                version=24,
            )
            peg_sell = oms.calculate_peg_limit_price(
                target_price=p_target,
                bid_price=99.0,
                ask_price=101.0,
                action="SELL",
                hawkes_intensity=h,
                version=24,
            )
            assert math.isclose(peg_buy, p_target, abs_tol=1e-6), f"Sub-threshold h={h} altered BUY peg price"
            assert math.isclose(peg_sell, p_target, abs_tol=1e-6), f"Sub-threshold h={h} altered SELL peg price"

        # Non-finite and malformed inputs
        malformed_inputs = [float("nan"), None, {}, {"invalid_key": 10.0}]
        for mf in malformed_inputs:
            peg = oms.calculate_peg_limit_price(
                target_price=p_target,
                bid_price=99.0,
                ask_price=101.0,
                action="BUY",
                hawkes_intensity=mf,
                version=24,
            )
            assert math.isclose(peg, p_target, abs_tol=1e-6), f"Malformed input {mf} caused unexpected price shift"


class TestLitMakerFloorExtremeToxicityAdversarial:
    """Adversarial stress testing of lit maker floor and dynamic toxicity contraction."""

    def test_maker_floor_never_drops_below_0_0000005_under_extreme_toxicity(self):
        """
        Under extreme toxicity gamma_toxic = 1.0, 0.9999999, 1.5, 10.0,
        the lit maker floor must NEVER drop below 0.0000005 (0.00005%, 5e-7).
        """
        sor = SmartOrderRouter()

        extreme_toxicities = [0.800001, 0.85, 0.90, 0.95, 0.99, 0.999999, 1.0, 1.5, 10.0]
        qty = 20_000_000  # 20M shares: 20M * 5e-7 = 10 shares

        for tox in extreme_toxicities:
            plan = {
                "symbol": "AAPL",
                "action": "BUY",
                "quantity": qty,
                "target_price": 150.0,
                "gamma_toxic_dir": tox,
                "version": 24,
            }
            res = sor.route_order(plan, ats_available=False)
            maker_ratio = res.get("maker_ratio", 0.0)

            # Strict lower bound verification
            assert maker_ratio >= 0.0000005, f"Maker ratio {maker_ratio} dropped below floor 0.0000005 at tox={tox}"
            assert maker_ratio <= 0.70, f"Maker ratio {maker_ratio} exceeded upper bound 0.70 at tox={tox}"

            # At tox >= 1.0, it must equal exactly 0.0000005
            if tox >= 1.0:
                assert math.isclose(maker_ratio, 0.0000005, abs_tol=1e-10), f"Maker ratio at tox={tox} was {maker_ratio}"

            # Check allocated maker leg quantity
            maker_legs = [l for l in res.get("legs", []) if "MAKER" in l.get("venue_type", "") or "PEG" in l.get("order_type", "")]
            assert len(maker_legs) >= 1
            assert maker_legs[0]["quantity"] >= 1, "Maker quantity must be at least 1 share for large order"

    def test_maker_floor_monotonic_contraction_hierarchy_across_versions(self):
        """
        Verify strict monotonic floor contraction hierarchy across system versions under gamma_toxic = 1.0:
        v24 (5e-7) < v23 (1e-6) < v22 (2e-6) < v21 (5e-6) < v20 (1e-5) < v19 (2e-5) < v18 (5e-5) < v17 (1e-4).
        """
        sor = SmartOrderRouter()
        qty = 100_000_000  # 100M shares

        versions = [24, 23, 22, 21, 20, 19, 18, 17]
        expected_floors = {
            24: 0.0000005,
            23: 0.000001,
            22: 0.000002,
            21: 0.000005,
            20: 0.00001,
            19: 0.00002,
            18: 0.00005,
            17: 0.0001,
        }

        ratios = {}
        for v in versions:
            plan = {
                "symbol": "NVDA",
                "action": "BUY",
                "quantity": qty,
                "target_price": 500.0,
                "gamma_toxic_dir": 1.0,
                "version": v,
            }
            res = sor.route_order(plan, ats_available=False)
            r = res["maker_ratio"]
            ratios[v] = r
            assert math.isclose(r, expected_floors[v], abs_tol=1e-8), f"Version {v} floor {r} != {expected_floors[v]}"

        # Check strict monotonic ordering
        for i in range(len(versions) - 1):
            v_curr = versions[i]
            v_prev = versions[i + 1]
            assert ratios[v_curr] < ratios[v_prev], f"Monotonicity violation: v{v_curr} ({ratios[v_curr]}) >= v{v_prev} ({ratios[v_prev]})"


class TestDarkPoolATSRoutingAndMinQtyAdversarial:
    """Adversarial stress testing of 99.998% dark ATS routing and 99.9995% anti-gaming MinQty."""

    def test_dark_ats_routing_saturation_at_99_998_percent(self):
        """Under high toxicity and dark pool scores, dark ATS routing must saturate strictly at 99.998%."""
        sor = SmartOrderRouter()
        qty = 10_000_000

        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": qty,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "queue_imbalance": 0.90,
            "version": 24,
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        assert len(dark_legs) > 0

        dark_qty = sum(l["quantity"] for l in dark_legs)
        expected_dark = int(qty * 0.99998)
        assert dark_qty == expected_dark, f"Dark quantity {dark_qty} != expected {expected_dark}"

    def test_share_conservation_across_order_fragmentation(self):
        """
        Verify strict conservation of shares across fragmented and odd-lot order quantities:
        total quantity allocated to dark legs + lit legs MUST equal total order quantity.
        """
        sor = SmartOrderRouter()
        test_quantities = [1, 2, 3, 5, 7, 11, 47, 99, 100, 101, 1000, 10007, 1_000_000, 2_000_001, 10_000_000]

        for q in test_quantities:
            plan = {
                "symbol": "TSLA",
                "action": "BUY",
                "quantity": q,
                "target_price": 200.0,
                "gamma_toxic_dir": 0.85,
                "darkpool_score": 0.80,
                "version": 24,
            }
            res = sor.route_order(plan, ats_available=True)
            legs = res.get("legs", [])
            allocated_total = sum(l["quantity"] for l in legs)
            assert allocated_total == q, f"Share conservation violated for qty={q}: allocated={allocated_total}"

    def test_anti_gaming_min_qty_cap_at_99_9995_percent(self):
        """
        Under extreme adverse selection (gamma_toxic = 1.0, dp_score = 1.0),
        the anti-gaming MinQty ratio must hit 99.9995% (0.999995).
        And min_quantity must strictly satisfy 1 <= min_quantity <= dark_quantity.
        """
        sor = SmartOrderRouter()
        test_quantities = [1000, 10_000, 100_000, 1_000_000, 10_000_000]

        for q in test_quantities:
            plan = {
                "symbol": "GOOGL",
                "action": "BUY",
                "quantity": q,
                "target_price": 140.0,
                "gamma_toxic_dir": 1.0,
                "darkpool_score": 1.0,
                "version": 24,
            }
            res = sor.route_order(plan, ats_available=True)
            assert math.isclose(res["min_ratio"], 0.999995, abs_tol=1e-8)

            dark_legs = [l for l in res.get("legs", []) if "DARK" in l.get("venue_type", "")]
            if dark_legs and dark_legs[0]["quantity"] > 0:
                d_qty = dark_legs[0]["quantity"]
                min_q = dark_legs[0].get("min_quantity", 0)
                assert dark_legs[0].get("anti_gaming_active") is True
                assert 1 <= min_q <= d_qty, f"MinQty {min_q} breached [1, {d_qty}]"
                ratio = min_q / d_qty
                assert math.isclose(ratio, 0.999995, abs_tol=1e-4)


class TestKNKQuintessencePhantomTachyonL3HydrodynamicsAdversarial:
    """Adversarial stress testing of KNK-PT L3 hydrodynamics under extreme radial regimes and orderbook states."""

    def test_knk_pt_extreme_radial_distances_near_zero_and_infinite_depth(self):
        """
        Stress test KNK-PT L3 orderbook hydrodynamics with extreme orderbook states:
        - r -> 0 regime (near-empty orderbook, one-sided book, zero depth).
        - r -> inf regime (ultra-deep orderbook, trillion-share liquidity).
        Verifies numerical stability, horizon safety, finite values, and absence of division by zero.
        """
        engine_empty = FastOrderBookMatchingEngine(symbol="EMPTY_SYM")
        engine_empty.add_limit_order("b1", "BUY", 10.0, 1e-5)
        engine_empty.add_limit_order("a1", "SELL", 10.1, 1e-5)

        res_empty = engine_empty.compute_kerr_newman_kiselev_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
        )
        assert math.isfinite(res_empty["knk_pt_hydrodynamic_acceleration"])
        assert math.isfinite(res_empty["frame_dragging_omega"])
        assert math.isfinite(res_empty["tidal_force"])
        assert -100.0 <= res_empty["knk_pt_hydrodynamic_acceleration"] <= 100.0
        assert -1.0 <= res_empty["knk_pt_accelerated_qi"] <= 1.0
        assert res_empty["knk_pt_micro_price"] > 0.0

        # Ultra-deep orderbook: 10^16 shares per level
        engine_deep = FastOrderBookMatchingEngine(symbol="DEEP_SYM")
        for i in range(10):
            engine_deep.add_limit_order(f"b_{i}", "BUY", 1000.0 - i, 1e16)
            engine_deep.add_limit_order(f"a_{i}", "SELL", 1001.0 + i, 1e16)

        res_deep = engine_deep.compute_kerr_newman_kiselev_tachyon_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
        )
        assert math.isfinite(res_deep["knk_pt_hydrodynamic_acceleration"])
        assert math.isfinite(res_deep["frame_dragging_omega"])
        assert math.isfinite(res_deep["tidal_force"])
        assert -100.0 <= res_deep["knk_pt_hydrodynamic_acceleration"] <= 100.0
        assert -1.0 <= res_deep["knk_pt_accelerated_qi"] <= 1.0
        assert res_deep["knk_pt_micro_price"] > 0.0
        assert res_deep["coordinate_radius_r"] > 10.0  # deep orderbook coordinates expand smoothly

    def test_knk_pt_triple_dark_energy_repulsive_tidal_force_physics(self):
        """
        Verify physical properties of triple dark energy repulsive tidal forces:
        F_{tidal}^{KNK-PT} = F_{tidal}^{KN} - c_q * r - 2 * c_p * r^3 - 2.5 * c_t * r^4.
        1. All three dark energy terms (-c_q*r, -2*c_p*r^3, -2.5*c_t*r^4) are strictly negative (repulsive).
        2. Increasing tachyon parameter c_t strictly decreases (repulses) tidal force before clamp saturation.
        3. Extreme parameters (large ct up to 100.0) are safely clamped to [-100.0, 100.0] without divergence.
        4. Tachyon horizon r_T lies strictly outside the event horizon: r_T > r_horizon.
        """
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 70000.0 - i * 10.0, 50.0)
            engine.add_limit_order(f"a_{i}", "SELL", 70050.0 + i * 10.0, 50.0)

        ct_values = [0.00001, 0.0001, 0.0005, 0.001, 0.002]
        prev_tidal = float("inf")

        for ct in ct_values:
            res = engine.compute_kerr_newman_kiselev_tachyon_queue_acceleration(
                charge_parameter=0.4,
                spin_parameter=0.6,
                quintessence_parameter=0.01,
                phantom_parameter=0.005,
                tachyon_parameter=ct,
            )
            tidal = res["knk_pt_tidal_force"]
            # Increasing c_t strictly increases repulsion (lowers tidal force)
            assert tidal < prev_tidal, f"Tidal force did not decrease with higher ct: {tidal} >= {prev_tidal}"
            prev_tidal = tidal

            # Horizon ordering
            r_H = res["horizon_radius"]
            r_T = res["tachyon_horizon_r_T"]
            r_P = res["phantom_horizon_r_P"]
            r_Q = res["quintessence_horizon_r_Q"]
            assert r_T > r_H, f"Tachyon horizon {r_T} <= event horizon {r_H}"
            assert r_P > r_H, f"Phantom horizon {r_P} <= event horizon {r_H}"
            assert r_Q > r_H, f"Quintessence horizon {r_Q} <= event horizon {r_H}"

        # Extreme tachyon parameters clamped to [-100.0, 100.0]
        res_extreme = engine.compute_kerr_newman_kiselev_tachyon_queue_acceleration(
            charge_parameter=0.4,
            spin_parameter=0.6,
            quintessence_parameter=0.5,
            phantom_parameter=0.5,
            tachyon_parameter=100.0,
        )
        assert res_extreme["knk_pt_tidal_force"] == -100.0, "Extreme tachyon force must be clamped at -100.0"
        assert math.isfinite(res_extreme["knk_pt_hydrodynamic_acceleration"])


class TestBenchmarkEngineStressAndTriPathSynchronization:
    """Adversarial stress testing of Phase 24 Benchmark calculations and markdown report synchronization."""

    def test_phase23_continuous_baseline_verbatim_match(self):
        """
        Verify that Phase 24 aggregate baseline strictly matches Phase 23 actual results verbatim:
        - Net Expected Return: 113.38%
        - Annualized Sharpe Ratio: 17.18
        - Maximum Drawdown (MDD): -0.019%
        - Trading & Friction Costs: 0.024 bps
        - Execution Slippage: 0.0012 bps
        - Top-Decile Alpha Spread: 84.9%
        """
        assert round(agg_bl["net_ret"], 2) == 113.38, f"Baseline Net Return {agg_bl['net_ret']} != 113.38"
        assert round(agg_bl["sharpe"], 2) == 17.18, f"Baseline Sharpe {agg_bl['sharpe']} != 17.18"
        assert round(agg_bl["mdd"], 3) == -0.019, f"Baseline MDD {agg_bl['mdd']} != -0.019"
        assert round(agg_bl["friction"], 3) == 0.024, f"Baseline Friction {agg_bl['friction']} != 0.024"
        assert round(agg_bl["slippage"], 4) == 0.0012, f"Baseline Slippage {agg_bl['slippage']} != 0.0012"
        assert round(agg_bl["top_decile"], 1) == 84.9, f"Baseline Top-Decile {agg_bl['top_decile']} != 84.9"

    def test_all_six_target_criteria_mathematical_safety_margins(self):
        """
        Verify that all 6 quantitative targets are met with strict positive safety margins:
        1. Net Return >= 115.45% (Achieved: 115.49%, margin +0.04%p)
        2. Sharpe Ratio >= 17.75 (Achieved: 17.78, margin +0.03)
        3. MDD <= -0.018% (Achieved: -0.016%, margin +0.002%p tighter)
        4. Friction Costs <= 0.018 bps (Achieved: 0.016 bps, margin -0.002 bps lower)
        5. Slippage <= 0.0010 bps (Achieved: 0.0008 bps, margin -0.0002 bps lower)
        6. Top-Decile Spread >= 87.2% (Achieved: 87.3%, margin +0.1%p)
        """
        assert agg_p24["net_ret"] >= 115.45
        assert agg_p24["net_ret"] - 115.45 >= 0.039, "Net return safety margin insufficient"

        assert agg_p24["sharpe"] >= 17.75
        assert agg_p24["sharpe"] - 17.75 >= 0.029, "Sharpe safety margin insufficient"

        assert abs(agg_p24["mdd"]) <= 0.018 or agg_p24["mdd"] >= -0.018
        assert agg_p24["mdd"] - (-0.018) >= 0.0019, "MDD compression safety margin insufficient"

        assert agg_p24["friction"] <= 0.018
        assert 0.018 - agg_p24["friction"] >= 0.0015, "Friction cost reduction safety margin insufficient"

        assert agg_p24["slippage"] <= 0.0010
        assert 0.0010 - agg_p24["slippage"] >= 0.00015, "Slippage reduction safety margin insufficient"

        assert agg_p24["top_decile"] >= 87.2
        assert agg_p24["top_decile"] - 87.2 >= 0.09, "Top-decile spread expansion safety margin insufficient"

    def test_tri_path_markdown_reports_strict_synchronization(self):
        """
        Verify strict synchronization of reports across all 3 destination paths:
        1. reports/quant_benchmark_comparison_phase24.md
        2. trading_system/result/quant_benchmark_comparison_phase24.md
        3. reports/quant_benchmark_comparison.md
        Path 1 and Path 2 must be byte-for-byte identical.
        Path 3 must contain Path 1 content at the top, preserving Phase 23 archive.
        """
        p1 = Path("reports/quant_benchmark_comparison_phase24.md")
        p2 = Path("trading_system/result/quant_benchmark_comparison_phase24.md")
        p3 = Path("reports/quant_benchmark_comparison.md")

        assert p1.exists(), f"{p1} missing"
        assert p2.exists(), f"{p2} missing"
        assert p3.exists(), f"{p3} missing"

        c1 = p1.read_text(encoding="utf-8")
        c2 = p2.read_text(encoding="utf-8")
        c3 = p3.read_text(encoding="utf-8")

        # 1. Byte-for-byte identity between primary and result copy
        assert c1 == c2, "reports/ and trading_system/result/ Phase 24 benchmark files are not byte-for-byte identical"

        # 2. Canonical comparison file contains Phase 24 at the top
        assert c3.startswith(c1), "reports/quant_benchmark_comparison.md does not start with Phase 24 content"

        # 3. Canonical comparison file preserves historical Phase 23 benchmark archive
        assert "Phase 23 Quantitative Enhancement" in c3, "Historical Phase 23 archive missing from canonical report"

        # 4. Canonical 3 standard tables verification
        for content in [c1, c2, c3]:
            assert "[표 1] 15대 종합 지표 비교표" in content
            assert "[표 2] 5대 시장별 성과표" in content
            assert "[표 3] 전략 팩터 기여도표" in content
            assert "115.49%" in content
            assert "17.78" in content
            assert "-0.016%" in content
            assert "0.016 bps" in content
            assert "0.0008 bps" in content
            assert "87.3%" in content
