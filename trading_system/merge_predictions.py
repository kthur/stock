#!/usr/bin/env python3
"""Merge per-market prediction files into unified result files.

Each strategy writes files like: surge_predictions_KOSPI.txt
This script merges them into: surge_predictions.txt
"""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ALL_31_STRATEGIES = [
    'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
    'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation',
    'event_driven', 'mq_factor', 'iv_skew', 'order_flow',
    'short_term_reversal', 'arm_factor', 'card_factor', 'latr_factor',
    'inst_foreign_sector', 'supply_chain', 'sentiment', 'factor_neutralized',
    'vol_target', 'microstructure', 'accruals_quality', 'short_squeeze',
    'valueup_catalyst', 'trend_efficiency', 'gamma_squeeze', 'insider_buying',
    'darkpool', 'earnings_tone_drift'
]
_STRATEGY_COUNT = len(ALL_31_STRATEGIES)

KNOWN_MARKETS = [
    "SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ",
    "CHINA_SSE", "CHINA_SZSE", "JAPAN_TSE", "INDIA_NSE",
    "EUROPE_STOXX", "VIETNAM_HOSE", "TAIWAN_TWSE",
    "AUSTRALIA_ASX", "BRAZIL_B3", "HKEX", "SINGAPORE_SGX", "CANADA_TSX"
]



def get_file_content(path: Path) -> str:
    if not path.exists():
        return ""
    # Try reading as UTF-8 first, ignoring decoding errors to avoid breaking execution
    try:
        return path.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n")
    except Exception:
        try:
            return path.read_text(encoding="cp949", errors="ignore").replace("\r\n", "\n")
        except Exception:
            return ""




def _first_available(target_dirs: dict, suffix: str) -> str:
    """Return content of the first existing file with given suffix."""
    for market, path in target_dirs.items():
        content = get_file_content(path / suffix.format(market=market))
        if content:
            return content
    return ""


def merge_pipeline_result(result_dir: Path, target_dirs: dict) -> None:
    merged_path = result_dir / "pipeline_result.txt"
    print(f"Merging pipeline_result.txt -> {merged_path}")

    lines_written = 0
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
                if "데이터 없음" in line or "No data" in line:
                    continue
                out.write(line + "\n")
                lines_written += 1

        if lines_written == 0:
            out.write("데이터 없음\n")


def merge_ensemble_predictions(result_dir: Path, target_dirs: dict) -> None:
    merged_path = result_dir / "ensemble_predictions.txt"
    print(f"Merging ensemble_predictions.txt -> {merged_path}")

    header = ""
    for market, path in target_dirs.items():
        file_path = path / f"ensemble_predictions_{market}.txt"
        if file_path.exists():
            content = get_file_content(file_path)
            idx = content.find("=========================================")
            if idx != -1:
                header = content[:idx].strip() + "\n\n"
                break

    if not header:
        from datetime import timezone, timedelta
        kst_now = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')
        header = f"=== Dynamic Multi-Strategy Ensemble Predictions ({_STRATEGY_COUNT} Strategies) ===\nDate: {kst_now}\n\n"

    sections_written = 0
    with open(merged_path, "w", encoding="utf-8") as out:
        out.write(header)

        for market in KNOWN_MARKETS:
            mkt_dir = target_dirs.get(market)
            if mkt_dir is None:
                continue
            file_path = mkt_dir / f"ensemble_predictions_{market}.txt"
            if not file_path.exists():
                file_path = result_dir / f"ensemble_predictions_{market}.txt"
            if not file_path.exists():
                continue

            content = get_file_content(file_path)
            if "데이터 없음" in content or "No data" in content:
                continue
            # Extract section — flexible whitespace and newline handling
            pattern = rf"(==={{10,}}\s*\n\[{re.escape(market)}\][^\n]*\n==={{10,}}\s*\n.*?)(?=\n==={{10,}}|\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                out.write(match.group(1).strip() + "\n\n")
                sections_written += 1
            else:
                # Fallback matching with relaxed newlines
                normalized_content = content.replace("\r\n", "\n")
                match = re.search(pattern, normalized_content, re.DOTALL)
                if match:
                    out.write(match.group(1).strip() + "\n\n")
                    sections_written += 1
                else:
                    print(f"  Warning: Could not extract section [{market}] from {file_path}")

        if sections_written == 0:
            out.write("데이터 없음\n")


