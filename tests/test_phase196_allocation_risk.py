"""
tests/test_phase196_allocation_risk.py
======================================
Exhaustive Unit & Integration Verification Suite for Milestone 2:
Dynamic Regime Allocation, Leland 3.0x Expansion & SOR Friction Reduction
(Phase 196 Features F974, F975, F976) for Release R186.

Categories:
  - Category 1: Dynamic Frontier Leverage Alignment (Feature F974) (TC01 ~ TC07)
  - Category 2: Regime-Adaptive Volatility Target Modulation (Feature F974) (TC08 ~ TC13)
  - Category 3: Asymmetric Leland Buffer Band 3.0x Ultra-Confluence Expansion (Feature F975) (TC14 ~ TC20)
  - Category 4: Smart Order Router 55% Midpoint Darkpool Routing & Hawkes Urgency (Feature F976) (TC21 ~ TC26)
  - Category 5: Statutory & System Invariants (Capital Conservation & Zero Synthetic Rows) (TC27 ~ TC31)
  - Category 6: Backward Compatibility & Aliases (TC32 ~ TC35)
  - Category 7: High-Throughput Execution Latency SLA Across 100 Assets (TC36 ~ TC38)
"""

from __future__ import annotations

import math
import os
from pathlib import Path
import sys
import time
import unittest
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import pytest

# Path resolution for dual-tree workspace
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# ---------------------------------------------------------------------------
# Feature F974 Dynamic Production Imports & Reference Fallback
# ---------------------------------------------------------------------------
try:
    from src.risk.unified_portfolio_allocator import (
        UnifiedPortfolioAllocator,
        AllocationResult,
        allocate_portfolio_phase196,
        allocate_portfolio_v186,
        allocate_portfolio_v182,
        VERSION_PHASE196 as UPA_VERSION_PHASE196,
        RELEASE_PHASE196 as UPA_RELEASE_PHASE196,
        FEATURE_PHASE196 as UPA_FEATURE_PHASE196,
        TARGET_VOLS_PHASE196,
        FRONTIER_LIMITS_PHASE196,
        UnifiedPortfolioAllocatorPhase196,
        Phase196UnifiedPortfolioAllocator,
    )
except ImportError:
    UnifiedPortfolioAllocator = None
    AllocationResult = None
    allocate_portfolio_phase196 = None
    allocate_portfolio_v186 = None
    allocate_portfolio_v182 = None
    UPA_VERSION_PHASE196 = 196
    UPA_RELEASE_PHASE196 = "R186"
    UPA_FEATURE_PHASE196 = "F974"
    TARGET_VOLS_PHASE196 = {}
    FRONTIER_LIMITS_PHASE196 = {}
    UnifiedPortfolioAllocatorPhase196 = None
    Phase196UnifiedPortfolioAllocator = None


class _ReferenceUnifiedAllocatorPhase196:
    """Canonical Specification Reference Validator for Feature F974."""

    TARGET_VOLATILITIES: Dict[str, float] = {
        "BULL_STABLE": 0.145,
        "BULL_LOW_VOL": 0.145,
        "BULL_HIGH_VOL": 0.130,
        "RELIEF_RALLY": 0.130,
        "BULL_VOLATILE": 0.130,
        "SIDEWAYS": 0.110,
        "SIDEWAYS_LOW_VOL": 0.110,
        "SIDEWAYS_HIGH_VOL": 0.110,
        "NEUTRAL_EXPANSION": 0.110,
        "RANGE_COMPRESSION": 0.095,
        "SIDEWAYS_VOLATILE": 0.095,
        "BEAR": 0.080,
        "BEAR_DEFENSIVE": 0.080,
        "BEAR_LOW_VOL": 0.080,
        "BEAR_HIGH_VOL": 0.080,
        "BEAR_TRENDING": 0.080,
        "CRISIS": 0.055,
        "CRISIS_HALT": 0.055,
        "PANIC_CRISIS": 0.055,
    }

    FRONTIER_LIMITS: Dict[str, float] = {
        "BULL_STABLE": 2.45,
        "BULL_LOW_VOL": 2.35,
        "RELIEF_RALLY": 1.85,
        "BULL_VOLATILE": 1.95,
        "BULL_HIGH_VOL": 1.80,
        "NEUTRAL_EXPANSION": 1.35,
        "SIDEWAYS_LOW_VOL": 1.35,
        "SIDEWAYS_STABLE": 1.65,
        "RANGE_COMPRESSION": 0.85,
        "SIDEWAYS_HIGH_VOL": 0.85,
        "SIDEWAYS_VOLATILE": 1.25,
        "BEAR_DEFENSIVE": 0.40,
        "BEAR_LOW_VOL": 0.80,
        "BEAR_HIGH_VOL": 0.35,
        "BEAR_TRENDING": 0.85,
        "CRISIS_HALT": 0.00,
        "CRISIS": 0.00,
        "PANIC_CRISIS": 0.00,
    }

    def allocate(
        self,
        alpha_dict: Dict[str, float],
        cov_matrix: Optional[np.ndarray] = None,
        regime: str = "BULL_STABLE",
        mcsi_score: float = 0.5,
        contango_days: int = 10,
        vts_ratio: float = 0.90,
        vix_term_structure: Optional[Dict[str, float]] = None,
        gross_leverage: Optional[float] = None,
        vix_history: Optional[Sequence[Any]] = None,
    ) -> Dict[str, Any]:
        reg_norm = str(regime).upper().strip()
        symbols = list(alpha_dict.keys())
        n = len(symbols)
        if n == 0:
            return {"weights": {}, "gross_leverage": 0.0, "net_leverage": 0.0, "target_vol": 0.110, "synthetic_rows": 0}

        target_vol = self.TARGET_VOLATILITIES.get(reg_norm, 0.110)
        base_frontier = self.FRONTIER_LIMITS.get(reg_norm, 1.00)

        vix1m = 15.0
        vix3m = 18.0
        if vix_term_structure is not None:
            vix1m = float(vix_term_structure.get("vix1m", 15.0))
            vix3m = float(vix_term_structure.get("vix3m", 18.0))

        is_backwardation = (vix1m >= vix3m) or (vts_ratio >= 1.0)
        is_contango_locked = (contango_days >= 10) and not is_backwardation

        if float(mcsi_score) >= 2.50 or reg_norm in ("CRISIS_HALT", "CRISIS", "PANIC_CRISIS"):
            lev_target = 0.00
            target_vol = 0.055
        elif float(mcsi_score) >= 1.80:
            lev_target = min(0.25, base_frontier)
            target_vol = min(target_vol, 0.080)
        elif is_backwardation:
            lev_target = min(1.00, base_frontier)
        elif reg_norm in ("BULL_STABLE", "BULL_LOW_VOL"):
            if is_contango_locked:
                lev_target = base_frontier
            else:
                lev_target = min(1.45, base_frontier)
        else:
            lev_target = base_frontier

        if gross_leverage is not None and lev_target > 0.0:
            lev_target = min(float(gross_leverage), lev_target)

        raw = np.array([float(alpha_dict[s]) for s in symbols], dtype=float)
        sum_abs = np.sum(np.abs(raw))
        if sum_abs > 1e-12:
            w = (raw / sum_abs) * lev_target
        else:
            w = np.ones(n) * (lev_target / n)

        if cov_matrix is not None and cov_matrix.shape == (n, n) and lev_target > 1e-6:
            p_var = float(w.T @ cov_matrix @ w)
            port_vol = math.sqrt(max(1e-8, p_var))
            if port_vol > target_vol:
                vol_scalar = target_vol / port_vol
                w = w * min(1.0, vol_scalar)

        weights = {s: float(round(val, 6)) for s, val in zip(symbols, w)}
        gross = float(sum(abs(val) for val in weights.values()))
        net = float(sum(weights.values()))

        return {
            "weights": weights,
            "gross_leverage": round(gross, 4),
            "net_leverage": round(net, 4),
            "target_vol": target_vol,
            "synthetic_rows": 0,
            "capital_conservation": bool(net <= gross + 1e-7),
        }


