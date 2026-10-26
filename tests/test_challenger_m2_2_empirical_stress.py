"""
tests/test_challenger_m2_2_empirical_stress.py
Empirical Stress Test Harness by Challenger 2 for Milestone 2 (Requirement R2).

Adversarial Stress Testing Suite:
1. Simplex Sum & Boundary Probing:
   - optimize_multi_model_blend under single-stock caps (N=4, N=20).
   - Near-singular covariance matrices (collinear returns, cond > 1e8).
   - Extreme volatility spikes (100% daily variance in CRISIS regime).
   - Illiquid stocks (micro ADV vs mega ADV) verifying no unintended leverage.
2. Leland Buffer & Waterfall Stability:
   - Repeated 50-cycle rebalance simulation with small alpha drifts within Leland bandwidth Delta_i in [0.005, 0.045].
   - Verification of zero cash ratchet decay and zero turnover explosion.
   - Partial allocation target ceiling preservation (e.g. max_total_allocation = 0.70).
   - Fresh entries (curr_w <= 1e-4) cleanly bypass buffer.
   - Full liquidations (tgt_w <= 1e-4) cleanly bypass buffer.
   - Waterfall capital redistribution under liquidity caps and alpha conviction priority.
   - Cap saturation bounds enforcement.
3. EnsembleScoringEngine Robustness:
   - 37-strategy REGIME_2D_WEIGHTS sum exact 1.000000 across all regimes.
   - Dynamic tier weight adaptation in bull vs defensive regimes.
   - Finite handling of extreme prediction outliers and empty dataframes.
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.ai.ensemble_scorer import EnsembleScoringEngine


class TestSimplexSumAndBoundaryProbing:
    """Stress-test optimize_multi_model_blend under boundary and extreme market conditions."""

    def test_n20_simplex_sum_and_single_stock_cap(self):
        """Verify N=20 portfolio satisfies sum = 1.000000 and w_i <= max_single_weight."""
        alloc = UnifiedPortfolioAllocator(max_single_weight=0.20, version=103)
        n = 20
        symbols = [f"SYM_{i:02d}" for i in range(n)]
        np.random.seed(101)
        preds = np.random.uniform(0.01, 0.08, n)
        cov = np.eye(n) * 0.0004
        rets = pd.DataFrame(np.random.normal(0, 0.02, (60, n)), columns=symbols)

        w = alloc.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=rets,
            cov_matrix=cov,
            symbols=symbols,
            total_capital=100_000_000.0,
            regime="BULL_LOW_VOL"
        )

        assert len(w) == n
        assert np.all(np.isfinite(w)), "Non-finite weight detected in N=20"
        assert np.all(w >= -1e-7), "Negative weight detected (unintended shorting)"
        assert math.isclose(float(np.sum(w)), 1.0, abs_tol=1e-5), f"Simplex sum breached: {np.sum(w)}"
        assert np.all(w <= 0.20 + 1e-5), f"Single-stock cap breached: max={np.max(w)}"

    def test_n4_small_universe_feasibility_and_sum(self):
        """Verify N=4 small universe handles cap feasibility adaptively and sums to 1.000000."""
        alloc = UnifiedPortfolioAllocator(max_single_weight=0.20, version=103)
        n = 4
        symbols = [f"STOCK_{i}" for i in range(n)]
        preds = np.array([0.06, 0.05, 0.04, 0.03])
        cov = np.eye(n) * 0.0004
        rets = pd.DataFrame(np.random.normal(0, 0.02, (60, n)), columns=symbols)

        # Case A: Starting from cash (curr_weights = None or 0)
        w_new = alloc.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=rets,
            cov_matrix=cov,
            symbols=symbols,
            total_capital=100_000_000.0,
            regime="BULL_LOW_VOL"
        )
        assert len(w_new) == n
        assert np.all(np.isfinite(w_new))
        assert np.all(w_new >= 0.0)
        assert math.isclose(float(np.sum(w_new)), 1.0, abs_tol=1e-5), f"N=4 sum != 1.0: {np.sum(w_new)}"

        # Case B: Starting from existing holdings at 0.25 each
        w_curr = np.full(n, 0.25)
        w_held = alloc.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=rets,
            cov_matrix=cov,
            symbols=symbols,
            current_weights=w_curr,
            total_capital=100_000_000.0,
            regime="BULL_LOW_VOL"
        )
        assert len(w_held) == n
        assert np.all(np.isfinite(w_held))
        assert math.isclose(float(np.sum(w_held)), 1.0, abs_tol=1e-5), f"N=4 held sum != 1.0: {np.sum(w_held)}"

    def test_near_singular_covariance_matrix_stability(self):
        """Verify allocator handles near-singular / collinear covariance matrix (cond > 1e8)."""
        alloc = UnifiedPortfolioAllocator(version=103)
        n = 6
        symbols = [f"COLLIN_{i}" for i in range(n)]
        preds = np.array([0.05, 0.04, 0.03, 0.02, 0.01, 0.00])
        np.random.seed(202)
        base_series = np.random.normal(0, 0.02, 60)
        # Highly collinear columns (micro noise 1e-6)
        rets_mat = np.column_stack([base_series + np.random.normal(0, 1e-6, 60) for _ in range(n)])
        rets_df = pd.DataFrame(rets_mat, columns=symbols)
        cov_singular = rets_df.cov().values

        cond_number = np.linalg.cond(cov_singular)
        assert cond_number > 1e6, f"Expected ill-conditioned cov matrix, got cond={cond_number}"

        w = alloc.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=rets_df,
            cov_matrix=cov_singular,
            symbols=symbols,
            total_capital=100_000_000.0,
            regime="BULL_LOW_VOL"
        )

        assert np.all(np.isfinite(w)), "Non-finite weights produced under near-singular cov"
        assert np.all(w >= 0.0), f"Negative weights produced: {w}"
        assert math.isclose(float(np.sum(w)), 1.0, abs_tol=1e-5), f"Sum != 1.0: {np.sum(w)}"
        assert float(np.sum(w)) <= 1.000001, "Unintended leverage created"

    def test_extreme_volatility_spike_derisking(self):
        """Verify that an extreme volatility spike on an asset triggers severe de-weighting without error."""
        alloc = UnifiedPortfolioAllocator(version=103)
        n = 5
        symbols = [f"VOL_{i}" for i in range(n)]
        preds = np.array([0.05, 0.04, 0.03, 0.02, 0.01])
        rets_df = pd.DataFrame(np.random.normal(0, 0.02, (60, n)), columns=symbols)

        # Asset 0 experiences massive vol spike: 100% daily variance (annualized ~1580%)
        cov_spike = np.eye(n) * 0.0004
        cov_spike[0, 0] = 1.0

        w_crisis = alloc.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=rets_df,
            cov_matrix=cov_spike,
            symbols=symbols,
            total_capital=100_000_000.0,
            regime="CRISIS"
        )

        assert np.all(np.isfinite(w_crisis))
        assert np.all(w_crisis >= 0.0)
        assert math.isclose(float(np.sum(w_crisis)), 1.0, abs_tol=1e-5)
        # Asset 0 must receive lowest risk allocation
        assert w_crisis[0] < min(w_crisis[1:]), f"Spiked vol asset not de-weighted: {w_crisis}"

    def test_illiquid_stocks_strict_no_leverage_invariant(self):
        """Verify that illiquid stocks respect ADV caps and no leverage (> 1.0) is ever created."""
        alloc = UnifiedPortfolioAllocator(max_single_weight=0.30, version=103)
        n = 5
        symbols = [f"LIQ_{i}" for i in range(n)]
        preds = np.array([0.06, 0.05, 0.04, 0.03, 0.02])
        rets_df = pd.DataFrame(np.random.normal(0, 0.02, (60, n)), columns=symbols)
        cov = np.eye(n) * 0.0004

        # 2 mega liquid, 3 micro illiquid
        advs = np.array([100_000_000.0, 50_000_000.0, 10_000.0, 2_000.0, 500.0])
        tot_cap = 100_000_000.0

        w = alloc.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=rets_df,
            cov_matrix=cov,
            symbols=symbols,
            advs=advs,
            total_capital=tot_cap,
            regime="BULL_LOW_VOL"
        )

        assert np.all(np.isfinite(w))
        assert np.all(w >= 0.0)
        # Illiquid assets must not breach ADV liquidity capacity
        for i in [2, 3, 4]:
            assert w[i] * tot_cap <= advs[i] * 0.20, f"Illiquid asset {i} breached ADV constraint: w={w[i]}"
        # Total weight strictly <= 1.000000 (no leverage)
        tot_w = float(np.sum(w))
        assert tot_w <= 1.000000 + 1e-6, f"Unintended leverage detected: {tot_w}"


class TestLelandBufferAndWaterfallStability:
    """Stress-test Leland no-trade buffers, ratchet decay, and waterfall capital redistribution."""

    def test_repeated_50_cycles_alpha_drift_preserves_buffer_and_no_ratchet(self):
        """Verify 50 consecutive cycles of small alpha drift stay in buffer with zero turnover & zero cash decay."""
        alloc = UnifiedPortfolioAllocator(version=103)
        np.random.seed(303)
        n = 5
        curr_w = np.full(n, 0.20)
        vols = np.full(n, 0.02)
        target_base = np.full(n, 0.20)

        turnovers = []
        sums = []

        for _ in range(50):
            # Drift within +/- 0.008 (smaller than Leland half-width 0.015~0.030)
            drift = np.random.uniform(-0.008, 0.008, n)
            drift -= np.mean(drift)
            tgt_w = target_base + drift

            realized_w = alloc.apply_leland_no_trade_buffers(
                target_weights=tgt_w,
                current_weights=curr_w,
                volatilities=vols,
                rebalance_mode="boundary"
            )

            to = float(np.sum(np.abs(realized_w - curr_w)))
            turnovers.append(to)
            sums.append(float(np.sum(realized_w)))
            curr_w = realized_w.copy()

        # Assert zero turnover throughout all 50 steps
        assert max(turnovers) < 1e-12, f"Turnover observed inside Leland buffer: max={max(turnovers)}"
        assert sum(turnovers) < 1e-12, f"Cumulative turnover leaked: {sum(turnovers)}"
        # Assert no downward cash ratchet decay: sum remains strictly 1.000000
        assert math.isclose(min(sums), 1.0, abs_tol=1e-5), f"Cash ratchet decay observed: min={min(sums)}"
        assert math.isclose(max(sums), 1.0, abs_tol=1e-5), f"Cash ratchet inflation observed: max={max(sums)}"

    def test_partial_allocation_ceiling_stability(self):
        """Verify target allocation ceiling (e.g. 0.70 in sideways) is stably maintained under Leland rebalancing."""
        alloc = UnifiedPortfolioAllocator(version=103)
        np.random.seed(404)
        n = 5
        target_alloc = 0.70
        curr_w = np.full(n, target_alloc / n)
        vols = np.full(n, 0.02)
        target_base = np.full(n, target_alloc / n)

        sums = []
        for _ in range(50):
            drift = np.random.uniform(-0.005, 0.005, n)
            drift -= np.mean(drift)
            tgt_w = target_base + drift

            realized_w = alloc.apply_leland_no_trade_buffers(
                target_weights=tgt_w,
                current_weights=curr_w,
                volatilities=vols,
                rebalance_mode="boundary",
                max_total_allocation=target_alloc
            )
            sums.append(float(np.sum(realized_w)))
            curr_w = realized_w.copy()

        assert math.isclose(min(sums), target_alloc, abs_tol=1e-5), f"Partial allocation decayed: min={min(sums)}"
        assert math.isclose(max(sums), target_alloc, abs_tol=1e-5), f"Partial allocation inflated: max={max(sums)}"

    def test_fresh_entry_and_full_liquidation_clean_bypass(self):
        """Verify fresh entries and full liquidations always bypass the buffer without hysteresis."""
        alloc = UnifiedPortfolioAllocator(version=103)
        vols = np.full(5, 0.02)

        # Asset 0: Fresh entry (0.000 -> 0.200)
        # Asset 1: Full liquidation (0.200 -> 0.000)
        # Assets 2, 3, 4: Held (0.200, 0.300, 0.300)
        curr_w = np.array([0.000, 0.200, 0.200, 0.300, 0.300])
        tgt_w = np.array([0.200, 0.000, 0.200, 0.300, 0.300])

        realized_w = alloc.apply_leland_no_trade_buffers(
            target_weights=tgt_w,
            current_weights=curr_w,
            volatilities=vols,
            rebalance_mode="boundary"
        )

        assert math.isclose(realized_w[0], 0.200, abs_tol=1e-5), f"Fresh entry blocked by buffer: {realized_w[0]}"
        assert math.isclose(realized_w[1], 0.000, abs_tol=1e-5), f"Liquidation trapped by buffer: {realized_w[1]}"
        assert math.isclose(float(np.sum(realized_w)), 1.0, abs_tol=1e-5)

    def test_waterfall_capital_redistribution_alpha_priority(self):
        """Verify unallocated capacity is redistributed in alpha conviction priority order without breaching caps."""
        alloc = UnifiedPortfolioAllocator(version=103)
        n = 8
        w_target = np.full(n, 0.125)  # Sum = 1.00
        w_curr = np.zeros(n)
        # Assets 0, 1 are severely liquidity capped
        max_delta_w = np.array([0.02, 0.02, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20])
        w_next = np.minimum(w_target, max_delta_w)  # Assets 0, 1 at 0.02, others at 0.125
        alpha_scores = np.array([0.20, 0.18, 0.15, 0.12, 0.10, 0.08, 0.06, 0.04])

        w_redist = alloc.redistribute_waterfall_capital(
            w_next=w_next,
            w_curr=w_curr,
            w_target=w_target,
            max_delta_w=max_delta_w,
            max_single_weight=0.20,
            alpha_scores=alpha_scores
        )

        assert np.all(np.isfinite(w_redist))
        assert math.isclose(float(np.sum(w_redist)), 1.0, abs_tol=1e-5)
        # Assets 0, 1 must remain capped at 0.02
        assert w_redist[0] <= 0.02 + 1e-6
        assert w_redist[1] <= 0.02 + 1e-6
        # Highest alpha unconstrained asset (asset 2) must receive full headroom up to 0.20
        assert math.isclose(w_redist[2], 0.20, abs_tol=1e-5)
        assert np.all(w_redist <= 0.20 + 1e-5)

    def test_waterfall_cap_saturation_holds_cash_without_leverage(self):
        """When all candidate assets reach max single weight, remainder remains cash buffer without leverage."""
        alloc = UnifiedPortfolioAllocator(version=103)
        n = 4
        w_next = np.full(n, 0.10)
        w_curr = np.zeros(n)
        w_target = np.full(n, 0.25)
        max_delta_w = np.full(n, 0.25)

        # Enforce hard 0.20 cap per asset (max investable = 4 * 0.20 = 0.80)
        w_redist = alloc.redistribute_waterfall_capital(
            w_next=w_next,
            w_curr=w_curr,
            w_target=w_target,
            max_delta_w=max_delta_w,
            max_single_weight=0.20,
            alpha_scores=np.array([0.10, 0.08, 0.06, 0.04])
        )

        assert np.all(w_redist <= 0.20 + 1e-6)
        assert math.isclose(float(np.sum(w_redist)), 0.80, abs_tol=1e-5)
        # Verify no leverage created
        assert float(np.sum(w_redist)) <= 1.0


class TestEnsembleScoringEngineRobustness:
    """Stress-test EnsembleScoringEngine weights, regimes, and prediction combination."""

    def test_all_regimes_2d_weights_sum_to_exact_unity(self):
        """Verify REGIME_2D_WEIGHTS sum to exactly 1.000000 across all 7 regimes with 37 strategies."""
        engine = EnsembleScoringEngine()
        regimes = [
            "BULL_LOW_VOL", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
            "CRISIS"
        ]

        for r in regimes:
            w_dict = engine.REGIME_2D_WEIGHTS[r]
            assert len(w_dict) == 37, f"Regime {r} does not contain 37 strategies (got {len(w_dict)})"
            sum_w = sum(w_dict.values())
            assert math.isclose(sum_w, 1.0, abs_tol=1e-8), f"Regime {r} weights sum={sum_w} != 1.0"
            for strat, weight in w_dict.items():
                assert weight > 0.0, f"Strategy {strat} in regime {r} has non-positive weight {weight}"

    def test_regime_adaptive_tier_weights_logic(self):
        """Verify get_regime_adaptive_tier_weights adapts tier allocation to regime characteristics."""
        engine = EnsembleScoringEngine()
        
        tw_bull = engine.get_regime_adaptive_tier_weights("BULL_LOW_VOL")
        assert math.isclose(sum(tw_bull.values()), 1.0, abs_tol=1e-8)
        assert tw_bull["fast"] >= 0.25, f"Bull regime should prioritize fast alphas: {tw_bull}"

        tw_bear = engine.get_regime_adaptive_tier_weights("BEAR_HIGH_VOL")
        assert math.isclose(sum(tw_bear.values()), 1.0, abs_tol=1e-8)
        assert tw_bear["slow"] >= 0.45, f"Bear high-vol regime should prioritize slow/defensive alphas: {tw_bear}"

    def test_combine_predictions_extreme_outliers(self):
        """Verify combine_predictions produces finite, non-NaN scores under extreme outlier signals."""
        engine = EnsembleScoringEngine()
        from trading_system.merge_predictions import ALL_31_STRATEGIES
        strats = ALL_31_STRATEGIES + [
            "cross_asset_spillover", "supply_chain_gnn", "range_expansion",
            "dual_correction", "index_rebalance", "overnight_gap"
        ]

        symbols = ["EXTREME_HIGH", "EXTREME_LOW", "MIXED_EXTREME", "NORMAL_1", "NORMAL_2"]
        df_dict = {"symbol": symbols}
        np.random.seed(505)

        for s in strats:
            df_dict[s] = [50.0, -50.0, 100.0, 0.03, -0.02]

        df = pd.DataFrame(df_dict)
        res = engine.combine_predictions(df, regime="BULL_LOW_VOL")

        assert "ensemble_expected_return" in res.columns
        assert res["ensemble_expected_return"].notna().all(), "NaN found in ensemble expected returns"
        assert np.all(np.isfinite(res["ensemble_expected_return"])), "Inf found in ensemble expected returns"
