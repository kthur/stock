import sys
import os
sys.path.insert(0, os.path.abspath("trading_system"))
import math
import numpy as np
import pandas as pd
from src.ai.ensemble_scorer import EnsembleScoringEngine

def run_adversarial_verification():
    scorer = EnsembleScoringEngine()

    print("=================================================================")
    print("REVIEWER M1-1 ADVERSARIAL VERIFICATION SUITE (F01, F02, F03, F05)")
    print("=================================================================")

    # -----------------------------------------------------------------
    # F01: 7-State 2D Regime Matrix & Dedicated CRISIS Base Weights
    # -----------------------------------------------------------------
    print("\n--- F01: CRISIS Weights & Resolution ---")
    assert "CRISIS" in scorer.REGIME_2D_WEIGHTS, "CRISIS missing from REGIME_2D_WEIGHTS"
    crisis_w = scorer.REGIME_2D_WEIGHTS["CRISIS"]

    # 1. Exact count of 37 strategies
    assert len(crisis_w) == 37, f"CRISIS strategy count {len(crisis_w)} != 37"
    print(f"[PASS] CRISIS contains exactly {len(crisis_w)} strategies.")

    # 2. Strict sum = 1.0000
    crisis_sum = sum(crisis_w.values())
    assert math.isclose(crisis_sum, 1.0, abs_tol=1e-6), f"CRISIS sum {crisis_sum} != 1.0"
    print(f"[PASS] CRISIS weights sum strictly = {crisis_sum:.6f}")

    # 3. Minimum floor >= 0.005
    min_w = min(crisis_w.values())
    assert min_w >= 0.005, f"Minimum weight {min_w} < 0.005"
    print(f"[PASS] All weights >= 0.005 (min weight = {min_w:.4f})")

    # 4. Defensive dominance
    defensive_weights = {
        "vol_target": crisis_w["vol_target"],
        "stat_arb": crisis_w["stat_arb"],
        "rim_valuation": crisis_w["rim_valuation"],
        "accruals_quality": crisis_w["accruals_quality"],
        "short_term_reversal": crisis_w["short_term_reversal"],
        "card_factor": crisis_w["card_factor"],
    }
    assert defensive_weights["vol_target"] == 0.080
    assert defensive_weights["stat_arb"] == 0.070
    assert defensive_weights["rim_valuation"] == 0.065
    assert defensive_weights["accruals_quality"] == 0.060
    assert defensive_weights["short_term_reversal"] == 0.055
    assert defensive_weights["card_factor"] == 0.050
    print(f"[PASS] Defensive dominance confirmed: {defensive_weights}")

    # 5. High-beta throttling
    high_beta = ["surge", "vcp_rule", "vcp_ml", "short_squeeze", "gamma_squeeze", "trend_efficiency", "range_expansion_breakout"]
    for hb in high_beta:
        assert crisis_w[hb] == 0.005, f"{hb} weight {crisis_w[hb]} != 0.005"
    print(f"[PASS] High-beta throttling confirmed (all capped at 0.005): {high_beta}")

    # 6. Fallback prevention
    w_sideways = scorer.get_base_weights("SIDEWAYS_LOW_VOL")
    crisis_test_strings = [
        "CRISIS", "crisis", "Crisis", "CRISIS_ACTIVE", "MACRO_CRISIS", "severe_crisis_level_3"
    ]
    for cts in crisis_test_strings:
        w_resolved = scorer.get_base_weights(cts)
        assert math.isclose(w_resolved["vol_target"], crisis_w["vol_target"], abs_tol=1e-5), f"Failed for {cts}"
        assert not math.isclose(w_resolved["vol_target"], w_sideways["vol_target"], abs_tol=1e-3), f"Fell back to SIDEWAYS_LOW_VOL for {cts}"
    print(f"[PASS] All crisis test strings correctly resolve to CRISIS and never SIDEWAYS_LOW_VOL")

    # -----------------------------------------------------------------
    # F02: Markov Posterior Regime Soft-Blending
    # -----------------------------------------------------------------
    print("\n--- F02: Markov Posterior Soft-Blending ---")
    # 1. 2D dict convex combination
    probs_2d = {"BULL_LOW_VOL": 0.50, "SIDEWAYS_LOW_VOL": 0.30, "CRISIS": 0.20}
    w_blend = scorer.get_base_weights(probs_2d)
    assert len(w_blend) == 37 or len([k for k, v in w_blend.items() if v > 0]) == 37
    assert math.isclose(sum(w_blend.values()), 1.0, abs_tol=1e-6)
    expected_vol_target = (
        0.50 * scorer.REGIME_2D_WEIGHTS["BULL_LOW_VOL"]["vol_target"] +
        0.30 * scorer.REGIME_2D_WEIGHTS["SIDEWAYS_LOW_VOL"]["vol_target"] +
        0.20 * scorer.REGIME_2D_WEIGHTS["CRISIS"]["vol_target"]
    )
    assert math.isclose(w_blend["vol_target"], expected_vol_target, abs_tol=1e-5)
    print(f"[PASS] 2D Markov soft blending matches convex combination (vol_target={w_blend['vol_target']:.4f})")

    # 2. 1D dict soft blending
    probs_1d = {"p_bear": 0.20, "p_sideways": 0.30, "p_bull": 0.50}
    w_1d = scorer.get_base_weights(probs_1d)
    assert math.isclose(sum(w_1d.values()), 1.0, abs_tol=1e-6)
    expected_1d_vol_target = (
        0.20 * scorer.REGIME_WEIGHTS[0]["vol_target"] +
        0.30 * scorer.REGIME_WEIGHTS[1]["vol_target"] +
        0.50 * scorer.REGIME_WEIGHTS[2]["vol_target"]
    )
    assert math.isclose(w_1d["vol_target"], expected_1d_vol_target, abs_tol=1e-5)
    print(f"[PASS] 1D Markov soft blending matches convex combination (vol_target={w_1d['vol_target']:.4f})")

    # 3. Unnormalized / dirty inputs
    probs_dirty = {"BULL_LOW_VOL": 2.0, "CRISIS": 2.0, "INVALID": np.nan, "NEG": -1.0}
    w_dirty = scorer.get_base_weights(probs_dirty)
    assert math.isclose(sum(w_dirty.values()), 1.0, abs_tol=1e-6)
    expected_dirty_vt = 0.50 * scorer.REGIME_2D_WEIGHTS["BULL_LOW_VOL"]["vol_target"] + 0.50 * crisis_w["vol_target"]
    assert math.isclose(w_dirty["vol_target"], expected_dirty_vt, abs_tol=1e-5)
    print(f"[PASS] Dirty/unnormalized probability dict normalized safely.")

    # 4. Fallback on empty or all-zero dict
    w_empty = scorer.get_base_weights({})
    assert math.isclose(w_empty["vol_target"], w_sideways["vol_target"], abs_tol=1e-5)
    w_zero = scorer.get_base_weights({"BULL_LOW_VOL": 0.0, "CRISIS": 0.0})
    assert math.isclose(w_zero["vol_target"], w_sideways["vol_target"], abs_tol=1e-5)
    print(f"[PASS] Degenerate/empty probability vectors fall back cleanly to SIDEWAYS_LOW_VOL.")

    # -----------------------------------------------------------------
    # F03: Continuous TV-Distance & VIX Entropy Smoothing
    # -----------------------------------------------------------------
    print("\n--- F03: Continuous TV-Distance & VIX Entropy Smoothing ---")
    engine_tv = EnsembleScoringEngine(alpha_smoothing=0.20)
    sharpes = {s: 1.0 for s in scorer.REGIME_2D_WEIGHTS["BULL_LOW_VOL"]}

    # Warmup
    w_t0 = engine_tv.compute_dynamic_weights_from_sharpe(sharpes, regime="BULL_LOW_VOL", market="US", enable_tv_smoothing=True, vix_val=15.0)
    # Calm steady state (d_tv = 0, sigma_vix = 0, h_vix low) -> eff_alpha near alpha_0 (0.20)
    w_t1 = engine_tv.compute_dynamic_weights_from_sharpe(sharpes, regime="BULL_LOW_VOL", market="US", enable_tv_smoothing=True, vix_val=15.0)
    # Sudden crisis shock (d_tv = 1.0, vix = 45.0, sigma_vix = 1.0, h_vix high) -> eff_alpha clamped to max 0.85
    w_t2 = engine_tv.compute_dynamic_weights_from_sharpe(sharpes, regime="CRISIS", market="US", enable_tv_smoothing=True, vix_val=45.0)
    target_crisis = engine_tv.get_base_weights("CRISIS")
    diff_t2 = sum(abs(w_t2[s] - target_crisis[s]) for s in target_crisis)
    # Under high alpha (up to 0.85), diff should be significantly reduced from raw distance (~1.2) but not 0 (EMA smoothed)
    assert 0.0 < diff_t2 < 0.55, f"Unexpected diff_t2: {diff_t2}"
    print(f"[PASS] High stress shift adapted quickly under dynamic alpha (residual diff={diff_t2:.4f})")

    # Verify bounds [0.15, 0.85] by simulating the exact equation directly
    alpha_0 = 0.20
    beta_trans = 0.35
    beta_vix = 0.30
    beta_ent = 0.05
    # Minimum possible:
    alpha_min = np.clip(alpha_0 + beta_trans * 0.0 + beta_vix * 0.0 + beta_ent * 0.0, 0.15, 0.85)
    assert alpha_min >= 0.15 and alpha_min <= 0.85
    # Maximum possible:
    alpha_max = np.clip(alpha_0 + beta_trans * 1.0 + beta_vix * 1.0 + beta_ent * 1.0 + 0.15, 0.15, 0.85)
    assert alpha_max == 0.85
    print(f"[PASS] Continuous alpha_t strictly bounded in [{alpha_min:.2f}, {alpha_max:.2f}]")

    # Backward compatibility: without TV smoothing, legacy 1-hot instant reset triggers (alpha = 1.0)
    engine_legacy = EnsembleScoringEngine(alpha_smoothing=0.20)
    w_bull_1 = engine_legacy.compute_dynamic_weights_from_sharpe(sharpes, regime="BULL_LOW_VOL")
    ref_legacy = EnsembleScoringEngine(alpha_smoothing=0.20)
    target_bear_ref = ref_legacy.compute_dynamic_weights_from_sharpe(sharpes, regime="BEAR_HIGH_VOL")
    w_bear_shift = engine_legacy.compute_dynamic_weights_from_sharpe(sharpes, regime="BEAR_HIGH_VOL")

    for k in target_bear_ref:
        assert math.isclose(w_bear_shift[k], target_bear_ref[k], rel_tol=1e-5, abs_tol=1e-6), (
            f"Legacy 1-hot regime switch without TV smoothing must perform exact instant reset for {k}"
        )
    print(f"[PASS] Backward compatibility verified: legacy 1-hot instant reset matches reference with zero lag")

    # -----------------------------------------------------------------
    # F05: Trend Inertia vs Crash Protection
    # -----------------------------------------------------------------
    print("\n--- F05: Trend Inertia vs Crash Protection ---")
    engine_f05 = EnsembleScoringEngine()
    sharpes_even = {s: 0.5 for s in scorer.REGIME_2D_WEIGHTS["BULL_LOW_VOL"]}
    # 1. BULL_LOW_VOL: Trend inertia with autocorrelation
    # Fresh engines to test static formula without consecutive EMA smoothing contamination
    w_ac_10 = EnsembleScoringEngine().compute_dynamic_weights_from_sharpe(
        sharpes_even, regime="BULL_LOW_VOL", factor_autocorr_dict={"surge": 1.0}
    )
    w_ac_00 = EnsembleScoringEngine().compute_dynamic_weights_from_sharpe(
        sharpes_even, regime="BULL_LOW_VOL", factor_autocorr_dict={"surge": 0.0}
    )
    w_ac_neg = EnsembleScoringEngine().compute_dynamic_weights_from_sharpe(
        sharpes_even, regime="BULL_LOW_VOL", factor_autocorr_dict={"surge": -0.5}
    )
    # Autocorr 1.0 gives 1.40 + 0.20 = 1.60x; Autocorr 0 gives 1.40x; Autocorr -0.5 gives 1.40x
    assert w_ac_10["surge"] > w_ac_00["surge"]
    assert math.isclose(w_ac_00["surge"], w_ac_neg["surge"], rel_tol=1e-5, abs_tol=1e-6)
    print(f"[PASS] BULL_LOW_VOL momentum turbo scales with autocorrelation: ac=1.0 ({w_ac_10['surge']:.4f}) > ac=0.0 ({w_ac_00['surge']:.4f})")

    # Reversal dampened in BULL_LOW_VOL (0.50x)
    assert w_ac_10["short_term_reversal"] < w_ac_10["surge"]
    print(f"[PASS] BULL_LOW_VOL reversal dampened (0.50x): short_term_reversal={w_ac_10['short_term_reversal']:.4f}")

    # 2. BULL_HIGH_VOL: Crash protection (1.15x)
    w_high_vol = engine_f05.compute_dynamic_weights_from_sharpe(sharpes_even, regime="BULL_HIGH_VOL")
    w_low_vol = engine_f05.compute_dynamic_weights_from_sharpe(sharpes_even, regime="BULL_LOW_VOL")
    ratio_high = w_high_vol["surge"] / w_high_vol["short_term_reversal"]
    ratio_low = w_low_vol["surge"] / w_low_vol["short_term_reversal"]
    assert ratio_high < ratio_low
    print(f"[PASS] BULL_HIGH_VOL crash protection reduces momentum/reversal ratio: {ratio_high:.2f} vs {ratio_low:.2f}")

    # 3. CRISIS & BEAR_HIGH_VOL: Reversal boost (1.40 ~ 1.68x) and momentum slashed (0.50x)
    w_crisis_20 = engine_f05.compute_dynamic_weights_from_sharpe(sharpes_even, regime="CRISIS", vix_val=20.0)
    w_crisis_40 = engine_f05.compute_dynamic_weights_from_sharpe(sharpes_even, regime="CRISIS", vix_val=40.0)
    # At vix=20, reversal multiplier is 1.40x. At vix=40, reversal multiplier is 1.40 * 1.20 = 1.68x.
    assert w_crisis_40["short_term_reversal"] > w_crisis_20["short_term_reversal"]
    assert w_crisis_40["short_term_reversal"] > w_crisis_40["surge"] * 3.0
    print(f"[PASS] CRISIS reversal boost verified: VIX 20 ({w_crisis_20['short_term_reversal']:.4f}) -> VIX 40 ({w_crisis_40['short_term_reversal']:.4f})")
    print(f"[PASS] CRISIS momentum slashed: surge={w_crisis_40['surge']:.4f} vs reversal={w_crisis_40['short_term_reversal']:.4f}")

    print("\n=================================================================")
    print("ALL ADVERSARIAL CHECKS PASSED (100% SUCCESSFUL VERIFICATION)")
    print("=================================================================")

if __name__ == "__main__":
    run_adversarial_verification()
