import os
import hashlib

def main():
    scripts = [f"trading_system/scripts/benchmark_phase{p}_quant_performance.py" for p in range(25, 40)]
    for s in scripts:
        with open(s, "r", encoding="utf-8") as f:
            lines = f.readlines()
        main_line = None
        write_lines = []
        for idx, l in enumerate(lines, 1):
            if 'if __name__' in l:
                main_line = idx
            if "open(" in l and ('"w"' in l or "'w'" in l):
                write_lines.append(idx)
        print(f"{s}: main at line {main_line}, writes at lines {write_lines}")

if __name__ == "__main__":
    main()
