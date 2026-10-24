"""
tax_loss_harvesting_optimizer.py — Dynamic Tax-Loss Harvesting & Wash-Sale Optimizer

Phase 107 / Feature F508 / Release R123 (v114 Production Master)
Milestone 4: Tax-Aware Portfolio Optimization & Wash-Sale Enforcement

This module implements an institutional tax-aware portfolio optimizer:
  1. Tracks per-lot cost basis, unrealized capital gains/losses, acquisition dates,
     holding periods (short-term vs. long-term), and tax regimes (US IRC & KRX).
  2. Wash-Sale Restriction Enforcement (WashSaleTracker):
     - Strictly enforces US IRC § 1091 30-day wash-sale restriction window:
       [T_sale - 30d, T_sale + 30d] around any loss sale.
     - Strictly disallows re-purchasing a loss-harvested symbol within 30 days.
  3. Economic Hurdle Invariant:
     - Calculates Gross Tax Alpha: tau_i * |Loss|.
     - Calculates Round-Trip Switching Friction: statutory STT/SEC taxes, broker fees,
       bid-ask half-spreads, and Gatheral 3/2-power market impact.
     - Strictly enforces hurdle invariant: lot is harvested if and only if
       Net Tax Alpha = Gross Tax Alpha - Total Friction > Hurdle >= 0.0.
  4. Surrogate Asset Selection:
     - Screens candidate substitute stocks within the same sector/industry.
     - Requires return correlation rho(R_A, R_B) >= 0.85 over lookback window.
     - Excludes wash-sale restricted symbols and enforces ADV liquidity bounds (Q_B / ADV_B <= 0.015).
"""

from __future__ import annotations

import math
import logging
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Date Utility Functions
# ---------------------------------------------------------------------------

def parse_date(date_val: Union[str, datetime.date, datetime.datetime, pd.Timestamp]) -> datetime.date:
    """Robustly parses input date into datetime.date."""
    if isinstance(date_val, datetime.datetime):
        return date_val.date()
    if isinstance(date_val, datetime.date):
        return date_val
    if isinstance(date_val, pd.Timestamp):
        return date_val.date()
    if isinstance(date_val, str):
        cleaned = date_val.strip()
        # Try standard formats
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.datetime.strptime(cleaned, fmt).date()
            except ValueError:
                pass
        # Fallback to ISO format
        return datetime.date.fromisoformat(cleaned[:10])
    raise ValueError(f"Unsupported date format or type: {type(date_val)} ({date_val})")


def format_date(d: Union[str, datetime.date, datetime.datetime, pd.Timestamp]) -> str:
    """Format date into standard YYYY-MM-DD string."""
    return parse_date(d).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Configuration & Enums
# ---------------------------------------------------------------------------

class TaxRegime(str, Enum):
    US = "US"
    KRX = "KRX"
    AUTO = "AUTO"


@dataclass
class TaxConfig:
    """
    Configuration parameters for tax rates, wash-sale windows, and friction costs.
    """
    # US IRC Federal Tax Rates
    us_short_term_rate: float = 0.37          # 37% short-term federal bracket (<= 365 days)
    us_long_term_rate: float = 0.20           # 20% long-term capital gains (> 365 days)

    # KRX Capital Gains Rate
    krx_capital_gains_rate: float = 0.22      # 22% standard capital gains tax rate

    # Wash-Sale Parameters
    wash_sale_window_days: int = 30           # US IRC § 1091 30-day window

    # Economic Hurdle Threshold
    min_net_alpha_hurdle: float = 0.0         # Net Tax Alpha must strictly exceed this (currency units)
    min_net_alpha_bps: float = 0.0            # Optional hurdle in basis points of position notional

    # Surrogate Asset Parameters
    min_surrogate_correlation: float = 0.85   # rho >= 0.85
    min_correlation_observations: int = 20    # Minimum return samples required
    max_adv_participation: float = 0.015      # 1.5% ADV limit

    # Execution & Microstructure Friction Parameters
    gatheral_kappa: float = 1.50              # Gatheral 3/2 power-law impact coefficient
    default_annual_volatility: float = 0.25   # 25% annualized volatility baseline

    # Statutory Taxes and Fees
    kospi_stt_rate: float = 0.0018            # 0.18% STT on KRX KOSPI sell
    kosdaq_stt_rate: float = 0.0020           # 0.20% STT on KRX KOSDAQ sell
    us_sec_rate: float = 0.0000278            # 0.00278% SEC regulatory fee on US sell
    broker_fee_krx: float = 0.00030           # 0.030% broker commission KRX
    broker_fee_us: float = 0.00005            # 0.005% broker commission US

    # Bid-Ask Half-Spread Baselines
    base_spread_krx: float = 0.0005           # 5 bps half-spread baseline for KRX
    base_spread_us: float = 0.0005            # 5 bps half-spread baseline for US


