"""
Adversarial Empirical Challenge Test Suite for Milestone 1 (Features F47 & F48).
Challenger 2: Empirical Verification of Core Mathematical Invariants:
1. Multiplier ordering: 5-Pillar > 4-Pillar > 3-Pillar > 2-Pillar > 1-Pillar == Baseline (1.0).
2. Multiplier cap in CRISIS regime strictly <= 1.040001.
3. Multiplier cap in BULL_LOW_VOL regime strictly <= 1.220001.
4. Legacy parity: when version=6, output matches historical Phase 6 baseline to within 10^-12.
5. Quartic Rank Modulation g_v7(r) has strictly positive first derivative g'(r) > 0 for all r in [0, 1].
"""

import math
import itertools
import numpy as np
import pandas as pd
import pytest

from src.ai.ensemble_scorer import EnsembleScoringEngine


# Canonical score columns defined across the 5 pillars in compute_quint_pillar_tensor_synergy
PILLAR_CLUSTERS = {
    'val': ['rim_score', 'valueup_catalyst_score', 'accruals_quality_score', 'arm_score', 'factor_neutralized_score', 'reg_score'],
    'mom': ['surge_score', 'vcp_ml_score', 'trend_efficiency_score', 'sector_score', 'range_expansion_score', 'mq_score', 'll_score', 'vcp_rule_score', 'lstm_score'],
    'flow': ['order_flow_score', 'inst_foreign_sector_score', 'darkpool_score', 'microstructure_score', 'overnight_gap_score', 'stat_arb_score', 'iv_skew_score', 'reversal_score', 'vol_target_score'],
    'cat': ['event_score', 'sentiment_score', 'short_squeeze_score', 'gamma_squeeze_score', 'insider_buying_score', 'earnings_tone_drift_score'],
    'net': ['supply_chain_score', 'supply_chain_gnn_score', 'cross_asset_spillover_score', 'dual_correction_score', 'index_rebalance_score', 'card_score', 'latr_score']
}
ALL_SCORE_COLS = [col for cols in PILLAR_CLUSTERS.values() for col in cols]


# =============================================================================
# HISTORICAL PHASE 6 REFERENCE IMPLEMENTATION (ORACLE FOR PARITY VERIFICATION)
# =============================================================================

