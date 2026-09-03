# 📈 주식 자동매매 및 예측 시스템 — 실행 가이드

본 가이드는 통합 37대 다변화 예측 파이프라인(`run_pipeline.py`), 자율 매매 시스템, 대시보드 리포트 생성기(`generate_report.py`)의 설치, 설정, 실행, 트러블슈팅을 안내합니다.

---

## 📚 상세 설계 및 참조 문서

| 문서 | 설명 |
|------|------|
| [ALGORITHMS_AND_STRATEGY.md](docs/ALGORITHMS_AND_STRATEGY.md) | **37대 다변화 전략 완전 알고리즘 명세** (GBDT 회귀, Surge, Lead-Lag, VCP, Strict Causal LSTM, Stat-Arb, Sector, RIM, Event, MQ, IV Skew, Order Flow, Reversal, ARM, CARD, LATR, Inst & Foreign, Supply Chain, Sentiment, Style Neutralizer, Vol Target, Microstructure, Accruals, Short Squeeze, Value-Up, Trend Efficiency, Gamma Squeeze, Insider Buying, Tone Drift, Darkpool HFT, Cross-Asset Spillover, SC GNN, Range Expansion, Dual Correction, Index Rebalance, Overnight Gap, 횡단면 정규화) |
| [SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | 시스템 아키텍처, 2D 시장 레짐, 통계적 직교화, `UnifiedPortfolioAllocator`(BL/HERC/RP/CVaR 4-Model), 미시구조 거래비용, DB 스키마 |
| [CONFIGURATION_REFERENCE.md](docs/CONFIGURATION_REFERENCE.md) | `.env` 환경 변수 및 설정 파라미터 완전 참조 |
| [KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) | V8 시스템 정밀 감사(43개 결함 해결) 및 고도화 내역 |
| [IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md) | 시스템 아키텍처 및 성능 최적화 개선 계획 |
| [OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md) | 실거래 운영 절차, 8대 주문 안전 게이트 (Gate 8 합성 인버스 헤지 포함), Almgren-Chriss 트랜치, 킬 스위치(Kill Switch) 및 장애 대응 런북 |
| [TEST_GUIDE.md](docs/TEST_GUIDE.md) | 통합 테스트 스위트(`tests/`) 및 2,182+ pytest 실행 가이드 |

---

## 🚀 빠른 시작 (Quick Start)

### 1. 가상환경 활성화 및 의존성 설치

```powershell
# 가상환경 생성 (최초 1회)
python -m venv .venv

# 가상환경 활성화
.venv\Scripts\activate

# 의존성 라이브러리 설치
pip install -r trading_system/requirements.txt
```

### 2. 환경 설정 파일(`.env`) 생성

```powershell
copy trading_system\.env.example trading_system\.env
```

---

## 💻 실행 방법

### 1. 통합 예측 파이프라인 (핵심)

37대 전략 모델을 기반으로 한국(KOSPI, KOSDAQ) 및 미국(S&P 500, NASDAQ, RUSSELL 2000) 5대 시장의 예측 결과를 생성하고 2D 시장 레짐 기반 동적 앙상블, 횡단면 점수 정규화(`CrossSectionalScoreNormalizer`), 30일 롤링 RankIC 동적 가중치, 포트폴리오 최적화(`UnifiedPortfolioAllocator`), 미시구조 거래비용 차감을 수행합니다.

#### CLI 옵션

```powershell
# 기본 실행 (전 시장, 모델 학습 포함)
.venv\Scripts\python trading_system/run_pipeline.py

# 도움말
.venv\Scripts\python trading_system/run_pipeline.py --help
```

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--target {KOSPI,KOSDAQ,NASDAQ,RUSSELL2000,KRX,SP500}` | 특정 시장만 추론 (학습은 전 유니버스 유지) | `--target KOSPI` |
| `--skip-training` | 기존 저장 모델 재사용 (학습 건너뛰기 — 빠른 재추론) | `--skip-training` |
| `--debug` | 시장별 3종목 샘플링 — 동작 빠른 검증 | `--debug` |

```powershell
# 예시 조합
.venv\Scripts\python trading_system/run_pipeline.py --target SP500 --skip-training
.venv\Scripts\python trading_system/run_pipeline.py --target KOSDAQ --debug
.venv\Scripts\python trading_system/run_pipeline.py --target KRX --skip-training
```

> **`--target KRX`** = KOSPI + KOSDAQ (증권거래세 0.15% 일원화 세제 적용)

### 2. 기관급 초저지연 실행 및 브로커 엔진

- **Fast LOB Engine (`src/core/fast_lob_engine.py`)**: 제로카피 고정 크기 링버퍼 기반 마이크로초 단위 Level 3 호가 매칭 및 Hawkes 오더 도착 강도 모델 구동.
- **기관 DMA FIX 4.4 Engine (`src/broker/fix_protocol_engine.py`)**: 초고속 DMA 주문 전송 및 하트비트 세션 제어.
- **Interactive Brokers Connector (`src/broker/interactive_brokers.py`)**: IBKR TWS/Gateway 소켓 연동을 통한 글로벌 멀티 마켓 자율 매매.
- **Smart Order Router (`src/execution/smart_order_router.py`)**: `.KS`, `.KQ` 접미사 자동 파싱 및 KRX/US/Global 브로커 자동 분기 및 2차 베뉴 자동 페일오버.
- **강화학습 주문 슬라이싱 에이전트 (`src/execution/rl_execution_agent.py`)**: Q-learning 기반 동적 최적 트랜치 분할 및 슬리피지 최소화.

### 3. 파이프라인 출력 파일 (`result/` 또는 `trading_system/`)

| 파일 | 설명 |
|------|------|
| `ensemble_predictions.txt` | **37대 전략 동적 앙상블 TOP 100** 및 Decision Rationale (KST) |
| `strategy_data_coverage_report.txt` | **37대 전략별 데이터 커버리지 & 최빈 결측 사유 비율 분석 보고서** |
| `pipeline_result.txt` | GBDT 회귀 모델 horizon별 예상수익률 TOP10 요약 |
| `pipeline_result.csv` | 전체 종목 회귀 예측값 원본 (기계 가독) |
| `surge_predictions.txt` | Surge 분류기 horizon별 20%↑ 급등 확률 TOP20 |
| `lead_lag_predictions.txt` | Leader-Follower 시차 상관 점수 (+1d US Lag Shift) |
| `vcp_patterns.txt` | Mark Minervini VCP 패턴 감지 종목 |
| `vcp_ml_predictions.txt` | 시장별 VCP ML surge 확률 TOP10 |
| `stat_arb_predictions.txt` | Log 가격 공적분 잔차 Z-score 차익거래 페어 |
| `sector_predictions.txt` | 업종 상대 모멘텀 & 순환매 점수 |
| `rim_predictions.txt` | 잔여이익 모델(RIM) 적정주가 및 안전마진 |
| `event_driven_predictions.txt` | DART 공시/실적 서프라이즈/자사주 촉매 스코어 |
| `mq_factor_predictions.txt` | 모멘텀 퀄리티(MQ) 팩터 점수 |
| `iv_skew_predictions.txt` | 옵션 풋/콜 IV 스큐 역발상 점수 |
| `order_flow_predictions.txt` | MFI 외인/기관 순매수 수급 가속도 |
| `short_term_reversal_predictions.txt` | 3~5일 연속 과매도 평균회귀 반등 신호 |
| `arm_factor_predictions.txt` | 애널리스트 추정치 수정 모멘텀 |
| `card_factor_predictions.txt` | 크로스에셋 괴리율 스코어 |
| `latr_factor_predictions.txt` | 유동성 조정 꼬리위험(LATR) 점수 |
| `inst_foreign_sector_predictions.txt` | 외인/투신 60일 누적 수급 & 업종 주도주 상관성 |
| `supply_chain_predictions.txt` | 전방 대형주 공급망 시차 온기 전이 점수 |
| `sentiment_predictions.txt` | FinBERT 공시/뉴스 텍스트 감성 촉매 스코어 |
| `factor_neutralized_predictions.txt` | Fama-French 5-Factor 노출 제거 순수 알파 |
| `vol_target_predictions.txt` | 변동성 타겟팅 리스크 파리티 점수 |
| `microstructure_predictions.txt` | 호가 불균형 & 종가 오버나이트 수급 |
| `accruals_quality_predictions.txt` | 순이익 대비 OCF 괴리율 회계품질 스코어 |
| `short_squeeze_predictions.txt` | 공매도 잔고 및 Days-to-Cover 숏스퀴즈 스코어 |
| `valueup_catalyst_predictions.txt` | 저PBR 및 총주주환원율 밸류업 스코어 |
| `trend_efficiency_predictions.txt` | Kaufman KER 및 Hurst Exponent 고순도 추세 스코어 |
| `gamma_squeeze_predictions.txt` | 옵션 OI 및 델타 가속도 감마 스퀴즈 스코어 |
| `insider_buying_predictions.txt` | 임원/대주주 내부자 매수 수급 스코어 |
| `darkpool_predictions.txt` | 다크풀 블록체결 및 틱 스프레드 마이크로스프레드 스코어 |
| `earnings_tone_drift_predictions.txt` | 어닝콜 텍스트 톤 변화 감성 퀀트 스코어 |
| `cross_asset_spillover_predictions.txt` | 글로벌 8대 매크로 임펄스 미가격 시차 파급 스코어 |
| `supply_chain_gnn_predictions.txt` | 2-Hop 가치사슬 그래프 메시지 패싱 & 채찍효과 스코어 |
| `range_expansion_predictions.txt` | NR7/볼린저 스퀴즈 압축 후 레인지 확장 돌파 스코어 |
| `dual_correction_predictions.txt` | 피보나치/AVWAP 및 거래량 고갈 정밀 눌림목 반등 스코어 |
| `index_rebalance_predictions.txt` | 40조 패시브 ETF 정기변경 15~30일 선반영 스코어 |
| `overnight_gap_predictions.txt` | ATR 정규화 오버나이트 갭 통계적 갭필 반등 스코어 |

### 4. GitHub Pages 대시보드 리포트 생성

```powershell
# HTML 대시보드 리포트 생성
.venv\Scripts\python trading_system/generate_report.py --out gh-pages/index.html

# 브라우저에서 https://kthur.github.io/stock/ 또는 로컬 gh-pages/index.html 열기
```

#### 대시보드 혁신 기능: 3대 통합 메가 카드
- **🎛️ Card 1 (Market Regime & Risk Gates Console)**: 2D 6대 레짐, CrisisDetector 4단계, VIX 속도 및 기간구조, 거시 지표 스트립 통합.
- **🏥 Card 2 (Strategy Coverage & Missingness Center)**: 37대 전략 실시간 헬스 모니터링, 동적 상태 필터, 결측 사유 비율 분석.
- **💼 Card 3 (Portfolio Optimization & Execution OMS)**: 4대 최적화 블렌딩 도넛 차트, 시장별 노출도, EVT-CVaR 꼬리위험, Leland 버퍼 밴드 및 실시간 슬리피지 피드백.
- **🕸️ 37-Alpha Radar Chart & Column Presets**: 37개 알파 다차원 레이더 차트, 핵심/전체/기술적 지표 컬럼 프리셋 지원.
- **⭐ 관심종목(Watchlist) & Stock Drawer**: 클라이언트 로컬 스토리지 관심종목 동기화 및 종목별 상세 팩터 분해 탭.
- **⚡ 시나리오 시뮬레이터 (Regime & Shock Simulator)**: VIX 급등, 환율 변동, 금리 충격 시뮬레이션 및 포트폴리오 가중치 반응 즉시 확인.
- **🎯 Decision Rationale & Macro Strip**: 6대 시장 레짐 및 실시간 거시지표 정상 범위 검증 배지.
- **📱 모바일 완전 반응형**: 터치 스크롤, 사이드바 드로어, 콤팩트 테이블 뷰.

### 5. 텔레그램 알림

`.env`에 아래 값을 설정하면 파이프라인 완료 시 KST 타임스탬프와 함께 Telegram 메시지가 전송됩니다:

```ini
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

---

## 📁 데이터베이스 파일

| 파일 | 설명 |
|------|------|
| `stock_prices.db` | 3,379 종목 일봉 OHLCV 캐시 (SQLite WAL & Write Mutex) |
| `market_indicators.db` | 글로벌 거시 지표, 종목 유니버스, 재무제표 메타데이터 |
| `trade_logs.db` | 자율 매매 거래 로그, 체결 슬리피지, Tracking Error 기록 |
| `asset_history.db` | 포트폴리오 자산 평가 히스토리 |

---

## 🛠️ 트러블슈팅

### Q1. "database is locked" 에러
- **원인**: 여러 프로세스에서 동시에 쓰기 시도.
- **해결**: 시스템에 내장된 SQLite WAL 모드와 `threading.Lock()` 쓰기 뮤텍스가 단일 프로세스 내 동시성을 보호합니다. 다른 백그라운드 파이프라인이 구동 중인지 확인하세요.

### Q2. "ModuleNotFoundError: No module named 'src'"
- **원인**: Python 실행 경로 문제.
- **해결**: 루트 디렉토리에서 `.venv\Scripts\python -m pytest tests/` 형태로 실행하거나 `PYTHONPATH`에 `trading_system`을 추가하세요.

### Q3. 파이프라인 실행 시간 단축 방법
- `--skip-training`: 기존 훈련된 모델 재사용.
- `STOCK_PRICE_FRESHNESS_DAYS=none`: 로컬 DB 캐시만 사용하여 네트워크 I/O 건너뛰기.
- `--debug`: 시장별 3개 종목만 샘플링하여 30초 내 동작 검증.