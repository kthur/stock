import os
import sys
import unittest
import numpy as np
import pandas as pd
import asyncio

# Ensure proper path loading
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.execution.oms_engine import ExecutionOMSEngine
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine, safe_matrix_precision_guard
from src.utils.rate_limiter import GlobalRateLimiter


class TestSprint1P0Fixes(unittest.TestCase):

    def test_leland_buffer_full_exit_bypass(self):
        """Verify that a position with w*=0.0 (full exit) is NEVER trapped by Leland buffer as HOLD."""
        oms = ExecutionOMSEngine()
        
        # Symbol with current holding 3% (w_curr = 0.03) but target 0.0% (SELL)
        predictions = [{
            "symbol": "005930",
            "name": "Samsung Electronics",
            "market": "KOSPI",
            "close_price": 70000.0,
            "target_price": 70000.0,
            "action": "SELL",
            "expected_return": 0.0,
            "volatility_20d": 0.02
        }]
        portfolio_weights = {"005930": 0.0}
        current_holdings = {"005930": 0.03}
        
        orders = oms.generate_order_plan(
            top_predictions=predictions,
            portfolio_weights=portfolio_weights,
            total_capital=100_000_000.0,
            current_holdings=current_holdings,
            use_leland_buffer=True
        )
        
        # Must generate a SELL order, not skipped as HOLD
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["action"], "SELL")
        self.assertEqual(orders[0]["symbol"], "005930")

    def test_leland_buffer_new_entry_bypass(self):
        """Verify that a new position (w_curr=0.0, w*=0.02) is NOT skipped by Leland buffer."""
        oms = ExecutionOMSEngine()
        
        predictions = [{
            "symbol": "000660",
            "name": "SK Hynix",
            "market": "KOSPI",
            "close_price": 150000.0,
            "target_price": 150000.0,
            "action": "BUY",
            "expected_return": 5.0,
            "volatility_20d": 0.025
        }]
        portfolio_weights = {"000660": 0.02}
        current_holdings = {"000660": 0.0}
        
        orders = oms.generate_order_plan(
            top_predictions=predictions,
            portfolio_weights=portfolio_weights,
            total_capital=100_000_000.0,
            current_holdings=current_holdings,
            use_leland_buffer=True
        )
        
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["action"], "BUY")

    def test_esrw_whitening_preserves_positive_consensus(self):
        """Verify ESRW whitening preserves positive sign affinity for high consensus alpha."""
        engine = FactorOrthogonalizerEngine()
        
        # Create two highly collinear features (rho = 0.90)
        np.random.seed(42)
        latent = np.random.normal(0, 1, 300)
        f1 = latent + 0.1 * np.random.normal(0, 1, 300)
        f2 = latent + 0.1 * np.random.normal(0, 1, 300)
        
        df = pd.DataFrame({"f1": f1, "f2": f2})
        ortho_df = engine.orthogonalize(df, ["f1", "f2"], method="pca_symmetric")
        
        # Check correlation between raw and orthogonalized is strongly positive
        corr_f1 = np.corrcoef(df["f1"], ortho_df["f1"])[0, 1]
        corr_f2 = np.corrcoef(df["f2"], ortho_df["f2"])[0, 1]
        self.assertGreater(corr_f1, 0.70)
        self.assertGreater(corr_f2, 0.70)

    def test_safe_matrix_precision_guard(self):
        """Verify safe_matrix_precision_guard ensures float64 execution without float32 overflow."""
        @safe_matrix_precision_guard
        def dummy_eigen(mat: np.ndarray):
            self.assertEqual(mat.dtype, np.float64)
            return np.linalg.eigh(mat)
            
        mat_f32 = np.eye(5, dtype=np.float32)
        vals, vecs = dummy_eigen(mat_f32)
        self.assertEqual(vals.shape, (5,))

    def test_host_aware_token_bucket_rate_limiter(self):
        """Verify host-aware token bucket rate limiter handles burst requests smoothly."""
        limiter = GlobalRateLimiter()
        
        for _ in range(5):
            limiter.wait(source="yahoo")
        
        # Also test async wait
        async def run_async():
            for _ in range(5):
                await limiter.async_wait(source="fred")
                
        asyncio.run(run_async())


if __name__ == "__main__":
    unittest.main()
