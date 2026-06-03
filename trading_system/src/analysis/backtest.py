"""Backtesting Engine - 전략 백테스트"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Callable
import logging
import itertools
import math

logger = logging.getLogger(__name__)


@dataclass
class PriceBar:
    """가격 바 (OHLCV)"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class BacktestTrade:
    """백테스트 거래"""
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    quantity: int
    pnl: float
    pnl_pct: float
    direction: str = "LONG"
    exit_reason: str = "SIGNAL"   # SIGNAL, TRAILING_STOP, FINAL
    duration: timedelta = field(default_factory=lambda: timedelta())
    
    def __post_init__(self):
        self.duration = self.exit_date - self.entry_date


@dataclass
class BacktestResult:
    """백테스트 결과"""
    symbol: str
    trades: List[BacktestTrade]
    total_return: float
    total_return_pct: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    total_fees: float
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    equity_curve: List[float] = None
    price_curve: List[float] = None
    dates: List[datetime] = None
    trailing_stop_count: int = 0


class BacktestEngine:
    
    POSITION_SIZE_FRACTION = 0.95
    
    def __init__(self, initial_capital: float = 1000000):
        self.initial_capital = initial_capital
        self.logger = logger
        self.fee_pct = 0.001  # 0.1% 수수료
        self._indicator_cache = {}
        self._current_price_bars = None
        self._closes_cache = None
        self._volumes_cache = None
        
    # ──────────────────────────────────────────────────────
    # 기술적 지표 유틸리티
    # ──────────────────────────────────────────────────────
    
    @staticmethod
    def _calc_ema(data: List[float], period: int) -> List[float]:
        """지수이동평균(EMA) 계산. 반환 리스트는 입력과 동일 길이(앞부분은 SMA로 시작)."""
        if len(data) < period:
            return [sum(data) / len(data)] * len(data)
        
        k = 2.0 / (period + 1)
        ema_values = [0.0] * len(data)
        # 최초 EMA 값은 첫 period 구간의 SMA
        ema_values[period - 1] = sum(data[:period]) / period
        for i in range(period, len(data)):
            ema_values[i] = data[i] * k + ema_values[i - 1] * (1 - k)
        # period 이전 구간도 SMA로 채움 (참조용)
        sma_init = ema_values[period - 1]
        for i in range(period - 1):
            ema_values[i] = sma_init
        return ema_values
    
    @staticmethod
    def _calc_atr(bars: List['PriceBar'], period: int = 14) -> float:
        """Average True Range (ATR) 계산. 최근 period 바 기준."""
        if len(bars) < 2:
            return 0.0
        
        true_ranges = []
        start = max(1, len(bars) - period)
        for i in range(start, len(bars)):
            high = bars[i].high
            low = bars[i].low
            prev_close = bars[i - 1].close
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)
        
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
        
    @staticmethod
    def _calc_rsi(closes: List[float], window: int = 14) -> List[float]:
        """Wilder's RSI (EMA 기반) 계산. closes 길이만큼의 리스트 반환."""
        if len(closes) <= window:
            return [50.0] * len(closes)
        
        rsi_values = [50.0] * len(closes)
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        gains = [d if d > 0 else 0.0 for d in deltas]
        losses = [abs(d) if d < 0 else 0.0 for d in deltas]
        
        # 첫 번째 값은 단순 이동평균(SMA)
        avg_gain = sum(gains[:window]) / window
        avg_loss = sum(losses[:window]) / window
        
        if avg_loss == 0:
            rsi_values[window] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_values[window] = 100.0 - (100.0 / (1.0 + rs))
            
        # 이후 값은 Wilder의 smoothing (EMA 방식)
        for i in range(window + 1, len(closes)):
            delta_idx = i - 1
            current_gain = gains[delta_idx]
            current_loss = losses[delta_idx]
            
            avg_gain = (avg_gain * (window - 1) + current_gain) / window
            avg_loss = (avg_loss * (window - 1) + current_loss) / window
            
            if avg_loss == 0:
                rsi_values[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i] = 100.0 - (100.0 / (1.0 + rs))
                
        return rsi_values

    def _get_closes(self) -> List[float]:
        if self._closes_cache is None:
            if self._current_price_bars is not None:
                self._closes_cache = [b.close for b in self._current_price_bars]
            else:
                return []
        return self._closes_cache

    def _get_volumes(self) -> List[float]:
        if self._volumes_cache is None:
            if self._current_price_bars is not None:
                self._volumes_cache = [b.volume for b in self._current_price_bars]
            else:
                return []
        return self._volumes_cache

    def _get_sma(self, window: int) -> List[float]:
        cache_key = ("SMA", window)
        if cache_key not in self._indicator_cache:
            closes = self._get_closes()
            sma = [0.0] * len(closes)
            if len(closes) >= window:
                running_sum = sum(closes[:window])
                sma[window-1] = running_sum / window
                for idx in range(window, len(closes)):
                    running_sum = running_sum + closes[idx] - closes[idx-window]
                    sma[idx] = running_sum / window
                # Fill warm-up
                for idx in range(window-1):
                    sma[idx] = sum(closes[:idx+1]) / (idx+1)
            else:
                for idx in range(len(closes)):
                    sma[idx] = sum(closes[:idx+1]) / (idx+1)
            self._indicator_cache[cache_key] = sma
        return self._indicator_cache[cache_key]

    def _get_ema(self, data: List[float], period: int) -> List[float]:
        cache_key = ("EMA", period, id(data))
        if cache_key not in self._indicator_cache:
            self._indicator_cache[cache_key] = self._calc_ema(data, period)
        return self._indicator_cache[cache_key]

    def _get_rsi(self, window: int) -> List[float]:
        cache_key = ("RSI", window)
        if cache_key not in self._indicator_cache:
            closes = self._get_closes()
            self._indicator_cache[cache_key] = self._calc_rsi(closes, window)
        return self._indicator_cache[cache_key]

    def _get_macd_hist(self, fast: int, slow: int, signal: int) -> List[float]:
        cache_key = ("MACD_HIST", fast, slow, signal)
        if cache_key not in self._indicator_cache:
            closes = self._get_closes()
            ema_fast = self._get_ema(closes, fast)
            ema_slow = self._get_ema(closes, slow)
            macd_line = [ema_fast[k] - ema_slow[k] for k in range(len(closes))]
            signal_line = self._get_ema(macd_line, signal)
            hist = [macd_line[k] - signal_line[k] for k in range(len(closes))]
            self._indicator_cache[cache_key] = hist
        return self._indicator_cache[cache_key]

    def _get_rolling_max(self, window: int) -> List[float]:
        cache_key = ("ROLLING_MAX", window)
        if cache_key not in self._indicator_cache:
            closes = self._get_closes()
            r_max = [0.0] * len(closes)
            for idx in range(len(closes)):
                start = max(0, idx - window + 1)
                r_max[idx] = max(closes[start:idx+1])
            self._indicator_cache[cache_key] = r_max
        return self._indicator_cache[cache_key]

    def _get_rolling_mean_volume(self, window: int) -> List[float]:
        cache_key = ("ROLLING_MEAN_VOL", window)
        if cache_key not in self._indicator_cache:
            vols = self._get_volumes()
            r_mean = [0.0] * len(vols)
            if len(vols) >= window:
                running_sum = sum(vols[:window])
                r_mean[window-1] = running_sum / window
                for idx in range(window, len(vols)):
                    running_sum = running_sum + vols[idx] - vols[idx-window]
                    r_mean[idx] = running_sum / window
                for idx in range(window-1):
                    r_mean[idx] = sum(vols[:idx+1]) / (idx+1)
            else:
                for idx in range(len(vols)):
                    r_mean[idx] = sum(vols[:idx+1]) / (idx+1)
            self._indicator_cache[cache_key] = r_mean
        return self._indicator_cache[cache_key]

    def _get_rolling_volatility(self, window: int) -> List[float]:
        cache_key = ("ROLLING_VOLATILITY", window)
        if cache_key not in self._indicator_cache:
            closes = self._get_closes()
            vol = [0.0] * len(closes)
            for idx in range(len(closes)):
                start = max(0, idx - window + 1)
                sub = closes[start:idx+1]
                diffs = [abs(sub[k] - sub[k-1]) for k in range(1, len(sub))]
                vol[idx] = sum(diffs) / len(diffs) if diffs else 0.0
            self._indicator_cache[cache_key] = vol
        return self._indicator_cache[cache_key]

    def _get_bollinger_bands(self, period: int, std_mult: float) -> Tuple[List[float], List[float]]:
        cache_key = ("BOLLINGER_BANDS", period, std_mult)
        if cache_key not in self._indicator_cache:
            closes = self._get_closes()
            upper = [0.0] * len(closes)
            lower = [0.0] * len(closes)
            for idx in range(len(closes)):
                start = max(0, idx - period + 1)
                sub = closes[start:idx+1]
                sma = sum(sub) / len(sub)
                variance = sum((c - sma) ** 2 for c in sub) / len(sub)
                std_dev = variance ** 0.5
                upper[idx] = sma + std_mult * std_dev
                lower[idx] = sma - std_mult * std_dev
            self._indicator_cache[cache_key] = (upper, lower)
        return self._indicator_cache[cache_key]

    # ──────────────────────────────────────────────────────
    # 메인 백테스트 루프
    # ──────────────────────────────────────────────────────
    
    def run_backtest(self, symbol: str, price_bars: List[PriceBar],
                    strategy_func, target_period_bars: int = None,
                    allow_short: bool = False,
                    trailing_stop_pct: float = 0.0,
                    scale_in: bool = False,
                    stop_loss_pct: float = 0.0,
                    take_profit_pct: float = 0.0,
                    market_regime_filter: bool = False,
                    volatility_sizing: bool = False) -> BacktestResult:
        """
        백테스트 실행
        
        Args:
            symbol: 종목
            price_bars: 가격 바 데이터
            strategy_func: 전략 함수 (가격->신호)
            target_period_bars: 성능 측정 대상 기간 바 수 (과거 데이터는 warm-up 용)
            allow_short: 공매도(Short Selling) 허용 여부
            trailing_stop_pct: 트레일링 스톱 비율 (0이면 비활성, 예: 0.05 = 5%)
            scale_in: 분할 진입 (True: 50%→50% 2단계 진입)
            stop_loss_pct: 고정 손절 비율 (0이면 비활성, 예: 0.05 = 5%)
            take_profit_pct: 부분 익절 비율 (0이면 비활성, 예: 0.10 = 10% 도달 시 50% 익절)
        
        Returns:
            BacktestResult: 백테스트 결과
        """
        self._current_price_bars = price_bars
        self._indicator_cache = {}
        self._closes_cache = None
        self._volumes_cache = None

        capital = self.initial_capital
        position = 0  # 양수: 롱 포지션 수량, 음수: 숏 포지션 수량
        entry_price = 0.0
        entry_timestamp = None  # 진입 시점 별도 추적
        trades: List[BacktestTrade] = []
        equity_curve = [capital]
        trailing_stop_count = 0
        
        # 트레일링 스톱 추적 변수
        trailing_peak = 0.0   # 롱: 보유 중 최고가
        trailing_trough = float('inf')  # 숏: 보유 중 최저가
        
        # 분할 진입 추적 변수
        scale_in_done = False  # 2차 진입 완료 여부
        first_entry_qty = 0   # 1차 진입 수량
        
        # 부분 익절 추적 변수
        has_partial_tp = False  # 50% 분할 익절 여부
        
        # 다음 봉 시가 진입을 위한 신호 대기 변수
        pending_signal = "HOLD"
        
        for i, bar in enumerate(price_bars):
            # ── 1단계: 이전 봉에서 넘어온 pending_signal 매매 실행 (현재 봉 시가 bar.open 기준) ──
            size_fraction = (self.POSITION_SIZE_FRACTION / 2) if scale_in else self.POSITION_SIZE_FRACTION
            
            if pending_signal == "BUY" and position == 0:
                if capital >= bar.open:
                    if volatility_sizing:
                        atr = self._calc_atr(price_bars[:i], 14)
                        if atr > 0:
                            risk_amount = capital * 0.02
                            qty = int(risk_amount / (2 * atr))
                            max_qty = int(capital * size_fraction / bar.open)
                            position = min(qty, max_qty)
                            if position <= 0:
                                position = max_qty
                        else:
                            position = int(capital * size_fraction / bar.open)
                    else:
                        position = int(capital * size_fraction / bar.open)
                    
                    entry_price = bar.open
                    entry_timestamp = bar.timestamp
                    capital -= position * bar.open * (1 + self.fee_pct)
                    trailing_peak = bar.open
                    scale_in_done = False
                    first_entry_qty = position
                    has_partial_tp = False
                    self.logger.debug(f"{bar.timestamp}: BUY (Long Entry @ Open) {position} @ {bar.open}")
                pending_signal = "HOLD"
                
            elif pending_signal == "SELL" and position > 0:
                exit_price = bar.open
                pnl = (exit_price - entry_price) * position
                fees = position * exit_price * self.fee_pct
                capital += position * exit_price * (1 - self.fee_pct)
                
                trade = BacktestTrade(
                    entry_date=entry_timestamp or bar.timestamp,
                    entry_price=entry_price,
                    exit_date=bar.timestamp,
                    exit_price=exit_price,
                    quantity=position,
                    pnl=pnl - fees,
                    pnl_pct=((exit_price - entry_price) / entry_price) * 100,
                    direction="LONG",
                    exit_reason="SIGNAL"
                )
                trades.append(trade)
                self.logger.debug(f"{bar.timestamp}: SELL (Long Exit @ Open) {position} @ {exit_price}, PnL={pnl-fees:.2f}")
                
                if allow_short:
                    if volatility_sizing:
                        atr = self._calc_atr(price_bars[:i], 14)
                        if atr > 0:
                            risk_amount = capital * 0.02
                            qty = int(risk_amount / (2 * atr))
                            max_qty = int(capital * size_fraction / bar.open)
                            qty = min(qty, max_qty)
                            if qty <= 0:
                                qty = max_qty
                        else:
                            qty = int(capital * size_fraction / bar.open)
                    else:
                        qty = int(capital * size_fraction / bar.open)
                        
                    position = -qty
                    entry_price = bar.open
                    entry_timestamp = bar.timestamp
                    capital += qty * bar.open * (1 - self.fee_pct)
                    trailing_trough = bar.open
                    scale_in_done = False
                    first_entry_qty = qty
                    has_partial_tp = False
                    self.logger.debug(f"{bar.timestamp}: SELL (Short Entry @ Open - Reverse) {qty} @ {bar.open}")
                else:
                    position = 0
                    scale_in_done = False
                pending_signal = "HOLD"
                
            elif pending_signal == "BUY" and position < 0 and allow_short:
                exit_price = bar.open
                qty = abs(position)
                pnl = (entry_price - exit_price) * qty
                fees = qty * exit_price * self.fee_pct
                capital -= qty * exit_price * (1 + self.fee_pct)
                
                trade = BacktestTrade(
                    entry_date=entry_timestamp or bar.timestamp,
                    entry_price=entry_price,
                    exit_date=bar.timestamp,
                    exit_price=exit_price,
                    quantity=-qty,
                    pnl=pnl - fees,
                    pnl_pct=((entry_price - exit_price) / entry_price) * 100,
                    direction="SHORT",
                    exit_reason="SIGNAL"
                )
                trades.append(trade)
                self.logger.debug(f"{bar.timestamp}: BUY (Short Cover @ Open) {qty} @ {exit_price}, PnL={pnl-fees:.2f}")
                
                if capital >= bar.open:
                    if volatility_sizing:
                        atr = self._calc_atr(price_bars[:i], 14)
                        if atr > 0:
                            risk_amount = capital * 0.02
                            qty = int(risk_amount / (2 * atr))
                            max_qty = int(capital * size_fraction / bar.open)
                            position = min(qty, max_qty)
                            if position <= 0:
                                position = max_qty
                        else:
                            position = int(capital * size_fraction / bar.open)
                    else:
                        position = int(capital * size_fraction / bar.open)
                        
                    entry_price = bar.open
                    entry_timestamp = bar.timestamp
                    capital -= position * bar.open * (1 + self.fee_pct)
                    trailing_peak = bar.open
                    scale_in_done = False
                    first_entry_qty = position
                    has_partial_tp = False
                    self.logger.debug(f"{bar.timestamp}: BUY (Long Entry @ Open - Reverse) {position} @ {bar.open}")
                else:
                    position = 0
                    scale_in_done = False
                pending_signal = "HOLD"
                
            elif pending_signal == "SELL" and position == 0 and allow_short:
                if volatility_sizing:
                    atr = self._calc_atr(price_bars[:i], 14)
                    if atr > 0:
                        risk_amount = capital * 0.02
                        qty = int(risk_amount / (2 * atr))
                        max_qty = int(capital * size_fraction / bar.open)
                        qty = min(qty, max_qty)
                        if qty <= 0:
                            qty = max_qty
                    else:
                        qty = int(capital * size_fraction / bar.open)
                else:
                    qty = int(capital * size_fraction / bar.open)
                    
                position = -qty
                entry_price = bar.open
                entry_timestamp = bar.timestamp
                capital += qty * bar.open * (1 - self.fee_pct)
                trailing_trough = bar.open
                scale_in_done = False
                first_entry_qty = qty
                has_partial_tp = False
                self.logger.debug(f"{bar.timestamp}: SELL (Short Entry @ Open) {qty} @ {bar.open}")
                pending_signal = "HOLD"
                
            # ── 2단계: 장중 실시간 익절/손절/트레일링 스톱 검사 ──
            if position != 0:
                # (A) 부분 익절 검사
                if take_profit_pct > 0.0 and not has_partial_tp:
                    if position > 0:
                        tp_trigger = entry_price * (1 + take_profit_pct)
                        if bar.high >= tp_trigger:
                            tp_qty = position // 2
                            if tp_qty > 0:
                                exit_price = max(bar.open, tp_trigger)
                                pnl = (exit_price - entry_price) * tp_qty
                                fees = tp_qty * exit_price * self.fee_pct
                                capital += tp_qty * exit_price * (1 - self.fee_pct)
                                
                                trade = BacktestTrade(
                                    entry_date=entry_timestamp or bar.timestamp,
                                    entry_price=entry_price,
                                    exit_date=bar.timestamp,
                                    exit_price=exit_price,
                                    quantity=tp_qty,
                                    pnl=pnl - fees,
                                    pnl_pct=((exit_price - entry_price) / entry_price) * 100,
                                    direction="LONG",
                                    exit_reason="PARTIAL_TAKE_PROFIT"
                                )
                                trades.append(trade)
                                position -= tp_qty
                                has_partial_tp = True
                                self.logger.debug(f"{bar.timestamp}: PARTIAL TP (Long) {tp_qty} @ {exit_price}")
                    elif position < 0:
                        tp_trigger = entry_price * (1 - take_profit_pct)
                        if bar.low <= tp_trigger:
                            qty = abs(position)
                            tp_qty = qty // 2
                            if tp_qty > 0:
                                exit_price = min(bar.open, tp_trigger)
                                pnl = (entry_price - exit_price) * tp_qty
                                fees = tp_qty * exit_price * self.fee_pct
                                capital -= tp_qty * exit_price * (1 + self.fee_pct)
                                
                                trade = BacktestTrade(
                                    entry_date=entry_timestamp or bar.timestamp,
                                    entry_price=entry_price,
                                    exit_date=bar.timestamp,
                                    exit_price=exit_price,
                                    quantity=-tp_qty,
                                    pnl=pnl - fees,
                                    pnl_pct=((entry_price - exit_price) / entry_price) * 100,
                                    direction="SHORT",
                                    exit_reason="PARTIAL_TAKE_PROFIT"
                                )
                                trades.append(trade)
                                position += tp_qty
                                has_partial_tp = True
                                self.logger.debug(f"{bar.timestamp}: PARTIAL TP (Short) {tp_qty} @ {exit_price}")

                # (B) 고정 손절 및 트레일링 스톱 검사
                if position > 0:
                    trailing_peak = max(trailing_peak, bar.high)
                    sl_trigger = entry_price * (1 - stop_loss_pct) if stop_loss_pct > 0.0 else 0.0
                    ts_trigger = trailing_peak * (1 - trailing_stop_pct) if trailing_stop_pct > 0.0 else 0.0
                    
                    trigger_price = max(sl_trigger, ts_trigger)
                    if trigger_price > 0.0 and bar.low <= trigger_price:
                        exit_price = min(bar.open, trigger_price)
                        pnl = (exit_price - entry_price) * position
                        fees = position * exit_price * self.fee_pct
                        capital += position * exit_price * (1 - self.fee_pct)
                        
                        reason = "STOP_LOSS" if trigger_price == sl_trigger else "TRAILING_STOP"
                        trade = BacktestTrade(
                            entry_date=entry_timestamp or bar.timestamp,
                            entry_price=entry_price,
                            exit_date=bar.timestamp,
                            exit_price=exit_price,
                            quantity=position,
                            pnl=pnl - fees,
                            pnl_pct=((exit_price - entry_price) / entry_price) * 100,
                            direction="LONG",
                            exit_reason=reason
                        )
                        trades.append(trade)
                        self.logger.debug(f"{bar.timestamp}: {reason} (Long) {position} @ {exit_price}, peak={trailing_peak:.2f}")
                        position = 0
                        scale_in_done = False
                        has_partial_tp = False
                        if reason == "TRAILING_STOP":
                            trailing_stop_count += 1
                        equity_curve.append(capital)
                        continue
                        
                elif position < 0:
                    trailing_trough = min(trailing_trough, bar.low)
                    sl_trigger = entry_price * (1 + stop_loss_pct) if stop_loss_pct > 0.0 else float('inf')
                    ts_trigger = trailing_trough * (1 + trailing_stop_pct) if trailing_stop_pct > 0.0 else float('inf')
                    
                    trigger_price = min(sl_trigger, ts_trigger)
                    if trigger_price < float('inf') and bar.high >= trigger_price:
                        exit_price = max(bar.open, trigger_price)
                        qty = abs(position)
                        pnl = (entry_price - exit_price) * qty
                        fees = qty * exit_price * self.fee_pct
                        capital -= qty * exit_price * (1 + self.fee_pct)
                        
                        reason = "STOP_LOSS" if trigger_price == sl_trigger else "TRAILING_STOP"
                        trade = BacktestTrade(
                            entry_date=entry_timestamp or bar.timestamp,
                            entry_price=entry_price,
                            exit_date=bar.timestamp,
                            exit_price=exit_price,
                            quantity=-qty,
                            pnl=pnl - fees,
                            pnl_pct=((entry_price - exit_price) / entry_price) * 100,
                            direction="SHORT",
                            exit_reason=reason
                        )
                        trades.append(trade)
                        self.logger.debug(f"{bar.timestamp}: {reason} (Short) {qty} @ {exit_price}, trough={trailing_trough:.2f}")
                        position = 0
                        scale_in_done = False
                        has_partial_tp = False
                        if reason == "TRAILING_STOP":
                            trailing_stop_count += 1
                        equity_curve.append(capital)
                        continue
            
            # ── 3단계: 분할 진입 (Scale-In) ──
            if scale_in and position > 0 and not scale_in_done:
                if bar.close > entry_price * 1.02 and capital >= bar.close:
                    add_qty = int(capital * size_fraction / bar.close)
                    if add_qty > 0:
                        total_cost = entry_price * first_entry_qty + bar.close * add_qty
                        position += add_qty
                        entry_price = total_cost / position
                        capital -= add_qty * bar.close * (1 + self.fee_pct)
                        scale_in_done = True
                        self.logger.debug(f"{bar.timestamp}: SCALE-IN (Long) +{add_qty} @ {bar.close}, avg={entry_price:.2f}")
            
            elif scale_in and position < 0 and not scale_in_done:
                if bar.close < entry_price * 0.98 and capital > 0:
                    add_qty = int(capital * size_fraction / bar.close)
                    if add_qty > 0:
                        old_qty = abs(position)
                        total_cost = entry_price * old_qty + bar.close * add_qty
                        position -= add_qty
                        entry_price = total_cost / abs(position)
                        capital += add_qty * bar.close * (1 - self.fee_pct)
                        scale_in_done = True
                        self.logger.debug(f"{bar.timestamp}: SCALE-IN (Short) +{add_qty} @ {bar.close}, avg={entry_price:.2f}")
            
            # ── 4단계: 전략 신호 계산 (봉 마감 시그널 -> 다음 봉 시가 매매 진입 예약) ──
            pending_signal = strategy_func(price_bars[:i+1])
            if market_regime_filter and pending_signal == "BUY":
                if i < 199:
                    pending_signal = "HOLD"
                else:
                    ema200 = self._get_ema(self._get_closes(), 200)
                    if price_bars[i].close < ema200[i]:
                        pending_signal = "HOLD"
            
            # 포지션 가치 계산 및 누적
            position_value = position * bar.close
            total_value = capital + position_value
            equity_curve.append(total_value)
            
        # 최종 청산 (남은 포지션 강제 종가 정리)
        if position > 0:
            final_price = price_bars[-1].close
            pnl = (final_price - entry_price) * position
            fees = position * final_price * self.fee_pct
            capital += position * final_price * (1 - self.fee_pct)
            
            trade = BacktestTrade(
                entry_date=entry_timestamp or price_bars[-1].timestamp,
                entry_price=entry_price,
                exit_date=price_bars[-1].timestamp,
                exit_price=final_price,
                quantity=position,
                pnl=pnl - fees,
                pnl_pct=((final_price - entry_price) / entry_price) * 100,
                direction="LONG",
                exit_reason="FINAL"
            )
            trades.append(trade)
        elif position < 0 and allow_short:
            final_price = price_bars[-1].close
            qty = abs(position)
            pnl = (entry_price - final_price) * qty
            fees = qty * final_price * self.fee_pct
            capital -= qty * final_price * (1 + self.fee_pct)
            
            trade = BacktestTrade(
                entry_date=entry_timestamp or price_bars[-1].timestamp,
                entry_price=entry_price,
                exit_date=price_bars[-1].timestamp,
                exit_price=final_price,
                quantity=-qty,
                pnl=pnl - fees,
                pnl_pct=((entry_price - final_price) / entry_price) * 100,
                direction="SHORT",
                exit_reason="FINAL"
            )
            trades.append(trade)
            
        # 결과 계산
        if target_period_bars and target_period_bars < len(price_bars):
            target_start_idx = len(price_bars) - target_period_bars
            initial_capital_target = equity_curve[target_start_idx - 1] if target_start_idx > 0 else equity_curve[0]
            final_capital_target = equity_curve[-1]
            total_return = final_capital_target - initial_capital_target
            total_return_pct = (total_return / initial_capital_target) * 100
            
            target_trades = []
            for t in trades:
                if t.exit_date >= price_bars[target_start_idx].timestamp:
                    target_trades.append(t)
                    
            win_rate = self._calculate_win_rate(target_trades)
            profit_factor = self._calculate_profit_factor(target_trades)
            
            target_equity_curve = equity_curve[target_start_idx:]
            max_drawdown = self._calculate_max_drawdown(target_equity_curve)
            sharpe_ratio = self._calculate_sharpe_ratio(target_equity_curve)
            
            dates = [b.timestamp for b in price_bars[target_start_idx:]]
            price_curve = [b.close for b in price_bars[target_start_idx:]]
            
            result = BacktestResult(
                symbol=symbol,
                trades=target_trades,
                total_return=total_return,
                total_return_pct=total_return_pct,
                win_rate=win_rate,
                profit_factor=profit_factor,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                total_fees=0.0,
                start_date=price_bars[target_start_idx].timestamp,
                end_date=price_bars[-1].timestamp,
                initial_capital=initial_capital_target,
                final_capital=final_capital_target,
                equity_curve=target_equity_curve,
                price_curve=price_curve,
                dates=dates,
                trailing_stop_count=trailing_stop_count
            )
        else:
            final_capital = capital
            total_return = final_capital - self.initial_capital
            total_return_pct = (total_return / self.initial_capital) * 100
            
            win_rate = self._calculate_win_rate(trades)
            profit_factor = self._calculate_profit_factor(trades)
            max_drawdown = self._calculate_max_drawdown(equity_curve)
            sharpe_ratio = self._calculate_sharpe_ratio(equity_curve)
            
            total_fees = sum(
                (abs(trade.quantity) * trade.entry_price * self.fee_pct +
                 abs(trade.quantity) * trade.exit_price * self.fee_pct)
                for trade in trades
            )
            
            result = BacktestResult(
                symbol=symbol,
                trades=trades,
                total_return=total_return,
                total_return_pct=total_return_pct,
                win_rate=win_rate,
                profit_factor=profit_factor,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                total_fees=total_fees,
                start_date=price_bars[0].timestamp,
                end_date=price_bars[-1].timestamp,
                initial_capital=self.initial_capital,
                final_capital=final_capital,
                equity_curve=equity_curve,
                price_curve=[b.close for b in price_bars],
                dates=[b.timestamp for b in price_bars],
                trailing_stop_count=trailing_stop_count
            )
        
        self.logger.info(f"Backtest completed for {symbol}: "
                        f"return={total_return_pct:.2f}%, "
                        f"trades={len(trades)}, "
                        f"win_rate={win_rate:.2%}, "
                        f"trailing_stops={trailing_stop_count}")
        
        return result
    
    def _calculate_win_rate(self, trades: List[BacktestTrade]) -> float:
        """승률 계산"""
        if not trades:
            return 0
        
        winning_trades = sum(1 for t in trades if t.pnl > 0)
        return winning_trades / len(trades)
    
    def _calculate_profit_factor(self, trades: List[BacktestTrade]) -> float:
        """이익 계수 계산"""
        if not trades:
            return 0
        
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl <= 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0
        
        return gross_profit / gross_loss
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """최대 낙폭 계산"""
        if not equity_curve:
            return 0
        
        peak = equity_curve[0]
        max_dd = 0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_sharpe_ratio(self, equity_curve: List[float], risk_free_rate: float = 0.02) -> float:
        """Sharpe Ratio 계산"""
        if len(equity_curve) < 2:
            return 0
        
        returns = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1] 
                  for i in range(1, len(equity_curve))]
        
        if not returns:
            return 0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0
        
        # 연율화 (252 거래일 기준)
        sharpe = ((avg_return - risk_free_rate / 252) / std_dev) * (252 ** 0.5)
        
        return sharpe
    
    def optimize_parameters(self, symbol: str, price_bars: List[PriceBar],
                           param_ranges: Dict) -> Dict:
        """파라미터 최적화"""
        best_result = None
        best_params = None
        best_return = -float('inf')
        
        self.logger.info("Starting parameter optimization...")
        
        # 간단한 그리드 서치
        for param_combo in self._generate_param_combos(param_ranges):
            def strategy(bars):
                # 파라미터 기반 전략 실행
                return self._simple_ma_strategy(bars, param_combo)
            
            result = self.run_backtest(symbol, price_bars, strategy)
            
            if result.total_return_pct > best_return:
                best_return = result.total_return_pct
                best_result = result
                best_params = param_combo
        
        self.logger.info(f"Optimization complete: best params={best_params}, "
                        f"best return={best_return:.2f}%")
        
        return {
            'best_params': best_params,
            'best_result': best_result,
            'best_return': best_return
        }
    
    def _generate_param_combos(self, param_ranges: Dict) -> List[Dict]:
        """파라미터 조합 생성"""
        keys = param_ranges.keys()
        values = [param_ranges[k] for k in keys]
        
        combos = []
        for combo in itertools.product(*values):
            combos.append(dict(zip(keys, combo)))
        
        return combos
    
    # ──────────────────────────────────────────────────────
    # 전략 함수들
    # ──────────────────────────────────────────────────────
    
    def _simple_ma_strategy(self, bars: List[PriceBar], params: Dict) -> str:
        """간단한 이동평균 전략"""
        short_window = params.get('short_window', 20)
        long_window = params.get('long_window', 50)
        
        if len(bars) < long_window:
            return "HOLD"
            
        L = len(bars)
        short_ma = self._get_sma(short_window)
        long_ma = self._get_sma(long_window)
        
        if short_ma[L-1] > long_ma[L-1]:
            return "BUY"
        elif short_ma[L-1] < long_ma[L-1]:
            return "SELL"
        else:
            return "HOLD"

    def _rsi_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """RSI 과매도/과매수 전략"""
        if params is None: params = {}
        window = params.get('window', 14)
        buy_threshold = params.get('buy_threshold', 30)
        sell_threshold = params.get('sell_threshold', 70)
        
        if len(bars) <= window:
            return "HOLD"
            
        L = len(bars)
        rsi_list = self._get_rsi(window)
        rsi = rsi_list[L-1]
            
        if rsi < buy_threshold:
            return "BUY"
        elif rsi > sell_threshold:
            return "SELL"
        else:
            return "HOLD"
            
    def _macd_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """MACD 전략 (진짜 EMA 기반: EMA12/EMA26/Signal9)"""
        if params is None: params = {}
        fast = params.get('fast', 12)
        slow = params.get('slow', 26)
        signal_period = params.get('signal', 9)
        
        if len(bars) <= slow + signal_period:
            return "HOLD"
            
        L = len(bars)
        hist = self._get_macd_hist(fast, slow, signal_period)
        
        curr_hist = hist[L-1]
        prev_hist = hist[L-2]
        
        # 히스토그램이 음→양 전환: 매수 (골든크로스)
        if prev_hist < 0 and curr_hist > 0:
            return "BUY"
        # 히스토그램이 양→음 전환: 매도 (데드크로스)
        elif prev_hist > 0 and curr_hist < 0:
            return "SELL"
        else:
            return "HOLD"
            
    def _buffett_proxy_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """워렌 버핏 Proxy (가치투자/역발상): 200일선 아래 크게 하락하고 단기 과매도 시 매수"""
        if len(bars) < 200: return "HOLD"
        L = len(bars)
        closes = self._get_closes()
        current_price = closes[L-1]
        ma200 = self._get_sma(200)
        rsi = self._get_rsi(14)
        
        if current_price < ma200[L-1] * 0.9 and rsi[L-1] < 30:
            return "BUY"
        elif current_price > ma200[L-1] or rsi[L-1] > 70:
            return "SELL"
        return "HOLD"
        
    def _lynch_proxy_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """피터 린치 Proxy (성장/모멘텀): 50일 신고가 및 평균 거래량 돌파 시 매수"""
        if len(bars) < 50: return "HOLD"
        L = len(bars)
        closes = self._get_closes()
        current_price = closes[L-1]
        
        highest_50 = self._get_rolling_max(50)
        avg_vol = self._get_rolling_mean_volume(49)
        vols = self._get_volumes()
        current_vol = vols[L-1]
        
        if current_price > highest_50[L-2] and current_vol > avg_vol[L-2] * 1.5:
            return "BUY"
        elif current_price < self._get_sma(20)[L-1]:
            return "SELL"
        return "HOLD"
        
    def _dalio_proxy_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """레이 달리오 Proxy (안정적 추세): 200일선 위에서 변동성이 적을 때 매수"""
        if len(bars) < 200: return "HOLD"
        L = len(bars)
        closes = self._get_closes()
        current_price = closes[L-1]
        ma200 = self._get_sma(200)
        
        vol_ratio = self._get_rolling_volatility(20)[L-1] / self._get_sma(20)[L-1]
        
        if current_price > ma200[L-1] and vol_ratio < 0.02:
            return "BUY"
        elif current_price < ma200[L-1]:
            return "SELL"
        return "HOLD"

    def _trend_following_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """추세 추종(Trend Following): 가격이 200일선 위에 있고 단기 이평(20일)이 중기 이평(50일) 위에 있을 때 매수"""
        if len(bars) < 200: return "HOLD"
        L = len(bars)
        closes = self._get_closes()
        current_price = closes[L-1]
        ma200 = self._get_sma(200)
        ma50 = self._get_sma(50)
        ma20 = self._get_sma(20)
        
        if current_price > ma200[L-1] and ma20[L-1] > ma50[L-1]:
            return "BUY"
        elif current_price < ma200[L-1] or ma20[L-1] < ma50[L-1]:
            return "SELL"
        return "HOLD"
    
    # ──────────────────────────────────────────────────────
    # 신규 전략들
    # ──────────────────────────────────────────────────────
    
    def _bollinger_band_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """볼린저밴드 + RSI 복합 전략 (Mean Reversion)
        
        하단 밴드 터치 + RSI 과매도 → BUY
        상단 밴드 터치 + RSI 과매수 → SELL
        횡보장/박스권에서 높은 수익률을 기대할 수 있음
        """
        if params is None: params = {}
        bb_period = params.get('bb_period', 20)
        bb_std_mult = params.get('bb_std_mult', 2.0)
        rsi_window = params.get('rsi_window', 14)
        
        if len(bars) < max(bb_period, rsi_window) + 1:
            return "HOLD"
        
        L = len(bars)
        closes = self._get_closes()
        current_price = closes[L-1]
        
        upper_band, lower_band = self._get_bollinger_bands(bb_period, bb_std_mult)
        rsi = self._get_rsi(rsi_window)
        
        if current_price <= lower_band[L-1] and rsi[L-1] < 35:
            return "BUY"
        elif current_price >= upper_band[L-1] and rsi[L-1] > 65:
            return "SELL"
        else:
            return "HOLD"
    
    def _ensemble_strategy(self, bars: List[PriceBar], params: Dict = None) -> str:
        """복합(앙상블) 전략: MA + RSI + MACD 3개 지표 투표
        
        2개 이상 BUY → BUY
        2개 이상 SELL → SELL
        그 외 → HOLD
        
        단일 지표 의존을 탈피하여 거짓 신호(whipsaw)를 필터링함
        """
        # 각 전략의 개별 신호 수집
        ma_signal = self._simple_ma_strategy(bars, {'short_window': 20, 'long_window': 50})
        rsi_signal = self._rsi_strategy(bars, {'window': 14, 'buy_threshold': 35, 'sell_threshold': 65})
        macd_signal = self._macd_strategy(bars, {})
        
        votes = [ma_signal, rsi_signal, macd_signal]
        
        buy_votes = sum(1 for v in votes if v == "BUY")
        sell_votes = sum(1 for v in votes if v == "SELL")
        
        if buy_votes >= 2:
            return "BUY"
        elif sell_votes >= 2:
            return "SELL"
        else:
            return "HOLD"
    
    # ──────────────────────────────────────────────────────
    # 전략 레지스트리
    # ──────────────────────────────────────────────────────
            
    def get_strategy_func(self, strategy_name: str) -> Callable:
        """이름으로 전략 함수 래퍼 반환"""
        name = strategy_name.upper()
        
        if name == "MA" or name == "이동평균선":
            return lambda bars: self._simple_ma_strategy(bars, {})
        elif name == "RSI":
            return lambda bars: self._rsi_strategy(bars, {})
        elif name == "MACD":
            return lambda bars: self._macd_strategy(bars, {})
        elif name == "TREND" or "추세" in strategy_name:
            return lambda bars: self._trend_following_strategy(bars, {})
        elif name == "BUFFETT" or "버핏" in strategy_name:
            return lambda bars: self._buffett_proxy_strategy(bars, {})
        elif name == "LYNCH" or "린치" in strategy_name:
            return lambda bars: self._lynch_proxy_strategy(bars, {})
        elif name == "DALIO" or "달리오" in strategy_name:
            return lambda bars: self._dalio_proxy_strategy(bars, {})
        elif name == "BOLLINGER" or "볼린저" in strategy_name:
            return lambda bars: self._bollinger_band_strategy(bars, {})
        elif name == "ENSEMBLE" or "앙상블" in strategy_name or "복합" in strategy_name:
            return lambda bars: self._ensemble_strategy(bars, {})
        else:
            self.logger.warning(f"Unknown strategy: {name}. Falling back to MA.")
            return lambda bars: self._simple_ma_strategy(bars, {})