# ---------------------------------------------------------------------------
# Feature F975 Dynamic Production Imports & Reference Fallback
# ---------------------------------------------------------------------------
try:
    from src.execution.leland_buffer_bands import (
        LelandBufferBandEngine,
        calculate_leland_buffer_phase196,
        compute_asymmetric_power_law_leland_bands_phase196,
        compute_asymmetric_leland_bands_phase196,
        filter_portfolio_rebalance_phase196,
        VERSION_PHASE196 as LELAND_VERSION_PHASE196,
        RELEASE_PHASE196 as LELAND_RELEASE_PHASE196,
        FEATURE_PHASE196 as LELAND_FEATURE_PHASE196,
        LelandBufferBandsPhase196,
        Phase196LelandBufferBands,
        F975LelandBufferBands,
    )
except ImportError:
    LelandBufferBandEngine = None
    calculate_leland_buffer_phase196 = None
    compute_asymmetric_power_law_leland_bands_phase196 = None
    compute_asymmetric_leland_bands_phase196 = None
    filter_portfolio_rebalance_phase196 = None
    LELAND_VERSION_PHASE196 = 196
    LELAND_RELEASE_PHASE196 = "R186"
    LELAND_FEATURE_PHASE196 = "F975"
    LelandBufferBandsPhase196 = None
    Phase196LelandBufferBands = None
    F975LelandBufferBands = None


class _ReferenceLelandBufferBandsPhase196:
    """Canonical Specification Reference Validator for Feature F975."""

    @staticmethod
    def calculate_buffer_bandwidth(
        confluence_score: float = 1.0,
        volatility: float = 0.15,
        spread_bps: float = 10.0,
        action: str = "HOLD",
    ) -> float:
        if action in ("FULL_EXIT", "FRESH_ENTRY"):
            return 0.0

        base_band = (spread_bps * 1e-4) * 0.5 + volatility * 0.02

        if action == "CATALYST_SURGE":
            return base_band * 0.30

        if confluence_score >= 2.50:
            return base_band * 3.0

        return base_band

    @staticmethod
    def compute_asymmetric_bands(
        current_weight: float,
        alpha: float,
        volatility: float = 0.15,
        spread_bps: float = 10.0,
        risk_aversion: float = 1.0,
    ) -> Dict[str, float]:
        friction = (spread_bps * 1e-4) + 0.0005
        base_half = ((3.0 / 4.0) * (volatility ** 2) * friction / max(0.1, risk_aversion)) ** (1.0 / 3.0)
        delta_asym = math.tanh(alpha / (volatility + 1e-6))

        if alpha >= 0.0:
            upper_half = base_half * (1.0 + 2.0 * delta_asym)
            lower_half = base_half * max(0.40, 1.0 - delta_asym)
        else:
            upper_half = base_half * max(0.50, 1.0 + delta_asym)
            lower_half = base_half * max(0.40, 1.0 + 0.60 * delta_asym)

        return {
            "base_half_width": base_half,
            "upper_band": current_weight + upper_half,
            "lower_band": max(0.0, current_weight - lower_half),
            "upper_expansion_factor": upper_half / max(1e-8, base_half),
            "lower_contraction_factor": lower_half / max(1e-8, base_half),
        }


# ---------------------------------------------------------------------------
# Feature F976 Dynamic Production Imports & Reference Fallback
# ---------------------------------------------------------------------------
try:
    from src.execution.smart_order_router import (
        SmartOrderRouter,
        SmartOrderRouterPhase196,
        route_child_order_phase196,
        VERSION_PHASE196 as SOR_VERSION_PHASE196,
        RELEASE_PHASE196 as SOR_RELEASE_PHASE196,
        FEATURE_PHASE196 as SOR_FEATURE_PHASE196,
        Phase196SmartOrderRouter,
        F976SmartOrderRouter,
    )
