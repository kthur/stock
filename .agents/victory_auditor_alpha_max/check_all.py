import sys, os, glob, ast
import numpy as np
import pandas as pd

sys.path.insert(0, 'trading_system')
sys.path.insert(0, 'trading_system/src')
sys.path.insert(0, '.')

print('=== VICTORY AUDITOR FORENSIC & INTEGRITY VERIFICATION ===')

# 1. StrategyRegistry check
from src.core.strategy_registry import get_registry
reg = get_registry()
reg.auto_discover(['src.core', 'src.ai'])
all_ids = reg.get_all_ids()
print(f'1. StrategyRegistry IDs ({len(all_ids)} total):')
for req in ['cross_asset_spillover', 'supply_chain_gnn', 'range_expansion_breakout']:
    assert req in all_ids, f'Missing {req}'
    cls, meta = reg.get(req)
    print(f'   - {req}: class={cls.__name__}, score_col={meta.score_column}, file={meta.output_file}')
print('   -> StrategyRegistry Check: PASS')

# 2. EnsembleScoringEngine check
from src.ai.ensemble_scorer import EnsembleScoringEngine
scorer = EnsembleScoringEngine()
print('\n2. EnsembleScoringEngine Regime Weights:')
for k, v in scorer.REGIME_WEIGHTS.items():
    s = sum(v.values())
    print(f'   - 1D Regime {k}: sum={s:.6f}, count={len(v)}')
    assert abs(s - 1.0) < 1e-5, f'1D Regime {k} sum error'

for k, v in scorer.REGIME_2D_WEIGHTS.items():
    s = sum(v.values())
    print(f'   - 2D Regime {k}: sum={s:.6f}, count={len(v)}')
    assert abs(s - 1.0) < 1e-5, f'2D Regime {k} sum error'
print('   -> Regime Weights Check: PASS')

# 3. Strategy Engines Execution Check
print('\n3. Empirical Execution of Strategies:')
from src.core.cross_asset_spillover import CrossAssetSpilloverEngine
from src.core.supply_chain_gnn import SupplyChainGNNEngine
from src.core.range_expansion_breakout import RangeExpansionBreakoutEngine

dates = pd.date_range('2026-01-01', periods=30, freq='D')
c = np.linspace(100, 120, 30)
df_sample = pd.DataFrame({
    'Open': c * 0.99,
    'High': c * 1.02,
    'Low': c * 0.98,
    'Close': c,
    'Volume': np.full(30, 200000.0)
}, index=dates)
p_dict = {'005930': df_sample, 'NVDA': df_sample, 'TSLA': df_sample}
ind_dict = {'sox_change': 3.5, 'usdkrw_change': 0.2, 'vix_change': -1.5}
sec_map = {'005930': 'Semiconductor', 'NVDA': 'Semiconductor', 'TSLA': 'Automotive'}

ca_res = CrossAssetSpilloverEngine().compute_scores(prices_dict=p_dict, indicators_df=ind_dict, sector_map=sec_map)
assert len(ca_res) == 3 and 'cross_asset_spillover_score' in ca_res.columns
print(f'   - CrossAssetSpilloverEngine scores: {dict(zip(ca_res.symbol, ca_res.cross_asset_spillover_score))}')

sc_res = SupplyChainGNNEngine().compute_scores(prices_dict=p_dict, sector_map=sec_map)
assert len(sc_res) == 3 and 'supply_chain_gnn_score' in sc_res.columns
print(f'   - SupplyChainGNNEngine scores: {dict(zip(sc_res.symbol, sc_res.supply_chain_gnn_score))}')

re_res = RangeExpansionBreakoutEngine().compute_scores(prices_dict=p_dict)
assert len(re_res) == 3 and 'range_expansion_score' in re_res.columns
print(f'   - RangeExpansionBreakoutEngine scores: {dict(zip(re_res.symbol, re_res.range_expansion_score))}')
print('   -> Strategy Execution Check: PASS')

# 4. Portfolio Optimization Check
print('\n4. Portfolio Optimization & Ledoit-Wolf Shrinkage:')
from src.analysis.portfolio_optimizer import calculate_risk_parity_weights, calculate_black_litterman_weights, shrink_covariance_matrix, calculate_hrp_weights
cov = np.array([[0.04, 0.01, 0.02], [0.01, 0.09, 0.01], [0.02, 0.01, 0.16]])
shrunk = shrink_covariance_matrix(cov)
rp_w = calculate_risk_parity_weights(shrunk)
bl_w = calculate_black_litterman_weights(shrunk, predicted_returns=np.array([0.05, 0.08, 0.12]))
hrp_w = calculate_hrp_weights(shrunk)
assert abs(sum(rp_w) - 1.0) < 1e-5
assert abs(sum(bl_w) - 1.0) < 1e-5
assert abs(sum(hrp_w) - 1.0) < 1e-5
print(f'   - Shrunk cov cond: {np.linalg.cond(shrunk):.2f}')
print(f'   - Risk Parity sum: {sum(rp_w):.6f}')
print(f'   - Black Litterman sum: {sum(bl_w):.6f}')
print(f'   - HRP sum: {sum(hrp_w):.6f}')
print('   -> Portfolio Optimization Check: PASS')

# 5. Execution OMS Precision Timing Check
print('\n5. Execution OMS Timing & Order Planning:')
from src.execution.oms_engine import ExecutionOMSEngine
oms = ExecutionOMSEngine(db_path=':memory:')
conf = oms.check_confluence_entry(ensemble_score=0.72, vcp_score=0.80, volume_surge_ratio=2.5, obi_score=0.5, price_above_ma50=True)
assert conf['is_valid_entry'] is True and conf['confluence_score'] >= 0.65
s1 = oms.generate_scale_in_order_plan('005930', total_target_shares=100, current_stage=1)
s2 = oms.generate_scale_in_order_plan('005930', total_target_shares=100, current_stage=2)
s3 = oms.generate_scale_in_order_plan('005930', total_target_shares=100, current_stage=3)
assert s1['allocated_shares'] == 30 and s2['allocated_shares'] == 50 and s3['allocated_shares'] == 20

top_picks = [{'symbol': '005930', 'name': 'Samsung Electronics', 'market': 'KOSPI', 'close_price': 80000.0, 'ensemble_score': 0.75}]
weights = {'005930': 0.10}
plans = oms.generate_order_plan(top_picks, weights, total_capital=100000000.0, crisis_level='NORMAL', use_leland_buffer=False)
assert len(plans) == 1 and plans[0]['symbol'] == '005930'
print(f'   - Confluence Entry: {conf}')
print(f'   - Scale-In 3 Stages: S1={s1[" allocated_shares\]}, S2={s2[\allocated_shares\]}, S3={s3[\allocated_shares\]}')
print(f' - Generated Orders: {len(plans)} orders in memory')
print(' -> OMS Precision Timing Check: PASS')

print('\n=== ALL AUDIT VERIFICATION CHECKS PASSED 100% ===')
