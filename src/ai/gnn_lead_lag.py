"""
Graph Neural Network (GNN / GAT) Supply Chain Lead-Lag Model (Strategy #36)
Models Graph Attention Network (GAT) node attention across supply chain & industry networks for n-stage lead-lag propagation.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GNNSupplyChainLeadLagEngine:
    """
    Strategy #36: Graph Neural Network (GAT) Supply Chain Lead-Lag Model.
    Computes graph attention weights alpha_ij over company supply chain edges to predict delayed price movement.
    """

    def __init__(self, num_heads: int = 4, alpha_leakage: float = 0.2):
        self.num_heads = num_heads
        self.alpha_leakage = alpha_leakage

    def _compute_gat_attention(self, leader_ret: float, follower_ret: float, edge_weight: float = 1.0) -> float:
        """
        Calculates Graph Attention coefficient alpha_ij between leader node j and follower node i.
        """
        l_ret = float(leader_ret) if (leader_ret is not None and np.isfinite(leader_ret)) else 0.0
        f_ret = float(follower_ret) if (follower_ret is not None and np.isfinite(follower_ret)) else 0.0
        ew = float(edge_weight) if (edge_weight is not None and np.isfinite(edge_weight)) else 1.0

        # LeakyReLU attention mechanism
        a_input = (l_ret - f_ret) * ew
        attn = np.maximum(a_input, a_input * self.alpha_leakage)
        attn_clipped = np.clip(attn, -50.0, 50.0)
        alpha = float(1.0 / (1.0 + np.exp(-attn_clipped)))
        return float(np.clip(alpha, 0.0, 1.0))

    def calculate_scores(
        self,
        universe_df: pd.DataFrame,
        prices_dict: Dict[str, pd.DataFrame],
        supply_chain_graph: Optional[Dict[str, List[str]]] = None
    ) -> pd.DataFrame:
        """
        Calculates Strategy #36 GNN Supply Chain scores across all stocks in universe.
        """
        results = []

        # Build 1-day price momentum for all symbols
        returns_1d = {}
        for sym, df_p in prices_dict.items():
            if df_p is not None and not df_p.empty and len(df_p) >= 2:
                c = df_p['Close'] if 'Close' in df_p.columns else df_p.iloc[:, 0]
                c_clean = c.dropna().values
                if len(c_clean) >= 2:
                    prev_c = float(c_clean[-2])
                    curr_c = float(c_clean[-1])
                    if prev_c > 1e-6 and np.isfinite(prev_c) and np.isfinite(curr_c):
                        returns_1d[sym] = float(np.clip((curr_c - prev_c) / prev_c, -1.0, 10.0))

        for row in universe_df.itertuples(index=False):
            r_dict = row._asdict() if hasattr(row, '_asdict') else dict(zip(universe_df.columns, row))
            sym = str(r_dict.get('symbol', ''))
            name = str(r_dict.get('name', ''))
            mkt = str(r_dict.get('market', ''))

            suppliers = supply_chain_graph.get(sym, []) if supply_chain_graph else []
            follower_ret = returns_1d.get(sym, 0.0)

            gat_signal = 0.0
            if suppliers:
                attn_weights = []
                for leader_sym in suppliers:
                    leader_ret = returns_1d.get(leader_sym, 0.0)
                    alpha = self._compute_gat_attention(leader_ret, follower_ret)
                    attn_weights.append(alpha * leader_ret)
                gat_signal = float(np.mean(attn_weights))

            # Normalized score [0, 100]
            gnn_score = (gat_signal + 0.05) / 0.10 * 100.0
            gnn_score = float(np.clip(gnn_score, 0.0, 100.0))

            results.append({
                "symbol": sym,
                "name": name,
                "market": mkt,
                "gnn_lead_lag_score": round(gnn_score, 2),
                "propagated_momentum": round(gat_signal, 4)
            })

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values(by="gnn_lead_lag_score", ascending=False).reset_index(drop=True)
        return res_df
