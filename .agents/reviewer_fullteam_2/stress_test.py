"""
Adversarial stress test suite for Reviewer 2:
Validating Microstructure L3 OMS/SOR, Hawkes, and Quant Benchmark robustness.
"""
import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root / "trading_system"))
sys.path.insert(0, str(root))

import math
import numpy as np
import pandas as pd

from src.core.fast_lob_engine import DeepHawkesArrivalProcess, FastOrderBookMatchingEngine
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from src.execution.slippage_feedback import SlippageFeedbackEngine
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator

def main():
    print("=== ADVERSARIAL STRESS TEST START ===")

    # 1. FastLOBEngine under extreme book conditions
    engine = FastOrderBookMatchingEngine(symbol="TEST")
    res1 = engine.compute_l3_queue_imbalance()
    assert res1["l3_queue_imbalance"] == 0.0
    assert res1["qi_acceleration"] == 0.0
    print("[PASS] 1. Empty book L3 imbalance returns 0.0 without crashing")

    # Add orders with identical timestamps (dt = 0)
    engine.add_limit_order("o1", "BUY", 100.0, 10, timestamp_ns=1000)
    engine.add_limit_order("o2", "SELL", 105.0, 10, timestamp_ns=1000)
    res2 = engine.compute_l3_queue_imbalance(timestamp_sec=1.0)
    res3 = engine.compute_l3_queue_imbalance(timestamp_sec=1.0) # dt = 0
    assert math.isfinite(res3["qi_velocity"])
    assert math.isfinite(res3["qi_acceleration"])
    assert math.isfinite(res3["qi_jerk"])
    print("[PASS] 2. Zero dt queue acceleration handled cleanly without DivByZero")

    # 2. DeepHawkesArrivalProcess extreme inputs
    hawkes = DeepHawkesArrivalProcess(version=15)
    # Test baseline
    res_h1 = hawkes.compute_preemptive_dark_routing(version=15)
    assert 0.65 <= res_h1["preemptive_dark_routing_ratio"] <= 0.99
    print(f"[PASS] 3. Default DeepHawkes ratio: {res_h1['preemptive_dark_routing_ratio']}")

    # Push high LIT events to trigger maximum toxicity
    hawkes_toxic = DeepHawkesArrivalProcess(mu=np.array([100.0, 0.1, 0.1]), version=15)
    res_h2 = hawkes_toxic.compute_preemptive_dark_routing(version=15)
    assert res_h2["preemptive_dark_routing_ratio"] == 0.99
    print(f"[PASS] 4. Toxic DeepHawkes dark ratio capped at 0.99: {res_h2['preemptive_dark_routing_ratio']}")

    # 3. SmartOrderRouter adversarial inputs
    sor = SmartOrderRouter()
    res_empty = sor.route_order({})
    assert res_empty["total_quantity"] == 0
    assert len(res_empty["legs"]) == 0
    print("[PASS] 5. SmartOrderRouter empty order handling")

    res_extreme = sor.route_order({
        "symbol": "XYZ",
        "action": "BUY",
        "quantity": 1000,
        "target_price": 100.0,
        "gamma_toxic_dir": 999.0, # extreme toxicity
        "darkpool_score": 10.0,
        "version": 15
    })
    assert res_extreme["legs"][0]["quantity"] <= 1000
    assert res_extreme["legs"][0]["min_quantity"] <= 1000
    print(f"[PASS] 6. SmartOrderRouter extreme toxicity legs generated: {len(res_extreme['legs'])}")

    # 4. OMS Hawkes Peg calculation under extreme inputs
    oms = ExecutionOMSEngine()
    peg_extreme = oms.calculate_peg_limit_price(
        target_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        action="BUY",
        hawkes_intensity=1e9,
        version=15
    )
    assert 99.0 <= peg_extreme <= 101.0
    print(f"[PASS] 7. ExecutionOMSEngine peg price strictly clipped: {peg_extreme}")

    # Crossed book edge case (bid > ask)
    peg_crossed = oms.calculate_peg_limit_price(
        target_price=100.0,
        bid_price=102.0,
        ask_price=98.0,
        action="BUY",
        version=15
    )
    assert 98.0 <= peg_crossed <= 102.0
    print(f"[PASS] 8. ExecutionOMSEngine peg price handles crossed bid/ask: {peg_crossed}")

    # 5. SlippageFeedbackEngine missing or corrupt DB fallback
    sf = SlippageFeedbackEngine(db_path="non_existent_fake_db.db")
    m = sf.calculate_realized_slippage()
    assert m.sample_count == 0
    assert m.avg_slippage_bps == 5.0
    print("[PASS] 9. SlippageFeedbackEngine missing DB fallback verified")

    # 6. UnifiedPortfolioAllocator Langlands Barycenter and Supra-Transfinite EVaR
    allocator = UnifiedPortfolioAllocator()
    bary_deg = allocator.compute_langlands_automorphic_fisher_rao_barycenter_blend({"bl": 0, "herc": 0, "rp": 0, "cvar": 0})
    assert math.isclose(sum(bary_deg.values()), 1.0, abs_tol=1e-5)
    print(f"[PASS] 10. Langlands barycenter degenerate all-zero: {bary_deg}")

    evar_nan = allocator.compute_supra_transfinite_evar_risk_measure(np.array([np.nan, np.inf, -np.inf]))
    assert math.isfinite(evar_nan["supra_transfinite_evar_value"])
    print(f"[PASS] 11. Supra-Transfinite EVaR handles non-finite inputs: {evar_nan['supra_transfinite_evar_value']}")

    print("=== ALL 11 ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
