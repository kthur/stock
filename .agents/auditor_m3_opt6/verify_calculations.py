import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from trading_system.scripts.benchmark_phase6_quant_performance import (
    Phase6QuantBenchmarkEngine,
    generate_markdown_report,
    QuantitativeMetrics,
    BENCHMARK_PROFILES,
    MARKET_DISPLAY_NAMES,
)

print("Starting quantitative benchmark forensic verification...")

# 1. Test profile values
expected_mkts = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
weights = {"SP500": 0.35, "NASDAQ": 0.25, "KOSPI": 0.20, "KOSDAQ": 0.10, "RUSSELL2000": 0.10}

for mode in ["baseline", "enhancement"]:
    print(f"\n--- Aggregate Check for {mode.upper()} ---")
    w_gross = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "gross_return_ann_pct") for m in weights)
    w_net = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "net_return_ann_pct") for m in weights)
    w_tot = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "total_return_ann_pct") for m in weights)
    w_sharpe = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "sharpe_ratio") for m in weights)
    w_rank_ic = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "spearman_rank_ic") for m in weights)
    w_p_ic = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "pearson_ic") for m in weights)
    w_mdd = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "max_drawdown_pct") for m in weights)
    w_turn = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "turnover_ann_pct") for m in weights)
    w_fric = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "friction_cost_bps") for m in weights)
    w_top_sp = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "top_decile_spread_pct") for m in weights)
    w_top_sh = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "top_decile_sharpe") for m in weights)
    w_slip = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "execution_slippage_bps") for m in weights)
    w_dark = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "darkpool_savings_bps") for m in weights)
    w_win = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "win_rate_pct") for m in weights)
    w_pf = sum(weights[m] * getattr(BENCHMARK_PROFILES[m][mode], "profit_factor") for m in weights)

    print(f"Weighted Gross: {w_gross:.2f}% | Net: {w_net:.2f}% | Tot: {w_tot:.2f}% | Sharpe: {w_sharpe:.2f}")
    print(f"Weighted Rank-IC: {w_rank_ic:.3f} | Pearson-IC: {w_p_ic:.3f} | MDD: {w_mdd:.2f}% (div*0.88={w_mdd*0.88:.2f}%)")
    print(f"Weighted Turnover: {w_turn:.1f}% | Friction: {w_fric:.1f} bps | Top Spread: {w_top_sp:.1f}% | Top Sharpe: {w_top_sh:.2f}")
    print(f"Weighted Slippage: {w_slip:.1f} bps | Dark Savings: {w_dark:.1f} bps | Win Rate: {w_win:.1f}% | PF: {w_pf:.2f}")

# 2. Test engine run
engine = Phase6QuantBenchmarkEngine(seed=42, num_days=252)
res = engine.run_benchmark()
b_agg = res["aggregate"]["baseline"]
e_agg = res["aggregate"]["enhancement"]

print("\n--- Verified Aggregate Outputs ---")
print(f"Baseline Gross: {b_agg.gross_return_ann_pct}%, Net: {b_agg.net_return_ann_pct}%, Sharpe: {b_agg.sharpe_ratio}")
print(f"Enhancement Gross: {e_agg.gross_return_ann_pct}%, Net: {e_agg.net_return_ann_pct}%, Sharpe: {e_agg.sharpe_ratio}")

# 3. Test Attribution Sums
# Attribution numbers from Table 3:
# F41: Net +1.75%, Sharpe +0.20, MDD -0.15%, Turnover -1.2%, Friction -1.0 bps
# F42: Net +1.30%, Sharpe +0.15, MDD -0.20%, Turnover -2.4%, Friction -1.4 bps
# F43: Net +1.35%, Sharpe +0.18, MDD -0.25%, Turnover -2.0%, Friction -1.5 bps
# F44: Net +1.10%, Sharpe +0.13, MDD -0.10%, Turnover -2.2%, Friction -2.1 bps
m1_net = 1.75 + 1.30
m1_sharpe = 0.20 + 0.15
m1_mdd = -0.15 + -0.20
m1_turn = -1.2 + -2.4
m1_fric = -1.0 + -1.4

m2_net = 1.35 + 1.10
m2_sharpe = 0.18 + 0.13
m2_mdd = -0.25 + -0.10
m2_turn = -2.0 + -2.2
m2_fric = -1.5 + -2.1

tot_net = m1_net + m2_net
tot_sharpe = m1_sharpe + m2_sharpe
tot_mdd = m1_mdd + m2_mdd
tot_turn = m1_turn + m2_turn
tot_fric = m1_fric + m2_fric

print("\n--- Attribution Arithmetic Verification ---")
print(f"M1 Subtotal: Net={m1_net:.2f}%p (exp: +3.05%), Sharpe={m1_sharpe:.2f} (exp: +0.35), MDD={m1_mdd:.2f}%p (exp: -0.35%), Turn={m1_turn:.1f}%p (exp: -3.6%), Fric={m1_fric:.1f} bps (exp: -2.4 bps)")
print(f"M2 Subtotal: Net={m2_net:.2f}%p (exp: +2.45%), Sharpe={m2_sharpe:.2f} (exp: +0.31), MDD={m2_mdd:.2f}%p (exp: -0.35%), Turn={m2_turn:.1f}%p (exp: -4.2%), Fric={m2_fric:.1f} bps (exp: -3.6 bps)")
print(f"Total Net: {tot_net:.2f}%p (exp: +5.50%), Sharpe={tot_sharpe:.2f} (exp: +0.66), MDD={tot_mdd:.2f}%p (exp: -0.70%), Turn={tot_turn:.1f}%p (exp: -7.8%), Fric={tot_fric:.1f} bps (exp: -6.0 bps)")

delta_net_actual = round(e_agg.net_return_ann_pct - b_agg.net_return_ann_pct, 2)
delta_sharpe_actual = round(e_agg.sharpe_ratio - b_agg.sharpe_ratio, 2)
delta_mdd_actual = round(e_agg.max_drawdown_pct - b_agg.max_drawdown_pct, 2)
delta_turn_actual = round(e_agg.turnover_ann_pct - b_agg.turnover_ann_pct, 1)
delta_fric_actual = round(e_agg.friction_cost_bps - b_agg.friction_cost_bps, 1)

assert round(tot_net, 2) == delta_net_actual, f"Net delta mismatch: {tot_net} vs {delta_net_actual}"
assert round(tot_sharpe, 2) == delta_sharpe_actual, f"Sharpe delta mismatch: {tot_sharpe} vs {delta_sharpe_actual}"
# For MDD, note baseline -3.30%, enhancement -2.60%, delta = +0.70%p improvement (or -0.70% drawdown reduction)
assert abs(abs(tot_mdd) - abs(delta_mdd_actual)) < 1e-6, f"MDD delta mismatch: {tot_mdd} vs {delta_mdd_actual}"
assert round(tot_turn, 1) == delta_turn_actual, f"Turnover delta mismatch: {tot_turn} vs {delta_turn_actual}"
assert round(tot_fric, 1) == delta_fric_actual, f"Friction delta mismatch: {tot_fric} vs {delta_fric_actual}"

print("\nALL MATHEMATICAL ATTRIBUTION SUMS AND AGGREGATE DELTAS MATCH EXACTLY!")
