# DISPATCH: Phase 40 Quant Enhancement (Full Team)

## Working Directory
d:\Finance\code\stock\.agents\orchestrator_quant_phase40_1

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal, Risk Allocation, Microstructure OMS, Quant Verification) to deliver Phase 40 Quant Enhancement across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-14T05:30:34Z)

## Four Specialized Roles to Decompose:
1. **Alpha Signal Specialist**:
   - Geometric Langlands & Non-Abelian Hodge-Deligne Analytic Cohomology 기반 팩터 얽힘 해소 커플러(F179, 비아벨 호지 조화 번들 곡률 장애 복합체 {\text{hodge}}$, 들리뉴 조절자 불변량 {\text{deligne}}$)를 src/ai/ensemble_scorer.py와 src/ai/factor_suppression.py에 구현.
   - 상위 0.00000000000000000000000001% 초극단 확신 자본 집중을 위한 35차 초볼록 순위 변조 함수 {\text{v40}}(r) = 0.50 + 1.45 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{35})$ (F180.1, 레짐 적응형 $\gamma_{\text{top}}$ 최대 4.20)와 128차 Octaconta-tetragonal($\alpha=128.0$) 쌍곡선 데드밴드(F180.2, 노이즈 누출률 $< 10^{-68}$)를 src/ai/factor_suppression.py에 추가.
   - src/ai/ensemble_scorer.py의 버전 분기(version >= 40)에서 이를 호출하여 Rank-IC와 선형 예측력을 추가 개선.

2. **Risk Allocation Specialist**:
   - src/risk/unified_portfolio_allocator.py에 Lurie-Langlands-Deligne Motivic Fisher-Rao 다양체 바리센터 블렌딩(F181.1, 메트릭 가중치 $\mu_{\text{lld}} = [3.00, 2.45, 2.40, 3.55]$)을 버전 분기(version >= 40)로 추가.
   - src/risk/portfolio_allocator.py에 36차 큐뮬런트 전개 기반 Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne EVaR 꼬리위험 예산화(! = 37,199,332,678,990,123,746,787,777,307,803,520,000,000$, $\xi_{\text{deligne}} = 0.999996$)를 구현.
   - 목표: MDD $\le -0.00004\%$, Annualized Sharpe Ratio $\ge 27.35$.

3. **Microstructure & OMS Specialist**:
   - src/core/fast_lob_engine.py에 Kerr-Newman-Kiselev 19-Dark-Energy PCQTGBDDDDHKMAE Elliptic Macdonald-Koornwinder-Askey-Wilson ( = -7.0$, {\text{elliptic}} = 0.11$) DAHA L3 오더북 수력학 모델(F181.2) 적용.
   - src/execution/smart_order_router.py에 메이커 플로어  \times 10^{-12}$.
   - src/execution/oms_engine.py에 선제적 틱 셰이딩 계수 $-0.999999999 \cdot \text{spread} \cdot (h - 0.0007)$, 다크풀 라우팅 99.99999999% ATS, Anti-Gaming MinQty 99.999999998% 구현.
   - 목표: 체결 슬리피지 $\le 0.00008$ bps, 거래 마찰비용 $\le 0.00008$ bps.

4. **Quant Verification Specialist**:
   - 	rading_system/scripts/benchmark_phase40_quant_performance.py(F182) 신규 작성.
   - 전용 단위/통합 테스트 스위트(	ests/test_phase40_*.py) 구현 (100% 통과, Phase 39 대비 회귀 없음).
   - 5대 시장 대상 15대 핵심 퀀트 지표 비교표 3종([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표) 산출.
   - 리포트 저장 및 최종 출력 동기화:
     - eports/quant_benchmark_comparison_phase40.md
     - 	rading_system/result/quant_benchmark_comparison_phase40.md
     - 	rading_system/reports/quant_benchmark_comparison_phase40.md
     - eports/quant_benchmark_comparison.md
   - AGENTS.md Key Files 테이블에 enchmark_phase40_quant_performance.py 추가, Requirements History에 R56 추가, PROJECT.md 업데이트.

## Performance Targets (5-Market Aggregate Portfolio)
- Net Expected Return: >= 149.05% (Phase 39 대비 +2.10%p 이상 개선, 목표: 149.09%)
- Annualized Sharpe Ratio: >= 27.35 (+0.60 이상 개선, 목표: 27.38)
- Maximum Drawdown (MDD): <= -0.00004% (하방 꼬리위험 40% 극단적 압축, 목표: -0.00003%)
- Trading & Friction Costs: <= 0.00008 bps (50% 감소, 목표: 0.00005 bps)
- Execution Slippage: <= 0.00008 bps (기관급 최저 슬리피지 엄격 유지, 목표: 0.00005 bps)
- Top-Decile Alpha Spread: >= 124.10% (+2.30%p 이상 확장, 목표: 124.12%)

## Execution Discipline
- Python executable: .venv/Scripts/python.exe (Windows)
- Maintain progress.md and plan.md in your working directory.
- Verify all tests pass before claiming completion.
- Complete backward compatibility with all prior phases (Phase 1~39).
- Once done, send a completion message to Sentinel with full deliverables summary so Victory Auditor can be dispatched.
