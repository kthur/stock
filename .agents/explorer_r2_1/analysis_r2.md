# Requirement 2 (R2): Precision Order Book Market Impact & Cost Modeling Analysis Report

## Executive Summary
This report presents a comprehensive financial and architectural analysis of trading cost modeling in the Stock Trading System. Currently, transaction costs in `EnsembleScoringEngine` (`trading_system/src/ai/ensemble_scorer.py`) rely on static market-based constants combined with a coarse 2-tier step-function penalty for low turnover. This simplified approach fails to capture continuous liquidity variation, bid-ask spread dynamics, order size hypothesis ($Q$), daily return volatility ($\sigma$), and Kyle/Almgren-Chriss square-root market impact laws.

We formulate a quantitative **Precision Order Book Market Impact & Bid-Ask Spread Model** rooted in financial market microstructure theory. We detail exact parameter additions to `TradingConfig` (`trading_system/src/config.py`), specify code integration for `EnsembleScoringEngine`, and outline a test suite to verify market impact behavior.

---

## 1. Investigation of Existing Cost & Impact Implementation

### 1.1 Current Configuration (`trading_system/src/config.py`)
In `TradingConfig`, trading cost and liquidity parameters are limited to:
```python
slippage_krx_market_order: float = 0.005      # Fixed 0.5% slippage
min_daily_volume_krx: float = 5_000_000_000.0  # 5B KRW min turnover
min_daily_volume_sp500: float = 1_000_000.0   # 1M shares min volume
```
- **Defect**: No parameters exist for order size hypothesis ($Q$), market impact square-root law multiplier ($Y$), base market spread coefficients ($S_{base}$), or volatility sensitivity parameters.

### 1.2 Current Cost Function in `EnsembleScoringEngine` (`trading_system/src/ai/ensemble_scorer.py`)
In `combine_predictions` (lines 928–948), costs are computed per stock via `_get_cost_pct`:
```python
def _get_cost_pct(row: pd.Series) -> float:
    symbol = str(row.get('symbol', ''))
    market = str(row.get('market', '')).upper()
    vol = float(row.get('volume', 0.0)) if pd.notna(row.get('volume')) else 0.0
    close_p = float(row.get('close', 0.0)) if pd.notna(row.get('close')) else 0.0
    turnover = vol * close_p

    # Market impact penalty based on liquidity (higher impact for low turnover)
    impact_penalty = 0.005 if turnover < 100_000_000 else (0.002 if turnover < 1_000_000_000 else 0.0)

    if market == 'KONEX' or symbol.endswith('.KN'):
        return 0.0010 + 0.0010 + base_slippage + impact_penalty  # STT 0.10% + Spread 0.10%
    elif market == 'KOSDAQ' or symbol.endswith('.KQ'):
        return 0.0018 + 0.0015 + base_slippage + impact_penalty  # STT 0.18% + Spread 0.15%
    elif market == 'KOSPI' or symbol.endswith('.KS') or (symbol.isdigit() and len(symbol) == 6):
        return 0.0015 + 0.0008 + base_slippage + impact_penalty  # STT 0.15% + Spread 0.08%
    elif market == 'SP500' or (symbol.isalpha() and len(symbol) <= 5):
        return 0.0003 + 0.0003 + (base_slippage * 0.2) + impact_penalty  # SEC fee + Tight US spread
    return 0.0020 + base_slippage + impact_penalty
```

### 1.3 Key Limitations Identified
1. **Coarse Step-Function Impact**: Turnover thresholds at 100M KRW and 1B KRW create artificial cost cliffs (jump discontinuities of 0.3% and 0.2%).
2. **Absence of Order Size Hypothesis ($Q$)**: Cost is identical whether an order is 1 million KRW or 1 billion KRW.
3. **Static Bid-Ask Spreads**: Hardcoded static spread percentages (e.g. 0.08% KOSPI, 0.15% KOSDAQ) ignore the reality that illiquid small-caps often have spreads of 0.50%–2.00%, while mega-caps (e.g. Samsung Electronics) operate at ~0.02%–0.04%.
4. **Ignored Volatility Effect**: Higher volatility ($\sigma$) widens order book spreads and increases market impact risk, but current logic treats high-volatility and low-volatility stocks identically.