def merge_surge_predictions(result_dir: Path, target_dirs: dict) -> None:
    merged_path = result_dir / "surge_predictions.txt"
    print(f"Merging surge_predictions.txt -> {merged_path}")

    header = ""
    for market, path in target_dirs.items():
        file_path = path / f"surge_predictions_{market}.txt"
        if file_path.exists():
            content = get_file_content(file_path)
            # Header ends before first ======= block
            idx = content.find("=" * 10)
            if idx != -1:
                header = content[:idx].strip() + "\n\n"
                break

    if not header:
        header = f"=== Surge Detection Results (>= 20% return) ===\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    horizons = ["1", "3", "5", "20"]
    markets = [m for m in KNOWN_MARKETS if m in target_dirs] or KNOWN_MARKETS

    sections_written = 0
    buffer = [header]

    for hz in horizons:
        for mkt in markets:
            mkt_dir = target_dirs.get(mkt)
            if mkt_dir is None:
                continue
            file_path = mkt_dir / f"surge_predictions_{mkt}.txt"
            if not file_path.exists():
                file_path = result_dir / "surge_predictions.txt"
            if not file_path.exists():
                continue

            content = get_file_content(file_path)
            if "데이터 없음" in content or "No data" in content:
                continue

            # Match: ====...\n[Nd일] MARKET Top ...\n====...\n<body>
            pattern = (
                rf"(==={{10,}}\s*\n"
                rf"\[{re.escape(hz)}일\]\s+{re.escape(mkt)}\s+Top[^\n]*\n"
                rf"==={{10,}}\s*\n"
                rf".*?)"
                rf"(?=\n==={{10,}}|\Z)"
            )
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                # Fallback to normalized content
                normalized_content = content.replace("\r\n", "\n")
                match = re.search(pattern, normalized_content, re.DOTALL)

            if match:
                buffer.append(match.group(1).strip() + "\n\n")
                sections_written += 1
            else:
                print(f"  Warning: [{hz}일] {mkt} section not found in {file_path.name}")

    if sections_written == 0:
        buffer.append("데이터 없음\n")

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write("".join(buffer))




def merge_vcp_ml_predictions(result_dir: Path, target_dirs: dict) -> None:
    merged_path = result_dir / "vcp_ml_predictions.txt"
    print(f"Merging vcp_ml_predictions.txt -> {merged_path}")

    header = ""
    for market, path in target_dirs.items():
        file_path = path / f"vcp_ml_predictions_{market}.txt"
        if file_path.exists():
            content = get_file_content(file_path)
            # Header is everything before the first [Nd일] line
            idx = re.search(r"^\[", content, re.MULTILINE)
            if idx:
                header = content[: idx.start()].strip() + "\n\n"
                break

    if not header:
        header = f"=== VCP ML Surge Predictions ===\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    horizons = ["1", "3", "5", "20"]
    markets = [m for m in KNOWN_MARKETS if m in target_dirs] or KNOWN_MARKETS

    sections_written = 0
    buffer = [header]

    # Pre-read contents to avoid open('w') truncation bug
    contents_cache = {}
    for mkt in markets:
        mkt_dir = target_dirs.get(mkt)
        if mkt_dir is None:
            continue
        file_path = mkt_dir / f"vcp_ml_predictions_{mkt}.txt"
        if not file_path.exists():
            file_path = result_dir / f"vcp_ml_predictions_{mkt}.txt"
        if not file_path.exists():
            file_path = result_dir / "vcp_ml_predictions.txt"
        if file_path.exists():
            contents_cache[mkt] = get_file_content(file_path)

    for hz in horizons:
        for mkt in markets:
            content = contents_cache.get(mkt, "")
            if not content or "데이터 없음" in content or "No data" in content:
                continue

            # Actual format: "[1일] KOSPI TOP 5\n  1. ...\n\n"
            # Also handles: "[1일] KOSPI - (no symbols)\n\n"
            pattern = (
                rf"(\[{re.escape(hz)}일\]\s+{re.escape(mkt)}[^\n]*\n"
                rf"(?:[ \t]+[^\n]+\n)*)"
            )
            match = re.search(pattern, content)
            if match:
                buffer.append(match.group(1).rstrip() + "\n\n")
                sections_written += 1
            else:
                print(f"  Warning: [{hz}일] {mkt} section not found in content cache")

    if sections_written == 0:
        buffer.append("데이터 없음\n")

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write("".join(buffer))


