"""
graph_granger_causality.py — High-Dimensional Graph Granger Causality Spillover Network.

Phase 110 / Feature F520 / Release R126 (v117 Production Master)

Estimates high-dimensional vector autoregressive (VAR) Granger causality graphs
across global macro indicators (SOX, FX, WTI, TNX, VIX, Gold, DXY, SP500) and
sector ETF return vectors using Elastic-Net penalized regression.

Provides:
1. Directed econometric causality network topology (asymmetric C matrix, zero self-loops).
2. Dynamic topology metrics (in/out-degree centrality, net spillover, directed PageRank d=0.85).
3. Companion matrix propagation velocities across 1D, 3D, and 5D horizons.
4. Forward-looking shock impulse vectors and systemic transmission matrices.
5. Dynamic sector-macro sensitivity matrix for CrossAssetSpilloverEngine.
6. Timezone causality: 1-day lag shift on US macro series for KRX context.
7. Complete backward compatibility alias trees.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

try:
    from sklearn.linear_model import ElasticNet, Ridge
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

logger = logging.getLogger(__name__)

# =========================================================================
# Canonical Node Sets & Aliases
# =========================================================================

DEFAULT_MACRO_NODES: List[str] = [
    "SOX", "USDKRW", "WTI", "TNX", "VIX", "GOLD", "DXY", "SP500"
]

DEFAULT_SECTOR_NODES: List[str] = [
    "XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLC", "XLRE", "XLU", "XLB"
]

US_MACRO_ALIASES: Dict[str, List[str]] = {
    "SOX": ["SOX", "^SOX", "SOXX", "sox", "sox_change", "sox_pct"],
    "SP500": ["SP500", "^GSPC", "SPY", "sp500", "sp500_change", "sp500_pct", "spx"],
    "VIX": ["VIX", "^VIX", "vix", "vix_change", "vix_pct", "vix_raw"],
    "TNX": ["TNX", "^TNX", "tnx", "tnx_change", "tnx_pct", "us10y", "yield_10y"],
    "WTI": ["WTI", "CL=F", "wti", "wti_change", "wti_pct", "crude_oil", "oil"],
    "GOLD": ["GOLD", "GC=F", "GLD", "gold", "gold_change", "gold_pct"],
    "DXY": ["DXY", "DX-Y.NYB", "UUP", "dxy", "dxy_change", "dxy_pct", "dollar_index"],
    "USDKRW": ["USDKRW", "USDKRW=X", "usdkrw", "usdkrw_change", "usdkrw_pct", "usd_krw"],
}

US_MACRO_INDICATORS_SET: set[str] = {
    "SOX", "^SOX", "SOXX", "sox",
    "SP500", "^GSPC", "SPY", "sp500", "spx",
    "VIX", "^VIX", "vix",
    "TNX", "^TNX", "tnx", "us10y", "yield_10y",
    "WTI", "CL=F", "wti", "crude_oil", "oil",
    "GOLD", "GC=F", "GLD", "gold",
    "DXY", "DX-Y.NYB", "UUP", "dxy", "dollar_index",
}

SECTOR_NAME_TO_ETF: Dict[str, str] = {
    "Information Technology": "XLK",
    "Tech": "XLK",
    "IT": "XLK",
    "Semiconductor": "XLK",
    "반도체": "XLK",
    "전기전자": "XLK",
    "IT하드웨어": "XLK",
    "IT소프트웨어": "XLK",
    "Financials": "XLF",
    "Finance": "XLF",
    "금융업": "XLF",
    "은행": "XLF",
    "증권": "XLF",
    "보험": "XLF",
    "Health Care": "XLV",
    "Healthcare": "XLV",
    "Biotechnology": "XLV",
    "의약품": "XLV",
    "바이오": "XLV",
    "Energy": "XLE",
    "Oil & Gas": "XLE",
    "정유": "XLE",
    "에너지": "XLE",
    "Industrials": "XLI",
    "기계": "XLI",
    "운수장비": "XLI",
    "Automotive": "XLI",
    "Defense": "XLI",
    "방산": "XLI",
    "Shipbuilding": "XLI",
    "조선": "XLI",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "유통업": "XLP",
    "음식료품": "XLP",
    "Communication": "XLC",
    "통신업": "XLC",
    "서비스업": "XLC",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "전기가스업": "XLU",
    "Materials": "XLB",
    "Chemical": "XLB",
    "화학": "XLB",
    "철강및금속": "XLB",
    "Steel": "XLB",
}


# =========================================================================
# Data Classes
# =========================================================================

@dataclass
class GrangerNetworkNode:
    symbol: str
    node_type: str  # "MACRO" or "SECTOR"
    display_name: str
    description: str = ""


@dataclass
class NetworkTopologyMetrics:
    in_degree_centrality: Dict[str, float]
    out_degree_centrality: Dict[str, float]
    net_spillover_centrality: Dict[str, float]
    directed_pagerank: Dict[str, float]
    propagation_velocities: Dict[int, Dict[Tuple[str, str], float]]  # horizon -> (src, dst) -> velocity
    systemic_transmission_matrix: Dict[int, np.ndarray]             # horizon -> K x K transmission matrix
    nodes: List[str]
    normalized_in_degree: Dict[str, float] = field(default_factory=dict)
    normalized_out_degree: Dict[str, float] = field(default_factory=dict)


@dataclass
class SystemicImpulseResponse:
    horizon: int
    shock_vector: Dict[str, float]
    projected_impulse: Dict[str, float]
    transmission_matrix: np.ndarray
    propagation_velocity: Dict[str, float]
    timestamp: Optional[str] = None


@dataclass
class GrangerFitSummary:
    nodes: List[str]
    lag_order: int
    alpha_penalty: float
    l1_ratio: float
    causal_adjacency_matrix: np.ndarray
    r_squared: Dict[str, float]
    topology: NetworkTopologyMetrics
    fit_duration_ms: float


# =========================================================================
# Math Helpers: Regularized Regression & PageRank
# =========================================================================

def _regularized_solve(
    X: np.ndarray,
    y: np.ndarray,
    alpha: float = 0.01,
    l1_ratio: float = 0.70,
    fit_intercept: bool = True,
) -> Tuple[np.ndarray, float]:
    """
    Fits Elastic-Net regression with analytical Ridge / Coordinate Descent fallback.
    Returns (coefficients_vector, intercept).
    """
    n_samples, n_features = X.shape

    if _HAS_SKLEARN:
        try:
            enet = ElasticNet(
                alpha=max(1e-4, float(alpha)),
                l1_ratio=float(l1_ratio),
                fit_intercept=fit_intercept,
                max_iter=3000,
                tol=1e-4,
                random_state=42,
            )
            enet.fit(X, y)
            coef = enet.coef_.astype(float)
            intercept = float(enet.intercept_) if fit_intercept else 0.0

            # If Elastic-Net over-penalized to exact zero while y has variance, fall back to soft Ridge
            if np.all(np.abs(coef) < 1e-12) and np.std(y) > 1e-6:
                ridge = Ridge(alpha=max(1e-3, float(alpha) * 0.1), fit_intercept=fit_intercept)
                ridge.fit(X, y)
                coef = ridge.coef_.astype(float)
                intercept = float(ridge.intercept_) if fit_intercept else 0.0

            return coef, intercept
        except Exception as e:
            logger.debug(f"[GraphGranger] Sklearn ElasticNet exception: {e}, using NumPy solver.")

    # NumPy Regularized Least Squares Fallback
    if fit_intercept:
        mean_X = np.mean(X, axis=0)
        mean_y = np.mean(y)
        X_c = X - mean_X
        y_c = y - mean_y
    else:
        X_c = X
        y_c = y
        mean_X = np.zeros(n_features)
        mean_y = 0.0

    # L2 Tikhonov Regularization (Ridge)
    XtX = X_c.T @ X_c
    reg_eye = np.eye(n_features) * (alpha * n_samples + 1e-6)
    try:
        coef = np.linalg.solve(XtX + reg_eye, X_c.T @ y_c)
    except np.linalg.LinAlgError:
        coef = np.linalg.pinv(XtX + reg_eye) @ (X_c.T @ y_c)

    intercept = float(mean_y - np.dot(mean_X, coef)) if fit_intercept else 0.0
    return coef, intercept


def compute_directed_pagerank(
    adj_matrix: np.ndarray,
    damping: float = 0.85,
    max_iter: int = 300,
    tol: float = 1e-10,
) -> np.ndarray:
    """
    Computes directed PageRank over adjacency matrix C where C[j, i] is weight of edge j -> i.
    Guarantees strictly positive components and exact sum = 1.000000.
    """
    K = adj_matrix.shape[0]
    if K == 0:
        return np.array([])
    if K == 1:
        return np.array([1.0])

    # Out-degree of each node j: sum of edges leaving j (i.e. sum over i of C[j, i])
    out_degree = np.sum(adj_matrix, axis=1)

    # Column-stochastic transition matrix M: M[i, j] is prob of transitioning j -> i
    M = np.zeros((K, K), dtype=float)
    for j in range(K):
        if out_degree[j] > 1e-12:
            M[:, j] = adj_matrix[j, :] / out_degree[j]
        else:
            # Dangling node distributes uniformly across all nodes
            M[:, j] = 1.0 / K

    # Power Iteration: p = d * M * p + (1 - d) / K * 1
    p = np.full(K, 1.0 / K, dtype=float)
    teleport = (1.0 - damping) / K

    for _ in range(max_iter):
        p_next = damping * (M @ p) + teleport
        diff = np.sum(np.abs(p_next - p))
        p = p_next
        if diff < tol:
            break

    total = np.sum(p)
    if total > 0:
        p = p / total
    else:
        p = np.full(K, 1.0 / K)

    return p


# =========================================================================
# Primary Engine: GraphGrangerCausalityNetwork
# =========================================================================

class GraphGrangerCausalityNetwork:
    """
    High-Dimensional VAR Granger Causality & Systemic Shock Propagation Network Engine.

    Estimates directed graph topology across macro drivers and sector ETF return vectors
    using Elastic-Net penalized regression.
    """

    VERSION: int = 117

    def __init__(
        self,
        config: Optional[Any] = None,
        lag_order: int = 2,
        alpha_penalty: float = 0.01,
        l1_ratio: float = 0.70,
        horizons: Sequence[int] = (1, 3, 5),
        pagerank_damping: float = 0.85,
        f_test_pvalue_threshold: float = 0.10,
        min_history_bars: int = 30,
        version: int = 117,
        gamma_decay: float = 0.70,
    ) -> None:
        self.config = config
        self.version = version
        self.lag_order = max(1, int(lag_order))
        self.alpha_penalty = float(alpha_penalty)
        self.l1_ratio = float(l1_ratio)
        self.horizons = tuple(sorted(horizons))
        self.pagerank_damping = float(pagerank_damping)
        self.f_test_pvalue_threshold = float(f_test_pvalue_threshold)
        self.min_history_bars = max(5, int(min_history_bars))
        self.gamma_decay = float(gamma_decay)

        # Internal state populated upon fit()
        self.nodes: List[str] = []
        self.node_type_map: Dict[str, str] = {}
        self.lag_coef_matrices: List[np.ndarray] = []  # A_1, ..., A_p each (K x K)
        self.intercepts: np.ndarray = np.array([])
        self.causal_adjacency_matrix: np.ndarray = np.array([[]])
        self.companion_matrix: np.ndarray = np.array([[]])
        self.systemic_transmission_matrix: Dict[int, np.ndarray] = {}
        self.propagation_velocities: Dict[int, Dict[Tuple[str, str], float]] = {}
        self.topology_metrics: Optional[NetworkTopologyMetrics] = None
        self.last_summary: Optional[GrangerFitSummary] = None
        self.is_fitted: bool = False

    def reset(self) -> None:
        """Clears all fitted state."""
        self.nodes = []
        self.node_type_map = {}
        self.lag_coef_matrices = []
        self.intercepts = np.array([])
        self.causal_adjacency_matrix = np.array([[]])
        self.companion_matrix = np.array([[]])
        self.systemic_transmission_matrix = {}
        self.propagation_velocities = {}
        self.topology_metrics = None
        self.last_summary = None
        self.is_fitted = False

    def _standardize_columns(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Maps raw input column names to canonical node symbols.
        Returns cleaned DataFrame with standardized uppercase symbols and mapping dict.
        """
        col_map: Dict[str, str] = {}
        alias_reverse: Dict[str, str] = {}
        for canonical, aliases in US_MACRO_ALIASES.items():
            for a in aliases:
                alias_reverse[a.lower()] = canonical

        new_cols: List[str] = []
        for col in df.columns:
            c_str = str(col).strip()
            c_lower = c_str.lower()
            if c_lower in alias_reverse:
                canonical = alias_reverse[c_lower]
                col_map[c_str] = canonical
                new_cols.append(canonical)
            else:
                canonical = c_str.upper()
                col_map[c_str] = canonical
                new_cols.append(canonical)

        df_std = df.copy()
        df_std.columns = new_cols
        # Deduplicate columns if any aliases collapsed to same canonical symbol
        df_std = df_std.loc[:, ~df_std.columns.duplicated(keep="last")]
        return df_std, col_map

    def fit(self, returns_df: pd.DataFrame, is_krx: bool = False) -> GrangerFitSummary:
        """
        Fits regularized VAR(p) model on multivariate return matrix and computes graph topology.

        Enforces 1-business-day lag shift on US macro series for KRX context to eliminate lookahead bias.
        """
        start_time = time.perf_counter()

        if returns_df is None or returns_df.empty:
            raise ValueError("Cannot fit GraphGrangerCausalityNetwork on empty returns_df.")

        # Standardize column labels
        df_clean, _ = self._standardize_columns(returns_df)

        # Timezone Causality: Shift US-origin macro indicators by 1 day when modeling KRX assets
        if is_krx:
            for col in df_clean.columns:
                if col in US_MACRO_INDICATORS_SET or col in DEFAULT_MACRO_NODES:
                    df_clean[col] = df_clean[col].shift(1)

        # Drop initial NaNs generated by shift or missing bars
        df_clean = df_clean.dropna()

        nodes = list(df_clean.columns)
        K = len(nodes)
        N = len(df_clean)

        if K < 1:
            raise ValueError("No valid columns remaining to fit Granger causality network.")

        self.nodes = nodes
        self.node_type_map = {
            node: ("MACRO" if node in DEFAULT_MACRO_NODES or node in US_MACRO_INDICATORS_SET else "SECTOR")
            for node in nodes
        }

        p = self.lag_order
        if N <= p + 2:
            # Fallback to mild identity / small noise network if history is extremely truncated
            logger.warning(
                f"[GraphGranger] History bars ({N}) insufficient for lag {p}. Using identity fallback."
            )
            A_matrices = [np.eye(K) * 0.10 for _ in range(p)]
            intercepts = np.zeros(K)
            r_squared = {node: 0.0 for node in nodes}
        else:
            # Construct VAR(p) lagged feature matrix X and target matrix Y
            # For row t in range(p, N):
            # Y[t - p] = returns[t]
            # X[t - p] = [returns[t-1], returns[t-2], ..., returns[t-p]]
            Y_mat = df_clean.iloc[p:].to_numpy(dtype=float)
            T_eff = len(Y_mat)

            X_blocks = []
            for lag in range(1, p + 1):
                block = df_clean.iloc[p - lag : N - lag].to_numpy(dtype=float)
                X_blocks.append(block)
            X_mat = np.hstack(X_blocks)  # shape (T_eff, K * p)

            # Fit Elastic-Net equation-by-equation: Y[:, i] = c_i + X_mat @ beta_i + eps_i
            A_matrices = [np.zeros((K, K), dtype=float) for _ in range(p)]
            intercepts = np.zeros(K, dtype=float)
            r_squared = {}

            for i in range(K):
                y_i = Y_mat[:, i]
                coef_i, int_i = _regularized_solve(
                    X_mat,
                    y_i,
                    alpha=self.alpha_penalty,
                    l1_ratio=self.l1_ratio,
                    fit_intercept=True,
                )
                intercepts[i] = int_i

                # Partition coefficients across lags l=1..p
                for lag_idx in range(p):
                    start_idx = lag_idx * K
                    end_idx = (lag_idx + 1) * K
                    # A_l[i, j] represents impact of node j at lag (lag_idx + 1) on target node i
                    A_matrices[lag_idx][i, :] = coef_i[start_idx:end_idx]

                # R-squared calculation
                y_pred = X_mat @ coef_i + int_i
                ss_tot = np.sum((y_i - np.mean(y_i)) ** 2)
                ss_res = np.sum((y_i - y_pred) ** 2)
                r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 1e-12 else 0.0
                r_squared[nodes[i]] = max(0.0, min(1.0, r2))

        self.lag_coef_matrices = A_matrices
        self.intercepts = intercepts

        # Compute Directed Adjacency Matrix C (K x K):
        # C[j, i] = directed causal impact of j -> i across all lags
        # C[j, i] >= 0; C[i, i] = 0.0 (strictly zero self-loops)
        C = np.zeros((K, K), dtype=float)
        for j in range(K):
            for i in range(K):
                if i != j:
                    # Accumulate magnitude across all lag matrices
                    lag_sum = sum(abs(A_matrices[l][i, j]) for l in range(p))
                    C[j, i] = lag_sum

        self.causal_adjacency_matrix = C

        # Build Companion Matrix Phi of size (K*p x K*p)
        Kp = K * p
        Phi = np.zeros((Kp, Kp), dtype=float)
        # Top block: [A_1, A_2, ..., A_p]
        for l in range(p):
            Phi[0:K, l * K : (l + 1) * K] = A_matrices[l]
        # Lower block: Identity submatrix [I_{(p-1)*K}, 0]
        if p > 1:
            Phi[K:Kp, 0 : (p - 1) * K] = np.eye((p - 1) * K)
        self.companion_matrix = Phi

        # Calculate impulse response matrices Psi_h = [Phi^h]_{0:K, 0:K}
        # and systemic transmission matrices T^(H) = sum_{h=1}^H gamma^{h-1} Psi_h
        max_horizon = max(self.horizons) if self.horizons else 5
        psi_powers: Dict[int, np.ndarray] = {}
        current_phi_power = np.eye(Kp, dtype=float)

        for h in range(1, max_horizon + 1):
            current_phi_power = current_phi_power @ Phi
            # Top-left K x K block represents the h-step impulse response
            psi_powers[h] = current_phi_power[0:K, 0:K]

        self.systemic_transmission_matrix = {}
        self.propagation_velocities = {}

        for H in self.horizons:
            # T^(H) = sum_{h=1}^H gamma^{h-1} * Psi_h
            T_H = np.zeros((K, K), dtype=float)
            velocity_sum = np.zeros((K, K), dtype=float)
            for h in range(1, H + 1):
                decay = self.gamma_decay ** (h - 1)
                psi_h = psi_powers.get(h, np.zeros((K, K)))
                T_H += decay * psi_h
                velocity_sum += np.abs(psi_h)

            self.systemic_transmission_matrix[H] = T_H

            # Average propagation velocity: (1/H) * sum_{h=1}^H |Psi_h|
            vel_dict: Dict[Tuple[str, str], float] = {}
            for j in range(K):
                for i in range(K):
                    vel_dict[(nodes[j], nodes[i])] = float(velocity_sum[i, j] / H)
            self.propagation_velocities[H] = vel_dict

        # Derive Network Topology Metrics
        self.topology_metrics = self.compute_topology_metrics()

        fit_duration = (time.perf_counter() - start_time) * 1000.0
        self.is_fitted = True

        self.last_summary = GrangerFitSummary(
            nodes=nodes,
            lag_order=p,
            alpha_penalty=self.alpha_penalty,
            l1_ratio=self.l1_ratio,
            causal_adjacency_matrix=C,
            r_squared=r_squared,
            topology=self.topology_metrics,
            fit_duration_ms=fit_duration,
        )
        return self.last_summary

    def compute_topology_metrics(self) -> NetworkTopologyMetrics:
        """
        Derives in/out-degree centrality, net spillover, directed PageRank,
        and propagation velocities from the fitted companion matrix.
        """
        C = self.causal_adjacency_matrix
        K = len(self.nodes)
        nodes = self.nodes

        if K == 0 or C.size == 0:
            return NetworkTopologyMetrics(
                in_degree_centrality={},
                out_degree_centrality={},
                net_spillover_centrality={},
                directed_pagerank={},
                propagation_velocities={},
                systemic_transmission_matrix={},
                nodes=[],
            )

        # In-degree centrality: sum of incoming edges to i: S_i^in = sum_{j != i} C[j, i]
        in_degree = np.sum(C, axis=0)  # column sum
        # Out-degree centrality: sum of outgoing edges from j: S_j^out = sum_{i != j} C[j, i]
        out_degree = np.sum(C, axis=1)  # row sum
        # Net spillover centrality: S_k^net = S_k^out - S_k^in
        net_spillover = out_degree - in_degree

        # Simplex Normalized In/Out-degrees (sum = 1.0 if sum > 0)
        tot_in = np.sum(in_degree)
        norm_in = in_degree / tot_in if tot_in > 1e-12 else np.full(K, 1.0 / K)

        tot_out = np.sum(out_degree)
        norm_out = out_degree / tot_out if tot_out > 1e-12 else np.full(K, 1.0 / K)

        # Directed PageRank (damping = 0.85, exact sum = 1.000000)
        pagerank = compute_directed_pagerank(C, damping=self.pagerank_damping)

        in_dict = {nodes[i]: float(in_degree[i]) for i in range(K)}
        out_dict = {nodes[i]: float(out_degree[i]) for i in range(K)}
        net_dict = {nodes[i]: float(net_spillover[i]) for i in range(K)}
        pr_dict = {nodes[i]: float(pagerank[i]) for i in range(K)}
        norm_in_dict = {nodes[i]: float(norm_in[i]) for i in range(K)}
        norm_out_dict = {nodes[i]: float(norm_out[i]) for i in range(K)}

        return NetworkTopologyMetrics(
            in_degree_centrality=in_dict,
            out_degree_centrality=out_dict,
            net_spillover_centrality=net_dict,
            directed_pagerank=pr_dict,
            propagation_velocities=self.propagation_velocities,
            systemic_transmission_matrix=self.systemic_transmission_matrix,
            nodes=nodes,
            normalized_in_degree=norm_in_dict,
            normalized_out_degree=norm_out_dict,
        )

    def compute_shock_impulse(
        self,
        current_shocks: Dict[str, float],
        horizon: int = 3,
        target_nodes: Optional[List[str]] = None,
    ) -> SystemicImpulseResponse:
        """
        Computes forward-looking shock impulse vector:
        I_t^(H) = T^(H) * e_t
        """
        if not self.is_fitted or not self.nodes:
            raise RuntimeError("GraphGrangerCausalityNetwork must be fitted before computing shock impulses.")

        K = len(self.nodes)
        nodes = self.nodes

        # Select closest horizon
        h_selected = horizon if horizon in self.systemic_transmission_matrix else min(
            self.systemic_transmission_matrix.keys(), key=lambda h: abs(h - horizon)
        )
        T_H = self.systemic_transmission_matrix[h_selected]

        # Vectorize current shocks e_t
        # Case-insensitive / alias resolution
        e_vec = np.zeros(K, dtype=float)
        clean_shocks = {k.upper(): v for k, v in current_shocks.items()}

        for i, node in enumerate(nodes):
            val = clean_shocks.get(node)
            if val is None:
                # Check aliases
                for canonical, aliases in US_MACRO_ALIASES.items():
                    if canonical == node:
                        for alias in aliases:
                            if alias.upper() in clean_shocks:
                                val = clean_shocks[alias.upper()]
                                break
                    if val is not None:
                        break
            if val is not None:
                try:
                    f_val = float(val)
                    if np.isfinite(f_val):
                        e_vec[i] = f_val
                except (ValueError, TypeError):
                    pass

        # Projected impulse on target nodes:
        # T_H[i, j] is transmission from j to i, so I_i = sum_j T_H[i, j] * e_j
        projected = T_H @ e_vec

        proj_dict = {nodes[i]: float(projected[i]) for i in range(K)}
        if target_nodes:
            proj_dict = {k: v for k, v in proj_dict.items() if k in target_nodes}

        # Average propagation velocity per target node
        vel_map = self.propagation_velocities.get(h_selected, {})
        node_velocities: Dict[str, float] = {}
        for node in nodes:
            v_list = [v for (src, dst), v in vel_map.items() if dst == node]
            node_velocities[node] = float(np.mean(v_list)) if v_list else 0.0

        return SystemicImpulseResponse(
            horizon=h_selected,
            shock_vector={nodes[i]: float(e_vec[i]) for i in range(K)},
            projected_impulse=proj_dict,
            transmission_matrix=T_H,
            propagation_velocity=node_velocities,
            timestamp=pd.Timestamp.now().isoformat(),
        )

    def get_sector_macro_sensitivity_matrix(self, horizon: int = 3) -> pd.DataFrame:
        """
        Extracts dynamic sector-to-macro sensitivity matrix to replace static beta heuristics in
        CrossAssetSpilloverEngine.

        Rows: Sectors (both ETF tickers and standard industry names)
        Columns: Macro Indicators (both uppercase and lowercase factor names)
        """
        if not self.is_fitted or not self.nodes:
            # Fallback mock template if uninitialized
            cols = ["sox", "usdkrw", "tnx", "wti", "vix", "sp500", "gold", "dxy"]
            return pd.DataFrame(0.0, index=["Market"], columns=cols)

        h_selected = horizon if horizon in self.systemic_transmission_matrix else min(
            self.systemic_transmission_matrix.keys(), key=lambda h: abs(h - horizon)
        )
        T_H = self.systemic_transmission_matrix[h_selected]
        nodes = self.nodes

        macro_cols = [n for n in nodes if n in DEFAULT_MACRO_NODES or n in US_MACRO_INDICATORS_SET]
        if not macro_cols:
            macro_cols = nodes[:min(8, len(nodes))]

        sector_rows = [n for n in nodes if n not in macro_cols]
        if not sector_rows:
            sector_rows = nodes

        # Base submatrix: rows = sector_rows, cols = macro_cols
        row_indices = [nodes.index(r) for r in sector_rows]
        col_indices = [nodes.index(c) for c in macro_cols]
        sub_matrix = T_H[np.ix_(row_indices, col_indices)]

        # Lowercase column names to seamlessly match cross_asset_spillover.py keys
        clean_cols = [c.lower() for c in macro_cols]
        base_df = pd.DataFrame(sub_matrix, index=sector_rows, columns=clean_cols)

        # Expand DataFrame with human-readable sector aliases so that queries like
        # dyn_sens.loc["Semiconductor", "sox"] resolve directly
        expanded_rows = []
        expanded_indices = []

        for alias_name, etf_ticker in SECTOR_NAME_TO_ETF.items():
            if etf_ticker in base_df.index:
                expanded_rows.append(base_df.loc[etf_ticker].values)
                expanded_indices.append(alias_name)

        if expanded_indices:
            alias_df = pd.DataFrame(expanded_rows, index=expanded_indices, columns=clean_cols)
            # Combine without duplicate indices
            full_df = pd.concat([base_df, alias_df])
            full_df = full_df[~full_df.index.duplicated(keep="first")]
        else:
            full_df = base_df

        # Add generic "Market" fallback row (average of sector rows)
        if "Market" not in full_df.index:
            mean_row = pd.DataFrame([full_df.mean(axis=0)], index=["Market"], columns=clean_cols)
            full_df = pd.concat([full_df, mean_row])

        return full_df

    def evaluate_spillover_momentum_score(
        self,
        current_shocks: Dict[str, float],
        stock_returns: Dict[str, float],
        sector_mapping: Dict[str, str],
        horizon: int = 3,
        gamma_decay: float = 0.70,
    ) -> Dict[str, float]:
        """
        Computes dynamic cross-asset spillover momentum scores bounded in [0.05, 0.95].
        """
        dyn_sens = self.get_sector_macro_sensitivity_matrix(horizon=horizon)
        scores: Dict[str, float] = {}

        # Pre-clean shocks with lowercase keys
        clean_shocks: Dict[str, float] = {}
        for k, v in current_shocks.items():
            clean_shocks[k.lower()] = float(v) if np.isfinite(v) else 0.0

        for sym, ret_val in stock_returns.items():
            sec = sector_mapping.get(sym, "Market")
            if sec in dyn_sens.index:
                beta_row = dyn_sens.loc[sec]
            elif str(sec).strip() in dyn_sens.index:
                beta_row = dyn_sens.loc[str(sec).strip()]
            else:
                beta_row = dyn_sens.loc["Market"] if "Market" in dyn_sens.index else dyn_sens.iloc[0]

            # Macro impulse = sum(beta_factor * shock_factor)
            macro_impulse = sum(
                float(beta_row.get(factor, 0.0)) * clean_shocks.get(factor, 0.0)
                for factor in dyn_sens.columns
            )

            # Unpriced spillover diffusion gap
            delta_spillover = macro_impulse - (gamma_decay * float(ret_val))

            # Coherence adjustment
            if macro_impulse > 0 and ret_val >= 0:
                coherence_mult = 1.0 + 0.50 * min(1.0, ret_val / 0.04)
                delta_spillover *= coherence_mult
            elif macro_impulse > 0 and ret_val < -0.03:
                delta_spillover *= 0.65

            # Logistic bounding
            clipped_exp = np.clip(-16.0 * delta_spillover, -50.0, 50.0)
            raw_score = 1.0 / (1.0 + np.exp(clipped_exp))
            scores[sym] = round(float(np.clip(raw_score, 0.05, 0.95)), 4)

        return scores


