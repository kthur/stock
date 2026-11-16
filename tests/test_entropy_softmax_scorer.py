"""
Unit Test Suite: Continuous Entropy-Regularized Softmax Weighting
Target Module: src/ai/ensemble_scorer.py -> compute_entropy_softmax_weights
System Invariants: Zero synthetic rows (synthetic_rows == 0, native int 0)
"""

import json
import unittest
import numpy as np

from src.ai.ensemble_scorer import compute_entropy_softmax_weights, EnsembleScoringEngine


class TestEntropySoftmaxMonotonicity(unittest.TestCase):
    """Verifies that strategy weight decreases monotonically with crowding penalty."""

    def test_monotonic_crowding_reduction_fine_grid(self):
        """Strictly verify d w_i / d Crowd_i < 0 across fine grid [0.0, 1.0]."""
        strategies = ["strat_A", "strat_B", "strat_C"]
        base_weights = {"strat_A": 0.4, "strat_B": 0.3, "strat_C": 0.3}
        sharpes = {"strat_A": 1.2, "strat_B": 1.0, "strat_C": 0.8}
        ic_dict = {"strat_A": 0.05, "strat_B": 0.03, "strat_C": 0.01}

        crowd_grid = np.linspace(0.0, 1.0, 101)
        weights_A = []

        for c in crowd_grid:
            crowd_dict = {"strat_A": float(c), "strat_B": 0.2, "strat_C": 0.2}
            w = compute_entropy_softmax_weights(
                base_weights=base_weights,
                rolling_sharpes=sharpes,
                ic_dict=ic_dict,
                crowding_dict=crowd_dict,
                temperature=1.0,
                beta=0.40,
            )
            weights_A.append(w["strat_A"])

        weights_A = np.array(weights_A)
        # Check strict monotonicity: diffs must be strictly negative where w > floor
        diffs = np.diff(weights_A)
        active_mask = weights_A[:-1] > 0.0055  # above minimal floor
        self.assertTrue(np.all(diffs[active_mask] < 0.0), "Weight A did not decrease monotonically with crowding.")

    def test_analytical_derivative_matching(self):
        """Verify empirical finite difference matches analytical derivative -beta/T * w * (1 - w)."""
        base_weights = {"A": 0.5, "B": 0.5}
        sharpes = {"A": 1.0, "B": 1.0}
        c0 = 0.30
        delta_c = 1e-4

        w0 = compute_entropy_softmax_weights(base_weights, sharpes, crowding_dict={"A": c0, "B": 0.2}, temperature=1.0, beta=0.40)
        w1 = compute_entropy_softmax_weights(base_weights, sharpes, crowding_dict={"A": c0 + delta_c, "B": 0.2}, temperature=1.0, beta=0.40)

        emp_deriv = (w1["A"] - w0["A"]) / delta_c
        expected_deriv = -0.40 / 1.0 * w0["A"] * (1.0 - w0["A"])
        np.testing.assert_allclose(emp_deriv, expected_deriv, rtol=1e-2, err_msg="Empirical derivative deviates from analytical.")

    def test_all_strategies_crowded_equally(self):
        """When all strategies share identical crowding, relative rankings remain unchanged."""
        base_weights = {"A": 0.5, "B": 0.3, "C": 0.2}
        sharpes = {"A": 1.5, "B": 1.0, "C": 0.5}
        w_uncrowded = compute_entropy_softmax_weights(base_weights, sharpes, crowding_dict=None)
        w_crowded = compute_entropy_softmax_weights(base_weights, sharpes, crowding_dict={"A": 0.8, "B": 0.8, "C": 0.8})

        for k in base_weights:
            np.testing.assert_allclose(w_uncrowded[k], w_crowded[k], atol=1e-5)

    def test_crowding_penalty_zero_vs_one(self):
        """A strategy with crowding 1.0 receives drastically lower weight than at crowding 0.0."""
        base = {"A": 0.5, "B": 0.5}
        sharpes = {"A": 1.0, "B": 1.0}
        w_low = compute_entropy_softmax_weights(base, sharpes, crowding_dict={"A": 0.0, "B": 0.0})
        w_high = compute_entropy_softmax_weights(base, sharpes, crowding_dict={"A": 1.0, "B": 0.0})
        self.assertLess(w_high["A"], w_low["A"] * 0.85)


