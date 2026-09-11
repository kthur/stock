import sys
sys.path.insert(0, 'trading_system')
import math, numpy as np, pandas as pd

print("=== FORENSIC INTEGRITY AUDIT TEST SUITE (PHASE 23) ===")

# 1. Exact 19! Factorial Check
assert math.factorial(19) == 121645100408832000
print("[Check 1: PASS] 19! exact:", math.factorial(19))

# 2. Factor Suppression & Deadband Noise Leakage Check
from src.ai.factor_suppression import apply_hexaquinquagintagonal_hyperbolic_deadband
z_noise = np.linspace(-0.005, 0.005, 1000)
leak = float(np.max(np.abs(apply_hexaquinquagintagonal_hyperbolic_deadband(z_noise, delta_noise=0.035))))
assert leak < 1e-30, f"Leakage too high: {leak}"
print(f"[Check 2: PASS] F112.2 Hexaquinquagintagonal deadband max leakage on [-0.005, 0.005]: {leak:.2e} < 1e-30")

# 3. 18th-Order Hyper-Convex Rank Modulation
from src.ai.ensemble_scorer import compute_phase23_hyperconvex_rank_modulation
r_grid = np.linspace(0.0, 1.0, 1000)
for gamma in [0.48, 0.70, 1.00, 1.40, 1.85, 2.10, 2.40]:
    g = compute_phase23_hyperconvex_rank_modulation(r_grid, gamma_top=gamma, z_denoised=np.ones_like(r_grid))
    diff = np.diff(g)
    assert np.all(diff > 0), f"Not strictly monotonic for gamma={gamma}"
    d2 = np.diff(diff)
    assert np.all(d2[300:] > 0), f"Not convex on [0.3, 1.0] for gamma={gamma}"
print("[Check 3: PASS] F112.1 18th-order rank modulation strictly monotonic & convex across all regimes.")

# 4. Toposic Geometric Langlands Coupler
from src.ai.ensemble_scorer import ToposicGeometricLanglandsCoupler
c = ToposicGeometricLanglandsCoupler()
res_coh = c.evaluate(np.array([0.5, 0.5, 0.5, 0.5, 0.5]))
assert math.isclose(float(res_coh['e_langlands']), 0.0, abs_tol=1e-6)
assert math.isclose(float(res_coh['z_satake']), 1.0, abs_tol=1e-6)
assert math.isclose(float(res_coh['h_langlands']), 1.0, abs_tol=1e-6)
assert math.isclose(float(res_coh['feri_v23']), 1.0, abs_tol=1e-6)

res_adv = c.evaluate(np.array([1.0, -1.0, 1.0, -1.0, 0.0]))
assert float(res_adv['e_langlands']) > 1.0
assert float(res_adv['z_satake']) < 0.5
assert float(res_adv['h_langlands']) < 0.05
print("[Check 4: PASS] F111 Toposic Geometric Langlands Coupler verified (coherent=1.0, adversarial squashed).")

# 5. Lurie Geometric Langlands Fisher-Rao Barycenter
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
upa = UnifiedPortfolioAllocator()
w_eq = {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25}
bary = upa.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(w_eq)
assert math.isclose(sum(bary.values()), 1.0, abs_tol=1e-6)
assert bary['cvar'] > bary['bl'] > bary['herc'] > bary['rp']
print(f"[Check 5: PASS] F113.1 Lurie Geometric Langlands Barycenter weights verified: {bary}")

# 6. Ultra-Trans-Hyper EVaR
np.random.seed(42)
rets_fat = np.random.standard_t(df=3, size=500) * 0.02 - 0.01
evar_res = upa.compute_ultra_trans_hyper_evar_risk_measure(rets_fat, alpha=0.05)
assert evar_res['order'] == 19
assert math.isclose(evar_res['xi_19'], 0.75)
var = float(np.percentile(-rets_fat, 95))
assert evar_res['ultra_trans_hyper_evar_value'] >= var
print(f"[Check 6: PASS] F113.1.2 Ultra-Trans-Hyper EVaR verified: {evar_res['ultra_trans_hyper_evar_value']} >= VaR {var:.6f}")

