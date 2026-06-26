# 🚀 시스템 아키텍처 및 성능 개선 계획 (IMPROVEMENT PLAN)

> **작성일**: 2026-06-21 (업데이트 완료: 2026-06-21)

본 문서는 최근 수행된 코드베이스 정밀 검토 및 핵심 버그 픽스 완료(Critical & Significant 대부분 해결) 이후, 시스템의 구조적 한계를 극복하고 프로덕션 레벨의 안정성을 확보하기 위해 수행된 개선 내역 및 향후 중장기 개선 계획입니다.

---

## 1. 데이터 파이프라인 및 병목 해소

### 1.1 펀더멘탈 데이터 수집 및 캐싱 (이슈 I9) - **완료 [2026-06-21]**
- **기존 상황**: 매 파이프라인 실행 시마다 야후 파이낸스(`yfinance`)를 통해 3,000여 개 종목의 펀더멘탈 데이터를 재수집하여 네트워크 병목 및 Rate Limit 문제 발생.
- **개선 완료**:
  - `earnings_data.py` 내의 `fetch_and_store_fundamentals_batch` 함수를 고도화하여 데이터 수집 시도 결과(성공 및 데이터 없음/실패 등 모든 경우)를 `fundamental_cache_meta` 테이블에 `last_fetched` 타임스탬프 메타데이터로 기록 및 캐싱.
  - 캐시 유효 기간(`fundamental_cache_expiry_days`)을 90일(분기 단위)로 설정하여, 이미 시도했거나 유효 기간 내에 있는 종목은 수집을 완전히 건너뛰도록 하여 yfinance API 호출 수 대폭 감축.
  - `GlobalRateLimiter`에 thread-safe 및 비동기 루프를 차단하지 않는 `async_wait` (내부적으로 `asyncio.sleep` 활용) 로직을 전면 구현하여, 단일 스레드 비동기 루프 내에서 Rate limit을 처리할 때 CPU/I/O 차단을 방지.

### 1.2 "펀더멘탈 데이터 누락(0.0) 편향" 해결 (이슈 S4) - **완료 [2026-06-21]**
- **기존 상황**: 재무 데이터가 없는 종목은 0.0으로 일괄 채워짐(`fillna(0.0)`). 이는 실제 0(예: 배당수익률 0%)과 데이터 누락을 모델이 구분하지 못하게 함.
- **개선 완료**:
  - `has_fundamental` (0 또는 1) 바이너리 피처를 추가하여 모델에 맥락 제공.
  - 최신 피처 정의가 반영되지 않은 레거시 pre-trained 모델이 로딩되어 크래시를 유발하지 않도록 `vcp_ml_predictor.py` 및 `prediction_model.py` 내에 다이나믹 모델 validation 로직 추가.
  - XGBoost 및 LightGBM이 기본적으로 지원하는 `NaN` 최적화 분기(Sparsity-aware Split Finding)를 적극 활용하도록, `FallbackMetadataDict`의 mock 생성 데이터 및 `prediction_model.py` 내의 파이프라인 피처 생성부에서 결측치를 `0.0` 대신 `np.nan`으로 변환/전환 처리 완료. 관련 스트레스/에드버서리얼 테스트 케이스도 NaN 전파 규칙에 맞춰 업데이트 완료.

### 1.3 데이터베이스 동시성 문제 (이슈 I5, S6 후속) - **중장기 계획**
- **현재 상황**: SQLite의 WAL 모드와 Python `threading.Lock`을 통해 `database is locked` 에러를 일차적으로 방어함. 유닛 테스트를 통해 동시성 쓰기/읽기 예외 처리와 잠금 획득 대기가 안정적으로 동작함을 확인.
- **향후 계획**:
  - 향후 트래픽 증가 및 다중 에이전트 환경 확장을 고려하여 PostgreSQL로의 마이그레이션 추진.
  - SQLAlchemy 또는 asyncpg를 도입하여 커넥션 풀링(Connection Pooling) 구성.

---

## 2. 테스트 커버리지 및 안정성 확보

