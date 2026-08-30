# Milestone 2 Investigation Report: Multi-Market Merge Synchronization & Section Extraction

## 1. Observation

### 1.1 Market Discovery Logic in `trading_system/merge_predictions.py` (Lines 680–702)
We inspected lines 677–712 of `trading_system/merge_predictions.py`:

```python
682:     markets = KNOWN_MARKETS
683:     target_dirs: dict[str, Path] = {}
684:     for m in markets:
685:         # Prefer market-specific split directory; fall back to unified result dir
686:         split_path = base_dir / f"result_{m}"
687:         if split_path.exists() and any(split_path.iterdir()):
688:             target_dirs[m] = split_path
689:         elif result_dir.exists():
690:             # Check if market-suffixed files exist inside result_dir itself
691:             probe = result_dir / f"surge_predictions_{m}.txt"
692:             if probe.exists():
693:                 target_dirs[m] = result_dir
694: 
695:     if not target_dirs:
696:         print("Warning: No per-market result directories found. Checking result/ for suffix files.")
697:         for m in markets:
698:             probe = result_dir / f"pipeline_result_{m}.txt"
699:             if probe.exists():
700:                 target_dirs[m] = result_dir
```

**Key Empirical Observations**:
1. **Single Probe File (`surge_predictions_{m}.txt`)**: Line 691 explicitly checks only `probe = result_dir / f"surge_predictions_{m}.txt"`. If a market run produced outputs for other strategies (e.g. `pipeline_result_NASDAQ.txt`, `ensemble_predictions_NASDAQ.txt`, `rim_predictions_NASDAQ.txt`) but not surge predictions, that market is omitted from `target_dirs`.
2. **Short-Circuiting Fallback**: If at least one market has `surge_predictions_{m}.txt` (e.g. `KOSPI`), `target_dirs` is non-empty (`target_dirs = {'KOSPI': result_dir}`). Consequently, the fallback check `if not target_dirs:` at line 695 evaluates to `False` and is skipped entirely. Markets without surge files will never have `pipeline_result_{m}.txt` probed.
3. **Dedicated Directory Conventions**: GitHub Actions and local split jobs may place artifacts into `artifacts_in/result-{m}/`, `result_split/`, or `result_{m}/`. Only `result_{m}` is checked in line 686.
4. **Static Known Markets**: `KNOWN_MARKETS` (lines 24–31) lacks certain markets like `KONEX` despite `ensemble_predictions_KONEX.txt` existing in `trading_system/result/`.

---

### 1.2 Ensemble Section Extraction in `merge_ensemble_predictions()` (Lines 140–160)
We inspected lines 130–165 of `trading_system/merge_predictions.py`:

```python
131:         for market in KNOWN_MARKETS:
132:             mkt_dir = target_dirs.get(market)
133:             if mkt_dir is None:
134:                 continue
135:             file_path = mkt_dir / f"ensemble_predictions_{market}.txt"
136:             if not file_path.exists():
137:                 file_path = result_dir / f"ensemble_predictions_{market}.txt"
138:             if not file_path.exists():
139:                 continue
140: 
141:             content = get_file_content(file_path)
142:             if "데이터 없음" in content or "No data" in content:
143:                 continue
144:             # Extract section — flexible whitespace and newline handling
145:             pattern = rf"(==={{10,}}\s*\n\[{re.escape(market)}\][^\n]*\n==={{10,}}\s*\n.*?)(?=\n==={{10,}}|\Z)"
146:             match = re.search(pattern, content, re.DOTALL)
147:             if match:
148:                 out.write(match.group(1).strip() + "\n\n")
149:                 sections_written += 1
150:             else:
151:                 # Fallback matching with relaxed newlines
152:                 normalized_content = content.replace("\r\n", "\n")
153:                 match = re.search(pattern, normalized_content, re.DOTALL)
154:                 if match:
155:                     out.write(match.group(1).strip() + "\n\n")
156:                     sections_written += 1
157:                 else:
158:                     print(f"  Warning: Could not extract section [{market}] from {file_path}")
```

**Verbatim Execution Output when running `python trading_system/merge_predictions.py`**:
```text
Target directories: {'SP500': 'D:\\Finance\\code\\stock\\trading_system\\result', 'NASDAQ': 'D:\\Finance\\code\\stock\\trading_system\\result', 'RUSSELL2000': 'D:\\Finance\\code\\stock\\trading_system\\result', 'KOSPI': 'D:\\Finance\\code\\stock\\trading_system\\result', 'KOSDAQ': 'D:\\Finance\\code\\stock\\trading_system\\result'}
Merging pipeline_result.txt -> D:\Finance\code\stock\trading_system\result\pipeline_result.txt
Merging ensemble_predictions.txt -> D:\Finance\code\stock\trading_system\result\ensemble_predictions.txt
  Warning: Could not extract section [NASDAQ] from D:\Finance\code\stock\trading_system\result\ensemble_predictions_NASDAQ.txt
  Warning: Could not extract section [RUSSELL2000] from D:\Finance\code\stock\trading_system\result\ensemble_predictions_RUSSELL2000.txt
```

