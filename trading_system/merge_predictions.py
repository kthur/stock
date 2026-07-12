#!/usr/bin/env python3
import re
from datetime import datetime
from pathlib import Path

def get_file_content(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")

def merge_pipeline_result(result_dir: Path, target_dirs: dict[str, Path]) -> None:
    merged_path = result_dir / "pipeline_result.txt"
    print(f"Merging pipeline_result.txt -> {merged_path}")

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write("=== Full Pipeline Inference Results (Merged) ===\n")
        out.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        for market, path in target_dirs.items():
            file_path = path / f"pipeline_result_{market}.txt"
            if not file_path.exists():
                print(f"  Warning: {file_path} not found, skipping.")
                continue

            content = get_file_content(file_path)
            for line in content.splitlines():
                if line.startswith("===") or line.startswith("Date:") or line.startswith("Total symbols:") or not line.strip():
                    continue
                out.write(line + "\n")

def merge_ensemble_predictions(result_dir: Path, target_dirs: dict[str, Path]) -> None:
    merged_path = result_dir / "ensemble_predictions.txt"
    print(f"Merging ensemble_predictions.txt -> {merged_path}")

    # 1. Read header from first available file
    header = ""
    for market, path in target_dirs.items():
        file_path = path / f"ensemble_predictions_{market}.txt"
        if file_path.exists():
            content = get_file_content(file_path)
            # Find the header section before the first recommendation list
            idx = content.find("=========================================")
            if idx != -1:
                header = content[:idx].strip() + "\n\n"
                break

    if not header:
        header = f"=== Dynamic Multi-Strategy Ensemble Predictions ===\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write(header)

        for market in ["KOSPI", "KOSDAQ", "KONEX", "SP500"]:
            mkt_dir = target_dirs.get(market)
            if mkt_dir is None:
                continue
            file_path = mkt_dir / f"ensemble_predictions_{market}.txt"
            if not file_path.exists():
                print(f"  Warning: {file_path} not found, skipping recommendations for {market}.")
                continue

            content = get_file_content(file_path)
            # Extract section
            pattern = rf"(={{10,}}\s*\n\[{market}\][^\n]*\n={{10,}}\s*\n.*?)(?=\n={{10,}}\s*\n\[|\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                out.write(match.group(1).strip() + "\n\n")
            else:
                print(f"  Warning: Could not extract section [{market}] from {file_path}")

def merge_surge_predictions(result_dir: Path, target_dirs: dict[str, Path]) -> None:
    merged_path = result_dir / "surge_predictions.txt"
    print(f"Merging surge_predictions.txt -> {merged_path}")

    header = ""
    for market, path in target_dirs.items():
        file_path = path / f"surge_predictions_{market}.txt"
        if file_path.exists():
            content = get_file_content(file_path)
            idx = content.find("============================================================")
            if idx != -1:
                header = content[:idx].strip() + "\n\n"
                break

    if not header:
        header = f"=== Surge Detection Results (>= 20% return) ===\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write(header)

        horizons = ["1일", "3일", "5일", "20일"]
        markets = ["KOSPI", "KOSDAQ", "KONEX", "SP500"]

        for hz in horizons:
            for mkt in markets:
                mkt_dir = target_dirs.get(mkt)
                if mkt_dir is None:
                    continue
                file_path = mkt_dir / f"surge_predictions_{mkt}.txt"
                if not file_path.exists():
                    continue

                content = get_file_content(file_path)
                pattern = rf"(={{10,}}\s*\n\[{hz}\]\s+{mkt}\s+Top[^\n]*\n={{10,}}\s*\n.*?)(?=\n={{10,}}\s*\n\[|\Z)"
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    out.write(match.group(1).strip() + "\n\n")

def merge_vcp_ml_predictions(result_dir: Path, target_dirs: dict[str, Path]) -> None:
    merged_path = result_dir / "vcp_ml_predictions.txt"
    print(f"Merging vcp_ml_predictions.txt -> {merged_path}")

    header = ""
    for market, path in target_dirs.items():
        file_path = path / f"vcp_ml_predictions_{market}.txt"
        if file_path.exists():
            content = get_file_content(file_path)
            idx = content.find("[1일]")
            if idx != -1:
                header = content[:idx].strip() + "\n\n"
                break

    if not header:
        header = f"=== VCP ML Surge Predictions ===\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write(header)

        horizons = ["1일", "3일", "5일", "20일"]
        markets = ["KOSPI", "KOSDAQ", "KONEX", "SP500"]

        for hz in horizons:
            for mkt in markets:
                mkt_dir = target_dirs.get(mkt)
                if mkt_dir is None:
                    continue
                file_path = mkt_dir / f"vcp_ml_predictions_{mkt}.txt"
                if not file_path.exists():
                    continue

                content = get_file_content(file_path)
                pattern = rf"(\[{hz}\]\s+{mkt}\s+TOP[^\n]*\n.*?)(?=\n\[|\Z)"
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    out.write(match.group(1).strip() + "\n\n")

def merge_vcp_patterns(result_dir: Path, target_dirs: dict[str, Path]) -> None:
    merged_path = result_dir / "vcp_patterns.txt"
    print(f"Merging vcp_patterns.txt -> {merged_path}")

    sections = []
    total_patterns = 0
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')

    for mkt in ["KOSPI", "KOSDAQ", "KONEX", "SP500"]:
        path = target_dirs.get(mkt)
        if not path:
            continue
        file_path = path / f"vcp_patterns_{mkt}.txt"
        if not file_path.exists():
            continue

        content = get_file_content(file_path)
        # Parse date from file
        m = re.search(r"Date:\s*(.+)", content)
        if m:
            date_str = m.group(1).strip()

        pattern = rf"(--- {mkt} ---\n.*?)(?=\n--- |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            sect_text = match.group(1).strip()
            sections.append(sect_text)
            # Count patterns
            cnt = len(re.findall(r"^\s*\d+\.\s+\[", sect_text, re.MULTILINE))
            total_patterns += cnt

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write("=== VCP (Volatility Contraction Pattern) Results ===\n")
        out.write(f"Date: {date_str}\n")
        out.write(f"Total VCP patterns found: {total_patterns}\n\n")
        for sect in sections:
            out.write(sect + "\n\n")

def merge_lead_lag_predictions(result_dir: Path, target_dirs: dict[str, Path]) -> None:
    merged_path = result_dir / "lead_lag_predictions.txt"
    print(f"Merging lead_lag_predictions.txt -> {merged_path}")

    header = ""
    leaders_sect = ""
    for market, path in target_dirs.items():
        file_path = path / f"lead_lag_predictions_{market}.txt"
        if file_path.exists():
            content = get_file_content(file_path)
            idx = content.find("---")
            if idx != -1:
                header = content[:idx].strip() + "\n\n"
            # Get leaders section from first file containing it
            idx_leaders = content.find("--- Leaders with highest today return ---")
            if idx_leaders != -1:
                leaders_sect = content[idx_leaders:].strip() + "\n\n"
                break

    if not header:
        header = f"=== Lead-Lag Surge Predictions ===\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write(header)

        for mkt in ["KOSPI", "KOSDAQ", "KONEX", "SP500"]:
            mkt_dir = target_dirs.get(mkt)
            if mkt_dir is None:
                continue
            file_path = mkt_dir / f"lead_lag_predictions_{mkt}.txt"
            if not file_path.exists():
                continue

            content = get_file_content(file_path)
            pattern = rf"(--- {mkt}\s+Top\s+\d+\s*---\n.*?)(?=\n--- |\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                out.write(match.group(1).strip() + "\n\n")

        if leaders_sect:
            out.write(leaders_sect)

def main():
    base_dir = Path(__file__).resolve().parent
    result_dir = base_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)

    # We will search for target dirs under base_dir (which is trading_system/)
    # GHA merge job runs in the root directory, so the script is at trading_system/merge_predictions.py
    # and results are checked out / downloaded under trading_system/result_SP500/ etc.
    markets = ["SP500", "KOSPI", "KOSDAQ", "KONEX"]
    target_dirs = {}
    for m in markets:
        # Check standard path used by download action: trading_system/result_MARKET
        path = base_dir / f"result_{m}"
        if path.exists():
            target_dirs[m] = path
        else:
            # Fallback to result/ if files were downloaded directly into result/ (e.g. local testing)
            target_dirs[m] = result_dir

    print(f"Target directories identified: { {k: str(v.resolve()) for k, v in target_dirs.items()} }")

    merge_pipeline_result(result_dir, target_dirs)
    merge_ensemble_predictions(result_dir, target_dirs)
    merge_surge_predictions(result_dir, target_dirs)
    merge_vcp_ml_predictions(result_dir, target_dirs)
    merge_vcp_patterns(result_dir, target_dirs)
    merge_lead_lag_predictions(result_dir, target_dirs)

    print("All prediction files successfully merged.")

if __name__ == "__main__":
    main()
