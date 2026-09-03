"""
Adversarial Empirical Stress Testing for Milestone 1 (F01, F02, F03, F05).
Exhaustively validates:
1. Extreme & Degenerate Regime Posterior Vectors (NaNs, Infs, Negatives, Sums != 1, 100-State).
2. Rapid 50-Step Oscillations under varying VIX (5.0 to 80.0) with Zero Memory Leaks.
3. Fallback Integrity (Strings like 'CRISIS', 'crisis', 'CRISIS_EVENT', 'CRISIS_SEVERE' -> CRISIS weights only).
4. F05 Boundary Stress (Extreme VIX & Autocorrelation conditions).
5. Empirical Performance Metrics (Latency, Normalization Drift, Max Weight Deltas).
"""

import time
import math
import pytest
import numpy as np

from src.ai.ensemble_scorer import EnsembleScoringEngine


# =========================================================================
# 1. EXTREME & DEGENERATE REGIME POSTERIOR VECTORS
# =========================================================================

DEGENERATE_POSTERIORS = [
    ({}, "empty_dict"),
    ({"BULL_LOW_VOL": 0.0, "BEAR_HIGH_VOL": 0.0, "CRISIS": 0.0}, "all_zeros"),
    ({"BULL_LOW_VOL": float('nan'), "CRISIS": float('nan')}, "all_nans"),
    ({"BULL_LOW_VOL": 0.5, "SIDEWAYS_LOW_VOL": float('nan'), "CRISIS": 0.5}, "mixed_nan_finite"),
    ({"BULL_LOW_VOL": float('inf'), "CRISIS": float('-inf')}, "all_infinities"),
    ({"BULL_LOW_VOL": 0.6, "CRISIS": float('inf')}, "mixed_inf_finite"),
    ({"BULL_LOW_VOL": -0.5, "BEAR_HIGH_VOL": -1.0, "CRISIS": -0.2}, "all_negative"),
    ({"BULL_LOW_VOL": -0.5, "CRISIS": 0.5}, "mixed_negative_positive"),
    ({"BULL_LOW_VOL": 50.0, "CRISIS": 150.0}, "sum_much_greater_than_1"),
    ({"BULL_LOW_VOL": 0.001, "CRISIS": 0.002}, "sum_much_less_than_1"),
    ({"BULL_LOW_VOL": 1e-15, "CRISIS": 1e-16}, "subnormal_sum_near_zero"),
    ({f"STATE_{i}_LOW_VOL": 0.01 for i in range(100)}, "100_state_low_vol"),
    ({f"ARBITRARY_NAME_{i}": 0.01 for i in range(100)}, "100_state_unknown_keys"),
    (
        {f"S_{i}": (float('nan') if i % 4 == 0 else (float('inf') if i % 4 == 1 else (-0.1 if i % 4 == 2 else 0.05))) for i in range(100)},
        "100_state_adversarial_mixture"
    ),
    (None, "none_input"),
    ("COMPLETELY_UNKNOWN_REGIME_XYZ", "unknown_string"),
    (99999, "unknown_int"),
    (3.14159, "float_input"),
]


@pytest.mark.parametrize("probs,label", DEGENERATE_POSTERIORS)
def test_adversarial_degenerate_regime_posteriors(probs, label):
    """Verify get_base_weights handles degenerate/extreme inputs without crashing, maintaining sum=1 and floor>=0.005."""
    scorer = EnsembleScoringEngine()
    
    # Must never crash on any input
    weights = scorer.get_base_weights(probs)
    assert isinstance(weights, dict), f"Expected dict output for {label}, got {type(weights)}"
    
    # Filter active positive weights
    active_weights = {k: v for k, v in weights.items() if v > 0}
    assert len(active_weights) == 37, f"Expected exactly 37 active strategies for {label}, got {len(active_weights)}"
    
    # Normalization check: sum w_i == 1.0000 +- 1e-5
    tot_weight = sum(active_weights.values())
    norm_drift = abs(tot_weight - 1.0)
    assert norm_drift <= 1e-5, f"Normalization drift exceeded 1e-5 for {label}: sum={tot_weight}, drift={norm_drift}"
    
    # Floor check: w_i >= 0.005 for all 37 active strategies (with float tolerance)
    for strat, w in active_weights.items():
        assert np.isfinite(w), f"Non-finite weight detected for {strat} in {label}: {w}"
        assert w >= 0.005 - 1e-6, f"Weight floor violation for {strat} in {label}: {w} < 0.005"


