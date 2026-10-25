"""
Closed-Loop Realized Slippage Execution Feedback Engine
Calculates real vs theoretical slippage from trade_logs.db and dynamically updates
microstructure cost parameters in the ensemble scoring engine.
Enhanced with an Online Adaptive Recursive Kalman Filter for continuous calibration
of the Gatheral/Almgren-Chriss market impact coefficient (kappa) and spread fraction (beta).
"""

from __future__ import annotations

import logging
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SlippageMetrics:
    avg_slippage_bps: float = 5.0
    market_impact_alpha: float = 0.50
    sample_count: int = 0
    cost_scaling_factor: float = 1.0
    market_slippage_map: Dict[str, float] = field(
        default_factory=lambda: {
            "KOSPI": 5.0,
            "KOSDAQ": 8.0,
            "SP500": 3.0,
            "NASDAQ": 4.0,
            "RUSSELL2000": 7.0,
        }
    )
    market_cost_scaling_map: Dict[str, float] = field(
        default_factory=lambda: {
            "KOSPI": 1.0,
            "KOSDAQ": 1.0,
            "SP500": 1.0,
            "NASDAQ": 1.0,
            "RUSSELL2000": 1.0,
        }
    )
    total_trades: int = 0
    mean_slippage_bps: float = 5.0
    max_slippage_bps: float = 15.0
    recommended_market_impact_multiplier: float = 1.0
    bayesian_cost_scaling_factor: float = 1.0
    # Recursive Kalman Filter Calibration States
    kalman_kappa: float = 0.50
    kalman_beta: float = 1.00
    kalman_state: List[float] = field(default_factory=lambda: [0.50, 1.00])
    kalman_covariance: List[List[float]] = field(default_factory=lambda: [[0.25, 0.0], [0.0, 0.25]])
    kalman_cost_scaling_factor: float = 1.0


