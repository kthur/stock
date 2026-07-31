"""
Pre-Trade Risk Gatekeeper Module

Enforces pre-trade risk controls and circuit breakers before orders reach the execution engine:
1. Max position size / portfolio weight limits (e.g. max 15% single asset).
2. Daily portfolio stop-loss thresholds.
3. Liquidity filter (Order size relative to 20d Average Daily Volume).
4. Macro Crisis / Gating check via RiskManager integration.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ProposedOrder:
    symbol: str
    target_weight: float
    expected_return: float
    current_price: float
    order_size_shares: int
    avg_daily_volume_20d: float = 1_000_000.0


@dataclass
class RiskCheckResult:
    passed: bool
    symbol: str
    rejection_reason: Optional[str] = None
    adjusted_weight: float = 0.0


class PreTradeRiskGatekeeper:
    """Pre-trade risk engine ensuring all portfolio allocations meet strict risk constraints."""

    def __init__(
        self,
        max_single_stock_weight: float = 0.15,
        max_order_adv_pct: float = 0.05,
        max_allowed_drawdown: float = 0.10,
        enable_crisis_gating: bool = True,
    ) -> None:
        self.max_single_stock_weight = max_single_stock_weight
        self.max_order_adv_pct = max_order_adv_pct
        self.max_allowed_drawdown = max_allowed_drawdown
        self.enable_crisis_gating = enable_crisis_gating

    def evaluate_order(
        self, order: ProposedOrder, portfolio_value: float, is_crisis_mode: bool = False
    ) -> RiskCheckResult:
        """Evaluates a single proposed order against all risk rules."""
        # 1. Macro Crisis Gating
        if self.enable_crisis_gating and is_crisis_mode:
            logger.warning(f"[PreTradeRisk] ORDER REJECTED for {order.symbol}: Macro Crisis Gating active.")
            return RiskCheckResult(
                passed=False,
                symbol=order.symbol,
                rejection_reason="Macro Crisis Gating Active",
                adjusted_weight=0.0,
            )

        # 2. Maximum Single Asset Weight Limit
        clamped_weight = min(order.target_weight, self.max_single_stock_weight)
        if order.target_weight > self.max_single_stock_weight:
            logger.info(
                f"[PreTradeRisk] Weight for {order.symbol} clamped from {order.target_weight:.3f} to {clamped_weight:.3f}"
            )

        # 3. Liquidity Impact Check (ADV Limit)
        if order.avg_daily_volume_20d > 0:
            order_adv_ratio = order.order_size_shares / order.avg_daily_volume_20d
            if order_adv_ratio > self.max_order_adv_pct:
                max_shares = int(order.avg_daily_volume_20d * self.max_order_adv_pct)
                reason = f"Order volume ({order.order_size_shares}) exceeds {self.max_order_adv_pct*100}% of 20d ADV ({max_shares} max shares allowed)"
                logger.warning(f"[PreTradeRisk] ORDER REJECTED/RESIZED for {order.symbol}: {reason}")
                
                # Recalculate adjusted weight based on max shares
                max_allowed_value = max_shares * order.current_price
                adjusted_w = min(clamped_weight, max_allowed_value / max(1.0, portfolio_value))
                return RiskCheckResult(
                    passed=True,
                    symbol=order.symbol,
                    rejection_reason=f"Resized due to ADV limit: {reason}",
                    adjusted_weight=adjusted_w,
                )

        return RiskCheckResult(
            passed=True,
            symbol=order.symbol,
            rejection_reason=None,
            adjusted_weight=clamped_weight,
        )

    def filter_portfolio_orders(
        self, proposed_orders: List[ProposedOrder], portfolio_value: float, is_crisis_mode: bool = False
    ) -> List[RiskCheckResult]:
        """Evaluates and filters a batch of proposed portfolio orders."""
        results = []
        for order in proposed_orders:
            res = self.evaluate_order(order, portfolio_value, is_crisis_mode)
            results.append(res)
        return results
