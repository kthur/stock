## 2026-09-04T08:37:43Z

You are the Project Orchestrator for Phase 5 Deep Quantitative Enhancements (5차 심화 퀀트 개선) across 37 strategies and 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).

Your working directory is:
`d:\Finance\code\stock\.agents\orchestrator_quant_opt5`

Authoritative User Request is in:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (see header `## 2026-09-04T08:36:42Z`).

## Core Requirements
### R1. 37대 전략 동적 알파 신호 품질 및 상위 알파 식별력 5차 극대화
- 37대 전략 신호의 고차 비선형 결합 및 횡단면 우측 꼬리 볼록성(Right-Tail Convexity)을 고도화하여 Top 분위 종목의 초과수익률(Top-Decile Alpha Spread)을 추가 극대화.
- 거시 경제 및 레짐 전이 불확실성 하에서의 지연 감쇠(Half-life) 및 노이즈 필터링을 미세 조정하여 하방 리스크를 원천 억제.

### R2. 포트폴리오 최적 배분 및 체결 슬리피지/마찰비용 최소화 5차 심화
- 4-Model(Black-Litterman, HERC, Risk Parity, EVT-CVaR) 동적 포트폴리오 배분의 위험조정수익률과 자본 배분 효율을 추가 최적화.
- SmartOrderRouter(SOR) 및 다크풀/HFT 호가잔량불균형(OBI) 페깅 집행을 정밀화하여 체결 슬리피지 및 마찰 비용을 추가 감축.

### R3. 개선 전후 성과 정량 비교 및 결과 표 정리
- 5차 고도화 전/후의 순기대수익률, 총수익률, 샤프 지수(Sharpe), 정보 비율(Rank-IC), 최대 낙폭(MDD), 회전율, 거래비용 등을 5대 시장별로 정량 비교하여 Markdown 표로 정리 및 보고.

## Acceptance Criteria
- [ ] 37대 전략 신호 결합, 앙상블 가중치, 포트폴리오 배분 및 체결 최적화 5차 심화 코드 수정 완료.
- [ ] 기존 2,351+ 단위/통합 테스트 스위트 100% 합격 및 회귀 결함 0건 유지.
- [ ] 5차 개선 전후 핵심 지표를 일목요연하게 대조한 종합 표(Table) 보고서 생성 (e.g. `reports/quant_benchmark_comparison_phase5.md` 및 동기화).
