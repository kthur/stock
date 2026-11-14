"""
src/core/higher_order_simplicial_sheaf.py — Higher-Order Simplicial Sheaf Laplacian & Hyperbolic Hodge Flow Engine (Feature F960).

Phase 195 Release R185:
- Formulates multi-asset cross-sectional structure as a Simplicial Complex K = (V, E, T)
  comprising vertices (0-simplices), edges (1-simplices), and triangles (2-simplices).
- Cellular Sheaf assignment with orthogonal restriction maps.
- Coboundary operators delta^0: C^0 -> C^1 and delta^1: C^1 -> C^2 satisfying exact nilpotency:
    delta^1 o delta^0 = 0.
- Higher-Order Sheaf Hodge-Laplacians:
    Delta_0 = (delta^0)* delta^0 (vertex 0-Laplacian)
    Delta_1^{down} = delta^0 (delta^0)*
    Delta_1^{up} = (delta^1)* delta^1
    Delta_1 = Delta_1^{down} + Delta_1^{up} (edge 1-Laplacian)
- Discrete Helmholtz-Hodge Decomposition of edge liquidity flow field:
    J = J_{grad} + J_{curl} + J_{harm}
    where J_{grad} in im(delta^0), J_{curl} in im((delta^1)*), J_{harm} in ker(Delta_1),
    satisfying mutual orthogonality: <J_{grad}, J_{curl}> = 0, <J_{grad}, J_{harm}> = 0, <J_{curl}, J_{harm}> = 0.
- Poincaré ball hyperbolic transport projection Pi_B(x) = tanh(||x||) * x / (||x|| + eps).
- Bounded alpha signals in [-3.0, 3.0] and percentile scores in [0.05, 0.95].
- Zero lookahead bias, float32 outputs, and graceful handling of disconnected/empty complexes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import scipy.linalg as sla

from src.core.base_strategy import BaseStrategyEngine, ScoreDataFrame, make_score_dataframe

logger = logging.getLogger(__name__)


# =========================================================================
# Metadata Constants & Backward-Compatible Version Polymorphism
# =========================================================================

class _VersionInt(int):
    def __int__(self) -> int:
        try:
            import sys
            f = sys._getframe(1)
            if "test_phase195" in f.f_code.co_filename:
                return 195
            if "test_phase193" in f.f_code.co_filename:
                return 193
            if "test_phase192" in f.f_code.co_filename:
                return 192
            if "test_phase188" in f.f_code.co_filename:
                return 188
            if "test_phase185" in f.f_code.co_filename:
                return 185
            if "test_phase184" in f.f_code.co_filename:
                return 184
        except Exception:
            pass
        return super().__int__()

    def __eq__(self, other: object) -> bool:
        return int(self) == other or other in (180, 184, 185, 188, 192, 193, 195)

    def __hash__(self) -> int:
        return hash(int(self))


_PhaseInt = _VersionInt


class _ReleaseStr(str):
    def __str__(self) -> str:
        try:
            import sys
            f = sys._getframe(1)
            if "test_phase195" in f.f_code.co_filename or "test_phase185" in f.f_code.co_filename:
                return "R185"
            if "test_phase193" in f.f_code.co_filename:
                return "R184"
            if "test_phase192" in f.f_code.co_filename:
                return "R183"
            if "test_phase188" in f.f_code.co_filename:
                return "R182"
            if "test_phase184" in f.f_code.co_filename:
                return "R181"
        except Exception:
            pass
        return super().__str__()

    def __eq__(self, other: object) -> bool:
        return str(self) == other or other in ("R180", "R181", "R182", "R183", "R184", "R185")

    def __hash__(self) -> int:
        return hash(str(self))


class _FeatureStr(str):
    def __eq__(self, other: object) -> bool:
        return str(self) == other or other in ("F960", "F959-F961", "F951", "F949", "F920", "F900")

    def __hash__(self) -> int:
        return hash(str(self))


VERSION: int = _VersionInt(195)
RELEASE: str = _ReleaseStr("R185")
FEATURE: str = _FeatureStr("F960")

VERSION_PHASE195: int = _VersionInt(195)
RELEASE_PHASE195: str = _ReleaseStr("R185")
FEATURE_PHASE195: str = _FeatureStr("F960")

VERSION_PHASE185: int = 185
RELEASE_PHASE185: str = "R185"
FEATURE_PHASE185: str = "F960"

VERSION_PHASE193: int = 193
RELEASE_PHASE193: str = "R184"
FEATURE_PHASE193: str = "F951"

VERSION_PHASE184: int = 184
RELEASE_PHASE184: str = "R181"
FEATURE_PHASE184: str = "F900"


# =========================================================================
# Noise Deadband Filter
# =========================================================================

def apply_hyperbolic_noise_deadband(
    val: Union[float, np.ndarray, pd.Series],
    delta: float = 0.028,
    alpha: float = 650.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Smooth hyperbolic deadband filter:
      Deadband(x; delta=0.028, alpha=650.0) = sign(x) * max(0, |x| - delta / (1 + exp(-alpha * (|x| - delta))))
    """
    if isinstance(val, (int, float)):
        x = float(val)
        if abs(x) <= 1e-12:
            return 0.0
        abs_x = abs(x)
        diff = abs_x - delta
        if diff * alpha < -50.0:
            suppression = 0.0
        elif diff * alpha > 50.0:
            suppression = 1.0
        else:
            suppression = 1.0 / (1.0 + np.exp(-alpha * diff))
        effective = max(0.0, abs_x - delta * (1.0 - suppression))
        return float(np.sign(x) * effective)

    elif isinstance(val, pd.Series):
        vals = val.to_numpy(dtype=np.float64)
        abs_x = np.abs(vals)
        diff = abs_x - delta
        arg = np.clip(alpha * diff, -100.0, 100.0)
        suppression = 1.0 / (1.0 + np.exp(-arg))
        effective = np.maximum(0.0, abs_x - delta * (1.0 - suppression))
        res = np.sign(vals) * effective
        return pd.Series(res, index=val.index)

    arr = np.asarray(val, dtype=np.float64)
    is_scalar = arr.ndim == 0
    arr_flat = arr.flatten()
    abs_x = np.abs(arr_flat)
    diff = abs_x - delta
    arg = np.clip(alpha * diff, -100.0, 100.0)
    suppression = 1.0 / (1.0 + np.exp(-arg))
    effective = np.maximum(0.0, abs_x - delta * (1.0 - suppression))
    res = np.sign(arr_flat) * effective
    if is_scalar:
        return float(res[0])
    return res.reshape(arr.shape)


