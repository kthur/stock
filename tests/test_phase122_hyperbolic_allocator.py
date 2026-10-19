"""
tests/test_phase122_hyperbolic_allocator.py
===========================================
Verification Test Suite for:
Hyperbolic Manifold Curvature-Adaptive Risk Budgeting & Dynamic Optimal Transport Allocator (Feature F582).
Phase 122 (Release R138 / v129 Production Master).
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
from pathlib import Path
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.hyperbolic_optimal_transport_allocator import (
    VERSION,
    RELEASE,
    FEATURE,
    HyperbolicRegime,
    HyperbolicAllocatorConfig,
    HyperbolicAllocationOutput,
    HyperbolicOptimalTransportAllocator,
    HyperbolicWassersteinAllocator,
)


class TestPhase122HyperbolicAllocator:
    """Tests for Hyperbolic Manifold Curvature-Adaptive Optimal Transport Allocator."""

    def test_tc01_version_and_metadata(self):
        """Verifies metadata constants."""
        assert VERSION == 122
        assert RELEASE == "R138"
        assert FEATURE == "F582"

    def test_tc02_dual_tree_sha256_parity(self):
        """Verifies 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        f1 = PROJECT_ROOT / "src" / "risk" / "hyperbolic_optimal_transport_allocator.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "risk" / "hyperbolic_optimal_transport_allocator.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc03_poincare_geodesic_distance(self):
        """Tests Poincaré ball geodesic distance properties."""
        x = np.array([0.10, 0.20])
        y = np.array([0.30, -0.15])
        z = np.array([-0.20, 0.25])

        # Self-distance is 0
        d_xx = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, x, c=0.25)
        assert abs(d_xx) < 1e-6

        # Symmetry
        d_xy = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, y, c=0.25)
        d_yx = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(y, x, c=0.25)
        assert abs(d_xy - d_yx) < 1e-6
        assert d_xy > 0.0

        # Triangle inequality: d(x, z) <= d(x, y) + d(y, z)
        d_yz = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(y, z, c=0.25)
        d_xz = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, z, c=0.25)
        assert d_xz <= d_xy + d_yz + 1e-4

    def test_tc04_sinkhorn_optimal_transport(self):
        """Tests entropic regularized Sinkhorn-Knopp solver."""
        allocator = HyperbolicOptimalTransportAllocator()
        p = np.array([0.40, 0.30, 0.30])
        q = np.array([0.20, 0.50, 0.30])
        cost = np.array([
            [0.0, 1.2, 2.5],
            [1.2, 0.0, 1.0],
            [2.5, 1.0, 0.0]
        ])
        t_plan, w_dist = allocator.sinkhorn_optimal_transport(p, q, cost, eps=0.05)
        assert t_plan.shape == (3, 3)
        assert w_dist >= 0.0
        # Row sums match p, column sums match q
        assert np.allclose(np.sum(t_plan, axis=1), p, atol=1e-3)
        assert np.allclose(np.sum(t_plan, axis=0), q, atol=1e-3)

    def test_tc05_bull_regime_allocation(self):
        """Tests allocation under Bull regime (low curvature, high liquidity)."""
        allocator = HyperbolicOptimalTransportAllocator()
        symbols = ["AAPL", "NVDA", "MSFT", "GOOGL"]
        curr_w = np.array([0.25, 0.25, 0.25, 0.25])
        alphas = np.array([0.80, 0.95, 0.40, 0.30])  # NVDA & AAPL strong

        out = allocator.allocate(
            current_weights=curr_w,
            alpha_scores=alphas,
            symbols=symbols,
            regime="BULL_LOW_VOL"
        )
        assert isinstance(out, HyperbolicAllocationOutput)
        assert out.regime == "BULL_LOW_VOL"
        assert out.effective_curvature == 0.10
        # High conviction winners should receive increased weights
        res_map = dict(zip(out.symbols, out.weights))
        assert res_map["NVDA"] > res_map["GOOGL"]
        assert float(np.sum(out.weights)) <= 1.00

    def test_tc06_crisis_regime_cash_derisking(self):
        """Tests allocation under Crisis regime enforces >= 85% cash preservation."""
        allocator = HyperbolicOptimalTransportAllocator()
        symbols = ["AAPL", "NVDA", "MSFT", "GOOGL"]
        curr_w = np.array([0.25, 0.25, 0.25, 0.25])
        alphas = np.array([0.50, 0.50, 0.50, 0.50])

        out = allocator.allocate(
            current_weights=curr_w,
            alpha_scores=alphas,
            symbols=symbols,
            regime="CRISIS"
        )
        assert out.regime == "CRISIS"
        assert out.effective_curvature == 0.90
        tot_alloc = float(np.sum(out.weights))
        assert tot_alloc <= 0.15 + 1e-4, f"Crisis allocation {tot_alloc} exceeded 0.15 cap"

    def test_tc07_leland_bypass_rules(self):
        """Tests Leland buffer bypass on fresh entry and full liquidation."""
        allocator = HyperbolicOptimalTransportAllocator()
        symbols = ["NEW_STOCK", "EXIT_STOCK", "STABLE_STOCK"]
        curr_w = np.array([0.0, 0.20, 0.20])
        alphas = np.array([0.60, 0.0, 0.20])  # NEW enters, EXIT leaves, STABLE holds

        out = allocator.allocate(
            current_weights=curr_w,
            alpha_scores=alphas,
            symbols=symbols,
            regime="SIDEWAYS_LOW_VOL"
        )
        assert out.rebalance_actions["NEW_STOCK"] == "BUY"
        assert out.weights[0] > 0.0  # fresh entry executed
        assert out.rebalance_actions["EXIT_STOCK"] == "SELL"
        assert out.weights[1] == 0.0  # full liquidation executed

    def test_tc08_serialization_and_aliases(self):
        """Tests serialization and class aliases."""
        assert HyperbolicWassersteinAllocator is HyperbolicOptimalTransportAllocator
        allocator = HyperbolicWassersteinAllocator()
        out = allocator.allocate(
            current_weights=np.array([0.5, 0.5]),
            alpha_scores=np.array([0.7, 0.3]),
            symbols=["S1", "S2"],
            regime="BULL_LOW_VOL"
        )
        d = out.to_dict()
        assert d["regime"] == "BULL_LOW_VOL"
        assert "wasserstein_distance" in d
        assert len(d["weights"]) == 2
