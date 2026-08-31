"""
Closed-Loop Realized Slippage Execution Feedback Engine
Calculates real vs theoretical slippage from trade_logs.db and dynamically updates
microstructure cost parameters in the ensemble scoring engine.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Union, List, Any

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
    total_trades: int = 0
    mean_slippage_bps: float = 5.0
    max_slippage_bps: float = 15.0
    recommended_market_impact_multiplier: float = 1.0


class SlippageFeedbackEngine:
    """
    Queries execution trade logs and computes real vs theoretical slippage metrics,
    returning cost adjustments to tune microstructure cost modeling.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None, default_slippage_bps: float = 5.0):
        import math
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
            safe_slip = float(default_slippage_bps) if (default_slippage_bps is not None and math.isfinite(float(default_slippage_bps))) else 5.0
        except (ValueError, TypeError):
            safe_slip = 5.0
        self.default_slippage_bps = max(0.0, min(1000.0, safe_slip))

    def calculate_realized_slippage(self, *args, **kwargs) -> SlippageMetrics:
        """Reads trade_logs.db and returns realized slippage metrics in basis points (bps)."""
        if not Path(self.db_path).exists():
            return SlippageMetrics(
                avg_slippage_bps=self.default_slippage_bps,
                market_impact_alpha=0.50,
                sample_count=0,
                cost_scaling_factor=1.0,
                total_trades=0,
                mean_slippage_bps=self.default_slippage_bps,
                max_slippage_bps=15.0,
                recommended_market_impact_multiplier=1.0,
            )

        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            try:
                cursor = conn.cursor()

                # Check if order_plans / execution_logs or trade_logs exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cursor.fetchall()]

                slippages = []
                mkt_slippage: dict[str, list[float]] = {
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
                    import math
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
                                if mkt in mkt_slippage:
                                    mkt_slippage[mkt].append(slip_bps)

                elif "executions" in tables and "orders" in tables:
                    cursor.execute("PRAGMA table_info(orders)")
                    ord_cols = {r[1] for r in cursor.fetchall()}
                    type_col = "order_type" if "order_type" in ord_cols else ("side" if "side" in ord_cols else "order_type")
                    cursor.execute(f"""
                        SELECT o.symbol, o.{type_col}, o.price, e.price
                        FROM executions e
                        JOIN orders o ON e.order_id = o.order_id
                        WHERE e.price IS NOT NULL AND o.price > 0
                    """)
                    rows = cursor.fetchall()
                    import math
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
                                if mkt in mkt_slippage:
                                    mkt_slippage[mkt].append(slip_bps)

                elif "trade_logs" in tables:
                    import math
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
                                if mkt in mkt_slippage:
                                    mkt_slippage[mkt].append(slip_bps)
            finally:
                conn.close()

            valid_slippages = [s for s in slippages if math.isfinite(s)]

            if not valid_slippages:
                return SlippageMetrics(
                    avg_slippage_bps=self.default_slippage_bps,
                    market_impact_alpha=0.50,
                    sample_count=0,
                    cost_scaling_factor=1.0,
                    total_trades=0,
                    mean_slippage_bps=self.default_slippage_bps,
                    max_slippage_bps=15.0,
                    recommended_market_impact_multiplier=1.0,
                )

            # Robust estimation: Hard-clip extreme outliers (e.g. > 500 bps data artifacts) and apply MAD
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
            avg_slip = float(np.clip(avg_slip, -50.0, 100.0)) if (avg_slip is not None and math.isfinite(avg_slip)) else self.default_slippage_bps
            max_slip = float(np.clip(max_slip, -100.0, 500.0)) if (max_slip is not None and math.isfinite(max_slip)) else 15.0

            # V7-22: Dynamic slippage scaling cap up to 8.0x for illiquid micro-cap protection
            max_scale_cap = 8.0
            scaling = float(np.clip(avg_slip / self.default_slippage_bps, 0.5, max_scale_cap)) if self.default_slippage_bps > 0 else 1.0
            if not math.isfinite(scaling):
                scaling = 1.0
            # Square-root market impact power exponent alpha = 0.50 (Almgren-Chriss / Kyle standard)
            # Level scaling is handled via cost_scaling_factor to avoid double counting
            alpha = 0.50

            final_mkt_map = {}
            for mkt, val_list in mkt_slippage.items():
                v_finite = [v for v in val_list if math.isfinite(v)]
                if v_finite:
                    m_val = float(np.mean(v_finite))
                    final_mkt_map[mkt] = float(np.clip(m_val, 0.1, 100.0)) if math.isfinite(m_val) else self.default_slippage_bps
                else:
                    baseline_defaults = {"KOSPI": 5.0, "KOSDAQ": 8.0, "SP500": 3.0, "NASDAQ": 4.0, "RUSSELL2000": 7.0}
                    final_mkt_map[mkt] = baseline_defaults.get(mkt, self.default_slippage_bps)

            return SlippageMetrics(
                avg_slippage_bps=avg_slip,
                market_impact_alpha=alpha,
                sample_count=len(valid_slippages),
                cost_scaling_factor=scaling,
                market_slippage_map=final_mkt_map,
                total_trades=len(valid_slippages),
                mean_slippage_bps=avg_slip,
                max_slippage_bps=max_slip,
                recommended_market_impact_multiplier=scaling,
            )

        except Exception as e:
            logger.error(f"Error calculating realized slippage: {e}")
            return SlippageMetrics(
                avg_slippage_bps=self.default_slippage_bps,
                market_impact_alpha=0.50,
                sample_count=0,
                cost_scaling_factor=1.0,
            )

    def analyze_realized_slippage(self) -> SlippageMetrics:
        return self.calculate_realized_slippage()


RealizedSlippageFeedback = SlippageFeedbackEngine
