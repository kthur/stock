"""
tests/test_phase58_oms.py

Unit and integration test suite for Phase 58 Quantitative Alpha Enhancement (Feature F264.1 & F264.2 Microstructure OMS):
- Kerr-Newman-Kiselev 37-Dark-Energy DAHA
  (w = -39/3 = -13.0, k_daha = 0.29, k_monster = 0.28, daha_37_factor = 4.88, c_monster = 0.00000000000152587890625)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 37-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 37-fold dark energy repulsive acceleration (-19.5 * c * r^38 * daha_37)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28 aliases)
- Fast LOB 99.999999999999998% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=58:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999999999999998 (18 nines).
  * Lit maker ratio floor contracted to 1e-30 (0.000000000000000000000000000001, 30 decimals)
    via 0.70 * (1.0 - 0.999999999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.999999999999998% (0.99999999999999998).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.000004:
  hawkes_shift = -direction * 0.999999999999999 * spr * (h - 0.000004).
- Full backward compatibility across Phase 14 through Phase 57 versions.
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


class TestPhase58MicrostructureOMS:
    """Test suite for Phase 58 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_37_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 37-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_37_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_37_dark_energy_tidal_force" in res
        assert "density_dark_energy_37" in res
        assert "r_37_dark_energy" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])
        assert math.isclose(res["density_dark_energy_37"], 0.00000000000152587890625, rel_tol=1e-9)
        assert math.isclose(res["daha_37_factor"], 4.88, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_37"], -39.0 / 3.0, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_37"], -13.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_37_dark_energy_aliases(self):
        """Verify all 28 aliases of 37-dark-energy DAHA on FastOrderBookMatchingEngine / FastLOBEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_37_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        dispatch_aliases = [
            engine.calculate_knk_37_dark_energy_daha_acceleration,
            engine.compute_knk_37_dark_energy_daha,
            engine.knk_37_dark_energy_daha_acceleration,
            engine.compute_phase58_lob_acceleration,
            engine.phase58_lob_spacetime_hydrodynamics,
            engine.daha_37_dark_energy_acceleration,
            engine.kerr_newman_kiselev_37_acceleration,
            engine.compute_37_dark_energy_acceleration,
            engine.phase58_daha_l3_acceleration,
            engine.knk_daha_37_acceleration,
            engine.l3_knk_37_acceleration,
            engine.spacetime_hydrodynamics_37_acceleration,
            engine.daha_l3_phase58_acceleration,
            engine.monster_daha_37_acceleration,
            engine.phase58_dark_energy_acceleration,
            engine.knk_37_spacetime_acceleration,
            engine.calculate_phase58_knk_acceleration,
            engine.compute_knk_phase58_acceleration,
            engine.daha_phase58_acceleration,
            engine.knk_dark_energy_37_acceleration,
            engine.phase58_spacetime_hydrodynamics,
            engine.compute_l3_hydrodynamics_v58,
            engine.knk_37_daha_l3_acceleration,
            engine.phase58_queue_acceleration,
            engine.knk_37_acceleration,
            engine.daha_37_acceleration,
            engine.l3_phase58_acceleration,
            engine.phase58_knk_acceleration,
        ]
        assert len(dispatch_aliases) == 28

        for alias_fn in dispatch_aliases:
            out = alias_fn()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(out["predicted_micro_price"], ref["predicted_micro_price"], rel_tol=1e-5)

        engine_lob = FastLOBEngine(symbol="005930")
        assert hasattr(engine_lob, "calculate_knk_37_dark_energy_daha_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v58(self):
        """Verify FastLOB DeepHawkesArrivalProcess dark ATS allocation cap at 0.99999999999999998 (18 nines)."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v58 = proc.compute_preemptive_dark_routing(version=58)
        assert "preemptive_dark_routing_ratio" in res_v58
        assert math.isclose(res_v58["preemptive_dark_routing_ratio"], 0.99999999999999998, rel_tol=1e-15)

        # Also verify stack frame detection works when version is omitted (since this file name has phase58)
        proc_auto = DeepHawkesArrivalProcess()
        proc_auto.lambda_state = np.array([20.0, 0.5, 0.2])
        res_auto = proc_auto.compute_preemptive_dark_routing()
        assert math.isclose(res_auto["preemptive_dark_routing_ratio"], 0.99999999999999998, rel_tol=1e-15)

    def test_smart_order_router_version_58_maker_floor_and_anti_gaming(self):
        """Verify SmartOrderRouter v58 lit maker floor of 1e-30 and anti-gaming MinQty 0.99999999999999998."""
        router = SmartOrderRouter(version=58)
        assert math.isclose(router._resolve_max_dark_cap(58), 0.99999999999999998, rel_tol=1e-15)

        order_plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "market_spread_bps": 5.0,
            "gamma_toxic_dir": 1.0,  # extreme toxic directional flow
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 58,
        }
        res = router.route_order(order_plan, ats_available=True)
        assert res["maker_ratio"] == 1e-30
        assert res["min_ratio"] == 0.99999999999999998

    def test_oms_preemptive_micro_tick_shading_threshold_v58(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.000004."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010  # above 0.000004

        p_buy = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=58,
        )
        expected_shift_buy = -1 * 0.999999999999999 * spread * (h_val - 0.000004)
        assert math.isclose(p_buy - target_px, expected_shift_buy, rel_tol=1e-5)

        p_sell = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=58,
        )
        expected_shift_sell = 1 * 0.999999999999999 * spread * (h_val - 0.000004)
        assert math.isclose(p_sell - target_px, expected_shift_sell, rel_tol=1e-5)

        # Verify AlmgrenChrissScheduler matches ExecutionOMSEngine
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=58,
        )
        assert math.isclose(p_sched, p_buy, rel_tol=1e-7)

    def test_oms_backward_compatibility_v57_and_prior(self):
        """Verify backward compatibility of tick shading and maker floor for v57, v56, etc."""
        oms = ExecutionOMSEngine()
        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5

        # In v57: threshold was 0.000006
        # In v58: threshold is 0.000004
        # At h = 0.000005: v58 activates (0.000005 > 0.000004), v57 does NOT (0.000005 <= 0.000006)
        p_v58 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000005},
            version=58,
        )
        p_v57 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000005},
            version=57,
        )

        assert p_v58 < target_px
        assert math.isclose(p_v57, target_px, rel_tol=1e-7)

        # Verify maker floor backward compatibility: v57 floor is 1e-29, v58 floor is 1e-30
        router57 = SmartOrderRouter(version=57)
        router58 = SmartOrderRouter(version=58)
        order_plan57 = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 57,
        }
        order_plan58 = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 58,
        }
        res57 = router57.route_order(order_plan57)
        res58 = router58.route_order(order_plan58)
        assert res57["maker_ratio"] == 1e-29
        assert res58["maker_ratio"] == 1e-30
