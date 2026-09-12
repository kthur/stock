# Project: Stock Trading System Pipeline & 37-Strategy Institutional Trading Architecture

## Architecture
- **Data & Ingestion Layer**: `src/data_layer/indicator_storage.py`, `src/data_layer/earnings_data.py`, `src/persistence/database.py`, `download_db.py`, `preseed_data.py`.
- **Model Training & Inference Layer**: `src/ai/prediction_model.py`, `src/ai/vcp_ml_predictor.py`, `src/ai/vcp_detector.py`, `train_models.py`, `run_pipeline.py`.
- **37-Strategy Factor Engine & Ensemble**: `src/core/*`, `src/ai/score_normalizer.py`, `src/ai/ensemble_scorer.py`, `src/ai/factor_orthogonalizer.py`, `src/core/strategy_registry.py`.
- **Portfolio & Risk Management Layer**: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `src/risk/risk_manager.py`, `src/analysis/portfolio_optimizer.py`, `src/execution/oms_engine.py`, `src/execution/slippage_feedback.py`.
- **Institutional Execution & Broker Layer**: `src/core/fast_lob_engine.py`, `src/broker/fix_protocol_engine.py`, `src/broker/interactive_brokers.py`, `src/execution/smart_order_router.py`, `src/execution/rl_execution_agent.py`.
- **Reporting & Visualization Layer**: `src/pipeline/reporter.py`, `trading_system/generate_report.py`, `gh-pages/index.html`.
- **CI/CD & Verification Layer**: `.github/workflows/pipeline.yml`, `preseed.yml`, `training.yml`, `trading_system/scripts/verify_gha_artifacts.py`, `merge_predictions.py`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | GHA 5-Market Pipeline Integrity | Validate and patch workflow scripts (`pipeline.yml`, `preseed.yml`, `training.yml`) for 5 markets end-to-end | M1 | Survey 1 / ORIGINAL_REQUEST R1 |
| F02 | GHA Static List & Cache Fallback | Add `lstm_predictions.txt` to `pipeline.yml` and `restore-keys` to `training.yml` | M1 | Survey 1 / ORIGINAL_REQUEST R1 |
| F03 | 31-Strategy Canonical Master Sequence | Standardize strategy ordering 1~31 across `AGENTS.md`, `run_pipeline.py`, and `reporter.py` | M2 | Survey 2 / ORIGINAL_REQUEST R2 |
| F04 | GHA Artifact Verifier 31-Strategy Expansion | Expand `verify_gha_artifacts.py` and `SKILL.md` from 23 to all 31 strategies in canonical order | M2 | Survey 2 / ORIGINAL_REQUEST R2 |
| F05 | Full Prediction Output Verification | Expand `run_pipeline.py` verification files list to cover all 31 strategy `.txt` files | M2 | Survey 2 / ORIGINAL_REQUEST R2 |
| F06 | Card 1: Market Regime & Risk Gates Console | Consolidate 2D Regime, Crisis Detector, VIX Velocity & Term Structure, Macro Grid into unified Card 1 | M3 | Survey 3 / ORIGINAL_REQUEST R3 |
| F07 | Card 2: Strategy Coverage & Missingness Center | Consolidate 31-Strategy Health Monitor, Dynamic Status Filters, Missingness Reasons, and CPCV/PBO Stress Test into unified Card 2 | M3 | Survey 3 / ORIGINAL_REQUEST R3 |
| F08 | Card 3: Portfolio Optimization & Execution OMS | Consolidate HRP Donut, Market Exposure, EVT-CVaR Tail Risk, Leland Buffer Bands, and Slippage Feedback into unified Card 3 | M3 | Survey 3 / ORIGINAL_REQUEST R3 |
| F09 | 31-Strategy Canonical Tab Navigation & Responsive UX | Standardize 1~31 tab sequence, responsive desktop/mobile layouts, tooltips, and stock drawer factor breakdown | M3 | Survey 3 / ORIGINAL_REQUEST R3 |
| F10 | E2E Artifact Verification & 100% Test Suite Pass | Run full pytest test suite and `verify_gha_artifacts.py` validating 100% pass and non-zero artifacts | M4 | ORIGINAL_REQUEST Acceptance Criteria |
| F11 | 37-Strategy Factor Expansion | Implement strategies 32~37 (Cross-Asset Spillover, Supply Chain GNN, Range Expansion Breakout, Dual Correction, Index Rebalance, Overnight Gap Reversal) | M5 | Institutional Expansion R14, R15 |
| F12 | Unified Institutional Portfolio Allocator | Implement `UnifiedPortfolioAllocator` with BL + HERC + RP + CVaR 4-model regime blending & 3/2-power market impact penalty | M6 | Institutional Expansion R15 |
| F13 | OMS Gate 8 Synthetic Beta Inverse Hedge | Add Gate 8 for automated inverse ETF hedging during Bear/Crisis regimes and fix currency denominator | M6 | Execution OMS R15 |
| F14 | Comprehensive V8 System Integrity Remediation | Resolve 43 system defects (Critical 13, High 16, Medium 14) across data lag, causality, PSD flooring, and pooling | M7 | V8 Integrity Audit |
| F15 | World-Class Quant & Trader Enhancements | Continuous Fractional Kelly, Midpoint Peg, Intraday ATR Trailing Ratchet, and Top-K concentration | M8 | World-Class Alpha Upgrade |
| F16 | Fast LOB Engine & L3 Orderbook Matching | Zero-copy ring buffer, Level 3 orderbook matching, Hawkes arrival intensity modeling (`fast_lob_engine.py`) | M9 | Institutional Execution R16 |
| F17 | FIX 4.4 Protocol Engine & IBKR Connector | Institutional DMA via FIX 4.4 protocol client and native Interactive Brokers TWS/Gateway socket connector | M9 | Institutional Execution R16 |
| F18 | Global Smart Order Router & RL Execution Agent | Intelligent multi-venue routing (KRX/US/Global) and Q-learning dynamic optimal order slicing agent | M9 | Institutional Execution R16 |
| F19 | Master Plan Phase 1-3 Systemic Quant Enhancements | 30-day rolling RankIC dynamic alpha weighting, contrarian reversal alpha in crash, EWMA covariance ($\lambda=0.94$), continuous Leland bands | M10 | Quant Master Plan R19 |
| F20 | Consolidated 3 Mega Cards Dashboard & 37-Alpha Radar | 3 Mega Cards UX architecture, 37-Alpha radar chart, column presets, stock drawer factor breakdown, and watchlist | M10 | Dashboard Modernization R19 |
| F21 | Top-Decile Spread 0.833 Alpha Ceiling Unlock | Remove premature [-0.5, 0.5] clipping before power expansion in `combine_predictions` to restore top 5% convexity | M11 | ORIGINAL_REQUEST R1 |
| F22 | NaN-Aware & Softplus Smooth Convex Boost | Use asset's own mean rather than 0.0 for NaNs and replace Heaviside step with continuous sigmoid gate | M11 | ORIGINAL_REQUEST R1 |
| F23 | Tri-Linear Synergy Kernel & Full 6-Regime Coupling | Add tri-linear confluence ($\Xi_{tri}$) and differentiate LOW_VOL vs HIGH_VOL across all 6 regimes | M11 | ORIGINAL_REQUEST R1 |
| F24 | Sideways 2D Regime Weight Rebalancing | Trim whipsaw false breakouts and reallocate to stat_arb, dual_correction, reversal | M11 | ORIGINAL_REQUEST R1 |
| F25 | Single-Stock KER Dynamic Alpha Switching | Activate `apply_ker_dynamic_alpha_switching` in `combine_predictions` based on Kaufman efficiency | M11 | ORIGINAL_REQUEST R1 |
| F26 | Strategy-Class Asymmetric Half-Life Filtering | Accelerate decay for momentum in sideways regimes while extending in bull regimes | M11 | ORIGINAL_REQUEST R1 |
| F27 | Regime-Adaptive Bessembinder Tail Thresholds | Parameterize `u_thresh` by 2D regime (0.45 Bull Low Vol to 0.70 Sideways High Vol) in Bessembinder convex scaling | M11 | ORIGINAL_REQUEST R1 |
| F28 | Downside Semi-Covariance (Sortino) EVT-CVaR Optimization | Blend `compute_downside_semi_cov` into `calculate_cvar_weights` to penalize downside risk while preserving upside runners | M12 | ORIGINAL_REQUEST R2 |
| F29 | Dynamic Model Conviction & Return-Dispersion Blending | Modulate BL vs HERC/CVaR blend dynamically based on cross-sectional alpha dispersion | M12 | ORIGINAL_REQUEST R2 |
| F30 | Market-Specific STT & Fee-Aware Leland Buffers | Adapt Leland buffer cost sizing by asset/market (25 bps KRX for STT, 3.5-8 bps US) to suppress Korean churn by 35%+ | M12 | ORIGINAL_REQUEST R2 |
| F31 | Multi-Tier L2 OBI & Micro-Price Pegging | Enhance `calculate_peg_limit_price` with volume-weighted micro-price and composite multi-tier OBI (1, 5, 10 levels) | M12 | ORIGINAL_REQUEST R2 |
| F32 | Hawkes Arrival Intensity Adverse Selection Gating | Gate primary maker leg allocations in `SmartOrderRouter.route_order` when Hawkes arrival intensity spikes | M12 | ORIGINAL_REQUEST R2 |
| F33 | Closed-Loop Empirical Slippage Feedback Scaling | Dynamically scale Gatheral impact coefficient $\kappa_{\text{eff}}$ using realized execution slippage from `trade_logs.db` | M12 | ORIGINAL_REQUEST R2 |
| F34 | Phase 4 Benchmark Performance Engine & Reports | Build `benchmark_phase4_quant_performance.py` and generate comprehensive comparison tables for all 5 markets across Phase 3 vs Phase 4 | M13 | ORIGINAL_REQUEST R3 |
| F35 | High-Order Non-Linear Signal Combination & Right-Tail Convexity | Regime-adaptive Richards exponent $\gamma_{\text{tail}} \in [1.00, 1.30]$, quadratic rank modulation, Quad-Pillar confluence kernel $\Xi_{\text{quad}}$, Hölder $p=2.0$ quadratic mean boost, asymmetric Richards tail scaling ($\eta_{\text{right}}=2.0$) | M15 | ORIGINAL_REQUEST R1 |
| F36 | Regime Transition Half-Life Dynamic Decay & Downside Noise Filtering | Probabilistic regime half-life expectation with Shannon entropy factor $\phi_{\text{entropy}}$ & TV jump penalty $\phi_{\text{jump}}$, and smooth tanh noise deadband attenuation $z \cdot \tanh((|z|/\delta)^3)$ | M15 | ORIGINAL_REQUEST R1 |
| F37 | 4-Model Portfolio Allocation & Capital Efficiency 5th Deepening | Higher-order co-skewness/co-kurtosis alpha conviction tilt, dynamic Cornish-Fisher EVT-CVaR tail expansion, DRP-DR scaling, and Shannon entropy-weighted adaptive target volatility scaling | M16 | ORIGINAL_REQUEST R2 |
| F38 | SOR & Darkpool/HFT OBI Pegging & Micro-Friction Slippage Minimization | Continuous Hawkes toxicity modulation, Darkpool midpoint resting with MinQty $\ge 20\%$, volatility/depth-adaptive L2 OBI micro-price curvature, ADV-adaptive Gatheral slice count with volume smile, and 5-market Leland buffer bands | M16 | ORIGINAL_REQUEST R2 |
| F39 | Phase 5 Benchmark Performance Engine & Multi-Market Comparison Reports | Build `benchmark_phase5_quant_performance.py`, generate 5-market comparison tables across 15 metrics, sync to 3 report destinations, and build `test_benchmark_phase5.py` | M17 | ORIGINAL_REQUEST R3 |
| F40 | Phase 5 Full Test Suite & Multi-Agent Forensic Verification | Scale test suite to 2,380+ tests with 100% pass rate, zero regressions, and multi-agent forensic integrity audit | M18 | ORIGINAL_REQUEST Acceptance Criteria |
| F111 | Toposic Geometric Langlands & Derived Satake Equivalence Coupler | Bundle stack $\text{Bun}_G$ and derived Satake category $\mathcal{D}(\text{Gr}_G)$ obstruction $E_{\text{langlands}}$ and invariant $Z_{\text{satake}}$ | M1 (P23) | Phase 23 R1 |
| F112.1 | 18th-Order Ultra-Convex Rank Modulation | $g_{\text{v23}}(r) = 0.50 + 1.10 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{18})$ with regime-adaptive $\gamma_{\text{top}}$ up to 2.40 | M1 (P23) | Phase 23 R1 |
| F112.2 | 56th-Order Hexaquinquagintagonal Hyperbolic Deadband | $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{56})$ eliminating noise leakage to $< 10^{-30}$ | M1 (P23) | Phase 23 R1 |
| F113.1 | Lurie Geometric Langlands Barycenter & Ultra-Trans-Hyper EVaR | Fisher-Rao Riemannian manifold barycenter with $\mu_{\text{langlands}}=[2.10, 1.60, 1.55, 2.60]$ and $19! = 121,645,100,408,832,000$ tail bounds | M2 (P23) | Phase 23 R2 |
| F113.2 | KNK Quintessence-Phantom L3 & Preemptive OMS | Kerr-Newman-Kiselev double dark energy ($w_p = -4/3$), 0.000001 maker floor, 99.995% dark ATS, 99.999% anti-gaming, tick shading $-0.9995 \cdot \text{spread} \cdot (h-0.035)$ | M3 (P23) | Phase 23 R3 |
| F114 | Phase 23 Quantitative Benchmark Engine & Multi-Market Reports | `benchmark_phase23_quant_performance.py`, 5-market 15-metric benchmark reports synced across 3 paths, and dedicated test suites | M4 (P23) | Phase 23 R4 |
| F115 | Derived Arithmetic Topology & Étale-Motivic Spectral Homotopy Coupler | Étale-motivic spectral cohomology $H^*_{\text{ét-mot}}$, Artin-Verdier obstruction $E_{\text{arithmetic}}$ and L-function invariant $Z_{\text{spectral}}$ | M1 (P24) | Phase 24 R1 |
| F116.1 | 19th-Order Ultra-Convex Rank Modulation | $g_{\text{v24}}(r) = 0.50 + 1.12 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{19})$ with regime-adaptive $\gamma_{\text{top}}$ up to 2.50 | M1 (P24) | Phase 24 R1 |
| F116.2 | 60th-Order Hexacontagonal Hyperbolic Deadband | $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{60})$ eliminating noise leakage to $< 10^{-32}$ | M1 (P24) | Phase 24 R1 |
| F117.1 | Lurie Arithmetic Spectral Barycenter & Trans-Super-Hyper EVaR | Fisher-Rao Riemannian manifold barycenter with $\mu_{\text{arithmetic}}=[2.15, 1.65, 1.60, 2.70]$ and $20! = 2,432,902,008,176,640,000$ tail bounds | M2 (P24) | Phase 24 R2 |
| F117.2 | KNK Quintessence-Phantom-Tachyon L3 & Preemptive OMS | Kerr-Newman-Kiselev triple dark energy ($w_{\text{tachyon}} = -5/3$), 0.0000005 maker floor, 99.998% dark ATS, 99.9995% anti-gaming, tick shading $-0.9998 \cdot \text{spread} \cdot (h-0.030)$ | M3 (P24) | Phase 24 R3 |
| F118 | Phase 24 Quantitative Benchmark Engine & Multi-Market Reports | `benchmark_phase24_quant_performance.py`, 5-market 15-metric benchmark reports synced across 3 paths, and dedicated test suites | M4 (P24) | Phase 24 R4 |
| F119 | Non-Abelian Hodge Theory & Deligne-Simpson Spectral Moduli Coupler | Hitchin equations $\bar{\partial}_E \Phi = 0, F_A + [\Phi, \Phi^*] = 0$ harmonic bundle obstruction $E_{\text{hodge}}$ and Deligne-Simpson moduli invariant $Z_{\text{simpson}}$ | M1 (P25) | Phase 25 R1 |
| F120.1 | 20th-Order Ultra-Convex Rank Modulation | $g_{\text{v25}}(r) = 0.50 + 1.14 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{20})$ with regime-adaptive $\gamma_{\text{top}}$ up to 2.60 | M1 (P25) | Phase 25 R1 |
| F120.2 | 64th-Order Hexatetrahedral Hyperbolic Deadband | $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{64})$ eliminating noise leakage to $< 10^{-34}$ | M1 (P25) | Phase 25 R1 |
| F121.1 | Lurie Non-Abelian Hodge Barycenter & Ultra-Trans-Super-Hyper EVaR | Fisher-Rao Riemannian manifold barycenter with $\mu_{\text{hodge}}=[2.20, 1.70, 1.65, 2.75]$ and $21! = 51,090,942,171,709,440,000$ tail bounds | M2 (P25) | Phase 25 R2 |
| F121.2 | KNK Quintom 4-Dark-Energy L3 & Preemptive OMS | Kerr-Newman-Kiselev 4-dark-energy ($w_{\text{quintom}} = -2$), 0.0000002 maker floor, 99.999% dark ATS, 99.9998% anti-gaming, tick shading $-0.9999 \cdot \text{spread} \cdot (h-0.025)$ | M3 (P25) | Phase 25 R3 |
| F122 | Phase 25 Quantitative Benchmark Engine & Multi-Market Reports | `benchmark_phase25_quant_performance.py`, 5-market 15-metric benchmark reports synced across 3 paths, and dedicated test suites | M4 (P25) | Phase 25 R4 |
| F123 | Perfectoid Shimura Variety & Mochizuki IUT Coupler | Hodge-Tate filtration obstruction complex $E_{\text{shimura}}$ and Mochizuki theta-link moduli invariant $Z_{\text{mochizuki}}$ | M1 (P26) | Phase 26 R1 |
| F124.1 | 21st-Order Hyper-Convex Rank Modulation | $g_{\text{v26}}(r) = 0.50 + 1.16 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{21})$ with regime-adaptive $\gamma_{\text{top}}$ up to 2.70 | M1 (P26) | Phase 26 R1 |
| F124.2 | 68th-Order Hexaoctagonal Hyperbolic Deadband | $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{68})$ eliminating noise leakage to $< 10^{-36}$ | M1 (P26) | Phase 26 R1 |
| F125.1 | Lurie Mochizuki IUT Barycenter & Trans-Singular-Hyper EVaR | Fisher-Rao Riemannian manifold barycenter with $\mu_{\text{mochizuki}}=[2.25, 1.75, 1.70, 2.80]$ and $22! = 1,124,000,727,777,607,680,000$ tail bounds | M2 (P26) | Phase 26 R2 |
| F125.2 | KNK Chameleon 5-Dark-Energy L3 & Preemptive OMS | Kerr-Newman-Kiselev 5-dark-energy ($w_{\text{chameleon}} = -7/3$), 0.0000001 maker floor, 99.9995% dark ATS, 99.9999% anti-gaming, tick shading $-0.99995 \cdot \text{spread} \cdot (h-0.020)$ | M3 (P26) | Phase 26 R3 |
| F126 | Phase 26 Quantitative Benchmark Engine & Multi-Market Reports | `benchmark_phase26_quant_performance.py`, 5-market 15-metric benchmark reports synced across 3 paths, and dedicated test suites | M4 (P26) | Phase 26 R4 |
| F127 | Anabelian Grothendieck Section Conjecture Coupler | Étale fundamental group section obstruction $H_{\text{anabelian}}$ and arithmetic Grothendieck invariant $Z_{\text{anabelian}}$ | M1 (P27) | Phase 27 R1 |
| F128.1 | 22nd-Order Hyper-Convex Rank Modulation | $g_{\text{v27}}(r) = 0.50 + 1.18 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{22})$ with regime-adaptive $\gamma_{\text{top}}$ up to 2.80 | M1 (P27) | Phase 27 R1 |
| F128.2 | 72nd-Order Heptaduo-gonal Hyperbolic Deadband | $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{72})$ eliminating noise leakage to $< 10^{-38}$ | M1 (P27) | Phase 27 R1 |
| F129.1 | Lurie Anabelian Grothendieck Barycenter & Trans-Singular-Ultra EVaR | Fisher-Rao Riemannian manifold barycenter with $\mu_{\text{anabelian}}=[2.30, 1.80, 1.75, 2.85]$ and $23! = 25,852,016,738,884,976,640,000$ tail bounds | M2 (P27) | Phase 27 R2 |
| F129.2 | KNK Phantom-Chameleon 6-Dark-Energy L3 & Preemptive OMS | Kerr-Newman-Kiselev 6-dark-energy ($w_{\text{phantom\_chameleon}} = -8/3$), 0.00000005 maker floor, 99.9998% dark ATS, 99.99995% anti-gaming, tick shading $-0.99998 \cdot \text{spread} \cdot (h-0.015)$ | M3 (P27) | Phase 27 R3 |
| F130 | Phase 27 Quantitative Benchmark Engine & Multi-Market Reports | `benchmark_phase27_quant_performance.py`, 5-market 15-metric benchmark reports synced across 3 paths, and dedicated test suites | M4 (P27) | Phase 27 R4 |
| F131 | Motivic Galois & Deligne-Tannakian Duality Coupler | Deligne-Tannakian cycle defect obstruction $E_{\text{tannaka}}$ and Motivic Galois invariant $Z_{\text{tannaka}}$ | M1 (P28) | Phase 28 R1 |
| F132.1 | 23rd-Order Hyper-Convex Rank Modulation | $g_{\text{v28}}(r) = 0.50 + 1.20 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{23})$ with regime-adaptive $\gamma_{\text{top}}$ up to 2.90 | M1 (P28) | Phase 28 R1 |
| F132.2 | 76th-Order Hexaheptacontagonal Hyperbolic Deadband | $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{76})$ eliminating noise leakage to $< 10^{-40}$ | M1 (P28) | Phase 28 R1 |
| F133.1 | Lurie Tannakian Motivic Barycenter & Trans-Singular-Extreme EVaR | Fisher-Rao Riemannian manifold barycenter with $\mu_{\text{tannaka}}=[2.35, 1.85, 1.80, 2.90]$ and $24! = 620,448,401,733,239,439,360,000$ tail bounds | M2 (P28) | Phase 28 R2 |
| F133.2 | KNK Phantom-Chameleon-Quintom 7-Dark-Energy L3 & Preemptive OMS | Kerr-Newman-Kiselev 7-dark-energy ($w_{\text{phantom\_chameleon\_quintom}} = -3.0$), 0.00000002 maker floor, 99.9999% dark ATS, 99.99998% anti-gaming, tick shading $-0.99999 \cdot \text{spread} \cdot (h-0.012)$ | M3 (P28) | Phase 28 R3 |
| F134 | Phase 28 Quantitative Benchmark Engine & Multi-Market Reports | `benchmark_phase28_quant_performance.py`, 5-market 15-metric benchmark reports synced across 3 paths, and dedicated test suites | M4 (P28) | Phase 28 R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | GHA Pipeline & Model Integrity (R1) | F01, F02: GHA workflows, caching fallback, 5-market pipeline data seeding & model training | none | DONE |
| M2 | 31-Strategy Canonical Sequence Unification (R2) | F03, F04, F05: Canonical sequence 1~31 across pipeline, verifier, SKILL.md, and text outputs | M1 | DONE |
| M3 | Dashboard Metric Consolidation & UX Enhancement (R3) | F06, F07, F08, F09: 3 unified consolidated cards, 31 canonical tabs, responsive design in `generate_report.py` | M2 | DONE |
| M4 | E2E Testing & Full Verification | F10: 100% pytest pass (1,569 tests, 0 fails), artifact non-zero verification across 5 markets, gh-pages validation | M1, M2, M3 | DONE |
| M5 | 37-Strategy Factor Engine Scaling | F11: Strategies 32~37 implementation, scoring pipeline, and output reports | M4 | DONE |
| M6 | Institutional Portfolio & OMS Gate 8 | F12, F13: `UnifiedPortfolioAllocator` 4-model blending, OMS Gate 8 synthetic inverse hedge overlay | M5 | DONE |
| M7 | V8 System Integrity Remediation | F14: 43 defects resolved across data pipeline, causality, covariance shrinkage, and DB connection pooling | M6 | DONE |
| M8 | World-Class Trader Alpha Upgrade | F15: Top-K concentration, fractional Kelly, tick grid rounding, and test suite expansion | M7 | DONE |
| M9 | Institutional Ultra-Low Latency Execution Layer | F16, F17, F18: Fast LOB Engine, FIX 4.4 DMA, IBKR Connector, Global SOR, and RL Execution Agent | M8 | DONE |
| M10 | Master Plan Phase 1-3 Quant Upgrades & 2,182 Tests | F19, F20: 30-day RankIC, EWMA Cov, 3 Mega Cards Dashboard, and 2,182 pytest suite 100% pass | M9 | DONE |
| M11 | Phase 4 Dynamic Signal Quality & Top Alpha (R1) | F21~F27: 0.833 alpha unlock, softplus convex boost, tri-linear synergy kernel, sideways rebalancing, KER switching, asymmetric half-life, Bessembinder tail thresholds | M10 | DONE |
| M12 | Phase 4 Portfolio Allocation & Execution Friction Optimization (R2) | F28~F33: Downside semi-covariance Sortino CVaR, dispersion conviction blending, Korean STT Leland buffers, L2 OBI micro-pegging, Hawkes adverse selection gating, closed-loop slippage feedback | M11 | DONE |
| M13 | Phase 4 Quantitative Benchmark Engine & Multi-Market Reports (R3) | F34: `benchmark_phase4_quant_performance.py` and 5-market benchmark reports across 3 target destinations | M11, M12 | DONE |
| M14 | Phase 4 Full Test Suite & Forensic Verification (R4) | 2,333 items pytest suite 100% pass, zero regressions, and forensic audit verification | M11, M12, M13 | DONE |
| M15 | Phase 5 Dynamic Alpha Signal Quality & Top Alpha (R1) | F35, F36: `ensemble_scorer.py`, `test_phase5_signal_enhancement.py` | M14 | DONE |
| M16 | Phase 5 Portfolio Allocation & Execution Friction (R2) | F37, F38: `unified_portfolio_allocator.py`, `smart_order_router.py`, `oms_engine.py`, `test_phase5_portfolio_execution.py` | M15 | DONE |
| M17 | Phase 5 Quantitative Benchmark Engine & Multi-Market Reports (R3) | F39: `benchmark_phase5_quant_performance.py`, sync reports across 3 paths, `test_benchmark_phase5.py` | M15, M16 | DONE |
| M18 | Phase 5 Full Test Suite & Forensic Verification (R4) | F40: 2,380+ test suite 100% pass rate, zero regressions, multi-agent review, challenger & forensic audit | M15, M16, M17 | DONE |
| M1 (P23) | Phase 23 Alpha Signal Disentanglement & Ultra-Convex Modulation (R1) | F111, F112.1, F112.2: Toposic Geometric Langlands Coupler, 18th-order rank modulation, 56th-order deadband | none | DONE |
| M2 (P23) | Phase 23 Portfolio Allocation & Ultra-Trans-Hyper EVaR (R2) | F113.1: Lurie Geometric Langlands Barycenter, 19th-cumulant EVaR tail risk bounds, headroom redistribution | M1 (P23) | DONE |
| M3 (P23) | Phase 23 Microstructure Hydrodynamics & Preemptive OMS (R3) | F113.2: KNK Quintessence-Phantom L3, 99.995% dark ATS, 0.000001 maker floor, 99.999% anti-gaming, tick shading | M2 (P23) | DONE |
| M4 (P23) | Phase 23 Benchmark Engine & Forensic Verification (R4) | F114: `benchmark_phase23_quant_performance.py`, comparison reports, 60/60 tests 100% pass | M1, M2, M3 (P23) | DONE |
| M1 (P24) | Phase 24 Alpha Signal Disentanglement & Ultra-Convex Modulation (R1) | F115, F116.1, F116.2: Derived Arithmetic Topology Coupler, 19th-order rank modulation, 60th-order deadband | none | DONE |
| M2 (P24) | Phase 24 Portfolio Allocation & Trans-Super-Hyper EVaR (R2) | F117.1: Lurie Arithmetic Spectral Barycenter, 20th-cumulant EVaR tail risk bounds, headroom redistribution | M1 (P24) | DONE |
| M3 (P24) | Phase 24 Microstructure Hydrodynamics & Preemptive OMS (R3) | F117.2: KNK Quintessence-Phantom-Tachyon L3, 99.998% dark ATS, 0.0000005 maker floor, 99.9995% anti-gaming, tick shading | M2 (P24) | DONE |
| M4 (P24) | Phase 24 Benchmark Engine & Forensic Verification (R4) | F118: `benchmark_phase24_quant_performance.py`, comparison reports, 104/104 tests 100% pass | M1, M2, M3 (P24) | DONE |
| M1 (P25) | Phase 25 Alpha Signal Disentanglement & Ultra-Convex Modulation (R1) | F119, F120.1, F120.2: Non-Abelian Hodge Coupler, 20th-order rank modulation, 64th-order deadband | none | DONE |
| M2 (P25) | Phase 25 Portfolio Allocation & Ultra-Trans-Super-Hyper EVaR (R2) | F121.1: Lurie Non-Abelian Hodge Barycenter, 21st-cumulant EVaR tail risk bounds, headroom redistribution | M1 (P25) | DONE |
| M3 (P25) | Phase 25 Microstructure Hydrodynamics & Preemptive OMS (R3) | F121.2: KNK Quintom 4-Dark-Energy L3, 99.999% dark ATS, 0.0000002 maker floor, 99.9998% anti-gaming, tick shading | M2 (P25) | DONE |
| M4 (P25) | Phase 25 Benchmark Engine & Forensic Verification (R4) | F122: `benchmark_phase25_quant_performance.py`, comparison reports, tests 100% pass | M1, M2, M3 (P25) | DONE |
| M1 (P26) | Phase 26 Alpha Signal Disentanglement & Hyper-Convex Modulation (R1) | F123, F124.1, F124.2: Perfectoid Shimura Coupler, 21st-order rank modulation, 68th-order deadband | none | DONE |
| M2 (P26) | Phase 26 Portfolio Allocation & Trans-Singular-Hyper EVaR (R2) | F125.1: Lurie Mochizuki IUT Barycenter, 22nd-cumulant EVaR tail risk bounds, headroom redistribution | M1 (P26) | DONE |
| M3 (P26) | Phase 26 Microstructure Hydrodynamics & Preemptive OMS (R3) | F125.2: KNK Chameleon 5-Dark-Energy L3, 99.9995% dark ATS, 0.0000001 maker floor, 99.9999% anti-gaming, tick shading | M2 (P26) | DONE |
| M4 (P26) | Phase 26 Benchmark Engine & Forensic Verification (R4) | F126: `benchmark_phase26_quant_performance.py`, comparison reports, tests 100% pass | M1, M2, M3 (P26) | DONE |
| M1 (P27) | Phase 27 Alpha Signal Disentanglement & Hyper-Convex Modulation (R1) | F127, F128.1, F128.2: Anabelian Grothendieck Coupler, 22nd-order rank modulation, 72nd-order deadband | none | DONE |
| M2 (P27) | Phase 27 Portfolio Allocation & Trans-Singular-Ultra EVaR (R2) | F129.1: Lurie Anabelian Grothendieck Barycenter, 23rd-cumulant EVaR tail risk bounds, headroom redistribution | M1 (P27) | DONE |
| M3 (P27) | Phase 27 Microstructure Hydrodynamics & Preemptive OMS (R3) | F129.2: KNK Phantom-Chameleon 6-Dark-Energy L3, 99.9998% dark ATS, 0.00000005 maker floor, 99.99995% anti-gaming, tick shading | M2 (P27) | DONE |
| M4 (P27) | Phase 27 Benchmark Engine & Forensic Verification (R4) | F130: `benchmark_phase27_quant_performance.py`, comparison reports, tests 100% pass | M1, M2, M3 (P27) | DONE |
| M1 (P28) | Phase 28 Alpha Signal Disentanglement & Hyper-Convex Modulation (R1) | F131, F132.1, F132.2: Motivic Galois Tannakian Coupler, 23rd-order rank modulation, 76th-order deadband | none | DONE |
| M2 (P28) | Phase 28 Portfolio Allocation & Trans-Singular-Extreme EVaR (R2) | F133.1: Lurie Tannakian Motivic Barycenter, 24th-cumulant EVaR tail risk bounds, headroom redistribution | M1 (P28) | DONE |
| M3 (P28) | Phase 28 Microstructure Hydrodynamics & Preemptive OMS (R3) | F133.2: KNK Phantom-Chameleon-Quintom 7-Dark-Energy L3, 99.9999% dark ATS, 0.00000002 maker floor, 99.99998% anti-gaming, tick shading | M2 (P28) | DONE |
| M4 (P28) | Phase 28 Benchmark Engine & Forensic Verification (R4) | F134: `benchmark_phase28_quant_performance.py`, comparison reports, tests 100% pass | M1, M2, M3 (P28) | DONE |

