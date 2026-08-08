"""
microstructure.py — Microstructure Cost & Market Impact Model

Calculates realistic execution friction costs:
  - STT (Securities Transaction Tax) for KRX (KOSPI/KOSDAQ/KONEX)
  - SEC transaction fee for US exchanges (SP500/NASDAQ/RUSSELL2000)
  - Bid-Ask spread friction cost
  - Square-root market impact cost (Kyle's Lambda proxy based on Order Size / ADV)
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TransactionCostConfig:
    krx_stt_rate: float = 0.0018       # 0.18% STT
    us_sec_rate: float = 0.0000278     # 0.00278% SEC fee
    base_spread_pct: float = 0.0005    # 0.05% default spread
    market_impact_gamma: float = 0.1    # Square-root impact coefficient


class MicrostructureCostModel:
    """Calculates microstructure transaction friction and net return adjustments."""

    def __init__(self, config: TransactionCostConfig | None = None):
        self.cfg = config or TransactionCostConfig()

    def get_tax_fee_rate(self, market: str, is_sell: bool = True) -> float:
        """Return statutory tax and regulatory exchange fee rate."""
        mkt = (market or "").upper()
        if mkt in ("KOSPI", "KOSDAQ", "KONEX"):
            return self.cfg.krx_stt_rate if is_sell else 0.0
        elif mkt in ("SP500", "NASDAQ", "RUSSELL2000", "NYSE"):
            return self.cfg.us_sec_rate if is_sell else 0.0
        return 0.0010  # default fallback

    def calculate_bid_ask_spread(self, volatility: float, price: float) -> float:
        """Estimate half-spread percentage based on price & volatility."""
        if price <= 0:
            return self.cfg.base_spread_pct
        # Low price stocks generally have higher percentage bid-ask spread
        spread = max(self.cfg.base_spread_pct, 0.0002 + (volatility * 0.02))
        return float(spread)

    def calculate_market_impact(self, order_amount: float, adv: float, volatility: float) -> float:
        """Square-root market impact cost: Impact = gamma * volatility * sqrt(Order / ADV)."""
        if adv <= 0 or order_amount <= 0:
            return 0.0005  # 5 bps fallback
        participation_rate = min(1.0, order_amount / adv)
        impact = self.cfg.market_impact_gamma * max(0.10, volatility) * math.sqrt(participation_rate)
        return float(impact)

    def calculate_total_friction(
        self,
        symbol: str,
        market: str,
        price: float,
        volatility: float,
        order_amount: float,
        adv: float,
        is_sell: bool = True
    ) -> float:
        """Calculate total round-trip friction cost percentage."""
        tax = self.get_tax_fee_rate(market, is_sell=is_sell)
        spread = self.calculate_bid_ask_spread(volatility, price)
        impact = self.calculate_market_impact(order_amount, adv, volatility)
        total_cost = tax + spread + impact
        return float(total_cost)

    def net_expected_return(
        self,
        gross_return: float,
        symbol: str,
        market: str,
        price: float = 100.0,
        volatility: float = 0.20,
        order_amount: float = 10000.0,
        adv: float = 1000000.0
    ) -> float:
        """Return expected return net of microstructure transaction costs."""
        friction = self.calculate_total_friction(
            symbol=symbol,
            market=market,
            price=price,
            volatility=volatility,
            order_amount=order_amount,
            adv=adv,
            is_sell=True
        )
        return float(gross_return - friction)