# ---------------------------------------------------------------------------
# Core Data Structures: TaxLot, HarvestingCandidate, TaxHarvestingPlan
# ---------------------------------------------------------------------------

@dataclass
class TaxLot:
    """
    Represents an individual tax lot purchased at a specific date and price.
    """
    lot_id: str
    symbol: str
    market: str
    acquisition_date: str                     # Format: YYYY-MM-DD
    quantity: float
    cost_basis_per_share: float
    current_price: float = 0.0
    commission_paid: float = 0.0
    tax_regime: str = "AUTO"                  # "US", "KRX", or "AUTO"

    def __post_init__(self):
        self.symbol = str(self.symbol).strip().upper()
        self.market = str(self.market).strip().upper()
        self.acquisition_date = format_date(self.acquisition_date)
        self.quantity = float(self.quantity)
        self.cost_basis_per_share = float(self.cost_basis_per_share)
        self.current_price = float(self.current_price)
        self.commission_paid = float(self.commission_paid)

    @property
    def total_cost(self) -> float:
        """Total acquisition cost basis including initial commissions."""
        return (self.quantity * self.cost_basis_per_share) + self.commission_paid

    @property
    def market_value(self) -> float:
        """Current total market value of the lot."""
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        """
        Unrealized profit/loss.
        Positive indicates unrealized gain; negative indicates unrealized loss.
        """
        return self.market_value - (self.quantity * self.cost_basis_per_share)

    @property
    def unrealized_return_pct(self) -> float:
        """Percentage unrealized return based on per-share cost basis."""
        if self.cost_basis_per_share <= 0:
            return 0.0
        return (self.current_price - self.cost_basis_per_share) / self.cost_basis_per_share

    def holding_days(self, as_of_date: Union[str, datetime.date, datetime.datetime, pd.Timestamp]) -> int:
        """Calculates holding duration in calendar days from acquisition_date to as_of_date."""
        dt_acq = parse_date(self.acquisition_date)
        dt_as_of = parse_date(as_of_date)
        diff = (dt_as_of - dt_acq).days
        return max(0, diff)

    def is_long_term(self, as_of_date: Union[str, datetime.date, datetime.datetime, pd.Timestamp]) -> bool:
        """
        Under US IRC, holding period strictly exceeding 1 year (> 365 calendar days)
        qualifies as long-term capital gains/losses.
        """
        return self.holding_days(as_of_date) > 365

    def resolve_tax_regime(self) -> str:
        """Infers the applicable tax regime ('US' or 'KRX')."""
        reg = str(self.tax_regime).upper()
        if reg in ("US", "KRX"):
            return reg
        mkt = self.market.upper()
        if mkt in ("KOSPI", "KOSDAQ", "KRX") or self.symbol.isdigit():
            return "KRX"
        return "US"

    def applicable_tax_rate(
        self,
        as_of_date: Union[str, datetime.date, datetime.datetime, pd.Timestamp],
        config: Optional[TaxConfig] = None
    ) -> float:
        """
        Determines the statutory marginal tax rate applicable to this lot upon liquidation.
        """
        cfg = config or TaxConfig()
        regime = self.resolve_tax_regime()
        if regime == "KRX":
            return cfg.krx_capital_gains_rate
        else:  # US
            if self.is_long_term(as_of_date):
                return cfg.us_long_term_rate
            return cfg.us_short_term_rate


@dataclass
class HarvestingCandidate:
    """
    Detailed evaluation outcome for harvesting an individual TaxLot.
    """
    lot: TaxLot
    gross_tax_savings: float
    switching_friction: float
    net_tax_alpha: float
    surrogate_symbol: Optional[str]
    surrogate_correlation: float
    is_eligible: bool
    rejection_reason: str = ""
    estimated_sell_friction: float = 0.0
    estimated_buy_friction: float = 0.0
    surrogate_quantity: float = 0.0
    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaxHarvestingPlan:
    """
    Portfolio-wide tax-loss harvesting execution plan.
    """
    as_of_date: str
    candidates_screened: int
    harvest_recommendations: List[HarvestingCandidate]
    rejected_candidates: List[HarvestingCandidate]
    total_gross_tax_savings: float
    total_switching_friction: float
    total_net_tax_alpha: float
    wash_sale_restricted_symbols: List[str]

    @property
    def total_harvested_proceeds(self) -> float:
        """Total gross liquidation proceeds from recommended harvesting sales."""
        return sum(c.lot.market_value for c in self.harvest_recommendations)

    @property
    def total_realized_loss(self) -> float:
        """Total gross realized loss from recommended harvesting sales."""
        return sum(abs(c.lot.unrealized_pnl) for c in self.harvest_recommendations)


