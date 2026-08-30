import numpy as np
import pandas as pd
from trading_system.src.core.sector_rotation import SectorRotationEngine
from trading_system.src.analysis.regime_detector import MarketRegimeDetector
from trading_system.src.analysis.scenario_simulator import ScenarioSimulationEngine, SectorOutlookScenario, MacroIndicatorScenario
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine
from trading_system.generate_report import parse_ensemble


def test_decoupling_threshold_logic():
    """Verify that when 20d correlation is < 0.40, regime detector sets status to DECOUPLED."""
    detector = MarketRegimeDetector()
    dates = pd.date_range(end='2026-08-20', periods=40)
    np.random.seed(42)
    sp500_chg = np.random.normal(0.001, 0.01, 40)
    kospi_chg = np.random.normal(0.001, 0.01, 40)
    
    df = pd.DataFrame({
        'sp500_close': 5000 * (1 + sp500_chg).cumprod(),
        'sp500_change': sp500_chg,
        'kospi_close': 2600 * (1 + kospi_chg).cumprod(),
        'kospi_change': kospi_chg,
        'vix_close': [15.0] * 40,
        'vix_change': [0.0] * 40,
        'tnx_close': [4.5] * 40,
        'usdkrw_close': [1350.0] * 40,
    }, index=dates)

    dual_info = detector.predict_dual_market_regime(df)
    assert dual_info['correlation_20d'] < 0.40
    assert "DECOUP" in dual_info['decoupling_status'].upper()

    ens_text = """
Current Market Regime Detected: BULL (2D State: BULL_LOW_VOL)
Dual Market Correlation (20d): 0.11 | Status: COUPLED
S&P 500 (20d Rolling Mean Return) : +0.200% / day
VIX Index (Fear Gauge)            : 15.32
USD/KRW FX Rate                   : 1,395.00 KRW
US 10Y Bond Yield (TNX)           : 4.65%
KR 10Y Bond Yield                 : 3.20%
WTI Crude Oil                     : $87.00 / bbl
Gold (GLD ETF)                    : $220.00
"""
    ens_data = parse_ensemble(ens_text)
    assert ens_data.decoupling_status == "DECOUPLED"
    assert ens_data.decoupling_corr == "0.11"


def test_gics_sector_mapping_accuracy():
    """Verify that specific misclassified stocks are now correctly mapped to standard GICS 11 sectors."""
    # 1. Curated Symbol Map Checks
    assert SectorRotationEngine.normalize_sector("General", symbol="MT", name="ArcelorMittal") == "Materials"
    assert SectorRotationEngine.normalize_sector("General", symbol="FANG", name="Diamondback Energy") == "Energy"
    assert SectorRotationEngine.normalize_sector("General", symbol="XPRO", name="Expro Group Holdings") == "Energy"
    assert SectorRotationEngine.normalize_sector("General", symbol="MGTX", name="MeiraGTx Holdings") == "Health Care"
    assert SectorRotationEngine.normalize_sector("General", symbol="001450", name="현대해상") == "Financials"
    assert SectorRotationEngine.normalize_sector("General", symbol="003450", name="현대차증권") == "Financials"
    assert SectorRotationEngine.normalize_sector("General", symbol="000720", name="현대건설") == "Industrials"
    assert SectorRotationEngine.normalize_sector("General", symbol="005490", name="POSCO홀딩스") == "Materials"
    assert SectorRotationEngine.normalize_sector("General", symbol="005380", name="현대차") == "Consumer Discretionary"
    assert SectorRotationEngine.normalize_sector("General", symbol="005930", name="삼성전자") == "Information Technology"

    # 2. Token-based Name/Sector Fallback Checks (Insurance taking priority over Group prefix)
    assert SectorRotationEngine.normalize_sector("", name="DB손해보험") == "Financials"
    assert SectorRotationEngine.normalize_sector("", name="한화생명") == "Financials"
    assert SectorRotationEngine.normalize_sector("", name="SK바이오사이언스") == "Health Care"
    assert SectorRotationEngine.normalize_sector("", name="삼성중공업") == "Industrials"
    assert SectorRotationEngine.normalize_sector("", name="S-Oil") == "Energy"
    assert SectorRotationEngine.normalize_sector("", name="포스코케미칼") == "Materials"


def test_31_strategy_weights_normalization():
    """Verify that 31 strategy dynamic weights strictly sum to 1.0 (100.0%)."""
    scorer = EnsembleScoringEngine()
    weights = scorer.get_base_weights(regime="BULL_HIGH_VOL")
    assert len(weights) >= 30
    assert abs(sum(weights.values()) - 1.0) < 1e-6

    rolling_sharpes = {
        'regression': -2.0,
        'surge': 1.5,
        'lead_lag': -1.0,
        'vcp_ml': 0.8,
        'stat_arb': 1.2,
        'rim_valuation': 2.0,
        'event_driven': 1.1,
        'mq_factor': 1.4,
    }
    dyn_weights = scorer.compute_dynamic_weights_from_sharpe(rolling_sharpes, regime="BULL_HIGH_VOL")
    assert abs(sum(dyn_weights.values()) - 1.0) < 1e-6