**Direct Examination of `ensemble_predictions_NASDAQ.txt` & `ensemble_predictions_RUSSELL2000.txt`**:
- `ensemble_predictions_NASDAQ.txt` lines 89–112 contained sections for `[KOSPI]`, `[KOSDAQ]`, and `[SP500]`, but contained **zero occurrences** of `[NASDAQ]`.
- Similarly, `ensemble_predictions_RUSSELL2000.txt` contained only `[KOSPI]`, `[KOSDAQ]`, and `[SP500]`.
- This occurred because earlier artifact copy operations in GHA (or test mocks) copied a 3-market `ensemble_predictions.txt` directly to `ensemble_predictions_NASDAQ.txt` and `ensemble_predictions_RUSSELL2000.txt`.

---

## 2. Logic Chain

### 2.1 Root Cause Analysis of Market Discovery Failures
1. **Hypothesis**: The merger fails to detect active markets if `surge_predictions_{m}.txt` does not exist in `result/`.
2. **Evidence**: `merge_predictions.py:691` evaluates `probe = result_dir / f"surge_predictions_{m}.txt"`. If `surge_predictions_NASDAQ.txt` is missing, `target_dirs["NASDAQ"]` is not set.
3. **Chain**:
   - `target_dirs` only contains markets that have a `surge_predictions_{m}.txt` file.
   - When merging all other 30+ strategies (e.g. `merge_pipeline_result`, `merge_generic_strategy_files`, `merge_portfolio_allocation`, `merge_coverage_report`), the loop only iterates over `market in target_dirs`.
   - Any market missing the surge probe is skipped across all strategy merges, even if `pipeline_result_NASDAQ.txt` or `rim_predictions_NASDAQ.txt` exist with full valid data.

### 2.2 Root Cause Analysis of `Could not extract section [MARKET]` Warnings
1. **Hypothesis**: Regex failure occurs due to missing sections in the target split file and strict divider pattern constraints.
2. **Evidence**:
   - **Case A (Missing Section in Split File)**: When `ensemble_predictions_{market}.txt` is present on disk but was generated by a run that did not include `{market}` rows, the section header `[{market}]` is absent. `merge_ensemble_predictions()` only checks `ensemble_predictions_{market}.txt` and does not check `ensemble_predictions.txt` or other candidate files.
   - **Case B (Separator Variations)**: Regex `rf"(==={{10,}}\s*\n\[{re.escape(market)}\][^\n]*\n==={{10,}}\s*\n.*?)(?=\n==={{10,}}|\Z)"` requires:
     1. Leading divider of at least 10 `=` signs: `==={10,}\s*\n`.
     2. Exact line `[{market}]...`.
     3. Trailing divider of at least 10 `=` signs: `==={10,}\s*\n`.
     If a generator or mock uses fewer equals signs (e.g. `=== [NASDAQ] Top 100 ===`), dash lines (`---`), or omits the top border divider, regex match fails completely.
   - **Case C (Footer Bleed-Through)**: Lookahead `(?=\n==={{10,}}|\Z)` matches until EOF (`\Z`) for the last market section in a file. If the file ends with `--- Data Quality Notes (auto-detected) ---` or trailing summaries, those lines are swallowed into the market section text and duplicated across merged output blocks.

---

## 3. Caveats

1. **Read-Only Explorer Scope**: In accordance with the Explorer archetype, no production source files were modified during this investigation.
2. **Legacy Artifact Presence**: Stale files in `trading_system/result/` (e.g. `ensemble_predictions_NASDAQ.txt` lacking `[NASDAQ]`) can trigger extraction warnings if the pipeline has not regenerated them in the current environment.
3. **Platform Encoding Differences**: When printing Korean strings (e.g., `[1일]`) to Windows CP949 terminals, logging output may display mojibake characters like `[1]` unless stdout encoding is UTF-8 or sanitized.

---

## 4. Conclusion & Concrete Recommendations

### 4.1 Recommendation 1: Robust Multi-Artifact Market Discovery
Replace lines 682–702 of `trading_system/merge_predictions.py` with a dedicated discovery routine `discover_target_markets()`:

```python
def discover_target_markets(base_dir: Path, result_dir: Path) -> dict[str, Path]:
    """Discover all present market targets across dedicated split dirs and result_dir.
    
    Robust against any present market artifact (*_{m}.txt or *_{m}.json), dedicated
    artifact directories (artifacts_in/result-{m}, result_{m}, result_split), and
    dynamically discovered market suffixes.
    """
    target_dirs: dict[str, Path] = {}

    # 1. Check dedicated split folders
    candidate_locations = [base_dir, base_dir / "artifacts_in"]
    for loc in candidate_locations:
        if not loc.exists():
            continue
        for m in KNOWN_MARKETS:
            for folder_name in [f"result_{m}", f"result-{m}", f"result_split_{m}", f"result_split-{m}"]:
                split_path = loc / folder_name
                if split_path.is_dir() and any(split_path.iterdir()):
                    target_dirs[m] = split_path
                    break

    # 2. Check result_dir for any market-suffixed files (*_{m}.txt, *_{m}.json)
    if result_dir.exists():
        for m in KNOWN_MARKETS:
            if m not in target_dirs:
                mkt_files = list(result_dir.glob(f"*_{m}.txt")) + list(result_dir.glob(f"*_{m}.json"))
                if mkt_files:
                    target_dirs[m] = result_dir

        # 3. Dynamic discovery for custom or unlisted markets (e.g. KONEX, regional markets)
        for f in result_dir.iterdir():
            if f.is_file() and f.suffix in [".txt", ".json"]:
                parts = f.stem.rsplit("_", 1)
                if len(parts) == 2:
                    discovered_mkt = parts[1].upper()
                    # Filter out non-market suffixes like 'result', 'predictions', 'report', 'summary'
                    if (
                        discovered_mkt not in ["RESULT", "PREDICTIONS", "REPORT", "SUMMARY", "METRICS", "ALLOCATION"]
                        and discovered_mkt not in target_dirs
                        and (discovered_mkt in KNOWN_MARKETS or discovered_mkt.isalpha())
                    ):
                        target_dirs[discovered_mkt] = result_dir

    return target_dirs
```

---

### 4.2 Recommendation 2: Flexible Multi-Tier Section Extraction in `merge_ensemble_predictions()`
Refactor section extraction in `merge_ensemble_predictions()` to:
1. Support flexible header separators (`===`, `---`, or no top border).
2. Cleanly bound the bottom of the section before footers (`--- Data Quality`, `--- Applied`, `--- Executive`, `\n===`, or next `\[[A-Z0-9_]+\] Top`).
3. Check fallback files (`result_dir / "ensemble_predictions.txt"` or any other available file) if `ensemble_predictions_{market}.txt` lacks the section.

**Proposed Implementation**:
```python
def _extract_ensemble_market_section(content: str, market: str) -> str:
    """Extract [{market}] section robustly across varying header divider styles and boundaries."""
    if not content or "데이터 없음" in content or "No data" in content:
        return ""

    normalized = content.replace("\r\n", "\n")

    # Primary Pattern: Standard border with === or ---
    pattern_primary = (
        rf"(?:^[ \t]*[=\-]{{3,}}[^\n]*\n)?"
        rf"^[ \t]*\[{re.escape(market)}\][^\n]*\n"
        rf"(?:^[ \t]*[=\-]{{3,}}[^\n]*\n)?"
        rf"(.*?)"
        rf"(?=\n[ \t]*[=\-]{{3,}}\s*\n\[|\n--- |\n=== |\Z)"
    )
    m = re.search(pattern_primary, normalized, re.DOTALL | re.MULTILINE)
    if m:
        body = m.group(1).strip()
        header = f"=========================================\n[{market}] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)\n========================================="
        return f"{header}\n{body}"

    # Secondary Pattern: Line-by-line state machine parser
    lines = normalized.splitlines()
    in_section = False
    captured_lines = []
    for line in lines:
        l_str = line.strip()
        if re.match(rf"^\[{re.escape(market)}\]\s+Top", l_str, re.IGNORECASE):
            in_section = True
            continue
        elif in_section:
            if re.match(r"^\[[A-Za-z0-9_]+\]\s+Top", l_str) or l_str.startswith("--- Data Quality") or l_str.startswith("=== Dynamic"):
                break
            if l_str.startswith("==="):
                continue
            captured_lines.append(line)

    if captured_lines:
        body = "\n".join(captured_lines).strip()
        header = f"=========================================\n[{market}] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)\n========================================="
        return f"{header}\n{body}"

    return ""
```

---

### 4.3 Recommendation 3: Standardize Market List & Surge Extraction
1. Add `"KONEX"` to `KNOWN_MARKETS`.
2. Apply the same flexible border extractor to `merge_surge_predictions` and `merge_vcp_ml_predictions` to prevent horizon extraction warnings.

---

## 5. Verification Method

To verify the updated merge logic and section extraction:

1. **Unit & Edge-Case Tests**:
   ```bash
   .venv/bin/pytest tests/test_merge_generic_strategies.py tests/test_challenger_rim_2_stress.py -v
   ```
2. **Execute Multi-Market Merge Script**:
   ```bash
   .venv/bin/python trading_system/merge_predictions.py
   ```
   *Expected*: Discovers all active markets (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`, `KONEX`), merges without `Could not extract section` warnings, and writes valid merged prediction files.
3. **Verify Generated HTML Dashboard**:
   ```bash
   .venv/bin/python trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html
   ```
   *Expected*: Runs cleanly and renders fully populated tables for all discovered markets.