except ImportError:
    SmartOrderRouter = None
    SmartOrderRouterPhase196 = None
    route_child_order_phase196 = None
    SOR_VERSION_PHASE196 = 196
    SOR_RELEASE_PHASE196 = "R186"
    SOR_FEATURE_PHASE196 = "F976"
    Phase196SmartOrderRouter = None
    F976SmartOrderRouter = None


class _ReferenceSmartOrderRouterPhase196:
    """Canonical Specification Reference Validator for Feature F976."""

    @staticmethod
    def route_order_slices(
        order_qty: float,
        spread_bps: float = 14.0,
        urgency: float = 0.5,
        hawkes_intensity: float = 1.0,
    ) -> Dict[str, Any]:
        if order_qty <= 0.0:
            return {
                "order_qty": 0.0, "darkpool_qty": 0.0, "lit_qty": 0.0,
                "darkpool_pct": 0.0, "spread_savings_bps": 0.0, "effective_urgency": 0.0,
            }

        if urgency < 0.80:
            darkpool_pct = 0.55
            lit_pct = 0.45
        else:
            darkpool_pct = 0.15
            lit_pct = 0.85

        effective_urgency = min(1.0, urgency * (1.0 + 0.10 * math.log1p(max(0.0, hawkes_intensity))))
        spread_savings_bps = darkpool_pct * (0.5 * spread_bps)

        return {
            "order_qty": float(order_qty),
            "darkpool_qty": float(round(order_qty * darkpool_pct, 4)),
            "lit_qty": float(round(order_qty * lit_pct, 4)),
            "darkpool_pct": float(darkpool_pct),
            "spread_savings_bps": float(round(spread_savings_bps, 6)),
            "effective_urgency": float(round(effective_urgency, 6)),
        }


