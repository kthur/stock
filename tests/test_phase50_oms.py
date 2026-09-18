"""
tests/test_phase50_oms.py

Unit and integration test suite for Phase 50 Quantitative Enhancement (Feature F224.1 & F224.2 Microstructure OMS):
- Kerr-Newman-Kiselev 29-Dark-Energy PCQTGBDDDDHKMAEETUVWXYZ DAHA
  (w = -31/3, k_daha = 0.21, k_monster = 0.20, daha_29_factor = 3.12, c_monster = 0.000000000390625)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 29-fold dark energy density
  * Outer cosmological horizon scale
  * Radial tidal force with 29-fold dark energy repulsive acceleration (-15.5 * c * r^30)
  * Hydrodynamic queue acceleration and micro-price prediction
  * Complete method aliases on FastOrderBookMatchingEngine (27 aliases)
- Fast LOB 99.999999999999% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=50:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999999999999 (99.999999999999%).
  * Lit maker ratio floor contracted to 1e-22 (0.0000000000000000000001)
    via 0.70 * (1.0 - 0.9999999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.999999999999% (0.99999999999999).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.00005:
  hawkes_shift = -direction * 0.9999999999995 * spr * (h - 0.00005).
- Full backward compatibility across Phase 14 through Phase 49 versions.
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


class TestPhase50MicrostructureOMS:
    """Test suite for Phase 50 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_29_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 29-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_29_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert math.isfinite(res["queue_acceleration"])
        assert math.isfinite(res["predicted_micro_price"])

    def test_kerr_newman_kiselev_29_dark_energy_aliases(self):
        """Verify all 27 aliases of 29-dark-energy DAHA on FastOrderBookMatchingEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(5):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 500.0)

        ref = engine.compute_kerr_newman_kiselev_29_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        for alias_fn in [
            engine.compute_kerr_newman_kiselev_29_dark_energy_daha_queue_acceleration,
            engine.calculate_kerr_newman_kiselev_29_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            engine.compute_knk_29_dark_energy_daha_queue_acceleration,
            engine.compute_knk_29_dark_energy_queue_acceleration,
            engine.compute_knk_borcherds_moonshine_monster_29_dark_energy_daha_queue_acceleration,
            engine.compute_kerr_newman_kiselev_29_dark_energy_moonshine_monster_queue_acceleration,
            engine.compute_knk_29_dark_energy_monster_moonshine_queue_acceleration,
            engine.compute_phase50_queue_acceleration,
            engine.compute_phase50_knk_daha_queue_acceleration,
            engine.compute_phase50_lob_hydrodynamics,
            engine.compute_phase50_lob_acceleration,
            engine.compute_knk_daha_order50_queue_acceleration,
            engine.compute_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_whittaker_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_virasoro_whittaker_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_universal_virasoro_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_elliptic_hypergeometric_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_askey_wilson_elliptic_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_macdonald_askey_wilson_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_kostka_macdonald_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_cherednik_kostka_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_hecke_cherednik_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_dunkl_hecke_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_dirac_dunkl_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_dilaton_dirac_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_brane_dilaton_borcherds_moonshine_monster_daha_order50_queue_acceleration,
            engine.compute_daha_29_queue_acceleration,
        ]:
            out = alias_fn()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)
            assert math.isclose(out["predicted_micro_price"], ref["predicted_micro_price"], rel_tol=1e-5)

    def test_preemptive_dark_routing_cap_version_50(self):
        """Verify dark routing allocation cap reaches 0.99999999999999 under version 50."""
        proc = DeepHawkesArrivalProcess()
        proc.lambda_state = np.array([15.0, 0.5, 0.2])
        res_v50 = proc.compute_preemptive_dark_routing(version=50)
        assert "preemptive_dark_routing_ratio" in res_v50
        assert math.isclose(res_v50["preemptive_dark_routing_ratio"], 0.99999999999999, rel_tol=1e-12)

    def test_smart_order_router_dark_cap_and_maker_floor_version_50(self):
        """Verify SmartOrderRouter dark cap 0.99999999999999 and lit maker floor 1e-22 under version 50."""
        router = SmartOrderRouter(version=50)
        assert math.isclose(router._resolve_max_dark_cap(50), 0.99999999999999, rel_tol=1e-12)

        order_plan = {
            "symbol": "005930",
            "quantity": 1000000,
            "action": "BUY",
            "target_price": 70000.0,
            "market_spread_bps": 5.0,
            "gamma_toxic_dir": 1.0,  # extreme toxic directional flow
            "destination": {"venue": "KRX_ATS_NEXTRADE"},
            "version": 50,
        }
        res = router.route_order(order_plan, ats_available=True)
        assert res["maker_ratio"] == 1e-22
        assert res["min_ratio"] == 0.99999999999999

    def test_preemptive_micro_tick_shading_version_50(self):
        """Verify micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.00005."""
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spread = ask_px - bid_px
        h_val = 0.00010  # above 0.00005

        p_buy = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=50,
        )
        # Shift should be negative for BUY (shade down to avoid adverse selection)
        expected_shift = -1 * 0.9999999999995 * spread * (h_val - 0.00005)
        assert math.isclose(p_buy - target_px, expected_shift, rel_tol=1e-5)

        p_buy_sched = scheduler.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=50,
        )
        assert math.isclose(p_buy_sched - target_px, expected_shift, rel_tol=1e-5)

    def test_backward_compatibility_version_49_and_prior(self):
        """Verify backward compatibility for version 49 and 48 in SmartOrderRouter and OMS."""
        router = SmartOrderRouter()
        assert math.isclose(router._resolve_max_dark_cap(49), 0.99999999999998, rel_tol=1e-12)
        assert math.isclose(router._resolve_max_dark_cap(48), 0.99999999999995, rel_tol=1e-12)

        oms = ExecutionOMSEngine()
        p_v49 = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00010},
            version=49,
        )
        exp_v49 = -1 * 0.999999999999 * 1.0 * (0.00010 - 0.00006)
        assert math.isclose(p_v49 - 100.0, exp_v49, rel_tol=1e-5)
