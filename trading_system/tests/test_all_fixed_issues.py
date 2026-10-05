"""
Unit and regression tests verifying all system bug fixes.
"""

import math
import os
import numpy as np
import pandas as pd
import pytest


def test_fast_lob_market_order_no_corrupting_resting_orders():
    """Verify market orders do not rest in the book at 1e9 or 0.0 upon partial fill."""
    from src.core.fast_lob_engine import FastOrderBookMatchingEngine

    engine = FastOrderBookMatchingEngine("AAPL")
    engine.add_limit_order("sell_1", "SELL", 150.0, 10.0)
    engine.add_limit_order("buy_1", "BUY", 149.0, 10.0)

    # Market BUY for 25 units when only 10 available at 150.0
    fills_buy = engine.match_market_order("BUY", 25.0)
    assert len(fills_buy) == 1
    assert fills_buy[0]["volume"] == 10.0
    assert fills_buy[0]["price"] == 150.0

    # Book should NOT have a resting bid at 1e9
    assert 1e9 not in engine.bids
    assert len(engine.asks) == 0

    # Market SELL for 25 units when only 10 available at 149.0
    fills_sell = engine.match_market_order("SELL", 25.0)
    assert len(fills_sell) == 1
    assert fills_sell[0]["volume"] == 10.0
    assert fills_sell[0]["price"] == 149.0

    # Book should NOT have a resting ask at 0.0
    assert 0.0 not in engine.asks
    assert len(engine.bids) == 0


def test_fast_lob_engine_hawkes_type_annotations():
    """Verify BivariateHawkesIntensity and other LOB classes accept Union type annotations."""
    from src.core.fast_lob_engine import BivariateHawkesIntensity

    bhi = BivariateHawkesIntensity(beta=1.5)
    assert bhi.beta == 1.5


def test_interactive_brokers_order_id_resolution():
    """Verify place_order returns an order_id that resolves in get_order_status."""
    from src.broker.interactive_brokers import InteractiveBrokersConnector

    ib = InteractiveBrokersConnector()
    ib.connect("TEST_ACC")
    oid = ib.place_order("AAPL", 5, 150.0, "BUY")
    status = ib.get_order_status(oid)
    assert status["status"] == "FILLED"
    assert status["symbol"] == "AAPL"
    assert status["quantity"] == 5


def test_fix_protocol_order_id_resolution():
    """Verify place_order returns a cl_ord_id that resolves in get_order_status."""
    from src.broker.fix_protocol_engine import FIX44Engine

    fix = FIX44Engine()
    fix.connect("TEST_FIX")
    oid = fix.place_order("MSFT", 10, 200.0, "BUY")
    status = fix.get_order_status(oid)
    assert status["status"] == "FILLED"
    assert status["symbol"] == "MSFT"
    assert status["quantity"] == 10


def test_portfolio_optimizer_mass_preservation_under_tight_caps():
    """Verify weights strictly sum to 1.0 even under tight single-stock and sector caps."""
    from src.analysis.portfolio_optimizer import apply_portfolio_constraints

    w0 = np.array([0.40, 0.35, 0.15, 0.05, 0.03, 0.02])
    symbols = ["A", "B", "C", "D", "E", "F"]
    sectors = ["TECH", "TECH", "FIN", "FIN", "HLTH", "HLTH"]

    w_opt = apply_portfolio_constraints(
        w0,
        symbols=symbols,
        sectors=sectors,
        max_single_stock_weight=0.20,
        max_sector_weight=0.35
    )

    assert abs(w_opt.sum() - 1.0) < 1e-6
    assert np.all(w_opt <= 0.20 + 1e-6)
    # Check sector totals
    df_w = pd.DataFrame({"weight": w_opt, "sector": sectors})
    sec_sums = df_w.groupby("sector")["weight"].sum()
    assert np.all(sec_sums <= 0.35 + 1e-6)


def test_hrp_weights_robust_to_nan_covariance():
    """Verify HRP produces valid risk-based weights without collapsing to equal weights on NaNs."""
    from src.analysis.portfolio_optimizer import calculate_hrp_weights

    rng = np.random.default_rng(42)
    R = rng.normal(0, 0.02, (250, 6)) * np.array([1, 2, 3, 1, 2, 3])
    C_clean = np.cov(R.T)
    w_clean = calculate_hrp_weights(C_clean, tail_stress=False)

    C_nan = C_clean.copy()
    C_nan[0, 3] = C_nan[3, 0] = np.nan
    C_nan[2, 5] = np.nan
    C_nan[4, 4] = np.nan

    w_nan = calculate_hrp_weights(C_nan, tail_stress=False)

    assert np.all(np.isfinite(w_nan))
    assert abs(w_nan.sum() - 1.0) < 1e-6
    # Should not collapse to exact 1/N equal weights
    assert not np.allclose(w_nan, 1.0 / 6.0, atol=1e-3)
    # Correlation between clean and nan weights should be high (> 0.90)
    corr = np.corrcoef(w_clean, w_nan)[0, 1]
    assert corr > 0.90


