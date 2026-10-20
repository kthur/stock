"""
tests/test_phase123_modular_ensemble.py
=======================================
Verification Test Suite for:
Modular Ensemble Decoupler & Strategy Weight Registry (Feature F585).
Phase 123 (Release R139 / v130 Production Master).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.ensemble_weight_registry import (
    VERSION,
    RELEASE,
    FEATURE,
    StrategyCategory,
    MarketRegimeType,
    StrategyWeightProfile,
    CANONICAL_37_STRATEGIES,
    EnsembleWeightRegistry,
    DEFAULT_WEIGHT_REGISTRY,
)
from src.ai.modular_ensemble_decoupler import (
    ModularEnsembleDecoupler,
    DecoupledEnsembleOutput,
)


class TestPhase123ModularEnsemble:
    """Comprehensive test suite for Feature F585."""

    def test_tc01_version_and_metadata(self):
        """Verifies metadata constants."""
        assert VERSION == 123
        assert RELEASE == "R139"
        assert FEATURE == "F585"

    def test_tc02_dual_tree_sha256_parity_registry(self):
        """Verifies 100% bit-for-bit SHA-256 parity for ensemble_weight_registry.py."""
        f1 = PROJECT_ROOT / "src" / "ai" / "ensemble_weight_registry.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "ai" / "ensemble_weight_registry.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc03_dual_tree_sha256_parity_decoupler(self):
        """Verifies 100% bit-for-bit SHA-256 parity for modular_ensemble_decoupler.py."""
        f1 = PROJECT_ROOT / "src" / "ai" / "modular_ensemble_decoupler.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "ai" / "modular_ensemble_decoupler.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc04_package_exports(self):
        """Verifies exports from src.ai package."""
        import src.ai as ai_pkg
        assert hasattr(ai_pkg, "EnsembleWeightRegistry")
        assert hasattr(ai_pkg, "ModularEnsembleDecoupler")
        assert hasattr(ai_pkg, "CANONICAL_37_STRATEGIES")

    def test_tc05_canonical_37_strategies_inventory(self):
        """Verifies all 37 canonical alpha strategies are defined with valid bounds."""
        assert len(CANONICAL_37_STRATEGIES) == 37
        codes = [s.code for s in CANONICAL_37_STRATEGIES]
        assert len(set(codes)) == 37  # Unique codes
        for s in CANONICAL_37_STRATEGIES:
            assert s.base_weight > 0.0
            assert s.min_weight > 0.0
            assert s.max_weight >= s.min_weight
            assert isinstance(s.category, StrategyCategory)

    def test_tc06_base_weights_normalization(self):
        """Verifies normalized base weights sum to 1.0 within floating point tolerance."""
        weights = DEFAULT_WEIGHT_REGISTRY.get_base_weights(normalize=True)
        assert len(weights) == 37
        assert np.isclose(sum(weights.values()), 1.0, atol=1e-6)

    def test_tc07_regime_weight_modulation(self):
        """Verifies regime multipliers alter weights properly."""
        bull_weights = DEFAULT_WEIGHT_REGISTRY.get_regime_weights(MarketRegimeType.BULL_LOW_VOL)
        crisis_weights = DEFAULT_WEIGHT_REGISTRY.get_regime_weights(MarketRegimeType.PANIC_CRISIS)
        assert np.isclose(sum(bull_weights.values()), 1.0, atol=1e-6)
        assert np.isclose(sum(crisis_weights.values()), 1.0, atol=1e-6)
        # Momentum quality should have higher weight in Bull Low Vol than Panic Crisis
        assert bull_weights["mq_factor"] > crisis_weights["mq_factor"]
        # IV skew should have higher weight in Panic Crisis
        assert crisis_weights["iv_skew"] > bull_weights["iv_skew"]

    def test_tc08_missing_strategy_zero_weighting(self):
        """Verifies missing strategies are omitted and weights safely renormalized."""
        available = {"regression", "surge", "lead_lag", "stat_arb"}
        weights = DEFAULT_WEIGHT_REGISTRY.get_regime_weights(
            MarketRegimeType.SIDEWAYS_LOW_VOL,
            available_strategies=available,
            normalize=True,
        )
        assert set(weights.keys()) == available
        assert np.isclose(sum(weights.values()), 1.0, atol=1e-6)

    def test_tc09_registry_json_export(self):
        """Verifies registry JSON serialization roundtrip."""
        json_str = DEFAULT_WEIGHT_REGISTRY.to_json()
        data = json.loads(json_str)
        assert data["version"] == 123
        assert data["release"] == "R139"
        assert len(data["strategies"]) == 37

    def test_tc10_cross_sectional_normalization(self):
        """Verifies rank percentile normalization across symbols."""
        decoupler = ModularEnsembleDecoupler()
        df = pd.DataFrame({
            "symbol": ["AAPL", "MSFT", "GOOGL"],
            "regression": [10.0, 50.0, 20.0],
            "surge": [0.2, 0.8, 0.5],
        })
        norm = decoupler.normalize_cross_sectional(df)
        assert norm.shape == df.shape
        # Check relative order preserved
        assert norm.loc[norm["symbol"] == "MSFT", "regression"].values[0] > norm.loc[norm["symbol"] == "AAPL", "regression"].values[0]

    def test_tc11_single_symbol_synthesis(self):
        """Verifies single symbol score synthesis with friction costs."""
        decoupler = ModularEnsembleDecoupler()
        scores = {
            "regression": 0.8,
            "surge": 0.7,
            "lead_lag": 0.6,
        }
        res = decoupler.compute_symbol_score("005930.KS", scores, regime=MarketRegimeType.BULL_LOW_VOL)
        assert isinstance(res, DecoupledEnsembleOutput)
        assert res.symbol == "005930.KS"
        assert 0.0 <= res.ensemble_score <= 1.0
        assert res.net_score <= res.ensemble_score
        assert res.friction_cost > 0.0

    def test_tc12_portfolio_synthesis_batch(self):
        """Verifies batch dataframe scoring and ranking."""
        decoupler = ModularEnsembleDecoupler()
        df = pd.DataFrame({
            "symbol": ["A", "B", "C"],
            "regression": [0.1, 0.9, 0.5],
            "stat_arb": [0.2, 0.8, 0.6],
        })
        res_df = decoupler.synthesize_portfolio_dataframe(df)
        assert not res_df.empty
        assert "expected_return" in res_df.columns
        # Top symbol should be B
        assert res_df.iloc[0]["symbol"] == "B"
        # Ordered descending
        assert res_df.iloc[0]["expected_return"] >= res_df.iloc[1]["expected_return"]

    def test_tc13_empty_dataframe_resilience(self):
        """Verifies graceful handling of empty inputs."""
        decoupler = ModularEnsembleDecoupler()
        empty_df = pd.DataFrame()
        assert decoupler.normalize_cross_sectional(empty_df).empty
        assert decoupler.synthesize_portfolio_dataframe(empty_df).empty
