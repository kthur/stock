"""
tests/test_phase73_oms.py

Unit and integration test suite for Phase 73 Quantitative Alpha Enhancement (Feature F339.1 & F339.2 Microstructure OMS):
- Kerr-Newman-Kiselev 52-Dark-Energy DAHA
  (w = -54/3 = -18.0, k_daha = 0.44, k_monster = 0.43, daha_52_factor = 8.60, c_monster = 5.551115123125783e-17 [2^-54])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 52-fold dark energy density
  * Repulsive acceleration -27.5 * c * (r ** 54) * daha_52_factor
  * Metric distortion
  * Charge acceleration
  * 16 method aliases on FastOrderBookMatchingEngine and FastLOBEngine
- SmartOrderRouter version=73:
  * Lit maker ratio floor contracted to 1e-45
  * 45-decimal rounding precision for maker_ratio and min_ratio
  * Cascading version flags: is_phase73 -> is_phase72 -> is_phase71
- Preemptive micro-tick shading at h > 0.00000006:
  hawkes_shift = -direction * 0.99999999999999999999999999 * spr * (h - 0.00000006)
- Full backward compatibility with Phase 72 and earlier.
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


class TestPhase73MicrostructureOMS:
    """Test suite for Phase 73 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_52_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 52-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_52_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_52_dark_energy_correction" in res
        assert "knk_52_dark_energy_daha_acceleration" in res
        assert "phase73_knk_acceleration" in res

        assert math.isfinite(res["knk_52_dark_energy_correction"])
        assert math.isfinite(res["knk_52_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_52_factor"], 8.60, rel_tol=1e-5)
        assert math.isclose(res["k_daha_52"], 0.44, rel_tol=1e-5)
        assert math.isclose(res["k_monster_52"], 0.43, rel_tol=1e-5)
        assert math.isclose(res["c_monster_52"], 5.551115123125783e-17, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_52"], -18.0, rel_tol=1e-5)

    def test_kerr_newman_kiselev_52_aliases(self):
        """Verify aliases on FastOrderBookMatchingEngine for KNK-52."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_52_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        assert engine.compute_phase73_lob_acceleration() == ref
        assert engine.phase73_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_52_dark_energy_acceleration() == ref
        assert engine.compute_kerr_newman_kiselev_52_dark_energy_acceleration() == ref
        assert engine.phase73_daha_l3_acceleration() == ref
        assert engine.knk_52_dark_energy_daha_l3() == ref
        assert engine.daha_l3_phase73_acceleration() == ref
        assert engine.phase73_dark_energy_acceleration() == ref
        assert engine.calculate_phase73_knk_acceleration() == ref
        assert engine.compute_knk_phase73_acceleration() == ref
        assert engine.daha_phase73_acceleration() == ref
        assert engine.phase73_spacetime_hydrodynamics() == ref
        assert engine.phase73_queue_acceleration() == ref
        assert engine.l3_phase73_acceleration() == ref
        assert engine.phase73_knk_acceleration() == ref
        assert engine.compute_phase73_knk_daha_queue_acceleration() == ref

        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_52_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase73_lob_acceleration")
        assert hasattr(flob, "phase73_queue_acceleration")

    def test_smart_order_router_version_73_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 73."""
        sor = SmartOrderRouter(version=73)
        assert sor.version == 73
        assert sor.is_phase73 is True
        assert sor.is_phase72 is True
        assert sor.is_phase71 is True
        assert sor.is_phase70 is True
        assert sor.is_phase69 is True
        assert sor.is_phase68 is True

        order_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 73,
        }
        res = sor.route_order(order_plan)
        assert res["maker_ratio"] >= 1e-45
        assert res["maker_ratio"] <= 1e-35

    def test_smart_order_router_phase73_floor_contraction(self):
        """Verify Phase 73 lit maker floor contracts to 1e-45 vs 1e-44 in Phase 72."""
        sor73 = SmartOrderRouter(version=73)
        sor72 = SmartOrderRouter(version=72)

        order_plan_73 = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 73,
        }
        order_plan_72 = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 72,
        }

        res73 = sor73.route_order(order_plan_73)
        res72 = sor72.route_order(order_plan_72)

        assert res73["maker_ratio"] == 1e-45
        assert res72["maker_ratio"] == 1e-44
        assert res73["maker_ratio"] < res72["maker_ratio"]

    def test_oms_and_scheduler_phase73_shading(self):
        """Verify ExecutionOMSEngine and AlmgrenChrissScheduler preemptive micro-tick shading under Phase 73."""
        # Test sub-threshold for v72 (h = 0.00000007), which triggers v73 (h > 0.00000006)
        oms_p73_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=73,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000007}
        )
        oms_p72_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=72,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000007}
        )
        # v73 should trigger tick shading (buying lower) while v72 remains unshaded
        assert oms_p73_sub < oms_p72_sub

        # Test above-threshold for both (h = 0.0000010)
        oms_p73 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=73,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        oms_p72 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=72,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert oms_p73 <= oms_p72

        sched = AlmgrenChrissScheduler()
        sched_p73_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=73,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000007}
        )
        sched_p72_sub = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=72,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000007}
        )
        assert sched_p73_sub < sched_p72_sub

        sched_p73 = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=73,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert sched_p73 <= oms_p72

    def test_strict_backward_compatibility_v72_and_prior(self):
        """Verify strict backward compatibility with Phase 72 and earlier versions."""
        sor72 = SmartOrderRouter(version=72)
        assert sor72.is_phase72 is True
        assert sor72.is_phase73 is False

        sor71 = SmartOrderRouter(version=71)
        assert sor71.is_phase71 is True
        assert sor71.is_phase72 is False
        assert sor71.is_phase73 is False

        sor70 = SmartOrderRouter(version=70)
        assert sor70.is_phase70 is True
        assert sor70.is_phase71 is False
        assert sor70.is_phase72 is False
        assert sor70.is_phase73 is False

        # Phase 72 unshaded behavior preserved
        unshaded_p72 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=72,
            hawkes_intensity={"cross_excitation_toxicity": 0.00000007}
        )
        baseline_p72 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=72,
            hawkes_intensity={"cross_excitation_toxicity": 0.0}
        )
        assert math.isclose(unshaded_p72, baseline_p72, rel_tol=1e-7)

    def test_fast_lob_dark_energy_numerical_stability(self):
        """Verify numerical stability of KNK-52 Dark Energy DAHA under extreme queue sizes."""
        engine = FastOrderBookMatchingEngine(symbol="TSLA")
        engine.add_limit_order("bid_1", "BUY", 200.0, 1e8)
        engine.add_limit_order("ask_1", "SELL", 200.1, 1e-3)

        res = engine.compute_kerr_newman_kiselev_52_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.99,
            spin_parameter=0.99,
        )
        assert math.isfinite(res["knk_52_dark_energy_correction"])
        assert math.isfinite(res["knk_52_dark_energy_daha_acceleration"])
        assert -1e6 <= res["knk_52_dark_energy_correction"] <= 1e6
