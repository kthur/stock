"""
Adversarial Empirical Stress Test Suite: Milestone M1 Alpha & Simplex Enhancements.

Agent: Challenger M1-1 (Alpha & Simplex Challenger)
Roles: critic, specialist

Attack Vectors Covered:
1. Simplex normalization across ALL 2D regimes in `REGIME_2D_WEIGHTS` (both trees):
   - sum(weights.values()) == 1.000000 (tolerance < 1e-6 and < 1e-9)
   - strictly 37 canonical strategies per regime
   - individual strategy weights bounded in [0.0, 0.50]
   - individual strategy weights strictly > 0.0
2. Exact factor weight allocations:
   - trend_efficiency == 0.075 in BULL_LOW_VOL, 0.065 in BULL_HIGH_VOL
   - arm_factor == 0.050 in BULL_LOW_VOL, 0.045 in BULL_HIGH_VOL
   - range_expansion_breakout == 0.055 in BULL_LOW_VOL, 0.050 in BULL_HIGH_VOL
   - supply_chain_gnn == 0.035 in BULL_LOW_VOL, 0.025 in BULL_HIGH_VOL
   - cross_asset_spillover == 0.045 in BULL_LOW_VOL, 0.040 in BULL_HIGH_VOL
   - trimmed strategies: vcp_rule (0.025), lead_lag (0.030), overnight_gap_reversal (0.015)
3. Invariant Baseline Defense:
   - BEAR_LOW_VOL, BEAR_HIGH_VOL, CRISIS weights 100% identical to git HEAD baseline
4. Return Calibration & Grinold-Kahn Bridge:
   - Score 0.50 maps to exactly 10.0% (base 8.0%) with ZERO synthetic upward bias
   - Score 0.85 and 0.95 under BULL_LOW_VOL generate expected CAGR in [30.0%, 45.0%] range
   - Strict monotonicity, boundary clipping [-40.0, 40.0], shape invariance, pd.Series indexing
5. Dual-Tree Cryptographic Mirror Consistency:
   - 100% bit-for-bit behavior across `src/` and `trading_system/src/`
"""

import ast
import os
import sys
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.ensemble_scorer import (
    EnsembleScoringEngine as SrcEngine,
    calculate_realistic_annualized_cagr as src_calc_cagr,
    calc_realistic_annualized_cagr as src_calc_alias1,
    calculate_realistic_cagr as src_calc_alias2,
    calc_realistic_cagr as src_calc_alias3,
    calculate_annualized_cagr_v111 as src_calc_alias4,
    f494_realistic_annualized_cagr as src_calc_alias5,
)

from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine as MirrorEngine


CANONICAL_37_STRATEGIES = {
    'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
    'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation', 'event_driven',
    'mq_factor', 'iv_skew', 'order_flow', 'short_term_reversal', 'arm_factor',
    'card_factor', 'latr_factor', 'inst_foreign_sector', 'supply_chain', 'sentiment',
    'factor_neutralized', 'vol_target', 'microstructure', 'accruals_quality', 'short_squeeze',
    'valueup_catalyst', 'trend_efficiency', 'gamma_squeeze', 'insider_buying', 'darkpool',
    'earnings_tone_drift', 'cross_asset_spillover', 'supply_chain_gnn',
    'range_expansion_breakout', 'dual_correction', 'index_rebalance', 'overnight_gap_reversal'
}

REGIMES_2D = [
    'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
    'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
    'BULL_LOW_VOL', 'BULL_HIGH_VOL',
    'CRISIS'
]


# ==============================================================================
# 1. Simplex Normalization & Weight Boundedness Tests
# ==============================================================================