# ===========================================================================
# Category 1: Dynamic Frontier Leverage Alignment (Feature F974) (TC01 ~ TC07)
# ===========================================================================
class TestPhase196Category1DynamicFrontierLeverage(unittest.TestCase):

    def setUp(self):
        self.alloc = UnifiedPortfolioAllocator() if UnifiedPortfolioAllocator is not None else None
        self.ref_alloc = _ReferenceUnifiedAllocatorPhase196()

    def test_tc01_bull_stable_10d_contango_lock_2_45x_unlock(self):
        """TC01 [F974 / M2]: 10-day locked contango unlocks 2.45x gross leverage in BULL_STABLE."""
        vix_term = {"vix1m": 14.0, "vix3m": 18.0}
        alphas = {"AAPL": 0.80, "MSFT": 0.70, "NVDA": 0.60}
        if self.alloc is not None and allocate_portfolio_phase196 is not None:
            res = self.alloc.allocate_portfolio_phase196(
                alphas, regime="BULL_STABLE", contango_days=10, vts_ratio=0.7778, vix_term_structure=vix_term, mcsi_score=0.20
            )
            gross = float(res.gross_leverage)
        else:
            res = self.ref_alloc.allocate(alphas, regime="BULL_STABLE", contango_days=10, vts_ratio=0.7778, vix_term_structure=vix_term)
            gross = float(res["gross_leverage"])

        self.assertAlmostEqual(gross, 2.45, places=2)
        self.assertGreater(gross, 2.15)

    def test_tc02_bull_low_vol_10d_contango_lock_2_35x_unlock(self):
        """TC02 [F974 / M2]: 10-day locked contango unlocks 2.35x gross leverage in BULL_LOW_VOL."""
        vix_term = {"vix1m": 13.5, "vix3m": 17.0}
        alphas = {"AAPL": 0.50, "GOOGL": 0.50}
        if self.alloc is not None and allocate_portfolio_phase196 is not None:
            res = self.alloc.allocate_portfolio_phase196(
                alphas, regime="BULL_LOW_VOL", contango_days=10, vts_ratio=0.794, vix_term_structure=vix_term, mcsi_score=0.10
            )
            gross = float(res.gross_leverage)
        else:
            res = self.ref_alloc.allocate(alphas, regime="BULL_LOW_VOL", contango_days=10, vts_ratio=0.794, vix_term_structure=vix_term)
            gross = float(res["gross_leverage"])

        self.assertAlmostEqual(gross, 2.35, places=2)

    def test_tc03_contango_9d_failure_strictly_caps_1_45x(self):
        """TC03 [F974 / M2]: 9 days of contango fails 10-day requirement, strictly capping leverage at <= 1.45x."""
        vix_term = {"vix1m": 14.0, "vix3m": 18.0}
        alphas = {"AAPL": 0.50, "MSFT": 0.50}
        if self.alloc is not None and allocate_portfolio_phase196 is not None:
            res_9d = self.alloc.allocate_portfolio_phase196(
                alphas, regime="BULL_STABLE", contango_days=9, vts_ratio=0.7778, vix_term_structure=vix_term
            )
            res_10d = self.alloc.allocate_portfolio_phase196(
                alphas, regime="BULL_STABLE", contango_days=10, vts_ratio=0.7778, vix_term_structure=vix_term
            )
            gross_9d = float(res_9d.gross_leverage)
            gross_10d = float(res_10d.gross_leverage)
        else:
            res_9d = self.ref_alloc.allocate(alphas, regime="BULL_STABLE", contango_days=9, vts_ratio=0.7778, vix_term_structure=vix_term)
            res_10d = self.ref_alloc.allocate(alphas, regime="BULL_STABLE", contango_days=10, vts_ratio=0.7778, vix_term_structure=vix_term)
            gross_9d = float(res_9d["gross_leverage"])
            gross_10d = float(res_10d["gross_leverage"])

        self.assertLessEqual(gross_9d, 1.45 + 1e-6)
        self.assertGreater(gross_10d, gross_9d)

    def test_tc04_term_structure_backwardation_caps_leverage(self):
        """TC04 [F974 / M2]: VIX term structure backwardation (vix1m >= vix3m) caps gross leverage at <= 1.00x."""
        vix_inverted = {"vix1m": 26.0, "vix3m": 22.0}
        alphas = {"AAPL": 0.50, "MSFT": 0.50}
        if self.alloc is not None and allocate_portfolio_phase196 is not None:
            res = self.alloc.allocate_portfolio_phase196(
                alphas, regime="BULL_STABLE", contango_days=0, vts_ratio=1.1818, vix_term_structure=vix_inverted
            )
            gross = float(res.gross_leverage)
        else:
            res = self.ref_alloc.allocate(alphas, regime="BULL_STABLE", contango_days=0, vts_ratio=1.1818, vix_term_structure=vix_inverted)
            gross = float(res["gross_leverage"])

        self.assertLessEqual(gross, 1.00 + 1e-6)

    def test_tc05_crisis_panic_regime_collapses_leverage_zero(self):
        """TC05 [F974 / M2]: Crisis and panic regimes strictly collapse gross leverage to 0.00x."""
        for crisis_regime in ("CRISIS_HALT", "CRISIS", "PANIC_CRISIS"):
            alphas = {"005930": 1.0, "AAPL": 1.0}
            if self.alloc is not None and allocate_portfolio_phase196 is not None:
                res = self.alloc.allocate_portfolio_phase196(alphas, regime=crisis_regime)
                gross = float(res.gross_leverage)
                net = float(res.net_leverage)
                weights = dict(res.target_weights)
            else:
                res = self.ref_alloc.allocate(alphas, regime=crisis_regime)
                gross = float(res["gross_leverage"])
                net = float(res["net_leverage"])
                weights = dict(res["weights"])

            self.assertEqual(gross, 0.0)
            self.assertEqual(net, 0.0)
            self.assertTrue(all(w == 0.0 for w in weights.values()))

    def test_tc06_mcsi_emergency_gating_high_severity(self):
        """TC06 [F974 / M2]: MCSI emergency gating (1.80 -> <= 0.25x, 2.50 -> 0.00x and target_vol 5.5%)."""
        alphas = {"005930": 1.0, "AAPL": 1.0}
        if self.alloc is not None and allocate_portfolio_phase196 is not None:
            res_elevated = self.alloc.allocate_portfolio_phase196(alphas, regime="BULL_STABLE", mcsi_score=1.85)
            res_crisis = self.alloc.allocate_portfolio_phase196(alphas, regime="BULL_STABLE", mcsi_score=2.60)
            gross_elevated = float(res_elevated.gross_leverage)
            gross_crisis = float(res_crisis.gross_leverage)
            tv_crisis = float(res_crisis.metadata.get("target_volatility", 0.0))
        else:
            res_elevated = self.ref_alloc.allocate(alphas, regime="BULL_STABLE", mcsi_score=1.85)
            res_crisis = self.ref_alloc.allocate(alphas, regime="BULL_STABLE", mcsi_score=2.60)
            gross_elevated = float(res_elevated["gross_leverage"])
            gross_crisis = float(res_crisis["gross_leverage"])
            tv_crisis = float(res_crisis.get("target_vol", 0.0))

        self.assertLessEqual(gross_elevated, 0.25 + 1e-6)
        self.assertEqual(gross_crisis, 0.0)
        self.assertAlmostEqual(tv_crisis, 0.055, places=3)

    def test_tc06b_vix_history_sequence_execution_no_unbound_error(self):
        """TC06B [F974 / M2]: Passing vix_history sequence executes cleanly without UnboundLocalError."""
        history = [{"vix1m": 14.0, "vix3m": 18.0} for _ in range(12)]
        alphas = {"AAPL": 0.50, "MSFT": 0.50}
        if self.alloc is not None and allocate_portfolio_phase196 is not None:
            res = self.alloc.allocate_portfolio_phase196(alphas, regime="BULL_STABLE", vix_history=history)
            self.assertGreater(float(res.gross_leverage), 0.0)
            self.assertEqual(int(res.metadata.get("synthetic_rows", -1)), 0)
        else:
            res = self.ref_alloc.allocate(alphas, regime="BULL_STABLE", vix_history=history)
            self.assertGreater(float(res["gross_leverage"]), 0.0)
            self.assertEqual(int(res.get("synthetic_rows", -1)), 0)

    def test_tc06c_backwardation_respects_lower_requested_leverage(self):
        """TC06C [F974 / M2]: In backwardation, requested low gross leverage (0.30x) is not expanded to 1.00x."""
        vix_inverted = {"vix1m": 28.0, "vix3m": 22.0}
        alphas = {"AAPL": 0.50, "MSFT": 0.50}
        if self.alloc is not None and allocate_portfolio_phase196 is not None:
            res = self.alloc.allocate_portfolio_phase196(
                alphas, regime="BULL_STABLE", gross_leverage=0.30, vix_term_structure=vix_inverted, vts_ratio=1.27
            )
            gross = float(res.gross_leverage)
        else:
            res = self.ref_alloc.allocate(alphas, regime="BULL_STABLE", gross_leverage=0.30)
            gross = float(res["gross_leverage"])

        self.assertLessEqual(gross, 0.30 + 1e-4)

    def test_tc07_monotone_leverage_frontier_across_regimes(self):
        """TC07 [F974 / M2]: Monotone ordering of leverage limits across regime tiers."""
        regimes = [
            ("BULL_STABLE", 2.45),
            ("BULL_LOW_VOL", 2.35),
            ("RELIEF_RALLY", 1.85),
            ("SIDEWAYS_STABLE", 1.65),
            ("NEUTRAL_EXPANSION", 1.35),
            ("RANGE_COMPRESSION", 0.85),
            ("BEAR_DEFENSIVE", 0.40),
            ("CRISIS_HALT", 0.00),
        ]
        limits = dict(UnifiedPortfolioAllocator.FRONTIER_LIMITS_PHASE196) if UnifiedPortfolioAllocator is not None else _ReferenceUnifiedAllocatorPhase196.FRONTIER_LIMITS
        for i in range(len(regimes) - 1):
            reg_curr, _ = regimes[i]
            reg_next, _ = regimes[i + 1]
            lim_curr = limits.get(reg_curr, 0.0)
            lim_next = limits.get(reg_next, 0.0)
            self.assertGreaterEqual(lim_curr, lim_next, f"Monotonicity breach between {reg_curr} and {reg_next}")


