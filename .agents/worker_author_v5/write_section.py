import sys
import base64

if len(sys.argv) < 3:
    print('Usage: write_section.py <target_file> <b64_string> [mode]')
    sys.exit(1)

target_file = sys.argv[1]
b64_content = sys.argv[2].strip()
mode = sys.argv[3] if len(sys.argv) > 3 else 'w'

# Auto-pad missing base64 padding
b64_content += '=' * (-len(b64_content) % 4)

data = base64.b64decode(b64_content.encode('ascii')).decode('utf-8')
with open(target_file, mode, encoding='utf-8') as f:
    f.write(data)

print(f'Successfully wrote {len(data)} chars to {target_file}')
