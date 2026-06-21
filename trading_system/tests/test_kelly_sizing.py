import unittest
import pandas as pd
import numpy as np
from src.risk.position_sizing import PortfolioAllocator

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class TestKellySizing(unittest.TestCase):

    def setUp(self):
        self.allocator = PortfolioAllocator(
            max_single_position=0.15,
            min_single_position=0.02,
            max_total_allocation=0.80,
            target_horizon=20,
            use_kelly=True,
            kelly_fraction=0.5
        )

    def test_kelly_vs_sharpe_scores(self):
        """Test that Kelly sizing uses variance (volatility^2) and Sharpe proxy uses volatility."""
        predictions = pd.DataFrame([
            {'symbol': 'AAPL', 20: 0.10},
            {'symbol': 'MSFT', 20: 0.05}
        ])
        prices = {
            'AAPL': pd.DataFrame({'Close': [100.0] * 30}),
            'MSFT': pd.DataFrame({'Close': [100.0] * 30})
        }
        
        # Override Close prices to produce specific standard deviations
        # AAPL: vol = 0.02, MSFT: vol = 0.04
        np.random.seed(42)
        prices['AAPL']['Close'] = [100.0 * (1.0 + 0.02 * np.sin(i)) for i in range(30)]
        prices['MSFT']['Close'] = [100.0 * (1.0 + 0.04 * np.sin(i)) for i in range(30)]

        # Calculate using Kelly Sizing
        res_kelly = self.allocator.allocate(predictions, prices, total_portfolio_value=1000000.0, use_kelly=True)
        self.assertFalse(res_kelly.empty)
        
        # Calculate using Sharpe Proxy
        res_sharpe = self.allocator.allocate(predictions, prices, total_portfolio_value=1000000.0, use_kelly=False)
        self.assertFalse(res_sharpe.empty)

        # The raw score for Kelly should be expected_return / (volatility^2)
        # Verify Kelly ranks AAPL higher because AAPL has much lower variance
        aapl_kelly = res_kelly[res_kelly['symbol'] == 'AAPL'].iloc[0]
        msft_kelly = res_kelly[res_kelly['symbol'] == 'MSFT'].iloc[0]
        
        aapl_sharpe = res_sharpe[res_sharpe['symbol'] == 'AAPL'].iloc[0]
        msft_sharpe = res_sharpe[res_sharpe['symbol'] == 'MSFT'].iloc[0]

        # Kelly raw score = 0.5 * return / var
        # Sharpe raw score = return / vol
        self.assertAlmostEqual(aapl_kelly['raw_score'], 0.5 * aapl_kelly['predicted_return'] / (aapl_kelly['volatility'] ** 2), places=4)
        self.assertAlmostEqual(aapl_sharpe['raw_score'], aapl_sharpe['predicted_return'] / aapl_sharpe['volatility'], places=4)

    def test_kelly_cash_retention(self):
        """Test that if the sum of Kelly weights is less than max_total_allocation, it is NOT scaled up."""
        # Low returns and high volatility -> tiny Kelly fractions
        predictions = pd.DataFrame([
            {'symbol': 'AAPL', 20: 0.01},  # 1% predicted return
            {'symbol': 'MSFT', 20: 0.01}
        ])
        
        # High volatility -> 0.15 daily return std
        np.random.seed(42)
        prices = {
            'AAPL': pd.DataFrame({'Close': [100.0 * (1.0 + 0.15 * np.sin(i)) for i in range(30)]}),
            'MSFT': pd.DataFrame({'Close': [100.0 * (1.0 + 0.15 * np.sin(i)) for i in range(30)]})
        }

        # Kelly allocation
        res = self.allocator.allocate(predictions, prices, total_portfolio_value=1000000.0, use_kelly=True, kelly_fraction=0.1)
        self.assertFalse(res.empty)
        
        total_weight = res['weight'].sum()
        # Since expected return is very small and volatility is extremely high, the sum of Kelly fractions
        # should be very small, and it should NOT be scaled up to max_total_allocation (0.80)
        self.assertLess(total_weight, self.allocator.max_total_allocation)
        self.assertGreater(total_weight, 0.0)


if __name__ == '__main__':
    unittest.main()
