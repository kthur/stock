import json
import re
from collections import defaultdict

with open('.agents/explorer_m3_2/test_collection_data.json') as f:
    data = json.load(f)

domains = {
    "Factor Neutralization & SLA Gate (|rho| < 0.15)": [
        "factor_neutralized", "factor_ortho", "factor_orthogonalization", "quad_factor"
    ],
    "2D Market Regime & Dynamic Ensemble Scorer": [
        "regime", "ensemble", "hpo_and_2d_ensemble", "isotonic_sharpe", "adversarial_regime", "milestone2_m2", "meta_and_hybrid"
    ],
    "Strategy Engines (Surge, VCP, Stat-Arb, Sector, RIM, etc.)": [
        "vcp", "stat_arb", "sector", "rim", "lead_lag", "order_book", "inst_foreign", "sentiment",
        "llm_sentiment", "new_5_strategies", "new_27_strategies", "new_strategies", "strategies_24_to_27",
        "microstructure", "lstm_predictor", "alt_data", "slippage_feedback"
    ],
    "Risk Management, Crisis Gating & Intraday Protection": [
        "risk_manager", "risk_enhancements", "portfolio_risk", "intraday_stop_loss", "trade_executor_kill_switch",
        "kis_safety_and_atr", "critical_bugs", "macro_stress", "macro_regime"
    ],
    "Portfolio Allocation, HRP & Execution OMS": [
        "portfolio_allocator", "hrp_optimizer", "drl_allocator", "allocation", "black_litterman",
        "kelly_sizing", "portfolio_optimizer_and_oms", "broker_reporting", "mock_trading"
    ],
    "Data Layer, Indicator Storage & Fetching": [
        "database", "database_concurrency", "indicator_storage", "indicators", "dart_corp_mapper",
        "data_validator", "fred_client", "macro", "tuning_and_retry", "technical_cache", "ring_buffer"
    ],
    "Pipeline Orchestration, System Architecture & E2E": [
        "e2e_consolidated", "system", "system_architecture", "dag_pipeline", "modular_pipeline",
        "orchestrator", "event_bus", "network_hardening", "realtime_monitor", "report_generator"
    ],
    "Milestone & Empirical Challenger Suites": [
        "m1_master_suite", "m1_empirical", "challenger_m1", "challenger_m4", "phase", "cpcv_stress",
        "screener_dash_challenger", "target_labeling_and_walkforward", "feature_normalization"
    ]
}

categorized = defaultdict(lambda: {"files": set(), "test_count": 0, "tests_dir_count": 0, "ts_tests_dir_count": 0})

all_files = {}
all_files.update(data['tests_files'])
all_files.update(data['ts_tests_files'])

for fpath, count in all_files.items():
    fname = fpath.split('/')[-1]
    matched = False
    for domain, patterns in domains.items():
        if any(p in fname for p in patterns):
            categorized[domain]["files"].add(fpath)
            categorized[domain]["test_count"] += count
            if fpath.startswith("tests/"):
                categorized[domain]["tests_dir_count"] += count
            else:
                categorized[domain]["ts_tests_dir_count"] += count
            matched = True
            break
    if not matched:
        categorized["Uncategorized / General"]["files"].add(fpath)
        categorized["Uncategorized / General"]["test_count"] += count
        if fpath.startswith("tests/"):
            categorized["Uncategorized / General"]["tests_dir_count"] += count
        else:
            categorized["Uncategorized / General"]["ts_tests_dir_count"] += count

print("=== DOMAIN BREAKDOWN ===")
total_accounted = 0
for domain, info in sorted(categorized.items(), key=lambda x: x[1]['test_count'], reverse=True):
    print(f"\n### {domain}")
    print(f"- Total Tests: {info['test_count']} (tests/: {info['tests_dir_count']}, trading_system/tests/: {info['ts_tests_dir_count']})")
    print(f"- File Count: {len(info['files'])}")
    for f in sorted(info['files']):
        print(f"  - {f}")
    total_accounted += info['test_count']

print(f"\nTotal Accounted Tests: {total_accounted} / {data['total_tests']}")

summary = {
    domain: {
        "test_count": info["test_count"],
        "tests_dir_count": info["tests_dir_count"],
        "ts_tests_dir_count": info["ts_tests_dir_count"],
        "file_count": len(info["files"]),
        "files": sorted(list(info["files"]))
    }
    for domain, info in categorized.items()
}

with open('.agents/explorer_m3_2/domain_breakdown.json', 'w') as f:
    json.dump(summary, f, indent=2)
print("Saved domain_breakdown.json")
