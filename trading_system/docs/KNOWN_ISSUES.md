# ⚠️ Known Issues & 시스템 개선 로드맵

> **Last Updated**: 2026-08-17 (KST)  
> **분석 기준**: 31대 다변화 전략 완결, HRP/EVT-CVaR 포트폴리오 최적화, 30개 전수 감사 및 단일 `tests/` 스위트(1,124+ 테스트 100% 통과) 검증 완료

---

## 🟢 Resolved Issues (2026-08-17 최신 완료)

다음의 핵심 에이전트 연동, 31대 퀀트 고도화, 안정성 이슈 및 아키텍처 개선 사항들이 모두 반영되어 수정 및 구현이 완료되었습니다.

### 1. 31대 전략 다변화 및 퀀트 엔진 고도화
- [x] **31대 전략 앙상블 완결**: 기존 17대에서 Supply Chain Momentum, FinBERT Sentiment, Fama-French 5-Factor Neutralizer, Dynamic Volatility Targeting, Microstructure Imbalance, Accruals Quality, Short Squeeze, Value-Up Catalyst, Kaufman Trend Efficiency, Gamma Squeeze, Insider Buying, Earnings Tone Drift, High-Frequency Darkpool 등 31대 전략으로 확장 완료.
- [x] **데이터 무결성 & 시점이탈 제거**: 재무제표 60일 Filing Lag 적용으로 Lookahead Bias 원천 제거, Lead-Lag US ETF 1일 Lag Shift 적용.
- [x] **Stat-Arb Cointegration Log 변환**: raw price $P$ 대신 $\ln P$ 사용으로 스케일 불변 공적분 수식 정상화.
- [x] **RIM Terminal Value 보정**: $N$년 후 BPS 중복 할인 수식 오류 제거 및 음수 이익 유보율 정상화.
- [x] **LATR 팩터 부호 역전 수정**: 90% 폭락 주식 우대 부호 오작동을 주가 안정성 - 꼬리위험 페널티 수식으로 정상화.
- [x] **Optuna HPO 목적함수 보정**: trial 가중치 합 대신 패턴 검출 후 실제 5일 전방 수익률(Forward Return) 기반으로 최적화 재설계.

### 2. 포트폴리오 최적화 & 미시구조 거래비용
- [x] **Hierarchical Risk Parity (HRP)**: Lopez de Prado 머신러닝 클러스터 트리 기반 위험 배분 및 Ledoit-Wolf 축소($\delta=0.15$) 결합.
- [x] **EVT-CVaR 극단값 꼬리위험 예산**: POT-GPD 3단계 계층 구조로 95% CVaR 계산 및 포트폴리오 테일 리스크 방어.
- [x] **Leland 동적 No-Trade 버퍼 밴드**: 거래비용 및 변동성 기반 $\delta_i \in [0.5\%, 5.0\%]$ 버퍼 밴드 도입으로 리밸런싱 마찰비용 $\ge 60\%$ 절감.
- [x] **실전 미시구조 모델링**: 증권거래세(STT), US SEC 수수료, 호가 갭(Spread), ADV 거래대금 충격 비용(Market Impact) 산출식 구현 및 순예상수익률(`ensemble_expected_return`) 기준 포트폴리오 정렬.
- [x] **실시간 슬리피지 피드백 루프**: `trade_logs.db` 체결 기록 기반 비용 승수($k_{\text{cost}}$) 및 충격 지수($\alpha$) 자동 피드백 보정.

### 3. 시스템 안정성 & 동시성 인프라
- [x] **SQLite WAL & Mutex Lock**: `indicator_storage.py` `_connect()` 컨텍스트 매니저 통일 및 `StockPriceDB` `_write_lock` 적용으로 동시성 DB Lock 예외 원천 제거.
- [x] **RiskManager 파이프라인 연동**: `run_pipeline.py` 실행 시 VIX, 환율, 유가, 금리 기반 `CrisisDetector` 구동 및 위기 단계별 앙상블 기대수익률 스케일링 제어.
- [x] **Execution OMS 6대 주문 안전 게이트**: Severe 위기 차단, 킬 스위치(Kill Switch), 심볼 정규식 검증, 가격 이상치 필터, 10주 단위 라운딩, 단일 포지션 상한 하드 캡 구현.
- [x] **테스트 스위트 단일화**: 중복 실행되던 `trading_system/tests/`를 프로젝트 루트의 `tests/`로 단일 통합하여 1,124+ 테스트 100% 통과 체계 확립.

### 4. 대시보드 UI/UX & CI/CD
- [x] **31개 전략 패널 & 탭 네비게이션 복원**: 누락되었던 LSTM 및 최신 전략 탭 복원 및 데이터 바인딩 정상화.
- [x] **대시보드 상단 고정(Sticky) 헤더 버그 수정**: thead 고정 시 첫 번째(#1) 행이 가려지던 CSS 렌더링 결함 해결.
- [x] **모바일 완전 반응형 최적화**: 터치 스와이프 드로어, 콤팩트 테이블 뷰, 가로 스크롤 필터 바 완비.
- [x] **GHA 워크플로우 5-Matrix 병렬화**: 분할 추론 및 Pages 배포 워크플로우 안정화.

---

## 🟡 운영 유지보수 및 모니터링 수칙

1. **GitHub Actions 5-Matrix Runner 모니터링**:
   - 주말 배치: `training.yml` (토요일 11:30 UTC) 모델 학습 및 캐싱.
   - 주중 배치: `pipeline.yml` (월~금 11:30 UTC) 5개 시장 분할 추론 및 Pages 릴리즈.
2. **실시간 슬리피지 추적**:
   - `trade_logs.db`의 `tracking_error_bps`와 `realized_slippage`를 주기적으로 검토하여 비용 모델 정합성 유지.
3. **거시 위기 단계 모니터링**:
   - VIX > 30 또는 USDKRW 급등 시 `CrisisLevel.ACTIVE` / `SEVERE` 게이트가 정상 작동하는지 Telegram 알림 확인.