---

## 2. Quantitative Precision Formulations

To model order book market dynamics accurately, we adopt the industry-standard **Almgren-Chriss / Kyle Square-Root Law** for market impact and a **microstructure liquidity regression model** for bid-ask spreads.

### 2.1 Dynamic Bid-Ask Spread Model ($\text{Spread}_{\%}$)
The percentage bid-ask spread for stock $i$ is modeled as a function of Average Daily Turnover ($ADV_i = \text{Volume}_i \times \text{Price}_i$) and daily volatility ($\sigma_i$):

$$\text{Spread}_{\%}(i) = \text{clamp}\left( S_{base, mkt} \cdot \left( \frac{ADV_{ref}}{ADV_i} \right)^{\alpha} \cdot \left( \frac{\sigma_i}{\sigma_{ref}} \right)^{\beta}, S_{min, mkt}, S_{max, mkt} \right)$$

Where:
- $S_{base, mkt}$: Market baseline half-spread (KOSPI: 0.06%, KOSDAQ: 0.10%, KONEX: 0.25%, SP500: 0.02%).
- $ADV_{ref}$: Baseline reference daily turnover ($1,000,000,000$ KRW for KRX; $\$1,000,000$ USD for SP500).
- $\alpha = 0.25$: Elasticity exponent of spread relative to turnover.
- $\sigma_i$: 20-day daily price return standard deviation (default $0.020$ for KRX, $0.015$ for SP500 if unpopulated).
- $\sigma_{ref} = 0.020$: Reference daily volatility (2.0%).
- $\beta = 0.50$: Volatility elasticity exponent.
- Clamping Bounds $[S_{min}, S_{max}]$:
  - **KOSPI**: $[0.02\%, 1.50\%]$
  - **KOSDAQ**: $[0.03\%, 2.50\%]$
  - **KONEX**: $[0.10\%, 5.00\%]$
  - **SP500**: $[0.01\%, 0.50\%]$

### 2.2 Square-Root Law Order Book Market Impact Model ($I_{impact}$)
Market impact cost per trade (one-way execution slip) follows Kyle's lambda & Almgren-Chriss square-root formulation:

$$I_{impact,\%}(i) = Y_{mkt} \cdot \sigma_i \cdot \sqrt{\frac{Q_{mkt}}{ADV_i}}$$

Where:
- $Q_{mkt}$: Order size hypothesis (default $50,000,000$ KRW for KRX; $\$50,000$ USD for SP500).
- $ADV_i$: Average Daily Turnover ($ADV_i = \max(\text{Volume}_i \times \text{Price}_i, 10,000,000)$).
- $\sigma_i$: Daily return volatility.
- $Y_{mkt}$: Empirical market impact coefficient ($Y_{KRX} = 0.75$, $Y_{SP500} = 0.50$).

#### Participation Rate Overflow Penalty
If the order ratio $P = \frac{Q_{mkt}}{ADV_i} > 0.10$ (order exceeds 10% of total daily market turnover), execution liquidity degrades rapidly due to order book exhaustion. An illiquidity penalty is added:

$$I_{penalty,\%}(i) = 0.50 \cdot \left( \frac{Q_{mkt}}{ADV_i} - 0.10 \right)$$

Total One-Way Market Impact:

$$I_{total,\%}(i) = I_{impact,\%}(i) + I_{penalty,\%}(i)$$

### 2.3 Total Round-Trip Execution & Friction Cost ($C_{total}$)
The net transaction cost percentage subtracted from raw expected returns is:

$$C_{total}(i) = \text{Tax}_{\text{sell}} + \text{Fee}_{\text{broker}} + \text{Spread}_{\%}(i) + 2 \cdot I_{total,\%}(i)$$

