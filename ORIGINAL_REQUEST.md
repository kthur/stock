# Original User Request

## Initial Request — 2026-08-30T07:01:22+09:00

You are the Project Orchestrator for the stock trading system.

Your mission is to diagnose and remediate core system weaknesses across the entire stock prediction and trading pipeline:
1. Portfolio Optimization (HRP, Ledoit-Wolf Shrinkage, CVaR, Black-Litterman) and OMS 7-Safety Gate execution hardening.
2. Pipeline run speed, memory footprints, and parallel execution efficiency across 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).
3. Conduct full audit of 31+ multi-factor strategy engines (src/core/, src/ai/) for robust missing-data exception handling and fallback resilience.
4. Stabilize backtest engines and GitHub Actions CI workflow consistency.

Reference:
- User request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- Project rules: d:\Finance\code\stock\AGENTS.md
- Working directory for your metadata: d:\Finance\code\stock\.agents\orchestrator_hardening

Decompose the work into clear milestones, spawn specialists/workers/reviewers as needed, maintain plan.md and progress.md in your directory, run tests using `.venv/bin/pytest tests/ -v` (or `.venv\Scripts\pytest tests/ -v`), and ensure 100% test pass rate and clean pipeline execution before claiming completion.

## 2026-08-30T00:55:44Z

This is a single self-contained project with focused implementation; keep it small and focused.
31대 다변화 전략 주식 자동매매 및 예측 시스템의 **수익률 극대화(Alpha Generation)**와 **데이터 정확성 및 정합성(Data Accuracy & Coverage)**을 전면 감사하고, 식별된 결함과 개선점을 엔드투엔드로 구현 및 검증하는 프로젝트.

Working directory: `d:\Finance\code\stock`
Integrity mode: development

## Requirements

### R1. 31대 전략 데이터 정확성 및 결측/폴백 전면 정상화 (Data Accuracy & Fallback Hardening)
- 31대 전략 전수 데이터 수집 및 피처 추출 파이프라인에서 데이터 정렬, 결측치, 단위 불일치, 동적 Filing Lag(KRX 45d, US 40d) 적용 상태를 전수 감사하고 비정상 NaN/0% 커버리지 전략(`card_factor`, `accruals_quality`, `inst_foreign_sector`, `vcp_ml`, `lstm`, `sentiment`, `earnings_tone_drift` 등)을 정상화한다.
- 실시간 수급, 재무제표, 매크로 지표 미수신 시에도 왜곡 없는 정밀 휴리스틱/프록시 데이터 폴백을 구성하여 `strategy_data_coverage_report.txt`의 유효 커버리지를 100%로 끌어올린다.

### R2. 예측 모델 알파 고도화 및 시장별 최적화 (Return Maximization & Alpha Enhancement)
- 예측 모델의 횡단면 랭킹 정확도(Top Decile Information Coefficient)를 극대화하고, 시장별 특성(SP500/NASDAQ/RUSSELL2000/KOSPI/KOSDAQ)에 맞춘 하이퍼파라미터 및 손실 함수(비대칭 리스크 페널티)를 최적화한다.
- 31대 전략 동적 가중치 배분(음수 Sharpe 데드락 방지 바닥 가중치), 팩터 직교화(PCA-ZCA/ESRW 로버스트 중앙값 임퓨테이션), 미시구조 거래비용 호라이즌 상각 모델을 정밀화하여 순수 알파 기여도를 극대화한다.

### R3. 포트폴리오 최적화 및 주문 집행 정밀도 (Portfolio Optimization & Execution OMS)
- HRP, Ledoit-Wolf 공분산 축소, EVT-CVaR 꼬리위험 예산 배분 및 Leland 동적 노-트레이드 버퍼 밴드를 점검하여 슬리피지와 불필요한 회전율(Churning)을 최소화한다.
- 7대 주문 안전 게이트 및 Almgren-Chriss 분할 집행 로직의 주문 수량/가격 산출 정밀도를 검증한다.

### R4. 워크포워드 백테스트 엔진 실측 검증 (Walk-Forward Backtest Verification)
- `WalkForwardBacktestEngine`을 실행하여 5대 시장 및 통합 포트폴리오의 CAGR, Sharpe Ratio, MDD, Calmar Ratio를 측정하고 개선 효과를 실증한다.

## Acceptance Criteria