def merge_vcp_patterns(result_dir: Path, target_dirs: dict) -> None:
    merged_path = result_dir / "vcp_patterns.txt"
    print(f"Merging vcp_patterns.txt -> {merged_path}")

    sections = []
    total_patterns = 0
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Pre-read contents to avoid open('w') truncation bug
    contents_cache = {}
    markets = [m for m in KNOWN_MARKETS if m in target_dirs] or KNOWN_MARKETS
    for mkt in markets:
        path = target_dirs.get(mkt)
        if not path:
            continue
        file_path = path / f"vcp_patterns_{mkt}.txt"
        if not file_path.exists():
            file_path = result_dir / f"vcp_patterns_{mkt}.txt"
        if not file_path.exists():
            file_path = result_dir / "vcp_patterns.txt"
        if file_path.exists():
            contents_cache[mkt] = get_file_content(file_path)

    for mkt in markets:
        content = contents_cache.get(mkt, "")
        if not content or "데이터 없음" in content or "No data" in content:
            continue
        m = re.search(r"Date:\s*(.+)", content)
        if m:
            date_str = m.group(1).strip()

        pattern = rf"(--- {re.escape(mkt)}.*?\n.*?)(?=\n--- |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            sect_text = match.group(1).strip()
            sections.append(sect_text)
            cnt = len(re.findall(r"^\s*\d+\.\s+\[", sect_text, re.MULTILINE))
            total_patterns += cnt

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write("=== VCP (Volatility Contraction Pattern) Results ===\n")
        out.write(f"Date: {date_str}\n")
        out.write(f"Total VCP patterns found: {total_patterns}\n\n")
        if not sections:
            out.write("데이터 없음\n")
        else:
            for sect in sections:
                out.write(sect + "\n\n")


def merge_lead_lag_predictions(result_dir: Path, target_dirs: dict) -> None:
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
            idx_leaders = content.find("--- Leaders with highest today return ---")
            if idx_leaders != -1:
                leaders_sect = content[idx_leaders:].strip() + "\n\n"
                break

    if not header:
        header = f"=== Lead-Lag Surge Predictions ===\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    sections_written = 0
    with open(merged_path, "w", encoding="utf-8") as out:
        out.write(header)

        markets = [m for m in KNOWN_MARKETS if m in target_dirs] or KNOWN_MARKETS
        for mkt in markets:
            mkt_dir = target_dirs.get(mkt)
            if mkt_dir is None:
                continue
            file_path = mkt_dir / f"lead_lag_predictions_{mkt}.txt"
            if not file_path.exists():
                file_path = result_dir / f"lead_lag_predictions_{mkt}.txt"
            if not file_path.exists():
                continue

            content = get_file_content(file_path)
            if "데이터 없음" in content or "No data" in content:
                continue

            # Actual format: "--- KOSPI Top 20 ---\n  1. ...\n"
            pattern = rf"(--- {re.escape(mkt)}\s+Top\s+\d+\s*---\n.*?)(?=\n--- |\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                out.write(match.group(1).strip() + "\n\n")
                sections_written += 1
            else:
                print(f"  Warning: {mkt} Top section not found in {file_path.name}")

        if sections_written == 0:
            out.write("데이터 없음\n\n")

        if leaders_sect:
            out.write(leaders_sect)


def merge_generic_strategy_files(result_dir: Path, target_dirs: dict, filename: str, title: str) -> None:
    merged_path = result_dir / filename
    print(f"Merging {filename} -> {merged_path}")

    from datetime import timezone, timedelta
    kst_now = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')

    stem = Path(filename).stem

    # Pre-read source content BEFORE opening output file to avoid
    # self-referencing bug where fallback reads the same file being truncated.
    data_lines: list[str] = []
    all_fallbacks_self_ref = True

    for market, path in target_dirs.items():
        file_path = path / f"{stem}_{market}.txt"
        if not file_path.exists():
            # Check if fallback would self-reference (same as output file)
            if (path / filename) != merged_path:
                all_fallbacks_self_ref = False
            continue

        all_fallbacks_self_ref = False
        content = get_file_content(file_path)
        for line in content.splitlines():
            if line.startswith("===") or line.startswith("Date:") or line.startswith("Total symbols:") or not line.strip():
                continue
            if "데이터 없음" in line or "No data" in line:
                continue
            data_lines.append(line + "\n")

    # If all per-market files are missing and the only fallback is self-referencing,
    # leave the original pipeline file untouched (nothing to merge).
    if all_fallbacks_self_ref:
        if merged_path.exists():
            print(f"  Only self-referencing fallbacks available; leaving {filename} untouched.")
            return

    if not data_lines:
        data_lines.append("데이터 없음\n")

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write(f"=== {title} ===\n")
        out.write(f"Date: {kst_now}\n\n")
        out.writelines(data_lines)