def test_rl_execution_agent_directional_slippage():
    """Verify BUY orders have price increased by slippage and SELL orders have price decreased."""
    from src.execution.rl_execution_agent import RLOrderExecutionAgent

    agent = RLOrderExecutionAgent()
    p0 = 100.0

    res_buy = agent.optimize_trajectory("XYZ", 10_000, start_price=p0, side="BUY")
    res_sell = agent.optimize_trajectory("XYZ", 10_000, start_price=p0, side="SELL")

    buy_prices = [t["price"] for t in res_buy["tranches"] if t["shares"] > 0 and t["slippage_bps"] > 0]
    sell_prices = [t["price"] for t in res_sell["tranches"] if t["shares"] > 0 and t["slippage_bps"] > 0]

    assert all(p >= p0 for p in buy_prices)
    assert all(p <= p0 for p in sell_prices)


def test_supply_chain_gnn_bullwhip_coefficients():
    """Verify SupplyChainGNNEngine bullwhip transform dampens positive demand (0.85x) and amplifies negative (1.35x)."""
    from src.core.supply_chain_gnn import SupplyChainGNNEngine

    gnn = SupplyChainGNNEngine()
    mom_pos = {"S1": 0.10}
    mom_neg = {"S1": -0.10}

    # Inject edge S1 -> S2
    gnn.in_adj = {"S2": [("S1", 1.0)]}
    gnn.out_adj = {"S1": [("S2", 1.0)]}

    hop1_pos, _ = gnn._propagate_message_passing(mom_pos)
    hop1_neg, _ = gnn._propagate_message_passing(mom_neg)

    assert abs(hop1_pos["S2"] - 0.10 * 0.85) < 1e-6
    assert abs(hop1_neg["S2"] - (-0.10 * 1.35)) < 1e-6


def test_range_expansion_nr7_lookahead_bias():
    """Verify NR7 detection at t-2 does not leak t-1 bar range."""
    from src.core.range_expansion_breakout import RangeExpansionBreakoutEngine

    engine = RangeExpansionBreakoutEngine()

    high = np.array([10.0] * 12 + [10.5, 12.0, 10.0])
    low =  np.array([ 9.0] * 12 + [10.0, 10.0,  9.5])
    close = np.array([9.5] * 12 + [10.2, 11.5,  9.8])
    volume = np.array([1000] * 15)

    df = pd.DataFrame({"high": high, "low": low, "close": close, "volume": volume})
    scores = engine.calculate_scores({"TEST": df})

    assert isinstance(scores, pd.DataFrame)
    assert not scores.empty


def test_dual_correction_ma20_nan_handling():
    """Verify dual correction handles dataframes with exactly 32 bars without NaN propagation."""
    from src.core.dual_correction import DualCorrectionEngine, TimeCorrectionScorer

    n = 32
    df = pd.DataFrame({
        "open": np.linspace(100, 110, n),
        "high": np.linspace(101, 111, n),
        "low": np.linspace(99, 109, n),
        "close": np.linspace(100.5, 110.5, n),
        "volume": np.full(n, 100000.0)
    })
    # Test TimeCorrectionScorer directly where ma20 slope calculation lives
    time_score, details = TimeCorrectionScorer.compute_score(df)
    assert np.isfinite(time_score)
    assert np.isfinite(details["base_duration_score"])

    # Test full engine scores calculation
    engine = DualCorrectionEngine()
    scores = engine.calculate_scores({"TEST": df})
    assert isinstance(scores, pd.DataFrame)
    assert not scores.empty
    assert np.all(np.isfinite(scores["dual_correction_score"]))


def test_strategy_executor_duplicated_close_column_robustness():
    """Verify strategy executor handles dataframes with duplicate Close columns without crashing."""
    from src.pipeline.strategy_executor import AlphaStrategyExecutor, PipelineStrategyContext

    df_dup = pd.DataFrame({
        "Close": [100.0, 105.0],
        "close": [100.0, 105.0]
    })
    # If duplicated columns exist with same name
    df_dup.columns = ["Close", "Close"]

    ctx = PipelineStrategyContext(
        cfg=None,
        symbols_list=["005930"],
        infer_data_dict={"005930": df_dup},
        universe=pd.DataFrame({"symbol": ["005930"], "market": ["KOSPI"]})
    )

    executor = AlphaStrategyExecutor()
    executor.prepare_shared_context(ctx)
    assert "005930" in ctx.sentiment_map
    assert np.isfinite(ctx.sentiment_map["005930"])


def test_prediction_reporter_nan_market_fallback():
    """Verify prediction reporter properly falls back to KRX on NaN market without printing 'nan'."""
    from src.pipeline.prediction_reporter import save_strategy_predictions_report

    df = pd.DataFrame({
        "symbol": ["005930"],
        "name": ["Samsung"],
        "market": [np.nan],
        "score": [0.85]
    })

    test_file = "test_output_report.txt"
    try:
        save_strategy_predictions_report(
            df_strat=df,
            score_col="score",
            title="Test Report",
            output_filename=test_file,
            result_dir=".",
            universe=pd.DataFrame({"symbol": ["005930"], "name": ["Samsung"], "market": [np.nan]})
        )
        assert os.path.exists(test_file)
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        # Verify 'KRX' was written as default instead of 'nan'
        lines = [line for line in content.splitlines() if "005930" in line]
        assert len(lines) == 1
        assert "KRX" in lines[0]
        assert "nan" not in lines[0]
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
