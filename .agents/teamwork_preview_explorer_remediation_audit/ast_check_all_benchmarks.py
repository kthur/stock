import glob
import ast
import os

def check_all():
    files = sorted(glob.glob("trading_system/scripts/benchmark_phase*.py"))
    unprotected_writes = []

    for fpath in files:
        with open(fpath, "r", encoding="utf-8-sig") as f:
            content = f.read()
        try:
            tree = ast.parse(content, filename=fpath)
        except Exception as e:
            print(f"Error parsing {fpath}: {e}")
            continue

        top_level_writes = []

        for node in tree.body:
            # If node is a function or class definition, its body is NOT executed at module import
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue

            # If node is `if __name__ == '__main__':`, its body is protected
            if isinstance(node, ast.If):
                test_src = ast.unparse(node.test)
                if "__name__" in test_src and "__main__" in test_src:
                    continue

            # Any other statement at module level that writes files or opens files with 'w'
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call):
                    try:
                        call_src = ast.unparse(subnode)
                        if "open(" in call_src and ('"w"' in call_src or "'w'" in call_src):
                            top_level_writes.append((node.lineno, call_src))
                    except Exception:
                        pass

        if top_level_writes:
            unprotected_writes.append((fpath, top_level_writes))

    print(f"Total benchmark scripts scanned: {len(files)}")
    print(f"Scripts with UNPROTECTED top-level module file writes: {len(unprotected_writes)}")
    for fpath, writes in unprotected_writes:
        print(f"  {fpath}: {writes}")

if __name__ == "__main__":
    check_all()
