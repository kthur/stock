
import sys
sys.stdout.reconfigure(encoding='utf-8')

print('=== FAST_LOB_ENGINE.PY ===')
with open('trading_system/src/core/fast_lob_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()
for kw in ['F117', 'Kerr-Newman-Kiselev', 'Tachyon', 'tachyon', '-5/3', 'dark_energy', 'w_tachyon']:
    print(f'{kw}: {kw in text}')

print('=== SMART_ORDER_ROUTER.PY ===')
with open('trading_system/src/execution/smart_order_router.py', 'r', encoding='utf-8') as f:
    text_sor = f.read()
for kw in ['0.0000005', 'maker_floor', 'maker floor', '99.998%', '0.99998', 'ATS']:
    print(f'{kw}: {kw in text_sor}')

print('=== OMS_ENGINE.PY ===')
with open('trading_system/src/execution/oms_engine.py', 'r', encoding='utf-8') as f:
    text_oms = f.read()
for kw in ['-0.9998', '0.030', '99.998', '0.99998', '99.9995', '0.999995', 'anti_gaming', 'shading']:
    print(f'{kw}: {kw in text_oms}')
