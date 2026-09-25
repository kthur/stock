import subprocess

other_scripts = [
    "trading_system/scripts/benchmark_phase2_quant_performance.py",
    "trading_system/scripts/benchmark_phase20_quant_performance.py",
    "trading_system/scripts/benchmark_phase21_quant_performance.py",
    "trading_system/scripts/benchmark_phase22_quant_performance.py",
    "trading_system/scripts/benchmark_phase23_quant_performance.py",
    "trading_system/scripts/benchmark_phase24_quant_performance.py",
]

for s in other_scripts:
    res = subprocess.run(["git", "diff", "HEAD", "--", s], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(f"=== {s} ===")
    print(res.stdout)