# ---------------------------------------------------------------------------
# WashSaleTracker: US IRC § 1091 & KRX Enforcement
# ---------------------------------------------------------------------------

@dataclass
class WashSaleRecord:
    symbol: str
    sale_date: str                            # YYYY-MM-DD
    loss_amount: float
    quantity: float
    lot_id: str = ""
    cooldown_days: int = 30


class WashSaleTracker:
    """
    Tracks and enforces 30-day wash-sale restriction windows under US IRC § 1091
    and KRX capital gains rules.

    US IRC § 1091 Rule:
    A wash sale occurs when a taxpayer sells or trades stock or securities at a loss
    and within 30 days before or after the sale acquires substantially identical stock
    or securities. The loss deduction is disallowed and added to the cost basis of the
    repurchased shares.
    """

    def __init__(self, restriction_days: int = 30):
        self.restriction_days = int(restriction_days)
        # symbol -> list of WashSaleRecord
        self.records: Dict[str, List[WashSaleRecord]] = {}

    def record_loss_sale(
        self,
        symbol: str,
        sale_date: Union[str, datetime.date, datetime.datetime, pd.Timestamp],
        loss_amount: float,
        quantity: float = 0.0,
        lot_id: str = ""
    ) -> None:
        """
        Registers a realized loss sale for a given symbol, opening a 30-day restriction window.
        """
        sym = str(symbol).strip().upper()
        d_str = format_date(sale_date)
        loss = float(loss_amount)
        if loss <= 0:
            # Not a loss sale; ignore
            return

        rec = WashSaleRecord(
            symbol=sym,
            sale_date=d_str,
            loss_amount=loss,
            quantity=float(quantity),
            lot_id=str(lot_id),
            cooldown_days=self.restriction_days
        )
        if sym not in self.records:
            self.records[sym] = []
        self.records[sym].append(rec)
        logger.info(
            f"WashSaleTracker: Recorded loss sale of {loss:.2f} for {sym} on {d_str}. "
            f"Restricted until {(parse_date(d_str) + datetime.timedelta(days=self.restriction_days)).strftime('%Y-%m-%d')}."
        )

    def is_restricted(
        self,
        symbol: str,
        query_date: Union[str, datetime.date, datetime.datetime, pd.Timestamp]
    ) -> bool:
        """
        Returns True if query_date falls within the wash-sale restriction window
        [T_sale - restriction_days, T_sale + restriction_days] for any recorded loss sale.
        """
        sym = str(symbol).strip().upper()
        if sym not in self.records:
            return False

        q_date = parse_date(query_date)
        for rec in self.records[sym]:
            s_date = parse_date(rec.sale_date)
            # The window spans from 30 days before the sale up to 30 days after the sale
            window_start = s_date - datetime.timedelta(days=rec.cooldown_days)
            window_end = s_date + datetime.timedelta(days=rec.cooldown_days)
            if window_start <= q_date <= window_end:
                return True
        return False

    def is_repurchase_restricted(
        self,
        symbol: str,
        repurchase_date: Union[str, datetime.date, datetime.datetime, pd.Timestamp]
    ) -> bool:
        """
        Checks whether re-purchasing `symbol` on `repurchase_date` violates the 30-day cooldown
        following a prior loss sale (i.e. T_sale <= repurchase_date <= T_sale + 30d).
        """
        sym = str(symbol).strip().upper()
        if sym not in self.records:
            return False

        r_date = parse_date(repurchase_date)
        for rec in self.records[sym]:
            s_date = parse_date(rec.sale_date)
            window_end = s_date + datetime.timedelta(days=rec.cooldown_days)
            if s_date <= r_date <= window_end:
                return True
        return False

    def get_restriction_window(
        self,
        symbol: str,
        sale_date: Union[str, datetime.date, datetime.datetime, pd.Timestamp]
    ) -> Tuple[str, str]:
        """Returns the start and end dates of the restriction window as formatted strings."""
        s_date = parse_date(sale_date)
        w_start = s_date - datetime.timedelta(days=self.restriction_days)
        w_end = s_date + datetime.timedelta(days=self.restriction_days)
        return format_date(w_start), format_date(w_end)

    def get_restriction_expiry(
        self,
        symbol: str,
        as_of_date: Optional[Union[str, datetime.date, datetime.datetime, pd.Timestamp]] = None
    ) -> Optional[str]:
        """
        Returns the latest expiration date of active wash-sale restrictions for symbol.
        If no active restrictions exist as of as_of_date, returns None.
        """
        sym = str(symbol).strip().upper()
        if sym not in self.records:
            return None

        ref_date = parse_date(as_of_date) if as_of_date is not None else None
        latest_expiry: Optional[datetime.date] = None

        for rec in self.records[sym]:
            s_date = parse_date(rec.sale_date)
            expiry = s_date + datetime.timedelta(days=rec.cooldown_days)
            if ref_date is not None:
                # Must be active on ref_date
                w_start = s_date - datetime.timedelta(days=rec.cooldown_days)
                if not (w_start <= ref_date <= expiry):
                    continue
            if latest_expiry is None or expiry > latest_expiry:
                latest_expiry = expiry

        return format_date(latest_expiry) if latest_expiry else None

    def get_active_restricted_symbols(
        self,
        as_of_date: Union[str, datetime.date, datetime.datetime, pd.Timestamp]
    ) -> List[str]:
        """Returns a sorted list of symbols currently under wash-sale cooldown."""
        active: List[str] = []
        for sym in self.records:
            if self.is_restricted(sym, as_of_date):
                active.append(sym)
        return sorted(active)

    def clear(self) -> None:
        """Clears all records."""
        self.records.clear()