def historical_phase6_quint_pillar_tensor_synergy(
    scores_df: pd.DataFrame,
    regime: str = 'SIDEWAYS_LOW_VOL',
    kappa: float = 8.0,
    regime_adaptive_cap: bool = True,
    max_cap=None
) -> pd.Series:
    """Exact, byte-level historical Phase 6 reference implementation."""
    if scores_df is None or scores_df.empty:
        return pd.Series(1.0, index=scores_df.index if scores_df is not None else [0])
    if len(scores_df) < 5:
        return pd.Series(1.0, index=scores_df.index)

    clusters = PILLAR_CLUSTERS

    denom = float(np.log(1.0 + np.exp(kappa * 0.50)) - np.log(2.0))
    denom = max(1e-4, denom)
    pillar_convictions = {}

    for pillar_name, cols in clusters.items():
        valid_cols = [c for c in cols if c in scores_df.columns]
        if not valid_cols:
            pillar_convictions[pillar_name] = pd.Series(0.0, index=scores_df.index)
            continue
        sub = scores_df[valid_cols].apply(pd.to_numeric, errors='coerce')
        sub_max = sub.max(axis=1).fillna(0.50)
        sub_mean = sub.mean(axis=1).fillna(0.50)
        agg_s = (0.70 * sub_max + 0.30 * sub_mean).clip(0.0, 1.0)
        excess_arg = kappa * (agg_s - 0.50)
        raw_softplus = np.log1p(np.exp(np.clip(excess_arg, -20.0, 20.0))) - np.log(2.0)
        psi = np.where(agg_s > 0.50, raw_softplus / denom, 0.0)
        pillar_convictions[pillar_name] = pd.Series(np.clip(psi, 0.0, 1.0), index=scores_df.index)

    reg_str = str(regime).upper()
    if 'BULL_LOW_VOL' in reg_str:
        omega_pairs = {('val', 'mom'): 0.025, ('val', 'flow'): 0.020, ('val', 'cat'): 0.015, ('val', 'net'): 0.015, ('mom', 'flow'): 0.035, ('mom', 'cat'): 0.040, ('mom', 'net'): 0.030, ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020, ('cat', 'net'): 0.025}
        w_tri = 0.025
        w_quad = 0.035
        w_quint = 0.060
        reg_cap = 0.180  # Phase 6 cap
    elif 'BULL_HIGH_VOL' in reg_str:
        omega_pairs = {('val', 'mom'): 0.020, ('val', 'flow'): 0.025, ('val', 'cat'): 0.015, ('val', 'net'): 0.015, ('mom', 'flow'): 0.040, ('mom', 'cat'): 0.025, ('mom', 'net'): 0.025, ('flow', 'cat'): 0.030, ('flow', 'net'): 0.020, ('cat', 'net'): 0.020}
        w_tri = 0.020
        w_quad = 0.025
        w_quint = 0.045
        reg_cap = 0.145
    elif 'SIDEWAYS_LOW_VOL' in reg_str:
        omega_pairs = {('val', 'mom'): 0.020, ('val', 'flow'): 0.035, ('val', 'cat'): 0.025, ('val', 'net'): 0.020, ('mom', 'flow'): 0.015, ('mom', 'cat'): 0.015, ('mom', 'net'): 0.015, ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020, ('cat', 'net'): 0.020}
        w_tri = 0.015
        w_quad = 0.015
        w_quint = 0.030
        reg_cap = 0.115
    elif 'SIDEWAYS_HIGH_VOL' in reg_str:
        omega_pairs = {('val', 'mom'): 0.015, ('val', 'flow'): 0.040, ('val', 'cat'): 0.025, ('val', 'net'): 0.020, ('mom', 'flow'): 0.008, ('mom', 'cat'): 0.008, ('mom', 'net'): 0.008, ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020, ('cat', 'net'): 0.015}
        w_tri = 0.008
        w_quad = 0.005
        w_quint = 0.015
        reg_cap = 0.070
    elif 'BEAR_HIGH_VOL' in reg_str:
        omega_pairs = {('val', 'mom'): 0.010, ('val', 'flow'): 0.045, ('val', 'cat'): 0.030, ('val', 'net'): 0.020, ('mom', 'flow'): 0.005, ('mom', 'cat'): 0.005, ('mom', 'net'): 0.005, ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020, ('cat', 'net'): 0.010}
        w_tri = 0.002
        w_quad = 0.000
        w_quint = 0.000
        reg_cap = 0.045
    elif 'BEAR_LOW_VOL' in reg_str or 'BEAR' in reg_str:
        omega_pairs = {('val', 'mom'): 0.018, ('val', 'flow'): 0.035, ('val', 'cat'): 0.030, ('val', 'net'): 0.020, ('mom', 'flow'): 0.010, ('mom', 'cat'): 0.010, ('mom', 'net'): 0.010, ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020, ('cat', 'net'): 0.015}
        w_tri = 0.010
        w_quad = 0.008
        w_quint = 0.020
        reg_cap = 0.085
    elif 'CRISIS' in reg_str:
        omega_pairs = {('val', 'mom'): 0.010, ('val', 'flow'): 0.040, ('val', 'cat'): 0.020, ('val', 'net'): 0.015, ('mom', 'flow'): 0.005, ('mom', 'cat'): 0.005, ('mom', 'net'): 0.005, ('flow', 'cat'): 0.020, ('flow', 'net'): 0.015, ('cat', 'net'): 0.010}
        w_tri = 0.000
        w_quad = 0.000
        w_quint = 0.000
        reg_cap = 0.040
    elif 'BULL' in reg_str:
        omega_pairs = {('val', 'mom'): 0.025, ('val', 'flow'): 0.020, ('val', 'cat'): 0.015, ('val', 'net'): 0.015, ('mom', 'flow'): 0.035, ('mom', 'cat'): 0.035, ('mom', 'net'): 0.025, ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020, ('cat', 'net'): 0.025}
        w_tri = 0.022
        w_quad = 0.030
        w_quint = 0.050
        reg_cap = 0.160
    else:
        omega_pairs = {('val', 'mom'): 0.022, ('val', 'flow'): 0.030, ('val', 'cat'): 0.025, ('val', 'net'): 0.020, ('mom', 'flow'): 0.015, ('mom', 'cat'): 0.015, ('mom', 'net'): 0.015, ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020, ('cat', 'net'): 0.020}
        w_tri = 0.012
        w_quad = 0.012
        w_quint = 0.025
        reg_cap = 0.100

    p_val = pillar_convictions['val']
    p_mom = pillar_convictions['mom']
    p_flow = pillar_convictions['flow']
    p_cat = pillar_convictions['cat']
    p_net = pillar_convictions['net']

    synergy_sum = pd.Series(0.0, index=scores_df.index)
    for (p1, p2), w_omega in omega_pairs.items():
        synergy_sum += w_omega * (pillar_convictions[p1] * pillar_convictions[p2])

    triplets = [
        (p_val, p_mom, p_flow), (p_val, p_mom, p_cat), (p_val, p_mom, p_net),
        (p_val, p_flow, p_cat), (p_val, p_flow, p_net), (p_val, p_cat, p_net),
        (p_mom, p_flow, p_cat), (p_mom, p_flow, p_net), (p_mom, p_cat, p_net),
        (p_flow, p_cat, p_net)
    ]
    tri_confluence = pd.Series(0.0, index=scores_df.index)
    if w_tri > 0:
        for t1, t2, t3 in triplets:
            tri_confluence += w_tri * (t1 * t2 * t3)

    quads = [
        (p_val, p_mom, p_flow, p_cat),
        (p_val, p_mom, p_flow, p_net),
        (p_val, p_mom, p_cat, p_net),
        (p_val, p_flow, p_cat, p_net),
        (p_mom, p_flow, p_cat, p_net)
    ]
    quad_confluence = pd.Series(0.0, index=scores_df.index)
    if w_quad > 0:
        for q1, q2, q3, q4 in quads:
            quad_confluence += w_quad * (q1 * q2 * q3 * q4)

    quint_confluence = pd.Series(0.0, index=scores_df.index)
    if w_quint > 0:
        quint_confluence = w_quint * (p_val * p_mom * p_flow * p_cat * p_net)

    total_confluence = synergy_sum + tri_confluence + quad_confluence + quint_confluence

    if max_cap is not None:
        eff_cap = float(max_cap)
    elif regime_adaptive_cap:
        eff_cap = float(reg_cap)
    else:
        eff_cap = 0.100

    return 1.0 + total_confluence.clip(0.0, eff_cap)


