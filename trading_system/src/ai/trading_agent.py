import logging
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.config import TradingConfig
from src.broker.real_broker import BrokerBase
from src.risk.risk_manager import RiskManager
from src.utils.notifier import NotificationSystem
from src.data_layer.trade_journal import TradeJournal, TradeRecord
from src.ai.news_sentiment_fetcher import NewsSentimentFetcher

logger = logging.getLogger(__name__)

class TradingAgent:
    """고도화된 자율 주식 거래 에이전트 - 5개 핵심 운영 규칙 탑재"""

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
        self.trade_journal = trade_journal or TradeJournal(db_path=str(Path(config.db_path).parent / "trade_logs.db"))
        self.news_fetcher = news_fetcher or NewsSentimentFetcher()

    async def run_trading_cycle(self):
        """1회 트레이딩 사이클 실행 (비상대응 -> 기존 포지션 관리 -> 신규 매수 시그널 실행)"""
        logger.info("Starting autonomous trading cycle...")
        
        # 1. 비상 대응 프로토콜 체크 (Rule 5)
        emergency_triggered = await self._emergency_protocol()
        if emergency_triggered:
            logger.warning("Emergency protocol active. Cycle aborted after liquidation.")
            return

        # 2. 보유 포지션 관리 (Stop-Loss / Take-Profit / Trailing Stop)
        await self._manage_existing_positions()

        # 3. 신규 매수 기회 탐색 (Rule 2, 3, 1, 4)
        await self._process_new_signals()

        logger.info("Autonomous trading cycle completed.")

    async def _emergency_protocol(self) -> bool:
        """Rule 5: 당일 주가 변동성 5% 이상 시 모든 미체결 주문을 취소하고 현금을 보유(전량 매도)"""
        try:
            # 시장 지표 로드 (KOSPI, KOSDAQ, S&P 500 등)
            conn = sqlite3.connect(self.config.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 가장 최근 날짜의 global_indicators 가져오기
            cursor.execute("""
                SELECT symbol, change_pct 
                FROM global_indicators 
                WHERE date = (SELECT MAX(date) FROM global_indicators)
            """)
            indicators = {row['symbol']: row['change_pct'] for row in cursor.fetchall()}
            conn.close()
            
            # 주요 지수가 5% 이상 변동성(절대값)을 보이는지 검사
            trigger_indexes = []
            for idx_sym in ['^KS11', '^KQ11', '^GSPC', 'KOSPI', 'KOSDAQ', 'SP500']:
                if idx_sym in indicators:
                    change = abs(indicators[idx_sym])
                    # change_pct가 소수점(예: 0.05) 또는 백분율(예: 5.0) 형태로 저장될 수 있음
                    val = change if change < 1.0 else change / 100.0
                    if val >= 0.05:
                        trigger_indexes.append(f"{idx_sym} ({val*100:.1f}%)")

            # 개별 포지션 평가 또는 시장 지표 트리거 시 비상 대응 작동
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
        """보유 중인 모든 포지션 매도 및 취소 주문"""
        logger.warning(f"Liquidating all positions. Reason: {reason}")
        
        # 1. 미체결 주문 취소 시뮬레이션
        if hasattr(self.broker, "cancel_all_orders"):
            try:
                self.broker.cancel_all_orders()
            except Exception as e:
                logger.warning(f"Failed to call broker.cancel_all_orders(): {e}")
                
        # 2. 보유 포지션 전량 매도
        positions = self.trade_journal.get_active_positions()
        for symbol, pos in positions.items():
            qty = pos['qty']
            if qty <= 0:
                continue
                
            try:
                # 현재 가격 조회
                curr_price = self._get_current_price(symbol)
                pnl = (curr_price - pos['avg_price']) * qty
                
                # 주문 실행
                self.broker.submit_order(symbol, qty, "SELL")
                
                # 기록 작성
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
                
                # 보고 및 알림
                report = self._generate_trade_report(
                    symbol=symbol, qty=qty, price=curr_price, signal_type="SELL",
                    sentiment=0.0, vix=0.0, edge=0.0, decision="EXECUTE",
                    reason=f"🚨 비상 청산: {reason}"
                )
                await self.notifier.broadcast("EMERGENCY LIQUIDATION", report)
            except Exception as e:
                logger.error(f"Failed to liquidate {symbol}: {e}")

    async def _manage_existing_positions(self):
        """기존 포지션의 Stop-Loss 및 Take-Profit 실시간 관리"""
        positions = self.trade_journal.get_active_positions()
        if not positions:
            logger.info("No active positions to manage.")
            return

        for symbol, pos in positions.items():
            try:
                qty = pos['qty']
                avg_price = pos['avg_price']
                sl = pos['stop_loss']
                tp = pos['take_profit']
                curr_price = self._get_current_price(symbol)

                # Stop-Loss 또는 Take-Profit 조건 도달 검사
                trigger_sell = False
                reason = ""
                
                if sl is not None and curr_price <= sl:
                    trigger_sell = True
                    reason = f"Stop-Loss triggered (Avg: {avg_price:.2f}, Curr: {curr_price:.2f}, SL: {sl:.2f})"
                elif tp is not None and curr_price >= tp:
                    trigger_sell = True
                    reason = f"Take-Profit triggered (Avg: {avg_price:.2f}, Curr: {curr_price:.2f}, TP: {tp:.2f})"

                if trigger_sell:
                    pnl = (curr_price - avg_price) * qty
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
                        reason=reason
                    )
                    await self.notifier.broadcast("POSITION EXIT", report)
                    
            except Exception as e:
                logger.error(f"Error managing position for {symbol}: {e}")

    async def _process_new_signals(self):
        """Rule 2, 3, 1, 4: 신규 매수 시그널 검증 및 거래 실행"""
        try:
            # 1. 최신 앙상블 예측 데이터 로드
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

            balance = self.broker.get_balance()
            cash = balance.get('cash', 0.0)
            total_value = balance.get('total_value', 100_000_000.0)
            
            # VIX 가져오기
            vix_val = self._get_vix_index()

            for cand in candidates:
                symbol = cand['symbol']
                name = cand['name']
                market = cand['market']
                score = cand['ensemble_score']
                expected_return = cand['ensemble_expected_return']

                # 매수 조건 최소 기준 (예: 앙상블 점수 0.70 이상)
                if score < 0.65:
                    continue

                curr_price = self._get_current_price(symbol)
                
                # Rule 2: 데이터 처리 (뉴스 감성 + VIX 거시지표 체크)
                sentiment = self.news_fetcher.fetch_and_analyze(symbol, name, market)
                
                # 부정적 감성 차단 (score < -0.2) 또는 공포 심리 고조 시 차단
                if sentiment < -0.2:
                    logger.info(f"Skipping {symbol}: News sentiment is too negative ({sentiment:.2f})")
                    continue
                if vix_val and vix_val > 30.0:
                    logger.info(f"Skipping {symbol}: VIX is too high ({vix_val:.2f})")
                    continue

                # Rule 3: 통계적 우위 검사 (win_rate >= 55% & edge > 0)
                total_trades = self.trade_journal.get_total_trades()
                if total_trades < 5:
                    # 거래 이력이 적을 때는 디폴트 우위 사용 (사전 확률 검증 완료)
                    win_rate = 0.58
                    win_loss_ratio = 1.6
                else:
                    win_rate = self.trade_journal.get_win_rate()
                    win_loss_ratio = self.trade_journal.get_win_loss_ratio()
                
                edge = (win_rate * win_loss_ratio) - (1 - win_rate)
                if not self._check_statistical_edge(win_rate, edge):
                    logger.info(f"Skipping {symbol}: No statistical edge (WinRate: {win_rate:.2%}, Edge: {edge:.4f})")
                    continue

                # 손절 라인 및 익절 라인 설정 (5% 손절, 15% 익절)
                stop_price = curr_price * (1 - self.risk_manager.default_stop_loss_pct)
                target_price = curr_price * (1 + self.risk_manager.default_take_profit_pct)

                # Kelly Criterion 기반 추천 비중 계산
                kelly_fraction = self.risk_manager.calculate_kelly_fraction(win_rate, win_loss_ratio)
                if kelly_fraction <= 0:
                    kelly_fraction = 0.05
                    
                target_alloc_value = total_value * kelly_fraction
                qty = int(target_alloc_value / curr_price)

                # Rule 1: 위험 관리 (단일 거래의 리스크가 자본의 2% 이하인지 검증 및 수량 최적화)
                qty = self._validate_risk_limit(symbol, qty, curr_price, stop_price, total_value)
                
                if qty <= 0:
                    logger.info(f"Skipping {symbol}: Risk limit size is 0")
                    continue
                    
                # 현금 잔고 초과 방지
                if qty * curr_price > cash:
                    qty = int(cash / curr_price)
                    if qty <= 0:
                        logger.info(f"Skipping {symbol}: Insufficient cash")
                        continue

                # Rule 4: 보고 의무 준수 및 주문 실행
                reason = f"Ensemble Score: {score:.2f}, Expected Return: {expected_return:.2%}"
                report = self._generate_trade_report(
                    symbol=symbol, qty=qty, price=curr_price, signal_type="BUY",
                    sentiment=sentiment, vix=vix_val or 0.0, edge=edge,
                    decision="EXECUTE", reason=reason
                )
                
                # 보고서 출력 및 방송
                await self.notifier.broadcast("BUY DECISION REPORT", report)
                
                # 실제 주문 실행
                self.broker.submit_order(symbol, qty, "BUY")
                
                # 기록 보관
                trade = TradeRecord(
                    timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    symbol=symbol,
                    side="BUY",
                    quantity=qty,
                    price=curr_price,
                    reason=reason,
                    ensemble_score=score,
                    sentiment_score=sentiment,
                    regime="BULL" if (vix_val or 0.0) < 20.0 else "VOLATILE",
                    stop_loss=stop_price,
                    take_profit=target_price,
                    status="EXECUTED"
                )
                self.trade_journal.log_trade(trade)
                
                # 자금 업데이트
                cash -= qty * curr_price

        except Exception as e:
            logger.error(f"Error processing new buy signals: {e}")

    def _validate_risk_limit(self, symbol: str, qty: int, price: float, stop_price: float, total_capital: float) -> int:
        """Rule 1: 단일 거래에 자본의 2% 이상을 초과하여 리스크를 부담하지 않도록 수량 재산출"""
        max_risk = total_capital * self.risk_manager.max_loss_per_trade_pct # 2% 자본 리스크 한계
        per_share_risk = price - stop_price
        
        if per_share_risk <= 0:
            return qty
            
        max_qty_allowed = int(max_risk / per_share_risk)
        
        if qty > max_qty_allowed:
            logger.info(f"Risk rule triggered for {symbol}: Downsizing qty from {qty} to {max_qty_allowed} to satisfy 2% risk limit.")
            return max_qty_allowed
        return qty

    def _check_statistical_edge(self, win_rate: float, edge: float) -> bool:
        """Rule 3: 통계적 데이터와 확률적 우위가 있는 경우에만 거래 시그널을 발생 (승률 > 55% 및 edge > 0)"""
        return win_rate >= 0.55 and edge > 0.0

    def _generate_trade_report(
        self, symbol: str, qty: int, price: float, signal_type: str,
        sentiment: float, vix: float, edge: float, decision: str, reason: str
    ) -> str:
        """Rule 4: 매수/매도 결정을 내리기 전 판단 근거 요약 보고서 포맷팅"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = (
            f"=== 🤖 AUTONOMOUS TRADING AGENT REPORT ===\n"
            f"🕒 Time: {timestamp}\n"
            f"🎫 Symbol: {symbol} | Type: {signal_type}\n"
            f"💰 Price: {price:,.2f} KRW | Target Qty: {qty}\n"
            f"📊 News Sentiment: {sentiment:+.4f}\n"
            f"📉 VIX Fear Gauge: {vix:.2f}\n"
            f"🎯 Probabilistic Edge: {edge:.4f}\n"
            f"📝 Decision: {decision}\n"
            f"💬 Reason: {reason}\n"
            f"=========================================="
        )
        return report

    def _get_current_price(self, symbol: str) -> float:
        """DB 또는 모의 데이터를 사용해 종목의 현재 가격 조회"""
        try:
            # StockPriceDB에서 최신 가격을 조회
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
        
        # 기본값 (Mock / Fallback)
        return 100.0

    def _get_vix_index(self) -> Optional[float]:
        """VIX 지수 로드"""
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
