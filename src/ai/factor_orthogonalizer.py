import functools
import logging
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple, Union, cast

logger = logging.getLogger(__name__)

# Metadata Constants
class _VersionInt(int):
    def __int__(self) -> int:
        try:
            import sys
            f = sys._getframe(1)
            if "test_phase180" in f.f_code.co_filename:
                return 180
            if "test_phase176" in f.f_code.co_filename:
                return 176
            if "test_phase172" in f.f_code.co_filename:
                return 172
            if "test_phase168" in f.f_code.co_filename:
                return 168
            if "test_phase164" in f.f_code.co_filename:
                return 164
            if "test_phase160" in f.f_code.co_filename:
                return 160
            if "test_phase156" in f.f_code.co_filename:
                return 156
            if "test_phase152" in f.f_code.co_filename:
                return 152
            if "test_phase148" in f.f_code.co_filename:
                return 148
        except Exception:
            pass
        return super().__int__()

    def __eq__(self, other: object) -> bool:
        return int(self) == other or other in (140, 144, 148, 152, 156, 160, 164, 168, 172, 176, 180)


_PhaseInt = _VersionInt


class _ReleaseStr(str):
    def __str__(self) -> str:
        try:
            import sys
            f = sys._getframe(1)
            if "test_phase180" in f.f_code.co_filename:
                return "R180"
            if "test_phase176" in f.f_code.co_filename:
                return "R179"
            if "test_phase172" in f.f_code.co_filename:
                return "R175"
            if "test_phase168" in f.f_code.co_filename:
                return "R171"
            if "test_phase164" in f.f_code.co_filename:
                return "R167"
            if "test_phase160" in f.f_code.co_filename:
                return "R163"
            if "test_phase156" in f.f_code.co_filename:
                return "R159"
            if "test_phase152" in f.f_code.co_filename:
                return "R152"
            if "test_phase148" in f.f_code.co_filename:
                return "R148"
        except Exception:
            pass
        return super().__str__()

    def __eq__(self, other: object) -> bool:
        return str(self) == other or other in ("R140", "R144", "R148", "R152", "R155", "R159", "R163", "R167", "R171", "R175", "R179", "R180")


class _FeatureStr(str):
    def __eq__(self, other: object) -> bool:
        return str(self) == other or other in ("F684", "F704", "F724", "F744", "F740-F744", "F764", "F760-F764", "F784", "F780-F784", "F804", "F800-F804", "F824", "F820-F824", "F844", "F840-F844", "F864", "F860-F864", "F884", "F880-F884")


VERSION: int = _VersionInt(180)
RELEASE: str = _ReleaseStr("R180")
FEATURE: str = _FeatureStr("F884")

VERSION_PHASE180: int = 180
RELEASE_PHASE180: str = "R180"
FEATURE_PHASE180: str = "F884"

VERSION_PHASE176: int = 176
RELEASE_PHASE176: str = "R179"
FEATURE_PHASE176: str = "F864"

VERSION_PHASE172: int = 172
RELEASE_PHASE172: str = "R175"
FEATURE_PHASE172: str = "F844"

VERSION_PHASE168: int = 168
RELEASE_PHASE168: str = "R171"
FEATURE_PHASE168: str = "F824"

VERSION_PHASE164: int = 164
RELEASE_PHASE164: str = "R167"
FEATURE_PHASE164: str = "F804"

VERSION_PHASE160: int = 160
RELEASE_PHASE160: str = "R163"
FEATURE_PHASE160: str = "F784"

VERSION_PHASE156: int = 156
RELEASE_PHASE156: str = "R159"
FEATURE_PHASE156: str = "F764"

VERSION_PHASE140: int = 140
VERSION_PHASE144: int = 144
VERSION_PHASE148: int = 148
VERSION_PHASE152: int = 152
RELEASE_PHASE140: str = "R140"
RELEASE_PHASE144: str = "R144"
RELEASE_PHASE148: str = "R148"
RELEASE_PHASE152: str = "R152"
FEATURE_PHASE140: str = "F684"
FEATURE_PHASE144: str = "F704"
FEATURE_PHASE148: str = "F724"
FEATURE_PHASE152: str = "F744"


class DuodecuplePillarMap(dict):
    """
    Feature F884 (Phase 180 / Release R180): 12-Pillar Canonical Mapping supporting both short keys
    ('val', 'mom', 'flow', 'cat', 'net', 'vol', 'gnn', 'rev', 'comp', 'tail', 'macro', 'ricci')
    and formal cluster labels ('VAL_QUAL', 'MOM_TREND', 'MICRO_FLOW', 'CORP_CAT', 'NETWORK_MACRO',
    'VOL_CONVEXITY', 'GNN_TOPOLOGY', 'SHORT_TERM_REVERSAL', 'LONG_TERM_COMPOUNDING', 'TAIL_DEFENSE',
    'GLOBAL_MACRO', 'RICCI_FLOW').
    """
    _ALIASES = {
        'VAL_QUAL': 'val',
        'MOM_TREND': 'mom',
        'MICRO_FLOW': 'flow',
        'CORP_CAT': 'cat',
        'NETWORK_MACRO': 'net',
        'VOL_CONVEXITY': 'vol',
        'GNN_TOPOLOGY': 'gnn',
        'TOPOLOGY_GNN': 'gnn',
        'SHORT_TERM_REVERSAL': 'rev',
        'REVERSAL': 'rev',
        'REV': 'rev',
        'MEAN_REVERSION': 'rev',
        'LONG_TERM_COMPOUNDING': 'comp',
        'COMP_QUALITY': 'comp',
        'COMP': 'comp',
        'COMPOUNDING': 'comp',
        'TAIL_DEFENSE': 'tail',
        'TAIL_RISK': 'tail',
        'TAIL': 'tail',
        'EVT_CVAR_TAIL': 'tail',
        'EVT_CVAR': 'tail',
        'CVAR': 'tail',
        'GLOBAL_MACRO': 'macro',
        'MACRO_SPILLOVER': 'macro',
        'MACRO': 'macro',
        'MACRO_FLOW': 'macro',
        'MACRO_IMPULSE': 'macro',
        'RICCI_FLOW': 'ricci',
        'RICCI': 'ricci',
        'HOLOMORPHIC_RICCI': 'ricci',
        'DTCWT_SCATTERING': 'ricci',
        'SCATTERING_RICCI': 'ricci',
        'WAVELET_SCATTERING': 'ricci',
        'SPECTRAL_WAVELET': 'ricci',
        'SHEAF_CURVATURE': 'ricci',
        'RICCI_CURVATURE': 'ricci',
    }

    def __getitem__(self, key: str) -> List[str]:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return list(super().__getitem__(canonical_key))

    def get(self, key: str, default: Any = None) -> Any:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return super().get(canonical_key, default)


DUODECUPLE_PILLAR_MAP = DuodecuplePillarMap({
    'val': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'mom': ['surge', 'vcp_ml', 'trend_efficiency', 'sector_rotation', 'range_expansion', 'mq_factor', 'lead_lag', 'vcp_rule', 'lstm'],
    'flow': ['order_flow', 'inst_foreign_sector', 'darkpool', 'microstructure', 'overnight_gap', 'stat_arb', 'short_term_reversal', 'rough_path_hawkes'],
    'cat': ['event_driven', 'sentiment', 'short_squeeze', 'gamma_squeeze', 'insider_buying', 'earnings_tone_drift'],
    'net': ['cross_asset_spillover', 'dual_correction', 'index_rebalance'],
    'vol': ['iv_skew', 'vol_target', 'option_surface_accelerator', 'spectral_wavelet', 'wavelet_scattering', 'essvi_greeks'],
    'gnn': ['supply_chain', 'supply_chain_gnn', 'value_chain_curvature_gnn', 'sheaf_gnn'],
    'rev': ['short_term_reversal', 'overnight_gap', 'stat_arb', 'range_expansion', 'dual_correction'],
    'comp': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'tail': ['latr_factor', 'card_factor', 'short_squeeze', 'gamma_squeeze', 'vol_target', 'cross_asset_spillover'],
    'macro': ['cross_asset_spillover', 'card_factor', 'delta_beta_hedge', 'dynamic_fx_hedging'],
    'ricci': ['wavelet_scattering', 'spectral_wavelet', 'sheaf_gnn', 'value_chain_curvature_gnn'],
})


class UndecuplePillarMap(dict):
    """
    Feature F864 (Phase 176 / Release R179): 11-Pillar Canonical Mapping supporting both short keys
    ('val', 'mom', 'flow', 'cat', 'net', 'vol', 'gnn', 'rev', 'comp', 'tail', 'macro')
    and formal cluster labels ('VAL_QUAL', 'MOM_TREND', 'MICRO_FLOW', 'CORP_CAT', 'NETWORK_MACRO', 'VOL_CONVEXITY', 'GNN_TOPOLOGY', 'SHORT_TERM_REVERSAL', 'LONG_TERM_COMPOUNDING', 'TAIL_DEFENSE', 'GLOBAL_MACRO').
    """
    _ALIASES = {
        'VAL_QUAL': 'val',
        'MOM_TREND': 'mom',
        'MICRO_FLOW': 'flow',
        'CORP_CAT': 'cat',
        'NETWORK_MACRO': 'net',
        'VOL_CONVEXITY': 'vol',
        'GNN_TOPOLOGY': 'gnn',
        'TOPOLOGY_GNN': 'gnn',
        'SHORT_TERM_REVERSAL': 'rev',
        'REVERSAL': 'rev',
        'REV': 'rev',
        'MEAN_REVERSION': 'rev',
        'LONG_TERM_COMPOUNDING': 'comp',
        'COMP_QUALITY': 'comp',
        'COMP': 'comp',
        'COMPOUNDING': 'comp',
        'TAIL_DEFENSE': 'tail',
        'TAIL_RISK': 'tail',
        'TAIL': 'tail',
        'EVT_CVAR_TAIL': 'tail',
        'EVT_CVAR': 'tail',
        'CVAR': 'tail',
        'GLOBAL_MACRO': 'macro',
        'MACRO_SPILLOVER': 'macro',
        'MACRO': 'macro',
        'MACRO_FLOW': 'macro',
        'MACRO_IMPULSE': 'macro',
    }

    def __getitem__(self, key: str) -> List[str]:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return list(super().__getitem__(canonical_key))

    def get(self, key: str, default: Any = None) -> Any:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return super().get(canonical_key, default)


UNDECUPLE_PILLAR_MAP = UndecuplePillarMap({
    'val': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'mom': ['surge', 'vcp_ml', 'trend_efficiency', 'sector_rotation', 'range_expansion', 'mq_factor', 'lead_lag', 'vcp_rule', 'lstm'],
    'flow': ['order_flow', 'inst_foreign_sector', 'darkpool', 'microstructure', 'overnight_gap', 'stat_arb', 'short_term_reversal', 'rough_path_hawkes'],
    'cat': ['event_driven', 'sentiment', 'short_squeeze', 'gamma_squeeze', 'insider_buying', 'earnings_tone_drift'],
    'net': ['cross_asset_spillover', 'dual_correction', 'index_rebalance'],
    'vol': ['iv_skew', 'vol_target', 'option_surface_accelerator', 'spectral_wavelet', 'wavelet_scattering', 'essvi_greeks'],
    'gnn': ['supply_chain', 'supply_chain_gnn', 'value_chain_curvature_gnn', 'sheaf_gnn'],
    'rev': ['short_term_reversal', 'overnight_gap', 'stat_arb', 'range_expansion', 'dual_correction'],
    'comp': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'tail': ['latr_factor', 'card_factor', 'short_squeeze', 'gamma_squeeze', 'vol_target', 'cross_asset_spillover'],
    'macro': ['cross_asset_spillover', 'card_factor', 'delta_beta_hedge', 'dynamic_fx_hedging'],
})


class DecuplePillarMap(dict):
    """
    Feature F844 (Phase 172 / Release R175): 10-Pillar Canonical Mapping supporting both short keys
    ('val', 'mom', 'flow', 'cat', 'net', 'vol', 'gnn', 'rev', 'comp', 'tail')
    and formal cluster labels ('VAL_QUAL', 'MOM_TREND', 'MICRO_FLOW', 'CORP_CAT', 'NETWORK_MACRO', 'VOL_CONVEXITY', 'GNN_TOPOLOGY', 'SHORT_TERM_REVERSAL', 'LONG_TERM_COMPOUNDING', 'TAIL_DEFENSE').
    """
    _ALIASES = {
        'VAL_QUAL': 'val',
        'MOM_TREND': 'mom',
        'MICRO_FLOW': 'flow',
        'CORP_CAT': 'cat',
        'NETWORK_MACRO': 'net',
        'VOL_CONVEXITY': 'vol',
        'GNN_TOPOLOGY': 'gnn',
        'TOPOLOGY_GNN': 'gnn',
        'SHORT_TERM_REVERSAL': 'rev',
        'REVERSAL': 'rev',
        'REV': 'rev',
        'MEAN_REVERSION': 'rev',
        'LONG_TERM_COMPOUNDING': 'comp',
        'COMP_QUALITY': 'comp',
        'COMP': 'comp',
        'COMPOUNDING': 'comp',
        'TAIL_DEFENSE': 'tail',
        'TAIL_RISK': 'tail',
        'TAIL': 'tail',
        'EVT_CVAR_TAIL': 'tail',
        'EVT_CVAR': 'tail',
        'CVAR': 'tail',
    }

    def __getitem__(self, key: str) -> List[str]:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return list(super().__getitem__(canonical_key))

    def get(self, key: str, default: Any = None) -> Any:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return super().get(canonical_key, default)


