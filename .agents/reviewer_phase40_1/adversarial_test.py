import sys
import os
sys.path.insert(0, os.path.abspath("."))
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
from trading_system.src.ai.factor_suppression import (
    apply_octacontatetragonal_hyperbolic_deadband,
    compute_phase40_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v40,
)
from trading_system.src.ai.ensemble_scorer import (
    GeometricLanglandsHodgeDeligneCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator

print("=== 1. CHECK FACTORIAL 36 SPECIFICATION ===")
f36_exact = math.factorial(36)
f36_expected = 37199332678990123746787777307803520000000
print(f"Mathematical 36!: {f36_exact}")
print(f"Specification:    {f36_expected}")
# Check that code uses the specification constant exactly as specified in ORIGINAL_REQUEST.md
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
import inspect
upa_src = inspect.getsource(UnifiedPortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure)
assert "37199332678990123746787777307803520000000" in upa_src, "fact_36 constant missing or mismatched in source!"
print("Factorial 36 specification adherence: PASS")

print("=== 2. ADVERSARIAL DEADBAND STRESS TEST ===")
np.random.seed(999)
noise_samples = np.random.uniform(-0.0004, 0.0004, 1000)
denoised = apply_octacontatetragonal_hyperbolic_deadband(noise_samples)
max_leakage = np.max(np.abs(denoised))
print(f"Max leakage across 1000 random noise samples in [-0.0004, 0.0004]: {max_leakage}")
assert max_leakage < 1e-68, f"Leakage exceeded 1e-68: {max_leakage}"
print("Deadband leakage: PASS")

print("=== 3. ADVERSARIAL RANK MODULATION TEST ===")
r = np.sort(np.random.uniform(0.0, 1.0, 10000))
gamma = get_regime_adaptive_gamma_top_v40('BULL_LOW_VOL')
g = compute_phase40_hyperconvex_rank_modulation(r, gamma_top=gamma)
diffs = np.diff(g)
assert np.all(diffs >= 0), "Rank modulation not strictly monotonic!"
g_oob = compute_phase40_hyperconvex_rank_modulation(np.array([-0.5, 1.5]), gamma_top=gamma)
assert np.isclose(g_oob[0], 0.50), "Lower clipping failed!"
assert np.isclose(g_oob[1], 0.50 + 1.45 * np.exp(gamma)), "Upper clipping failed!"
print("Rank modulation: PASS")

print("=== 4. ADVERSARIAL BARYCENTER TEST ===")
alloc = UnifiedPortfolioAllocator()
corners = [
    {'bl': 1.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 0.0},
    {'bl': 0.0, 'herc': 1.0, 'rp': 0.0, 'cvar': 0.0},
    {'bl': 0.0, 'herc': 0.0, 'rp': 1.0, 'cvar': 0.0},
    {'bl': 0.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 1.0},
    {'bl': 1e-12, 'herc': 1e-12, 'rp': 1e-12, 'cvar': 1e-12},
    np.array([100.0, 200.0, 300.0, 400.0]),
]
for c in corners:
    res = alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(c)
    s = sum(res.values())
    assert math.isclose(s, 1.0, rel_tol=1e-5), f"Simplex violated for {c}: {s}"
    assert all(v > 0 for v in res.values()), f"Non-positive weight: {res}"
print("Barycenter corner cases: PASS")

print("=== 5. ADVERSARIAL EVAR 36 vs 35 HIERARCHY TEST ===")
for seed in [1, 42, 123, 777, 9999]:
    np.random.seed(seed)
    rets = np.random.standard_t(df=3, size=300) * 0.02 - 0.005
    evar36 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(rets, alpha=0.05)['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value']
    evar35 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(rets, alpha=0.05)['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value']
    assert evar36 >= evar35 - 1e-6, f"Seed {seed}: EVaR 36 ({evar36}) < EVaR 35 ({evar35})"
print("EVaR 36 >= EVaR 35 across multiple fat-tailed distributions: PASS")

print("=== 6. ADVERSARIAL HODGE-DELIGNE COUPLER TEST ===")
coupler = GeometricLanglandsHodgeDeligneCoupler()
res_id = coupler(np.array([0.2, 0.2, 0.2, 0.2, 0.2]))
assert np.isclose(res_id['e_hodge'], 0.0), "Obstruction energy on identical inputs must be 0"
assert np.isclose(res_id['h_deligne'], 1.0), "Coupling on identical inputs must be 1.0"
res_disp = coupler(np.array([10.0, -10.0, 10.0, -10.0, 10.0]))
assert res_disp['e_hodge'] > 100.0, "Extreme dispersion must yield high energy"
assert res_disp['h_deligne'] < 1e-5, "Extreme dispersion must suppress coupling"
print("Hodge-Deligne Coupler math: PASS")

print("=== 7. INTEGRITY / HARCODING CHECK ===")
# Ensure outputs are not identical fixed constants across different inputs
r1 = np.random.normal(0, 1, 100)
r2 = np.random.normal(1, 2, 100)
ev1 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r1)['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value']
ev2 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(r2)['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value']
assert not np.isclose(ev1, ev2), "EVaR outputs appear to be hardcoded identical constants!"
print("No hardcoding detected in EVaR: PASS")

print("ALL ADVERSARIAL AND INTEGRITY TESTS PASSED!")