class TestSimplexNormalization:
    """Adversarially verify mathematical simplex invariants across all 2D regimes."""

    @pytest.mark.parametrize("regime", REGIMES_2D)
    def test_simplex_sum_src(self, regime):
        weights = SrcEngine.REGIME_2D_WEIGHTS[regime]
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-6, f"Simplex violation in {regime}: sum={total}"
        assert np.isclose(total, 1.0, atol=1e-9), f"Fine tolerance simplex violation: {total}"

    @pytest.mark.parametrize("regime", REGIMES_2D)
    def test_simplex_sum_mirror(self, regime):
        weights = MirrorEngine.REGIME_2D_WEIGHTS[regime]
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-6, f"Simplex violation in mirror {regime}: sum={total}"
        assert np.isclose(total, 1.0, atol=1e-9)

    @pytest.mark.parametrize("regime", REGIMES_2D)
    def test_strategy_count_and_keys(self, regime):
        weights = SrcEngine.REGIME_2D_WEIGHTS[regime]
        assert len(weights) == 37, f"Expected 37 strategies in {regime}, found {len(weights)}"
        keys = set(weights.keys())
        assert keys == CANONICAL_37_STRATEGIES, f"Strategy key mismatch in {regime}: {keys ^ CANONICAL_37_STRATEGIES}"

    @pytest.mark.parametrize("regime", REGIMES_2D)
    def test_weight_bounds(self, regime):
        weights = SrcEngine.REGIME_2D_WEIGHTS[regime]
        for strat, w in weights.items():
            assert isinstance(w, (float, int)), f"Weight for {strat} in {regime} is not numeric: {type(w)}"
            assert w >= 0.0, f"Negative weight for {strat} in {regime}: {w}"
            assert w <= 0.50, f"Weight exceeds 0.50 cap for {strat} in {regime}: {w}"
            assert w > 0.0, f"Strategy {strat} has non-positive weight in {regime}: {w}"


# ==============================================================================
# 2. Factor Weight Assertions (Specific M1 Alpha Elevations)
# ==============================================================================

class TestFactorWeightAllocations:
    """Verify exact values required by Milestone M1 specifications."""

    def test_bull_low_vol_allocations(self):
        w = SrcEngine.REGIME_2D_WEIGHTS['BULL_LOW_VOL']
        assert w['trend_efficiency'] == 0.075, f"trend_efficiency expected 0.075, got {w['trend_efficiency']}"
        assert w['arm_factor'] == 0.050, f"arm_factor expected 0.050, got {w['arm_factor']}"
        assert w['range_expansion_breakout'] == 0.055, f"range_expansion_breakout expected 0.055, got {w['range_expansion_breakout']}"
        assert w['supply_chain_gnn'] == 0.035, f"supply_chain_gnn expected 0.035, got {w['supply_chain_gnn']}"
        assert w['cross_asset_spillover'] == 0.045, f"cross_asset_spillover expected 0.045, got {w['cross_asset_spillover']}"
        # Trimmed checks
        assert w['vcp_rule'] == 0.025
        assert w['lead_lag'] == 0.030
        assert w['overnight_gap_reversal'] == 0.015
        assert w['stat_arb'] == 0.010
        assert w['regression'] == 0.020

    def test_bull_high_vol_allocations(self):
        w = SrcEngine.REGIME_2D_WEIGHTS['BULL_HIGH_VOL']
        assert w['trend_efficiency'] == 0.065, f"trend_efficiency expected 0.065, got {w['trend_efficiency']}"
        assert w['arm_factor'] == 0.045, f"arm_factor expected 0.045, got {w['arm_factor']}"
        assert w['range_expansion_breakout'] == 0.050, f"range_expansion_breakout expected 0.050, got {w['range_expansion_breakout']}"
        assert w['supply_chain_gnn'] == 0.025, f"supply_chain_gnn expected 0.025, got {w['supply_chain_gnn']}"
        assert w['cross_asset_spillover'] == 0.040, f"cross_asset_spillover expected 0.040, got {w['cross_asset_spillover']}"
        # Trimmed checks
        assert w['vcp_rule'] == 0.025
        assert w['lead_lag'] == 0.030
        assert w['overnight_gap_reversal'] == 0.015
        assert w['stat_arb'] == 0.015
        assert w['regression'] == 0.015

    def test_sideways_allocations(self):
        slv = SrcEngine.REGIME_2D_WEIGHTS['SIDEWAYS_LOW_VOL']
        shv = SrcEngine.REGIME_2D_WEIGHTS['SIDEWAYS_HIGH_VOL']
        assert slv['arm_factor'] == 0.035
        assert shv['arm_factor'] == 0.030
        assert slv['regression'] == 0.020
        assert shv['regression'] == 0.020
        assert slv['vcp_rule'] == 0.010
        assert shv['vcp_rule'] == 0.010


