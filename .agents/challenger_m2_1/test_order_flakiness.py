"""
Test execution order flakiness check.
"""

import sys
import unittest
import numpy as np

sys.path.insert(0, r"d:\Finance\code\stock")
from trading_system.tests.test_quad_factor_optimizer import TestQuadFactorOptimizer

def run_tests_in_order(order):
    print(f"\n--- Running tests in order: {order} ---")
    suite = unittest.TestSuite()
    for method_name in order:
        suite.addTest(TestQuadFactorOptimizer(method_name))
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    print("Failures:", len(result.failures))
    for test, err in result.failures:
        print("Failed test:", test)
        print("Error:", err.splitlines()[-1])

if __name__ == '__main__':
    order1 = [
        'test_fallback_on_infeasible_constraints',
        'test_optimize_portfolio_method_alias',
        'test_portfolio_optimizer_integration',
        'test_quad_factor_neutrality_bounds',
        'test_sector_cap_constraint',
        'test_weight_sum_equality_constraint'
    ]
    run_tests_in_order(order1)

    order2 = [
        'test_weight_sum_equality_constraint',
        'test_quad_factor_neutrality_bounds',
        'test_sector_cap_constraint',
        'test_fallback_on_infeasible_constraints',
        'test_portfolio_optimizer_integration',
        'test_optimize_portfolio_method_alias'
    ]
    run_tests_in_order(order2)
