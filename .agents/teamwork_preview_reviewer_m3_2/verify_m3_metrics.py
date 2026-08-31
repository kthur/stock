import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from pathlib import Path
from bs4 import BeautifulSoup

html_path = Path('gh-pages/index.html')
assert html_path.exists(), 'gh-pages/index.html does not exist'

html = html_path.read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

print(f'HTML Size: {len(html):,} bytes')

# 1. Check Card 1: 2D Market Regime & Risk Gates Console
card1 = soup.find(class_='regime-risk-card')
assert card1 is not None, 'Card 1 (regime-risk-card) not found'
print('[PASS] Card 1 (regime-risk-card) found')

regime_badges = card1.find_all(class_='badge')
badge_texts = [b.get_text(strip=True) for b in regime_badges]
print(f'Card 1 badges count: {len(badge_texts)}')
for b in badge_texts:
    print(f'  Badge: {b}')

macro_items = card1.find_all(class_='macro-item')
print(f'Card 1 macro items count: {len(macro_items)}')
assert len(macro_items) >= 10, f'Expected at least 10 macro items, got {len(macro_items)}'

gate_strip = card1.find(class_='gate-status-strip')
assert gate_strip is not None, 'gate-status-strip not found in Card 1'
print('[PASS] Gate status strip found in Card 1')

regime_matrix = card1.find('table')
assert regime_matrix is not None, '6-regime table not found in Card 1'
matrix_rows = regime_matrix.find_all('tr')
print(f'6-Regime table rows: {len(matrix_rows)}')

# 2. Check Card 2: Strategy Coverage & Data Health Diagnostic Center
card2 = soup.find(class_='health-monitor-section')
assert card2 is not None, 'Card 2 (health-monitor-section) not found'
print('[PASS] Card 2 (health-monitor-section) found')

health_cards = card2.find_all(class_='health-card')
print(f'Health cards count: {len(health_cards)}')
assert len(health_cards) == 31, f'Expected 31 health cards, got {len(health_cards)}'

cpcv_section = card2.find(class_='cpcv-stress-section')
assert cpcv_section is not None, 'CPCV stress section not found in Card 2'
print('[PASS] CPCV / Stress test section found in Card 2')

missingness_section = card2.find(class_='health-reasons-breakdown')
assert missingness_section is not None, 'Missingness breakdown section not found in Card 2'
print('[PASS] Missingness breakdown section found in Card 2')

# 3. Check Card 3: Portfolio Optimization & Execution OMS Command Center
panel_portfolio = soup.find(id='panel-portfolio')
assert panel_portfolio is not None, 'Panel portfolio (Card 3) not found'
print('[PASS] Panel portfolio found')

assert 'hrpDonutChart' in html, 'hrpDonutChart not found in HTML'
assert 'marketExposureChart' in html, 'marketExposureChart not found in HTML'
print('[PASS] Portfolio charts found')

portfolio_table = panel_portfolio.find('table')
assert portfolio_table is not None, 'Portfolio allocation table not found'
table_headers = [th.get_text(strip=True) for th in portfolio_table.find_all('th')]
print(f'Portfolio table headers: {table_headers}')
assert 'Leland 실행 상태' in table_headers or any('Leland' in h for h in table_headers), 'Leland status column missing'

# 4. Check 31 Strategy Navigation Tabs (Nav 2)
nav_tabs = soup.find_all('nav', class_='tabs')
assert len(nav_tabs) >= 2, f'Expected at least 2 nav.tabs, found {len(nav_tabs)}'
row2_tabs_nav = nav_tabs[1]
tabs = row2_tabs_nav.find_all('button', class_='tab')
print(f'Strategy tabs count: {len(tabs)}')
assert len(tabs) == 31, f'Expected 31 tabs, got {len(tabs)}'

expected_canonical_prefixes = [f'{i}.' for i in range(1, 32)]
actual_tab_texts = [t.get_text(strip=True) for t in tabs]
for i, (exp, act) in enumerate(zip(expected_canonical_prefixes, actual_tab_texts)):
    print(f'  Strategy {i+1}: {act}')
    assert act.startswith(exp), f'Tab {i+1} mismatch: expected prefix {exp}, got {act}'
print('[PASS] All 31 tabs match canonical numbering (1..31) in exact sequence')

# 5. Check for unformatted cell NaNs or None in tables
tables = soup.find_all('table')
print(f'Total tables in dashboard: {len(tables)}')
nan_cells = []
for t in tables:
    for td in t.find_all('td'):
        txt = td.get_text(strip=True)
        if txt.lower() in ['nan', 'none', 'undefined', 'null']:
            nan_cells.append((td.name, str(td.parent)[:100], txt))

print(f'Unformatted raw NaN table cells count: {len(nan_cells)}')
if nan_cells:
    for nc in nan_cells[:10]:
        print(f'  [WARN/FAIL] Tag <{nc[0]}> in parent {nc[1]}: {nc[2]}')

assert len(nan_cells) == 0, f'Found {len(nan_cells)} unformatted NaN cells!'
print('[PASS] Zero unformatted NaN/None/undefined cells in tables')

print('\nALL M3 REVIEW CHECKS PASSED PERFECTLY!')
