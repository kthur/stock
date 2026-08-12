"""
Portfolio Allocator Module:
- Tail-Risk EVT-CVaR Budgeting (Peaks-Over-Threshold GPD fitting & 3-tier fallback)
- Dynamic Band-Based Rebalancing (Leland optimal no-trade buffer zones)
- Microstructure Transaction Cost Sizing (STT tax, dynamic spread, market impact)
- Non-linear SLSQP Portfolio Risk Budget Optimization
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from scipy.stats import genpareto, norm, skew, kurtosis
from scipy.optimize import minimize

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class PortfolioAllocator:
    """
    Portfolio Allocator Engine implementing:
    1. EVT-GPD CVaR Estimation & Non-linear SLSQP Risk Budget Constraint Optimization.
    2. Dynamic Asset-Specific Microstructure Cost Sizing (KOSPI/KOSDAQ/SP500 STT, Spread, Market Impact).
    3. Leland Dynamic Band-Based No-Trade Buffer Zones for Transaction Drag Suppression.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        default_max_weight: float = 0.20,
        default_max_sector_weight: float = 0.35,
        risk_aversion: float = 1.0,
        delta_floor: float = 0.005,
        delta_cap: float = 0.050,
        rebalance_mode: str = "boundary",
        min_tail_samples: int = 15
    ):
        self.config = config
        self.default_max_weight = default_max_weight
        self.default_max_sector_weight = default_max_sector_weight
        self.risk_aversion = risk_aversion
        self.delta_floor = delta_floor
        self.delta_cap = delta_cap
        self.rebalance_mode = rebalance_mode.lower()
        self.min_tail_samples = min_tail_samples

    # =========================================================================
    # OBJECTIVE 1: EVT-CVaR LOSS BUDGET CONSTRAINTS & 3-TIER FALLBACK HIERARCHY
    # =========================================================================

    def estimate_evt_cvar(
        self,
        returns: Union[List[float], np.ndarray, pd.Series],
        confidence: float = 0.95,
        quantile_threshold: float = 0.90
    ) -> Dict[str, Any]:
        """
        Calculates Conditional Value-at-Risk (CVaR) using Extreme Value Theory (EVT)
        Peaks-Over-Threshold (POT) Generalized Pareto Distribution (GPD) fitting.

        Implements 3-Tier Fallback Hierarchy:
        - Tier 1: EVT-GPD POT Estimator (when N_u >= min_tail_samples and GPD converges).
        - Tier 2: Cornish-Fisher Expansion CVaR (skewness & kurtosis tail adjustment).
        - Tier 3: Empirical Quantile / Gaussian Parametric CVaR (when sample N < 10 or exceptions).

        Returns:
            Dict containing: 'var', 'cvar', 'xi', 'beta', 'method'
        """
        if returns is None:
            return {"var": 0.0, "cvar": 0.0, "xi": 0.0, "beta": 0.0, "method": "zero_fallback"}

        returns_arr = np.asarray(returns, dtype=np.float64)
        returns_arr = returns_arr[~np.isnan(returns_arr)]

        N = len(returns_arr)
        if N < 5:
            return {"var": 0.0, "cvar": 0.0, "xi": 0.0, "beta": 0.0, "method": "zero_fallback"}

        # Portfolio Loss L = -R
        losses = -returns_arr

        # Tier 3 check for extremely small sample size
        if N < 10:
            mu_l = float(np.mean(losses))
            sigma_l = float(np.std(losses, ddof=1)) if N > 1 else 0.01
            z_alpha = float(norm.ppf(confidence))
            cvar_gauss = max(0.0, mu_l + sigma_l * (norm.pdf(z_alpha) / (1.0 - confidence)))
            var_gauss = max(0.0, mu_l + sigma_l * z_alpha)
            return {
                "var": float(var_gauss),
                "cvar": float(cvar_gauss),
                "xi": 0.0,
                "beta": 0.0,
                "method": "gaussian_fallback_small_n"
            }

        # Threshold u selection (e.g. 90th percentile of losses)
        u = float(np.quantile(losses, quantile_threshold))
        exceedances = losses[losses > u] - u
        n_u = len(exceedances)

        # Check if Tier 1 GPD preconditions are met
        if n_u >= self.min_tail_samples and u > -1e-6:
            try:
                # Fit GPD with location fixed at 0 (floc=0)
                xi, _, beta = genpareto.fit(exceedances, floc=0)
                xi = float(xi)
                beta = float(beta)

                if beta > 1e-8 and xi < 0.95 and not np.isnan(xi) and not np.isnan(beta):
                    # Clamp xi shape parameter for numerical safety
                    xi_clamped = min(xi, 0.50)

                    tail_ratio = (N / n_u) * (1.0 - confidence)

                    if abs(xi_clamped) < 1e-4:
                        var_evt = u - beta * np.log(tail_ratio)
                        cvar_evt = var_evt + beta
                    else:
                        var_evt = u + (beta / xi_clamped) * (np.power(tail_ratio, -xi_clamped) - 1.0)
                        cvar_evt = (var_evt + beta - xi_clamped * u) / (1.0 - xi_clamped)

                    return {
                        "var": float(max(0.0, var_evt)),
                        "cvar": float(max(0.0, cvar_evt)),
                        "xi": xi_clamped,
                        "beta": beta,
                        "method": "evt_gpd"
                    }
            except Exception as e:
                logger.debug(f"EVT-GPD fitting non-convergent, falling back to Tier 2/3: {e}")

        # Tier 2: Cornish-Fisher Expansion Fallback
        try:
            mu_l = float(np.mean(losses))
            sigma_l = float(np.std(losses, ddof=1))
            if sigma_l > 1e-8:
                s_loss = float(skew(losses))
                k_loss = float(kurtosis(losses))  # excess kurtosis

                z_a = float(norm.ppf(confidence))
                z_cf = z_a + (s_loss / 6.0) * (z_a**2 - 1.0) + (k_loss / 24.0) * (z_a**3 - 3.0 * z_a) - (s_loss**2 / 36.0) * (2.0 * z_a**3 - 5.0 * z_a)

                var_cf = mu_l + sigma_l * z_cf
                pdf_cf = norm.pdf(z_cf)
                cvar_cf = mu_l + sigma_l * (pdf_cf / (1.0 - confidence)) * (1.0 + (s_loss / 6.0) * z_cf**3 + (k_loss / 24.0) * (z_cf**4 - 2.0 * z_cf**2 - 1.0))

                if not np.isnan(cvar_cf) and cvar_cf > 0:
                    return {
                        "var": float(max(0.0, var_cf)),
                        "cvar": float(max(0.0, cvar_cf)),
                        "xi": 0.0,
                        "beta": 0.0,
                        "method": "cornish_fisher"
                    }
        except Exception:
            pass

        # Tier 3: Empirical Quantile Tail Averaging Fallback
        var_emp = float(np.quantile(losses, confidence))
        worse_losses = losses[losses >= var_emp]
        cvar_emp = float(np.mean(worse_losses)) if len(worse_losses) > 0 else var_emp

        return {
            "var": float(max(0.0, var_emp)),
            "cvar": float(max(0.0, cvar_emp)),
            "xi": 0.0,
            "beta": 0.0,
            "method": "empirical_fallback"
        }

    def estimate_portfolio_evt_cvar(
        self,
        weights: np.ndarray,
        returns_matrix: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """
        Calculates portfolio-level EVT-CVaR for a weight vector w and return matrix R.
        """
        port_returns = np.dot(returns_matrix, weights)
        res = self.estimate_evt_cvar(port_returns, confidence=confidence)
        return float(res["cvar"])

    def optimize_with_evt_cvar_constraint(
        self,
        expected_returns: pd.Series,
        returns_df: pd.DataFrame,
        max_cvar: float = 0.04,
        confidence: float = 0.95,
        max_weight: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Mean-Variance Optimization subject to EVT-CVaR loss budget constraint.
        Constraint: EVT_CVaR_alpha(w) <= max_cvar
        """
        if max_weight is None:
            max_weight = self.default_max_weight

        symbols = list(expected_returns.index)
        n_assets = len(symbols)
        if n_assets == 0:
            return {}
        if n_assets == 1:
            return {symbols[0]: 1.0}

        returns_sub = returns_df[symbols] if not returns_df.empty else pd.DataFrame()
        if returns_sub.empty or len(returns_sub) < 5:
            return {sym: 1.0 / n_assets for sym in symbols}

        returns_matrix = returns_sub.values
        mu = expected_returns.values

        # Ledoit-Wolf Covariance Shrinkage for numerical stability & lower estimation error
        try:
            from sklearn.covariance import LedoitWolf
            if len(returns_matrix) >= 5 and n_assets > 1:
                cov_shrunk = LedoitWolf().fit(returns_matrix).covariance_
            else:
                cov_shrunk = np.cov(returns_matrix, rowvar=False)
                if cov_shrunk.ndim == 0:
                    cov_shrunk = np.array([[float(cov_shrunk)]])
        except Exception:
            cov_shrunk = np.cov(returns_matrix, rowvar=False) if len(returns_matrix) > 1 else np.eye(n_assets) * 0.0004
            if cov_shrunk.ndim == 0:
                cov_shrunk = np.array([[float(cov_shrunk)]])

        def objective(w):
            ret = np.dot(w, mu)
            var_p = float(w.T @ cov_shrunk @ w) if cov_shrunk.shape == (n_assets, n_assets) else float(np.var(np.dot(returns_matrix, w), ddof=1))
            return -(ret - 0.5 * self.risk_aversion * var_p)

        def cvar_constraint(w):
            cvar_val = self.estimate_portfolio_evt_cvar(w, returns_matrix, confidence)
            return max_cvar - cvar_val

        init_weights = np.ones(n_assets) / n_assets
        bounds = tuple((0.0, max_weight) for _ in range(n_assets))
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
            {'type': 'ineq', 'fun': cvar_constraint}
        ]

        res = minimize(
            objective,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 500, 'ftol': 1e-6}
        )

        if not res.success:
            logger.warning(f"EVT-CVaR constrained optimization status: {res.message}. Normalizing initial weights.")
            weights = init_weights
        else:
            weights = res.x / np.sum(res.x)

        return {sym: float(w) for sym, w in zip(symbols, weights)}

    # =========================================================================
    # OBJECTIVE 2: DYNAMIC LELAND BAND-BASED REBALANCING & MICROSTRUCTURE COSTS
    # =========================================================================

    def estimate_transaction_cost_rate(
        self,
        symbol: str,
        market: str,
        target_weight: float,
        portfolio_value: float = 100_000_000.0,
        volatility_20d: float = 0.020,
        adv: float = 1_000_000_000.0,
        is_sell: Optional[bool] = None
    ) -> float:
        """
        Estimates asset-specific one-way transaction cost rate (c_i):
        c_i = Tax & Fees + 0.5 * Spread + Market Impact

        Specific Rules:
        - KOSPI: Sell STT tax = 0.15% (0.0015), Brokerage fee = 0.03% (0.0003). Base spread = 0.06%.
        - KOSDAQ: Sell STT tax = 0.18% (0.0018), Brokerage fee = 0.03% (0.0003). Base spread = 0.10%.
        - NASDAQ: SEC fee = 0.003% (0.00003), Brokerage fee = 0.005% (0.00005). Base spread = 0.03%.
        - RUSSELL2000: SEC fee = 0.003% (0.00003), Brokerage fee = 0.005% (0.00005). Base spread = 0.08%.
        - SP500: SEC fee = 0.003% (0.00003), Brokerage fee = 0.005% (0.00005). Base spread = 0.02%.
        """
        market_upper = str(market).upper()
        is_us_stock = market_upper in ('SP500', 'NASDAQ', 'RUSSELL2000') or (symbol.isalpha() and len(symbol) <= 5)

        if market_upper in ['KOSDAQ', 'KQ'] or symbol.endswith('.KQ'):
            stt_tax = 0.0018
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_kosdaq', 0.0010) if self.config else 0.0010
            spread_min, spread_max = 0.0003, 0.0250
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75
        elif market_upper == 'NASDAQ':
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = getattr(self.config, 'base_spread_nasdaq', 0.0003) if self.config else 0.0003
            spread_min, spread_max = 0.0001, 0.0080
            adv_ref = 1_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50
        elif market_upper == 'RUSSELL2000':
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = getattr(self.config, 'base_spread_russell2000', 0.0008) if self.config else 0.0008
            spread_min, spread_max = 0.0002, 0.0150
            adv_ref = 500_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50
        elif is_us_stock:
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = getattr(self.config, 'base_spread_sp500', 0.0002) if self.config else 0.0002
            spread_min, spread_max = 0.0001, 0.0050
            adv_ref = 1_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50
        else:  # KOSPI default
            stt_tax = 0.0015
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_kospi', 0.0006) if self.config else 0.0006
            spread_min, spread_max = 0.0002, 0.0150
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75

        # Direct STT application depending on order side
        if is_sell is True:
            tax_fee = stt_tax + brokerage_fee
        elif is_sell is False:
            tax_fee = brokerage_fee
        else:
            tax_fee = 0.5 * stt_tax + brokerage_fee

        is_sp500 = (market_upper == 'SP500')
        min_adv = 10_000.0 if is_sp500 else 10_000_000.0
        adv_clean = max(adv, min_adv)
        base_vol = 0.015 if is_sp500 else 0.020
        vol_clean = max(volatility_20d, 0.005)

        # Dynamic spread formula: S_i = base_spread * (ADV_ref / ADV_i)^0.25 * (sigma_i / sigma_0)^0.50
        adv_ratio = adv_ref / adv_clean
        vol_ratio = vol_clean / base_vol
        dynamic_spread = base_spread * (adv_ratio ** 0.25) * (vol_ratio ** 0.50)
        clamped_spread = min(max(dynamic_spread, spread_min), spread_max)
        half_spread = 0.5 * clamped_spread

        # Square-root market impact formula
        order_val = max(1.0, target_weight * portfolio_value)
        participation = order_val / adv_clean
        impact_one_way = impact_coeff * vol_clean * np.sqrt(participation)
        if participation > 0.10:
            impact_one_way += 0.50 * (participation - 0.10)

        total_cost_rate = tax_fee + half_spread + impact_one_way
        return float(total_cost_rate)

    def calculate_dynamic_buffer_band(
        self,
        symbol: str,
        target_weight: float,
        cost_rate: float,
        volatility_20d: float,
        risk_aversion: Optional[float] = None
    ) -> float:
        """
        Calculates Leland optimal no-trade buffer threshold delta_i:
        delta_i = [ (3 * c_i * w_target_i * sigma_i) / (2 * gamma_risk) ]^(1/3)
        clamped to [delta_floor, delta_cap].
        """
        gamma = risk_aversion if risk_aversion is not None else self.risk_aversion
        if target_weight <= 0.0 or cost_rate <= 0.0:
            return self.delta_floor

        vol_clean = max(0.005, volatility_20d)

        cubic_term = (3.0 * cost_rate * target_weight * vol_clean) / (2.0 * max(1e-4, gamma))
        delta_raw = np.cbrt(cubic_term)
        return float(min(max(delta_raw, self.delta_floor), self.delta_cap))

    def compute_portfolio_rebalance(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        market_map: Dict[str, str],
        volatility_map: Dict[str, float],
        adv_map: Dict[str, float],
        portfolio_value: float = 100_000_000.0,
        rebalance_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates dynamic buffer bands [w_target - delta_i, w_target + delta_i]:
        - If current_weight is INSIDE band: returns action HOLD with 0 trade weight.
        - If current_weight BREACHES band: triggers BUY/SELL rebalancing trade.
        """
        mode = (rebalance_mode or self.rebalance_mode).lower()
        all_symbols = set(current_weights.keys()).union(set(target_weights.keys()))

        new_weights: Dict[str, float] = {}
        buffer_bands: Dict[str, Tuple[float, float, float]] = {}
        trades: Dict[str, Dict[str, Any]] = {}
        total_cost_saved = 0.0
        traded_count = 0
        skipped_count = 0

        for sym in all_symbols:
            w_curr = current_weights.get(sym, 0.0)
            w_targ = target_weights.get(sym, 0.0)
            mkt = market_map.get(sym, "KOSPI")
            vol = volatility_map.get(sym, 0.020)
            adv = adv_map.get(sym, 1_000_000_000.0)

            cost_rate = self.estimate_transaction_cost_rate(
                symbol=sym,
                market=mkt,
                target_weight=w_targ if w_targ > 0 else w_curr,
                portfolio_value=portfolio_value,
                volatility_20d=vol,
                adv=adv,
                is_sell=(w_curr > w_targ)
            )

            delta_i = self.calculate_dynamic_buffer_band(
                symbol=sym,
                target_weight=w_targ,
                cost_rate=cost_rate,
                volatility_20d=vol
            )

            L_i = max(0.0, w_targ - delta_i)
            U_i = w_targ + delta_i
            buffer_bands[sym] = (L_i, U_i, delta_i)

            # Check inside buffer band [L_i, U_i]
            if L_i <= w_curr <= U_i:
                new_weights[sym] = w_curr
                skipped_count += 1
                prevented_trade_size = abs(w_curr - w_targ) * portfolio_value
                saved_cost = prevented_trade_size * cost_rate
                total_cost_saved += saved_cost
                trades[sym] = {
                    "action": "HOLD",
                    "w_current": w_curr,
                    "w_target": w_targ,
                    "w_new": w_curr,
                    "delta": delta_i,
                    "band": (L_i, U_i),
                    "trade_weight": 0.0,
                    "cost_saved_krw": saved_cost
                }
            else:
                traded_count += 1
                if w_curr < L_i:
                    w_exec = L_i if mode == "boundary" else w_targ
                    action = "BUY"
                else:
                    w_exec = U_i if mode == "boundary" else w_targ
                    action = "SELL"
                new_weights[sym] = w_exec
                trades[sym] = {
                    "action": action,
                    "w_current": w_curr,
                    "w_target": w_targ,
                    "w_new": w_exec,
                    "delta": delta_i,
                    "band": (L_i, U_i),
                    "trade_weight": w_exec - w_curr,
                    "cost_saved_krw": 0.0
                }

        tot_asset_w = sum(new_weights.values())
        if tot_asset_w > 1.0:
            scale = 1.0 / tot_asset_w
            new_weights = {s: w * scale for s, w in new_weights.items()}

        return {
            "new_weights": new_weights,
            "buffer_bands": buffer_bands,
            "trades": trades,
            "summary": {
                "total_symbols": len(all_symbols),
                "traded_count": traded_count,
                "skipped_count": skipped_count,
                "total_cost_saved_krw": total_cost_saved,
                "total_asset_weight": sum(new_weights.values()),
                "cash_weight": max(0.0, 1.0 - sum(new_weights.values()))
            }
        }

    # =========================================================================
    # OBJECTIVE 3: SECTOR EXPOSURE CAPPING & FACTOR NEUTRALITY CONSTRAINTS
    # =========================================================================

    def apply_sector_and_factor_constraints(
        self,
        weights: Dict[str, float],
        sector_map: Optional[Dict[str, str]] = None,
        regime: Optional[Union[int, str]] = None,
        max_sector_cap: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Enforces Sector Exposure Cap and Factor Risk Budgeting:
        - Sector Cap: <= 25% in BEAR/SIDEWAYS regimes, <= 35% in BULL market regimes.
        - Rank Preservation: Iteratively rescales over-concentrated sectors while preserving relative rank.
        - Cash/Re-allocation: Re-distributes excess weight proportionally across compliant sectors.
        """
        if not weights:
            return {}

        # Determine Regime-Dependent Sector Cap
        if max_sector_cap is not None:
            sector_cap = max_sector_cap
        elif regime in [2, 'BULL', 'BULL_LOW_VOL', 'BULL_HIGH_VOL']:
            sector_cap = 0.35  # Dynamic relaxation in BULL market
        else:
            sector_cap = 0.25  # Defensive 25% cap in BEAR/SIDEWAYS

        if not sector_map:
            # Fallback if no sector mapping is available
            s_sum = sum(weights.values())
            return {s: w / s_sum for s, w in weights.items()} if s_sum > 0 else weights

        cleaned_weights = dict(weights)

        # Iterative Sector Cap Enforcement (up to 5 passes for convergence)
        for _ in range(5):
            sector_totals: Dict[str, float] = {}
            for sym, w in cleaned_weights.items():
                sec = sector_map.get(sym, "UNKNOWN")
                sector_totals[sec] = sector_totals.get(sec, 0.0) + w

            over_sectors = {sec: tot for sec, tot in sector_totals.items() if tot > sector_cap + 1e-6}
            if not over_sectors:
                break

            # Rescale symbols in over-concentrated sectors
            for sec, tot in over_sectors.items():
                scale_factor = sector_cap / tot
                for sym, w in cleaned_weights.items():
                    if sector_map.get(sym, "UNKNOWN") == sec:
                        cleaned_weights[sym] = w * scale_factor

        # Re-normalize total weight so scaled-down capital is redistributed proportionally
        tot_w = sum(cleaned_weights.values())
        if abs(tot_w - 1.0) > 1e-9 and tot_w > 0:
            cleaned_weights = {s: w / tot_w for s, w in cleaned_weights.items()}

        return cleaned_weights

    # =========================================================================
    # OBJECTIVE 4: REAL-TIME OMS SLIPPAGE FEEDBACK & ATR TRAILING STOP
    # =========================================================================

    def calibrate_slippage_from_trade_logs(self, db_path: Optional[str] = None) -> float:
        """
        Reads realized execution logs from trade_logs.db and calculates empirical
        realized slippage ratio vs predicted Almgren-Chriss cost, returning a
        calibrated cost scaling factor (default = 1.0 if insufficient trades).
        """
        import sqlite3

        target_db = Path(db_path) if db_path else _PROJECT_ROOT / "trade_logs.db"
        if not target_db.exists():
            return 1.0

        try:
            conn = sqlite3.connect(str(target_db), timeout=30.0)
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('trade_logs', 'orders');")
            tables = [r[0] for r in cursor.fetchall()]

            if not tables:
                conn.close()
                return 1.0

            tbl = 'trade_logs' if 'trade_logs' in tables else 'orders'
            df = pd.read_sql_query(f"SELECT * FROM {tbl} WHERE executed_price IS NOT NULL AND order_price IS NOT NULL LIMIT 500;", conn)  # nosec B608
            conn.close()

            if df.empty or len(df) < 5:
                return 1.0

            df['order_price'] = pd.to_numeric(df['order_price'], errors='coerce')
            df['executed_price'] = pd.to_numeric(df['executed_price'], errors='coerce')
            valid = df.dropna(subset=['order_price', 'executed_price'])
            valid = valid[valid['order_price'] > 0]

            if len(valid) < 5:
                return 1.0

            slippage_pct = (np.abs(valid['executed_price'] - valid['order_price']) / valid['order_price']).mean()
            # Normalize relative to benchmark 0.10% (10 bps)
            calibrated_factor = float(np.clip(slippage_pct / 0.0010, 0.5, 3.0))
            logger.info(f"[OMS SLIPPAGE FEEDBACK] Calibrated slippage factor = {calibrated_factor:.2f}x (from {len(valid)} trades)")
            return calibrated_factor
        except Exception as e:
            logger.warning(f"[OMS SLIPPAGE FEEDBACK] Failed to calibrate slippage: {e}")
            return 1.0

    def calculate_atr_trailing_stop(
        self,
        symbol: str,
        current_price: float,
        atr_20d: float,
        is_long: bool = True,
        multiplier: float = 2.5,
        highest_price: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculates intraday dynamic ATR-based trailing stop-loss and take-profit levels:
        - Stop Loss: peak_price - (multiplier * ATR_20d)
        - Take Profit: current_price + (1.5 * multiplier * ATR_20d)
        """
        if current_price <= 0.0 or atr_20d <= 0.0:
            return {
                "stop_loss": max(0.0, current_price * 0.95),
                "take_profit": current_price * 1.10,
                "risk_pct": 0.05
            }

        atr_clean = max(atr_20d, current_price * 0.005)
        stop_dist = multiplier * atr_clean

        if is_long:
            ref_price = max(highest_price, current_price) if (highest_price is not None and highest_price > 0) else current_price
            stop_loss = max(0.0, ref_price - stop_dist)
            take_profit = current_price + (1.5 * stop_dist)
        else:
            ref_price = min(highest_price, current_price) if (highest_price is not None and highest_price > 0) else current_price
            stop_loss = ref_price + stop_dist
            take_profit = max(0.0, current_price - (1.5 * stop_dist))

        risk_pct = float(abs(current_price - stop_loss) / current_price)
        return {
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "risk_pct": float(risk_pct)
        }


