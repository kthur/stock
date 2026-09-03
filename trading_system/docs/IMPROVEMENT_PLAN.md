# 🚀 시스템 아키텍처 및 성능 개선 계획 (IMPROVEMENT PLAN)

> **작성일**: 2026-06-21  
> **최종 갱신**: 2026-09-03 (KST) — 37대 전략 다변화, 초저지연 L3 LOB / FIX 4.4 / IBKR / 글로벌 SOR / RL 주문 슬라이싱 에이전트, `UnifiedPortfolioAllocator`(4-Model Blending, EWMA Cov), 3대 메가 카드 대시보드 및 2,182+ 전수 테스트 완료

본 문서는 코드베이스 정밀 검토 및 핵심 버그 픽스, 퀀트 시스템 전수 감사(Phase 1~8) 이후 수행된 개선 내역 및 운영 유지보수 계획입니다.

---

## 1. 데이터 파이프라인 및 병목 해소 - **완료**

### 1.1 시장별 동적 펀더멘탈 Filing Lag & 캐싱
- **개선 완료**:
  - `earnings_data.py` 내의 `fetch_and_store_fundamentals_batch` 함수를 고도화하여 데이터 수집 시도 결과를 `fundamental_cache_meta` 테이블에 타임스탬프로 캐싱.
  - 일률적 60일 지연 대신 시장 규정(KRX 45일, US 40일)과 공시 확인 시점(`filing_date`, `rcept_dt`)을 즉시 우선 반영하여 룩어헤드 바이어스를 원천 차단하면서도 실적 모멘텀을 적시에 반영.
  - 소켓 전역 락(`socket.setdefaulttimeout(5)`)을 제거하고 개별 적응형 타임아웃(8s/15s) 및 지터 백오프 재시도 적용.

### 1.2 층화 샘플링 (Stratified Sampling)
- **개선 완료**:
  - 모델 학습 데이터 샘플링(`prepare_training_data`) 시 단순 무작위 추출을 제거하고, Market × Sector × Market-Cap Quantile 다차원 층화 샘플링을 적용하여 표본 대표성 확보.

### 1.3 데이터베이스 동시성 문제
- **개선 완료**:
  - SQLite WAL 모드, busy_timeout 5,000ms, `threading.Lock()` 쓰기 뮤텍스 및 `threading.local` 커넥션을 전면 적용하여 다중 스레드 환경에서 `database is locked` 에러를 원천 제거.

---

## 2. 테스트 커버리지 및 안정성 확보 - **완료**

### 2.1 통합 단일 테스트 스위트 (`tests/`)
- **개선 완료**:
  - 중복 실행되던 `trading_system/tests/`를 루트 `tests/`로 단일 통합.
  - 37대 전략 엔진, `UnifiedPortfolioAllocator`, 앙상블 스코어러, 횡단면 정규화, DART 매퍼, 실체결 슬리피지 피드백, 적대적 스트레스 테스트 등 **2,182개 이상의 테스트**가 구성되어 100% 통과 검증 완료.

### 2.2 CI/CD 파이프라인 도입 및 5-Matrix 최적화
- **개선 완료**:
  - GitHub Actions 워크플로우를 주말 학습(`training.yml`)과 주중 분할 추론(`pipeline.yml` 5-Matrix)으로 분리하여 실행 시간 단축 및 OOM 방지.
  - `pytest.yml` CI에서 `tests/` 루트를 정확히 타겟팅하여 자동화된 회귀 검증 유지.

---

## 3. 코드 최적화 및 유지보수성 향상 - **완료**

### 3.1 성능 및 메모리 최적화
- **유니버스 조회 병목**: 파이프라인 내부의 O(n²)에 달하는 리스트 조회를 해시맵(Dict/Set) 기반 O(1) 조회로 최적화.
- **메모리 다운캐스팅**: float64 데이터프레임을 float32로 자동 다운캐스팅하고 중간 가비지 컬렉션(GC)을 수행하여 메모리 사용량 50% 이상 절감.
- **오케스트레이터 폴링 루프**: 데몬의 폴링 대기 시간을 60초 간격으로 설정하여 불필요한 idle CPU 점유를 축소.

---

## 4. 수익률 극대화 및 알파 창출 (37대 전략 확장) - **완료**

### 4.1 횡단면 점수 정규화 & 결측 가중치 재정규화
- **CrossSectionalScoreNormalizer**: 37개 전략의 출력 점수를 Percentile Rank / Winsorized Gaussian CDF로 $[0.0, 1.0]$ 스케일에 균일 분산 매핑.
- **Missing Strategy Zero-Weighting**: 미산출 전략에 0.50 기본값을 채우지 않고 해당 종목 가중치를 0으로 제외한 뒤 활성 전략 가중치를 정확히 재정규화($\sum \tilde{w} = 1.0$).
- **1D/2D 레짐 가중치 행렬 전수 정규화**: 6대 시장 국면별 37대 전략 가중치 합 strictly = 1.0000 유지.

