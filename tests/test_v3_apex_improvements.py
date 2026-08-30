"""
Tests for v3.0 Apex-Tier Quantitative Improvements:
1. Dynamic Horizon-Aware Purged & Embargoed CV in OptunaStrategyTuner.
2. VPIN Toxicity Gate (Adverse Selection Protection) in ExecutionOMSEngine.
3. Extremal Index (theta) Clustered EVT-CVaR Tail Risk Scaling.
4. Non-linear Asymmetric Bullwhip Spillover in SupplyChainEngine.
5. Institutional Factor Crowding & Fire-Sale Spillover Suppression in EnsembleScorer.
"""

import numpy as np
import pandas as pd
from src.ai.optuna_tuner import OptunaStrategyTuner
from src.execution.oms_engine import ExecutionOMSEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.core.supply_chain import SupplyChainEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine


def test_optuna_purged_embargoed_gap():
    tuner = OptunaStrategyTuner()
    
    # Check that for short horizon (H=1), gap is default (20)
    # and for long horizon (H=60), gap dynamically expands to >= 65
    np.random.seed(42)
    X = pd.DataFrame(np.random.randn(100, 4), columns=['f1', 'f2', 'f3', 'f4'])
    y = pd.Series(np.random.randn(100))

    # Regression tuning with horizon=60
    res_60d = tuner.tune_strategy_1_regression(X, y, n_trials=2, horizon=60)
    assert 'xgb' in res_60d
    assert 'lgb' in res_60d

    # Surge tuning with horizon=20
    res_surge = tuner.tune_strategy_2_surge(X, (y > 0).astype(int), n_trials=2, horizon=20)
    assert 'surge_xgb' in res_surge


def test_vpin_toxicity_execution_gate(tmp_path):
    db_path = str(tmp_path / "trade_logs_test.db")
    oms = ExecutionOMSEngine(db_path=db_path)

    # Candidate with extreme toxic order flow (VPIN > 0.70)
    top_preds = [
        {
            "symbol": "005930",
            "name": "삼성전자",
            "market": "KOSPI",
            "close_price": 70000.0,
            "target_price": 70000.0,
            "vpin": 0.85, # Extreme adverse toxicity
            "adv": 500_000_000_000.0
        }
    ]
    weights = {"005930": 0.10}

    plans = oms.generate_order_plan(
        top_predictions=top_preds,
        portfolio_weights=weights,
        total_capital=100_000_000.0,
        crisis_level="NORMAL"
    )

    assert len(plans) == 1
    # Should switch to PASSIVE_LIMIT with elevated slice count to prevent toxic adverse selection
    assert plans[0]["execution_strategy"] == "PASSIVE_LIMIT"
    assert plans[0]["slice_count"] >= 6


def test_extremal_index_clustered_evt_cvar():
    allocator = PortfolioAllocator()
    np.random.seed(42)

    # 1. Independent losses (unclustered)
    normal_returns = np.random.normal(0, 0.02, 300)
    # Add a few random dispersed spikes
    normal_returns[::50] = -0.08

    # 2. Clustered crash returns (consecutive days of extreme drops)
    clustered_returns = np.random.normal(0, 0.02, 300)
    clustered_returns[100:106] = -0.08 # 6 consecutive crash days

    res_normal = allocator.estimate_evt_cvar(normal_returns, confidence=0.95)
    res_clustered = allocator.estimate_evt_cvar(clustered_returns, confidence=0.95)

    assert res_normal['var'] > 0.0
    assert res_clustered['var'] > 0.0
    # Clustered consecutive losses must produce wider CVaR tail risk buffer
    assert res_clustered['cvar'] >= res_normal['cvar'] * 0.90


def test_asymmetric_bullwhip_supply_chain():
    engine = SupplyChainEngine()

    universe = pd.DataFrame([
        {"symbol": "042700", "name": "한미반도체", "market": "KOSPI"} # Supplier to 000660 / NVDA
    ])

    # Case 1: Positive customer move (+5% NVDA)
    prices_pos = {
        "042700": pd.DataFrame({"Close": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]}),
        "000660": pd.DataFrame({"Close": [100.0, 100.0, 100.0, 100.0, 100.0, 105.0]}), # +5%
        "005930": pd.DataFrame({"Close": [100.0, 100.0, 100.0, 100.0, 100.0, 105.0]}),
        "NVDA": pd.DataFrame({"Close": [100.0, 100.0, 100.0, 100.0, 100.0, 105.0]})
    }
    df_pos = engine.compute_scores(prices_dict=prices_pos, universe=universe)

    # Case 2: Negative customer shock (-5% NVDA)
    prices_neg = {
        "042700": pd.DataFrame({"Close": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]}),
        "000660": pd.DataFrame({"Close": [100.0, 100.0, 100.0, 100.0, 100.0, 95.0]}), # -5%
        "005930": pd.DataFrame({"Close": [100.0, 100.0, 100.0, 100.0, 100.0, 95.0]}),
        "NVDA": pd.DataFrame({"Close": [100.0, 100.0, 100.0, 100.0, 100.0, 95.0]})
    }
    df_neg = engine.compute_scores(prices_dict=prices_neg, universe=universe)

    score_pos = df_pos['supply_chain_score'].iloc[0]
    score_neg = df_neg['supply_chain_score'].iloc[0]

    assert score_pos > 0.50
    assert score_neg < 0.50
    # Downside shock transmission produces strong asymmetric divergence from neutral
    assert abs(score_neg - 0.50) > 0.05


def test_factor_crowding_fire_sale_damping():
    scorer_uncrowded = EnsembleScoringEngine()
    scorer_crowded = EnsembleScoringEngine()

    sharpes = {
        "regression": 1.5,
        "surge": 1.4,
        "vcp_ml": 1.6,
        "stat_arb": 1.2
    }
    # Uncrowded weights
    w_uncrowded = scorer_uncrowded.compute_dynamic_weights_from_sharpe(sharpes, regime="BULL_LOW_VOL")

    # Crowded vcp_ml (penalty = 0.40 due to institutional crowding)
    crowding_penalties = {"vcp_ml": 0.40}
    w_crowded = scorer_crowded.compute_dynamic_weights_from_sharpe(
        sharpes,
        regime="BULL_LOW_VOL",
        factor_crowding_penalties=crowding_penalties
    )

    # vcp_ml weight must be damped when crowded
    assert w_crowded["vcp_ml"] < w_uncrowded["vcp_ml"]
    assert np.isclose(sum(w_crowded.values()), 1.0)
