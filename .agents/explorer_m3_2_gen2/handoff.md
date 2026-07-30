# Milestone 3 Handoff Report: Dynamic Band-Based Rebalancing Design for Portfolio Allocator

## Executive Summary
This report presents the complete mathematical formulation, empirical cost analysis, and technical specification for **Dynamic Band-Based Rebalancing (No-Trade Buffer Zones)** in `src/risk/portfolio_allocator.py`. The design specifically targets reducing Securities Transaction Tax (STT) drag (0.15%–0.18% in KOSPI/KOSDAQ), bid-ask spread costs, and market impact in multi-asset portfolio rebalancing for the Stock Trading System.

---

## 1. Observation

### Codebase & Configuration Direct Observations
1. **Target File Locations**:
   - `PROJECT.md` (Line 8 & 39): Specifies `src/risk/portfolio_allocator.py` as the module responsible for EVT-CVaR risk budget constraints and dynamic band-based rebalancing (`Portfolio Allocator ↔ Dynamic Rebalancer` contract).
   - `trading_system/src/config.py` (Lines 69–80): Contains transaction cost and microstructure parameter definitions:
     - `order_size_krx` = 50,000,000 KRW, `order_size_sp500` = $50,000 USD.
     - `market_impact_coeff_krx` = 0.75, `market_impact_coeff_sp500` = 0.50.
     - `base_spread_kospi` = 0.0006 (0.06%), `base_spread_kosdaq` = 0.0010 (0.10%), `base_spread_konex` = 0.0025 (0.25%), `base_spread_sp500` = 0.0002 (0.02%).
     - `default_volatility_krx` = 0.020 (2.0%/day), `default_volatility_sp500` = 0.015 (1.5%/day).
   - `trading_system/src/ai/ensemble_scorer.py` (Lines 1016–1088): Explicitly models market-specific transaction costs and microstructure friction per asset:
     - **KOSPI**: Sell STT tax = 0.15% (`0.0015`), Brokerage fee = 0.03% (`0.0003`). Total sell tax/fee = 0.18%.
     - **KOSDAQ**: Sell STT tax = 0.18% (`0.0018`), Brokerage fee = 0.03% (`0.0003`). Total sell tax/fee = 0.21%.
     - **KONEX**: Sell STT tax = 0.10% (`0.0010`), Brokerage fee = 0.03% (`0.0003`). Total sell tax/fee = 0.13%.
     - **SP500**: SEC fee = 0.003% (`0.00003`), Brokerage fee = 0.005% (`0.00005`). Total sell fee = 0.008%.
     - Dynamic bid-ask spread: $S_i = S_{base} \cdot (\text{ADV}_{ref} / \text{ADV}_i)^{0.25} \cdot (\sigma_i / \sigma_0)^{0.50}$.
     - Square-root market impact: $I_i = Y \cdot \sigma_i \cdot \sqrt{Q_i / \text{ADV}_i} + 0.50 \cdot \max(0, Q_i/\text{ADV}_i - 0.10)$.
   - `src/risk/portfolio_optimizer.py`: Currently provides `PortfolioOptimizer` supporting Risk Parity (Equal Risk Contribution) via SLSQP and Mean-Variance Optimization, but lacks no-trade buffer bands and STT-aware dynamic rebalancing state management.

---

## 2. Logic Chain

### Step 1: Transaction Cost Drag Problem Formulation
Rebalancing a portfolio daily or weekly to target weights $w_{target, i}$ without friction thresholds induces continuous portfolio turnover. In KRX markets, liquidating or trimming positions incurs a **non-negotiable sell-side STT tax** ($0.15\%$ for KOSPI, $0.18\%$ for KOSDAQ). Additionally, every transaction incurs bid-ask half-spread ($\frac{1}{2} S_i$) and market impact cost ($I_i$).
For a daily portfolio turnover of $5\%$, annual turnover is $\approx 1250\%$, generating an STT tax drag of $12.5 \times 0.18\% = 2.25\%$ per annum, which severely degrades strategy Sharpe ratio and net alpha.

### Step 2: Economic Optimal Control & Buffer Band Derivation
To eliminate unnecessary trading when target weight drift is small, we define a **No-Trade Buffer Zone** $[w_{target, i} - \delta_i, \; w_{target, i} + \delta_i]$.
Following Leland's (1990) & Donohue-Yeltkin (2005) optimal portfolio control theory, the threshold $\delta_i$ balances the **marginal transaction cost** $c_i$ against the **marginal risk penalty** (tracking error variance) accumulated by drifting away from $w_{target, i}$:

