import unittest
import numpy as np
from src.analysis.portfolio_optimizer import calculate_black_litterman_weights
from src.strategy.asset_allocation import AssetAllocator

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class TestBlackLitterman(unittest.TestCase):

    def test_black_litterman_math_integrity(self):
        """Test the Black-Litterman optimization returns valid weights that sum to 1.0."""
        # AAPL (high variance), MSFT (low variance)
        cov = np.array([
            [0.08, 0.01],
            [0.01, 0.02]
        ])
        # Views: Apple return 10%, Microsoft return 5%
        predicted_returns = np.array([0.10, 0.05])
        
        weights = calculate_black_litterman_weights(
            cov_matrix=cov,
            predicted_returns=predicted_returns,
            prior_weights=np.array([0.5, 0.5]),
            risk_aversion=2.5,
            tau=0.05,
            omega_scale=0.1
        )
        
        self.assertEqual(len(weights), 2)
        self.assertAlmostEqual(np.sum(weights), 1.0, places=6)
        self.assertTrue(np.all(weights >= 0.0))
        self.assertTrue(np.all(weights <= 1.0))

    def test_asset_allocator_black_litterman(self):
        """Test the AssetAllocator integration with Black-Litterman strategy."""
        allocator = AssetAllocator(strategy="black_litterman")
        
        prices_dict = {
            'AAPL': [100.0 * (1.0 + 0.01 * i) for i in range(25)],
            'MSFT': [100.0 * (1.0 + 0.005 * i) for i in range(25)]
        }
        
        predicted_returns = {
            'AAPL': 0.12,
            'MSFT': 0.06
        }
        
        weights = allocator.allocate(prices_dict, predicted_returns)
        
        self.assertIn('AAPL', weights)
        self.assertIn('MSFT', weights)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)


if __name__ == '__main__':
    unittest.main()
