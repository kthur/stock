# ⚠️ Known Issues & 시스템 개선 로드맵

> **Last Updated**: 2026-09-03 (KST)  
> **분석 기준**: 37대 다변화 전략 완결, `UnifiedPortfolioAllocator`(BL/HERC/RP/CVaR 4-Model Blending & 3/2승 충격 페널티), Execution OMS 8대 안전 게이트 (Gate 8 합성 인버스 헤지), V8 정밀 감사(43개 결함 해결) 및 단일 `tests/` 스위트(2,130+ 테스트 100% 통과) 검증 완료

---

## 🟢 Resolved Issues (최신 완료 내역)

다음의 핵심 에이전트 연동, 37대 퀀트 고도화, 안정성 이슈 및 아키텍처 개선 사항들이 모두 반영되어 수정 및 구현이 완료되었습니다.

### 1. 37대 전략 다변화 및 퀀트 엔진 고도화
- [x] **37대 전략 앙상블 완결**: 기존 31개 전략에 6개 기관급 전략(32: Cross-Asset Spillover, 33: Supply Chain GNN, 34: Range Expansion Breakout, 35: Dual Correction, 36: Index Rebalance, 37: Overnight Gap Reversal)을 추가하여 총 37대 전략 포괄.
- [x] **1D/2D 레짐 가중치 행렬 전수 동기화**: 1D 4개 레짐 및 2D 6개 레짐에 대한 37대 전략의 가중치 합이 모든 레짐에서 엄밀하게 $\sum w_i = 1.0000$이 되도록 직교 정규화 완료.
- [x] **37대 전략 횡단면 점수 정규화 (`CrossSectionalScoreNormalizer`)**: 37개 전략의 서로 다른 출력 스케일을 Percentile Rank / Winsorized Gaussian CDF로 $[0.0, 1.0]$ 스케일에 균일 분산으로 매핑하여 앙상블 왜곡 원천 차단.
- [x] **결측 전략 동적 제로 가중치 재정규화**: 산출 불가 전략에 0.50 기본값을 채우지 않고 해당 종목에서 해당 전략 가중치를 0으로 제외한 뒤 활성 전략 가중치를 정확히 재정규화($\sum \tilde{w} = 1.0$).
- [x] **데이터 무결성 & 시장별 동적 Filing Lag**: 일률적 60일 대신 시장 규정(KRX 45일, US 40일) 및 실제 공시일(`filing_date`) 즉시 우선 반영으로 분기 실적 모멘텀 적시 반영.
- [x] **층화 샘플링 (Stratified Sampling)**: 학습 데이터 준비 시 Market × Sector × Market-Cap Quantile 다차원 층화 샘플링으로 대형주/주도주 표본 대표성 확보.
- [x] **Stat-Arb 순수 공적분 선별**: 가짜 BENCHMARK 페어 생성을 완전 제거하고 Engle-Granger ADF($p < 0.05$) 통과 실제 공적분 페어만 파이프라인 전달.

### 2. 포트폴리오 최적화 & 미시구조 거래비용
- [x] **UnifiedPortfolioAllocator (4-Model Regime Blending)**: Black-Litterman + HERC + Risk Parity + EVT-CVaR 4대 최적화 패러다임을 6대 시장 국면에 따라 적응형 블렌딩.
- [x] **3/2승 비선형 시장충격 목적함수 (Gatheral & Almgren-Chriss)**: 거래대금 대비 집행 규모의 1.5제곱 페널티를 목적함수에 부과하여 대형 펀드 집행 시 시장충격 최소화.
- [x] **Leland 동적 No-Trade 버퍼 밴드**: 거래비용 및 변동성 기반 $\delta_i \in [0.5\%, 5.0\%]$ 버퍼 밴드 도입으로 리밸런싱 마찰비용 $\ge 60\%$ 절감. 신규 진입($w_{\text{curr}}=0$) 및 전량 청산($w_{\text{targ}}=0$) 시 즉시 바이패스.
- [x] **실전 미시구조 모델링**: 증권거래세(STT), US SEC 수수료, 호가 갭(Spread), ADV 거래대금 충격 비용(Market Impact) 산출식 구현 및 순예상수익률 기준 포트폴리오 정렬.
- [x] **실시간 슬리피지 피드백 루프**: `trade_logs.db` 체결 기록 기반 비용 승수($k_{\text{cost}}$) 및 충격 지수($\alpha$) 자동 피드백 보정.

