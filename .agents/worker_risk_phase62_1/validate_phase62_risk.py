import sys
import os
sys.path.insert(0, os.path.abspath("."))

import math
import numpy as np
import pandas as pd

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator

def test_barycenter():
    allocator = UnifiedPortfolioAllocator()
    model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
    blended = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_12_fisher_rao_barycenter_blend(model_weights)
    print("Barycenter result:", blended)
    assert isinstance(blended, dict)
    assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
    assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
    # mu_lmbwdh12 = [5.20, 3.60, 3.55, 5.75]
    assert blended["cvar"] > blended["bl"], f"{blended['cvar']} <= {blended['bl']}"
    assert blended["bl"] > blended["herc"], f"{blended['bl']} <= {blended['herc']}"
    assert blended["herc"] > blended["rp"], f"{blended['herc']} <= {blended['rp']}"
    for k, v in blended.items():
        assert 0.0 < v < 1.0

    # Test input types: 1D array, list of dicts, 2D array
    arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
    res_1d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_12_fisher_rao_barycenter_blend(arr_1d)
    assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

    list_dicts = [
        {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
        {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
    ]
    res_list = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_12_fisher_rao_barycenter_blend(list_dicts)
    assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

    arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
    res_2d = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_12_fisher_rao_barycenter_blend(arr_2d)
    assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)
    print("test_barycenter passed successfully!")

def test_barycenter_aliases():
    allocator = UnifiedPortfolioAllocator()
    w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
    ref = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_12_fisher_rao_barycenter_blend(w)

    upa_aliases = [
        allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_12_barycenter,
        allocator.compute_lurie_drinfeld_higher_homology_12_barycenter,
        allocator.compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_12_fisher_rao_barycenter,
        allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_barycenter,
        allocator.compute_drinfeld_higher_homology_12_barycenter,
        allocator.compute_phase62_fisher_rao_barycenter,
        allocator.compute_phase62_barycenter_blend,
        allocator.compute_higher_homology_12_barycenter,
        allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_fisher_rao_barycenter_blend,
        allocator.compute_motivic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_barycenter_blend,
        allocator.compute_analytic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_barycenter_blend,
        allocator.compute_chiral_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_barycenter_blend,
        allocator.compute_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_barycenter_blend,
        allocator.compute_chiral_oper_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_barycenter_blend,
        allocator.compute_lurie_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_barycenter,
        allocator.compute_lmbmwdh12_barycenter,
        allocator.compute_lmbmwdh12_fisher_rao_barycenter,
        allocator.compute_lmmwdh12_barycenter,
        allocator.compute_lmmwdh12_fisher_rao_barycenter,
        allocator.compute_fisher_rao_barycenter_lmbwdh12,
        allocator.compute_phase62_barycenter,
        allocator.lmbwdh12_barycenter,
        allocator.higher_homology_12_fisher_rao_blend,
        allocator.fisher_rao_higher_homology_12,
        allocator.barycenter_lmbwdh12,
        allocator.blend_weights_lmbwdh12,
        allocator.riemannian_higher_homology_12_barycenter,
        allocator.lmbwd_h12_barycenter,
        allocator.phase62_fisher_rao_barycenter,
        allocator.drinfeld_higher_homology_12_barycenter,
        allocator.borcherds_higher_homology_12_barycenter,
        allocator.monster_higher_homology_12_barycenter,
        allocator.whittaker_higher_homology_12_barycenter,
        allocator.moonshine_higher_homology_12_barycenter,
        allocator.lurie_higher_homology_12_barycenter,
        allocator.higher_homology_12_blend,
        allocator.phase62_homology_barycenter,
    ]
    assert len(upa_aliases) == 37, f"Expected 37 aliases, got {len(upa_aliases)}"
    for fn in upa_aliases:
        res = fn(w)
        for k in ["bl", "herc", "rp", "cvar"]:
            assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    pa = PortfolioAllocator()
    pa_aliases = [
        pa.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_12_fisher_rao_barycenter_blend,
        pa.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_12_barycenter,
        pa.compute_phase62_fisher_rao_barycenter,
        pa.compute_higher_homology_12_barycenter,
        pa.compute_lmbmwdh12_barycenter,
        pa.lmbwdh12_barycenter,
        pa.phase62_homology_barycenter,
        PortfolioAllocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_12_fisher_rao_barycenter_blend,
        PortfolioAllocator.compute_phase62_fisher_rao_barycenter,
        PortfolioAllocator.compute_higher_homology_12_barycenter,
        PortfolioAllocator.compute_phase62_barycenter,
        PortfolioAllocator.lmbwdh12_barycenter,
    ]
    for fn in pa_aliases:
        res = fn(w)
        for k in ["bl", "herc", "rp", "cvar"]:
            assert math.isclose(res[k], ref[k], rel_tol=1e-5)
    print("test_barycenter_aliases passed successfully!")

def test_evar():
    allocator = UnifiedPortfolioAllocator()
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 1000)

    res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_risk_measure(
        returns,
        confidence_level=0.99,
    )
    print("EVaR result:", res)
    assert isinstance(res, dict)
    evar_val = float(res.get(
        "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_value",
        res.get("evar", 0.0)
    ))
    assert math.isfinite(evar_val)
    assert evar_val > 0.0
    assert "evar" in res
    assert "order" in res
    assert res["order"] == 58
    assert "xi_monster" in res
    assert math.isclose(res["xi_monster"], 0.9999999999998)

    # Empty returns
    res_empty = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_risk_measure([])
    assert res_empty["evar"] == 0.0

    # Student-t sensitivity
    norm_rets = np.random.normal(0.0, 0.02, 2000)
    t_rets = np.random.standard_t(df=3, size=2000) * 0.02 / math.sqrt(3)
    evar_norm = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_risk_measure(norm_rets)["evar"]
    evar_t = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_risk_measure(t_rets)["evar"]
    assert evar_t > evar_norm, f"Fat-tailed Student-t EVaR ({evar_t}) must exceed Gaussian EVaR ({evar_norm})"
    print("test_evar passed successfully!")

