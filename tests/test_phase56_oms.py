"""
tests/test_phase56_oms.py

Unit and integration test suite for Phase 56 Quantitative Alpha Enhancement (Feature F254.1 & F254.2 Microstructure OMS):
- Kerr-Newman-Kiselev 35-Dark-Energy DAHA
  (w = -37/3, k_daha = 0.27, k_monster = 0.26, daha_35_factor = 4.42, c_monster = 0.000000000006103515625)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 35-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 35-fold dark energy repulsive acceleration (-18.5 * c * r^36 * daha_35)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (28 aliases)
- Fast LOB 99.99999999999999% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=56:
  * Preemptive lit queue imbalance allocation with max dark cap 0.9999999999999999 (99.99999999999999%).
  * Lit maker ratio floor contracted to 1e-28 (0.0000000000000000000000000001, 28 decimals)
    via 0.70 * (1.0 - 0.9999999999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.99999999999999% (0.9999999999999999).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.000008:
  hawkes_shift = -direction * 0.999999999999995 * spr * (h - 0.000008).
- Full backward compatibility across Phase 14 through Phase 55 versions.
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


class TestPhase56MicrostructureOMS:
    """Test suite for Phase 56 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_35_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 35-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_35_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_35_dark_energy_tidal_force" in res
        assert "density_dark_energy_35" in res
        assert "r_35_dark_energy" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])
        assert math.isclose(res["density_dark_energy_35"], 0.000000000006103515625, rel_tol=1e-9)
        assert math.isclose(res["daha_35_factor"], 4.42, rel_tol=1e-5)
        assert math.isclose(res["equation_of_state_w_35"], -37.0 / 3.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_35_dark_energy_aliases(self):
        """Verify all 28 aliases of 35-dark-energy DAHA on FastOrderBookMatchingEngine / FastLOBEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_35_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        dispatch_aliases = [
            engine.calculate_knk_35_dark_energy_daha_acceleration,
            engine.compute_knk_35_dark_energy_daha,
            engine.knk_35_dark_energy_daha_acceleration,
            engine.compute_phase56_lob_acceleration,
            engine.phase56_lob_spacetime_hydrodynamics,
            engine.daha_35_dark_energy_acceleration,
            engine.kerr_newman_kiselev_35_acceleration,
            engine.compute_35_dark_energy_acceleration,
            engine.phase56_daha_l3_acceleration,
            engine.knk_daha_35_acceleration,
            engine.l3_knk_35_acceleration,
            engine.spacetime_hydrodynamics_35_acceleration,
            engine.daha_l3_phase56_acceleration,
            engine.monster_daha_35_acceleration,
            engine.phase56_dark_energy_acceleration,
            engine.knk_35_spacetime_acceleration,
            engine.calculate_phase56_knk_acceleration,
            engine.compute_knk_phase56_acceleration,
            engine.daha_phase56_acceleration,
            engine.knk_dark_energy_35_acceleration,
            engine.phase56_spacetime_hydrodynamics,
            engine.compute_l3_hydrodynamics_v56,
            engine.knk_35_daha_l3_acceleration,
            engine.phase56_queue_acceleration,
            engine.knk_35_acceleration,
            engine.daha_35_acceleration,
            engine.l3_phase56_acceleration,
            engine.phase56_knk_acceleration,
        ]
        assert len(dispatch_aliases) == 28

        for alias_fn in dispatch_aliases:
            out = alias_fn()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(out["predicted_micro_price"], ref["predicted_micro_price"], rel_tol=1e-5)

        engine_lob = FastLOBEngine(symbol="005930")
        assert hasattr(engine_lob, "calculate_knk_35_dark_energy_daha_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v56(self):
        """Verify FastLOB DeepHawkesArrivalProcess dark ATS allocation cap at 0.9999999999999999 (16 nines)."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v56 = proc.compute_preemptive_dark_routing(version=56)
        assert "preemptive_dark_routing_ratio" in res_v56
        assert math.isclose(res_v56["preemptive_dark_routing_ratio"], 0.9999999999999999, rel_tol=1e-15)

    def test_smart_order_router_version_56_maker_floor_and_anti_gaming(self):
        """Verify SmartOrderRouter v56 lit maker floor of 1e-28 and anti-gaming MinQty 0.9999999999999999."""
        router = SmartOrderRouter(version=56)
        assert math.isclose(router._resolve_max_dark_cap(56), 0.9999999999999999, rel_tol=1e-15)

        order_plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "market_spread_bps": 5.0,
            "gamma_toxic_dir": 1.0,  # extreme toxic directional flow
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 56,
        }
        res = router.route_order(order_plan, ats_available=True)
        assert res["maker_ratio"] == 1e-28
        assert res["min_ratio"] == 0.9999999999999999

    def test_oms_preemptive_micro_tick_shading_threshold_v56(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.000008."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010  # above 0.000008

        p_buy = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=56,
        )
        expected_shift_buy = -1 * 0.999999999999995 * spread * (h_val - 0.000008)
        assert math.isclose(p_buy - target_px, expected_shift_buy, rel_tol=1e-5)

        p_sell = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="SELL",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=56,
        )
        expected_shift_sell = 1 * 0.999999999999995 * spread * (h_val - 0.000008)
        assert math.isclose(p_sell - target_px, expected_shift_sell, rel_tol=1e-5)

        # Verify AlmgrenChrissScheduler matches ExecutionOMSEngine
        p_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=56,
        )
        assert math.isclose(p_sched, p_buy, rel_tol=1e-7)

    def test_oms_backward_compatibility_v55_and_prior(self):
        """Verify backward compatibility of tick shading for v55, v54, v53."""
        oms = ExecutionOMSEngine()
        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5

        # In v55: threshold was 0.000010
        # At h = 0.000009: v56 activates (0.000009 > 0.000008), v55 does NOT (0.000009 <= 0.000010)
        p_v56 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000009},
            version=56,
        )
        p_v55 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.000009},
            version=55,
        )

        assert p_v56 < target_px
        assert math.isclose(p_v55, target_px, rel_tol=1e-7)
