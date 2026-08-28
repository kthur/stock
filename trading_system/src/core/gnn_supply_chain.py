# -*- coding: utf-8 -*-
"""
GNNSupplyChainEngine: Relational Graph Neural Network & Supply Chain Peer Momentum Engine.
Propagates upstream/downstream returns, supply-chain demand shocks, and institutional flow across the industry graph.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class GNNSupplyChainEngine:
    """
    Relational Graph Propagation Engine for Supply Chain & Industry Peer Spillover Momentum.
    """

    # Comprehensive multi-sector graph edges (Source Leader -> Target Beneficiary, Edge Weight)
    EXTENDED_GRAPH_EDGES = [
        # AI / Semiconductor
        ('NVDA', 'TSM', 0.85), ('NVDA', '000660', 0.90), ('NVDA', '005930', 0.70),
        ('AAPL', 'TSM', 0.75), ('AAPL', '005930', 0.60), ('AAPL', '066570', 0.50),
        ('000660', '042700', 0.80), ('000660', '036540', 0.75), ('005930', '005290', 0.65),
        ('ASML', '005930', 0.70), ('ASML', '000660', 0.70), ('AMD', 'TSM', 0.80),
        # Defense & Aerospace
        ('012450', '079550', 0.80), ('012450', '047810', 0.75), ('079550', '005380', 0.50),
        ('LMT', 'RTX', 0.75), ('RTX', '012450', 0.60),
        # Power Grid & Energy
        ('267260', '010120', 0.85), ('267260', '028670', 0.75), ('010120', '028670', 0.70),
        ('GE', '267260', 0.65), ('ETN', '010120', 0.60),
        # Shipbuilding & Marine
        ('009540', '010140', 0.85), ('042660', '010140', 0.80), ('009540', '042660', 0.70),
        # Bio / Pharma
        ('207940', '068270', 0.65), ('000100', '185750', 0.75), ('LLY', 'NVO', 0.80),
        ('LLY', '207940', 0.60), ('PFE', '000100', 0.50),
        # EV & Battery
        ('TSLA', '373220', 0.75), ('TSLA', '006400', 0.70), ('373220', '247540', 0.85),
        ('006400', '051910', 0.80), ('373220', '086520', 0.75),
    ]

    def __init__(self,
                 decay_factor: float = 0.85,
                 hops: int = 2,
                 lookback_days: int = 5):
        self.decay_factor = decay_factor
        self.hops = hops
        self.lookback_days = lookback_days
        self._build_adjacency()

    def _build_adjacency(self):
        self.adj: Dict[str, List[Tuple[str, float]]] = {}  # source -> [(target, weight)]
        self.in_adj: Dict[str, List[Tuple[str, float]]] = {} # target -> [(source, weight)]
        self.all_nodes: Set[str] = set()

        for src, dst, w in self.EXTENDED_GRAPH_EDGES:
            src_u, dst_u = src.upper(), dst.upper()
            self.all_nodes.add(src_u)
            self.all_nodes.add(dst_u)

            if src_u not in self.adj:
                self.adj[src_u] = []
            self.adj[src_u].append((dst_u, float(w)))

            if dst_u not in self.in_adj:
                self.in_adj[dst_u] = []
            self.in_adj[dst_u].append((src_u, float(w)))

    def compute_graph_momentum(self,
                               prices_dict: Dict[str, pd.DataFrame],
                               universe_symbols: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Computes 2-hop message-passed momentum scores across the supply-chain graph.
        Returns: {symbol: momentum_score [0.0, 1.0]}
        """
        # Step 1: Compute node-level initial momentum features
        node_mom: Dict[str, float] = {}
        for sym, df in prices_dict.items():
            sym_u = sym.upper()
            if df is None or len(df) < 5:
                continue

            close_col = next((c for c in df.columns if str(c).lower() in ('close', 'adj close', 'adjclose')), None)
            if not close_col:
                continue

            close_s = pd.to_numeric(df[close_col], errors='coerce').dropna()
            if len(close_s) < 5:
                continue

            ret_1d = float((close_s.iloc[-1] / close_s.iloc[-2]) - 1.0) if len(close_s) >= 2 else 0.0
            ret_3d = float((close_s.iloc[-1] / close_s.iloc[-4]) - 1.0) if len(close_s) >= 4 else 0.0
            ret_5d = float((close_s.iloc[-1] / close_s.iloc[-5]) - 1.0) if len(close_s) >= 5 else 0.0

            # Composite initial lead momentum: 50% 1d + 30% 3d + 20% 5d
            mom_composite = 0.50 * ret_1d + 0.30 * ret_3d + 0.20 * ret_5d
            node_mom[sym_u] = mom_composite

        # Step 2: Message Passing (Graph Convolution / Attention)
        # Hop 1
        hop1_signals: Dict[str, float] = {}
        for target, in_edges in self.in_adj.items():
            weighted_sum = 0.0
            weight_norm = 0.0
            for source, weight in in_edges:
                s_mom = node_mom.get(source, 0.0)
                weighted_sum += s_mom * weight
                weight_norm += weight
            if weight_norm > 0:
                hop1_signals[target] = weighted_sum / weight_norm

        # Hop 2 (Decayed propagation)
        hop2_signals: Dict[str, float] = {}
        for target, in_edges in self.in_adj.items():
            weighted_sum = 0.0
            weight_norm = 0.0
            for source, weight in in_edges:
                s_hop1 = hop1_signals.get(source, node_mom.get(source, 0.0))
                weighted_sum += s_hop1 * weight
                weight_norm += weight
            if weight_norm > 0:
                hop2_signals[target] = weighted_sum / weight_norm

        # Step 3: Combine self-momentum with propagated supply-chain heat
        final_scores: Dict[str, float] = {}
        target_symbols = universe_symbols if universe_symbols is not None else list(prices_dict.keys())

        for sym in target_symbols:
            sym_u = sym.upper()
            raw_self = node_mom.get(sym_u, 0.0)
            h1 = hop1_signals.get(sym_u, 0.0)
            h2 = hop2_signals.get(sym_u, 0.0)

            # Combined graph spillover momentum
            graph_signal = 0.40 * raw_self + 0.40 * h1 + 0.20 * h2

            # Map to sigmoid score [0.0, 1.0] centered at 0.50 (scale factor 15.0)
            score = 1.0 / (1.0 + np.exp(-15.0 * graph_signal))
            final_scores[sym] = float(np.clip(score, 0.01, 0.99))

        return final_scores
