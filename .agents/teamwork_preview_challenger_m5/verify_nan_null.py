import os
import re
import sys

def check_nan_null(file_path):
    if not os.path.exists(file_path):
        return {"exists": False, "total_lines": 0, "nan_count": 0, "null_count": 0, "matches": []}
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    nan_patterns = re.compile(r'\b(nan|NaN|NAN|-nan)\b')
    null_patterns = re.compile(r'\b(null|Null|NULL|None|N/A|undefined)\b')
    
    matches = []
    nan_count = 0
    null_count = 0
    
    for i, line in enumerate(lines, 1):
        line_clean = line.strip()
        if nan_patterns.search(line_clean):
            nan_count += 1
            matches.append(f"Line {i}: {line_clean}")
        elif null_patterns.search(line_clean):
            # Check if 'None' or 'N/A' is actual missing data or part of legitimate string
            # e.g., 'None' in header/text or actual null value
            null_count += 1
            matches.append(f"Line {i}: {line_clean}")
            
    return {
        "exists": True,
        "total_lines": len(lines),
        "nan_count": nan_count,
        "null_count": null_count,
        "matches": matches
    }

target_files = [
    "pipeline_result.txt",
    "surge_predictions.txt",
    "lead_lag_predictions.txt",
    "vcp_patterns.txt",
    "vcp_ml_predictions.txt",
    "ensemble_predictions.txt"
]

directories = [
    "trading_system",
    "trading_system/result"
]

all_passed = True

print("="*80)
print("NaN / NULL RATE VERIFICATION Across Prediction Files")
print("="*80)

for d in directories:
    print(f"\nDirectory: {d}")
    for fname in target_files:
        fpath = os.path.join(d, fname)
        res = check_nan_null(fpath)
        if not res["exists"]:
            print(f"  [MISSING] {fname} (path: {fpath})")
            continue
        
        total = res["total_lines"]
        nans = res["nan_count"]
        nulls = res["null_count"]
        bad = nans + nulls
        rate = (bad / total * 100) if total > 0 else 0.0
        
        status = "PASS" if bad == 0 else "FAIL"
        if bad > 0:
            all_passed = False
            
        print(f"  [{status}] {fname} - Total lines: {total}, NaNs: {nans}, Nulls: {nulls}, Invalid Rate: {rate:.2f}%")
        if bad > 0:
            for m in res["matches"][:5]:
                print(f"      {m}")

# Also check market-specific result files in trading_system/result/
if os.path.exists("trading_system/result"):
    print("\nDirectory: trading_system/result (market-specific split files)")
    for fname in os.listdir("trading_system/result"):
        if fname.endswith(".txt") and fname not in target_files:
            fpath = os.path.join("trading_system/result", fname)
            res = check_nan_null(fpath)
            total = res["total_lines"]
            nans = res["nan_count"]
            nulls = res["null_count"]
            bad = nans + nulls
            rate = (bad / total * 100) if total > 0 else 0.0
            status = "PASS" if bad == 0 else "FAIL"
            if bad > 0:
                all_passed = False
            print(f"  [{status}] {fname} - Total lines: {total}, NaNs: {nans}, Nulls: {nulls}, Invalid Rate: {rate:.2f}%")

print("="*80)
if all_passed:
    print("VERIFICATION RESULT: 0% NaN/Null Rate - PASSED 100%")
else:
    print("VERIFICATION RESULT: FAILED - NaN/Null found in outputs!")
print("="*80)
sys.exit(0 if all_passed else 1)

