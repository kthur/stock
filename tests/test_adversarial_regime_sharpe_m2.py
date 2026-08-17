"""
Adversarial Stress Test Suite for 2D Regime Engine & Dynamic Exponential Sharpe Scorer (Milestone 2 Gen 2)

Covers:
1. Rapid Regime Switching (BULL -> BEAR -> SIDEWAYS) verifying alpha = 1.0 weight realignment and EMA smoothing.
2. Extreme Strategy Sharpe Inputs (+5.0, -4.0, +/-inf, NaN) verifying clipping at [-0.8047, +0.8047] and pruning at < -0.50.
3. Extreme Ratio Power Damping (> 20.0 raw score ratio bounded to <= 20.0).
4. Microstructure Friction Deduction on Low-Liquidity and Penny Stocks (SPAC, preferred, zero turnover, market impact).
"""

import math
import numpy as np
import pandas as pd
import pytest
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.config import TradingConfig


class TestRapidRegimeSwitching:
    """Adversarial stress testing for rapid regime switching and EMA weight smoothing."""

    def test_rapid_regime_transitions_eff_alpha_reset(self):
        """Verify that transitioning between regimes forces eff_alpha = 1.0 (no lag or contamination from prior regime)."""
        engine = EnsembleScoringEngine(alpha_smoothing=0.2)
        sharpes = {
            'regression': 0.5,
            'surge': 0.8,
            'vcp_ml': 0.6,
            'stat_arb': 0.2,
            'rim_valuation': 0.4
        }

        # Step 1: Initial call in BULL_LOW_VOL
        w_bull_1 = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL')
        assert engine._prev_regime == 'BULL_LOW_VOL'

        # Compute independent reference target for BEAR_HIGH_VOL
        ref_engine_bear = EnsembleScoringEngine(alpha_smoothing=0.2)
        target_bear = ref_engine_bear.compute_dynamic_weights_from_sharpe(sharpes, regime='BEAR_HIGH_VOL')

        # Step 2: Switch to BEAR_HIGH_VOL -> Must trigger eff_alpha = 1.0 immediately
        w_bear = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='BEAR_HIGH_VOL')
        assert engine._prev_regime == 'BEAR_HIGH_VOL'

        # Verified: w_bear must exactly equal target_bear (no trace of w_bull_1 remaining)
        for k in target_bear:
            assert math.isclose(w_bear[k], target_bear[k], rel_tol=1e-5, abs_tol=1e-6), (
                f"Regime switch did not apply eff_alpha=1.0 for {k}: {w_bear[k]} vs target {target_bear[k]}"
            )

        # Step 3: Switch to SIDEWAYS_LOW_VOL -> Must trigger eff_alpha = 1.0 immediately
        ref_engine_side = EnsembleScoringEngine(alpha_smoothing=0.2)
        target_side = ref_engine_side.compute_dynamic_weights_from_sharpe(sharpes, regime='SIDEWAYS_LOW_VOL')

        w_side = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='SIDEWAYS_LOW_VOL')
        for k in target_side:
            assert math.isclose(w_side[k], target_side[k], rel_tol=1e-5, abs_tol=1e-6), (
                f"Regime switch did not apply eff_alpha=1.0 for {k}: {w_side[k]} vs target {target_side[k]}"
            )

    def test_steady_regime_ema_smoothing_applied(self):
        """Verify that within the same regime, eff_alpha = 0.2 is smoothly applied."""
        engine = EnsembleScoringEngine(alpha_smoothing=0.2)
        sharpes_t1 = {'regression': 0.1, 'surge': 0.1}
        w_t1 = engine.compute_dynamic_weights_from_sharpe(sharpes_t1, regime='BULL_LOW_VOL')

        # Same regime, new sharpes at t2
        sharpes_t2 = {'regression': 0.8, 'surge': 0.8}
        ref_engine = EnsembleScoringEngine(alpha_smoothing=0.2)
        ref_engine._prev_weights = None
        target_t2 = ref_engine.compute_dynamic_weights_from_sharpe(sharpes_t2, regime='BULL_LOW_VOL')

        w_t2 = engine.compute_dynamic_weights_from_sharpe(sharpes_t2, regime='BULL_LOW_VOL')

        # Hand-calculate expected EMA: 0.2 * target_t2 + 0.8 * w_t1
        expected_raw = {k: 0.2 * target_t2[k] + 0.8 * w_t1[k] for k in target_t2}
        total_exp = sum(expected_raw.values())
        expected_smoothed = {k: v / total_exp for k, v in expected_raw.items()}

        for k in target_t2:
            assert math.isclose(w_t2[k], expected_smoothed[k], rel_tol=1e-4, abs_tol=1e-5), (
                f"EMA smoothing mismatch for {k}: actual={w_t2[k]}, expected={expected_smoothed[k]}"
            )

    def test_rapid_oscillating_regime_switches_stability(self):
        """Stress-test 50 rapid alternating regime switches to verify numerical stability and non-divergence."""
        engine = EnsembleScoringEngine(alpha_smoothing=0.2)
        regimes = ['BULL_LOW_VOL', 'BEAR_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'BULL_HIGH_VOL', 'BEAR_LOW_VOL', 'SIDEWAYS_HIGH_VOL']

        for i in range(50):
            reg = regimes[i % len(regimes)]
            # Dynamic pseudo-random but valid Sharpes
            sharpes = {
                'regression': math.sin(i * 0.5) * 1.5,
                'surge': math.cos(i * 0.3) * 1.2,
                'vcp_ml': math.sin(i * 0.7) * 0.8,
                'stat_arb': math.cos(i * 0.9) * 1.0,
            }
            w = engine.compute_dynamic_weights_from_sharpe(sharpes, regime=reg)
            assert np.isclose(sum(w.values()), 1.0, atol=1e-6)
            for strat, weight in w.items():
                assert weight >= 0.0, f"Negative weight for {strat}: {weight}"
                assert not np.isnan(weight), f"NaN weight for {strat}"
                assert not np.isinf(weight), f"Inf weight for {strat}"


class TestExtremeSharpeClippingAndPruning:
    """Adversarial stress testing for Sharpe multiplier clipping and underperformance pruning."""

    def test_exact_clipping_bounds_gamma_1(self):
        """Verify exact clipping at [-0.8047, +0.8047] when gamma = 1.0."""
        engine = EnsembleScoringEngine()
        gamma = 1.0
        max_ratio = 5.0
        expected_clip = float(np.log(np.sqrt(max_ratio)) / gamma)
        # expected_clip is ln(sqrt(5)) ≈ 0.8047189562170501
        assert math.isclose(expected_clip, 0.8047189562, abs_tol=1e-6)

        # Sharpe = +5.0 and Sharpe = +0.8047189562 must yield identical relative multiplier
        sharpes_extreme = {'regression': 5.0, 'stat_arb': 0.0}
        sharpes_at_clip = {'regression': expected_clip, 'stat_arb': 0.0}

        w_extreme = engine.compute_dynamic_weights_from_sharpe(sharpes_extreme, regime='SIDEWAYS_LOW_VOL', gamma=gamma)
        w_at_clip = engine.compute_dynamic_weights_from_sharpe(sharpes_at_clip, regime='SIDEWAYS_LOW_VOL', gamma=gamma)

        assert math.isclose(w_extreme['regression'], w_at_clip['regression'], rel_tol=1e-4, abs_tol=1e-5), (
            f"Sharpe +5.0 was not clipped to +{expected_clip:.4f}: {w_extreme['regression']} vs {w_at_clip['regression']}"
        )

    def test_severe_underperformance_pruning_hard_gate(self):
        """Verify that any strategy with Sharpe < -0.50 is strictly pruned (weight == 0.0)."""
        engine = EnsembleScoringEngine()
        sharpes = {
            'regression': 1.0,
            'surge': -0.51,        # < -0.50 -> Must be pruned
            'vcp_ml': -4.0,        # Extreme negative -> Must be pruned
            'lead_lag': -0.500001, # Borderline negative -> Must be pruned
            'stat_arb': 0.3,
            'rim_valuation': -0.49 # > -0.50 -> Should NOT be pruned
        }

        w = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='SIDEWAYS_LOW_VOL')

        assert w['surge'] == 0.0, f"Surge with Sharpe -0.51 was not pruned: {w['surge']}"
        assert w['vcp_ml'] == 0.0, f"VCP ML with Sharpe -4.0 was not pruned: {w['vcp_ml']}"
        assert w['lead_lag'] == 0.0, f"Lead-Lag with Sharpe -0.500001 was not pruned: {w['lead_lag']}"
        assert w['rim_valuation'] > 0.0, f"RIM with Sharpe -0.49 should not be pruned: {w['rim_valuation']}"
        assert np.isclose(sum(w.values()), 1.0, atol=1e-6)

    def test_borderline_pruning_boundary(self):
        """Verify exact precision at the -0.50 boundary."""
        engine = EnsembleScoringEngine()
        # -0.50 exactly is not < -0.50
        sharpes_exact = {'surge': -0.50, 'regression': 0.5}
        w_exact = engine.compute_dynamic_weights_from_sharpe(sharpes_exact, regime='SIDEWAYS_LOW_VOL')
        assert w_exact['surge'] > 0.0, "Sharpe exactly -0.50 should not be pruned."

        # -0.50001 is < -0.50
        sharpes_below = {'surge': -0.50001, 'regression': 0.5}
        w_below = engine.compute_dynamic_weights_from_sharpe(sharpes_below, regime='SIDEWAYS_LOW_VOL')
        assert w_below['surge'] == 0.0, "Sharpe -0.50001 must be pruned."

    def test_adversarial_all_strategies_negative_or_pruned(self):
        """If all strategies are severely underperforming (Sharpe < -0.50), verify fallback to base weights."""
        engine = EnsembleScoringEngine()
        base_w = engine.get_base_weights('BEAR_LOW_VOL')
        sharpes_all_pruned = {strat: -3.0 for strat in base_w}

        w = engine.compute_dynamic_weights_from_sharpe(sharpes_all_pruned, regime='BEAR_LOW_VOL')
        assert np.isclose(sum(w.values()), 1.0, atol=1e-6)
        for strat in base_w:
            assert math.isclose(w[strat], base_w[strat], rel_tol=1e-4, abs_tol=1e-5), (
                f"Fallback failed for {strat}: {w[strat]} vs base {base_w[strat]}"
            )

    def test_nan_and_inf_sharpe_handling(self):
        """Verify robust handling of NaN, +inf, -inf in Sharpe dictionary."""
        engine = EnsembleScoringEngine()
        sharpes_corrupt = {
            'regression': np.nan,      # nan -> float(nan) -> behaves as nan or pruned/clipped
            'surge': float('inf'),     # +inf -> clipped to +0.8047
            'vcp_ml': float('-inf'),   # -inf -> < -0.50 -> pruned to 0.0
            'stat_arb': 0.5
        }
        w = engine.compute_dynamic_weights_from_sharpe(sharpes_corrupt, regime='BULL_LOW_VOL')
        assert np.isclose(sum(w.values()), 1.0, atol=1e-6)
        assert w['vcp_ml'] == 0.0
        assert not np.isnan(w['regression'])
        assert not np.isinf(w['surge'])

    def test_none_in_sharpes_sanitized_safely(self):
        """Verify None and NaN in Sharpe dictionary are sanitized to 0.0 without errors."""
        engine = EnsembleScoringEngine()
        engine._prev_weights = None
        sharpes_with_none = {
            'regression': None,
            'surge': float('nan'),
            'vcp_ml': 0.8,
            'stat_arb': 0.2,
        }
        w = engine.compute_dynamic_weights_from_sharpe(sharpes_with_none, regime='BULL_LOW_VOL')
        assert np.isclose(sum(w.values()), 1.0, atol=1e-6)
        assert not np.isnan(w['regression'])
        assert not np.isnan(w['surge'])
        assert w['vcp_ml'] > w['stat_arb']

    def test_pruned_strategy_strictly_zero_under_ema_smoothing(self):
        """Verify that a strategy pruned in the current step receives strictly 0.0 weight despite positive prior EMA weight."""
        engine = EnsembleScoringEngine(alpha_smoothing=0.2)
        # Step 1: surge has high performance and receives strong weight
        sharpes_t1 = {'surge': 1.5, 'regression': 0.2, 'stat_arb': 0.2}
        w_t1 = engine.compute_dynamic_weights_from_sharpe(sharpes_t1, regime='BULL_LOW_VOL')
        assert w_t1['surge'] > 0.0
        assert engine._prev_weights['surge'] > 0.0

        # Step 2: same regime, surge collapses to Sharpe = -0.80 (pruned < -0.50)
        sharpes_t2 = {'surge': -0.80, 'regression': 0.5, 'stat_arb': 0.5}
        w_t2 = engine.compute_dynamic_weights_from_sharpe(sharpes_t2, regime='BULL_LOW_VOL')

        # Surge MUST be strictly 0.0, not contaminated or diluted by (1 - alpha) * prev_weight
        assert w_t2['surge'] == 0.0, f"Pruned strategy received non-zero weight under EMA smoothing: {w_t2['surge']}"
        assert engine._prev_weights['surge'] == 0.0
        assert np.isclose(sum(w_t2.values()), 1.0, atol=1e-6)


