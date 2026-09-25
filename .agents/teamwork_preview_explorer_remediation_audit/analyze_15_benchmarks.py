import subprocess
import os

scripts = [f"trading_system/scripts/benchmark_phase{p}_quant_performance.py" for p in range(25, 40)]

for s in scripts:
    print(f"=== {s} ===")
    res = subprocess.run(["git", "diff", "HEAD", "--", s], capture_output=True, text=True)
    print(res.stdout)
