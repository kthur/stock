"""
tests/test_oms_modularization_m2.py

Comprehensive architectural tests for Milestone 2:
Execution OMS & Microstructure Modularization.

Verifies:
1. OMSSafetyGatekeeper modular isolation and delegation via ExecutionOMSEngine
2. MicrostructurePegPricer modular isolation and delegation via ExecutionOMSEngine & AlmgrenChrissScheduler
3. AlmgrenChrissScheduler & GatheralMarketImpactKernel relocation and backward compatibility
4. Exact numerical and behavioral preservation across all 12 safety gates
"""

import math
import numpy as np
import pytest

from src.execution.oms_safety_gates import (
    OMSSafetyGatekeeper,
    _is_invalid_or_nonpositive_price,
    check_gate11_idiosyncratic_risk_ratio,
    check_gate12_factor_crowding_shock,
    evaluate_gate11_and_gate12,
)
from src.execution.microstructure_peg_pricer import MicrostructurePegPricer
from src.execution.almgren_chriss import AlmgrenChrissScheduler, GatheralMarketImpactKernel
from src.execution.oms_engine import ExecutionOMSEngine, OMSEngine


class TestOMSSafetyGatesModularization:
    """Verifies OMSSafetyGatekeeper extraction and delegation."""

    def test_standalone_gatekeeper_instantiation(self):
        gatekeeper = OMSSafetyGatekeeper()
        assert gatekeeper.factor_crowding_shock_z == 0.0
        assert gatekeeper.is_factor_crowding_throttled is False
        assert gatekeeper._owner is None

    def test_gatekeeper_delegation_via_oms_engine(self):
        oms = ExecutionOMSEngine(db_path=":memory:")
        assert hasattr(oms, "safety_gatekeeper")
        assert isinstance(oms.safety_gatekeeper, OMSSafetyGatekeeper)
        assert oms.safety_gatekeeper._owner is oms

        # Gate 1: Capital slice
        assert oms.check_capital_slice_gate(10_000_000.0) is True
        assert oms.check_capital_slice_gate(30_000_000.0) is False

        # Gate 2: Price validity
        assert oms._is_invalid_or_nonpositive_price(100.0) is False
        assert oms._is_invalid_or_nonpositive_price(0.0) is True
        assert oms._is_invalid_or_nonpositive_price(-5.0) is True
        assert oms._is_invalid_or_nonpositive_price(float("nan")) is True

        # Gate 3: Single stock weight
        assert oms.check_single_stock_weight_gate(0.04) is True
        assert oms.check_single_stock_weight_gate(0.06) is False

        # Gate 4: Circuit breaker
        assert oms.check_circuit_breaker_gate("005930", 15.0) is True
        assert oms.check_circuit_breaker_gate("005930", 29.8) is False

        # Gate 5: Sector concentration
        assert oms.check_sector_concentration_gate(0.20) is True
        assert oms.check_sector_concentration_gate(0.30) is False

        # Gate 6: ADV participation
        assert oms.check_adv_participation_gate(100, 100_000) is True
        assert oms.check_adv_participation_gate(2000, 100_000) is False

        # Gate 7: Cash reserve
        assert oms.check_cash_reserve_gate(5_000_000, 50_000_000) is True
        assert oms.check_cash_reserve_gate(60_000_000, 50_000_000) is False

        # Gate 8: Synthetic inverse hedge
        h_normal = oms.evaluate_gate8_inverse_hedge("BULL_LOW_VOL", "KOSPI")
        assert h_normal["hedge_active"] is False
        h_panic = oms.evaluate_gate8_inverse_hedge("PANIC_CRISIS", "KOSPI")
        assert h_panic["hedge_active"] is True
        assert h_panic["symbol"] == "114800"

        # Gate 9: Capital conservation
        assert oms.verify_physical_capital_conservation(100.0, 100.0, 0.0, 10.0) is True
        assert oms.verify_physical_capital_conservation(105.0, 100.0, 0.0, 10.0) is False

        # Gate 10: Adverse impact & stale quote
        assert oms.check_adverse_impact_gate(25.0) is True
        assert oms.check_adverse_impact_gate(55.0) is False
        assert oms.check_stale_quote_gate(200.0) is True
        assert oms.check_stale_quote_gate(700.0) is False
        assert oms.check_gate10_adverse_impact_and_stale_quote(25.0, 200.0) is True
        assert oms.check_gate10_adverse_impact_and_stale_quote(55.0, 200.0) is False

        # Gate 11: Hawkes VPIN
        assert oms.check_hawkes_vpin_gate(0.60, 3.0) is True
        assert oms.check_hawkes_vpin_gate(0.90, 3.0) is False

        # Gate 12: Settlement collateral
        assert oms.check_settlement_collateral_gate(2, 1.2) is True
        assert oms.check_settlement_collateral_gate(3, 1.2) is False

    def test_factor_crowding_state_synchronization(self):
        oms = ExecutionOMSEngine(db_path=":memory:")
        assert oms.is_factor_crowding_throttled is False
        assert oms.safety_gatekeeper.is_factor_crowding_throttled is False

        # Update via oms
        throttled, params = oms.update_factor_crowding_state(3.5)
        assert throttled is True
        assert oms.is_factor_crowding_throttled is True
        assert oms.safety_gatekeeper.is_factor_crowding_throttled is True
        assert oms.factor_crowding_shock_z == 3.5

        # Reset via oms
        oms.reset_factor_crowding_state()
        assert oms.is_factor_crowding_throttled is False
        assert oms.safety_gatekeeper.is_factor_crowding_throttled is False
        assert oms.factor_crowding_shock_z == 0.0