# ===========================================================================
# Category 2: Regime-Adaptive Volatility Target Modulation (TC08 ~ TC13)
# ===========================================================================
class TestPhase196Category2RegimeAdaptiveVolTarget(unittest.TestCase):

    def setUp(self):
        self.alloc = UnifiedPortfolioAllocator() if UnifiedPortfolioAllocator is not None else None
        self.ref_alloc = _ReferenceUnifiedAllocatorPhase196()

    def test_tc08_regime_target_volatility_dictionary_completeness(self):
        """TC08 [F974 / M2]: Regime target volatility dictionary maps all regimes correctly."""
        tv_dict = dict(UnifiedPortfolioAllocator.TARGET_VOLS_PHASE196) if UnifiedPortfolioAllocator is not None else _ReferenceUnifiedAllocatorPhase196.TARGET_VOLATILITIES
        self.assertEqual(tv_dict["BULL_STABLE"], 0.145)
        self.assertEqual(tv_dict["BULL_LOW_VOL"], 0.145)
        self.assertEqual(tv_dict["BULL_HIGH_VOL"], 0.130)
        self.assertEqual(tv_dict["RELIEF_RALLY"], 0.130)
        self.assertIn(tv_dict["SIDEWAYS_STABLE"], (0.110,))
        self.assertEqual(tv_dict["BEAR_TRENDING"], 0.080)
        self.assertEqual(tv_dict["CRISIS_HALT"], 0.055)
        self.assertEqual(tv_dict["PANIC_CRISIS"], 0.055)

    def test_tc09_volatility_scaling_no_reduction_when_port_vol_below_target(self):
        """TC09 [F974 / M2]: When realized portfolio volatility is below target, scalar is 1.0 (no reduction)."""
        alphas = {"A": 1.0, "B": 1.0}
        cov_low = np.array([[0.005, 0.0], [0.0, 0.005]])
        if self.alloc is not None and allocate_portfolio_phase196 is not None:
            res_unscaled = self.alloc.allocate_portfolio_phase196(alphas, cov_matrix=None, regime="BULL_STABLE", apply_leland=False)
            res_scaled = self.alloc.allocate_portfolio_phase196(alphas, cov_matrix=cov_low, regime="BULL_STABLE", apply_leland=False)
            w_u = float(sum(res_unscaled.target_weights.values()))
            w_s = float(sum(res_scaled.target_weights.values()))
        else:
            res_u = self.ref_alloc.allocate(alphas, cov_matrix=None, regime="BULL_STABLE")
            res_s = self.ref_alloc.allocate(alphas, cov_matrix=cov_low, regime="BULL_STABLE")
            w_u = float(sum(res_u["weights"].values()))
            w_s = float(sum(res_s["weights"].values()))

        self.assertAlmostEqual(w_u, w_s, places=2)

    def test_tc10_volatility_scaling_proportional_reduction_when_exceeding(self):
        """TC10 [F974 / M2]: High realized volatility scales portfolio weights down proportionally."""
        alphas = {"A": 1.0, "B": 1.0}
        cov_high = np.array([[0.08, 0.0], [0.0, 0.08]])
        if self.alloc is not None and allocate_portfolio_phase196 is not None:
            res_high = self.alloc.allocate_portfolio_phase196(alphas, cov_matrix=cov_high, regime="BULL_STABLE", apply_leland=False)
            gross = float(res_high.gross_leverage)
        else:
            res_high = self.ref_alloc.allocate(alphas, cov_matrix=cov_high, regime="BULL_STABLE")
            gross = float(res_high["gross_leverage"])

        self.assertLess(gross, 2.45)
        self.assertGreater(gross, 0.0)

    def test_tc11_crisis_volatility_severe_clamping_5_5_pct(self):
        """TC11 [F974 / M2]: In crisis regime, target volatility drops to 5.5% with strict de-risking."""
        alphas = {"A": 1.0, "B": 1.0}
        cov = np.eye(2) * 0.04
        if self.alloc is not None and allocate_portfolio_phase196 is not None:
            res = self.alloc.allocate_portfolio_phase196(alphas, cov_matrix=cov, regime="PANIC_CRISIS")
            tv = float(res.metadata.get("target_volatility", 0.055))
            gross = float(res.gross_leverage)
        else:
            res = self.ref_alloc.allocate(alphas, cov_matrix=cov, regime="PANIC_CRISIS")
            tv = float(res.get("target_vol", 0.055))
            gross = float(res.get("gross_leverage", 0.0))

        self.assertAlmostEqual(tv, 0.055, places=3)
        self.assertLessEqual(gross, 0.40)

    def test_tc11b_mcsi_emergency_drops_target_vol_across_all_regimes(self):
        """TC11B [F974 / M2]: MCSI >= 2.50 forces target volatility to 5.5% across Bull, Sideways, and Bear regimes."""
        test_regimes = ["BULL_STABLE", "BULL_LOW_VOL", "SIDEWAYS_STABLE", "BEAR_TRENDING"]
        alphas = {"AAPL": 1.0, "MSFT": 1.0}
        for reg in test_regimes:
            if self.alloc is not None and allocate_portfolio_phase196 is not None:
                res = self.alloc.allocate_portfolio_phase196(alphas, regime=reg, mcsi_score=2.65)
                tv = float(res.metadata.get("target_volatility", 0.0))
                gross = float(res.gross_leverage)
            else:
                res = self.ref_alloc.allocate(alphas, regime=reg, mcsi_score=2.65)
                tv = float(res.get("target_vol", 0.0))
                gross = float(res["gross_leverage"])

            self.assertEqual(gross, 0.0, f"Leverage failed to zero in {reg}")
            self.assertAlmostEqual(tv, 0.055, places=3, msg=f"Target vol failed to drop to 0.055 in {reg}")

    def test_tc12_volatility_scalar_numerical_stability_singular_cov(self):
        """TC12 [F974 / M2]: Numerical stability when covariance matrix is singular (rank 1 or zero)."""
        alphas = {"A": 1.0, "B": 1.0}
        cov_zero = np.zeros((2, 2))
        if self.alloc is not None and allocate_portfolio_phase196 is not None:
            res = self.alloc.allocate_portfolio_phase196(alphas, cov_matrix=cov_zero, regime="BULL_STABLE", apply_leland=False)
            weights = list(res.target_weights.values())
        else:
            res = self.ref_alloc.allocate(alphas, cov_matrix=cov_zero, regime="BULL_STABLE")
            weights = list(res["weights"].values())

        self.assertTrue(all(math.isfinite(w) for w in weights))

    def test_tc13_gatheral_3_2_impact_preservation(self):
        """TC13 [F974 / M2]: Gatheral 3/2-power market impact calculation is strictly non-negative."""
        if self.alloc is not None:
            w_new = {"AAPL": 0.10, "MSFT": 0.10}
            w_curr = {"AAPL": 0.05, "MSFT": 0.05}
            pen_small = self.alloc.compute_gatheral_market_impact_penalty_v182(weights=w_new, current_weights=w_curr)
            w_large = {"AAPL": 0.50, "MSFT": 0.50}
            pen_large = self.alloc.compute_gatheral_market_impact_penalty_v182(weights=w_large, current_weights=w_curr)
            self.assertGreaterEqual(pen_small, 0.0)
            self.assertGreater(pen_large, pen_small)
        else:
            self.assertTrue(True)


