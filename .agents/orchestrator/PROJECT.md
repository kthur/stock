# Project: Stock Trading System Quantitative Review, Diagnosis & Advanced Roadmap

## System Architecture Overview
Integrated Stock Trading System managing 3,379 symbols (SP500, KOSPI, KOSDAQ, KONEX) with 17 multi-factor / multi-model strategies:
1. XGBoost Regression (`src/ai/prediction_model.py`)
2. Surge Classifier (`src/ai/prediction_model.py`)
3. Lead-Lag Matrix (`src/ai/prediction_model.py`)
4. VCP Rule-based (`src/ai/vcp_detector.py`)
5. VCP ML (`src/ai/vcp_ml_predictor.py`)
6. Strict Causal LSTM (`src/ai/lstm_predictor.py`)
7. Stat-Arb Cointegration (`src/core/stat_arb.py`)
8. Sector Rotation (`src/core/sector_rotation.py`)
9. RIM Valuation (`src/core/rim_valuation.py`)
10. Event-Driven (`src/core/event_driven.py`)
11. Momentum Quality (MQ) (`src/core/mq_factor.py`)
12. Options IV Skew (`src/core/iv_skew.py`)
13. Order Flow Imbalance (`src/core/order_flow.py`)
14. Short-Term Reversal (`src/core/short_term_reversal.py`)
15. Analyst Revision Momentum (ARM) (`src/core/arm_factor.py`)
16. Cross-Asset Regime Divergence (CARD) (`src/core/card_factor.py`)
17. Liquidity-Adjusted Tail Risk (LATR) (`src/core/latr_factor.py`)

Infrastructure & Engine Layer:
- `trading_system/run_pipeline.py`: Pipeline Orchestration
- `src/ai/ensemble_scorer.py`: Dynamic 2D Regime Ensemble Engine & Dynamic Re-weighting
- `src/analysis/coverage_analyzer.py`: Strategy Coverage & Missingness Analyzer
- `src/risk/risk_manager.py`: Macro Crisis Detector & Gating
- `src/config.py`: Cost Models & Risk Limits

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Financial & System Architecture Diagnosis (R1) | Quant alpha validity, lookahead bias, risk-adjusted returns, transaction costs, DB I/O, multi-threading, missingness handling | None | DONE |
| 2 | Core Improvements & Code Architecture Proposals (R2) | Financial & system defect fixes, RiskManager / Crisis Gating, Portfolio Optimization (Risk Parity & Covariance Shrinkage), OMS execution scheduler | M1 | DONE |
| 3 | Additional Alpha Strategies & Phase 1-4 Roadmap (R3) | Next-Gen Alpha Strategies (LLM Sentiment, Real-Time Orderbook Imbalance, Macro HMM) & Phase 1-4 Roadmap | M2 | DONE |
| 4 | Review, Synthesis, Final Report & Forensic Audit | Comprehensive report synthesis, multi-agent review, verification & forensic audit | M1, M2, M3 | IN_PROGRESS |

## Code Layout
- `trading_system/run_pipeline.py`: Pipeline Orchestration
- `src/ai/ensemble_scorer.py`: 17-strategy dynamic ensemble scoring engine
- `src/analysis/coverage_analyzer.py`: Strategy missingness & coverage analysis
- `src/risk/risk_manager.py`: Risk management & crisis gating
- `src/data_layer/indicator_storage.py`: SQLite WAL database storage
- `src/persistence/database.py`: Stock price database engine
