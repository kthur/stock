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
        # LeakyReLU attention mechanism
        a_input = (leader_ret - follower_ret) * edge_weight
        attn = np.maximum(a_input, a_input * self.alpha_leakage)
        alpha = float(1.0 / (1.0 + np.exp(-attn)))
        return alpha

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
                    returns_1d[sym] = (c_clean[-1] - c_clean[-2]) / c_clean[-2]

        for _, row in universe_df.iterrows():
            sym = str(row['symbol'])
            name = str(row.get('name', ''))
            mkt = str(row.get('market', ''))

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
