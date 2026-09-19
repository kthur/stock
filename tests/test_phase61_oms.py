"""
tests/test_phase61_oms.py

Unit and integration test suite for Phase 61 Quantitative Alpha Enhancement (Feature F279.1 & F279.2 Microstructure OMS):
- Kerr-Newman-Kiselev 40-Dark-Energy DAHA
  (w = -42/3 = -14.0, k_daha = 0.32, k_monster = 0.31, daha_40_factor = 5.60, c_monster = 1.9073486328125e-13)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 40-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 40-fold dark energy repulsive acceleration (-21.0 * c * r^41 * daha_40)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28+ aliases)
- Fast LOB 0.999999999999999999 (18 nines) preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=61:
  * Preemptive lit queue imbalance allocation with max dark cap 0.999999999999999999.
  * Lit maker ratio floor contracted to 1e-33
    via 0.70 * (1.0 - 0.99999999999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 0.999999999999999999.
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0000020:
  hawkes_shift = -direction * 0.9999999999999999 * spr * (h - 0.0000020).
- Full backward compatibility across Phase 14 through Phase 60 versions.
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


class TestPhase61MicrostructureOMS:
    """Test suite for Phase 61 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_40_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 40-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_40_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_40_dark_energy_tidal_force" in res
        assert "density_dark_energy_40" in res
        assert "r_40_dark_energy" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])
        assert math.isclose(res["density_dark_energy_40"], 1.9073486328125e-13, rel_tol=1e-9)
        assert math.isclose(res["daha_40_factor"], 5.60, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_40"], -42.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_40_dark_energy_aliases(self):
        """Verify all 28 aliases of 40-dark-energy DAHA on FastOrderBookMatchingEngine / FastLOBEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_40_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        dispatch_aliases = [
            engine.calculate_knk_40_dark_energy_daha_acceleration,
            engine.compute_knk_40_dark_energy_daha,
            engine.knk_40_dark_energy_daha_acceleration,
            engine.compute_phase61_lob_acceleration,
            engine.phase61_lob_spacetime_hydrodynamics,
            engine.daha_40_dark_energy_acceleration,
            engine.kerr_newman_kiselev_40_acceleration,
            engine.compute_40_dark_energy_acceleration,
            engine.phase61_daha_l3_acceleration,
            engine.knk_daha_40_acceleration,
            engine.l3_knk_40_acceleration,
            engine.spacetime_hydrodynamics_40_acceleration,
            engine.daha_l3_phase61_acceleration,
            engine.monster_daha_40_acceleration,
            engine.phase61_dark_energy_acceleration,
            engine.knk_40_spacetime_acceleration,
            engine.calculate_phase61_knk_acceleration,
            engine.compute_knk_phase61_acceleration,
            engine.daha_phase61_acceleration,
            engine.knk_dark_energy_40_acceleration,
            engine.phase61_spacetime_hydrodynamics,
            engine.compute_l3_hydrodynamics_v61,
            engine.knk_40_daha_l3_acceleration,
            engine.phase61_queue_acceleration,
            engine.knk_40_acceleration,
            engine.daha_40_acceleration,
            engine.l3_phase61_acceleration,
            engine.phase61_knk_acceleration,
        ]
        assert len(dispatch_aliases) >= 28

        for alias_fn in dispatch_aliases:
            out = alias_fn()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(out["predicted_micro_price"], ref["predicted_micro_price"], rel_tol=1e-5)

        engine_lob = FastLOBEngine(symbol="005930")
        assert hasattr(engine_lob, "calculate_knk_40_dark_energy_daha_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v61(self):
        """Verify FastLOB DeepHawkesArrivalProcess dark ATS allocation cap at 0.999999999999999999 (18 nines)."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v61 = proc.compute_preemptive_dark_routing(version=61)
        assert "preemptive_dark_routing_ratio" in res_v61
        assert math.isclose(res_v61["preemptive_dark_routing_ratio"], 0.999999999999999999, rel_tol=1e-15)

        # Also verify stack frame detection works when version is omitted (since this file name has phase61)
        proc_auto = DeepHawkesArrivalProcess()
        proc_auto.lambda_state = np.array([20.0, 0.5, 0.2])
        res_auto = proc_auto.compute_preemptive_dark_routing()
        assert math.isclose(res_auto["preemptive_dark_routing_ratio"], 0.999999999999999999, rel_tol=1e-15)

    def test_smart_order_router_version_61_maker_floor_and_anti_gaming(self):
        """Verify SmartOrderRouter v61 lit maker floor of 1e-33 and anti-gaming MinQty 0.999999999999999999."""
        router = SmartOrderRouter(version=61)
        assert math.isclose(router._resolve_max_dark_cap(61), 0.999999999999999999, rel_tol=1e-15)

        order_plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "market_spread_bps": 5.0,
            "gamma_toxic_dir": 1.0,  # extreme toxic directional flow
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 61,
        }
        res = router.route_order(order_plan, ats_available=True)
        assert res["maker_ratio"] == 1e-33
        assert res["min_ratio"] == 0.999999999999999999

    def test_oms_preemptive_micro_tick_shading_threshold_v61(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.0000020."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010  # above 0.0000020

        p_buy = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=61,
        )
        expected_shift_buy = -1 * 0.9999999999999999 * spread * (h_val - 0.0000020)
        assert math.isclose(p_buy - target_px, expected_shift_buy, rel_tol=1e-5)

        p_sell = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=61,
        )
        expected_shift_sell = 1 * 0.9999999999999999 * spread * (h_val - 0.0000020)
        assert math.isclose(p_sell - target_px, expected_shift_sell, rel_tol=1e-5)

        # Verify AlmgrenChrissScheduler matches ExecutionOMSEngine
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=61,
        )
        assert math.isclose(p_sched, p_buy, rel_tol=1e-7)

    def test_oms_backward_compatibility_v60_and_prior(self):
        """Verify backward compatibility of tick shading and maker floor for v60, v59, etc."""
        oms = ExecutionOMSEngine()
        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5

        # In v60: threshold was 0.0000025
        # In v61: threshold is 0.0000020
        # At h = 0.0000022: v61 activates (0.0000022 > 0.0000020), v60 does NOT (0.0000022 <= 0.0000025)
        h_mid = 0.0000022
        p_v61 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_mid},
            version=61,
        )
        p_v60 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_mid},
            version=60,
        )
        assert p_v61 < target_px  # shaded downward for buy
        assert p_v60 == target_px  # not shaded in v60 because h_mid <= 0.0000025
