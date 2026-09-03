# Stock Trading System

## Project Overview

통합 주식 자동매매 및 예측 시스템. 한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장을 대상으로 **37대 다변화 전략(Multi-Factor & Multi-Model)**을 병행 운영 및 2D/Dual 시장 레짐 기반 앙상블, 포트폴리오 최적화, 자율 주문 실행(OMS)을 수행합니다:

| # | 전략 | 방식 | 출력 |
|---|------|------|------|
| **1** | XGBoost 회귀 | 8개 horizon(1~200d) 예상수익률 | `pipeline_result.txt` |
| **2** | Surge 분류기 | 4개 horizon(1/3/5/20d) 급등 확률 (scale_pos_weight ≤ 20.0) | `surge_predictions.txt` |
| **3** | Lead-Lag | 2-Tier 업종 지수/대형주 시차 상관성 기반 후행 종목 (+1d US Lag Shift) | `lead_lag_predictions.txt` |
| **4** | VCP 패턴 | 변동성 수축 + 거래량 감소 + 고점 근접 규칙 | `vcp_patterns.txt` |
| **5** | VCP ML | 시장별 XGBClassifier 기반 VCP 급등 확률 | `vcp_ml_predictions.txt` |
| **6** | Strict Causal LSTM | 시점 분리 롤링 정규화 기반 시계열 딥러닝 | `lstm_predictions.txt` |
| **7** | Stat-Arb Cointegration | Log 주가 잔차 평균회귀 Z-score 기반 횡보장 차익거래 | `stat_arb_predictions.txt` |
| **8** | Sector Rotation | KRX/GICS 업종 1M/3M 상대모멘텀 & 순환매 수급 | `sector_predictions.txt` |
| **9** | RIM Valuation | 잔여이익 모델 기반 정밀 가치평가 (Terminal Value 보정) | `rim_predictions.txt` |
| **10** | Event-Driven | DART 공시, 실적 서프라이즈, 자사주, 거래량 3배 | `event_driven_predictions.txt` |
| **11** | Momentum Quality (MQ) | 12M-1M 모멘텀 - 1M 반전 노이즈 제거 + 영업이익률/ROE | `mq_factor_predictions.txt` |
| **12** | Options IV Skew | yfinance 풋/콜 IV Skew 및 공포 역발상 매수 점수 | `iv_skew_predictions.txt` |
| **13** | Order Flow Imbalance | 외인/기관 순매수 수급 가속도 (MFI) | `order_flow_predictions.txt` |
| **14** | Short-Term Reversal | 3~5일 연속 과매도/볼린저 하단 이탈 평균회귀 | `short_term_reversal_predictions.txt` |
| **15** | Analyst Revision Momentum (ARM) | 컨센서스 EPS/목표주가 추정치 상향 조정 및 실적 서프라이즈 | `arm_factor_predictions.txt` |
| **16** | Cross-Asset Regime Divergence (CARD) | 주식-원자재-환율 이탈 괴리율 역발상 매수 스코어링 | `card_factor_predictions.txt` |
| **17** | Liquidity-Adjusted Tail Risk (LATR) | 52주 고점 낙폭(DD) + 유동성 서지 - 하방 꼬리위험 페널티 | `latr_factor_predictions.txt` |
| **18** | Inst & Foreign Sector | 외인/투신 2개월 수급 누적 & 업종 주도주 상관성 | `inst_foreign_sector_predictions.txt` |
| **19** | Supply Chain Momentum | 전방 대표기업 1D/3D 수익률 ➔ 부품/장비 공급망 시차 온기 전이 | `supply_chain_predictions.txt` |
| **20** | NLP Sentiment Catalyst | DART/SEC 공시 요약, 기업 뉴스, 실적 텍스트 FinBERT 감성 스코어 | `sentiment_predictions.txt` |
| **21** | Multi-Factor Style Neutralizer | Fama-French 5-Factor(시총/가치/수익성/투자) 노출 제거 순수 알파 | `factor_neutralized_predictions.txt` |
| **22** | Dynamic Volatility Targeting | 실산출 변동성 및 목표 변동성(연 12%) 리스크 파리티 비중 스코어링 | `vol_target_predictions.txt` |
| **23** | Microstructure Imbalance | 호가창 매수/매도 잔량 불균형 & 종가 동시호가 수급 오버나이트 갭 | `microstructure_predictions.txt` |
| **24** | Accruals Quality Anomaly | 당기순이익 대비 영업현금흐름(OCF) 괴리율 회계적 품질 점수 | `accruals_quality_predictions.txt` |
| **25** | Short Interest & Squeeze | 공매도 잔고 비율 + Days-to-Cover + 5D 상승 모멘텀 숏스퀴즈 촉매 | `short_squeeze_predictions.txt` |
| **26** | Value-Up & Shareholder Yield | PBR 1배 미만 + 순현금/시총 + 총주주환원율(배당+자사주 소각) | `valueup_catalyst_predictions.txt` |
| **27** | Kaufman Trend Efficiency | 5D/10D/20D KER(트렌드 효율성) + Hurst Exponent 고순도 추세 필터 | `trend_efficiency_predictions.txt` |
| **28** | Gamma Squeeze | 옵션 미결제약정 및 콜 옵션 델타 가속도 기반 숏/델타 스퀴즈 | `gamma_squeeze_predictions.txt` |
| **29** | Insider Buying | 임원/대주주 내부자 매수 공시 및 수급 수치화 | `insider_buying_predictions.txt` |
| **30** | Darkpool & HFT Flow | 다크풀 블록트레이드 & HFT 마이크로스프레드 모멘텀 | `darkpool_predictions.txt` |
| **31** | Earnings Tone Drift | 실적 발표 콘퍼런스콜 텍스트 톤 변화 감성 퀀트 | `earnings_tone_drift_predictions.txt` |
| **32** | Cross-Asset Spillover Momentum | 업종별 거시지표(SOX/FX/WTI/TNX/VIX/Gold/DXY/SP500) 탄력도 벡터 기반 글로벌 매크로 임펄스 & 주가 미가격 리드-래그 파급 | `cross_asset_spillover_predictions.txt` |
| **33** | Supply Chain GNN | 글로벌 밸류체인 2-hop 그래프 메시지 패싱 + 불위그 쇼크 비선형 증폭 & 업종 플로우 유동성 모멘텀 | `supply_chain_gnn_predictions.txt` |
| **34** | Range Expansion Breakout | 변동성 압축(NR7/볼린저 스퀴즈/Inside Day) 후 REF≥1.5 폭발적 레인지 확장 + RVOL≥1.8 거래량 서지 + CLV≥0.65 | `range_expansion_predictions.txt` |
| **35** | Dual Correction | 피보나치(38.2%/50%/61.8%) 및 앵커드 VWAP 가격 조정 + 거래량 고갈 정밀 눌림목 반등 | `dual_correction_predictions.txt` |
| **36** | Index Rebalance Structural Flow | KOSPI200/MSCI 패시브 ETF 40조 수급 리밸런싱 15~30일 선반영 패시브 추종 차익 | `index_rebalance_predictions.txt` |
| **37** | Overnight Gap Reversal | 개장가-전일종가 갭 정규화(ATR) 기반 통계적 갭 메우기(Gap Fill) 및 오버익스텐션 반전 | `overnight_gap_predictions.txt` |