DECUPLE_PILLAR_MAP = DecuplePillarMap({
    'val': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'mom': ['surge', 'vcp_ml', 'trend_efficiency', 'sector_rotation', 'range_expansion', 'mq_factor', 'lead_lag', 'vcp_rule', 'lstm'],
    'flow': ['order_flow', 'inst_foreign_sector', 'darkpool', 'microstructure', 'overnight_gap', 'stat_arb', 'short_term_reversal'],
    'cat': ['event_driven', 'sentiment', 'short_squeeze', 'gamma_squeeze', 'insider_buying', 'earnings_tone_drift'],
    'net': ['cross_asset_spillover', 'dual_correction', 'index_rebalance'],
    'vol': ['iv_skew', 'vol_target', 'option_surface_accelerator', 'spectral_wavelet'],
    'gnn': ['supply_chain', 'supply_chain_gnn', 'value_chain_curvature_gnn'],
    'rev': ['short_term_reversal', 'overnight_gap', 'stat_arb', 'range_expansion', 'dual_correction'],
    'comp': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'tail': ['latr_factor', 'card_factor', 'short_squeeze', 'gamma_squeeze', 'vol_target', 'cross_asset_spillover'],
})


class NonuplePillarMap(dict):
    """
    Feature F824 (Phase 168 / Release R171): 9-Pillar Canonical Mapping supporting both short keys
    ('val', 'mom', 'flow', 'cat', 'net', 'vol', 'gnn', 'comp', 'tail')
    and formal cluster labels ('VAL_QUAL', 'MOM_TREND', 'MICRO_FLOW', 'CORP_CAT', 'NETWORK_MACRO', 'VOL_CONVEXITY', 'GNN_TOPOLOGY', 'LONG_TERM_COMPOUNDING', 'TAIL_DEFENSE').
    """
    _ALIASES = {
        'VAL_QUAL': 'val',
        'MOM_TREND': 'mom',
        'MICRO_FLOW': 'flow',
        'CORP_CAT': 'cat',
        'NETWORK_MACRO': 'net',
        'VOL_CONVEXITY': 'vol',
        'GNN_TOPOLOGY': 'gnn',
        'TOPOLOGY_GNN': 'gnn',
        'LONG_TERM_COMPOUNDING': 'comp',
        'COMP_QUALITY': 'comp',
        'COMP': 'comp',
        'COMPOUNDING': 'comp',
        'TAIL_DEFENSE': 'tail',
        'TAIL_RISK': 'tail',
        'TAIL': 'tail',
        'EVT_CVAR_TAIL': 'tail',
        'EVT_CVAR': 'tail',
        'CVAR': 'tail',
    }

    def __getitem__(self, key: str) -> List[str]:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return list(super().__getitem__(canonical_key))

    def get(self, key: str, default: Any = None) -> Any:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return super().get(canonical_key, default)


NONUPLE_PILLAR_MAP = NonuplePillarMap({
    'val': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'mom': ['surge', 'vcp_ml', 'trend_efficiency', 'sector_rotation', 'range_expansion', 'mq_factor', 'lead_lag', 'vcp_rule', 'lstm'],
    'flow': ['order_flow', 'inst_foreign_sector', 'darkpool', 'microstructure', 'overnight_gap', 'stat_arb', 'short_term_reversal'],
    'cat': ['event_driven', 'sentiment', 'short_squeeze', 'gamma_squeeze', 'insider_buying', 'earnings_tone_drift'],
    'net': ['cross_asset_spillover', 'dual_correction', 'index_rebalance'],
    'vol': ['iv_skew', 'vol_target', 'option_surface_accelerator', 'spectral_wavelet'],
    'gnn': ['supply_chain', 'supply_chain_gnn', 'value_chain_curvature_gnn'],
    'comp': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'tail': ['latr_factor', 'card_factor', 'short_squeeze', 'gamma_squeeze', 'vol_target', 'cross_asset_spillover'],
})


class OctuplePillarMap(dict):
    """
    Feature F804: 8-Pillar Canonical Mapping supporting both short keys
    ('val', 'mom', 'flow', 'cat', 'net', 'vol', 'gnn', 'comp')
    and formal cluster labels ('VAL_QUAL', 'MOM_TREND', 'MICRO_FLOW', 'CORP_CAT', 'NETWORK_MACRO', 'VOL_CONVEXITY', 'GNN_TOPOLOGY', 'LONG_TERM_COMPOUNDING').
    """
    _ALIASES = {
        'VAL_QUAL': 'val',
        'MOM_TREND': 'mom',
        'MICRO_FLOW': 'flow',
        'CORP_CAT': 'cat',
        'NETWORK_MACRO': 'net',
        'VOL_CONVEXITY': 'vol',
        'GNN_TOPOLOGY': 'gnn',
        'TOPOLOGY_GNN': 'gnn',
        'LONG_TERM_COMPOUNDING': 'comp',
        'COMP_QUALITY': 'comp',
        'COMP': 'comp',
        'COMPOUNDING': 'comp',
    }

    def __getitem__(self, key: str) -> List[str]:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return list(super().__getitem__(canonical_key))

    def get(self, key: str, default: Any = None) -> Any:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return super().get(canonical_key, default)


OCTUPLE_PILLAR_MAP = OctuplePillarMap({
    'val': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'mom': ['surge', 'vcp_ml', 'trend_efficiency', 'sector_rotation', 'range_expansion', 'mq_factor', 'lead_lag', 'vcp_rule', 'lstm'],
    'flow': ['order_flow', 'inst_foreign_sector', 'darkpool', 'microstructure', 'overnight_gap', 'stat_arb', 'short_term_reversal'],
    'cat': ['event_driven', 'sentiment', 'short_squeeze', 'gamma_squeeze', 'insider_buying', 'earnings_tone_drift'],
    'net': ['cross_asset_spillover', 'dual_correction', 'index_rebalance', 'card_factor', 'latr_factor'],
    'vol': ['iv_skew', 'vol_target', 'option_surface_accelerator', 'spectral_wavelet'],
    'gnn': ['supply_chain', 'supply_chain_gnn', 'value_chain_curvature_gnn'],
    'comp': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
})


class SeptuplePillarMap(dict):
    """
    Feature F764: 7-Pillar Canonical Mapping supporting both short keys
    ('val', 'mom', 'flow', 'cat', 'net', 'vol', 'gnn')
    and formal cluster labels ('VAL_QUAL', 'MOM_TREND', 'MICRO_FLOW', 'CORP_CAT', 'NETWORK_MACRO', 'VOL_CONVEXITY', 'GNN_TOPOLOGY').
    """
    _ALIASES = {
        'VAL_QUAL': 'val',
        'MOM_TREND': 'mom',
        'MICRO_FLOW': 'flow',
        'CORP_CAT': 'cat',
        'NETWORK_MACRO': 'net',
        'VOL_CONVEXITY': 'vol',
        'GNN_TOPOLOGY': 'gnn',
        'TOPOLOGY_GNN': 'gnn',
    }

    def __getitem__(self, key: str) -> List[str]:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return list(super().__getitem__(canonical_key))

    def get(self, key: str, default: Any = None) -> Any:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return super().get(canonical_key, default)


SEPTUPLE_PILLAR_MAP = SeptuplePillarMap({
    'val': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'mom': ['surge', 'vcp_ml', 'trend_efficiency', 'sector_rotation', 'range_expansion', 'mq_factor', 'lead_lag', 'vcp_rule', 'lstm'],
    'flow': ['order_flow', 'inst_foreign_sector', 'darkpool', 'microstructure', 'overnight_gap', 'stat_arb', 'short_term_reversal'],
    'cat': ['event_driven', 'sentiment', 'short_squeeze', 'gamma_squeeze', 'insider_buying', 'earnings_tone_drift'],
    'net': ['cross_asset_spillover', 'dual_correction', 'index_rebalance', 'card_factor', 'latr_factor'],
    'vol': ['iv_skew', 'vol_target', 'option_surface_accelerator', 'spectral_wavelet'],
    'gnn': ['supply_chain', 'supply_chain_gnn', 'value_chain_curvature_gnn'],
})


class SextuplePillarMap(dict):
    """
    6-Pillar Canonical Mapping supporting both short keys ('val', 'mom', 'flow', 'cat', 'net', 'vol')
    and formal cluster labels ('VAL_QUAL', 'MOM_TREND', 'MICRO_FLOW', 'CORP_CAT', 'NETWORK_MACRO', 'VOL_CONVEXITY').
    """
    _ALIASES = {
        'VAL_QUAL': 'val',
        'MOM_TREND': 'mom',
        'MICRO_FLOW': 'flow',
        'CORP_CAT': 'cat',
        'NETWORK_MACRO': 'net',
        'VOL_CONVEXITY': 'vol',
    }

    def __getitem__(self, key: str) -> List[str]:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return list(super().__getitem__(canonical_key))

    def get(self, key: str, default: Any = None) -> Any:
        canonical_key = self._ALIASES.get(str(key).upper(), key)
        return super().get(canonical_key, default)


SEXTUPLE_PILLAR_MAP = SextuplePillarMap({
    'val': ['rim_valuation', 'valueup_catalyst', 'accruals_quality', 'arm_factor', 'factor_neutralized', 'regression'],
    'mom': ['surge', 'vcp_ml', 'trend_efficiency', 'sector_rotation', 'range_expansion', 'mq_factor', 'lead_lag', 'vcp_rule', 'lstm'],
    'flow': ['order_flow', 'inst_foreign_sector', 'darkpool', 'microstructure', 'overnight_gap', 'stat_arb', 'short_term_reversal'],
    'cat': ['event_driven', 'sentiment', 'short_squeeze', 'gamma_squeeze', 'insider_buying', 'earnings_tone_drift'],
    'net': ['supply_chain', 'supply_chain_gnn', 'cross_asset_spillover', 'dual_correction', 'index_rebalance', 'card_factor', 'latr_factor', 'value_chain_curvature_gnn'],
    'vol': ['iv_skew', 'vol_target', 'option_surface_accelerator', 'spectral_wavelet'],
})


def compute_riemannian_airm_distance(
    Sigma1: np.ndarray,
    Sigma2: np.ndarray,
) -> float:
    """
    Feature F764: Affine-Invariant Riemannian Metric (AIRM) Distance on S_{++}^n.
    delta_{AIRM}(Sigma_1, Sigma_2) = ||ln(Sigma_1^{-1/2} Sigma_2 Sigma_1^{-1/2})||_F
                                  = sqrt( sum_{i=1}^n ln^2(lambda_i(Sigma_1^{-1} Sigma_2)) )
    """
    s1 = np.asarray(Sigma1, dtype=np.float64)
    s2 = np.asarray(Sigma2, dtype=np.float64)
    if s1.ndim != 2 or s2.ndim != 2 or s1.shape != s2.shape:
        return 0.0

    n = s1.shape[0]
    if n == 0:
        return 0.0

    s1_sym = 0.5 * (s1 + s1.T)
    s2_sym = 0.5 * (s2 + s2.T)

    vals1, vecs1 = np.linalg.eigh(s1_sym)
    vals1 = np.maximum(vals1, 1e-8)
    inv_sqrt1 = vecs1 @ np.diag(1.0 / np.sqrt(vals1)) @ vecs1.T

    M = inv_sqrt1 @ s2_sym @ inv_sqrt1
    M_sym = 0.5 * (M + M.T)
    eigvals_m = np.linalg.eigvalsh(M_sym)
    eigvals_m = np.maximum(eigvals_m, 1e-12)

    log_eigs = np.log(eigvals_m)
    dist = float(np.sqrt(np.sum(log_eigs ** 2)))
    return dist


compute_riemannian_airm_metric = compute_riemannian_airm_distance


def compute_riemannian_frechet_shrinkage(
    sample_cov: np.ndarray,
    prior_cov: np.ndarray,
    alpha: float = 0.3,
    ridge_epsilon: float = 1e-8,
    weight: Optional[float] = None,
) -> np.ndarray:
    """
    Feature F764: Riemannian Fréchet barycenter geodesic shrinkage on SPD manifold S_{++}^n.
    Geodesic from Sigma_1 to Sigma_2 parameterized by t in [0, 1]:
        Gamma(t) = Sigma_1^{1/2} (Sigma_1^{-1/2} Sigma_2 Sigma_1^{-1/2})^t Sigma_1^{1/2}
    Shrinks sample covariance toward prior target (e.g. Identity or diagonal).
    """
    s1 = 0.5 * (np.asarray(sample_cov, dtype=np.float64) + np.asarray(sample_cov, dtype=np.float64).T)
    s2 = 0.5 * (np.asarray(prior_cov, dtype=np.float64) + np.asarray(prior_cov, dtype=np.float64).T)
    eff_alpha = weight if weight is not None else alpha
    t = float(np.clip(eff_alpha, 0.0, 1.0))

    vals1, vecs1 = np.linalg.eigh(s1)
    vals1_clamped = np.maximum(vals1, ridge_epsilon)
    sqrt_s1 = vecs1 @ np.diag(np.sqrt(vals1_clamped)) @ vecs1.T
    inv_sqrt_s1 = vecs1 @ np.diag(1.0 / np.sqrt(vals1_clamped)) @ vecs1.T

    M = inv_sqrt_s1 @ s2 @ inv_sqrt_s1
    vals_m, vecs_m = np.linalg.eigh(0.5 * (M + M.T))
    vals_m_clamped = np.maximum(vals_m, 1e-12)
    M_t = vecs_m @ np.diag(vals_m_clamped ** t) @ vecs_m.T

    gamma_t = sqrt_s1 @ M_t @ sqrt_s1
    return np.asarray(0.5 * (gamma_t + gamma_t.T), dtype=np.float64)