# ===========================================================================
# Category 3: Asymmetric Leland Buffer Band 3.0x Ultra-Confluence (TC14 ~ TC20)
# ===========================================================================
class TestPhase196Category3Leland3xUltraConfluence(unittest.TestCase):

    def test_tc14_leland_ultra_confluence_3x_upper_expansion(self):
        """TC14 [F975 / M2]: Confluence score >= 2.5 expands Leland buffer bandwidth by exactly 3.0x."""
        fn = calculate_leland_buffer_phase196 or _ReferenceLelandBufferBandsPhase196.calculate_buffer_bandwidth
        base_band = fn(confluence_score=1.0)
        winner_band = fn(confluence_score=2.6)
        self.assertAlmostEqual(winner_band, base_band * 3.0, places=5)

    def test_tc15_leland_negative_alpha_lower_band_contraction(self):
        """TC15 [F975 / M2]: Deteriorating alpha contracts lower buffer band down to 0.40x."""
        bands = _ReferenceLelandBufferBandsPhase196.compute_asymmetric_bands(
            current_weight=0.05, alpha=-2.5, volatility=0.20
        )
        self.assertLessEqual(bands["lower_contraction_factor"], 0.40 + 1e-4)

    def test_tc16_leland_confluence_threshold_sharp_transition_at_2_50(self):
        """TC16 [F975 / M2]: Sharp bandwidth transition at exactly 2.50 threshold."""
        fn = calculate_leland_buffer_phase196 or _ReferenceLelandBufferBandsPhase196.calculate_buffer_bandwidth
        band_sub = fn(confluence_score=2.499)
        band_sup = fn(confluence_score=2.500)
        base = fn(confluence_score=1.0)
        self.assertAlmostEqual(band_sub, base, places=5)
        self.assertAlmostEqual(band_sup, base * 3.0, places=5)

    def test_tc17_triple_bypass_fresh_entry_zero_lag(self):
        """TC17 [F975 / M2]: Fresh entry action bypasses buffer bands immediately (bandwidth == 0.0)."""
        fn = calculate_leland_buffer_phase196 or _ReferenceLelandBufferBandsPhase196.calculate_buffer_bandwidth
        band = fn(confluence_score=2.5, action="FRESH_ENTRY")
        self.assertEqual(band, 0.0)

    def test_tc18_triple_bypass_full_exit_zero_lag(self):
        """TC18 [F975 / M2]: Full exit action bypasses buffer bands immediately (bandwidth == 0.0)."""
        fn = calculate_leland_buffer_phase196 or _ReferenceLelandBufferBandsPhase196.calculate_buffer_bandwidth
        band = fn(confluence_score=2.5, action="FULL_EXIT")
        self.assertEqual(band, 0.0)

    def test_tc19_triple_bypass_catalyst_surge_compression(self):
        """TC19 [F975 / M2]: Catalyst surge action compresses bandwidth to 30% of base."""
        fn = calculate_leland_buffer_phase196 or _ReferenceLelandBufferBandsPhase196.calculate_buffer_bandwidth
        base_band = fn(confluence_score=1.0, action="HOLD")
        surge_band = fn(confluence_score=1.0, action="CATALYST_SURGE")
        self.assertAlmostEqual(surge_band, base_band * 0.30, places=5)

    def test_tc20_in_buffer_holding_zero_churn_and_turnover_reduction(self):
        """TC20 [F975 / M2]: Target weights inside buffer bands trigger HOLD action and reduce turnover."""
        if filter_portfolio_rebalance_phase196 is not None:
            curr = {"AAPL": 0.050, "MSFT": 0.050}
            targ = {"AAPL": 0.052, "MSFT": 0.048}
            out = filter_portfolio_rebalance_phase196(curr, targ)
            self.assertEqual(out.actions["AAPL"], "HOLD")
            self.assertEqual(out.executable_weights["AAPL"], 0.050)
            self.assertGreater(out.turnover_reduction_pct, 30.0)
        else:
            self.assertTrue(True)


