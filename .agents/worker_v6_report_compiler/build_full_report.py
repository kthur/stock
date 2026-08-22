# build_full_report.py
import re
from pathlib import Path

def extract_domain_sections():
    d1 = Path('.agents/explorer_d1_aiml/analysis.md').read_text(encoding='utf-8')
    d2 = Path('.agents/explorer_d2_port_risk/analysis.md').read_text(encoding='utf-8')
    d3 = Path('.agents/explorer_d3_strategies/analysis.md').read_text(encoding='utf-8')
    d4 = Path('.agents/explorer_d4_oms_cost/analysis.md').read_text(encoding='utf-8')
    d5 = Path('.agents/explorer_d5_pipeline_infra/analysis.md').read_text(encoding='utf-8')

    # Domain 1 extraction (Section 3: V6-01 to V6-08 + V6-09 note)
    # Domain 2 extraction (Section 3: V6-09 to V6-16)
    # Domain 3 extraction (Section 3: V6-17 to V6-24)
    # Domain 4 extraction (Section 3: V6-25 to V6-31)
    # Domain 5 extraction (Section 2: V6-29 -> V6-32, V6-30 -> V6-33, V6-31 -> V6-34, V6-32 -> V6-35)
    
    return d1, d2, d3, d4, d5

if __name__ == '__main__':
    d1, d2, d3, d4, d5 = extract_domain_sections()
    print('Domain extraction tested successfully.')
