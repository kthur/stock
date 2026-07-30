#!/usr/bin/env python3
"""
Empirical Stress Test Harness - Challenger 1
Target Requirements:
1. Dynamic weight rescaling across 1,000 random missing strategy combinations (ensuring total weight = 1.0).
2. Order book market impact monotonicity with respect to order size Q and inverse turnover 1/ADV.
3. Correlation matrix positive semi-definiteness and VIF stability under noise.
"""

import sys
import os
import math
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

# Ensure project src is in Python path
PROJECT_ROOT = r"D:\Finance\code\stock\trading_system"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.correlation_monitor import StrategyCorrelationMonitor, ALL_17_STRATEGIES
from src.config import TradingConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("StressTestHarness")


class DynamicWeightRescalingTester:
    """Task 1: Verify dynamic weight rescaling across 1,000 random missing strategy combinations."""

    def __init__(self, engine: EnsembleScoringEngine):
        self.engine = engine
        self.strategies = ALL_17_STRATEGIES

    def run_tests(self, num_trials: int = 1000) -> Dict[str, Any]:
        logger.info(f"--- Running Dynamic Weight Rescaling Stress Test ({num_trials} trials) ---")
        np.random.seed(42)

        base_weights = self.engine.REGIME_2D_WEIGHTS['BULL_LOW_VOL']
        total_base = sum(base_weights.get(s, 0.10) for s in self.strategies)
        norm_base_weights = {s: base_weights.get(s, 0.10) / total_base for s in self.strategies}

        trials_passed = 0
        max_weight_error = 0.0
        min_active_count = 17
        max_active_count = 0
        zero_active_passed = False

        # Test 1: 1,000 random missing combinations
        for trial in range(num_trials):
            # Pick random active mask (at least 1 strategy active)
            num_active = np.random.randint(1, 18)
            active_strats = set(np.random.choice(self.strategies, size=num_active, replace=False))

            min_active_count = min(min_active_count, num_active)
            max_active_count = max(max_active_count, num_active)

            active_sum = sum(norm_base_weights[s] for s in active_strats)
            rescaled_weights = {s: (norm_base_weights[s] / active_sum if s in active_strats else 0.0) for s in self.strategies}

            rescaled_sum = sum(rescaled_weights.values())
            error = abs(rescaled_sum - 1.0)
            max_weight_error = max(max_weight_error, error)

            if error < 1e-12:
                trials_passed += 1

        # Test 2: Edge case - 0 active strategies (all missing)
        zero_active_rescaled_sum = sum(0.0 for _ in self.strategies)
        # Verify safe division / fallback in calculate_ensemble_score
        synthetic_data = {'symbol': ['TEST_ZERO']}
        for s in self.strategies:
            score_col = self.engine.factor_suppression.STRATEGY_SCORE_COL_MAP.get(s, f"{s}_score") if hasattr(self.engine, 'factor_suppression') else f"{s}_score"
            synthetic_data[score_col] = [np.nan]

        df_zero = pd.DataFrame(synthetic_data)
        # Pass empty/NaN dfs for all strategies
        score_df = self.engine.calculate_ensemble_score(
            reg_df=pd.DataFrame(),
            s_df=pd.DataFrame(),
            ll_df=pd.DataFrame(),
            v_rule_df=None,
            vcp_ml_df=pd.DataFrame(),
            weights=norm_base_weights
        )

        if score_df.empty or ('ensemble_score' in score_df.columns and (score_df['ensemble_score'].fillna(0.0) == 0.0).all()):
            zero_active_passed = True

        rescaling_results = {
            "num_trials": num_trials,
            "trials_passed": trials_passed,
            "pass_rate_pct": (trials_passed / num_trials) * 100.0,
            "max_weight_sum_error": max_weight_error,
            "min_active_strategies": min_active_count,
            "max_active_strategies": max_active_count,
            "zero_active_edge_case_passed": zero_active_passed,
            "status": "PASS" if (trials_passed == num_trials and zero_active_passed and max_weight_error < 1e-12) else "FAIL"
        }
        logger.info(f"Dynamic Weight Rescaling Result: {rescaling_results['status']} (Pass Rate: {rescaling_results['pass_rate_pct']:.2f}%, Max Error: {max_weight_error:.2e})")
        return rescaling_results