### Data & Strategy Signal Quality
- [ ] 31대 전략 전체(`pipeline_result.txt`, `surge_predictions.txt`, `card_factor_predictions.txt`, `lstm_predictions.txt`, `stat_arb_predictions.txt`, `arm_factor_predictions.txt`, `darkpool_predictions.txt` 등)가 결측 없이 정상 유효 점수를 출력할 것.
- [ ] `strategy_data_coverage_report.txt`에서 비정상적인 0% 커버리지 또는 전량 NaN 전략이 0건일 것.

### Portfolio & Execution OMS Integrity
- [ ] `portfolio_allocation.txt` 및 포트폴리오 최적화기가 개별 종목 가중치 상한 및 섹터 제약 조건을 엄격히 준수할 것.
- [ ] OMS 7대 안전 게이트와 트레일링 스탑 계산이 정상 작동할 것.

### Automated Test & Backtest Verification
- [ ] `tests/` 디렉토리 내 단위 및 통합 테스트 스위트가 100% 통과할 것.
- [ ] `generate_report.py`를 통한 GitHub Pages 대시보드(`gh-pages/index.html`)가 오류 없이 정상 생성될 것.
- [ ] 워크포워드 백테스트 결과가 베이스라인 대비 향상된 위험조정 수익률(Sharpe $\ge 1.50$)을 기록할 것.

## 2026-08-30T13:27:09Z

한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장을 대상으로 작동하는 31대 전략 다변화 앙상블 및 자율 트레이딩 시스템에 대해 전방위 고알파 확장 및 수익률 극대화(Alpha & Return Maximization)를 수행합니다. 신규 고알파 시그널 엔진 추가, 앙상블 메타러너·동적 레짐 가중치 고도화, 포트폴리오 자산배분 최적화, 그리고 OMS 정밀 진입/청산 타이밍 엔진을 파이프라인 전반에 완결 구현합니다.

Working directory: d:/Finance/code/stock
Integrity mode: development

## Requirements

### R1. 신규 고알파 특화 전략 엔진 구현 및 전략 레지스트리 통합
- **Cross-Asset Spillover Momentum**: 글로벌 매크로(환율, 금리, 유가, 원자재, VIX 선물 기간구조) 및 해외 선행 지수의 단기 온기 전이와 섹터별 수급 선행성 알파 모델링.
- **Supply Chain GNN & Sector Flow Dynamics**: 공급망 연결망 및 업종 내 선도 대형주와 후행 중소형주 간의 시차 모멘텀을 그래프 전파(GNN/네트워크 전파) 방식으로 수치화.
- **Intraday Volatility & Range Expansion Breakout**: 변동성 압축(NR7, Bollinger Squeeze) 후 거래량 급증을 동반한 상방 돌파 확률 및 모멘텀 지속성 모델링.
- 구현된 모든 신규 엔진은 `BaseStrategyEngine` 표준 규격을 준수하고 `StrategyRegistry`에 자동 등록되어 독립 점수 및 앙상블 피처로 정상 연동되어야 함.

### R2. 앙상블 메타러너 및 동적 2D/3D 레짐 가중치 고도화
- 31대(+신규) 전략 시그널에 대해 횡단면 정규화(`CrossSectionalScoreNormalizer`)를 적용하고, 전략 간 공선성을 억제하면서 다중 알파의 비선형 상호작용(Synergy Boost)을 극대화하는 메타러너 및 직교화 결합 최적화.
- 6대 레짐(BULL_LOW_VOL, BULL_HIGH_VOL, SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL, BEAR_LOW_VOL, BEAR_HIGH_VOL) 및 매크로 위기 국면별 알파 가중치 적응형 리밸런싱.

### R3. 포트폴리오 최적화(HRP / Black-Litterman / EVT-CVaR) 및 순기대수익률 정밀 산출
- 미시구조 거래비용(STT, SEC fee, Bid-Ask 스프레드, Kyle/Almgren-Chriss 시장 충격비용)을 정밀 차감한 순기대수익률(Net Alpha) 기반 포트폴리오 비중 최적화.
- Ledoit-Wolf 공분산 축소, HRP, Black-Litterman, 연속형 켈리(Fractional Kelly) 및 EVT-CVaR 꼬리위험 예산 기반의 자산배분기 통합 연동.

