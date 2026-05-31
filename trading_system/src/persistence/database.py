"""Persistence Layer - 데이터 저장소"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class TradeLogger:
    """주문 및 체결 로그 저장"""
    
    def __init__(self, db_path: str = "trade_logs.db"):
        self.db_path = Path(db_path)
        self.logger = logger
        self._init_database()
    
    def _init_database(self):
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 주문 테이블
            cursor.execute('''
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
            cursor.execute('''
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
            
            conn.commit()
        
        self.logger.info(f"Database initialized at {self.db_path}")
    
    def log_order(self, order):
        """주문 로그"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
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
            conn.commit()
        
        self.logger.debug(f"Order logged: {order.order_id}")
    
    def log_execution(self, order_id: str, symbol: str, quantity: int, price: float):
        """체결 기록"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO executions 
                (order_id, symbol, quantity, price, executed_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (order_id, symbol, quantity, price, datetime.now().isoformat()))
            conn.commit()
        
        self.logger.info(f"Execution logged: {symbol} x{quantity} @ {price}")
    
    def get_trade_history(self, symbol: str | None = None, limit: int = 100) -> List[Dict]:
        """거래 이력 조회"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if symbol:
                cursor.execute('SELECT * FROM orders WHERE symbol = ? ORDER BY created_at DESC LIMIT ?',
                             (symbol, limit))
            else:
                cursor.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT ?', (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


class AssetHistoryDB:
    """자산 이력 저장"""
    
    def __init__(self, db_path: str = "asset_history.db"):
        self.db_path = Path(db_path)
        self.logger = logger
        self._init_database()
    
    def _init_database(self):
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 자산 스냅샷 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS asset_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cash REAL,
                    total_value REAL,
                    holdings TEXT,
                    timestamp TIMESTAMP
                )
            ''')
            
            conn.commit()
        
        self.logger.info(f"Asset history DB initialized at {self.db_path}")
    
    def save_snapshot(self, cash: float, total_value: float, holdings: Dict[str, int]):
        """자산 스냅샷 저장"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            holdings_json = json.dumps(holdings)
            cursor.execute('''
                INSERT INTO asset_snapshots (cash, total_value, holdings, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (cash, total_value, holdings_json, datetime.now().isoformat()))
            conn.commit()
        
        self.logger.info(f"Asset snapshot saved: cash={cash}, total={total_value}")
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """자산 이력 조회"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM asset_snapshots ORDER BY timestamp DESC LIMIT ?', (limit,))
            
            rows = cursor.fetchall()
            result = []
            for row in rows:
                record = dict(row)
                record['holdings'] = json.loads(record['holdings'])
                result.append(record)
            
            return result
