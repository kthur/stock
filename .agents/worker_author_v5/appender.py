import sys

def append_text(target_path, text):
    with open(target_path, 'a', encoding='utf-8') as f:
        f.write(text)

if __name__ == '__main__':
    target = sys.argv[1]
    # read from stdin
    data = sys.stdin.read()
    append_text(target, data)
    print(f'Appended {len(data)} chars to {target}')
