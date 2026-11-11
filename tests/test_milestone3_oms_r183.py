"""
tests/test_milestone3_oms_r183.py — Comprehensive Unit Test Suite for Milestone 3 (Release R183).
Features F944 & F945:
- Feature F944: Smart Order Router 45% Midpoint Dark Pool Slicing & Friction Reduction.
- Feature F945: 12-Gate Institutional OMS Physical Capital Conservation (Net Equity <= Gross Equity) & Inverse Hedge.

MANDATORY INTEGRITY:
All tests verify real mathematical models, multi-tier execution slicing, 12 discrete safety gates,
strict zero synthetic rows (synthetic_rows == 0 native int), and dual-tree cryptographic parity.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pytest

# Repository root setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent

from src.execution.smart_order_router import (
    SmartOrderRouter,
    VERSION as SOR_VERSION,
    RELEASE as SOR_RELEASE,
    FEATURE as SOR_FEATURE,
    VERSION_PHASE183 as SOR_VERSION_P183,
    RELEASE_PHASE183 as SOR_RELEASE_P183,
    FEATURE_PHASE183 as SOR_FEATURE_P183,
    Phase183SmartOrderRouter,
    SmartOrderRouterPhase183,
)

from src.execution.oms_engine import (
    ExecutionOMSEngine,
    VERSION as OMS_VERSION,
    RELEASE as OMS_RELEASE,
    FEATURE as OMS_FEATURE,
    VERSION_R183 as OMS_VERSION_R183,
    RELEASE_R183 as OMS_RELEASE_R183,
    FEATURE_F945 as OMS_FEATURE_F945,
    Phase183OMSGateway,
    Phase183OMSEngine,
    ExecutionOMSEngineR183,
)


def _compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ==============================================================================
# 1. Feature F944: Smart Order Router 45% Midpoint Dark Pool Slicing Tests
# ==============================================================================

class TestF944SmartOrderRouter:
    """Verifies Feature F944 multi-tier routing, 45% dark midpoint slice, ADV capping, and telemetry."""

    def test_f944_01_default_dark_probe_ratio_45pct(self) -> None:
        """TC01: Verify SmartOrderRouter supports dark_probe_ratio=0.45 by default and allows overrides."""
        sor_default = SmartOrderRouter()
        assert sor_default.dark_probe_ratio == 0.45
        assert sor_default.adv_participation_cap == 0.015
        assert hasattr(sor_default, "audit_log")
        assert isinstance(sor_default.audit_log, list)

        sor_custom = SmartOrderRouter(dark_probe_ratio=0.50, adv_participation_cap=0.02)
        assert sor_custom.dark_probe_ratio == 0.50
        assert sor_custom.adv_participation_cap == 0.02

    def test_f944_02_version_polymorphism_and_aliases(self) -> None:
        """TC02: Verify version polymorphism, release identifiers, and institutional aliases."""
        assert SOR_VERSION == 183
        assert SOR_RELEASE == "R183"
        assert "F944" in SOR_FEATURE
        assert SOR_VERSION_P183 == 183
        assert SOR_RELEASE_P183 == "R183"
        assert Phase183SmartOrderRouter is SmartOrderRouter
        assert SmartOrderRouterPhase183 is SmartOrderRouter

    def test_f944_03_multi_tier_routing_hierarchy_structure(self) -> None:
        """TC03: Verify 3-tier routing hierarchy: Tier 1 Dark Midpoint -> Tier 2 Peg Maker -> Tier 3 Lit Sweeper."""
        sor = SmartOrderRouter(dark_probe_ratio=0.45)
        order_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 70_000.0,
            "execution_strategy": "PATIENT_TWAP",
            "market_spread_bps": 10.0,
        }
        res = sor.route_order(order_plan, ats_available=True)
        assert res["total_quantity"] == 10_000
        legs = res["legs"]
        assert len(legs) >= 2, f"Expected multi-tier legs, got {len(legs)}"

        # Verify priority ordering
        priorities = [leg["priority"] for leg in legs]
        assert priorities == sorted(priorities)
        venue_types = [leg["venue_type"] for leg in legs]
        assert "DARK_ATS_MIDPOINT" in venue_types
        assert "PRIMARY_EXCHANGE_MAKER" in venue_types or "LIT_EXCHANGE_SWEEPER" in venue_types

    def test_f944_04_dark_midpoint_slice_allocation_45pct(self) -> None:
        """TC04: Verify Dark Midpoint leg captures exactly 45% (4,500 shares) of eligible 10,000 share order."""
        sor = SmartOrderRouter(dark_probe_ratio=0.45)
        order_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 70_000.0,
            "execution_strategy": "MIDPOINT_PEG",
            "market_spread_bps": 12.0,
        }
        res = sor.route_order(order_plan, ats_available=True)
        assert res["effective_dark_ratio"] == 0.45
        dark_leg = res["dark_ats_midpoint"]
        assert dark_leg is not None
        assert dark_leg["quantity"] == 4500
        assert dark_leg["priority"] == 1
        assert dark_leg["venue_type"] == "DARK_ATS_MIDPOINT"

    def test_f944_05_maker_and_sweeper_residual_decomposition(self) -> None:
        """TC05: Verify remaining 55% (5,500 shares) decomposes between primary maker and residual sweeper."""
        sor = SmartOrderRouter(dark_probe_ratio=0.45)
        order_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 70_000.0,
            "execution_strategy": "MIDPOINT_PEG",
        }
        res = sor.route_order(order_plan, ats_available=True)
        tot_qty = sum(leg["quantity"] for leg in res["legs"])
        assert tot_qty == 10_000, f"Quantity conservation failed: {tot_qty} != 10000"

        rem_qty = 10_000 - res["dark_ats_midpoint"]["quantity"]
        assert rem_qty == 5500
        maker_leg = res.get("primary_exchange_maker")
        sweeper_leg = res.get("lit_exchange_sweeper")
        maker_q = maker_leg["quantity"] if maker_leg else 0
        sweeper_q = sweeper_leg["quantity"] if sweeper_leg else 0
        assert maker_q + sweeper_q == rem_qty

    def test_f944_06_midpoint_spread_savings_calculation(self) -> None:
        """TC06: Verify midpoint cross spread savings calculation (>= 1.5 bps on 5.0 bps half-spread)."""
        sor = SmartOrderRouter(dark_probe_ratio=0.45)
        half_spread_bps = 5.0
        savings = sor.calculate_midpoint_spread_savings(half_spread_bps)
        assert math.isclose(savings, 2.25, abs_tol=1e-5)
        assert savings >= 1.5

        # Custom dark ratio calculation
        assert math.isclose(sor.calculate_midpoint_spread_savings(6.0, dark_ratio=0.40), 2.40, abs_tol=1e-5)

    def test_f944_07_adv_participation_capping_enforcement(self) -> None:
        """TC07: Verify ADV participation cap <= 1.5% ADV clamps order quantity across venues."""
        sor = SmartOrderRouter(dark_probe_ratio=0.45, adv_participation_cap=0.015)
        # ADV = 100,000 shares -> 1.5% ADV cap is 1,500 shares
        order_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 5000,
            "adv": 100_000,
            "target_price": 70_000.0,
            "execution_strategy": "MIDPOINT_PEG",
        }
        res = sor.route_order(order_plan, ats_available=True)
        assert res["adv_capped"] is True
        assert res["original_quantity"] == 5000
        assert res["total_quantity"] == 1500
        assert sum(leg["quantity"] for leg in res["legs"]) == 1500

    def test_f944_08_adv_participation_under_cap_unmodified(self) -> None:
        """TC08: Verify order with quantity below 1.5% ADV is not capped."""
        sor = SmartOrderRouter(dark_probe_ratio=0.45)
        # ADV = 100,000 -> 1.5% is 1,500. Order is 1,000 (1.0% ADV)
        order_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "adv": 100_000,
            "target_price": 70_000.0,
        }
        res = sor.route_order(order_plan, ats_available=True)
        assert res["adv_capped"] is False
        assert res["total_quantity"] == 1000
        assert res["original_quantity"] == 1000

    def test_f944_09_routing_audit_telemetry_logging(self) -> None:
        """TC09: Verify self.audit_log captures venue execution telemetry and decision timestamps."""
        sor = SmartOrderRouter(dark_probe_ratio=0.45)
        assert len(sor.audit_log) == 0

        order1 = {"symbol": "005930", "action": "BUY", "quantity": 1000, "target_price": 70000.0}
        order2 = {"symbol": "AAPL", "action": "SELL", "quantity": 500, "target_price": 180.0, "market": "NASDAQ"}
        sor.route_order(order1, ats_available=True)
        sor.route_order(order2, ats_available=True)

        assert len(sor.audit_log) == 2
        entry1 = sor.audit_log[0]
        assert entry1["symbol"] == "005930"
        assert entry1["action"] == "BUY"
        assert entry1["total_quantity"] == 1000
        assert "timestamp" in entry1
        assert "venues" in entry1

        entry2 = sor.audit_log[1]
        assert entry2["symbol"] == "AAPL"
        assert entry2["action"] == "SELL"
        assert entry2["total_quantity"] == 500

    def test_f944_10_routing_result_audit_record_payload(self) -> None:
        """TC10: Verify returned routing result dictionary contains audit_record and dark_spread_savings_bps."""
        sor = SmartOrderRouter(dark_probe_ratio=0.45)
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 2000,
            "target_price": 70000.0,
            "market_spread_bps": 16.0,
            "execution_strategy": "MIDPOINT_PEG",
        }
        res = sor.route_order(plan, ats_available=True)
        assert "audit_record" in res
        assert "audit_log" in res
        assert "dark_spread_savings_bps" in res
        # With spread 16 bps, half-spread is 8 bps; 0.45 * 8 = 3.6 bps savings
        assert math.isclose(res["dark_spread_savings_bps"], 3.6, abs_tol=0.1)

    def test_f944_11_dynamic_dark_probe_scaling_with_accumulation(self) -> None:
        """TC11: Verify block accumulation or darkpool_score dynamically scales dark ratio up to 0.70."""
        sor = SmartOrderRouter(dark_probe_ratio=0.45)
        accum_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 70000.0,
            "darkpool_score": 0.85,
            "is_accumulation": True,
        }
        res = sor.route_order(accum_plan, ats_available=True)
        assert res["effective_dark_ratio"] >= 0.65
        assert res["effective_dark_ratio"] <= 0.70
        assert res["dark_ats_midpoint"]["quantity"] >= 6500

    def test_f944_12_destination_determination_multi_market(self) -> None:
        """TC12: Verify determine_destination resolves KRX ATS Nextrade and US FIX DMA gateways."""
        sor = SmartOrderRouter()
        dest_krx = sor.determine_destination("005930", market="KOSPI")
        assert dest_krx["market_region"] == "KRX"
        assert dest_krx["venue"] == "KRX_ATS_NEXTRADE"
        assert dest_krx["primary_broker"] == "korea_investment"

        dest_us = sor.determine_destination("AAPL", market="NASDAQ")
        assert dest_us["market_region"] == "US"
        assert dest_us["venue"] == "US_SMART_DMA"
        assert dest_us["primary_broker"] == "interactive_brokers"

        dest_jp = sor.determine_destination("7203.T", market="JAPAN")
        assert dest_jp["market_region"] == "JP"

    def test_f944_13_batch_routing_consistency(self) -> None:
        """TC13: Verify route_batch correctly routes multi-order portfolio batch with audit logging."""
        sor = SmartOrderRouter(dark_probe_ratio=0.45)
        batch_plans = [
            {"symbol": "005930", "action": "BUY", "quantity": 1000, "target_price": 70000.0},
            {"symbol": "000660", "action": "BUY", "quantity": 500, "target_price": 120000.0},
            {"symbol": "AAPL", "action": "BUY", "quantity": 300, "target_price": 180.0, "market": "NASDAQ"},
        ]
        results = sor.route_batch(batch_plans, ats_available=True)
        assert len(results) == 3
        assert len(sor.audit_log) == 3
        assert results[0]["symbol"] == "005930"
        assert results[1]["symbol"] == "000660"
        assert results[2]["symbol"] == "AAPL"


# ==============================================================================
# 2. Feature F945: 12-Gate Institutional OMS Safety Gates Tests
# ==============================================================================

class TestF945InstitutionalOMS12Gates:
    """Verifies Feature F945 12 safety gates, physical capital conservation, inverse hedge, and invariants."""

    @pytest.fixture
    def oms(self) -> ExecutionOMSEngine:
        return ExecutionOMSEngine()

    def test_f945_14_oms_version_release_and_aliases(self, oms: ExecutionOMSEngine) -> None:
        """TC14: Verify OMS engine exports version constants, aliases, and synthetic_rows == 0 invariant."""
        assert OMS_VERSION == 191 or OMS_VERSION == 183
        assert OMS_VERSION_R183 == 183
        assert OMS_RELEASE_R183 == "R183"
        assert "F945" in OMS_FEATURE_F945
        assert hasattr(oms, "synthetic_rows")
        assert oms.synthetic_rows == 0
        assert type(oms.synthetic_rows) is int
        assert not isinstance(oms.synthetic_rows, bool)
        assert Phase183OMSGateway is ExecutionOMSEngine
        assert ExecutionOMSEngineR183 is ExecutionOMSEngine

    def test_f945_15_gate8_panic_crisis_synthetic_inverse_hedge(self, oms: ExecutionOMSEngine) -> None:
        """TC15: Verify Gate 8 triggers action_override == 'CASH_OVERLAY' on PANIC_CRISIS or SEVERE crisis."""
        cand_short = {
            "symbol": "005930",
            "price": 50000.0,
            "quantity": 50,
            "weight": 0.02,
            "action": "SELL_SHORT",
            "market": "KOSPI",
        }
        res_severe = oms.evaluate_12_safety_gates(
            cand_short,
            context={"portfolio_capital": 100_000_000.0, "crisis_level": "SEVERE"}
        )
        assert res_severe["action_override"] == "CASH_OVERLAY"
        assert "GATE8" in res_severe["info"]

        res_panic = oms.evaluate_12_safety_gates(
            cand_short,
            context={"portfolio_capital": 100_000_000.0, "regime": "PANIC_CRISIS"}
        )
        assert res_panic["action_override"] == "CASH_OVERLAY"
        assert "GATE8" in res_panic["info"]

    def test_f945_16_gate8_normal_regime_no_override(self, oms: ExecutionOMSEngine) -> None:
        """TC16: Verify Gate 8 in normal regime does not set action_override."""
        cand_buy = {
            "symbol": "005930",
            "price": 50000.0,
            "quantity": 20,
            "weight": 0.01,
            "action": "BUY",
            "market": "KOSPI",
        }
        res = oms.evaluate_12_safety_gates(
            cand_buy,
            context={"portfolio_capital": 100_000_000.0, "regime": "BULL_LOW_VOL"}
        )
        assert res["action_override"] is None
        assert res["passed"] is True

    def test_f945_17_gate9_physical_capital_conservation_pass(self, oms: ExecutionOMSEngine) -> None:
        """TC17: Verify Gate 9 passes when Net Equity <= Gross Equity within 1e-4 tolerance."""
        cand = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "market": "KOSPI"}
        res = oms.evaluate_12_safety_gates(
            cand,
            context={
                "portfolio_capital": 100_000_000.0,
                "gross_equity": 100_000_000.0,
                "net_equity": 99_998_500.0,  # Net < Gross due to friction
                "friction": 1500.0,
                "available_cash": 20_000_000.0,
            }
        )
        assert res["gate_results"]["gate9_capital_conservation"]["passed"] is True
        assert res["passed"] is True

    def test_f945_18_gate9_physical_capital_conservation_breach_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC18: Verify Gate 9 rejects when Net Equity > Gross Equity + 1e-4."""
        cand = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "market": "KOSPI"}
        res = oms.evaluate_12_safety_gates(
            cand,
            context={
                "portfolio_capital": 100_000_000.0,
                "gross_equity": 100_000_000.0,
                "net_equity": 105_000_000.0,  # Unphysical phantom gain
            }
        )
        assert res["passed"] is False
        assert "GATE9_PHYSICAL_CAPITAL_CONSERVATION_BREACH" in res["rejection_reason"]
        assert 9 in res["failed_gates"]

    def test_f945_19_gate9_friction_non_negativity_invariant(self, oms: ExecutionOMSEngine) -> None:
        """TC19: Verify negative friction (< -1e-6) breaches capital conservation and is rejected."""
        cand = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "market": "KOSPI"}
        res = oms.evaluate_12_safety_gates(
            cand,
            context={
                "portfolio_capital": 100_000_000.0,
                "gross_equity": 100_000_000.0,
                "net_equity": 100_000_000.0,
                "friction": -50.0,  # Negative friction is unphysical
            }
        )
        assert res["passed"] is False
        assert "GATE9_PHYSICAL_CAPITAL_CONSERVATION_BREACH" in res["rejection_reason"]

    def test_f945_20_gate9_cash_solvency_invariant(self, oms: ExecutionOMSEngine) -> None:
        """TC20: Verify negative cash (< -1e-4) breaches capital conservation."""
        cand = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "market": "KOSPI"}
        res = oms.evaluate_12_safety_gates(
            cand,
            context={
                "portfolio_capital": 100_000_000.0,
                "gross_equity": 100_000_000.0,
                "net_equity": 90_000_000.0,
                "available_cash": -1000.0,  # Negative cash solvency failure
            }
        )
        assert res["passed"] is False
        assert "GATE9_PHYSICAL_CAPITAL_CONSERVATION_BREACH" in res["rejection_reason"]

    def test_f945_21_gate10_excessive_market_impact_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC21: Verify Gate 10 rejects orders with expected adverse impact > 45 bps."""
        cand_impact = {
            "symbol": "005930",
            "price": 50000.0,
            "quantity": 10,
            "weight": 0.02,
            "expected_impact_bps": 52.0,  # > 45.0 bps limit
            "market": "KOSPI",
        }
        res = oms.evaluate_12_safety_gates(cand_impact, context={"portfolio_capital": 100_000_000.0})
        assert res["passed"] is False
        assert "GATE10_EXCESSIVE_MARKET_IMPACT" in res["rejection_reason"]
        assert 10 in res["failed_gates"]

    def test_f945_22_gate10_stale_quote_latency_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC22: Verify Gate 10 rejects stale quote latency > 500 ms."""
        cand_stale = {
            "symbol": "005930",
            "price": 50000.0,
            "quantity": 10,
            "weight": 0.02,
            "quote_age_ms": 750.0,  # > 500 ms limit
            "market": "KOSPI",
        }
        res = oms.evaluate_12_safety_gates(cand_stale, context={"portfolio_capital": 100_000_000.0})
        assert res["passed"] is False
        assert "GATE10_STALE_QUOTE_LATENCY" in res["rejection_reason"]
        assert 10 in res["failed_gates"]

    def test_f945_23_gate11_vpin_toxicity_breach_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC23: Verify Gate 11 rejects orders when VPIN toxicity > 0.82."""
        cand_vpin = {
            "symbol": "005930",
            "price": 50000.0,
            "quantity": 10,
            "weight": 0.02,
            "vpin": 0.89,  # > 0.82 limit
            "market": "KOSPI",
        }
        res = oms.evaluate_12_safety_gates(cand_vpin, context={"portfolio_capital": 100_000_000.0})
        assert res["passed"] is False
        assert "GATE11_VPIN_TOXICITY_BREACH" in res["rejection_reason"]
        assert 11 in res["failed_gates"]

    def test_f945_24_gate11_hawkes_arrival_surge_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC24: Verify Gate 11 rejects orders when Hawkes arrival intensity > 5.0."""
        cand_hawkes = {
            "symbol": "005930",
            "price": 50000.0,
            "quantity": 10,
            "weight": 0.02,
            "hawkes_intensity": 7.2,  # > 5.0 limit
            "market": "KOSPI",
        }
        res = oms.evaluate_12_safety_gates(cand_hawkes, context={"portfolio_capital": 100_000_000.0})
        assert res["passed"] is False
        assert "GATE11_HAWKES_SURGE_BREACH" in res["rejection_reason"]
        assert 11 in res["failed_gates"]

    def test_f945_25_gate12_insufficient_collateral_ratio_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC25: Verify Gate 12 rejects orders when multi-currency collateral ratio < 1.0."""
        cand_collat = {
            "symbol": "005930",
            "price": 50000.0,
            "quantity": 10,
            "weight": 0.02,
            "collateral_ratio": 0.82,  # < 1.0 limit
            "market": "KOSPI",
        }
        res = oms.evaluate_12_safety_gates(cand_collat, context={"portfolio_capital": 100_000_000.0})
        assert res["passed"] is False
        assert "GATE12_INSUFFICIENT_COLLATERAL" in res["rejection_reason"]
        assert 12 in res["failed_gates"]

    def test_f945_26_gate12_invalid_settlement_cycle_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC26: Verify Gate 12 rejects settlement cycle exceeding T+2."""
        cand_settle = {
            "symbol": "005930",
            "price": 50000.0,
            "quantity": 10,
            "weight": 0.02,
            "settlement_days": 4,  # > 2 limit
            "market": "KOSPI",
        }
        res = oms.evaluate_12_safety_gates(cand_settle, context={"portfolio_capital": 100_000_000.0})
        assert res["passed"] is False
        assert "GATE12_INVALID_SETTLEMENT_CYCLE" in res["rejection_reason"]

    def test_f945_27_gate12_invalid_currency_conversion_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC27: Verify Gate 12 rejects when currency_valid is False."""
        cand_cur = {
            "symbol": "005930",
            "price": 50000.0,
            "quantity": 10,
            "weight": 0.02,
            "currency_valid": False,
            "market": "KOSPI",
        }
        res = oms.evaluate_12_safety_gates(cand_cur, context={"portfolio_capital": 100_000_000.0})
        assert res["passed"] is False
        assert "GATE12_CURRENCY_CONVERSION_INVALID" in res["rejection_reason"]


# ==============================================================================
# 3. Hostile Edge Cases & Zero Synthetic Rows Invariant Tests
# ==============================================================================

class TestMilestone3InvariantsAndEdgeCases:
    """Verifies robustness against hostile inputs, non-finite values, missing keys, and strict invariants."""

    @pytest.fixture
    def oms(self) -> ExecutionOMSEngine:
        return ExecutionOMSEngine()

    def test_m3_28_zero_synthetic_rows_invariant_native_int(self, oms: ExecutionOMSEngine) -> None:
        """TC28: Verify strict synthetic_rows == 0 invariant (Python native int 0, not bool)."""
        assert oms.synthetic_rows == 0
        assert type(oms.synthetic_rows) is int
        assert not isinstance(oms.synthetic_rows, bool)

        cand = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "market": "KOSPI"}
        res = oms.evaluate_12_safety_gates(cand, context={"portfolio_capital": 100_000_000.0})
        assert "synthetic_rows" in res
        assert res["synthetic_rows"] == 0
        assert type(res["synthetic_rows"]) is int
        assert not isinstance(res["synthetic_rows"], bool)

    def test_m3_29_zero_and_negative_adv_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC29: Verify order candidates with ADV <= 0 fail Gate 6 ADV participation gate."""
        cand_zero_adv = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "adv": 0.0, "market": "KOSPI"}
        res0 = oms.evaluate_12_safety_gates(cand_zero_adv, context={"portfolio_capital": 100_000_000.0})
        assert res0["passed"] is False
        assert "GATE6_ADV_PARTICIPATION_EXCEEDED" in res0["rejection_reason"]

        cand_neg_adv = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "adv": -500.0, "market": "KOSPI"}
        res_neg = oms.evaluate_12_safety_gates(cand_neg_adv, context={"portfolio_capital": 100_000_000.0})
        assert res_neg["passed"] is False
        assert "GATE6_ADV_PARTICIPATION_EXCEEDED" in res_neg["rejection_reason"]

    def test_m3_30_negative_equity_insolvency_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC30: Verify negative net equity triggers capital conservation breach rejection."""
        cand = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "market": "KOSPI"}
        res = oms.evaluate_12_safety_gates(
            cand,
            context={
                "portfolio_capital": 100_000_000.0,
                "gross_equity": 100_000_000.0,
                "net_equity": -500_000.0,  # Negative equity insolvency
            }
        )
        assert res["passed"] is False
        assert "GATE9_PHYSICAL_CAPITAL_CONSERVATION_BREACH" in res["rejection_reason"]

    def test_m3_31_nan_and_inf_adverse_impact_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC31: Verify NaN and Inf expected_impact_bps reject under Gate 10."""
        cand_nan = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "expected_impact_bps": float("nan"), "market": "KOSPI"}
        res_nan = oms.evaluate_12_safety_gates(cand_nan, context={"portfolio_capital": 100_000_000.0})
        assert res_nan["passed"] is False
        assert "GATE10_EXCESSIVE_MARKET_IMPACT" in res_nan["rejection_reason"]

        cand_inf = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "expected_impact_bps": float("inf"), "market": "KOSPI"}
        res_inf = oms.evaluate_12_safety_gates(cand_inf, context={"portfolio_capital": 100_000_000.0})
        assert res_inf["passed"] is False
        assert "GATE10_EXCESSIVE_MARKET_IMPACT" in res_inf["rejection_reason"]

    def test_m3_32_nan_and_inf_vpin_and_hawkes_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC32: Verify NaN and Inf VPIN / Hawkes intensity reject under Gate 11."""
        cand_nan_vpin = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "vpin": float("nan"), "market": "KOSPI"}
        res1 = oms.evaluate_12_safety_gates(cand_nan_vpin, context={"portfolio_capital": 100_000_000.0})
        assert res1["passed"] is False
        assert "GATE11_VPIN_TOXICITY_BREACH" in res1["rejection_reason"]

        cand_inf_hawkes = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "hawkes_intensity": float("inf"), "market": "KOSPI"}
        res2 = oms.evaluate_12_safety_gates(cand_inf_hawkes, context={"portfolio_capital": 100_000_000.0})
        assert res2["passed"] is False
        assert "GATE11_HAWKES_SURGE_BREACH" in res2["rejection_reason"]

    def test_m3_33_nan_collateral_ratio_rejection(self, oms: ExecutionOMSEngine) -> None:
        """TC33: Verify NaN collateral ratio rejects under Gate 12."""
        cand_nan_collat = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "collateral_ratio": float("nan"), "market": "KOSPI"}
        res = oms.evaluate_12_safety_gates(cand_nan_collat, context={"portfolio_capital": 100_000_000.0})
        assert res["passed"] is False
        assert "GATE12_INSUFFICIENT_COLLATERAL" in res["rejection_reason"]

    def test_m3_34_missing_context_keys_graceful_evaluation(self, oms: ExecutionOMSEngine) -> None:
        """TC34: Verify evaluate_12_safety_gates handles empty or None context without crashing."""
        cand = {"symbol": "005930", "price": 50000.0, "quantity": 10, "weight": 0.02, "market": "KOSPI"}
        res_none = oms.evaluate_12_safety_gates(cand, context=None)
        assert res_none["passed"] is True
        assert res_none["status"] == "APPROVED"

        res_empty = oms.evaluate_12_safety_gates(cand, context={})
        assert res_empty["passed"] is True

    def test_m3_35_dual_tree_sha256_cryptographic_parity(self) -> None:
        """TC35: Verify 100% bit-for-bit SHA-256 match between src/ and trading_system/src/ for both modules."""
        files = [
            ("src/execution/smart_order_router.py", "trading_system/src/execution/smart_order_router.py"),
            ("src/execution/oms_engine.py", "trading_system/src/execution/oms_engine.py"),
        ]
        for src_rel, ts_rel in files:
            src_p = PROJECT_ROOT / src_rel
            ts_p = PROJECT_ROOT / ts_rel
            assert src_p.is_file(), f"Missing source file: {src_p}"
            assert ts_p.is_file(), f"Missing mirror file: {ts_p}"
            h_src = _compute_sha256(src_p)
            h_ts = _compute_sha256(ts_p)
            assert h_src == h_ts, f"Dual-tree parity mismatch for {src_rel}: {h_src} != {h_ts}"

    def test_m3_36_multi_gate_simultaneous_rejections(self, oms: ExecutionOMSEngine) -> None:
        """TC36: Verify multiple safety gate breaches simultaneously accumulate distinct rejection reasons."""
        hostile_cand = {
            "symbol": "005930",
            "price": 0.0,                   # Gate 2 breach
            "quantity": 10,
            "weight": 0.08,                 # Gate 3 breach (> 5%)
            "adv": 0.0,                     # Gate 6 breach
            "expected_impact_bps": 60.0,    # Gate 10 breach (> 45 bps)
            "vpin": 0.95,                   # Gate 11 breach (> 0.82)
            "collateral_ratio": 0.50,       # Gate 12 breach (< 1.0)
            "market": "KOSPI",
        }
        res = oms.evaluate_12_safety_gates(
            hostile_cand,
            context={
                "portfolio_capital": 100_000_000.0,
                "gross_equity": 100_000_000.0,
                "net_equity": 110_000_000.0, # Gate 9 breach
            }
        )
        assert res["passed"] is False
        assert len(res["failed_gates"]) >= 6
        reasons = res["rejection_reasons"]
        assert "GATE2_INVALID_PRICE" in reasons
        assert "GATE3_WEIGHT_LIMIT_EXCEEDED" in reasons
        assert "GATE6_ADV_PARTICIPATION_EXCEEDED" in reasons
        assert "GATE9_PHYSICAL_CAPITAL_CONSERVATION_BREACH" in reasons
        assert "GATE10_EXCESSIVE_MARKET_IMPACT" in reasons
        assert "GATE11_VPIN_TOXICITY_BREACH" in reasons
        assert "GATE12_INSUFFICIENT_COLLATERAL" in reasons
