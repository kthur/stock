import glob
import re

for f in sorted(glob.glob('trading_system/scripts/benchmark_phase*.py')):
    with open(f, 'r', encoding='utf-8') as fh:
        text = fh.read()
    if 'reports/quant_benchmark_comparison.md' in text:
        # Check how it writes
        lines = [line.strip() for line in text.splitlines() if 'reports/quant_benchmark_comparison.md' in line]
        print(f, lines)