## Pipeline

`run_pipeline.py` 실행 순서:

```
1. Load config (TradingConfig)
2. Fetch global indicators (VIX, TNX, USDKRW, WTI, Gold, DXY, SOX 등 — 적응형 타임아웃 & 지터 지수 백오프)
3. Store market indicators (SQLite WAL & Write Mutex)
4. Load/update stock universe (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000)
5. Fetch indicator history (train + inference)
6. Prepare training data (Market x Sector x Cap 층화 샘플링 + 동적 Filing Lag[KRX 45d, US 40d] + float32 다운캐스팅)
7. Train:
   a. Regression (per market: sp500/nasdaq/russell2000/kospi/kosdaq)
   b. Surge classifier (per market, capped scale weight)
   c. Lead-Lag 2-tier matrix
   d. VCP ML (per market)
   e. Strict Causal LSTM sequence models
   f. Isotonic & Platt Regression Calibrators fitting
8. Fetch inference fundamentals (background async, dynamic filing lag applied)
9. Fetch inference price data (ALL symbols)
10. Predict:
    a. Regression + Surge (shared feature computation)
    b. VCP rule-based pattern detection
    c. Lead-Lag 2-tier inference
    d. Stat-Arb pair cointegration scanning (순수 통계적 유의 페어만 선별)
    e. Sector Rotation relative momentum scoring
    f. 37-Strategy factor scoring (전략 1~37 동시 병렬 스코어링)
    g. CrossSectionalScoreNormalizer (Percentile Rank / Winsorized Gaussian CDF [0.05, 0.95])
    h. 37-Strategy Dynamic Weighted Ensemble Scoring (PCA-ZCA Whitening, Gram-Schmidt Decorrelation, Missing Strategy Zero-Weighting, Microstructure friction costs deduction & RiskManager Crisis Gating)
11. Portfolio Optimization & Execution:
    a. UnifiedPortfolioAllocator: Black-Litterman, HERC, Risk Parity, EVT-CVaR 4-Model Regime Blending & 3/2-Power Market Impact Penalty
    b. EVT-CVaR Tail Risk Budgeting & Leland No-Trade Buffer Bands (새 진입/전량 청산 즉시 바이패스)
    c. Execution OMS 8-Safety Gates (Gate 8: 합성 인버스 헤지 오버레이), Almgren-Chriss Slicing & Slippage Feedback Loop (`trade_logs.db`)
12. Save predictions to DB & 37-Strategy Ensemble Output + Strategy Data Coverage Report
13. Save output files & Update GitHub Pages HTML Report (KST Timezone)
```

