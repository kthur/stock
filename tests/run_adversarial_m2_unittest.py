import sys
import os
import math
import numpy as np
import pandas as pd

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.config import TradingConfig

passed = 0
failed = 0

def record_test(name, success, msg=""):
    global passed, failed
    if success:
        passed += 1
        print(f"[PASS] {name}", flush=True)
    else:
        failed += 1
        print(f"[FAIL] {name} - {msg}", flush=True)

def run_all_stress_tests():
    print("==================================================================", flush=True)
    print("STARTING EMPIRICAL ADVERSARIAL STRESS TEST SUITE (M2 GEN 2)", flush=True)
    print("==================================================================", flush=True)

    # -------------------------------------------------------------
    # Category 1: Rapid Regime Switching & EMA Smoothing
    # -------------------------------------------------------------
    print("\n--- [Category 1] Rapid Regime Switching & EMA Smoothing ---", flush=True)
    engine = EnsembleScoringEngine(alpha_smoothing=0.2)
    sharpes = {'regression': 0.5, 'surge': 0.8, 'vcp_ml': 0.6, 'stat_arb': 0.2, 'rim_valuation': 0.4}

    # Step 1.1: BULL_LOW_VOL
    w_bull_1 = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL')
    record_test("T1.1 Initial BULL_LOW_VOL dynamic weights generated", np.isclose(sum(w_bull_1.values()), 1.0))

    # Step 1.2: Switch to BEAR_HIGH_VOL -> eff_alpha must be 1.0 (no residual bull weights)
    ref_engine_bear = EnsembleScoringEngine(alpha_smoothing=0.2)
    target_bear = ref_engine_bear.compute_dynamic_weights_from_sharpe(sharpes, regime='BEAR_HIGH_VOL')
    w_bear = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='BEAR_HIGH_VOL')

    diffs_bear = [abs(w_bear[k] - target_bear[k]) for k in target_bear]
    max_diff_bear = max(diffs_bear)
    record_test(
        "T1.2 Regime shift (BULL -> BEAR) enforces eff_alpha=1.0 instant realignment",
        max_diff_bear < 1e-6,
        f"max difference = {max_diff_bear:.8f}"
    )

    # Step 1.3: Switch to SIDEWAYS_LOW_VOL -> eff_alpha must be 1.0
    ref_engine_side = EnsembleScoringEngine(alpha_smoothing=0.2)
    target_side = ref_engine_side.compute_dynamic_weights_from_sharpe(sharpes, regime='SIDEWAYS_LOW_VOL')
    w_side = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='SIDEWAYS_LOW_VOL')

    diffs_side = [abs(w_side[k] - target_side[k]) for k in target_side]
    max_diff_side = max(diffs_side)
    record_test(
        "T1.3 Regime shift (BEAR -> SIDEWAYS) enforces eff_alpha=1.0 instant realignment",
        max_diff_side < 1e-6,
        f"max difference = {max_diff_side:.8f}"
    )

    # Step 1.4: Steady State in SIDEWAYS_LOW_VOL -> eff_alpha = 0.2 EMA applied
    sharpes_t2 = {'regression': 0.1, 'surge': 0.1, 'vcp_ml': 0.1}
    target_side_t2 = ref_engine_side.compute_dynamic_weights_from_sharpe(sharpes_t2, regime='SIDEWAYS_LOW_VOL')
    w_side_t2 = engine.compute_dynamic_weights_from_sharpe(sharpes_t2, regime='SIDEWAYS_LOW_VOL')

    expected_raw = {k: 0.2 * target_side_t2[k] + 0.8 * w_side[k] for k in target_side_t2}
    tot_exp = sum(expected_raw.values())
    expected_smoothed = {k: v / tot_exp for k, v in expected_raw.items()}
    max_diff_ema = max([abs(w_side_t2[k] - expected_smoothed[k]) for k in expected_smoothed])
    record_test(
        "T1.4 Steady regime applies eff_alpha=0.2 EMA smoothing correctly",
        max_diff_ema < 1e-5,
        f"max difference = {max_diff_ema:.8f}"
    )

    # Step 1.5: 100 Rapid Oscillating Regime Switches
    oscillations_ok = True
    regimes_list = ['BULL_LOW_VOL', 'BEAR_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'BULL_HIGH_VOL', 'BEAR_LOW_VOL', 'SIDEWAYS_HIGH_VOL']
    for i in range(100):
        reg = regimes_list[i % len(regimes_list)]
        test_sharpes = {'regression': math.sin(i), 'surge': math.cos(i), 'vcp_ml': 0.5}
        w_osc = engine.compute_dynamic_weights_from_sharpe(test_sharpes, regime=reg)
        if not np.isclose(sum(w_osc.values()), 1.0, atol=1e-5) or any(v < 0 for v in w_osc.values()):
            oscillations_ok = False
            break
    record_test("T1.5 100 Rapid oscillating regime switches maintain sum=1.0 and non-negative weights", oscillations_ok)

    # -------------------------------------------------------------
    # Category 2: Extreme Strategy Sharpe Inputs & Pruning
    # -------------------------------------------------------------
    print("\n--- [Category 2] Extreme Strategy Sharpe Inputs & Pruning ---", flush=True)
    gamma = 1.0
    max_ratio = 5.0
    sharpe_clip = float(np.log(np.sqrt(max_ratio)) / gamma)
    record_test(
        f"T2.1 Theoretical Sharpe clipping bound is exactly ln(sqrt(5)) = {sharpe_clip:.4f}",
        math.isclose(sharpe_clip, 0.8047189562, abs_tol=1e-6)
    )

    # Test Sharpe +5.0 vs clipped +0.8047
    w_sh5 = engine.compute_dynamic_weights_from_sharpe({'regression': 5.0, 'stat_arb': 0.0}, regime='SIDEWAYS_LOW_VOL')
    w_sh_clip = engine.compute_dynamic_weights_from_sharpe({'regression': sharpe_clip, 'stat_arb': 0.0}, regime='SIDEWAYS_LOW_VOL')
    record_test(
        "T2.2 Extreme positive Sharpe (+5.0) strictly clipped at +0.804719 multiplier",
        math.isclose(w_sh5['regression'], w_sh_clip['regression'], rel_tol=1e-4, abs_tol=1e-5)
    )

    # Test Sharpe -4.0 and -0.51 pruned to 0.0
    w_pruned = engine.compute_dynamic_weights_from_sharpe(
        {'regression': 1.0, 'surge': -0.51, 'vcp_ml': -4.0, 'lead_lag': -0.500001, 'rim_valuation': -0.49},
        regime='SIDEWAYS_LOW_VOL'
    )
    prune_ok = (
        w_pruned['surge'] == 0.0 and
        w_pruned['vcp_ml'] == 0.0 and
        w_pruned['lead_lag'] == 0.0 and
        w_pruned['rim_valuation'] > 0.0 and
        np.isclose(sum(w_pruned.values()), 1.0)
    )
    record_test(
        "T2.3 Strategies with Sharpe < -0.50 strictly pruned to 0.0 weight",
        prune_ok,
        f"surge={w_pruned['surge']}, vcp_ml={w_pruned['vcp_ml']}, lead_lag={w_pruned['lead_lag']}, rim={w_pruned['rim_valuation']}"
    )

    # Test All Strategies Pruned Fallback
    base_w_bear = engine.get_base_weights('BEAR_LOW_VOL')
    all_neg_sharpes = {strat: -3.5 for strat in base_w_bear}
    w_all_neg = engine.compute_dynamic_weights_from_sharpe(all_neg_sharpes, regime='BEAR_LOW_VOL')
    all_neg_ok = all(math.isclose(w_all_neg[k], base_w_bear[k], abs_tol=1e-5) for k in base_w_bear)
    record_test(
        "T2.4 Universal underperformance (all Sharpe < -0.50) safely defaults to regime base weights",
        all_neg_ok
    )

    # Test NaN and +/- Inf robustness
    w_corrupt = engine.compute_dynamic_weights_from_sharpe(
        {'regression': np.nan, 'surge': float('inf'), 'vcp_ml': float('-inf'), 'stat_arb': 0.5},
        regime='BULL_LOW_VOL'
    )
    corrupt_ok = (
        np.isclose(sum(w_corrupt.values()), 1.0) and
        w_corrupt['vcp_ml'] == 0.0 and
        not np.isnan(w_corrupt['regression']) and
        not np.isinf(w_corrupt['surge'])
    )
    record_test("T2.5 NaN and +/-Inf Sharpe inputs handled cleanly without throwing NaN or crashing", corrupt_ok)

    # -------------------------------------------------------------
    # Category 3: Extreme Ratio Power Damping (> 20.0)
    # -------------------------------------------------------------
    print("\n--- [Category 3] Extreme Ratio Power Damping ---", flush=True)
    w_extreme_ratio = engine.compute_dynamic_weights_from_sharpe(
        rolling_sharpes={'surge': 5.0, 'vcp_ml': 5.0, 'regression': -0.49},
        regime='BULL_HIGH_VOL'
    )
    pos_w = [v for v in w_extreme_ratio.values() if v > 0.0]
    max_w, min_w = max(pos_w), min(pos_w)
    ratio = max_w / min_w
    record_test(
        f"T3.1 Positive weight ratio strictly bounded <= 20.0 (observed ratio: {ratio:.4f})",
        ratio <= 20.0001
    )

    # Test Monotonic Ordering under Power Damping
    w_ordering = engine.compute_dynamic_weights_from_sharpe(
        {'surge': 2.0, 'vcp_ml': 1.5, 'event_driven': 1.0, 'stat_arb': 0.5, 'regression': 0.0},
        regime='BULL_LOW_VOL'
    )
    order_ok = (w_ordering['surge'] >= w_ordering['vcp_ml'] >= w_ordering['event_driven'] >= w_ordering['stat_arb'])
    record_test("T3.2 Monotonic ranking order preserved under power damping", order_ok)

    # -------------------------------------------------------------
    # Category 4: Microstructure Friction & Penny/Illiquid Stocks
    # -------------------------------------------------------------
    print("\n--- [Category 4] Microstructure Friction & Penny/Illiquid Stocks ---", flush=True)
    mock_universe = pd.DataFrame([
        {'symbol': '005930', 'name': '삼성전자', 'market': 'KOSPI', 'close': 75000.0, 'volume': 15_000_000, 'volatility_20d': 0.018},
        {'symbol': 'AAPL', 'name': 'Apple Inc', 'market': 'SP500', 'close': 180.0, 'volume': 50_000_000, 'volatility_20d': 0.015},
        {'symbol': '005935', 'name': '삼성전자우', 'market': 'KOSPI', 'close': 60000.0, 'volume': 500_000, 'volatility_20d': 0.019},
        {'symbol': '001045', 'name': 'CJ우B', 'market': 'KOSPI', 'close': 25000.0, 'volume': 100_000, 'volatility_20d': 0.022},
        {'symbol': '450120', 'name': '미래에셋비전스팩1호', 'market': 'KOSDAQ', 'close': 2000.0, 'volume': 50_000, 'volatility_20d': 0.010},
        {'symbol': 'DHCA', 'name': 'DHC Acquisition Corp SPAC', 'market': 'NASDAQ', 'close': 10.2, 'volume': 10_000, 'volatility_20d': 0.005},
        {'symbol': '099990', 'name': '초저유동주', 'market': 'KOSDAQ', 'close': 5000.0, 'volume': 0, 'volatility_20d': 0.020},
        {'symbol': '088880', 'name': '동전한계기업', 'market': 'KOSDAQ', 'close': 50.0, 'volume': 1_000, 'volatility_20d': 0.080},
        {'symbol': '035720', 'name': '카카오', 'market': 'KOSPI', 'close': 50000.0, 'volume': 1_000_000, 'volatility_20d': 0.025},
    ])

    reg_df = mock_universe[['symbol', 'market', 'close', 'volume', 'name', 'volatility_20d']].copy()
    reg_df['expected_return_20d'] = 0.20

    res = engine.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=reg_df,
        surge_df=pd.DataFrame({'symbol': mock_universe['symbol'], 'surge_prob_20d': 0.85}),
        lead_lag_df=pd.DataFrame({'symbol': mock_universe['symbol'], 'lead_lag_score': 0.80}),
        vcp_ml_df=pd.DataFrame({'symbol': mock_universe['symbol'], 'vcp_surge_prob': 0.75}),
    )
    res_map = res.set_index('symbol')

    # T4.1 Preferred Stock Gate
    pref_ok = (
        res_map.loc['005935', 'ensemble_score'] == 0.0 and res_map.loc['005935', 'ensemble_expected_return'] == 0.0 and
        res_map.loc['001045', 'ensemble_score'] == 0.0 and res_map.loc['001045', 'ensemble_expected_return'] == 0.0
    )
    record_test("T4.1 Preferred stocks ('우', '우B') completely zeroed out by Liquidity Gate", pref_ok)

    # T4.2 SPAC Gate
    spac_ok = (
        res_map.loc['450120', 'ensemble_score'] == 0.0 and res_map.loc['450120', 'ensemble_expected_return'] == 0.0 and
        res_map.loc['DHCA', 'ensemble_score'] == 0.0 and res_map.loc['DHCA', 'ensemble_expected_return'] == 0.0
    )
    record_test("T4.2 SPAC stocks (KRX '스팩' & US 'SPAC') completely zeroed out by Liquidity Gate", spac_ok)

    # T4.3 Illiquid & Penny Gate
    illiquid_ok = (
        res_map.loc['099990', 'ensemble_score'] == 0.0 and res_map.loc['099990', 'ensemble_expected_return'] == 0.0 and
        res_map.loc['088880', 'ensemble_score'] == 0.0 and res_map.loc['088880', 'ensemble_expected_return'] == 0.0
    )
    record_test("T4.3 Zero volume (099990) and sub-threshold penny stock (088880) zeroed out", illiquid_ok)

    # T4.4 Microstructure Friction Differentiation
    friction_df = pd.DataFrame([
        {'symbol': '005930', 'market': 'KOSPI', 'close': 70000.0, 'volume': 1_500_000, 'volatility_20d': 0.015, 'expected_return_20d': 0.10},
        {'symbol': '035720', 'market': 'KOSPI', 'close': 50000.0, 'volume': 20_000, 'volatility_20d': 0.035, 'expected_return_20d': 0.10},
    ])
    res_f = engine.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=friction_df,
        surge_df=pd.DataFrame({'symbol': friction_df['symbol'], 'surge_prob_20d': 0.80}),
        lead_lag_df=pd.DataFrame({'symbol': friction_df['symbol'], 'lead_lag_score': 0.80}),
        vcp_ml_df=pd.DataFrame({'symbol': friction_df['symbol'], 'vcp_surge_prob': 0.80}),
    )
    res_f_map = res_f.set_index('symbol')
    ret_samsung = res_f_map.loc['005930', 'ensemble_expected_return']
    ret_kakao = res_f_map.loc['035720', 'ensemble_expected_return']
    record_test(
        f"T4.4 High turnover Samsung (ret={ret_samsung:.2f}%) yields higher net return than low turnover Kakao (ret={ret_kakao:.2f}%)",
        ret_samsung > ret_kakao
    )

    # T4.5 Cost Scaling Factor Bounds
    class MockSlippageMetrics:
        def __init__(self, cost_factor, impact_alpha):
            self.cost_scaling_factor = cost_factor
            self.market_impact_alpha = impact_alpha
            self.market_slippage_map = {'KOSPI': 8.5}
            self.avg_slippage_bps = 8.5
            self.sample_count = 100

    engine.update_microstructure_costs(MockSlippageMetrics(0.10, 0.45))
    c_low = engine.cost_scaling_factor
    engine.update_microstructure_costs(MockSlippageMetrics(10.0, 0.60))
    c_high = engine.cost_scaling_factor
    engine.update_microstructure_costs(MockSlippageMetrics(1.85, 0.52))
    c_mid = engine.cost_scaling_factor
    record_test(
        f"T4.5 Slippage feedback cost scaling factor clamped in [0.50, 3.00] (min={c_low}, max={c_high}, mid={c_mid})",
        (c_low == 0.50 and c_high == 3.00 and math.isclose(c_mid, 1.85))
    )

    print("==================================================================", flush=True)
    print(f"ADVERSARIAL STRESS TEST SUMMARY: {passed} PASSED, {failed} FAILED", flush=True)
    print("==================================================================", flush=True)
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(run_all_stress_tests())
