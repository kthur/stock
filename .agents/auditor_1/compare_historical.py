import os
import re

ROOT = r"d:\Finance\code\stock"

# Load v5
v5_path = os.path.join(ROOT, "system_improvement_report_v5.md")
with open(v5_path, "r", encoding="utf-8") as f:
    v5_content = f.read()

# Load v6
v6_path = os.path.join(ROOT, "system_improvement_report_v6.md")
with open(v6_path, "r", encoding="utf-8") as f:
    v6_content = f.read()

# Load v1
v1_path = os.path.join(ROOT, "docs", "improvement_report.md")
with open(v1_path, "r", encoding="utf-8") as f:
    v1_content = f.read()

# Extract V5 tasks
v5_tasks = re.findall(r"\|\s*\*\*(V5-\d{2})\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|", v5_content)
print(f"V5 tasks count: {len(v5_tasks)}")

# Extract V6 tasks
v6_tasks = re.findall(r"\|\s*\*\*(V6-\d{2})\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|", v6_content)
print(f"V6 tasks count: {len(v6_tasks)}")

print("\n--- DETAILED COMPARISON V6 vs V5 ---")
overlaps = []
for v6_id, v6_dom, v6_sev, v6_title, v6_files, v6_stat in v6_tasks:
    for v5_id, v5_dom, v5_sev, v5_title, v5_files in v5_tasks:
        # Check title similarity or semantic duplication
        v6_t_clean = v6_title.strip()
        v5_t_clean = v5_title.strip()
        if v6_t_clean == v5_t_clean:
            overlaps.append((v6_id, v5_id, "IDENTICAL TITLE", v6_t_clean))
            
print(f"Direct Title Overlaps: {len(overlaps)}")

# Print domain breakdown for V6
v6_domain_counts = {}
v6_sev_counts = {}
for tid, dom, sev, title, files, stat in v6_tasks:
    dom_clean = dom.strip()
    sev_clean = sev.strip()
    v6_domain_counts[dom_clean] = v6_domain_counts.get(dom_clean, 0) + 1
    v6_sev_counts[sev_clean] = v6_sev_counts.get(sev_clean, 0) + 1

print("\nV6 Domain Breakdown:")
for d, c in v6_domain_counts.items():
    print(f"  {d}: {c} tasks")

print("\nV6 Severity Breakdown:")
for s, c in v6_sev_counts.items():
    print(f"  {s}: {c} tasks")
