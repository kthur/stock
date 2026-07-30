## 2026-07-30T04:29:08Z

<USER_REQUEST>
You are Worker M2 v2 (Core Improvements & Code Architecture Specialist).
Working directory: d:\Finance\code\stock\.agents\worker_m2_v2
Project Scope document: d:\Finance\code\stock\.agents\orchestrator\PROJECT.md

Your task is to formulate comprehensive, highly detailed code improvement proposals and technical specifications addressing all diagnosed financial and system vulnerabilities in requirement R2.

Your proposals must cover:
1. Strategy & Quant Fixes:
   - Stat-Arb Cointegration: Fit OLS on log prices $\ln(P)$, replace ADF step function with MacKinnon p-value surface, fix FDR ordering.
   - RIM Valuation: Correct terminal value formula $PV_{terminal} = BPS_N / (1+r_e)^N$, fix negative net income payout ratio.
   - LATR Factor: Invert drawdown penalty $-0.4 \times DD_{pct}$ and tail risk penalty $-0.2 \times |TailRisk|$.
   - CARD Factor: Normalize returns/macro inputs with rolling Z-scores before weighting.
   - Event-Driven: Match OpenDART corp_code exactly via mapping dict, penalize volume surge on price crash.
   - Lead-Lag: Shift US market dates by +1 day (KST alignment) to eliminate 15-hr lookahead.
   - Strict Causal LSTM: Multi-feature input with rolling sequence z-score normalization.
   - VCP Rule & ML: Symmetric window bounds, enforce $R_3 > R_2$, time-series purged split for ML lookback.
   - Missing strategy restoration: Restore `arm_factor`, `card_factor`, `latr_factor` in base weights, dataframe merges, and Coverage Analyzer `col_map`.
2. Microstructure & Transaction Cost Modeling:
   - Order Book Market Impact model: $Cost_{total} = Fee_{flat} + STT_{sell\_only} + \frac{Spread}{2} + \gamma \cdot \left(\frac{OrderSize}{ADV}\right)^\alpha \cdot \sigma_{daily}$.
   - Liquidity screening: Enforce minimum daily volume thresholds from `config.py`.
3. System Architecture & Concurrency:
   - SQLite WAL Connection Manager: Thread-safe pool with `busy_timeout=30000`, `synchronous=NORMAL`.
   - Thread safety in `StockPriceDB`: Add `threading.Lock()` mutex around writes.
   - Memory & Concurrency: ProcessPoolExecutor for CPU-bound feature extraction, periodic `gc.collect()`, float64 preservation for high monetary values.
4. Advanced Core Architecture:
   - Enhanced Risk Management: Pipeline `RiskManager` integration & 2D Market Crisis Gating.
   - Portfolio Optimization: Risk Parity allocation & Ledoit-Wolf Covariance Shrinkage.
   - OMS Execution Scheduler: Slice order execution, trade_logs.db, real-time tracking error and slippage monitoring.

Write your complete specification report to `d:\Finance\code\stock\.agents\worker_m2_v2\handoff.md` and send a message when done.
</USER_REQUEST>
