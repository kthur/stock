import os
import sys
import math
import numpy as np
import pandas as pd

# Add repo to sys.path
sys.path.insert(0, r"d:\Finance\code\stock\trading_system")
sys.path.insert(0, r"d:\Finance\code\stock")

from src.risk.portfolio_allocator import PortfolioAllocator
from src.execution.oms_engine import ExecutionOMSEngine
from src.execution.kill_switch import engage, disengage, is_kill_switch_active
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer

allocator = PortfolioAllocator()

# 1. Stress test EVT-CVaR edge cases
assert allocator.estimate_evt_cvar(None)['method'] == 'zero_fallback'
assert allocator.estimate_evt_cvar([])['method'] == 'zero_fallback'
assert allocator.estimate_evt_cvar([0.01]*3)['method'] == 'zero_fallback'
res_const = allocator.estimate_evt_cvar([0.01]*50)
assert res_const['cvar'] >= 0.0
res_nan = allocator.estimate_evt_cvar([np.nan, 0.01, -0.05, 0.02, -0.03, np.nan, 0.01, -0.02, 0.03, 0.01])
assert res_nan['cvar'] >= 0.0

# 2. Stress test Leland Buffer Band
assert allocator.calculate_dynamic_buffer_band('SYM', 0.0, 0.002, 0.02) == allocator.delta_floor
assert allocator.calculate_dynamic_buffer_band('SYM', 0.20, 0.0, 0.02) == allocator.delta_floor
band_huge = allocator.calculate_dynamic_buffer_band('SYM', 0.20, 0.05, 0.80, risk_aversion=0.01)
assert band_huge == allocator.delta_cap

# 3. Stress test OMS safety gates
test_db = r"d:\Finance\code\stock\.agents\reviewer_2\stress_test_trade_logs.db"
if os.path.exists(test_db):
    try:
        os.remove(test_db)
    except Exception:
        pass

oms = ExecutionOMSEngine(test_db)

# Test severe crisis gate
assert oms.generate_order_plan([{'symbol': '005930', 'close_price': 70000}], {'005930': 0.1}, crisis_level='SEVERE') == []

# Test kill switch gate
engage('Adversarial Test')
assert is_kill_switch_active()
assert oms.generate_order_plan([{'symbol': '005930', 'close_price': 70000}], {'005930': 0.1}) == []
disengage()
assert not is_kill_switch_active()

# Test invalid symbols
assert oms.generate_order_plan([{'symbol': 'DROP TABLE;--', 'close_price': 70000}], {'DROP TABLE;--': 0.1}) == []
assert oms.generate_order_plan([{'symbol': "{'dict': 123}", 'close_price': 70000}], {"{'dict': 123}": 0.1}) == []

# Test price bounds
assert oms.generate_order_plan([{'symbol': '005930', 'close_price': 0.0}], {'005930': 0.1}) == []
assert oms.generate_order_plan([{'symbol': '005930', 'close_price': -50.0}], {'005930': 0.1}) == []
assert oms.generate_order_plan([{'symbol': '005930', 'close_price': 200_000_000.0}], {'005930': 0.1}) == []

# Test valid order plan generation
valid_plan = oms.generate_order_plan([{'symbol': '005930', 'close_price': 70000, 'name': 'Samsung', 'market': 'KOSPI'}], {'005930': 0.10}, total_capital=100000000.0)
assert len(valid_plan) == 1
assert valid_plan[0]['symbol'] == '005930'
assert valid_plan[0]['target_amount'] == 10000000.0
# 10,000,000 / 70,000 = 142.85 -> raw 142 -> 10-share round lot = 140
assert valid_plan[0]['quantity'] == 140

print('All adversarial stress tests PASSED successfully!')
