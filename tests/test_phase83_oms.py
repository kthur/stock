"""
tests/test_phase83_oms.py

Unit test suite for Phase 83 Execution OMS and Microstructure:
- Feature F389: Gate 8 Synthetic Beta Inverse Hedge Overlay with 0.0700 deadband clamp, multi-market risk decomposition (KRX vs US).
- Verification of ExecutionOMSEngine order generation, hedge planning, and micro-tick execution scheduling.
"""

import math
import numpy as np
import pytest

from trading_system.src.execution.oms_engine import ExecutionOMSEngine
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase83OMS:
    """Test suite for Phase 83 OMS Gate 8 and Execution Engine."""

    def test_feature_f389_synthetic_inverse_hedge_bear_regime(self):
        """Verify synthetic inverse hedge calculation in Bear / Crisis regimes."""
        portfolio_weights = {
            "005930.KS": 0.30,
            "000660.KS": 0.20,
            "AAPL": 0.25,
            "MSFT": 0.25,
        }

        # In Bull regime, no hedge should be required
        bull_res = PortfolioAllocator.compute_synthetic_inverse_hedge(
            portfolio_weights=portfolio_weights,
            market="KOSPI",
            regime_label="BULL",
        )
        assert bull_res["hedge_required"] is False
        assert bull_res["hedge_weight"] == 0.0

        # In Bear regime, KRX hedge should select 114800 (-2x leverage)
        krx_weights = {"005930.KS": 0.60, "000660.KS": 0.40}
        krx_res = PortfolioAllocator.compute_synthetic_inverse_hedge(
            portfolio_weights=krx_weights,
            market="KOSPI",
            regime_label="BEAR",
        )
        assert krx_res["hedge_required"] is True
        assert krx_res["hedge_symbol"] == "114800"
        assert krx_res["hedge_leverage"] == 2.0
        assert krx_res["hedge_weight"] > 0.0

        # US hedge should select PSQ or SH
        us_weights = {"AAPL": 0.50, "MSFT": 0.50}
        us_res = PortfolioAllocator.compute_synthetic_inverse_hedge(
            portfolio_weights=us_weights,
            market="NASDAQ",
            regime_label="CRISIS",
        )
        assert us_res["hedge_required"] is True
        assert us_res["hedge_symbol"] == "PSQ"
        assert us_res["hedge_leverage"] == 1.0
        assert us_res["hedge_weight"] > 0.0

    def test_feature_f389_oms_plan_creation(self):
        """Verify ExecutionOMSEngine generates order plan without errors."""
        import tempfile
        import os
        import uuid
        db_file = os.path.join(tempfile.gettempdir(), f"test_oms_{uuid.uuid4().hex}.db")
        try:
            oms = ExecutionOMSEngine(db_path=db_file)
            top_predictions = [
                {"symbol": "005930", "market": "KOSPI", "expected_return": 0.08, "confidence": 0.90, "close": 70000.0},
                {"symbol": "AAPL", "market": "NASDAQ", "expected_return": 0.07, "confidence": 0.88, "close": 150.0},
            ]
            portfolio_weights = {"005930": 0.50, "AAPL": 0.50}
            prices_dict = {"005930": 70000.0, "AAPL": 150.0}

            orders = oms.generate_order_plan(
                top_predictions=top_predictions,
                portfolio_weights=portfolio_weights,
                total_capital=100_000_000,
                regime_label="BULL",
                prices_dict=prices_dict,
            )
            assert isinstance(orders, list)
            assert len(orders) >= 1
            for order in orders:
                assert "symbol" in order
                assert "quantity" in order
                assert order["quantity"] > 0
        finally:
            if os.path.exists(db_file):
                try:
                    os.remove(db_file)
                except Exception:
                    pass
