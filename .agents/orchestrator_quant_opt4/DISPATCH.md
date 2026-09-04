## 2026-09-04T00:33:16Z

<USER_REQUEST>
You are the Project Orchestrator for Phase 4 of the Quantitative Trading System Enhancement.

## Working Directory & Identity
- Your working directory: d:\Finance\code\stock\.agents\orchestrator_quant_opt4
- Create your working directory and maintain plan.md and progress.md in it.
- Maintain your own BRIEFING.md in your working directory.
- Follow agent workspace conventions: only write metadata (.md) inside your working directory. Never place project code or data files in .agents/.

## Authoritative User Request
- Original Request File: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- Request header: ## 2026-09-04T00:32:34Z
- Integrity mode: development
- Target Markets: KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000 (5 markets)

## Core Tasks & Requirements

### R1. 37대 전략 동적 신호 품질 및 상위 알파 식별력 4차 극대화
- 37대 전략 신호의 비선형 상호작용 및 횡단면 순위 보존을 정밀 고도화하여 Top 분위 종목의 초과수익률(Top-Decile Alpha Spread)을 추가 극대화.
- 레짐별 가중치 적응성 및 지연 감쇠(Half-life) 필터링을 미세 조정하여 시장 잡음 및 횡보장 손실을 원천 억제.

### R2. 포트폴리오 최적 배분 및 체결 슬리피지/마찰비용 최소화 4차 심화
- 4-Model(Black-Litterman, HERC, Risk Parity, EVT-CVaR) 동적 포트폴리오 배분의 위험조정수익률과 자본 배분 효율을 추가 최적화.
- SmartOrderRouter(SOR) 및 다크풀/HFT 오더북 불균형(OBI) 페깅 집행을 정밀화하여 체결 슬리피지 및 마찰 비용을 추가 감축.

### R3. 개선 전후 성과 정량 비교 및 결과 표 정리
- 4차 고도화 전/후의 순기대수익률, 총수익률, 샤프 지수(Sharpe), 정보 비율(Rank-IC), 최대 낙폭(MDD), 회전율, 거래비용 등을 5대 시장별로 정량 비교하여 Markdown 표(Table)로 정리 및 보고.
- 생성/동기화 대상 리포트:
  - `d:\Finance\code\stock\reports\quant_benchmark_comparison_phase4.md`
  - `d:\Finance\code\stock\trading_system\result\quant_benchmark_comparison_phase4.md`
  - `d:\Finance\code\stock\reports\quant_benchmark_comparison.md`

### Acceptance Criteria
- [ ] 37대 전략 신호 결합, 앙상블 가중치, 포트폴리오 배분 및 체결 최적화 4차 심화 코드 수정 완료
- [ ] 기존 2,295+ 단위/통합 테스트 스위트 100% 합격 및 회귀 결함 0건 유지 (.venv\Scripts\python.exe -m pytest tests/ -v)
- [ ] 4차 개선 전후 핵심 지표를 일목요연하게 대조한 종합 표(Table) 보고서 생성

## Execution Guidelines
1. Read the codebase, previous benchmark reports (e.g. `reports/quant_benchmark_comparison_phase3.md`), and explore current implementations in `src/ai/`, `src/risk/`, `src/execution/`, `src/core/`.
2. Decompose tasks, dispatch specialists (workers, reviewers, challengers) under .agents/, implement improvements carefully ensuring backward compatibility with existing tests.
3. Verify test suite thoroughly using .venv\Scripts\python.exe -m pytest tests/.
4. When finished, write handoff.md in your working directory and notify the sentinel via send_message.
</USER_REQUEST>
