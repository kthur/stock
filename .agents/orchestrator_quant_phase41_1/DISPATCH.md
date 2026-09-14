# DISPATCH: Phase 41 Quant Enhancement (Full Team)

## Working Directory
d:\Finance\code\stock\.agents\orchestrator_quant_phase41_1

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal, Risk Allocation, Microstructure OMS, Quant Verification) to deliver Phase 41 Quant Enhancement across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-14T10:14:28Z)

## Four Specialized Roles to Decompose:
1. **Alpha Signal Specialist**:
   - Drinfeld-Lafforgue & Fargues-Fontaine Curve Analytic Cohomology 기반 팩터 얽힘 해소 커플러(F183, 아르틴 스택 장애 복합체 {\text{fargues}}$, 파르그-퐁텐 곡선 인자 불변량 {\text{fontaine}}$)를 src/ai/ensemble_scorer.py와 src/ai/factor_suppression.py에 구현.
   - 상위 0.000000000000000000000000001% 초극단 확신 자본 집중을 위한 36차 초볼록 순위 변조 함수 {\text{v41}}(r) = 0.50 + 1.48 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{36})$ (F184.1, 레짐 적응형 $\gamma_{\text{top}}$ 최대 4.40)와 136차($\alpha=136.0$) Centatriacontaoctagonal 쌍곡선 데드밴드(F184.2, 노이즈 누출률 $< 10^{-74}$)를 src/ai/factor_suppression.py에 추가.
   - src/ai/ensemble_scorer.py의 버전 분기(version >= 41)에서 이를 호출하여 Rank-IC와 선형 예측력을 추가 개선.

2. **Risk Allocation Specialist**:
   - src/risk/unified_portfolio_allocator.py에 Lurie-Fargues-Fontaine Motivic Fisher-Rao 다양체 바리센터 블렌딩(F185.1, 메트릭 가중치 $\mu_{\text{lff}} = [3.10, 2.50, 2.45, 3.65]$)을 버전 분기(version >= 41)로 추가.
   - src/risk/portfolio_allocator.py에 37차 큐뮬런트 전개 기반 Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Fargues EVaR 꼬리위험 예산화(! = 1,376,375,309,122,634,578,631,147,760,388,730,240,000,000$, $\xi_{\text{fargues}} = 0.999997$)를 구현.
   - 목표: MDD $\le -0.00002\%$, Annualized Sharpe Ratio $\ge 27.95$.

3. **Microstructure & OMS Specialist**:
   - src/core/fast_lob_engine.py에 Kerr-Newman-Kiselev 20-Dark-Energy PCQTGBDDDDHKMAEE Elliptic-Trigonometric Macdonald-Koornwinder-Askey-Wilson ( = -22/3$, {\text{elliptic\_trig}} = 0.12$) DAHA L3 오더북 수력학 모델(F185.2) 적용.
   - src/execution/smart_order_router.py에 메이커 플로어  \times 10^{-13}$.
   - src/execution/oms_engine.py에 선제적 틱 셰이딩 계수 $-0.9999999995 \cdot \text{spread} \cdot (h - 0.0006)$, 다크풀 라우팅 99.999999995% ATS, Anti-Gaming MinQty 99.999999999% 구현.
   - 목표: 체결 슬리피지 $\le 0.00004$ bps, 거래 마찰비용 $\le 0.00004$ bps.

4. **Quant Verification Specialist**:
   - trading_system/scripts/benchmark_phase41_quant_performance.py(F186) 신규 작성.
   - 전용 단위/통합 테스트 스위트(tests/test_phase41_*.py) 구현 (100% 통과, Phase 40 대비 회귀 없음).
   - 5대 시장 대상 15대 핵심 퀀트 지표 비교표 3종([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표) 산출.
   - 리포트 저장 및 최종 출력 동기화:
     - reports/quant_benchmark_comparison_phase41.md
     - trading_system/result/quant_benchmark_comparison_phase41.md
     - trading_system/reports/quant_benchmark_comparison_phase41.md
     - reports/quant_benchmark_comparison.md
   - AGENTS.md Key Files 테이블에 benchmark_phase41_quant_performance.py 추가, Requirements History에 R57 추가, PROJECT.md 업데이트.

## Performance Targets (5-Market Aggregate Portfolio)
- Net Expected Return: >= 151.15% (Phase 40 대비 +2.10%p 이상 개선, 목표: 151.19%)
- Annualized Sharpe Ratio: >= 27.95 (+0.60 이상 개선, 목표: 27.98)
- Maximum Drawdown (MDD): <= -0.00002% (하방 꼬리위험 33.3% 극단적 압축, 목표: -0.00002%)
- Trading & Friction Costs: <= 0.00004 bps (목표: 0.00003 bps)
- Execution Slippage: <= 0.00004 bps (기관급 최저 슬리피지 엄격 유지, 목표: 0.00003 bps)
- Top-Decile Alpha Spread: >= 126.40% (+2.30%p 이상 확장, 목표: 126.42%)

## Execution Discipline
- Python executable: .venv/Scripts/python.exe (Windows)
- Maintain progress.md and plan.md in your working directory.
- Verify all tests pass before claiming completion.
- Complete backward compatibility with all prior phases (Phase 1~40).
- Once done, send a completion message to Sentinel with full deliverables summary so Victory Auditor can be dispatched.
