import sys
import math
import numpy as np

sys.path.insert(0, 'trading_system/src')
sys.path.insert(0, 'trading_system')

from src.core.fast_lob_engine import FastOrderBookMatchingEngine, DeepHawkesArrivalProcess
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler

print('=== 1. Testing FastOrderBookMatchingEngine F113.2 ===')
lob = FastOrderBookMatchingEngine('AAPL')
lob.add_limit_order('b1', 'BUY', 150.0, 5000)
lob.add_limit_order('a1', 'SELL', 150.10, 5000)

res_knkp = lob.compute_kerr_newman_kiselev_phantom_queue_acceleration(
    charge_parameter=0.5,
    spin_parameter=0.5,
    quintessence_parameter=0.05,
    phantom_parameter=0.02,
    w_q=-2.0/3.0,
    w_p=-4.0/3.0
)
assert res_knkp['equation_of_state_w_q'] == -0.6667
assert res_knkp['equation_of_state_w_p'] == -1.3333
assert res_knkp['phantom_c_p'] == 0.02
assert res_knkp['quintessence_c_q'] == 0.05
assert 'phantom_horizon_r_P' in res_knkp
assert 'knk_p_hydrodynamic_acceleration' in res_knkp
assert 'knk_p_tidal_force' in res_knkp
assert 'knk_p_micro_price' in res_knkp
print('KNK-P acceleration:', res_knkp['knk_p_hydrodynamic_acceleration'])
print('KNK-P tidal force:', res_knkp['knk_p_tidal_force'])

# Check aliases
aliases = [
    'compute_kerr_newman_kiselev_phantom_acceleration',
    'compute_knk_phantom_acceleration',
    'compute_knk_phantom_hydrodynamics',
    'calculate_kerr_newman_kiselev_phantom_queue_acceleration',
    'calculate_knk_phantom_queue_acceleration',
    'compute_kerr_newman_kiselev_phantom_frame_dragging',
    'calculate_kerr_newman_kiselev_phantom_hydrodynamics',
    'calculate_kerr_newman_kiselev_phantom_frame_dragging',
]
for a in aliases:
    fn = getattr(lob, a, None)
    assert fn is not None, f'Missing alias: {a}'
    res_a = fn()
    assert math.isclose(res_a['knk_p_hydrodynamic_acceleration'], res_knkp['knk_p_hydrodynamic_acceleration'])
print('All 8 KNK-P aliases verified successfully!')

# Check DeepHawkesArrivalProcess dark routing cap
proc = DeepHawkesArrivalProcess()
proc.lambda_state = np.array([15.0, 0.5, 0.2])
cap_23 = proc.compute_preemptive_dark_routing(version=23)
print('DeepHawkes dark cap v23:', cap_23['preemptive_dark_routing_ratio'])
assert cap_23['preemptive_dark_routing_ratio'] == 0.99995

cap_22 = proc.compute_preemptive_dark_routing(version=22)
print('DeepHawkes dark cap v22:', cap_22['preemptive_dark_routing_ratio'])
assert cap_22['preemptive_dark_routing_ratio'] == 0.9999
print('DeepHawkes dark cap v22 and v23 verified!')

print('=== 2. Testing SmartOrderRouter Micro-Friction Minimization ===')
sor = SmartOrderRouter()

# Maker floor under extreme toxicity
res_maker = sor.route_order({'symbol': 'AAPL', 'action': 'BUY', 'quantity': 1000000, 'gamma_toxic_dir': 1.0, 'version': 23}, ats_available=False)
maker_legs = [l for l in res_maker['legs'] if 'MAKER' in l.get('venue_type', '')]
assert len(maker_legs) > 0
assert maker_legs[0]['quantity'] == 1, f"Expected 1, got {maker_legs[0]['quantity']}"
print('SOR maker floor contracted to exactly 1 share out of 1,000,000 (0.000001)!')

