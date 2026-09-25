"""
tests/test_phase68_oms.py

Unit and integration test suite for Phase 68 Quantitative Alpha Enhancement (Feature F314.1 & F314.2 Microstructure OMS):
- Kerr-Newman-Kiselev 47-Dark-Energy DAHA
  (w = -49/3, k_daha = 0.39, k_monster = 0.38, daha_47_factor = 7.35, c_monster = 1.4901161193847656e-15)
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 46-fold dark energy density
  * Repulsive acceleration
  * Metric distortion
  * Charge acceleration
- SmartOrderRouter version=68:
  * Lit maker ratio floor contracted to 1e-40
  * Dark ATS cap 0.9999999999999999999995 (21 decimals)
  * Anti-gaming MinQty 0.9999999999999999999995
- Preemptive micro-tick shading at h > 0.0000003:
  hawkes_shift = -direction * 0.999999999999999999999 * spr * (h - 0.0000003)
- Full backward compatibility with Phase 66 and earlier.
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


class TestPhase68MicrostructureOMS:
    """Test suite for Phase 68 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_47_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 47-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        res = engine.compute_kerr_newman_kiselev_47_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_47_dark_energy_correction" in res
        assert "knk_47_dark_energy_daha_acceleration" in res
        assert "phase68_knk_acceleration" in res

        assert math.isfinite(res["knk_47_dark_energy_correction"])
        assert math.isfinite(res["knk_47_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_47_factor"], 7.35, rel_tol=1e-5)
        assert math.isclose(res["k_daha_47"], 0.39, rel_tol=1e-5)
        assert math.isclose(res["k_monster_47"], 0.38, rel_tol=1e-5)
        assert math.isclose(res["c_monster_47"], 1.4901161193847656e-15, rel_tol=1e-9)

    def test_kerr_newman_kiselev_47_aliases(self):
        """Verify aliases on FastOrderBookMatchingEngine for KNK-46."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        ref = engine.compute_kerr_newman_kiselev_47_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        assert engine.compute_phase68_lob_acceleration() == ref
        assert engine.phase68_lob_spacetime_hydrodynamics() == ref
        assert engine.compute_knk_47_dark_energy_acceleration() == ref

        flob = FastLOBEngine(symbol="AAPL")
        assert hasattr(flob, "compute_kerr_newman_kiselev_47_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration")
        assert hasattr(flob, "compute_phase68_lob_acceleration")

    def test_fast_lob_preemptive_dark_routing_cap_v67(self):
        """Verify Fast LOB preemptive dark routing cap under version 67."""
        proc = DeepHawkesArrivalProcess(version=68)
        proc.lambda_state = np.array([20.0, 0.5, 0.2])
        res = proc.compute_preemptive_dark_routing()
        assert res["preemptive_dark_routing_ratio"] >= 0.9999999999999999999995 - 1e-15

        proc_default = DeepHawkesArrivalProcess()
        proc_default.lambda_state = np.array([20.0, 0.5, 0.2])
        res_v67 = proc_default.compute_preemptive_dark_routing(version=68)
        assert res_v67["preemptive_dark_routing_ratio"] >= 0.9999999999999999999995 - 1e-15

    def test_smart_order_router_version_67_properties(self):
        """Verify SmartOrderRouter initialization and routing properties under version 67."""
        sor = SmartOrderRouter(version=68)
        assert sor.version == 68
        assert sor.is_phase68 is True
        assert sor.is_phase66 is True
        assert sor.is_phase64 is True
        assert sor.is_phase63 is True

        plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 150.0,
            "execution_strategy": "DYNAMIC_VWAP",
            "gamma_toxic_dir": 0.95,
            "darkpool_score": 0.70,
            "version": 68,
        }
        res = sor.route_order(plan)
        assert res["toxic_flow_detected"] is True
        assert res["maker_ratio"] <= 0.05
        assert res["min_ratio"] >= 0.90

    def test_smart_order_router_maker_floor_contraction_v67(self):
        """Verify maker floor contracts to 1e-40 under extreme toxicity in Phase 68."""
        sor = SmartOrderRouter(version=68)
        plan = {
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 400.0,
            "gamma_toxic_dir": 1.0,
            "version": 68,
        }
        res = sor.route_order(plan)
        assert res["maker_ratio"] >= 1e-40
        assert res["maker_ratio"] <= 0.01

    def test_oms_engine_phase68_preemptive_micro_tick_shading(self):
        """Verify preemptive micro-tick shading activates at h > 0.0000003."""
        oms = ExecutionOMSEngine()
        target_price = 100.0
        best_bid = 99.95
        best_ask = 100.05

        p_sub = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000003,
            version=68,
        )

        p_above = oms.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000010,
            version=68,
        )

        assert p_above < p_sub, f"BUY limit price should shade downward (p_above={p_above}, p_sub={p_sub})"

    def test_almgren_chriss_phase68_preemptive_micro_tick_shading(self):
        """Verify preemptive micro-tick shading in AlmgrenChrissScheduler at h > 0.0000003."""
        scheduler = AlmgrenChrissScheduler()
        target_price = 100.0
        best_bid = 99.95
        best_ask = 100.05

        p_sub = scheduler.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000003,
            version=68,
        )

        p_above = scheduler.calculate_peg_limit_price(
            target_price=target_price,
            action="BUY",
            best_bid=best_bid,
            best_ask=best_ask,
            peg_offset=0.0,
            hawkes_intensity=0.0000010,
            version=68,
        )

        assert p_above < p_sub, "Almgren-Chriss scheduler must shade BUY price downward for h > 0.0000003"

    def test_backward_compatibility_v66_and_prior(self):
        """Verify backward compatibility of SOR and OMS with Phase 66."""
        sor66 = SmartOrderRouter(version=66)
        assert sor66.is_phase68 is False
        assert sor66.is_phase66 is True

        oms = ExecutionOMSEngine()
        p66 = oms.calculate_peg_limit_price(
            target_price=100.0,
            action="BUY",
            best_bid=99.95,
            best_ask=100.05,
            peg_offset=0.0,
            hawkes_intensity=0.0000012,
            version=66,
        )
        assert np.isfinite(p66)