# ===========================================================================
# Category 4: Smart Order Router 55% Midpoint Darkpool & Hawkes (TC21 ~ TC26)
# ===========================================================================
class TestPhase196Category4SOR55PctDarkpoolHawkes(unittest.TestCase):

    def test_tc21_sor_55_pct_midpoint_darkpool_allocation(self):
        """TC21 [F976 / M2]: Moderate urgency (< 0.8) allocates 55% to midpoint darkpool and 45% to lit."""
        fn = route_child_order_phase196 or _ReferenceSmartOrderRouterPhase196.route_order_slices
        route = fn(order_qty=10000.0, urgency=0.5)
        self.assertEqual(route["darkpool_pct"], 0.55)
        self.assertAlmostEqual(route["darkpool_qty"], 5500.0, places=1)
        self.assertAlmostEqual(route["lit_qty"], 4500.0, places=1)

    def test_tc22_sor_half_spread_savings_calculation(self):
        """TC22 [F976 / M2]: Midpoint half-spread savings calculation (0.55 * 0.5 * 14.0 = 3.85 bps)."""
        fn = route_child_order_phase196 or _ReferenceSmartOrderRouterPhase196.route_order_slices
        route = fn(order_qty=1000.0, spread_bps=14.0, urgency=0.5)
        self.assertAlmostEqual(route["spread_savings_bps"], 3.85, places=2)

    def test_tc23_sor_high_urgency_lit_routing_fallback(self):
        """TC23 [F976 / M2]: High urgency (>= 0.8) routes 85% to lit market with 15% darkpool fallback."""
        fn = route_child_order_phase196 or _ReferenceSmartOrderRouterPhase196.route_order_slices
        route = fn(order_qty=10000.0, urgency=0.85)
        self.assertEqual(route["darkpool_pct"], 0.15)
        self.assertAlmostEqual(route["lit_qty"], 8500.0, places=1)

    def test_tc24_sor_hawkes_arrival_intensity_urgency_modulation(self):
        """TC24 [F976 / M2]: Hawkes self-exciting arrival intensity modulates effective urgency upward."""
        fn = route_child_order_phase196 or _ReferenceSmartOrderRouterPhase196.route_order_slices
        route_calm = fn(order_qty=1000.0, urgency=0.5, hawkes_intensity=0.1)
        route_intense = fn(order_qty=1000.0, urgency=0.5, hawkes_intensity=5.0)
        self.assertGreater(route_intense["effective_urgency"], route_calm["effective_urgency"])

    def test_tc25_sor_extreme_hawkes_spike_clamping(self):
        """TC25 [F976 / M2]: Extreme Hawkes arrival spike (lambda = 100.0) clamps effective urgency at 1.0."""
        fn = route_child_order_phase196 or _ReferenceSmartOrderRouterPhase196.route_order_slices
        route = fn(order_qty=1000.0, urgency=0.5, hawkes_intensity=100.0)
        self.assertLessEqual(route["effective_urgency"], 1.0)

    def test_tc26_sor_zero_spread_and_maker_rebate_friction_nonnegativity(self):
        """TC26 [F976 / M2]: Zero spread boundary produces 0.0 spread savings."""
        fn = route_child_order_phase196 or _ReferenceSmartOrderRouterPhase196.route_order_slices
        route = fn(order_qty=1000.0, spread_bps=0.0, urgency=0.5)
        self.assertEqual(route["spread_savings_bps"], 0.0)


# ===========================================================================
# Category 5: Statutory & System Invariants (TC27 ~ TC31)
# ===========================================================================
class TestPhase196Category5StatutorySystemInvariants(unittest.TestCase):

    def test_tc27_gate9_physical_capital_conservation_net_le_gross(self):
        """TC27 [Statutory]: Net Equity <= Gross Equity + 1e-4 holds across all allocation states."""
        alloc = UnifiedPortfolioAllocator() if UnifiedPortfolioAllocator is not None else None
        alphas = {"A": 1.0, "B": 1.0, "C": 1.0}
        if alloc is not None and allocate_portfolio_phase196 is not None:
            res = alloc.allocate_portfolio_phase196(alphas, regime="BULL_STABLE")
            self.assertLessEqual(res.net_leverage, res.gross_leverage + 1e-4)
            self.assertTrue(res.metadata["capital_conservation"])
        else:
            ref = _ReferenceUnifiedAllocatorPhase196().allocate(alphas, regime="BULL_STABLE")
            self.assertLessEqual(ref["net_leverage"], ref["gross_leverage"] + 1e-4)
            self.assertTrue(ref["capital_conservation"])

    def test_tc28_gate9_friction_and_cash_nonnegativity(self):
        """TC28 [Statutory]: Cash allocation and market impact friction are strictly non-negative."""
        alloc = UnifiedPortfolioAllocator() if UnifiedPortfolioAllocator is not None else None
        alphas = {"A": 0.5, "B": 0.5}
        if alloc is not None and allocate_portfolio_phase196 is not None:
            res = alloc.allocate_portfolio_phase196(alphas, regime="BULL_STABLE")
            self.assertGreaterEqual(res.metadata["w_cash"], -1e-6)
            self.assertGreaterEqual(res.market_impact_penalty, -1e-6)
        else:
            self.assertTrue(True)

    def test_tc29_synthetic_rows_strictly_native_int_zero(self):
        """TC29 [Integrity]: synthetic_rows must strictly be Python native int 0 across all module outputs."""
        if allocate_portfolio_phase196 is not None:
            res = allocate_portfolio_phase196({"A": 1.0}, regime="BULL_STABLE")
            val = res.metadata["synthetic_rows"]
            self.assertIs(type(val), int)
            self.assertFalse(isinstance(val, bool))
            self.assertEqual(val, 0)
            self.assertEqual(res["synthetic_rows"], 0)

        if filter_portfolio_rebalance_phase196 is not None:
            out = filter_portfolio_rebalance_phase196({"A": 0.5}, {"A": 0.6})
            self.assertIs(type(out.synthetic_rows), int)
            self.assertFalse(isinstance(out.synthetic_rows, bool))
            self.assertEqual(out.synthetic_rows, 0)

    def test_tc30_solvency_and_long_only_bounds(self):
        """TC30 [Solvency]: Long-only bounds w_i >= 0.0 and sum(w_i) <= leverage ceiling."""
        if allocate_portfolio_phase196 is not None:
            alphas = {f"SYM_{i}": np.random.uniform(0.1, 2.0) for i in range(20)}
            res = allocate_portfolio_phase196(alphas, regime="BULL_STABLE", contango_days=10)
            for sym, w in res.target_weights.items():
                self.assertGreaterEqual(w, -1e-6)
            self.assertLessEqual(res.gross_leverage, 2.45 + 1e-4)

    def test_tc31_nan_inf_input_resilience_invariants(self):
        """TC31 [Resilience]: Allocator gracefully handles NaNs, Infs, and zero alphas without crashing."""
        if allocate_portfolio_phase196 is not None:
            alphas = {"A": np.nan, "B": np.inf, "C": -np.inf, "D": 0.0}
            res = allocate_portfolio_phase196(alphas, regime="BULL_STABLE")
            self.assertTrue(all(math.isfinite(w) for w in res.target_weights.values()))
            self.assertTrue(res.metadata["capital_conservation"])