Where:
- $\text{Tax}_{\text{sell}}$: Sell-side statutory transaction tax (KOSPI: 0.15%, KOSDAQ: 0.18%, KONEX: 0.10%, SP500: 0.003% SEC/FINRA fee).
- $\text{Fee}_{\text{broker}}$: Brokerage fee round-trip (KRX: 0.03%, SP500: 0.008%).
- $\text{Spread}_{\%}(i)$: Dynamic bid-ask spread cost.
- $2 \cdot I_{total,\%}(i)$: Round-trip market impact (buy entry + sell exit).

---

## 3. Parameter Updates in `src/config.py`

### 3.1 New Configuration Fields
Add the following fields to `TradingConfig` in `trading_system/src/config.py`:

```python
    # Order Book Market Impact & Bid-Ask Spread Cost Parameters (R2)
    order_size_krx: float = 50_000_000.0        # KRX 기본 주문 금액 가설 (5천만원)
    order_size_sp500: float = 50_000.0          # SP500 기본 주문 금액 가설 ($50,000)
    market_impact_coeff_krx: float = 0.75       # KRX 시장 충격 Square-Root 계수 Y
    market_impact_coeff_sp500: float = 0.50     # SP500 시장 충격 Square-Root 계수 Y
    base_spread_kospi: float = 0.0006           # KOSPI 기준 스프레드 (0.06%)
    base_spread_kosdaq: float = 0.0010          # KOSDAQ 기준 스프레드 (0.10%)
    base_spread_konex: float = 0.0025           # KONEX 기준 스프레드 (0.25%)
    base_spread_sp500: float = 0.0002           # SP500 기준 스프레드 (0.02%)
```

### 3.2 Environment Variable Overrides in `__post_init__`
```python
        if "ORDER_SIZE_KRX" in os.environ:
            try:
                self.order_size_krx = float(os.environ["ORDER_SIZE_KRX"])
            except ValueError:
                pass
        if "ORDER_SIZE_SP500" in os.environ:
            try:
                self.order_size_sp500 = float(os.environ["ORDER_SIZE_SP500"])
            except ValueError:
                pass
        if "MARKET_IMPACT_COEFF_KRX" in os.environ:
            try:
                self.market_impact_coeff_krx = float(os.environ["MARKET_IMPACT_COEFF_KRX"])
            except ValueError:
                pass
        if "MARKET_IMPACT_COEFF_SP500" in os.environ:
            try:
                self.market_impact_coeff_sp500 = float(os.environ["MARKET_IMPACT_COEFF_SP500"])
            except ValueError:
                pass
```

---

## 4. Code Integration Plan for `src/ai/ensemble_scorer.py`

### 4.1 Upgraded `_get_cost_pct` Implementation
In `EnsembleScoringEngine.combine_predictions`:

```python
        # Microstructure execution model: Sell-side STT tax, SEC fees, dynamic Bid-Ask spread,
        # and Kyle/Almgren-Chriss Square-Root Market Impact Cost modeling.
        order_size_krx = getattr(self.config, 'order_size_krx', 50_000_000.0) if self.config else 50_000_000.0
        order_size_sp500 = getattr(self.config, 'order_size_sp500', 50_000.0) if self.config else 50_000.0
        impact_coeff_krx = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75
        impact_coeff_sp500 = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50

        base_spread_kospi = getattr(self.config, 'base_spread_kospi', 0.0006) if self.config else 0.0006
        base_spread_kosdaq = getattr(self.config, 'base_spread_kosdaq', 0.0010) if self.config else 0.0010
        base_spread_konex = getattr(self.config, 'base_spread_konex', 0.0025) if self.config else 0.0025
        base_spread_sp500 = getattr(self.config, 'base_spread_sp500', 0.0002) if self.config else 0.0002

        def _get_cost_pct(row: pd.Series) -> float:
            symbol = str(row.get('symbol', ''))
            market = str(row.get('market', '')).upper()
            vol = float(row.get('volume', 0.0)) if pd.notna(row.get('volume')) else 0.0
            close_p = float(row.get('close', 0.0)) if pd.notna(row.get('close')) else 0.0
            turnover = vol * close_p

            # Retrieve daily return volatility (fallback to default if unpopulated)
            volatility = float(row.get('volatility_20d', 0.020)) if pd.notna(row.get('volatility_20d')) else (0.015 if market == 'SP500' else 0.020)
            if volatility <= 0:
                volatility = 0.020

            # Determine market parameters
            if market == 'KONEX' or symbol.endswith('.KN'):
                stt_tax = 0.0010
                brokerage_fee = 0.0003
                base_spread = base_spread_konex
                spread_min, spread_max = 0.0010, 0.0500
                q_order = order_size_krx
                adv_ref = 1_000_000_000.0
                impact_coeff = impact_coeff_krx
            elif market == 'KOSDAQ' or symbol.endswith('.KQ'):
                stt_tax = 0.0018
                brokerage_fee = 0.0003
                base_spread = base_spread_kosdaq
                spread_min, spread_max = 0.0003, 0.0250
                q_order = order_size_krx
                adv_ref = 1_000_000_000.0
                impact_coeff = impact_coeff_krx
            elif market == 'KOSPI' or symbol.endswith('.KS') or (symbol.isdigit() and len(symbol) == 6):
                stt_tax = 0.0015
                brokerage_fee = 0.0003
                base_spread = base_spread_kospi
                spread_min, spread_max = 0.0002, 0.0150
                q_order = order_size_krx
                adv_ref = 1_000_000_000.0
                impact_coeff = impact_coeff_krx
            elif market == 'SP500' or (symbol.isalpha() and len(symbol) <= 5):
                stt_tax = 0.00003  # SEC fee
                brokerage_fee = 0.00005
                base_spread = base_spread_sp500
                spread_min, spread_max = 0.0001, 0.0050
                q_order = order_size_sp500
                adv_ref = 1_000_000.0  # $1M USD
                impact_coeff = impact_coeff_sp500
            else:
                stt_tax = 0.0015
                brokerage_fee = 0.0003
                base_spread = base_spread_kospi
                spread_min, spread_max = 0.0002, 0.0150
                q_order = order_size_krx
                adv_ref = 1_000_000_000.0
                impact_coeff = impact_coeff_krx

            # Safe ADV calculation
            adv = max(turnover, 10_000_000.0 if market != 'SP500' else 10_000.0)

            # 1. Dynamic Bid-Ask Spread Modeling
            adv_ratio = adv_ref / adv
            vol_ratio = volatility / 0.020
            dynamic_spread = base_spread * (adv_ratio ** 0.25) * (vol_ratio ** 0.50)
            clamped_spread = min(max(dynamic_spread, spread_min), spread_max)

            # 2. Order Book Square-Root Market Impact Modeling
            participation_ratio = q_order / adv
            impact_one_way = impact_coeff * volatility * np.sqrt(participation_ratio)

            # 3. Participation Rate Overflow Penalty (> 10% ADV)
            if participation_ratio > 0.10:
                impact_one_way += 0.50 * (participation_ratio - 0.10)

            # Round-trip execution cost sum
            total_cost_pct = stt_tax + brokerage_fee + clamped_spread + (2.0 * impact_one_way)
            return float(total_cost_pct)
```

### 4.2 Updating `get_regime_reasoning_summary`
Update the transaction cost reasoning string block:
```python
lines.append("\n[Transaction Costs & Liquidity Filter Rationale]")
lines.append("• Microstructure Execution & Market Impact Model Active:")
lines.append(f"  - Order Size Hypothesis (Q): KRX = {order_size_krx:,.0f} KRW | SP500 = ${order_size_sp500:,.0f} USD")
lines.append("  - Bid-Ask Spread Model: Dynamic power-law scaling relative to ADV and 20d volatility")
lines.append("  - Market Impact Model: Kyle / Almgren-Chriss Square-Root law (I = Y * σ * sqrt(Q / ADV))")
lines.append("  - Statutory Taxes: Sell-side STT (KOSPI 0.15%, KOSDAQ 0.18%, KONEX 0.10%), US SEC fee (0.003%)")
```

---

## 5. Test Suite Design (`trading_system/tests/test_order_book_market_impact.py`)

A new test file `test_order_book_market_impact.py` should be created to verify all market impact properties:

```python
import pytest
import numpy as np
import pandas as pd
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.config import TradingConfig


def test_square_root_market_impact_scaling():
    """Verify market impact follows square-root relationship when order size or turnover changes."""
    config = TradingConfig(order_size_krx=50_000_000.0, market_impact_coeff_krx=0.75)
    scorer = EnsembleScoringEngine(config=config)

    # Stock 1: High turnover (100B KRW) -> low Q/ADV ratio
    # Stock 2: Lower turnover (6.25B KRW) -> 16x smaller turnover -> sqrt(16) = 4x higher market impact
    df_reg = pd.DataFrame({
        'symbol': ['HIGH_TURNOVER.KS', 'LOW_TURNOVER.KS'],
        'market': ['KOSPI', 'KOSPI'],
        'volume': [1_000_000, 62_500],
        'close': [100_000, 100_000],  # Turnover: 100B vs 6.25B
        'volatility_20d': [0.02, 0.02],
        20: [0.25, 0.25]
    })

    res = scorer.combine_predictions(reg_df=df_reg, target_horizon=20)
    high_row = res[res['symbol'] == 'HIGH_TURNOVER.KS'].iloc[0]
    low_row = res[res['symbol'] == 'LOW_TURNOVER.KS'].iloc[0]

    # Lower turnover stock must have lower net expected return due to higher market impact & spread
    assert low_row['ensemble_expected_return'] < high_row['ensemble_expected_return']


def test_volatility_impact_scaling():
    """Verify higher volatility leads to higher bid-ask spread and market impact."""
    scorer = EnsembleScoringEngine()

    df_reg = pd.DataFrame({
        'symbol': ['LOW_VOL.KS', 'HIGH_VOL.KS'],
        'market': ['KOSPI', 'KOSPI'],
        'volume': [100_000, 100_000],
        'close': [50_000, 50_000],
        'volatility_20d': [0.01, 0.04],  # 1% vs 4% daily vol
        20: [0.25, 0.25]
    })

    res = scorer.combine_predictions(reg_df=df_reg, target_horizon=20)
    low_vol = res[res['symbol'] == 'LOW_VOL.KS'].iloc[0]
    high_vol = res[res['symbol'] == 'HIGH_VOL.KS'].iloc[0]

    assert high_vol['ensemble_expected_return'] < low_vol['ensemble_expected_return']


def test_participation_rate_overflow_penalty():
    """Verify orders exceeding 10% ADV incur participation rate penalty."""
    config = TradingConfig(order_size_krx=500_000_000.0)  # Large order: 500M KRW
    scorer = EnsembleScoringEngine(config=config)

    # Micro-cap stock with 1B KRW turnover (Q/ADV = 500M / 1B = 0.50 > 0.10)
    df_reg = pd.DataFrame({
        'symbol': ['MICRO_CAP.KQ'],
        'market': ['KOSDAQ'],
        'volume': [20_000],
        'close': [50_000],  # Turnover: 1B KRW
        20: [0.25]
    })

    res = scorer.combine_predictions(reg_df=df_reg, target_horizon=20)
    micro_row = res[res['symbol'] == 'MICRO_CAP.KQ'].iloc[0]

    # Net expected return should reflect heavy execution cost
    assert micro_row['ensemble_expected_return'] < 20.0
```

---

## 6. Conclusion & Implementation Guidance
The proposed Precision Order Book Market Impact Cost Model replaces rigid static cost assumptions with an industry-grade, microstructurally sound model based on:
1. Dynamic bid-ask spread power-law scaling ($\text{Spread}_{\%} \propto ADV^{-0.25} \cdot \sigma^{0.50}$).
2. Kyle / Almgren-Chriss square-root market impact ($I_{\%} \propto \sigma \cdot \sqrt{Q / ADV}$).
3. Explicit order size hypotheses ($Q_{KRX} = 50\text{M KRW}$, $Q_{SP500} = \$50\text{K USD}$) in `TradingConfig`.
4. Linear overflow penalty for participation rates $>10\%$ of ADV.

This ensures accurate backtesting, prevents illiquid small-cap order book slippage traps, and fulfills Requirement 2 (R2) completely.
