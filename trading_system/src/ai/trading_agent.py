import logging
import sqlite3
import datetime
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import TradingConfig
from src.broker.real_broker import BrokerBase
from src.risk.risk_manager import RiskManager, CrisisLevel
from src.utils.notifier import NotificationSystem
from src.data_layer.trade_journal import TradeJournal, TradeRecord
from src.ai.news_sentiment_fetcher import NewsSentimentFetcher

logger = logging.getLogger(__name__)

# ─── 거래비용 상수 ──────────────────────────────────────────────────────────────
# 한국 주식 기준 (실제 환경에 맞게 조정 가능)
BUY_COMMISSION_RATE  = 0.00015  # 매수 수수료 0.015%
BUY_SLIPPAGE_RATE    = 0.002    # 매수 슬리피지 0.2%
SELL_COMMISSION_RATE = 0.00015  # 매도 수수료 0.015%
SELL_TAX_RATE        = 0.0023   # 증권거래세 0.23% (KOSPI/KOSDAQ)
SELL_SLIPPAGE_RATE   = 0.002    # 매도 슬리피지 0.2%

# 매수 실효 비용 배율 (진입 가격에 곱함)
BUY_EFFECTIVE_RATE  = 1.0 + BUY_COMMISSION_RATE  + BUY_SLIPPAGE_RATE
# 매도 실효 수익 배율 (청산 가격에 곱함)
SELL_EFFECTIVE_RATE = 1.0 - SELL_COMMISSION_RATE - SELL_TAX_RATE - SELL_SLIPPAGE_RATE

# 위기 단계별 단일 거래 최대 리스크 한도 (총 자본 대비 %)
CRISIS_RISK_CAP = {
    CrisisLevel.NONE:   0.020,  # 2.0%
    CrisisLevel.WATCH:  0.015,  # 1.5%
    CrisisLevel.ACTIVE: 0.010,  # 1.0%
    CrisisLevel.SEVERE: 0.000,  # 신규 매수 차단
}

# ATR 기반 트레일링 스탑 — 가격 이력 조회 기간
ATR_LOOKBACK_DAYS = 14

# 포트폴리오 상관관계 평가 기간 (영업일 기준)
CORRELATION_LOOKBACK_DAYS = 60

# 상관계수 임계값 (이 값 초과 시 비중 절반 축소, 0.85 초과 시 진입 차단)
CORRELATION_THRESHOLD_HALVE  = 0.70
CORRELATION_THRESHOLD_BLOCK  = 0.85


