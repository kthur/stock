"""
CLI execution script for Macro & Sector Scenario Simulation.
"""
import sys
import logging
from pathlib import Path
import pandas as pd

# Add project root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Ensure UTF-8 stdout encoding on Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.analysis.scenario_simulator import (
    ScenarioSimulationEngine,
    SectorOutlookScenario,
    MacroIndicatorScenario
)

def run_preset_scenarios():
    print("=" * 70)
    print(" [Scenario Simulation Engine] Sector & Macro Dynamics Forecast")
    print("=" * 70)

    engine = ScenarioSimulationEngine()

    # 샘플 종목 데이터베이스 기반 Base Score & Sector
    sample_scores = {
        '005930.KS': 0.68, # 삼성전자 (IT/반도체)
        '000660.KS': 0.72, # SK하이닉스 (IT/반도체)
        '051910.KS': 0.62, # LG화학 (이차전지/화학)
        '005380.KS': 0.65, # 현대차 (자동차/운수장비)
        '105560.KS': 0.58, # KB금융 (금융업)
        '011780.KS': 0.50, # S-Oil (에너지/정유)
        '097950.KS': 0.52, # CJ제일제당 (음식료품)
        '005490.KS': 0.54, # POSCO홀딩스 (철강금속)
    }

    sector_map = {
        '005930.KS': '전기전자',
        '000660.KS': '전기전자',
        '051910.KS': '화학',
        '005380.KS': '자동차',
        '105560.KS': '금융업',
        '011780.KS': '에너지',
        '097950.KS': '음식료품',
        '005490.KS': '철강금속',
    }

    # 시나리오 1: 반도체 슈퍼사이클 & 환율 상승 (+5.0%)
    print("\n[Scenario 1] Semiconductor Supercycle + USD/KRW Surge (+5.0%)")
    sec_scen1 = SectorOutlookScenario(semiconductor=0.8, consumer_staples=-0.2)
    macro_scen1 = MacroIndicatorScenario(usdkrw_change_pct=5.0, wti_change_pct=1.0, us10y_rate=4.1)

    df1 = engine.simulate(sample_scores, sector_map, sec_scen1, macro_scen1)
    print(df1[['sim_rank', 'symbol', 'sector', 'base_score', 'simulated_score', 'score_delta', 'impact_rationale']].to_string(index=False))

    # 시나리오 2: 고유가/고금리 스태그플레이션 (유가 +20%, 금리 4.8%)
    print("\n[Scenario 2] High WTI Oil + High Interest Rate Stagflation (WTI +20%, US10Y 4.8%)")
    sec_scen2 = SectorOutlookScenario(energy_chemical=0.7, finance=0.5, semiconductor=-0.3, consumer_staples=-0.5)
    macro_scen2 = MacroIndicatorScenario(usdkrw_change_pct=8.0, wti_change_pct=20.0, us10y_rate=4.8, vix_change_pct=25.0)

    df2 = engine.simulate(sample_scores, sector_map, sec_scen2, macro_scen2)
    print(df2[['sim_rank', 'symbol', 'sector', 'base_score', 'simulated_score', 'score_delta', 'impact_rationale']].to_string(index=False))

if __name__ == '__main__':
    run_preset_scenarios()
