import re
import os

def fix_naver_urls(file_path: str):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace legacy Naver mobile stock URLs with modern mobile URL format
    updated_content = re.sub(
        r'https://m\.stock\.naver\.com/item/main\.nhn\?code=([A-Za-z0-9]+)',
        r'https://m.stock.naver.com/domestic/stock/\1/total',
        content
    )
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated_content)
    print(f"Successfully updated Naver URLs in {file_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fix_naver_urls(os.path.join(base_dir, "gh-pages", "index.html"))
    if os.path.exists(os.path.join(base_dir, "trading_system", "gh-pages", "index.html")):
        fix_naver_urls(os.path.join(base_dir, "trading_system", "gh-pages", "index.html"))
