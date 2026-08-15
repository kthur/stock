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
    kospi_stt_rate: float = 0.0015     # 0.15% STT (current statutory rate)
    kosdaq_stt_rate: float = 0.0018    # 0.18% STT
    konex_stt_rate: float = 0.0008     # 0.08% STT
    brokerage_fee_rate: float = 0.00030 # 0.030% brokerage fee
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
        elif mkt == "KONEX":
            return self.cfg.konex_stt_rate + fee
        elif mkt in ("SP500", "NASDAQ", "RUSSELL2000", "NYSE"):
            return self.cfg.us_sec_rate + fee
        return self.cfg.kospi_stt_rate + fee

    def calculate_bid_ask_spread(self, volatility: float, price: float, market: str = "KOSPI") -> float:
        """Estimate half-spread percentage based on price & volatility."""
        p = float(price) if (price is not None and math.isfinite(price) and price > 0) else 0.0
        if p <= 0:
            return float(self.cfg.base_spread_pct)
        vol = max(0.001, float(volatility)) if (volatility is not None and math.isfinite(volatility) and volatility > 0) else 0.20
        mkt = (market or "").upper()
        threshold = 20.0 if mkt in ("SP500", "NASDAQ", "RUSSELL2000", "NYSE") else 10000.0
        price_factor = 1.0 + max(0.0, (threshold - p) / threshold) if p < threshold else 1.0
        spread = max(self.cfg.base_spread_pct, (0.0002 + (vol * 0.02)) * price_factor)
        return float(spread)

    def calculate_market_impact(self, order_amount: float, adv: float, volatility: float) -> float:
        """Square-root market impact cost using daily volatility: Impact = gamma * daily_vol * sqrt(Order / ADV)."""
        amt = float(order_amount) if (order_amount is not None and math.isfinite(order_amount) and order_amount > 0) else 0.0
        adv_val = float(adv) if (adv is not None and math.isfinite(adv) and adv > 0) else 0.0
        vol = max(0.001, float(volatility)) if (volatility is not None and math.isfinite(volatility) and volatility > 0) else 0.20

        if adv_val <= 0 or amt <= 0:
            return 0.0005  # 5 bps fallback
        participation_rate = min(1.0, amt / adv_val)
        daily_vol = max(0.005, vol / math.sqrt(252.0))
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
        gross = float(gross_return) if (gross_return is not None and math.isfinite(gross_return)) else 0.0
        return float(gross - friction)