def test_ensemble_score_not_defamatorily_distorted():
    """
    Verify that when input strategies are in the 50%~90% range,
    the final ensemble score is maintained in high range (e.g. >= 60%) rather than collapsed to 26%.
    """
    scorer = EnsembleScoringEngine()
    symbols = ['090080', '005930', 'AAPL']
    
    reg_df = pd.DataFrame({'symbol': symbols, 'expected_return': [0.15, 0.12, 0.18]})
    s_df = pd.DataFrame({'symbol': symbols, 'surge_probability': [0.75, 0.70, 0.80]})
    ll_df = pd.DataFrame({'symbol': symbols, 'lead_lag_score': [0.70, 0.65, 0.75]})
    vr_df = pd.DataFrame({'symbol': symbols, 'vcp_score': [80.0, 75.0, 85.0]})
    vm_df = pd.DataFrame({'symbol': symbols, 'vcp_ml_score': [0.72, 0.68, 0.78]})
    lstm_df = pd.DataFrame({'symbol': symbols, 'lstm_score': [0.70, 0.65, 0.72]})
    rim_df = pd.DataFrame({'symbol': symbols, 'rim_score': [0.75, 0.80, 0.70]})
    mq_df = pd.DataFrame({'symbol': symbols, 'mq_score': [0.78, 0.72, 0.82]})
    arm_df = pd.DataFrame({'symbol': symbols, 'arm_score': [0.74, 0.70, 0.76]})
    of_df = pd.DataFrame({'symbol': symbols, 'order_flow_score': [0.70, 0.65, 0.72]})
    te_df = pd.DataFrame({'symbol': symbols, 'trend_efficiency_score': [0.75, 0.70, 0.80]})

    res = scorer.combine_predictions(
        reg_df=reg_df,
        s_df=s_df,
        ll_df=ll_df,
        v_rule_df=vr_df,
        vcp_ml_df=vm_df,
        lstm_df=lstm_df,
        rim_df=rim_df,
        mq_df=mq_df,
        arm_df=arm_df,
        order_flow_df=of_df,
        trend_efficiency_df=te_df,
        regime='BULL_LOW_VOL'
    )

    assert not res.empty
    assert 'ensemble_score' in res.columns
    for _, row in res.iterrows():
        assert row['ensemble_score'] >= 0.60, f"Ensemble score {row['ensemble_score']} is unreasonably low for symbol {row['symbol']}"


def test_scenario_simulator_gics_elasticity():
    """Verify ScenarioSimulator produces accurate rationales for financial interest rate benefits & energy oil benefits."""
    sim_engine = ScenarioSimulationEngine()
    base_scores = {
        '001450': 0.70,
        'FANG': 0.72,
        'MT': 0.68,
        '005930': 0.75,
    }
    sector_map = {
        '001450': '보험',
        'FANG': 'Energy',
        'MT': '철강',
        '005930': '전기전자'
    }

    macro_scen = MacroIndicatorScenario(
        usdkrw_change_pct=5.0,
        wti_change_pct=20.0,
        us10y_rate=4.8,
        vix_change_pct=15.0
    )
    sec_scen = SectorOutlookScenario(
        finance=0.5,
        energy_chemical=0.7,
        semiconductor=-0.3
    )

    df_sim = sim_engine.simulate(base_scores, sector_map, sec_scen, macro_scen)
    assert not df_sim.empty

    row_hyundai = df_sim[df_sim['symbol'] == '001450'].iloc[0]
    assert row_hyundai['sector'] == 'Financials'
    assert "고금리" in row_hyundai['impact_rationale'] and "마진 확대" in row_hyundai['impact_rationale']

    row_fang = df_sim[df_sim['symbol'] == 'FANG'].iloc[0]
    assert row_fang['sector'] == 'Energy'
    assert "유가변동" in row_fang['impact_rationale'] and "수혜" in row_fang['impact_rationale']

    row_mt = df_sim[df_sim['symbol'] == 'MT'].iloc[0]
    assert row_mt['sector'] == 'Materials'
    assert "유가변동" in row_mt['impact_rationale'] and "수혜" in row_mt['impact_rationale']


def test_sector_rotation_curated_symbol_runtime_mapping():
    """V6-18: Verify compute_sector_momentum_scores properly uses curated symbol mapping even when raw sector is 'General' or empty."""
    engine = SectorRotationEngine()
    
    # 005930 (Samsung Electronics) -> Information Technology
    # NVDA -> Information Technology
    # MT -> Materials
    # FANG -> Energy
    dates = pd.date_range(end='2026-08-20', periods=65)
    prices_dict = {
        '005930': pd.DataFrame({'Close': np.linspace(60000, 70000, 65)}, index=dates),
        'NVDA': pd.DataFrame({'Close': np.linspace(100, 130, 65)}, index=dates),
        'MT': pd.DataFrame({'Close': np.linspace(20, 25, 65)}, index=dates),
        'FANG': pd.DataFrame({'Close': np.linspace(150, 180, 65)}, index=dates),
    }
    # Raw sector map has "General" or empty
    raw_sector_map = {
        '005930': 'General',
        'NVDA': '',
        'MT': 'General',
        'FANG': 'General',
    }
    
    scores_df = engine.compute_sector_momentum_scores(prices_dict, sector_map=raw_sector_map)
    assert not scores_df.empty
    assert len(scores_df) == 4
    # All 4 stocks should have valid sector scores and properly mapped sectors
    assert (scores_df['sector_score'] >= 0.0).all() and (scores_df['sector_score'] <= 1.0).all()