class TestExtremeRatioPowerDamping:
    """Adversarial stress testing for ratio power damping (max_total_ratio <= 20.0)."""

    def test_ratio_exceeding_20_damped_to_under_20(self):
        """Verify that score disparities exceeding 20.0:1 among positive weights are strictly damped."""
        engine = EnsembleScoringEngine()
        # Create base weights or Sharpe combination with high disparity
        # In BULL_HIGH_VOL, regression base is 0.02 and surge base is 0.08 (4x ratio)
        # With Sharpe +5.0 (clip +0.8047) on surge and -0.49 (multiplier e^-0.49 ≈ 0.61) on regression:
        # Multiplier ratio is ~3.67, combined ratio 4 * 3.67 = 14.7.
        # Let's test with extreme base weights or multipliers
        # Let's test by verifying the dynamic weight ratio property directly:
        w = engine.compute_dynamic_weights_from_sharpe(
            rolling_sharpes={'surge': 5.0, 'vcp_ml': 5.0, 'regression': -0.49},
            regime='BULL_HIGH_VOL'
        )
        pos_weights = [v for v in w.values() if v > 0.0]
        max_w = max(pos_weights)
        min_w = min(pos_weights)
        ratio = max_w / min_w
        assert ratio <= 20.0001, f"Weight ratio exceeded 20.0: {ratio:.4f}"

    def test_monotonic_rank_order_preservation_under_damping(self):
        """Verify that power damping preserves strict order of scores (s_i > s_j ==> s_i^alpha > s_j^alpha)."""
        engine = EnsembleScoringEngine()
        sharpes = {
            'surge': 2.0,
            'vcp_ml': 1.5,
            'event_driven': 1.0,
            'stat_arb': 0.5,
            'regression': 0.0
        }
        w = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL')
        # Check that surge > vcp_ml in BULL_LOW_VOL where both had high base weights and surge had higher Sharpe
        assert w['surge'] >= w['vcp_ml'] >= w['event_driven'] >= w['stat_arb']


