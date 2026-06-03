"""Risk Management - 위험 관리 시스템"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """위험 수준"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RiskMetrics:
    """위험 지표"""
    current_value: float
    max_loss_limit: float
    max_position_size: float
    stop_loss_pct: float  # 1% = 0.01
    take_profit_pct: float
    current_drawdown: float
    max_drawdown_allowed: float
    portfolio_volatility: float
    risk_level: RiskLevel
    timestamp: datetime = field(default_factory=datetime.now)


class RiskManager:
    """위험 관리 시스템"""
    
    def __init__(self, portfolio_value: float = 1000000):
        """
        위험 관리 초기화
        
        Args:
            portfolio_value: 초기 포트폴리오 가치
        """
        self.portfolio_value = portfolio_value
        self.peak_value = portfolio_value
        self.logger = logger
        
        # 위험 정책
        self.max_loss_per_trade_pct = 0.02  # 거래당 최대 손실 2%
        self.max_portfolio_loss_pct = 0.10  # 포트폴리오 최대 손실 10%
        self.max_position_size_pct = 0.20  # 최대 포지션 크기 20%
        self.position_limits: Dict[str, float] = {}  # 종목별 한계
        
        # 기본 Stop Loss / Take Profit
        self.default_stop_loss_pct = 0.05  # 5%
        self.default_take_profit_pct = 0.10  # 10%
        
        # 활성 자동매매 전략
        self.active_strategy = "HYBRID"
        
        # 설정 로드
        self._load_config()
        
        self.metrics_history: List[RiskMetrics] = []
        self.alerts: List[Dict] = []

    def _get_config_path(self):
        import os
        from pathlib import Path
        return Path(__file__).parent.parent.parent / "risk_config.json"

    def _load_config(self):
        import json
        config_path = self._get_config_path()
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.default_stop_loss_pct = data.get("default_stop_loss_pct", self.default_stop_loss_pct)
                    self.max_portfolio_loss_pct = data.get("max_portfolio_loss_pct", self.max_portfolio_loss_pct)
                    self.max_position_size_pct = data.get("max_position_size_pct", self.max_position_size_pct)
                    self.active_strategy = data.get("active_strategy", self.active_strategy).upper()
                self.logger.info(f"Risk configuration loaded from {config_path}: StopLoss={self.default_stop_loss_pct:.2%}, MaxPortfolioLoss={self.max_portfolio_loss_pct:.2%}, MaxPositionSize={self.max_position_size_pct:.2%}, ActiveStrategy={self.active_strategy}")
            except Exception as e:
                self.logger.error(f"Failed to load risk configuration: {e}")

    def save_config(self):
        import json
        config_path = self._get_config_path()
        try:
            data = {
                "default_stop_loss_pct": self.default_stop_loss_pct,
                "max_portfolio_loss_pct": self.max_portfolio_loss_pct,
                "max_position_size_pct": self.max_position_size_pct,
                "active_strategy": self.active_strategy
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.logger.info(f"Risk configuration saved to {config_path}: StopLoss={self.default_stop_loss_pct:.2%}, MaxPortfolioLoss={self.max_portfolio_loss_pct:.2%}, MaxPositionSize={self.max_position_size_pct:.2%}, ActiveStrategy={self.active_strategy}")
        except Exception as e:
            self.logger.error(f"Failed to save risk configuration: {e}")
        
    def set_position_limit(self, symbol: str, max_quantity: int):
        """종목별 최대 수량 설정"""
        self.position_limits[symbol] = max_quantity
        self.logger.info(f"Position limit set for {symbol}: {max_quantity}")
    
    def calculate_max_position_size(self, current_price: float) -> int:
        """최대 포지션 크기 계산"""
        max_value = self.portfolio_value * self.max_position_size_pct
        max_quantity = int(max_value / current_price)
        return max_quantity
    
    def calculate_position_sizing(self, symbol: str, entry_price: float, 
                                 stop_loss_price: float) -> int:
        """Kelly Criterion 기반 포지션 사이징"""
        # 위험금 계산
        risk_per_share = entry_price - stop_loss_price
        if risk_per_share <= 0:
            self.logger.warning("Invalid stop loss price")
            return 0
        
        # 거래당 최대 손실액
        max_loss = self.portfolio_value * self.max_loss_per_trade_pct
        
        # 포지션 수량
        position_quantity = int(max_loss / risk_per_share)
        
        # 최대 포지션 제한 적용
        max_position = self.calculate_max_position_size(entry_price)
        position_quantity = min(position_quantity, max_position)
        
        # 종목별 한계 적용
        if symbol in self.position_limits:
            position_quantity = min(position_quantity, self.position_limits[symbol])
        
        self.logger.info(f"Calculated position size for {symbol}: {position_quantity} shares")
        return position_quantity
    
    def check_stop_loss(self, symbol: str, current_price: float, 
                       entry_price: float) -> bool:
        """Stop Loss 확인"""
        stop_loss_price = entry_price * (1 - self.default_stop_loss_pct)
        
        if current_price <= stop_loss_price:
            self._create_alert("STOP_LOSS", symbol, current_price, entry_price)
            return True
        
        return False
    
    def check_take_profit(self, symbol: str, current_price: float, 
                         entry_price: float) -> bool:
        """Take Profit 확인"""
        take_profit_price = entry_price * (1 + self.default_take_profit_pct)
        
        if current_price >= take_profit_price:
            self._create_alert("TAKE_PROFIT", symbol, current_price, entry_price)
            return True
        
        return False
    
    def update_portfolio_value(self, new_value: float):
        """포트폴리오 가치 업데이트"""
        self.portfolio_value = new_value
        
        # 최고값 업데이트
        if new_value > self.peak_value:
            self.peak_value = new_value
        
        self.logger.debug(f"Portfolio value updated: {new_value}")
    
    def calculate_drawdown(self) -> float:
        """현재 Drawdown 계산 (%)"""
        if self.peak_value == 0:
            return 0
        
        drawdown = (self.peak_value - self.portfolio_value) / self.peak_value
        return drawdown
    
    def calculate_risk_level(self, positions: Dict[str, float]) -> RiskLevel:
        """현재 위험 수준 계산"""
        drawdown = self.calculate_drawdown()
        
        if drawdown >= 0.20:  # 20% 이상 손실
            return RiskLevel.CRITICAL
        elif drawdown >= 0.10:  # 10% 이상 손실
            return RiskLevel.HIGH
        elif drawdown >= 0.05:  # 5% 이상 손실
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def get_risk_adjusted_position_size(self, base_quantity: int, risk_level: RiskLevel) -> int:
        """위험 수준 기반 포지션 크기 조정"""
        adjustments = {
            RiskLevel.LOW: 1.0,
            RiskLevel.MEDIUM: 0.75,
            RiskLevel.HIGH: 0.5,
            RiskLevel.CRITICAL: 0.25
        }
        
        multiplier = adjustments.get(risk_level, 0.5)
        adjusted_quantity = int(base_quantity * multiplier)
        
        self.logger.info(f"Position size adjusted from {base_quantity} to {adjusted_quantity} "
                        f"(risk level: {risk_level.value}, multiplier: {multiplier})")
        
        return adjusted_quantity
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """Value at Risk (VaR) 계산"""
        if not returns:
            return 0
        
        sorted_returns = sorted(returns)
        var_index = int(len(sorted_returns) * (1 - confidence))
        
        if var_index >= len(sorted_returns):
            var_index = 0
        
        var = sorted_returns[var_index]
        return var
    
    def calculate_cvar(self, returns: List[float], confidence: float = 0.95) -> float:
        """Conditional Value at Risk (CVaR) 계산"""
        if not returns:
            return 0
        
        var = self.calculate_var(returns, confidence)
        worse_returns = [r for r in returns if r <= var]
        
        if not worse_returns:
            return var
        
        cvar = sum(worse_returns) / len(worse_returns)
        return cvar
    
    def generate_risk_report(self, positions: Dict[str, float], 
                            market_prices: Dict[str, float]) -> RiskMetrics:
        """위험 보고서 생성"""
        # 현재 포지션 가치 계산
        position_value = sum(market_prices.get(symbol, 0) * qty 
                            for symbol, qty in positions.items())
        
        total_value = self.portfolio_value + position_value
        current_drawdown = self.calculate_drawdown()
        risk_level = self.calculate_risk_level(positions)
        
        # 포트폴리오 변동성 추정 (간단한 예시)
        portfolio_volatility = 0.15 if risk_level == RiskLevel.HIGH else 0.10
        
        metrics = RiskMetrics(
            current_value=total_value,
            max_loss_limit=self.portfolio_value * self.max_portfolio_loss_pct,
            max_position_size=self.portfolio_value * self.max_position_size_pct,
            stop_loss_pct=self.default_stop_loss_pct,
            take_profit_pct=self.default_take_profit_pct,
            current_drawdown=current_drawdown,
            max_drawdown_allowed=0.20,
            portfolio_volatility=portfolio_volatility,
            risk_level=risk_level
        )
        
        self.metrics_history.append(metrics)
        self.logger.info(f"Risk report generated: drawdown={current_drawdown:.2%}, "
                        f"level={risk_level.value}")
        
        return metrics
    
    def _create_alert(self, alert_type: str, symbol: str, 
                     current_price: float, entry_price: float):
        """경고 생성"""
        alert = {
            'type': alert_type,
            'symbol': symbol,
            'current_price': current_price,
            'entry_price': entry_price,
            'pnl_pct': (current_price - entry_price) / entry_price * 100,
            'timestamp': datetime.now()
        }
        
        self.alerts.append(alert)
        self.logger.warning(f"Risk alert: {alert_type} for {symbol} "
                           f"@ {current_price} (entry: {entry_price})")
    
    def get_active_alerts(self) -> List[Dict]:
        """활성 경고 조회"""
        return self.alerts
    
    def clear_alerts(self):
        """경고 초기화"""
        self.alerts.clear()
        self.logger.info("Alerts cleared")