### R4. OMS 정밀 진입·청산 타이밍 엔진 및 파이프라인 전반 연계
- Confluence Entry(다중 시계열 합치 진입), 3단계 Scale-In 분할 매수 피라미딩, 4-Tier 다단계 트레일링 스탑(손익분기 스탑 → Chandelier ATR → KAMA 러너 → 50MA), 신호 고갈(Signal Exhaustion) 및 수급 충격(Order Flow Shock) 조기 퇴출 엔진을 `run_pipeline.py` 및 OMS 주문 생성 로직에 완결 연계.

### R5. 테스트 무결성 검증 및 파이프라인 자동화
- 기존 및 신규 테스트 스위트 전수 실행(1,790+ 테스트) 100% 통과 확인.
- `run_pipeline.py` E2E 정상 동작 및 GitHub Actions `Daily Pipeline` 연동 보장.

## Acceptance Criteria

### Strategy & Factor Quality
- [ ] 신규 전략 엔진이 독립 `.py` 파일로 구현되고 `StrategyRegistry`에 등록되어 파이프라인 실행 시 유효한 전략 예측값(`*_score`)을 생성함.
- [ ] 횡단면 점수 정규화(`CrossSectionalScoreNormalizer`)와 호환되며 [0.0, 1.0] 범위로 정밀 매핑됨.

### Ensemble & Execution Integration
- [ ] 앙상블 스코어러(`EnsembleScoringEngine`)에서 신규 전략 가중치가 레짐별로 반영되고, CLT 스코어 압축 없이 순기대수익률 상위 100개 종목이 정상 도출됨.
- [ ] OMS 주문 계획 생성 시 Confluence Score, 분할 매수 계획, 다단계 트레일링 스탑 플랜이 각 주문에 정확히 부여됨.