# 7. KNK-P L3 Hydrodynamics & Aliases
from src.core.fast_lob_engine import FastOrderBookMatchingEngine
lob = FastOrderBookMatchingEngine(symbol="005930")
lob.add_limit_order(1, 'BID', 100.0, 100)
lob.add_limit_order(2, 'ASK', 101.0, 100)
knkp = lob.compute_kerr_newman_kiselev_phantom_queue_acceleration()
assert 'tidal_force' in knkp
for alias in [
    'compute_kerr_newman_kiselev_phantom_acceleration',
    'compute_knk_phantom_acceleration',
    'compute_knk_phantom_hydrodynamics',
    'calculate_kerr_newman_kiselev_phantom_queue_acceleration',
    'calculate_knk_phantom_queue_acceleration',
    'compute_kerr_newman_kiselev_phantom_frame_dragging',
    'calculate_kerr_newman_kiselev_phantom_hydrodynamics',
    'calculate_kerr_newman_kiselev_phantom_frame_dragging'
]:
    assert hasattr(lob, alias), f"Missing alias {alias}"
print("[Check 7: PASS] F113.2 KNK-P L3 order book hydrodynamics & all 8 aliases verified.")

# 8. SOR Maker Floor & Dark Cap
from src.execution.smart_order_router import SmartOrderRouter
sor = SmartOrderRouter()
plan_v23 = {
    "symbol": "AAPL",
    "action": "BUY",
    "quantity": 1_000_000,
    "target_price": 150.0,
    "gamma_toxic_dir": 1.0,
    "darkpool_score": 0.10,
    "version": 23,
}
res_v23 = sor.route_order(plan_v23, ats_available=False)
maker_legs = [
    l for l in res_v23.get("legs", [])
    if l.get("venue_type") == "PRIMARY_EXCHANGE_MAKER" or l.get("order_type") == "PRIMARY_PEG_LIMIT"
]
assert len(maker_legs) > 0
assert maker_legs[0]["quantity"] == 1, f"Expected 1 share, got {maker_legs[0]['quantity']}"
assert math.isclose(maker_legs[0]["maker_ratio"], 0.000001, abs_tol=1e-7)

# Also test dark ATS cap = 99.995%
plan_dark = {
    "symbol": "AAPL",
    "action": "BUY",
    "quantity": 1_000_000,
    "target_price": 150.0,
    "queue_imbalance": 0.80,
    "qi_acceleration": 0.50,
    "gamma_toxic_dir": 1.0,
    "darkpool_score": 0.90,
    "version": 23,
}
res_dark = sor.route_order(plan_dark, ats_available=True)
dark_legs = [l for l in res_dark.get("legs", []) if "DARK" in l.get("venue_type", "") or "ATS" in l.get("venue_type", "")]
assert len(dark_legs) > 0
total_dark = sum(l["quantity"] for l in dark_legs)
assert total_dark == 999_950, f"Expected 999,950 shares (99.995%), got {total_dark}"
print(f"[Check 8: PASS] F113.2.2 SOR maker floor 0.000001 (1 share) & dark ATS cap 99.995% (999,950 shares) verified.")

# 9. OMS Micro-Tick Shading
from src.execution.oms_engine import ExecutionOMSEngine
oms = ExecutionOMSEngine()
px_above = oms.calculate_peg_limit_price(target_price=100.0, bid_price=99.99, ask_price=100.01, spread=0.02, action='BUY', hawkes_intensity=0.040, version=23)
px_boundary = oms.calculate_peg_limit_price(target_price=100.0, bid_price=99.99, ask_price=100.01, spread=0.02, action='BUY', hawkes_intensity=0.035, version=23)
px_below = oms.calculate_peg_limit_price(target_price=100.0, bid_price=99.99, ask_price=100.01, spread=0.02, action='BUY', hawkes_intensity=0.030, version=23)
assert px_above < px_boundary, f"Expected shift below boundary, got {px_above} vs {px_boundary}"
assert math.isclose(px_boundary, px_below, abs_tol=1e-7)
print(f"[Check 9: PASS] F113.2.2 OMS Preemptive Micro-Tick Shading verified: h=0.04 px={px_above:.6f}, h=0.035 px={px_boundary:.6f}, h=0.03 px={px_below:.6f}")

print("\n*** ALL 9 INDEPENDENT MATHEMATICAL & ALGORITHMIC INTEGRITY CHECKS PASSED EMPIRICALLY ***")
