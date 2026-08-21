import os

for worker in ['m3', 'm4', 'm5']:
    p = rf'D:\Finance\code\stock\.agents\teamwork_preview_worker_{worker}\handoff.md'
    out_p = rf'D:\Finance\code\stock\.agents\teamwork_preview_reviewer_2\{worker}_handoff_clean.txt'
    if os.path.exists(p):
        with open(p, 'rb') as f:
            data = f.read()
        text = data.decode('utf-8', errors='replace')
        with open(out_p, 'w', encoding='utf-8') as out:
            out.write(text)
        print(f'{worker}: decoded {len(data)} bytes -> {len(text)} chars')
    else:
        print(f'{worker}: not found {p}')
