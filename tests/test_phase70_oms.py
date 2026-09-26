"""
tests/test_phase70_oms.py

Unit and integration test suite for Phase 70 Quantitative Alpha Enhancement (Feature F324.1 & F324.2 Microstructure OMS):
- Kerr-Newman-Kiselev 49-Dark-Energy DAHA
  (w = -51/3, k_daha = 0.41, k_monster = 0.40, daha_49_factor = 7.85, c_monster = 4.440892098500626e-16)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 49-fold dark energy density
  * Repulsive acceleration -26.0 * c * (r ** 51) * daha_49_factor
  * Metric distortion
  * Charge acceleration
- SmartOrderRouter version=70:
  * Lit maker ratio floor contracted to 1e-42
  * Dark ATS cap 0.99999999999999999999995 (23 decimals)
  * Anti-gaming MinQty 0.99999999999999999999995
- Preemptive micro-tick shading at h > 0.00000015:
  hawkes_shift = -direction * 0.99999999999999999999999 * spr * (h - 0.00000015)
- Full backward compatibility with Phase 69 and earlier.
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


class TestPhase70MicrostructureOMS:
    """Test suite for Phase 70 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_49_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 49-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_49_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_49_dark_energy_correction" in res
        assert "knk_49_dark_energy_daha_acceleration" in res
        assert "phase70_knk_acceleration" in res

        assert math.isfinite(res["knk_49_dark_energy_correction"])
        assert math.isfinite(res["knk_49_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_49_factor"], 7.85, rel_tol=1e-5)
        assert math.isclose(res["k_daha_49"], 0.41, rel_tol=1e-5)
        assert math.isclose(res["k_monster_49"], 0.40, rel_tol=1e-5)
        assert math.isclose(res["c_monster_49"], 4.440892098500626e-16, rel_tol=1e-9)

    def test_kerr_newman_kiselev_49_aliases(self):
        """Verify aliases on FastOrderBookMatchingEngine for KNK-49."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_49_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        assert engine.compute_phase70_lob_acceleration() == ref
        assert engine.phase70_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_49_dark_energy_acceleration() == ref

        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_49_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase70_lob_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v70(self):
        """Verify Fast LOB preemptive dark routing cap under version 70."""
        proc = DeepHawkesArrivalProcess(version=70)
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res = proc.compute_preemptive_dark_routing()
        assert res["preemptive_dark_routing_ratio"] >= 0.99999999999999999999995 - 1e-15

        proc_default = DeepHawkesArrivalProcess()
        proc_default.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v70 = proc_default.compute_preemptive_dark_routing(version=70)
        assert res_v70["preemptive_dark_routing_ratio"] >= 0.99999999999999999999995 - 1e-15

    def test_smart_order_router_version_70_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 70."""
        sor = SmartOrderRouter(version=70)
        assert sor.version == 70
        assert sor.is_phase70 is True
        assert sor.is_phase69 is True
        assert sor.is_phase68 is True
        assert sor.is_phase67 is True
        assert sor.is_phase66 is True

        order_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "gamma_toxic_dir": 1.0,
            "version": 70,
        }
        res = sor.route_order(order_plan)
        assert res["maker_ratio"] >= 1e-42
        assert res["maker_ratio"] <= 1e-35

    def test_oms_and_scheduler_phase70_shading(self):
        """Verify ExecutionOMSEngine and AlmgrenChrissScheduler preemptive micro-tick shading under Phase 70."""
        oms_p70 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=70,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        oms_p69 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=69,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert oms_p70 <= oms_p69

        sched = AlmgrenChrissScheduler()
        sched_p70 = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=70,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert sched_p70 <= oms_p69

    def test_strict_backward_compatibility_v69_and_prior(self):
        """Verify strict backward compatibility with Phase 69 and earlier versions."""
        sor69 = SmartOrderRouter(version=69)
        assert sor69.is_phase69 is True
        assert sor69.is_phase70 is False

        sor68 = SmartOrderRouter(version=68)
        assert sor68.is_phase68 is True
        assert sor68.is_phase69 is False
        assert sor68.is_phase70 is False
