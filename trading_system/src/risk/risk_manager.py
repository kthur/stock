"""Risk Management - 위험 관리 시스템"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List
import logging
from pathlib import Path
import json

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
    
    def __init__(
        self,
        portfolio_value: float = 1000000,
        max_loss_per_trade_pct: float = 0.02,
        max_portfolio_loss_pct: float = 0.10,
        max_position_size_pct: float = 0.20,
        default_stop_loss_pct: float = 0.05,
        default_take_profit_pct: float = 0.10,
        max_drawdown_allowed: float = 0.20,
        atr_multiplier_stop: float = 2.0,
        atr_multiplier_target: float = 4.0,
        volatility_scaling: bool = True,
    ):
        self.portfolio_value = portfolio_value
        self.peak_value = portfolio_value
        self.logger = logger
        
        self.max_loss_per_trade_pct = max_loss_per_trade_pct
        self.max_portfolio_loss_pct = max_portfolio_loss_pct
        self.max_position_size_pct = max_position_size_pct
        self.default_stop_loss_pct = default_stop_loss_pct
        self.default_take_profit_pct = default_take_profit_pct
        self.max_drawdown_allowed = max_drawdown_allowed
        self.atr_multiplier_stop = atr_multiplier_stop
        self.atr_multiplier_target = atr_multiplier_target
        self.volatility_scaling = volatility_scaling
        self.position_limits: Dict[str, float] = {}
        
        self.active_strategy = "HYBRID"
        
        self._load_config()
        
        self.metrics_history: List[RiskMetrics] = []
        self.alerts: List[Dict] = []

    def calculate_atr_based_stop(self, entry_price: float, atr: float) -> float:
        stop_distance = atr * self.atr_multiplier_stop
        return max(entry_price - stop_distance, entry_price * (1 - self.default_stop_loss_pct * 2))

    def calculate_atr_based_target(self, entry_price: float, atr: float) -> float:
        target_distance = atr * self.atr_multiplier_target
        return min(entry_price + target_distance, entry_price * (1 + self.default_take_profit_pct * 2))

    def _volatility_scalar(self, vix: float = 20.0) -> float:
        if not self.volatility_scaling or vix <= 0:
            return 1.0
        if vix >= 40:
            return 0.25
        elif vix >= 30:
            return 0.50
        elif vix >= 25:
            return 0.75
        elif vix <= 12:
            return 1.25
        return 1.0

    def _get_config_path(self):
        return Path(__file__).parent.parent.parent / "risk_config.json"

    def _load_config(self):
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
    
    def calculate_kelly_fraction(self, win_rate: float, win_loss_ratio: float, half_kelly: bool = True) -> float:
        """Kelly Criterion을 사용한 최적 투자 비중 계산 (f*)"""
        if win_loss_ratio <= 0:
            return 0.0
            
        # Kelly 공식: f* = W - ((1 - W) / R)
        kelly_pct = win_rate - ((1.0 - win_rate) / win_loss_ratio)
        
        if kelly_pct <= 0:
            return 0.0
            
        # 보수적 운영을 위해 Half Kelly 적용
        if half_kelly:
            kelly_pct /= 2.0
            
        # 최대 포지션 한도를 초과하지 않도록 제한
        return min(kelly_pct, self.max_position_size_pct)

    
    def calculate_position_sizing(self, symbol: str, entry_price: float, 
                                 stop_loss_price: float, 
                                 win_rate: float = 0.0, 
                                 win_loss_ratio: float = 0.0,
                                 vix: float = 20.0) -> int:
        """Kelly Criterion 기반 포지션 사이징 (선택적) 및 리스크 기반 사이징"""
        # 위험금 계산
        risk_per_share = entry_price - stop_loss_price
        if risk_per_share <= 0:
            self.logger.warning("Invalid stop loss price")
            return 0
        
        # Kelly 공식 적용 (정보가 있는 경우)
        if win_rate > 0 and win_loss_ratio > 0:
            kelly_pct = self.calculate_kelly_fraction(win_rate, win_loss_ratio)
            max_value = self.portfolio_value * kelly_pct
        else:
            max_loss = self.portfolio_value * self.max_loss_per_trade_pct
            max_value = max_loss * (entry_price / risk_per_share)
        
        vol_scalar = self._volatility_scalar(vix)
        max_value *= vol_scalar
        
        position_quantity = int(max_value / entry_price)
        
        max_position = self.calculate_max_position_size(entry_price)
        position_quantity = min(position_quantity, max_position)
        
        if symbol in self.position_limits:
            position_quantity = int(min(position_quantity, self.position_limits[symbol]))
        
        if vol_scalar < 1.0:
            self.logger.info(f"Volatility scaling applied: {vol_scalar:.2f}x (VIX={vix})")
        
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
        """현재 위험 수준 계산 (drawdown + 포지션 집중도 기반)"""
        drawdown = self.calculate_drawdown()
        concentration_risk = 0.0
        
        if positions:
            total_exposure = sum(abs(v) for v in positions.values())
            if total_exposure > 0:
                max_single = max(abs(v) for v in positions.values())
                concentration_risk = max_single / total_exposure
        
        if drawdown >= self.max_drawdown_allowed or concentration_risk > 0.50:
            return RiskLevel.CRITICAL
        elif drawdown >= self.max_drawdown_allowed * 0.5 or concentration_risk > 0.35:
            return RiskLevel.HIGH
        elif drawdown >= self.max_drawdown_allowed * 0.25 or concentration_risk > 0.25:
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
        
        high_vol = self.max_drawdown_allowed * 0.75
        low_vol = self.max_drawdown_allowed * 0.5
        portfolio_volatility = high_vol if risk_level == RiskLevel.HIGH else low_vol
        
        metrics = RiskMetrics(
            current_value=total_value,
            max_loss_limit=self.portfolio_value * self.max_portfolio_loss_pct,
            max_position_size=self.portfolio_value * self.max_position_size_pct * self._volatility_scalar(),
            stop_loss_pct=self.default_stop_loss_pct,
            take_profit_pct=self.default_take_profit_pct,
            current_drawdown=current_drawdown,
            max_drawdown_allowed=self.max_drawdown_allowed,
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