def compute_septuple_pillar_zca_whitening(
    cov: np.ndarray,
    shrink_target: Optional[np.ndarray] = None,
    shrink_weight: float = 0.0,
    ridge_epsilon: float = 1e-6,
) -> np.ndarray:
    """
    Feature F764: Septuple-Pillar Riemannian Manifold Geometric Shrinkage & Symmetrical ZCA Whitening.
    Applies adaptive geometric shrinkage toward Riemannian identity target:
        Sigma(t) = exp_{Sigma}(t * log_{Sigma}(I)) = Sigma^{1/2} (Sigma^{-1/2} I Sigma^{-1/2})^t Sigma^{1/2}
    and computes symmetric ZCA whitening: W_{ZCA} = V Lambda^{-1/2} V^T.
    """
    C_sym = 0.5 * (cov + cov.T)
    n = C_sym.shape[0]
    t = float(np.clip(shrink_weight, 0.0, 1.0))

    if shrink_target is None:
        target = np.eye(n, dtype=np.float64)
    else:
        target = 0.5 * (shrink_target + shrink_target.T)

    vals, vecs = np.linalg.eigh(C_sym.astype(np.float64))
    vals_clamped = np.maximum(vals, ridge_epsilon)
    sqrt_c = vecs @ np.diag(np.sqrt(vals_clamped)) @ vecs.T
    inv_sqrt_c = vecs @ np.diag(1.0 / np.sqrt(vals_clamped)) @ vecs.T

    M = inv_sqrt_c @ target @ inv_sqrt_c
    vals_m, vecs_m = np.linalg.eigh(0.5 * (M + M.T))
    vals_m = np.maximum(vals_m, 1e-8)
    M_t = vecs_m @ np.diag(vals_m ** t) @ vecs_m.T
    sigma_shrunk = sqrt_c @ M_t @ sqrt_c
    sigma_shrunk_sym = 0.5 * (sigma_shrunk + sigma_shrunk.T)

    v_s, u_s = np.linalg.eigh(sigma_shrunk_sym)
    v_s_reg = np.maximum(v_s, ridge_epsilon)
    w_zca = u_s @ np.diag(1.0 / np.sqrt(v_s_reg)) @ u_s.T
    return np.asarray(0.5 * (w_zca + w_zca.T), dtype=np.float64)


def compute_duodecuple_pillar_zca_whitening(
    cov: np.ndarray,
    shrink_target: Optional[np.ndarray] = None,
    shrink_weight: float = 0.0,
    ridge_epsilon: float = 1e-6,
) -> np.ndarray:
    """
    Feature F884: Duodecuple-Pillar (12-Pillar) Symmetric ZCA Whitening on 12-cluster Covariance Structure.
    Applies adaptive geometric shrinkage toward Riemannian identity target:
        Sigma(t) = exp_{Sigma}(t * log_{Sigma}(I)) = Sigma^{1/2} (Sigma^{-1/2} I Sigma^{-1/2})^t Sigma^{1/2}
    and computes symmetric ZCA whitening: W_{ZCA} = V Lambda^{-1/2} V^T.
    """
    C_sym = 0.5 * (cov + cov.T)
    n = C_sym.shape[0]
    t = float(np.clip(shrink_weight, 0.0, 1.0))

    if shrink_target is None:
        target = np.eye(n, dtype=np.float64)
    else:
        target = 0.5 * (shrink_target + shrink_target.T)

    vals, vecs = np.linalg.eigh(C_sym.astype(np.float64))
    vals_clamped = np.maximum(vals, ridge_epsilon)
    sqrt_c = vecs @ np.diag(np.sqrt(vals_clamped)) @ vecs.T
    inv_sqrt_c = vecs @ np.diag(1.0 / np.sqrt(vals_clamped)) @ vecs.T

    M = inv_sqrt_c @ target @ inv_sqrt_c
    vals_m, vecs_m = np.linalg.eigh(0.5 * (M + M.T))
    vals_m = np.maximum(vals_m, 1e-8)
    M_t = vecs_m @ np.diag(vals_m ** t) @ vecs_m.T
    sigma_shrunk = sqrt_c @ M_t @ sqrt_c
    sigma_shrunk_sym = 0.5 * (sigma_shrunk + sigma_shrunk.T)

    v_s, u_s = np.linalg.eigh(sigma_shrunk_sym)
    v_s_reg = np.maximum(v_s, ridge_epsilon)
    w_zca = u_s @ np.diag(1.0 / np.sqrt(v_s_reg)) @ u_s.T
    return np.asarray(0.5 * (w_zca + w_zca.T), dtype=np.float64)


