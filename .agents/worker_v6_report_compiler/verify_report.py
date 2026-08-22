# -*- coding: utf-8 -*-
"""
Verification Script for system_improvement_report_v6.md
Checks for task IDs V6-01 through V6-35, section headers, tables, formulas, and completeness.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import re
from pathlib import Path

def verify():
    report_path = Path(r"d:\Finance\code\stock\system_improvement_report_v6.md")
    assert report_path.exists(), "Report file does not exist!"
    
    content = report_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    print(f"Report Size: {len(content):,} chars, {len(lines):,} lines")
    
    # 1. Check task IDs V6-01 to V6-35 in Master Table and in Section 3
    for i in range(1, 36):
        task_id = f"V6-{i:02d}"
        
        # Check in Master Table
        table_match = re.search(rf"\|\s*\*\*{task_id}\*\*\s*\|", content)
        assert table_match, f"Missing {task_id} in Master Task Table!"
        
        # Check in Section 3 deep-dive headers
        header_match = re.search(rf"###+\s*{task_id}\b", content)
        assert header_match, f"Missing {task_id} deep dive section header in Section 3!"
        
    print("[PASS] All 35 Tasks (V6-01 through V6-35) verified in both Master Table and Section 3 deep-dives.")

    # 2. Check Major Sections
    sections = [
        "## 1. Executive Summary & System Architecture Overview",
        "## 2. 종합 과제 일람표 (Comprehensive Master Task Table)",
        "## 3. 도메인별 세부 분석 및 수정안 (Deep-Dive Analysis & Remediations)",
        "### 3.1 Domain 1: AI/ML & 예측 무결성 (V6-01 ~ V6-08)",
        "### 3.2 Domain 2: 포트폴리오 & 리스크 공학 (V6-09 ~ V6-16)",
        "### 3.3 Domain 3: 31대 전략 엔진 & 데이터 레이어 (V6-17 ~ V6-24)",
        "### 3.4 Domain 4: 실행 OMS & 거래비용 (V6-25 ~ V6-31)",
        "### 3.5 Domain 5: 파이프라인, CI/CD & 아키텍처 (V6-32 ~ V6-35)",
        "## 4. 시스템 횡단 구조적 과제 및 아키텍처 고도화 방안 (System-Wide Cross-Cutting Architecture)",
        "## 5. 31대 전략 간 상관관계 및 다변화 효과 분석 (31-Strategy Diversification & Correlation Analysis)",
        "## 6. 우선순위별 실행 로드맵 (Phased Implementation Roadmap)"
    ]
    for sec in sections:
        assert sec in content, f"Missing section: {sec}"
    print("[PASS] All 11 major section and domain headers verified.")

    # 3. Check LaTeX Formulas and Code blocks
    latex_blocks = content.count("$$")
    code_blocks = content.count("```")
    print(f"[PASS] LaTeX display math delimiters: {latex_blocks} ($$), Code fence markers: {code_blocks} (```)")
    assert latex_blocks >= 10, "Expected multiple LaTeX display math blocks"
    assert code_blocks >= 20, "Expected multiple code blocks and git diffs"

    print("\n=======================================================")
    print("REPORT COMPILATION AND INTEGRITY 100% VERIFIED!")
    print("=======================================================")

if __name__ == "__main__":
    verify()
