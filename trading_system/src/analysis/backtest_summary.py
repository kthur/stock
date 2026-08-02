"""Phase 6-A & 6-B Automation Scripts:
- generate_backtest_summary(): computes REAL strategy performance metrics from the
  stored ensemble prediction history (realized 20d forward returns) and outputs
  backtest_summary.json for the GitHub Pages dashboard.
- No hardcoded numbers: when realized history is insufficient, the summary
  explicitly reports "insufficient_data" instead of fabricating metrics.
"""

import json
import logging
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Strategy display name -> score column stored in ensemble_predictions
STRATEGY_SCORE_COLS: List[tuple] = [
    ("Dynamic Ensemble", "ensemble_score"),
    ("XGBoost Regression", "reg_score"),
    ("Surge Classifier", "surge_score"),
    ("Lead-Lag Alpha", "ll_score"),
    ("VCP Rule Pattern", "vcp_rule_score"),
    ("VCP Pattern ML", "vcp_ml_score"),
    ("Strict Causal LSTM", "lstm_score"),
    ("Stat-Arb Cointegration", "stat_arb_score"),
    ("Sector Rotation Momentum", "sector_score"),
    ("RIM Intrinsic Valuation", "rim_score"),
    ("Event-Driven Catalyst", "event_score"),
    ("MQ Factor Quality", "mq_score"),
    ("Options IV Skew", "iv_skew_score"),
    ("Order Flow Imbalance", "order_flow_score"),
    ("Short-Term Reversal", "reversal_score"),
    ("ARM Factor", "arm_score"),
    ("CARD Factor", "card_score"),
    ("LATR Factor", "latr_score"),
    ("Inst & Foreign Sector", "inst_foreign_sector_score"),
]

_KST = timezone(timedelta(hours=9))
_TRADING_DAYS_PER_YEAR = 252


def _compute_strategy_metrics(daily_returns: pd.Series, horizon: int) -> Dict[str, Any]:
    """Compute annualized performance metrics from a series of `horizon`-day returns.

    Since each observation is a fixed-horizon (e.g. 20d) return, annualization uses
    the horizon as the compounding period: periods_per_year = 252 / horizon.
    """
    if daily_returns is None or len(daily_returns) == 0:
        return {}
    s = daily_returns.dropna()
    n = len(s)
    if n == 0:
        return {}

    periods_per_year = _TRADING_DAYS_PER_YEAR / max(horizon, 1)

    mean_period = float(s.mean())
    std_period = float(s.std(ddof=0))

    # Annualized return (geometric compounding of average period return)
    annualized_return = ((1.0 + mean_period) ** periods_per_year - 1.0) * 100.0

    # Annualized volatility
    annualized_vol = std_period * math.sqrt(periods_per_year)
    sharpe = (annualized_return / 100.0) / annualized_vol if annualized_vol > 1e-12 else 0.0

    # Win rate per rebalance period
    win_rate = float((s > 0).mean()) * 100.0

    # Max drawdown on the compounded equity curve
    equity = np.cumprod(1.0 + s.values)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = float(np.min(dd)) * 100.0 if len(dd) else 0.0

    return {
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd, 1),
        "win_rate_pct": round(win_rate, 1),
        "annualized_return_pct": round(annualized_return, 1),
        "samples": int(n),
    }


