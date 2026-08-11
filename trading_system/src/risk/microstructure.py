"""
microstructure.py — Microstructure Cost & Market Impact Model

Calculates realistic execution friction costs:
  - STT (Securities Transaction Tax) for KRX (KOSPI/KOSDAQ)
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
    kospi_stt_rate: float = 0.0018     # 0.18% STT
    kosdaq_stt_rate: float = 0.0018    # 0.18% STT
    konex_stt_rate: float = 0.0008     # 0.08% STT
    brokerage_fee_rate: float = 0.00035 # 0.035% brokerage fee
    us_sec_rate: float = 0.0000278     # 0.00278% SEC fee
    us_brokerage_fee_rate: float = 0.00005 # 0.005% US fee
    base_spread_pct: float = 0.0005    # 0.05% default spread
    market_impact_gamma: float = 0.1    # Square-root impact coefficient


class MicrostructureCostModel:
    """Calculates microstructure transaction friction and net return adjustments."""

    def __init__(self, config: TransactionCostConfig | None = None):
        self.cfg = config or TransactionCostConfig()

    def get_tax_fee_rate(self, market: str, is_sell: bool = True) -> float:
        """Return statutory tax and regulatory exchange fee rate."""
        mkt = (market or "").upper()
        fee = self.cfg.us_brokerage_fee_rate if mkt in ("SP500", "NASDAQ", "RUSSELL2000", "NYSE") else self.cfg.brokerage_fee_rate
        if not is_sell:
            return fee
        if mkt == "KOSPI":
            return self.cfg.kospi_stt_rate + fee
        elif mkt == "KOSDAQ":
            return self.cfg.kosdaq_stt_rate + fee
        elif mkt in ("SP500", "NASDAQ", "RUSSELL2000", "NYSE"):
            return self.cfg.us_sec_rate + fee
        return self.cfg.kospi_stt_rate + fee

    def calculate_bid_ask_spread(self, volatility: float, price: float, market: str = "KOSPI") -> float:
        """Estimate half-spread percentage based on price & volatility."""
        if price <= 0:
            return self.cfg.base_spread_pct
        mkt = (market or "").upper()
        threshold = 20.0 if mkt in ("SP500", "NASDAQ", "RUSSELL2000", "NYSE") else 10000.0
        price_factor = 1.0 + max(0.0, (threshold - price) / threshold) if price < threshold else 1.0
        spread = max(self.cfg.base_spread_pct, (0.0002 + (volatility * 0.02)) * price_factor)
        return float(spread)

    def calculate_market_impact(self, order_amount: float, adv: float, volatility: float) -> float:
        """Square-root market impact cost using daily volatility: Impact = gamma * daily_vol * sqrt(Order / ADV)."""
        if adv <= 0 or order_amount <= 0:
            return 0.0005  # 5 bps fallback
        participation_rate = min(1.0, order_amount / adv)
        daily_vol = max(0.005, volatility / math.sqrt(252.0))
        impact = self.cfg.market_impact_gamma * daily_vol * math.sqrt(participation_rate)
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
        spread = self.calculate_bid_ask_spread(volatility, price, market=market)
        impact = self.calculate_market_impact(order_amount, adv, volatility)
        total_cost = tax + (0.5 * spread) + impact
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
