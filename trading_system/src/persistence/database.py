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
