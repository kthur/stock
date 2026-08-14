# Original User Request

## Initial Request — 2026-08-14T09:21:31Z

You are the Project Orchestrator for the Stock Trading System (3,379 symbols: KOSPI, KOSDAQ, KONEX, SP500, NASDAQ, RUSSELL2000).

Your working directory: `d:\Finance\code\stock\.agents\orchestrator_factor_regime`
Original request file: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (also `d:\Finance\code\stock\ORIGINAL_REQUEST.md`)

User Request Summary:
3,379개 한국/미국 주식을 대상으로 한 통합 주식 자동매매 및 예측 시스템의 31대 Multi-Factor & Multi-Model 전략 알파 성능을 고도화하고, Fama-French 5-Factor 노출 제거(Factor Neutralization) 강화 및 2D 시장 레짐 기반 동적 Sharpe 앙상블 가중치 배분을 최적화하는 프로젝트.

Requirements:
1. R1. 31대 전략 알파 스코어링 고도화 및 Fama-French 팩터 중립화 강화:
   - Surge 분류기, VCP, Stat-Arb, Sector Rotation 등 주요 전략 엔진의 노이즈 필터링 및 시그널 정밀도를 향상시킨다.
   - Style Neutralizer 엔진에서 Gram-Schmidt 직교화 및 5-Factor(시총, 가치, 수익성, 투자, 모멘텀) 노출 제거 제약을 강화하여 순수 알파(Pure Alpha) 산출 능력을 증대시킨다 (|rho| < 0.15 이하 보장).
2. R2. 2D 레짐 기반 동적 가중치 배분 및 Sharpe Multiplier 최적화:
   - 2D 시장 레짐(BULL/BEAR, HIGH/LOW VOL) 상태에 따른 31대 전략 가중치 조정을 롤링 Sharpe Ratio 기반 지수형 멀티플라이어(Exponential Sharpe Multiplier)와 EMA 스무딩으로 정밀화하여 변동성 장세 하방 방어력을 극대화한다.
3. R3. 백테스트 검증 및 시스템 회귀 테스트 준수:
   - 백테스트 평가 엔진을 통해 3,379개 종목 대상 롤링 연율화 수익률, Sharpe Ratio, MDD 개선을 검증한다.
   - 기존 pytest 테스트 수트(818개 이상의 unit/integration tests)가 100% PASS 상태를 유지하도록 품질을 보장한다.
   - `run_pipeline.py` 실행 및 `index.html` GitHub Pages 대시보드 리포트가 정상 갱신되는지 확인한다.

Acceptance Criteria:
- 31대 전략 앙상블 알파 백테스트 Sharpe Ratio 향상
- Fama-French 5-Factor 노출 잔여 상관성이 |rho| < 0.15 이하로 제어됨
- 818개 이상의 pytest 단위/통합 테스트 수트 전체 100% 통과 유지
- `run_pipeline.py` 파이프라인 실행 시 오류 없이 31대 전략 스코어링 및 앙상블 출력 정상 완료
- GitHub Pages 대시보드 리포트(`index.html`) 갱신 및 최신 앙상블 TOP 20 및 Rationale 정확한 시각화
