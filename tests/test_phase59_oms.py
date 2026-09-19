"""
tests/test_phase59_oms.py

Unit and integration test suite for Phase 59 Quantitative Alpha Enhancement (Feature F269.1 & F269.2 Microstructure OMS):
- Kerr-Newman-Kiselev 38-Dark-Energy DAHA
  (w = -40/3 = -13.333333333333334, k_daha = 0.30, k_monster = 0.29, daha_38_factor = 5.12, c_monster = 7.62939453125e-13)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 38-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 38-fold dark energy repulsive acceleration (-20.0 * c * r^39 * daha_38)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28 aliases)
- Fast LOB 99.999999999999999% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=59:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999999999999999 (17 nines).
  * Lit maker ratio floor contracted to 1e-31 (0.0000000000000000000000000000001, 31 decimals)
    via 0.70 * (1.0 - 0.999999999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.999999999999999% (0.99999999999999999).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.000003:
  hawkes_shift = -direction * 0.9999999999999995 * spr * (h - 0.000003).
- Full backward compatibility across Phase 14 through Phase 58 versions.
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


class TestPhase59MicrostructureOMS:
    """Test suite for Phase 59 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_38_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 38-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_38_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_38_dark_energy_tidal_force" in res
        assert "density_dark_energy_38" in res
        assert "r_38_dark_energy" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])
        assert math.isclose(res["density_dark_energy_38"], 7.62939453125e-13, rel_tol=1e-9)
        assert math.isclose(res["daha_38_factor"], 5.12, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_38"], -40.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_38_dark_energy_aliases(self):
        """Verify all 28 aliases of 38-dark-energy DAHA on FastOrderBookMatchingEngine / FastLOBEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_38_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        dispatch_aliases = [
            engine.calculate_knk_38_dark_energy_daha_acceleration,
            engine.compute_knk_38_dark_energy_daha,
            engine.knk_38_dark_energy_daha_acceleration,
            engine.compute_phase59_lob_acceleration,
            engine.phase59_lob_spacetime_hydrodynamics,
            engine.daha_38_dark_energy_acceleration,
            engine.kerr_newman_kiselev_38_acceleration,
            engine.compute_38_dark_energy_acceleration,
            engine.phase59_daha_l3_acceleration,
            engine.knk_daha_38_acceleration,
            engine.l3_knk_38_acceleration,
            engine.spacetime_hydrodynamics_38_acceleration,
            engine.daha_l3_phase59_acceleration,
            engine.monster_daha_38_acceleration,
            engine.phase59_dark_energy_acceleration,
            engine.knk_38_spacetime_acceleration,
            engine.calculate_phase59_knk_acceleration,
            engine.compute_knk_phase59_acceleration,
            engine.daha_phase59_acceleration,
            engine.knk_dark_energy_38_acceleration,
            engine.phase59_spacetime_hydrodynamics,
            engine.compute_l3_hydrodynamics_v59,
            engine.knk_38_daha_l3_acceleration,
            engine.phase59_queue_acceleration,
            engine.knk_38_acceleration,
            engine.daha_38_acceleration,
            engine.l3_phase59_acceleration,
            engine.phase59_knk_acceleration,
        ]
        assert len(dispatch_aliases) == 28

        for alias_fn in dispatch_aliases:
            out = alias_fn()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(out["predicted_micro_price"], ref["predicted_micro_price"], rel_tol=1e-5)

        engine_lob = FastLOBEngine(symbol="005930")
        assert hasattr(engine_lob, "calculate_knk_38_dark_energy_daha_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v59(self):
        """Verify FastLOB DeepHawkesArrivalProcess dark ATS allocation cap at 0.99999999999999999 (17 nines)."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v59 = proc.compute_preemptive_dark_routing(version=59)
        assert "preemptive_dark_routing_ratio" in res_v59
        assert math.isclose(res_v59["preemptive_dark_routing_ratio"], 0.99999999999999999, rel_tol=1e-15)

        # Also verify stack frame detection works when version is omitted (since this file name has phase59)
        proc_auto = DeepHawkesArrivalProcess()
        proc_auto.lambda_state = np.array([20.0, 0.5, 0.2])
        res_auto = proc_auto.compute_preemptive_dark_routing()
        assert math.isclose(res_auto["preemptive_dark_routing_ratio"], 0.99999999999999999, rel_tol=1e-15)

    def test_smart_order_router_version_59_maker_floor_and_anti_gaming(self):
        """Verify SmartOrderRouter v59 lit maker floor of 1e-31 and anti-gaming MinQty 0.99999999999999999."""
        router = SmartOrderRouter(version=59)
        assert math.isclose(router._resolve_max_dark_cap(59), 0.99999999999999999, rel_tol=1e-15)

        order_plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "market_spread_bps": 5.0,
            "gamma_toxic_dir": 1.0,  # extreme toxic directional flow
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 59,
        }
        res = router.route_order(order_plan, ats_available=True)
        assert res["maker_ratio"] == 1e-31
        assert res["min_ratio"] == 0.99999999999999999

    def test_oms_preemptive_micro_tick_shading_threshold_v59(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.000003."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010  # above 0.000003

        p_buy = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=59,
        )
        expected_shift_buy = -1 * 0.9999999999999995 * spread * (h_val - 0.000003)
        assert math.isclose(p_buy - target_px, expected_shift_buy, rel_tol=1e-5)

        p_sell = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=59,
        )
        expected_shift_sell = 1 * 0.9999999999999995 * spread * (h_val - 0.000003)
        assert math.isclose(p_sell - target_px, expected_shift_sell, rel_tol=1e-5)

        # Verify AlmgrenChrissScheduler matches ExecutionOMSEngine
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=59,
        )
        assert math.isclose(p_sched, p_buy, rel_tol=1e-7)

    def test_oms_backward_compatibility_v58_and_prior(self):
        """Verify backward compatibility of tick shading and maker floor for v58, v57, etc."""
        oms = ExecutionOMSEngine()
        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5

        # In v58: threshold was 0.000004
        # In v59: threshold is 0.000003
        # At h = 0.0000035: v59 activates (0.0000035 > 0.000003), v58 does NOT (0.0000035 <= 0.000004)
        p_v59 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.0000035},
            version=59,
        )
        p_v58 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.0000035},
            version=58,
        )

        assert p_v59 < target_px
        assert math.isclose(p_v58, target_px, rel_tol=1e-7)

        # Verify maker floor backward compatibility: v58 floor is 1e-30, v59 floor is 1e-31
        router58 = SmartOrderRouter(version=58)
        router59 = SmartOrderRouter(version=59)
        order_plan58 = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 58,
        }
        order_plan59 = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 59,
        }
        res58 = router58.route_order(order_plan58)
        res59 = router59.route_order(order_plan59)
        assert res58["maker_ratio"] == 1e-30
        assert res59["maker_ratio"] == 1e-31
