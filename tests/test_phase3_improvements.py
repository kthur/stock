import pytest
import numpy as np
import pandas as pd
from trading_system.src.core.event_driven import EventDrivenEngine
from trading_system.src.core.lead_lag_3tier import ThreeTierLeadLagEngine
from trading_system.src.risk.risk_manager import RiskManager, CrisisLevel


def test_cb_bw_overhang_and_margin_risk_sandbox():
    """Verify CB/BW dilution overhang detection blacklists symbols and margin rate >9% applies penalty."""
    engine = EventDrivenEngine()
    
    symbols = ['005930', '000660', '035420']
    mock_filings = [
        {'stock_code': '000660', 'report_nm': '전환청구권행사 (CB 전환 6% 희석)'}
    ]
    margin_rates = {
        '005930': 4.5,
        '000660': 6.0,
        '035420': 11.0  # > 9.0% threshold -> excess 2.0% -> penalty = 1.0 - 0.10 = 0.90
    }

    res = engine.evaluate_cb_bw_overhang_and_margin_risk(
        symbols=symbols,
        filings=mock_filings,
        margin_rate_dict=margin_rates
    )

    # 1. 000660 should be blacklisted due to CB conversion notice
    assert res['000660']['is_overhang_blacklisted'] is True
    assert res['000660']['cb_bw_ratio'] > 0.05

    # 2. 035420 margin penalty check (rate = 11.0% -> penalty = 0.90)
    assert res['035420']['is_overhang_blacklisted'] is False
    assert pytest.approx(res['035420']['margin_penalty'], abs=1e-3) == 0.90
    assert res['005930']['margin_penalty'] == 1.0


def test_3tier_lead_lag_momentum_transfer():
    """Verify 3-Tier Lead-Lag engine transfers momentum from Tier 1 (US) & Tier 2 (KRX) to Tier 3 (KOSDAQ)."""
    engine = ThreeTierLeadLagEngine()
    
    dates = pd.date_range('2026-08-01', periods=5)
    
    # Mock prices: Tier 1 (NVDA) and Tier 2 (SK Hynix) show strong positive returns (+5%)
    prices_dict = {
        'NVDA': pd.DataFrame({'Close': [100.0, 101.0, 102.0, 103.0, 105.0]}, index=dates),
        '000660': pd.DataFrame({'Close': [100000, 101000, 102000, 103000, 105000]}, index=dates),
        '035420': pd.DataFrame({'Close': [50000, 50000, 50000, 50000, 50000]}, index=dates)  # Delayed follower
    }

    df_res = engine.compute_3tier_lead_lag_scores(prices_dict, tier3_symbols=['035420'])
    assert len(df_res) == 1
    assert df_res['symbol'].iloc[0] == '035420'
    score = df_res['tier3_lead_lag_score'].iloc[0]
    # Delayed follower score should be boosted above baseline (0.50)
    assert score > 0.50


def test_credit_cds_and_oil_shock_risk_engine():
    """Verify high CDS 5Y premium (>100bp) and 3D oil shock (>8%) trigger ACTIVE/SEVERE crisis levels."""
    rm = RiskManager(portfolio_value=100_000_000)
    cd = rm.crisis_detector

    # 1. Normal state (CDS = 30bp, VIX = 18)
    lvl_normal = cd.evaluate(vix=18.0, cds_5y=30.0)
    assert lvl_normal == CrisisLevel.NONE

    # 2. High CDS 5Y Premium (120bp) -> Triggers ACTIVE crisis level
    lvl_cds = cd.evaluate(vix=18.0, cds_5y=120.0)
    assert lvl_cds in [CrisisLevel.ACTIVE, CrisisLevel.SEVERE]

    # 3. Severe CDS 5Y Spike (160bp) -> Triggers SEVERE crisis level
    lvl_severe = cd.evaluate(vix=18.0, cds_5y=160.0)
    assert lvl_severe == CrisisLevel.SEVERE