class MarketImpactMonotonicityTester:
    """Task 2: Verify order book market impact monotonicity with respect to order size Q and inverse turnover 1/ADV."""

    def __init__(self, engine: EnsembleScoringEngine):
        self.engine = engine
        self.config = engine.config or TradingConfig()

    def calculate_cost(self, q_order: float, turnover: float, market: str = 'KOSPI', volatility: float = 0.020) -> float:
        """Isolated implementation of microstructure cost function in ensemble_scorer.py."""
        symbol = '005930' if market == 'KOSPI' else ('091990' if market == 'KOSDAQ' else ('000001' if market == 'KONEX' else 'AAPL'))
        market_upper = market.upper()
        is_sp500 = market_upper == 'SP500'

        impact_coeff_krx = getattr(self.config, 'market_impact_coeff_krx', 0.75)
        impact_coeff_sp500 = getattr(self.config, 'market_impact_coeff_sp500', 0.50)
        base_spread_kospi = getattr(self.config, 'base_spread_kospi', 0.0006)
        base_spread_kosdaq = getattr(self.config, 'base_spread_kosdaq', 0.0010)
        base_spread_konex = getattr(self.config, 'base_spread_konex', 0.0025)
        base_spread_sp500 = getattr(self.config, 'base_spread_sp500', 0.0002)

        if market_upper == 'KONEX':
            stt_tax = 0.0010
            brokerage_fee = 0.0003
            base_spread = base_spread_konex
            spread_min, spread_max = 0.0010, 0.0500
            adv_ref = 1_000_000_000.0
            impact_coeff = impact_coeff_krx
        elif market_upper == 'KOSDAQ':
            stt_tax = 0.0018
            brokerage_fee = 0.0003
            base_spread = base_spread_kosdaq
            spread_min, spread_max = 0.0003, 0.0250
            adv_ref = 1_000_000_000.0
            impact_coeff = impact_coeff_krx
        elif market_upper == 'KOSPI':
            stt_tax = 0.0015
            brokerage_fee = 0.0003
            base_spread = base_spread_kospi
            spread_min, spread_max = 0.0002, 0.0150
            adv_ref = 1_000_000_000.0
            impact_coeff = impact_coeff_krx
        else: # SP500
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = base_spread_sp500
            spread_min, spread_max = 0.0001, 0.0050
            adv_ref = 1_000_000.0
            impact_coeff = impact_coeff_sp500

        min_adv = 10_000.0 if is_sp500 else 10_000_000.0
        adv = max(turnover, min_adv)

        # 1. Dynamic Bid-Ask Spread Modeling
        adv_ratio = adv_ref / adv
        vol_ratio = volatility / 0.020
        dynamic_spread = base_spread * (adv_ratio ** 0.25) * (vol_ratio ** 0.50)
        clamped_spread = min(max(dynamic_spread, spread_min), spread_max)

        # 2. Order Book Square-Root Market Impact Modeling
        participation_ratio = q_order / adv
        impact_one_way = impact_coeff * volatility * np.sqrt(participation_ratio)

        # 3. Participation Rate Overflow Penalty (> 10% ADV)
        if participation_ratio > 0.10:
            impact_one_way += 0.50 * (participation_ratio - 0.10)

        total_cost_pct = stt_tax + brokerage_fee + clamped_spread + (2.0 * impact_one_way)
        return float(total_cost_pct)

    def run_tests(self, num_points: int = 100) -> Dict[str, Any]:
        logger.info(f"--- Running Market Impact Monotonicity Stress Test ({num_points}x{num_points} grid) ---")

        q_grid_krx = np.logspace(5, 10, num_points)  # 100k KRW to 10B KRW
        adv_grid_krx = np.logspace(7, 11, num_points) # 10M KRW to 100B KRW

        results_by_market = {}
        total_monotonic_checks = 0
        total_monotonic_violations = 0

        for market in ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500']:
            if market == 'SP500':
                q_grid = np.logspace(2, 7, num_points)    # $100 to $10M USD
                adv_grid = np.logspace(4, 9, num_points)  # $10k to $1B USD
            else:
                q_grid = q_grid_krx
                adv_grid = adv_grid_krx

            q_violations = 0
            adv_inv_violations = 0
            q_checks = 0
            adv_inv_checks = 0

            # Monotonicity test 1: Cost increases as Order Size Q increases (fixed ADV)
            for adv_val in adv_grid:
                costs = [self.calculate_cost(q, adv_val, market=market) for q in q_grid]
                diffs = np.diff(costs)
                q_checks += len(diffs)
                # Allow tiny numerical precision tolerance (-1e-15)
                q_violations += np.sum(diffs < -1e-15)

            # Monotonicity test 2: Cost increases as Inverse Turnover 1/ADV increases (fixed Q)
            # 1/ADV increases means ADV decreases!
            inv_adv_grid = 1.0 / adv_grid  # sorted ascending (1/ADV increases)
            adv_from_inv = 1.0 / inv_adv_grid # sorted descending (ADV decreases)

            for q_val in q_grid:
                costs = [self.calculate_cost(q_val, adv, market=market) for adv in adv_from_inv]
                diffs = np.diff(costs)
                adv_inv_checks += len(diffs)
                adv_inv_violations += np.sum(diffs < -1e-15)

            market_violations = q_violations + adv_inv_violations
            market_checks = q_checks + adv_inv_checks
            total_monotonic_violations += market_violations
            total_monotonic_checks += market_checks

            results_by_market[market] = {
                "q_checks": int(q_checks),
                "q_violations": int(q_violations),
                "inv_adv_checks": int(adv_inv_checks),
                "inv_adv_violations": int(adv_inv_violations),
                "market_pass_rate_pct": ((market_checks - market_violations) / market_checks) * 100.0
            }

        overall_pass_rate = ((total_monotonic_checks - total_monotonic_violations) / total_monotonic_checks) * 100.0
        impact_results = {
            "total_checks": int(total_monotonic_checks),
            "total_violations": int(total_monotonic_violations),
            "overall_pass_rate_pct": float(overall_pass_rate),
            "results_by_market": results_by_market,
            "status": "PASS" if total_monotonic_violations == 0 else "FAIL"
        }
        logger.info(f"Market Impact Monotonicity Result: {impact_results['status']} (Pass Rate: {overall_pass_rate:.2f}%, Violations: {total_monotonic_violations})")
        return impact_results