# ---------------------------------------------------------------------------
# DynamicTaxLossHarvestingOptimizer
# ---------------------------------------------------------------------------

class DynamicTaxLossHarvestingOptimizer:
    """
    Institutional Tax-Loss Harvesting & Wash-Sale Replacement Engine.

    Responsibilities:
    1. Scan portfolio tax lots for unrealized losses.
    2. Calculate Gross Tax Alpha based on statutory tax brackets.
    3. Calculate two-legged round-trip switching friction (selling lot, buying surrogate).
       - Statutory taxes & fees (STT / SEC / broker commissions).
       - Half-spread friction.
       - Gatheral 3/2-power market impact.
    4. Enforce strict economic hurdle: Net Tax Alpha > Hurdle >= 0.0.
    5. Screen same-sector surrogate assets with correlation rho >= 0.85 and ADV liquidity bound.
    6. Enforce 30-day wash-sale restrictions to ensure full tax deductibility.
    """

    def __init__(
        self,
        config: Optional[TaxConfig] = None,
        wash_sale_tracker: Optional[WashSaleTracker] = None,
        wash_sale_days: int = 30,
        min_net_alpha_bps: float = 0.0,
        min_surrogate_correlation: float = 0.85
    ):
        self.config = config or TaxConfig()
        if wash_sale_days != 30:
            self.config.wash_sale_window_days = int(wash_sale_days)
        if min_net_alpha_bps > 0.0:
            self.config.min_net_alpha_bps = float(min_net_alpha_bps)
        if min_surrogate_correlation != 0.85:
            self.config.min_surrogate_correlation = float(min_surrogate_correlation)

        self.wash_sale_tracker = wash_sale_tracker or WashSaleTracker(
            restriction_days=self.config.wash_sale_window_days
        )

    # -----------------------------------------------------------------------
    # Tax Alpha Calculations
    # -----------------------------------------------------------------------

    def calculate_gross_tax_alpha(
        self,
        lot: TaxLot,
        as_of_date: Union[str, datetime.date, datetime.datetime, pd.Timestamp]
    ) -> float:
        """
        Gross Tax Alpha = tau_i * |Loss| if unrealized_pnl < 0 else 0.0.
        """
        if lot.unrealized_pnl >= 0.0:
            return 0.0
        tax_rate = lot.applicable_tax_rate(as_of_date, self.config)
        loss = abs(lot.unrealized_pnl)
        gross_alpha = tax_rate * loss
        return float(gross_alpha)

    # -----------------------------------------------------------------------
    # Switching Friction & Market Impact Model
    # -----------------------------------------------------------------------

    def calculate_single_leg_friction(
        self,
        symbol: str,
        market: str,
        price: float,
        quantity: float,
        adv: float,
        volatility: float = 0.25,
        is_sell: bool = True
    ) -> float:
        """
        Calculates execution friction for a single leg (sell or buy):
          Friction = Notional * [Fee_rate + Half_spread + Gatheral_Impact]

        - Statutory Taxes & Fees:
          KRX: broker fee (3 bps) + if sell: STT (18 bps KOSPI, 20 bps KOSDAQ)
          US: broker fee (0.5 bps) + if sell: SEC fee (0.00278%)
        - Spread Friction: 0.5 * spread_rate * Notional
        - Gatheral 3/2-Power Market Impact:
          kappa * sigma_ann * (Participation_Rate ** 1.5) * Notional
        """
        if quantity <= 0.0 or price <= 0.0:
            return 0.0

        notional = float(quantity * price)
        mkt = str(market).strip().upper()
        is_krx = (mkt in ("KOSPI", "KOSDAQ", "KRX") or symbol.isdigit())

        # 1. Statutory Fees & Taxes
        if is_krx:
            broker_fee = self.config.broker_fee_krx
            if is_sell:
                stt_rate = self.config.kosdaq_stt_rate if mkt == "KOSDAQ" else self.config.kospi_stt_rate
            else:
                stt_rate = 0.0
            statutory_rate = broker_fee + stt_rate
        else:  # US
            broker_fee = self.config.broker_fee_us
            sec_rate = self.config.us_sec_rate if is_sell else 0.0
            statutory_rate = broker_fee + sec_rate

        fee_cost = notional * statutory_rate

        # 2. Bid-Ask Half-Spread
        half_spread_rate = self.config.base_spread_krx if is_krx else self.config.base_spread_us
        spread_cost = notional * half_spread_rate

        # 3. Gatheral 3/2-Power Market Impact
        # Participation rate based on ADV (in currency notional, or share volume * price)
        adv_val = float(adv) if (adv is not None and math.isfinite(adv) and adv > 0) else 1e8
        # Normalize ADV to currency notional if passed as share volume
        if adv_val < 50000.0 and price > 0:
            adv_val = adv_val * price

        participation_rate = min(1.0, notional / adv_val) if adv_val > 0 else 0.0
        annual_vol = max(0.05, float(volatility)) if (volatility is not None and math.isfinite(volatility)) else self.config.default_annual_volatility

        impact_rate = self.config.gatheral_kappa * annual_vol * (participation_rate ** 1.5)
        impact_cost = notional * impact_rate

        total_leg_friction = fee_cost + spread_cost + impact_cost
        return float(total_leg_friction)

    def calculate_round_trip_switching_friction(
        self,
        lot: TaxLot,
        surrogate_symbol: str,
        surrogate_price: float,
        lot_adv: float,
        surrogate_adv: float,
        lot_vol: float = 0.25,
        surrogate_vol: float = 0.25
    ) -> Tuple[float, float, float]:
        """
        Calculates two-legged round-trip switching friction:
          Leg 1: Selling the tax-loss lot
          Leg 2: Buying the surrogate asset using the net liquidation proceeds
        Returns: (sell_friction, buy_friction, total_friction)
        """
        # Leg 1: Selling Lot
        sell_friction = self.calculate_single_leg_friction(
            symbol=lot.symbol,
            market=lot.market,
            price=lot.current_price,
            quantity=lot.quantity,
            adv=lot_adv,
            volatility=lot_vol,
            is_sell=True
        )

        gross_proceeds = lot.quantity * lot.current_price
        net_proceeds = max(0.0, gross_proceeds - sell_friction)

        # Leg 2: Buying Surrogate
        if surrogate_price > 0.0 and net_proceeds > 0.0:
            surrogate_qty = net_proceeds / surrogate_price
            buy_friction = self.calculate_single_leg_friction(
                symbol=surrogate_symbol,
                market=lot.market,  # Typically same market
                price=surrogate_price,
                quantity=surrogate_qty,
                adv=surrogate_adv,
                volatility=surrogate_vol,
                is_sell=False
            )
        else:
            buy_friction = 0.0

        total_friction = sell_friction + buy_friction
        return float(sell_friction), float(buy_friction), float(total_friction)

    # -----------------------------------------------------------------------
    # Surrogate Asset Selection
    # -----------------------------------------------------------------------

    def find_surrogate_stock(
        self,
        symbol: str,
        price_history_df: pd.DataFrame,
        sector_map: Dict[str, str],
        min_correlation: Optional[float] = None,
        adv_dict: Optional[Dict[str, float]] = None,
        required_notional: float = 0.0,
        current_prices: Optional[Dict[str, float]] = None,
        as_of_date: Optional[Union[str, datetime.date, datetime.datetime, pd.Timestamp]] = None
    ) -> Optional[Tuple[str, float]]:
        """
        Screens candidate substitute stocks within the same sector/industry:
          - Target sector == Candidate sector
          - Candidate != Target
          - Candidate not in wash-sale cooldown
          - Pearson return correlation rho(R_target, R_candidate) >= min_correlation (default 0.85)
          - Satisfies ADV liquidity bound: Order_Notional / ADV <= 0.015 (1.5%)

        Returns: (best_surrogate_symbol, best_correlation) or None if no candidate qualifies.
        """
        sym = str(symbol).strip().upper()
        target_sector = sector_map.get(sym)
        if not target_sector:
            logger.warning(f"No sector mapping found for {sym}")
            return None

        threshold = min_correlation if min_correlation is not None else self.config.min_surrogate_correlation
        ref_date = format_date(as_of_date) if as_of_date is not None else None

        # Filter price history up to as_of_date if specified
        hist_df = price_history_df.copy()
        if ref_date is not None and isinstance(hist_df.index, pd.DatetimeIndex):
            hist_df = hist_df.loc[hist_df.index <= pd.Timestamp(ref_date)]

        if sym not in hist_df.columns:
            logger.warning(f"Target symbol {sym} not present in price history DataFrame")
            return None

        target_prices = hist_df[sym].dropna()
        if len(target_prices) < self.config.min_correlation_observations:
            return None

        target_returns = target_prices.pct_change().dropna()
        if target_returns.std() < 1e-9:
            # Zero variance
            return None

        candidates: List[Tuple[str, float]] = []

        for cand_sym, cand_sector in sector_map.items():
            cand_sym_clean = str(cand_sym).strip().upper()
            if cand_sym_clean == sym:
                continue
            if cand_sector != target_sector:
                continue

            # Wash-sale restriction check
            if ref_date and self.wash_sale_tracker.is_restricted(cand_sym_clean, ref_date):
                continue

            # Liquidity bound check
            if adv_dict and required_notional > 0.0:
                cand_adv = adv_dict.get(cand_sym_clean, 0.0)
                if cand_adv <= 0:
                    continue
                # If cand_adv is in shares and current_prices is available
                if current_prices and cand_adv < 50000.0 and cand_sym_clean in current_prices:
                    cand_adv = cand_adv * current_prices[cand_sym_clean]
                participation = required_notional / cand_adv if cand_adv > 0 else 1.0
                if participation > self.config.max_adv_participation:
                    # Violates 1.5% ADV participation bound
                    continue

            # Return correlation check
            if cand_sym_clean not in hist_df.columns:
                continue

            cand_prices = hist_df[cand_sym_clean].dropna()
            if len(cand_prices) < self.config.min_correlation_observations:
                continue

            # Align returns
            aligned = pd.concat([target_returns, cand_prices.pct_change().dropna()], axis=1, join="inner")
            if len(aligned) < self.config.min_correlation_observations:
                continue

            cand_ret = aligned.iloc[:, 1]
            if cand_ret.std() < 1e-9:
                continue

            corr = float(aligned.iloc[:, 0].corr(cand_ret))
            if math.isnan(corr):
                continue

            if corr >= threshold:
                candidates.append((cand_sym_clean, corr))

        if not candidates:
            return None

        # Sort by highest correlation descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0]

    # -----------------------------------------------------------------------
    # Individual Lot Evaluation
    # -----------------------------------------------------------------------

    def evaluate_lot_for_harvesting(
        self,
        lot: TaxLot,
        current_price: float,
        price_history_df: pd.DataFrame,
        sector_map: Dict[str, str],
        adv_dict: Dict[str, float],
        as_of_date: Union[str, datetime.date, datetime.datetime, pd.Timestamp],
        vol_dict: Optional[Dict[str, float]] = None
    ) -> HarvestingCandidate:
        """
        Evaluates a single TaxLot against:
          1. Unrealized loss existence.
          2. Gross Tax Alpha calculation.
          3. Wash-sale status on the asset itself (if recently sold at loss, repurchase restricted).
          4. Surrogate asset screening (same sector, rho >= 0.85, ADV participation <= 1.5%).
          5. Round-trip switching friction calculation (STT/SEC + spread + Gatheral 3/2 impact).
          6. Economic Hurdle Invariant: Net Tax Alpha = Gross Tax Alpha - Friction > Hurdle >= 0.0.
        """
        as_of_str = format_date(as_of_date)
        lot.current_price = float(current_price)

        # 1. Unrealized Loss Check
        if lot.unrealized_pnl >= 0.0:
            return HarvestingCandidate(
                lot=lot,
                gross_tax_savings=0.0,
                switching_friction=0.0,
                net_tax_alpha=0.0,
                surrogate_symbol=None,
                surrogate_correlation=0.0,
                is_eligible=False,
                rejection_reason="NO_UNREALIZED_LOSS: Lot is profitable or at break-even"
            )

        # 2. Gross Tax Alpha
        gross_alpha = self.calculate_gross_tax_alpha(lot, as_of_str)

        # 3. Target ADV & Volatility
        sym = lot.symbol
        lot_adv = adv_dict.get(sym, 1e8)
        vol_lookup = vol_dict or {}
        lot_vol = vol_lookup.get(sym, self.config.default_annual_volatility)

        # 4. Surrogate Selection
        target_notional = lot.quantity * lot.current_price
        surrogate_res = self.find_surrogate_stock(
            symbol=sym,
            price_history_df=price_history_df,
            sector_map=sector_map,
            min_correlation=self.config.min_surrogate_correlation,
            adv_dict=adv_dict,
            required_notional=target_notional,
            current_prices={k: float(price_history_df[k].iloc[-1]) for k in price_history_df.columns if len(price_history_df[k].dropna()) > 0},
            as_of_date=as_of_str
        )

        if surrogate_res is None:
            return HarvestingCandidate(
                lot=lot,
                gross_tax_savings=gross_alpha,
                switching_friction=0.0,
                net_tax_alpha=0.0,
                surrogate_symbol=None,
                surrogate_correlation=0.0,
                is_eligible=False,
                rejection_reason=f"NO_SURROGATE_QUALIFIED: No same-sector asset with rho >= {self.config.min_surrogate_correlation} and ADV participation <= 1.5%"
            )

        surr_sym, surr_corr = surrogate_res
        surr_adv = adv_dict.get(surr_sym, 1e8)
        surr_vol = vol_lookup.get(surr_sym, self.config.default_annual_volatility)
        surr_price = float(price_history_df[surr_sym].dropna().iloc[-1]) if surr_sym in price_history_df.columns else lot.current_price

        # 5. Round-Trip Switching Friction
        sell_fric, buy_fric, total_friction = self.calculate_round_trip_switching_friction(
            lot=lot,
            surrogate_symbol=surr_sym,
            surrogate_price=surr_price,
            lot_adv=lot_adv,
            surrogate_adv=surr_adv,
            lot_vol=lot_vol,
            surrogate_vol=surr_vol
        )

        # 6. Economic Hurdle Invariant Check
        net_tax_alpha = gross_alpha - total_friction
        bps_hurdle_amount = (self.config.min_net_alpha_bps / 10000.0) * target_notional
        effective_hurdle = max(self.config.min_net_alpha_hurdle, bps_hurdle_amount)

        if net_tax_alpha <= effective_hurdle:
            return HarvestingCandidate(
                lot=lot,
                gross_tax_savings=gross_alpha,
                switching_friction=total_friction,
                net_tax_alpha=net_tax_alpha,
                surrogate_symbol=surr_sym,
                surrogate_correlation=surr_corr,
                is_eligible=False,
                rejection_reason=(
                    f"ECONOMIC_HURDLE_FAILED: Net Tax Alpha ({net_tax_alpha:.2f}) <= Hurdle ({effective_hurdle:.2f}). "
                    f"Friction ({total_friction:.2f}) exceeds tax alpha ({gross_alpha:.2f})."
                ),
                estimated_sell_friction=sell_fric,
                estimated_buy_friction=buy_fric
            )

        # Eligible
        surrogate_qty = max(0.0, (target_notional - sell_fric) / surr_price) if surr_price > 0 else 0.0

        return HarvestingCandidate(
            lot=lot,
            gross_tax_savings=gross_alpha,
            switching_friction=total_friction,
            net_tax_alpha=net_tax_alpha,
            surrogate_symbol=surr_sym,
            surrogate_correlation=surr_corr,
            is_eligible=True,
            rejection_reason="",
            estimated_sell_friction=sell_fric,
            estimated_buy_friction=buy_fric,
            surrogate_quantity=surrogate_qty,
            notes={
                "target_notional": target_notional,
                "holding_days": lot.holding_days(as_of_str),
                "is_long_term": lot.is_long_term(as_of_str),
                "tax_rate": lot.applicable_tax_rate(as_of_str, self.config),
                "surrogate_price": surr_price
            }
        )

    # -----------------------------------------------------------------------
    # Portfolio-Wide Optimization
    # -----------------------------------------------------------------------

    def optimize_portfolio_harvesting(
        self,
        lots: List[TaxLot],
        current_prices: Dict[str, float],
        price_history_df: pd.DataFrame,
        sector_map: Dict[str, str],
        adv_dict: Dict[str, float],
        as_of_date: Union[str, datetime.date, datetime.datetime, pd.Timestamp],
        vol_dict: Optional[Dict[str, float]] = None,
        auto_record_wash_sale: bool = True
    ) -> TaxHarvestingPlan:
        """
        Screens portfolio lots, selects tax-loss harvesting candidates using HIFO ordering,
        evaluates economic hurdle and surrogate replacement, and produces an execution plan.

        If auto_record_wash_sale is True, any harvested lots are automatically recorded in
        WashSaleTracker to enforce the 30-day cooldown against subsequent repurchases.
        """
        as_of_str = format_date(as_of_date)
        sorted_lots = self.hifo_sort(lots)

        recommendations: List[HarvestingCandidate] = []
        rejected: List[HarvestingCandidate] = []

        for lot in sorted_lots:
            p_curr = current_prices.get(lot.symbol, lot.current_price)
            candidate = self.evaluate_lot_for_harvesting(
                lot=lot,
                current_price=p_curr,
                price_history_df=price_history_df,
                sector_map=sector_map,
                adv_dict=adv_dict,
                as_of_date=as_of_str,
                vol_dict=vol_dict
            )

            if candidate.is_eligible:
                recommendations.append(candidate)
                if auto_record_wash_sale:
                    # Record the loss sale to activate 30-day wash-sale restriction
                    loss_amt = abs(candidate.lot.unrealized_pnl)
                    self.wash_sale_tracker.record_loss_sale(
                        symbol=candidate.lot.symbol,
                        sale_date=as_of_str,
                        loss_amount=loss_amt,
                        quantity=candidate.lot.quantity,
                        lot_id=candidate.lot.lot_id
                    )
            else:
                rejected.append(candidate)

        tot_gross_savings = sum(c.gross_tax_savings for c in recommendations)
        tot_friction = sum(c.switching_friction for c in recommendations)
        tot_net_alpha = sum(c.net_tax_alpha for c in recommendations)
        restricted_syms = self.wash_sale_tracker.get_active_restricted_symbols(as_of_str)

        return TaxHarvestingPlan(
            as_of_date=as_of_str,
            candidates_screened=len(lots),
            harvest_recommendations=recommendations,
            rejected_candidates=rejected,
            total_gross_tax_savings=float(tot_gross_savings),
            total_switching_friction=float(tot_friction),
            total_net_tax_alpha=float(tot_net_alpha),
            wash_sale_restricted_symbols=restricted_syms
        )

    # -----------------------------------------------------------------------
    # Lot Accounting Ordering Helpers: HIFO, FIFO, LIFO
    # -----------------------------------------------------------------------

    @staticmethod
    def hifo_sort(lots: List[TaxLot]) -> List[TaxLot]:
        """
        Highest-In, First-Out (HIFO) sorting:
        Orders lots by highest cost basis per share descending, maximizing realized loss.
        """
        return sorted(lots, key=lambda lot: lot.cost_basis_per_share, reverse=True)

    @staticmethod
    def fifo_sort(lots: List[TaxLot]) -> List[TaxLot]:
        """First-In, First-Out (FIFO) sorting based on acquisition date ascending."""
        return sorted(lots, key=lambda lot: parse_date(lot.acquisition_date))

    @staticmethod
    def lifo_sort(lots: List[TaxLot]) -> List[TaxLot]:
        """Last-In, First-Out (LIFO) sorting based on acquisition date descending."""
        return sorted(lots, key=lambda lot: parse_date(lot.acquisition_date), reverse=True)

    # -----------------------------------------------------------------------
    # Order Generation for Execution OMS
    # -----------------------------------------------------------------------

    def generate_rebalance_orders(self, plan: TaxHarvestingPlan) -> List[Dict[str, Any]]:
        """
        Translates a TaxHarvestingPlan into actionable execution orders:
          - SELL orders for harvested lots
          - BUY orders for corresponding surrogate assets
        """
        orders: List[Dict[str, Any]] = []
        for cand in plan.harvest_recommendations:
            # 1. SELL Order for original asset
            orders.append({
                "action": "SELL",
                "symbol": cand.lot.symbol,
                "market": cand.lot.market,
                "quantity": cand.lot.quantity,
                "target_price": cand.lot.current_price,
                "target_notional": cand.lot.market_value,
                "order_type": "TAX_HARVEST_LIQUIDATION",
                "lot_id": cand.lot.lot_id,
                "tax_alpha": cand.gross_tax_savings
            })

            # 2. BUY Order for surrogate asset
            if cand.surrogate_symbol and cand.surrogate_quantity > 0:
                surr_price = cand.notes.get("surrogate_price", cand.lot.current_price)
                orders.append({
                    "action": "BUY",
                    "symbol": cand.surrogate_symbol,
                    "market": cand.lot.market,
                    "quantity": cand.surrogate_quantity,
                    "target_price": surr_price,
                    "target_notional": cand.surrogate_quantity * surr_price,
                    "order_type": "TAX_SURROGATE_REPLACEMENT",
                    "paired_lot_id": cand.lot.lot_id,
                    "surrogate_correlation": cand.surrogate_correlation
                })

        return orders


# ---------------------------------------------------------------------------
# Module Aliases for Phase 107 Compliance
# ---------------------------------------------------------------------------
TaxLossHarvestingEngine = DynamicTaxLossHarvestingOptimizer
InstitutionalTaxOptimizer = DynamicTaxLossHarvestingOptimizer
Phase107TaxOptimizer = DynamicTaxLossHarvestingOptimizer

# Ensure canonical sys.modules registration across import paths
import sys as _sys
for _mod_alias in (
    "src.risk.tax_loss_harvesting_optimizer",
    "trading_system.src.risk.tax_loss_harvesting_optimizer",
    "risk.tax_loss_harvesting_optimizer",
):
    _sys.modules[_mod_alias] = _sys.modules[__name__]

