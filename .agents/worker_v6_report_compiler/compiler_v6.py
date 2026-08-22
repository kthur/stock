# Master Compiler for system_improvement_report_v6.md
import sys
import re
from pathlib import Path

def build_master_report():
    print('Starting compilation of system_improvement_report_v6.md...')
    
    # Load analysis reports
    d1_raw = Path('.agents/explorer_d1_aiml/analysis.md').read_text(encoding='utf-8')
    d2_raw = Path('.agents/explorer_d2_port_risk/analysis.md').read_text(encoding='utf-8')
    d3_raw = Path('.agents/explorer_d3_strategies/analysis.md').read_text(encoding='utf-8')
    d4_raw = Path('.agents/explorer_d4_oms_cost/analysis.md').read_text(encoding='utf-8')
    d5_raw = Path('.agents/explorer_d5_pipeline_infra/analysis.md').read_text(encoding='utf-8')

    out = []
    
    # 1. Header and Section 1 & 2
    from sec1_sec2 import get_sec1_sec2
    out.append(get_sec1_sec2())
    
    # 3. Section 3: Domain by Domain Analysis
    out.append('## 3. 도메인별 세부 분석 및 수정안 (Deep-Dive Analysis & Remediations)\n')
    
    # 3.1 Domain 1
    out.append('### 3.1 Domain 1: AI/ML & 예측 무결성 (V6-01 ~ V6-08)\n')
    d1_sec3_match = re.search(r'## 3\\. In-Depth Technical Analysis & Git Diff Proposals\\s+(.+?)(?=\\n## 4\\.|$)', d1_raw, re.DOTALL)
    if d1_sec3_match:
        d1_sec3 = d1_sec3_match.group(1).strip()
        # Clean up any formatting
        out.append(d1_sec3 + '\n')
    
    # 3.2 Domain 2
    out.append('\n### 3.2 Domain 2: 포트폴리오 & 리스크 공학 (V6-09 ~ V6-16)\n')
    d2_sec3_match = re.search(r'## 3\\. Detailed Audit Findings & Mathematical Remedies\\s+(.+?)(?=\\n## 4\\.|$)', d2_raw, re.DOTALL)
    if d2_sec3_match:
        d2_sec3 = d2_sec3_match.group(1).strip()
        out.append(d2_sec3 + '\n')

    # 3.3 Domain 3
    out.append('\n### 3.3 Domain 3: 31대 전략 엔진 & 데이터 레이어 (V6-17 ~ V6-24)\n')
    d3_sec3_match = re.search(r'## 3\\. In-Depth Technical Analyses & Actionable Remedies\\s+(.+?)(?=\\n## 4\\.|$)', d3_raw, re.DOTALL)
    if d3_sec3_match:
        d3_sec3 = d3_sec3_match.group(1).strip()
        out.append(d3_sec3 + '\n')

    # 3.4 Domain 4
    out.append('\n### 3.4 Domain 4: 실행 OMS & 거래비용 (V6-25 ~ V6-31)\n')
    d4_sec3_match = re.search(r'## 3\\. Deep Technical Analysis & Verification\\s+(.+?)(?=\\n## 4\\.|$)', d4_raw, re.DOTALL)
    if d4_sec3_match:
        d4_sec3 = d4_sec3_match.group(1).strip()
        out.append(d4_sec3 + '\n')

    # 3.5 Domain 5 (Renumber V6-29->V6-32, V6-30->V6-33, V6-31->V6-34, V6-32->V6-35)
    out.append('\n### 3.5 Domain 5: 파이프라인, CI/CD & 아키텍처 (V6-32 ~ V6-35)\n')
    d5_sec2_match = re.search(r'## 2\\. Detailed Technical Forensic Findings\\s+(.+?)(?=\\n## 3\\.|$)', d5_raw, re.DOTALL)
    if d5_sec2_match:
        d5_sec2 = d5_sec2_match.group(1).strip()
        # Perform renumbering
        d5_sec2 = d5_sec2.replace('### V6-29', '#### V6-32')
        d5_sec2 = d5_sec2.replace('### V6-30', '#### V6-33')
        d5_sec2 = d5_sec2.replace('### V6-31', '#### V6-34')
        d5_sec2 = d5_sec2.replace('### V6-32', '#### V6-35')
        out.append(d5_sec2 + '\n')

    # 4. Section 4, 5, 6
    from sec4_sec5_sec6 import get_sec4_sec5_sec6
    out.append(get_sec4_sec5_sec6())

    full_report = '\n'.join(out)
    target_path = Path('system_improvement_report_v6.md')
    target_path.write_text(full_report, encoding='utf-8')
    print(f'Successfully compiled {target_path} ({len(full_report)} chars, {len(full_report.splitlines())} lines)')

if __name__ == '__main__':
    build_master_report()
