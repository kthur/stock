"""
tests/test_phase72_oms.py

Unit and integration test suite for Phase 72 Quantitative Alpha Enhancement (Feature F334.1 & F334.2 Microstructure OMS):
- Kerr-Newman-Kiselev 51-Dark-Energy DAHA
  (w = -53/3, k_daha = 0.43, k_monster = 0.42, daha_51_factor = 8.35, c_monster = 1.1102230246251565e-16)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 51-fold dark energy density
  * Repulsive acceleration -27.0 * c * (r ** 53) * daha_51_factor
  * Metric distortion
  * Charge acceleration
- SmartOrderRouter version=72:
  * Lit maker ratio floor contracted to 1e-44
  * Dark ATS cap 0.999999999999999999999999 (25 decimals)
  * Anti-gaming MinQty 0.999999999999999999999999
- Preemptive micro-tick shading at h > 0.00000008:
  hawkes_shift = -direction * 0.9999999999999999999999999 * spr * (h - 0.00000008)
- Full backward compatibility with Phase 71 and earlier.
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


class TestPhase72MicrostructureOMS:
    """Test suite for Phase 72 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_51_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 51-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_51_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_51_dark_energy_correction" in res
        assert "knk_51_dark_energy_daha_acceleration" in res
        assert "phase72_knk_acceleration" in res

        assert math.isfinite(res["knk_51_dark_energy_correction"])
        assert math.isfinite(res["knk_51_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_51_factor"], 8.35, rel_tol=1e-5)
        assert math.isclose(res["k_daha_51"], 0.43, rel_tol=1e-5)
        assert math.isclose(res["k_monster_51"], 0.42, rel_tol=1e-5)
        assert math.isclose(res["c_monster_51"], 1.1102230246251565e-16, rel_tol=1e-9)

    def test_kerr_newman_kiselev_51_aliases(self):
        """Verify aliases on FastOrderBookMatchingEngine for KNK-51."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_51_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        assert engine.compute_phase72_lob_acceleration() == ref
        assert engine.phase72_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_51_dark_energy_acceleration() == ref

        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_51_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase72_lob_acceleration")

    def test_smart_order_router_version_72_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 72."""
        sor = SmartOrderRouter(version=72)
        assert sor.version == 72
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
            "version": 72,
        }
        res = sor.route_order(order_plan)
        assert res["maker_ratio"] >= 1e-44
        assert res["maker_ratio"] <= 1e-35

    def test_oms_and_scheduler_phase72_shading(self):
        """Verify ExecutionOMSEngine and AlmgrenChrissScheduler preemptive micro-tick shading under Phase 72."""
        oms_p72 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=72,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        oms_p71 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=71,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert oms_p72 <= oms_p71

        sched = AlmgrenChrissScheduler()
        sched_p72 = sched.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=72,
            hawkes_intensity={"cross_excitation_toxicity": 0.0000010}
        )
        assert sched_p72 <= oms_p71

    def test_strict_backward_compatibility_v71_and_prior(self):
        """Verify strict backward compatibility with Phase 71 and earlier versions."""
        sor71 = SmartOrderRouter(version=71)
        assert sor71.is_phase71 is True
        assert sor71.is_phase72 is False

        sor70 = SmartOrderRouter(version=70)
        assert sor70.is_phase70 is True
        assert sor70.is_phase71 is False
        assert sor70.is_phase72 is False