# =========================================================================
# 2. RAPID REGIME OSCILLATIONS (50 STEPS)
# =========================================================================

def test_adversarial_rapid_regime_oscillations_continuous():
    """Stress test 50-step high-frequency regime switching (BULL <-> BEAR <-> CRISIS) across VIX 5.0 to 80.0."""
    scorer = EnsembleScoringEngine(alpha_smoothing=0.20)
    market = "oscillation_test_market"
    
    regime_cycle = [
        ("BULL_LOW_VOL", {"BULL_LOW_VOL": 0.85, "CRISIS": 0.15}, 12.0),
        ("BEAR_HIGH_VOL", {"BEAR_HIGH_VOL": 0.70, "CRISIS": 0.30}, 45.0),
        ("CRISIS", {"CRISIS": 0.90, "BEAR_HIGH_VOL": 0.10}, 75.0),
    ]
    
    base_sharpes = {s: 0.8 for s in scorer.REGIME_2D_WEIGHTS["BULL_LOW_VOL"]}
    active_strats = list(scorer.REGIME_2D_WEIGHTS["BULL_LOW_VOL"].keys())
    prev_w = None
    
    max_weight_delta = 0.0
    max_norm_drift = 0.0
    weight_history = []
    
    for step in range(50):
        reg_label, reg_probs, base_vix = regime_cycle[step % 3]
        # Oscillate VIX dynamically between 5.0 and 80.0
        vix_val = float(np.clip(base_vix + 8.0 * np.sin(step * 0.7), 5.0, 80.0))
        
        # Perturb sharpes slightly per step to simulate live drift
        noisy_sharpes = {s: v + 0.1 * np.cos(step + i) for i, (s, v) in enumerate(base_sharpes.items())}
        
        weights = scorer.compute_dynamic_weights_from_sharpe(
            rolling_sharpes=noisy_sharpes,
            regime=reg_label,
            market=market,
            vix_val=vix_val,
            regime_probs=reg_probs,
            enable_tv_smoothing=True
        )
        
        # Check normalization
        sum_w = sum(weights.values())
        drift = abs(sum_w - 1.0)
        if drift > max_norm_drift:
            max_norm_drift = drift
        assert drift <= 1e-5, f"Step {step}: Normalization drift {drift} > 1e-5"
        
        # Check bounds for all active 37 strategies (ignoring standalone zero-weight strategies)
        for s in active_strats:
            w = weights.get(s, 0.0)
            assert np.isfinite(w), f"Step {step}: Non-finite weight for {s}: {w}"
            assert w >= 0.005 - 1e-6, f"Step {step}: Weight below floor for {s}: {w}"
            assert w <= 0.35, f"Step {step}: Weight exploded above 0.35 for {s}: {w}"
            
        # Check transition smooth delta
        if prev_w is not None:
            step_delta = max(abs(weights[s] - prev_w[s]) for s in active_strats)
            if step_delta > max_weight_delta:
                max_weight_delta = step_delta
            # Maximum single-step delta must be reasonably bounded by TV smoothing (alpha_t <= 0.85)
            assert step_delta < 0.15, f"Step {step}: Runaway weight delta {step_delta:.4f} >= 0.15"
            
        prev_w = dict(weights)
        weight_history.append(weights)
        
        # Check for memory leaks in _prev_regime_probs
        assert len(scorer._prev_regime_probs) == 1, "_prev_regime_probs grew across markets!"
        assert len(scorer._prev_regime_probs[market]) <= 4, f"_prev_regime_probs[{market}] leaked historical states!"
        assert len(scorer._prev_weights) == 1, "_prev_weights grew across markets!"

    # Verify smooth evolution: no runaway weights or NaN values across entire 50-step run
    assert max_norm_drift <= 1e-5
    assert max_weight_delta < 0.15


def test_adversarial_instance_isolation_weight_decay():
    """Adversarial stress test: Ensure repeated instantiations of EnsembleScoringEngine
    do not progressively decay base weights of strategies 32-37 (e.g. overnight_gap_reversal)
    below the 0.005 floor due to in-place mutation of class-level REGIME_2D_WEIGHTS."""
    for i in range(10):
        engine = EnsembleScoringEngine()
        w = engine.get_base_weights("BULL_LOW_VOL")
        og_weight = w.get("overnight_gap_reversal", 0.0)
        assert og_weight >= 0.005, (
            f"Instance {i+1}: overnight_gap_reversal decayed to {og_weight:.6f} (< 0.005 floor) "
            f"due to class-level REGIME_2D_WEIGHTS mutation in _load_tuned_regime_weights!"
        )