# =========================================================================
# Class-Level and Module-Level Backward-Compatibility Alias Trees
# =========================================================================

HighDimensionalGrangerNetwork = GraphGrangerCausalityNetwork
Phase110GrangerSpilloverEngine = GraphGrangerCausalityNetwork
GraphGrangerSpilloverNetwork = GraphGrangerCausalityNetwork
GrangerCausalityNetwork = GraphGrangerCausalityNetwork
DirectedMacroSpilloverNetwork = GraphGrangerCausalityNetwork

# Expose aliases directly on the class
GraphGrangerCausalityNetwork.HighDimensionalGrangerNetwork = HighDimensionalGrangerNetwork
GraphGrangerCausalityNetwork.Phase110GrangerSpilloverEngine = Phase110GrangerSpilloverEngine
GraphGrangerCausalityNetwork.GraphGrangerSpilloverNetwork = GraphGrangerSpilloverNetwork
GraphGrangerCausalityNetwork.GrangerCausalityNetwork = GrangerCausalityNetwork
GraphGrangerCausalityNetwork.DirectedMacroSpilloverNetwork = DirectedMacroSpilloverNetwork

__all__ = [
    "GrangerNetworkNode",
    "NetworkTopologyMetrics",
    "SystemicImpulseResponse",
    "GrangerFitSummary",
    "GraphGrangerCausalityNetwork",
    "HighDimensionalGrangerNetwork",
    "Phase110GrangerSpilloverEngine",
    "GraphGrangerSpilloverNetwork",
    "GrangerCausalityNetwork",
    "DirectedMacroSpilloverNetwork",
    "DEFAULT_MACRO_NODES",
    "DEFAULT_SECTOR_NODES",
    "US_MACRO_ALIASES",
    "SECTOR_NAME_TO_ETF",
    "compute_directed_pagerank",
]