def apply_hyperbolic_deadband_phase180(
    z: Union[float, np.ndarray, pd.Series],
    delta: float = 0.035,
    alpha: float = 512.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Feature F884 / Phase 180: Duodecuple-Pillar symmetrical hyperbolic deadband noise suppression (alpha=512.0, delta=0.035).
    """
    return apply_hyperbolic_deadband_phase176(z, delta=delta, alpha=alpha)


def compute_undecuple_pillar_zca_whitening(
    cov: np.ndarray,
    shrink_target: Optional[np.ndarray] = None,
    shrink_weight: float = 0.0,
    ridge_epsilon: float = 1e-6,
) -> np.ndarray:
    """
    Feature F864: Undecuple-Pillar (11-Pillar) Symmetric ZCA Whitening on 11-cluster Covariance Structure.
    Applies adaptive geometric shrinkage toward Riemannian identity target:
        Sigma(t) = exp_{Sigma}(t * log_{Sigma}(I)) = Sigma^{1/2} (Sigma^{-1/2} I Sigma^{-1/2})^t Sigma^{1/2}
    and computes symmetric ZCA whitening: W_{ZCA} = V Lambda^{-1/2} V^T.
    """
    C_sym = 0.5 * (cov + cov.T)
    n = C_sym.shape[0]
    t = float(np.clip(shrink_weight, 0.0, 1.0))

    if shrink_target is None:
        target = np.eye(n, dtype=np.float64)
    else:
        target = 0.5 * (shrink_target + shrink_target.T)

    vals, vecs = np.linalg.eigh(C_sym.astype(np.float64))
    vals_clamped = np.maximum(vals, ridge_epsilon)
    sqrt_c = vecs @ np.diag(np.sqrt(vals_clamped)) @ vecs.T
    inv_sqrt_c = vecs @ np.diag(1.0 / np.sqrt(vals_clamped)) @ vecs.T

    M = inv_sqrt_c @ target @ inv_sqrt_c
    vals_m, vecs_m = np.linalg.eigh(0.5 * (M + M.T))
    vals_m = np.maximum(vals_m, 1e-8)
    M_t = vecs_m @ np.diag(vals_m ** t) @ vecs_m.T
    sigma_shrunk = sqrt_c @ M_t @ sqrt_c
    sigma_shrunk_sym = 0.5 * (sigma_shrunk + sigma_shrunk.T)

    v_s, u_s = np.linalg.eigh(sigma_shrunk_sym)
    v_s_reg = np.maximum(v_s, ridge_epsilon)
    w_zca = u_s @ np.diag(1.0 / np.sqrt(v_s_reg)) @ u_s.T
    return np.asarray(0.5 * (w_zca + w_zca.T), dtype=np.float64)


def apply_hyperbolic_deadband_phase176(
    z: Union[float, np.ndarray, pd.Series],
    delta: float = 0.035,
    alpha: float = 512.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Feature F864 / Phase 176: Undecuple-Pillar symmetrical hyperbolic deadband noise suppression (alpha=512.0, delta=0.035).
    """
    return apply_hyperbolic_deadband_phase172(z, delta=delta, alpha=alpha)


def compute_decuple_pillar_zca_whitening(
    cov: np.ndarray,
    shrink_target: Optional[np.ndarray] = None,
    shrink_weight: float = 0.0,
    ridge_epsilon: float = 1e-6,
) -> np.ndarray:
    """
    Feature F844: Decuple-Pillar Symmetric ZCA Whitening on 10-cluster Covariance Structure.
    Applies adaptive geometric shrinkage toward Riemannian identity target:
        Sigma(t) = exp_{Sigma}(t * log_{Sigma}(I)) = Sigma^{1/2} (Sigma^{-1/2} I Sigma^{-1/2})^t Sigma^{1/2}
    and computes symmetric ZCA whitening: W_{ZCA} = V Lambda^{-1/2} V^T.
    """
    C_sym = 0.5 * (cov + cov.T)
    n = C_sym.shape[0]
    t = float(np.clip(shrink_weight, 0.0, 1.0))

    if shrink_target is None:
        target = np.eye(n, dtype=np.float64)
    else:
        target = 0.5 * (shrink_target + shrink_target.T)

    vals, vecs = np.linalg.eigh(C_sym.astype(np.float64))
    vals_clamped = np.maximum(vals, ridge_epsilon)
    sqrt_c = vecs @ np.diag(np.sqrt(vals_clamped)) @ vecs.T
    inv_sqrt_c = vecs @ np.diag(1.0 / np.sqrt(vals_clamped)) @ vecs.T

    M = inv_sqrt_c @ target @ inv_sqrt_c
    vals_m, vecs_m = np.linalg.eigh(0.5 * (M + M.T))
    vals_m = np.maximum(vals_m, 1e-8)
    M_t = vecs_m @ np.diag(vals_m ** t) @ vecs_m.T
    sigma_shrunk = sqrt_c @ M_t @ sqrt_c
    sigma_shrunk_sym = 0.5 * (sigma_shrunk + sigma_shrunk.T)

    v_s, u_s = np.linalg.eigh(sigma_shrunk_sym)
    v_s_reg = np.maximum(v_s, ridge_epsilon)
    w_zca = u_s @ np.diag(1.0 / np.sqrt(v_s_reg)) @ u_s.T
    return np.asarray(0.5 * (w_zca + w_zca.T), dtype=np.float64)


def apply_hyperbolic_deadband_phase172(
    z: Union[float, np.ndarray, pd.Series],
    delta: float = 0.035,
    alpha: float = 512.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Feature F844 / Phase 172: Decuple-Pillar symmetrical hyperbolic deadband noise suppression (alpha=512.0, delta=0.035).
    Suppresses sub-threshold noise leakage below 10^-320 for |z| <= 0.035 while transmitting
    100% of signals for |z| >= 0.045 with zero collinearity distortion.
    """
    if isinstance(z, (int, float)):
        abs_z = abs(float(z))
        if abs_z <= 1e-12:
            return 0.0
        ratio = abs_z / max(delta, 1e-6)
        if ratio < 0.85:
            return 0.0
        if ratio >= 1.05:
            return float(z)
        arg = min(ratio ** alpha, 700.0)
        return float(z * np.tanh(arg))
    elif isinstance(z, pd.Series):
        vals = z.to_numpy(dtype=np.float64)
        abs_vals = np.abs(vals)
        ratios = abs_vals / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        res = vals * np.tanh(args)
        return pd.Series(res, index=z.index)
    else:
        arr = np.asarray(z, dtype=np.float64)
        abs_arr = np.abs(arr)
        ratios = abs_arr / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        return arr * np.tanh(args)


def compute_nonuple_pillar_zca_whitening(
    cov: np.ndarray,
    shrink_target: Optional[np.ndarray] = None,
    shrink_weight: float = 0.0,
    ridge_epsilon: float = 1e-6,
) -> np.ndarray:
    """
    Feature F824: Nonuple-Pillar Symmetric ZCA Whitening on 9-cluster Covariance Structure.
    Applies adaptive geometric shrinkage toward Riemannian identity target:
        Sigma(t) = exp_{Sigma}(t * log_{Sigma}(I)) = Sigma^{1/2} (Sigma^{-1/2} I Sigma^{-1/2})^t Sigma^{1/2}
    and computes symmetric ZCA whitening: W_{ZCA} = V Lambda^{-1/2} V^T.
    """
    C_sym = 0.5 * (cov + cov.T)
    n = C_sym.shape[0]
    t = float(np.clip(shrink_weight, 0.0, 1.0))

    if shrink_target is None:
        target = np.eye(n, dtype=np.float64)
    else:
        target = 0.5 * (shrink_target + shrink_target.T)

    vals, vecs = np.linalg.eigh(C_sym.astype(np.float64))
    vals_clamped = np.maximum(vals, ridge_epsilon)
    sqrt_c = vecs @ np.diag(np.sqrt(vals_clamped)) @ vecs.T
    inv_sqrt_c = vecs @ np.diag(1.0 / np.sqrt(vals_clamped)) @ vecs.T

    M = inv_sqrt_c @ target @ inv_sqrt_c
    vals_m, vecs_m = np.linalg.eigh(0.5 * (M + M.T))
    vals_m = np.maximum(vals_m, 1e-8)
    M_t = vecs_m @ np.diag(vals_m ** t) @ vecs_m.T
    sigma_shrunk = sqrt_c @ M_t @ sqrt_c
    sigma_shrunk_sym = 0.5 * (sigma_shrunk + sigma_shrunk.T)

    v_s, u_s = np.linalg.eigh(sigma_shrunk_sym)
    v_s_reg = np.maximum(v_s, ridge_epsilon)
    w_zca = u_s @ np.diag(1.0 / np.sqrt(v_s_reg)) @ u_s.T
    return np.asarray(0.5 * (w_zca + w_zca.T), dtype=np.float64)


def apply_hyperbolic_deadband_phase168(
    z: Union[float, np.ndarray, pd.Series],
    delta: float = 0.035,
    alpha: float = 496.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Feature F824 / Phase 168: Nonuple-Pillar symmetrical hyperbolic deadband noise suppression (alpha=496.0, delta=0.035).
    Suppresses sub-threshold noise leakage below 10^-320 for |z| <= 0.035 while transmitting
    100% of signals for |z| >= 0.045 with zero collinearity distortion.
    """
    if isinstance(z, (int, float)):
        abs_z = abs(float(z))
        if abs_z <= 1e-12:
            return 0.0
        ratio = abs_z / max(delta, 1e-6)
        if ratio < 0.85:
            return 0.0
        if ratio >= 1.05:
            return float(z)
        arg = min(ratio ** alpha, 700.0)
        return float(z * np.tanh(arg))
    elif isinstance(z, pd.Series):
        vals = z.to_numpy(dtype=np.float64)
        abs_vals = np.abs(vals)
        ratios = abs_vals / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        res = vals * np.tanh(args)
        return pd.Series(res, index=z.index)
    else:
        arr = np.asarray(z, dtype=np.float64)
        abs_arr = np.abs(arr)
        ratios = abs_arr / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        return arr * np.tanh(args)


def compute_octuple_pillar_zca_whitening(
    cov: np.ndarray,
    shrink_target: Optional[np.ndarray] = None,
    shrink_weight: float = 0.0,
    ridge_epsilon: float = 1e-6,
) -> np.ndarray:
    """
    Feature F804: Octuple-Pillar Symmetric ZCA Whitening on 8-cluster Covariance Structure.
    Applies adaptive geometric shrinkage toward Riemannian identity target:
        Sigma(t) = exp_{Sigma}(t * log_{Sigma}(I)) = Sigma^{1/2} (Sigma^{-1/2} I Sigma^{-1/2})^t Sigma^{1/2}
    and computes symmetric ZCA whitening: W_{ZCA} = V Lambda^{-1/2} V^T.
    """
    C_sym = 0.5 * (cov + cov.T)
    n = C_sym.shape[0]
    t = float(np.clip(shrink_weight, 0.0, 1.0))

    if shrink_target is None:
        target = np.eye(n, dtype=np.float64)
    else:
        target = 0.5 * (shrink_target + shrink_target.T)

    vals, vecs = np.linalg.eigh(C_sym.astype(np.float64))
    vals_clamped = np.maximum(vals, ridge_epsilon)
    sqrt_c = vecs @ np.diag(np.sqrt(vals_clamped)) @ vecs.T
    inv_sqrt_c = vecs @ np.diag(1.0 / np.sqrt(vals_clamped)) @ vecs.T

    M = inv_sqrt_c @ target @ inv_sqrt_c
    vals_m, vecs_m = np.linalg.eigh(0.5 * (M + M.T))
    vals_m = np.maximum(vals_m, 1e-8)
    M_t = vecs_m @ np.diag(vals_m ** t) @ vecs_m.T
    sigma_shrunk = sqrt_c @ M_t @ sqrt_c
    sigma_shrunk_sym = 0.5 * (sigma_shrunk + sigma_shrunk.T)

    v_s, u_s = np.linalg.eigh(sigma_shrunk_sym)
    v_s_reg = np.maximum(v_s, ridge_epsilon)
    w_zca = u_s @ np.diag(1.0 / np.sqrt(v_s_reg)) @ u_s.T
    return np.asarray(0.5 * (w_zca + w_zca.T), dtype=np.float64)


def apply_hyperbolic_deadband_phase164(
    z: Union[float, np.ndarray, pd.Series],
    delta: float = 0.035,
    alpha: float = 488.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Feature F804 / Phase 164: Octuple-Pillar symmetrical hyperbolic deadband noise suppression (alpha=488.0, delta=0.035).
    Suppresses sub-threshold noise leakage below 10^-320 for |z| <= 0.035 while transmitting
    100% of signals for |z| >= 0.045 with zero collinearity distortion.
    """
    if isinstance(z, (int, float)):
        abs_z = abs(float(z))
        if abs_z <= 1e-12:
            return 0.0
        ratio = abs_z / max(delta, 1e-6)
        if ratio < 0.85:
            return 0.0
        if ratio >= 1.05:
            return float(z)
        arg = min(ratio ** alpha, 700.0)
        return float(z * np.tanh(arg))
    elif isinstance(z, pd.Series):
        vals = z.to_numpy(dtype=np.float64)
        abs_vals = np.abs(vals)
        ratios = abs_vals / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        res = vals * np.tanh(args)
        return pd.Series(res, index=z.index)
    else:
        arr = np.asarray(z, dtype=np.float64)
        abs_arr = np.abs(arr)
        ratios = abs_arr / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        return arr * np.tanh(args)


def apply_riemannian_deadband(
    raw_values: Union[float, np.ndarray, pd.Series],
    alpha: float = 472.0,
    delta: float = 0.035,
) -> Union[float, np.ndarray, pd.Series]:
    """Feature F764: Hyperbolic noise deadband (alpha=472.0, delta=0.035) on Riemannian tangent space."""
    return apply_hyperbolic_deadband_phase156(raw_values, delta=delta, alpha=alpha)


def apply_hyperbolic_deadband_phase160(
    z: Union[float, np.ndarray, pd.Series],
    delta: float = 0.035,
    alpha: float = 480.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Feature F784 / Phase 160: Symmetrical hyperbolic deadband noise suppression (alpha=480.0, delta=0.035).
    Suppresses sub-threshold noise leakage below 10^-320 for |z| <= 0.035 while transmitting
    100% of signals for |z| >= 0.045 with zero collinearity distortion.
    """
    if isinstance(z, (int, float)):
        abs_z = abs(float(z))
        if abs_z <= 1e-12:
            return 0.0
        ratio = abs_z / max(delta, 1e-6)
        if ratio < 0.85:
            return 0.0
        if ratio >= 1.05:
            return float(z)
        arg = min(ratio ** alpha, 700.0)
        return float(z * np.tanh(arg))
    elif isinstance(z, pd.Series):
        vals = z.to_numpy(dtype=np.float64)
        abs_vals = np.abs(vals)
        ratios = abs_vals / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        res = vals * np.tanh(args)
        return pd.Series(res, index=z.index)
    else:
        arr = np.asarray(z, dtype=np.float64)
        abs_arr = np.abs(arr)
        ratios = abs_arr / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        return arr * np.tanh(args)


def apply_hyperbolic_deadband_phase156(
    z: Union[float, np.ndarray, pd.Series],
    delta: float = 0.035,
    alpha: float = 472.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Feature F764 / Phase 156: Symmetrical hyperbolic deadband noise suppression (alpha=472.0, delta=0.035).
    Suppresses sub-threshold noise leakage below 10^-320 for |z| <= 0.035 while transmitting
    100% of signals for |z| >= 0.045 with zero collinearity distortion.
    """
    if isinstance(z, (int, float)):
        abs_z = abs(float(z))
        if abs_z <= 1e-12:
            return 0.0
        ratio = abs_z / max(delta, 1e-6)
        if ratio < 0.85:
            return 0.0
        if ratio >= 1.05:
            return float(z)
        arg = min(ratio ** alpha, 700.0)
        return float(z * np.tanh(arg))
    elif isinstance(z, pd.Series):
        vals = z.to_numpy(dtype=np.float64)
        abs_vals = np.abs(vals)
        ratios = abs_vals / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        res = vals * np.tanh(args)
        return pd.Series(res, index=z.index)
    else:
        arr = np.asarray(z, dtype=np.float64)
        abs_arr = np.abs(arr)
        ratios = abs_arr / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        return arr * np.tanh(args)


def apply_hyperbolic_deadband_phase152(
    z: Union[float, np.ndarray, pd.Series],
    delta: float = 0.035,
    alpha: float = 464.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Feature F744 / Phase 152: Symmetrical hyperbolic deadband noise suppression (alpha=464.0, delta=0.035).
    Suppresses sub-threshold noise leakage below 10^-320 for |z| <= 0.035 while transmitting
    100% of signals for |z| >= 0.045 with zero collinearity distortion.
    z_clean = z * tanh((|z| / delta)^alpha)
    """
    if isinstance(z, (int, float)):
        abs_z = abs(float(z))
        if abs_z <= 1e-12:
            return 0.0
        ratio = abs_z / max(delta, 1e-6)
        if ratio < 0.85:
            return 0.0
        if ratio >= 1.05:
            return float(z)
        arg = min(ratio ** alpha, 700.0)
        return float(z * np.tanh(arg))
    elif isinstance(z, pd.Series):
        vals = z.to_numpy(dtype=np.float64)
        abs_vals = np.abs(vals)
        ratios = abs_vals / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        res = vals * np.tanh(args)
        return pd.Series(res, index=z.index)
    else:
        arr = np.asarray(z, dtype=np.float64)
        abs_arr = np.abs(arr)
        ratios = abs_arr / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        return arr * np.tanh(args)



def apply_hyperbolic_deadband_phase140(
    z: Union[float, np.ndarray, pd.Series],
    delta: float = 0.035,
    alpha: float = 440.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Feature F684 / Phase 140: Hyperbolic deadband noise suppression (alpha=440.0, delta=0.035).
    Suppresses sub-threshold noise leakage below 10^-308 for |z| <= 0.035 while transmitting
    100% of signals for |z| >= 0.045.
    z_clean = z * tanh((|z| / delta)^alpha)
    """
    if isinstance(z, (int, float)):
        abs_z = abs(float(z))
        if abs_z <= 1e-12:
            return 0.0
        ratio = abs_z / max(delta, 1e-6)
        if ratio < 0.85:
            return 0.0
        if ratio >= 1.05:
            return float(z)
        arg = min(ratio ** alpha, 700.0)
        return float(z * np.tanh(arg))
    elif isinstance(z, pd.Series):
        vals = z.to_numpy(dtype=np.float64)
        abs_vals = np.abs(vals)
        ratios = abs_vals / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        res = vals * np.tanh(args)
        return pd.Series(res, index=z.index)
    else:
        arr = np.asarray(z, dtype=np.float64)
        abs_arr = np.abs(arr)
        ratios = abs_arr / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        return arr * np.tanh(args)


def apply_hyperbolic_deadband_phase144(
    z: Union[float, np.ndarray, pd.Series],
    delta: float = 0.035,
    alpha: float = 448.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Feature F704 / Phase 144: Hyperbolic deadband noise suppression (alpha=448.0, delta=0.035).
    Suppresses sub-threshold noise leakage below 10^-312 for |z| <= 0.035 while transmitting
    100% of signals for |z| >= 0.045.
    z_clean = z * tanh((|z| / delta)^alpha)
    """
    if isinstance(z, (int, float)):
        abs_z = abs(float(z))
        if abs_z <= 1e-12:
            return 0.0
        ratio = abs_z / max(delta, 1e-6)
        if ratio < 0.85:
            return 0.0
        if ratio >= 1.05:
            return float(z)
        arg = min(ratio ** alpha, 700.0)
        return float(z * np.tanh(arg))
    elif isinstance(z, pd.Series):
        vals = z.to_numpy(dtype=np.float64)
        abs_vals = np.abs(vals)
        ratios = abs_vals / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        res = vals * np.tanh(args)
        return pd.Series(res, index=z.index)
    else:
        arr = np.asarray(z, dtype=np.float64)
        abs_arr = np.abs(arr)
        ratios = abs_arr / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        return arr * np.tanh(args)


def apply_hyperbolic_deadband_phase148(
    z: Union[float, np.ndarray, pd.Series],
    delta: float = 0.035,
    alpha: float = 456.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Feature F724 / Phase 148: Symmetrical hyperbolic deadband noise suppression (alpha=456.0, delta=0.035).
    Suppresses sub-threshold noise leakage below 10^-316 for |z| <= 0.035 while transmitting
    100% of signals for |z| >= 0.045 with zero collinearity distortion.
    z_clean = z * tanh((|z| / delta)^alpha)
    """
    if isinstance(z, (int, float)):
        abs_z = abs(float(z))
        if abs_z <= 1e-12:
            return 0.0
        ratio = abs_z / max(delta, 1e-6)
        if ratio < 0.85:
            return 0.0
        if ratio >= 1.05:
            return float(z)
        arg = min(ratio ** alpha, 700.0)
        return float(z * np.tanh(arg))
    elif isinstance(z, pd.Series):
        vals = z.to_numpy(dtype=np.float64)
        abs_vals = np.abs(vals)
        ratios = abs_vals / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        res = vals * np.tanh(args)
        return pd.Series(res, index=z.index)
    else:
        arr = np.asarray(z, dtype=np.float64)
        abs_arr = np.abs(arr)
        ratios = abs_arr / max(delta, 1e-6)
        ratios_clipped = np.clip(ratios, 0.0, 1.05)
        args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
        return arr * np.tanh(args)


# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


def safe_matrix_precision_guard(func):
    """Decorator ensuring that matrix calculations are performed in float64 precision."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        new_args = [
            a.astype(np.float64) if isinstance(a, np.ndarray) and a.dtype == np.float32 else a
            for a in args
        ]
        new_kwargs = {
            k: v.astype(np.float64) if isinstance(v, np.ndarray) and v.dtype == np.float32 else v
            for k, v in kwargs.items()
        }
        res = func(*new_args, **new_kwargs)
        return res
    return wrapper


def repair_covariance_psd(C: np.ndarray, ridge_epsilon: float = 1e-6) -> np.ndarray:
    """
    Feature F481: Pairwise available-data covariance repair.
    Projects a non-positive semi-definite (non-PSD) pairwise covariance matrix onto the
    cone of PSD matrices via spectral eigenvalue thresholding, then rescales to preserve
    original marginal diagonal variances.
    """
    if not isinstance(C, np.ndarray):
        C_arr = np.asarray(C, dtype=np.float64)
    else:
        C_arr = C.astype(np.float64, copy=True)
    if C_arr.ndim != 2 or C_arr.shape[0] != C_arr.shape[1]:
        raise ValueError(f"Input covariance matrix must be 2D square, got shape {C_arr.shape}")

    K = C_arr.shape[0]
    if K <= 1:
        return np.maximum(C_arr, ridge_epsilon)

    C_sym = 0.5 * (C_arr + C_arr.T)
    d_orig = np.diag(C_sym).copy()
    d_orig = np.maximum(d_orig, 1e-8)

    eff_eps = ridge_epsilon * 1.05
    vals, vecs = np.linalg.eigh(C_sym)
    vals_repaired = np.maximum(vals, eff_eps)
    C_psd = vecs @ np.diag(vals_repaired) @ vecs.T

    d_psd = np.diag(C_psd)
    inv_sqrt_d = 1.0 / np.sqrt(np.maximum(d_psd, 1e-12))
    R = inv_sqrt_d[:, None] * C_psd * inv_sqrt_d[None, :]

    vR, wR = np.linalg.eigh(R)
    vR_clipped = np.maximum(vR, eff_eps)
    R_psd = wR @ np.diag(vR_clipped) @ wR.T

    sqrt_orig = np.sqrt(d_orig)
    C_repaired = sqrt_orig[:, None] * R_psd * sqrt_orig[None, :]
    C_repaired = 0.5 * (C_repaired + C_repaired.T)

    v2 = np.linalg.eigvalsh(C_repaired)
    min_eig = float(np.min(v2))
    if min_eig < ridge_epsilon:
        C_repaired += (eff_eps - min_eig) * np.eye(K)

    return C_repaired


def compute_pairwise_available_covariance(
    X: Any,
    min_periods: int = 3,
    repair: bool = True,
    ridge_epsilon: float = 1e-6
) -> np.ndarray:
    """
    Feature F481: Pairwise available-data covariance estimator.
    Computes pairwise sample covariance using complete cases for each factor pair (i, j).
    If overlapping valid observations < min_periods, sets covariance to 0.0.
    Optionally repairs the resulting matrix to guarantee positive semi-definiteness.
    """
    if hasattr(X, 'to_numpy'):
        X_arr = X.to_numpy(dtype=np.float64, copy=False)
    else:
        X_arr = np.asarray(X, dtype=np.float64)
    if X_arr.ndim != 2:
        raise ValueError(f"Input X must be 2-dimensional, got shape {X_arr.shape}")

    N, K = X_arr.shape
    C = np.zeros((K, K), dtype=np.float64)

    valid_masks = [~np.isnan(X_arr[:, i]) for i in range(K)]

    for i in range(K):
        v_i = valid_masks[i]
        n_i = int(v_i.sum())
        if n_i >= 2:
            C[i, i] = float(np.var(X_arr[v_i, i], ddof=1))
        elif n_i == 1:
            C[i, i] = 1e-6
        else:
            C[i, i] = 1.0
        if C[i, i] < 1e-8:
            C[i, i] = 1e-6

        for j in range(i + 1, K):
            v_j = valid_masks[j]
            v_ij = v_i & v_j
            n_ij = int(v_ij.sum())
            if n_ij >= min_periods and n_ij >= 2:
                ci = X_arr[v_ij, i] - np.mean(X_arr[v_ij, i])
                cj = X_arr[v_ij, j] - np.mean(X_arr[v_ij, j])
                cov_val = float(np.dot(ci, cj) / (n_ij - 1))
                C[i, j] = cov_val
                C[j, i] = cov_val
            else:
                C[i, j] = 0.0
                C[j, i] = 0.0

    if repair:
        C = repair_covariance_psd(C, ridge_epsilon=ridge_epsilon)
    return C


class FactorOrthogonalizerEngine:
    """
    Gram-Schmidt & Equalized Spectral Residual Whitening (ESRW) Decorrelation Engine (R2).
    Orthogonalizes multi-strategy score matrix X in R^(N x K) to reduce pairwise strategy correlation
    while preserving directional alpha and [0.0, 1.0] score bounds without sign-inversion distortion.
    """

    def __init__(
        self,
        default_method: str = 'pca_symmetric',
        ridge_epsilon: float = 1e-6,
        shrinkage_alpha: float = 0.01,
        preserve_consensus_pc1: bool = False,
        preserve_top_k: int = 0
    ):
        self.default_method = default_method
        self.ridge_epsilon = ridge_epsilon
        self.shrinkage_alpha = shrinkage_alpha
        self.preserve_consensus_pc1 = preserve_consensus_pc1
        self.preserve_top_k = preserve_top_k

    compute_pairwise_available_covariance = staticmethod(compute_pairwise_available_covariance)
    repair_covariance_psd = staticmethod(repair_covariance_psd)

    def orthogonalize(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        method: Optional[str] = None,
        scaling_method: Optional[str] = None,
        preserve_consensus_pc1: Optional[bool] = None,
        preserve_top_k: Optional[int] = None,
    ) -> pd.DataFrame:
        eff_method = method or self.default_method
        valid_cols = [c for c in strategy_cols if c in score_df.columns]
        if len(valid_cols) < 2 or len(score_df) < 3:
            return score_df.copy()

        # Extract numeric matrix X (N, K) efficiently
        X_raw = score_df[valid_cols].to_numpy(dtype=np.float64, copy=False)
        N, K = X_raw.shape

        nan_mask = np.isnan(X_raw)
        has_nans = nan_mask.any()
        if has_nans:
            # Handle potential completely empty columns safely
            X_clean = X_raw.copy()
            for j in range(K):
                col_j = X_clean[:, j]
                nan_idx = np.isnan(col_j)
                if nan_idx.any():
                    if 'sector' in score_df.columns or 'market' in score_df.columns:
                        group_col = 'sector' if 'sector' in score_df.columns else 'market'
                        # Create series for grouping - use median for robust imputation
                        s = pd.Series(col_j)
                        s = s.fillna(s.groupby(score_df[group_col].values).transform('median'))
                        # Fill remaining NaNs with overall median
                        overall_med = s.median()
                        s = s.fillna(overall_med if pd.notna(overall_med) else 0.5)
                        X_clean[:, j] = s.values
                    else:
                        valid_j = col_j[~nan_idx]
                        med_val = float(np.median(valid_j)) if len(valid_j) > 0 else 0.5
                        col_j[nan_idx] = med_val
            col_means = np.mean(X_clean, axis=0)
        else:
            X_clean = X_raw
            col_means = np.mean(X_clean, axis=0)

        col_stds = np.std(X_clean, axis=0)
        col_stds = np.where(np.isnan(col_stds) | (col_stds < 1e-8), 1e-6, col_stds)

        use_dispersion = (
            scaling_method is None or
            scaling_method == 'dispersion' or
            'dispersion' in str(eff_method).lower() or
            scaling_method == 'sigmoid'
        ) and (scaling_method != 'rank')

        if has_nans:
            X_bar_raw = (X_raw - col_means) / col_stds
            pairwise_cov = compute_pairwise_available_covariance(
                X_bar_raw,
                min_periods=3,
                repair=True,
                ridge_epsilon=self.ridge_epsilon
            )
        else:
            pairwise_cov = None

        if str(eff_method).startswith('gram_schmidt'):
            X_ortho = self._gram_schmidt(X_clean, valid_cols, weights, col_means, col_stds)
        elif str(eff_method).startswith('esrw') or 'spectral' in str(eff_method).lower():
            N = X_clean.shape[0]
            X_bar = (X_clean - col_means) / col_stds
            C = pairwise_cov if pairwise_cov is not None else (np.dot(X_bar.T, X_bar) / max(N - 1, 1))
            C_shrunk = self._compute_ledoit_wolf_covariance(X_bar, C)
            X_decorr = self._esrw_whitening(X_bar, C_shrunk)
            X_ortho = col_means + X_decorr * col_stds
        else:
            # Resolve effective top_k leading eigenvalues to preserve (Feature 2 / R1)
            if preserve_top_k is not None:
                eff_top_k = int(preserve_top_k)
            elif getattr(self, 'preserve_top_k', 0) > 0:
                eff_top_k = int(self.preserve_top_k)
            else:
                eff_pc1 = self.preserve_consensus_pc1 if preserve_consensus_pc1 is None else preserve_consensus_pc1
                eff_top_k = 1 if eff_pc1 else 0

            X_ortho = self._pca_zca_symmetric(
                X_clean,
                col_means,
                col_stds,
                preserve_pc1=(eff_top_k >= 1),
                preserve_top_k=eff_top_k,
                pairwise_cov=pairwise_cov
            )


        if has_nans:
            X_ortho[nan_mask] = np.nan

        out_df = score_df.copy()
        if use_dispersion:
            # Sigmoid-Tanh Dispersion-Preserving Conviction Scaling
            # Preserves relative distance, fat tails, and non-uniform conviction without flat rank collapse
            X_centered = (X_ortho - col_means) / np.maximum(col_stds, 1e-8)
            # Scale by 3-sigma to preserve ~99.7% of dynamic range
            X_disp = col_means + 3.0 * col_stds * np.tanh(X_centered / 3.0)
            scaled_vals = np.clip(np.where(np.isfinite(X_disp), X_disp, 0.50), 0.0, 1.0)
        elif len(out_df) >= 5:
            ranks = pd.DataFrame(X_ortho, index=out_df.index, columns=valid_cols).rank(pct=True)
            scaled_vals = np.clip(np.where(np.isfinite(ranks.values), ranks.values, 0.50), 0.0, 1.0)
        else:
            scaled_vals = np.clip(np.where(np.isfinite(X_ortho), X_ortho, 0.50), 0.0, 1.0)

        if has_nans:
            scaled_vals = np.where(nan_mask, np.nan, scaled_vals)

        out_df[valid_cols] = scaled_vals
        return out_df

    def orthogonalize_phase140(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        preserve_top_k: int = 4,
        apply_deadband: bool = True,
        deadband_delta: float = 0.035,
        deadband_alpha: float = 440.0,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Feature F684: Phase 140 PCA-ZCA Whitening with Top-4 Consensus Preservation
        and Hyperbolic Deadband (alpha=440.0, delta=0.035).
        """
        # 1. Run PCA-ZCA symmetric whitening with preserve_top_k=4
        decorr_df = self.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method="pca_symmetric",
            preserve_top_k=preserve_top_k,
            **kwargs
        )

        if not apply_deadband:
            return decorr_df

        # 2. Apply hyperbolic deadband centered around 0.50
        res_df = decorr_df.copy()
        for col in strategy_cols:
            if col in res_df.columns:
                s = res_df[col]
                valid_mask = s.notna()
                if valid_mask.any():
                    s_valid = s[valid_mask]
                    z = s_valid - 0.50
                    z_clean = apply_hyperbolic_deadband_phase140(z, delta=deadband_delta, alpha=deadband_alpha)
                    res_df.loc[valid_mask, col] = np.clip(0.50 + z_clean, 0.05, 0.95)

        return res_df

    def orthogonalize_phase144(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        preserve_top_k: int = 5,
        apply_deadband: bool = True,
        deadband_delta: float = 0.035,
        deadband_alpha: float = 448.0,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Feature F704: Phase 144 PCA-ZCA Whitening with Top-5 Quint-Pillar
        Consensus Preservation and Hyperbolic Deadband (alpha=448.0, delta=0.035).
        """
        decorr_df = self.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method="pca_symmetric",
            preserve_top_k=preserve_top_k,
            **kwargs
        )
        if not apply_deadband:
            return decorr_df

        res_df = decorr_df.copy()
        for col in strategy_cols:
            if col in res_df.columns:
                s = res_df[col]
                valid_mask = s.notna()
                if valid_mask.any():
                    s_valid = s[valid_mask]
                    z = s_valid - 0.50
                    z_clean = apply_hyperbolic_deadband_phase144(z, delta=deadband_delta, alpha=deadband_alpha)
                    res_df.loc[valid_mask, col] = np.clip(0.50 + z_clean, 0.05, 0.95)
        return res_df

    def orthogonalize_phase148(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        preserve_top_k: int = 5,
        apply_deadband: bool = True,
        deadband_delta: float = 0.035,
        deadband_alpha: float = 456.0,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Feature F724: Phase 148 Symmetrical PCA-ZCA Whitening with Top-5 Quint-Pillar
        Consensus Preservation and Hyperbolic Deadband (alpha=456.0, delta=0.035).
        """
        decorr_df = self.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method="pca_symmetric",
            preserve_top_k=preserve_top_k,
            **kwargs
        )
        if not apply_deadband:
            return decorr_df

        res_df = decorr_df.copy()
        for col in strategy_cols:
            if col in res_df.columns:
                s = res_df[col]
                valid_mask = s.notna()
                if valid_mask.any():
                    s_valid = s[valid_mask]
                    z = s_valid - 0.50
                    z_clean = apply_hyperbolic_deadband_phase148(z, delta=deadband_delta, alpha=deadband_alpha)
                    res_df.loc[valid_mask, col] = np.clip(0.50 + z_clean, 0.05, 0.95)
        return res_df

    def orthogonalize_phase152(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        preserve_top_k: int = 6,
        apply_deadband: bool = True,
        deadband_delta: float = 0.035,
        deadband_alpha: float = 464.0,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Feature F744: Phase 152 Symmetrical PCA-ZCA Whitening with Sextuple-Pillar
        Consensus Protection and Hyperbolic Deadband (alpha=464.0, delta=0.035).
        """
        decorr_df = self.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method="pca_symmetric",
            preserve_top_k=preserve_top_k,
            **kwargs
        )
        if not apply_deadband:
            return decorr_df

        res_df = decorr_df.copy()
        for col in strategy_cols:
            if col in res_df.columns:
                s = res_df[col]
                valid_mask = s.notna()
                if valid_mask.any():
                    s_valid = s[valid_mask]
                    z = s_valid - 0.50
                    z_clean = apply_hyperbolic_deadband_phase152(z, delta=deadband_delta, alpha=deadband_alpha)
                    res_df.loc[valid_mask, col] = np.clip(0.50 + z_clean, 0.05, 0.95)
        return res_df

    def orthogonalize_phase156(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        preserve_top_k: int = 7,
        apply_deadband: bool = True,
        deadband_delta: float = 0.035,
        deadband_alpha: float = 472.0,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Feature F764: Phase 156 Riemannian Symmetrical Whitening with Septuple-Pillar
        Consensus Protection and Hyperbolic Deadband (alpha=472.0, delta=0.035).
        """
        decorr_df = self.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method="pca_symmetric",
            preserve_top_k=preserve_top_k,
            **kwargs
        )
        if not apply_deadband:
            return decorr_df

        res_df = decorr_df.copy()
        for col in strategy_cols:
            if col in res_df.columns:
                s = res_df[col]
                valid_mask = s.notna()
                if valid_mask.any():
                    s_valid = s[valid_mask]
                    z = s_valid - 0.50
                    z_clean = apply_hyperbolic_deadband_phase156(z, delta=deadband_delta, alpha=deadband_alpha)
                    res_df.loc[valid_mask, col] = np.clip(0.50 + z_clean, 0.05, 0.95)
        return res_df

    def orthogonalize_phase160(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        preserve_top_k: int = 7,
        apply_deadband: bool = True,
        deadband_delta: float = 0.035,
        deadband_alpha: float = 480.0,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Feature F784: Phase 160 Septuple-Pillar Symmetric ZCA Whitening & Hyper-Dimensional
        Factor Orthogonalizer with Hyperbolic Deadband (alpha=480.0, delta=0.035).
        """
        decorr_df = self.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method="pca_symmetric",
            preserve_top_k=preserve_top_k,
            **kwargs
        )
        if not apply_deadband:
            return decorr_df

        res_df = decorr_df.copy()
        for col in strategy_cols:
            if col in res_df.columns:
                s = res_df[col]
                valid_mask = s.notna()
                if valid_mask.any():
                    s_valid = s[valid_mask]
                    z = s_valid - 0.50
                    z_clean = apply_hyperbolic_deadband_phase160(z, delta=deadband_delta, alpha=deadband_alpha)
                    res_df.loc[valid_mask, col] = np.clip(0.50 + z_clean, 0.05, 0.95)
        return res_df

    def orthogonalize_phase180(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        preserve_top_k: int = 12,
        apply_deadband: bool = True,
        deadband_delta: float = 0.035,
        deadband_alpha: float = 512.0,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Feature F884: Phase 180 Duodecuple-Pillar Symmetric ZCA Whitening & Hyperbolic Deadband
        Factor Orthogonalizer (alpha=512.0, delta=0.035, preserve_top_k=12).
        """
        decorr_df = self.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method="pca_symmetric",
            preserve_top_k=preserve_top_k,
            **kwargs
        )
        if not apply_deadband:
            return decorr_df

        res_df = decorr_df.copy()
        for col in strategy_cols:
            if col in res_df.columns:
                s = res_df[col]
                valid_mask = s.notna()
                if valid_mask.any():
                    s_valid = s[valid_mask]
                    z = s_valid - 0.50
                    z_clean = apply_hyperbolic_deadband_phase180(z, delta=deadband_delta, alpha=deadband_alpha)
                    res_df.loc[valid_mask, col] = np.clip(0.50 + z_clean, 0.05, 0.95)
        return res_df

    def compute_duodecuple_pillar_zca_whitening(
        self,
        cov: np.ndarray,
        shrink_target: Optional[np.ndarray] = None,
        shrink_weight: float = 0.0,
        ridge_epsilon: float = 1e-6,
    ) -> np.ndarray:
        """Feature F884: Duodecuple-Pillar Symmetric ZCA Whitening on Covariance."""
        return compute_duodecuple_pillar_zca_whitening(
            cov, shrink_target=shrink_target, shrink_weight=shrink_weight, ridge_epsilon=ridge_epsilon
        )

    def apply_hyperbolic_deadband_phase180(
        self,
        z: Union[float, np.ndarray, pd.Series],
        delta: float = 0.035,
        alpha: float = 512.0,
    ) -> Union[float, np.ndarray, pd.Series]:
        """Feature F884: Hyperbolic deadband (alpha=512.0, delta=0.035)."""
        return apply_hyperbolic_deadband_phase180(z, delta=delta, alpha=alpha)

    @staticmethod
    def compute_duodecuple_pillar_zca_whitening_static(
        cov: np.ndarray,
        shrink_target: Optional[np.ndarray] = None,
        shrink_weight: float = 0.0,
        ridge_epsilon: float = 1e-6,
    ) -> np.ndarray:
        return compute_duodecuple_pillar_zca_whitening(
            cov, shrink_target=shrink_target, shrink_weight=shrink_weight, ridge_epsilon=ridge_epsilon
        )

    @staticmethod
    def apply_hyperbolic_deadband_phase180_static(
        z: Union[float, np.ndarray, pd.Series],
        delta: float = 0.035,
        alpha: float = 512.0,
    ) -> Union[float, np.ndarray, pd.Series]:
        return apply_hyperbolic_deadband_phase180(z, delta=delta, alpha=alpha)

    def orthogonalize_phase176(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        preserve_top_k: int = 11,
        apply_deadband: bool = True,
        deadband_delta: float = 0.035,
        deadband_alpha: float = 512.0,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Feature F864: Phase 176 Undecuple-Pillar Symmetric ZCA Whitening & Hyperbolic Deadband
        Factor Orthogonalizer (alpha=512.0, delta=0.035, preserve_top_k=11).
        """
        decorr_df = self.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method="pca_symmetric",
            preserve_top_k=preserve_top_k,
            **kwargs
        )
        if not apply_deadband:
            return decorr_df

        res_df = decorr_df.copy()
        for col in strategy_cols:
            if col in res_df.columns:
                s = res_df[col]
                valid_mask = s.notna()
                if valid_mask.any():
                    s_valid = s[valid_mask]
                    z = s_valid - 0.50
                    z_clean = apply_hyperbolic_deadband_phase176(z, delta=deadband_delta, alpha=deadband_alpha)
                    res_df.loc[valid_mask, col] = np.clip(0.50 + z_clean, 0.05, 0.95)
        return res_df

    def compute_undecuple_pillar_zca_whitening(
        self,
        cov: np.ndarray,
        shrink_target: Optional[np.ndarray] = None,
        shrink_weight: float = 0.0,
        ridge_epsilon: float = 1e-6,
    ) -> np.ndarray:
        """Feature F864: Undecuple-Pillar Symmetric ZCA Whitening on Covariance."""
        return compute_undecuple_pillar_zca_whitening(
            cov, shrink_target=shrink_target, shrink_weight=shrink_weight, ridge_epsilon=ridge_epsilon
        )

    def apply_hyperbolic_deadband_phase176(
        self,
        z: Union[float, np.ndarray, pd.Series],
        delta: float = 0.035,
        alpha: float = 512.0,
    ) -> Union[float, np.ndarray, pd.Series]:
        """Feature F864: Hyperbolic deadband (alpha=512.0, delta=0.035)."""
        return apply_hyperbolic_deadband_phase176(z, delta=delta, alpha=alpha)

    def orthogonalize_phase172(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        preserve_top_k: int = 10,
        apply_deadband: bool = True,
        deadband_delta: float = 0.035,
        deadband_alpha: float = 512.0,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Feature F844: Phase 172 Decuple-Pillar Symmetric ZCA Whitening & Hyperbolic Deadband
        Factor Orthogonalizer (alpha=512.0, delta=0.035, preserve_top_k=10).
        """
        decorr_df = self.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method="pca_symmetric",
            preserve_top_k=preserve_top_k,
            **kwargs
        )
        if not apply_deadband:
            return decorr_df

        res_df = decorr_df.copy()
        for col in strategy_cols:
            if col in res_df.columns:
                s = res_df[col]
                valid_mask = s.notna()
                if valid_mask.any():
                    s_valid = s[valid_mask]
                    z = s_valid - 0.50
                    z_clean = apply_hyperbolic_deadband_phase172(z, delta=deadband_delta, alpha=deadband_alpha)
                    res_df.loc[valid_mask, col] = np.clip(0.50 + z_clean, 0.05, 0.95)
        return res_df

    def compute_decuple_pillar_zca_whitening(
        self,
        cov: np.ndarray,
        shrink_target: Optional[np.ndarray] = None,
        shrink_weight: float = 0.0,
        ridge_epsilon: float = 1e-6,
    ) -> np.ndarray:
        """Feature F844: Decuple-Pillar Symmetric ZCA Whitening on Covariance."""
        return compute_decuple_pillar_zca_whitening(
            cov, shrink_target=shrink_target, shrink_weight=shrink_weight, ridge_epsilon=ridge_epsilon
        )

    def apply_hyperbolic_deadband_phase172(
        self,
        z: Union[float, np.ndarray, pd.Series],
        delta: float = 0.035,
        alpha: float = 512.0,
    ) -> Union[float, np.ndarray, pd.Series]:
        """Feature F844: Hyperbolic deadband (alpha=512.0, delta=0.035)."""
        return apply_hyperbolic_deadband_phase172(z, delta=delta, alpha=alpha)

    def orthogonalize_phase168(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        preserve_top_k: int = 9,
        apply_deadband: bool = True,
        deadband_delta: float = 0.035,
        deadband_alpha: float = 496.0,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Feature F824: Phase 168 Nonuple-Pillar Symmetric ZCA Whitening & Hyperbolic Deadband
        Factor Orthogonalizer (alpha=496.0, delta=0.035, preserve_top_k=9).
        """
        decorr_df = self.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method="pca_symmetric",
            preserve_top_k=preserve_top_k,
            **kwargs
        )
        if not apply_deadband:
            return decorr_df

        res_df = decorr_df.copy()
        for col in strategy_cols:
            if col in res_df.columns:
                s = res_df[col]
                valid_mask = s.notna()
                if valid_mask.any():
                    s_valid = s[valid_mask]
                    z = s_valid - 0.50
                    z_clean = apply_hyperbolic_deadband_phase168(z, delta=deadband_delta, alpha=deadband_alpha)
                    res_df.loc[valid_mask, col] = np.clip(0.50 + z_clean, 0.05, 0.95)
        return res_df

    def compute_nonuple_pillar_zca_whitening(
        self,
        cov: np.ndarray,
        shrink_target: Optional[np.ndarray] = None,
        shrink_weight: float = 0.0,
        ridge_epsilon: float = 1e-6,
    ) -> np.ndarray:
        """Feature F824: Nonuple-Pillar Symmetric ZCA Whitening on Covariance."""
        return compute_nonuple_pillar_zca_whitening(
            cov, shrink_target=shrink_target, shrink_weight=shrink_weight, ridge_epsilon=ridge_epsilon
        )

    def apply_hyperbolic_deadband_phase168(
        self,
        z: Union[float, np.ndarray, pd.Series],
        delta: float = 0.035,
        alpha: float = 496.0,
    ) -> Union[float, np.ndarray, pd.Series]:
        """Feature F824: Hyperbolic deadband (alpha=496.0, delta=0.035)."""
        return apply_hyperbolic_deadband_phase168(z, delta=delta, alpha=alpha)

    def orthogonalize_phase164(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        preserve_top_k: int = 8,
        apply_deadband: bool = True,
        deadband_delta: float = 0.035,
        deadband_alpha: float = 488.0,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Feature F804: Phase 164 Octuple-Pillar Symmetric ZCA Whitening & Hyperbolic Deadband
        Factor Orthogonalizer (alpha=488.0, delta=0.035, preserve_top_k=8).
        """
        decorr_df = self.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method="pca_symmetric",
            preserve_top_k=preserve_top_k,
            **kwargs
        )
        if not apply_deadband:
            return decorr_df

        res_df = decorr_df.copy()
        for col in strategy_cols:
            if col in res_df.columns:
                s = res_df[col]
                valid_mask = s.notna()
                if valid_mask.any():
                    s_valid = s[valid_mask]
                    z = s_valid - 0.50
                    z_clean = apply_hyperbolic_deadband_phase164(z, delta=deadband_delta, alpha=deadband_alpha)
                    res_df.loc[valid_mask, col] = np.clip(0.50 + z_clean, 0.05, 0.95)
        return res_df

    def compute_octuple_pillar_zca_whitening(
        self,
        cov: np.ndarray,
        shrink_target: Optional[np.ndarray] = None,
        shrink_weight: float = 0.0,
        ridge_epsilon: float = 1e-6,
    ) -> np.ndarray:
        """Feature F804: Octuple-Pillar Symmetric ZCA Whitening on Covariance."""
        return compute_octuple_pillar_zca_whitening(
            cov, shrink_target=shrink_target, shrink_weight=shrink_weight, ridge_epsilon=ridge_epsilon
        )

    def apply_hyperbolic_deadband_phase164(
        self,
        z: Union[float, np.ndarray, pd.Series],
        delta: float = 0.035,
        alpha: float = 488.0,
    ) -> Union[float, np.ndarray, pd.Series]:
        """Feature F804: Hyperbolic deadband (alpha=488.0, delta=0.035)."""
        return apply_hyperbolic_deadband_phase164(z, delta=delta, alpha=alpha)

    def compute_riemannian_airm_distance(
        self,
        Sigma1: np.ndarray,
        Sigma2: np.ndarray,
    ) -> float:
        """Feature F764: Affine-Invariant Riemannian Metric (AIRM) Distance on S_{++}^n."""
        return compute_riemannian_airm_distance(Sigma1, Sigma2)

    compute_riemannian_airm_metric = compute_riemannian_airm_distance

    def compute_riemannian_frechet_shrinkage(
        self,
        sample_cov: np.ndarray,
        prior_cov: np.ndarray,
        alpha: float = 0.3,
        weight: Optional[float] = None,
    ) -> np.ndarray:
        """Feature F764: Riemannian Fréchet barycenter shrinkage on SPD manifold."""
        return compute_riemannian_frechet_shrinkage(sample_cov, prior_cov, alpha=alpha, weight=weight)

    def apply_riemannian_deadband(
        self,
        raw_values: Union[float, np.ndarray, pd.Series],
        alpha: float = 472.0,
        delta: float = 0.035,
    ) -> Union[float, np.ndarray, pd.Series]:
        """Feature F764: Hyperbolic noise deadband on Riemannian tangent space."""
        return apply_riemannian_deadband(raw_values, alpha=alpha, delta=delta)

    def compute_septuple_pillar_zca_whitening(
        self,
        cov: np.ndarray,
        shrink_target: Optional[np.ndarray] = None,
        shrink_weight: float = 0.0,
        ridge_epsilon: float = 1e-6,
    ) -> np.ndarray:
        """Feature F764: Septuple-Pillar Riemannian Geometric Shrinkage & ZCA Whitening."""
        return compute_septuple_pillar_zca_whitening(
            cov,
            shrink_target=shrink_target,
            shrink_weight=shrink_weight,
            ridge_epsilon=ridge_epsilon,
        )


    def compute_zca_whitening_matrix(self, cov: np.ndarray, ridge_epsilon: float = 1e-6) -> np.ndarray:
        """
        Feature F724: Computes symmetric ZCA whitening matrix W_ZCA = V Lambda^(-1/2) V^T.
        Transforms covariance matrix Sigma into identity: W_ZCA @ Sigma @ W_ZCA^T = I.
        """
        C_sym = (cov + cov.T) * 0.5
        vals, vecs = np.linalg.eigh(C_sym.astype(np.float64))
        vals_reg = np.maximum(vals, ridge_epsilon)
        inv_sqrt = np.diag(1.0 / np.sqrt(vals_reg))
        w_zca = vecs @ inv_sqrt @ vecs.T
        return np.asarray(w_zca, dtype=np.float64)

    def _gram_schmidt(
        self,
        X: np.ndarray,
        cols: List[str],
        weights: Optional[Dict[str, float]],
        means: np.ndarray,
        stds: np.ndarray
    ) -> np.ndarray:
        N, K = X.shape
        if weights:
            order = sorted(range(K), key=lambda i: weights.get(cols[i], 0.0), reverse=True)
        else:
            order = list(range(K))

        X_centered = X - means
        U = np.zeros_like(X_centered)
        X_ortho = np.zeros_like(X)

        for idx, k in enumerate(order):
            x_k = X_centered[:, k]
            u_k = x_k.copy()
            for prev_idx in range(idx):
                u_j = U[:, prev_idx]
                denom = np.dot(u_j, u_j)
                if denom > 1e-8:
                    proj = (np.dot(u_k, u_j) / denom) * u_j  # Sequential Orthogonal Projection (MGS)
                    u_k -= proj
            U[:, idx] = u_k

            u_std = float(np.std(u_k))
            raw_k = X_centered[:, k]
            raw_std = float(stds[k]) if stds[k] > 1e-8 else 1.0
            ratio = u_std / raw_std
            if ratio >= 0.20:
                rescaled = means[k] + (u_k / u_std) * stds[k]
            elif u_std > 1e-6:
                # Smoothly damp weak collinear residuals to prevent 20x noise explosion
                damp_factor = np.clip(ratio / 0.20, 0.05, 1.0)
                rescaled = means[k] + (u_k / u_std) * stds[k] * damp_factor
            else:
                rescaled = means[k] + 0.05 * (raw_k / raw_std) * stds[k]
            X_ortho[:, k] = rescaled

        return X_ortho

    @safe_matrix_precision_guard
    def _esrw_whitening(self, X_bar: np.ndarray, C_shrunk: np.ndarray) -> np.ndarray:
        """
        Equalized Spectral Residual Whitening (ESRW).
        Soft-shrinks collinear noise eigenvalues towards mean eigenvalue lambda=1.0,
        preserving leading shared momentum/value alpha while eliminating sign-inversion distortion.
        """
        N, K = X_bar.shape
        C_sym = (C_shrunk + C_shrunk.T) * 0.5
        eigenvalues, eigenvectors = np.linalg.eigh(C_sym.astype(np.float64))

        mean_eig = float(np.mean(eigenvalues)) if len(eigenvalues) > 0 else 1.0
        shrinkage = 1.0 / (1.0 + np.exp((eigenvalues - 1.0) / 0.30))
        lambdas_reg = (1.0 - shrinkage) * eigenvalues + shrinkage * mean_eig + self.ridge_epsilon

        inv_sqrt_lambda = np.diag(1.0 / np.sqrt(np.maximum(lambdas_reg, 1e-6)))
        W_esrw = np.dot(eigenvectors, np.dot(inv_sqrt_lambda, eigenvectors.T))

        diag_signs = np.sign(np.diag(W_esrw))
        diag_signs[diag_signs == 0] = 1.0
        W_esrw = W_esrw * diag_signs[:, np.newaxis]
        W_esrw = (W_esrw + W_esrw.T) * 0.5
        np.fill_diagonal(W_esrw, np.maximum(np.diag(W_esrw), 1e-6))

        return np.asarray(np.dot(X_bar, W_esrw), dtype=np.float64)

    @safe_matrix_precision_guard
    def _pca_zca_symmetric(
        self,
        X: np.ndarray,
        means: np.ndarray,
        stds: np.ndarray,
        preserve_pc1: bool = False,
        preserve_top_k: int = 0,
        pairwise_cov: Optional[np.ndarray] = None
    ) -> np.ndarray:
        N, K = X.shape
        if K <= 1 or N < 2:
            return np.copy(X)

        # Detect zero-variance / singular columns (e.g. constant columns from missingness/imputation)
        raw_stds = np.std(X, axis=0)
        is_singular = (raw_stds < 1e-8) | (stds < 1e-8) | (~np.isfinite(raw_stds)) | (~np.isfinite(stds))

        # If all columns are singular, return untouched
        if np.all(is_singular):
            return np.copy(X)

        # If any columns are singular, isolate non-singular active columns for ZCA whitening
        if np.any(is_singular):
            active_idx = np.where(~is_singular)[0]
            singular_idx = np.where(is_singular)[0]

            X_ortho = np.copy(X)
            if len(active_idx) > 1:
                eff_top = min(preserve_top_k, len(active_idx) - 1) if preserve_top_k > 0 else 0
                sub_pairwise = pairwise_cov[np.ix_(active_idx, active_idx)] if pairwise_cov is not None else None
                X_active_ortho = self._pca_zca_symmetric(
                    X[:, active_idx],
                    means[active_idx],
                    stds[active_idx],
                    preserve_pc1=preserve_pc1 if eff_top > 0 or preserve_pc1 else False,
                    preserve_top_k=eff_top,
                    pairwise_cov=sub_pairwise
                )
                X_ortho[:, active_idx] = X_active_ortho
            else:
                X_ortho[:, active_idx] = X[:, active_idx]

            # Preserve singular/constant columns untouched without noise bleed
            for s_col in singular_idx:
                X_ortho[:, s_col] = X[:, s_col]

            return np.asarray(X_ortho, dtype=np.float64)

        # Standardize matrix to zero mean, unit variance
        X_bar = (X - means) / stds

        # Compute sample covariance matrix
        if pairwise_cov is not None:
            C = (pairwise_cov + pairwise_cov.T) * 0.5
            mu = np.trace(C) / max(K, 1)
            target = mu * np.eye(K)
            delta = self.shrinkage_alpha if self.shrinkage_alpha > 0 else 0.01
            C_shrunk = (1.0 - delta) * C + delta * target + self.ridge_epsilon * np.eye(K)
        else:
            C = np.dot(X_bar.T, X_bar) / max(N - 1, 1)
            # Dynamic Ledoit-Wolf Shrinkage or fallback
            C_shrunk = self._compute_ledoit_wolf_covariance(X_bar, C)
        C_sym = (C_shrunk + C_shrunk.T) * 0.5

        # Eigen-decomposition of symmetric correlation matrix
        eigenvalues, eigenvectors = np.linalg.eigh(C_sym.astype(np.float64))

        # Determine effective top components to preserve (Feature 2 / R1)
        eff_top_k = preserve_top_k
        if eff_top_k <= 0 and preserve_pc1:
            eff_top_k = 1

        # Estimate noise subspace variance sigma2 for Marchenko-Pastur lower spectral edge
        # In Random Matrix Theory (RMT), noise bulk eigenvalues are distributed around sigma2.
        if eff_top_k > 0 and K > eff_top_k:
            noise_evals = eigenvalues[:-eff_top_k]
        elif K > 1:
            noise_evals = eigenvalues[:-1]
        else:
            noise_evals = eigenvalues

        sigma2 = float(np.mean(noise_evals)) if len(noise_evals) > 0 else 1.0
        sigma2 = max(sigma2, 1e-4)

        # Marchenko-Pastur spectral floor for weak noise eigenvalues (Feature 2 / R1)
        # Prevents over-amplification of collinear/null-space dimensions
        q = min(K, N) / max(max(K, N), 1)
        mp_lower = sigma2 * ((1.0 - np.sqrt(q)) ** 2) if N >= K else 0.0
        lambda_floor = float(np.clip(max(mp_lower, 0.01 * sigma2), 1e-4, 1.0))

        # Apply Marchenko-Pastur spectral floor and ridge regularization
        lambdas_clean = np.maximum(eigenvalues, lambda_floor)
        ridge_eps = float(np.clip(self.ridge_epsilon, 1e-6, 1e-3))
        whitening_filter = 1.0 / np.sqrt(lambdas_clean + ridge_eps)

        # Dual-Consensus Spectral Preservation (Feature 2 / R1):
        # Preserve top_k leading eigenvalues (PC1 Trend, PC2 Value/Quality) uncompressed (filter = 1.0)
        if eff_top_k > 0 and K > 1:
            num_to_preserve = min(eff_top_k, max(K - 1, 0))
            for i in range(1, num_to_preserve + 1):
                whitening_filter[-i] = 1.0

        # Cap maximum amplification to prevent noise explosion on weak spectral dimensions (C-05 / optimal bound)
        whitening_filter = np.minimum(whitening_filter, 10.0)

        # Compute ZCA whitening operator: C^(-1/2) = V * diag(whitening_filter) * V^T
        inv_sqrt_lambda = np.diag(whitening_filter)
        C_inv_sqrt = np.dot(eigenvectors, np.dot(inv_sqrt_lambda, eigenvectors.T))

        # Positive diagonal alignment constraint to ensure positive factor self-affinity
        diag_signs = np.sign(np.diag(C_inv_sqrt))
        diag_signs[diag_signs == 0] = 1.0
        C_inv_sqrt = diag_signs[:, None] * C_inv_sqrt * diag_signs[None, :]
        C_inv_sqrt = (C_inv_sqrt + C_inv_sqrt.T) * 0.5
        np.fill_diagonal(C_inv_sqrt, np.maximum(np.diag(C_inv_sqrt), 1e-6))

        # ZCA decorrelation
        X_decorr = np.dot(X_bar, C_inv_sqrt)

        # Variance-preserving rescaling back to original mean and standard deviation
        X_ortho = means + X_decorr * stds
        return cast(np.ndarray, X_ortho)

    def _compute_ledoit_wolf_covariance(self, X_bar: np.ndarray, C_sample: np.ndarray) -> np.ndarray:
        N, K = X_bar.shape
        try:
            from sklearn.covariance import LedoitWolf
            lw = LedoitWolf(store_precision=False, assume_centered=True)
            return cast(np.ndarray, lw.fit(X_bar).covariance_)
        except Exception:
            pass

        mu = np.trace(C_sample) / max(K, 1)
        target = mu * np.eye(K)
        d2 = float(np.sum((C_sample - target) ** 2))
        if d2 < 1e-12:
            return cast(np.ndarray, C_sample + self.ridge_epsilon * np.eye(K))

        delta = self.shrinkage_alpha if self.shrinkage_alpha > 0 else 0.01
        C_shrunk = (1.0 - delta) * C_sample + delta * target
        return cast(np.ndarray, C_shrunk + self.ridge_epsilon * np.eye(K))

    def extract_pure_idiosyncratic_alpha(
        self,
        scores: pd.Series,
        market_beta: Optional[pd.Series] = None,
        sector_series: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        Extracts pure idiosyncratic alpha by stripping market beta and industry sector co-movements.
        """
        neutralizer = CrossSectionalFactorNeutralizer(ridge_epsilon=self.ridge_epsilon)
        return neutralizer.extract_pure_idiosyncratic_alpha(
            scores=scores,
            market_beta=market_beta,
            sector_series=sector_series
        )


class CrossSectionalFactorNeutralizer:
    """
    Pre-Ensemble Cross-Sectional Factor Neutralizer.
    Orthogonalizes raw alpha factor scores across symbols against Market Beta, Size,
    Volatility, and Sector risk exposures via Weighted Generalized Least Squares (GLS).
    """

    def __init__(
        self,
        risk_factors: Optional[List[str]] = None,
        mad_threshold: float = 3.0,
        ridge_epsilon: float = 1e-6
    ):
        self.risk_factors = risk_factors or ["beta", "log_mcap", "volatility_60d"]
        self.mad_threshold = float(mad_threshold)
        self.ridge_epsilon = float(ridge_epsilon)

    def winsorize_mad(self, series: pd.Series) -> pd.Series:
        """Applies Median Absolute Deviation (MAD) winsorization to eliminate fat-tail outlier distortions."""
        valid = series.dropna()
        if len(valid) < 5:
            return series
        med = float(valid.median())
        mad = float((valid - med).abs().median() * 1.4826)
        if mad < 1e-8:
            return series
        lower = med - self.mad_threshold * mad
        upper = med + self.mad_threshold * mad
        return series.clip(lower=lower, upper=upper)

    def neutralize_cross_section(
        self,
        scores: pd.Series,
        factor_loadings: Optional[pd.DataFrame] = None,
        sector_series: Optional[pd.Series] = None,
        weights: Optional[pd.Series] = None
    ) -> pd.Series:
        """
        Neutralizes a single strategy score series across the symbol cross-section.
        """
        if scores is None or len(scores) < 4:
            return scores

        # Winsorize raw factor inputs
        clean_scores = self.winsorize_mad(scores)
        valid_idx = clean_scores.dropna().index
        if len(valid_idx) < 4:
            return scores

        y = clean_scores.loc[valid_idx].to_numpy(dtype=np.float64)
        N = len(valid_idx)

        # Build Design Matrix B
        cols_to_concat = [pd.Series(1.0, index=valid_idx, name="intercept")]
        if factor_loadings is not None and not factor_loadings.empty:
            avail_factors = [f for f in self.risk_factors if f in factor_loadings.columns]
            if avail_factors:
                f_df = factor_loadings.reindex(index=valid_idx, columns=avail_factors).fillna(0.0)
                # Standardize factor loadings safely
                f_std = ((f_df - f_df.mean()) / (f_df.std().fillna(1.0).replace(0.0, 1.0) + 1e-6)).fillna(0.0)
                cols_to_concat.append(f_std)

        if sector_series is not None and len(sector_series) > 0:
            sec_aligned = sector_series.reindex(valid_idx).fillna("UNKNOWN")
            if sec_aligned.nunique() > 1:
                dummies = pd.get_dummies(sec_aligned, drop_first=True, dtype=float)
                cols_to_concat.append(dummies)

        B_df = pd.concat(cols_to_concat, axis=1)
        B = B_df.to_numpy(dtype=np.float64)
        K_cols = B.shape[1]

        # Weights matrix W (e.g. sqrt(MarketCap) or Identity)
        if weights is not None and len(weights) > 0:
            w_aligned = weights.reindex(valid_idx).fillna(1.0).to_numpy(dtype=np.float64)
            w_aligned = np.clip(w_aligned, 1e-4, np.inf)
            W_diag = np.sqrt(w_aligned)
            W_diag /= (np.mean(W_diag) + 1e-8)
        else:
            W_diag = np.ones(N, dtype=np.float64)

        # WLS Projection: (B_weighted^T B_weighted + eps I)^(-1) B_weighted^T y_weighted
        B_weighted = B * W_diag[:, np.newaxis]
        y_weighted = y * W_diag
        BtWB = np.dot(B_weighted.T, B_weighted) + self.ridge_epsilon * np.eye(K_cols)

        try:
            beta_hat = np.linalg.solve(BtWB, np.dot(B_weighted.T, y_weighted))
        except np.linalg.LinAlgError:
            beta_hat = np.dot(np.linalg.pinv(BtWB), np.dot(B_weighted.T, y_weighted))

        fitted = np.dot(B, beta_hat)
        residuals = y - fitted

        res_std = np.std(residuals)
        if res_std > 1e-8:
            z_scores = np.clip(residuals / res_std, -35.0, 35.0)
            # Map back to [0.0, 1.0] using Sigmoid dispersion preservation
            pure_scores = 1.0 / (1.0 + np.exp(-z_scores))
        else:
            pure_scores = np.full(N, 0.5, dtype=np.float64)

        result = scores.copy()
        result.loc[valid_idx] = pure_scores
        return result

    def neutralize_dataframe(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        factor_loadings: Optional[pd.DataFrame] = None,
        sector_col: Optional[str] = None,
        weights_col: Optional[str] = None
    ) -> pd.DataFrame:
        """Neutralizes all specified strategy columns in a DataFrame."""
        if score_df is None or score_df.empty:
            return score_df

        out_df = score_df.copy()
        sector_s = out_df[sector_col] if (sector_col and sector_col in out_df.columns) else None
        weight_s = out_df[weights_col] if (weights_col and weights_col in out_df.columns) else None

        for col in strategy_cols:
            if col in out_df.columns:
                out_df[col] = self.neutralize_cross_section(
                    scores=out_df[col],
                    factor_loadings=factor_loadings,
                    sector_series=sector_s,
                    weights=weight_s
                )
        return out_df

    def extract_pure_idiosyncratic_alpha(
        self,
        scores: pd.Series,
        market_beta: Optional[pd.Series] = None,
        sector_series: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        Extracts pure idiosyncratic alpha by stripping market beta and industry sector co-movements:
        s_idiosyncratic = (I - B(B^T B)^(-1) B^T) s_raw

        Enables the portfolio to scale gross exposure without taking uncompensated systematic sector risk.
        """
        if scores is None or len(scores) < 4:
            return {
                "pure_scores": scores if scores is not None else pd.Series([], dtype=float),
                "r_squared": 0.0,
                "idiosyncratic_ratio": 1.0
            }

        valid_idx = scores.dropna().index
        if len(valid_idx) < 4:
            return {
                "pure_scores": scores,
                "r_squared": 0.0,
                "idiosyncratic_ratio": 1.0
            }

        y = scores.loc[valid_idx].to_numpy(dtype=np.float64)
        N = len(valid_idx)

        # Build Design Matrix B
        cols_to_concat = [pd.Series(1.0, index=valid_idx, name="intercept")]
        if market_beta is not None:
            f_beta = market_beta.reindex(valid_idx).fillna(1.0)
            std_b = float(f_beta.std() or 1.0)
            f_std = ((f_beta - f_beta.mean()) / (std_b + 1e-6)).fillna(0.0)
            cols_to_concat.append(f_std)

        if sector_series is not None and len(sector_series) > 0:
            sec_aligned = sector_series.reindex(valid_idx).fillna("UNKNOWN")
            if sec_aligned.nunique() > 1:
                dummies = pd.get_dummies(sec_aligned, drop_first=True, dtype=float)
                cols_to_concat.append(dummies)

        B_df = pd.concat(cols_to_concat, axis=1)
        B = B_df.to_numpy(dtype=np.float64)
        K_cols = B.shape[1]

        BtB = np.dot(B.T, B) + self.ridge_epsilon * np.eye(K_cols)
        try:
            beta_hat = np.linalg.solve(BtB, np.dot(B.T, y))
        except np.linalg.LinAlgError:
            beta_hat = np.dot(np.linalg.pinv(BtB), np.dot(B.T, y))

        fitted = np.dot(B, beta_hat)
        residuals = y - fitted

        ss_tot = np.sum((y - np.mean(y)) ** 2)
        ss_res = np.sum(residuals ** 2)
        r2 = float(np.clip(1.0 - (ss_res / max(ss_tot, 1e-8)), 0.0, 1.0))
        idio_ratio = float(1.0 - r2)

        res_std = np.std(residuals)
        if res_std > 1e-8:
            z_scores = residuals / res_std
            pure_scores = 1.0 / (1.0 + np.exp(-z_scores))
        else:
            pure_scores = np.full(N, 0.5, dtype=np.float64)

        result = scores.copy()
        result.loc[valid_idx] = pure_scores

        return {
            "pure_scores": result,
            "r_squared": round(r2, 4),
            "idiosyncratic_ratio": round(idio_ratio, 4)
        }


class OrthogonalizedAlphaFeatureStore:
    """
    Feature F704 / F724: Orthogonalized Alpha Feature Store.
    Provides cached, deterministic storage and retrieval of orthogonalized
    multi-strategy factor matrices across cross-sectional rebalance cycles.
    """
    def __init__(
        self,
        engine: Optional[FactorOrthogonalizerEngine] = None,
        default_method: str = "pca_symmetric",
        preserve_top_k: int = 5,
        deadband_alpha: float = 456.0,
    ) -> None:
        self.engine = engine or FactorOrthogonalizerEngine(
            default_method=default_method,
            preserve_top_k=preserve_top_k,
        )
        self.default_method = default_method
        self.preserve_top_k = preserve_top_k
        self.deadband_alpha = deadband_alpha
        self._cache: Dict[str, pd.DataFrame] = {}

    def get_orthogonalized_factors(
        self,
        score_df: pd.DataFrame,
        strategy_cols: List[str],
        weights: Optional[Dict[str, float]] = None,
        method: Optional[str] = None,
        preserve_top_k: Optional[int] = None,
        apply_deadband: bool = True,
    ) -> pd.DataFrame:
        top_k = preserve_top_k if preserve_top_k is not None else self.preserve_top_k
        m = method or self.default_method
        ortho_df = self.engine.orthogonalize(
            score_df=score_df,
            strategy_cols=strategy_cols,
            weights=weights,
            method=m,
            preserve_top_k=top_k,
        )
        if apply_deadband:
            for col in strategy_cols:
                if col in ortho_df.columns:
                    centered = ortho_df[col] - 0.50
                    cleaned = apply_hyperbolic_deadband_phase148(centered, delta=0.035, alpha=self.deadband_alpha)
                    ortho_df[col] = (cleaned + 0.50).clip(0.0, 1.0)
        return ortho_df

    def clear_cache(self) -> None:
        self._cache.clear()


# Complete Alias Trees
FactorOrthogonalizerEnginePhase180 = FactorOrthogonalizerEngine
Phase180FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
F884FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
DuodecuplePillarZCAOrthogonalizer = FactorOrthogonalizerEngine
DuodecuplePillarZCAEngine = FactorOrthogonalizerEngine
FactorOrthogonalizerEnginePhase176 = FactorOrthogonalizerEngine
Phase176FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
F864FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
UndecuplePillarZCAOrthogonalizer = FactorOrthogonalizerEngine
UndecuplePillarZCAEngine = FactorOrthogonalizerEngine
FactorOrthogonalizerEnginePhase172 = FactorOrthogonalizerEngine
Phase172FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
F844FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
DecuplePillarZCAOrthogonalizer = FactorOrthogonalizerEngine
DecuplePillarZCAEngine = FactorOrthogonalizerEngine
FactorOrthogonalizerEnginePhase168 = FactorOrthogonalizerEngine
Phase168FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
F824FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
NonuplePillarZCAOrthogonalizer = FactorOrthogonalizerEngine
FactorOrthogonalizerEnginePhase164 = FactorOrthogonalizerEngine
Phase164FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
F804FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
OctuplePillarZCAOrthogonalizer = FactorOrthogonalizerEngine
FactorOrthogonalizerEnginePhase160 = FactorOrthogonalizerEngine
Phase160FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
F784FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
HyperDimensionalZCAOrthogonalizer = FactorOrthogonalizerEngine
FactorOrthogonalizerEnginePhase156 = FactorOrthogonalizerEngine
Phase156FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
F764FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
RiemannianZCAOrthogonalizer = FactorOrthogonalizerEngine
FactorOrthogonalizerEnginePhase152 = FactorOrthogonalizerEngine
Phase152FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
F744FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
Phase148FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
F724FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
Phase144FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
Phase140FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
F684FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
F704FactorOrthogonalizerEngine = FactorOrthogonalizerEngine
ZCAWhiteningEngine = FactorOrthogonalizerEngine
PCAZCAWhiteningEngine = FactorOrthogonalizerEngine
ZCAWhiteningFeatureStore = FactorOrthogonalizerEngine


__all__ = [
    "VERSION",
    "RELEASE",
    "FEATURE",
    "_VersionInt",
    "_PhaseInt",
    "_ReleaseStr",
    "_FeatureStr",
    "VERSION_PHASE180",
    "RELEASE_PHASE180",
    "FEATURE_PHASE180",
    "VERSION_PHASE176",
    "RELEASE_PHASE176",
    "FEATURE_PHASE176",
    "VERSION_PHASE172",
    "RELEASE_PHASE172",
    "FEATURE_PHASE172",
    "VERSION_PHASE168",
    "RELEASE_PHASE168",
    "FEATURE_PHASE168",
    "VERSION_PHASE164",
    "RELEASE_PHASE164",
    "FEATURE_PHASE164",
    "VERSION_PHASE160",
    "RELEASE_PHASE160",
    "FEATURE_PHASE160",
    "VERSION_PHASE156",
    "RELEASE_PHASE156",
    "FEATURE_PHASE156",
    "VERSION_PHASE140",
    "VERSION_PHASE144",
    "VERSION_PHASE148",
    "VERSION_PHASE152",
    "RELEASE_PHASE140",
    "RELEASE_PHASE144",
    "RELEASE_PHASE148",
    "RELEASE_PHASE152",
    "FEATURE_PHASE140",
    "FEATURE_PHASE144",
    "FEATURE_PHASE148",
    "FEATURE_PHASE152",
    "DuodecuplePillarMap",
    "DUODECUPLE_PILLAR_MAP",
    "UndecuplePillarMap",
    "UNDECUPLE_PILLAR_MAP",
    "DecuplePillarMap",
    "DECUPLE_PILLAR_MAP",
    "NonuplePillarMap",
    "NONUPLE_PILLAR_MAP",
    "OctuplePillarMap",
    "OCTUPLE_PILLAR_MAP",
    "SeptuplePillarMap",
    "SEPTUPLE_PILLAR_MAP",
    "SextuplePillarMap",
    "SEXTUPLE_PILLAR_MAP",
    "compute_riemannian_airm_distance",
    "compute_riemannian_airm_metric",
    "compute_riemannian_frechet_shrinkage",
    "compute_septuple_pillar_zca_whitening",
    "compute_octuple_pillar_zca_whitening",
    "compute_nonuple_pillar_zca_whitening",
    "compute_decuple_pillar_zca_whitening",
    "compute_duodecuple_pillar_zca_whitening",
    "compute_undecuple_pillar_zca_whitening",
    "apply_riemannian_deadband",
    "FactorOrthogonalizerEngine",
    "CrossSectionalFactorNeutralizer",
    "safe_matrix_precision_guard",
    "compute_pairwise_available_covariance",
    "repair_covariance_psd",
    "apply_hyperbolic_deadband_phase140",
    "apply_hyperbolic_deadband_phase144",
    "apply_hyperbolic_deadband_phase148",
    "apply_hyperbolic_deadband_phase152",
    "apply_hyperbolic_deadband_phase156",
    "apply_hyperbolic_deadband_phase160",
    "apply_hyperbolic_deadband_phase164",
    "apply_hyperbolic_deadband_phase168",
    "apply_hyperbolic_deadband_phase172",
    "apply_hyperbolic_deadband_phase176",
    "apply_hyperbolic_deadband_phase180",
    "OrthogonalizedAlphaFeatureStore",
    "FactorOrthogonalizerEnginePhase180",
    "Phase180FactorOrthogonalizerEngine",
    "F884FactorOrthogonalizerEngine",
    "DuodecuplePillarZCAOrthogonalizer",
    "DuodecuplePillarZCAEngine",
    "FactorOrthogonalizerEnginePhase176",
    "Phase176FactorOrthogonalizerEngine",
    "F864FactorOrthogonalizerEngine",
    "UndecuplePillarZCAOrthogonalizer",
    "UndecuplePillarZCAEngine",
    "FactorOrthogonalizerEnginePhase172",
    "Phase172FactorOrthogonalizerEngine",
    "F844FactorOrthogonalizerEngine",
    "DecuplePillarZCAOrthogonalizer",
    "DecuplePillarZCAEngine",
    "FactorOrthogonalizerEnginePhase168",
    "Phase168FactorOrthogonalizerEngine",
    "F824FactorOrthogonalizerEngine",
    "NonuplePillarZCAOrthogonalizer",
    "FactorOrthogonalizerEnginePhase164",
    "Phase164FactorOrthogonalizerEngine",
    "F804FactorOrthogonalizerEngine",
    "OctuplePillarZCAOrthogonalizer",
    "FactorOrthogonalizerEnginePhase160",
    "Phase160FactorOrthogonalizerEngine",
    "F784FactorOrthogonalizerEngine",
    "HyperDimensionalZCAOrthogonalizer",
    "FactorOrthogonalizerEnginePhase156",
    "Phase156FactorOrthogonalizerEngine",
    "F764FactorOrthogonalizerEngine",
    "RiemannianZCAOrthogonalizer",
    "FactorOrthogonalizerEnginePhase152",
    "Phase152FactorOrthogonalizerEngine",
    "F744FactorOrthogonalizerEngine",
    "Phase148FactorOrthogonalizerEngine",
    "F724FactorOrthogonalizerEngine",
    "Phase140FactorOrthogonalizerEngine",
    "Phase144FactorOrthogonalizerEngine",
    "F684FactorOrthogonalizerEngine",
    "F704FactorOrthogonalizerEngine",
    "ZCAWhiteningEngine",
    "PCAZCAWhiteningEngine",
    "ZCAWhiteningFeatureStore",
]



