import os
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Add paths to sys.path for robust imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.stat_arb import StatisticalArbitrageEngine, _extract_15d_features, _estimate_adf_pvalue, _estimate_half_life

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class TestFastCointegrationScanner(unittest.TestCase):

    def setUp(self):
        self.stat_arb = StatisticalArbitrageEngine(use_clustering=True, n_clusters=20, clustering_method="kmeans")

    def _make_synthetic_universe(self, n_symbols: int = 150, n_days: int = 120, planted_pairs: int = 3, seed: int = 42) -> dict:
        np.random.seed(seed)
        universe = {}
        for i in range(n_symbols):
            sym = f"SYM_{i:04d}"
            returns = np.random.normal(0.0002, 0.015, size=n_days)
            p = 100.0 * np.exp(np.cumsum(returns))
            universe[sym] = list(p)

        # Plant cointegrated pairs
        for p in range(planted_pairs):
            s1 = f"SYM_{p:04d}"
            s2 = f"SYM_{p+50:04d}"
            p1 = np.array(universe[s1])
            noise = np.random.normal(0, 0.2, size=n_days)
            p2 = p1 * 1.2 + noise
            # Spike near end below stop loss limit
            p1[-1] = p1[-1] + 1.0
            universe[s1] = list(p1)
            universe[s2] = list(p2)

        return universe

    def test_kmeans_optics_pre_clustering(self):
        """Verify feature extraction and pre-clustering logic."""
        universe = self._make_synthetic_universe(n_symbols=150, n_days=120)
        feats = []
        for sym, p in universe.items():
            f = _extract_15d_features(pd.Series(p))
            self.assertEqual(len(f), 15)
            feats.append(f)

        feat_matrix = np.array(feats)
        labels, centroids = self.stat_arb._cluster_symbols(feat_matrix, n_clusters=10)
        self.assertEqual(len(labels), 150)
        self.assertLessEqual(centroids.shape[0], 10)

    def test_two_stage_filtering_recall(self):
        """Verify that planted cointegrated pairs are detected."""
        universe = self._make_synthetic_universe(n_symbols=150, n_days=120, planted_pairs=3)
        pairs = self.stat_arb.find_cointegrated_pairs(universe, min_correlation=0.70)
        self.assertTrue(len(pairs) > 0)
        detected_pair_tuples = [p["pair"] for p in pairs]
        # At least one planted pair detected
        planted = [("SYM_0000", "SYM_0050"), ("SYM_0001", "SYM_0051"), ("SYM_0002", "SYM_0052")]
        found_any = any(pt in detected_pair_tuples or (pt[1], pt[0]) in detected_pair_tuples for pt in planted)
        self.assertTrue(found_any)

    def test_log_price_adf_and_half_life(self):
        """Test ADF test and half-life estimation on stationary spread."""
        np.random.seed(42)
        steps = 100
        # AR(1) mean-reverting process: x_t = 0.7 * x_{t-1} + e_t
        spread = np.zeros(steps)
        for t in range(1, steps):
            spread[t] = 0.7 * spread[t-1] + np.random.normal(0, 1)

        t_stat, p_val = _estimate_adf_pvalue(spread)
        hl = _estimate_half_life(spread)

        self.assertLess(t_stat, -2.5)
        self.assertLess(p_val, 0.10)
        self.assertGreater(hl, 0.5)
        self.assertLess(hl, 10.0)

    def test_fast_scan_edge_cases(self):
        """Test edge cases: empty input, short history, constant prices."""
        # Empty
        pairs_empty = self.stat_arb.find_cointegrated_pairs({})
        self.assertEqual(pairs_empty, [])

        # Short history (< 30)
        short_dict = {"A": list(range(20)), "B": list(range(20))}
        pairs_short = self.stat_arb.find_cointegrated_pairs(short_dict)
        self.assertEqual(pairs_short, [])

        # Constant price (zero std)
        const_dict = {"A": [100.0] * 100, "B": [100.0] * 100}
        pairs_const = self.stat_arb.find_cointegrated_pairs(const_dict)
        self.assertEqual(pairs_const, [])

    def test_benchmark_3379_symbols_under_30s(self):
        """Primary M2 R2 SLA Benchmark: Full universe (3,379 symbols x 120 days) scan execution time < 30.0 seconds."""
        np.random.seed(42)
        n_symbols = 3379
        n_days = 120

        # Fast vector generation of 3,379 synthetic symbol prices
        rets = np.random.normal(0.0002, 0.015, size=(n_symbols, n_days))
        cum_rets = np.cumsum(rets, axis=1)
        prices_mat = 100.0 * np.exp(cum_rets)

        # Plant cointegrated pairs
        for p in range(5):
            prices_mat[p+1000] = prices_mat[p] * 1.1 + np.random.normal(0, 0.1, size=n_days)
            prices_mat[p][-1] += 0.8

        universe = {f"SYM_{i:04d}": prices_mat[i].tolist() for i in range(n_symbols)}

        t0 = time.perf_counter()
        pairs = self.stat_arb.find_cointegrated_pairs(universe, min_correlation=0.70)
        elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, 30.0)
        print(f"\n[BENCHMARK] Scanned {n_symbols} symbols in {elapsed:.2f}s (SLA Target: < 30.0s)")


if __name__ == '__main__':
    unittest.main()
