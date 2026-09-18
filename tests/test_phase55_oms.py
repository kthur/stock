"""
tests/test_phase55_oms.py

Unit and integration test suite for Phase 55 Quantitative Alpha Enhancement (Feature F249.1 & F249.2 Microstructure OMS):
- Kerr-Newman-Kiselev 34-Dark-Energy DAHA
  (w = -36/3 = -12.0, k_daha = 0.26, k_monster = 0.25, daha_34_factor = 4.20, c_monster = 0.00000000001220703125)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 34-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 34-fold dark energy repulsive acceleration (-18.0 * c * r^35 * daha_34)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28 aliases)
- Fast LOB 99.99999999999998% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=55:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9999999999999998 (99.99999999999998%).
  * Lit maker ratio floor contracted to 1e-27 (0.000000000000000000000000001, 27 decimals)
    via 0.70 * (1.0 - 0.999999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.99999999999998% (0.9999999999999998).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.00001:
  hawkes_shift = -direction * 0.99999999999999 * spr * (h - 0.00001).
- Full backward compatibility across Phase 14 through Phase 54 versions.
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    DeepHawkesArrivalProcess,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestPhase55MicrostructureOMS:
    """Test suite for Phase 55 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_34_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 34-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_34_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_34_dark_energy_tidal_force" in res
        assert "density_dark_energy_34" in res
        assert "r_34_dark_energy" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])
        assert math.isclose(res["density_dark_energy_34"], 0.00000000001220703125, rel_tol=1e-9)
        assert math.isclose(res["daha_34_factor"], 4.20, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_34"], -36.0 / 3.0, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_34"], -12.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_34_dark_energy_aliases(self):
        """Verify all 28 aliases of 34-dark-energy DAHA on FastOrderBookMatchingEngine / FastLOBEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_34_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        # 28 canonical aliases from DISPATCH.md:
        dispatch_aliases = [
            engine.calculate_knk_34_dark_energy_daha_acceleration,
            engine.compute_knk_34_dark_energy_daha,
            engine.knk_34_dark_energy_daha_acceleration,
            engine.compute_phase55_lob_acceleration,
            engine.phase55_lob_spacetime_hydrodynamics,
            engine.daha_34_dark_energy_acceleration,
            engine.kerr_newman_kiselev_34_acceleration,
            engine.compute_34_dark_energy_acceleration,
            engine.phase55_daha_l3_acceleration,
            engine.knk_daha_34_acceleration,
            engine.l3_knk_34_acceleration,
            engine.spacetime_hydrodynamics_34_acceleration,
            engine.daha_l3_phase55_acceleration,
            engine.monster_daha_34_acceleration,
            engine.phase55_dark_energy_acceleration,
            engine.knk_34_spacetime_acceleration,
            engine.calculate_phase55_knk_acceleration,
            engine.compute_knk_phase55_acceleration,
            engine.daha_phase55_acceleration,
            engine.knk_dark_energy_34_acceleration,
            engine.phase55_spacetime_hydrodynamics,
            engine.compute_l3_hydrodynamics_v55,
            engine.knk_34_daha_l3_acceleration,
            engine.phase55_queue_acceleration,
            engine.knk_34_acceleration,
            engine.daha_34_acceleration,
            engine.l3_phase55_acceleration,
            engine.phase55_knk_acceleration,
        ]
        assert len(dispatch_aliases) == 28

        for alias_fn in dispatch_aliases:
            out = alias_fn()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(out["predicted_micro_price"], ref["predicted_micro_price"], rel_tol=1e-5)

        # Also verify FastLOBEngine class alias has access
        engine_lob = FastLOBEngine(symbol="005930")
        assert hasattr(engine_lob, "calculate_knk_34_dark_energy_daha_acceleration")

    def test_preemptive_dark_routing_cap_version_55(self):
        """Verify dark routing allocation cap reaches 0.9999999999999998 under version 55."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v55 = proc.compute_preemptive_dark_routing(version=55)
        assert "preemptive_dark_routing_ratio" in res_v55
        assert math.isclose(res_v55["preemptive_dark_routing_ratio"], 0.9999999999999998, rel_tol=1e-15)

    def test_smart_order_router_dark_cap_and_maker_floor_version_55(self):
        """Verify SmartOrderRouter dark cap 0.9999999999999998 and lit maker floor 1e-27 under version 55."""
        router = SmartOrderRouter(version=55)
        assert math.isclose(router._resolve_max_dark_cap(55), 0.9999999999999998, rel_tol=1e-15)

        order_plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "market_spread_bps": 5.0,
            "gamma_toxic_dir": 1.0,  # extreme toxic directional flow
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 55,
        }
        res = router.route_order(order_plan, ats_available=True)
        assert res["maker_ratio"] == 1e-27
        assert res["min_ratio"] == 0.9999999999999998

    def test_preemptive_micro_tick_shading_version_55(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.00001."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010  # above 0.00001

        p_buy = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=55,
        )
        expected_shift_buy = -1 * 0.99999999999999 * spread * (h_val - 0.00001)
        assert math.isclose(p_buy - target_px, expected_shift_buy, rel_tol=1e-5)

        p_sell = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=55,
        )
        expected_shift_sell = 1 * 0.99999999999999 * spread * (h_val - 0.00001)
        assert math.isclose(p_sell - target_px, expected_shift_sell, rel_tol=1e-5)

        # Verify AlmgrenChrissScheduler matches ExecutionOMSEngine
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=55,
        )
        assert math.isclose(p_sched, p_buy, rel_tol=1e-7)

    def test_preemptive_micro_tick_shading_deadband_version_55(self):
        """Verify deadband region preserved at h <= 0.00001 for version 55."""
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
            hawkes_intensity={"cross_excitation_toxicity": 0.00001},
            version=55,
        )
        assert math.isclose(p_thresh, target_px, rel_tol=1e-7)

        # Below threshold
        p_sub = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000005},
            version=55,
        )
        assert math.isclose(p_sub, target_px, rel_tol=1e-7)

    def test_stack_frame_inspection_phase55(self):
        """Verify stack frame inspection properly detects phase55 in caller frame."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        # This test file is named test_phase55_oms.py which contains "phase55"
        res = proc.compute_preemptive_dark_routing()
        assert math.isclose(res["preemptive_dark_routing_ratio"], 0.9999999999999998, rel_tol=1e-15)

    def test_backward_compatibility_oms_phase54_and_prior(self):
        """Verify backward compatibility of SOR and tick shading for version 54 and prior."""
        router54 = SmartOrderRouter(version=54)
        assert math.isclose(router54._resolve_max_dark_cap(54), 0.9999999999999995, rel_tol=1e-15)

        router53 = SmartOrderRouter(version=53)
        assert math.isclose(router53._resolve_max_dark_cap(53), 0.999999999999999, rel_tol=1e-15)

        oms = ExecutionOMSEngine()
        # In version 54, threshold was 0.000015
        p_v54_dead = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            spread=1.0,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000012},
            version=54
        )
        assert math.isclose(p_v54_dead, 100.0, rel_tol=1e-5)

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
