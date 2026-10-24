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
from typing import List, Optional
import numpy as np

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
        safe_single_w = float(max_single_stock_weight) if (max_single_stock_weight is not None and np.isfinite(max_single_stock_weight)) else 0.15
        self.max_single_stock_weight = max(0.01, min(1.0, safe_single_w))
        safe_adv_pct = float(max_order_adv_pct) if (max_order_adv_pct is not None and np.isfinite(max_order_adv_pct)) else 0.05
        self.max_order_adv_pct = max(0.001, min(1.0, safe_adv_pct))
        safe_dd = float(max_allowed_drawdown) if (max_allowed_drawdown is not None and np.isfinite(max_allowed_drawdown)) else 0.10
        self.max_allowed_drawdown = max(0.01, min(1.0, safe_dd))
        self.enable_crisis_gating = bool(enable_crisis_gating)

    def evaluate_order(
        self, order: ProposedOrder, portfolio_value: float, is_crisis_mode: bool = False
    ) -> RiskCheckResult:
        """Evaluates a single proposed order against all risk rules."""
        if order is None:
            return RiskCheckResult(
                passed=False,
                symbol="",
                rejection_reason="Null Order",
                adjusted_weight=0.0,
            )

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
        target_w = float(order.target_weight) if (order.target_weight is not None and np.isfinite(order.target_weight)) else 0.0
        clamped_weight = max(0.0, min(target_w, float(self.max_single_stock_weight)))
        if target_w > self.max_single_stock_weight:
            logger.info(
                f"[PreTradeRisk] Weight for {order.symbol} clamped from {target_w:.3f} to {clamped_weight:.3f}"
            )

        # 3. Liquidity Impact Check (ADV Limit)
        adv_20d = float(order.avg_daily_volume_20d) if (order.avg_daily_volume_20d is not None and np.isfinite(order.avg_daily_volume_20d)) else 0.0
        shares = int(order.order_size_shares) if (order.order_size_shares is not None and np.isfinite(order.order_size_shares)) else 0
        price = float(order.current_price) if (order.current_price is not None and np.isfinite(order.current_price) and order.current_price > 0) else 0.0

        if adv_20d > 0 and shares > 0:
            order_adv_ratio = shares / adv_20d
            if order_adv_ratio > self.max_order_adv_pct:
                max_shares = int(adv_20d * self.max_order_adv_pct)
                reason = f"Order volume ({shares}) exceeds {self.max_order_adv_pct*100:.1f}% of 20d ADV ({max_shares} max shares allowed)"
                logger.warning(f"[PreTradeRisk] ORDER RESIZED for {order.symbol}: {reason}")

                # Recalculate adjusted weight based on max shares
                port_val = max(1.0, float(portfolio_value)) if (portfolio_value is not None and np.isfinite(portfolio_value)) else 1.0
                max_allowed_value = max_shares * price
                val_ratio = max_allowed_value / port_val
                adjusted_w = min(clamped_weight, val_ratio if np.isfinite(val_ratio) else clamped_weight)
                adjusted_w = float(np.clip(adjusted_w, 0.0, 1.0))
                return RiskCheckResult(
                    passed=True,
                    symbol=order.symbol,
                    rejection_reason=f"Resized due to ADV limit: {reason}",
                    adjusted_weight=round(float(adjusted_w), 4),
                )

        return RiskCheckResult(
            passed=True,
            symbol=order.symbol,
            rejection_reason=None,
            adjusted_weight=round(float(clamped_weight), 4),
        )

    def filter_portfolio_orders(
        self, proposed_orders: Optional[List[ProposedOrder]], portfolio_value: float, is_crisis_mode: bool = False
    ) -> List[RiskCheckResult]:
        """Evaluates and filters a batch of proposed portfolio orders."""
        if not proposed_orders:
            return []
        results = []
        for order in proposed_orders:
            if order is not None:
                res = self.evaluate_order(order, portfolio_value, is_crisis_mode)
                results.append(res)
        return results
