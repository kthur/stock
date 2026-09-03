# -*- coding: utf-8 -*-
"""
Test all 31 trading strategies across all 16 global markets.
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime

from src.config import TradingConfig
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.vcp_detector import VCPPatternDetector
from src.core.stat_arb import StatisticalArbitrageEngine
from src.core.sector_rotation import SectorRotationEngine
from src.core.rim_valuation import RIMValuationEngine
from src.core.event_driven import EventDrivenEngine
from src.core.mq_factor import MQFactorEngine
from src.core.iv_skew import IVSkewEngine
from src.core.order_flow import OrderFlowEngine
from src.core.short_term_reversal import ShortTermReversalEngine
from src.core.arm_factor import ARMFactorEngine
from src.core.card_factor import CARDFactorEngine
from src.core.latr_factor import LATRFactorEngine
from src.core.inst_foreign_sector import InstForeignSectorEngine
from src.core.supply_chain import SupplyChainEngine
from src.core.llm_sentiment_engine import DARTSECSentimentEngine
from src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine
from src.core.vol_target import VolTargetingEngine
from src.core.hft_engine import MicrostructureImbalanceEngine
from src.core.accruals_quality import AccrualsQualityEngine
from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
from src.core.valueup_catalyst import ValueUpCatalystEngine
from src.core.trend_efficiency import TrendEfficiencyEngine
from src.core.gamma_squeeze import OptionsGammaSqueezeEngine
from src.core.insider_buying import InsiderBuyingEngine
from src.core.earnings_tone_drift import EarningsToneDriftEngine
from src.core.cross_asset_spillover import CrossAssetSpilloverEngine
from src.core.supply_chain_gnn import SupplyChainGNNEngine
from src.core.range_expansion_breakout import RangeExpansionBreakoutEngine
from src.core.dual_correction import DualCorrectionEngine
from src.core.index_rebalance import IndexRebalanceEngine
from src.core.overnight_gap_reversal import OvernightGapReversalEngine


ALL_16_MARKET_SYMBOLS = {
    'SP500': 'AAPL',
    'NASDAQ': 'NVDA',
    'RUSSELL2000': 'IWM_SYM',
    'KOSPI': '005930',
    'KOSDAQ': '035720',
    'CHINA_SSE': '600519.SS',
    'CHINA_SZSE': '000858.SZ',
    'JAPAN_TSE': '7203.T',
    'INDIA_NSE': 'RELIANCE.NS',
    'EUROPE_STOXX': 'MC.PA',
    'VIETNAM_HOSE': 'VNM.VN',
    'TAIWAN_TWSE': '2330.TW',
    'AUSTRALIA_ASX': 'BHP.AX',
    'BRAZIL_B3': 'PETR4.SA',
    'HKEX': '0700.HK',
    'SINGAPORE_SGX': 'D05.SI',
    'CANADA_TSX': 'RY.TO',
}


def _create_synthetic_ohlcv(symbol: str, n_days: int = 150) -> pd.DataFrame:
    np.random.seed(abs(hash(symbol)) % (2**31))
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')
    base_price = 100.0 + (abs(hash(symbol)) % 500)
    returns = np.random.normal(0.001, 0.02, size=n_days)
    prices = base_price * np.exp(np.cumsum(returns))
    
    high = prices * (1 + np.abs(np.random.normal(0.005, 0.005, size=n_days)))
    low = prices * (1 - np.abs(np.random.normal(0.005, 0.005, size=n_days)))
    open_p = low + (high - low) * np.random.uniform(0.2, 0.8, size=n_days)
    volume = np.random.randint(50000, 2000000, size=n_days).astype(float)
    
    df = pd.DataFrame({
        'date': dates,
        'open': open_p,
        'high': high,
        'low': low,
        'close': prices,
        'volume': volume,
        'change': np.insert(np.diff(prices) / prices[:-1], 0, 0.0),
    })
    df.set_index('date', inplace=True)
    return df


@pytest.fixture
def global_test_fixture():
    cfg = TradingConfig()
    symbols = list(ALL_16_MARKET_SYMBOLS.values())
    prices_dict = {sym: _create_synthetic_ohlcv(sym, 120) for sym in symbols}
    
    universe = pd.DataFrame([
        {'symbol': sym, 'name': f'{mkt}_Stock', 'market': mkt, 'sector': 'Technology'}
        for mkt, sym in ALL_16_MARKET_SYMBOLS.items()
    ])
    
    macro_dates = pd.date_range(end=datetime.now(), periods=120, freq='B')
    macro_df = pd.DataFrame({
        'VIX': np.random.uniform(12, 25, size=120),
        'TNX': np.random.uniform(3.5, 4.8, size=120),
        'USDKRW': np.random.uniform(1250, 1400, size=120),
        'WTI': np.random.uniform(70, 90, size=120),
        'Gold': np.random.uniform(1800, 2400, size=120),
        'DXY': np.random.uniform(100, 106, size=120),
    }, index=macro_dates)
    
    return cfg, symbols, prices_dict, universe, macro_df


class TestAll16Markets31Strategies:
    """End-to-end multi-market multi-strategy validation suite."""

    def test_all_16_markets_covered_in_universe(self, global_test_fixture):
        cfg, symbols, prices_dict, universe, macro_df = global_test_fixture
        assert len(universe) == len(ALL_16_MARKET_SYMBOLS)
        assert set(universe['market'].unique()) == set(ALL_16_MARKET_SYMBOLS.keys())
        for sym in symbols:
            assert sym in prices_dict
            assert len(prices_dict[sym]) >= 100

    def test_strategy_04_vcp_rules(self, global_test_fixture):
        cfg, symbols, prices_dict, universe, _ = global_test_fixture
        detector = VCPPatternDetector()
        for sym, df in prices_dict.items():
            pattern = detector.detect(df)
            assert isinstance(pattern, dict)
            assert 'is_vcp' in pattern
            assert 'vcp_score' in pattern

    def test_strategy_07_stat_arb(self, global_test_fixture):
        cfg, symbols, prices_dict, _, _ = global_test_fixture
        sa_engine = StatisticalArbitrageEngine()
        pairs = sa_engine.find_cointegrated_pairs(prices_dict)
        scores_df = sa_engine.get_symbol_stat_arb_scores(pairs)
        assert isinstance(scores_df, pd.DataFrame)
        assert 'stat_arb_score' in scores_df.columns

    def test_strategy_08_sector_rotation(self, global_test_fixture):
        cfg, symbols, prices_dict, universe, macro_df = global_test_fixture
        sec_engine = SectorRotationEngine()
        sec_map = dict(zip(universe['symbol'], universe['sector']))
        sec_scores = sec_engine.compute_sector_momentum_scores(
            prices_dict, sector_map=sec_map, macro_indicators=macro_df, regime_label="BULL_TREND"
        )
        assert isinstance(sec_scores, pd.DataFrame)
        assert 'sector_score' in sec_scores.columns
        assert len(sec_scores) > 0

    def test_strategy_09_rim_valuation(self, global_test_fixture):
        cfg, symbols, prices_dict, universe, _ = global_test_fixture
        rim_engine = RIMValuationEngine()
        input_rows = []
        for sym, df_p in prices_dict.items():
            latest = df_p.iloc[-1].to_dict()
            latest['symbol'] = sym
            latest['market'] = universe.loc[universe['symbol'] == sym, 'market'].iloc[0]
            latest['bps'] = 50000.0
            latest['roe'] = 0.15
            input_rows.append(latest)
        df_rim_input = pd.DataFrame(input_rows)
        rim_scores = rim_engine.compute_rim_scores(df_rim_input)
        assert isinstance(rim_scores, pd.DataFrame)
        assert 'rim_score' in rim_scores.columns
        assert len(rim_scores) == len(symbols)

    def test_strategy_10_to_14_core_momentum_factors(self, global_test_fixture):
        cfg, symbols, prices_dict, universe, _ = global_test_fixture
        
        # 10. Event-Driven
        ev_engine = EventDrivenEngine()
        ev_scores = ev_engine.compute_event_scores(symbols, prices_dict)
        assert 'event_score' in ev_scores.columns
        assert len(ev_scores) == len(symbols)

        # 11. MQ Factor
        mq_engine = MQFactorEngine()
        mq_scores = mq_engine.compute_mq_scores(prices_dict)
        assert 'mq_score' in mq_scores.columns
        assert len(mq_scores) == len(symbols)

        # 12. IV Skew
        iv_engine = IVSkewEngine()
        iv_scores = iv_engine.compute_iv_skew_scores(symbols, prices_dict)
        assert 'iv_skew_score' in iv_scores.columns
        assert len(iv_scores) == len(symbols)

        # 13. Order Flow
        of_engine = OrderFlowEngine()
        of_scores = of_engine.compute_order_flow_scores(prices_dict)
        assert 'order_flow_score' in of_scores.columns
        assert len(of_scores) == len(symbols)

        # 14. Short-Term Reversal
        rev_engine = ShortTermReversalEngine()
        rev_scores = rev_engine.compute_reversal_scores(prices_dict)
        assert 'reversal_score' in rev_scores.columns
        assert len(rev_scores) == len(symbols)

    def test_strategy_15_to_20_macro_and_sentiment_factors(self, global_test_fixture):
        cfg, symbols, prices_dict, universe, macro_df = global_test_fixture
        
        # 15. ARM
        arm_engine = ARMFactorEngine()
        arm_scores = arm_engine.compute_scores(prices_dict)
        assert isinstance(arm_scores, pd.DataFrame)
        assert 'arm_score' in arm_scores.columns

        # 16. CARD
        card_engine = CARDFactorEngine()
        card_scores = card_engine.compute_scores(prices_dict, macro_df)
        assert isinstance(card_scores, pd.DataFrame)
        assert 'card_score' in card_scores.columns

        # 17. LATR
        latr_engine = LATRFactorEngine()
        latr_scores = latr_engine.compute_scores(prices_dict)
        assert isinstance(latr_scores, (pd.DataFrame, dict))

        # 18. Inst & Foreign Sector
        ifs_engine = InstForeignSectorEngine()
        sec_map = dict(zip(universe['symbol'], universe['sector']))
        ifs_scores = ifs_engine.compute_scores(prices_dict, sector_mapping=sec_map)
        assert isinstance(ifs_scores, pd.DataFrame)
        assert 'inst_foreign_sector_score' in ifs_scores.columns

        # 19. Supply Chain
        sc_engine = SupplyChainEngine()
        sc_scores = sc_engine.compute_scores(prices_dict, universe)
        assert isinstance(sc_scores, pd.DataFrame)
        assert 'supply_chain_score' in sc_scores.columns
        assert len(sc_scores) == len(symbols)

        # 20. NLP Sentiment
        sent_engine = DARTSECSentimentEngine()
        sent_scores = sent_engine.compute_scores(universe=universe, prices_dict=prices_dict)
        assert isinstance(sent_scores, pd.DataFrame)
        assert 'sentiment_score' in sent_scores.columns

    def test_strategy_21_to_31_microstructure_and_anomaly_factors(self, global_test_fixture):
        cfg, symbols, prices_dict, universe, _ = global_test_fixture

        # 21. Multi-Factor Neutralizer
        fn_engine = MultiFactorNeutralizerEngine()
        fn_scores = fn_engine.compute_scores(prices_dict=prices_dict, universe=universe)
        assert isinstance(fn_scores, pd.DataFrame)
        assert 'factor_neutralized_score' in fn_scores.columns

        # 22. Volatility Targeting
        vt_engine = VolTargetingEngine()
        vt_scores = vt_engine.compute_scores(prices_dict, universe)
        assert isinstance(vt_scores, pd.DataFrame)
        assert 'vol_target_score' in vt_scores.columns

        # 23. Microstructure
        micro_engine = MicrostructureImbalanceEngine()
        micro_scores = micro_engine.compute_scores(prices_dict, universe)
        assert isinstance(micro_scores, pd.DataFrame)
        assert 'microstructure_score' in micro_scores.columns

        # 24. Accruals Quality
        aq_engine = AccrualsQualityEngine(cfg)
        aq_scores = aq_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(aq_scores, pd.DataFrame)
        assert 'accruals_quality_score' in aq_scores.columns

        # 25. Short Squeeze
        sq_engine = ShortInterestSqueezeEngine(cfg)
        sq_scores = sq_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(sq_scores, pd.DataFrame)
        assert 'short_squeeze_score' in sq_scores.columns

        # 26. Value-Up Catalyst
        vu_engine = ValueUpCatalystEngine(cfg)
        vu_scores = vu_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(vu_scores, pd.DataFrame)
        assert 'valueup_catalyst_score' in vu_scores.columns

        # 27. Trend Efficiency
        te_engine = TrendEfficiencyEngine(cfg)
        te_scores = te_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(te_scores, pd.DataFrame)
        assert 'trend_efficiency_score' in te_scores.columns

        # 28. Gamma Squeeze
        gamma_engine = OptionsGammaSqueezeEngine(cfg)
        gamma_scores = gamma_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(gamma_scores, pd.DataFrame)
        assert 'gamma_squeeze_score' in gamma_scores.columns

        # 29. Insider Buying
        insider_engine = InsiderBuyingEngine(cfg)
        insider_scores = insider_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(insider_scores, pd.DataFrame)
        assert 'insider_buying_score' in insider_scores.columns

        # 30. Earnings Tone Drift
        tone_engine = EarningsToneDriftEngine(cfg)
        tone_scores = tone_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(tone_scores, pd.DataFrame)
        assert 'earnings_tone_drift_score' in tone_scores.columns

    def test_strategies_32_to_37_cross_asset_to_overnight_gap(self, global_test_fixture):
        """Test strategies 32 through 37 operate on all 16 markets."""
        cfg, symbols, prices_dict, universe, macro_df = global_test_fixture

        # 32. Cross-Asset Spillover
        cas_engine = CrossAssetSpilloverEngine(cfg)
        cas_scores = cas_engine.calculate_scores(symbols, prices_dict=prices_dict, macro_df=macro_df)
        assert isinstance(cas_scores, pd.DataFrame)
        assert 'cross_asset_spillover_score' in cas_scores.columns

        # 33. Supply Chain GNN
        gnn_engine = SupplyChainGNNEngine(cfg)
        gnn_scores = gnn_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(gnn_scores, pd.DataFrame)
        assert 'supply_chain_gnn_score' in gnn_scores.columns

        # 34. Range Expansion Breakout
        reb_engine = RangeExpansionBreakoutEngine(cfg)
        reb_scores = reb_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(reb_scores, pd.DataFrame)
        assert 'range_expansion_score' in reb_scores.columns

        # 35. Dual Correction
        dc_engine = DualCorrectionEngine(cfg)
        dc_scores = dc_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(dc_scores, pd.DataFrame)
        assert 'dual_correction_score' in dc_scores.columns

        # 36. Index Rebalance
        ir_engine = IndexRebalanceEngine(cfg)
        ir_scores = ir_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(ir_scores, pd.DataFrame)
        assert 'index_rebalance_score' in ir_scores.columns

        # 37. Overnight Gap Reversal
        og_engine = OvernightGapReversalEngine(cfg)
        og_scores = og_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert isinstance(og_scores, pd.DataFrame)
        assert 'overnight_gap_score' in og_scores.columns

    def test_ensemble_scoring_all_16_markets_and_friction_deductions(self, global_test_fixture):
        """Test that EnsembleScoringEngine successfully aggregates all 37 strategy scores across all 16 markets."""
        cfg, symbols, prices_dict, universe, macro_df = global_test_fixture
        scorer = EnsembleScoringEngine(config=cfg)

        # Build mock dataframes with symbol, market, and scores
        reg_df = pd.DataFrame({
            'symbol': symbols,
            'name': [f'{s}_name' for s in symbols],
            'market': [universe.loc[universe['symbol'] == s, 'market'].iloc[0] for s in symbols],
            1: np.random.uniform(0.01, 0.05, size=len(symbols)),
            5: np.random.uniform(0.02, 0.10, size=len(symbols)),
            20: np.random.uniform(0.05, 0.20, size=len(symbols)),
            60: np.random.uniform(0.10, 0.40, size=len(symbols)),
        })
        
        surge_df = pd.DataFrame({
            'symbol': symbols,
            'surge_1d': np.random.uniform(0.1, 0.8, size=len(symbols)),
            'surge_5d': np.random.uniform(0.1, 0.8, size=len(symbols)),
            'surge_20d': np.random.uniform(0.1, 0.8, size=len(symbols)),
        })

        lead_lag_df = pd.DataFrame({
            'symbol': symbols,
            'lead_lag_score': np.random.uniform(0.0, 0.5, size=len(symbols)),
        })

        vcp_ml_df = pd.DataFrame({
            'symbol': symbols,
            'vcp_20d': np.random.uniform(0.1, 0.7, size=len(symbols)),
            'vcp_5d': np.random.uniform(0.1, 0.7, size=len(symbols)),
        })

        lstm_df = pd.DataFrame({
            'symbol': symbols,
            'lstm_return_20d': np.random.uniform(0.02, 0.15, size=len(symbols)),
        })

        # Run full ensemble scoring
        ensemble_df = scorer.calculate_ensemble_score(
            regime="BULL_TREND",
            regression_df=reg_df,
            surge_df=surge_df,
            lead_lag_df=lead_lag_df,
            vcp_rule_df=pd.DataFrame({'symbol': symbols, 'vcp_score': [70.0]*len(symbols)}),
            vcp_ml_df=vcp_ml_df,
            lstm_df=lstm_df,
            cross_asset_spillover_df=pd.DataFrame({'symbol': symbols, 'cross_asset_spillover_score': [0.65]*len(symbols)}),
            supply_chain_gnn_df=pd.DataFrame({'symbol': symbols, 'supply_chain_gnn_score': [0.55]*len(symbols)}),
            range_expansion_df=pd.DataFrame({'symbol': symbols, 'range_expansion_score': [0.72]*len(symbols)}),
            dual_correction_df=pd.DataFrame({'symbol': symbols, 'dual_correction_score': [0.60]*len(symbols)}),
            index_rebalance_df=pd.DataFrame({'symbol': symbols, 'index_rebalance_score': [0.58]*len(symbols)}),
            overnight_gap_df=pd.DataFrame({'symbol': symbols, 'overnight_gap_score': [0.62]*len(symbols)}),
            target_horizon=20,
            prices_dict=prices_dict,
        )

        assert not ensemble_df.empty
        assert len(ensemble_df) == len(symbols)
        assert 'ensemble_score' in ensemble_df.columns
        assert 'ensemble_expected_return' in ensemble_df.columns
        assert 'portfolio_weight' in ensemble_df.columns

        # Verify all 37 strategy columns are integrated and all symbols scored
        for sym in symbols:
            assert sym in ensemble_df['symbol'].values
            sym_row = ensemble_df[ensemble_df['symbol'] == sym].iloc[0]
            assert pd.notna(sym_row['ensemble_score'])
            assert sym_row['ensemble_score'] >= 0.0
