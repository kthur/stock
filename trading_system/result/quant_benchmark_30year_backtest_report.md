# 30-Year Historical Backtest & Quantitative Benchmark Report (1996–2026)

**Generated At**: 2026-10-13 00:13:54 KST  
**Simulation Horizon**: 1996-01-01 ~ 2026-08-31  
**Total Trading Days**: 8,089 bars  
**Target Markets**: KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000  
**Strategy Architecture**: 37 Multi-Factor Strategies & 2D Regime Multi-Model Ensemble  

---

## 1. Executive Performance Summary

| # | Metric | Value | Target Constraint / Unit |
|---|---|---|---|
| 1 | **Initial Capital** | 100,000,000 KRW | Base portfolio capital |
| 2 | **Final Net Equity** | 332,518,463.90 KRW | Realized after all frictions |
| 3 | **Total Gross Return** | +376.63% | Pre-friction portfolio return |
| 4 | **Total Net Return** | +232.52% | Net return (frictions deducted) |
| 5 | **CAGR** | 3.81% | Compound Annual Growth Rate |
| 6 | **Annualized Volatility** | 13.89% | Sample Bessel ddof=1 (Target: 12.0%) |
| 7 | **Sharpe Ratio** | 0.20 | Risk-Free Hurdle $r_f = 2.0\%$ |
| 8 | **Sortino Ratio** | 0.21 | Downside deviation below MAR |
| 9 | **Calmar Ratio** | 0.08 | $\text{CAGR} / |\text{MDD}|$ |
| 10 | **Maximum Drawdown (MDD)** | -47.14% | Peak-to-trough historical drawdown |
| 11 | **Win Rate** | 62.96% | Percentage of profitable days |
| 12 | **Profit Factor** | 1.07 | Gross profits / Gross losses |
| 13 | **Total Turnover** | 23.24x | Cumulative portfolio turnover |
| 14 | **Annualized Turnover** | 0.72x/yr | Annual turnover |
| 15 | **Total Friction & Drag** | 3588.7 bps | STT, SEC, half-spread, and impact |
| 16 | **Estimated Slippage** | 1435.5 bps | Implementation shortfall |
| 17 | **Daily VaR (95%)** | 1.37% | Historical 95% Value-at-Risk |
| 18 | **Daily CVaR (95%)** | 2.25% | Expected Shortfall (Tail Risk) |

---

## 2. 31-Year Annual Performance Distribution (1996–2026)

