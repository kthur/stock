import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


def _safe_series(val):
    if isinstance(val, pd.DataFrame):
        return val.iloc[:, 0]
    return val


def _load_tuned_vcp_params() -> Dict[str, Any]:
    models_dir = Path(__file__).resolve().parent.parent.parent / "models"
    tuned_path = models_dir / "tuned_params.json"
    if tuned_path.exists():
        try:
            with open(tuned_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'vcp_detector' in data and isinstance(data['vcp_detector'], dict):
                return dict(data['vcp_detector'])
            if 'vcp_rule' in data and isinstance(data['vcp_rule'], dict):
                return dict(data['vcp_rule'])
        except Exception as e:
            logger.warning(f"Failed to load tuned params in vcp_detector: {e}")
    return {}


class VCPPatternDetector:
    """Class wrapper for VCP pattern detection with dynamic parameter loading."""

    def __init__(self, model_dir: Optional[str] = None):
        if model_dir is None:
            self.model_dir = Path(__file__).resolve().parent.parent.parent / "models"
        else:
            self.model_dir = Path(model_dir)

        self.params: Dict[str, Any] = {
            'contraction_ratio': 1.05,
            'near_high_cutoff': 0.60,
            'vol_declining_threshold': 0.85,
            'min_vcp_score': 50.0,
            'decreasing_weight': 25.0,
            'volume_weight': 15.0,
        }

        tuned_path = self.model_dir / "tuned_params.json"
        if tuned_path.exists():
            try:
                with open(tuned_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                vcp_p = data.get('vcp_detector') or data.get('vcp_rule')
                if vcp_p:
                    self.params.update(vcp_p)
                    logger.info(f"VCPPatternDetector dynamically loaded tuned params: {vcp_p}")
            except Exception as e:
                logger.warning(f"VCPPatternDetector failed to load tuned params: {e}")

    def detect(self, df: pd.DataFrame) -> Dict[str, Any]:
        return detect_vcp(df, params=self.params)


def detect_vcp(df: pd.DataFrame, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Volatility Contraction Pattern detection.

    VCP (Mark Minervini): narrowing daily ranges + declining volume
    before a potential breakout.

    Returns dict with pattern info or all-default if insufficient data.
    """
    pivot_price = 0.0
    if df is not None and not df.empty:
        h_col = [c for c in df.columns if str(c).lower() == 'high']
        if h_col:
            h_s = _safe_series(df[h_col[0]])
            pivot_price = float(h_s.iloc[-20:].max()) if len(h_s) >= 20 else float(h_s.iloc[-1])

    if df is None or len(df) < 50:
        return {'is_vcp': False, 'vcp_score': 0.0, 'pivot_price': round(pivot_price, 2), 'contraction_peaks': []}



    if params is None:
        params = _load_tuned_vcp_params()

    contraction_ratio = params.get('contraction_ratio', 1.05)
    near_high_cutoff = params.get('near_high_cutoff', 0.60)
    vol_declining_threshold = params.get('vol_declining_threshold', 0.85)
    min_vcp_score = params.get('min_vcp_score', 50.0)
    decreasing_weight = params.get('decreasing_weight', 25.0)
    volume_weight = params.get('volume_weight', 15.0)

    df = df.copy()
    # Standardize column casing to capitalize (e.g. close -> Close, volume -> Volume)
    df.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in df.columns]

    high = _safe_series(df['High'])
    low = _safe_series(df['Low'])
    close = _safe_series(df['Close'])
    volume = _safe_series(df['Volume'])

    # 1. Daily range %
    df['range_pct'] = (high - low) / (close + 1e-10) * 100
    # 2. VCP contraction steps on non-overlapping windows
    # Slice 1: [-5:], Slice 2: [-15:-5], Slice 3: [-35:-15], Slice 4: [-60:-35]
    n = len(df)
    r1 = float(df['range_pct'].iloc[-min(5, n):].max())
    r2 = float(df['range_pct'].iloc[-min(15, n):-min(5, n)].max()) if n > 5 else r1
    r3 = float(df['range_pct'].iloc[-min(35, n):-min(15, n)].max()) if n > 15 else r2
    r4 = float(df['range_pct'].iloc[-min(60, n):-min(35, n)].max()) if n > 35 else r3

    ranges = [r1, r2, r3, r4]

    # Contraction: recent ranges are tighter than earlier ranges (strict non-expanding)
    eff_ratio = float(contraction_ratio)
    decreasing = (r1 <= r2 * eff_ratio) and (r2 <= r3 * eff_ratio) and (r1 < r4)

    # 3. Volume contraction
    vol_20d = float(volume.tail(20).mean())
    vol_60d = float(volume.tail(60).mean())
    volume_declining = vol_20d < vol_60d * vol_declining_threshold

    # 4. Price above key MAs
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    last_close = float(close.iloc[-1])
    above_sma50 = last_close > float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else False
    above_sma200 = last_close > float(sma200.iloc[-1]) if not pd.isna(sma200.iloc[-1]) else False

    # 5. Current tightness (last 5d range)
    current_range = float(df['range_pct'].tail(5).max())

    # 6. Price near range high (tight + constructive) & near 52-week high (257 trading days)
    last_10d_high = float(high.tail(10).max())
    last_10d_low = float(low.tail(10).min())
    near_high_10d = (last_close - last_10d_low) / (last_10d_high - last_10d_low + 1e-10) > near_high_cutoff

    high_52w = float(high.tail(min(len(high), 257)).max())
    near_52w_high = (last_close / (high_52w + 1e-10)) >= 0.75

    near_high = near_high_10d and near_52w_high

    # 7. Recent price action: positive return over last 5-10 days
    momentum_ok = float(close.tail(10).iloc[0]) < last_close

    score = 0.0
    if decreasing:
        score += decreasing_weight
    if volume_declining:
        score += volume_weight
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
    is_vcp = decreasing and above_sma50 and score >= min_vcp_score

    pivot_price = float(high.iloc[-20:].max()) if len(high) >= 20 else float(high.iloc[-1])

    return {
        'is_vcp': is_vcp,
        'vcp_score': score,
        'pivot_price': round(pivot_price, 2),
        'contraction_peaks': ranges,
        'current_range_pct': round(current_range, 2),
        'volume_declining': volume_declining,
        'above_sma50': above_sma50,
        'above_sma200': above_sma200,
        'near_high': near_high,
    }

