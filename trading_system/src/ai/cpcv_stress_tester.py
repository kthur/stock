"""
CPCV & Historical Stress Testing Engine
Combinatorial Purged Cross-Validation (CPCV) and Historical Scenario Stress Testing Engine.
"""

import itertools
import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StressScenarioResult:
    scenario_name: str
    equity_drawdown: float
    volatility_surge: float
    var_99: float
    cvar_99: float
    passed_stress_test: bool


class CPCVCombinatorialSplitter:
    """
    Combinatorial Purged Cross-Validation (CPCV) Splitter.
    Generates N groups and takes k test groups, applying purging and embargoing to prevent leakage.
    """

    def __init__(self, n_groups: int = 5, k_test_groups: int = 2, purge_pct: float = 0.02, embargo_pct: float = 0.01):
        self.n_groups = n_groups
        self.k_test_groups = k_test_groups
        self.purge_pct = purge_pct
        self.embargo_pct = embargo_pct

    def split(self, n_samples: int) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Generates purged & embargoed train/test index splits."""
        indices = np.arange(n_samples)
        group_size = n_samples // self.n_groups
        groups = [indices[i * group_size : (i + 1) * group_size] for i in range(self.n_groups)]
        if n_samples % self.n_groups != 0:
            groups[-1] = np.concatenate([groups[-1], indices[self.n_groups * group_size :]])

        combos = list(itertools.combinations(range(self.n_groups), self.k_test_groups))
        splits = []

        purge_len = int(n_samples * self.purge_pct)
        embargo_len = int(n_samples * self.embargo_pct)

        for combo in combos:
            test_indices = np.concatenate([groups[g] for g in combo])
            test_mask = np.zeros(n_samples, dtype=bool)
            test_mask[test_indices] = True

            train_mask = ~test_mask.copy()

            # Purge & Embargo around test boundaries
            for g in combo:
                start_idx = groups[g][0]
                end_idx = groups[g][-1]

                # Purge before test start
                p_start = max(0, start_idx - purge_len)
                train_mask[p_start:start_idx] = False

                # Embargo after test end
                e_end = min(n_samples, end_idx + 1 + embargo_len)
                train_mask[end_idx + 1 : e_end] = False

            train_indices = indices[train_mask]
            splits.append((train_indices, test_indices))

        return splits


class HistoricalStressTester:
    """
    Simulates portfolio behavior under severe market historical shocks:
    - 2008 Subprime Financial Crisis
    - 2020 COVID Market Crash
    - 2022 Fed Rate Spike & Tech Selloff
    """

    SCENARIOS = {
        "2008_FINANCIAL_CRISIS": {"equity_shock": -0.45, "vol_mult": 3.2, "corr_breakdown": 0.85},
        "2020_COVID_PANIC": {"equity_shock": -0.35, "vol_mult": 4.0, "corr_breakdown": 0.90},
        "2022_FED_RATE_HIKE": {"equity_shock": -0.25, "vol_mult": 2.1, "corr_breakdown": 0.70},
    }

    def __init__(self, mdd_limit: float = -0.30):
        self.mdd_limit = mdd_limit

    def run_stress_tests(
        self, weights: Dict[str, float], asset_volatilities: Dict[str, float]
    ) -> List[StressScenarioResult]:
        """Runs stress tests for all historical scenarios on current portfolio allocation."""
        results = []
        symbols = list(weights.keys())
        w_vec = np.array([weights[s] for s in symbols])

        if len(w_vec) == 0:
            return results

        for sc_name, params in self.SCENARIOS.items():
            shock = params["equity_shock"]
            vol_mult = params["vol_mult"]

            # Expected portfolio return under shock
            simulated_drawdown = float(np.sum(w_vec * shock))
            vols = np.array([asset_volatilities.get(s, 0.20) for s in symbols])
            simulated_vol = float(np.sum(w_vec * vols) * vol_mult)

            # VaR 99% and CVaR 99% under parametric normal / fat tail assumption
            var_99 = float(simulated_drawdown - 2.33 * simulated_vol / np.sqrt(252))
            cvar_99 = float(simulated_drawdown - 2.68 * simulated_vol / np.sqrt(252))

            passed = simulated_drawdown >= self.mdd_limit

            results.append(
                StressScenarioResult(
                    scenario_name=sc_name,
                    equity_drawdown=simulated_drawdown,
                    volatility_surge=simulated_vol,
                    var_99=var_99,
                    cvar_99=cvar_99,
                    passed_stress_test=passed,
                )
            )

        return results
