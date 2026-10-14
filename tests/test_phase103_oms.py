"""
tests/test_phase103_oms.py

Unit and integration test suite for Phase 103 Quantitative Alpha Enhancement (Feature F488 Microstructure OMS):
- Kerr-Newman-Kiselev 81-Dark-Energy DAHA
  (w = -83.0/3.0 approx -27.667, k_daha = 0.73, k_monster = 0.72,
   daha_81_factor = 16.20, c_monster = 1.0339757656912846e-25 [2^-83])
  Black Hole Spacetime L3 Orderbook Hydrodynamics:
  * 81-fold dark energy density
  * Repulsive acceleration -46.5 * c * (r ** 92) * daha_81_factor clamped in [-1e6, 1e6]
  * Theoretical check at r_eff = 2.0: exactly -385689.60
  * Method aliases on FastOrderBookMatchingEngine, FastLOBEngine, Phase103FastLOBEngine, and module level (23 aliases)
- SmartOrderRouter version=103:
  * Default version: 103
  * Lit maker ratio floor contracted to 1e-74 with 76-decimal precision
  * Cascading version flags: is_phase103 -> is_phase102 -> is_phase101...
  * Spread-conditional dark pool probing: when is_phase103 and market_spread_bps >= 5.0, is_probe_eligible = True
- Dual-OMS Preemptive micro-tick shading at h > 6.0e-12 (tested at h = 7.0e-12):
  * 56-nines factor (1 - 10^-56)
  * Exact parity between ExecutionOMSEngine and AlmgrenChrissScheduler (< 10^-12)
  * oms_p103_sub < oms_p102_sub
- Intraday U-curve volume profile weighted trajectory slicing:
  * u_i = 1.0 + 0.8 * (2*i/(N-1) - 1)^2
- Adaptive opening gap Gate 7.7 overheat & dip-limit pricing:
  * Excessive gap (>= +5.0%) routes to DIP_LIMIT with adaptive volatility discount
- Zero Regression with Phase 102, Phase 101 & Phase 100
"""

import math
import numpy as np
import pytest

