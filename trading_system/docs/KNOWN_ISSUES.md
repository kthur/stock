# ⚠️ Known Issues & 시스템 개선 로드맵

> **Last Updated**: 2026-09-03 (KST)  
> **분석 기준**: 37대 다변화 전략 완결, 초저지연 L3 LOB / FIX 4.4 DMA / IBKR / 글로벌 SOR / RL 주문 슬라이싱 에이전트 구축, `UnifiedPortfolioAllocator`(BL/HERC/RP/CVaR 4-Model Blending & 3/2승 충격 페널티, EWMA 공분산), KOSDAQ STT 세제 개편(0.15%), 3대 통합 메가 카드 대시보드, 단일 `tests/` 스위트(2,182+ 테스트 100% 통과) 검증 완료

---

## 🟢 Resolved Issues (최신 완료 내역)

다음의 핵심 에이전트 연동, 37대 퀀트 고도화, 안정성 이슈 및 아키텍처 개선 사항들이 모두 반영되어 수정 및 구현이 완료되었습니다.

### 1. 기관급 초저지연 실행 레이어 완결 (R16)
- [x] **Fast LOB Engine (`fast_lob_engine.py`)**: 마이크로초 단위 제로카피 65,536 고정 크기 링버퍼, Level 3 오더북 매칭 및 Hawkes 자기여기 점 과정 도착 강도 모델 완비.
- [x] **기관 DMA FIX 4.4 Protocol Engine (`fix_protocol_engine.py`)**: Tag-Value 기반 직렬화, 주문 전송(`35=D`), 체결 리포트(`35=8`), 하트비트 세션 관리.
- [x] **Interactive Brokers 네이티브 커넥터 (`interactive_brokers.py`)**: TWS / IB Gateway 소켓 인터페이스 기반 글로벌 주문 집행 및 `MultiBrokerManager` 연동.
- [x] **글로벌 Smart Order Router (`smart_order_router.py`)**: 국내외 다중 거래소(KRX/US/JP/HK/EU/CA) 지능형 자동 분기 및 2차 베뉴 자동 페일오버.
- [x] **강화학습 주문 슬라이싱 에이전트 (`rl_execution_agent.py`)**: Q-learning 기반 동적 최적 주문 분할로 시장충격 및 타이밍 리스크 최소화.

### 2. 엔터프라이즈 6대 아키텍처 결함 해결 (R17)
- [x] **KOSDAQ 증권거래세 0.15% 동기화**: 세제 개편안을 반영하여 KOSPI와 KOSDAQ 모두 0.15%로 통일, 3 bps 불필요한 알파 마찰 페널티 해소.
- [x] **수익률 역방향 편향(`.bfill()`) 원천 제거**: 포트폴리오 수익률 및 팩터 시계열 계산 시 미래 참조 인과성 왜곡 원천 배제.
- [x] **OMS 37대 전략 Alpha Half-Life 동적 집행 라우팅**: 초단기($t_{1/2} \le 1$d) Fast-VWAP, 단기($1\text{d} < t_{1/2} \le 5\text{d}$) Almgren-Chriss, 중장기 POV 자동 분기.
- [x] **SmartOrderRouter `.KS`/`.KQ` 접미사 파싱 보정**: 국내외 종목 티커 자동 인식 및 거래소 라우팅 안정화.
- [x] **StrategyCoverageAnalyzer Standalone 격리**: 독립 장전 특수 전략 분리 격리 및 결측 사유 매핑 보정.

### 3. Master Plan Phase 1-3 퀀트 시스템 & 대시보드 고도화 (R18, R19)
- [x] **30일 롤링 RankIC 동적 알파 가중치**: 실현 예측력 기반 37대 팩터 동적 가중치 스케일링.
- [x] **패닉 역발상 알파 (Contrarian Reversal)**: 극단적 위기 국면에서 과매도 평균회귀 팩터 가중치 일시 증폭으로 반등 알파 선취.
- [x] **EWMA 공분산 행렬**: RiskMetrics 표준 반감기 $\lambda=0.94$ 적용으로 변동성 급변 적시 반영.
- [x] **연속 비례 Leland 버퍼 밴드**: 거래비용 및 변동성 비율에 비례하는 동적 불감대 적용으로 턴오버 60% 이상 절감.
- [x] **소프트 크라이시스 게이팅**: 하드 컷오프 대신 2차 함수 기반의 점진적 디리스킹(De-risking).
- [x] **대시보드 3대 통합 메가 카드 & 37-Alpha 레이더 차트**:
  - Card 1: Market Regime & Risk Gates Console
  - Card 2: Strategy Coverage & Missingness Center
  - Card 3: Portfolio Optimization & Execution OMS
  - 37-Alpha 레이더 차트, 컬럼 프리셋, 관심종목(Watchlist), 종목 상세 팩터 분해 드로어 완비.

