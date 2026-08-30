"""
Adversarial Stress Testing Script for Milestone 1 Strategy Engines.
Tests extreme inputs, numerical instabilities, NaN/Inf handling, boundary violations,
and non-linear edge cases.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add paths
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir / "trading_system"))
sys.path.insert(0, str(root_dir / "trading_system" / "src"))
sys.path.insert(0, str(root_dir))

from src.core.cross_asset_spillover import CrossAssetSpilloverEngine, cross_asset_spillover_score
from src.core.supply_chain_gnn import SupplyChainGNNEngine, supply_chain_gnn_score
from src.core.range_expansion_breakout import RangeExpansionBreakoutEngine, range_expansion_score
from src.core.strategy_registry import get_registry


def run_stress_tests():
    print("=== STARTING ADVERSARIAL STRESS TESTS ===")
    failures = []

    # -------------------------------------------------------------
    # Test 1: NaN, Inf, Zero, and Negative Prices
    # -------------------------------------------------------------
    print("\n--- Test 1: Corrupted Price Feeds (NaN, Inf, Negatives) ---")
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    
    # NaN dataframe
    df_nan = pd.DataFrame({
        "Open": [np.nan] * 30,
        "High": [np.nan] * 30,
        "Low": [np.nan] * 30,
        "Close": [np.nan] * 30,
        "Volume": [np.nan] * 30,
    }, index=dates)

    # Inf dataframe
    df_inf = pd.DataFrame({
        "Open": [np.inf] * 30,
        "High": [np.inf] * 30,
        "Low": [-np.inf] * 30,
        "Close": [np.inf] * 30,
        "Volume": [np.inf] * 30,
    }, index=dates)

    # Negative / zero prices
    df_neg = pd.DataFrame({
        "Open": [-10.0] * 30,
        "High": [0.0] * 30,
        "Low": [-20.0] * 30,
        "Close": [-5.0] * 30,
        "Volume": [0.0] * 30,
    }, index=dates)

    corrupted_dict = {"NAN_SYM": df_nan, "INF_SYM": df_inf, "NEG_SYM": df_neg}

    for name, engine in [
        ("CrossAssetSpillover", CrossAssetSpilloverEngine()),
        ("SupplyChainGNN", SupplyChainGNNEngine()),
        ("RangeExpansion", RangeExpansionBreakoutEngine()),
    ]:
        try:
            res = engine.compute_scores(prices_dict=corrupted_dict)
            col = [c for c in res.columns if "score" in c][0]
            scores = res[col].values
            print(f"[{name}] Corrupted input handled gracefully. Scores: {dict(zip(res['symbol'], scores))}")
            for sym, sc in zip(res['symbol'], scores):
                if not (0.05 <= sc <= 0.95):
                    failures.append(f"[{name}] Score out of bounds on {sym}: {sc}")
                if np.isnan(sc) or np.isinf(sc):
                    failures.append(f"[{name}] Score is NaN/Inf on {sym}: {sc}")
        except Exception as e:
            failures.append(f"[{name}] Crash on corrupted input: {e}")

    # -------------------------------------------------------------
    # Test 2: Extreme Macro Indicator Outliers
    # -------------------------------------------------------------
    print("\n--- Test 2: Extreme Macro Indicator Outliers ---")
    spillover_engine = CrossAssetSpilloverEngine()
    df_normal = pd.DataFrame({
        "Open": [100.0] * 30,
        "High": [105.0] * 30,
        "Low": [95.0] * 30,
        "Close": [100.0] * 30,
        "Volume": [100000.0] * 30,
    }, index=dates)

    extreme_indicators = {
        "sox_change": 9999.0,
        "wti_change": -99.9,
        "tnx_change": 500.0,
        "usdkrw_change": -80.0,
        "vix_change": 1000.0,
        "sp500_change": -90.0,
        "gold_change": 200.0,
        "dxy_change": 50.0,
    }

    try:
        res = spillover_engine.compute_scores(
            prices_dict={"TEST_SEMI": df_normal},
            indicators_df=extreme_indicators,
            sector_map={"TEST_SEMI": "Semiconductor"}
        )
        sc = res["cross_asset_spillover_score"].iloc[0]
        print(f"[CrossAssetSpillover] Extreme indicator score: {sc}")
        if not (0.05 <= sc <= 0.95) or np.isnan(sc):
            failures.append(f"[CrossAssetSpillover] Extreme indicator test failed: {sc}")
    except Exception as e:
        failures.append(f"[CrossAssetSpillover] Extreme indicator crash: {e}")

    # -------------------------------------------------------------
    # Test 3: Relational Graph Cyclic and Self-Loop Stress
    # -------------------------------------------------------------
    print("\n--- Test 3: Cyclic, Self-Loop, and Disconnected Graph ---")
    cyclic_edges = [
        ("A", "B", 0.9),
        ("B", "C", 0.9),
        ("C", "A", 0.9),
        ("A", "A", 0.5), # self loop
    ]
    gnn_engine = SupplyChainGNNEngine(custom_edges=cyclic_edges)
    df_a = pd.DataFrame({"Close": np.linspace(100, 150, 30), "Volume": [1000.0]*30}, index=dates)
    df_b = pd.DataFrame({"Close": np.linspace(100, 80, 30), "Volume": [1000.0]*30}, index=dates)
    df_c = pd.DataFrame({"Close": [100.0]*30, "Volume": [1000.0]*30}, index=dates)

    try:
        res = gnn_engine.compute_scores(prices_dict={"A": df_a, "B": df_b, "C": df_c})
        for sym, sc in zip(res["symbol"], res["supply_chain_gnn_score"]):
            print(f"[SupplyChainGNN] Cyclic graph node {sym}: {sc}")
            if not (0.05 <= sc <= 0.95) or np.isnan(sc):
                failures.append(f"[SupplyChainGNN] Cyclic test failed on {sym}: {sc}")
    except Exception as e:
        failures.append(f"[SupplyChainGNN] Cyclic graph crash: {e}")

    # -------------------------------------------------------------
    # Test 4: Flatline Zero-Variance Range Expansion
    # -------------------------------------------------------------
    print("\n--- Test 4: Flatline & Zero-Variance OHLCV ---")
    re_engine = RangeExpansionBreakoutEngine()
    df_flat = pd.DataFrame({
        "Open": [100.0] * 30,
        "High": [100.0] * 30,
        "Low": [100.0] * 30,
        "Close": [100.0] * 30,
        "Volume": [0.0] * 30,
    }, index=dates)

    try:
        res = re_engine.compute_scores(prices_dict={"FLAT": df_flat})
        sc = res["range_expansion_score"].iloc[0]
        print(f"[RangeExpansion] Flatline score: {sc}")
        if not (0.05 <= sc <= 0.95) or np.isnan(sc):
            failures.append(f"[RangeExpansion] Flatline test failed: {sc}")
    except Exception as e:
        failures.append(f"[RangeExpansion] Flatline crash: {e}")

    # -------------------------------------------------------------
    # Test 5: High Volume Scale (1000 Tickers)
    # -------------------------------------------------------------
    print("\n--- Test 5: High Universe Scale (1,000 symbols) ---")
    np.random.seed(42)
    large_prices = {}
    for i in range(1000):
        sym = f"SYM_{i:04d}"
        c = 100.0 * np.cumprod(1.0 + np.random.normal(0, 0.02, 25))
        large_prices[sym] = pd.DataFrame({
            "Open": c,
            "High": c * 1.01,
            "Low": c * 0.99,
            "Close": c,
            "Volume": np.random.uniform(10000, 50000, 25),
        }, index=dates[:25])

    for name, engine in [
        ("CrossAssetSpillover", CrossAssetSpilloverEngine()),
        ("SupplyChainGNN", SupplyChainGNNEngine()),
        ("RangeExpansion", RangeExpansionBreakoutEngine()),
    ]:
        import time
        t0 = time.time()
        res = engine.compute_scores(prices_dict=large_prices)
        elapsed = time.time() - t0
        col = [c for c in res.columns if "score" in c][0]
        scores = res[col].values
        print(f"[{name}] 1,000 symbols processed in {elapsed:.3f}s. Min: {scores.min():.4f}, Max: {scores.max():.4f}, Mean: {scores.mean():.4f}")
        if len(res) != 1000:
            failures.append(f"[{name}] Universe size mismatch: expected 1000, got {len(res)}")
        if not ((scores >= 0.05).all() and (scores <= 0.95).all()):
            failures.append(f"[{name}] Boundary failure in large universe test")

    print("\n=== STRESS TEST SUMMARY ===")
    if not failures:
        print("ALL ADVERSARIAL STRESS TESTS PASSED (CLEAN).")
        return True
    else:
        print(f"FAILURES DETECTED ({len(failures)}):")
        for f in failures:
            print(f" - {f}")
        return False


if __name__ == "__main__":
    success = run_stress_tests()
    sys.exit(0 if success else 1)