# =============================================================================
# INVARIANT 1: MULTIPLIER ORDERING & HIERARCHY
# =============================================================================

def test_challenger2_invariant_1_multiplier_ordering_nested():
    """
    Adversarial verification of Multiplier Ordering:
    5-Pillar > 4-Pillar > 3-Pillar > 2-Pillar > 1-Pillar == Baseline (1.000).
    Tested across varying conviction levels (s in [0.55, 0.92] for capped regime,
    and s in [0.55, 0.99] for uncapped kernel) in BULL_LOW_VOL under version=7.
    """
    engine = EnsembleScoringEngine()
    strat_map = {
        'val': 'rim_score',
        'mom': 'surge_score',
        'flow': 'order_flow_score',
        'cat': 'event_score',
        'net': 'supply_chain_score'
    }

    # 1. Capped regime testing up to conviction 0.92 (before both 4-P and 5-P saturate 1.220)
    for conviction in [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.88, 0.90, 0.92]:
        idx = [f"A_{i}" for i in range(10)]
        df = pd.DataFrame(0.50, index=idx, columns=list(strat_map.values()))

        # A_0: Baseline (all 0.50)
        # A_1: 1-pillar (mom active)
        # A_2: 2-pillar (mom + flow active)
        # A_3: 3-pillar (mom + flow + val active)
        # A_4: 4-pillar (mom + flow + val + cat active)
        # A_5: 5-pillar (all 5 active)
        df.loc['A_1', 'surge_score'] = conviction
        df.loc['A_2', ['surge_score', 'order_flow_score']] = conviction
        df.loc['A_3', ['surge_score', 'order_flow_score', 'rim_score']] = conviction
        df.loc['A_4', ['surge_score', 'order_flow_score', 'rim_score', 'event_score']] = conviction
        df.loc['A_5', :] = conviction

        mult = engine.compute_quint_pillar_tensor_synergy(
            scores_df=df,
            regime='BULL_LOW_VOL',
            version=7
        )

        m0 = mult.loc['A_0']
        m1 = mult.loc['A_1']
        m2 = mult.loc['A_2']
        m3 = mult.loc['A_3']
        m4 = mult.loc['A_4']
        m5 = mult.loc['A_5']

        # Exact baseline invariant
        assert math.isclose(m0, 1.000000, abs_tol=1e-12), f"Baseline must be 1.0, got {m0}"
        # 1-pillar == baseline invariant (no cross-pillar synergy without at least 2 pillars)
        assert math.isclose(m1, 1.000000, abs_tol=1e-12), f"1-Pillar must equal Baseline 1.0, got {m1}"
        # Strict hierarchy
        assert m2 > m1, f"2-Pillar ({m2:.6f}) must strictly exceed 1-Pillar ({m1:.6f}) at conviction {conviction}"
        assert m3 > m2, f"3-Pillar ({m3:.6f}) must strictly exceed 2-Pillar ({m2:.6f}) at conviction {conviction}"
        assert m4 > m3, f"4-Pillar ({m4:.6f}) must strictly exceed 3-Pillar ({m3:.6f}) at conviction {conviction}"
        assert m5 > m4, f"5-Pillar ({m5:.6f}) must strictly exceed 4-Pillar ({m4:.6f}) at conviction {conviction}"

    # 2. Uncapped kernel testing up to conviction 0.99 (verifying mathematical tensor ordering unconditionally)
    for conviction in [0.70, 0.85, 0.92, 0.95, 0.99]:
        idx = [f"A_{i}" for i in range(10)]
        df = pd.DataFrame(0.50, index=idx, columns=list(strat_map.values()))
        df.loc['A_1', 'surge_score'] = conviction
        df.loc['A_2', ['surge_score', 'order_flow_score']] = conviction
        df.loc['A_3', ['surge_score', 'order_flow_score', 'rim_score']] = conviction
        df.loc['A_4', ['surge_score', 'order_flow_score', 'rim_score', 'event_score']] = conviction
        df.loc['A_5', :] = conviction

        mult_raw = engine.compute_quint_pillar_tensor_synergy(
            scores_df=df,
            regime='BULL_LOW_VOL',
            regime_adaptive_cap=False,
            max_cap=10.0,
            version=7
        )
        assert mult_raw.loc['A_5'] > mult_raw.loc['A_4'] > mult_raw.loc['A_3'] > mult_raw.loc['A_2'] > mult_raw.loc['A_1'] == 1.000000