def merge_portfolio_allocation(result_dir: Path, target_dirs: dict) -> None:
    """Merge per-market portfolio allocation files into one unified allocation file.

    The daily GHA pipeline runs per-market, so each market job writes its own
    portfolio_allocation_{MARKET}.txt (each sized against the full portfolio
    capital). This merge combines all market allocations into a single
    portfolio_allocation.txt, properly re-normalizing weights against the global
    target max allocation and total capital to prevent multi-market weight overflow,
    and recording mathematically consistent Allocated Capital and Remaining Cash.
    """
    merged_path = result_dir / "portfolio_allocation.txt"

    row_re = re.compile(
        r"^\s*(\d+)\s+(\S+)\s+(.+?)\s+(KOSPI|KOSDAQ|SP500|NASDAQ|RUSSELL2000)"
        r"\s+([-\d.]+%|nan%|NaN%|None%)\s+([-\d.]+%|nan%|NaN%|None%)"
        r"\s+([-\d.]+%|nan%|NaN%|None%)\s+([\d,]+|\S+)$"
    )

    all_rows: list[tuple] = []  # (weight_pct, symbol, name, market, exp_ret, vol, weight_str, amount_str)
    total_capital = "100,000,000 KRW"
    target_horizon = "20d"
    max_alloc = "85.0%"
    regime = "SIDEWAYS"
    date_str = ""

    for market, path in target_dirs.items():
        file_path = path / f"portfolio_allocation_{market}.txt"
        if not file_path.exists():
            continue
        content = get_file_content(file_path)
        if not content or "데이터 없음" in content or "No data" in content:
            continue
        for line in content.splitlines():
            m = re.match(r"Total Capital:\s*(.+)", line)
            if m:
                total_capital = m.group(1).strip()
            m = re.match(r"Target Horizon:\s*(.+)", line)
            if m:
                target_horizon = m.group(1).strip()
            m = re.match(r"Date:\s*(.+)", line)
            if m and not date_str:
                date_str = m.group(1).strip()
            m = re.match(r"Current Market Regime Detected:\s*([A-Za-z0-9_]+)", line)
            if m:
                regime = m.group(1).strip()
            m = re.match(r"Maximum Total Allocation Allowed:\s*(.+)", line)
            if m:
                max_alloc = m.group(1).strip()
            m = row_re.match(line)
            if m:
                w_str = m.group(7).replace("%", "")
                try:
                    w_pct = float(w_str)
                except ValueError:
                    continue
                all_rows.append((w_pct, m.group(2), m.group(3).strip(), m.group(4).strip(),
                                 m.group(5), m.group(6), m.group(7), m.group(8)))

    if not all_rows:
        print("  No per-market portfolio allocation files found; skipping merge.")
        return

    # Deduplicate by symbol (keep the highest weight) — a symbol must not appear
    # twice in the final allocation, e.g. when per-market fallbacks overlap.
    dedup: dict[str, tuple] = {}
    for row in all_rows:
        sym = row[1]
        if sym not in dedup or row[0] > dedup[sym][0]:
            dedup[sym] = row
    dedup_rows = sorted(dedup.values(), key=lambda r: r[0], reverse=True)

    # Parse total capital numeric value
    cap_num_match = re.search(r"[\d,]+", total_capital)
    total_cap_num = float(cap_num_match.group().replace(",", "")) if cap_num_match else 100_000_000.0

    # Parse target max allocation percentage
    alloc_pct_match = re.search(r"([\d.]+)%", max_alloc)
    target_max_alloc_pct = float(alloc_pct_match.group(1)) if alloc_pct_match else 85.0
    target_max_alloc_pct = max(5.0, min(100.0, target_max_alloc_pct))

    # Re-normalize weights across all markets to ensure total allocation <= target_max_alloc_pct
    raw_sum_pct = sum(r[0] for r in dedup_rows)
    norm_rows: list[tuple] = []

    if raw_sum_pct > target_max_alloc_pct and raw_sum_pct > 0:
        scale = target_max_alloc_pct / raw_sum_pct
        for r in dedup_rows:
            scaled_w_pct = r[0] * scale
            scaled_amount = int(round(total_cap_num * (scaled_w_pct / 100.0)))
            norm_rows.append((
                scaled_w_pct,
                r[1],  # symbol
                r[2],  # name
                r[3],  # market
                r[4],  # exp_ret
                r[5],  # vol
                f"{scaled_w_pct:.2f}%",
                f"{scaled_amount:,}"
            ))
    else:
        for r in dedup_rows:
            scaled_w_pct = r[0]
            scaled_amount = int(round(total_cap_num * (scaled_w_pct / 100.0)))
            norm_rows.append((
                scaled_w_pct,
                r[1],
                r[2],
                r[3],
                r[4],
                r[5],
                f"{scaled_w_pct:.2f}%",
                f"{scaled_amount:,}"
            ))

    norm_rows = sorted(norm_rows, key=lambda r: r[0], reverse=True)
    allocated_pct = sum(r[0] for r in norm_rows)
    allocated_amount = sum(float(r[7].replace(",", "")) for r in norm_rows)
    remaining_pct = max(0.0, 100.0 - allocated_pct)
    remaining_amount = max(0.0, total_cap_num - allocated_amount)

    from datetime import timezone, timedelta
    kst_now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST")
    header_date = date_str or kst_now

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write("=== Portfolio Allocation Recommendations (Ensemble HRP, Merged Across Markets) ===\n")
        out.write(f"Date: {header_date}\n")
        out.write(f"Total Capital: {total_capital}\n")
        out.write(f"Target Horizon: {target_horizon}\n\n")
        out.write(f"Current Market Regime Detected: {regime}\n")
        out.write(f"Maximum Total Allocation Allowed: {max_alloc}\n\n")
        out.write(f"{'No.':<4} {'Symbol':<12} {'Name':<20} {'Market':<14} {'Return':<10} {'Volatility':<12} {'Weight':<10} {'Amount':<15}\n")
        out.write("-" * 96 + "\n")
        for rank, (w_pct, sym, name, mkt, exp_ret, vol, weight, amount) in enumerate(norm_rows, 1):
            out.write(f"{rank:<4} {sym:<12} {name[:18]:<20} {mkt:<14} {exp_ret:>10} {vol:>12} {weight:>10} {amount:>15}\n")
        out.write("-" * 96 + "\n")
        out.write(f"Allocated Capital: {allocated_pct:.2f}% ({int(allocated_amount):>14,d})\n")
        out.write(f"Remaining Cash   : {remaining_pct:.2f}% ({int(remaining_amount):>14,d})\n")
    print(f"Merged portfolio allocation -> {merged_path} ({len(norm_rows)} rows, Allocated: {allocated_pct:.2f}%, Cash: {remaining_pct:.2f}%)")


