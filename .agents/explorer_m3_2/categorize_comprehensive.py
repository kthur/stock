import json
from collections import defaultdict

with open('.agents/explorer_m3_2/test_collection_data.json') as f:
    data = json.load(f)

# Domain mapping dictionary with explicit regex / string matching
def get_domain(fpath):
    fname = fpath.split('/')[-1]
    
    if any(k in fname for k in [
        'factor_neutralized', 'factor_ortho', 'factor_orthogonalization', 
        'quad_factor', 'correlation_suppression'
    ]):
        return "1. Factor Neutralization & SLA Gate (|rho| < 0.15)"
    
    if any(k in fname for k in [
        'regime', 'ensemble', 'hpo_and_2d_ensemble', 'isotonic_sharpe', 
        'adversarial_regime', 'milestone2_m2', 'meta_and_hybrid'
    ]):
        return "2. 2D Market Regime & Dynamic Ensemble Scorer"
        
    if any(k in fname for k in [
        'vcp', 'stat_arb', 'sector', 'rim', 'lead_lag', 'order_book', 'inst_foreign', 
        'sentiment', 'llm_sentiment', 'new_5_strategies', 'new_27_strategies', 
        'new_strategies', 'strategies_24_to_27', 'microstructure', 'lstm_predictor', 
        'alt_data', 'slippage_feedback', 'fast_cointegration', 'prediction_model'
    ]):
        return "3. Strategy Alpha Engines (31 Strategies) & Models"
        
    if any(k in fname for k in [
        'risk_manager', 'risk_enhancements', 'portfolio_risk', 'intraday_stop_loss', 
        'trade_executor_kill_switch', 'kis_safety_and_atr', 'critical_bugs', 
        'macro_stress', 'macro_regime'
    ]):
        return "4. Risk Management, Crisis Gating & Intraday Protection"
        
    if any(k in fname for k in [
        'portfolio_allocator', 'hrp_optimizer', 'drl_allocator', 'allocation', 
        'black_litterman', 'kelly_sizing', 'portfolio_optimizer_and_oms', 
        'broker_reporting', 'mock_trading'
    ]):
        return "5. Portfolio Optimization, HRP & Allocation"
        
    if any(k in fname for k in [
        'database', 'database_concurrency', 'indicator_storage', 'indicators', 
        'dart_corp_mapper', 'data_validator', 'fred_client', 'macro', 
        'tuning_and_retry', 'technical_cache', 'ring_buffer'
    ]):
        return "6. Data Storage (SQLite WAL), Indicators & Ingestion"
        
    if any(k in fname for k in [
        'e2e_consolidated', 'system.py', 'system_architecture', 'dag_pipeline', 
        'modular_pipeline', 'orchestrator', 'event_bus', 'network_hardening', 
        'realtime_monitor', 'report_generator', 'post_market_scoring', 
        'kst_and_coverage_reasoning', 'test_e2e.py'
    ]):
        return "7. Pipeline Orchestration, System Architecture & E2E"
        
    if any(k in fname for k in [
        'm1_master_suite', 'm1_empirical', 'challenger_m1', 'challenger_m4', 
        'phase', 'cpcv_stress', 'screener_dash_challenger', 
        'target_labeling_and_walkforward', 'feature_normalization', 
        'adversarial_fundamental', 'fundamental_prediction_adversarial',
        'm1_1_fixes', 'scenario_simulator', 'stacking_blender'
    ]):
        return "8. Milestone Verification & Challenger Stress Suites"
        
    if any(k in fname for k in [
        'telegram_bot', 'telegram_notifier', 'trading_agent'
    ]):
        return "9. Trading Agent Execution & Realtime Alerts"
        
    if any(k in fname for k in [
        'config', 'async_helper', 'backtest', 'enhancements', 
        'institutional_next_level', 'r3_coverage_and_universe', 
        'strategy_edge_cases', 'strategy_updates'
    ]):
        return "10. Core Infrastructure, Configuration & Backtesting"
        
    return "11. Miscellaneous / Unmapped"

all_files = {}
all_files.update(data['tests_files'])
all_files.update(data['ts_tests_files'])

domain_stats = defaultdict(lambda: {"total": 0, "tests_dir": 0, "ts_dir": 0, "files_tests": [], "files_ts": []})

for fpath, count in all_files.items():
    domain = get_domain(fpath)
    domain_stats[domain]["total"] += count
    if fpath.startswith("tests/"):
        domain_stats[domain]["tests_dir"] += count
        domain_stats[domain]["files_tests"].append((fpath, count))
    else:
        domain_stats[domain]["ts_dir"] += count
        domain_stats[domain]["files_ts"].append((fpath, count))

print("================================================================================")
print("              FULL PYTEST REGRESSION SUITE BREAKDOWN (1,600 TESTS)")
print("================================================================================")
print(f"Total Tests Collected: {data['total_tests']}")
print(f"Root tests/ Directory: {data['tests_count']} tests across {len(data['tests_files'])} files")
print(f"trading_system/tests/ Directory: {data['ts_tests_count']} tests across {len(data['ts_tests_files'])} files")
print("================================================================================\n")

for domain in sorted(domain_stats.keys()):
    stats = domain_stats[domain]
    print(f"### {domain}")
    print(f"Total: {stats['total']} tests | tests/: {stats['tests_dir']} tests | trading_system/tests/: {stats['ts_dir']} tests")
    print(f"Files ({len(stats['files_tests']) + len(stats['files_ts'])} total):")
    if stats['files_tests']:
        print("  [tests/]")
        for f, c in sorted(stats['files_tests']):
            print(f"    - {f} ({c} tests)")
    if stats['files_ts']:
        print("  [trading_system/tests/]")
        for f, c in sorted(stats['files_ts']):
            print(f"    - {f} ({c} tests)")
    print()

summary_dict = {
    domain: {
        "total": stats["total"],
        "tests_dir": stats["tests_dir"],
        "ts_dir": stats["ts_dir"],
        "file_count": len(stats["files_tests"]) + len(stats["files_ts"]),
        "files_tests": stats["files_tests"],
        "files_ts": stats["files_ts"]
    }
    for domain, stats in sorted(domain_stats.items())
}

with open('.agents/explorer_m3_2/comprehensive_domain_breakdown.json', 'w') as f:
    json.dump(summary_dict, f, indent=2)
print("Saved comprehensive_domain_breakdown.json")