from trading_system.src.core.fast_lob_engine import (
    FastOrderBookMatchingEngine,
    FastLOBEngine,
    Phase103FastLOBEngine,
    Phase102FastLOBEngine,
    Phase101FastLOBEngine,
    Phase100FastLOBEngine,
    Phase99FastLOBEngine,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from trading_system.src.execution.almgren_chriss import AlmgrenChrissScheduler as ReexportedAlmgrenChrissScheduler

from trading_system.src.core.fast_lob_engine import (
    compute_kerr_newman_kiselev_81_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
    compute_kerr_newman_kiselev_81_dark_energy_daha_queue_acceleration,
    compute_kerr_newman_kiselev_81_dark_energy_daha_acceleration,
    compute_knk_81_dark_energy_daha_acceleration,
    compute_phase103_daha_l3_acceleration,
    compute_phase103_lob_acceleration,
    phase103_lob_spacetime_hydrodynamics,
    compute_knk_81_dark_energy_acceleration,
    compute_kerr_newman_kiselev_81_dark_energy_acceleration,
    phase103_daha_l3_acceleration,
    knk_81_dark_energy_daha_l3,
    daha_l3_phase103_acceleration,
    phase103_dark_energy_acceleration,
    calculate_phase103_knk_acceleration,
    compute_knk_phase103_acceleration,
    daha_phase103_acceleration,
    phase103_spacetime_hydrodynamics,
    phase103_queue_acceleration,
    l3_phase103_acceleration,
    phase103_knk_acceleration,
    compute_phase103_knk_daha_queue_acceleration,
    compute_phase103_queue_acceleration,
    phase103_l3_queue_acceleration,
    knk_81_daha_queue_acceleration,
)


class TestPhase103MicrostructureAndOMS:
    """Test suite for Phase 103 Microstructure and Execution OMS enhancements."""

    def test_kerr_newman_kiselev_81_dark_energy_daha_queue_acceleration_basic(self):
        """Verify Kerr-Newman-Kiselev 81-Dark-Energy DAHA queue acceleration."""
        engine = FastOrderBookMatchingEngine(symbol="005930")
        for i in range(10):
            engine.add_limit_order(f"bid_{i}", "BUY", 70000.0 - i * 100.0, 500.0 + i * 50.0)
            engine.add_limit_order(f"ask_{i}", "SELL", 70100.0 + i * 100.0, 600.0 + i * 60.0)

        func = getattr(engine, "compute_kerr_newman_kiselev_81_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration", None)
        assert func is not None, "'FastOrderBookMatchingEngine' object missing KNK-81 acceleration method"

        res = func(
            charge_parameter=0.5,
            spin_parameter=0.5,
        )

        assert isinstance(res, dict)
        assert "queue_acceleration" in res
        assert "a_knk" in res
        assert "predicted_micro_price" in res
        assert "knk_81_dark_energy_correction" in res
        assert "knk_81_dark_energy_daha_acceleration" in res
        assert "phase103_knk_acceleration" in res
        assert "phase102_knk_acceleration" in res

        assert math.isfinite(res["knk_81_dark_energy_correction"])
        assert math.isfinite(res["knk_81_dark_energy_daha_acceleration"])
        assert res["daha_81_factor"] == 16.20
        assert res["k_daha_81"] == 0.73
        assert res["k_monster_81"] == 0.72
        assert math.isclose(res["c_monster_81"], 2.0 ** -83, rel_tol=1e-12)
        assert math.isclose(res["w_dark_energy_81"], -83.0 / 3.0, rel_tol=1e-9)

    def test_kerr_newman_kiselev_81_theoretical_check(self):
        """
        Verify KNK-81 theoretical acceleration at r_eff = 2.0:
        dark_81_accel = -46.5 * c_81 * (r_eff ** 92) * daha_81_factor
        At r_eff = 2.0: c_81 * (2^92) = (2^-83) * (2^92) = 2^9 = 512.0
        dark_81_accel = -46.5 * 512.0 * 16.20 = -385689.60 exactly.
        """
        c_81 = 2.0 ** -83
        r_eff = 2.0
        factor = 16.20
        theoretical_accel = -46.5 * c_81 * (r_eff ** 92) * factor
        assert math.isclose(theoretical_accel, -385689.60, abs_tol=1e-8), f"Expected -385689.60, got {theoretical_accel}"

        engine = FastOrderBookMatchingEngine(symbol="005930")
        res = engine.compute_kerr_newman_kiselev_81_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration(
            charge_parameter=0.5,
            spin_parameter=0.5,
            r_eff=2.0,
        )
        assert math.isclose(res["knk_81_dark_energy_correction"], -385689.60, abs_tol=1e-2)

    def test_kerr_newman_kiselev_81_aliases(self):
        """Verify all 23 method aliases on FastOrderBookMatchingEngine, class alias, and 24 module functions."""
        assert Phase103FastLOBEngine is FastOrderBookMatchingEngine
        engine = Phase103FastLOBEngine(symbol="005930")
        ref = engine.compute_kerr_newman_kiselev_81_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration()

        method_alias_names = [
            "compute_kerr_newman_kiselev_81_dark_energy_daha_queue_acceleration",
            "compute_kerr_newman_kiselev_81_dark_energy_daha_acceleration",
            "compute_knk_81_dark_energy_daha_acceleration",
            "compute_phase103_daha_l3_acceleration",
            "compute_phase103_lob_acceleration",
            "phase103_lob_spacetime_hydrodynamics",
            "compute_knk_81_dark_energy_acceleration",
            "compute_kerr_newman_kiselev_81_dark_energy_acceleration",
            "phase103_daha_l3_acceleration",
            "knk_81_dark_energy_daha_l3",
            "daha_l3_phase103_acceleration",
            "phase103_dark_energy_acceleration",
            "calculate_phase103_knk_acceleration",
            "compute_knk_phase103_acceleration",
            "daha_phase103_acceleration",
            "phase103_spacetime_hydrodynamics",
            "phase103_queue_acceleration",
            "l3_phase103_acceleration",
            "phase103_knk_acceleration",
            "compute_phase103_knk_daha_queue_acceleration",
            "compute_phase103_queue_acceleration",
            "phase103_l3_queue_acceleration",
            "knk_81_daha_queue_acceleration",
        ]
        assert len(method_alias_names) == 23
        for name in method_alias_names:
            fn = getattr(engine, name, None)
            assert fn is not None, f"Missing method alias {name} on FastOrderBookMatchingEngine"
            assert fn() == ref

        module_funcs = [
            compute_kerr_newman_kiselev_81_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration,
            compute_kerr_newman_kiselev_81_dark_energy_daha_queue_acceleration,
            compute_kerr_newman_kiselev_81_dark_energy_daha_acceleration,
            compute_knk_81_dark_energy_daha_acceleration,
            compute_phase103_daha_l3_acceleration,
            compute_phase103_lob_acceleration,
            phase103_lob_spacetime_hydrodynamics,
            compute_knk_81_dark_energy_acceleration,
            compute_kerr_newman_kiselev_81_dark_energy_acceleration,
            phase103_daha_l3_acceleration,
            knk_81_dark_energy_daha_l3,
            daha_l3_phase103_acceleration,
            phase103_dark_energy_acceleration,
            calculate_phase103_knk_acceleration,
            compute_knk_phase103_acceleration,
            daha_phase103_acceleration,
            phase103_spacetime_hydrodynamics,
            phase103_queue_acceleration,
            l3_phase103_acceleration,
            phase103_knk_acceleration,
            compute_phase103_knk_daha_queue_acceleration,
            compute_phase103_queue_acceleration,
            phase103_l3_queue_acceleration,
            knk_81_daha_queue_acceleration,
        ]
        assert len(module_funcs) == 24
        for m_fn in module_funcs:
            assert m_fn(engine) == ref

    def test_smart_order_router_phase103_flags_and_maker_ratio(self):
        """Verify SmartOrderRouter version 103 flags and lit maker floor to 1e-74."""
        sor_103 = SmartOrderRouter(version=103)
        assert getattr(sor_103, "is_phase103", False) is True
        assert getattr(sor_103, "is_phase102", False) is True
        assert getattr(sor_103, "is_phase101", False) is True
        assert getattr(sor_103, "is_phase100", False) is True
        assert getattr(sor_103, "is_phase99", False) is True

        # Default version should be 103
        sor_default = SmartOrderRouter()
        assert sor_default.version == 103
        assert sor_default.is_phase103 is True
        assert sor_default.is_phase102 is True
        assert sor_default.is_phase101 is True

        order_plan = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 103,
            "target_price": 150.0,
            "hawkes_intensity": 0.95,
        }
        res = sor_103.route_order(order_plan, gamma_toxic_dir=1.0)
        assert "maker_ratio" in res
        assert "min_ratio" in res
        assert res["maker_ratio"] == 1e-74
        assert res["maker_ratio"] < 1e-73

    def test_smart_order_router_spread_conditional_dark_probing(self):
        """Verify spread-conditional dark pool probing for spreads >= 5.0 bps in Phase 103."""
        sor = SmartOrderRouter(version=103)

        # Order plan with wide spread (6.0 bps) in DIRECT strategy (normally not dark eligible without high score/toxic)
        plan_wide = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 103,
            "target_price": 150.0,
            "execution_strategy": "DIRECT",
            "market_spread_bps": 6.0,
            "darkpool_activity_score": 0.10,  # Below 0.30 threshold
        }
        res_wide = sor.route_order(plan_wide, gamma_toxic_dir=0.0)
        venues_wide = [leg["venue_type"] for leg in res_wide["legs"]]
        assert "DARK_ATS_MIDPOINT" in venues_wide, "Wide spread (>= 5 bps) should trigger dark pool probing in Phase 103"

        # Order plan with tight spread (2.0 bps) in DIRECT strategy
        plan_tight = {
            "symbol": "AAPL",
            "quantity": 100,
            "action": "BUY",
            "version": 103,
            "target_price": 150.0,
            "execution_strategy": "DIRECT",
            "market_spread_bps": 2.0,
            "darkpool_activity_score": 0.10,
        }
        res_tight = sor.route_order(plan_tight, gamma_toxic_dir=0.0)
        venues_tight = [leg["venue_type"] for leg in res_tight["legs"]]
        assert "DARK_ATS_MIDPOINT" not in venues_tight, "Tight spread (< 5 bps) without catalysts should not probe dark pool"

    def test_tick_shading_dual_oms_phase103_threshold(self):
        """Verify tick shading threshold h > 6.0e-12 (tested at h = 7.0e-12)."""
        oms_p103_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=103,
            hawkes_intensity={"cross_excitation_toxicity": 7.0e-12}
        )
        oms_p102_sub = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=102,
            hawkes_intensity={"cross_excitation_toxicity": 7.0e-12}
        )
        # Phase 103 activates at h > 6.0e-12, so at 7.0e-12 it has non-zero shading.
        # Phase 102 activates at h > 8.0e-12, so at 7.0e-12 it has 0 shading offset (unshaded target price 100.0).
        assert oms_p103_sub < 100.0
        assert oms_p102_sub == 100.0
        assert oms_p103_sub < oms_p102_sub

        # Sub-threshold check: at h = 5.0e-12, neither should shade
        oms_p103_sub_low = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=103,
            hawkes_intensity={"cross_excitation_toxicity": 5.0e-12}
        )
        assert oms_p103_sub_low == 100.0

        # Exact parity with AlmgrenChrissScheduler
        sch_p103_sub = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=103,
            hawkes_intensity={"cross_excitation_toxicity": 7.0e-12}
        )
        assert math.isclose(oms_p103_sub, sch_p103_sub, rel_tol=1e-12, abs_tol=1e-12)

        # Also verify with re-exported AlmgrenChrissScheduler
        sch_reexp = ReexportedAlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=103,
            hawkes_intensity={"cross_excitation_toxicity": 7.0e-12}
        )
        assert math.isclose(sch_p103_sub, sch_reexp, rel_tol=1e-12, abs_tol=1e-12)

    def test_almgren_chriss_u_curve_intraday_slicing(self):
        """Verify Almgren-Chriss scheduler intraday U-curve volume profile weighting."""
        tranches_u = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=1000,
            adv=1e9,
            daily_volatility=0.02,
            strategy_tier="medium",
            n_slices=6,
            use_u_curve=True
        )
        tranches_no_u = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=1000,
            adv=1e9,
            daily_volatility=0.02,
            strategy_tier="medium",
            n_slices=6,
            use_u_curve=False
        )

        assert len(tranches_u) == 6
        assert sum(tranches_u) == 1000
        assert all(q >= 0 for q in tranches_u)

        # U-curve profile u_i = 1.0 + 0.8 * (2*i/(N-1) - 1)^2 has u_0 = 1.8, u_mid = 1.0, u_5 = 1.8
        # Slices at edges (open and close) receive elevated share compared to midday slices
        assert tranches_u[0] > tranches_u[2]
        assert tranches_u[5] > tranches_u[3]
        # Compare with non-U-curve hyperbolic schedule: the closing tranche is boosted by the U-curve
        assert tranches_u[-1] > tranches_no_u[-1]

    def test_gate_7_7_adaptive_opening_gap_pricing(self):
        """Verify Gate 7.7 adaptive opening gap overheat & dip-limit pricing."""
        engine = ExecutionOMSEngine(db_path=":memory:", version=103)
        top_predictions = [
            {
                "symbol": "AAPL",
                "market": "SP500",
                "action": "BUY",
                "target_price": 150.0,
                "change_pct": 6.5,  # Excessive gap > +5.0%
                "atr_15m": 2.50,
                "volatility_20d": 0.025,
                "version": 103,
            }
        ]
        portfolio_weights = {"AAPL": 0.10}
        plan = engine.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            total_capital=100_000_000.0,
            version=103,
        )

        assert len(plan) > 0
        order = plan[0]
        assert order["action"] == "BUY"
        # Overheated gap should route to DIP_LIMIT
        assert order["execution_strategy"] == "DIP_LIMIT"
        # Price should be discounted below current price
        assert order["target_price"] < 150.0

    def test_zero_regression_phase102_and_phase101_compatibility(self):
        """Verify backward compatibility and zero regressions for Phase 102 and Phase 101."""
        # 1. SmartOrderRouter Phase 102 maker ratio floor at 1e-73
        sor_102 = SmartOrderRouter(version=102)
        assert sor_102.is_phase102 is True
        res_102 = sor_102.route_order(
            {"symbol": "005930", "quantity": 10, "action": "BUY", "version": 102, "target_price": 70000.0},
            gamma_toxic_dir=1.0
        )
        assert res_102["maker_ratio"] == 1e-73

        # 2. SmartOrderRouter Phase 101 maker ratio floor at 1e-72
        sor_101 = SmartOrderRouter(version=101)
        assert sor_101.is_phase101 is True
        res_101 = sor_101.route_order(
            {"symbol": "005930", "quantity": 10, "action": "BUY", "version": 101, "target_price": 70000.0},
            gamma_toxic_dir=1.0
        )
        assert res_101["maker_ratio"] == 1e-72

        # 3. Micro-tick shading thresholds
        p102_shaded = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=102,
            hawkes_intensity={"cross_excitation_toxicity": 9.0e-12}
        )
        assert p102_shaded < 100.0

        p101_unshaded_at_9 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=101,
            hawkes_intensity={"cross_excitation_toxicity": 9.0e-12}
        )
        assert p101_unshaded_at_9 == 100.0

        p101_shaded_at_11 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.95,
            ask_price=100.05,
            action="BUY",
            version=101,
            hawkes_intensity={"cross_excitation_toxicity": 1.1e-11}
        )
        assert p101_shaded_at_11 < 100.0