def merge_backtest_summary(result_dir: Path, target_dirs: dict) -> None:
    """Merge per-market backtest_summary.json into the unified result directory.

    Picks the summary with real realized metrics when available; otherwise keeps
    the most recent insufficient-data summary so the dashboard never fabricates.
    """
    merged_path = result_dir / "backtest_summary.json"
    candidates = []
    for market, path in target_dirs.items():
        fp = path / f"backtest_summary_{market}.json"
        if not fp.exists():
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        data["market"] = market
        candidates.append((fp, data))

    if not candidates:
        print("  No per-market backtest summaries found; skipping merge.")
        return

    def _score(d):
        strategies = d.get("strategies") or {}
        return (1 if strategies else 0, d.get("updated_at", ""))

    candidates.sort(key=lambda c: _score(c[1]), reverse=True)
    best_path, best_data = candidates[0]

    try:
        merged_path.write_text(
            json.dumps(best_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Merged backtest summary -> {merged_path} (source: {best_path.name})")
    except Exception as e:
        print(f"  Warning: failed to write merged backtest summary: {e}")


def merge_coverage_report(result_dir: Path, target_dirs: dict) -> None:
    """Merge per-market strategy data coverage reports into the unified report.

    The pipeline only writes the market-suffixed coverage report (e.g.
    strategy_data_coverage_report_KOSPI.txt) per market, so the main file must
    be reconstructed from those; otherwise a stale committed file could leak
    into the release.
    """
    merged_path = result_dir / "strategy_data_coverage_report.txt"
    print(f"Merging strategy_data_coverage_report.txt -> {merged_path}")

    sections: list[str] = []
    for market, path in target_dirs.items():
        file_path = path / f"strategy_data_coverage_report_{market}.txt"
        content = get_file_content(file_path)
        if not content:
            continue
        lines = [
            ln
            for ln in content.splitlines()
            if ln.strip() and not ln.startswith("===")
        ]
        if not lines:
            continue
        sections.append(f"[{market}]\n" + "\n".join(lines))

    if not sections:
        if merged_path.exists():
            print("  No per-market coverage reports found; leaving existing file untouched.")
            return
        sections.append("데이터 없음\n")

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write(f"=== {_STRATEGY_COUNT}-Strategy Data Coverage & Missingness Report ===\n")
        out.write(f"Date: {datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')}\n\n")
        out.write("\n\n".join(sections) + "\n")


def main():
    base_dir = Path(__file__).resolve().parent
    result_dir = base_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)

    markets = KNOWN_MARKETS
    target_dirs: dict[str, Path] = {}
    for m in markets:
        # Prefer market-specific split directory; fall back to unified result dir
        split_path = base_dir / f"result_{m}"
        if split_path.exists() and any(split_path.iterdir()):
            target_dirs[m] = split_path
        elif result_dir.exists():
            # Check if market-suffixed files exist inside result_dir itself
            probe = result_dir / f"surge_predictions_{m}.txt"
            if probe.exists():
                target_dirs[m] = result_dir

    if not target_dirs:
        print("Warning: No per-market result directories found. Checking result/ for suffix files.")
        for m in markets:
            probe = result_dir / f"pipeline_result_{m}.txt"
            if probe.exists():
                target_dirs[m] = result_dir

    print(f"Target directories: { {k: str(v) for k, v in target_dirs.items()} }")

    merge_pipeline_result(result_dir, target_dirs)
    merge_ensemble_predictions(result_dir, target_dirs)
    merge_surge_predictions(result_dir, target_dirs)
    merge_vcp_ml_predictions(result_dir, target_dirs)
    merge_vcp_patterns(result_dir, target_dirs)
    merge_lead_lag_predictions(result_dir, target_dirs)
    merge_coverage_report(result_dir, target_dirs)
    merge_portfolio_allocation(result_dir, target_dirs)
    merge_backtest_summary(result_dir, target_dirs)

    # Merge remaining strategy individual outputs (all 31 strategies)
    merge_generic_strategy_files(result_dir, target_dirs, "lstm_predictions.txt", "Strict Causal LSTM Time-Series Deep Learning Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "sector_predictions.txt", "Sector Rotation Momentum & Macro Sensitivity Report")
    merge_generic_strategy_files(result_dir, target_dirs, "rim_predictions.txt", "RIM Intrinsic Valuation Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "event_driven_predictions.txt", "Event-Driven Disclosure Catalyst Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "mq_factor_predictions.txt", "Momentum Quality (MQ) Factor Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "iv_skew_predictions.txt", "Options Put/Call IV Skew Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "order_flow_predictions.txt", "Order Flow Imbalance (MFI) Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "short_term_reversal_predictions.txt", "Short-Term Mean Reversal Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "stat_arb_predictions.txt", "Statistical Arbitrage Cointegration Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "arm_factor_predictions.txt", "Analyst Revision Momentum (ARM) Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "card_factor_predictions.txt", "Cross-Asset Regime Divergence (CARD) Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "latr_factor_predictions.txt", "Liquidity-Adjusted Tail Risk (LATR) Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "inst_foreign_sector_predictions.txt", "Institutional & Foreign Sector Flow Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "supply_chain_predictions.txt", "Supply Chain Lead-Lag Momentum Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "sentiment_predictions.txt", "NLP & FinBERT Sentiment Catalyst Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "factor_neutralized_predictions.txt", "Multi-Factor Style Neutralized Pure Alpha Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "vol_target_predictions.txt", "Dynamic Volatility Targeting Risk Parity Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "microstructure_predictions.txt", "Order Book Microstructure Imbalance Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "accruals_quality_predictions.txt", "Accruals Quality Accounting Anomaly Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "short_squeeze_predictions.txt", "Short Interest & Squeeze Catalyst Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "valueup_catalyst_predictions.txt", "Value-Up & Shareholder Yield Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "trend_efficiency_predictions.txt", "Kaufman Trend Efficiency Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "gamma_squeeze_predictions.txt", "Options Gamma Squeeze Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "insider_buying_predictions.txt", "Executive & Insider Buying Catalyst Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "hft_order_flow_predictions.txt", "HFT Order Flow & Dark Pool Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "earnings_tone_drift_predictions.txt", "Earnings Tone Drift NLP Quant Predictions")

    print("All prediction files successfully merged.")


if __name__ == "__main__":
    main()
