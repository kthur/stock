import os
import sys
import unittest

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_factor_orthogonalization import TestFactorOrthogonalization
from tests.test_factor_ortho_empirical_stress import TestFactorOrthoEmpiricalStress
from tests.test_correlation_suppression import TestCorrelationSuppression
from tests.test_hpo_and_2d_ensemble import TestHPOAnd2DEnsemble
from tests.test_isotonic_sharpe_calibration import TestIsotonicSharpeCalibration
from tests.test_m1_empirical_challenger import TestM1EmpiricalChallenger

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestFactorOrthogonalization))
    suite.addTests(loader.loadTestsFromTestCase(TestFactorOrthoEmpiricalStress))
    suite.addTests(loader.loadTestsFromTestCase(TestCorrelationSuppression))
    suite.addTests(loader.loadTestsFromTestCase(TestHPOAnd2DEnsemble))
    suite.addTests(loader.loadTestsFromTestCase(TestIsotonicSharpeCalibration))
    suite.addTests(loader.loadTestsFromTestCase(TestM1EmpiricalChallenger))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
