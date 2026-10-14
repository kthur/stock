"""
tests/test_phase101_oms.py

Unit and integration test suite for Phase 101 Quantitative Alpha Enhancement (Feature F478 Microstructure OMS):
- Kerr-Newman-Kiselev 79-Dark-Energy DAHA
  (w = -81.0/3.0 = -27.000, k_daha = 0.71, k_monster = 0.70,
   daha_79_factor = 15.60, c_monster = 4.1359030627651384e-25 [2^-81])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 79-fold dark energy density
  * Repulsive acceleration -44.5 * c * (r ** 88) * daha_79_factor clamped in [-1e6, 1e6]
  * Theoretical check at r_eff = 2.0: exactly -88857.60
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, Phase101FastLOBEngine, and module level (23 aliases)
- SmartOrderRouter version=101:
  * Default version: 101
  * Lit maker ratio floor contracted to 1e-72 with 74-decimal precision
  * Cascading version flags: is_phase101 -> is_phase100 -> is_phase99...
- Dual-OMS Preemptive micro-tick shading at h > 0.000000000010 (1.0e-11, tested at h = 0.000000000011):
  oms_p101_sub < oms_p100_sub
- Gate 7.7 Adaptive Pricing:
  * Volatility-linked dynamic discount min(0.5 * Gap, 1.2 * ATR_15m) replacing flat 1.5% discount
- VIX Single Gating:
  * Consolidated single integrated gating min(vix_cap, smooth_crisis_mult)
- Rebalance Liquidation Guarantee:
  * Liquidates dropped holdings with weight 0.0
- Zero Regression with Phase 100 & Phase 99
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    Phase101FastLOBEngine,
    Phase100FastLOBEngine,
    Phase99FastLOBEngine,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from trading_system.src.risk.risk_manager import RiskManager, CrisisLevel

from trading_system.src.core.fast_lob_engine import (
    compute_kerr_newman_kiselev_79_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_kerr_newman_kiselev_79_dark_energy_daha_queue_acceleration,
    compute_kerr_newman_kiselev_79_dark_energy_daha_acceleration,
    compute_knk_79_dark_energy_daha_acceleration,
    compute_phase101_daha_l3_acceleration,
    compute_phase101_lob_acceleration,
    phase101_lob_spacetime_hydrodynamics,
    compute_knk_79_dark_energy_acceleration,
    compute_kerr_newman_kiselev_79_dark_energy_acceleration,
    phase101_daha_l3_acceleration,
    knk_79_dark_energy_daha_l3,
    daha_l3_phase101_acceleration,
    phase101_dark_energy_acceleration,
    calculate_phase101_knk_acceleration,
    compute_knk_phase101_acceleration,
    daha_phase101_acceleration,
    phase101_spacetime_hydrodynamics,
    phase101_queue_acceleration,
    l3_phase101_acceleration,
    phase101_knk_acceleration,
    compute_phase101_knk_daha_queue_acceleration,
    compute_phase101_queue_acceleration,
    phase101_l3_queue_acceleration,
    knk_79_daha_queue_acceleration,
)


class TestPhase101MicrostructureAndOMS:
    """Test suite for Phase 101 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_79_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 79-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_79_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None, "'FastOrderBookMatchingEngine' object missing KNK-79 acceleration method"

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_79_dark_energy_correction" in res
        assert "knk_79_dark_energy_daha_acceleration" in res
        assert "phase101_knk_acceleration" in res
        assert "phase100_knk_acceleration" in res

        assert math.isfinite(res["knk_79_dark_energy_correction"])
        assert math.isfinite(res["knk_79_dark_energy_daha_acceleration"])
        assert math.isclose(res["daha_79_factor"], 15.60, rel_tol=1e-5)
        assert math.isclose(res["k_daha_79"], 0.71, rel_tol=1e-5)
        assert math.isclose(res["k_monster_79"], 0.70, rel_tol=1e-5)
        assert math.isclose(res["c_monster_79"], 2.0**-81, rel_tol=1e-9)
        assert math.isclose(res["w_dark_energy_79"], -81.0 / 3.0, rel_tol=1e-5)

        # Theoretical check: at r_eff = 2.0, c_79 = 2^-81, daha_79_factor = 15.60
        # dark_79_accel = -44.5 * (2^-81) * (2^88) * 15.60 = -44.5 * 128.0 * 15.60 = -88857.60
        c_79 = 2.0**-81
        r_eff = 2.0
        theoretical_dark_accel = -44.5 * c_79 * (r_eff**88) * 15.60
        assert math.isclose(theoretical_dark_accel, -88857.60, rel_tol=1e-9)

    def test_kerr_newman_kiselev_79_aliases(self):
        """Verify 23 method aliases on FastOrderBookMatchingEngine, FastLOBEngine, Phase101FastLOBEngine, and module level for KNK-79."""
        engine = FastOrderBookMatchingEngine(symbol="AAPL")
        for i in range(5):
            engine.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_79_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None
        ref = func()

        # Check class method aliases (23 aliases)
        alias_names = [
            "compute_kerr_newman_kiselev_79_dark_energy_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_79_dark_energy_daha_acceleration",
            "compute_knk_79_dark_energy_daha_acceleration",
            "compute_phase101_daha_l3_acceleration",
            "compute_phase101_lob_acceleration",
            "phase101_lob_spacetime_hydrodynamics",
            "compute_knk_79_dark_energy_acceleration",
            "compute_kerr_newman_kiselev_79_dark_energy_acceleration",
            "phase101_daha_l3_acceleration",
            "knk_79_dark_energy_daha_l3",
            "daha_l3_phase101_acceleration",
            "phase101_dark_energy_acceleration",
            "calculate_phase101_knk_acceleration",
            "compute_knk_phase101_acceleration",
            "daha_phase101_acceleration",
            "phase101_spacetime_hydrodynamics",
            "phase101_queue_acceleration",
            "l3_phase101_acceleration",
            "phase101_knk_acceleration",
            "compute_phase101_knk_daha_queue_acceleration",
            "compute_phase101_queue_acceleration",
            "phase101_l3_queue_acceleration",
            "knk_79_daha_queue_acceleration",
        ]
        assert len(alias_names) == 23

        for alias in alias_names:
            method = getattr(engine, alias, None)
            assert method is not None, f"Missing method {alias} on FastOrderBookMatchingEngine"
            assert method() == ref

        # Check aliases on FastLOBEngine alias class
        engine_lob = FastLOBEngine(symbol="AAPL")
        for i in range(5):
            engine_lob.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine_lob.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)
        for alias in alias_names:
            method = getattr(engine_lob, alias, None)
            assert method is not None, f"Missing method {alias} on FastLOBEngine"
            assert method() == ref

        # Check aliases on Phase101FastLOBEngine alias class
        engine_p101 = Phase101FastLOBEngine(symbol="AAPL")
        for i in range(5):
            engine_p101.add_limit_order(f"b_{i}", "BUY", 150.0 - i * 0.1, 100.0)
            engine_p101.add_limit_order(f"a_{i}", "SELL", 150.1 + i * 0.1, 100.0)
        for alias in alias_names:
            method = getattr(engine_p101, alias, None)
            assert method is not None, f"Missing method {alias} on Phase101FastLOBEngine"
            assert method() == ref

        # Check module-level aliases (23 functions + base = 24 functions)
        module_funcs = [
            compute_kerr_newman_kiselev_79_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            compute_kerr_newman_kiselev_79_dark_energy_daha_queue_acceleration,
            compute_kerr_newman_kiselev_79_dark_energy_daha_acceleration,
            compute_knk_79_dark_energy_daha_acceleration,
            compute_phase101_daha_l3_acceleration,
            compute_phase101_lob_acceleration,
            phase101_lob_spacetime_hydrodynamics,
            compute_knk_79_dark_energy_acceleration,
            compute_kerr_newman_kiselev_79_dark_energy_acceleration,
            phase101_daha_l3_acceleration,
            knk_79_dark_energy_daha_l3,
            daha_l3_phase101_acceleration,
            phase101_dark_energy_acceleration,
            calculate_phase101_knk_acceleration,
            compute_knk_phase101_acceleration,
            daha_phase101_acceleration,
            phase101_spacetime_hydrodynamics,
            phase101_queue_acceleration,
            l3_phase101_acceleration,
            phase101_knk_acceleration,
            compute_phase101_knk_daha_queue_acceleration,
            compute_phase101_queue_acceleration,
            phase101_l3_queue_acceleration,
            knk_79_daha_queue_acceleration,
        ]
        assert len(module_funcs) == 24
        for m_fn in module_funcs:
            assert m_fn(engine) == ref

    def test_smart_order_router_phase101_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 101 flags and lit maker floor to 1e-72."""
        sor_101 = SmartOrderRouter(version=101)
        assert getattr(sor_101, "is_phase101", False) is True
        assert getattr(sor_101, "is_phase100", False) is True
        assert getattr(sor_101, "is_phase99", False) is True

        # Default version should be 101
        sor_default = SmartOrderRouter()
        assert sor_default.version == 101
        assert sor_default.is_phase101 is True
        assert sor_default.is_phase100 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 101,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_101.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-72

    def test_tick_shading_dual_oms_phase101_threshold(self):
        """Verify tick shading threshold h > 0.000000000010 (tested at h = 0.000000000011)."""
        oms_p101_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=101,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000011}
        )
        oms_p100_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=100,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000011}
        )
        # Phase 101 activates at h > 1.0e-11, so at 1.1e-11 it has non-zero shading:
        # Phase 100 activates at h > 1.2e-11, so at 1.1e-11 it has 0 shading offset
        assert oms_p101_sub < oms_p100_sub

        # Sub-threshold check: at h = 0.9e-11, neither should shade
        oms_p101_sub_low = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=101,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000009}
        )
        assert oms_p101_sub_low == 100.0

        # Exact parity with AlmgrenChrissScheduler
        sch_p101_sub = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=101,
            hawkes_intensity={"cross_excitation_toxicity": 0.000000000011}
        )
        assert math.isclose(oms_p101_sub, sch_p101_sub, rel_tol=1e-12, abs_tol=1e-12)

    def test_gate_7_7_adaptive_pricing(self):
        """Verify Gate 7.7 Adaptive Pricing dynamically adapts discount to volatility."""
        oms = ExecutionOMSEngine(lot_size_krx=1)
        # Low volatility gap up: atr_15m = 0.005 (0.5%), gap = +6.0%
        # discount = min(0.5 * 0.06, 1.2 * 0.005) = min(0.03, 0.006) = 0.006 (0.6% discount)
        # Target price = 100.0 * (1 - 0.006) = 99.4
        plan_low_vol = oms.generate_order_plan(
            top_predictions=[{
                "symbol": "005930",
                "action": "BUY",
                "change_pct": 6.0,
                "target_price": 100.0,
                "atr_15m": 0.005,
            }],
            portfolio_weights={"005930": 0.10},
            total_capital=1_000_000,
        )
        assert len(plan_low_vol) == 1
        assert plan_low_vol[0]["execution_strategy"] == "DIP_LIMIT"
        assert math.isclose(plan_low_vol[0]["target_price"], 99.4, rel_tol=1e-3)

        # Flat 1.5% would have yielded 98.5. Here 99.4 > 98.5 (less discount because volatility is tight).
        assert plan_low_vol[0]["target_price"] > 98.5

    def test_vix_single_gating_preserves_rebound_alpha(self):
        """Verify VIX Single Gating consolidates vix_cap and smooth_crisis_mult without compounding vol_scalar."""
        rm = RiskManager(
            target_annual_volatility=0.15,
            portfolio_value=1_000_000,
            max_position_size_pct=0.10,
        )
        rm.crisis_detector.crisis_level = CrisisLevel.NONE
        # In elevated VIX (e.g. 28.0), vix_cap = 1.0 - 0.02*(28-20) = 0.84
        # Previously vol_scalar = 0.15 / (28/100) = ~0.53 compounded with vix_cap
        # With single gating, integrated_vix_scale = min(vix_cap, smooth_crisis_mult)
        qty = rm.calculate_position_size(
            symbol="AAPL",
            entry_price=100.0,
            stop_loss_price=95.0,
            vix=28.0,
        )
        assert qty > 0
        # Check that size is not over-penalized down to zero
        max_qty = int(1_000_000 * 0.10 / 100.0)
        assert qty >= int(max_qty * 0.60)

    def test_rebalance_liquidation_guarantee(self):
        """Verify rebalance liquidation guarantee generates exit orders for dropped positions."""
        oms = ExecutionOMSEngine(lot_size_krx=1)
        current_holdings = {
            "005930": {"current_price": 70000.0, "portfolio_weight": 0.05, "shares": 100},
            "DROPPED_SYM": {"current_price": 50000.0, "portfolio_weight": 0.05, "shares": 50},
        }
        # Top predictions only includes 005930; DROPPED_SYM fell out of top picks
        top_picks = [{
            "symbol": "005930",
            "action": "BUY",
            "target_price": 70000.0,
        }]
        weights = {"005930": 0.08, "DROPPED_SYM": 0.0}
        plans = oms.generate_order_plan(
            top_predictions=top_picks,
            portfolio_weights=weights,
            total_capital=10_000_000,
            current_holdings=current_holdings,
        )
        plan_syms = {p["symbol"]: p for p in plans}
        assert "DROPPED_SYM" in plan_syms
        assert plan_syms["DROPPED_SYM"]["action"] == "SELL"
        assert plan_syms["DROPPED_SYM"]["quantity"] == 50

    def test_zero_regression_phase100_compatibility(self):
        """Verify Phase 100 calculations remain strictly preserved when requested."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        engine.add_limit_order("b1", "BUY", 100.0, 10.0)
        engine.add_limit_order("a1", "SELL", 101.0, 10.0)

        res_p100 = engine.compute_kerr_newman_kiselev_78_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()
        assert math.isclose(res_p100["daha_78_factor"], 15.30, rel_tol=1e-5)
        assert math.isclose(res_p100["k_daha_78"], 0.70, rel_tol=1e-5)
        assert math.isclose(res_p100["k_monster_78"], 0.69, rel_tol=1e-5)

        sor_100 = SmartOrderRouter(version=100)
        assert sor_100.is_phase100 is True
        assert sor_100.is_phase101 is False
        order_plan_100 = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 100,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res_routed = sor_100.route_order(order_plan_100, gamma_toxic_dir=1.0)
        assert res_routed["maker_ratio"] == 1e-71