def compute_realized_backtest(history: pd.DataFrame, horizon: int = 20,
                              top_n: int = 10, min_days: int = 10) -> Dict[str, Any]:
    """Compute realized performance metrics from stored ensemble prediction history.

    Methodology (no look-ahead, fully honest):
    - Only rows with a realized ``outcome_return`` (filled by update_ensemble_outcomes
      once `horizon` trading days have elapsed) are used.
    - For each prediction date, the Top-N symbols by each strategy score form a
      hypothetical equal-weight portfolio; the portfolio's realized return for that
      date is the mean of the Top-N outcomes.
    - Metrics (Sharpe / MDD / WinRate / CAGR) are then computed across dates.
    """
    if history is None or history.empty:
        return {}

    df = history.copy()
    if 'outcome_return' not in df.columns or df['outcome_return'].isna().all():
        return {}

    df = df[df['outcome_return'].notna()].copy()
    if df.empty:
        return {}

    # Ensure scores are numeric
    for _, col in STRATEGY_SCORE_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    strategies: Dict[str, Any] = {}
    for display_name, score_col in STRATEGY_SCORE_COLS:
        if score_col not in df.columns:
            continue
        portfolio_series = []
        for dt, grp in df.groupby('date', sort=True):
            if len(grp) == 0:
                continue
            top = grp.nlargest(top_n, score_col)
            if top.empty or top['outcome_return'].isna().all():
                continue
            portfolio_series.append((dt, float(top['outcome_return'].mean())))
        if len(portfolio_series) < min_days:
            continue
        ser = pd.Series([v for _, v in portfolio_series],
                        index=pd.to_datetime([d for d, _ in portfolio_series]))
        metrics = _compute_strategy_metrics(ser, horizon)
        if metrics:
            strategies[display_name] = metrics

    if not strategies:
        return {}

    return {
        "strategies": strategies,
        "dates_used": int(len(df['date'].unique())),
        "symbols_used": int(df['symbol'].nunique()),
        "outcome_rows": int(len(df)),
        "horizon_days": horizon,
        "top_n": top_n,
    }


def generate_backtest_summary(
    result_dir: str = "trading_system/result",
    storage=None,
    history_days: int = 180,
    horizon: int = 20,
    top_n: int = 10,
    min_days: int = 10,
) -> Dict[str, Any]:
    """Generate backtest_summary.json from REAL realized prediction performance.

    Args:
        result_dir: Output directory for backtest_summary.json
        storage: MarketIndicatorStorage instance (with ensemble prediction history)
        history_days: How many days of prediction history to evaluate
        horizon: Prediction horizon (days) matching the stored outcome_return
        top_n: Portfolio size per prediction date for the hypothetical portfolio
        min_days: Minimum number of dated observations required per strategy

    Returns:
        Structured summary dict. When realized data is insufficient, the summary
        is marked ``insufficient_data: true`` with an explanatory note — never
        fabricated metrics.
    """
    res_dir = Path(result_dir)
    res_dir.mkdir(parents=True, exist_ok=True)
    summary_path = res_dir / "backtest_summary.json"

    now_kst = datetime.now(_KST).strftime("%Y-%m-%d %H:%M KST")
    summary: Dict[str, Any] = {
        "updated_at": now_kst,
        "source": "realized_predictions",
        "horizon_days": horizon,
        "top_n": top_n,
        "note": ("Metrics computed from realized forward returns of stored ensemble predictions. "
                 "Metrics accumulate over time as outcomes mature."),
    }

    history = None
    if storage is not None:
        try:
            history = storage.get_ensemble_predictions_history(days=history_days)
        except Exception as e:
            logger.warning(f"[6-A] Failed to load ensemble history: {e}")
            history = None

    if history is None or history.empty:
        summary["insufficient_data"] = True
        summary["note"] = ("No ensemble prediction history available yet. "
                           "Real metrics will appear once predictions have matured (20 trading days).")
    else:
        realized = compute_realized_backtest(history, horizon=horizon, top_n=top_n, min_days=min_days)
        if realized and realized.get("strategies"):
            summary["strategies"] = realized["strategies"]
            summary["dates_used"] = realized["dates_used"]
            summary["symbols_used"] = realized["symbols_used"]
            summary["outcome_rows"] = realized["outcome_rows"]
            summary["insufficient_data"] = False
        else:
            summary["insufficient_data"] = True
            summary["note"] = ("Not enough matured predictions yet (need >= {} dated observations "
                               "with realized outcomes). First usable metrics appear after {} trading "
                               "days of daily runs.").format(min_days, horizon)

    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info(f"[Phase 6-A] Saved real backtest summary to {summary_path}")
    except Exception as e:
        logger.error(f"[Phase 6-A] Failed to write backtest summary: {e}")

    return summary
