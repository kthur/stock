import sys
import io
import re
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('system_improvement_report_v5.md', 'r', encoding='utf-8') as f:
    text = f.read()

sections = [
    '## 1. Executive Summary',
    '## 2. Comprehensive Task Master Table',
    '## 3. In-Depth Technical Analysis & Actionable Remedies',
    '## Section 4: Cross-Cutting Systemic & Architectural Issues',
    '## Section 5: Prioritized Execution Roadmap'
]

print('=== SECTION PRESENCE CHECK ===')
for s in sections:
    present = s in text
    res = 'PASS' if present else 'FAIL'
    print(f'[{res}] Section: {s}')

# Check Macro Diagram
mermaid_matches = re.findall(r'```mermaid(.*?)```', text, re.DOTALL)
print(f'\n=== MACRO ARCHITECTURE DIAGRAMS ===\nFound {len(mermaid_matches)} mermaid diagrams')

# Master table
table_rows = re.findall(r'\|\s*(V5-\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|', text)
print(f'\n=== MASTER TABLE TASKS ({len(table_rows)} tasks found) ===')
master_ids = set()
for r in table_rows:
    master_ids.add(r[0])
    print(f'{r[0]}: [{r[1]}] ({r[2]}) {r[3]} | File: {r[4]} | Status: {r[5]}')

# Section 3 tasks
section3_tasks = re.findall(r'###\s+(V5-\d+):\s*(.+)', text)
print(f'\n=== SECTION 3 DETAILED TASKS ({len(section3_tasks)} tasks found) ===')
sec3_ids = set()
for tid, name in section3_tasks:
    sec3_ids.add(tid)
    print(f'{tid}: {name}')

# Check consistency between Master table and Section 3
diff_master_sec3 = master_ids.symmetric_difference(sec3_ids)
print(f'\nDiscrepancies between Master Table and Section 3: {diff_master_sec3}')

# Check required components for each task in Section 3
print('\n=== TASK STRUCTURE VERIFICATION (Section 3 components) ===')
task_blocks = re.split(r'###\s+V5-\d+:', text)[1:]
for i, (tid, name) in enumerate(section3_tasks):
    block = task_blocks[i]
    has_symptom = '현상 및 원인 분석' in block or 'Symptom' in block or 'Analysis' in block
    has_math = '수학적' in block or '금융공학적' in block or 'Theoretical' in block or 'Mathematical' in block or 'Proof' in block
    has_diff = '```diff' in block or '```python' in block or '수정' in block or 'Diff' in block
    print(f'{tid}: Symptom/Root Cause: {has_symptom} | Math/Finance Proof: {has_math} | Code/Diff: {has_diff}')