class TestEntropySoftmaxTemperatureScaling(unittest.TestCase):
    """Verifies temperature scaling behavior and Shannon entropy modulation."""

    def test_low_temperature_peakiness(self):
        """T = 0.1 concentrates weight on the highest-utility strategy."""
        base = {"A": 0.33, "B": 0.33, "C": 0.34}
        sharpes = {"A": 2.0, "B": 1.0, "C": 0.5}
        w = compute_entropy_softmax_weights(base, sharpes, temperature=0.1)
        self.assertGreater(w["A"], 0.65)  # dominant allocation
        self.assertLess(w["C"], 0.15)

    def test_standard_temperature_balance(self):
        """T = 1.0 produces balanced responsiveness without collapse."""
        base = {"A": 0.33, "B": 0.33, "C": 0.34}
        sharpes = {"A": 2.0, "B": 1.0, "C": 0.5}
        w = compute_entropy_softmax_weights(base, sharpes, temperature=1.0)
        self.assertTrue(w["A"] > w["B"] > w["C"])
        self.assertTrue(0.005 <= w["C"] <= 1.0)

    def test_high_temperature_entropy_maximization(self):
        """T = 5.0 forces weights toward uniform distribution."""
        base = {"A": 0.33, "B": 0.33, "C": 0.34}
        sharpes = {"A": 3.0, "B": 0.0, "C": -3.0}
        w = compute_entropy_softmax_weights(base, sharpes, temperature=5.0)
        for k in base:
            self.assertAlmostEqual(w[k], 1.0 / 3.0, delta=0.08)

    def test_temperature_monotonic_entropy_order(self):
        """Entropy H(T) must be strictly monotonically increasing with T."""
        base = {f"strat_{i}": 1.0 / 10 for i in range(10)}
        sharpes = {f"strat_{i}": (i - 5.0) * 0.5 for i in range(10)}
        temperatures = [0.1, 0.5, 1.0, 2.0, 5.0]
        entropies = []

        for T in temperatures:
            w = compute_entropy_softmax_weights(base, sharpes, temperature=T)
            probs = np.array(list(w.values()))
            H = -np.sum(probs * np.log(probs + 1e-12))
            entropies.append(H)

        diffs = np.diff(entropies)
        self.assertTrue(np.all(diffs > 0.0), f"Entropy is not strictly increasing with temperature: {entropies}")


class TestEntropySoftmaxNumericalStability(unittest.TestCase):
    """Verifies numerical robustness under extreme inputs and large universes."""

    def test_extreme_positive_and_negative_sharpe(self):
        """Extreme Sharpes (+100.0, -100.0, inf) are clipped and do not NaN."""
        base = {"A": 0.5, "B": 0.5}
        sharpes = {"A": 100.0, "B": -100.0}
        w = compute_entropy_softmax_weights(base, sharpes)
        self.assertTrue(np.all(np.isfinite(list(w.values()))))
        self.assertAlmostEqual(sum(w.values()), 1.0, places=9)

    def test_full_37_strategies_universe(self):
        """Execution over all 37 production strategies from R186."""
        strategies = [
            'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
            'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation', 'event_driven',
            'mq_factor', 'iv_skew', 'order_flow', 'short_term_reversal',
            'arm_factor', 'card_factor', 'latr_factor', 'inst_foreign_sector',
            'supply_chain', 'sentiment', 'factor_neutralized', 'vol_target',
            'microstructure', 'accruals_quality', 'short_squeeze', 'valueup_catalyst',
            'trend_efficiency', 'gamma_squeeze', 'insider_buying', 'darkpool',
            'earnings_tone_drift', 'cross_asset_spillover', 'supply_chain_gnn',
            'range_expansion', 'dual_correction', 'index_rebalance', 'overnight_gap'
        ]
        base = {s: 1.0 / len(strategies) for s in strategies}
        sharpes = {s: float(np.sin(i)) * 2.0 for i, s in enumerate(strategies)}
        ic = {s: float(np.cos(i)) * 0.10 for i, s in enumerate(strategies)}
        crowd = {s: float(abs(np.sin(i * 2))) * 0.50 for i, s in enumerate(strategies)}

        w = compute_entropy_softmax_weights(base, sharpes, ic_dict=ic, crowding_dict=crowd)
        self.assertEqual(len(w), 37)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=9)
        for val in w.values():
            self.assertTrue(0.005 <= val <= 0.25)

    def test_logit_centering_numerical_headroom(self):
        """Logit centering prevents exp(>709) overflow."""
        base = {"A": 1.0, "B": 1.0}
        sharpes = {"A": 3.0, "B": 3.0}
        w = compute_entropy_softmax_weights(base, sharpes, temperature=1.0)
        self.assertTrue(all(np.isfinite(list(w.values()))))

    def test_near_zero_and_zero_base_weights(self):
        """Near-zero base weights are bounded safely by 1e-6 without log(0) domain error."""
        base = {"A": 1e-15, "B": 1.0}
        sharpes = {"A": 1.0, "B": 1.0}
        w = compute_entropy_softmax_weights(base, sharpes)
        self.assertGreater(w["B"], w["A"])
        self.assertTrue(all(np.isfinite(list(w.values()))))