## Interface Contracts
### GHA Workflows ↔ Pipeline Scripts
- `.github/workflows/pipeline.yml` executes `run_pipeline.py` producing per-market `result_split/*_{MARKET}.txt`.
- `merge_predictions.py` merges split files for all 37 strategies into `trading_system/result/*.txt` and invokes `generate_run_snapshot.py`.
- `generate_report.py` reads `trading_system/result/*.txt` and indicator SQLite DBs to produce `gh-pages/index.html`.

### 37-Strategy Canonical Specification (1~37)
1: `regression`, 2: `surge`, 3: `lead_lag`, 4: `vcp_rule`, 5: `vcp_ml`, 6: `lstm`, 7: `stat_arb`, 8: `sector_rotation`, 9: `rim_valuation`, 10: `event_driven`, 11: `mq_factor`, 12: `iv_skew`, 13: `order_flow`, 14: `short_term_reversal`, 15: `arm_factor`, 16: `card_factor`, 17: `latr_factor`, 18: `inst_foreign_sector`, 19: `supply_chain`, 20: `sentiment`, 21: `factor_neutralized`, 22: `vol_target`, 23: `microstructure`, 24: `accruals_quality`, 25: `short_squeeze`, 26: `valueup_catalyst`, 27: `trend_efficiency`, 28: `gamma_squeeze`, 29: `insider_buying`, 30: `darkpool`, 31: `earnings_tone_drift`, 32: `cross_asset_spillover`, 33: `supply_chain_gnn`, 34: `range_expansion_breakout`, 35: `dual_correction`, 36: `index_rebalance`, 37: `overnight_gap_reversal`.

