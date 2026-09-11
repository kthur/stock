
import sys
sys.stdout.reconfigure(encoding='utf-8')

print('--- UNIFIED_PORTFOLIO_ALLOCATOR.PY ---')
with open('trading_system/src/risk/unified_portfolio_allocator.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if any(k in line for k in ['F117', 'mu_arithmetic', '2.15', 'arithmetic_spectral', 'Phase 24']):
        print(f'{i+1}: {line.strip()}')

print('--- PORTFOLIO_ALLOCATOR.PY ---')
with open('trading_system/src/risk/portfolio_allocator.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if any(k in line for k in ['F117', 'Trans-Super-Hyper', 'super_hyper', 'cumulant', 'Phase 24']):
        print(f'{i+1}: {line.strip()}')
