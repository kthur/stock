import pytest
import pandas as pd
import numpy as np
from trading_system.src.analysis.scenario_simulator import (
    ScenarioSimulationEngine,
    SectorOutlookScenario,
    MacroIndicatorScenario
)

def test_scenario_simulator_basic():
    engine = ScenarioSimulationEngine()
    
    # Mock Base Ensemble Scores
    base_scores = {
        '005930.KS': 0.70,  # 삼성전자 (IT)
        '051910.KS': 0.65,  # LG화학 (Materials)
        '005380.KS': 0.60,  # 현대차 (Consumer Discretionary)
        '005490.KS': 0.55,  # POSCO홀딩스 (Materials)
        '035420.KS': 0.50,  # NAVER (IT)
        '097950.KS': 0.50,  # CJ제일제당 (Consumer Staples)
    }

    sector_map = {
        '005930.KS': '전기전자',
        '051910.KS': '화학',
        '005380.KS': '자동차',
        '005490.KS': '철강금속',
        '035420.KS': '소프트웨어',
        '097950.KS': '음식료품',
    }

    # Scenario 1: Semiconductor Supercycle + USD/KRW Surge (+5%)
    sec_scen = SectorOutlookScenario(semiconductor=0.8, consumer_staples=-0.5)
    macro_scen = MacroIndicatorScenario(usdkrw_change_pct=5.0, wti_change_pct=2.0)

    res_df = engine.simulate(base_scores, sector_map, sec_scen, macro_scen)

    assert not res_df.empty
    assert len(res_df) == 6
    assert 'simulated_score' in res_df.columns
    assert 'impact_rationale' in res_df.columns

    # Check top stock under Semiconductor boom
    top_sym = res_df.iloc[0]['symbol']
    assert top_sym in ['005930.KS', '035420.KS']
    assert res_df.loc[res_df['symbol'] == '005930.KS', 'simulated_score'].values[0] > 0.70

    # Check food stock penalty under high FX / high oil
    staples_delta = res_df.loc[res_df['symbol'] == '097950.KS', 'score_delta'].values[0]
    assert staples_delta < 0.0

def test_scenario_simulator_stagflation():
    engine = ScenarioSimulationEngine()
    
    base_scores = {
        '011780.KS': 0.50,  # S-Oil (Energy)
        '005930.KS': 0.60,  # 삼성전자 (IT)
    }
    sector_map = {'011780.KS': '에너지', '005930.KS': '전기전자'}

    # Stagflation Scenario: High Oil (+20%), High FX (+10%), High Rate (5.0%)
    sec_scen = SectorOutlookScenario(energy_chemical=0.7, semiconductor=-0.4)
    macro_scen = MacroIndicatorScenario(usdkrw_change_pct=10.0, wti_change_pct=20.0, us10y_rate=5.0)

    res_df = engine.simulate(base_scores, sector_map, sec_scen, macro_scen)
    
    soil_score = res_df.loc[res_df['symbol'] == '011780.KS', 'simulated_score'].values[0]
    assert soil_score > 0.50