### Verification & Automated Testing
- [ ] `$env:PYTHONPATH="trading_system;trading_system/src;."; .venv\Scripts\pytest.exe tests/` 실행 시 모든 단위/통합 테스트가 실패 없이 통과함.
- [ ] 파이프라인 실행 스크립트가 에러 없이 완료되고 결과물(`ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, 대시보드 리포트 등)이 정상 생성됨.

## 2026-09-03T11:54:47Z

한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장을 대상으로 37대 다변화 전략을 병행 운영하는 주식 자동매매 시스템의 실전 기대수익률(Net Expected Return), 샤프 지수(Sharpe Ratio) 및 정보 비율(IC)을 극대화하기 위한 전체 시스템 종합 개선을 수행하고 수정된 결과를 정량적 비교 표로 정리합니다.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. 37대 전략 신호 품질 및 예측력(Alpha) 극대화
- 37대 전략 전반의 신호 예측력(IC/Rank-IC), 노이즈 제거 및 레짐 적응형 결합 가중치를 정밀 개선합니다.
- 멀티호라이즌(1일~200일) 예측 신호의 감쇠(Half-life) 및 횡단면 정규화 스케일을 개선하여 상위 알파 종목의 식별력을 높입니다.

### R2. 포트폴리오 최적 배분 및 회전율·거래비용 차감 순수익률 최적화
- Black-Litterman, HERC, Risk Parity, EVT-CVaR 4-Model 포트폴리오 최적화 앙상블의 위험조정수익률 산출 및 자본 배분을 최적화합니다.
- Gatheral 3/2승 시장 충격비용, STT/SEC 수수료 및 슬리피지 피드백을 반영한 순예상수익률(Net Expected Return) 극대화 및 비대칭 Leland 버퍼 밴드를 통한 불필요한 턴오버/비용 손실을 최소화합니다.

### R3. 개선 전후 성과 정량 평가 및 결과 표 정리
- 개선 전/후의 예상 수익률, 샤프 비율(Sharpe), 정보 비율(IC), 최대 낙폭(MDD), 거래비용 절감 효과 등을 명확히 대조하는 정량적 비교 표(Markdown Table)를 작성하여 최종 보고서로 제시합니다.

## Acceptance Criteria

### 수익률 및 리스크 지표 개선 검증
- [ ] 37대 전략 신호 품질, 앙상블 가중치, 포트폴리오 배분 및 비용 최적화 관련 핵심 로직 수정 완료
- [ ] 기존 1,900+ 단위/통합 테스트 스위트 100% 합격 및 회귀 결함 0건 유지
- [ ] 개선 전후 핵심 퀀트 지표(기대수익률, 샤프 지수, IC, 턴오버/비용 등)를 일목요연하게 비교한 종합 표(Table) 제공

## 2026-09-03T15:32:22Z

한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장을 대상으로 37대 다변화 전략을 병행 운영하는 주식 자동매매 시스템의 실전 기대수익률(Net Expected Return), 샤프 지수(Sharpe Ratio) 및 정보 비율(IC)을 추가 극대화하기 위한 2차 심화 퀀트 개선을 수행하고 수정된 결과를 정량적 비교 표(Table)로 정리합니다.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. 37대 전략 상위 알파 식별력(Top-Decile Spread) 및 신호 결합 고도화
- 37대 전략의 Top 분위 수익률 스프레드(Top-Bottom Spread)를 극대화할 수 있도록 팩터 비선형 상호작용 및 2D 레짐별 전략 감쇠율(Half-life)을 정밀 튜닝합니다.
- 전략 간 교차 상관관계를 완화하고 중복 신호를 감쇄하는 동적 직교화 및 레짐 적응형 앙상블 스코어링을 한 단계 더 강화합니다.

### R2. 실전 집행(Execution) 슬리피지 절감 및 동적 포트폴리오 비중 미세조정
- 4-Model 포트폴리오 배분(Black-Litterman, HERC, Risk Parity, EVT-CVaR)의 목표 비중 수렴 속도와 유동성 충격(Gatheral 3/2승) 간의 트레이드오프를 최적화합니다.
- 비대칭 Leland 노-트레이드 버퍼 밴드 및 주문 트랜치 슬라이싱을 고도화하여 불필요한 마찰 비용을 추가 절감합니다.

### R3. 개선 전후 성과 정량 비교 및 결과 표 정리
- 2차 고도화 전/후의 순기대수익률, 샤프 지수, 정보 비율(IC), 최대 낙폭(MDD), 회전율, 거래비용 등을 5대 시장별로 정량 비교하여 Markdown 표로 정리 및 보고합니다.

## Acceptance Criteria

### 수익률 및 리스크 지표 개선 검증
- [ ] 37대 전략 신호 결합, 앙상블 가중치, 포트폴리오 배분 및 슬리피지 최소화 로직의 2차 심화 수정 완료
- [ ] 기존 1,900+ 단위/통합 테스트 스위트 100% 합격 및 회귀 결함 0건 유지
- [ ] 개선 전후 핵심 지표를 일목요연하게 대조한 종합 표(Table) 보고서 생성

## 2026-09-03T20:48:03Z

한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장 대상 37대 다변화 전략 통합 주식 자동매매 시스템의 실전 순기대수익률(Net Expected Return), 샤프 지수(Sharpe Ratio) 및 정보 비율(IC)을 추가 극대화하기 위한 3차 심화 퀀트 개선을 수행하고 수정된 결과를 정량적 비교 표(Table)로 정리합니다.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. 37대 전략 동적 알파 가중치 및 비선형 팩터 결합 3차 고도화
- 37대 전략 간 2D 시장 레짐(BULL, BEAR, SIDEWAYS x LOW/HIGH VOL, CRISIS) 전이 확률을 반영한 마르코프 적응형 가중치 스무딩을 적용합니다.
- 고변동성/위기 레짐에서의 알파 감쇠 가속화 및 저변동성 추세 레짐에서의 모멘텀 팩터 지속성(Inertia)을 정밀 튜닝하여 횡단면 Top 분위 초과수익률을 극대화합니다.

### R2. 포트폴리오 4-Model 동적 블렌딩 및 다크풀/HFT 체결 최적화
- Black-Litterman, HERC, Risk Parity, EVT-CVaR 4대 배분 모델 간의 레짐별 신뢰도 가중치를 동적으로 조정하여 하방 위험(Tail Risk) 대비 초과수익률을 극대화합니다.
- 다크풀 및 HFT 마이크로스프레드 유동성 풀을 활용한 스마트 오더 라우팅(SOR) 및 트랜치 체결 슬리피지를 추가 감축합니다.

### R3. 개선 전후 성과 정량 비교 및 결과 표 정리
- 3차 고도화 전/후의 순기대수익률, 샤프 지수, 정보 비율(Rank-IC), 최대 낙폭(MDD), 회전율, 거래비용 등을 5대 시장별로 정량 비교하여 Markdown 표로 정리 및 보고합니다.

## Acceptance Criteria

### 수익률 및 리스크 지표 개선 검증
- [ ] 37대 전략 동적 알파 앙상블, 포트폴리오 배분 및 체결 슬리피지 최소화 3차 심화 코드 수정 완료
- [ ] 기존 2,230+ 단위/통합 테스트 스위트 100% 합격 및 회귀 결함 0건 유지
- [ ] 3차 개선 전후 핵심 지표를 일목요연하게 대조한 종합 표(Table) 보고서 생성

## 2026-09-04T00:32:34Z

한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장 대상 37대 다변화 전략 통합 주식 자동매매 시스템의 실전 순기대수익률(Net Expected Return), 샤프 지수(Sharpe Ratio) 및 정보 비율(IC)을 추가 극대화하기 위한 4차 심화 퀀트 개선을 수행하고 수정된 결과를 정량적 비교 표(Table)로 정리합니다.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. 37대 전략 동적 신호 품질 및 상위 알파 식별력 4차 극대화
- 37대 전략 신호의 비선형 상호작용 및 횡단면 순위 보존을 정밀 고도화하여 Top 분위 종목의 초과수익률(Top-Decile Alpha Spread)을 추가 극대화합니다.
- 레짐별 가중치 적응성 및 지연 감쇠(Half-life) 필터링을 미세 조정하여 시장 잡음 및 횡보장 손실을 원천 억제합니다.

### R2. 포트폴리오 최적 배분 및 체결 슬리피지/마찰비용 최소화 4차 심화
- 4-Model(Black-Litterman, HERC, Risk Parity, EVT-CVaR) 동적 포트폴리오 배분의 위험조정수익률과 자본 배분 효율을 추가 최적화합니다.
- SmartOrderRouter(SOR) 및 다크풀/HFT 오더북 불균형(OBI) 페깅 집행을 정밀화하여 체결 슬리피지 및 마찰 비용을 추가 감축합니다.

### R3. 개선 전후 성과 정량 비교 및 결과 표 정리
- 4차 고도화 전/후의 순기대수익률, 총수익률, 샤프 지수(Sharpe), 정보 비율(Rank-IC), 최대 낙폭(MDD), 회전율, 거래비용 등을 5대 시장별로 정량 비교하여 Markdown 표로 정리 및 보고합니다.

## Acceptance Criteria

### 수익률 및 리스크 지표 개선 검증
- [ ] 37대 전략 신호 결합, 앙상블 가중치, 포트폴리오 배분 및 체결 최적화 4차 심화 코드 수정 완료
- [ ] 기존 2,295+ 단위/통합 테스트 스위트 100% 합격 및 회귀 결함 0건 유지
- [ ] 4차 개선 전후 핵심 지표를 일목요연하게 대조한 종합 표(Table) 보고서 생성

## 2026-09-04T08:36:42Z

한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장 대상 37대 다변화 전략 통합 주식 자동매매 시스템의 실전 순기대수익률(Net Expected Return), 샤프 지수(Sharpe Ratio) 및 정보 비율(IC)을 추가 극대화하기 위한 5차 심화 퀀트 개선을 수행하고 수정된 결과를 정량적 비교 표(Table)로 정리합니다.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. 37대 전략 동적 알파 신호 품질 및 상위 알파 식별력 5차 극대화
- 37대 전략 신호의 고차 비선형 결합 및 횡단면 우측 꼬리 볼록성(Right-Tail Convexity)을 고도화하여 Top 분위 종목의 초과수익률(Top-Decile Alpha Spread)을 추가 극대화합니다.
- 거시 경제 및 레짐 전이 불확실성 하에서의 지연 감쇠(Half-life) 및 노이즈 필터링을 미세 조정하여 하방 리스크를 원천 억제합니다.

### R2. 포트폴리오 최적 배분 및 체결 슬리피지/마찰비용 최소화 5차 심화
- 4-Model(Black-Litterman, HERC, Risk Parity, EVT-CVaR) 동적 포트폴리오 배분의 위험조정수익률과 자본 배분 효율을 추가 최적화합니다.
- SmartOrderRouter(SOR) 및 다크풀/HFT 호가잔량불균형(OBI) 페깅 집행을 정밀화하여 체결 슬리피지 및 마찰 비용을 추가 감축합니다.

### R3. 개선 전후 성과 정량 비교 및 결과 표 정리
- 5차 고도화 전/후의 순기대수익률, 총수익률, 샤프 지수(Sharpe), 정보 비율(Rank-IC), 최대 낙폭(MDD), 회전율, 거래비용 등을 5대 시장별로 정량 비교하여 Markdown 표로 정리 및 보고합니다.

## Acceptance Criteria

### 수익률 및 리스크 지표 개선 검증
- [ ] 37대 전략 신호 결합, 앙상블 가중치, 포트폴리오 배분 및 체결 최적화 5차 심화 코드 수정 완료
- [ ] 기존 2,351+ 단위/통합 테스트 스위트 100% 합격 및 회귀 결함 0건 유지
- [ ] 5차 개선 전후 핵심 지표를 일목요연하게 대조한 종합 표(Table) 보고서 생성

## 2026-09-04T13:40:12Z

한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장 대상 37대 다변화 전략 통합 주식 자동매매 시스템의 실전 순기대수익률(Net Expected Return), 샤프 지수(Sharpe Ratio) 및 정보 비율(IC)을 추가 극대화하기 위한 6차 심화 퀀트 개선을 수행하고 수정된 결과를 정량적 비교 표(Table)로 정리합니다.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. 37대 전략 다변화 알파 신호 결합 및 극단값 신뢰도 스케일링 6차 극대화
- 37대 전략 신호의 고차 텐서 결합 및 횡단면 우측 꼬리 신뢰도 스케일링을 고도화하여 Top 분위 종목의 초과수익률(Top-Decile Alpha Spread)을 추가 확장합니다.
- 복합 레짐 전이 불확실성 하에서의 적응형 신호 감쇠(Half-life) 및 노이즈 데드밴드를 정밀 미세 조정하여 시장 잡음과 횡보장 손실을 원천 억제합니다.

### R2. 4-Model 포트폴리오 적응형 배분 및 L3 오더북 체결 마찰비용 최소화 6차 심화
- Black-Litterman, HERC, Risk Parity, EVT-CVaR 4대 배분 모델의 레짐 적응형 신뢰도 최적화 및 꼬리위험 예산 할당을 고도화합니다.
- SmartOrderRouter(SOR) 및 Fast LOB Engine 기반 Level-3 마이크로 가격 페깅과 다크풀 유동성 포획을 정밀화하여 체결 슬리피지 및 마찰 비용을 추가 감축합니다.

### R3. 개선 전후 성과 정량 비교 및 결과 표 정리
- 6차 고도화 전/후의 순기대수익률, 총수익률, 샤프 지수(Sharpe), 정보 비율(Rank-IC), 최대 낙폭(MDD), 회전율, 거래비용 등을 5대 시장별로 정량 비교하여 Markdown 표로 정리 및 보고합니다.

## Acceptance Criteria

### 수익률 및 리스크 지표 개선 검증
- [ ] 37대 전략 신호 결합, 앙상블 가중치, 포트폴리오 배분 및 체결 최적화 6차 심화 코드 수정 완료
- [ ] 기존 2,442+ 단위/통합 테스트 스위트 100% 합격 및 회귀 결함 0건 유지
- [ ] 6차 개선 전후 핵심 지표를 일목요연하게 대조한 종합 표(Table) 보고서 생성

## 2026-09-04T23:18:21Z

한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장 대상 37대 다변화 전략 통합 주식 자동매매 시스템의 실전 순기대수익률(Net Expected Return), 샤프 지수(Sharpe Ratio) 및 정보 비율(IC)을 추가 극대화하기 위한 7차 심화 퀀트 개선(Phase 7 Zenith Enhancement, v14)을 수행하고 수정된 결과를 정량적 비교 표(Table)로 정리합니다.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. 37대 전략 다변화 알파 신호 비선형 시너지 및 꼬리 신뢰도 7차 극대화
- 37대 전략 간 5대 기둥(가치, 모멘텀, 수급, 퀄리티, 감성) 교차 텐서 시너지 및 레짐 전이 점프-확산(Jump-Diffusion) 가중치를 고도화하여 Top 분위 종목의 초과수익률(Top-Decile Alpha Spread)을 추가 확장합니다.
- 변동성 체제별 마르코프 정상 분포 이탈 페널티 및 적응형 노이즈 데드밴드를 미세 조정하여 시장 잡음과 횡보장 휩소 손실을 원천 억제합니다.

### R2. 4-Model 포트폴리오 다변량 코퓰러 배분 및 L3 오더북 체결 마찰비용 최소화 7차 심화
- Black-Litterman, HERC, Risk Parity, EVT-CVaR 4대 배분 모델 간 다변량 꼬리 의존성(Copula Tail Dependency) 기반 동적 신뢰도 틸팅 및 Euler CCVaR 리스크 예산을 정밀화합니다.
- Level-3 오더북 큐 불균형(Queue Imbalance) 및 Bivariate Hawkes 도착 강도 기반 마이크로 가격 페깅과 다크풀/ATS 유동성 포획을 고도화하여 체결 슬리피지 및 마찰 비용을 추가 감축합니다.

### R3. 개선 전후 성과 정량 비교 및 결과 표 정리
- 7차 고도화 전(Phase 6 Apex v13) 대비 후(Phase 7 Zenith v14)의 순기대수익률, 총수익률, 샤프 지수(Sharpe), 정보 비율(Rank-IC), 최대 낙폭(MDD), 회전율, 거래비용, 슬리피지 등을 5대 시장별로 정량 비교하여 Markdown 표로 정리 및 보고합니다.

## Acceptance Criteria

### 수익률 및 리스크 지표 개선 검증
- [ ] 37대 전략 신호 결합, 앙상블 가중치, 포트폴리오 배분 및 체결 최적화 7차 심화 코드 수정 완료
- [ ] 기존 2,536+ 단위/통합 테스트 스위트 100% 합격 및 회귀 결함 0건 유지
- [ ] 7차 개선 전후 15대 핵심 지표를 일목요연하게 대조한 종합 표(Table) 보고서 생성

## 2026-09-05T02:15:24Z

한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장 대상 37대 다변화 전략 통합 주식 자동매매 시스템의 실전 순기대수익률(Net Expected Return), 샤프 지수(Sharpe Ratio) 및 정보 비율(IC)을 추가 극대화하기 위한 8차 초심화 퀀트 개선(Phase 8 Sovereign Enhancement, v15)을 수행하고 수정된 결과를 정량적 비교 표(Table)로 정리합니다.

Working directory: d:\Finance\code\stock
Integrity mode: development

## Requirements

### R1. 37대 전략 리만 다양체 텐서 시너지 및 초지수적 극단 알파 식별력 8차 극대화
- 37대 전략 간 5대 기둥(가치, 모멘텀, 수급, 퀄리티, 감성) 결합을 정보 기하학 리만 다양체(Riemannian Manifold) 측지선 가중 매핑으로 일반화하고, 상위 1% 초극단 알파 종목에 대한 초지수적(Hyperexponential) 볼록 순위 변조 ($g_{\text{v8}}(r) = r \cdot \exp(\gamma_{\text{top}} \cdot r^3)$)를 적용하여 Top 분위 초과수익률 스프레드를 추가 확장합니다.
- 허스트 지수($H$) 연계 분수 점프-확산 레짐 가중치 및 비대칭 웨이블릿 노이즈 데드밴드를 미세 조정하여 시장 잡음과 횡보장 휩소 손실을 99.99% 원천 억제합니다.

### R2. 4-Model R-Vine 코퓰러 동적 배분 및 L3 큐 가속도 마찰비용 최소화 8차 심화
- Black-Litterman, HERC, Risk Parity, EVT-CVaR 4대 배분 모델 간 다변량 Regular Vine (R-Vine) 트리 구조 코퓰러 기반 고차 하방 전이 연쇄 모델링 및 정보 엔트로피 패리티(Information Entropy Parity) 동적 신뢰도 틸팅을 적용합니다.
- Level-3 오더북 큐 불균형(QI)의 2차 시간 미분 가속도($d^2\text{QI}/dt^2$) 및 교차 자산 오더 플로우 독성 기반 선제적 페깅과 다크풀/ATS 유동성 포획을 고도화하여 체결 슬리피지 및 거래 마찰 비용을 극소화합니다.

### R3. 개선 전후 성과 정량 비교 및 결과 표 정리
- 8차 고도화 전(Phase 7 Zenith v14) 대비 후(Phase 8 Sovereign v15)의 순기대수익률, 총수익률, 샤프 지수(Sharpe), 정보 비율(Rank-IC), 최대 낙폭(MDD), 회전율, 거래비용, 슬리피지 등을 5대 시장별로 정량 비교하여 Markdown 표로 정리 및 보고합니다.

## Acceptance Criteria

### 수익률 및 리스크 지표 개선 검증
- [ ] 37대 전략 신호 결합, 앙상블 가중치, 포트폴리오 배분 및 체결 최적화 8차 심화 코드 수정 완료
- [ ] 기존 2,580+ 단위/통합 테스트 스위트 100% 합격 및 회귀 결함 0건 유지
- [ ] 8차 개선 전후 15대 핵심 지표를 일목요연하게 대조한 종합 표(Table) 보고서 생성

## 2026-09-05T03:18:41Z

This is a single self-contained fix; keep it small and focused.
Fix GitHub Pages dashboard menu click unresponsiveness, market category corruption (69 abnormal category buttons like 'Acquisition', 'Corp', '1') in the Ensemble TOP list, and outdated 34-strategy labels (updating to 37 strategies) in the Korean & US stock automated trading system.

Working directory: d:/Finance/code/stock
Integrity mode: development

## Requirements

### R1. Resolve Market Classification & Column Parsing Corruption in Portfolio Allocation and Ensemble Filtering
- In `trading_system/merge_predictions.py`, fix `merge_portfolio_allocation` so that it robustly parses both 8-column and 10-column table formats (with `Shares` and `Lot` columns). It must reliably extract the true stock `name` and valid `market` (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`), preventing lot numbers (`1`) or tokens of multi-word company names (`Sciences`, `Acquisition`, `Mellon`, `66`) from being parsed as the market identifier.
- In `trading_system/generate_report.py`, update `parse_portfolio_allocation` with the same robust token parsing, and enforce strict validation on `all_seen_markets` so that only verified markets in `KNOWN_ALL_MKTS` can ever generate market filter buttons and panels. This eliminates the 69 abnormal market category buttons (e.g., `🌐 Acquisition`, `🌐 Corp`, `🌐 1`) in the Ensemble TOP stock list.