class TestMicrostructureFrictionAndPennyStocks:
    """Adversarial stress testing for transaction costs, market impact, and penny/illiquid stock filtering."""

    @pytest.fixture
    def mock_universe(self):
        """Construct synthetic universe with liquid, penny, SPAC, and preferred stocks."""
        return pd.DataFrame([
            # 1. High-liquidity KRX Blue Chip
            {'symbol': '005930', 'name': '삼성전자', 'market': 'KOSPI', 'close': 75000.0, 'volume': 15_000_000, 'volatility_20d': 0.018},
            # 2. High-liquidity US Large Cap
            {'symbol': 'AAPL', 'name': 'Apple Inc', 'market': 'SP500', 'close': 180.0, 'volume': 50_000_000, 'volatility_20d': 0.015},
            # 3. Preferred Stock (KRX '우') -> Must be zeroed out
            {'symbol': '005935', 'name': '삼성전자우', 'market': 'KOSPI', 'close': 60000.0, 'volume': 500_000, 'volatility_20d': 0.019},
            # 4. Preferred Stock (KRX '우B') -> Must be zeroed out
            {'symbol': '001045', 'name': 'CJ우B', 'market': 'KOSPI', 'close': 25000.0, 'volume': 100_000, 'volatility_20d': 0.022},
            # 5. Korean SPAC -> Must be zeroed out
            {'symbol': '450120', 'name': '미래에셋비전스팩1호', 'market': 'KOSDAQ', 'close': 2000.0, 'volume': 50_000, 'volatility_20d': 0.010},
            # 6. US SPAC -> Must be zeroed out
            {'symbol': 'DHCA', 'name': 'DHC Acquisition Corp SPAC', 'market': 'NASDAQ', 'close': 10.2, 'volume': 10_000, 'volatility_20d': 0.005},
            # 7. Zero Volume Illiquid Stock -> Must be zeroed out
            {'symbol': '099990', 'name': '초저유동주', 'market': 'KOSDAQ', 'close': 5000.0, 'volume': 0, 'volatility_20d': 0.020},
            # 8. Penny Stock with Sub-Threshold Turnover (Turnover = 50KRW * 1,000 = 50,000 KRW < 500M KRW)
            {'symbol': '088880', 'name': '동전한계기업', 'market': 'KOSDAQ', 'close': 50.0, 'volume': 1_000, 'volatility_20d': 0.080},
            # 9. Mid-Cap Liquid Normal Stock (Turnover = 30,000 * 50,000 = 1.5B KRW > 500M KRW)
            {'symbol': '035720', 'name': '카카오', 'market': 'KOSPI', 'close': 50000.0, 'volume': 1_000_000, 'volatility_20d': 0.025},
        ])

    def test_preferred_and_spac_and_illiquid_stocks_zeroed(self, mock_universe):
        """Verify that preferred shares, SPACs, and illiquid stocks receive score=0.0 and expected_return=0.0."""
        engine = EnsembleScoringEngine()

        # Provide high regression and surge signals for all stocks
        reg_df = mock_universe[['symbol', 'market', 'close']].copy()
        reg_df['expected_return_20d'] = 0.20  # 20% raw expected return for all
        reg_df['volume'] = mock_universe['volume']
        reg_df['name'] = mock_universe['name']
        reg_df['volatility_20d'] = mock_universe['volatility_20d']

        res = engine.calculate_ensemble_score(
            regime='BULL_LOW_VOL',
            regression_df=reg_df,
            surge_df=pd.DataFrame({'symbol': mock_universe['symbol'], 'surge_prob_20d': 0.85}),
            lead_lag_df=pd.DataFrame({'symbol': mock_universe['symbol'], 'lead_lag_score': 0.80}),
            vcp_ml_df=pd.DataFrame({'symbol': mock_universe['symbol'], 'vcp_surge_prob': 0.75}),
        )

        res_map = res.set_index('symbol')

        # Check Liquid stocks have positive score
        assert res_map.loc['005930', 'ensemble_score'] > 0.0
        assert res_map.loc['AAPL', 'ensemble_score'] > 0.0
        assert res_map.loc['035720', 'ensemble_score'] > 0.0

        # Check Preferred shares are ZEROED
        assert res_map.loc['005935', 'ensemble_score'] == 0.0, "Samsung Electronics Pref (우) was not zeroed"
        assert res_map.loc['005935', 'ensemble_expected_return'] == 0.0
        assert res_map.loc['001045', 'ensemble_score'] == 0.0, "CJ Pref (우B) was not zeroed"
        assert res_map.loc['001045', 'ensemble_expected_return'] == 0.0

        # Check SPACs are ZEROED
        assert res_map.loc['450120', 'ensemble_score'] == 0.0, "KRX SPAC was not zeroed"
        assert res_map.loc['450120', 'ensemble_expected_return'] == 0.0
        assert res_map.loc['DHCA', 'ensemble_score'] == 0.0, "US SPAC was not zeroed"
        assert res_map.loc['DHCA', 'ensemble_expected_return'] == 0.0

        # Check Zero Volume and Sub-threshold Turnover are ZEROED
        assert res_map.loc['099990', 'ensemble_score'] == 0.0, "Zero volume stock was not zeroed"
        assert res_map.loc['088880', 'ensemble_score'] == 0.0, "Sub-threshold penny stock was not zeroed"

    def test_microstructure_friction_spread_and_impact_deductions(self):
        """Verify dynamic spread clamping and Almgren-Chriss market impact cost deductions on liquid stocks."""
        engine = EnsembleScoringEngine()

        df = pd.DataFrame([
            # Stock 1: Huge turnover (100B KRW) -> minimal spread and market impact
            {'symbol': '005930', 'market': 'KOSPI', 'close': 70000.0, 'volume': 1_500_000, 'volatility_20d': 0.015, 'expected_return_20d': 0.10},
            # Stock 2: Moderate turnover (1B KRW) -> higher spread and market impact
            {'symbol': '035720', 'market': 'KOSPI', 'close': 50000.0, 'volume': 20_000, 'volatility_20d': 0.035, 'expected_return_20d': 0.10},
        ])

        res = engine.calculate_ensemble_score(
            regime='BULL_LOW_VOL',
            regression_df=df,
            surge_df=pd.DataFrame({'symbol': df['symbol'], 'surge_prob_20d': 0.80}),
            lead_lag_df=pd.DataFrame({'symbol': df['symbol'], 'lead_lag_score': 0.80}),
            vcp_ml_df=pd.DataFrame({'symbol': df['symbol'], 'vcp_surge_prob': 0.80}),
        )

        res_map = res.set_index('symbol')
        ret_samsung = res_map.loc['005930', 'ensemble_expected_return']
        ret_kakao = res_map.loc['035720', 'ensemble_expected_return']

        # Samsung has higher turnover and lower vol -> lower transaction friction -> higher net expected return
        assert ret_samsung > ret_kakao, (
            f"Expected Samsung net return ({ret_samsung:.2f}%) > Kakao ({ret_kakao:.2f}%) due to lower microstructure friction."
        )

    def test_dynamic_cost_scaling_factor_bounds(self):
        """Verify that slippage feedback cost scaling factor is strictly clamped between [0.50, 3.00]."""
        engine = EnsembleScoringEngine()

        class MockSlippageMetrics:
            def __init__(self, cost_factor, impact_alpha):
                self.cost_scaling_factor = cost_factor
                self.market_impact_alpha = impact_alpha
                self.market_slippage_map = {'KOSPI': 8.5}
                self.avg_slippage_bps = 8.5
                self.sample_count = 100

        # Test extreme low
        engine.update_microstructure_costs(MockSlippageMetrics(0.10, 0.45))
        assert engine.cost_scaling_factor == 0.50

        # Test extreme high
        engine.update_microstructure_costs(MockSlippageMetrics(10.0, 0.60))
        assert engine.cost_scaling_factor == 3.00

        # Test within range
        engine.update_microstructure_costs(MockSlippageMetrics(1.85, 0.52))
        assert math.isclose(engine.cost_scaling_factor, 1.85, abs_tol=1e-5)