class OnlineKalmanSlippageFilter:
    """
    2D Recursive Kalman Filter for Online Slippage & Impact Estimation.

    State:
      theta_t = [kappa_t, beta_t]^T
      - kappa_t: Market impact coefficient (Almgren-Chriss / Gatheral impact scale)
      - beta_t: Effective spread fraction / base slippage scale

    Observation:
      y_t = H_t * theta_t + v_t
      - H_t = [h_kappa, h_beta]
      - h_kappa = sigma * sqrt(Q / ADV) * 10000 (bps) or impact proxy
      - h_beta = base_slippage_bps
      - y_t = realized_slippage_bps
    """

    def __init__(
        self,
        initial_kappa: float = 0.50,
        initial_beta: float = 1.00,
        process_noise_cov: Optional[np.ndarray] = None,
        measurement_noise_var: float = 9.0,
        initial_covariance: Optional[np.ndarray] = None,
        kappa_bounds: Tuple[float, float] = (0.05, 5.0),
        beta_bounds: Tuple[float, float] = (0.10, 5.0),
    ):
        self.theta = np.array([float(initial_kappa), float(initial_beta)], dtype=float)
        self.P = (
            np.array(initial_covariance, dtype=float)
            if initial_covariance is not None
            else np.diag([0.25, 0.25])
        )
        self.Q = (
            np.array(process_noise_cov, dtype=float)
            if process_noise_cov is not None
            else np.diag([1e-4, 1e-4])
        )
        self.R = float(measurement_noise_var)
        self.kappa_bounds = kappa_bounds
        self.beta_bounds = beta_bounds
        self.update_count = 0
        self.history: List[Dict[str, float]] = []

    def update(
        self,
        realized_slippage_bps: float,
        h_kappa: float,
        h_beta: float = 5.0,
        R_override: Optional[float] = None,
    ) -> Tuple[float, float]:
        """
        Executes one recursive Kalman update step with Joseph-stabilized covariance.
        Returns: (kappa_t, beta_t)
        """
        y = float(realized_slippage_bps)
        if not math.isfinite(y):
            return float(self.theta[0]), float(self.theta[1])

        hk = float(h_kappa) if (h_kappa is not None and math.isfinite(float(h_kappa))) else 0.0
        hb = float(h_beta) if (h_beta is not None and math.isfinite(float(h_beta))) else 5.0
        H = np.array([hk, hb], dtype=float)

        # 1. Prediction step: theta_{t|t-1} = theta_{t-1}, P_{t|t-1} = P_{t-1} + Q
        P_pred = self.P + self.Q

        # 2. Innovation
        pred_y = float(np.dot(H, self.theta))
        innovation = y - pred_y
        R = float(R_override) if R_override is not None else self.R
        S = float(np.dot(H, np.dot(P_pred, H)) + R)
        if S <= 1e-9:
            S = 1e-9

        # 3. Kalman Gain: K = P_pred * H^T / S
        K = np.dot(P_pred, H) / S

        # 4. State Update
        theta_new = self.theta + K * innovation

        # 5. Joseph-Stabilized Covariance Update:
        # P = (I - K*H) * P_pred * (I - K*H)^T + K * R * K^T
        I = np.eye(2)
        IKH = I - np.outer(K, H)
        P_new = np.dot(IKH, np.dot(P_pred, IKH.T)) + np.outer(K, K) * R
        P_new = 0.5 * (P_new + P_new.T)

        # 6. Projection / Bounding
        theta_new[0] = float(np.clip(theta_new[0], self.kappa_bounds[0], self.kappa_bounds[1]))
        theta_new[1] = float(np.clip(theta_new[1], self.beta_bounds[0], self.beta_bounds[1]))

        self.theta = theta_new
        self.P = P_new
        self.update_count += 1
        self.history.append({
            "step": float(self.update_count),
            "y": y,
            "pred_y": pred_y,
            "innovation": innovation,
            "kappa": float(theta_new[0]),
            "beta": float(theta_new[1]),
        })

        return float(self.theta[0]), float(self.theta[1])

    def batch_update(self, observations: List[Dict[str, float]]) -> Tuple[float, float]:
        """Runs a sequence of (realized_slippage_bps, h_kappa, h_beta) updates."""
        for obs in observations:
            y = obs.get("realized_slippage_bps", obs.get("y", 0.0))
            hk = obs.get("h_kappa", obs.get("hk", 0.0))
            hb = obs.get("h_beta", obs.get("hb", 5.0))
            self.update(y, hk, hb)
        return float(self.theta[0]), float(self.theta[1])

    def get_state(self) -> Dict[str, Any]:
        """Returns the current state vector, covariance matrix, and update count."""
        scaling = float(np.clip(self.theta[1] * (self.theta[0] / 0.50), 0.5, 8.0))
        return {
            "kappa": float(self.theta[0]),
            "beta": float(self.theta[1]),
            "covariance": self.P.tolist(),
            "update_count": self.update_count,
            "cost_scaling_factor": scaling,
        }

    def reset(self, initial_kappa: float = 0.50, initial_beta: float = 1.00) -> None:
        """Resets filter state and covariance to baseline priors."""
        self.theta = np.array([float(initial_kappa), float(initial_beta)], dtype=float)
        self.P = np.diag([0.25, 0.25])
        self.update_count = 0
        self.history.clear()