## Code Layout
- `trading_system/run_pipeline.py`: Main orchestration script
- `trading_system/generate_report.py`: HTML dashboard generator
- `src/pipeline/reporter.py`: Pipeline summary text reporter
- `trading_system/scripts/verify_gha_artifacts.py`: CI artifact verifier
- `trading_system/scripts/merge_predictions.py`: 37-strategy multi-market file merger
- `trading_system/scripts/benchmark_phase4_quant_performance.py`: Phase 4 quantitative benchmarking and multi-market comparison engine
- `trading_system/scripts/benchmark_phase5_quant_performance.py`: Phase 5 quantitative benchmarking and multi-market comparison engine
- `trading_system/scripts/benchmark_phase22_quant_performance.py`: Phase 22 quantitative benchmarking and multi-market comparison engine
- `trading_system/scripts/benchmark_phase23_quant_performance.py`: Phase 23 quantitative benchmarking and multi-market comparison engine
- `trading_system/scripts/benchmark_phase26_quant_performance.py`: Phase 26 quantitative benchmarking and multi-market comparison engine
- `trading_system/scripts/benchmark_phase27_quant_performance.py`: Phase 27 quantitative benchmarking and multi-market comparison engine
- `trading_system/scripts/benchmark_phase28_quant_performance.py`: Phase 28 quantitative benchmarking and multi-market comparison engine
- `src/risk/unified_portfolio_allocator.py`: Institutional multi-model portfolio allocator
- `src/execution/oms_engine.py`: 8-Safety Gate execution engine
- `src/core/fast_lob_engine.py`: Fast LOB Level 3 matching engine
- `src/broker/fix_protocol_engine.py`: FIX 4.4 protocol DMA engine
- `src/broker/interactive_brokers.py`: Native IBKR connector
- `src/execution/smart_order_router.py`: Global multi-market Smart Order Router
- `src/execution/rl_execution_agent.py`: Reinforcement learning order slicing agent
- `tests/`: Automated unit, integration, and e2e test suite (2,500+ items)