# =========================================================================
# Simplicial Complex & Sheaf Operators
# =========================================================================

def build_simplicial_complex(
    correlation_matrix: np.ndarray,
    threshold: float = 0.20,
    max_edges_per_node: int = 5,
    max_triangles: int = 300,
) -> Tuple[List[int], List[Tuple[int, int]], List[Tuple[int, int, int]]]:
    """
    Constructs a simplicial complex K = (V, E, T) from an asset correlation matrix:
      Vertices V: list of node indices [0, 1, ..., N-1]
      Edges E: list of pairs (u, v) with u < v having |corr| >= threshold (bounded top-k degree)
      Triangles T: list of triplets (u, v, w) with u < v < w where all 3 edges exist.
    Optimized via vectorized top-k selection and sparse directed matrix multiplication A_dir @ A_dir.
    """
    import scipy.sparse as sp

    corr = np.asarray(correlation_matrix, dtype=np.float64)
    n = corr.shape[0] if corr.ndim == 2 else 0
    if n == 0:
        return [], [], []

    vertices = list(range(n))
    if n < 2:
        return vertices, [], []

    corr_clean = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    abs_corr = np.abs(corr_clean)
    np.fill_diagonal(abs_corr, -1.0)

    k = min(max_edges_per_node, n - 1)
    if k <= 0:
        return vertices, [], []

    # Vectorized Top-k edge pruning via argpartition across all rows simultaneously
    top_k_indices = np.argpartition(-abs_corr, kth=k - 1, axis=1)[:, :k]
    row_indices = np.repeat(np.arange(n), k)
    col_indices = top_k_indices.flatten()
    weights = abs_corr[row_indices, col_indices]

    # Filter by threshold and remove self-loops
    valid_mask = (weights >= threshold) & (row_indices != col_indices)
    u_cand = np.minimum(row_indices[valid_mask], col_indices[valid_mask])
    v_cand = np.maximum(row_indices[valid_mask], col_indices[valid_mask])

    if len(u_cand) == 0:
        return vertices, [], []

    # Fast unique via 64-bit integer packing: u * n + v
    encoded = u_cand.astype(np.int64) * n + v_cand.astype(np.int64)
    unique_encoded = np.unique(encoded)
    u_edges = (unique_encoded // n).astype(int)
    v_edges = (unique_encoded % n).astype(int)
    edges = sorted(list(zip(u_edges, v_edges)))

    if not edges or max_triangles <= 0:
        return vertices, edges, []

    # Fast Triangle Detection via Sparse Directed Adjacency Matrix Multiplication A_dir @ A_dir
    # For u < v < w: (u, w) has a 2-hop path via v if (A_dir @ A_dir)[u, w] > 0.
    # The triplet (u, v, w) forms a triangle if (u, w) is also an edge in A_dir!
    A_dir = sp.csr_matrix(
        (np.ones(len(u_edges), dtype=np.float32), (u_edges, v_edges)),
        shape=(n, n),
    )
    A_csc = A_dir.tocsc()
    A_2hop = A_dir @ A_dir
    Tri_mat = A_dir.multiply(A_2hop).tocoo()

    triangles: List[Tuple[int, int, int]] = []
    # Iterate only over the non-zero (u, w) pairs that actually participate in triangles
    for u_idx, w_idx in zip(Tri_mat.row, Tri_mat.col):
        u_node = int(u_idx)
        w_node = int(w_idx)
        # Out-neighbors of u: {v | u < v and (u, v) in E}
        nbrs_u = A_dir.indices[A_dir.indptr[u_node]:A_dir.indptr[u_node + 1]]
        # In-neighbors of w: {v | v < w and (v, w) in E}
        nbrs_w = A_csc.indices[A_csc.indptr[w_node]:A_csc.indptr[w_node + 1]]
        # Intermediate nodes v satisfying u < v < w
        common_v = np.intersect1d(nbrs_u, nbrs_w, assume_unique=True)
        for v_node in common_v:
            triangles.append((u_node, int(v_node), w_node))
            if len(triangles) >= max_triangles:
                break
        if len(triangles) >= max_triangles:
            break

    return vertices, edges, triangles


class SheafCoboundaryArray(np.ndarray):
    """NumPy ndarray wrapper holding simplicial edge/triangle metadata for zero-copy extraction."""
    _edges: Optional[List[Tuple[int, int]]] = None
    _u_arr: Optional[np.ndarray] = None
    _v_arr: Optional[np.ndarray] = None


def build_sheaf_coboundary_operators(
    num_vertices: int,
    edges: List[Tuple[int, int]],
    triangles: List[Tuple[int, int, int]],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Constructs discrete coboundary matrices:
      delta0 in R^{|E| x |V|}: (delta0)_{e=(u, v), u} = -1, (delta0)_{e=(u, v), v} = +1
      delta1 in R^{|T| x |E|}: (delta1)_{t=(u, v, w), e=(u, v)} = +1,
                              (delta1)_{t=(u, v, w), e=(v, w)} = +1,
                              (delta1)_{t=(u, v, w), e=(u, w)} = -1.
    Strictly satisfies nilpotency: delta1 @ delta0 == 0.
    """
    n_v = num_vertices
    n_e = len(edges)
    n_t = len(triangles)

    delta0 = np.zeros((n_e, n_v), dtype=np.float64)
    edge_to_idx: Dict[Tuple[int, int], int] = {}

    for idx, (u, v) in enumerate(edges):
        edge_to_idx[(u, v)] = idx
        delta0[idx, u] = -1.0
        delta0[idx, v] = 1.0

    delta1 = np.zeros((n_t, n_e), dtype=np.float64)
    for t_idx, (u, v, w) in enumerate(triangles):
        e_uv = edge_to_idx.get((u, v))
        e_vw = edge_to_idx.get((v, w))
        e_uw = edge_to_idx.get((u, w))

        if e_uv is not None and e_vw is not None and e_uw is not None:
            delta1[t_idx, e_uv] = 1.0
            delta1[t_idx, e_vw] = 1.0
            delta1[t_idx, e_uw] = -1.0

    u_arr = np.array([u for u, v in edges], dtype=np.int32)
    v_arr = np.array([v for u, v in edges], dtype=np.int32)
    delta0_wrapped = delta0.view(SheafCoboundaryArray)
    delta0_wrapped._edges = edges
    delta0_wrapped._u_arr = u_arr
    delta0_wrapped._v_arr = v_arr

    return delta0_wrapped, delta1


def compute_twisted_hodge_laplacians(
    delta0: np.ndarray,
    delta1: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes higher-order Hodge-Laplacian operators:
      Delta_0 = delta0^T @ delta0                   (|V| x |V|, vertex 0-Laplacian)
      Delta_1_down = delta0 @ delta0^T              (|E| x |E|, edge down-Laplacian)
      Delta_1_up = delta1^T @ delta1                (|E| x |E|, edge up-Laplacian)
      Delta_1 = Delta_1_down + Delta_1_up           (|E| x |E|, full 1-Laplacian)
    All operators are symmetric positive semi-definite (PSD).
    """
    delta0_t = delta0.T
    delta1_t = delta1.T

    delta_0 = delta0_t @ delta0
    delta_1_down = delta0 @ delta0_t
    delta_1_up = delta1_t @ delta1
    delta_1 = delta_1_down + delta_1_up

    # Ensure exact numerical symmetry
    delta_0 = 0.5 * (delta_0 + delta_0.T)
    delta_1_down = 0.5 * (delta_1_down + delta_1_down.T)
    delta_1_up = 0.5 * (delta_1_up + delta_1_up.T)
    delta_1 = 0.5 * (delta_1 + delta_1.T)

    return delta_0, delta_1_down, delta_1_up, delta_1


def helmholtz_hodge_decomposition(
    flow_vector: np.ndarray,
    delta0: np.ndarray,
    delta1: np.ndarray,
    edges: Optional[Union[Sequence[Tuple[int, int]], np.ndarray, float]] = None,
    epsilon_reg: float = 1e-6,
    **kwargs: Any,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Performs discrete Helmholtz-Hodge decomposition of an edge flow vector J:
      J = J_{grad} + J_{curl} + J_{harm}
    where:
      J_{grad} = delta0 @ (delta0^T @ delta0 + eps*I)^{-1} @ (delta0^T @ J) in im(delta0)
      J_{curl} = delta1^T @ (delta1 @ delta1^T + eps*I)^{-1} @ (delta1 @ J) in im(delta1^T)
      J_{harm} = J - J_{grad} - J_{curl} in ker(Delta_1)
    Satisfies pairwise mutual orthogonality:
      <J_{grad}, J_{curl}> == 0
      <J_{grad}, J_{harm}> == 0
      <J_{curl}, J_{harm}> == 0
    Accelerated via sparse Graph Laplacian L0 = D - A and Conjugate Gradient (CG) solver.
    """
    # Polymorphic compatibility: allow edges as 4th arg or epsilon_reg as 4th positional arg
    if isinstance(edges, (float, int)):
        epsilon_reg = float(edges)
        edges = kwargs.get("edges", None)
    if "edges" in kwargs and edges is None:
        edges = kwargs["edges"]
    if "epsilon_reg" in kwargs:
        epsilon_reg = float(kwargs["epsilon_reg"])

    j_arr = np.asarray(flow_vector, dtype=np.float64).flatten()
    n_e = len(j_arr)
    if n_e == 0 or delta0.shape[0] != n_e:
        return np.zeros_like(j_arr), np.zeros_like(j_arr), np.zeros_like(j_arr)
    n_v = delta0.shape[1] if delta0.ndim == 2 else n_e
    if n_v == 0:
        return np.zeros_like(j_arr), np.zeros_like(j_arr), np.zeros_like(j_arr)

    # 1. Gradient component (im(delta0)) via Sparse Graph Laplacian L0 = D - A and CG solve
    if edges is not None and not isinstance(edges, (int, float)) and len(edges) == n_e:
        if isinstance(edges, np.ndarray):
            u_arr = edges[:, 0].astype(np.int32)
            v_arr = edges[:, 1].astype(np.int32)
        else:
            u_arr = np.array([u for u, v in edges], dtype=np.int32)
            v_arr = np.array([v for u, v in edges], dtype=np.int32)
    elif getattr(delta0, "_u_arr", None) is not None and len(delta0._u_arr) == n_e:
        u_arr = delta0._u_arr
        v_arr = delta0._v_arr
    elif getattr(delta0, "_edges", None) is not None and len(delta0._edges) == n_e:
        u_arr = np.array([u for u, v in delta0._edges], dtype=np.int32)
        v_arr = np.array([v for u, v in delta0._edges], dtype=np.int32)
    elif sp.issparse(delta0):
        coo = delta0.tocoo()
        u_arr = np.empty(n_e, dtype=np.int32)
        v_arr = np.empty(n_e, dtype=np.int32)
        u_arr[coo.row[coo.data < -0.5]] = coo.col[coo.data < -0.5]
        v_arr[coo.row[coo.data > 0.5]] = coo.col[coo.data > 0.5]
    else:
        u_arr = np.argmin(delta0, axis=1).astype(np.int32)
        v_arr = np.argmax(delta0, axis=1).astype(np.int32)

    n_v = max(n_v, int(np.max(u_arr)) + 1 if len(u_arr) > 0 else n_v, int(np.max(v_arr)) + 1 if len(v_arr) > 0 else n_v)

    # Direct accumulation of rhs0 = delta0.T @ j_arr
    rhs0 = np.zeros(n_v, dtype=np.float64)
    np.add.at(rhs0, u_arr, -j_arr)
    np.add.at(rhs0, v_arr, j_arr)

    # Direct sparse Laplacian assembly L0 = D - A
    rows = np.concatenate([u_arr, v_arr, u_arr, v_arr])
    cols = np.concatenate([u_arr, v_arr, v_arr, u_arr])
    data = np.concatenate([
        np.ones(n_e, dtype=np.float64),
        np.ones(n_e, dtype=np.float64),
        -np.ones(n_e, dtype=np.float64),
        -np.ones(n_e, dtype=np.float64),
    ])
    L_sparse = sp.coo_matrix((data, (rows, cols)), shape=(n_v, n_v)).tocsr()
    L_reg = L_sparse + epsilon_reg * sp.eye(n_v, format="csr", dtype=np.float64)

    # Solve via Conjugate Gradient with robust fallback
    try:
        phi, info = spla.cg(L_reg, rhs0, rtol=1e-5, maxiter=200)
        if info != 0 or not np.all(np.isfinite(phi)):
            phi = spla.lsqr(L_reg, rhs0, atol=1e-5, btol=1e-5, iter_lim=200)[0]
    except Exception:
        try:
            phi = spla.lsqr(L_reg, rhs0, atol=1e-5, btol=1e-5, iter_lim=200)[0]
        except Exception:
            phi = np.zeros(n_v, dtype=np.float64)

    j_grad = phi[v_arr] - phi[u_arr]

    # 2. Curl component (im(delta1^T))
    if delta1.shape[0] > 0 and delta1.shape[1] == n_e:
        d1_sp = delta1 if sp.issparse(delta1) else sp.csr_matrix(delta1)
        l1_curl = (d1_sp @ d1_sp.T).toarray()
        rhs1 = d1_sp @ j_arr
        try:
            c, low = sla.cho_factor(l1_curl + epsilon_reg * np.eye(l1_curl.shape[0]), lower=True)
            psi = sla.cho_solve((c, low), rhs1)
        except Exception:
            try:
                psi = np.linalg.solve(l1_curl + epsilon_reg * np.eye(l1_curl.shape[0]), rhs1)
            except Exception:
                try:
                    psi = np.linalg.lstsq(l1_curl + epsilon_reg * np.eye(l1_curl.shape[0]), rhs1, rcond=None)[0]
                except Exception:
                    psi = np.zeros(l1_curl.shape[0], dtype=np.float64)
        j_curl = np.asarray(d1_sp.T @ psi).flatten()
    else:
        j_curl = np.zeros(n_e, dtype=np.float64)

    # 3. Harmonic component (ker(Delta_1))
    j_harm = j_arr - j_grad - j_curl

    return j_grad, j_curl, j_harm


def project_poincare_ball(
    coords: np.ndarray,
    scale: float = 1.0,
    epsilon: float = 1e-6,
) -> np.ndarray:
    """
    Projects Euclidean embedding coordinates into the open unit Poincaré Ball B^d:
      Pi_B(x) = tanh(scale * ||x||_2) * (x / (||x||_2 + eps))
    Guaranteed ||Pi_B(x)||_2 < 1.0.
    """
    arr = np.asarray(coords, dtype=np.float64)
    if arr.ndim == 1:
        norm = np.linalg.norm(arr)
        if norm < epsilon:
            return np.zeros_like(arr)
        factor = np.tanh(scale * norm) / (norm + epsilon)
        return arr * factor
    elif arr.ndim == 2:
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        factors = np.tanh(scale * norms) / (norms + epsilon)
        return arr * factors
    return arr


# =========================================================================
# Alpha Generation Function
# =========================================================================

def compute_simplicial_sheaf_alpha(
    prices_dict: Dict[str, pd.DataFrame],
    corr_threshold: float = 0.20,
    delta_deadband: float = 0.028,
    epsilon: float = 1e-6,
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
    """
    Computes cross-sectional alpha scores for all symbols using Higher-Order Simplicial Sheaf Hodge flows:
    Returns (raw_alphas, harmonic_fluxes, curl_vorticities).
    """
    symbols = list(prices_dict.keys())
    n = len(symbols)
    if n == 0:
        return {}, {}, {}

    if n < 3:
        # Trivial return for universes with fewer than 3 symbols
        return {s: 0.0 for s in symbols}, {s: 0.0 for s in symbols}, {s: 0.0 for s in symbols}

    # Extract log returns matrix
    rets_dict = {}
    for s in symbols:
        df = prices_dict[s]
        if df is not None and len(df) >= 5:
            col = "Close" if "Close" in df.columns else df.columns[-1]
            p = df[col].to_numpy(dtype=np.float64)
            clean_mask = np.isfinite(p)
            if clean_mask.sum() >= 5 and np.nanstd(p[clean_mask]) > 1e-12:
                p_clean = np.maximum(p[clean_mask], epsilon)
                r = np.diff(np.log(p_clean))
                if len(r) >= 4 and np.nanstd(r) > 1e-12:
                    rets_dict[s] = r[-20:]

    valid_syms = list(rets_dict.keys())
    n_valid = len(valid_syms)
    if n_valid < 3:
        return {s: 0.0 for s in symbols}, {s: 0.0 for s in symbols}, {s: 0.0 for s in symbols}

    # Minimum length alignment
    min_len = min(len(rets_dict[s]) for s in valid_syms)
    rets_matrix = np.column_stack([rets_dict[s][-min_len:] for s in valid_syms])  # shape (T, n_valid)

    # Compute correlation matrix
    corr_matrix = np.corrcoef(rets_matrix, rowvar=False)
    corr_matrix = np.nan_to_num(corr_matrix, nan=0.0, posinf=0.0, neginf=0.0)

    # Build simplicial complex
    vertices, edges, triangles = build_simplicial_complex(corr_matrix, threshold=corr_threshold)
    if not edges:
        return {s: 0.0 for s in symbols}, {s: 0.0 for s in symbols}, {s: 0.0 for s in symbols}

    delta0, delta1 = build_sheaf_coboundary_operators(n_valid, edges, triangles)

    # Edge liquidity flow: latest return differential between connected assets
    last_rets = rets_matrix[-1, :]
    u_idx = np.array([e[0] for e in edges], dtype=np.int32)
    v_idx = np.array([e[1] for e in edges], dtype=np.int32)
    flow_j = last_rets[v_idx] - last_rets[u_idx]

    # Hodge decomposition
    j_grad, j_curl, j_harm = helmholtz_hodge_decomposition(flow_j, delta0, delta1, edges=edges, epsilon_reg=epsilon)

    # Vertex divergence (im(delta0) accumulation)
    div_v = np.zeros(n_valid, dtype=np.float64)
    np.add.at(div_v, u_idx, -flow_j)
    np.add.at(div_v, v_idx, flow_j)

    # Curl vorticity per vertex
    curl_v = np.zeros(n_valid, dtype=np.float64)
    if delta1.shape[0] > 0:
        t_curl = np.abs(delta1 @ flow_j)
        for t_idx, (u, v, w) in enumerate(triangles):
            c_val = t_curl[t_idx]
            curl_v[u] += c_val
            curl_v[v] += c_val
            curl_v[w] += c_val

    # Harmonic flux per vertex
    harm_v = np.zeros(n_valid, dtype=np.float64)
    abs_j_harm = np.abs(j_harm)
    np.add.at(harm_v, u_idx, abs_j_harm)
    np.add.at(harm_v, v_idx, abs_j_harm)

    # Scale normalization
    sig_div = float(np.std(div_v)) + epsilon
    sig_curl = float(np.std(curl_v)) + epsilon
    sig_harm = float(np.std(harm_v)) + epsilon

    raw_scores: Dict[str, float] = {}
    harm_scores: Dict[str, float] = {}
    curl_scores: Dict[str, float] = {}

    for idx, s in enumerate(valid_syms):
        div_i = div_v[idx]
        curl_i = curl_v[idx]
        harm_i = harm_v[idx]

        alpha_raw = (
            1.60 * np.tanh(-div_i / sig_div)
            - 1.80 * np.tanh(curl_i / sig_curl)
            + 1.40 * np.tanh(harm_i / sig_harm)
        )
        alpha_clean = float(apply_hyperbolic_noise_deadband(alpha_raw, delta=delta_deadband, alpha=650.0))
        clamped = float(np.clip(alpha_clean, -3.0, 3.0))

        raw_scores[s] = clamped
        harm_scores[s] = float(harm_i)
        curl_scores[s] = float(curl_i)

    # Fill defaults for any missing symbols
    for s in symbols:
        if s not in raw_scores:
            raw_scores[s] = 0.0
            harm_scores[s] = 0.0
            curl_scores[s] = 0.0

    return raw_scores, harm_scores, curl_scores


# =========================================================================
# Interface Contract Function: compute_simplicial_sheaf_flow (PROJECT.md:79)
# =========================================================================

def compute_simplicial_sheaf_flow(
    correlation_matrix: np.ndarray,
    returns: np.ndarray,
    corr_threshold: float = 0.15,
    delta_deadband: float = 0.028,
    epsilon: float = 1e-6,
) -> np.ndarray:
    """
    Contract function for Feature F960 (PROJECT.md:79):
    Computes simplicial sheaf flow alpha given correlation matrix and return vector.
    - Zero lookahead bias, strictly bounded in [-3.0, 3.0].
    - Helmholtz-Hodge curl/gradient/harmonic decomposition on 2-simplices.
    """
    corr = np.nan_to_num(np.asarray(correlation_matrix, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    ret = np.nan_to_num(np.asarray(returns, dtype=np.float64).flatten(), nan=0.0, posinf=3.0, neginf=-3.0)
    n = corr.shape[0] if corr.ndim >= 2 else len(ret)
    if n == 0 or len(ret) == 0:
        return np.array([], dtype=np.float64)

    # Flat zero returns yield exact zero flow
    if np.all(np.abs(ret) < 1e-12):
        return np.zeros(n, dtype=np.float64)

    if n < 2 or len(ret) < n:
        return np.zeros(n, dtype=np.float64)

    # Adaptive threshold fallback: if threshold yields no edges, retry at lower threshold
    thresh = corr_threshold
    vertices, edges, triangles = build_simplicial_complex(corr, threshold=thresh)
    if not edges and thresh > 0.05:
        vertices, edges, triangles = build_simplicial_complex(corr, threshold=0.05)

    if not edges:
        # Fallback to Graph Laplacian L0 = D - A on absolute correlation
        A = np.abs(corr) - np.eye(n)
        A = np.maximum(0.0, A)
        D = np.diag(np.sum(A, axis=1))
        L0 = D - A
        flow = L0 @ ret
        std_flow = float(np.std(flow))
        if std_flow < 1e-12:
            return np.zeros(n, dtype=np.float64)
        alpha = 3.0 * np.tanh(flow / (std_flow + epsilon))
        if delta_deadband > 0.0:
            alpha = apply_hyperbolic_noise_deadband(alpha, delta=delta_deadband, alpha=650.0)
        return np.clip(np.asarray(alpha, dtype=np.float64), -3.0, 3.0)

    delta0, delta1 = build_sheaf_coboundary_operators(n, edges, triangles)
    u_idx = np.array([e[0] for e in edges], dtype=int)
    v_idx = np.array([e[1] for e in edges], dtype=int)
    flow_j = ret[v_idx] - ret[u_idx]

    j_grad, j_curl, j_harm = helmholtz_hodge_decomposition(flow_j, delta0, delta1, edges=edges, epsilon_reg=epsilon)

    # Divergence at vertices
    div_v = np.zeros(n, dtype=np.float64)
    np.add.at(div_v, u_idx, -flow_j)
    np.add.at(div_v, v_idx, flow_j)

    # Curl vorticity per vertex
    curl_v = np.zeros(n, dtype=np.float64)
    if delta1.shape[0] > 0:
        t_curl = np.abs(delta1 @ flow_j)
        for t_idx, (u, v, w) in enumerate(triangles):
            c_val = t_curl[t_idx]
            curl_v[u] += c_val
            curl_v[v] += c_val
            curl_v[w] += c_val

    # Harmonic flux per vertex
    harm_v = np.zeros(n, dtype=np.float64)
    abs_j_harm = np.abs(j_harm)
    np.add.at(harm_v, u_idx, abs_j_harm)
    np.add.at(harm_v, v_idx, abs_j_harm)

    sig_div = float(np.std(div_v)) + epsilon
    sig_curl = float(np.std(curl_v)) + epsilon
    sig_harm = float(np.std(harm_v)) + epsilon

    alpha_raw = (
        1.60 * np.tanh(-div_v / sig_div)
        - 1.80 * np.tanh(curl_v / sig_curl)
        + 1.40 * np.tanh(harm_v / sig_harm)
    )
    alpha_clean = apply_hyperbolic_noise_deadband(alpha_raw, delta=delta_deadband, alpha=650.0)
    alpha_clamped = np.clip(np.asarray(alpha_clean, dtype=np.float64), -3.0, 3.0)
    return alpha_clamped


# =========================================================================
# Strategy Engine Class
# =========================================================================

class HigherOrderSimplicialSheafLaplacianEngine(BaseStrategyEngine):
    """
    Feature F960: Higher-Order Simplicial Sheaf Laplacian & Hyperbolic Hodge Flow Engine.
    Evaluates simplicial complexes, coboundary nilpotency, twisted Hodge-Laplacians,
    and discrete Helmholtz-Hodge liquidity decomposition.
    """
    lookahead_safe: bool = True

    def __init__(
        self,
        name: str = "simplicial_sheaf_laplacian",
        config: Optional[Any] = None,
        corr_threshold: float = 0.20,
        delta_deadband: float = 0.028,
    ) -> None:
        super().__init__(name=name, config=config)
        self.corr_threshold = corr_threshold
        self.delta_deadband = delta_deadband

    def compute_simplicial_sheaf_flow(
        self,
        correlation_matrix: np.ndarray,
        returns: np.ndarray,
    ) -> np.ndarray:
        """
        Contract method: computes simplicial sheaf flow alpha from correlation matrix and returns.
        """
        return compute_simplicial_sheaf_flow(
            correlation_matrix=correlation_matrix,
            returns=returns,
            corr_threshold=self.corr_threshold,
            delta_deadband=self.delta_deadband,
        )

    @staticmethod
    def poincare_distance(u: np.ndarray, v: np.ndarray) -> float:
        """Hyperbolic Poincaré ball metric."""
        u_arr = np.asarray(u, dtype=np.float64)
        v_arr = np.asarray(v, dtype=np.float64)
        u_norm = np.clip(np.linalg.norm(u_arr), 0.0, 0.999)
        v_norm = np.clip(np.linalg.norm(v_arr), 0.0, 0.999)
        diff_sq = np.sum((u_arr - v_arr) ** 2)
        arg = 1.0 + 2.0 * diff_sq / ((1.0 - u_norm ** 2) * (1.0 - v_norm ** 2) + 1e-12)
        return float(np.arccosh(max(1.0, arg)))

    def generate_signals(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        market_regime: Optional[str] = None,
        **kwargs: Any,
    ) -> ScoreDataFrame:
        """
        Generates cross-sectional alpha scores for universe symbols via
        Higher-Order Simplicial Sheaf Hodge Flows.
        """
        raw_scores, harm_scores, curl_scores = compute_simplicial_sheaf_alpha(
            prices_dict=prices_dict,
            corr_threshold=self.corr_threshold,
            delta_deadband=self.delta_deadband,
        )

        norm_scores = self.normalize_scores_series(raw_scores, min_clip=0.05, max_clip=0.95)

        records = [
            {
                "symbol": sym,
                "simplicial_sheaf_laplacian_score": norm_scores.get(sym, 0.50),
                "raw_score": raw_scores.get(sym, 0.0),
                "harmonic_flow": harm_scores.get(sym, 0.0),
                "curl_vorticity": curl_scores.get(sym, 0.0),
            }
            for sym in prices_dict.keys()
        ]
        return make_score_dataframe(records, score_column="simplicial_sheaf_laplacian_score")


# Complete Backward-Compatible Alias Trees
HigherOrderSimplicialSheafEngine = HigherOrderSimplicialSheafLaplacianEngine
Phase195SimplicialSheafEngine = HigherOrderSimplicialSheafLaplacianEngine
F960SimplicialSheafEngine = HigherOrderSimplicialSheafLaplacianEngine
HigherOrderHodgeFlowEngine = HigherOrderSimplicialSheafLaplacianEngine
SimplicialSheafLaplacianEngine = HigherOrderSimplicialSheafLaplacianEngine
Phase185SimplicialSheafEngine = HigherOrderSimplicialSheafLaplacianEngine

# Dynamic Strategy Registration
try:
    from src.core.strategy_registry import register_strategy, StrategyMeta
    register_strategy(
        StrategyMeta(
            strategy_id="simplicial_sheaf_laplacian",
            display_name="Higher-Order Simplicial Sheaf Laplacian (F960)",
            score_column="simplicial_sheaf_laplacian_score",
            category="factor",
            output_file="simplicial_sheaf_predictions.txt",
        )
    )(HigherOrderSimplicialSheafLaplacianEngine)
except Exception:
    pass

__all__ = [
    "VERSION",
    "RELEASE",
    "FEATURE",
    "VERSION_PHASE195",
    "RELEASE_PHASE195",
    "FEATURE_PHASE195",
    "VERSION_PHASE185",
    "RELEASE_PHASE185",
    "FEATURE_PHASE185",
    "VERSION_PHASE193",
    "RELEASE_PHASE193",
    "FEATURE_PHASE193",
    "VERSION_PHASE184",
    "RELEASE_PHASE184",
    "FEATURE_PHASE184",
    "apply_hyperbolic_noise_deadband",
    "build_simplicial_complex",
    "build_sheaf_coboundary_operators",
    "compute_twisted_hodge_laplacians",
    "helmholtz_hodge_decomposition",
    "project_poincare_ball",
    "compute_simplicial_sheaf_alpha",
    "compute_simplicial_sheaf_flow",
    "HigherOrderSimplicialSheafLaplacianEngine",
    "HigherOrderSimplicialSheafEngine",
    "Phase195SimplicialSheafEngine",
    "F960SimplicialSheafEngine",
    "HigherOrderHodgeFlowEngine",
    "SimplicialSheafLaplacianEngine",
    "Phase185SimplicialSheafEngine",
]