class TestMicrostructurePegPricerModularization:
    """Verifies MicrostructurePegPricer extraction and delegation."""

    def test_standalone_peg_pricer_computation(self):
        px = MicrostructurePegPricer.calculate_peg_limit_price(
            target_price=50000.0,
            bid_price=49900.0,
            ask_price=50100.0,
            alpha_urgency=0.50,
            action="BUY",
        )
        assert px == 50000.0

    def test_oms_engine_delegates_to_peg_pricer(self):
        oms = ExecutionOMSEngine(db_path=":memory:")
        px1 = MicrostructurePegPricer.calculate_peg_limit_price(
            target_price=50000.0,
            bid_price=49900.0,
            ask_price=50100.0,
            alpha_urgency=0.75,
            action="BUY",
        )
        px2 = oms.calculate_peg_limit_price(
            target_price=50000.0,
            bid_price=49900.0,
            ask_price=50100.0,
            alpha_urgency=0.75,
            action="BUY",
        )
        px3 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=50000.0,
            bid_price=49900.0,
            ask_price=50100.0,
            alpha_urgency=0.75,
            action="BUY",
        )
        assert px1 == px2 == px3 == (49900.0 + 0.75 * 200.0)


class TestAlmgrenChrissRelocation:
    """Verifies AlmgrenChrissScheduler and GatheralMarketImpactKernel relocation."""

    def test_almgren_chriss_trajectory_computation(self):
        alloc = AlmgrenChrissScheduler.compute_trajectory(
            total_quantity=1000,
            adv=500000.0,
            daily_volatility=0.02,
            strategy_tier="medium",
            n_slices=5,
        )
        assert len(alloc) == 5
        assert sum(alloc) == 1000
        assert all(x >= 0 for x in alloc)

    def test_almgren_chriss_peg_price_delegation(self):
        px = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=50000.0,
            bid_price=49900.0,
            ask_price=50100.0,
            alpha_urgency=0.50,
        )
        assert px == 50000.0

    def test_gatheral_market_impact_kernel(self):
        perm = GatheralMarketImpactKernel.estimate_permanent_impact(
            quantity=10000.0,
            adv=1000000.0,
            daily_volatility=0.02,
        )
        assert perm > 0.0

        slices = GatheralMarketImpactKernel.compute_optimal_gatheral_slices(
            total_quantity=5000,
            n_slices=5,
            adv=1000000.0,
        )
        assert len(slices) == 5
        assert sum(slices) == 5000
        assert all(x >= 0 for x in slices)

    def test_oms_engine_re_exports(self):
        from src.execution.oms_engine import (
            AlmgrenChrissScheduler as ACS,
            GatheralMarketImpactKernel as GMIK,
            OMSSafetyGatekeeper as OSSG,
            MicrostructurePegPricer as MPP,
        )
        assert ACS is AlmgrenChrissScheduler
        assert GMIK is GatheralMarketImpactKernel
        assert OSSG is OMSSafetyGatekeeper
        assert MPP is MicrostructurePegPricer
