import unittest
import numpy as np
import pandas as pd
from datetime import datetime

from src.analysis.portfolio_optimizer import (
    calculate_hrp_weights,
    discretize_weights_to_lot_sizes
)
from src.risk.position_sizing import PortfolioAllocator
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.execution.oms_engine import ExecutionOMSEngine


class TestMinOrderQuantityDiscreteAllocation(unittest.TestCase):
    def test_discretize_weights_basic_lot_sizing(self):
        weights = {'AAPL': 0.40, 'MSFT': 0.40, 'GOOGL': 0.20}
        prices = {'AAPL': 150.0, 'MSFT': 300.0, 'GOOGL': 100.0}
        total_capital = 10_000.0

        result = discretize_weights_to_lot_sizes(
            weights=weights,
            prices=prices,
            total_capital=total_capital,
            lot_sizes={'AAPL': 1, 'MSFT': 1, 'GOOGL': 1},
            max_single_cap=0.50
        )

        self.assertEqual(len(result['shares']), 3)
        self.assertTrue(all(isinstance(s, (int, np.integer)) for s in result['shares']))
        self.assertTrue(all(s > 0 for s in result['shares']))
        self.assertLessEqual(result['total_allocated'], total_capital)
        self.assertGreaterEqual(result['unallocated_cash'], 0.0)

    def test_discretize_weights_tse_100_lot_size(self):
        weights = {'7203.T': 0.50, '9984.T': 0.50}
        prices = {'7203.T': 2500.0, '9984.T': 8000.0}
        total_capital = 2_000_000.0

        result = discretize_weights_to_lot_sizes(
            weights=weights,
            prices=prices,
            total_capital=total_capital,
            lot_sizes={'7203.T': 100, '9984.T': 100},
            max_single_cap=0.60
        )

        for s in result['shares']:
            self.assertEqual(s % 100, 0)
        self.assertLessEqual(result['total_allocated'], total_capital)

    def test_discretize_weights_sub_lot_pruning_and_reallocation(self):
        weights = {'CHEAP': 0.70, 'EXPENSIVE': 0.30}
        prices = {'CHEAP': 10.0, 'EXPENSIVE': 50_000.0}
        total_capital = 10_000.0

        result = discretize_weights_to_lot_sizes(
            weights=weights,
            prices=prices,
            total_capital=total_capital,
            lot_sizes={'CHEAP': 1, 'EXPENSIVE': 1},
            max_single_cap=1.00
        )

        shares_dict = dict(zip(['CHEAP', 'EXPENSIVE'], result['shares']))
        self.assertEqual(shares_dict['EXPENSIVE'], 0)
        self.assertGreater(shares_dict['CHEAP'], 0)
        self.assertLessEqual(result['total_allocated'], total_capital)

    def test_hrp_with_discrete_lot_sizes(self):
        cov = np.array([
            [0.04, 0.01, 0.005],
            [0.01, 0.09, 0.02],
            [0.005, 0.02, 0.16]
        ])
        prices = [100.0, 200.0, 50.0]
        total_cap = 50_000.0

        weights = calculate_hrp_weights(
            cov_matrix=cov,
            symbols=['A', 'B', 'C'],
            prices=prices,
            total_capital=total_cap,
            lot_sizes=[1, 1, 10]
        )

        self.assertEqual(len(weights), 3)
        self.assertTrue(np.all(weights >= 0.0))
        self.assertLessEqual(np.sum(weights), 1.0001)

    def test_portfolio_allocator_discrete_shares_output(self):
        allocator = PortfolioAllocator(target_horizon=20, max_total_allocation=1.0)
        dates = pd.date_range(end=datetime.now(), periods=100)
        prices_dict = {
            '005930': pd.DataFrame({'Close': np.linspace(70000, 75000, 100), 'Volume': 1000000}, index=dates),
            '000660': pd.DataFrame({'Close': np.linspace(120000, 130000, 100), 'Volume': 500000}, index=dates),
            'AAPL': pd.DataFrame({'Close': np.linspace(180, 190, 100), 'Volume': 2000000}, index=dates),
        }
        pred_df = pd.DataFrame({
            'symbol': ['005930', '000660', 'AAPL'],
            'market': ['KOSPI', 'KOSPI', 'SP500'],
            20: [0.08, 0.06, 0.05]
        })

        alloc_df = allocator.allocate(
            pred_df,
            prices_dict=prices_dict,
            total_portfolio_value=100_000_000.0,
            use_hrp=True
        )

        self.assertFalse(alloc_df.empty)
        self.assertIn('shares', alloc_df.columns)
        self.assertIn('lot_size', alloc_df.columns)
        self.assertIn('min_order_qty', alloc_df.columns)
        self.assertIn('realized_weight', alloc_df.columns)
        self.assertIn('executable_amount', alloc_df.columns)

        for _, row in alloc_df.iterrows():
            self.assertEqual(row['shares'], int(row['shares']))
            self.assertGreaterEqual(row['shares'], 0)
            self.assertEqual(row['shares'] % row['lot_size'], 0)

        total_exec = alloc_df['executable_amount'].sum()
        self.assertLessEqual(total_exec, 100_000_000.0 + 1e-4)

    def test_ensemble_scorer_lot_feasibility_metadata(self):
        scorer = EnsembleScoringEngine()
        pred_data = {
            'symbol': ['005930', '7203.T', 'BRK.A'],
            'market': ['KOSPI', 'JAPAN_TSE', 'SP500'],
            'close': [70000.0, 2500.0, 600000.0],
            'regression_score': [0.8, 0.7, 0.6],
            'surge_score': [0.7, 0.6, 0.5],
            'expected_return': [5.0, 4.0, 3.0]
        }
        pred_df = pd.DataFrame(pred_data)
        combined = scorer.combine_predictions(reg_df=pred_df, s_df=pred_df)

        self.assertIn('lot_size', combined.columns)
        self.assertIn('min_order_qty', combined.columns)
        self.assertIn('min_order_amount', combined.columns)
        self.assertIn('is_lot_executable', combined.columns)

        tse_row = combined[combined['symbol'] == '7203.T'].iloc[0]
        self.assertEqual(tse_row['lot_size'], 100)
        self.assertEqual(tse_row['min_order_amount'], 2500.0 * 100)

        krx_row = combined[combined['symbol'] == '005930'].iloc[0]
        self.assertEqual(krx_row['lot_size'], 1)

    def test_oms_gate_lot_size_rounding_and_slicing(self):
        oms = ExecutionOMSEngine(db_path=':memory:', lot_size_krx=1)
        predictions = [
            {
                'symbol': '005930',
                'name': 'Samsung',
                'market': 'KOSPI',
                'close_price': 70000.0,
                'target_price': 70000.0,
                'expected_return': 10.0,
                'action': 'BUY'
            },
            {
                'symbol': '7203.T',
                'name': 'Toyota',
                'market': 'JAPAN_TSE',
                'close_price': 2500.0,
                'target_price': 2500.0,
                'expected_return': 8.0,
                'action': 'BUY'
            }
        ]
        weights = {'005930': 0.20, '7203.T': 0.20}
        total_cap = 100_000_000.0

        plans = oms.generate_order_plan(predictions, weights, total_capital=total_cap)

        self.assertGreater(len(plans), 0)
        plan_dict = {p['symbol']: p for p in plans}

        if '005930' in plan_dict:
            p_krx = plan_dict['005930']
            self.assertEqual(p_krx['lot_size'], 1)
            self.assertEqual(p_krx['quantity'] % p_krx['lot_size'], 0)
            self.assertIn('order_amount', p_krx)

        if '7203.T' in plan_dict:
            p_jp = plan_dict['7203.T']
            self.assertEqual(p_jp['lot_size'], 100)
            self.assertEqual(p_jp['quantity'] % 100, 0)
            self.assertGreaterEqual(p_jp['quantity'] // p_jp['slice_count'], 100)


if __name__ == '__main__':
    unittest.main()
