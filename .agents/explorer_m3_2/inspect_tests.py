import json
import os
import hashlib

def get_file_hash(path):
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

with open('.agents/explorer_m3_2/test_collection_data.json') as f:
    data = json.load(f)

tests_files = {k.replace('tests/', '', 1): (k, v) for k, v in data['tests_files'].items()}
ts_tests_files = {k.replace('trading_system/tests/', '', 1): (k, v) for k, v in data['ts_tests_files'].items()}

common = set(tests_files.keys()) & set(ts_tests_files.keys())
only_tests = set(tests_files.keys()) - set(ts_tests_files.keys())
only_ts_tests = set(ts_tests_files.keys()) - set(tests_files.keys())

print(f"Total in tests/: {len(tests_files)} files ({data['tests_count']} tests)")
print(f"Total in ts_tests/: {len(ts_tests_files)} files ({data['ts_tests_count']} tests)")
print(f"Files common to both directories: {len(common)}")
print(f"Files only in tests/: {len(only_tests)}")
print(f"Files only in trading_system/tests/: {len(only_ts_tests)}")

print("\n--- Common Files: Test Count or Hash Differences ---")
identical_count = 0
diff_hash_count = 0
for f in sorted(common):
    c1 = tests_files[f][1]
    c2 = ts_tests_files[f][1]
    p1 = os.path.join('tests', f)
    p2 = os.path.join('trading_system', 'tests', f)
    h1 = get_file_hash(p1)
    h2 = get_file_hash(p2)
    if c1 != c2 or h1 != h2:
        diff_hash_count += 1
        print(f"{f}: tests/ count={c1}, ts_tests/ count={c2}, same_hash={h1==h2}")
    else:
        identical_count += 1

print(f"\nIdentical files in both: {identical_count}, Files with diffs in both: {diff_hash_count}")

print("\n--- Files ONLY in tests/ ---")
for f in sorted(only_tests):
    print(f"  {f} ({tests_files[f][1]} tests)")

print("\n--- Files ONLY in trading_system/tests/ ---")
for f in sorted(only_ts_tests):
    print(f"  {f} ({ts_tests_files[f][1]} tests)")