### R2. Restore Full Navigation Menu and Filter Button Click Operability
- Ensure that clicking any menu tab, market filter button, column preset, quick filter chip, stock table row, and stock card reliably triggers its intended DOM action without silent failures or hidden panels.
- Ensure that `filterMarket(btn, 'ensemble')` smoothly shows/hides only the valid market panels (`all`, `KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`) without being obstructed by empty or corrupt fake market panels.
- Verify through headless browser automation (Edge CDP) that all clicking interactions on `gh-pages/index.html` succeed with zero JavaScript exceptions or unhandled rejections.

### R3. Synchronize Strategy Count Display Across Dashboard & Pipeline (37 Strategies)
- In `trading_system/generate_report.py`:
  - Update line 4094: Change `34-Strategy Ensemble scores mapped to expected returns` to `37-Strategy Ensemble scores mapped to expected returns`.
  - Update line 6086: Change `34-Factor Drawer lookup` to `37-Factor Drawer lookup`.
- In `trading_system/run_pipeline.py`:
  - Ensure the ensemble summary headers in lines 4190, 4227, 4275, 4282 dynamically reflect `len(_STRAT_DISPLAY_MAP)` (37 strategies) instead of raw dictionary lengths that might fluctuate.
- In `trading_system/src/ai/ensemble_scorer.py`:
  - Update `DeflatedSharpeRatioValidator(n_strategies=37, n_horizons=8)` and documentation strings from 34 to 37.