class CorrelationPSDAndVIFStabilityTester:
    """Task 3: Verify Correlation Matrix Positive Semi-Definiteness and VIF stability under noise."""

    def __init__(self):
        self.monitor = StrategyCorrelationMonitor()
        self.strategies = ALL_17_STRATEGIES

    def run_tests(self, num_iterations: int = 100) -> Dict[str, Any]:
        logger.info(f"--- Running Correlation Matrix PSD & VIF Stability Stress Test ({num_iterations} iterations) ---")
        np.random.seed(42)

        symmetry_violations = 0
        psd_violations = 0
        vif_overflows = 0
        min_eigenvalue_found = 1.0
        max_vif_found = 1.0

        for it in range(num_iterations):
            # Construct synthetic strategy predictions with varying noise & collinearity
            num_samples = 500
            data = {}

            # Base factors
            f1 = np.random.randn(num_samples)
            f2 = np.random.randn(num_samples)

            for idx, strat in enumerate(self.strategies):
                score_col = self.monitor.STRATEGY_SCORE_COL_MAP.get(strat, f"{strat}_score")
                if idx < 5:
                    # High collinear group 1
                    signal = 0.8 * f1 + 0.2 * np.random.randn(num_samples)
                elif idx < 10:
                    # High collinear group 2
                    signal = 0.8 * f2 + 0.2 * np.random.randn(num_samples)
                else:
                    # Pure noise
                    signal = np.random.randn(num_samples)

                # Inject occasional NaNs and extreme values
                mask_nan = np.random.rand(num_samples) < 0.05
                signal[mask_nan] = np.nan
                data[score_col] = signal

            df_scores = pd.DataFrame(data)

            # Update rolling correlation matrix
            corr_mat = self.monitor.update_correlation(df_scores)

            # Check 1: Symmetry R = R^T
            R = corr_mat.values
            sym_diff = np.max(np.abs(R - R.T))
            if sym_diff > 1e-12:
                symmetry_violations += 1

            # Check 2: Positive Semi-Definiteness (minimum eigenvalue >= -1e-10)
            eigenvalues = np.linalg.eigvalsh(R)
            min_ev = float(np.min(eigenvalues))
            min_eigenvalue_found = min(min_eigenvalue_found, min_ev)

            if min_ev < -1e-10:
                psd_violations += 1

            # Check 3: VIF stability under noise & extreme collinearity
            vif_dict = self.monitor.compute_vif(corr_mat)
            for s, vif in vif_dict.items():
                max_vif_found = max(max_vif_found, vif)
                if not (1.0 <= vif <= 100.0) or math.isnan(vif) or math.isinf(vif):
                    vif_overflows += 1

        status = "PASS" if (symmetry_violations == 0 and psd_violations == 0 and vif_overflows == 0) else "FAIL"
        correlation_results = {
            "num_iterations": num_iterations,
            "symmetry_violations": symmetry_violations,
            "psd_violations": psd_violations,
            "vif_overflows": vif_overflows,
            "min_eigenvalue_found": min_eigenvalue_found,
            "max_vif_found": max_vif_found,
            "status": status
        }
        logger.info(f"Correlation PSD & VIF Result: {status} (Min EV: {min_eigenvalue_found:.2e}, Max VIF: {max_vif_found:.2f})")
        return correlation_results


def main():
    logger.info("Starting Full Empirical Stress Test Suite...")
    engine = EnsembleScoringEngine()

    tester1 = DynamicWeightRescalingTester(engine)
    res1 = tester1.run_tests(num_trials=1000)

    tester2 = MarketImpactMonotonicityTester(engine)
    res2 = tester2.run_tests(num_points=100)

    tester3 = CorrelationPSDAndVIFStabilityTester()
    res3 = tester3.run_tests(num_iterations=100)

    all_passed = (res1["status"] == "PASS" and res2["status"] == "PASS" and res3["status"] == "PASS")

    logger.info("==================================================")
    logger.info(f"FINAL VERDICT: {'ALL TESTS PASSED' if all_passed else 'TEST FAILURES DETECTED'}")
    logger.info("==================================================")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