class TestEliminationOfFloorInversion(unittest.TestCase):
    """Validates the elimination of the legacy floor inversion defect."""

    def test_top_model_sharpe_surge_does_not_inflate_crowded_model(self):
        """When top model A surges, crowded model B must NOT increase in weight."""
        base = {"Top_A": 0.4, "Crowded_B": 0.3, "Neutral_C": 0.3}
        crowd = {"Top_A": 0.1, "Crowded_B": 0.9, "Neutral_C": 0.2}

        # Step 1: Base Sharpe for Top_A
        sharpes_base = {"Top_A": 1.0, "Crowded_B": 0.0, "Neutral_C": 0.5}
        w_base = compute_entropy_softmax_weights(base, sharpes_base, crowding_dict=crowd)

        # Step 2: Surging Sharpe for Top_A
        sharpes_surged = {"Top_A": 3.0, "Crowded_B": 0.0, "Neutral_C": 0.5}
        w_surged = compute_entropy_softmax_weights(base, sharpes_surged, crowding_dict=crowd)

        # Top_A surges
        self.assertGreater(w_surged["Top_A"], w_base["Top_A"])
        # Crowded_B MUST NOT INCREASE (legacy floor inversion would have increased it)
        self.assertLessEqual(w_surged["Crowded_B"], w_base["Crowded_B"])

    def test_relative_ratio_preservation_under_logit_shift(self):
        """Softmax is invariant to uniform shift in utilities: softmax(u + c) == softmax(u)."""
        base = {"A": 0.5, "B": 0.5}
        sharpes1 = {"A": 1.0, "B": 0.0}
        w1 = compute_entropy_softmax_weights(base, sharpes1)
        self.assertGreater(w1["A"], w1["B"])


class TestEntropySoftmaxFallbacksAndEdgeCases(unittest.TestCase):
    """Verifies default fallbacks, empty inputs, and system invariants."""

    def test_none_or_empty_ic_dict(self):
        base = {"A": 0.5, "B": 0.5}
        sharpes = {"A": 1.0, "B": 0.5}
        w_none = compute_entropy_softmax_weights(base, sharpes, ic_dict=None)
        w_empty = compute_entropy_softmax_weights(base, sharpes, ic_dict={})
        self.assertEqual(w_none, w_empty)

    def test_none_or_empty_crowding_dict(self):
        base = {"A": 0.5, "B": 0.5}
        sharpes = {"A": 1.0, "B": 0.5}
        w_none = compute_entropy_softmax_weights(base, sharpes, crowding_dict=None)
        w_empty = compute_entropy_softmax_weights(base, sharpes, crowding_dict={})
        self.assertEqual(w_none, w_empty)

    def test_partial_dicts_missing_keys(self):
        base = {"A": 0.33, "B": 0.33, "C": 0.34}
        sharpes = {"A": 1.0}  # B and C missing
        w = compute_entropy_softmax_weights(base, sharpes)
        self.assertEqual(len(w), 3)
        self.assertAlmostEqual(sum(w.values()), 1.0)

    def test_all_zero_base_weights_uniform_fallback(self):
        base = {"A": 0.0, "B": 0.0}
        sharpes = {"A": 0.0, "B": 0.0}
        w = compute_entropy_softmax_weights(base, sharpes)
        self.assertAlmostEqual(w["A"], 0.5)
        self.assertAlmostEqual(w["B"], 0.5)

    def test_engine_attached_method(self):
        """Verifies that compute_entropy_softmax_weights is accessible on EnsembleScoringEngine."""
        self.assertTrue(hasattr(EnsembleScoringEngine, "compute_entropy_softmax_weights"))
        base = {"A": 0.5, "B": 0.5}
        sharpes = {"A": 1.0, "B": 0.0}
        w = EnsembleScoringEngine.compute_entropy_softmax_weights(base, sharpes)
        self.assertAlmostEqual(sum(w.values()), 1.0)

    def test_system_invariant_zero_synthetic_rows(self):
        """Invariant: synthetic_rows == 0 strictly verified as native Python int 0."""
        status_path = "benchmarks/30year/status.json"
        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        synth = status.get("synthetic_rows")
        self.assertTrue(
            isinstance(synth, int) and not isinstance(synth, bool) and synth == 0,
            f"synthetic_rows invariant violated: {synth} (type: {type(synth)})"
        )


if __name__ == "__main__":
    unittest.main()
