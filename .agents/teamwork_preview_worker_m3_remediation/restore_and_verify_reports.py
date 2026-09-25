import shutil, hashlib, os

src = "trading_system/reports/quant_benchmark_comparison.md"
dest1 = "reports/quant_benchmark_comparison.md"
dest2 = "trading_system/result/quant_benchmark_comparison.md"

expected_hash = "d09edbfd088fe7a030407cd9e65c2e29d9b6ced0939dec69efe20ebb8c432f83"
expected_size = 386864

# Copy src to dest1 and dest2 to ensure 100% bit-for-bit sync
shutil.copyfile(src, dest1)
shutil.copyfile(src, dest2)

paths = [dest1, src, dest2]
hashes = {}
sizes = {}

for p in paths:
    data = open(p, "rb").read()
    h = hashlib.sha256(data).hexdigest()
    s = len(data)
    hashes[p] = h
    sizes[p] = s
    assert h == expected_hash, f"Hash mismatch for {p}: {h} != {expected_hash}"
    assert s == expected_size, f"Size mismatch for {p}: {s} != {expected_size}"
    print(f"Verified {p}: size={s}, sha256={h}")

assert len(set(hashes.values())) == 1, "Hashes are not identical across all 3 files!"
assert len(set(sizes.values())) == 1, "Sizes are not identical across all 3 files!"
print("ALL 3 COMPARISON REPORTS MATCH BIT-FOR-BIT!")