# Dark pool routing cap
res_dark = sor.route_order({'symbol': 'AAPL', 'action': 'BUY', 'quantity': 1000000, 'gamma_toxic_dir': 1.0, 'version': 23, 'queue_imbalance': 0.8, 'qi_acceleration': 0.5}, ats_available=True)
dark_legs = [l for l in res_dark['legs'] if 'DARK' in l.get('venue_type', '') or 'ATS' in l.get('venue_type', '')]
total_dark = sum(l['quantity'] for l in dark_legs)
assert total_dark == 999950, f"Expected 999950, got {total_dark}"
print('SOR dark routing cap expanded to exactly 99.995% (999,950 shares)!')

# Anti-gaming dynamic MinQty
res_ag = sor.route_order({'symbol': 'AAPL', 'action': 'BUY', 'quantity': 1000000, 'gamma_toxic_dir': 1.0, 'darkpool_score': 1.0, 'version': 23}, ats_available=True)
dark_legs_ag = [l for l in res_ag.get('legs', []) if 'DARK' in l.get('venue_type', '')]
assert len(dark_legs_ag) > 0
dark_qty_ag = dark_legs_ag[0]['quantity']
min_qty_ag = dark_legs_ag[0].get('min_quantity', 0)
ratio_ag = min_qty_ag / dark_qty_ag
print(f'SOR Anti-Gaming min_quantity: {min_qty_ag}, dark_qty: {dark_qty_ag}, ratio: {ratio_ag:.7f}')
assert math.isclose(ratio_ag, 0.99999, abs_tol=1e-4)
print('SOR Anti-Gaming MinQty scaled up to exactly 99.999%!')

print('=== 3. Testing ExecutionOMSEngine & AlmgrenChrissScheduler Preemptive Tick Shading ===')
oms = ExecutionOMSEngine()
sched = AlmgrenChrissScheduler()

# At h = 0.040, spr = 1.0
peg_oms = oms.calculate_peg_limit_price(100.0, 99.5, 100.5, action='BUY', hawkes_intensity=0.040, version=23)
peg_sched = sched.calculate_peg_limit_price(100.0, 99.5, 100.5, action='BUY', hawkes_intensity=0.040, version=23)
expected_peg = 100.0 - 0.9995 * 1.0 * (0.040 - 0.035)
assert math.isclose(peg_oms, expected_peg, abs_tol=1e-6)
assert math.isclose(peg_sched, expected_peg, abs_tol=1e-6)
print(f'OMS and Scheduler peg at h=0.040: {peg_oms:.7f} (expected: {expected_peg:.7f})')

# At h = 0.035 (boundary)
peg_oms_bd = oms.calculate_peg_limit_price(100.0, 99.5, 100.5, action='BUY', hawkes_intensity=0.035, version=23)
assert math.isclose(peg_oms_bd, 100.0, abs_tol=1e-6)
print('OMS boundary at h=0.035 verified: no shift applied')

# Backward compatibility with v22 at h=0.038
peg_v22 = oms.calculate_peg_limit_price(100.0, 99.5, 100.5, action='BUY', hawkes_intensity=0.038, version=22)
assert math.isclose(peg_v22, 100.0, abs_tol=1e-6)
print('v22 backward compatibility at h=0.038 verified: unshifted at 100.0')

# Phase 23 activation at h=0.038
peg_v23 = oms.calculate_peg_limit_price(100.0, 99.5, 100.5, action='BUY', hawkes_intensity=0.038, version=23)
expected_v23 = 100.0 - 0.9995 * 1.0 * (0.038 - 0.035)
assert math.isclose(peg_v23, expected_v23, abs_tol=1e-6)
print(f'v23 activation at h=0.038 verified: {peg_v23:.7f} (expected: {expected_v23:.7f})')

print('\n*** ALL PHASE 23 MICROSTRUCTURE & OMS TESTS PASSED 100% ***')
