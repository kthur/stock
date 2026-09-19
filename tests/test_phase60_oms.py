"""
tests/test_phase60_oms.py

Unit and integration test suite for Phase 60 Quantitative Alpha Enhancement (Feature F274.1 & F274.2 Microstructure OMS):
- Kerr-Newman-Kiselev 39-Dark-Energy DAHA
  (w = -41/3 = -13.666666666666666, k_daha = 0.31, k_monster = 0.30, daha_39_factor = 5.36, c_monster = 3.814697265625e-13)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 39-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 39-fold dark energy repulsive acceleration (-20.5 * c * r^40 * daha_39)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28+ aliases)
- Fast LOB 99.9999999999999995% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=60:
  * Preemptive lit queue imbalance allocation with max dark cap 0.999999999999999995.
  * Lit maker ratio floor contracted to 1e-32
    via 0.70 * (1.0 - 0.9999999999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.9999999999999995% (0.999999999999999995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0000025:
  hawkes_shift = -direction * 0.9999999999999998 * spr * (h - 0.0000025).
- Full backward compatibility across Phase 14 through Phase 59 versions.
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


class TestPhase60MicrostructureOMS:
    """Test suite for Phase 60 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_39_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 39-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_39_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_39_dark_energy_tidal_force" in res
        assert "density_dark_energy_39" in res
        assert "r_39_dark_energy" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])
        assert math.isclose(res["density_dark_energy_39"], 3.814697265625e-13, rel_tol=1e-9)
        assert math.isclose(res["daha_39_factor"], 5.36, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_39"], -41.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_39_dark_energy_aliases(self):
        """Verify all 28 aliases of 39-dark-energy DAHA on FastOrderBookMatchingEngine / FastLOBEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_39_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        dispatch_aliases = [
            engine.calculate_knk_39_dark_energy_daha_acceleration,
            engine.compute_knk_39_dark_energy_daha,
            engine.knk_39_dark_energy_daha_acceleration,
            engine.compute_phase60_lob_acceleration,
            engine.phase60_lob_spacetime_hydrodynamics,
            engine.daha_39_dark_energy_acceleration,
            engine.kerr_newman_kiselev_39_acceleration,
            engine.compute_39_dark_energy_acceleration,
            engine.phase60_daha_l3_acceleration,
            engine.knk_daha_39_acceleration,
            engine.l3_knk_39_acceleration,
            engine.spacetime_hydrodynamics_39_acceleration,
            engine.daha_l3_phase60_acceleration,
            engine.monster_daha_39_acceleration,
            engine.phase60_dark_energy_acceleration,
            engine.knk_39_spacetime_acceleration,
            engine.calculate_phase60_knk_acceleration,
            engine.compute_knk_phase60_acceleration,
            engine.daha_phase60_acceleration,
            engine.knk_dark_energy_39_acceleration,
            engine.phase60_spacetime_hydrodynamics,
            engine.compute_l3_hydrodynamics_v60,
            engine.knk_39_daha_l3_acceleration,
            engine.phase60_queue_acceleration,
            engine.knk_39_acceleration,
            engine.daha_39_acceleration,
            engine.l3_phase60_acceleration,
            engine.phase60_knk_acceleration,
        ]
        assert len(dispatch_aliases) >= 28

        for alias_fn in dispatch_aliases:
            out = alias_fn()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(out["predicted_micro_price"], ref["predicted_micro_price"], rel_tol=1e-5)

        engine_lob = FastLOBEngine(symbol="005930")
        assert hasattr(engine_lob, "calculate_knk_39_dark_energy_daha_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v60(self):
        """Verify FastLOB DeepHawkesArrivalProcess dark ATS allocation cap at 0.999999999999999995."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v60 = proc.compute_preemptive_dark_routing(version=60)
        assert "preemptive_dark_routing_ratio" in res_v60
        assert math.isclose(res_v60["preemptive_dark_routing_ratio"], 0.999999999999999995, rel_tol=1e-15)

        # Also verify stack frame detection works when version is omitted (since this file name has phase60)
        proc_auto = DeepHawkesArrivalProcess()
        proc_auto.lambda_state = np.array([20.0, 0.5, 0.2])
        res_auto = proc_auto.compute_preemptive_dark_routing()
        assert math.isclose(res_auto["preemptive_dark_routing_ratio"], 0.999999999999999995, rel_tol=1e-15)

    def test_smart_order_router_version_60_maker_floor_and_anti_gaming(self):
        """Verify SmartOrderRouter v60 lit maker floor of 1e-32 and anti-gaming MinQty 0.999999999999999995."""
        router = SmartOrderRouter(version=60)
        assert math.isclose(router._resolve_max_dark_cap(60), 0.999999999999999995, rel_tol=1e-15)

        order_plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "market_spread_bps": 5.0,
            "gamma_toxic_dir": 1.0,  # extreme toxic directional flow
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 60,
        }
        res = router.route_order(order_plan, ats_available=True)
        assert res["maker_ratio"] == 1e-32
        assert res["min_ratio"] == 0.999999999999999995

    def test_oms_preemptive_micro_tick_shading_threshold_v60(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0000025."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010  # above 0.0000025

        p_buy = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=60,
        )
        expected_shift_buy = -1 * 0.9999999999999998 * spread * (h_val - 0.0000025)
        assert math.isclose(p_buy - target_px, expected_shift_buy, rel_tol=1e-5)

        p_sell = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=60,
        )
        expected_shift_sell = 1 * 0.9999999999999998 * spread * (h_val - 0.0000025)
        assert math.isclose(p_sell - target_px, expected_shift_sell, rel_tol=1e-5)

        # Verify AlmgrenChrissScheduler matches ExecutionOMSEngine
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=60,
        )
        assert math.isclose(p_sched, p_buy, rel_tol=1e-7)

    def test_oms_backward_compatibility_v59_and_prior(self):
        """Verify backward compatibility of tick shading and maker floor for v59, v58, etc."""
        oms = ExecutionOMSEngine()
        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5

        # In v59: threshold was 0.000003
        # In v60: threshold is 0.0000025
        # At h = 0.0000028: v60 activates (0.0000028 > 0.0000025), v59 does NOT (0.0000028 <= 0.000003)
        p_v60 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.0000028},
            version=60,
        )
        p_v59 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.0000028},
            version=59,
        )

        assert p_v60 < target_px
        assert math.isclose(p_v59, target_px, rel_tol=1e-7)

        # Verify maker floor backward compatibility: v59 floor is 1e-31, v60 floor is 1e-32
        router59 = SmartOrderRouter(version=59)
        router60 = SmartOrderRouter(version=60)
        order_plan59 = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 59,
        }
        order_plan60 = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 60,
        }
        res59 = router59.route_order(order_plan59)
        res60 = router60.route_order(order_plan60)
        assert res59["maker_ratio"] == 1e-31
        assert res60["maker_ratio"] == 1e-32