### 3. V8 시스템 정밀 감사 결함 전수 해결 (43개)
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
- [x] **High 16건**:
  - Top-K 켈리 폴백 안전장치, Index Rebalance 3월/9월 정기변경 확장, Overnight Gap 장중 미해소 왜곡 보정 등.
- [x] **Medium 14건**:
  - 로깅 포맷 표준화, KST 타임존 변환 일관성 유지, 결측치 보간 안전화 등.

### 4. 시스템 안정성 & 동시성 인프라
- [x] **전역 소켓 락 제거 & 적응형 타임아웃**: 소스별(FRED, ECOS, DART, yfinance) 개별 적응형 타임아웃(8s/15s) 및 지터 백오프 재시도 적용.
- [x] **VIX 속도 및 기간구조 완충 (`CrisisDetector`)**: 5일 VIX 속도($\Delta \text{VIX}_{5d}$) 및 콘탱고 비율($R_{\text{term}}$)을 반영하여 패닉 후 반등 국면에서 과도한 주문 차단 완화.
- [x] **Execution OMS 8대 주문 안전 게이트**: Severe 위기 차단, 킬 스위치(Kill Switch), 심볼 정규식 검증, 가격 이상치 필터, 10주 단위 라운딩, 단일 포지션 상한 하드 캡, 순알파 허들 검증, **Gate 8 합성 인버스 헤지 오버레이**.
- [x] **Almgren-Chriss 최적 집행 스케줄러**: 시장 충격과 타이밍 리스크 절충 비선형 주문 분할 트랜치 생성.
- [x] **SQLite WAL & Mutex Lock**: `indicator_storage.py` `_connect()` 컨텍스트 매니저 통일 및 `StockPriceDB` `_write_lock` 적용으로 동시성 DB Lock 예외 원천 제거.
- [x] **단일 통합 `tests/` 스위트 2,130+ 전수 테스트 100% 통과**: 회귀/경계/상호작용/적대적 스트레스 테스트 전수 통과.

### 5. 대시보드 UI/UX & CI/CD
- [x] **37개 전략 패널 & 탭 네비게이션 복원**: 상단 고정(Sticky) 네비게이션 및 부드러운 스크롤.
- [x] **모바일 완전 반응형 최적화**: 터치 스와이프 드로어, 콤팩트 테이블 뷰, 가로 스크롤 필터 바 완비.
- [x] **GHA 워크플로우 5-Matrix 병렬화**: 37대 전략 분할 추론 및 Pages 배포 워크플로우 안정화.

---

## 🟡 운영 유지보수 및 모니터링 수칙

1. **GitHub Actions 5-Matrix Runner 모니터링**:
   - 주말 배치: `training.yml` (토요일 11:30 UTC) 모델 학습 및 캐싱.
   - 주중 배치: `pipeline.yml` (월~금 11:30 UTC) 5개 시장 분할 추론 및 Pages 릴리즈.
2. **실시간 슬리피지 추적**:
   - `trade_logs.db`의 `tracking_error_bps`와 `realized_slippage`를 주기적으로 검토하여 비용 모델 정합성 유지.
3. **거시 위기 단계 모니터링**:
   - VIX > 30 또는 USDKRW 급등 시 `CrisisLevel.ACTIVE` / `SEVERE` 게이트 및 Gate 8 인버스 헤지가 정상 작동하는지 Telegram 알림 확인.
