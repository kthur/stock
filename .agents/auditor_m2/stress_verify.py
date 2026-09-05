import sys
import math
import numpy as np
import pandas as pd

sys.path.insert(0, "trading_system")

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.core.fast_lob_engine import FastOrderBookMatchingEngine
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from src.execution.smart_order_router import SmartOrderRouter

alloc = UnifiedPortfolioAllocator()

# 1. R-Vine with zero variance or collinear returns
r_const = np.zeros((20, 4))
res1 = alloc.compute_rvine_tail_cascade_metrics(r_const)
print("Const returns:", res1["lambda_cascade_aggregate"])

# 2. R-Vine with NaN/Inf returns
r_nan = np.random.randn(20, 4)
r_nan[5, 2] = np.nan
r_nan[10, 1] = np.inf
res2 = alloc.compute_rvine_tail_cascade_metrics(r_nan)
print("NaN/Inf returns:", res2["lambda_cascade_aggregate"])

# 3. IEP with extreme values
w_iep = alloc.compute_information_theoretic_blend_weights(
    regime="CRISIS",
    rvine_cascade_index=np.nan,
    tree2_conditional_tail=np.inf,
    version=8
)
print("IEP with NaN/Inf:", w_iep)

# 4. FastLOB with zero or reverse delta-t
engine = FastOrderBookMatchingEngine("STRESS")
engine.add_limit_order("b1", "BUY", 100.0, 100)
engine.add_limit_order("a1", "SELL", 101.0, 100)
res_lob1 = engine.compute_l3_queue_imbalance(timestamp_sec=10.0)
res_lob2 = engine.compute_l3_queue_imbalance(timestamp_sec=10.0)
res_lob3 = engine.compute_l3_queue_imbalance(timestamp_sec=9.0)
print("LOB dt<=0 acceleration:", res_lob2["qi_acceleration"], res_lob3["qi_acceleration"])

# 5. OMS Peg with NaNs
p1 = ExecutionOMSEngine.calculate_peg_limit_price(
    target_price=100.0, bid_price=99.0, ask_price=101.0, spread=2.0,
    action="BUY", qi_acceleration=float("nan"), cross_asset_toxicity=float("inf"), version=8
)
p2 = AlmgrenChrissScheduler.calculate_peg_limit_price(
    target_price=100.0, bid_price=99.0, ask_price=101.0, spread=2.0,
    action="BUY", qi_acceleration=float("nan"), cross_asset_toxicity=float("inf"), version=8
)
print("OMS Peg with NaN/Inf parity:", p1, p2, p1 == p2)

# 6. SOR with extreme inputs
sor = SmartOrderRouter()
res_sor = sor.route_order(
    {"symbol": "STRESS", "action": "BUY", "quantity": 1000, "target_price": 50.0, "version": 8},
    qi_acceleration=float("nan"), cross_asset_toxicity=float("inf"), version=8
)
print("SOR with NaN/Inf:", res_sor["effective_dark_ratio"], res_sor["maker_ratio"])
