"""Distributed Order Manager — split large orders into tranches for better entry/exit."""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.core.order_management import Order, OrderManagementSystem, OrderStatus, OrderType

logger = logging.getLogger(__name__)


@dataclass
class DistributedOrderConfig:
    """Configuration for distributed order splitting."""

    n_tranches_buy: int = 4
    n_tranches_sell: int = 3
    buy_spread_pct: float = 0.02
    sell_spread_pct: float = 0.025
    buy_allocation: Tuple[float, ...] = (0.30, 0.27, 0.23, 0.20)
    sell_allocation: Tuple[float, ...] = (0.40, 0.35, 0.25)


def _normalize(allocation: Tuple[float, ...], n: int) -> List[float]:
    """Ensure the allocation tuple matches *n* and sums to 1.0."""
    if n <= 0:
        return []
    alloc = []
    for a in allocation[:n]:
        try:
            a_val = float(a)
            alloc.append(max(0.0, a_val) if math.isfinite(a_val) else 0.0)
        except (ValueError, TypeError):
            alloc.append(0.0)
    if len(alloc) < n:
        alloc += [0.0] * (n - len(alloc))
    s = sum(alloc)
    if s <= 0 or not math.isfinite(s):
        alloc = [1.0 / n] * n
    else:
        alloc = [a / s for a in alloc]
    return alloc


def _build_buy_levels(
    center_price: float,
    n: int,
    spread_pct: float,
    allocation: Tuple[float, ...],
) -> List[Dict]:
    """Generate price/quantity levels for a distributed buy.

    Prices descend below *center_price* so earlier (lower-index) orders
    are closer to market and later orders are deeper discounts.
    """
    alloc = _normalize(allocation, n)
    levels: List[Dict] = []
    try:
        cp_val = float(center_price)
        cp = max(0.0, cp_val) if math.isfinite(cp_val) else 0.0
    except (ValueError, TypeError):
        cp = 0.0
    try:
        sp_val = float(spread_pct)
        sp = max(0.0, sp_val) if math.isfinite(sp_val) else 0.02
    except (ValueError, TypeError):
        sp = 0.02

    for i in range(n):
        offset = max(0.01, 1.0 - sp * i)
        levels.append(
            {
                "price": round(cp * offset, 2),
                "frac": alloc[i],
            }
        )
    return levels


def _build_sell_levels(
    center_price: float,
    n: int,
    spread_pct: float,
    allocation: Tuple[float, ...],
) -> List[Dict]:
    """Generate price/quantity levels for a distributed sell.

    Prices ascend above *center_price* so earlier orders capture smaller
    gains and later orders capture larger gains.
    """
    alloc = _normalize(allocation, n)
    levels: List[Dict] = []
    try:
        cp_val = float(center_price)
        cp = max(0.0, cp_val) if math.isfinite(cp_val) else 0.0
    except (ValueError, TypeError):
        cp = 0.0
    try:
        sp_val = float(spread_pct)
        sp = max(0.0, sp_val) if math.isfinite(sp_val) else 0.025
    except (ValueError, TypeError):
        sp = 0.025

    for i in range(n):
        offset = 1.0 + sp * (i + 1)
        levels.append(
            {
                "price": round(cp * offset, 2),
                "frac": alloc[i],
            }
        )
    return levels


class DistributedOrderManager:
    """Manages splitting of large buy/sell orders into multiple tranches.

    Usage
    -----
    dom = DistributedOrderManager(order_mgmt)
    orders = await dom.create_distributed_buy("AAPL", 300, 150.0)
    for o in orders:
        await order_mgmt.submit_order(o)
    """

    def __init__(
        self,
        order_management: OrderManagementSystem,
        config: Optional[DistributedOrderConfig] = None,
    ):
        self.oms = order_management
        self.cfg = config or DistributedOrderConfig()

    # ── Public API ──────────────────────────────────────────────────────────

    def create_distributed_buy(
        self,
        symbol: str,
        total_quantity: int,
        center_price: float,
        stop_loss_price: float,
        take_profit_price: float,
    ) -> List[Order]:
        """Split a buy order into *n* limit orders at descending prices.

        Returns the list of entry orders (already registered in OMS).
        """
        if total_quantity <= 0 or center_price <= 0:
            return []

        levels = _build_buy_levels(
            center_price,
            self.cfg.n_tranches_buy,
            self.cfg.buy_spread_pct,
            self.cfg.buy_allocation,
        )
        return self._create_tranches(symbol, OrderType.BUY, total_quantity, levels, stop_loss_price, take_profit_price)

    def create_distributed_sell(
        self,
        symbol: str,
        total_quantity: int,
        center_price: float,
        stop_loss_price: float,
        take_profit_price: float,
    ) -> List[Order]:
        """Split a sell order into *n* limit orders at ascending prices.

        Returns the list of entry orders (already registered in OMS).
        """
        if total_quantity <= 0 or center_price <= 0:
            return []

        levels = _build_sell_levels(
            center_price,
            self.cfg.n_tranches_sell,
            self.cfg.sell_spread_pct,
            self.cfg.sell_allocation,
        )
        return self._create_tranches(symbol, OrderType.SELL, total_quantity, levels, stop_loss_price, take_profit_price)

    def cancel_all_for_symbol(self, symbol: str) -> int:
        """Cancel every pending/submitted order for *symbol*."""
        cancelled = 0
        for o in list(self.oms.orders.values()):
            if o.symbol == symbol and o.status in (
                OrderStatus.PENDING,
                OrderStatus.SUBMITTED,
                OrderStatus.PARTIALLY_FILLED,
            ):
                o.status = OrderStatus.CANCELLED
                cancelled += 1
        return cancelled

    # ── Internal helpers ────────────────────────────────────────────────────

    def _create_tranches(
        self,
        symbol: str,
        order_type: OrderType,
        total_quantity: int,
        levels: List[Dict],
        stop_loss_price: float,
        take_profit_price: float,
    ) -> List[Order]:
        if not levels or total_quantity <= 0:
            return []

        # For very small quantities, fold everything into a single tranche
        if total_quantity < len(levels):
            levels = [levels[0]]

        center_price = levels[0]["price"] or 1e-8
        q_remaining = total_quantity
        orders: List[Order] = []

        for idx, level in enumerate(levels):
            is_last = idx == len(levels) - 1
            q = int(round(total_quantity * level["frac"]))
            if is_last:
                q = q_remaining
            elif q_remaining - (len(levels) - idx - 1) < q:
                q = max(0, q_remaining - (len(levels) - idx - 1))
            elif q <= 0 and q_remaining > 0:
                q = 1
            q = max(0, q)
            if q <= 0:
                continue

            q_remaining -= q
            entry_price = level["price"]

            entry = self.oms.create_order(symbol, order_type, q, entry_price)
            orders.append(entry)

            # Per-tranche stop-loss / take-profit scaled to this entry price
            ratio = entry_price / center_price
            sl_price = round(stop_loss_price * ratio, 2)
            tp_price = round(take_profit_price * ratio, 2)

            sl_order = self.oms.create_stop_loss_order(
                symbol,
                q,
                sl_price,
                entry.order_id,
            )
            tp_order = self.oms.create_take_profit_order(
                symbol,
                q,
                tp_price,
                entry.order_id,
            )
            orders.extend([sl_order, tp_order])

            logger.info(
                "Tranche %d/%d: %s %s x%d @ %.2f (SL=%.2f TP=%.2f)",
                idx + 1,
                len(levels),
                symbol,
                order_type.value,
                q,
                entry_price,
                sl_price,
                tp_price,
            )

        return orders
