import subprocess
import os

scripts = [f"trading_system/scripts/benchmark_phase{p}_quant_performance.py" for p in range(25, 40)]

output = []

for s in scripts:
    res = subprocess.run(["git", "diff", "HEAD", "--", s], capture_output=True, text=True)
    diff = res.stdout
    # parse the diff chunk header: @@ -start,len +start,len @@
    lines = diff.splitlines()
    chunk_headers = [l for l in lines if l.startswith("@@")]
    output.append({
        "script": s,
        "chunk_header": chunk_headers[0] if chunk_headers else "NO DIFF",
        "diff": diff
    })

with open(".agents/teamwork_preview_explorer_remediation_audit/diff_analysis.txt", "w", encoding="utf-8") as f:
    for item in output:
        f.write(f"Script: {item['script']}\n")
        f.write(f"Chunk Header: {item['chunk_header']}\n")
        f.write("Diff:\n")
        f.write(item['diff'])
        f.write("\n" + "="*80 + "\n\n")

print(f"Successfully analyzed {len(output)} scripts.")
