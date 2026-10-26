# Track 3: Autonomous Paper Trading Session & Shadow OMS Execution Report

- **Session Timestamp**: 2026-10-27T06:24:38.646772+09:00 (KST)
- **Execution Mode**: `PAPER`
- **Market Regime**: `BULL_LOW_VOL` (Crisis Level: `NORMAL`)
- **Rebalance Iterations**: 1
- **Mathematical Invariant (`Net Equity <= Gross Equity`)**: **PASSED**

## 1. Portfolio Financial Snapshot

| Metric | Value (KRW) | Percentage / Details |
| :--- | :---: | :---: |
| **Initial Capital** | 50,000,000.00 | 100.0% Baseline |
| **Gross Equity** | 50,000,000.00 | Before statutory fees & slippage |
| **Net Equity** | **49,999,843.88** | **Realized Net (Fees & Slippage accounted)** |
| **Cash Balance** | 48,988,743.88 | Unallocated liquid cash reserve |
| **Invested Market Value** | 1,011,100.00 | Active risk asset exposure |
| **Total Statutory Fees Paid** | 150.57 | KRX STT + Broker Fees |
| **Total Slippage Friction Cost** | 5.55 | Gatheral 3/2 & Fast LOB orderbook slippage |
| **Total Realized Net PnL** | 0.00 | Cumulative closed position returns |

## 2. Active Holdings & Rebalanced Positions

| Symbol | Market | Quantity | Avg Price | Current Price | Market Value (KRW) | Weight |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `196490` | KOSDAQ | 20 | 50,007.50 | 50,000.00 | 1,000,000.00 | 2.00% |
| `ABT` | SP500 | 46 | 100.05 | 100.00 | 4,600.00 | 0.01% |
| `AES` | SP500 | 7 | 100.06 | 100.00 | 700.00 | 0.00% |
| `AFL` | SP500 | 10 | 100.05 | 100.00 | 1,000.00 | 0.00% |
| `APD` | SP500 | 16 | 100.05 | 100.00 | 1,600.00 | 0.00% |
| `CAG` | SP500 | 17 | 100.06 | 100.00 | 1,700.00 | 0.00% |
| `MMM` | SP500 | 15 | 100.06 | 100.00 | 1,500.00 | 0.00% |

## 3. OMS Safety Gates & Friction Telemetry

- **Total Executions Processed**: 7
- **Enforced Gates**: Gate 1 (Crisis Gating), Gate 2 (Kill Switch), Gate 3 (Leland Buffer Bands), Gate 4 (Price Limits), Gate 5 (STT Net Alpha Hurdle), Gate 6 (Adverse Opening Gap), Gate 7 (ADV Cap), Gate 8 (Synthetic Beta Inverse Hedge).
- **Closed-Loop Feedback**: Live empirical execution slippages successfully transferred to `SlippageFeedbackEngine` and `trade_logs.db`.

---
**Verification Verdict**: Certified Institutional Paper Trading OMS Loop Operational.