# Original User Request

## 2026-08-21T16:26:00Z

제6차 종합 시스템 개선 보고서(`system_improvement_report_v6.md`)에 명시된 35개 신규 결함 및 고도화 과제(V6-01 ~ V6-35)를 전수 수정하고, 단위/통합 회귀 테스트를 100% 통과시킨 후 [문제, 원인, 조치 내용] 형식의 종합 완료 표를 작성합니다.

Working directory: D:\Finance\code\stock
Integrity mode: demo

## Requirements

### R1. 제6차 개선 과제 35건 전수 수정 (Full Implementation of V6-01 ~ V6-35)
`system_improvement_report_v6.md`에 기술된 5대 도메인의 35개 과제를 소스코드에 직접 반영한다:
1. **Domain 1: AI/ML & 예측 무결성 (V6-01 ~ V6-08)**: Causal LSTM 타깃 $\log(1+p)$ 변환 블렌딩 정합, 31대 전략 멀티호라이즌 감쇠 필터 컬럼 스키마 정합, US-KR 듀얼 레짐 가중치 교차 오염 방지, LSTM 교차 시장 모델 하이재킹 수정, Lead-Lag 폴백 1일 수익률 정규화, Optuna 2D 레짐 하락장 2차 효용 최적화 및 심플렉스 경계 투영, Lead-Lag HPO 10종목 상한 해제, MetaEnsembleLearner 피처 차원 정렬
2. **Domain 2: 포트폴리오 & 리스크 공학 (V6-09 ~ V6-16)**: Leland 동적 버퍼 밴드 $w_{\text{curr}}=0$ 신규 진입 및 $w_{\text{targ}}=0$ 전량 청산 우회 허용, Black-Litterman 목적함수 $C^1$ 연속성 확보, EVT-POT 상한선 $u \le q_\alpha$ 및 정규 GPD 형상 모수 하한($\xi \ge -0.5$), Rockafellar-Uryasev 평활화(Pseudo-Huber) 및 제약조건 벡터화, CrisisDetector WATCH 상태 포지션 헤어컷 정상화, 커버리지 분석기 최다 빈도 결측 사유 정합, 하방 세미코베리언스 대각 성분 수축 타깃, RMT Marchenko-Pastur 잔차 고윳값 분산 추정
3. **Domain 3: 31대 전략 엔진 & 데이터 레이어 (V6-17 ~ V6-24)**: RIM valuation BPS/총자본 스케일 정합, Sector Rotation 정밀 GICS 업종 맵 정합, Options IV Skew 실시간 체인 우선 조회, Event-Driven OpenDART 8자리 고유번호-6자리 티커 맵핑, CARD Factor 5일 주가-1일 매크로 충격 시간축 정렬, 다수 팩터 엔진 단일 종목($N=1$) 중립 백분위 랭크 가드, Stat-Arb 10만 원소 넘파이 배열 로깅 제거, DataValidator 주식 역분할(Reverse Split) 처리 및 거래량 확인
4. **Domain 4: 실행 OMS & 거래비용 (V6-25 ~ V6-31)**: ExecutionOMSEngine 원화/달러 통화 분모 환산 적용(1,350배 폭발 방지), OMS Safety Gate 7.2 & 7.4 무차원 수익률 스케일 자동 정규화, Almgren-Chriss 잔여 수량 언더플로우 방지 및 비음수 트랜치 보장, OMS Gate 7.3 마찰 비용 이중 차감 제거, TurnoverOptimizer 턴오버 히스테리시스 전량 청산 우회, SlippageFeedbackEngine `BUY_HEDGE` 슬리피지 부호 교정 및 SQLite `finally` 닫기, SmartOrderRouter ATS 오라우팅 방지
5. **Domain 5: 파이프라인 & CI/CD (V6-32 ~ V6-35)**: `config.py` 최상단 `import json` 및 커스텀 비용 파서 복원, `run_pipeline.py` 최상위 `try...finally` DB 락 보호 및 상태 회수, `generate_run_snapshot.py` 텍스트 파서 인덱스 정합, 파이프라인 수집 시점 KST 타임존 통일 및 config 환경변수 매핑

### R2. 전수 단위 및 통합 회귀 테스트 검증 (Regression & Unit Test Suite Pass)
- 수정된 35개 항목에 대해 기존 1,263개 이상의 테스트 및 신규 추가 테스트가 100% 통과함을 검증한다 (`.venv\Scripts\python.exe -m pytest tests/ -q`).
- 회귀 결함이나 사이드이펙트(Side Effect)가 전혀 발생하지 않도록 테스트 격리를 보장한다.

### R3. [문제, 원인, 내용] 종합 조치 완료 표 작성 (Comprehensive Summary Table)
모든 수정 및 테스트 검증 완료 후, 35개 과제 전체를 **[# | 영역 | 심각도 | 문제 (Issue) | 원인 (Root Cause) | 조치 내용 (Remedy) | 상태]** 열로 체계화된 한글 표로 정리하여 보고서 및 결과물에 수록한다.

## Acceptance Criteria

### 코드 수정 완전성 (Implementation Completeness)
- [ ] V6-01부터 V6-35까지 35개 과제 전체가 지정된 파일 및 라인에 누락 없이 정확하게 수정 적용됨
- [ ] 하드코딩이나 임시 패치가 아닌, 수식 및 아키텍처 원칙에 부합하는 정규 코드로 작성됨

### 테스트 무결성 (Test Pass)
- [ ] 전체 pytest 테스트 스위트 실행 시 실패(Failed) 0건, 에러 0건 달성 (100% Pass)
- [ ] 테스트 실행 중 영구 데드락이나 OOM 없이 안정적으로 완료

### 산출물 체계성 (Structured Table Output)
- [ ] 35개 과제 전체에 대한 [문제, 원인, 내용] 표가 명확하게 작성되어 사용자에게 최종 제공됨

## Verification Resources
- 제6차 종합 개선 보고서: `system_improvement_report_v6.md`
- 시스템 아키텍처 정의: `AGENTS.md`
- 테스트 실행 명령: `.venv\Scripts\python.exe -m pytest tests/ -q`