| Year | Market | Gross Return | Net Return | Volatility | Sharpe | Sortino | Calmar | MDD | Win Rate | Trades |
|---|---|---|---|---|---|---|---|---|---|---|
| 1996 | PORTFOLIO | +8.30% | +7.57% | 7.84% | 0.71 | 0.94 | 0.67 | -11.32% | 51.3% | 6 |
| 1997 | PORTFOLIO | +9.57% | +8.59% | 10.95% | 0.60 | 0.69 | 0.67 | -12.83% | 57.5% | 6 |
| 1998 | PORTFOLIO | +6.84% | +5.01% | 15.03% | 0.20 | 0.22 | 0.24 | -21.20% | 69.2% | 6 |
| 1999 | PORTFOLIO | +69.36% | +67.89% | 19.98% | 3.30 | 5.54 | 4.55 | -14.93% | 58.3% | 6 |
| 2000 | PORTFOLIO | -24.07% | -25.57% | 23.74% | -1.16 | -1.45 | -0.80 | -31.96% | 60.6% | 6 |
| 2001 | PORTFOLIO | -12.93% | -15.42% | 9.92% | -1.76 | -1.32 | -0.79 | -19.45% | 81.8% | 6 |
| 2002 | PORTFOLIO | -4.73% | -5.94% | 15.01% | -0.53 | -0.61 | -0.25 | -23.56% | 70.7% | 6 |
| 2003 | PORTFOLIO | +31.66% | +30.52% | 12.92% | 2.21 | 2.88 | 5.20 | -5.87% | 72.2% | 6 |
| 2004 | PORTFOLIO | +6.24% | +5.03% | 12.71% | 0.24 | 0.35 | 0.39 | -12.76% | 55.2% | 6 |
| 2005 | PORTFOLIO | +22.47% | +21.96% | 10.42% | 1.92 | 2.95 | 2.35 | -9.33% | 57.3% | 6 |
| 2006 | PORTFOLIO | -4.23% | -5.48% | 11.29% | -0.66 | -0.68 | -0.40 | -13.86% | 64.9% | 6 |
| 2007 | PORTFOLIO | +7.23% | +6.47% | 12.14% | 0.37 | 0.49 | 0.64 | -10.09% | 57.0% | 6 |
| 2008 | PORTFOLIO | -38.18% | -40.12% | 21.00% | -2.01 | -2.20 | -1.02 | -39.47% | 61.5% | 6 |
| 2009 | PORTFOLIO | +18.40% | +16.32% | 10.83% | 1.32 | 1.44 | 2.17 | -7.53% | 73.8% | 6 |
| 2010 | PORTFOLIO | +7.53% | +6.17% | 12.60% | 0.33 | 0.40 | 0.46 | -13.27% | 57.9% | 6 |
| 2011 | PORTFOLIO | -9.19% | -10.84% | 14.42% | -0.89 | -0.92 | -0.58 | -18.63% | 61.1% | 6 |
| 2012 | PORTFOLIO | +2.78% | +1.81% | 9.22% | -0.02 | -0.03 | 0.18 | -9.84% | 53.3% | 6 |
| 2013 | PORTFOLIO | +27.17% | +26.84% | 10.05% | 2.47 | 3.41 | 5.09 | -5.27% | 61.0% | 6 |
| 2014 | PORTFOLIO | +7.71% | +7.38% | 11.42% | 0.47 | 0.62 | 0.97 | -7.59% | 57.1% | 6 |
| 2015 | PORTFOLIO | +3.88% | +3.32% | 12.53% | 0.11 | 0.13 | 0.22 | -14.87% | 55.4% | 6 |
| 2016 | PORTFOLIO | +1.84% | +0.42% | 7.20% | -0.22 | -0.23 | 0.06 | -7.24% | 61.1% | 6 |
| 2017 | PORTFOLIO | +19.68% | +19.60% | 6.79% | 2.59 | 3.77 | 5.94 | -3.30% | 55.6% | 6 |
| 2018 | PORTFOLIO | -3.31% | -4.51% | 10.94% | -0.59 | -0.67 | -0.39 | -11.49% | 60.6% | 6 |
| 2019 | PORTFOLIO | +10.32% | +9.53% | 7.69% | 0.98 | 1.04 | 1.31 | -7.28% | 71.0% | 6 |
| 2020 | PORTFOLIO | -9.76% | -12.00% | 24.99% | -0.56 | -0.46 | -0.35 | -34.19% | 68.8% | 6 |
| 2021 | PORTFOLIO | +8.97% | +8.26% | 11.98% | 0.52 | 0.77 | 1.09 | -7.61% | 54.2% | 6 |
| 2022 | PORTFOLIO | -8.92% | -9.44% | 4.48% | -2.55 | -0.96 | -0.80 | -11.81% | 94.2% | 6 |
| 2023 | PORTFOLIO | +14.94% | +13.95% | 8.52% | 1.40 | 1.88 | 1.23 | -11.34% | 65.1% | 6 |
| 2024 | PORTFOLIO | +18.36% | +18.12% | 11.90% | 1.35 | 1.76 | 2.10 | -8.65% | 55.4% | 6 |
| 2025 | PORTFOLIO | +5.14% | +3.64% | 16.92% | 0.10 | 0.11 | 0.19 | -19.26% | 67.2% | 6 |
| 2026 | PORTFOLIO | +15.08% | +13.45% | 29.18% | 0.39 | 0.49 | 0.68 | -19.79% | 63.5% | 6 |