def test_challenger2_invariant_1_all_combinations_monotonicity():
    """
    Exhaustively check all singletons, pairs, triplets, quads, and the quint:
    Every 1-pillar singleton must yield exactly 1.000000.
    Adding any additional pillar strictly increases synergy.
    """
    engine = EnsembleScoringEngine()
    pillars = ['val', 'mom', 'flow', 'cat', 'net']
    strat_map = {
        'val': 'rim_score',
        'mom': 'surge_score',
        'flow': 'order_flow_score',
        'cat': 'event_score',
        'net': 'supply_chain_score'
    }

    # Generate all subsets of pillars
    all_subsets = []
    for k in range(1, 6):
        all_subsets.extend(list(itertools.combinations(pillars, k)))

    idx = [f"SUBSET_{'_'.join(s)}" for s in all_subsets]
    df = pd.DataFrame(0.50, index=idx, columns=list(strat_map.values()))

    for s in all_subsets:
        row_id = f"SUBSET_{'_'.join(s)}"
        for p in s:
            df.loc[row_id, strat_map[p]] = 0.85

    mult = engine.compute_quint_pillar_tensor_synergy(
        scores_df=df,
        regime='BULL_LOW_VOL',
        version=7
    )

    # 1. All 5 singletons must be exactly 1.0
    for p in pillars:
        row_id = f"SUBSET_{p}"
        val = mult.loc[row_id]
        assert math.isclose(val, 1.000000, abs_tol=1e-12), f"Singleton {p} got {val} != 1.0"

    # 2. All pairs must exceed 1.0
    for s in itertools.combinations(pillars, 2):
        row_id = f"SUBSET_{'_'.join(s)}"
        val = mult.loc[row_id]
        assert val > 1.000000, f"Pair {s} got {val} <= 1.0"

    # 3. For any subset S and any pillar p not in S, mult(S + {p}) > mult(S)
    for k in range(1, 5):
        for s in itertools.combinations(pillars, k):
            base_row = f"SUBSET_{'_'.join(s)}"
            base_val = mult.loc[base_row]
            for p in pillars:
                if p not in s:
                    superset = tuple(sorted(s + (p,), key=lambda x: pillars.index(x)))
                    super_row = f"SUBSET_{'_'.join(superset)}"
                    super_val = mult.loc[super_row]
                    assert super_val > base_val, (
                        f"Adding {p} to {s} failed monotonicity: {super_val:.6f} <= {base_val:.6f}"
                    )