### 2.1 통합 테스트 스위트 보강 (이슈 I1, I2, I4) - **완료 [2026-06-21]**
- **개선 완료**:
  - `config.py`의 잘못된 설정(음수 자산, 음수 재시도 횟수 등)을 검증하고 예외를 던지는 유닛 테스트를 `test_config.py`에 작성 및 추가 완료.
  - `backtest.py`의 Trailing Stop Loss, Take Profit, Scale-in(추가 매수), Volatility sizing, Short position(공매도) 시뮬레이션 로직을 정밀 검증하는 테스트 케이스를 `test_backtest.py`에 추가 완료.
  - SQLite 병렬 다중 쓰기/읽기 상황에서의 동시성 동기화를 검증하는 `TestStockPriceDBConcurrency` 스트레스 테스트 벤치마크를 `test_database.py`에 작성 및 추가 완료.
  - 전체 **383개 패스, 2개 스킵**으로 테스트 모듈 전체 성공 확인 완료.

### 2.2 CI/CD 파이프라인 도입 (이슈 I11, I12) - **완료 [2026-06-21]**
- **개선 완료**:
  - GitHub Actions 기반의 자동화 워크플로우 구성 완료: `.github/workflows/ci.yml` 파일을 신규 생성하여 push 및 pull request 트리거 시 `pytest` 실행, `ruff`를 활용한 코드 스타일 및 린트 검사, `mypy`를 통한 정적 타입 검사가 수행되도록 빌드 파이프라인 구축.

---

## 3. 코드 최적화 및 유지보수성 향상

### 3.1 성능 및 로직 최적화 (이슈 I5, I6) - **완료 [2026-06-21]**
- **유니버스 조회 병목**: 파이프라인 내부의 O(n²)에 달하는 리스트 조회를 해시맵(Dict/Set) 기반 O(1) 조회로 최적화하여 딕셔너리 재구축 오버헤드를 완전 제거함.
- **오케스트레이터 폴링 루프**: 데몬의 기존 30초 간격 polling 루프 대기 시간을 `orchestrator.py`에서 60초 간격으로 늘려 불필요한 idle CPU 점유를 축소 완료.

### 3.2 불필요한 의존성 정리 및 리팩토링 (이슈 I7, I8) - **완료 [2026-06-21]**
- 오케스트레이터 및 파이프라인 코드에서 더 이상 사용하지 않는 패키지 및 사용하지 않는 imports 정리 완료.
- `FallbackMetadataDict` 등의 레거시 유틸리티 함수 로직 완전 재작성 혹은 삭제 및 멤버십 검증 unit test assertions 수정 완료.
- 텔레그램 봇의 예외 처리 강화: 오류 발생 시 전체 traceback이 노출되지 않도록 `telegram_bot_runner.py` 내에 예외 포착 및 사용자 친화적 에러 메시지 출력 기능 구현 완료.

---

## 4. 수익률 극대화 및 알파 창출 (Phase 4) - **완료 [2026-06-21]**

안정성과 기본 파이프라인 최적화가 완료됨에 따라, 시스템의 절대 수익률(Rate of Return)과 복리 성장률(CAGR)을 폭발적으로 증가시키기 위한 Phase 4 신규 로드맵입니다.

### 4.1 포트폴리오 최적화 및 자금 관리 고도화
- **Kelly Criterion (켈리 공식) 기반 사이징**: 기존의 `예상 수익률 / 변동성` 방식(Sharpe-ratio proxy)을 탈피하여, 수학적으로 복리 수익을 극대화하는 `예상 수익률 / 분산`($\mu / \sigma^2$) 기반의 켈리 비중(또는 Half-Kelly)으로 포지션 사이징 모듈 전면 개편.
- **Black-Litterman 포트폴리오 모델**: 기존 Risk Parity 모델이 지닌 "변동성 최소화" 한계를 넘어, 예측 모델(XGBoost 등)의 8개 Horizon 예상 수익률을 시장 공분산 행렬과 결합하여 수익을 극대화하는 최적 접점(Tangency) 포트폴리오 산출.

### 4.2 모델 아키텍처 다각화 및 비선형 시계열 인지
- **딥러닝 시계열 모델 도입**: XGB/LGB/Cat 등 테이블형 트리 모델의 한계를 보완하기 위해, 시계열적 흐름을 인지하는 LSTM, Transformer(TimeSformer), TabNet 등을 추가하여 앙상블 체계 확장.
- **시장 국면(Regime) 감지 모델**: HMM(Hidden Markov Model) 또는 GMM을 활용하여 강세장(Bull), 약세장(Bear), 횡보장(Sideways) 국면을 판별하고, 국면에 따라 모델의 가중치와 매매 전략(Trend Following vs Mean Reversion)을 동적으로 변경하는 상위 Meta-Agent 도입.

