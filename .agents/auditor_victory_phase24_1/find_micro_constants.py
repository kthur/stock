
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

for py_path in Path('trading_system/src').rglob('*.py'):
    with open(py_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    found = []
    for kw in ['0.9998', '0.99998', '0.999995', '99.998', '99.9995', '0.0000005', 'anti_gaming', 'anti-gaming']:
        if kw in text:
            found.append(kw)
    if found:
        print(f'{py_path}: {found}')
