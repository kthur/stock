
import sys
sys.stdout.reconfigure(encoding='utf-8')

print('=== CHECKING UNIFIED_PORTFOLIO_ALLOCATOR.PY ===')
with open('trading_system/src/risk/unified_portfolio_allocator.py', 'r', encoding='utf-8') as f:
    text = f.read()

for kw in ['F117', 'Lurie', 'Fisher-Rao', 'Fisher', 'barycenter', '2.15', '1.65', '1.60', '2.70', 'mu_arithmetic', 'version >= 24']:
    print(f'{kw}: {kw in text}')

print('=== CHECKING PORTFOLIO_ALLOCATOR.PY ===')
with open('trading_system/src/risk/portfolio_allocator.py', 'r', encoding='utf-8') as f:
    p_text = f.read()

for kw in ['F117', 'Trans-Super-Hyper', 'super_hyper', '20!', '2432902008176640000', '0.80', 'cumulant']:
    print(f'{kw}: {kw in p_text}')
