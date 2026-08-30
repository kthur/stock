import ast
import os
import glob

src_files = glob.glob('trading_system/src/**/*.py', recursive=True) + glob.glob('src/**/*.py', recursive=True)
src_files = list(set(src_files))
print(f'Scanning {len(src_files)} source files for facade / hardcoding patterns...')

facades = []
empty_funcs = []
hardcoded_returns = []

for fpath in sorted(src_files):
    if '__pycache__' in fpath:
        continue
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=fpath)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for 1-line return constant functions
                real_stmts = [s for s in node.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))] # filter docstrings
                if len(real_stmts) == 1:
                    stmt = real_stmts[0]
                    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                        hardcoded_returns.append((fpath, node.name, stmt.value.value))
                    elif isinstance(stmt, ast.Pass):
                        empty_funcs.append((fpath, node.name))
    except Exception as e:
        print(f'Error parsing {fpath}: {e}')

print(f'Scan completed. Total 1-line constant returns: {len(hardcoded_returns)}, Empty funcs: {len(empty_funcs)}')
print('\n--- Constant Return Functions ---')
for fpath, name, val in hardcoded_returns[:25]:
    print(f'  {fpath} -> {name}() -> {val}')

print('\n--- Empty Functions ---')
for fpath, name in empty_funcs[:25]:
    print(f'  {fpath} -> {name}()')
