import sys
sys.path.insert(0, '.')
import math
import numpy as np
import pandas as pd

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
import trading_system.src.risk.unified_portfolio_allocator as upa_mod
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator

alloc = UnifiedPortfolioAllocator()

# --- TEST 1: F243.1 Barycenter properties ---
w = {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25}
b = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_4_fisher_rao_barycenter_blend(w)
assert set(b.keys()) == {'bl', 'herc', 'rp', 'cvar'}, 'Keys mismatch'
assert math.isclose(sum(b.values()), 1.0, rel_tol=1e-5), f'Sum not 1.0: {sum(b.values())}'
assert b['cvar'] > b['bl'] > b['herc'] > b['rp'], f'Curvature ordering mismatch: {b}'
for k, v in b.items():
    assert 0.0 < v < 1.0, f'Interior point violation: {k}={v}'
print('Test 1: F243.1 barycenter properties PASSED')

# --- TEST 2: F243.1 Barycenter input types ---
res_1d = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_4_fisher_rao_barycenter_blend(np.array([0.3, 0.2, 0.2, 0.3]))
assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

list_dicts = [{'bl': 0.3, 'herc': 0.2, 'rp': 0.2, 'cvar': 0.3}, {'bl': 0.2, 'herc': 0.3, 'rp': 0.1, 'cvar': 0.4}]
res_list = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_4_fisher_rao_barycenter_blend(list_dicts)
assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
res_2d = alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_4_fisher_rao_barycenter_blend(arr_2d)
assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)
print('Test 2: F243.1 barycenter input types PASSED')

# --- TEST 3: F243.1 Barycenter aliases on UnifiedPortfolioAllocator & PortfolioAllocator ---
upa_b_aliases = [
    alloc.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_4_barycenter,
    alloc.compute_lurie_drinfeld_higher_homology_4_barycenter,
    alloc.compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_4_fisher_rao_barycenter,
    alloc.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter,
    alloc.compute_drinfeld_higher_homology_4_barycenter,
    alloc.compute_phase54_fisher_rao_barycenter,
    alloc.compute_phase54_barycenter_blend,
    alloc.compute_higher_homology_4_barycenter,
    alloc.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_fisher_rao_barycenter_blend,
    alloc.compute_motivic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter_blend,
    alloc.compute_analytic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter_blend,
    alloc.compute_chiral_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter_blend,
    alloc.compute_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter_blend,
    alloc.compute_chiral_oper_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter_blend,
    alloc.compute_lurie_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter,
    alloc.compute_lmbmwdh4_barycenter,
    alloc.compute_lmbmwdh4_fisher_rao_barycenter,
    alloc.compute_lmmwdh4_barycenter,
    alloc.compute_lmmwdh4_fisher_rao_barycenter,
]
assert len(upa_b_aliases) == 19
for fn in upa_b_aliases:
    res = fn(w)
    for k in w:
        assert math.isclose(res[k], b[k], rel_tol=1e-5)

pa_b_aliases = [
    PortfolioAllocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_4_fisher_rao_barycenter_blend,
    PortfolioAllocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_4_barycenter,
    PortfolioAllocator.compute_lurie_drinfeld_higher_homology_4_barycenter,
    PortfolioAllocator.compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_4_fisher_rao_barycenter,
    PortfolioAllocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter,
    PortfolioAllocator.compute_drinfeld_higher_homology_4_barycenter,
    PortfolioAllocator.compute_phase54_fisher_rao_barycenter,
    PortfolioAllocator.compute_phase54_barycenter_blend,
    PortfolioAllocator.compute_higher_homology_4_barycenter,
    PortfolioAllocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_fisher_rao_barycenter_blend,
    PortfolioAllocator.compute_motivic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter_blend,
    PortfolioAllocator.compute_analytic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter_blend,
    PortfolioAllocator.compute_chiral_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter_blend,
    PortfolioAllocator.compute_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter_blend,
    PortfolioAllocator.compute_chiral_oper_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter_blend,
    PortfolioAllocator.compute_lurie_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_barycenter,
    PortfolioAllocator.compute_lmbmwdh4_barycenter,
    PortfolioAllocator.compute_lmbmwdh4_fisher_rao_barycenter,
    PortfolioAllocator.compute_lmmwdh4_barycenter,
    PortfolioAllocator.compute_lmmwdh4_fisher_rao_barycenter,
]
assert len(pa_b_aliases) == 20
for fn in pa_b_aliases:
    res = fn(w)
    for k in w:
        assert math.isclose(res[k], b[k], rel_tol=1e-5)
print('Test 3: F243.1 barycenter aliases PASSED')