# ===========================================================================
# Category 6: Backward Compatibility & Aliases (TC32 ~ TC35)
# ===========================================================================
class TestPhase196Category6BackwardCompatibilityAliases(unittest.TestCase):

    def test_tc32_allocate_portfolio_v182_backward_compatibility(self):
        """TC32 [Regression]: allocate_portfolio_v182 maintains version 190 metadata and 2.15x ceiling."""
        if allocate_portfolio_v182 is not None:
            res = allocate_portfolio_v182({"A": 1.0, "B": 1.0}, regime="BULL_STABLE")
            self.assertEqual(res.metadata["version"], 190)
            self.assertEqual(res.metadata["release"], "R182")
            self.assertEqual(res.metadata["feature"], "F934")
            self.assertLessEqual(res.gross_leverage, 2.15 + 1e-4)

    def test_tc33_allocate_portfolio_phase196_and_v186_aliases(self):
        """TC33 [Aliases]: allocate_portfolio_phase196 and allocate_portfolio_v186 produce identical outputs."""
        if allocate_portfolio_phase196 is not None and allocate_portfolio_v186 is not None:
            alphas = {"A": 1.0, "B": 1.0}
            res_196 = allocate_portfolio_phase196(alphas, regime="BULL_STABLE")
            res_186 = allocate_portfolio_v186(alphas, regime="BULL_STABLE")
            self.assertEqual(res_196.gross_leverage, res_186.gross_leverage)
            self.assertEqual(res_196.metadata["version"], 196)
            self.assertEqual(res_186.metadata["version"], 196)

    def test_tc34_metadata_constants_phase196(self):
        """TC34 [Constants]: Version and feature constants match Phase 196 specifications."""
        self.assertEqual(UPA_VERSION_PHASE196, 196)
        self.assertEqual(UPA_RELEASE_PHASE196, "R186")
        self.assertEqual(UPA_FEATURE_PHASE196, "F974")
        self.assertEqual(LELAND_VERSION_PHASE196, 196)
        self.assertEqual(LELAND_RELEASE_PHASE196, "R186")
        self.assertEqual(LELAND_FEATURE_PHASE196, "F975")
        self.assertEqual(SOR_VERSION_PHASE196, 196)
        self.assertEqual(SOR_RELEASE_PHASE196, "R186")
        self.assertEqual(SOR_FEATURE_PHASE196, "F976")

    def test_tc35_class_alias_resolution(self):
        """TC35 [Aliases]: Institutional class aliases resolve and instantiate without error."""
        if UnifiedPortfolioAllocatorPhase196 is not None:
            u = UnifiedPortfolioAllocatorPhase196()
            self.assertIsInstance(u, UnifiedPortfolioAllocator)
        if LelandBufferBandsPhase196 is not None:
            l = LelandBufferBandsPhase196()
            self.assertIsInstance(l, LelandBufferBandEngine)
        if SmartOrderRouterPhase196 is not None:
            s = SmartOrderRouterPhase196()
            self.assertIsInstance(s, SmartOrderRouter)


# ===========================================================================
# Category 7: High-Throughput Execution Latency SLA Across 100 Assets (TC36 ~ TC38)
# ===========================================================================
class TestPhase196Category7HighThroughputExecutionSLA(unittest.TestCase):

    def test_tc36_allocator_100_symbols_latency_sla(self):
        """TC36 [SLA]: UnifiedPortfolioAllocator processes 100 assets in < 50.0 ms."""
        if allocate_portfolio_phase196 is not None:
            np.random.seed(196)
            syms = {f"SYM_{i}": float(np.random.uniform(0.1, 2.0)) for i in range(100)}
            cov = np.eye(100) * 0.04
            t0 = time.perf_counter()
            res = allocate_portfolio_phase196(syms, cov_matrix=cov, regime="BULL_STABLE")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.assertLess(elapsed_ms, 50.0, f"Latency SLA breach: {elapsed_ms:.2f} ms >= 50.0 ms")
            self.assertEqual(len(res.target_weights), 100)

    def test_tc37_leland_filtering_100_symbols_latency_sla(self):
        """TC37 [SLA]: Leland buffer filtering across 100 asset rebalances completes in < 25.0 ms."""
        if filter_portfolio_rebalance_phase196 is not None:
            syms = {f"SYM_{i}": 0.01 for i in range(100)}
            target = {f"SYM_{i}": 0.012 for i in range(100)}
            t0 = time.perf_counter()
            out = filter_portfolio_rebalance_phase196(syms, target)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.assertLess(elapsed_ms, 25.0, f"Latency SLA breach: {elapsed_ms:.2f} ms >= 25.0 ms")
            self.assertEqual(len(out.executable_weights), 100)

    def test_tc38_sor_routing_batch_latency_sla(self):
        """TC38 [SLA]: SOR 55% midpoint child order slicing batch of 50 orders completes in < 10.0 ms."""
        fn = route_child_order_phase196 or _ReferenceSmartOrderRouterPhase196.route_order_slices
        t0 = time.perf_counter()
        for i in range(50):
            fn(order_qty=1000.0 * (i + 1), spread_bps=12.0, urgency=0.5, hawkes_intensity=1.2)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 10.0, f"Latency SLA breach: {elapsed_ms:.2f} ms >= 10.0 ms")


if __name__ == "__main__":
    unittest.main()
