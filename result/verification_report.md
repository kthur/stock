# Macroeconomic & Stock Market Data Integrity Verification Report

- **Generated At**: 2026-11-18T11:41:36.830784+00:00
- **Overall Status**: **[PASS]**
- **Dataset Health Score**: **97.84 / 100.0** (EXCELLENT)
- **Synthetic Rows Invariant**: `0` (Zero Synthetic Data)

---

## 1. Executive Summary

| Category | Status | Score | Key Quantitative Metrics |
|---|:---:|:---:|---|
| **R1: Macroeconomic Data Integrity** | `[PASS]` | 100.0 / 100 | 12/12 in bounds, Missing Rate: 0.0%, Cache Corruption: False |
| **R2: Stock Price & Volume Integrity** | `[PASS]` | 94.59 / 100 | 25 symbols across 5 markets, OHLC Violations: 0, Mean Zero Volume: 0.0041 |
| **R3: Correlation & Lead-Lag Consistency** | `[PASS]` | 100.0 / 100 | 6/6 checks passed, Meucci ESC: 4.01 (min 2.5), Temporal +1d Shift Verified |

---

## 2. Macroeconomic Data Integrity (R1)

| Symbol | Description | Price / Yield | Plausible Range | Scaling Checked | Status | Source |
|---|---|:---:|:---:|:---:|:---:|---|
| `^VIX` | CBOE Volatility Index | 20.6300 | [5.0, 120.0] | Standard | `[PASS]` | sqlite_storage |
| `^TNX` | US 10Y Treasury Yield | 5.1390 | [0.0, 15.0] | Standard | `[PASS]` | sqlite_storage |
| `USDKRW=X` | USD/KRW FX Rate | 1334.9900 | [900.0, 2500.0] | Standard | `[PASS]` | sqlite_storage |
| `CL=F` | WTI Crude Oil Futures | 87.5800 | [10.0, 300.0] | Standard | `[PASS]` | sqlite_storage |
| `GLD` | Gold ETF | 355.4500 | [50.0, 1000.0] | Standard | `[PASS]` | sqlite_storage |
| `GC=F` | Gold Futures | 3871.5000 | [300.0, 10000.0] | Standard | `[PASS]` | sqlite_storage |
| `DX-Y.NYB` | US Dollar Index (DXY) | 103.5020 | [50.0, 200.0] | Standard | `[PASS]` | sqlite_storage |
| `^SOX` | PHLX Semiconductor Index | 10146.3200 | [100.0, 30000.0] | Standard | `[PASS]` | sqlite_storage |
| `^GSPC` | S&P 500 Index | 7561.6700 | [1000.0, 10000.0] | Standard | `[PASS]` | sqlite_storage |
| `^IXIC` | NASDAQ Composite Index | 25136.2700 | [1000.0, 50000.0] | Standard | `[PASS]` | sqlite_storage |
| `^KS11` | KOSPI Index | 5100.5000 | [500.0, 15000.0] | Standard | `[PASS]` | sqlite_storage |
| `^KQ11` | KOSDAQ Index | 665.6500 | [100.0, 5000.0] | Standard | `[PASS]` | sqlite_storage |

### Storage & Database Persistence
- **Market Indicators DB**: `D:\Finance\code\stock\trading_system\market_indicators.db`
- **Total Indicator Rows**: 1,097
- **NULL Prices Count**: 0
- **Non-Positive Prices Count**: 0
- **Max Calendar Date Gap**: 3 days

---

## 3. Stock Price & Trading Volume Integrity across 5 Markets (R2)

| Market | Symbols Sampled | Passed | Total Bars | OHLC Invariant Violations | Zero Vol Ratio | Extreme Spikes (>300%) | Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **KOSPI** | 5 | 4 | 25,394 | 0 | 0.0080 | 1 | `[WARN]` |
| **KOSDAQ** | 5 | 5 | 21,654 | 0 | 0.0081 | 0 | `[PASS]` |
| **SP500** | 5 | 5 | 32,349 | 0 | 0.0000 | 0 | `[PASS]` |
| **NASDAQ** | 5 | 5 | 24,763 | 0 | 0.0000 | 0 | `[PASS]` |
| **RUSSELL2000** | 5 | 4 | 10,622 | 0 | 0.0081 | 0 | `[PASS]` |

---

## 4. Macro-to-Stock Correlation and Lead-Lag Consistency (R3)

### Directional & Elasticity Sign Checks
- **USD/KRW vs KOSPI Direction**: `rho(lag 0) = -0.3565`, `rho(lag 1) = 0.2009` -> `[PASS]`
- **VIX Volatility Tail Risk**: `rho(VIX, S&P 500) = -0.8493` -> `[PASS]`
- **Sector Rate Elasticity**: Bank Beta (`-0.2217`) vs Tech Beta (`-0.9975`) -> `[PASS]`
- **Sector FX Elasticity**: Exporter Beta (`-1.7295`) vs Utility Beta (`-1.879`) -> `[PASS]`

### Empirical Stock-Level Macro Sensitivities & Elasticity Betas
| Sector | Asset Name | Symbol | Evaluated Bars | Rate Beta (^TNX) | FX Beta (USDKRW) | Market Beta (^KS11) | VIX Vol Corr |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Financials** | Shinhan Financial Group | `055550` | 150 | -0.2217 | -1.0503 | +0.3666 | +0.1177 |
| **Semiconductor** | Samsung Electronics | `005930` | 215 | -0.9975 | -2.8467 | +1.2679 | +0.1046 |
| **Automotive** | Hyundai Motor | `005380` | 150 | -0.1032 | -1.7295 | +0.9603 | +0.1179 |
| **Utilities** | Korea Electric Power (KEPCO) | `015760` | 150 | -0.6169 | -1.8790 | +0.6669 | +0.1177 |

### Temporal & Diversification Checks
- **Meucci Effective Signal Count (ESC)**: `4.01` (Threshold: `>= 2.5`) -> `[PASS]`
- **Peak Lead-Lag Offset**: `tau* = 1` (+1d US lag shift applied for KRX equities) -> `[PASS]`

---

## 5. Invariants & Acceptance Verdict

- **Zero Synthetic Rows**: Verified pure Python integer `synthetic_rows == 0`.
- **OHLC Consistency**: $Low \le Open \le High$ and $Low \le Close \le High$ strictly enforced across all equity feeds.
- **Overall Pipeline Verdict**: **PASS** (Health Grade: **EXCELLENT**).
