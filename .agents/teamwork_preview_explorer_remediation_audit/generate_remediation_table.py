import subprocess
import os

scripts = [f"trading_system/scripts/benchmark_phase{p}_quant_performance.py" for p in range(25, 40)]

results = []

for s in scripts:
    res = subprocess.run(["git", "diff", "HEAD", "--", s], capture_output=True, text=True, encoding="utf-8", errors="replace")
    diff = res.stdout
    
    # Also get the HEAD file content
    res_head = subprocess.run(["git", "show", f"HEAD:{s}"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    head_lines = res_head.stdout.splitlines() if res_head.stdout else []
    
    # Find in HEAD where `content = "\n".join(lines)` starts
    head_start_idx = None
    for idx, l in enumerate(head_lines, 1):
        if 'content = "\\n".join(lines)' in l or "content = '\\n'.join(lines)" in l:
            head_start_idx = idx
            break
    head_end_idx = len(head_lines)
    
    # Get the current file content
    with open(s, "r", encoding="utf-8-sig") as f:
        curr_lines = f.read().splitlines()
    curr_main_idx = None
    for idx, l in enumerate(curr_lines, 1):
        if 'if __name__ == "__main__":' in l:
            curr_main_idx = idx
            break
    curr_end_idx = len(curr_lines)
    
    results.append({
        "phase": s.split("benchmark_phase")[1].split("_")[0],
        "script": s,
        "head_lines": f"L{head_start_idx}-L{head_end_idx}",
        "curr_lines": f"L{curr_main_idx}-L{curr_end_idx}",
        "head_start": head_start_idx,
        "head_end": head_end_idx,
        "curr_start": curr_main_idx,
        "curr_end": curr_end_idx,
    })

print(f"{'Phase':<6} | {'Script':<60} | {'HEAD Unwrapped Lines':<20} | {'Wrapped Lines':<20}")
print("-" * 115)
for r in results:
    print(f"{r['phase']:<6} | {r['script']:<60} | {r['head_lines']:<20} | {r['curr_lines']:<20}")

with open(".agents/teamwork_preview_explorer_remediation_audit/table_summary.txt", "w", encoding="utf-8") as f:
    f.write(f"{'Phase':<6} | {'Script':<60} | {'HEAD Unwrapped Lines':<20} | {'Wrapped Lines':<20}\n")
    f.write("-" * 115 + "\n")
    for r in results:
        f.write(f"{r['phase']:<6} | {r['script']:<60} | {r['head_lines']:<20} | {r['curr_lines']:<20}\n")
