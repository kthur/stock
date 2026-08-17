"""
System Architecture Unit Tests (v0.2 Enterprise Enhancements)

Tests FeatureDriftDetector, PreTradeRiskGatekeeper, and VectorizedFeatureEngine.
"""

import numpy as np
import pandas as pd

from src.ai.drift_detector import FeatureDriftDetector
from src.risk.pretrade_gatekeeper import PreTradeRiskGatekeeper, ProposedOrder
from src.utils.vectorized_ops import VectorizedFeatureEngine


def test_feature_drift_detector_psi():
    detector = FeatureDriftDetector(psi_threshold=0.25)

    # Identical distributions -> low PSI
    baseline = np.random.normal(0, 1, 1000)
    current_same = np.random.normal(0, 1, 1000)
    psi_same = detector.calculate_psi(baseline, current_same)
    assert psi_same < 0.1, f"Expected low PSI for identical distribution, got {psi_same}"

    # Shifted distribution -> high PSI
    current_shifted = np.random.normal(3, 1, 1000)
    psi_shifted = detector.calculate_psi(baseline, current_shifted)
    assert psi_shifted >= 0.25, f"Expected high PSI for shifted distribution, got {psi_shifted}"


def test_feature_drift_detector_dataframe():
    detector = FeatureDriftDetector(psi_threshold=0.25)
    df_base = pd.DataFrame({"f1": np.random.normal(0, 1, 500), "f2": np.random.normal(5, 2, 500)})
    df_curr = pd.DataFrame({"f1": np.random.normal(0, 1, 500), "f2": np.random.normal(15, 2, 500)})

    res = detector.analyze_dataframe_drift(df_base, df_curr, feature_cols=["f1", "f2"])
    assert "f1" in res and "f2" in res
    assert res["f1"]["status"] in ["NO_DRIFT", "MODERATE_DRIFT"]
    assert res["f2"]["has_significant_drift"] is True


def test_pretrade_risk_gatekeeper():
    gatekeeper = PreTradeRiskGatekeeper(
        max_single_stock_weight=0.15,
        max_order_adv_pct=0.05,
        enable_crisis_gating=True,
    )

    # Order exceeding max weight -> should be clamped
    order_large_w = ProposedOrder(
        symbol="005930",
        target_weight=0.25,
        expected_return=0.10,
        current_price=70000.0,
        order_size_shares=100,
        avg_daily_volume_20d=1_000_000,
    )
    res = gatekeeper.evaluate_order(order_large_w, portfolio_value=100_000_000.0, is_crisis_mode=False)
    assert res.passed is True
    assert res.adjusted_weight == 0.15

    # Crisis mode active -> should reject order completely
    res_crisis = gatekeeper.evaluate_order(order_large_w, portfolio_value=100_000_000.0, is_crisis_mode=True)
    assert res_crisis.passed is False
    assert res_crisis.adjusted_weight == 0.0


def test_vectorized_ops_rsi_and_bb():
    prices = np.array([100.0 + i + (i % 3) * 2.0 for i in range(50)])

    rsi = VectorizedFeatureEngine.rsi_vectorized(prices, period=14)
    assert len(rsi) == len(prices)
    assert np.all((rsi >= 0.0) & (rsi <= 100.0))

    upper, sma, lower = VectorizedFeatureEngine.bollinger_bands_vectorized(prices, window=20)
    assert len(upper) == len(prices)
    assert np.all(upper >= lower)

    df = pd.DataFrame({"close": prices})
    df_out = VectorizedFeatureEngine.compute_fast_indicators(df)
    assert "rsi_14" in df_out.columns
    assert "bb_upper" in df_out.columns