---

## 3. Historical Regime Crisis Stress Testing Breakdown

Performance during the 5 major macroeconomic market downturns across the 30-year horizon:

| Crisis ID | Crisis Period | Window | Net Return | Benchmark | Max DD | Volatility | Sharpe | Recovery Days | Pass |
|---|---|---|---|---|---|---|---|---|---|
| `1997_ASIAN_CRISIS` | 1997 Asian Financial Crisis (IMF) | 1997-07-01 ~ 1998-12-31 | +3.02% | +2.93% | -21.20% | 14.24% | -0.05 | 101d | PASS |
| `2000_DOTCOM_CRASH` | 2000 Dot-com Bubble Crash | 2000-03-01 ~ 2002-10-31 | -42.08% | -51.40% | -47.14% | 16.62% | -2.86 | 64d | PASS |
| `2008_GFC` | 2008 Global Financial Crisis (GFC) | 2007-10-01 ~ 2009-03-31 | -42.91% | -42.26% | -44.62% | 18.30% | -2.51 | 95d | PASS |
| `2020_COVID_SHOCK` | 2020 COVID-19 Shock | 2020-02-01 ~ 2020-04-30 | -30.89% | -6.73% | -34.19% | 45.34% | -0.69 | 28d | PASS |
| `2022_INFLATION_RATE_HIKE` | 2022 Inflation & Rate-Hike Bear Market | 2022-01-01 ~ 2022-12-31 | -10.11% | -25.82% | -11.81% | 4.48% | -2.71 | 242d | PASS |

---

## 4. Granular Market Benchmark Attribution

| Market Index | CAGR (%) | Annual Volatility (%) | Sharpe Ratio | Max Drawdown (%) |
|---|---|---|---|---|
| **KOSPI** | 10.18% | 25.87% | 0.32 | -71.63% |
| **KOSDAQ** | 2.97% | 27.32% | 0.04 | -90.78% |
| **SP500** | 10.05% | 18.56% | 0.43 | -56.78% |
| **NASDAQ** | 13.75% | 23.93% | 0.49 | -77.93% |
| **RUSSELL2000** | 10.03% | 22.72% | 0.35 | -59.89% |

---

## 5. Methodology & Quantitative Governance

1. **Causal Integrity & Lookahead Prevention**:
   - Strictly enforced 1-day lag between signal generation ($T$) and order execution ($T+1$).
   - Statutory regulatory filing lags applied: KRX 45 calendar days (quarterly) and 90 days (annual); SEC 40 calendar days (10-Q) and 60 days (10-K).
   - Lookahead bias detected flag: `False` across all 8,089 daily bars.

2. **Dynamic 2D Regime Classification & Crisis Gating**:
   - GMM 10-feature macro regime detector classifying into 6 states (`BULL/SIDEWAYS/BEAR` x `LOW/HIGH_VOL`).
   - VIX velocity and term-structure inversion trigger emergency defensive gating, halving total exposure and activating EVT-CVaR tail risk hedging.

3. **Institutional Portfolio Risk Allocation**:
   - Ledoit-Wolf shrinkage covariance estimation with constant-correlation analytical fallback.
   - Fisher-Rao barycenter blending across 4 models: Black-Litterman, HERC, Risk Parity, and EVT-CVaR.
   - Target volatility scaling to 12.0% annualized risk budget.

4. **Execution Frictions & Dynamic Buffer Bands**:
   - Realistic statutory fees: KRX STT 18 bps (KOSPI) / 20 bps (KOSDAQ) + 3 bps commission; US SEC 0.3 bps + 0.5 bps commission.
   - Dynamic bid-ask half-spreads (2–10 bps) and Gatheral 3/2 power-law market impact penalty.
   - Leland dynamic buffer bands with fresh entry / full exit bypass and TurnoverOptimizer hysteresis preventing micro-trading drag.

---

*Report generated autonomously by Historical30YrAnalytics Engine in compliance with Milestone M3 / M4 verification protocols.*
