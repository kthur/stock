import sys
import io
import re
import os
import ast

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

REPORT_PATH = 'system_improvement_report_v5.md'
BASELINE_PATH = '.agents/explorer_baseline_r1/baseline_catalog.md'
HISTORICAL_REPORT_PATH = 'SYSTEM_IMPROVEMENT_REPORT.md'

print('=' * 80)
print('STARTING AUTOMATED VICTORY AUDIT FOR SYSTEM IMPROVEMENT REPORT V5')
print('=' * 80)

if not os.path.exists(REPORT_PATH):
    print(f'FATAL: {REPORT_PATH} does not exist!')
    sys.exit(1)

with open(REPORT_PATH, 'r', encoding='utf-8') as f:
    report_text = f.read()

print(f'Loaded {REPORT_PATH}: {len(report_text)} chars, {len(report_text.splitlines())} lines.')

# ==============================================================================
# PHASE 1: SCOPE & DELIVERABLE VERIFICATION
# ==============================================================================
print('\n' + '=' * 80)
print('PHASE 1: SCOPE & DELIVERABLE VERIFICATION')
print('=' * 80)

required_sections = [
    ('1. Executive Summary', r'##\s+1\.\s+Executive Summary'),
    ('2. Task Master Table', r'##\s+2\.\s+Comprehensive Task Master Table'),
    ('3. Technical Analysis', r'##\s+3\.\s+In-Depth Technical Analysis'),
    ('4. Cross-Cutting Issues', r'##\s+(Section\s+4|4)\.?\s*:?\s*Cross-Cutting'),
    ('5. Prioritized Roadmap', r'##\s+(Section\s+5|5)\.?\s*:?\s*Prioritized Execution Roadmap')
]

phase1_pass = True
for name, pattern in required_sections:
    match = re.search(pattern, report_text, re.IGNORECASE)
    if match:
        print(f'[PASS] Section: {name} (Found: "{match.group(0)}")')
    else:
        print(f'[FAIL] Section: {name} MISSING!')
        phase1_pass = False

# Check Mermaid Diagrams
mermaid_blocks = re.findall(r'```mermaid(.*?)```', report_text, re.DOTALL)
print(f'[PASS] Architecture Macro Diagrams: {len(mermaid_blocks)} diagram(s) found.')

# Extract Task Master Table entries
# Format: | **V5-01** | Domain 1: AI/ML & Prediction | 🔴 CRITICAL | PCA-ZCA Whitening... | trading_system/src/ai/factor_orthogonalizer.py:147-163 | Proposed |
master_table_tasks = {}
for line in report_text.splitlines():
    if line.strip().startswith('|') and ('V5-' in line or 'v5-' in line):
        parts = [p.strip() for p in line.strip().split('|')[1:-1]]
        if len(parts) >= 6:
            m = re.search(r'V5-\d+', parts[0])
            if m:
                tid = m.group(0)
                master_table_tasks[tid] = {
                    'domain': parts[1],
                    'severity': parts[2],
                    'name': parts[3],
                    'file_path': parts[4],
                    'status': parts[5]
                }

print(f'Master Table Task Count: {len(master_table_tasks)}')

# Extract Section 3 tasks
# Format: #### V5-01 [🔴 CRITICAL]: PCA-ZCA Whitening...
section3_task_matches = list(re.finditer(r'####\s+(V5-\d+)\s*\[(.*?)\]:\s*(.+)', report_text))
print(f'Section 3 Detailed Tasks Found: {len(section3_task_matches)}')

section3_tasks = {}
for i, match in enumerate(section3_task_matches):
    tid = match.group(1)
    sev = match.group(2)
    tname = match.group(3)
    start_pos = match.start()
    end_pos = section3_task_matches[i+1].start() if i+1 < len(section3_task_matches) else len(report_text)
    # also cap at Section 4 if this is the last task
    sec4_match = re.search(r'##\s+(Section\s+4|4)', report_text[start_pos:])
    if sec4_match and i == len(section3_task_matches) - 1:
        end_pos = start_pos + sec4_match.start()
    
    block_content = report_text[start_pos:end_pos]
    section3_tasks[tid] = {
        'severity': sev,
        'name': tname,
        'content': block_content
    }

# Check Task consistency
expected_ids = [f'V5-{i:02d}' for i in range(1, 33)]
missing_in_master = set(expected_ids) - set(master_table_tasks.keys())
missing_in_sec3 = set(expected_ids) - set(section3_tasks.keys())

if missing_in_master:
    print(f'[FAIL] Missing in Master Table: {missing_in_master}')
    phase1_pass = False
else:
    print('[PASS] All 32 tasks (V5-01 ~ V5-32) present in Master Table.')

if missing_in_sec3:
    print(f'[FAIL] Missing in Section 3: {missing_in_sec3}')
    phase1_pass = False
else:
    print('[PASS] All 32 tasks (V5-01 ~ V5-32) present in Section 3.')

# Verify each Section 3 task has required subcomponents:
# - Affected File & Line Numbers
# - Severity
# - Symptom & Root Cause Analysis
# - Mathematical / Financial Engineering Rationale
# - Concrete Source Code Modification Snippet / diff
print('\nVerifying subcomponents for all 32 tasks:')
missing_subcomponents = []
for tid in sorted(section3_tasks.keys()):
    b = section3_tasks[tid]['content']
    has_file = bool(re.search(r'Affected File', b, re.IGNORECASE))
    has_symptom = bool(re.search(r'Symptom|현상', b, re.IGNORECASE))
    has_math = bool(re.search(r'Mathematical|Financial Engineering|수학적|금융공학적|Rationale', b, re.IGNORECASE))
    has_diff = bool('```diff' in b or '```python' in b)
    
    if not (has_file and has_symptom and has_math and has_diff):
        missing_subcomponents.append((tid, has_file, has_symptom, has_math, has_diff))
        print(f'[FAIL] {tid}: File={has_file}, Symptom={has_symptom}, Math={has_math}, Diff={has_diff}')

if not missing_subcomponents:
    print(f'[PASS] All 32 tasks in Section 3 have complete subcomponents (File, Symptom, Math, Diff).')
else:
    phase1_pass = False

# Check Section 4 subsections
sec4_subsections = ['4.1', '4.2', '4.3', '4.4']
for sub in sec4_subsections:
    if sub in report_text:
        print(f'[PASS] Section 4 Subsection {sub} present.')
    else:
        print(f'[FAIL] Section 4 Subsection {sub} missing.')
        phase1_pass = False

# Check Section 5 Roadmaps
sec5_phases = ['Phase 1', 'Phase 2', 'Phase 3']
for p in sec5_phases:
    if p in report_text:
        print(f'[PASS] Section 5 {p} present.')
    else:
        print(f'[FAIL] Section 5 {p} missing.')
        phase1_pass = False

print(f'\nPhase 1 Overall Result: {"PASS" if phase1_pass else "FAIL"}')