class SlippageFeedbackEngine:
    """
    Queries execution trade logs and computes real vs theoretical slippage metrics,
    returning cost adjustments to tune microstructure cost modeling and the Gatheral
    3/2-power market impact penalty via an online recursive Kalman filter.
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        default_slippage_bps: float = 5.0,
        initial_kappa: float = 0.50,
        initial_beta: float = 1.00,
    ):
        _root = Path(__file__).resolve().parent.parent.parent
        if db_path is None:
            p = _root / "trade_logs.db"
        else:
            p = Path(db_path)
            if not p.is_absolute():
                candidate = _root / p
                if candidate.exists():
                    p = candidate
                elif p.exists():
                    p = p.resolve()
                else:
                    p = _root / p
        self.db_path = str(p)
        try:
            safe_slip = (
                float(default_slippage_bps)
                if (default_slippage_bps is not None and math.isfinite(float(default_slippage_bps)))
                else 5.0
            )
        except (ValueError, TypeError):
            safe_slip = 5.0
        self.default_slippage_bps = max(0.0, min(1000.0, safe_slip))
        self.kalman_filter = OnlineKalmanSlippageFilter(
            initial_kappa=initial_kappa,
            initial_beta=initial_beta,
        )

    def calculate_realized_slippage(
        self,
        *args,
        use_bayesian_shrinkage: bool = False,
        use_kalman: bool = True,
        **kwargs,
    ) -> SlippageMetrics:
        """Reads trade_logs.db and returns realized slippage metrics in basis points (bps)."""
        baseline_defaults = {
            "KOSPI": 5.0,
            "KOSDAQ": 8.0,
            "SP500": 3.0,
            "NASDAQ": 4.0,
            "RUSSELL2000": 7.0,
        }

        if not Path(self.db_path).exists():
            k_state = self.kalman_filter.get_state()
            return SlippageMetrics(
                avg_slippage_bps=self.default_slippage_bps,
                market_impact_alpha=0.50,
                sample_count=0,
                cost_scaling_factor=1.0,
                total_trades=0,
                mean_slippage_bps=self.default_slippage_bps,
                max_slippage_bps=15.0,
                recommended_market_impact_multiplier=1.0,
                kalman_kappa=k_state["kappa"],
                kalman_beta=k_state["beta"],
                kalman_state=[k_state["kappa"], k_state["beta"]],
                kalman_covariance=k_state["covariance"],
                kalman_cost_scaling_factor=k_state["cost_scaling_factor"],
            )

        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            try:
                cursor = conn.cursor()

                # Check available tables in trade_logs.db
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cursor.fetchall()]

                slippages: List[float] = []
                kalman_obs: List[Tuple[float, float, float]] = []
                mkt_slippage: Dict[str, List[float]] = {
                    "KOSPI": [],
                    "KOSDAQ": [],
                    "SP500": [],
                    "NASDAQ": [],
                    "RUSSELL2000": [],
                }

                if "execution_logs" in tables and "order_plans" in tables:
                    cursor.execute("""
                        SELECT p.market, p.action, p.target_price, e.executed_price
                        FROM execution_logs e
                        JOIN order_plans p ON e.order_id = p.order_id
                        WHERE e.executed_price IS NOT NULL AND p.target_price > 0
                    """)
                    rows = cursor.fetchall()
                    for mkt, act, p_target, p_exec in rows:
                        try:
                            pt = float(p_target) if (p_target is not None and math.isfinite(float(p_target))) else 0.0
                            pe = float(p_exec) if (p_exec is not None and math.isfinite(float(p_exec))) else 0.0
                        except (ValueError, TypeError):
                            continue
                        if pt > 0 and pe > 0:
                            act_str = str(act).strip().upper()
                            sign = 1.0 if (act_str.startswith("BUY") or act_str in ["LONG", "BUY_HEDGE"]) else -1.0
                            slip_bps = sign * ((pe - pt) / pt) * 10000.0
                            if math.isfinite(slip_bps):
                                slippages.append(slip_bps)
                                mkt_name = str(mkt).upper().strip()
                                base_b = baseline_defaults.get(mkt_name, self.default_slippage_bps)
                                kalman_obs.append((slip_bps, 2.5, base_b))
                                if mkt_name in mkt_slippage:
                                    mkt_slippage[mkt_name].append(slip_bps)

                elif "executions" in tables and "orders" in tables:
                    cursor.execute("PRAGMA table_info(orders)")
                    ord_cols = {r[1] for r in cursor.fetchall()}
                    if "order_type" in ord_cols:
                        cursor.execute("""
                            SELECT o.symbol, o.order_type, o.price, e.price
                            FROM executions e
                            JOIN orders o ON e.order_id = o.order_id
                            WHERE e.price IS NOT NULL AND o.price > 0
                        """)
                    else:
                        cursor.execute("""
                            SELECT o.symbol, o.side, o.price, e.price
                            FROM executions e
                            JOIN orders o ON e.order_id = o.order_id
                            WHERE e.price IS NOT NULL AND o.price > 0
                        """)
                    rows = cursor.fetchall()
                    for sym, side, p_exp, p_fill in rows:
                        try:
                            pe = float(p_exp) if (p_exp is not None and math.isfinite(float(p_exp))) else 0.0
                            pf = float(p_fill) if (p_fill is not None and math.isfinite(float(p_fill))) else 0.0
                        except (ValueError, TypeError):
                            continue
                        if pe > 0 and pf > 0:
                            side_str = str(side).strip().upper()
                            sign = 1.0 if (side_str.startswith("BUY") or side_str in ["LONG", "BUY_HEDGE"]) else -1.0
                            slip_bps = sign * ((pf - pe) / pe) * 10000.0
                            if math.isfinite(slip_bps):
                                slippages.append(slip_bps)
                                sym_str = str(sym).upper().strip()
                                mkt = "KOSPI" if sym_str.isdigit() and len(sym_str) == 6 else ("KOSDAQ" if sym_str.endswith(".KQ") else "SP500")
                                base_b = baseline_defaults.get(mkt, self.default_slippage_bps)
                                kalman_obs.append((slip_bps, 2.5, base_b))
                                if mkt in mkt_slippage:
                                    mkt_slippage[mkt].append(slip_bps)

                elif "trade_logs" in tables:
                    cursor.execute("PRAGMA table_info(trade_logs)")
                    tl_cols = {r[1] for r in cursor.fetchall()}
                    if "adv_20d" in tl_cols and "volatility" in tl_cols and "order_qty" in tl_cols:
                        cursor.execute("""
                            SELECT market, side, expected_price, fill_price, order_qty, adv_20d, volatility
                            FROM trade_logs WHERE fill_price IS NOT NULL AND expected_price > 0
                        """)
                        rows = cursor.fetchall()
                        for mkt, side, p_exp, p_fill, o_qty, adv, vol in rows:
                            try:
                                pe = float(p_exp) if (p_exp is not None and math.isfinite(float(p_exp))) else 0.0
                                pf = float(p_fill) if (p_fill is not None and math.isfinite(float(p_fill))) else 0.0
                            except (ValueError, TypeError):
                                continue
                            if pe > 0 and pf > 0:
                                side_str = str(side).strip().upper()
                                sign = 1.0 if (side_str.startswith("BUY") or side_str in ["LONG", "BUY_HEDGE"]) else -1.0
                                slip_bps = sign * ((pf - pe) / pe) * 10000.0
                                if math.isfinite(slip_bps):
                                    slippages.append(slip_bps)
                                    mkt_u = str(mkt).upper().strip()
                                    base_b = baseline_defaults.get(mkt_u, self.default_slippage_bps)
                                    adv_f = float(adv) if (adv is not None and math.isfinite(float(adv))) else 0.0
                                    qty_f = float(o_qty) if (o_qty is not None and math.isfinite(float(o_qty))) else 0.0
                                    vol_f = float(vol) if (vol is not None and math.isfinite(float(vol))) else 0.02
                                    if adv_f > 0 and qty_f > 0:
                                        hk = vol_f * math.sqrt(min(1.0, max(0.0, qty_f / adv_f))) * 10000.0
                                    else:
                                        hk = 2.5
                                    kalman_obs.append((slip_bps, hk, base_b))
                                    if mkt_u in mkt_slippage:
                                        mkt_slippage[mkt_u].append(slip_bps)
                    else:
                        cursor.execute(
                            "SELECT market, side, expected_price, fill_price FROM trade_logs WHERE fill_price IS NOT NULL AND expected_price > 0"
                        )
                        rows = cursor.fetchall()
                        for mkt, side, p_exp, p_fill in rows:
                            try:
                                pe = float(p_exp) if (p_exp is not None and math.isfinite(float(p_exp))) else 0.0
                                pf = float(p_fill) if (p_fill is not None and math.isfinite(float(p_fill))) else 0.0
                            except (ValueError, TypeError):
                                continue
                            if pe > 0 and pf > 0:
                                side_str = str(side).strip().upper()
                                sign = 1.0 if (side_str.startswith("BUY") or side_str in ["LONG", "BUY_HEDGE"]) else -1.0
                                slip_bps = sign * ((pf - pe) / pe) * 10000.0
                                if math.isfinite(slip_bps):
                                    slippages.append(slip_bps)
                                    mkt_u = str(mkt).upper().strip()
                                    base_b = baseline_defaults.get(mkt_u, self.default_slippage_bps)
                                    kalman_obs.append((slip_bps, 2.5, base_b))
                                    if mkt_u in mkt_slippage:
                                        mkt_slippage[mkt_u].append(slip_bps)

                if "paper_executions" in tables:
                    cursor.execute("PRAGMA table_info(paper_executions)")
                    pe_cols = {r[1] for r in cursor.fetchall()}
                    if "market_impact_bps" in pe_cols:
                        cursor.execute("""
                            SELECT market, action, target_price, executed_price, slippage_bps, market_impact_bps
                            FROM paper_executions
                            WHERE executed_price IS NOT NULL AND target_price > 0
                        """)
                        rows = cursor.fetchall()
                        for mkt, act, p_target, p_exec, s_rec, imp_rec in rows:
                            try:
                                pt = float(p_target) if (p_target is not None and math.isfinite(float(p_target))) else 0.0
                                pe = float(p_exec) if (p_exec is not None and math.isfinite(float(p_exec))) else 0.0
                                s_bps = float(s_rec) if (s_rec is not None and math.isfinite(float(s_rec))) else None
                                imp_bps = float(imp_rec) if (imp_rec is not None and math.isfinite(float(imp_rec))) else None
                            except (ValueError, TypeError):
                                continue
                            if s_bps is not None and math.isfinite(s_bps):
                                slip_bps = s_bps
                            elif pt > 0 and pe > 0:
                                act_str = str(act).strip().upper()
                                sign = 1.0 if (act_str.startswith("BUY") or act_str in ["LONG", "BUY_HEDGE"]) else -1.0
                                slip_bps = sign * ((pe - pt) / pt) * 10000.0
                            else:
                                continue
                            if math.isfinite(slip_bps):
                                slippages.append(slip_bps)
                                mkt_u = str(mkt).upper().strip()
                                base_b = baseline_defaults.get(mkt_u, self.default_slippage_bps)
                                hk = imp_bps if (imp_bps is not None and imp_bps > 0) else 2.5
                                kalman_obs.append((slip_bps, hk, base_b))
                                if mkt_u in mkt_slippage:
                                    mkt_slippage[mkt_u].append(slip_bps)
                    else:
                        cursor.execute("""
                            SELECT market, action, target_price, executed_price, slippage_bps
                            FROM paper_executions
                            WHERE executed_price IS NOT NULL AND target_price > 0
                        """)
                        rows = cursor.fetchall()
                        for mkt, act, p_target, p_exec, s_rec in rows:
                            try:
                                pt = float(p_target) if (p_target is not None and math.isfinite(float(p_target))) else 0.0
                                pe = float(p_exec) if (p_exec is not None and math.isfinite(float(p_exec))) else 0.0
                                s_bps = float(s_rec) if (s_rec is not None and math.isfinite(float(s_rec))) else None
                            except (ValueError, TypeError):
                                continue
                            if s_bps is not None and math.isfinite(s_bps):
                                slip_bps = s_bps
                            elif pt > 0 and pe > 0:
                                act_str = str(act).strip().upper()
                                sign = 1.0 if (act_str.startswith("BUY") or act_str in ["LONG", "BUY_HEDGE"]) else -1.0
                                slip_bps = sign * ((pe - pt) / pt) * 10000.0
                            else:
                                continue
                            if math.isfinite(slip_bps):
                                slippages.append(slip_bps)
                                mkt_u = str(mkt).upper().strip()
                                base_b = baseline_defaults.get(mkt_u, self.default_slippage_bps)
                                kalman_obs.append((slip_bps, 2.5, base_b))
                                if mkt_u in mkt_slippage:
                                    mkt_slippage[mkt_u].append(slip_bps)
            finally:
                conn.close()

            valid_slippages = [s for s in slippages if math.isfinite(s)]

            if not valid_slippages:
                k_state = self.kalman_filter.get_state()
                return SlippageMetrics(
                    avg_slippage_bps=self.default_slippage_bps,
                    market_impact_alpha=0.50,
                    sample_count=0,
                    cost_scaling_factor=1.0,
                    total_trades=0,
                    mean_slippage_bps=self.default_slippage_bps,
                    max_slippage_bps=15.0,
                    recommended_market_impact_multiplier=1.0,
                    kalman_kappa=k_state["kappa"],
                    kalman_beta=k_state["beta"],
                    kalman_state=[k_state["kappa"], k_state["beta"]],
                    kalman_covariance=k_state["covariance"],
                    kalman_cost_scaling_factor=k_state["cost_scaling_factor"],
                )

            # Robust estimation: Hard-clip extreme outliers and apply MAD
            arr = np.clip(np.array(valid_slippages, dtype=float), -500.0, 500.0)
            med = float(np.median(arr)) if len(arr) > 0 else self.default_slippage_bps
            mad = float(np.median(np.abs(arr - med))) if len(arr) > 0 else 0.0
            mad_sigma = mad * 1.4826
            if mad_sigma > 1e-4 and len(arr) >= 5:
                filtered = arr[np.abs(arr - med) <= 3.5 * mad_sigma]
                avg_slip = float(np.mean(filtered)) if len(filtered) > 0 else med
            else:
                std_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
                if std_val > 1e-4:
                    filtered = arr[np.abs(arr - med) <= 3.5 * std_val]
                    avg_slip = float(np.mean(filtered)) if len(filtered) > 0 else med
                else:
                    avg_slip = med

            max_slip = float(np.max(valid_slippages)) if valid_slippages else 15.0
            avg_slip = (
                float(np.clip(avg_slip, -50.0, 100.0))
                if (avg_slip is not None and math.isfinite(avg_slip))
                else self.default_slippage_bps
            )
            max_slip = (
                float(np.clip(max_slip, -100.0, 500.0))
                if (max_slip is not None and math.isfinite(max_slip))
                else 15.0
            )

            # Bayesian shrinkage for small sample counts (N < 10)
            max_scale_cap = 8.0
            raw_scaling = (
                float(np.clip(avg_slip / self.default_slippage_bps, 0.5, max_scale_cap))
                if self.default_slippage_bps > 0
                else 1.0
            )
            if not math.isfinite(raw_scaling):
                raw_scaling = 1.0

            n_samples = len(valid_slippages)
            prior_n = 10.0
            bayesian_scaling = float(
                np.clip(
                    (n_samples / (n_samples + prior_n)) * raw_scaling
                    + (prior_n / (n_samples + prior_n)) * 1.0,
                    0.5,
                    max_scale_cap,
                )
            )
            scaling = bayesian_scaling if use_bayesian_shrinkage else raw_scaling

            # Online Recursive Kalman Filter updates across observed executions
            if use_kalman and kalman_obs:
                self.kalman_filter.reset()
                for s_bps, hk, hb in kalman_obs:
                    if math.isfinite(s_bps):
                        clipped_s = float(np.clip(s_bps, -50.0, 100.0))
                        self.kalman_filter.update(clipped_s, hk, hb)

            k_state = self.kalman_filter.get_state()
            kalman_kappa = k_state["kappa"]
            kalman_beta = k_state["beta"]
            kalman_cov = k_state["covariance"]
            kalman_cost_scaling = k_state["cost_scaling_factor"]

            alpha = 0.50

            final_mkt_map = {}
            final_mkt_scaling = {}
            for mkt, val_list in mkt_slippage.items():
                base_bps = baseline_defaults.get(mkt, self.default_slippage_bps)
                v_finite = [v for v in val_list if math.isfinite(v)]
                if v_finite:
                    m_val = float(np.mean(v_finite))
                    final_mkt_map[mkt] = float(np.clip(m_val, 0.1, 100.0)) if math.isfinite(m_val) else base_bps
                    final_mkt_scaling[mkt] = float(np.clip(m_val / max(base_bps, 0.1), 0.5, 4.0))
                else:
                    final_mkt_map[mkt] = base_bps
                    final_mkt_scaling[mkt] = 1.0

            for mkt, base_bps in baseline_defaults.items():
                if mkt not in final_mkt_map:
                    final_mkt_map[mkt] = base_bps
                if mkt not in final_mkt_scaling:
                    final_mkt_scaling[mkt] = 1.0

            return SlippageMetrics(
                avg_slippage_bps=avg_slip,
                market_impact_alpha=alpha,
                sample_count=len(valid_slippages),
                cost_scaling_factor=scaling,
                market_slippage_map=final_mkt_map,
                market_cost_scaling_map=final_mkt_scaling,
                total_trades=len(valid_slippages),
                mean_slippage_bps=avg_slip,
                max_slippage_bps=max_slip,
                recommended_market_impact_multiplier=bayesian_scaling,
                bayesian_cost_scaling_factor=bayesian_scaling,
                kalman_kappa=kalman_kappa,
                kalman_beta=kalman_beta,
                kalman_state=[kalman_kappa, kalman_beta],
                kalman_covariance=kalman_cov,
                kalman_cost_scaling_factor=kalman_cost_scaling,
            )

        except Exception as e:
            logger.error(f"Error calculating realized slippage: {e}")
            k_state = self.kalman_filter.get_state()
            return SlippageMetrics(
                avg_slippage_bps=self.default_slippage_bps,
                market_impact_alpha=0.50,
                sample_count=0,
                cost_scaling_factor=1.0,
                kalman_kappa=k_state["kappa"],
                kalman_beta=k_state["beta"],
                kalman_state=[k_state["kappa"], k_state["beta"]],
                kalman_covariance=k_state["covariance"],
                kalman_cost_scaling_factor=k_state["cost_scaling_factor"],
            )

    def analyze_realized_slippage(self) -> SlippageMetrics:
        return self.calculate_realized_slippage()

    def record_execution(
        self,
        symbol: str,
        market: str,
        side: str,
        order_qty: int,
        filled_qty: int,
        target_price: float,
        executed_price: float,
        realized_slippage_bps: Optional[float] = None,
        realized_impact_bps: Optional[float] = None,
        adv_20d: Optional[float] = None,
        volatility: Optional[float] = None,
        notes: str = "",
    ) -> None:
        """Records an execution event directly into SQLite and performs online Kalman update."""
        from datetime import datetime

        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_qty INTEGER NOT NULL,
                    filled_qty INTEGER NOT NULL,
                    expected_price REAL NOT NULL,
                    fill_price REAL NOT NULL,
                    slippage_bps REAL,
                    market_impact_bps REAL,
                    adv_20d REAL,
                    volatility REAL,
                    timestamp TIMESTAMP NOT NULL,
                    notes TEXT
                );
            """)
            s_bps = realized_slippage_bps
            if s_bps is None and target_price > 0:
                side_str = str(side).upper().strip()
                sign = 1.0 if (side_str.startswith("BUY") or side_str in ["LONG", "BUY_HEDGE"]) else -1.0
                s_bps = sign * ((executed_price - target_price) / target_price) * 10000.0

            cursor.execute("""
                INSERT INTO trade_logs (
                    symbol, market, side, order_qty, filled_qty,
                    expected_price, fill_price, slippage_bps,
                    market_impact_bps, adv_20d, volatility, timestamp, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(symbol), str(market), str(side), int(order_qty), int(filled_qty),
                float(target_price), float(executed_price), float(s_bps or 0.0),
                float(realized_impact_bps or 0.0), float(adv_20d or 0.0),
                float(volatility or 0.0), datetime.now().isoformat(), str(notes)
            ))
            conn.commit()
        finally:
            conn.close()

        # Online Recursive Kalman Filter Step
        try:
            h_k = float(realized_impact_bps) if (realized_impact_bps is not None and realized_impact_bps > 0) else None
            if h_k is None:
                if adv_20d is not None and adv_20d > 0 and order_qty > 0:
                    v = float(volatility) if (volatility is not None and volatility > 0) else 0.02
                    h_k = v * math.sqrt(min(1.0, float(order_qty) / float(adv_20d))) * 10000.0
                else:
                    h_k = 2.5
            baseline_defaults = {"KOSPI": 5.0, "KOSDAQ": 8.0, "SP500": 3.0, "NASDAQ": 4.0, "RUSSELL2000": 7.0}
            h_b = baseline_defaults.get(str(market).upper().strip(), self.default_slippage_bps)
            self.kalman_filter.update(float(s_bps or 0.0), h_k, h_b)
        except Exception as e_kf:
            logger.debug(f"[SlippageFeedbackEngine] Online Kalman step error: {e_kf}")

    def get_kalman_parameters(self) -> Dict[str, Any]:
        """Returns current Kalman filter parameters and diagnostics."""
        return self.kalman_filter.get_state()

    def reset_kalman_filter(self, initial_kappa: float = 0.50, initial_beta: float = 1.00) -> None:
        """Resets the Kalman filter state and covariance."""
        self.kalman_filter.reset(initial_kappa=initial_kappa, initial_beta=initial_beta)

    def get_summary(self) -> Dict[str, Any]:
        """Returns high-level summary of realized execution metrics and active market count."""
        metrics = self.calculate_realized_slippage()
        return {
            "total_executions": metrics.total_trades,
            "avg_slippage_bps": metrics.avg_slippage_bps,
            "cost_scaling_factor": metrics.cost_scaling_factor,
            "kalman_kappa": metrics.kalman_kappa,
            "kalman_beta": metrics.kalman_beta,
            "kalman_cost_scaling_factor": metrics.kalman_cost_scaling_factor,
            "markets": [m for m, v in metrics.market_slippage_map.items() if v > 0],
            "market_slippage_map": metrics.market_slippage_map,
        }


RealizedSlippageFeedback = SlippageFeedbackEngine
