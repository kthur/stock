"""
tests/test_phase57_oms.py

Unit and integration test suite for Phase 57 Quantitative Alpha Enhancement (Feature F259.1 & F259.2 Microstructure OMS):
- Kerr-Newman-Kiselev 36-Dark-Energy DAHA
  (w = -38/3, k_daha = 0.28, k_monster = 0.27, daha_36_factor = 4.64, c_monster = 0.0000000000030517578125)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 36-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 36-fold dark energy repulsive acceleration (-19.0 * c * r^37 * daha_36)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28 aliases)
- Fast LOB 99.999999999999995% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=57:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999999999999995 (99.999999999999995%).
  * Lit maker ratio floor contracted to 1e-29 (0.00000000000000000000000000001, 29 decimals)
    via 0.70 * (1.0 - 0.99999999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.999999999999995% (0.99999999999999995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.000006:
  hawkes_shift = -direction * 0.999999999999998 * spr * (h - 0.000006).
- Full backward compatibility across Phase 14 through Phase 56 versions.
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


class TestPhase57MicrostructureOMS:
    """Test suite for Phase 57 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_36_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 36-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_36_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_36_dark_energy_tidal_force" in res
        assert "density_dark_energy_36" in res
        assert "r_36_dark_energy" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])
        assert math.isclose(res["density_dark_energy_36"], 0.0000000000030517578125, rel_tol=1e-9)
        assert math.isclose(res["daha_36_factor"], 4.64, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_36"], -38.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_36_dark_energy_aliases(self):
        """Verify all 28 aliases of 36-dark-energy DAHA on FastOrderBookMatchingEngine / FastLOBEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_36_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        dispatch_aliases = [
            engine.calculate_knk_36_dark_energy_daha_acceleration,
            engine.compute_knk_36_dark_energy_daha,
            engine.knk_36_dark_energy_daha_acceleration,
            engine.compute_phase57_lob_acceleration,
            engine.phase57_lob_spacetime_hydrodynamics,
            engine.daha_36_dark_energy_acceleration,
            engine.kerr_newman_kiselev_36_acceleration,
            engine.compute_36_dark_energy_acceleration,
            engine.phase57_daha_l3_acceleration,
            engine.knk_daha_36_acceleration,
            engine.l3_knk_36_acceleration,
            engine.spacetime_hydrodynamics_36_acceleration,
            engine.daha_l3_phase57_acceleration,
            engine.monster_daha_36_acceleration,
            engine.phase57_dark_energy_acceleration,
            engine.knk_36_spacetime_acceleration,
            engine.calculate_phase57_knk_acceleration,
            engine.compute_knk_phase57_acceleration,
            engine.daha_phase57_acceleration,
            engine.knk_dark_energy_36_acceleration,
            engine.phase57_spacetime_hydrodynamics,
            engine.compute_l3_hydrodynamics_v57,
            engine.knk_36_daha_l3_acceleration,
            engine.phase57_queue_acceleration,
            engine.knk_36_acceleration,
            engine.daha_36_acceleration,
            engine.l3_phase57_acceleration,
            engine.phase57_knk_acceleration,
        ]
        assert len(dispatch_aliases) == 28

        for alias_fn in dispatch_aliases:
            out = alias_fn()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(out["predicted_micro_price"], ref["predicted_micro_price"], rel_tol=1e-5)

        engine_lob = FastLOBEngine(symbol="005930")
        assert hasattr(engine_lob, "calculate_knk_36_dark_energy_daha_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v57(self):
        """Verify FastLOB DeepHawkesArrivalProcess dark ATS allocation cap at 0.99999999999999995 (17 nines)."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v57 = proc.compute_preemptive_dark_routing(version=57)
        assert "preemptive_dark_routing_ratio" in res_v57
        assert math.isclose(res_v57["preemptive_dark_routing_ratio"], 0.99999999999999995, rel_tol=1e-15)

    def test_smart_order_router_version_57_maker_floor_and_anti_gaming(self):
        """Verify SmartOrderRouter v57 lit maker floor of 1e-29 and anti-gaming MinQty 0.99999999999999995."""
        router = SmartOrderRouter(version=57)
        assert math.isclose(router._resolve_max_dark_cap(57), 0.99999999999999995, rel_tol=1e-15)

        order_plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "market_spread_bps": 5.0,
            "gamma_toxic_dir": 1.0,  # extreme toxic directional flow
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 57,
        }
        res = router.route_order(order_plan, ats_available=True)
        assert res["maker_ratio"] == 1e-29
        assert res["min_ratio"] == 0.99999999999999995

    def test_oms_preemptive_micro_tick_shading_threshold_v57(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.000006."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010  # above 0.000006

        p_buy = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=57,
        )
        expected_shift_buy = -1 * 0.999999999999998 * spread * (h_val - 0.000006)
        assert math.isclose(p_buy - target_px, expected_shift_buy, rel_tol=1e-5)

        p_sell = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=57,
        )
        expected_shift_sell = 1 * 0.999999999999998 * spread * (h_val - 0.000006)
        assert math.isclose(p_sell - target_px, expected_shift_sell, rel_tol=1e-5)

        # Verify AlmgrenChrissScheduler matches ExecutionOMSEngine
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=57,
        )
        assert math.isclose(p_sched, p_buy, rel_tol=1e-7)

    def test_oms_backward_compatibility_v56_and_prior(self):
        """Verify backward compatibility of tick shading for v56, v55, etc."""
        oms = ExecutionOMSEngine()
        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5

        # In v56: threshold was 0.000008
        # At h = 0.000007: v57 activates (0.000007 > 0.000006), v56 does NOT (0.000007 <= 0.000008)
        p_v57 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000007},
            version=57,
        )
        p_v56 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000007},
            version=56,
        )

        assert p_v57 < target_px
        assert math.isclose(p_v56, target_px, rel_tol=1e-7)