# --- TEST 4: F243.2 EVaR properties and aliases ---
np.random.seed(42)
rets = np.random.normal(0.001, 0.02, 500)
res_evar = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_risk_measure(rets)
evar_val = res_evar['evar']
assert math.isfinite(evar_val) and evar_val > 0.0
assert res_evar['order'] == 50
assert math.isclose(res_evar['xi_monster'], 0.9999999998, rel_tol=1e-8)

upa_evar_aliases = [
    alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar,
    alloc.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_risk_measure,
    alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_blend,
    alloc.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar,
    alloc.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_risk_measure,
    alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase54,
    alloc.compute_phase54_evar,
    alloc.compute_phase54_evar_risk_measure,
    alloc.compute_evar_order50,
    alloc.compute_50th_cumulant_evar,
    alloc.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_risk_measure,
    alloc.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_risk_measure,
    alloc.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar,
    alloc.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar,
    alloc.compute_drinfeld_higher_homology_4_evar_risk_measure,
    alloc.compute_drinfeld_higher_homology_4_evar,
    alloc.compute_lurie_drinfeld_higher_homology_4_evar_risk_measure,
    alloc.compute_lurie_drinfeld_higher_homology_4_evar,
]
assert len(upa_evar_aliases) == 18
for fn in upa_evar_aliases:
    val = fn(rets)['evar']
    assert math.isclose(val, evar_val, rel_tol=1e-5)

pa_evar_aliases = [
    PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_risk_measure,
    PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar,
    PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_risk_measure,
    PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_blend,
    PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar,
    PortfolioAllocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_risk_measure,
    PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase54,
    PortfolioAllocator.compute_phase54_evar,
    PortfolioAllocator.compute_phase54_evar_risk_measure,
    PortfolioAllocator.compute_evar_order50,
    PortfolioAllocator.compute_50th_cumulant_evar,
    PortfolioAllocator.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_risk_measure,
    PortfolioAllocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_risk_measure,
    PortfolioAllocator.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar,
    PortfolioAllocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar,
    PortfolioAllocator.compute_drinfeld_higher_homology_4_evar_risk_measure,
    PortfolioAllocator.compute_drinfeld_higher_homology_4_evar,
    PortfolioAllocator.compute_lurie_drinfeld_higher_homology_4_evar_risk_measure,
    PortfolioAllocator.compute_lurie_drinfeld_higher_homology_4_evar,
]
assert len(pa_evar_aliases) == 19
for fn in pa_evar_aliases:
    val = fn(rets)['evar']
    assert math.isclose(val, evar_val, rel_tol=1e-5)
print('Test 4: F243.2 EVaR properties and aliases PASSED')

# --- TEST 5: Student-t heavy tail monotonicity ---
t_rets = np.random.standard_t(df=3, size=1000) * 0.015 + 0.0005
gauss_rets = np.random.normal(0.0005, 0.015, 1000)
evar_t = alloc.compute_50th_cumulant_evar(t_rets)['evar']
evar_g = alloc.compute_50th_cumulant_evar(gauss_rets)['evar']
assert evar_t > evar_g, f'Student-t EVaR ({evar_t}) <= Gauss ({evar_g})'
print('Test 5: Student-t heavy tail monotonicity PASSED')

# --- TEST 6: Degenerate EVaR inputs ---
assert alloc.compute_50th_cumulant_evar([])['evar'] == 0.0
assert alloc.compute_50th_cumulant_evar([0.05])['evar'] == 0.0
assert alloc.compute_50th_cumulant_evar([np.nan, np.nan])['evar'] == 0.0
print('Test 6: Degenerate EVaR inputs PASSED')

# --- TEST 7: Dynamic blend weights version=54 ---
w_v53 = alloc.compute_information_theoretic_blend_weights('BEAR', version=53)
w_v54 = alloc.compute_information_theoretic_blend_weights('BEAR', version=54)
calc_v54 = alloc.calculate_weights('BEAR', version=54)
assert math.isclose(sum(w_v54.values()), 1.0, rel_tol=1e-5)
assert w_v54['cvar'] >= w_v53['cvar'] - 1e-6, f"CVaR not prioritized: v54={w_v54['cvar']}, v53={w_v53['cvar']}"
for k in w_v54:
    assert math.isclose(w_v54[k], calc_v54[k], rel_tol=1e-5)
    assert 0.0 < w_v54[k] < 1.0

for reg in ['BULL_LOW_VOL', 'BULL_HIGH_VOL', 'CRISIS', 'SIDEWAYS']:
    wr = alloc.compute_information_theoretic_blend_weights(reg, version=54)
    assert math.isclose(sum(wr.values()), 1.0, rel_tol=1e-5)
    for v in wr.values():
        assert 0.0 < v < 1.0
print('Test 7: Dynamic blend weights version=54 PASSED')

print('ALL PHASE 54 TESTS PASSED PERFECTLY!')
