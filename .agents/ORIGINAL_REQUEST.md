# Original User Request

## 2026-08-21T10:09:50Z

제5차 종합 시스템 개선 보고서(`system_improvement_report_v5.md`)에 명시된 32개 신규 결함 및 고도화 과제(V5-01 ~ V5-32)를 전수 수정하고, 단위/통합 회귀 테스트를 100% 통과시킨 후 [문제, 원인, 조치 내용] 형식의 종합 완료 표를 작성합니다.

Working directory: D:\Finance\code\stock
Integrity mode: demo

## Requirements

### R1. 제5차 개선 과제 32건 전수 수정 (Full Implementation of V5-01 ~ V5-32)
`system_improvement_report_v5.md`에 기술된 5대 도메인의 32개 과제를 소스코드에 직접 반영한다:
1. **Domain 1: AI/ML & 예측 무결성 (V5-01 ~ V5-06)**: PCA-ZCA 직교화 릿지 수축 보정, WLS 인덱스 정렬, 팩터 노이즈 억제 에일리어스 정합, 앙상블 샤프 가중치 하한 연결, Optuna VCP 목적함수 연결, Platt Scaling 로짓 입력 변환
2. **Domain 2: 포트폴리오 & 리스크 공학 (V5-07 ~ V5-12)**: Black-Litterman 스케일 정렬 및 2차 효용 최적화, Clayton Copula PSD 스펙트럼 수축, 역방향 CV 훈련 기아 해소, HRP 분산 바닥값($10^{-8}$) 가드, CrisisDetector 큐 동기화, 커버리지 분석기 재무 스키마 정합
3. **Domain 3: 31대 전략 엔진 & 데이터 레이어 (V5-13 ~ V5-23, V5-26 ~ V5-31)**: CARD NameError 수정, Gamma Squeeze `**kwargs` 확장, Microstructure 기본 반환 정상화, Short Squeeze 스케일 정규화, Split-Runner 교차시장 알파 정렬, OBV 0 나눔 방지, RIM 한계기업 순위 오염 방지, DART 8자리 코드 매핑, Factor Neutralizer 릿지 회귀, Flash Crash 주식 분할 오작동 방지, Reversal 소문자 KeyError 방지, IV Skew 세미바리언스 교정, Vol Target 점수 스케일 복원, 발생액 품질 단일 종목 가드, 4개 팩터 연속형 랭킹 전환, 내부자 매수 기본값 처리, config 환경변수 형변환
4. **Domain 4: 실행 OMS & 거래비용 (V5-24 ~ V5-25)**: `calculate_realized_slippage` 시그니처 및 DataClass 반환 정합 복원, 인버스 ETF 헤지 실시간 종가 분모 적용
5. **Domain 5: 파이프라인 & CI/CD (V5-32)**: 20일 시장 수익률 표시 스케일 100배 보정

### R2. 전수 단위 및 통합 회귀 테스트 검증 (Regression & Unit Test Suite Pass)
- 수정된 32개 항목에 대해 기존 1,228개 이상의 테스트 및 신규 추가 테스트가 100% 통과함을 검증한다 (`.venv\Scripts\python.exe -m pytest tests/ -q`).
- 회귀 결함이나 사이드이펙트(Side Effect)가 전혀 발생하지 않도록 테스트 격리를 보장한다.

### R3. [문제, 원인, 내용] 종합 조치 완료 표 작성 (Comprehensive Summary Table)
모든 수정 및 테스트 검증 완료 후, 32개 과제 전체를 **[# | 영역 | 심각도 | 문제 (Issue) | 원인 (Root Cause) | 조치 내용 (Remedy) | 상태]** 열로 체계화된 한글 표로 정리하여 보고서 및 결과물에 수록한다.

## Acceptance Criteria

### 코드 수정 완전성 (Implementation Completeness)
- [ ] V5-01부터 V5-32까지 32개 과제 전체가 지정된 파일 및 라인에 누락 없이 정확하게 수정 적용됨
- [ ] 하드코딩이나 임시 패치가 아닌, 수식 및 아키텍처 원칙에 부합하는 정규 코드로 작성됨

### 테스트 무결성 (Test Pass)
- [ ] 전체 pytest 테스트 스위트 실행 시 실패(Failed) 0건, 에러 0건 달성
- [ ] 테스트 실행 중 영구 데드락이나 OOM 없이 안정적으로 완료

### 산출물 체계성 (Structured Table Output)
- [ ] 32개 과제 전체에 대한 [문제, 원인, 내용] 표가 명확하게 작성되어 사용자에게 최종 제공됨

## Verification Resources
- 제5차 종합 개선 보고서: `system_improvement_report_v5.md`
- 시스템 아키텍처 정의: `AGENTS.md`
- 테스트 실행 명령: `.venv\Scripts\python.exe -m pytest tests/ -q`
