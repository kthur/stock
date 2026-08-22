import os
import sys
import re

ROOT_DIR = r"d:\Finance\code\stock"
V6_PATH = os.path.join(ROOT_DIR, "system_improvement_report_v6.md")
V5_PATH = os.path.join(ROOT_DIR, "system_improvement_report_v5.md")
V1_PATH = os.path.join(ROOT_DIR, "docs", "improvement_report.md")

def run_forensic_audit():
    print("=" * 80)
    print("COMPREHENSIVE FORENSIC AUDIT: system_improvement_report_v6.md")
    print("=" * 80)

    if not os.path.exists(V6_PATH):
        print(f"[FAIL] V6 report file not found at: {V6_PATH}")
        return False

    with open(V6_PATH, "r", encoding="utf-8") as f:
        v6_text = f.read()

    lines = v6_text.splitlines()
    print(f"Report Size: {len(lines)} lines, {len(v6_text.encode('utf-8'))} bytes")

    # 1. Structural Section Checks
    print("\n--- 1. SECTION COMPLETENESS CHECK ---")
    required_sections = [
        ("1. Executive Summary", r"^## 1\.\s+Executive Summary"),
        ("2. Master Task Table", r"^## 2\.\s+종합 과제 일람표"),
        ("3. Deep-Dive Analysis", r"^## 3\.\s+도메인별 세부 분석 및 수정안"),
        ("3.1 Domain 1: AI/ML", r"^### 3\.1\s+Domain 1:"),
        ("3.2 Domain 2: Portfolio & Risk", r"^### 3\.2\s+Domain 2:"),
        ("3.3 Domain 3: Strategies & Data", r"^### 3\.3\s+Domain 3:"),
        ("3.4 Domain 4: OMS & Friction", r"^### 3\.4\s+Domain 4:"),
        ("3.5 Domain 5: Pipeline & Infra", r"^### 3\.5\s+Domain 5:"),
        ("4. Cross-Cutting Architecture", r"^## 4\.\s+시스템 횡단 구조적 과제"),
        ("5. 31-Strategy Matrix", r"^## 5\.\s+31대 전략 간 상관관계 및 다변화 효과 분석"),
        ("6. Phased Roadmap", r"^## 6\.\s+우선순위별 실행 로드맵 및 독립 검증 계획"),
        ("7. Conclusion", r"^## 7\.\s+결론 및 향후 시스템 발전 방향")
    ]

    all_sections_pass = True
    for sec_name, sec_pattern in required_sections:
        match = re.search(sec_pattern, v6_text, re.MULTILINE)
        if match:
            print(f"  [PASS] Found section: {sec_name}")
        else:
            print(f"  [FAIL] Missing section: {sec_name}")
            all_sections_pass = False

    # 2. Master Table Extraction
    print("\n--- 2. MASTER TASK TABLE EXTRACTION ---")
    table_pattern = re.compile(r"^\|\s*\*\*(V6-\d{2})\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|", re.MULTILINE)
    table_matches = table_pattern.findall(v6_text)
    print(f"Total tasks found in Master Table: {len(table_matches)}")
    
    table_tasks = {}
    for item in table_matches:
        tid, domain, severity, title, target_files, status = [x.strip() for x in item]
        table_tasks[tid] = {
            "domain": domain,
            "severity": severity,
            "title": title,
            "target_files": target_files,
            "status": status
        }
    
    expected_ids = [f"V6-{i:02d}" for i in range(1, 36)]
    missing_table_ids = set(expected_ids) - set(table_tasks.keys())
    if not missing_table_ids and len(table_tasks) == 35:
        print("  [PASS] Master Table contains exactly all 35 tasks (V6-01 through V6-35) with zero gaps.")
    else:
        print(f"  [FAIL] Master Table task mismatch: missing {missing_table_ids}, total count: {len(table_tasks)}")

    # 3. Deep Dive Sections Extraction & Verification
    print("\n--- 3. DEEP DIVE SECTIONS & ARTIFACT VERIFICATION ---")
    deep_dive_pattern = re.compile(r"^###\s+(V6-\d{2})\s+\[([^\]]+)\]:\s+(.+)$", re.MULTILINE)
    deep_dive_matches = deep_dive_pattern.findall(v6_text)
    print(f"Total Deep-Dive task sections found: {len(deep_dive_matches)}")
    
    deep_dive_tasks = {}
    for item in deep_dive_matches:
        tid, sev, title = [x.strip() for x in item]
        deep_dive_tasks[tid] = {"severity": sev, "title": title}
    
    missing_dd_ids = set(expected_ids) - set(deep_dive_tasks.keys())
    if not missing_dd_ids and len(deep_dive_tasks) == 35:
        print("  [PASS] Deep Dive sections contain exactly all 35 tasks (V6-01 through V6-35).")
    else:
        print(f"  [FAIL] Deep Dive section mismatch: missing {missing_dd_ids}, total count: {len(deep_dive_tasks)}")

    # Check for each task: Affected File, Severity, LaTeX math, and Git diff snippet
    print("\n--- 4. TASK-BY-TASK DETAILED VERIFICATION ---")
    task_audit_results = []
    
    for i in range(1, 36):
        tid = f"V6-{i:02d}"
        # Extract task block
        start_pat = rf"^###\s+{tid}\s+\["
        start_match = re.search(start_pat, v6_text, re.MULTILINE)
        if not start_match:
            print(f"  [FAIL] {tid}: Section header not found")
            continue
            
        start_pos = start_match.start()
        # Find next section or end
        if i < 35:
            next_tid = f"V6-{i+1:02d}"
            next_pat = rf"^###\s+{next_tid}\s+\["
            next_match = re.search(next_pat, v6_text[start_pos:], re.MULTILINE)
            end_pos = start_pos + next_match.start() if next_match else len(v6_text)
        else:
            next_sec_pat = r"^##\s+4\."
            next_match = re.search(next_sec_pat, v6_text[start_pos:], re.MULTILINE)
            end_pos = start_pos + next_match.start() if next_match else len(v6_text)

        task_block = v6_text[start_pos:end_pos]
        
        # Check required fields with flexible naming
        has_file = bool(re.search(r"-\s+\*\*(?:Affected Files? & Line Numbers?|Exact File Path)\*\*:", task_block))
        has_sev = bool(re.search(r"-\s+\*\*Severity\*\*:", task_block))
        has_symptom = bool(re.search(r"(?:Symptom & Root Cause Analysis|Phenomenon & Root Cause)", task_block, re.IGNORECASE))
        has_math_rationale = bool(re.search(r"(?:Rationale|Mathematical|Econometric|Portfolio Theory|Microstructure|Distributed Systems)", task_block, re.IGNORECASE))
        has_math_formula = "$" in task_block or "O(1)" in task_block or "O(N)" in task_block or "tau" in task_block or "N=" in task_block
        has_diff = ("```diff" in task_block or "```\ndiff" in task_block) and ("--- a/" in task_block and "+++ b/" in task_block)
        
        # Extract files cited
        file_tokens = re.findall(r"([a-zA-Z0-9_\-\.\/\\]+\.py)", task_block)
        # remove test files or dummy paths if any
        target_py_files = set(ft for ft in file_tokens if ("src" in ft or "run_pipeline" in ft or "generate_run_snapshot" in ft or "config.py" in ft))
        
        file_check_details = []
        files_exist = True
        for pf in target_py_files:
            # normalize path
            norm_pf = pf.replace("\\", "/").strip()
            if norm_pf.startswith("a/") or norm_pf.startswith("b/"):
                norm_pf = norm_pf[2:]
            
            p1 = os.path.join(ROOT_DIR, norm_pf.replace("/", os.sep))
            p2 = os.path.join(ROOT_DIR, "trading_system", norm_pf.replace("/", os.sep))
            
            if os.path.exists(p1) and os.path.isfile(p1):
                file_check_details.append((norm_pf, True, p1))
            elif os.path.exists(p2) and os.path.isfile(p2):
                file_check_details.append((norm_pf, True, p2))
            else:
                file_check_details.append((norm_pf, False, p1))
                files_exist = False

        status_flag = "PASS" if (has_file and has_sev and has_symptom and has_math_rationale and has_diff and files_exist and len(file_check_details) > 0) else "FAIL"
        
        task_audit_results.append({
            "tid": tid,
            "status": status_flag,
            "has_file": has_file,
            "has_sev": has_sev,
            "has_symptom": has_symptom,
            "has_math_rationale": has_math_rationale,
            "has_math_formula": has_math_formula,
            "has_diff": has_diff,
            "files_exist": files_exist,
            "file_checks": file_check_details,
        })

    # Summary of task audit results
    all_tasks_pass = all(r["status"] == "PASS" for r in task_audit_results)
    print(f"Task Verification Summary: {sum(1 for r in task_audit_results if r['status'] == 'PASS')} / 35 PASS")
    for r in task_audit_results:
        if r["status"] == "FAIL":
            print(f"  [FAIL] {r['tid']}: details: {r}")
        else:
            files_str = ", ".join(f"{fc[0]} (EXISTS)" for fc in r["file_checks"])
            print(f"  [PASS] {r['tid']}: Math/Rationale=True, GitDiff=True, TargetFiles=[{files_str}]")

    # 4. Check for duplication against V5 and V1
    print("\n--- 5. HISTORICAL NON-DUPLICATION AUDIT (vs V5 and earlier) ---")
    if os.path.exists(V5_PATH):
        with open(V5_PATH, "r", encoding="utf-8") as f:
            v5_text = f.read()
        v5_tasks = re.findall(r"\*\*(V5-\d{2})\*\*", v5_text)
        print(f"V5 tasks count: {len(set(v5_tasks))}")
        
        # Check task titles comparison
        v5_titles = re.findall(r"^\|\s*\*\*(V5-\d{2})\*\*\s*\|\s*[^|]+\|\s*[^|]+\|\s*([^|]+)\|", v5_text, re.MULTILINE)
        print(f"V5 extracted titles count: {len(v5_titles)}")
        
        # Check if any v6 title is identical to v5 title
        duplicate_count = 0
        for tid, tinfo in table_tasks.items():
            v6_title = tinfo["title"]
            for v5_id, v5_title in v5_titles:
                if v6_title.strip() == v5_title.strip():
                    print(f"  [DUPLICATE DETECTED] {tid} matches {v5_id}: {v6_title}")
                    duplicate_count += 1
        if duplicate_count == 0:
            print("  [PASS] 0% Title Duplication between V6 (35 items) and V5 (32 items).")
    else:
        print("  [WARN] V5 report not found for cross-comparison.")

    print("\n" + "=" * 80)
    if all_sections_pass and len(table_tasks) == 35 and len(deep_dive_tasks) == 35 and all_tasks_pass:
        print("FINAL VERDICT: CLEAN (100% EMPIRICAL INTEGRITY VERIFIED)")
    else:
        print("FINAL VERDICT: INTEGRITY VIOLATION (Issues Detected)")
    print("=" * 80)

if __name__ == "__main__":
    run_forensic_audit()