def test_evar_aliases():
    allocator = UnifiedPortfolioAllocator()
    np.random.seed(123)
    returns = np.random.normal(0.0005, 0.015, 500)
    ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_risk_measure(returns)
    ref_val = ref["evar"]

    upa_evar_aliases = [
        allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar,
        allocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_risk_measure,
        allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_blend,
        allocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar,
        allocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_risk_measure,
        allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase62,
        allocator.compute_phase62_evar,
        allocator.compute_phase62_evar_risk_measure,
        allocator.compute_evar_order58,
        allocator.compute_58th_cumulant_evar,
        allocator.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_risk_measure,
        allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_risk_measure,
        allocator.compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar,
        allocator.compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar,
        allocator.compute_drinfeld_higher_homology_12_evar_risk_measure,
        allocator.compute_drinfeld_higher_homology_12_evar,
        allocator.compute_lurie_drinfeld_higher_homology_12_evar_risk_measure,
        allocator.compute_lurie_drinfeld_higher_homology_12_evar,
        allocator.calculate_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_evar_58th_cumulant,
        allocator.evar_58th_cumulant,
        allocator.trans_singular_58th_cumulant_evar,
        allocator.eternal_omni_cosmic_58th_cumulant_evar,
        allocator.supreme_transcendent_evar_58,
        allocator.phase62_tail_risk_evar,
        allocator.calculate_phase62_evar_tail_risk,
        allocator.cumulant_58_evar_bound,
        allocator.trans_singular_evar_v62,
        allocator.transcendent_58th_cumulant_evar,
        allocator.infinite_supreme_58th_cumulant_evar,
        allocator.omni_cosmic_evar_58,
        allocator.monster_58th_cumulant_evar,
        allocator.higher_homology_12_evar,
        allocator.drinfeld_58th_cumulant_evar,
        allocator.phase62_evar_bound,
        allocator.compute_higher_homology_12_evar,
        allocator.compute_lmbmwdh12_evar,
        allocator.lmbmwdh12_evar,
    ]
    assert len(upa_evar_aliases) == 37, f"Expected 37 EVaR aliases, got {len(upa_evar_aliases)}"
    for fn in upa_evar_aliases:
        res = fn(returns)
        assert math.isclose(res["evar"], ref_val, rel_tol=1e-5)

    pa = PortfolioAllocator()
    pa_evar_aliases = [
        pa.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_12_evar_risk_measure,
        pa.compute_higher_homology_12_evar,
        pa.compute_phase62_evar,
        pa.compute_58th_cumulant_evar,
        pa.evar_58th_cumulant,
        pa.trans_singular_evar_v62,
        PortfolioAllocator.compute_phase62_evar,
        PortfolioAllocator.compute_58th_cumulant_evar,
        PortfolioAllocator.evar_58th_cumulant,
    ]
    for fn in pa_evar_aliases:
        res = fn(returns)
        assert math.isclose(res["evar"], ref_val, rel_tol=1e-5)
    print("test_evar_aliases passed successfully!")

def test_blend_weights():
    allocator = UnifiedPortfolioAllocator()
    market_regime = "BEAR"
    weights_v61 = allocator.compute_information_theoretic_blend_weights(market_regime, version=61)
    weights_v62 = allocator.compute_information_theoretic_blend_weights(market_regime, version=62)
    calc_v62 = allocator.calculate_weights(market_regime, version=62)

    print("Weights v61:", weights_v61)
    print("Weights v62:", weights_v62)
    assert isinstance(weights_v62, dict)
    assert set(weights_v62.keys()) == {"bl", "herc", "rp", "cvar"}
    assert math.isclose(sum(weights_v62.values()), 1.0, rel_tol=1e-5)
    # In BEAR regime with Phase 62, CVaR weight is prioritized and boosted
    assert weights_v62["cvar"] >= weights_v61["cvar"] - 1e-6
    for k, v in weights_v62.items():
        assert 0.0 < v < 1.0
        assert math.isclose(v, calc_v62[k], rel_tol=1e-5)

    # Test backward compatibility for versions 50 to 61
    for v in [61, 60, 59, 58, 57, 56, 55, 54, 53, 52, 51, 50]:
        w = allocator.compute_information_theoretic_blend_weights(
            regime="BULL_LOW_VOL",
            uncertainty=0.1,
            contagion_risk=0.05,
            version=v,
        )
        assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
        for k in ["bl", "herc", "rp", "cvar"]:
            assert 0.0 < w[k] < 1.0
    print("test_blend_weights passed successfully!")

if __name__ == "__main__":
    test_barycenter()
    test_barycenter_aliases()
    test_evar()
    test_evar_aliases()
    test_blend_weights()
    print("\nALL PHASE 62 RISK ALLOCATION VERIFICATION TESTS PASSED 100%!")
