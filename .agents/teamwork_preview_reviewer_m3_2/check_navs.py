import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from pathlib import Path
from bs4 import BeautifulSoup

html = Path('gh-pages/index.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')

nav_tabs = soup.find_all('nav', class_='tabs')
print(f'Total nav.tabs found: {len(nav_tabs)}')
for i, nav in enumerate(nav_tabs):
    buttons = nav.find_all('button', class_='tab')
    print(f'Nav {i+1} button count: {len(buttons)}')
    btn_texts = [b.get_text(strip=True) for b in buttons[:5]]
    print(f'  First 5 buttons: {btn_texts}')
