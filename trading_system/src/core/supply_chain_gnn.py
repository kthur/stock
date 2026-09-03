"""
supply_chain_gnn.py — Supply Chain GNN & Sector Flow Dynamics Strategy Engine.

Performs 2-hop relational graph message passing across global anchor leaders and supplier/vendor
networks with non-linear bullwhip shock amplification and sector flow liquidity momentum.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd

from .base_strategy import BaseStrategyEngine, make_score_dataframe
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)

# Extended Multi-Market Value Chain Graph Edges (Source / Lead Anchor -> Target Supplier / Beneficiary, Edge Weight)
GLOBAL_VALUE_CHAIN_EDGES: List[Tuple[str, str, float]] = [
    # AI, Semiconductor Memory, Foundries & Equipment
    ("NVDA", "TSM", 0.90), ("NVDA", "000660", 0.90), ("NVDA", "005930", 0.75),
    ("AAPL", "TSM", 0.85), ("AAPL", "005930", 0.65), ("AAPL", "066570", 0.50),
    ("MSFT", "NVDA", 0.80), ("GOOGL", "NVDA", 0.80), ("AMZN", "NVDA", 0.80),
    ("TSM", "ASML", 0.85), ("TSM", "AMAT", 0.80), ("TSM", "LRCX", 0.80), ("TSM", "KLAC", 0.75),
    ("000660", "042700", 0.85),  # SK Hynix -> Hanmi Semiconductor (HBM Dual TC Bonder)
    ("000660", "036540", 0.75),  # SK Hynix -> SFA
    ("000660", "240810", 0.75),  # SK Hynix -> Wonik IPS
    ("005930", "042700", 0.75),  # Samsung -> Hanmi Semiconductor
    ("005930", "005290", 0.65),  # Samsung -> Dongjin Semichem
    ("005930", "101490", 0.70),  # Samsung -> SnS Tech
    ("005930", "039030", 0.70),  # Samsung -> EO Technics
    ("005930", "067310", 0.65),  # Samsung -> Hana Micron
    ("ASML", "005930", 0.75), ("ASML", "000660", 0.75),
    ("AMD", "TSM", 0.80), ("QCOM", "TSM", 0.80), ("AVGO", "TSM", 0.80),

    # EV, Battery & Clean Energy Value Chain
    ("TSLA", "373220", 0.85),  # Tesla -> LG Energy Solution
    ("TSLA", "006400", 0.75),  # Tesla -> Samsung SDI
    ("373220", "247540", 0.90),  # LGES -> Ecopro BM (Cathode)
    ("373220", "086520", 0.80),  # LGES -> Ecopro
    ("373220", "003670", 0.85),  # LGES -> POSCO Future M
    ("006400", "051910", 0.80),  # Samsung SDI -> LG Chem
    ("006400", "247540", 0.80),  # Samsung SDI -> Ecopro BM
    ("006400", "278280", 0.75),  # Samsung SDI -> Chunbo
    ("GM", "373220", 0.75), ("F", "373220", 0.70),

    # Defense & Aerospace Value Chain
    ("LMT", "RTX", 0.75), ("RTX", "012450", 0.65), ("BA", "047810", 0.70),
    ("012450", "079550", 0.85),  # Hanwha Aerospace -> LIG Nex1
    ("012450", "047810", 0.80),  # Hanwha Aerospace -> KAI
    ("012450", "272210", 0.80),  # Hanwha Aerospace -> Hanwha Systems
    ("079550", "005380", 0.55),  # LIG Nex1 -> Hyundai Motor (Defense/Mobility)
    ("012450", "064350", 0.75),  # Hanwha Aero -> Hyundai Rotem

    # AI Data Center Power Grid & Infrastructure
    ("GE", "267260", 0.75),  # GE -> HD Hyundai Electric
    ("ETN", "010120", 0.70),  # Eaton -> LS Electric
    ("PWR", "298040", 0.70),  # Quanta -> Hyosung Heavy
    ("267260", "010120", 0.85),  # HD Hyundai Electric -> LS Electric
    ("267260", "298040", 0.80),  # HD Hyundai Electric -> Hyosung Heavy
    ("010120", "028670", 0.70),  # LS Electric -> Pan Ocean (Power Cable Logistics)

    # Shipbuilding & LNG Energy Logistics
    ("XOM", "329180", 0.75), ("CVX", "042660", 0.75),
    ("329180", "010140", 0.80),  # HD Hyundai Heavy -> Samsung Heavy
    ("042660", "010140", 0.80),  # Hanwha Ocean -> Samsung Heavy
    ("329180", "042660", 0.75),  # HD Hyundai Heavy -> Hanwha Ocean

    # Global Pharma / Bio CDMO
    ("LLY", "NVO", 0.80), ("LLY", "207940", 0.65), ("NVO", "207940", 0.65),
    ("PFE", "207940", 0.65), ("PFE", "000100", 0.60),
    ("207940", "068270", 0.70),  # Samsung Bio -> Celltrion
    ("000100", "185750", 0.75),  # Yuhan -> Chong Kun Dang

    # Automotive OEM & Mobility Tier-1
    ("TSLA", "005380", 0.70), ("TM", "005380", 0.65),
    ("005380", "000270", 0.90),  # Hyundai Motor -> Kia
    ("005380", "012330", 0.90),  # Hyundai Motor -> Hyundai Mobis
    ("005380", "018880", 0.80),  # Hyundai Motor -> Hanon Systems
    ("005380", "204320", 0.80),  # Hyundai Motor -> HL Mando
    ("005380", "005850", 0.75),  # Hyundai Motor -> SL Corp
]


@register_strategy(
    StrategyMeta(
        strategy_id="supply_chain_gnn",
        display_name="Supply Chain GNN & Sector Flow Dynamics",
        score_column="supply_chain_gnn_score",
        category="network",
        output_file="supply_chain_gnn_predictions.txt",
        default_regime_weights={
            "BEAR_LOW_VOL": 0.02,
            "BEAR_HIGH_VOL": 0.01,
            "SIDEWAYS_LOW_VOL": 0.03,
            "SIDEWAYS_HIGH_VOL": 0.03,
            "BULL_LOW_VOL": 0.04,
            "BULL_HIGH_VOL": 0.04,
            "BEAR": 0.02,
            "SIDEWAYS": 0.03,
            "BULL": 0.04,
        },
    )
)
class SupplyChainGNNEngine(BaseStrategyEngine):
    """
    Relational Graph Propagation & Supply Chain GNN Engine.

    Executes 2-hop message passing with non-linear asymmetric Bullwhip shock
    amplification (1.35x downside / 0.85x upside) and sector liquidity flow acceleration.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        custom_edges: Optional[List[Tuple[str, str, float]]] = None,
        decay_factor: float = 0.50
    ) -> None:
        super().__init__(name="SupplyChainGNNEngine", config=config)
        self.edges = custom_edges or GLOBAL_VALUE_CHAIN_EDGES
        self.decay_factor = decay_factor
        self._build_graph()

    def _canon_sym(self, s: str) -> str:
        s_str = str(s).strip()
        return s_str.split(".")[0].zfill(6) if s_str.split(".")[0].isdigit() else s_str.upper()

    def _build_graph(self) -> None:
        self.in_adj: Dict[str, List[Tuple[str, float]]] = {}
        self.out_adj: Dict[str, List[Tuple[str, float]]] = {}
        self.all_nodes: Set[str] = set()

        for src, dst, w in self.edges:
            src_c = self._canon_sym(src)
            dst_c = self._canon_sym(dst)
            w_f = float(w)

            self.all_nodes.add(src_c)
            self.all_nodes.add(dst_c)

            if dst_c not in self.in_adj:
                self.in_adj[dst_c] = []
            self.in_adj[dst_c].append((src_c, w_f))

            if src_c not in self.out_adj:
                self.out_adj[src_c] = []
            self.out_adj[src_c].append((dst_c, w_f))

    def _compute_node_features(
        self, prices_dict: Dict[str, pd.DataFrame]
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Computes base node initial momentum h_i^(0) and volume surge ratio for each symbol.
        """
        node_mom: Dict[str, float] = {}
        node_flow: Dict[str, float] = {}

        for sym, df in prices_dict.items():
            sym_c = self._canon_sym(sym)
            df_ohlcv = self.extract_ohlcv(sym, prices_dict, min_bars=5)
            if df_ohlcv is None or df_ohlcv.empty or len(df_ohlcv) < 5:
                continue

            try:
                close_s = pd.to_numeric(df_ohlcv["Close"], errors="coerce").dropna()
                vol_s = pd.to_numeric(df_ohlcv["Volume"], errors="coerce").fillna(0.0) if "Volume" in df_ohlcv.columns else pd.Series(dtype=float)

                if len(close_s) < 5:
                    continue

                c_now = float(close_s.iloc[-1])
                c_1d = float(close_s.iloc[-2]) if len(close_s) >= 2 else c_now
                c_3d = float(close_s.iloc[-4]) if len(close_s) >= 4 else c_1d
                c_5d = float(close_s.iloc[-5]) if len(close_s) >= 5 else c_3d

                r1 = (c_now / c_1d - 1.0) if c_1d > 0 else 0.0
                r3 = (c_now / c_3d - 1.0) if c_3d > 0 else 0.0
                r5 = (c_now / c_5d - 1.0) if c_5d > 0 else 0.0

                # Initial base momentum h_i^(0)
                mom = 0.50 * r1 + 0.30 * r3 + 0.20 * r5
                if not np.isfinite(mom):
                    mom = 0.0
                node_mom[sym_c] = float(mom)

                # Node flow acceleration: 1D return * volume surge ratio
                if len(vol_s) >= 20:
                    v_now = float(vol_s.iloc[-1])
                    v_sma = float(vol_s.tail(20).mean())
                    if np.isfinite(v_now) and np.isfinite(v_sma) and v_sma > 0:
                        v_ratio = (v_now / v_sma)
                    else:
                        v_ratio = 1.0
                else:
                    v_ratio = 1.0

                if not np.isfinite(v_ratio):
                    v_ratio = 1.0

                flow_val = float(r1 * np.clip(v_ratio, 0.5, 3.0)) if np.isfinite(r1) else 0.0
                if not np.isfinite(flow_val):
                    flow_val = 0.0
                node_flow[sym_c] = flow_val

            except Exception as e:
                logger.debug(f"[SupplyChainGNN] Feature error for {sym}: {e}")

        return node_mom, node_flow

    def _propagate_message_passing(
        self, node_mom: Dict[str, float]
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Executes 2-hop message passing with asymmetric Bullwhip amplification:
        Negative source returns amplify by 1.35x; Positive expand at 0.85x.
        """
        def bullwhip_transform(r: float) -> float:
            if not np.isfinite(r):
                return 0.0
            # Bullwhip Operational Leverage: Upstream suppliers experience amplified demand surges (1.25x)
            # and sharp downside inventory correction shocks (1.35x)
            return float(r * 1.35) if r < 0 else float(r * 1.25)

        # Hop 1 (Linear neighbor momentum aggregation followed by bullwhip operational leverage transform)
        hop1: Dict[str, float] = {}
        for target, in_edges in self.in_adj.items():
            w_sum = 0.0
            w_total = 0.0
            for src, weight in in_edges:
                s_ret = node_mom.get(src, 0.0)
                if not np.isfinite(s_ret):
                    s_ret = 0.0
                w_sum += s_ret * weight
                w_total += weight
            if w_total > 0:
                raw_h1 = w_sum / w_total
                hop1[target] = bullwhip_transform(raw_h1)

        # Hop 2 (Propagate 1-hop representations without compounding bullwhip multiplier exponentially)
        hop2: Dict[str, float] = {}
        for target, in_edges in self.in_adj.items():
            w_sum = 0.0
            w_total = 0.0
            for src, weight in in_edges:
                # Use hop1 if available, else direct node_mom
                s_hop1 = hop1.get(src, node_mom.get(src, 0.0))
                if not np.isfinite(s_hop1):
                    s_hop1 = 0.0
                w_sum += s_hop1 * weight
                w_total += weight
            if w_total > 0:
                hop2[target] = w_sum / w_total

        return hop1, hop2

    def calculate_scores(
        self,
        symbols: Optional[List[str]] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Universal calculate_scores method compatible with all test suites and pipeline runners."""
        if prices_dict is None and isinstance(symbols, dict):
            prices_dict = symbols
            symbols = None
        if symbols is not None and prices_dict is not None:
            prices_dict = {s: prices_dict[s] for s in symbols if s in prices_dict}
        return self.compute_scores(prices_dict=prices_dict, **kwargs)

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Supply Chain GNN & Sector Flow momentum scores.

        Returns:
            pd.DataFrame / ScoreDataFrame with ['symbol', 'supply_chain_gnn_score']
        """
        prices_source = kwargs.get("df_prices", prices_dict)
        sector_map: Dict[str, str] = kwargs.get("sector_map") or {}

        if not prices_source:
            return make_score_dataframe({}, score_column="supply_chain_gnn_score")

        if isinstance(prices_source, dict):
            p_dict = prices_source
            symbols = list(p_dict.keys())
        elif isinstance(prices_source, pd.DataFrame):
            if "symbol" in prices_source.columns:
                symbols = prices_source["symbol"].dropna().astype(str).unique().tolist()
                p_dict = {s: prices_source[prices_source["symbol"] == s] for s in symbols}
            else:
                symbols = list(prices_source.columns)
                p_dict = {col: pd.DataFrame({"Close": prices_source[col]}) for col in symbols}
        else:
            return make_score_dataframe({}, score_column="supply_chain_gnn_score")

        node_mom, node_flow = self._compute_node_features(p_dict)
        hop1, hop2 = self._propagate_message_passing(node_mom)

        # Compute sector aggregate flow momentum
        sector_flows: Dict[str, List[float]] = {}
        for sym in symbols:
            sym_c = self._canon_sym(sym)
            sec = sector_map.get(str(sym), sector_map.get(sym_c, "Default"))
            f_val = node_flow.get(sym_c, 0.0)
            if not np.isfinite(f_val):
                f_val = 0.0
            if sec not in sector_flows:
                sector_flows[sec] = []
            sector_flows[sec].append(f_val)

        sector_flow_boost: Dict[str, float] = {}
        for sec, flows in sector_flows.items():
            valid_flows = [f for f in flows if np.isfinite(f)]
            sector_flow_boost[sec] = float(np.mean(valid_flows)) if valid_flows else 0.0

        scores: Dict[str, float] = {}

        for sym in symbols:
            sym_str = str(sym).strip()
            sym_c = self._canon_sym(sym_str)

            raw_self = node_mom.get(sym_c, 0.0)
            if not np.isfinite(raw_self):
                raw_self = 0.0
            h1 = hop1.get(sym_c, 0.0)
            if not np.isfinite(h1):
                h1 = 0.0
            h2 = hop2.get(sym_c, 0.0)
            if not np.isfinite(h2):
                h2 = 0.0

            sec = sector_map.get(sym_str, sector_map.get(sym_c, "Default"))
            flow_boost = sector_flow_boost.get(sec, 0.0)
            if not np.isfinite(flow_boost):
                flow_boost = 0.0

            # Check if node is part of value chain graph
            is_in_graph = (sym_c in self.all_nodes) or (sym_c in self.in_adj) or (h1 != 0.0) or (h2 != 0.0)

            if is_in_graph:
                # Composite graph message-passed momentum + sector flow
                graph_signal = (
                    0.35 * raw_self +
                    0.40 * h1 +
                    0.25 * h2 * self.decay_factor +
                    0.20 * flow_boost
                )
                # Graph Resonance Ignition: Constructive multi-hop supply chain cascade
                if h1 >= 0.025 and h2 >= 0.015 and raw_self >= 0.0:
                    graph_signal += 0.020
            else:
                # Isolated node fallback: blend self-momentum with sector flow
                graph_signal = 0.70 * raw_self + 0.30 * flow_boost

            if not np.isfinite(graph_signal):
                graph_signal = 0.0

            # Sigmoid activation mapping to [0.05, 0.95] centered at 0.50
            clipped_exp = np.clip(-14.0 * graph_signal, -50.0, 50.0)
            raw_score = 1.0 / (1.0 + np.exp(clipped_exp))
            if not np.isfinite(raw_score):
                clipped_score = 0.50
            else:
                clipped_score = float(np.clip(raw_score, 0.05, 0.95))

            if not np.isfinite(clipped_score):
                clipped_score = 0.50
            scores[sym_str] = round(clipped_score, 4)

        res_df = make_score_dataframe(scores, score_column="supply_chain_gnn_score")
        if not res_df.empty:
            s_series = pd.to_numeric(res_df['supply_chain_gnn_score'], errors='coerce').fillna(0.50).clip(0.05, 0.95)
            if len(res_df) > 1:
                ranks = s_series.rank(pct=True, ascending=True)
                # Multi-Tier Supply Chain GNN Booster (Top 5% receives 1.15x, Top 15% receives 1.10x)
                enhanced = np.where(ranks >= 0.95, (s_series * 1.15).clip(0.05, 0.95),
                           np.where(ranks >= 0.85, (s_series * 1.10).clip(0.05, 0.95), s_series))
                res_df['supply_chain_gnn_score'] = pd.to_numeric(pd.Series(enhanced, index=res_df.index), errors='coerce').fillna(0.50).clip(0.05, 0.95)
            else:
                res_df['supply_chain_gnn_score'] = s_series
        return res_df


def supply_chain_gnn_score(
    prices_dict: Any,
    **kwargs: Any
) -> pd.DataFrame:
    """
    Convenience function to compute Supply Chain GNN & Sector Flow scores.
    """
    engine = SupplyChainGNNEngine()
    return engine.compute_scores(prices_dict=prices_dict, **kwargs)
