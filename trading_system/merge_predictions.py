#!/usr/bin/env python3
"""Merge per-market prediction files into unified result files.

Each strategy writes files like: surge_predictions_KOSPI.txt
This script merges them into: surge_predictions.txt
"""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ALL_37_STRATEGIES = [
    'regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml',
    'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation',
    'event_driven', 'mq_factor', 'iv_skew', 'order_flow',
    'short_term_reversal', 'arm_factor', 'card_factor', 'latr_factor',
    'inst_foreign_sector', 'supply_chain', 'sentiment', 'factor_neutralized',
    'vol_target', 'microstructure', 'accruals_quality', 'short_squeeze',
    'valueup_catalyst', 'trend_efficiency', 'gamma_squeeze', 'insider_buying',
    'darkpool', 'earnings_tone_drift', 'cross_asset_spillover',
    'supply_chain_gnn', 'range_expansion_breakout',
    'dual_correction', 'index_rebalance', 'overnight_gap_reversal'
]
ALL_34_STRATEGIES = ALL_37_STRATEGIES
ALL_31_STRATEGIES = ALL_37_STRATEGIES[:31]
_STRATEGY_COUNT = len(ALL_37_STRATEGIES)

KNOWN_MARKETS = [
    "SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ", "KONEX",
    "CHINA_SSE", "CHINA_SZSE", "JAPAN_TSE", "INDIA_NSE",
    "EUROPE_STOXX", "VIETNAM_HOSE", "TAIWAN_TWSE",
    "AUSTRALIA_ASX", "BRAZIL_B3", "HKEX", "SINGAPORE_SGX", "CANADA_TSX",
    "CHINA", "JAPAN", "INDIA", "EUROPE", "VIETNAM", "TAIWAN",
    "AUSTRALIA", "BRAZIL", "SINGAPORE", "CANADA", "US"
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
                if line.startswith("===") or line.startswith("Date:") or line.startswith("Total symbols") or not line.strip():
                    continue
                if "데이터 없음" in line or "No data" in line:
                    continue
                out.write(line + "\n")
                lines_written += 1

        if lines_written == 0:
            out.write("데이터 없음\n")


def _extract_ensemble_market_section(content: str, market: str) -> str:
    """Extract [{market}] section robustly across varying header divider styles and boundaries."""
    if not content or "데이터 없음" in content or "No data" in content:
        return ""

    normalized = content.replace("\r\n", "\n")

    # Primary Pattern: Flexible header divider with === or --- or none, market tag, optional lower divider
    pattern_primary = (
        rf"(?:^[ \t]*[=\-]{{3,}}[^\n]*\n)?"
        rf"^[ \t]*\[{re.escape(market)}\][^\n]*\n"
        rf"(?:^[ \t]*[=\-]{{3,}}[^\n]*\n)?"
        rf"(.*?)"
        rf"(?=\n[ \t]*[=\-]{{3,}}\s*\n\[|\n[ \t]*\[[A-Za-z0-9_]+\]\s+(?:Top|All)|\n--- Data Quality|\n--- Applied|\n--- Executive|\n=== Dynamic|\Z)"
    )
    m = re.search(pattern_primary, normalized, re.DOTALL | re.MULTILINE)
    if m:
        body = m.group(1).strip()
        for footer_marker in ["--- Data Quality", "--- Applied", "--- Executive", "=== Dynamic"]:
            f_idx = body.find(footer_marker)
            if f_idx != -1:
                body = body[:f_idx].strip()
        if body:
            hdr_match = re.search(rf"^[ \t]*(\[{re.escape(market)}\][^\n]*)", m.group(0), re.MULTILINE)
            hdr_text = hdr_match.group(1).strip() if hdr_match else f"[{market}] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)"
            header = f"=========================================\n{hdr_text}\n========================================="
            return f"{header}\n{body}"

    # Secondary Pattern: Line-by-line state machine parser
    lines = normalized.splitlines()
    in_section = False
    captured_lines: list[str] = []
    matched_hdr_text = f"[{market}] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)"
    for line in lines:
        l_str = line.strip()
        if re.match(rf"^\[{re.escape(market)}\](?:\s+(?:Top|All))?", l_str, re.IGNORECASE) or l_str == f"[{market}]":
            in_section = True
            matched_hdr_text = l_str
            continue
        elif in_section:
            if (
                (re.match(r"^\[[A-Za-z0-9_]+\]\s+(?:Top|All)", l_str) and not re.match(rf"^\[{re.escape(market)}\]\s+(?:Top|All)", l_str, re.IGNORECASE))
                or l_str.startswith("--- Data Quality")
                or l_str.startswith("--- Applied")
                or l_str.startswith("--- Executive")
                or l_str.startswith("=== Dynamic")
            ):
                break
            if not captured_lines and l_str.startswith("==="):
                continue
            captured_lines.append(line)

    if captured_lines:
        body = "\n".join(captured_lines).strip()
        for footer_marker in ["--- Data Quality", "--- Applied", "--- Executive", "=== Dynamic"]:
            f_idx = body.find(footer_marker)
            if f_idx != -1:
                body = body[:f_idx].strip()
        if body:
            header = f"=========================================\n{matched_hdr_text}\n========================================="
            return f"{header}\n{body}"

    return ""


def merge_ensemble_predictions(result_dir: Path, target_dirs: dict) -> None:
    merged_path = result_dir / "ensemble_predictions.txt"
    print(f"Merging ensemble_predictions.txt -> {merged_path}")

    header = ""
    # 1. Prefer existing ensemble_predictions.txt if it already has the full weights and executive summary
    existing_merged = result_dir / "ensemble_predictions.txt"
    if existing_merged.exists():
        c_exist = get_file_content(existing_merged)
        idx_exist = c_exist.find("=========================================")
        if idx_exist != -1 and ("--- Applied" in c_exist[:idx_exist] or "--- Executive" in c_exist[:idx_exist] or "[2D Market Regime" in c_exist[:idx_exist]):
            header = c_exist[:idx_exist].strip() + "\n\n"

    # 2. Check individual market files for full weights header
    if not header:
        for market, path in target_dirs.items():
            file_path = path / f"ensemble_predictions_{market}.txt"
            if file_path.exists():
                content = get_file_content(file_path)
                idx = content.find("=========================================")
                if idx != -1 and ("--- Applied" in content[:idx] or "--- Executive" in content[:idx] or "[2D Market Regime" in content[:idx]):
                    header = content[:idx].strip() + "\n\n"
                    break

    # 3. Fallback to basic header from any market file
    if not header:
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
    sections_list: list[str] = []

    markets_to_merge = [m for m in KNOWN_MARKETS if m in target_dirs] or [m for m in target_dirs] or KNOWN_MARKETS

    for market in markets_to_merge:
        mkt_dir = target_dirs.get(market)
        candidate_paths: list[Path] = []
        if mkt_dir is not None:
            candidate_paths.append(mkt_dir / f"ensemble_predictions_{market}.txt")
        candidate_paths.append(result_dir / f"ensemble_predictions_{market}.txt")
        if existing_merged.exists():
            candidate_paths.append(existing_merged)
        for other_m, other_dir in target_dirs.items():
            if other_dir != mkt_dir:
                candidate_paths.append(other_dir / f"ensemble_predictions_{other_m}.txt")

        extracted_section = ""
        for cp in candidate_paths:
            if cp.exists():
                c = get_file_content(cp)
                sect = _extract_ensemble_market_section(c, market)
                if sect:
                    extracted_section = sect
                    break

        if extracted_section:
            sections_list.append(extracted_section)
            sections_written += 1
        else:
            print(f"  Warning: Could not extract section [{market}] from available files")

    with open(merged_path, "w", encoding="utf-8") as out:
        out.write(header)
        if sections_written == 0:
            out.write("데이터 없음\n")
        else:
            for s in sections_list:
                out.write(s + "\n\n")


def merge_surge_predictions(result_dir: Path, target_dirs: dict) -> None:
    merged_path = result_dir / "surge_predictions.txt"
    print(f"Merging surge_predictions.txt -> {merged_path}")

    header = ""
    for market, path in target_dirs.items():
        file_path = path / f"surge_predictions_{market}.txt"
        if file_path.exists():
            content = get_file_content(file_path)
            idx = content.find("=" * 10)
            if idx != -1:
                header = content[:idx].strip() + "\n\n"
                break

    if not header:
        header = f"=== Surge Detection Results (>= 20% return) ===\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    horizons = ["1", "3", "5", "20"]
    markets = [m for m in KNOWN_MARKETS if m in target_dirs] or [m for m in target_dirs] or KNOWN_MARKETS

    sections_written = 0
    buffer = [header]

    for hz in horizons:
        for mkt in markets:
            mkt_dir = target_dirs.get(mkt)
            candidate_paths = []
            if mkt_dir is not None:
                candidate_paths.append(mkt_dir / f"surge_predictions_{mkt}.txt")
            candidate_paths.append(result_dir / f"surge_predictions_{mkt}.txt")
            candidate_paths.append(result_dir / "surge_predictions.txt")

            match_text = ""
            for cp in candidate_paths:
                if not cp.exists():
                    continue
                content = get_file_content(cp)
                if not content or "데이터 없음" in content or "No data" in content:
                    continue

                pattern = (
                    rf"(?:^[ \t]*[=\-]{{3,}}[^\n]*\n)?"
                    rf"^[ \t]*\[{re.escape(hz)}일\]\s+{re.escape(mkt)}\s+(?:Top|All)[^\n]*\n"
                    rf"(?:^[ \t]*[=\-]{{3,}}[^\n]*\n)?"
                    rf"(.*?)"
                    rf"(?=\n[ \t]*[=\-]{{3,}}\s*\n\[|\n[ \t]*\[\d+일\]|\Z)"
                )
                m = re.search(pattern, content, re.DOTALL | re.MULTILINE)
                if m:
                    b_text = m.group(1).strip()
                    hdr = f"=========================================\n[{hz}일] {mkt} Top 20 Surge Predictions (>= 20% Return Probability)\n========================================="
                    match_text = f"{hdr}\n{b_text}"
                    break
                else:
                    pattern_legacy = (
                        rf"(==={{10,}}\s*\n"
                        rf"\[{re.escape(hz)}일\]\s+{re.escape(mkt)}\s+(?:Top|All)[^\n]*\n"
                        rf"==={{10,}}\s*\n"
                        rf".*?)"
                        rf"(?=\n==={{10,}}|\Z)"
                    )
                    m_leg = re.search(pattern_legacy, content, re.DOTALL)
                    if m_leg:
                        match_text = m_leg.group(1).strip()
                        break

            if match_text:
                buffer.append(match_text + "\n\n")
                sections_written += 1

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

            # Actual format: "--- KOSPI Top 20 ---\n  1. ...\n" or "--- KOSPI All (500) ---\n"
            pattern = rf"(--- {re.escape(mkt)}\s+(?:Top\s+\d+|All[^\n]*)\s*---\n.*?)(?=\n--- |\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                out.write(match.group(1).strip() + "\n\n")
                sections_written += 1
            else:
                print(f"  Warning: {mkt} section not found in {file_path.name}")

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
    header_lines: list[str] = []
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
            line_str = line.strip()
            if line_str.startswith("===") or line_str.startswith("Date:") or line_str.startswith("Total symbols") or line_str.startswith("Total cointegrated") or not line_str:
                continue
            if "데이터 없음" in line_str or "No data" in line_str:
                continue
            # Header lines (Filters:, column headers with Rank, Pair, No., Symbol, divider dashes)
            is_header = (
                line_str.startswith("Filters:")
                or line_str.startswith("Rank ")
                or line_str.startswith("Rank\t")
                or line_str == "Rank"
                or line_str.startswith("Pair ")
                or line_str.startswith("Pair\t")
                or line_str == "Pair"
                or line_str.startswith("No. ")
                or line_str.startswith("No.\t")
                or line_str == "No."
                or line_str.startswith("No\t")
                or line_str.startswith("Symbol ")
                or line_str.startswith("Symbol\t")
                or line_str == "Symbol"
                or line_str.startswith("---")
                or line_str.startswith("───")
                or line_str.startswith("===")
                or line_str.startswith("═══")
            )
            if is_header:
                prefix = line_str[:5]
                if not any(h.strip().startswith(prefix) for h in header_lines):
                    header_lines.append(line + "\n")
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
        if header_lines:
            out.writelines(header_lines)
            out.write("\n")
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
        r"^\s*(\d+)\s+(\S+)\s+(.+?)\s+([A-Za-z0-9_]+)"
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


KNOWN_STRATEGY_PREFIXES = [
    "pipeline_result", "surge_predictions", "ensemble_predictions", "vcp_ml_predictions",
    "vcp_patterns", "lead_lag_predictions", "strategy_data_coverage_report",
    "portfolio_allocation", "backtest_summary", "lstm_predictions", "sector_predictions",
    "rim_predictions", "event_driven_predictions", "mq_factor_predictions",
    "iv_skew_predictions", "order_flow_predictions", "short_term_reversal_predictions",
    "stat_arb_predictions", "arm_factor_predictions", "card_factor_predictions",
    "latr_factor_predictions", "inst_foreign_sector_predictions", "supply_chain_predictions",
    "sentiment_predictions", "factor_neutralized_predictions", "vol_target_predictions",
    "microstructure_predictions", "accruals_quality_predictions", "short_squeeze_predictions",
    "valueup_catalyst_predictions", "trend_efficiency_predictions", "gamma_squeeze_predictions",
    "insider_buying_predictions", "hft_order_flow_predictions", "darkpool_predictions",
    "earnings_tone_drift_predictions", "cross_asset_spillover_predictions",
    "supply_chain_gnn_predictions", "range_expansion_predictions",
    "dual_correction_predictions", "index_rebalance_predictions", "overnight_gap_predictions"
]


def discover_target_markets(base_dir: Path, result_dir: Path) -> dict[str, Path]:
    """Discover all present market targets across dedicated split dirs and result_dir.

    Robust against any present market artifact (*_{m}.txt or *_{m}.json), dedicated
    artifact directories (artifacts_in/result-{m}, result_{m}, result_split), and
    dynamically discovered market suffixes.
    """
    target_dirs: dict[str, Path] = {}

    # 1. Check dedicated split folders
    candidate_locations = [base_dir, base_dir / "artifacts_in", base_dir.parent / "artifacts_in"]
    for loc in candidate_locations:
        if not loc.exists():
            continue
        for m in KNOWN_MARKETS:
            for folder_name in [
                f"result_{m}", f"result-{m}",
                f"result_split_{m}", f"result_split-{m}",
                f"market_{m}", f"market-{m}"
            ]:
                split_path = loc / folder_name
                if split_path.is_dir() and any(split_path.iterdir()):
                    target_dirs[m] = split_path
                    break

    # 2. Multi-probe checking in result_dir for KNOWN_MARKETS
    if result_dir.exists():
        for m in KNOWN_MARKETS:
            if m not in target_dirs:
                probes = [
                    result_dir / f"surge_predictions_{m}.txt",
                    result_dir / f"pipeline_result_{m}.txt",
                    result_dir / f"ensemble_predictions_{m}.txt",
                    result_dir / f"rim_predictions_{m}.txt",
                    result_dir / f"sentiment_predictions_{m}.txt",
                    result_dir / f"backtest_summary_{m}.json",
                    result_dir / f"portfolio_allocation_{m}.txt",
                    result_dir / f"strategy_data_coverage_report_{m}.txt",
                ]
                if any(p.exists() for p in probes) or any(result_dir.glob(f"*_{m}.txt")) or any(result_dir.glob(f"*_{m}.json")):
                    target_dirs[m] = result_dir

        # 3. Dynamic discovery for custom or unlisted markets matching known strategy patterns
        excluded_market_names = {
            "RESULT", "PREDICTIONS", "REPORT", "SUMMARY", "METRICS",
            "ALLOCATION", "DATA", "SNAPSHOT", "HISTORY", "LOG", "STATUS",
            "COMPARISON", "PATTERNS", "BLACK_LITTERMAN", "LITTERMAN", "HRP"
        }
        for f in result_dir.iterdir():
            if f.is_file() and f.suffix in [".txt", ".json"]:
                for prefix in KNOWN_STRATEGY_PREFIXES:
                    if f.stem.startswith(f"{prefix}_"):
                        mkt_candidate = f.stem[len(prefix) + 1:].upper()
                        if (
                            mkt_candidate
                            and mkt_candidate not in excluded_market_names
                            and mkt_candidate not in target_dirs
                            and (mkt_candidate in KNOWN_MARKETS or (mkt_candidate.isalnum() and len(mkt_candidate) <= 12))
                        ):
                            target_dirs[mkt_candidate] = result_dir

    return target_dirs


def main():
    base_dir = Path(__file__).resolve().parent
    result_dir = base_dir / "result"
    result_dir.mkdir(parents=True, exist_ok=True)

    target_dirs = discover_target_markets(base_dir, result_dir)
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

    # Merge remaining strategy individual outputs (all 31 strategies + darkpool aliases + extended)
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
    merge_generic_strategy_files(result_dir, target_dirs, "darkpool_predictions.txt", "Dark Pool & Off-Exchange Volume Divergence Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "earnings_tone_drift_predictions.txt", "Earnings Tone Drift NLP Quant Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "cross_asset_spillover_predictions.txt", "Cross-Asset Spillover Momentum Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "supply_chain_gnn_predictions.txt", "Supply Chain GNN & Sector Flow Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "range_expansion_predictions.txt", "Range Expansion Breakout Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "dual_correction_predictions.txt", "Dual Correction Strategy Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "index_rebalance_predictions.txt", "Index Rebalance Structural Flow Predictions")
    merge_generic_strategy_files(result_dir, target_dirs, "overnight_gap_predictions.txt", "Overnight Gap Reversal Predictions")

    print("All prediction files successfully merged.")


if __name__ == "__main__":
    main()
