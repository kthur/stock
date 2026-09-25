import os
import hashlib

# Collect content for each phase from 66 down to 2
phases = list(range(66, 1, -1))
phase_contents = []

for p in phases:
    # Check possible paths for phase p
    candidate_paths = [
        f"reports/quant_benchmark_comparison_phase{p}.md",
        f"trading_system/reports/quant_benchmark_comparison_phase{p}.md",
        f"trading_system/result/quant_benchmark_comparison_phase{p}.md",
    ]
    found = False
    for cp in candidate_paths:
        if os.path.exists(cp) and os.path.getsize(cp) > 0:
            with open(cp, "r", encoding="utf-8") as f:
                c = f.read().strip()
                if len(c) > 0:
                    phase_contents.append((p, c))
                    found = True
                    break
    if not found:
        print(f"WARNING: Phase {p} not found in any candidate path!")

print(f"Total phases collected: {len(phase_contents)}")

# Format with standard markdown separator
separator = "\n\n---\n\n"
canonical_text = separator.join(content for _, content in phase_contents) + "\n"

# Verify critical phases are present in order
for p in [66, 65, 64, 60, 52, 46, 45, 44, 43, 39, 23, 22, 2]:
    assert f"Phase {p}" in canonical_text, f"Phase {p} missing from canonical text!"

# Verify descending order of key phases
p46_idx = canonical_text.find("Phase 46 Quantitative Enhancement")
p45_idx = canonical_text.find("Phase 45 Quantitative Enhancement")
p44_idx = canonical_text.find("Phase 44 Quantitative Enhancement")
p43_idx = canonical_text.find("Phase 43 Quantitative Enhancement")
assert p46_idx < p45_idx < p44_idx < p43_idx, f"Order error: {p46_idx}, {p45_idx}, {p44_idx}, {p43_idx}"

# Target destination paths
target_paths = [
    "reports/quant_benchmark_comparison.md",
    "trading_system/reports/quant_benchmark_comparison.md",
    "trading_system/result/quant_benchmark_comparison.md",
]

for tp in target_paths:
    os.makedirs(os.path.dirname(tp), exist_ok=True)
    with open(tp, "w", encoding="utf-8", newline="\n") as f:
        f.write(canonical_text)

# Verify SHA256 synchronization
hashes = {}
for tp in target_paths:
    with open(tp, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
        hashes[tp] = h
        print(f"{tp}: {os.path.getsize(tp)} bytes, sha256={h[:16]}...")

assert len(set(hashes.values())) == 1, f"SHA-256 mismatch: {hashes}"
print("SUCCESS: All 3 canonical benchmark reports synchronized perfectly!")