## Architecture

### Overall Block Diagram

```mermaid
flowchart TB
    subgraph Data ["Data Storage & Orchestration Layer"]
        DB[("StockPriceDB / MarketIndicatorStorage\n(SQLite WAL, Write Lock Mutex)")]
        EData["Earnings & Fundamental Fetcher\n(Adaptive Retry, Dynamic Market Filing Lag)")]
        GraphDB["Value Chain Knowledge Graph\n(2-Hop Relational Edges)"]
    end

    subgraph Strategies ["37-Strategy Multi-Factor Engine"]
        Reg["1. XGBoost Regression"]
        Surge["2. Surge Classifier"]
        LL["3. Lead-Lag Shift (+1d US)"]
        VCP_Rule["4. VCP Rule Pattern"]
        VCP_ML["5. VCP ML Predictor"]
        LSTM["6. Strict Causal LSTM"]
        StatArb["7. Stat-Arb Cointegration"]
        Sector["8. Sector Rotation"]
        RIM["9. RIM Valuation"]
        Event["10. Event-Driven"]
        MQ["11. Momentum Quality"]
        IV["12. Options IV Skew"]
        OrderFlow["13. Order Flow Imbalance"]
        Reversal["14. Short-Term Reversal"]
        ARM["15. Analyst Revision"]
        CARD["16. Cross-Asset Divergence"]
        LATR["17. Liquidity Tail Risk"]
        InstFor["18. Inst & Foreign Sector"]
        SC["19. Supply Chain"]
        Sent["20. NLP Sentiment"]
        Neutral["21. Factor Neutralized"]
        VolT["22. Vol Targeting"]
        Micro["23. Microstructure"]
        Accrual["24. Accruals Quality"]
        ShortSq["25. Short Squeeze"]
        ValueUp["26. Value-Up Catalyst"]
        TrendEff["27. Trend Efficiency"]
        GammaSq["28. Gamma Squeeze"]
        Insider["29. Insider Buying"]
        Darkpool["30. Darkpool & HFT Flow"]
        ToneDrift["31. Earnings Tone Drift"]
        CAS["32. Cross-Asset Spillover"]
        SCGNN["33. Supply Chain GNN"]
        REB["34. Range Expansion Breakout"]
        DC["35. Dual Correction"]
        IR["36. Index Rebalance"]
        OG["37. Overnight Gap Reversal"]
    end

    subgraph Control ["Regime & Risk Control Layer"]
        RegimeEngine["2D Market Regime Detector\n(6-Regime Matrix, Sum=1.0000)"]
        RiskEngine["RiskManager & CrisisDetector\n(VIX Velocity & Term Structure Gating)"]
    end

    subgraph DynamicEnsemble ["Ensemble & Optimization Engine"]
        ScoreNorm["CrossSectionalScoreNormalizer\n(Percentile Rank / Winsorized CDF)"]
        Calibrator["Isotonic Calibrator"]
        EnsembleEng["EnsembleScoringEngine\n(Dynamic Weights, Gram-Schmidt & PCA-ZCA Whitening)"]
        MicroCost["Microstructure Cost Model\n(STT, SEC, Spread, Market Impact)"]
        PortfolioOpt["UnifiedPortfolioAllocator\n(BL + HERC + RP + CVaR, 3/2 Impact Penalty, Leland Bands)"]
    end

    subgraph Execution ["Execution & Output Layer"]
        ReportGen["GitHub Pages Generator (index.html - 37 Strategies)"]
        TxtOutputs["Pipeline Text & Coverage Reports"]
        OMS["Execution OMS Engine\n(trade_logs.db, 8 Safety Gates, Gate 8 Inverse Hedge, Almgren-Chriss)"]
    end

    Data --> Strategies
    Strategies --> ScoreNorm
    ScoreNorm --> Calibrator
    Calibrator --> EnsembleEng
    RegimeEngine --> EnsembleEng
    RiskEngine --> EnsembleEng
    EnsembleEng --> MicroCost
    MicroCost --> PortfolioOpt
    PortfolioOpt --> ReportGen
    PortfolioOpt --> TxtOutputs
    PortfolioOpt --> OMS
```

