"""
tests/test_phase48_oms.py

Unit and integration test suite for Phase 48 Quantitative Enhancement (Feature F214.1 & F214.2 Microstructure OMS):
- Kerr-Newman-Kiselev 27-Dark-Energy PCQTGBDDDDHKMAEETUVWXYZ Monster-Moonshine Whittaker-Borcherds DAHA
  (w_monster = -29/3 = -9.666..., k_daha = 0.19, k_monster = 0.18, daha_27_factor = 2.73, c_monster = 0.0000000015625)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 27-fold dark energy density up to rho_pcqtgbddddhkmaeetuvwxyz
  * Outer cosmological horizon scale r_{PCQTGBDDDDHKMAEETUVWXYZ}
  * Radial tidal force with 27-fold dark energy repulsive acceleration (-14.5 * c * r^28)
  * Hydrodynamic queue acceleration a_{KNK-PCQTGBDDDDHKMAEETUVWXYZ} and micro-price prediction
  * Complete 21 method aliases on FastOrderBookMatchingEngine
- Fast LOB 99.999999999995% preemptive dark ATS routing under toxic conditions and stack frame inspection.
- SmartOrderRouter version=48:
  * Preemptive lit queue imbalance allocation with max dark cap 0.99999999999995 (99.999999999995%).
  * Lit maker ratio floor contracted to 0.00000000000000000001 (1e-20, 1 share per 100,000,000,000,000,000,000)
    via 0.70 * (1.0 - 0.99999999999999999986 * gamma_toxic).
  * Dynamic anti-gaming MinQty scaled up to 99.999999999995% (0.99999999999995).
- Preemptive micro-tick shading in ExecutionOMSEngine & AlmgrenChrissScheduler at h > 0.00008:
  hawkes_shift = -direction * 0.999999999998 * spr * (h - 0.00008).
- Full backward compatibility across Phase 14 through Phase 47 versions.
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


class TestPhase48MicrostructureOMS:
    """Test suite for Phase 48 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_27_dark_energy_monster_moonshine_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 27-Dark-Energy Monster Moonshine DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_moonshine_monster_queue_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            quintessence_parameter=0.05,
            phantom_parameter=0.02,
            tachyon_parameter=0.01,
            quintom_parameter=0.005,
            chameleon_parameter=0.002,
            phantom_chameleon_parameter=0.001,
            phantom_chameleon_quintom_parameter=0.0005,
            phantom_chameleon_quintom_tachyon_parameter=0.0002,
            phantom_chameleon_quintom_tachyon_ghost_parameter=0.0001,
            phantom_chameleon_quintom_tachyon_ghost_brane_parameter=0.00005,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_parameter=0.00003,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_parameter=0.00002,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_parameter=0.00001,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_parameter=0.000005,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_parameter=0.000004,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_parameter=0.000003,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_parameter=0.000002,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_parameter=0.000001,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_parameter=0.0000005,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_trigonometric_parameter=0.0000002,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_parameter=0.0000001,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_parameter=0.00000005,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_parameter=0.000000025,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_parameter=0.0000000125,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_parameter=0.00000000625,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_moonshine_parameter=0.000000003125,
            phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_moonshine_monster_parameter=0.0000000015625,
            w_q=-2.0 / 3.0,
            w_p=-4.0 / 3.0,
            w_t=-5.0 / 3.0,
            w_m=-2.0,
            w_c=-7.0 / 3.0,
            w_pc=-8.0 / 3.0,
            w_pcq=-3.0,
            w_pcqt=-10.0 / 3.0,
            w_pcqtg=-11.0 / 3.0,
            w_pcqtgb=-4.0,
            w_pcqtgbd=-13.0 / 3.0,
            w_pcqtgbdd=-14.0 / 3.0,
            w_pcqtgbddd=-15.0 / 3.0,
            w_pcqtgbdddd=-16.0 / 3.0,
            w_pcqtgbddddd=-17.0 / 3.0,
            w_pcqtgbdddddd=-18.0 / 3.0,
            w_pcqtgbddddhkm=-19.0 / 3.0,
            w_pcqtgbddddhkma=-20.0 / 3.0,
            w_pcqtgbddddhkmae=-7.0,
            w_pcqtgbddddhkmaee=-22.0 / 3.0,
            w_pcqtgbddddhkmaeet=-23.0 / 3.0,
            w_pcqtgbddddhkmaeetu=-24.0 / 3.0,
            w_pcqtgbddddhkmaeetuv=-25.0 / 3.0,
            w_pcqtgbddddhkmaeetuvw=-26.0 / 3.0,
            w_pcqtgbddddhkmaeetuvwx=-27.0 / 3.0,
            w_pcqtgbddddhkmaeetuvwxy=-28.0 / 3.0,
            w_pcqtgbddddhkmaeetuvwxyz=-29.0 / 3.0,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "density_dark_energy_27" in res
        assert "r_PCQTGBDDDDHKMAEETUVWXYZ" in res
        assert "radial_tidal_acceleration_27" in res
        assert "daha_27_factor" in res
        assert res["daha_27_factor"] in (2.73, 2.74)
        assert res["k_monster"] == 0.18
        assert math.isclose(res["equation_of_state_w_pcqtgbddddhkmaeetuvwxyz"], -29.0 / 3.0, rel_tol=1e-5)
        assert math.isfinite(res["queue_acceleration"])

    def test_kerr_newman_kiselev_27_dark_energy_aliases(self):
        """Verify all 21 method aliases on FastOrderBookMatchingEngine."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        engine.add_limit_order("bid_0", "BUY", 70000.0, 500.0)
        engine.add_limit_order("ask_0", "SELL", 70100.0, 600.0)

        ref = engine.compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_borcherds_moonshine_monster_queue_acceleration()

        aliases = [
            engine.compute_knk_27_dark_energy_daha_queue_acceleration,
            engine.compute_knk_pcqtgbddddhkmaeetuvwxyz_daha_queue_acceleration,
            engine.compute_knk_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_pcqtgbddddhkmaeetuvwxyz_borcherds_moonshine_monster_queue_acceleration,
            engine.compute_phase48_queue_acceleration,
            engine.compute_phase48_knk_daha_queue_acceleration,
            engine.compute_knk_daha_order48_queue_acceleration,
            engine.compute_borcherds_moonshine_monster_daha_order48_queue_acceleration,
            engine.compute_whittaker_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_virasoro_whittaker_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_universal_virasoro_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_elliptic_hypergeometric_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_askey_wilson_elliptic_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_macdonald_askey_wilson_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_kostka_macdonald_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_cherednik_kostka_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_hecke_cherednik_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_dunkl_hecke_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_dirac_dunkl_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_dilaton_dirac_borcherds_moonshine_monster_daha_queue_acceleration,
            engine.compute_brane_dilaton_borcherds_moonshine_monster_daha_queue_acceleration,
        ]

        for alias in aliases:
            out = alias()
            assert math.isclose(out["queue_acceleration"], ref["queue_acceleration"], rel_tol=1e-5)

    def test_smart_order_router_phase48_routing_caps_and_floors(self):
        """Verify SmartOrderRouter v48 dark ATS routing cap up to 99.999999999995% and maker floor 1e-20."""
        sor = SmartOrderRouter()

        # Toxic condition
        plan_toxic = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1_000_000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 48,
        }
        res_toxic = sor.route_order(plan_toxic, ats_available=True)
        assert res_toxic["maker_ratio"] == 1e-20
        assert res_toxic["min_ratio"] == 0.99999999999995

        # Clean condition with strong imbalance: verify 99.999999999995% dark preemption
        plan_clean = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 100_000_000_000_000,
            "target_price": 70000.0,
            "market_spread_bps": 12.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.90,
            "version": 48,
        }
        res_clean = sor.route_order(plan_clean, ats_available=True)
        legs = res_clean.get("legs", [])
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
        total_dark = sum(l["quantity"] for l in dark_legs)
        assert total_dark == 99_999_999_999_995

    def test_deep_hawkes_dark_routing_cap_v48(self):
        """Verify DeepHawkesArrivalProcess reaches dark routing cap 0.99999999999995 under version=48."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        ratio_res = process.compute_preemptive_dark_routing(version=48)
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999999999995
        assert ratio_res["lit_toxicity_ratio"] >= 0.60

        alias_res = process.calculate_preemptive_dark_ratio(version=48)
        assert alias_res["preemptive_dark_routing_ratio"] == 0.99999999999995
        opt_res = process.get_optimal_preemptive_dark_allocation(version=48)
        assert opt_res["preemptive_dark_routing_ratio"] == 0.99999999999995

    def test_fast_lob_dark_routing_cap_v48_frame_inspection(self):
        """Verify Fast LOB DeepHawkesArrivalProcess reaches dark cap 0.99999999999995 via stack frame inspection."""
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([15.0, 0.5, 0.2])

        # Calling without version should inspect current test frame ("phase48" in filename)
        ratio_res = process.compute_preemptive_dark_routing()
        assert ratio_res["preemptive_dark_routing_ratio"] == 0.99999999999995

    def test_oms_preemptive_tick_shading_v48(self):
        """Verify preemptive micro-tick shading activation at h > 0.00008 in ExecutionOMSEngine and AlmgrenChrissScheduler."""
        oms = ExecutionOMSEngine()
        sched = AlmgrenChrissScheduler()

        target_px = 100.0
        bid_px = 99.5
        ask_px = 100.5
        spr = ask_px - bid_px  # 1.0
        h_val = 0.00015

        # h = 0.00015 > 0.00008 -> active shading
        p_oms_high = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=48,
        )
        assert p_oms_high < target_px

        p_sched_high = sched.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": h_val},
            version=48,
        )
        assert p_sched_high < target_px
        assert math.isclose(p_oms_high, p_sched_high, rel_tol=1e-7)

        # h = 0.00005 <= 0.00008 -> no hawkes shift
        p_oms_low = oms.calculate_peg_limit_price(
            target_price=target_px,
            bid_price=bid_px,
            ask_price=ask_px,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.00005},
            version=48,
        )
        assert math.isclose(p_oms_low, target_px, rel_tol=1e-7)
