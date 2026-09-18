"""
tests/test_phase49_oms.py

Unit and integration test suite for Phase 49 Quantitative Enhancement (Feature F219.1 & F219.2 Microstructure OMS):
- Kerr-Newman-Kiselev 28-Dark-Energy PCQTGBDDDDHKMAEETUVWXYZ DAHA
  (w = -10.0 = -30/3, k_daha = 0.20, k_monster = 0.19, daha_28_factor = 2.92, c_monster = 0.00000000078125)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 28-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 28-fold dark energy repulsive acceleration (-15.0 * c * r^29)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.999999999998% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=49:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999999999998 (99.999999999998%).
  * Lit maker ratio floor contracted to 1e-21 (0.000000000000000000001)
    via 0.70 * (1.0 - 0.999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.999999999998% (0.99999999999998).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.00006:
  hawkes_shift = -direction * 0.999999999999 * spr * (h - 0.00006).
- Full backward compatibility across Phase 14 through Phase 48 versions.
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


class TestPhase49MicrostructureOMS:
    """Test suite for Phase 49 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_28_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 28-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_28_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])

    def test_kerr_newman_kiselev_28_dark_energy_aliases(self):
        """Verify all 21+ aliases of 28-dark-energy DAHA on FastOrderBookMatchingEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_28_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        for alias_fn in [
            engine.compute_kerr_newman_kiselev_28_dark_energy_daha_queue_acceleration,
            engine.calculate_kerr_newman_kiselev_28_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            engine.compute_knk_28_dark_energy_daha_queue_acceleration,
            engine.compute_knk_28_dark_energy_queue_acceleration,
            engine.compute_knk_borcherds_moonshine_monster_28_dark_energy_daha_queue_acceleration,
            engine.compute_kerr_newman_kiselev_28_dark_energy_moonshine_monster_queue_acceleration,
            engine.compute_knk_28_dark_energy_monster_moonshine_queue_acceleration,
            engine.compute_phase49_queue_acceleration,
            engine.compute_phase49_knk_daha_queue_acceleration,
            engine.compute_phase49_lob_hydrodynamics,
            engine.compute_phase49_lob_acceleration,
            engine.compute_knk_daha_order49_queue_acceleration,
            engine.compute_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_whittaker_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_virasoro_whittaker_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_universal_virasoro_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_elliptic_hypergeometric_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_askey_wilson_elliptic_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_macdonald_askey_wilson_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_kostka_macdonald_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_cherednik_kostka_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_hecke_cherednik_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_dunkl_hecke_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_dirac_dunkl_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_dilaton_dirac_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_brane_dilaton_borcherds_moonshine_monster_daha_order49_queue_acceleration,
            engine.compute_daha_28_queue_acceleration,
        ]:
            out = alias_fn()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(out["predicted_micro_price"], ref["predicted_micro_price"], rel_tol=1e-5)

    def test_preemptive_dark_routing_cap_version_49(self):
        """Verify dark routing allocation cap reaches 0.99999999999998 under version 49."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([15.0, 0.5, 0.2])
        res_v49 = proc.compute_preemptive_dark_routing(version=49)
        assert "preemptive_dark_routing_ratio" in res_v49
        assert math.isclose(res_v49["preemptive_dark_routing_ratio"], 0.99999999999998, rel_tol=1e-12)

    def test_smart_order_router_dark_cap_and_maker_floor_version_49(self):
        """Verify SmartOrderRouter dark cap 0.99999999999998 and lit maker floor 1e-21 under version 49."""
        router = SmartOrderRouter(version=49)
        assert math.isclose(router._resolve_max_dark_cap(49), 0.99999999999998, rel_tol=1e-12)

        order_plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "market_spread_bps": 5.0,
            "gamma_toxic_dir": 1.0,  # extreme toxic directional flow
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 49,
        }
        res = router.route_order(order_plan, ats_available=True)
        assert res["maker_ratio"] == 1e-21
        assert res["min_ratio"] == 0.99999999999998

    def test_preemptive_micro_tick_shading_version_49(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.00006."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010  # above 0.00006

        p_buy = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=49,
        )
        # Shift should be negative for BUY (shade down to avoid adverse selection)
        expected_shift = -1 * 0.999999999999 * spread * (h_val - 0.00006)
        assert math.isclose(p_buy - target_px, expected_shift, rel_tol=1e-5)

        p_buy_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=49,
        )
        assert math.isclose(p_buy_sched - target_px, expected_shift, rel_tol=1e-5)

    def test_backward_compatibility_v48_and_prior(self):
        """Verify backward compatibility of Hawkes shading for v48."""
        oms = ExecutionOMSEngine()
        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010

        p_v48 = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=48,
        )
        expected_v48_shift = -1 * 0.999999999998 * spread * (h_val - 0.00008)
        assert math.isclose(p_v48 - target_px, expected_v48_shift, rel_tol=1e-5)
