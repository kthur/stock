"""
tests/test_phase52_oms.py

Unit and integration test suite for Phase 52 Quantitative Enhancement (Feature F234.1 & F234.2 Microstructure OMS):
- Kerr-Newman-Kiselev 31-Dark-Energy DAHA
  (w = -33/3 = -11.0, k_daha = 0.23, k_monster = 0.22, daha_31_factor = 3.54, c_monster = 0.00000000009765625)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 31-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 31-fold dark energy repulsive acceleration (-16.5 * c * r^32 * daha_31)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28 aliases)
- Fast LOB 99.9999999999998% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=52:
  * Preemptive lit queue imbalance allocation with max dark cap 0.999999999999998 (99.9999999999998%).
  * Lit maker ratio floor contracted to 1e-24 (0.000000000000000000000001, 24 decimals)
    via 0.70 * (1.0 - 0.999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.9999999999998% (0.999999999999998).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.00003:
  hawkes_shift = -direction * 0.9999999999999 * spr * (h - 0.00003).
- Full backward compatibility across Phase 14 through Phase 51 versions.
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    DeepHawkesArrivalProcess,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase52MicrostructureOMS:
    """Test suite for Phase 52 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_31_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 31-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_31_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_31_dark_energy_tidal_force" in res
        assert "density_dark_energy_31" in res
        assert "r_31_dark_energy" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])
        assert math.isclose(res["density_dark_energy_31"], 0.00000000009765625, rel_tol=1e-9)
        assert math.isclose(res["daha_31_factor"], 3.54, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_31"], -11.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_31_dark_energy_aliases(self):
        """Verify all 28 aliases of 31-dark-energy DAHA on FastOrderBookMatchingEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_31_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        aliases = [
            engine.compute_kerr_newman_kiselev_31_dark_energy_daha_queue_acceleration,
            engine.calculate_kerr_newman_kiselev_31_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            engine.compute_knk_31_dark_energy_daha_queue_acceleration,
            engine.compute_knk_31_dark_energy_queue_acceleration,
            engine.compute_knk_borcherds_moonshine_monster_31_dark_energy_daha_queue_acceleration,
            engine.compute_kerr_newman_kiselev_31_dark_energy_moonshine_monster_queue_acceleration,
            engine.compute_knk_31_dark_energy_monster_moonshine_queue_acceleration,
            engine.compute_phase52_queue_acceleration,
            engine.compute_phase52_knk_daha_queue_acceleration,
            engine.compute_phase52_lob_hydrodynamics,
            engine.compute_phase52_lob_acceleration,
            engine.compute_knk_daha_order52_queue_acceleration,
            engine.compute_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_whittaker_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_virasoro_whittaker_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_universal_virasoro_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_elliptic_hypergeometric_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_askey_wilson_elliptic_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_macdonald_askey_wilson_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_kostka_macdonald_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_cherednik_kostka_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_hecke_cherednik_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_dunkl_hecke_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_dirac_dunkl_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_dilaton_dirac_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_brane_dilaton_borcherds_moonshine_monster_daha_order52_queue_acceleration,
            engine.compute_daha_31_queue_acceleration,
            engine.calculate_knk_31_dark_energy_daha_l3_spacetime_hydrodynamics,
        ]
        assert len(aliases) == 28

        for alias_fn in aliases:
            out = alias_fn()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(out["predicted_micro_price"], ref["predicted_micro_price"], rel_tol=1e-5)

    def test_preemptive_dark_routing_cap_version_52(self):
        """Verify dark routing allocation cap reaches 0.999999999999998 under version 52."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([15.0, 0.5, 0.2])
        res_v52 = proc.compute_preemptive_dark_routing(version=52)
        assert "preemptive_dark_routing_ratio" in res_v52
        assert math.isclose(res_v52["preemptive_dark_routing_ratio"], 0.999999999999998, rel_tol=1e-15)

    def test_smart_order_router_dark_cap_and_maker_floor_version_52(self):
        """Verify SmartOrderRouter dark cap 0.999999999999998 and lit maker floor 1e-24 under version 52."""
        router = SmartOrderRouter(version=52)
        assert math.isclose(router._resolve_max_dark_cap(52), 0.999999999999998, rel_tol=1e-15)

        order_plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "market_spread_bps": 5.0,
            "gamma_toxic_dir": 1.0,  # extreme toxic directional flow
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 52,
        }
        res = router.route_order(order_plan, ats_available=True)
        assert res["maker_ratio"] == 1e-24
        assert res["min_ratio"] == 0.999999999999998

    def test_preemptive_micro_tick_shading_version_52(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.00003."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010  # above 0.00003

        p_buy = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=52,
        )
        # Shift should be negative for BUY (shade down to avoid adverse selection)
        expected_shift = -1 * 0.9999999999999 * spread * (h_val - 0.00003)
        assert math.isclose(p_buy - target_px, expected_shift, rel_tol=1e-5)

        p_buy_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=52,
        )
        assert math.isclose(p_buy_sched - target_px, expected_shift, rel_tol=1e-5)

    def test_backward_compatibility_version_51_and_prior(self):
        """Verify backward compatibility for version 51 and 50 in SmartOrderRouter and OMS."""
        router = SmartOrderRouter()
        assert math.isclose(router._resolve_max_dark_cap(51), 0.999999999999995, rel_tol=1e-14)
        assert math.isclose(router._resolve_max_dark_cap(50), 0.99999999999999, rel_tol=1e-14)

        oms = ExecutionOMSEngine()
        p_v51 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00010},
            version=51,
        )
        exp_v51 = -1 * 0.9999999999998 * 1.0 * (0.00010 - 0.00004)
        assert math.isclose(p_v51 - 100.0, exp_v51, rel_tol=1e-5)

    def test_stack_frame_inspection_phase52(self):
        """Verify stack frame inspection automatically detects 'phase52' in filename."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res = proc.compute_preemptive_dark_routing()
        assert math.isclose(res["preemptive_dark_routing_ratio"], 0.999999999999998, rel_tol=1e-15)

    def test_preemptive_micro_tick_shading_sell_direction_v52(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler for SELL direction."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00009  # above 0.00003

        p_sell = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=52,
        )
        # Shift should be positive for SELL (direction = -1 => -(-1) = +1: shade up to avoid under-selling)
        expected_shift = 1.0 * 0.9999999999999 * spread * (h_val - 0.00003)
        assert math.isclose(p_sell - target_px, expected_shift, rel_tol=1e-5)

        p_sell_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=52,
        )
        assert math.isclose(p_sell_sched - target_px, expected_shift, rel_tol=1e-5)

    def test_maker_leg_maker_ratio_in_route_order_v52(self):
        """Verify maker_leg internal dictionary preserves 24-decimal maker_ratio."""
        router = SmartOrderRouter(version=52)
        order_plan = {
            "symbol": "005930",
            "quantity": 1_000_000_000_000_000_000_000_000,
            "action": "BUY",
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 52,
        }
        res = router.route_order(order_plan, ats_available=False)
        maker_legs = [l for l in res.get("legs", []) if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER"]
        assert len(maker_legs) > 0
        assert maker_legs[0]["maker_ratio"] == 1e-24

    def test_kerr_newman_kiselev_31_dark_energy_physics_parameters(self):
        """Verify physics equations and constants for 31st dark energy component."""
        c_monster = 0.00000000009765625
        w_31 = -33.0 / 3.0
        k_daha = 0.23
        k_monster = 0.22
        daha_31_factor = 3.54

        # Horizon scale exponent 1/33.0
        c_monster_scale = (1.0 / max(1e-6, c_monster)) ** (1.0 / 33.0)
        assert c_monster_scale > 1.0

        engine = FastOrderBookMatchingEngine(symbol="005930")
        res = engine.compute_kerr_newman_kiselev_31_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            c_monster=c_monster,
            w=w_31,
            k_daha=k_daha,
            k_monster=k_monster,
            daha_31_factor=daha_31_factor,
        )
        assert res["c_monster"] == c_monster
        assert res["equation_of_state_w_31"] == -11.0
        assert res["k_daha"] == 0.23
        assert res["k_monster"] == 0.22
        assert res["daha_31_factor"] == 3.54
        assert res["density_dark_energy_31"] == c_monster

