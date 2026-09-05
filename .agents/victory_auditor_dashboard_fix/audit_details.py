import sys, os
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
sys.path.insert(0, os.getcwd())

import re
from pathlib import Path
from trading_system.generate_report import KNOWN_ALL_MKTS,_CORE_ORDER,_INTL_ORDER

print('KNOWN_ALL_MKTS size:', len(KNOWN_ALL_MKTS))

for p in [Path('gh-pages/index.html'), Path('trading_system/gh-pages/index.html')]:
    if not p.exists():
        print(f'{p} does not exist')
        continue
    content = p.read_text(encoding='utf-8')
    print(f'=== File: {p} (size {len(content):,} chars) ===')
    
    # 1. Spurious filter buttons
    btns = re.findall(r'<button class="filter-btn[^"]*"[^>]*data-mkt="([^"]+)">([^<]+)</button>', content)
    unique_btns = set(btns)
    print(f'Total filter buttons in file: {len(btns)}, unique pairs: {len(unique_btns)}')
    spurious = []
    for mkt, text in unique_btns:
        if mkt != 'all' and mkt not in KNOWN_ALL_MKTS:
            spurious.append((mkt, text))
    if spurious:
        print('  FAIL: Spurious filter buttons found:', spurious)
    else:
        print('  PASS: ZERO spurious filter buttons found!')
        
    bad_keywords = ['Acquisition', 'Corp', '1', 'Sciences', 'Mellon', '66']
    corrupt_hits = [b for b in btns if any(k in b[0] or k in b[1] for k in bad_keywords)]
    print('  Corrupt keyword button matches:', len(corrupt_hits))
    assert len(corrupt_hits) == 0

    s34 = re.findall(r'.{0,50}(?:34-Strategy|34 Strategy|34 Strategies|34-Factor).{0,50}', content, re.IGNORECASE)
    print(f'  34-strategy strings found ({len(s34)}):)', s34)
    assert len(s34) == 0

    s37 = re.findall(r'.{0,50}(?:37-Strategy|37 Strategy|37 Strategies|37-Factor).{0,50}', content, re.IGNORECASE)
    print(f'  37-strategy strings found ({len(s37)}):')
    for item in s37[:6]:
        print('    ', ascii(item.strip()))
    assert len(s37) >= 5

    tabs = re.findall(r'<div class="row2-wrapper">.*?<nav class="tabs">(.*?)</nav>', content, re.DOTALL)
    if tabs:
        strat_buttons = re.findall(r"onclick=\"switchTab\(this,'([^']+)'\)\"", tabs[0])
        print(f'  Row 2 strategy buttons count: {len(strat_buttons)}')
        assert len(strat_buttons) == 37
        assert len(set(strat_buttons)) == 37
    else:
        strat_buttons = []
        print('  Row 2 wrapper not found')
        assert False

    missing_panels = []
    for s_id in strat_buttons:
        if f'id="panel-{s_id}"' not in content:
            missing_panels.append(s_id)
    print(f'  Missing strategy panels count: {len(missing_panels)}')
    assert len(missing_panels) == 0, f"Missing panels: {missing_panels}"
    print(f'  All 37 strategy panels (id="panel-<strat>") present!')

    row1_tabs = ['portfolio', 'backtest', 'regime', 'scenario', 'history', 'ensemble']
    for t_id in row1_tabs:
        assert f"switchTab(this,'{t_id}')" in content or f'switchTab(this, \'{t_id}\')' in content or f'id="tab-{t_id}"' in content, f"Missing row 1 tab {t_id}"
        assert f'id="panel-{t_id}"' in content, f"Missing row 1 panel panel-{t_id}"
    print(f'  All {len(row1_tabs)} Row 1 navigation tabs and panels present!')

print('ALL HTML CHECKS PASSED!')

