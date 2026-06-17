import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _safe_series(val):
    if isinstance(val, pd.DataFrame):
        return val.iloc[:, 0]
    return val


def detect_vcp(df: pd.DataFrame) -> Dict:
    """Volatility Contraction Pattern detection.

    VCP (Mark Minervini): narrowing daily ranges + declining volume
    before a potential breakout.

    Returns dict with pattern info or all-default if insufficient data.
    """
    if df is None or len(df) < 200:
        return {'is_vcp': False, 'vcp_score': 0.0, 'contraction_peaks': []}

    df = df.copy()
    high = _safe_series(df['High'])
    low = _safe_series(df['Low'])
    close = _safe_series(df['Close'])
    volume = _safe_series(df['Volume'])

    # 1. Daily range %
    df['range_pct'] = (high - low) / close * 100
    # 2. VCP contraction windows (T1..T5: narrower range = later contraction)
    windows = [5, 10, 20, 40, 60]
    ranges = []
    for w in windows:
        r = float(df['range_pct'].tail(w).max())
        ranges.append(r)

    # VCP: ranges should be decreasing (T5 > T4 > T3 > T2 > T1)
    decreasing = all(ranges[i] > ranges[i + 1] for i in range(len(ranges) - 1))

    # 3. Volume contraction
    vol_20d = float(volume.tail(20).mean())
    vol_60d = float(volume.tail(60).mean())
    volume_declining = vol_20d < vol_60d * 0.85

    # 4. Price above key MAs
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    last_close = float(close.iloc[-1])
    above_sma50 = last_close > float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else False
    above_sma200 = last_close > float(sma200.iloc[-1]) if not pd.isna(sma200.iloc[-1]) else False

    # 5. Current tightness (last 5d range)
    current_range = float(df['range_pct'].tail(5).max())

    # 6. Price near range high (tight + constructive)
    last_10d_high = float(high.tail(10).max())
    last_10d_low = float(low.tail(10).min())
    near_high = (last_close - last_10d_low) / (last_10d_high - last_10d_low + 1e-10) > 0.6

    # 7. Recent price action: positive return over last 5-10 days
    momentum_ok = float(close.tail(10).iloc[0]) < last_close

    score = 0.0
    if decreasing:
        score += 25.0
    if volume_declining:
        score += 15.0
    if above_sma50:
        score += 15.0
    if above_sma200:
        score += 15.0
    if near_high:
        score += 15.0
    if momentum_ok:
        score += 15.0

    # Tightness bonus
    if current_range < 4:
        score += 20.0
    elif current_range < 7:
        score += 12.0
    elif current_range < 10:
        score += 6.0

    score = min(score, 100.0)

    # VCP confirmed: strong contraction + constructive price action
    is_vcp = decreasing and above_sma50 and score >= 50

    return {
        'is_vcp': is_vcp,
        'vcp_score': score,
        'contraction_peaks': ranges,
        'current_range_pct': round(current_range, 2),
        'volume_declining': volume_declining,
        'above_sma50': above_sma50,
        'above_sma200': above_sma200,
        'near_high': near_high,
    }