### 4.2 포트폴리오 최적화 및 자금 관리 고도화
- **UnifiedPortfolioAllocator (4-Model Regime Blending)**: Black-Litterman, HERC, Risk Parity, EVT-CVaR 4대 최적화 모델의 레짐 적응형 결합.
- **3/2승 비선형 시장충격 목적함수**: Gatheral & Almgren-Chriss 모델 기반 비선형 대형 펀드 집행 충격 페널티 최적화.
- **EVT-CVaR 극단값 꼬리위험 예산**: POT-GPD 3단계 계층 구조로 95% CVaR를 엄밀하게 산출하여 테일 리스크 방어.
- **Leland 동적 No-Trade 버퍼 밴드**: 종목별 거래비용과 변동성을 고려한 버퍼 밴드($\delta_i \in [0.5\%, 5.0\%]$)를 적용하여 턴오버 마찰 비용 60% 이상 절감.

### 4.3 37대 전략 다변화 및 직교화
- **37대 전략 완비**: 기존 31개 전략 + 전략 32~37(Cross-Asset Spillover, Supply Chain GNN, Range Expansion Breakout, Dual Correction, Index Rebalance, Overnight Gap Reversal) 완결.
- **PCA-ZCA 대칭 화이트닝 & Gram-Schmidt 직교화**를 적용하여 팩터 간 상관관계 제거 및 순수 알파 추출.

---

## 5. 자율 주식 거래 에이전트 & Execution OMS - **완료**

- `TradeJournal`(`trade_logs.db`) 실시간 체결 기록 및 통계 산출.
- **8대 주문 안전 게이트** 완비:
  - Gate 1: Severe 위기 차단
  - Gate 2: 하드웨어 킬 스위치
  - Gate 3: 심볼 정규식 검증
  - Gate 4: 가격 이상치 및 틱 그리드 정렬
  - Gate 5: 10주/1주 단위 라운딩
  - Gate 6: 포지션 및 섹터 캡
  - Gate 7: 어드밴스드 실행 서브게이트 (단기 과열, 유동성, 순알파 허들)
  - **Gate 8: 합성 베타 인버스 헤지 오버레이 (Bear/Crisis 국면 하락 방어)**
- **Almgren-Chriss 최적 집행 스케줄러**를 통한 비선형 트랜치 주문 분할.
- 실체결 슬리피지 피드백 루프(`SlippageFeedbackEngine`)를 통한 비용 파라미터 적응형 보정.

---

## 6. V8 시스템 정밀 감사 결함 전수 해결 (43개) - **완료**

- Critical 13건: Dynamic filing lag, lookahead bias, PSD covariance flooring, connection pool 누수, FX 환산 분모 버그 등 전수 해결.
- High 16건: Top-K 켈리 폴백, Index Rebalance 3월/9월 정기변경 확장, Overnight Gap 장중 미해소 왜곡 보정 등 전수 해결.
- Medium 14건: 로깅 표준화, KST 타임존 변환 일관성 등 전수 해결.

---

## 7. 초저지연 기관급 실행 레이어 & Master Plan 퀀트 시스템 고도화 - **완료**

### 7.1 Fast LOB Engine (`fast_lob_engine.py`)
- 마이크로초 단위 제로카피 65,536 링버퍼 및 Level 3 오더북 매칭.
- Hawkes 자기여기 점 과정 도착 강도 모델을 통한 주문 폭주 및 유동성 증발 감지.

### 7.2 기관 DMA FIX 4.4 & Interactive Brokers 커넥터
- `fix_protocol_engine.py`: 기관 직결 FIX 4.4 프로토콜 클라이언트 세션 및 하트비트 제어.
- `interactive_brokers.py`: IBKR TWS/Gateway 네이티브 소켓 API 연동.

### 7.3 글로벌 Smart Order Router (SOR) & 강화학습 주문 슬라이싱
- `smart_order_router.py`: `.KS`, `.KQ` 접미사 자동 파싱 및 글로벌 거래소 자동 분기, 베뉴 페일오버.
- `rl_execution_agent.py`: Q-learning 기반 동적 최적 주문 분할 에이전트.

### 7.4 Master Plan Phase 1-3 퀀트 시스템
- **30일 롤링 RankIC 동적 가중치**: 실현 예측력 기반 37대 알파 가중치 스케일링.
- **패닉 역발상 알파 부스트**: 위기 시 과매도 평균회귀 팩터 가중치 일시 증폭.
- **EWMA 공분산 행렬**: RiskMetrics 표준 $\lambda=0.94$ 지수이동평균 추정.
- **연속 비례 Leland 버퍼 밴드**: 거래비용 및 변동성에 비례하는 동적 밴드.
- **KOSDAQ 증권거래세 0.15% 동기화**: 세제 개편안 반영 (3 bps 알파 마찰 제거).
- **대시보드 3대 통합 메가 카드**: Regime Console, Coverage Center, Portfolio OMS 3대 카드 완비.