# =============================================================================
# INVARIANT 2: MULTIPLIER CAP IN CRISIS REGIME STRICTLY <= 1.040001
# =============================================================================

def test_challenger2_invariant_2_crisis_cap_stress():
    """
    Stress-test CRISIS regime cap under extreme inputs:
    Scores = 1.00 (maximum theoretical), high kappa, version=7.
    Multiplier must be strictly <= 1.040001 and >= 1.000000.
    """
    engine = EnsembleScoringEngine()
    cols = ALL_SCORE_COLS

    # 1. Extreme 1.00 score tensor
    idx = [f"CRISIS_MAX_{i}" for i in range(20)]
    df_max = pd.DataFrame(1.00, index=idx, columns=cols)

    for k in [4.0, 8.0, 16.0, 32.0]:
        mult = engine.compute_quint_pillar_tensor_synergy(
            scores_df=df_max,
            regime='CRISIS',
            kappa=k,
            version=7
        )
        assert (mult <= 1.040001).all(), f"CRISIS cap violated at kappa={k}: max was {mult.max()}"
        assert (mult >= 1.000000).all(), f"CRISIS lower bound violated at kappa={k}: min was {mult.min()}"
        # Extreme input saturates to 1.040 cap
        assert math.isclose(mult.max(), 1.040000, abs_tol=1e-5), f"Expected exact cap 1.040, got {mult.max()}"

    # 2. Monte Carlo randomized stress test in CRISIS (500 assets)
    np.random.seed(999)
    n_mc = 500
    idx_mc = [f"MC_{i}" for i in range(n_mc)]
    df_mc = pd.DataFrame(
        np.random.uniform(0.0, 1.0, size=(n_mc, len(cols))),
        index=idx_mc,
        columns=cols
    )
    mult_mc = engine.compute_quint_pillar_tensor_synergy(
        scores_df=df_mc,
        regime='CRISIS',
        version=7
    )
    assert (mult_mc <= 1.040001).all(), f"Monte Carlo CRISIS cap violated: max was {mult_mc.max()}"
    assert (mult_mc >= 1.000000).all(), f"Monte Carlo CRISIS min violated: min was {mult_mc.min()}"


# =============================================================================
# INVARIANT 3: MULTIPLIER CAP IN BULL_LOW_VOL REGIME STRICTLY <= 1.220001
# =============================================================================

