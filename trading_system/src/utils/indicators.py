from typing import List


def calc_sma(closes: List[float], period: int) -> List[float]:
    """단순이동평균(SMA) 계산 (슬라이딩 윈도우, O(n))"""
    if not closes or period is None or period < 1:
        return []
    n = len(closes)
    sma = [0.0] * n
    for i in range(n):
        start = max(0, i - period + 1)
        window = closes[start : i + 1]
        sma[i] = sum(window) / len(window)
    return sma


def calc_ema_list(data: List[float], period: int) -> List[float]:
    """지수이동평균(EMA) 계산. 반환 리스트는 입력과 동일 길이."""
    period = max(1, period)
    n = len(data)
    if n == 0:
        return []
    if n < period:
        avg = sum(data) / n
        return [avg] * n

    k = 2.0 / (period + 1)
    ema = [0.0] * n
    ema[period - 1] = sum(data[:period]) / period
    for i in range(period, n):
        ema[i] = data[i] * k + ema[i - 1] * (1 - k)
    for i in range(period - 1):
        ema[i] = ema[period - 1]
    return ema


def calc_ema(data: List[float], period: int) -> float:
    """지수이동평균(EMA) 최종값만 반환."""
    period = max(1, period)
    n = len(data)
    if n == 0:
        return 0.0
    if n < period:
        return sum(data) / n

    k = 2.0 / (period + 1)
    ema = sum(data[:period]) / period
    for i in range(period, n):
        ema = data[i] * k + ema * (1 - k)
    return ema


def calc_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> float:
    """MACD 히스토그램 값 반환."""
    if len(closes) < slow + signal:
        return 0.0
    ema_fast = calc_ema_list(closes, fast)
    ema_slow = calc_ema_list(closes, slow)
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
    signal_line = calc_ema_list(macd_line, signal)
    return macd_line[-1] - signal_line[-1]


def calc_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Average True Range (ATR) 계산."""
    if len(closes) < period + 1:
        return 0.0
    true_ranges = []
    for i in range(max(1, len(closes) - period), len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)
    return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0


def calc_rsi_list(closes: List[float], window: int = 14) -> List[float]:
    """RSI 리스트 반환 (입력과 동일 길이, Wilder smoothing)."""
    window = max(1, window)
    n = len(closes)
    if n <= window:
        return [50.0] * n
    rsi = [50.0] * n
    deltas = [closes[i] - closes[i - 1] for i in range(1, n)]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [abs(d) if d < 0 else 0.0 for d in deltas]
    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window
    if avg_loss == 0:
        rsi[window] = 100.0
    else:
        rsi[window] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    for i in range(window + 1, n):
        delta_idx = i - 1
        avg_gain = (avg_gain * (window - 1) + gains[delta_idx]) / window
        avg_loss = (avg_loss * (window - 1) + losses[delta_idx]) / window
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rsi[i] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    return rsi


def calc_rsi(closes: List[float], window: int = 14) -> float:
    """현재 RSI 값 계산 (Wilder 방식)."""
    if len(closes) <= window:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [abs(d) if d < 0 else 0.0 for d in deltas]
    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window
    for i in range(window, len(deltas)):
        avg_gain = (avg_gain * (window - 1) + gains[i]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i]) / window
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
