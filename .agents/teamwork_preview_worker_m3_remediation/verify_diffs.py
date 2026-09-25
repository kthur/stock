import subprocess

all_matched = True
for phase in range(25, 40):
    script_path = f"trading_system/scripts/benchmark_phase{phase}_quant_performance.py"
    res = subprocess.run(["git", "diff", script_path], capture_output=True, text=True)
    actual_diff = res.stdout.strip()
    if not actual_diff:
        print(f"Phase {phase}: NO GIT DIFF (unmodified from git index)")
        all_matched = False
    elif 'if __name__ == "__main__":' in actual_diff:
        print(f"Phase {phase}: Diff has __main__ guard verified")
    else:
        print(f"Phase {phase}: Diff missing guard: {actual_diff}")
        all_matched = False

print("Overall match:", all_matched)