# =========================================================================
# 3. FALLBACK INTEGRITY FOR CRISIS STRINGS
# =========================================================================

CRISIS_STRING_VARIANTS = [
    "CRISIS",
    "crisis",
    "Crisis",
    "CRISIS_EVENT",
    "CRISIS_SEVERE",
    "CRISIS_ACTIVE",
    "MARKET_CRISIS",
    "crisis_shock",
    "SEVERE_CRISIS",
    "macro_crisis_tail",
]


@pytest.mark.parametrize("crisis_str", CRISIS_STRING_VARIANTS)
def test_adversarial_crisis_fallback_strict_resolution(crisis_str):
    """Verify all case/affix variants of CRISIS strictly resolve to CRISIS weights and NEVER to SIDEWAYS_LOW_VOL."""
    scorer = EnsembleScoringEngine()
    
    weights = scorer.get_base_weights(crisis_str)
    crisis_ref = scorer.REGIME_2D_WEIGHTS["CRISIS"]
    sideways_ref = scorer.REGIME_2D_WEIGHTS["SIDEWAYS_LOW_VOL"]
    
    # Verify exact match with CRISIS base weights
    for strat, ref_w in crisis_ref.items():
        assert pytest.approx(weights[strat], abs=1e-5) == ref_w, (
            f"{crisis_str} failed to resolve to CRISIS weight for {strat}: got {weights[strat]}, expected {ref_w}"
        )
        
    # Strictly verify it did NOT fall back to SIDEWAYS_LOW_VOL
    assert pytest.approx(weights["vol_target"], abs=1e-5) == 0.080, f"{crisis_str} vol_target must be 0.080, got {weights['vol_target']}"
    assert pytest.approx(weights["stat_arb"], abs=1e-5) == 0.070, f"{crisis_str} stat_arb must be 0.070, got {weights['stat_arb']}"
    assert pytest.approx(weights["rim_valuation"], abs=1e-5) == 0.065, f"{crisis_str} rim_valuation must be 0.065, got {weights['rim_valuation']}"
    assert pytest.approx(weights["surge"], abs=1e-5) == 0.005, f"{crisis_str} surge must be throttled to 0.005, got {weights['surge']}"
    assert not math.isclose(weights["vol_target"], sideways_ref["vol_target"], abs_tol=1e-4), f"{crisis_str} fell back to SIDEWAYS_LOW_VOL!"
    assert not math.isclose(weights["stat_arb"], sideways_ref["stat_arb"], abs_tol=1e-4), f"{crisis_str} fell back to SIDEWAYS_LOW_VOL!"


def test_adversarial_crisis_fallback_in_prob_dict():
    """Verify probabilistic dictionaries with CRISIS substrings strictly map to CRISIS weights."""
    scorer = EnsembleScoringEngine()
    
    dict_crisis = {"CRISIS_SEVERE": 0.70, "crisis_shock": 0.30}
    w_blended = scorer.get_base_weights(dict_crisis)
    crisis_ref = scorer.REGIME_2D_WEIGHTS["CRISIS"]
    
    # 0.70 * CRISIS + 0.30 * CRISIS == CRISIS
    for strat, ref_w in crisis_ref.items():
        assert pytest.approx(w_blended[strat], abs=1e-5) == ref_w


# =========================================================================
# 4. F05 BOUNDARY STRESS: EXTREME VIX & AUTOCORRELATION
# =========================================================================

def test_adversarial_f05_extreme_boundary_stress():
    """Stress test F05 under extreme out-of-bounds inputs: VIX=150.0, VIX=0.0, Autocorr=99.0 and -99.0."""
    scorer = EnsembleScoringEngine()
    sharpes = {s: 0.5 for s in scorer.REGIME_2D_WEIGHTS["CRISIS"]}
    
    # 1. Hyper-crisis: VIX = 150.0 (well above normal clipping range)
    w_hyper = scorer.compute_dynamic_weights_from_sharpe(
        rolling_sharpes=sharpes,
        regime="CRISIS",
        vix_val=150.0
    )
    assert pytest.approx(sum(w_hyper.values()), abs=1e-5) == 1.0
    assert all(np.isfinite(v) for v in w_hyper.values())
    # Reversal strategies must be boosted cleanly without overflow
    assert w_hyper["short_term_reversal"] > 0.04
    
    # 2. Sub-zero VIX anomaly: VIX = -10.0
    w_subzero = scorer.compute_dynamic_weights_from_sharpe(
        rolling_sharpes=sharpes,
        regime="BULL_LOW_VOL",
        vix_val=-10.0
    )
    assert pytest.approx(sum(w_subzero.values()), abs=1e-5) == 1.0
    assert all(np.isfinite(v) for v in w_subzero.values())
    
    # 3. Out-of-bounds autocorrelation: autocorr = 99.0 and -99.0
    w_autocorr_overflow = scorer.compute_dynamic_weights_from_sharpe(
        rolling_sharpes=sharpes,
        regime="BULL_LOW_VOL",
        factor_autocorr_dict={"surge": 99.0, "vcp_ml": -99.0}
    )
    assert pytest.approx(sum(w_autocorr_overflow.values()), abs=1e-5) == 1.0
    assert all(np.isfinite(v) for v in w_autocorr_overflow.values())
    # Clipped to 1.0, so turbo_mult should be 1.40 + 0.20 * 1.0 = 1.60
    assert w_autocorr_overflow["surge"] > w_autocorr_overflow["vcp_ml"]


