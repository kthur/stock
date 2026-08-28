# -*- coding: utf-8 -*-
"""
Unit tests for ConceptDriftDetector.
"""

import unittest
import numpy as np
import pandas as pd

from src.analysis.drift_detector import ConceptDriftDetector


class TestDriftDetector(unittest.TestCase):

    def setUp(self):
        self.detector = ConceptDriftDetector(
            psi_moderate_threshold=0.10,
            psi_severe_threshold=0.25
        )

    def test_psi_identical_distributions(self):
        np.random.seed(42)
        ref = np.random.normal(0, 1, 1000)
        cur = np.random.normal(0, 1, 1000)

        psi = self.detector.calculate_psi(ref, cur)
        # Identical distributions should have very low PSI (< 0.05)
        self.assertLess(psi, 0.08)

    def test_psi_shifted_distributions(self):
        np.random.seed(42)
        ref = np.random.normal(0, 1, 1000)
        cur = np.random.normal(2, 1, 1000)  # Significant shift

        psi = self.detector.calculate_psi(ref, cur)
        self.assertGreater(psi, 0.25)

    def test_wasserstein_distance(self):
        ref = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        cur = np.array([3.0, 4.0, 5.0, 6.0, 7.0])

        w_dist = self.detector.calculate_wasserstein(ref, cur)
        self.assertAlmostEqual(w_dist, 2.0, places=2)

    def test_evaluate_feature_drift(self):
        ref_df = pd.DataFrame({
            'feature_stable': np.random.normal(0, 1, 200),
            'feature_drifted': np.random.normal(0, 1, 200),
        })
        cur_df = pd.DataFrame({
            'feature_stable': np.random.normal(0, 1, 200),
            'feature_drifted': np.random.normal(3, 1.5, 200),
        })

        report = self.detector.evaluate_feature_drift(ref_df, cur_df)
        self.assertIn('overall_status', report)
        self.assertIn('feature_details', report)
        self.assertEqual(report['feature_details']['feature_drifted']['status'], 'SEVERE_DRIFT')


if __name__ == '__main__':
    unittest.main()
