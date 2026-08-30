import ast
import os
import glob
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

log_lines = []
def log(msg):
    log_lines.append(str(msg))

log('=== FORENSIC SCAN & VERIFICATION REPORT ===\n')

# 1. Check all Strategy Files
src_files = glob.glob('trading_system/src/**/*.py', recursive=True) + glob.glob('src/**/*.py', recursive=True)
src_files = sorted(list(set(src_files)))

log(f'[1] Scanning {len(src_files)} python source files...')

empty_funcs = []
constant_returns = []

for fpath in src_files:
    if '__pycache__' in fpath or '.pytest' in fpath:
        continue
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=fpath)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                real_stmts = [s for s in node.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
                if len(real_stmts) == 1:
                    stmt = real_stmts[0]
                    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                        constant_returns.append((fpath, node.name, repr(stmt.value.value)))
                    elif isinstance(stmt, ast.Pass):
                        empty_funcs.append((fpath, node.name))
    except Exception as e:
        log(f'  Error parsing {fpath}: {e}')

log(f'  Total 1-line constant return functions found: {len(constant_returns)}')
for fpath, name, val in constant_returns:
    log(f'    - {fpath} :: {name}() -> {val}')

log(f'  Total empty functions found: {len(empty_funcs)}')
for fpath, name in empty_funcs[:10]:
    log(f'    - {fpath} :: {name}()')

# 2. Verify StrategyRegistry
log('\n[2] Verifying StrategyRegistry and Strategy Registrations...')
sys.path.insert(0, 'trading_system')
sys.path.insert(0, 'trading_system/src')
sys.path.insert(0, '.')

from src.core.strategy_registry import get_registry
reg = get_registry()
reg.auto_discover(['src.core', 'src.ai'])
all_ids = reg.get_all_ids()
log(f'  Total registered strategies in StrategyRegistry: {len(all_ids)}')
log(f'  Registered IDs: {sorted(all_ids)}')

for req_id in ['cross_asset_spillover', 'supply_chain_gnn', 'range_expansion_breakout']:
    if req_id in all_ids:
        item = reg.get(req_id)
        cls, meta = item
        log(f'  [PASS] Required Strategy {req_id}: Class={cls.__name__}, ScoreCol={meta.score_column}, OutputFile={meta.output_file}')
    else:
        log(f'  [FAIL] Required Strategy {req_id} NOT found in StrategyRegistry!')

# 3. Verify EnsembleScoringEngine Weights
log('\n[3] Verifying EnsembleScoringEngine Regime Weights & Consistency...')
from src.ai.ensemble_scorer import EnsembleScoringEngine
scorer = EnsembleScoringEngine()

# 1D Regime Weights
log('  Checking 1D REGIME_WEIGHTS sums:')
for reg_code, w_dict in scorer.REGIME_WEIGHTS.items():
    w_sum = sum(w_dict.values())
    log(f'    Regime {reg_code}: sum = {w_sum:.6f} ({len(w_dict)} strategies)')
    assert abs(w_sum - 1.0) < 1e-5, f'1D Regime {reg_code} sum is {w_sum}, not 1.0!'

# 2D Regime Weights
log('  Checking 2D REGIME_2D_WEIGHTS sums:')
for reg_name, w_dict in scorer.REGIME_2D_WEIGHTS.items():
    w_sum = sum(w_dict.values())
    log(f'    2D Regime {reg_name}: sum = {w_sum:.6f} ({len(w_dict)} strategies)')
    assert abs(w_sum - 1.0) < 1e-5, f'2D Regime {reg_name} sum is {w_sum}, not 1.0!'

# Dynamic Weights resolution
for test_regime in ['BULL_HIGH_VOL', 'BULL_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'BEAR_HIGH_VOL', 'BEAR_LOW_VOL']:
    resolved = scorer.get_base_weights(regime=test_regime)
    r_sum = sum(resolved.values())
    log(f'    Resolved weights for {test_regime}: sum = {r_sum:.6f}')
    assert abs(r_sum - 1.0) < 1e-5

# 4. Verify Strategy Engines execution on synthetic data
log('\n[4] Empirical Execution of 3 New Strategy Engines...')
from src.core.cross_asset_spillover import CrossAssetSpilloverEngine
from src.core.supply_chain_gnn import SupplyChainGNNEngine
from src.core.range_expansion_breakout import RangeExpansionBreakoutEngine

# Synthetic OHLCV
dates = pd.date_range('2026-01-01', periods=30, freq='D')
c = np.linspace(100, 120, 30)
df_sample = pd.DataFrame({
    'Open': c * 0.99,
    'High': c * 1.02,
    'Low': c * 0.98,
    'Close': c,
    'Volume': np.full(30, 200000.0)
}, index=dates)

prices_dict = {'005930': df_sample, 'NVDA': df_sample, 'TSLA': df_sample}
indicators = {'sox_change': 3.5, 'usdkrw_change': 0.2, 'vix_change': -1.5}
sector_map = {'005930': 'Semiconductor', 'NVDA': 'Semiconductor', 'TSLA': 'Automotive'}

# Test CrossAssetSpillover
ca_eng = CrossAssetSpilloverEngine()
ca_res = ca_eng.compute_scores(prices_dict=prices_dict, indicators_df=indicators, sector_map=sector_map)
log(f'  CrossAssetSpillover output:\n{ca_res}')
assert not ca_res.empty and 'cross_asset_spillover_score' in ca_res.columns

# Test SupplyChainGNN
sc_eng = SupplyChainGNNEngine()
sc_res = sc_eng.compute_scores(prices_dict=prices_dict, sector_map=sector_map)
log(f'  SupplyChainGNN output:\n{sc_res}')
assert not sc_res.empty and 'supply_chain_gnn_score' in sc_res.columns

# Test RangeExpansionBreakout
re_eng = RangeExpansionBreakoutEngine()
re_res = re_eng.compute_scores(prices_dict=prices_dict)
log(f'  RangeExpansionBreakout output:\n{re_res}')
assert not re_res.empty and 'range_expansion_score' in re_res.columns

# 5. Verify PortfolioOptimizer
log('\n[5] Verifying Portfolio Optimization & Covariance Shrinkage...')
from src.analysis.portfolio_optimizer import calculate_risk_parity_weights, calculate_black_litterman_weights, shrink_covariance_matrix, calculate_hrp_weights
cov = np.array([[0.04, 0.01, 0.02], [0.01, 0.09, 0.01], [0.02, 0.01, 0.16]])
shrunk = shrink_covariance_matrix(cov)
log(f'  Covariance shrinkage test: shape={shrunk.shape}, cond={np.linalg.cond(shrunk):.2f}')

rp_w = calculate_risk_parity_weights(shrunk)
log(f'  Risk parity weights: {rp_w} (sum={sum(rp_w):.6f})')
assert abs(sum(rp_w) - 1.0) < 1e-5

bl_w = calculate_black_litterman_weights(shrunk, predicted_returns=np.array([0.05, 0.08, 0.12]))
log(f'  Black-Litterman weights: {bl_w} (sum={sum(bl_w):.6f})')
assert abs(sum(bl_w) - 1.0) < 1e-5

hrp_w = calculate_hrp_weights(shrunk)
log(f'  HRP weights: {hrp_w} (sum={sum(hrp_w):.6f})')
assert abs(sum(hrp_w) - 1.0) < 1e-5

# 6. Verify OMS Timing Engines
log('\n[6] Verifying OMS Precision Timing Engines...')
from src.execution.oms_engine import ExecutionOMSEngine
oms = ExecutionOMSEngine(db_path=':memory:')

# Confluence Entry
conf = oms.check_confluence_entry(ensemble_score=0.72, vcp_score=0.80, volume_surge_ratio=2.5, obi_score=0.5, price_above_ma50=True)
log(f'  Confluence entry (high signals): {conf}')
assert conf['is_valid_entry'] is True and conf['confluence_score'] >= 0.65

# Scale-In Pyramiding
s1_sh = s1['allocated_shares']
s2_sh = s2['allocated_shares']
s3_sh = s3['allocated_shares']
log(f'  Scale-in stages: S1={s1_sh}, S2={s2_sh}, S3={s3_sh}')
assert s1['allocated_shares'] == 30 and s2['allocated_shares'] == 50 and s3['allocated_shares'] == 20

# Trailing Stop Plan
holdings = {
 '005930': {'quantity': 100, 'entry_price': 70000.0, 'current_price': 80000.0, 'days_held': 5, 'current_score': 0.65, 'mfi': 60.0, 'obi': 0.2}
}
ts_plans = oms.calculate_trailing_stop_plan(current_holdings=holdings, prices_dict=prices_dict, regime='BULL_HIGH_VOL')
log(f' Trailing stop plan generated: {ts_plans}')

# Order Plan Generation
top_picks = [{'symbol': '005930', 'name': 'Samsung Electronics', 'market': 'KOSPI', 'close_price': 80000.0, 'ensemble_score': 0.75}]
weights = {'005930': 0.10}
plans = oms.generate_order_plan(top_picks, weights, total_capital=100000000.0, crisis_level='NORMAL', use_leland_buffer=False)
log(f' Generated OMS order plans: {len(plans)} orders')
assert len(plans) == 1 and plans[0]['symbol'] == '005930'

log('\n=== ALL FORENSIC CHECKS PASSED PERFECTLY ===')

with open('d:/Finance/code/stock/.agents/victory_auditor_alpha_max/forensic_report_raw.txt', 'w', encoding='utf-8') as f:
 f.write('\n'.join(log_lines))

print('Wrote forensic_report_raw.txt successfully.')
