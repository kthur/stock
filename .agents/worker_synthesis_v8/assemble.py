# -*- coding: utf-8 -*-
"""
Assembler and Validator for system_improvement_plan_v8.md
Combines Executive Summary, Section 1, Section 2, Section 3, and Section 4.
Validates structure and completeness.
"""

import os
import sys

from test_build import build_plan
from build_section1 import get_section1
from build_section2 import get_section2
from build_section3 import get_section3
from build_section4 import get_section4

def assemble_master_plan():
    target_path = r"d:\Finance\code\stock\system_improvement_plan_v8.md"
    
    parts = [
        build_plan(),
        "\n\n",
        get_section1(),
        "\n\n",
        get_section2(),
        "\n\n",
        get_section3(),
        "\n\n",
        get_section4(),
    ]
    
    full_content = "".join(parts)
    
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(full_content)
        
    print(f"Successfully wrote master plan to: {target_path}")
    print(f"Total characters: {len(full_content):,}")
    lines = full_content.splitlines()
    print(f"Total lines: {len(lines):,}")
    
    # Validation checks
    critical_ids = [f"CRIT-{i:02d}" for i in range(1, 14)]
    high_ids = [f"HIGH-{i:02d}" for i in range(1, 17)]
    med_ids = [f"MED-{i:02d}" for i in range(1, 15)]
    all_ids = critical_ids + high_ids + med_ids
    
    print(f"\nValidating {len(all_ids)} issues...")
    missing_ids = [issue_id for issue_id in all_ids if issue_id not in full_content]
    if missing_ids:
        print(f"ERROR: Missing issue IDs: {missing_ids}")
        sys.exit(1)
    else:
        print(f"All {len(all_ids)} issue IDs present!")
        
    # Check 4-stage structure for each issue
    sections_req = [
        "#### 1. 현황 및 문제점",
        "#### 2. 정량적/공학적 개선 방안",
        "#### 3. 수정 대상 파일",
        "#### 4. 검증 방안"
    ]
    
    for issue_id in all_ids:
        # Find where issue starts
        pos = full_content.find(f"[{issue_id}]")
        if pos == -1:
            print(f"ERROR: Header [{issue_id}] not found!")
            sys.exit(1)
        next_pos = len(full_content)
        # find next issue
        curr_idx = all_ids.index(issue_id)
        if curr_idx + 1 < len(all_ids):
            next_id = all_ids[curr_idx + 1]
            p_next = full_content.find(f"[{next_id}]")
            if p_next != -1:
                next_pos = p_next
        else:
            p_sec4 = full_content.find("## Section 4:")
            if p_sec4 != -1 and p_sec4 > pos:
                next_pos = p_sec4
                
        chunk = full_content[pos:next_pos]
        for req in sections_req:
            if req not in chunk:
                print(f"ERROR: Issue {issue_id} is missing '{req}'")
                sys.exit(1)
                
    print("All 43 issues strictly follow the 4-stage structure!")
    print("Validation passed successfully!")

if __name__ == "__main__":
    assemble_master_plan()
