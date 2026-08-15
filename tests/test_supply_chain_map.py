"""
test_supply_chain_map.py — Unit and integration tests for SupplyChainEngine with JSON mapping database
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.core.supply_chain import SupplyChainEngine, LEAD_CUSTOMER_MAP


def test_supply_chain_engine_loads_json_map():
    """Verify that SupplyChainEngine loads the JSON map correctly."""
    engine = SupplyChainEngine()
    assert len(engine.customer_map) >= 30, "Supply chain map should have at least 30 symbols mapped."
    assert "005930" in engine.customer_map
    assert "042700" in engine.customer_map
    assert "NVDA" in engine.customer_map


def test_supply_chain_weighted_momentum_calculation():
    """Verify weighted spillover momentum calculation based on customer returns."""
    engine = SupplyChainEngine()

    dates = pd.date_range("2026-01-01", periods=10, freq="B")
    
    # Simulate a scenario where 000660 (SK Hynix) and 005930 (Samsung) have strong positive returns
    # and Hanmi Semiconductor (042700) is evaluated
    df_prices = pd.DataFrame({
        "005930": [100, 101, 102, 103, 104, 105, 106, 108, 110, 115],  # +4.5% 1d, +8.4% 3d
        "000660": [200, 201, 203, 205, 207, 210, 212, 216, 220, 230],  # +4.5% 1d, +8.4% 3d
        "NVDA": [1000, 1010, 1020, 1030, 1040, 1050, 1060, 1080, 1100, 1150],
        "042700": [50, 51, 52, 53, 54, 55, 56, 57, 58, 59],
        "999999": [10, 10, 10, 10, 10, 10, 10, 10, 10, 10], # unmapped
    }, index=dates)

    universe_df = pd.DataFrame({
        "symbol": ["042700", "999999"],
        "name": ["Hanmi Semi", "Unmapped Stock"],
        "market": ["KOSPI", "KOSPI"]
    })

    res = engine.compute_scores(df_prices=df_prices, universe=universe_df)
    assert not res.empty
    assert "supply_chain_score" in res.columns
    
    hanmi_score = res.loc[res["symbol"] == "042700", "supply_chain_score"].iloc[0]
    unmapped_score = res.loc[res["symbol"] == "999999", "supply_chain_score"].iloc[0]

    # Hanmi Semiconductor should have a bullish score (> 0.50) due to lead customers rising
    assert hanmi_score > 0.55, f"Expected Hanmi score > 0.55, got {hanmi_score}"
    # Unmapped symbol should default to 0.50
    assert unmapped_score == 0.50, f"Expected unmapped score == 0.50, got {unmapped_score}"