### 4. V8 시스템 정밀 감사 결함 전수 해결 (43개)
- [x] **Critical 13건**:
  1. `run_pipeline.py` dynamic filing lag KRX/US 누락 해결
  2. `earnings_data.py` 미래 데이터 누수(lookahead bias) 차단
  3. `portfolio_optimizer.py` Ledoit-Wolf 공분산 비양정치(Non-PSD) 고유치 플로어링($\lambda_{\min} \ge 10^{-6}$)
  4. `indicator_storage.py` 커넥션 풀 누수 및 WAL 체크포인트 블로킹 해소
  5. `order_manager.py` 환율 변환 분모(FX Denominator) US 달러화 역산 버그 수정
  6. `oms_engine.py` Gate 8 합성 인버스 헤지 주문량 생성 및 부호 오류 수정
  7. `ensemble_scorer.py` 37대 전략 가중치 합 정규화 오차 해소
  8. `vcp_detector.py` 분할 조정 미반영으로 인한 허위 VCP 감지 수정
  9. `stat_arb.py` 반감기 계산 시 log(2)/theta 분모 0 보호
  10. `unified_portfolio_allocator.py` SLSQP 실패 시 HERC fallback 안전장치
  11. `trade_journal.py` 트랜잭션 롤백 시 락 잔존 버그 수정
  12. `generate_report.py` 특수문자 및 NaN 미이스케이프로 인한 HTML 파싱 실패 방지
  13. `preseed_data.py` 무한 루프 재시도 방지 및 지수 백오프 적용
- [x] **High 16건**: Top-K 켈리 폴백 안전장치, Index Rebalance 3월/9월 정기변경 확장, Overnight Gap 장중 미해소 왜곡 보정 등.
- [x] **Medium 14건**: 로깅 포맷 표준화, KST 타임존 변환 일관성 유지, 결측치 보간 안전화 등.

### 5. 시스템 인프라 & 테스트 전수 무결점
- [x] **전역 소켓 락 제거 & 적응형 타임아웃**: 소스별(FRED, ECOS, DART, yfinance) 개별 적응형 타임아웃(8s/15s) 및 지터 백오프 재시도 적용.
- [x] **Execution OMS 8대 주문 안전 게이트**: Severe 위기 차단, 킬 스위치(Kill Switch), 심볼 정규식 검증, 가격 이상치 필터, 10주 단위 라운딩, 단일 포지션 상한 하드 캡, 순알파 허들 검증, **Gate 8 합성 인버스 헤지 오버레이**.
- [x] **SQLite WAL & Mutex Lock**: `indicator_storage.py` 컨텍스트 매니저 통일 및 `StockPriceDB` `_write_lock` 적용으로 동시성 DB Lock 예외 원천 제거.
- [x] **단일 통합 `tests/` 스위트 2,182+ 전수 테스트 100% 통과**: 2,182개 테스트 무결점 통과.

---

## 🟡 운영 유지보수 및 모니터링 수칙

1. **GitHub Actions 5-Matrix Runner 모니터링**:
   - 주말 배치: `training.yml` (토요일 11:30 UTC) 모델 학습 및 캐싱.
   - 주중 배치: `pipeline.yml` (월~금 11:30 UTC) 5개 시장 분할 추론 및 Pages 릴리즈.
2. **실시간 슬리피지 추적**:
   - `trade_logs.db`의 `tracking_error_bps`와 `realized_slippage`를 주기적으로 검토하여 비용 모델 정합성 유지.
3. **기관 실행 세션 모니터링**:
   - FIX 4.4 하트비트 세션, IBKR TWS/Gateway 연결 포트, Fast LOB 링버퍼 오버플로우 여부 모니터링.
4. **거시 위기 단계 모니터링**:
   - VIX > 30 또는 USDKRW 급등 시 `CrisisLevel.ACTIVE` / `SEVERE` 게이트 및 Gate 8 인버스 헤지가 정상 작동하는지 Telegram 알림 확인.