# =========================================================================
# 5. EMPIRICAL PERFORMANCE & LATENCY BENCHMARK
# =========================================================================

def test_empirical_performance_benchmark():
    """Measure empirical latency, max weight delta, and normalization drift over 200 iterations."""
    scorer = EnsembleScoringEngine(alpha_smoothing=0.20)
    sharpes = {s: 0.6 for s in scorer.REGIME_2D_WEIGHTS["BULL_LOW_VOL"]}
    
    latencies_dyn = []
    latencies_base = []
    norm_drifts = []
    max_deltas = []
    
    regimes = ["BULL_LOW_VOL", "BEAR_HIGH_VOL", "CRISIS", "SIDEWAYS_HIGH_VOL"]
    prev_w = None
    
    for i in range(200):
        reg = regimes[i % len(regimes)]
        vix = 10.0 + (i % 60)
        
        # 1. Base weights Markov soft-blending benchmark
        t_b0 = time.perf_counter()
        _ = scorer.get_base_weights(reg)
        t_b1 = time.perf_counter()
        latencies_base.append((t_b1 - t_b0) * 1000.0)
        
        # 2. Dynamic weights full engine benchmark
        t0 = time.perf_counter()
        w = scorer.compute_dynamic_weights_from_sharpe(
            rolling_sharpes=sharpes,
            regime=reg,
            market="benchmark_mkt",
            vix_val=vix,
            enable_tv_smoothing=True
        )
        t1 = time.perf_counter()
        
        latencies_dyn.append((t1 - t0) * 1000.0)  # ms
        norm_drifts.append(abs(sum(w.values()) - 1.0))
        if prev_w is not None:
            max_deltas.append(max(abs(w[s] - prev_w[s]) for s in w))
        prev_w = w
        
    mean_base_lat = float(np.mean(latencies_base))
    mean_dyn_lat = float(np.mean(latencies_dyn))
    p95_dyn_lat = float(np.percentile(latencies_dyn, 95))
    p99_dyn_lat = float(np.percentile(latencies_dyn, 99))
    max_drift = float(np.max(norm_drifts))
    max_delta = float(np.max(max_deltas))
    
    print(f"\n--- Empirical Metrics Report ---")
    print(f"Iterations: {len(latencies_dyn)}")
    print(f"Base Weights Mean Latency: {mean_base_lat:.4f} ms")
    print(f"Dynamic Weights Mean Latency: {mean_dyn_lat:.4f} ms")
    print(f"Dynamic Weights P95 Latency: {p95_dyn_lat:.4f} ms")
    print(f"Dynamic Weights P99 Latency: {p99_dyn_lat:.4f} ms")
    print(f"Max Normalization Drift: {max_drift:.8e}")
    print(f"Max Weight Delta: {max_delta:.4f}")
    
    # Assert institutional SLAs
    assert mean_base_lat < 15.0, f"Base weights mean latency {mean_base_lat:.4f} ms exceeds 15.0 ms"
    assert mean_dyn_lat < 25.0, f"Dynamic weights mean latency {mean_dyn_lat:.4f} ms exceeds 25.0 ms"
    assert p99_dyn_lat < 60.0, f"Dynamic weights P99 latency {p99_dyn_lat:.4f} ms exceeds 60.0 ms"
    assert max_drift <= 1e-5, f"Max normalization drift {max_drift:.8e} exceeds 1e-5"
    assert max_delta < 0.15, f"Max weight delta {max_delta:.4f} exceeds 0.15 limit"


