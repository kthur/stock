## 2026-08-22T08:00:46Z
You are the Project Orchestrator for the stock trading system audit project.

Your Working Directory: d:\Finance\code\stock\.agents\orchestrator_quant_audit
Project Workspace: d:\Finance\code\stock
Authoritative User Request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md

Please conduct an end-to-end quantitative, algorithmic, and architectural audit of the entire stock trading codebase (`d:\Finance\code\stock`) to diagnose all bottlenecks limiting investment returns (Sharpe, Calmar, Net Alpha) and operational stability across 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ), and produce an exhaustive, actionable improvement report with concrete mathematical formulas, code refactor proposals, and prioritized execution steps.

Follow the requirements in ORIGINAL_REQUEST.md:
- R1. 31-Strategy Alpha Engine & Predictive Signal Diagnostic: Audit all 31 alpha and multi-factor strategies. Identify factor decay, lookahead risks, horizon mismatches (1d~200d), sample weighting biases, feature collinearity, and regime-conditional breakdown.
- R2. Factor Orthogonalization & Dynamic Regime Ensemble Audit: Examine FactorOrthogonalizerEngine, FactorSuppressionEngine, and EnsembleScoringEngine across 6 macro/market regimes. Identify signal dilution or cancellation issues.
- R3. Portfolio Optimization, Tail Risk Budgeting & Cost Modeling: Review PortfolioOptimizer (HRP, Ledoit-Wolf), PortfolioAllocator (EVT-CVaR, Leland buffer bands), microstructure cost model, and slippage feedback loop.
- R4. Pipeline Operations, Concurrency, and Data Ingestion Stability: Audit run_pipeline.py, MarketIndicatorStorage, StockPriceDB, async fundamental fetch, float32 optimizations, and CI/CD GHA workflow.
- R5. Comprehensive Improvement Report & Actionable Implementation Roadmap: Produce `IMPROVEMENT_ROADMAP.md` (and/or detailed markdown reports) containing Executive Summary, Strategy-by-Strategy Alpha Enhancement Proposals with concrete formulas/pseudocode/target files, Ensemble & Portfolio Construction Enhancements, Operational & Execution OMS Optimizations, and Prioritized Action Matrix (Critical/High/Medium/Low) with estimated Sharpe/return impact and implementation complexity.