# ==============================================================================
# 3. Defensive Invariance: Bear and Crisis Weights Identical to Baseline
# ==============================================================================

class TestDefensiveInvariance:
    """Empirically assert Bear and Crisis regimes are 100% bit-identical to git HEAD baseline."""

    def test_bear_and_crisis_git_baseline_identity(self):
        # Retrieve git HEAD baseline file content with utf-8 encoding
        cmd = ["git", "show", "HEAD:src/ai/ensemble_scorer.py"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", check=True)
        baseline_code = res.stdout

        # Extract baseline REGIME_2D_WEIGHTS literal
        start_idx = baseline_code.find('REGIME_2D_WEIGHTS = {') + len('REGIME_2D_WEIGHTS = ')
        end_idx = baseline_code.find('\n    # 3D Macro Regime', start_idx)
        assert start_idx > len('REGIME_2D_WEIGHTS = ') and end_idx > start_idx, "Failed to locate REGIME_2D_WEIGHTS in HEAD"
        baseline_regimes = ast.literal_eval(baseline_code[start_idx:end_idx].strip())

        # Assert BEAR_LOW_VOL, BEAR_HIGH_VOL, and CRISIS are 100% identical in keys and values
        for def_regime in ['BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'CRISIS']:
            current_w = SrcEngine.REGIME_2D_WEIGHTS[def_regime]
            baseline_w = baseline_regimes[def_regime]
            assert current_w == baseline_w, f"Regime {def_regime} differs from git HEAD baseline!"

    def test_bear_and_crisis_git_diff_clean(self):
        diff_cmd = ["git", "diff", "HEAD", "src/ai/ensemble_scorer.py"]
        diff_res = subprocess.run(diff_cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", check=True)
        diff_text = diff_res.stdout

        # Assert no modified lines (starting with + or -) alter BEAR or CRISIS keys
        changed_lines = [
            line for line in diff_text.splitlines()
            if (line.startswith('+') or line.startswith('-')) and not line.startswith(('+++', '---'))
        ]
        assert not any('BEAR_LOW_VOL' in line for line in changed_lines), "BEAR_LOW_VOL modified in diff!"
        assert not any('BEAR_HIGH_VOL' in line for line in changed_lines), "BEAR_HIGH_VOL modified in diff!"
        assert not any('CRISIS' in line for line in changed_lines), "CRISIS key modified in diff!"

    def test_bear_and_crisis_exact_values(self):
        w_blv = SrcEngine.REGIME_2D_WEIGHTS['BEAR_LOW_VOL']
        w_bhv = SrcEngine.REGIME_2D_WEIGHTS['BEAR_HIGH_VOL']
        w_cri = SrcEngine.REGIME_2D_WEIGHTS['CRISIS']

        # Verify canonical defensive weights
        assert w_blv['regression'] == 0.05
        assert w_blv['rim_valuation'] == 0.05
        assert w_blv['stat_arb'] == 0.04
        assert w_blv['vol_target'] == 0.04
        assert w_blv['card_factor'] == 0.04

        assert w_bhv['stat_arb'] == 0.06
        assert w_bhv['short_term_reversal'] == 0.05
        assert w_bhv['vol_target'] == 0.05
        assert w_bhv['rim_valuation'] == 0.05

        assert w_cri['vol_target'] == 0.080
        assert w_cri['stat_arb'] == 0.070
        assert w_cri['rim_valuation'] == 0.065
        assert w_cri['accruals_quality'] == 0.060
        assert w_cri['factor_neutralized'] == 0.050
        assert w_cri['card_factor'] == 0.050
        assert w_cri['short_term_reversal'] == 0.055


# ==============================================================================
# 4. Realistic Annualized Return Calibration Tests
# ==============================================================================

class TestRealisticCAGRCalibration:
    """Stress-test calculate_realistic_annualized_cagr for exact neutrality and bull compounding."""

    def test_neutral_score_zero_upward_bias(self):
        calc = SrcEngine.calculate_realistic_annualized_cagr

        # Neutral score 0.50 in Bull Low Vol: base=0.08 -> reg_base = 0.08 * 1.25 = 10.0%
        cagr_blv = calc(0.50, regime='BULL_LOW_VOL', base_market_return=0.08)
        assert abs(cagr_blv - 10.0) < 1e-9, f"Neutral bias detected! Expected 10.0%, got {cagr_blv}"

        # Neutral score 0.50 in Bull High Vol
        cagr_bhv = calc(0.50, regime='BULL_HIGH_VOL', base_market_return=0.08)
        assert abs(cagr_bhv - 10.0) < 1e-9, f"Neutral bias detected in BHV! Expected 10.0%, got {cagr_bhv}"

        # Neutral score 0.50 in Sideways Low Vol: base=0.08 -> 8.0%
        cagr_slv = calc(0.50, regime='SIDEWAYS_LOW_VOL', base_market_return=0.08)
        assert abs(cagr_slv - 8.0) < 1e-9, f"Expected 8.0%, got {cagr_slv}"

        # Neutral score 0.50 in Bear Low Vol: 4.0%
        cagr_blv_bear = calc(0.50, regime='BEAR_LOW_VOL', base_market_return=0.08)
        assert abs(cagr_blv_bear - 4.0) < 1e-9

        # Neutral score 0.50 in Crisis: 2.0%
        cagr_crisis = calc(0.50, regime='CRISIS', base_market_return=0.08)
        assert abs(cagr_crisis - 2.0) < 1e-9

        # Return score 0.0 (with is_return=True)
        cagr_ret0 = calc(0.0, regime='BULL_LOW_VOL', base_market_return=0.08, is_return=True)
        assert abs(cagr_ret0 - 10.0) < 1e-9, f"Expected 10.0% for return=0.0, got {cagr_ret0}"

    def test_high_conviction_scores_bull_low_vol(self):
        calc = SrcEngine.calculate_realistic_annualized_cagr

        # With bull target_volatility = 0.16 (calibrated in UnifiedPortfolioAllocator)
        cagr_85_vol16 = calc(0.85, regime='BULL_LOW_VOL', target_volatility=0.16)
        cagr_95_vol16 = calc(0.95, regime='BULL_LOW_VOL', target_volatility=0.16)

        assert 30.0 <= cagr_85_vol16 <= 45.0, f"Score 0.85 (vol=0.16) got {cagr_85_vol16}%, outside [30.0%, 45.0%]"
        assert 30.0 <= cagr_95_vol16 <= 45.0, f"Score 0.95 (vol=0.16) got {cagr_95_vol16}%, outside [30.0%, 45.0%]"

        # With default target_volatility = 0.12
        cagr_95_vol12 = calc(0.95, regime='BULL_LOW_VOL', target_volatility=0.12)
        assert 30.0 <= cagr_95_vol12 <= 45.0, f"Score 0.95 (vol=0.12) got {cagr_95_vol12}%, outside [30.0%, 45.0%]"

    def test_monotonicity_across_probability_domain(self):
        calc = SrcEngine.calculate_realistic_annualized_cagr
        scores = np.linspace(0.0, 1.0, 201)

        # In BULL_LOW_VOL
        cagrs_blv = calc(scores, regime='BULL_LOW_VOL')
        # Check monotonicity on negative conviction [0.0, 0.50] and positive conviction [0.501, 1.0]
        neg_diffs = np.diff(cagrs_blv[scores <= 0.50])
        pos_diffs = np.diff(cagrs_blv[scores > 0.50])
        assert np.all(neg_diffs >= -1e-12), f"Non-monotonicity on negative side: min diff={np.min(neg_diffs)}"
        assert np.all(pos_diffs >= -1e-12), f"Non-monotonicity on positive side: min diff={np.min(pos_diffs)}"

    def test_extreme_input_resilience(self):
        calc = SrcEngine.calculate_realistic_annualized_cagr

        # Extreme positive score (e.g. 100.0) -> z clamped to 1.0 (same as score 1.0)
        res_high = calc(100.0, regime='BULL_LOW_VOL')
        res_1 = calc(1.0, regime='BULL_LOW_VOL')
        assert abs(res_high - res_1) < 1e-9, f"Expected score 100.0 to clamp to z=1.0: {res_high} vs {res_1}"

        # Under higher volatility (e.g. vol=0.16) or custom max_cagr (e.g. 25.0%), it clips cleanly to max_cagr
        res_clipped_vol = calc(1.0, regime='BULL_LOW_VOL', target_volatility=0.16, max_cagr=40.0)
        assert res_clipped_vol == 40.0, f"Expected 40.0% cap with vol=0.16, got {res_clipped_vol}"

        res_clipped_custom = calc(1.0, regime='BULL_LOW_VOL', max_cagr=25.0)
        assert res_clipped_custom == 25.0, f"Expected 25.0% cap, got {res_clipped_custom}"

        # Extreme negative score -> z clamped to -1.0 (same as score 0.0)
        res_low = calc(-100.0, regime='BULL_LOW_VOL')
        res_0 = calc(0.0, regime='BULL_LOW_VOL')
        assert abs(res_low - res_0) < 1e-9, f"Expected score -100.0 to clamp to z=-1.0: {res_low} vs {res_0}"

        res_floor_custom = calc(0.0, regime='BULL_LOW_VOL', min_cagr=-10.0)
        assert res_floor_custom == -10.0, f"Expected -10.0% floor, got {res_floor_custom}"

        # Series input preservation
        s = pd.Series([0.2, 0.5, 0.85, 0.95], index=['A', 'B', 'C', 'D'])
        res_series = calc(s, regime='BULL_LOW_VOL')
        assert isinstance(res_series, pd.Series)
        assert list(res_series.index) == ['A', 'B', 'C', 'D']

        # as_percentage=False check
        dec = calc(0.50, regime='BULL_LOW_VOL', as_percentage=False)
        assert abs(dec - 0.10) < 1e-9

    def test_class_and_module_aliases(self):
        engine = SrcEngine
        score = 0.85
        expected = engine.calculate_realistic_annualized_cagr(score, regime='BULL_LOW_VOL')

        assert engine.calc_realistic_annualized_cagr(score, regime='BULL_LOW_VOL') == expected
        assert engine.calculate_realistic_cagr(score, regime='BULL_LOW_VOL') == expected
        assert engine.calc_realistic_cagr(score, regime='BULL_LOW_VOL') == expected
        assert engine.calculate_annualized_cagr_v111(score, regime='BULL_LOW_VOL') == expected
        assert engine.f494_realistic_annualized_cagr(score, regime='BULL_LOW_VOL') == expected

        assert src_calc_cagr(score, regime='BULL_LOW_VOL') == expected
        assert src_calc_alias1(score, regime='BULL_LOW_VOL') == expected
        assert src_calc_alias2(score, regime='BULL_LOW_VOL') == expected
        assert src_calc_alias3(score, regime='BULL_LOW_VOL') == expected
        assert src_calc_alias4(score, regime='BULL_LOW_VOL') == expected
        assert src_calc_alias5(score, regime='BULL_LOW_VOL') == expected


# ==============================================================================
# 5. Dual-Tree Parity Symmetry Tests
# ==============================================================================

class TestDualTreeMirrorSymmetry:
    """Empirically test that src/ and trading_system/src/ produce bit-identical results."""

    @pytest.mark.parametrize("regime", REGIMES_2D)
    def test_exact_weights_match(self, regime):
        src_w = SrcEngine.REGIME_2D_WEIGHTS[regime]
        mirror_w = MirrorEngine.REGIME_2D_WEIGHTS[regime]
        assert src_w == mirror_w, f"Weight dictionary mismatch in {regime}"

    def test_cagr_calculation_match(self):
        scores = np.linspace(0.0, 1.0, 50)
        for reg in REGIMES_2D:
            cagr_src = SrcEngine.calculate_realistic_annualized_cagr(scores, regime=reg)
            cagr_mirror = MirrorEngine.calculate_realistic_annualized_cagr(scores, regime=reg)
            np.testing.assert_array_equal(cagr_src, cagr_mirror)
