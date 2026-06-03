"""Persistence Layer - 데이터 저장소 (aiosqlite 비동기 마이그레이션)"""

import json
import sqlite3
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class TradeLogger:
    """주문 및 체결 로그 저장 (aiosqlite 기반 비동기 구현)"""
    
    def __init__(self, db_path: str = "trade_logs.db"):
        self.db_path = Path(db_path)
        self.logger = logger
        self._db_initialized = False
    
    async def _init_database(self):
        """데이터베이스 초기화 (비동기 지연 초기화)"""
        if self._db_initialized:
            return
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.cursor()
            
            # 주문 테이블
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    order_type TEXT,
                    quantity INTEGER,
                    price REAL,
                    status TEXT,
                    filled_quantity INTEGER,
                    created_at TIMESTAMP,
                    executed_at TIMESTAMP
                )
            ''')
            
            # 체결 기록 테이블
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT,
                    symbol TEXT,
                    quantity INTEGER,
                    price REAL,
                    executed_at TIMESTAMP,
                    FOREIGN KEY(order_id) REFERENCES orders(order_id)
                )
            ''')
            
            await conn.commit()
        self._db_initialized = True
        self.logger.info(f"Database initialized at {self.db_path}")
    
    async def log_order(self, order):
        """주문 로그"""
        await self._init_database()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                INSERT OR REPLACE INTO orders 
                (order_id, symbol, order_type, quantity, price, status, filled_quantity, created_at, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order.order_id,
                order.symbol,
                order.order_type.value,
                order.quantity,
                order.price,
                order.status.value,
                order.filled_quantity,
                order.created_at.isoformat(),
                order.executed_at.isoformat() if order.executed_at else None
            ))
            await conn.commit()
        
        self.logger.debug(f"Order logged: {order.order_id}")
    
    async def log_execution(self, order_id: str, symbol: str, quantity: int, price: float):
        """체결 기록"""
        await self._init_database()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                INSERT INTO executions 
                (order_id, symbol, quantity, price, executed_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (order_id, symbol, quantity, price, datetime.now().isoformat()))
            await conn.commit()
        
        self.logger.info(f"Execution logged: {symbol} x{quantity} @ {price}")
    
    async def get_trade_history(self, symbol: str | None = None, limit: int = 100) -> List[Dict]:
        """거래 이력 조회"""
        await self._init_database()
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            async with conn.execute(
                'SELECT * FROM orders WHERE symbol = ? ORDER BY created_at DESC LIMIT ?' if symbol
                else 'SELECT * FROM orders ORDER BY created_at DESC LIMIT ?',
                (symbol, limit) if symbol else (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


class AssetHistoryDB:
    """자산 이력 저장 (aiosqlite 기반 비동기 구현)"""
    
    def __init__(self, db_path: str = "asset_history.db"):
        self.db_path = Path(db_path)
        self.logger = logger
        self._db_initialized = False
    
    async def _init_database(self):
        """데이터베이스 초기화 (비동기 지연 초기화)"""
        if self._db_initialized:
            return
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.cursor()
            
            # 자산 스냅샷 테이블
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS asset_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cash REAL,
                    total_value REAL,
                    holdings TEXT,
                    timestamp TIMESTAMP
                )
            ''')
            
            await conn.commit()
        self._db_initialized = True
        self.logger.info(f"Asset history DB initialized at {self.db_path}")
    
    async def save_snapshot(self, cash: float, total_value: float, holdings: Dict[str, int]):
        """자산 스냅샷 저장"""
        await self._init_database()
        async with aiosqlite.connect(self.db_path) as conn:
            holdings_json = json.dumps(holdings)
            await conn.execute('''
                INSERT INTO asset_snapshots (cash, total_value, holdings, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (cash, total_value, holdings_json, datetime.now().isoformat()))
            await conn.commit()
        
        self.logger.info(f"Asset snapshot saved: cash={cash}, total={total_value}")
    
    async def get_history(self, limit: int = 100) -> List[Dict]:
        """자산 이력 조회"""
        await self._init_database()
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            async with conn.execute('SELECT * FROM asset_snapshots ORDER BY timestamp DESC LIMIT ?', (limit,)) as cursor:
                rows = await cursor.fetchall()
                result = []
                for row in rows:
                    record = dict(row)
                    record['holdings'] = json.loads(record['holdings'])
                    result.append(record)
                return result

class AIPredictionDB:
    """AI 투자 예측 기록 및 자체 평가 (aiosqlite 기반 비동기 구현)"""
    
    def __init__(self, db_path: str = "ai_predictions.db"):
        self.db_path = Path(db_path)
        self.logger = logger
        self._db_initialized = False
    
    async def _init_database(self):
        if self._db_initialized:
            return
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.cursor()
            
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    recommendation TEXT,
                    sentiment TEXT,
                    confidence REAL,
                    target_price REAL,
                    current_price REAL,
                    reasoning TEXT,
                    timestamp TIMESTAMP,
                    evaluated INTEGER DEFAULT 0,
                    accuracy_score REAL DEFAULT NULL
                )
            ''')
            await conn.commit()
        self._db_initialized = True
        self.logger.info(f"AI Prediction DB initialized at {self.db_path}")

    async def log_prediction(self, opinion, current_price: float):
        await self._init_database()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                INSERT INTO predictions 
                (symbol, recommendation, sentiment, confidence, target_price, current_price, reasoning, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                opinion.symbol,
                opinion.recommendation,
                opinion.sentiment.value if hasattr(opinion.sentiment, 'value') else str(opinion.sentiment),
                opinion.confidence,
                opinion.target_price,
                current_price,
                opinion.reasoning,
                opinion.timestamp.isoformat() if opinion.timestamp else datetime.now().isoformat()
            ))
            await conn.commit()
        self.logger.debug(f"AI prediction logged for {opinion.symbol}")

    async def evaluate_pending_predictions(self, get_current_price_func):
        """저장된 예측 중 오래된(예: 7일 이상) 항목을 실제 가격과 비교하여 정확도 평가"""
        await self._init_database()
        try:
            from datetime import timedelta
            threshold_date = (datetime.now() - timedelta(days=7)).isoformat()
            
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                async with conn.execute('SELECT * FROM predictions WHERE evaluated = 0 AND timestamp < ?', (threshold_date,)) as cursor:
                    rows = await cursor.fetchall()
                    
                for row in rows:
                    symbol = row['symbol']
                    rec = row['recommendation']
                    orig_price = row['current_price']
                    
                    try:
                        latest_price = get_current_price_func(symbol)
                        if not latest_price:
                            continue
                            
                        # 간단한 정확도 계산 로직
                        price_diff_pct = (latest_price - orig_price) / orig_price
                        
                        score = 0.5  # 기본
                        if rec == 'BUY':
                            if price_diff_pct > 0.05: score = 1.0
                            elif price_diff_pct > 0: score = 0.8
                            elif price_diff_pct < -0.05: score = 0.0
                            else: score = 0.3
                        elif rec == 'SELL':
                            if price_diff_pct < -0.05: score = 1.0
                            elif price_diff_pct < 0: score = 0.8
                            elif price_diff_pct > 0.05: score = 0.0
                            else: score = 0.3
                        else:  # HOLD
                            if abs(price_diff_pct) < 0.05: score = 1.0
                            else: score = 0.0
                            
                        await conn.execute('UPDATE predictions SET evaluated = 1, accuracy_score = ? WHERE id = ?', (score, row['id']))
                        self.logger.info(f"Evaluated AI prediction for {symbol} (Rec: {rec}, Score: {score})")
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to evaluate prediction for {symbol}: {e}")
                
                await conn.commit()
        except Exception as e:
            self.logger.error(f"Error evaluating AI predictions: {e}")