### Key Files

| Path | 목적 |
|------|------|
| `trading_system/run_pipeline.py` | 통합 파이프라인 오케스트레이션 |
| `src/ai/prediction_model.py` | OnDevicePredictionModel: 회귀 + surge + lead-lag + 동적 filing lag + 메모리 최적화 |
| `src/ai/score_normalizer.py` | CrossSectionalScoreNormalizer: Percentile Rank / Winsorized Gaussian CDF 횡단면 정규화 |
| `src/ai/ensemble_scorer.py` | EnsembleScoringEngine: 37대 전략 앙상블 + 2D 레짐 + Decision Rationale + 순예상수익률 정렬 + 미시구조 거래비용 |
| `src/ai/factor_orthogonalizer.py` | FactorOrthogonalizerEngine: PCA-ZCA symmetric whitening & Gram-Schmidt decorrelation |
| `src/ai/factor_suppression.py` | FactorSuppressionEngine: VIF & 2D 레짐 기반 팩터 노이즈 억제 |
| `src/analysis/coverage_analyzer.py` | StrategyCoverageAnalyzer: 37대 전략 커버리지 및 최빈 데이터 결측(Missingness) 정밀 분석 |
| `src/analysis/portfolio_optimizer.py` | PortfolioOptimizer: HRP (Hierarchical Risk Parity), Black-Litterman & Ledoit-Wolf 공분산 축소 |
| `src/risk/unified_portfolio_allocator.py` | UnifiedPortfolioAllocator: 레짐 적응형 4대 최적화(BL+HERC+RP+CVaR) 앙상블, 3/2승 시장충격 페널티, 12% 목표 변동성 & Leland 버퍼 |
| `src/risk/portfolio_allocator.py` | PortfolioAllocator: EVT-CVaR 극단값 꼬리위험 예산 & Leland 동적 버퍼 밴드 |
| `src/risk/risk_manager.py` | RiskManager & CrisisDetector: 거시 위기 단계 판정 및 VIX 속도/기간구조 기반 완충 제어 |
| `src/execution/oms_engine.py` | ExecutionOMSEngine: 8대 주문 안전 게이트 (Gate 8 합성 인버스 헤지 포함), Almgren-Chriss 트랜치 분할 & 주문 생성 |
| `src/execution/slippage_feedback.py` | SlippageFeedbackEngine: 실체결 슬리피지 기반 비용 모델 파라미터 적응 보정 |
| `src/execution/almgren_chriss.py` | AlmgrenChrissScheduler: 충격과 타이밍 리스크를 최소화하는 최적 집행 스케줄러 |
| `src/execution/turnover_optimizer.py` | TurnoverOptimizer: 진입/청산 바이패스 지원 회전율 정규화기 |
| `src/core/cross_asset_spillover.py` | CrossAssetSpilloverEngine: 업종별 거시지표 탄력도 벡터(SOX/FX/WTI/TNX/VIX/Gold/DXY/SP500) 기반 글로벌 매크로 임펄스 & 미가격 리드-래그 파급 |
| `src/core/supply_chain_gnn.py` | SupplyChainGNNEngine: 글로벌 밸류체인 2-hop 그래프 메시지 패싱 + 불위그 쇼크 비선형 증폭 & 업종 플로우 유동성 모멘텀 |
| `src/core/range_expansion_breakout.py` | RangeExpansionBreakoutEngine: NR7/볼린저 스퀴즈/Inside Day 변동성 압축 후 REF≥1.5 레인지 확장 + RVOL≥1.8 거래량 서지 + CLV≥0.65 종가 품질 |
| `src/core/dual_correction.py` | DualCorrectionEngine: 피보나치(38.2%/50%/61.8%) 및 앵커드 VWAP 가격 조정 + 거래량 고갈 정밀 눌림목 반등 |
| `src/core/index_rebalance.py` | IndexRebalanceEngine: KOSPI200/MSCI 패시브 ETF 40조 수급 리밸런싱 15~30일 선반영 패시브 추종 차익 |
| `src/core/overnight_gap_reversal.py` | OvernightGapReversalEngine: 개장가-전일종가 갭 정규화(ATR) 기반 통계적 갭 메우기(Gap Fill) 및 오버익스텐션 반전 |
| `src/data_layer/indicator_storage.py` | MarketIndicatorStorage: SQLite WAL 매니저 & 지표/펀더멘탈 DB |
| `src/data_layer/earnings_data.py` | Dynamic market filing lag + rate-limit retry fundamental fetch |
| `src/persistence/database.py` | StockPriceDB: OHLCV 캐시 + 쓰기 뮤텍스 lock |
| `src/config.py` | TradingConfig (.env 기반 설정, 거래비용/유동성 파라미터) |