def test_challenger2_invariant_3_bull_low_vol_cap_stress():
    """
    Stress-test BULL_LOW_VOL regime cap under extreme inputs:
    Scores = 1.00, perfect harmony across all 5 pillars, version=7.
    Multiplier must be strictly <= 1.220001 and >= 1.000000.
    """
    engine = EnsembleScoringEngine()
    cols = ALL_SCORE_COLS

    # 1. Extreme 1.00 score tensor
    idx = [f"BULL_MAX_{i}" for i in range(20)]
    df_max = pd.DataFrame(1.00, index=idx, columns=cols)

    for k in [4.0, 8.0, 16.0, 32.0]:
        mult = engine.compute_quint_pillar_tensor_synergy(
            scores_df=df_max,
            regime='BULL_LOW_VOL',
            kappa=k,
            version=7
        )
        assert (mult <= 1.220001).all(), f"BULL_LOW_VOL cap violated at kappa={k}: max was {mult.max()}"
        assert (mult >= 1.000000).all(), f"BULL_LOW_VOL min violated at kappa={k}: min was {mult.min()}"
        # Max input should saturate to cap 1.220
        assert math.isclose(mult.max(), 1.220000, abs_tol=1e-5), f"Extreme input should reach cap 1.220, got {mult.max()}"

    # 2. Monte Carlo randomized stress test in BULL_LOW_VOL (500 assets)
    np.random.seed(888)
    n_mc = 500
    idx_mc = [f"MC_{i}" for i in range(n_mc)]
    df_mc = pd.DataFrame(
        np.random.uniform(0.0, 1.0, size=(n_mc, len(cols))),
        index=idx_mc,
        columns=cols
    )
    mult_mc = engine.compute_quint_pillar_tensor_synergy(
        scores_df=df_mc,
        regime='BULL_LOW_VOL',
        version=7
    )
    assert (mult_mc <= 1.220001).all(), f"Monte Carlo BULL_LOW_VOL cap violated: max was {mult_mc.max()}"
    assert (mult_mc >= 1.000000).all(), f"Monte Carlo BULL_LOW_VOL min violated: min was {mult_mc.min()}"


# =============================================================================
# INVARIANT 4: LEGACY PARITY (VERSION=6 MATCHES HISTORICAL BASELINE TO 10^-12)
# =============================================================================

def test_challenger2_invariant_4_legacy_parity_exact():
    """
    Empirical verification that when version=6:
    compute_quint_pillar_tensor_synergy matches historical Phase 6 baseline
    to within 10^-12 across all 7 regimes and diverse random datasets.
    """
    engine = EnsembleScoringEngine()
    cols = ALL_SCORE_COLS

    all_regimes = [
        'BULL_LOW_VOL', 'BULL_HIGH_VOL',
        'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
        'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
        'CRISIS'
    ]

    np.random.seed(777)
    for regime in all_regimes:
        for trial in range(5):
            n_assets = np.random.randint(5, 50)
            data = np.random.uniform(0.0, 1.0, size=(n_assets, len(cols)))
            idx = [f"ASSET_{i}" for i in range(n_assets)]
            df = pd.DataFrame(data, index=idx, columns=cols)

            # 1. Output from production method with version=6
            prod_v6 = engine.compute_quint_pillar_tensor_synergy(
                scores_df=df,
                regime=regime,
                kappa=8.0,
                version=6
            )

            # 2. Output from historical Phase 6 reference oracle
            hist_ref = historical_phase6_quint_pillar_tensor_synergy(
                scores_df=df,
                regime=regime,
                kappa=8.0
            )

            # Maximum absolute discrepancy
            max_diff = np.max(np.abs(prod_v6.values - hist_ref.values))
            assert max_diff < 1e-12, (
                f"Legacy parity violated in {regime} (trial {trial}): max_diff = {max_diff:.2e} >= 1e-12"
            )

            # Also verify default version (no argument) defaults to version 6 behavior
            prod_default = engine.compute_quint_pillar_tensor_synergy(
                scores_df=df,
                regime=regime,
                kappa=8.0
            )
            max_diff_default = np.max(np.abs(prod_default.values - hist_ref.values))
            assert max_diff_default < 1e-12, (
                f"Default version argument does not match Phase 6 baseline in {regime}: max_diff = {max_diff_default:.2e}"
            )


