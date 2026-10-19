"""
tests/test_phase122_hawkes_alpha.py
===================================
Verification Test Suite for:
Multi-Asset Non-Markovian Hawkes Cross-Excitation & Queue Imbalance Alpha Engine (Feature F581).
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

from src.ai.hawkes_cross_excitation_alpha_engine import (
    VERSION,
    RELEASE,
    FEATURE,
    MarketNode,
    FlowDirection,
    HawkesConfig,
    HawkesAlphaOutput,
    HawkesCrossExcitationAlphaEngine,
    HawkesCrossExcitationEngine,
)


class TestPhase122HawkesAlpha:
    """Tests for Multi-Asset Hawkes Cross-Excitation & Queue Imbalance Alpha Engine."""

    def test_tc01_version_and_metadata(self):
        """Verifies metadata constants."""
        assert VERSION == 122
        assert RELEASE == "R138"
        assert FEATURE == "F581"

    def test_tc02_dual_tree_sha256_parity(self):
        """Verifies 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        f1 = PROJECT_ROOT / "src" / "ai" / "hawkes_cross_excitation_alpha_engine.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "ai" / "hawkes_cross_excitation_alpha_engine.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc03_market_node_resolution(self):
        """Verifies market node resolution across all 5 markets."""
        assert HawkesCrossExcitationAlphaEngine.resolve_market_node("SP500") == MarketNode.SP500
        assert HawkesCrossExcitationAlphaEngine.resolve_market_node("NASDAQ") == MarketNode.NASDAQ
        assert HawkesCrossExcitationAlphaEngine.resolve_market_node("RUSSELL2000") == MarketNode.RUSSELL2000
        assert HawkesCrossExcitationAlphaEngine.resolve_market_node("KOSPI") == MarketNode.KOSPI
        assert HawkesCrossExcitationAlphaEngine.resolve_market_node("KOSDAQ") == MarketNode.KOSDAQ

    def test_tc04_spectral_radius_stability_constraint(self):
        """Verifies that spectral radius rho(Gamma) is strictly sub-critical (< 1.0)."""
        engine = HawkesCrossExcitationAlphaEngine()
        assert engine.spectral_radius < 1.0
        assert engine.spectral_radius <= engine.config.max_spectral_radius
        assert engine.branching_matrix.shape == (5, 5)

    def test_tc05_queue_imbalance_calculation(self):
        """Tests multi-level depth weighted queue imbalance calculation."""
        engine = HawkesCrossExcitationAlphaEngine()
        # Heavy bid side: should produce positive imbalance
        bids = [1000.0, 800.0, 600.0, 400.0, 200.0]
        asks = [100.0, 80.0, 60.0, 40.0, 20.0]
        oi_pos = engine.compute_queue_imbalance(bids, asks)
        assert oi_pos > 0.50
        assert oi_pos <= 1.00

        # Heavy ask side: should produce negative imbalance
        oi_neg = engine.compute_queue_imbalance(asks, bids)
        assert oi_neg < -0.50
        assert oi_neg >= -1.00

        # Balanced: should be near zero
        oi_bal = engine.compute_queue_imbalance([500.0]*5, [500.0]*5)
        assert abs(oi_bal) < 1e-4

    def test_tc06_cross_intensity_evaluation(self):
        """Tests cross-arrival intensity evaluation across markets."""
        engine = HawkesCrossExcitationAlphaEngine()
        l_self, l_in, l_out = engine.evaluate_cross_intensities(MarketNode.NASDAQ)
        assert l_self > 0.0
        assert l_in > 0.0
        assert l_out > 0.0
        assert math.isfinite(l_self)

    def test_tc07_microprice_drift_projection(self):
        """Tests directional microprice drift and 1-second alpha projection."""
        engine = HawkesCrossExcitationAlphaEngine()
        # Positive queue imbalance should project positive price drift
        drift_up, alpha_up = engine.compute_microprice_drift(0.60, 40.0, 150.0)
        assert drift_up > 0.0
        assert alpha_up > 0.0

        # Negative queue imbalance should project negative price drift
        drift_dn, alpha_dn = engine.compute_microprice_drift(-0.60, 40.0, 150.0)
        assert drift_dn < 0.0
        assert alpha_dn < 0.0

    def test_tc08_process_order_book_tick_full(self):
        """Tests full end-to-end L3/L2 order book tick processing."""
        engine = HawkesCrossExcitationAlphaEngine()
        out = engine.process_order_book_tick(
            symbol="NVDA",
            market="NASDAQ",
            mid_price=120.0,
            bid_sizes=[500.0, 400.0, 300.0, 200.0, 100.0],
            ask_sizes=[200.0, 150.0, 100.0, 50.0, 20.0],
        )
        assert isinstance(out, HawkesAlphaOutput)
        assert out.symbol == "NVDA"
        assert out.market == "NASDAQ"
        assert out.queue_imbalance > 0.0
        assert out.microprice_drift_bps > 0.0
        assert out.spectral_radius < 1.0
        assert len(out.conditioning_vector) == 10
        assert np.all(np.isfinite(out.conditioning_vector))

    def test_tc09_serialization_and_aliases(self):
        """Tests dictionary serialization and class aliases."""
        assert HawkesCrossExcitationEngine is HawkesCrossExcitationAlphaEngine
        engine = HawkesCrossExcitationEngine()
        out = engine.process_order_book_tick("005930.KS", "KOSPI", 70000.0, [1000.0]*5, [800.0]*5)
        d = out.to_dict()
        assert d["symbol"] == "005930.KS"
        assert "spectral_radius" in d
        assert len(d["conditioning_vector"]) == 10
