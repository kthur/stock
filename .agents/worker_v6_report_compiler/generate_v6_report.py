# Auto-generated builder for system_improvement_report_v6.md
import sys
import re
from pathlib import Path

def get_text(p):
    return Path(p).read_text(encoding='utf-8')

def main():
    print('Reading source analysis reports...')
    d1 = get_text('.agents/explorer_d1_aiml/analysis.md')
    d2 = get_text('.agents/explorer_d2_port_risk/analysis.md')
    d3 = get_text('.agents/explorer_d3_strategies/analysis.md')
    d4 = get_text('.agents/explorer_d4_oms_cost/analysis.md')
    d5 = get_text('.agents/explorer_d5_pipeline_infra/analysis.md')
    
    print('All 5 analysis reports successfully read.')

if __name__ == '__main__':
    main()
