import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

@dataclass
class TradeRecord:
    timestamp: str
    symbol: str
    side: str            # BUY / SELL / CANCEL
    quantity: int
    price: float
    reason: Optional[str] = None
    ensemble_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    regime: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: Optional[float] = None
    status: str = "EXECUTED"

class TradeJournal:
    """거래 기록 저장 및 통계 분석 (SQLite 기반 동기 구현)"""

    def __init__(self, db_path: str = "trade_logs.db"):
        self.db_path = Path(db_path)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """데이터베이스 및 테이블 초기화"""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    reason TEXT,
                    ensemble_score REAL,
                    sentiment_score REAL,
                    regime TEXT,
                    stop_loss REAL,
                    take_profit REAL,
                    pnl REAL,
                    status TEXT DEFAULT 'EXECUTED'
                )
            """)
            conn.commit()
            logger.info(f"TradeJournal initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        finally:
            conn.close()

    def add_trade(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        reason: Optional[str] = None,
        ensemble_score: Optional[float] = None,
        sentiment_score: Optional[float] = None,
        regime: Optional[str] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        pnl: Optional[float] = None,
        status: str = "EXECUTED",
        timestamp: Optional[str] = None,
    ) -> None:
        import math
        def _sf(v):
            if v is None:
                return None
            try:
                f = float(v)
                return f if math.isfinite(f) else None
            except (ValueError, TypeError):
                return None

        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        safe_qty = int(quantity) if quantity is not None else 0
        safe_price = float(price) if (price is not None and math.isfinite(price)) else 0.0

        trade = TradeRecord(
            timestamp=timestamp,
            symbol=str(symbol or "").strip(),
            side=str(side or "").upper().strip(),
            quantity=safe_qty,
            price=safe_price,
            reason=reason,
            ensemble_score=_sf(ensemble_score),
            sentiment_score=_sf(sentiment_score),
            regime=regime,
            stop_loss=_sf(stop_loss),
            take_profit=_sf(take_profit),
            pnl=_sf(pnl),
            status=status,
        )
        self.log_trade(trade)

    def log_trade(self, trade: TradeRecord) -> None:
        """거래 기록 저장 (매수/매도/취소)"""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO trade_journal (
                    timestamp, symbol, side, quantity, price, reason,
                    ensemble_score, sentiment_score, regime, stop_loss,
                    take_profit, pnl, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.timestamp, trade.symbol, trade.side, trade.quantity,
                trade.price, trade.reason, trade.ensemble_score,
                trade.sentiment_score, trade.regime, trade.stop_loss,
                trade.take_profit, trade.pnl, trade.status
            ))
            conn.commit()
            logger.info(f"Logged trade: {trade.side} {trade.quantity} {trade.symbol} @ {trade.price}")
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
            raise
        finally:
            conn.close()

    def get_total_trades(self, lookback_days: int = 90) -> int:
        """최근 N일간 총 매매(매도) 횟수 조회"""
        conn = self._get_connection()
        try:
            safe_days = max(1, int(lookback_days)) if lookback_days is not None else 90
            since_date = (datetime.now() - timedelta(days=safe_days)).strftime("%Y-%m-%d %H:%M:%S")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM trade_journal
                WHERE side = 'SELL' AND timestamp >= ? AND pnl IS NOT NULL
            """, (since_date,))
            row = cursor.fetchone()
            return row['total'] if row else 0
        except Exception as e:
            logger.error(f"Failed to get total trades count: {e}")
            return 0
        finally:
            conn.close()

    def get_win_rate(self, lookback_days: int = 90) -> float:
        """최근 N일간 승률 계산 (매도 중 실현 손익 > 0인 비중)"""
        conn = self._get_connection()
        try:
            safe_days = max(1, int(lookback_days)) if lookback_days is not None else 90
            since_date = (datetime.now() - timedelta(days=safe_days)).strftime("%Y-%m-%d %H:%M:%S")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
                FROM trade_journal
                WHERE side = 'SELL' AND timestamp >= ? AND pnl IS NOT NULL
            """, (since_date,))
            row = cursor.fetchone()
            if not row or row['total'] == 0:
                return 0.0
            return float(row['wins']) / float(row['total'])
        except Exception as e:
            logger.error(f"Failed to calculate win rate: {e}")
            return 0.0
        finally:
            conn.close()

    def get_win_loss_ratio(self, lookback_days: int = 90) -> float:
        """평균 이익 / 평균 손실 비율"""
        conn = self._get_connection()
        try:
            since_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d %H:%M:%S")
            cursor = conn.cursor()
            # 평균 이익
            cursor.execute("""
                SELECT AVG(pnl) as avg_win
                FROM trade_journal
                WHERE side = 'SELL' AND timestamp >= ? AND pnl > 0
            """, (since_date,))
            r_win = cursor.fetchone()
            avg_win = r_win['avg_win'] if r_win and r_win['avg_win'] is not None else None

            # 평균 손실
            cursor.execute("""
                SELECT AVG(pnl) as avg_loss
                FROM trade_journal
                WHERE side = 'SELL' AND timestamp >= ? AND pnl < 0
            """, (since_date,))
            r_loss = cursor.fetchone()
            avg_loss = r_loss['avg_loss'] if r_loss and r_loss['avg_loss'] is not None else None

            if not avg_win or float(avg_win) <= 0:
                return 0.0
            if not avg_loss or float(avg_loss) == 0:
                return 10.0 if float(avg_win) > 0 else 0.0

            return float(avg_win) / abs(float(avg_loss))
        except Exception as e:
            logger.error(f"Failed to calculate win-loss ratio: {e}")
            return 0.0
        finally:
            conn.close()

    def get_trade_history(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """거래 이력 조회"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if symbol:
                cursor.execute("""
                    SELECT * FROM trade_journal
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                """, (symbol,))
            else:
                cursor.execute("""
                    SELECT * FROM trade_journal
                    ORDER BY timestamp DESC
                """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to fetch trade history: {e}")
            return []
        finally:
            conn.close()

    def get_daily_pnl(self) -> float:
        """당일 실현 손익 합계"""
        conn = self._get_connection()
        try:
            today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(pnl) as daily_pnl
                FROM trade_journal
                WHERE side = 'SELL' AND timestamp >= ? AND pnl IS NOT NULL
            """, (today_start,))
            row = cursor.fetchone()
            if row and row['daily_pnl'] is not None:
                return float(row['daily_pnl'])
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get daily PnL: {e}")
            return 0.0
        finally:
            conn.close()

    def get_active_positions(self) -> Dict[str, Dict[str, Any]]:
        """거래 로그를 기반으로 현재 보유 중인 포지션과 평단가 계산"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, side, quantity, price, stop_loss, take_profit
                FROM trade_journal
                WHERE status = 'EXECUTED'
                ORDER BY timestamp ASC
            """)
            rows = cursor.fetchall()

            positions: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                symbol = row['symbol']
                side = row['side']
                qty = row['quantity']
                price = row['price']
                sl = row['stop_loss']
                tp = row['take_profit']

                if side == 'BUY':
                    if symbol not in positions:
                        positions[symbol] = {
                            'symbol': symbol,
                            'qty': 0,
                            'avg_price': 0.0,
                            'total_cost': 0.0,
                            'stop_loss': sl,
                            'take_profit': tp
                        }
                    p = positions[symbol]
                    p['qty'] += qty
                    p['total_cost'] += qty * price
                    p['avg_price'] = p['total_cost'] / p['qty'] if p['qty'] > 0 else 0.0
                    if sl is not None:
                        p['stop_loss'] = sl
                    if tp is not None:
                        p['take_profit'] = tp
                elif side == 'SELL':
                    if symbol in positions:
                        p = positions[symbol]
                        p['qty'] -= qty
                        if p['qty'] <= 0:
                            positions.pop(symbol)
                        else:
                            p['total_cost'] = p['qty'] * p['avg_price']

            return positions
        except Exception as e:
            logger.error(f"Failed to calculate active positions: {e}")
            return {}
        finally:
            conn.close()
