import urllib.request
import urllib.parse
import json

q = "삼성전자"
url = f"https://finance.daum.net/api/search/search?q={urllib.parse.quote(q)}"
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://finance.daum.net/'
})
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
