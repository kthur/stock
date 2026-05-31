"""Asset Management - 포트폴리오 및 자산 관리"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class AssetSnapshot:
    """자산 스냅샷"""
    cash: float
    holdings: Dict[str, int]  # symbol: quantity
    total_value: float
    timestamp: datetime


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    quantity: int
    avg_price: float
    
    def get_value(self, current_price: float) -> float:
        return self.quantity * current_price


class PortfolioManager:
    """포트폴리오 관리자 - 실시간 가용 자산 계산"""
    
    def __init__(self, initial_cash: float = 0):
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.asset_history: List[AssetSnapshot] = []
        self.logger = logger
        
    def add_position(self, symbol: str, quantity: int, price: float):
        """포지션 추가 또는 업데이트"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_qty = pos.quantity + quantity
            total_cost = pos.quantity * pos.avg_price + quantity * price
            self.positions[symbol].avg_price = total_cost / total_qty
            self.positions[symbol].quantity = total_qty
        else:
            self.positions[symbol] = Position(symbol=symbol, quantity=quantity, avg_price=price)
        
        self.logger.info(f"Position added: {symbol} x{quantity} @ {price}")
    
    def reduce_position(self, symbol: str, quantity: int) -> bool:
        """포지션 감소"""
        if symbol not in self.positions or self.positions[symbol].quantity < quantity:
            self.logger.warning(f"Cannot reduce position: {symbol}")
            return False
        
        self.positions[symbol].quantity -= quantity
        if self.positions[symbol].quantity == 0:
            del self.positions[symbol]
        
        self.logger.info(f"Position reduced: {symbol} x{quantity}")
        return True
    
    def get_available_cash(self) -> float:
        """사용 가능한 현금 조회"""
        return self.cash
    
    def deposit(self, amount: float):
        """예금"""
        self.cash += amount
        self.logger.info(f"Deposited: {amount}, total cash: {self.cash}")
    
    def withdraw(self, amount: float) -> bool:
        """출금"""
        if self.cash >= amount:
            self.cash -= amount
            self.logger.info(f"Withdrawn: {amount}, remaining cash: {self.cash}")
            return True
        return False
    
    def get_portfolio_value(self, market_prices: Dict[str, float]) -> float:
        """포트폴리오 총 가치 계산"""
        total = self.cash
        for symbol, position in self.positions.items():
            if symbol in market_prices:
                total += position.quantity * market_prices[symbol]
        return total
    
    def take_snapshot(self) -> AssetSnapshot:
        """자산 스냅샷 기록"""
        snapshot = AssetSnapshot(
            cash=self.cash,
            holdings={s: p.quantity for s, p in self.positions.items()},
            total_value=self.cash,  # 시장가 정보 없이는 현금만 계산
            timestamp=datetime.now()
        )
        self.asset_history.append(snapshot)
        return snapshot


class AccountSyncAgent:
    """자산 동기화 에이전트 - 증권사 잔고와 동기화"""
    
    def __init__(self, portfolio: PortfolioManager):
        self.portfolio = portfolio
        self.sync_history: List[Dict] = []
        self.logger = logger
        self.subscribers: List[Callable] = []
    
    def subscribe(self, callback: Callable):
        """동기화 결과 구독"""
        self.subscribers.append(callback)
    
    def sync_with_broker(self, broker_cash: float, broker_holdings: Dict[str, int]) -> Dict:
        """증권사 계좌 잔고와 동기화"""
        cash_diff = broker_cash - self.portfolio.cash
        holdings_diff = {}
        
        # 포지션 차이 계산
        for symbol, broker_qty in broker_holdings.items():
            portfolio_qty = self.portfolio.positions.get(symbol, Position(symbol, 0, 0)).quantity
            if portfolio_qty != broker_qty:
                holdings_diff[symbol] = broker_qty - portfolio_qty
        
        # 포트폴리오에만 있는 포지션 확인
        for symbol in self.portfolio.positions:
            if symbol not in broker_holdings:
                holdings_diff[symbol] = -self.portfolio.positions[symbol].quantity
        
        # 동기화 수행
        if cash_diff != 0:
            self.portfolio.cash = broker_cash
            self.logger.warning(f"Cash adjusted: {cash_diff}")
        
        for symbol, diff in holdings_diff.items():
            if diff > 0:
                self.portfolio.add_position(symbol, diff, 0)
            elif diff < 0:
                self.portfolio.reduce_position(symbol, -diff)
        
        sync_result = {
            'cash_diff': cash_diff,
            'holdings_diff': holdings_diff,
            'timestamp': datetime.now()
        }
        self.sync_history.append(sync_result)
        
        # 구독자에게 알림
        for callback in self.subscribers:
            callback(sync_result)
        
        self.logger.info(f"Account synced: cash_diff={cash_diff}, holdings={holdings_diff}")
        return sync_result