class TradingAgent:
    """고도화된 자율 주식 거래 에이전트

    [핵심 운영 규칙]
    Rule 1 — 위기 단계 연동 동적 리스크 한도 (2%→1.5%→1%→0%)
    Rule 2 — 뉴스 감성 + VIX 거시지표 데이터 처리
    Rule 3 — 통계적 우위(Win-Rate ≥ 55%, Edge > 0) 검증
    Rule 4 — 매매 전 판단 근거 보고서 출력 의무
    Rule 5 — 시장 변동성 5% 초과 시 비상 청산 프로토콜

    [고도화 퀀트 기능]
    Q1 — ATR 기반 동적 트레일링 스탑 (고정 -5% 대체)
    Q2 — 포트폴리오 상관관계 분산 검사 (Pearson ≥ 0.85 진입 차단)
    Q3 — 위기 단계별 동적 리스크 캡 (CRISIS_RISK_CAP 테이블)
    Q4 — 슬리피지 및 세금을 반영한 Net PnL 계산
    """

    def __init__(
        self,
        config: TradingConfig,
        broker: BrokerBase,
        risk_manager: RiskManager,
        notifier: NotificationSystem,
        trade_journal: Optional[TradeJournal] = None,
        news_fetcher: Optional[NewsSentimentFetcher] = None
    ):
        self.config = config
        self.broker = broker
        self.risk_manager = risk_manager
        self.notifier = notifier
        self.trade_journal = trade_journal or TradeJournal(
            db_path=str(Path(config.db_path).parent / "trade_logs.db")
        )
        self.news_fetcher = news_fetcher or NewsSentimentFetcher()

    # ───────────────────────────────────────────────────────────────
    # 메인 트레이딩 사이클
    # ───────────────────────────────────────────────────────────────

    async def run_trading_cycle(self):
        """1회 트레이딩 사이클 실행 (비상대응 → 포지션 관리 → 신규 매수)"""
        logger.info("Starting autonomous trading cycle...")

        # Rule 5: 비상 대응 프로토콜
        if await self._emergency_protocol():
            logger.warning("Emergency protocol active. Cycle aborted after liquidation.")
            return

        # Q1: ATR 기반 트레일링 스탑을 포함한 포지션 관리
        await self._manage_existing_positions()

        # Rules 1–4 + Q2–Q4: 신규 매수 시그널 처리
        await self._process_new_signals()

        logger.info("Autonomous trading cycle completed.")

    # ───────────────────────────────────────────────────────────────
    # Rule 5: 비상 대응 프로토콜
    # ───────────────────────────────────────────────────────────────

    async def _emergency_protocol(self) -> bool:
        """Rule 5: 당일 주가 변동성 5% 이상 시 모든 미체결 주문을 취소하고 전량 청산"""
        try:
            conn = sqlite3.connect(self.config.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, change_pct
                FROM global_indicators
                WHERE date = (SELECT MAX(date) FROM global_indicators)
            """)
            indicators = {row['symbol']: row['change_pct'] for row in cursor.fetchall()}
            conn.close()

            trigger_indexes = []
            for idx_sym in ['^KS11', '^KQ11', '^GSPC', 'KOSPI', 'KOSDAQ', 'SP500']:
                if idx_sym in indicators:
                    change = abs(indicators[idx_sym])
                    val = change if change < 1.0 else change / 100.0
                    if val >= 0.05:
                        trigger_indexes.append(f"{idx_sym} ({val*100:.1f}%)")

            if trigger_indexes:
                msg = f"🚨 비상대응 발동: 시장 변동성 5% 초과 감지 - {', '.join(trigger_indexes)}"
                logger.warning(msg)
                await self.notifier.broadcast("EMERGENCY SIGNAL", msg)
                await self._liquidate_all_positions("시장 변동성 5% 초과 비상 대응")
                return True

            return False
        except Exception as e:
            logger.error(f"Error in emergency protocol: {e}")
            return False

    async def _liquidate_all_positions(self, reason: str):
        """보유 중인 모든 포지션 즉시 매도 (Q4: Net PnL 반영)"""
        logger.warning(f"Liquidating all positions. Reason: {reason}")

        if hasattr(self.broker, "cancel_all_orders"):
            try:
                self.broker.cancel_all_orders()
            except Exception as e:
                logger.warning(f"Failed to call broker.cancel_all_orders(): {e}")

        positions = self.trade_journal.get_active_positions()
        for symbol, pos in positions.items():
            qty = pos['qty']
            if qty <= 0:
                continue
            try:
                curr_price = self._get_current_price(symbol)
                avg_price  = pos['avg_price']

                # Q4: 세금 및 슬리피지 반영 Net PnL
                net_sell_proceeds = curr_price * SELL_EFFECTIVE_RATE * qty
                net_buy_cost      = avg_price  * BUY_EFFECTIVE_RATE  * qty
                pnl = net_sell_proceeds - net_buy_cost

                self.broker.submit_order(symbol, qty, "SELL")

                trade = TradeRecord(
                    timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    symbol=symbol,
                    side="SELL",
                    quantity=qty,
                    price=curr_price,
                    reason=reason,
                    pnl=pnl,
                    status="EXECUTED"
                )
                self.trade_journal.log_trade(trade)

                report = self._generate_trade_report(
                    symbol=symbol, qty=qty, price=curr_price, signal_type="SELL",
                    sentiment=0.0, vix=0.0, edge=0.0, decision="EXECUTE",
                    reason=f"🚨 비상 청산: {reason}", net_pnl=pnl
                )
                await self.notifier.broadcast("EMERGENCY LIQUIDATION", report)
            except Exception as e:
                logger.error(f"Failed to liquidate {symbol}: {e}")

    # ───────────────────────────────────────────────────────────────
    # 포지션 관리 — Q1 ATR 트레일링 스탑
    # ───────────────────────────────────────────────────────────────

    async def _manage_existing_positions(self):
        """Q1: ATR 기반 동적 트레일링 스탑으로 기존 포지션 관리"""
        positions = self.trade_journal.get_active_positions()
        if not positions:
            logger.info("No active positions to manage.")
            return

        for symbol, pos in positions.items():
            try:
                qty       = pos['qty']
                avg_price = pos['avg_price']
                curr_price = self._get_current_price(symbol)

                # Q1: ATR 계산 (14일 True Range 평균)
                atr = self._calculate_atr(symbol, lookback=ATR_LOOKBACK_DAYS)

                # 진입 이후 최고가 추적
                highest_price = self._get_highest_price_since_entry(symbol, avg_price)

                trigger_sell = False
                reason = ""

                # 고정 Take-Profit은 ATR 유무와 무관하게 항상 먼저 체크
                tp = pos.get('take_profit')
                if tp and curr_price >= tp:
                    trigger_sell = True
                    reason = f"Take-Profit triggered (TP={tp:.2f}, Curr={curr_price:.2f})"

                if not trigger_sell:
                    if atr > 0:
                        # Q1: ATR 기반 트레일링 스탑 (동적 손절) — risk_manager의 고급 로직 활용
                        trailing_hit = self.risk_manager.check_trailing_stop_signal(
                            symbol=symbol,
                            current_price=curr_price,
                            highest_price=highest_price,
                            atr=atr,
                            regime="weak_bull",  # 향후 레짐 감지 연동 가능
                        )
                        if trailing_hit:
                            trigger_sell = True
                            reason = (
                                f"ATR Trailing Stop (ATR={atr:.2f}, "
                                f"Peak={highest_price:.2f}, Curr={curr_price:.2f})"
                            )
                    else:
                        # ATR 계산 불가 시 고정 손절 폴백
                        sl = pos.get('stop_loss')
                        if sl and curr_price <= sl:
                            trigger_sell = True
                            reason = f"Stop-Loss triggered (SL={sl:.2f}, Curr={curr_price:.2f})"

                if trigger_sell:
                    # Q4: Net PnL 계산
                    net_sell_proceeds = curr_price * SELL_EFFECTIVE_RATE * qty
                    net_buy_cost      = avg_price  * BUY_EFFECTIVE_RATE  * qty
                    pnl = net_sell_proceeds - net_buy_cost

                    self.broker.submit_order(symbol, qty, "SELL")

                    trade = TradeRecord(
                        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        symbol=symbol,
                        side="SELL",
                        quantity=qty,
                        price=curr_price,
                        reason=reason,
                        pnl=pnl,
                        status="EXECUTED"
                    )
                    self.trade_journal.log_trade(trade)

                    report = self._generate_trade_report(
                        symbol=symbol, qty=qty, price=curr_price, signal_type="SELL",
                        sentiment=0.0, vix=0.0, edge=0.0, decision="EXECUTE",
                        reason=reason, net_pnl=pnl
                    )
                    await self.notifier.broadcast("POSITION EXIT", report)

            except Exception as e:
                logger.error(f"Error managing position for {symbol}: {e}")

    # ───────────────────────────────────────────────────────────────
    # 신규 매수 시그널 처리 — Rules 2, 3, 1, 4 + Q2, Q3, Q4
    # ───────────────────────────────────────────────────────────────

    async def _process_new_signals(self):
        """신규 매수 시그널 검증 및 거래 실행"""
        try:
            conn = sqlite3.connect(self.config.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.*, u.name, u.market
                FROM ensemble_predictions e
                LEFT JOIN stock_universe u ON e.symbol = u.symbol
                WHERE e.date = (SELECT MAX(date) FROM ensemble_predictions)
                ORDER BY e.ensemble_score DESC
                LIMIT 10
            """)
            candidates = [dict(row) for row in cursor.fetchall()]
            conn.close()

            if not candidates:
                logger.info("No ensemble candidates found for today.")
                return

            balance     = self.broker.get_balance()
            cash        = balance.get('cash', 0.0)
            total_value = balance.get('total_value', 100_000_000.0)

            vix_val = self._get_vix_index()

            # Q3: 위기 단계를 먼저 평가하여 이번 사이클 전체에 적용
            crisis_level = self.risk_manager.evaluate_crisis(vix=vix_val or 20.0)
            if crisis_level == CrisisLevel.SEVERE:
                logger.warning("Crisis level SEVERE: all new buys blocked.")
                return

            # Q2: 현재 보유 종목 목록 (상관관계 비교용)
            active_positions = self.trade_journal.get_active_positions()

            for cand in candidates:
                symbol          = cand['symbol']
                name            = cand.get('name')
                market          = cand.get('market', 'KOSPI')
                score           = cand['ensemble_score']
                expected_return = cand['ensemble_expected_return']

                if score < 0.65:
                    continue

                curr_price = self._get_current_price(symbol)

                # Rule 2: 뉴스 감성 + VIX 체크
                sentiment = self.news_fetcher.fetch_and_analyze(symbol, name, market)
                if sentiment < -0.2:
                    logger.info(f"Skipping {symbol}: negative sentiment ({sentiment:.2f})")
                    continue
                if vix_val and vix_val > 30.0:
                    logger.info(f"Skipping {symbol}: VIX too high ({vix_val:.2f})")
                    continue

                # Rule 3: 통계적 우위 검증
                total_trades = self.trade_journal.get_total_trades()
                if total_trades < 5:
                    win_rate       = 0.58
                    win_loss_ratio = 1.6
                else:
                    win_rate       = self.trade_journal.get_win_rate()
                    win_loss_ratio = self.trade_journal.get_win_loss_ratio()

                edge = (win_rate * win_loss_ratio) - (1 - win_rate)
                if not self._check_statistical_edge(win_rate, edge):
                    logger.info(
                        f"Skipping {symbol}: no statistical edge "
                        f"(WinRate={win_rate:.2%}, Edge={edge:.4f})"
                    )
                    continue

                # Q3: 위기 단계별 동적 리스크 한도
                max_risk_pct = CRISIS_RISK_CAP.get(crisis_level, 0.02)
                if max_risk_pct <= 0:
                    logger.info(f"Skipping {symbol}: crisis-level risk cap is 0")
                    continue

                # 손절 / 익절 라인 (ATR 기반 우선, 없으면 고정 비율)
                atr = self._calculate_atr(symbol, lookback=ATR_LOOKBACK_DAYS)
                if atr > 0:
                    stop_price   = self.risk_manager.calculate_atr_based_stop(curr_price, atr)
                    target_price = self.risk_manager.calculate_atr_based_target(curr_price, atr)
                else:
                    stop_price   = curr_price * (1 - self.risk_manager.default_stop_loss_pct)
                    target_price = curr_price * (1 + self.risk_manager.default_take_profit_pct)

                # Kelly Criterion 기반 포지션 비중
                kelly_fraction = self.risk_manager.calculate_kelly_fraction(win_rate, win_loss_ratio)
                if kelly_fraction <= 0:
                    kelly_fraction = 0.05

                target_alloc_value = total_value * kelly_fraction
                qty = int(target_alloc_value / curr_price)

                # Q2: 포트폴리오 상관관계 분산 검사
                corr_action = self._check_portfolio_correlation(
                    symbol, active_positions
                )
                if corr_action == "BLOCK":
                    logger.info(
                        f"Skipping {symbol}: too highly correlated with existing positions"
                    )
                    continue
                elif corr_action == "HALVE":
                    qty = max(1, qty // 2)
                    logger.info(
                        f"{symbol}: high correlation detected — position halved to {qty}"
                    )

                # Rule 1 (Q3 강화): 동적 리스크 한도 적용 수량 검증
                qty = self._validate_risk_limit(
                    symbol, qty, curr_price, stop_price, total_value,
                    risk_pct_override=max_risk_pct
                )
                if qty <= 0:
                    logger.info(f"Skipping {symbol}: dynamic risk limit → qty=0")
                    continue

                # 현금 잔고 초과 방지
                if qty * curr_price > cash:
                    qty = int(cash / curr_price)
                    if qty <= 0:
                        logger.info(f"Skipping {symbol}: insufficient cash")
                        continue

                # Rule 4: 보고서 생성 및 방송
                reason = (
                    f"Ensemble Score: {score:.2f}, "
                    f"Expected Return: {expected_return:.2%}, "
                    f"Crisis: {crisis_level.value}, "
                    f"Risk Cap: {max_risk_pct:.1%}"
                )
                report = self._generate_trade_report(
                    symbol=symbol, qty=qty, price=curr_price, signal_type="BUY",
                    sentiment=sentiment, vix=vix_val or 0.0, edge=edge,
                    decision="EXECUTE", reason=reason,
                    crisis_level=crisis_level.value
                )
                await self.notifier.broadcast("BUY DECISION REPORT", report)

                # 주문 실행
                self.broker.submit_order(symbol, qty, "BUY")

                # 거래 기록 (Q4: 실효 매수 비용 반영)
                effective_buy_price = curr_price * BUY_EFFECTIVE_RATE
                trade = TradeRecord(
                    timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    symbol=symbol,
                    side="BUY",
                    quantity=qty,
                    price=effective_buy_price,   # 수수료+슬리피지 반영 실효가
                    reason=reason,
                    ensemble_score=score,
                    sentiment_score=sentiment,
                    regime="BULL" if (vix_val or 0.0) < 20.0 else "VOLATILE",
                    stop_loss=stop_price,
                    take_profit=target_price,
                    status="EXECUTED"
                )
                self.trade_journal.log_trade(trade)
                cash -= qty * curr_price

        except Exception as e:
            logger.error(f"Error processing new buy signals: {e}")

    # ───────────────────────────────────────────────────────────────
    # 핵심 헬퍼 메서드
    # ───────────────────────────────────────────────────────────────

    def _validate_risk_limit(
        self,
        symbol: str,
        qty: int,
        price: float,
        stop_price: float,
        total_capital: float,
        risk_pct_override: Optional[float] = None
    ) -> int:
        """Q3 + Rule 1: 위기 단계를 반영한 동적 리스크 한도로 수량 재산출"""
        risk_pct     = risk_pct_override if risk_pct_override is not None \
                       else self.risk_manager.max_loss_per_trade_pct
        max_risk     = total_capital * risk_pct
        per_share_risk = price - stop_price

        if per_share_risk <= 0:
            return qty

        max_qty_allowed = int(max_risk / per_share_risk)
        if qty > max_qty_allowed:
            logger.info(
                f"Risk rule [{risk_pct:.1%}] triggered for {symbol}: "
                f"qty {qty} → {max_qty_allowed}"
            )
            return max_qty_allowed
        return qty

    def _check_statistical_edge(self, win_rate: float, edge: float) -> bool:
        """Rule 3: 승률 ≥ 55% 및 Edge > 0인 경우에만 거래 허용"""
        return win_rate >= 0.55 and edge > 0.0

    def _check_portfolio_correlation(
        self,
        candidate_symbol: str,
        active_positions: Dict[str, Any]
    ) -> str:
        """Q2: 신규 후보와 기존 보유 종목의 상관계수를 계산하여 분산 여부 결정

        Returns:
            "OK"    — 진입 가능
            "HALVE" — 상관관계 높음, 비중 절반 축소 후 진입
            "BLOCK" — 상관관계 매우 높음, 진입 차단
        """
        if not active_positions:
            return "OK"

        try:
            # 후보 종목 수익률 시계열
            cand_returns = self._get_daily_returns(candidate_symbol, CORRELATION_LOOKBACK_DAYS)
            if cand_returns is None or len(cand_returns) < 20:
                return "OK"  # 데이터 부족 시 보수적으로 허용

            max_corr = 0.0
            for held_symbol in active_positions:
                if held_symbol == candidate_symbol:
                    # 동일 종목 추가 매수 → HALVE로 처리
                    max_corr = max(max_corr, CORRELATION_THRESHOLD_HALVE + 0.01)
                    continue

                held_returns = self._get_daily_returns(held_symbol, CORRELATION_LOOKBACK_DAYS)
                if held_returns is None or len(held_returns) < 20:
                    continue

                # 기간 맞추기
                min_len = min(len(cand_returns), len(held_returns))
                corr = float(np.corrcoef(
                    cand_returns[-min_len:],
                    held_returns[-min_len:]
                )[0, 1])

                if np.isnan(corr):
                    continue

                max_corr = max(max_corr, abs(corr))

            if max_corr >= CORRELATION_THRESHOLD_BLOCK:
                return "BLOCK"
            elif max_corr >= CORRELATION_THRESHOLD_HALVE:
                return "HALVE"
            return "OK"

        except Exception as e:
            logger.warning(f"Correlation check failed for {candidate_symbol}: {e}")
            return "OK"

    def _get_daily_returns(self, symbol: str, days: int) -> Optional[np.ndarray]:
        """StockPriceDB에서 일별 수익률 배열 계산"""
        try:
            conn = sqlite3.connect(self.config.stock_price_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT close FROM stock_prices
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT ?
                """,
                (symbol, days + 1)
            )
            rows = cursor.fetchall()
            conn.close()

            if len(rows) < 5:
                return None

            closes = np.array([row[0] for row in reversed(rows)], dtype=float)
            returns = np.diff(closes) / closes[:-1]
            return returns  # type: ignore[no-any-return]
        except Exception as e:
            logger.debug(f"Failed to get daily returns for {symbol}: {e}")
            return None

    def _calculate_atr(self, symbol: str, lookback: int = ATR_LOOKBACK_DAYS) -> float:
        """Q1: 최근 N일 ATR(Average True Range) 계산"""
        try:
            conn = sqlite3.connect(self.config.stock_price_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT high, low, close FROM stock_prices
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT ?
                """,
                (symbol, lookback + 1)
            )
            rows = cursor.fetchall()
            conn.close()

            if len(rows) < 5:
                return 0.0

            # rows는 DESC 순, 역순으로 정렬
            rows = list(reversed(rows))
            true_ranges = []
            for i in range(1, len(rows)):
                high  = rows[i][0]
                low   = rows[i][1]
                prev_close = rows[i - 1][2]
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low  - prev_close)
                )
                true_ranges.append(tr)

            return float(np.mean(true_ranges)) if true_ranges else 0.0
        except Exception as e:
            logger.debug(f"Failed to calculate ATR for {symbol}: {e}")
            return 0.0

    def _get_highest_price_since_entry(self, symbol: str, avg_entry_price: float) -> float:
        """Q1: 진입 이후 최고 종가 조회 (TradeJournal 매수 시점 기준)"""
        try:
            history = self.trade_journal.get_trade_history(symbol=symbol)
            buy_records = [r for r in history if r['side'] == 'BUY']
            if not buy_records:
                return avg_entry_price

            # 가장 최근 매수 시점 이후 데이터
            latest_buy_ts = max(r['timestamp'] for r in buy_records)
            buy_date = latest_buy_ts[:10]

            conn = sqlite3.connect(self.config.stock_price_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT MAX(high) FROM stock_prices
                WHERE symbol = ? AND date >= ?
                """,
                (symbol, buy_date)
            )
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                return float(row[0])
        except Exception as e:
            logger.debug(f"Failed to get highest price since entry for {symbol}: {e}")

        return avg_entry_price

    def _generate_trade_report(
        self,
        symbol: str,
        qty: int,
        price: float,
        signal_type: str,
        sentiment: float,
        vix: float,
        edge: float,
        decision: str,
        reason: str,
        net_pnl: Optional[float] = None,
        crisis_level: Optional[str] = None
    ) -> str:
        """Rule 4: 매수/매도 결정 전 판단 근거 보고서 포맷팅 (Q4: Net PnL 포함)"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pnl_line = (
            f"💹 Net PnL (세금·수수료 반영): {net_pnl:+,.0f} KRW\n"
            if net_pnl is not None else ""
        )
        crisis_line = (
            f"⚠️  Crisis Level: {crisis_level}\n"
            if crisis_level else ""
        )
        report = (
            f"=== 🤖 AUTONOMOUS TRADING AGENT REPORT ===\n"
            f"🕒 Time: {timestamp}\n"
            f"🎫 Symbol: {symbol} | Type: {signal_type}\n"
            f"💰 Price: {price:,.2f} KRW | Target Qty: {qty}\n"
            f"📊 News Sentiment: {sentiment:+.4f}\n"
            f"📉 VIX Fear Gauge: {vix:.2f}\n"
            f"🎯 Probabilistic Edge: {edge:.4f}\n"
            f"{crisis_line}"
            f"{pnl_line}"
            f"📝 Decision: {decision}\n"
            f"💬 Reason: {reason}\n"
            f"=========================================="
        )
        return report

    def _get_current_price(self, symbol: str) -> float:
        """StockPriceDB에서 종목 최신 종가 조회"""
        try:
            conn = sqlite3.connect(self.config.stock_price_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT close FROM stock_prices WHERE symbol = ? ORDER BY date DESC LIMIT 1",
                (symbol,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return float(row[0])
        except Exception as e:
            logger.debug(f"Failed to query local price cache for {symbol}: {e}")
        return 100.0

    def _get_vix_index(self) -> Optional[float]:
        """VIX 지수 조회"""
        try:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT price FROM global_indicators WHERE symbol = '^VIX' ORDER BY date DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return float(row[0])
        except Exception:
            pass
        return 15.0