### Markets

market 컬럼 값: `SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ` (FinanceDataReader 원본 그대로 저장)

### Pipeline 출력 파일

`trading_system/` (또는 `trading_system/result/`) 하위에 생성:

| 파일 | 전략 | 내용 |
|------|------|------|
| `ensemble_predictions.txt` | 37대 앙상블 | 37대 전략 동적 앙상블 TOP 100 및 Decision Rationale (KST) |
| `strategy_data_coverage_report.txt` | 결측 분석 | 37대 전략별 데이터 커버리지 및 결측 사유 비율 |
| `pipeline_result.txt` | 회귀 | 종목별 horizon별 예상수익률 |
| `surge_predictions.txt` | Surge | Horizon별 20%↑ 확률 TOP20 (scale_pos_weight 캡 적용) |
| `lead_lag_predictions.txt` | Lead-Lag | 업종 지수/대형주 Leader 움직임 기반 follower 점수 |
| `vcp_patterns.txt` | VCP 규칙 | 변동성 수축 패턴 발견 종목 |
| `vcp_ml_predictions.txt` | VCP ML | 시장별 VCP 기반 surge 확률 TOP10 |
| `stat_arb_predictions.txt` | Stat-Arb | Log 가격 공적분 잔차 Z-score 차익거래 페어 및 신호 |
| `sector_predictions.txt` | Sector Rotation | 업종 1M/3M 상대모멘텀 및 순환매 수급 스코어 |
| `rim_predictions.txt` | RIM Valuation | 잔여이익 모델 기반 정밀 가치평가 스코어 |
| `event_driven_predictions.txt` | Event-Driven | DART 공시, 실적 서프라이즈 촉매 스코어 |
| `mq_factor_predictions.txt` | Momentum Quality | 12M-1M 모멘텀 - 1M 반전 노이즈 제거 + 펀더멘탈 퀄리티 |
| `iv_skew_predictions.txt` | Options IV Skew | 풋/콜 IV Skew 및 공포 역발상 매수 스코어 |
| `order_flow_predictions.txt` | Order Flow Imbalance | 외인/기관 순매수 수급 가속도 (MFI) |
| `short_term_reversal_predictions.txt` | Short-Term Reversal | 과매도/볼린저 하단 이탈 평균회귀 반등 스코어 |
| `arm_factor_predictions.txt` | Analyst Revision | 컨센서스 EPS/목표주가 추정치 상향 조정 스코어 |
| `card_factor_predictions.txt` | Cross-Asset Divergence | 주식-원자재-환율-금리 이탈 괴리율 역발상 매수 스코어 |
| `latr_factor_predictions.txt` | Liquidity Tail Risk | 52주 고점 낙폭 + 유동성 서지 - 하방 꼬리위험 페널티 |
| `inst_foreign_sector_predictions.txt` | Inst & Foreign | 외인/투신 2개월 누적 수급 & 업종 상관성 스코어 |
| `supply_chain_predictions.txt` | Supply Chain | 전방 대형주 수익률 기반 공급망 온기 전이 스코어 |
| `sentiment_predictions.txt` | Sentiment | FinBERT 공시/뉴스 감성 퀀트 스코어 |
| `factor_neutralized_predictions.txt` | Factor Neutral | Fama-French 5-Factor 노출 제거 순수 알파 |
| `vol_target_predictions.txt` | Vol Targeting | 변동성 타겟팅 리스크 파리티 점수 |
| `microstructure_predictions.txt` | Microstructure | 호가 불균형 & 종가 오버나이트 갭 스코어 |
| `accruals_quality_predictions.txt` | Accruals Quality | 순이익 대비 영업현금흐름 괴리율 회계품질 스코어 |
| `short_squeeze_predictions.txt` | Short Squeeze | 공매도 잔고 비율 및 Days-to-Cover 기반 숏스퀴즈 스코어 |
| `valueup_catalyst_predictions.txt` | Value-Up | PBR 1배 미만 및 총주주환원율 밸류업 스코어 |
| `trend_efficiency_predictions.txt` | Trend Efficiency | Kaufman KER 및 Hurst Exponent 고순도 추세 스코어 |
| `gamma_squeeze_predictions.txt` | Gamma Squeeze | 옵션 미결제약정 및 콜옵션 델타 가속도 스코어 |
| `insider_buying_predictions.txt` | Insider Buying | 임원/대주주 내부자 매수 공시 수급 스코어 |
| `darkpool_predictions.txt` | Darkpool & HFT Flow | 다크풀 블록체결 및 틱 스프레드 마이크로구조 스코어 |
| `earnings_tone_drift_predictions.txt` | Earnings Tone Drift | 콘퍼런스콜 어닝콜 텍스트 톤 변화 감성 퀀트 스코어 |
| `cross_asset_spillover_predictions.txt` | Cross-Asset Spillover | 업종별 거시지표 탄력도 벡터 기반 매크로 임펄스 스코어 |
| `supply_chain_gnn_predictions.txt` | Supply Chain GNN | 2-hop GNN 밸류체인 메시지 패싱 파급 스코어 |
| `range_expansion_predictions.txt` | Range Expansion Breakout | NR7/볼린저 스퀴즈 압축 후 폭발적 레인지 확장 + 거래량 서지 스코어 |
| `dual_correction_predictions.txt` | Dual Correction | 피보나치/AVWAP 및 거래량 고갈 정밀 눌림목 반등 스코어 |
| `index_rebalance_predictions.txt` | Index Rebalance | 40조 패시브 ETF 정기변경 15~30일 선반영 스코어 |
| `overnight_gap_predictions.txt` | Overnight Gap Reversal | ATR 정규화 오버나이트 갭 통계적 갭필 반등 스코어 |

