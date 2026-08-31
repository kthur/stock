import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from trading_system.generate_report import parse_strategy_coverage_report, StrategyHealthInfo, build_strategy_health_monitor_html

# Test empty cov_text
total, items = parse_strategy_coverage_report('')
print(f'Empty cov_text test: total_symbols={total}, items_count={len(items)}')
assert len(items) == 31, f'Expected 31 items even on empty report, got {len(items)}'

# Check all 31 default items
for i, item in enumerate(items):
    assert item.num == i + 1, f'Item {i} num mismatch: {item.num}'
    print(f'Item {item.num:2d}: id={item.strategy_id:25s} name={item.name_ko:20s} status={item.status:10s} cov={item.coverage_pct:.1f}%')

# Test rendering HTML with fallback items
html = build_strategy_health_monitor_html(total, items, '')
assert 'Strategy Data Health Monitor' in html
assert 'data-status=healthy' in html
assert 'data-status=fallback' in html or 'data-status=partial' in html
print('\nCoverage Parser Empty Robustness & HTML Rendering Test Passed!')
