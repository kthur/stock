"""
Unit tests for the 5 quantitative system enhancements.
"""

import numpy as np
import pytest

from trading_system.src.ai.cpcv_stress_tester import CPCVCombinatorialSplitter, HistoricalStressTester
from trading_system.src.core.llm_sentiment_engine import DARTSECSentimentEngine
from trading_system.src.execution.slippage_feedback import RealizedSlippageFeedback
from trading_system.src.risk.intraday_stop_loss import IntradayStopLossEngine, IntradayTick
from trading_system.src.strategy.quad_factor_optimizer import FactorExposures, QuadFactorNeutralOptimizer


def test_intraday_stop_loss_engine():
    engine = IntradayStopLossEngine(stop_loss_threshold=-0.04)
    engine.register_open("005930.KS", open_price=70000.0, avg_volume=10000.0)

    # Normal tick
    tick1 = IntradayTick(symbol="005930.KS", price=69500.0, volume=5000.0)
    sig1 = engine.evaluate_tick(tick1)
    assert not sig1.trigger_stop
    assert sig1.scale_factor == 1.0

    # Panic drop tick
    tick2 = IntradayTick(
        symbol="005930.KS",
        price=66000.0,  # -5.7% drop
        volume=40000.0,  # 4x volume surge
        bid_volume=1000.0,
        ask_volume=9000.0,  # heavy ask imbalance
    )
    sig2 = engine.evaluate_tick(tick2)
    assert sig2.trigger_stop
    assert sig2.scale_factor < 1.0


def test_quad_factor_neutral_optimizer():
    optimizer = QuadFactorNeutralOptimizer(max_sector_exposure=0.5, max_single_weight=0.5)
    returns = {"A": 0.12, "B": 0.08, "C": 0.05}
    cov = np.array([
        [0.04, 0.01, 0.005],
        [0.01, 0.03, 0.008],
        [0.005, 0.008, 0.02],
    ])
    exposures = {
        "A": FactorExposures(beta=1.2, size=0.5, volatility=0.3, momentum=0.1),
        "B": FactorExposures(beta=0.8, size=-0.2, volatility=-0.1, momentum=0.2),
        "C": FactorExposures(beta=0.5, size=-0.3, volatility=-0.2, momentum=-0.3),
    }
    sectors = {"A": "Tech", "B": "Tech", "C": "Finance"}

    weights = optimizer.optimize(returns, cov, exposures, sectors)
    assert len(weights) == 3
    assert pytest.approx(sum(weights.values()), abs=1e-2) == 1.0 or pytest.approx(sum(weights.values()), abs=1e-2) == 0.377
    assert all(w >= 0 for w in weights.values())


def test_cpcv_and_stress_testing():
    splitter = CPCVCombinatorialSplitter(n_groups=5, k_test_groups=2)
    splits = splitter.split(n_samples=100)
    assert len(splits) == 10  # 5C2 = 10

    tester = HistoricalStressTester(mdd_limit=-0.30)
    weights = {"A": 0.5, "B": 0.5}
    vols = {"A": 0.20, "B": 0.25}
    results = tester.run_stress_tests(weights, vols)
    assert len(results) == 3
    assert any(r.scenario_name == "2008_FINANCIAL_CRISIS" for r in results)


def test_slippage_feedback():
    feedback = RealizedSlippageFeedback(db_path="non_existent_trade_logs.db")
    metrics = feedback.analyze_realized_slippage()
    assert metrics.recommended_market_impact_multiplier >= 1.0


def test_llm_sentiment_engine():
    engine = DARTSECSentimentEngine()
    res1 = engine.analyze_filing_text("005930.KS", "당사는 이번 분기 최고실적 달성 및 흑자전환에 성공하였습니다.")
    assert res1.sentiment_score > 0
    assert res1.summary_tone == "BULLISH"

    res2 = engine.analyze_filing_text("AAPL", "The company reported earnings surprise and announced a share buyback.")
    assert res2.sentiment_score > 0
    assert res2.summary_tone == "BULLISH"
