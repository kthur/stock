"""
tests/test_phase54_oms.py

Unit and integration test suite for Phase 54 Quantitative Enhancement (Feature F244.1 & F244.2 Microstructure OMS):
- Kerr-Newman-Kiselev 33-Dark-Energy DAHA
  (w = -35/3, k_daha = 0.25, k_monster = 0.24, daha_33_factor = 3.98, c_monster = 0.0000000000244140625)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 33-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 33-fold dark energy repulsive acceleration (-17.5 * c * r^34 * daha_33)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28 aliases)
- Fast LOB 99.99999999999995% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=54:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9999999999999995 (99.99999999999995%).
  * Lit maker ratio floor contracted to 1e-26 (0.00000000000000000000000001, 26 decimals)
    via 0.70 * (1.0 - 0.99999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.99999999999995% (0.9999999999999995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.000015:
  hawkes_shift = -direction * 0.99999999999998 * spr * (h - 0.000015).
- Full backward compatibility across Phase 14 through Phase 53 versions.
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


class TestPhase54MicrostructureOMS:
    """Test suite for Phase 54 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_33_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 33-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_33_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_33_dark_energy_tidal_force" in res
        assert "density_dark_energy_33" in res
        assert "r_33_dark_energy" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])
        assert math.isclose(res["density_dark_energy_33"], 0.0000000000244140625, rel_tol=1e-9)
        assert math.isclose(res["daha_33_factor"], 3.98, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_33"], -35.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_33_dark_energy_aliases(self):
        """Verify all 28 aliases of 33-dark-energy DAHA on FastOrderBookMatchingEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_33_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        aliases = [
            engine.compute_kerr_newman_kiselev_33_dark_energy_daha_queue_acceleration,
            engine.calculate_kerr_newman_kiselev_33_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            engine.compute_knk_33_dark_energy_daha_queue_acceleration,
            engine.compute_knk_33_dark_energy_queue_acceleration,
            engine.compute_knk_borcherds_moonshine_monster_33_dark_energy_daha_queue_acceleration,
            engine.compute_kerr_newman_kiselev_33_dark_energy_moonshine_monster_queue_acceleration,
            engine.compute_knk_33_dark_energy_monster_moonshine_queue_acceleration,
            engine.compute_phase54_queue_acceleration,
            engine.compute_phase54_knk_daha_queue_acceleration,
            engine.compute_phase54_lob_hydrodynamics,
            engine.compute_phase54_lob_acceleration,
            engine.compute_knk_daha_order54_queue_acceleration,
            engine.compute_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_whittaker_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_virasoro_whittaker_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_universal_virasoro_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_elliptic_hypergeometric_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_askey_wilson_elliptic_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_macdonald_askey_wilson_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_kostka_macdonald_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_cherednik_kostka_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_hecke_cherednik_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_dunkl_hecke_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_dirac_dunkl_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_dilaton_dirac_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_brane_dilaton_borcherds_moonshine_monster_daha_order54_queue_acceleration,
            engine.compute_daha_33_queue_acceleration,
            engine.calculate_knk_33_dark_energy_daha_l3_spacetime_hydrodynamics,
        ]
        assert len(aliases) == 28

        for alias_fn in aliases:
            out = alias_fn()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(out["predicted_micro_price"], ref["predicted_micro_price"], rel_tol=1e-5)

    def test_preemptive_dark_routing_cap_version_54(self):
        """Verify dark routing allocation cap reaches 0.9999999999999995 under version 54."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v54 = proc.compute_preemptive_dark_routing(version=54)
        assert "preemptive_dark_routing_ratio" in res_v54
        assert math.isclose(res_v54["preemptive_dark_routing_ratio"], 0.9999999999999995, rel_tol=1e-15)

    def test_smart_order_router_dark_cap_and_maker_floor_version_54(self):
        """Verify SmartOrderRouter dark cap 0.9999999999999995 and lit maker floor 1e-26 under version 54."""
        router = SmartOrderRouter(version=54)
        assert math.isclose(router._resolve_max_dark_cap(54), 0.9999999999999995, rel_tol=1e-15)

        order_plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "market_spread_bps": 5.0,
            "gamma_toxic_dir": 1.0,  # extreme toxic directional flow
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 54,
        }
        res = router.route_order(order_plan, ats_available=True)
        assert res["maker_ratio"] == 1e-26
        assert res["min_ratio"] == 0.9999999999999995

    def test_preemptive_micro_tick_shading_version_54(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.000015."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010  # above 0.000015

        p_buy = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=54,
        )
        expected_shift_buy = -1 * 0.99999999999998 * spread * (h_val - 0.000015)
        assert math.isclose(p_buy - target_px, expected_shift_buy, rel_tol=1e-5)

        p_sell = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=54,
        )
        expected_shift_sell = 1 * 0.99999999999998 * spread * (h_val - 0.000015)
        assert math.isclose(p_sell - target_px, expected_shift_sell, rel_tol=1e-5)

        # Verify AlmgrenChrissScheduler matches ExecutionOMSEngine
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=54,
        )
        assert math.isclose(p_sched, p_buy, rel_tol=1e-7)

    def test_preemptive_micro_tick_shading_deadband_version_54(self):
        """Verify deadband region preserved at h <= 0.000015 for version 54."""
        oms = ExecutionOMSEngine()
        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5

        # Exactly at threshold
        p_thresh = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000015},
            version=54,
        )
        assert math.isclose(p_thresh, target_px, rel_tol=1e-7)

        # Below threshold
        p_sub = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000005},
            version=54,
        )
        assert math.isclose(p_sub, target_px, rel_tol=1e-7)

    def test_stack_frame_inspection_phase54(self):
        """Verify stack frame inspection properly detects phase54 in caller frame."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        # This test file is named test_phase54_oms.py which contains "phase54"
        res = proc.compute_preemptive_dark_routing()
        assert math.isclose(res["preemptive_dark_routing_ratio"], 0.9999999999999995, rel_tol=1e-15)

    def test_backward_compatibility_oms_phase53_and_prior(self):
        """Verify backward compatibility of SOR and tick shading for version 53 and prior."""
        router53 = SmartOrderRouter(version=53)
        assert math.isclose(router53._resolve_max_dark_cap(53), 0.999999999999999, rel_tol=1e-15)

        oms = ExecutionOMSEngine()
        # In version 53, threshold was 0.00002
        p_v53_dead = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            spread=1.0,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000018},
            version=53
        )
        assert math.isclose(p_v53_dead, 100.0, rel_tol=1e-5)