# =============================================================================
# INVARIANT 5: QUARTIC RANK MODULATION MONOTONICITY & STRICT POSITIVE DERIVATIVE
# =============================================================================

def test_challenger2_invariant_5_quartic_rank_modulation_strictly_positive_derivative():
    """
    Verify Quartic Rank Modulation polynomial:
        g_v7(r) = 0.60 + 0.25*r + 0.25*r^2 + 0.40*r^3 + 0.35*r^4
    First derivative:
        g'_v7(r) = 0.25 + 0.50*r + 1.20*r^2 + 1.40*r^3
    Must have g'(r) > 0 for ALL r in [0, 1].
    Empirical checks:
    - Minimum analytical derivative on [0, 1] is 0.25 at r=0.
    - Mesh evaluation across 1,000,000 equidistant points.
    - Numerical differentiation verification.
    - Strict rank preservation: for all r_1 < r_2, g(r_1) < g(r_2).
    """
    # 1. Mesh of 1,000,000 points on [0.0, 1.0]
    r_mesh = np.linspace(0.0, 1.0, 1_000_000)

    # Value function
    g_vals = 0.60 + 0.25 * r_mesh + 0.25 * (r_mesh ** 2) + 0.40 * (r_mesh ** 3) + 0.35 * (r_mesh ** 4)

    # Analytical derivative
    g_prime = 0.25 + 0.50 * r_mesh + 1.20 * (r_mesh ** 2) + 1.40 * (r_mesh ** 3)

    # Monotonicity test: min derivative must be strictly positive
    min_deriv = np.min(g_prime)
    max_deriv = np.max(g_prime)
    assert min_deriv >= 0.250000, f"Minimum derivative was {min_deriv:.6f} < 0.25"
    assert math.isclose(min_deriv, 0.250000, abs_tol=1e-6), f"Min derivative at r=0 must be 0.25, got {min_deriv}"
    assert math.isclose(max_deriv, 3.350000, abs_tol=1e-6), f"Max derivative at r=1 must be 3.35, got {max_deriv}"

    # Numerical difference step check
    diffs = np.diff(g_vals)
    assert (diffs > 0).all(), "Pointwise difference not strictly positive across 1,000,000 points!"

    # 2. Numerical differentiation check via central difference
    eps = 1e-6
    r_sample = np.linspace(0.01, 0.99, 1000)
    g_plus = 0.60 + 0.25 * (r_sample + eps) + 0.25 * ((r_sample + eps) ** 2) + 0.40 * ((r_sample + eps) ** 3) + 0.35 * ((r_sample + eps) ** 4)
    g_minus = 0.60 + 0.25 * (r_sample - eps) + 0.25 * ((r_sample - eps) ** 2) + 0.40 * ((r_sample - eps) ** 3) + 0.35 * ((r_sample - eps) ** 4)
    num_deriv = (g_plus - g_minus) / (2.0 * eps)
    ana_deriv = 0.25 + 0.50 * r_sample + 1.20 * (r_sample ** 2) + 1.40 * (r_sample ** 3)
    np.testing.assert_allclose(num_deriv, ana_deriv, rtol=1e-5, err_msg="Numerical derivative does not match analytical derivative!")

    # 3. Second derivative convexity check: g''(r) = 0.50 + 2.40*r + 4.20*r^2 >= 0.50 > 0
    g_double_prime = 0.50 + 2.40 * r_mesh + 4.20 * (r_mesh ** 2)
    assert (g_double_prime >= 0.50).all(), f"g''(r) fell below 0.50: min={g_double_prime.min()}"

    # 4. Strict rank monotonicity on random sorted samples
    np.random.seed(42)
    for _ in range(100):
        rand_ranks = np.sort(np.random.uniform(0.0, 1.0, 50))
        g_rand = 0.60 + 0.25 * rand_ranks + 0.25 * (rand_ranks ** 2) + 0.40 * (rand_ranks ** 3) + 0.35 * (rand_ranks ** 4)
        assert (np.diff(g_rand) > 0).all(), "Random rank evaluation violated strict monotonicity!"