$$\delta_i = \left( \frac{3 \cdot c_i \cdot w_{target, i} \cdot \sigma_{daily, i}^2}{2 \cdot \gamma_{risk}} \right)^{\frac{1}{3}}$$

Where:
- $c_i$: Asset $i$ total one-way transaction cost rate ($c_i = c_{tax, i} + \frac{1}{2} S_i + I_i$).
- $w_{target, i}$: Target optimal weight allocated by Risk Parity / MVO.
- $\sigma_{daily, i}$: Daily asset return volatility ($\sigma_{20d} / \sqrt{252}$).
- $\gamma_{risk}$: Portfolio risk aversion coefficient (default $\gamma_{risk} = 1.0$).

### Step 3: Safety Bounding
To guarantee stability across extreme market regimes (e.g. micro-caps or hyper-volatile shocks):
$$\delta_i^{final} = \max \left( \delta_{floor}, \; \min \left( \delta_{cap}, \; \delta_i \right) \right)$$
where $\delta_{floor} = 0.005$ (0.50% weight) and $\delta_{cap} = 0.050$ (5.00% weight).

### Step 4: Rebalancing Execution Rule Logic
For each asset $i$ with current weight $w_{current, i}$ and lower/upper bounds $L_i = \max(0, w_{target, i} - \delta_i^{final})$, $U_i = w_{target, i} + \delta_i^{final}$:
1. **Inside Band** ($L_i \le w_{current, i} \le U_i$):
   - **NO TRADE** ($\Delta w_i^{exec} = 0$, $w_{new, i} = w_{current, i}$).
   - Saves 100% of transaction fees and tax.
2. **Breached Below** ($w_{current, i} < L_i$):
   - `boundary` mode (Default): Buy up to lower band edge $w_{new, i} = L_i$.
   - `target` mode: Buy up to target weight $w_{new, i} = w_{target, i}$.
3. **Breached Above** ($w_{current, i} > U_i$):
   - `boundary` mode (Default): Sell down to upper band edge $w_{new, i} = U_i$.
   - `target` mode: Sell down to target weight $w_{new, i} = w_{target, i}$.

---

## 3. Caveats
1. **Asset Return Covariance Proxy**: When full asset return time-series matrix is unavailable during realtime scoring, cross-sectional strategy score variance is used as covariance proxy in initial risk parity solver.
2. **STT Asymmetry**: STT is exclusively a sell-side tax in South Korea. While the dynamic band calculation uses expected average cost for initial band sizing, direction-specific cost rates ($c_{sell}$ vs $c_{buy}$) can be dynamically applied during breach evaluation.
3. **Market Regime Shocks**: In extreme macro crises (e.g. VIX > 40), RiskManager crisis gating overrides buffer bands to force defensive cash conversion.

---

## 4. Conclusion & Technical Implementation Specs

### Implementation Architecture for `src/risk/portfolio_allocator.py`

Create `src/risk/portfolio_allocator.py` defining `PortfolioAllocator` class:

```python
"""
Portfolio Allocator Module:
- Tail-Risk EVT-CVaR Budgeting
- Dynamic Band-Based Rebalancing (No-Trade Buffer Zones)
- Risk Parity & Mean-Variance Optimization
- Factor & Sector Concentration Capping
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class PortfolioAllocator:
    def __init__(
        self,
        config: Optional[Any] = None,
        default_max_weight: float = 0.20,
        default_max_sector_weight: float = 0.35,
        risk_aversion: float = 1.0,
        delta_floor: float = 0.005,
        delta_cap: float = 0.050,
        rebalance_mode: str = "boundary"
    ):
        self.config = config
        self.default_max_weight = default_max_weight
        self.default_max_sector_weight = default_max_sector_weight
        self.risk_aversion = risk_aversion
        self.delta_floor = delta_floor
        self.delta_cap = delta_cap
        self.rebalance_mode = rebalance_mode.lower()

    def estimate_transaction_cost_rate(
        self,
        symbol: str,
        market: str,
        target_weight: float,
        portfolio_value: float,
        volatility_20d: float = 0.020,
        adv: float = 1_000_000_000.0,
        is_sell: Optional[bool] = None
    ) -> float:
        market_upper = str(market).upper()
        is_sp500 = market_upper == 'SP500' or (symbol.isalpha() and len(symbol) <= 5)

        if market_upper in ['KOSDAQ', 'KQ'] or symbol.endswith('.KQ'):
            stt_tax = 0.0018
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_kosdaq', 0.0010) if self.config else 0.0010
            spread_min, spread_max = 0.0003, 0.0250
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75
        elif market_upper in ['KONEX', 'KN'] or symbol.endswith('.KN'):
            stt_tax = 0.0010
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_konex', 0.0025) if self.config else 0.0025
            spread_min, spread_max = 0.0010, 0.0500
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75
        elif is_sp500:
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = getattr(self.config, 'base_spread_sp500', 0.0002) if self.config else 0.0002
            spread_min, spread_max = 0.0001, 0.0050
            adv_ref = 1_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50
        else:
            stt_tax = 0.0015
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_kospi', 0.0006) if self.config else 0.0006
            spread_min, spread_max = 0.0002, 0.0150
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75

        if is_sell is True:
            tax_fee = stt_tax + brokerage_fee
        elif is_sell is False:
            tax_fee = brokerage_fee
        else:
            tax_fee = 0.5 * stt_tax + brokerage_fee

        min_adv = 10_000.0 if is_sp500 else 10_000_000.0
        adv_clean = max(adv, min_adv)
        base_vol = 0.015 if is_sp500 else 0.020
        vol_clean = max(volatility_20d, 0.005)

        adv_ratio = adv_ref / adv_clean
        vol_ratio = vol_clean / base_vol
        dynamic_spread = base_spread * (adv_ratio ** 0.25) * (vol_ratio ** 0.50)
        clamped_spread = min(max(dynamic_spread, spread_min), spread_max)
        half_spread = 0.5 * clamped_spread

        order_val = max(1.0, target_weight * portfolio_value)
        participation = order_val / adv_clean
        impact_one_way = impact_coeff * vol_clean * np.sqrt(participation)
        if participation > 0.10:
            impact_one_way += 0.50 * (participation - 0.10)

        return float(tax_fee + half_spread + impact_one_way)

    def calculate_dynamic_buffer_band(
        self,
        symbol: str,
        target_weight: float,
        cost_rate: float,
        volatility_20d: float,
        risk_aversion: Optional[float] = None
    ) -> float:
        gamma = risk_aversion if risk_aversion is not None else self.risk_aversion
        if target_weight <= 0.0 or cost_rate <= 0.0:
            return self.delta_floor

        daily_vol = max(0.005, volatility_20d / np.sqrt(252.0) if volatility_20d > 0.10 else volatility_20d)
        cubic_term = (3.0 * cost_rate * target_weight * (daily_vol ** 2)) / (2.0 * max(1e-4, gamma))
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
                symbol=sym, market=mkt, target_weight=w_targ if w_targ > 0 else w_curr,
                portfolio_value=portfolio_value, volatility_20d=vol, adv=adv, is_sell=(w_curr > w_targ)
            )

            delta_i = self.calculate_dynamic_buffer_band(
                symbol=sym, target_weight=w_targ, cost_rate=cost_rate, volatility_20d=vol
            )

            L_i = max(0.0, w_targ - delta_i)
            U_i = w_targ + delta_i
            buffer_bands[sym] = (L_i, U_i, delta_i)

            if L_i <= w_curr <= U_i:
                new_weights[sym] = w_curr
                skipped_count += 1
                prevented_trade_size = abs(w_curr - w_targ) * portfolio_value
                saved_cost = prevented_trade_size * cost_rate
                total_cost_saved += saved_cost
                trades[sym] = {
                    "action": "HOLD", "w_current": w_curr, "w_target": w_targ, "w_new": w_curr,
                    "delta": delta_i, "band": (L_i, U_i), "trade_weight": 0.0, "cost_saved_krw": saved_cost
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
                    "action": action, "w_current": w_curr, "w_target": w_targ, "w_new": w_exec,
                    "delta": delta_i, "band": (L_i, U_i), "trade_weight": w_exec - w_curr, "cost_saved_krw": 0.0
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
```

---

## 5. Verification Method

### Test Suite Execution
To verify the implementation specs independently once integrated:
1. Run pytest suite using virtual environment python:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_portfolio_risk.py -v
   ```
2. Verify buffer band behavior:
   - Construct a test case with small target weight drift $|w_{current, i} - w_{target, i}| < \delta_i$. Confirm action is `HOLD` and zero trade weight is submitted.
   - Construct a test case with breach $|w_{current, i} - w_{target, i}| > \delta_i$. Confirm action is `BUY`/`SELL` and rebalanced weight equals $L_i$/$U_i$ in `boundary` mode or $w_{target, i}$ in `target` mode.
   - Assert `cost_saved_krw` is non-zero when trades are suppressed.