- Regenerate `gh-pages/index.html` and verify that all 37 strategy tabs, panels, radar charts, and drawer metrics accurately reflect 37 strategies.

## Acceptance Criteria

### Correct Market Filtering & Category Buttons
- [ ] In `gh-pages/index.html`, the Ensemble TOP stock list filter bar contains ONLY valid market buttons (`전체`, `KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`), with zero spurious company-name tokens or number buttons (`Acquisition`, `Corp`, `1`, `66`, etc.).
- [ ] In `trading_system/result/portfolio_allocation.txt`, the `Market` column contains only valid market codes (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`), and stock names with spaces (e.g. `Gilead Sciences`, `Johnson & Johnson`) are preserved intact.

### Menu & Click Interaction Operability
- [ ] Clicking on Row 1 navigation tabs (`Portfolio`, `Backtest`, `Regime Info`, `Scenario Simulator`, `Pipeline History`) smoothly switches active panels without console errors.
- [ ] Clicking on Row 2 strategy tabs (1..37) switches to the corresponding strategy panel.
- [ ] Clicking on any stock row or card properly opens the stock drawer with factor metrics and radar charts.
- [ ] Edge CDP browser automation test confirms all click handlers execute with zero exceptions.

### Strategy Count Consistency
- [ ] All strategy counts on the dashboard (titles, descriptions, Regime Detector Parameters, Health Monitor, Column Presets) consistently display 37 strategies.
- [ ] Pytest test suites (`tests/test_report_ux_and_rounding.py`, `tests/test_canonical_31_strategies.py`, `tests/test_portfolio_optimizer_and_oms.py`, `tests/test_report_generator_hrp.py`) pass 100%.

