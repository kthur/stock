import re
import hashlib

def main():
    print("=== CHECKING DASHBOARD HTML INTEGRITY ===")
    
    # 1. Compare gh-pages/index.html and trading_system/gh-pages/index.html
    f1 = open('gh-pages/index.html', 'rb').read()
    f2 = open('trading_system/gh-pages/index.html', 'rb').read()
    h1 = hashlib.md5(f1).hexdigest()
    h2 = hashlib.md5(f2).hexdigest()
    print(f"gh-pages/index.html size: {len(f1)}, md5: {h1}")
    print(f"trading_system/gh-pages/index.html size: {len(f2)}, md5: {h2}")
    assert f1 == f2, "HTML files are not identical!"
    print("[PASS] Both index.html files are strictly identical.")

    # 2. Check Ensemble Market Filter Buttons
    html = f1.decode('utf-8')
    m = re.search(r'id="filter-ensemble"[^>]*>(.*?)</div>', html, re.DOTALL)
    assert m, "filter-ensemble container not found!"
    btn_container = m.group(1)
    mkts = re.findall(r'data-mkt="([^"]+)"', btn_container)
    print(f"Ensemble Filter Bar Buttons (data-mkt): {mkts}")
    
    # Check for corrupt words
    corrupt_words = ['Acquisition', 'Corp', 'Sciences', 'Mellon', '1', '66']
    for word in corrupt_words:
        assert f'data-mkt="{word}"' not in btn_container, f"Corrupt data-mkt '{word}' found!"
        assert f'data-mkt="{word.lower()}"' not in btn_container, f"Corrupt data-mkt '{word.lower()}' found!"
    print("[PASS] Zero corrupt market category buttons found.")

    # 3. Check 37-strategy labels in index.html
    assert "34-Strategy" not in html, "Outdated '34-Strategy' string still present in index.html!"
    assert "34-Factor" not in html, "Outdated '34-Factor' string still present in index.html!"
    
    # Check 37 strategies presence in tabs
    s35 = "switchTab(this,'dualcorrection')" in html
    s36 = "switchTab(this,'indexrebalance')" in html
    s37 = "switchTab(this,'overnightgap')" in html
    print(f"37-strategy tabs presence: DualCorrection={s35}, IndexRebalance={s36}, OvernightGap={s37}")
    assert s35 and s36 and s37, "37-strategy tabs missing!"
    print("[PASS] 37-strategy tabs and panels present.")

    # 4. Check portfolio_allocation.txt
    port_text = open('trading_system/result/portfolio_allocation.txt', encoding='utf-8').read()
    print("Checking trading_system/result/portfolio_allocation.txt...")
    lines = port_text.splitlines()
    table_started = False
    valid_mkts = {"KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"}
    for line in lines:
        if "No." in line and "Symbol" in line:
            table_started = True
            continue
        if table_started and line.startswith("---"):
            continue
        if table_started and ("Allocated Capital" in line or "Remaining Cash" in line):
            break
        if table_started and line.strip():
            tokens = line.split()
            if len(tokens) >= 8:
                # In 8-column format: tokens[-5] is Market
                mkt = tokens[-5]
                assert mkt in valid_mkts, f"Invalid market in portfolio_allocation.txt: '{mkt}' in line: {line}"
    print("[PASS] portfolio_allocation.txt contains only valid market codes.")

if __name__ == '__main__':
    main()
