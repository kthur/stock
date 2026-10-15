"""
tests/test_phase111_borrow_dynamics.py
Phase 111 Milestone M3 Test Suite (Release R127 / v118 Production Master).

Comprehensive Verification for Short Squeeze Borrow Dynamics & HTB Fee Model (Feature F527):
1. Version metadata (VERSION == 111, RELEASE == "R127") and complete alias trees.
2. Dual-placement bit-for-bit SHA-256 equivalence across src/ and trading_system/src/.
3. Dual-placement import equivalence and functional parity.
4. Non-linear loan utilization curve U(t) and regime boundaries.
5. Dynamic borrow fee calculation and non-linear HTB fee explosion.
6. Inventory depletion velocity v_dep(t) calculation.
7. SEC Rule 203(b)(1) affirmative locate tracking and ledger auditing.
8. Days-to-Cover (DTC) and Short Interest Ratio (SIR) diagnostics.
9. Calibrated multi-factor recall risk logistic scoring.
10. Negative carry drag deduction and economic hurdle viability.
11. Composite short squeeze catalyst scoring and explosive breakout trigger.
12. ExecutionOMSEngine Gate 8.1 safety rules:
    - Naked shorts without locate blocked.
    - Negative carry shorts blocked.
    - Shorts into squeeze breakouts blocked.
    - Acute recall risk shorts blocked.
    - Long squeeze breakouts promoted to MOMENTUM_SQUEEZE.
13. Edge cases: NaNs, Infinities, division by zero, zero float/ADV, negative numbers.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

from src.risk.borrow_dynamics_model import (
    BorrowDynamicsModel,
    HardToBorrowFeeModel,
    ShortSqueezeBorrowRisk,
    Phase111BorrowModel,
    ShortSqueezeBorrowModel,
    HardToBorrowFeeEngine,
    Phase111BorrowDynamicsEngine,
    InstitutionalBorrowRiskModel,
    ShortSqueezeGuardGate,
    BorrowFeeQuote,
    BorrowState,
    LocateResult,
    NegativeCarryResult,
    SqueezeEvaluationResult,
    Gate8_1Verdict,
    calculate_borrow_fee,
    evaluate_short_squeeze_risk,
)
import trading_system.src.risk.borrow_dynamics_model as ts_bdm


# =============================================================================
# 1. Exports, Aliases & Dual-Placement Mirror Hash Integrity
# =============================================================================

class TestBorrowDynamicsExportsAndIntegrity:
    """Verifies module exports, version constants, alias trees, and SHA-256 integrity."""

    def test_version_and_release_metadata(self):
        model = BorrowDynamicsModel()
        assert model.VERSION == 111
        assert model.RELEASE == "R127"
        assert model.version == 111

    def test_alias_tree_identities(self):
        assert HardToBorrowFeeModel is BorrowDynamicsModel
        assert ShortSqueezeBorrowRisk is BorrowDynamicsModel
        assert Phase111BorrowModel is BorrowDynamicsModel
        assert ShortSqueezeBorrowModel is BorrowDynamicsModel
        assert HardToBorrowFeeEngine is BorrowDynamicsModel
        assert Phase111BorrowDynamicsEngine is BorrowDynamicsModel
        assert InstitutionalBorrowRiskModel is BorrowDynamicsModel
        assert ShortSqueezeGuardGate is BorrowDynamicsModel
        assert BorrowState is BorrowFeeQuote

    def test_dual_tree_import_parity(self):
        assert ts_bdm.BorrowDynamicsModel is not None
        assert ts_bdm.BorrowDynamicsModel.VERSION == 111
        assert ts_bdm.BorrowDynamicsModel.RELEASE == "R127"
        assert ts_bdm.HardToBorrowFeeModel is ts_bdm.BorrowDynamicsModel
        assert ts_bdm.calculate_borrow_fee is not None

    def test_dual_placement_sha256_hash_equality(self):
        p1 = Path("src/risk/borrow_dynamics_model.py")
        p2 = Path("trading_system/src/risk/borrow_dynamics_model.py")

        assert p1.exists(), f"Canonical file missing: {p1}"
        assert p2.exists(), f"Mirror file missing: {p2}"

        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()

        assert h1 == h2, f"SHA-256 mismatch between {p1} and {p2}: {h1} != {h2}"
        assert len(h1) == 64


# =============================================================================
# 2. Loan Utilization Curve Tests
# =============================================================================

class TestLoanUtilizationCurve:
    """Verifies non-linear loan utilization curve calculation and boundaries."""

    @pytest.fixture
    def model(self):
        return BorrowDynamicsModel()

    def test_standard_utilization(self, model):
        u = model.calculate_loan_utilization(shares_on_loan=500_000, lendable_inventory=1_000_000)
        assert u == pytest.approx(0.50, abs=1e-6)

        u = model.calculate_loan_utilization(shares_on_loan=850_000, lendable_inventory=1_000_000)
        assert u == pytest.approx(0.85, abs=1e-6)

    def test_zero_and_over_loan_boundaries(self, model):
        # Zero loan
        u_zero = model.calculate_loan_utilization(shares_on_loan=0, lendable_inventory=1_000_000)
        assert u_zero == 0.0

        # Over-loan clamped to 1.0
        u_over = model.calculate_loan_utilization(shares_on_loan=1_500_000, lendable_inventory=1_000_000)
        assert u_over == 1.0

        # Zero lendable inventory with active loan -> 1.0 (saturated)
        u_sat = model.calculate_loan_utilization(shares_on_loan=10_000, lendable_inventory=0)
        assert u_sat == 1.0

        # Zero lendable and zero loan -> 0.0
        u_empty = model.calculate_loan_utilization(shares_on_loan=0, lendable_inventory=0)
        assert u_empty == 0.0

    def test_nan_and_negative_loan_sanitization(self, model):
        u_nan = model.calculate_loan_utilization(shares_on_loan=float("nan"), lendable_inventory=1_000_000)
        assert u_nan == 0.0

        u_neg = model.calculate_loan_utilization(shares_on_loan=-50_000, lendable_inventory=1_000_000)
        assert u_neg == 0.0


# =============================================================================
# 3. Dynamic Borrow Fee Formulation Tests
# =============================================================================

class TestDynamicBorrowFeeCalculation:
    """Verifies non-linear borrow fee rate formulation across markets and utilization levels."""

    @pytest.fixture
    def model(self):
        return BorrowDynamicsModel()

    def test_general_collateral_baseline(self, model):
        # Under unconstrained regime (U < 0.60), borrow fee equals GC rate
        fee_sp = model.calculate_borrow_fee(utilization=0.30, market="SP500")
        assert fee_sp == pytest.approx(0.0030, abs=1e-6)

        fee_nq = model.calculate_borrow_fee(utilization=0.45, market="NASDAQ")
        assert fee_nq == pytest.approx(0.0040, abs=1e-6)

        fee_kp = model.calculate_borrow_fee(utilization=0.55, market="KOSPI")
        assert fee_kp == pytest.approx(0.0100, abs=1e-6)

        fee_kq = model.calculate_borrow_fee(utilization=0.20, market="KOSDAQ")
        assert fee_kq == pytest.approx(0.0120, abs=1e-6)

        fee_rut = model.calculate_borrow_fee(utilization=0.50, market="RUSSELL2000")
        assert fee_rut == pytest.approx(0.0060, abs=1e-6)

    def test_explicit_gc_flag_override(self, model):
        # Even at high utilization, explicit is_gc=True forces base GC rate
        fee_gc = model.calculate_borrow_fee(utilization=0.92, market="SP500", is_gc=True)
        assert fee_gc == pytest.approx(0.0030, abs=1e-6)

    def test_non_linear_fee_escalation(self, model):
        # As utilization rises from 60% to 95%, fees must strictly escalate
        f60 = model.calculate_borrow_fee(utilization=0.60, market="SP500")
        f75 = model.calculate_borrow_fee(utilization=0.75, market="SP500")
        f85 = model.calculate_borrow_fee(utilization=0.85, market="SP500")
        f95 = model.calculate_borrow_fee(utilization=0.95, market="SP500")
        f98 = model.calculate_borrow_fee(utilization=0.98, market="SP500")

        assert f60 < f75 < f85 < f95 < f98
        # At 95% utilization, borrow fee should exceed 100% annual rate
        assert f95 > 1.0

    def test_depletion_velocity_markup(self, model):
        # High depletion velocity adds beta_depletion * v_dep
        f_static = model.calculate_borrow_fee(utilization=0.75, market="SP500", depletion_velocity=0.0)
        f_surging = model.calculate_borrow_fee(utilization=0.75, market="SP500", depletion_velocity=0.10)

        # Difference should be approximately beta_depletion * 0.10 = 0.10 * 0.10 = 0.010 (100 bps)
        diff = f_surging - f_static
        assert diff == pytest.approx(0.010, abs=1e-5)


# =============================================================================
# 4. Inventory Depletion Velocity Tests
# =============================================================================

class TestInventoryDepletionVelocity:
    """Verifies inventory depletion velocity calculation."""

    @pytest.fixture
    def model(self):
        return BorrowDynamicsModel()

    def test_scalar_velocity(self, model):
        v = model.calculate_inventory_depletion_velocity(0.08)
        assert v == pytest.approx(0.08, abs=1e-6)

    def test_history_series_depletion(self, model):
        # Series increasing from 0.50 to 0.70 over 5 days (dt=1.0)
        history = [0.50, 0.55, 0.60, 0.65, 0.70]
        v = model.calculate_inventory_depletion_velocity(history, dt_days=1.0)
        # Delta = (0.70 - 0.50) / 4 = 0.05 per day
        assert v == pytest.approx(0.05, abs=1e-6)

    def test_empty_or_single_item_series(self, model):
        assert model.calculate_inventory_depletion_velocity([]) == 0.0
        assert model.calculate_inventory_depletion_velocity([0.80]) == 0.0


# =============================================================================
# 5. SEC Rule 203(b)(1) Affirmative Locate Tests
# =============================================================================

class TestAffirmativeLocateTracking:
    """Verifies locate availability, fraction scoring, and audit ledger tracking."""

    @pytest.fixture
    def model(self):
        return BorrowDynamicsModel()

    def test_unconstrained_locate_approved(self, model):
        res = model.check_locate_availability(
            symbol="AAPL",
            requested_shares=10_000,
            lendable_shares=1_000_000,
            shares_on_loan=200_000,  # 20% utilization
            depletion_velocity=0.0,
            market="NASDAQ",
        )
        assert res.locate_approved is True
        assert res.locate_fraction > 0.70
        assert res.available_shares >= 500_000
        assert res.locate_id.startswith("LOC_AAPL_")
        assert "Affirmative locate confirmed" in res.reason

    def test_saturated_inventory_blocks_locate(self, model):
        # Utilization >= 98% strictly blocks locate under Rule 203(b)(1)
        res = model.check_locate_availability(
            symbol="GME",
            requested_shares=100,
            lendable_shares=1_000_000,
            shares_on_loan=985_000,  # 98.5% utilization
            depletion_velocity=0.05,
            market="SP500",
        )
        assert res.locate_approved is False
        assert res.locate_fraction == 0.0
        assert "Inventory saturated" in res.reason or "Locate pool exhausted" in res.reason

    def test_insufficient_volume_blocks_locate(self, model):
        # Pool has 5,000 available, but trader requests 50,000
        res = model.check_locate_availability(
            symbol="AMC",
            requested_shares=50_000,
            lendable_shares=100_000,
            shares_on_loan=95_000,
            depletion_velocity=0.01,
            market="SP500",
        )
        assert res.locate_approved is False
        assert "Insufficient lendable volume" in res.reason

    def test_locate_ledger_auditing(self, model):
        model.check_locate_availability("TSLA", 1000, 100_000, 10_000)
        model.check_locate_availability("TSLA", 2000, 100_000, 12_000)

        ledger = model._locate_ledger.get("TSLA", [])
        assert len(ledger) == 2
        assert ledger[0].requested_shares == 1000
        assert ledger[1].requested_shares == 2000


# =============================================================================
# 6. Days-to-Cover (DTC) & Short Interest Ratio (SIR) Tests
# =============================================================================

class TestShortInterestMetrics:
    """Verifies SIR and DTC calculations."""

    @pytest.fixture
    def model(self):
        return BorrowDynamicsModel()

    def test_standard_metrics(self, model):
        sir, dtc = model.calculate_short_interest_metrics(
            short_interest_shares=2_000_000,
            public_float_shares=10_000_000,
            adv_20d=500_000,
        )
        assert sir == pytest.approx(0.20, abs=1e-6)  # 20% of float
        assert dtc == pytest.approx(4.0, abs=1e-6)   # 4 days to cover

    def test_division_by_zero_safety(self, model):
        sir, dtc = model.calculate_short_interest_metrics(
            short_interest_shares=100_000,
            public_float_shares=0.0,
            adv_20d=0.0,
        )
        assert sir == 0.0
        assert dtc == 99.0  # Safe finite high fallback when short interest exists without ADV


# =============================================================================
# 7. Recall Risk Scoring Tests
# =============================================================================

class TestRecallRiskScoring:
    """Verifies calibrated logistic recall probability model."""

    @pytest.fixture
    def model(self):
        return BorrowDynamicsModel()

    def test_low_recall_risk_uncrowded(self, model):
        # Low utilization (30%), zero depletion velocity, low DTC (1.5 days), no momentum
        r = model.calculate_recall_risk_score(
            utilization=0.30,
            depletion_velocity=0.0,
            dtc=1.5,
            upward_momentum=0.0,
        )
        assert 0.0 <= r < 0.20

    def test_high_recall_risk_crowded(self, model):
        # Extreme utilization (95%), rapid depletion (0.10/day), high DTC (9.0 days), strong momentum (+15%)
        r = model.calculate_recall_risk_score(
            utilization=0.95,
            depletion_velocity=0.10,
            dtc=9.0,
            upward_momentum=0.15,
        )
        assert r > 0.75

    def test_monotonicity(self, model):
        r1 = model.calculate_recall_risk_score(0.70, 0.0, 3.0, 0.0)
        r2 = model.calculate_recall_risk_score(0.85, 0.0, 3.0, 0.0)
        r3 = model.calculate_recall_risk_score(0.85, 0.05, 3.0, 0.0)
        r4 = model.calculate_recall_risk_score(0.85, 0.05, 6.0, 0.0)
        r5 = model.calculate_recall_risk_score(0.85, 0.05, 6.0, 0.05)

        assert r1 < r2 < r3 < r4 < r5


# =============================================================================
# 8. Negative Carry Drag Tests
# =============================================================================

class TestNegativeCarryDrag:
    """Verifies negative carry drag subtraction and hurdle evaluation."""

    @pytest.fixture
    def model(self):
        return BorrowDynamicsModel()

    def test_viable_general_collateral_short(self, model):
        # Base GC rate 0.50% p.a., 20 days hold, gross expected short alpha 3.0% (300 bps)
        res = model.calculate_negative_carry(
            borrow_fee_annual=0.005,
            holding_days=20.0,
            expected_alpha=0.030,
            hurdle_rate=0.0010,
        )
        # Drag = 0.005 * (20 / 252) = 0.0003968 (approx 4 bps)
        assert res.holding_period_cost == pytest.approx(0.005 * (20 / 252), rel=1e-4)
        assert res.net_alpha == pytest.approx(0.030 - res.holding_period_cost, rel=1e-4)
        assert res.is_economically_viable is True

    def test_unviable_hard_to_borrow_short(self, model):
        # HTB rate 60% p.a. (0.60), 20 days hold, gross expected alpha 2.0% (200 bps)
        res = model.calculate_negative_carry(
            borrow_fee_annual=0.60,
            holding_days=20.0,
            expected_alpha=0.020,
            hurdle_rate=0.0010,
        )
        # Drag = 0.60 * (20 / 252) = 0.0476 (approx 476 bps drag!)
        # Net alpha = 200 bps - 476 bps = -276 bps (negative EV)
        assert res.net_alpha < 0.0
        assert res.is_economically_viable is False


# =============================================================================
# 9. Explosive Short Squeeze Catalyst Trigger Tests
# =============================================================================

class TestShortSqueezeScoreAndTrigger:
    """Verifies composite squeeze score and catalyst trigger."""

    @pytest.fixture
    def model(self):
        return BorrowDynamicsModel()

    def test_low_squeeze_baseline(self, model):
        score = model.calculate_squeeze_score(
            sir=0.02,
            dtc=1.0,
            utilization=0.30,
            upward_momentum=-0.02,
            relative_volume=0.8,
        )
        assert 0.0 <= score < 0.35

    def test_explosive_short_squeeze_trigger(self, model):
        # Heavy short interest (30%), long DTC (8 days), 95% utilization, +12% 5-day breakout, 3x volume
        score = model.calculate_squeeze_score(
            sir=0.30,
            dtc=8.0,
            utilization=0.95,
            upward_momentum=0.12,
            relative_volume=3.0,
        )
        assert score >= 0.75

        eval_res = model.evaluate_squeeze_catalyst(
            symbol="SPCE",
            market="SP500",
            borrow_quote=BorrowFeeQuote(
                symbol="SPCE",
                short_interest_ratio=0.30,
                days_to_cover=8.0,
                utilization_rate=0.95,
                borrow_fee_annual=0.45,
                locate_available=True,
                locate_fraction=0.10,
            ),
            upward_momentum=0.12,
            relative_volume=3.0,
        )
        assert eval_res.is_squeeze_triggered is True
        assert eval_res.squeeze_score >= 0.75
        assert eval_res.recommended_action == "BLOCK_SHORT"
        assert eval_res.gate_8_1_status == "REJECTED"
        assert eval_res.rejection_reason == "SHORT_SQUEEZE_BREAKOUT_RISK"


# =============================================================================
# 10. ExecutionOMSEngine Gate 8.1 Tests
# =============================================================================

class TestOMSEngineGate8_1:
    """Verifies Gate 8.1 rules for short orders, buy orders, and squeeze catalyst modifications."""

    @pytest.fixture
    def model(self):
        return BorrowDynamicsModel()

    def test_naked_short_blocked_by_locate_absence(self, model):
        # Short order without affirmative locate -> REJECTED
        order = {"symbol": "MEME", "action": "SHORT", "market": "NASDAQ", "target_price": 50.0}
        quote = BorrowFeeQuote(
            symbol="MEME",
            utilization_rate=0.99,
            locate_available=False,
            locate_fraction=0.0,
            borrow_fee_annual=0.80,
        )
        verdict = model.evaluate_gate_8_1(order=order, borrow_quote=quote)

        assert verdict.status == "REJECTED"
        assert verdict.reason == "NO_AFFIRMATIVE_LOCATE"

    def test_negative_carry_short_blocked(self, model):
        # Short order where borrow fee destroys expected alpha -> REJECTED
        order = {
            "symbol": "HARD",
            "action": "SELL_SHORT",
            "market": "SP500",
            "expected_return": 0.015,  # 150 bps alpha
            "target_price": 100.0,
        }
        quote = BorrowFeeQuote(
            symbol="HARD",
            utilization_rate=0.90,
            locate_available=True,
            locate_fraction=0.20,
            borrow_fee_annual=0.50,  # 50% p.a. borrow fee
        )
        verdict = model.evaluate_gate_8_1(order=order, borrow_quote=quote)

        assert verdict.status == "REJECTED"
        assert verdict.reason == "NEGATIVE_CARRY_DRAG"

    def test_short_into_squeeze_breakout_blocked(self, model):
        # Short order into squeeze breakout (S_squeeze >= 0.70) -> REJECTED
        order = {
            "symbol": "SQZ",
            "action": "SHORT",
            "market": "SP500",
            "expected_return": 0.05,
            "target_price": 40.0,
        }
        quote = BorrowFeeQuote(
            symbol="SQZ",
            utilization_rate=0.85,
            locate_available=True,
            locate_fraction=0.15,
            borrow_fee_annual=0.15,
            short_interest_ratio=0.28,
            days_to_cover=6.5,
        )
        squeeze_eval = SqueezeEvaluationResult(
            symbol="SQZ",
            market="SP500",
            squeeze_score=0.78,
            is_squeeze_triggered=True,
            negative_carry_bps=4.1,
            net_alpha_after_carry=0.038,
            recall_risk=0.60,
            recommended_action="BLOCK_SHORT",
            gate_8_1_status="REJECTED",
            rejection_reason="SHORT_SQUEEZE_BREAKOUT_RISK",
        )
        verdict = model.evaluate_gate_8_1(order=order, borrow_quote=quote, squeeze_eval=squeeze_eval)

        assert verdict.status == "REJECTED"
        assert verdict.reason == "SHORT_SQUEEZE_BREAKOUT_RISK"

    def test_acute_recall_risk_short_blocked(self, model):
        # Short order with acute recall probability (>= 0.80) -> REJECTED
        order = {"symbol": "CALL", "action": "SHORT", "market": "SP500", "expected_return": 0.08}
        quote = BorrowFeeQuote(
            symbol="CALL",
            utilization_rate=0.96,
            locate_available=True,
            locate_fraction=0.10,
            borrow_fee_annual=0.20,
            recall_risk_score=0.88,  # Acute recall risk
        )
        squeeze_eval = SqueezeEvaluationResult(
            symbol="CALL",
            market="SP500",
            squeeze_score=0.55,
            is_squeeze_triggered=False,
            negative_carry_bps=5.5,
            net_alpha_after_carry=0.064,
            recall_risk=0.88,
            recommended_action="RECALL_COVER",
            gate_8_1_status="REJECTED",
            rejection_reason="ACUTE_RECALL_RISK",
        )
        verdict = model.evaluate_gate_8_1(order=order, borrow_quote=quote, squeeze_eval=squeeze_eval)

        assert verdict.status == "REJECTED"
        assert verdict.reason == "ACUTE_RECALL_RISK"

    def test_compliant_short_approved(self, model):
        # Low utilization, abundant locate, positive net alpha -> APPROVED
        order = {"symbol": "BEAR", "action": "SHORT", "market": "SP500", "expected_return": 0.05}
        quote = BorrowFeeQuote(
            symbol="BEAR",
            utilization_rate=0.35,
            locate_available=True,
            locate_fraction=0.90,
            borrow_fee_annual=0.003,
            recall_risk_score=0.15,
        )
        verdict = model.evaluate_gate_8_1(order=order, borrow_quote=quote)

        assert verdict.status == "APPROVED"
        assert verdict.reason is None
        assert verdict.recommended_sleeve == "DEFENSIVE_SHORT"
        assert verdict.recommended_exec_strategy == "FAST_LIMIT"

    def test_long_squeeze_breakout_accelerated(self, model):
        # Long BUY order on explosive squeeze breakout (S_squeeze >= 0.75) -> MODIFIED to MOMENTUM_SQUEEZE
        order = {
            "symbol": "SQZ_LONG",
            "action": "BUY",
            "market": "SP500",
            "target_price": 100.0,
            "expected_return": 0.10,
        }
        quote = BorrowFeeQuote(
            symbol="SQZ_LONG",
            utilization_rate=0.92,
            depletion_velocity=0.08,
            borrow_fee_annual=0.50,
        )
        squeeze_eval = SqueezeEvaluationResult(
            symbol="SQZ_LONG",
            market="SP500",
            squeeze_score=0.82,
            is_squeeze_triggered=True,
            negative_carry_bps=13.7,
            net_alpha_after_carry=0.06,
            recall_risk=0.72,
            recommended_action="PASS",
            gate_8_1_status="APPROVED",
        )
        verdict = model.evaluate_gate_8_1(order=order, borrow_quote=quote, squeeze_eval=squeeze_eval)

        assert verdict.status == "MODIFIED"
        assert verdict.recommended_sleeve == "MOMENTUM_SQUEEZE"
        assert verdict.recommended_exec_strategy == "AGGRESSIVE_TAKER"
        assert verdict.target_stop_loss == pytest.approx(95.0, abs=1e-4)  # 5% protective stop
        assert verdict.slice_count_multiplier == 0.5


# =============================================================================
# 11. Functional Convenience Interfaces & Serialization Tests
# =============================================================================

class TestConvenienceInterfacesAndSerialization:
    """Verifies functional entry points and serialization fidelity."""

    def test_calculate_borrow_fee_functional(self):
        f = calculate_borrow_fee(utilization=0.40, market="SP500")
        assert f == pytest.approx(0.0030, abs=1e-6)

    def test_evaluate_short_squeeze_risk_functional(self):
        res = evaluate_short_squeeze_risk(
            symbol="TEST",
            market="SP500",
            loan_shares=500_000,
            lendable_shares=1_000_000,
            short_interest=150_000,
            public_float=1_000_000,
            adv_20d=50_000,
            upward_momentum=0.05,
            relative_volume=1.8,
        )
        assert isinstance(res, SqueezeEvaluationResult)
        assert res.symbol == "TEST"
        assert 0.0 <= res.squeeze_score <= 1.0

    def test_dataclass_serialization(self):
        quote = BorrowFeeQuote(symbol="NVDA", market="NASDAQ", utilization_rate=0.75)
        d = quote.to_dict()
        assert d["symbol"] == "NVDA"
        assert d["market"] == "NASDAQ"
        assert d["utilization_rate"] == 0.75

        verdict = Gate8_1Verdict(
            symbol="NVDA",
            action="BUY",
            status="APPROVED",
            borrow_quote=quote,
        )
        vd = verdict.to_dict()
        assert vd["symbol"] == "NVDA"
        assert vd["status"] == "APPROVED"
        assert vd["borrow_quote"]["symbol"] == "NVDA"
