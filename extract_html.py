import re

with open('trading_system/src/web/dashboard.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Using regex to capture from return ''' to '''
match = re.search(r"return '''(.*?)'''", code, re.DOTALL)
if match:
    with open('dashboard_html.html', 'w', encoding='utf-8') as f2:
        f2.write(match.group(1))
    print("Extracted HTML.")
else:
    print("Failed to extract HTML.")