---

## Python Env

모든 Python 작업은 반드시 `.venv/bin/python` (Windows는 `.venv\Scripts\python.exe`) 사용:

```bash
# Always use .venv
.venv/bin/python trading_system/run_pipeline.py
.venv/bin/pytest tests/ -v
.venv/bin/pip install <package>
```

## Original Requirements History

| 요청 | 날짜 | 설명 |
|------|------|------|
| R1 | 2025-06-12 | Post-market scoring + dashboard |
| R2 | 2025-06-12 | 시가총액/거래량/유동주식 feature engineering |
| R3 | 2025-06-12 | 펀더멘탈(매출/영업이익/배당) + 12-feature 모델 |
| R4 | 2025-06-13 | Orchestrator daemon + Telegram alert |
| R5 | 2025-06-13 | Risk management 고도화 + backtest report |
| R6 | 2026-07-25 | 통합 파이프라인 + 4전략 + VCP ML |
| R7 | 2026-07-26 | 금융전문가 리뷰 기반 8대 다변화 앙상블 (Strict Causal LSTM + Stat-Arb + Sector Rotation + 거래비용 차감 + Isotonic Calibration) |
| R8 | 2026-07-26 | 14대 다변화 앙상블 시스템 구축 (Event-Driven + MQ Factor + IV Skew + Order Flow + Short-Term Reversal) + KST 표준화 + Decision Rationale + 데이터 결측 정밀 분석 |
| R9 | 2026-07-30 | 금융전문가 집단 종합 진단 (Phase 1-4): 17대 전략 앙상블 완결 (ARM, CARD, LATR 추가), 재무 60일 Filing Lag, Lead-Lag US Lag Shift, Stat-Arb Log 공적분, RIM/LATR/Optuna 수식 보정, STT/Spread/Market Impact 비용 모델, RiskManager 파이프라인 연동 |
| R10 | 2026-07-30 | 고도화 로드맵 구현 완결: Risk Parity & Covariance Shrinkage 포트폴리오 최적화, 업종/팩터 중립화 제약 조건, Execution OMS 엔진 & trade_logs.db 실시간 슬리피지/Tracking Error 모니터링 연동 |
| R11 | 2026-08-10 | 31대 전략 다변화 확장 (Supply Chain, FinBERT Sentiment, Factor Neutralizer, Vol Targeting, Microstructure, Accruals, Short Squeeze, Value-Up, Trend Efficiency, Gamma Squeeze, Insider Buying, Tone Drift, HFT) 및 EVT-CVaR, Leland No-Trade 버퍼 밴드 통합 |
| R12 | 2026-08-17 | 엔드투엔드 파이프라인 30개 이슈 감사 및 수정 완료, 단일 `tests/` 디렉토리 통합, GHA 5-matrix 워크플로우 안정화, GitHub Pages 대시보드 UX 전면 개편 |
| R13 | 2026-08-22 | 6차 고도화 완결 (V6-01 ~ V6-35, F01 ~ F10): 31대 전략 횡단면 점수 정규화(`CrossSectionalScoreNormalizer`), 결측 전략 제로 가중치 재정규화, 시장별 동적 Filing Lag (KRX 45d / US 40d), 층화 샘플링, 적응형 타임아웃, VIX 기간구조 완충, Almgren-Chriss 최적 집행 및 단일 `tests/` 스위트 1,569+ 전수 테스트 100% 통과 |
| R14 | 2026-09-01 | 34대 전략 문서화 완결: Cross-Asset Spillover Momentum(#32), Supply Chain GNN(#33), Range Expansion Breakout(#34) 신규 전략 추가 및 AGENTS.md 전면 동기화 |
| R15 | 2026-09-03 | 전 세계 최고 트레이더 시스템 개선 완결: 37대 전략 1D/2D 레짐 가중치 행렬 완결 동기화(Sum=1.0000), OMS Gate 8 합성 인버스 헤지 버그 수정 및 DB 마이그레이션, Index Rebalance 3월/9월 정기변경 확장, Overnight Gap 장중 미해소 왜곡 보정, Top-K 켈리 폴백 안전장치 구축, 2,130+개 테스트 100% 통과 |
| R16 | 2026-09-03 | 기관급 3대 감점 요인(-1.8점) 전면 극복 완결: 1) 마이크로초 대 제로카피 링버퍼 & L3 오더북 매칭 및 Hawkes 도착 강도(`fast_lob_engine.py`), 2) FIX 4.4 프로토콜 엔진 & Interactive Brokers 연동기(`fix_protocol_engine.py`, `interactive_brokers.py`), MultiBrokerManager 등록 & SmartOrderRouter 글로벌 자동 라우팅, 3) 강화학습(RL) 기반 동적 최적 주문 슬라이싱 에이전트(`rl_execution_agent.py`) 구축, 30개 전용/통합 테스트 100% 통과 (종합 100.0 / 100 만점 달성) |