### 4.3 신규 Alpha 피처 확장 및 전략 추가
- **미시구조(Microstructure) 및 수급 피처**: `alt_data.py`, `darkpool_tracker.py` 등을 활성화하여 장외 다크풀(Dark Pool) 블록트레이드 추적, 옵션 시장의 Gamma Exposure(GEX), Put/Call Ratio 등 기관 수급 데이터를 피처로 추가.
- **통계적 차익거래 (Statistical Arbitrage)**: 현재 코드베이스에 존재하나 미활성 상태인 `src/core/stat_arb.py`를 가동하여, 상관관계가 높은 자산 페어(Pair)의 스프레드 매매를 통해 시장 방향성에 무관한 절대 수익(Alpha) 창출.
- **실행(Execution) 최적화**: 일봉(Daily) 기반 EOD 진입을 장중(Intraday) 분봉 기반 진입으로 세분화하고, 슬리피지를 최소화하는 TWAP/VWAP 체결 알고리즘 연동.

---

## 5. 자율 주식 거래 에이전트(Autonomous Trading Agent) 도입 - **완료 [2026-06-27]**

예측 신호 생성에 머무르지 않고, 실제 위험을 관리하며 자산을 배분하고 체결 및 청산을 수행할 수 있도록 규칙 기반의 자율 매매 시스템을 도입하고 4대 핵심 퀀트 고도화를 수행했습니다.

### 5.1 SQLite 기반 거래 일지 및 통계 산출
- `TradeJournal`(`trade_logs.db`)을 구현하여 매수/매도/취소 거래 내역을 실시간으로 영속화.
- 포지션별 평단가 계산, 승률, 평균 손익비(Win-Loss Ratio), 일일 실현 손익 등 핵심 트레이딩 메트릭 산출 및 검증.

### 5.2 Google News RSS 실시간 뉴스 감성 분석
- `NewsSentimentFetcher`를 구현하여 Google News RSS 피드를 실시간 파싱.
- 1시간 메모리 캐싱 기법을 적용하여 지연 방지 및 불필요한 네트워크 API 호출 방어.

### 5.3 5대 핵심 운영 규칙
- **Rule 1 (자본 위험 관리)**: 단일 거래당 자본의 최대 2% 리스크 한도 설정 (수량 동적 축소).
- **Rule 2 (시장 및 심리 차단)**: VIX > 30.0 또는 뉴스 감성 점수 <= -0.2 시 신규 매수 전면 차단.
- **Rule 3 (통계적 우위)**: 최근 90일 거래 횟수 5회 이상 시 승률 55% 이상 및 기댓값(Edge) > 0 일 때만 진입 허용.
- **Rule 4 (거래 보고)**: 모든 매매 전 진입/청산 사유, 가격, 수량, 손절/익절가를 명시한 요약 보고서 Telegram 전송.
- **Rule 5 (비상 셧다운)**: 지수 일일 변동성 5% 이상 시 모든 미체결 주문 취소 및 보유 주식 전량 즉시 현금화.

### 5.4 4대 핵심 퀀트 고도화 (Quant Enhancements)
- **Q1 (동적 ATR 트레일링 스탑)**: 고정 -5% 손절 대신 `ATR(14) × 2.5` 수준의 동적 트레일링 스탑 적용.
- **Q2 (상관관계 기반 분산)**: 신규 매수 시 기존 보유 종목들과 최근 60영업일 Pearson 상관계수를 계산하여 0.85 이상 BLOCK, 0.70 이상 비중 반감.
- **Q3 (동적 위기 리스크 캡)**: VIX 지수 기반 위기 단계에 따라 거래 리스크 한도 축소 (NONE 2% ~ ACTIVE 1% / SEVERE 매수 차단).
- **Q4 (실효 매매비용 내재화)**: 매수 시 수수료 0.015%+슬리피지 0.2%, 매도 시 거래세/수수료 0.255%+슬리피지 0.2% 실효 매매비용을 반영해 정밀한 Net PnL 산출.

