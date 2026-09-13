# DISPATCH: Phase 39 Quant Enhancement (Full Team)

## Working Directory
`d:\Finance\code\stock\.agents\orchestrator_quant_phase39_1`

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal, Risk Allocation, Microstructure OMS, Quant Verification) to deliver Phase 39 Quant Enhancement across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-13T20:29:00Z`)

## Four Specialized Roles to Decompose:
1. **Alpha Signal Specialist**:
   - Motivic Clausen-Scholze Analytic Geometry & Liquid Vector Spaces 기반 팩터 얽힘 해소 커플러(F175, 응집 해석적 장애 복합체 $E_{\text{condensed}}$, 리퀴드 불변량 $Z_{\text{liquid}}$)를 `src/ai/ensemble_scorer.py`와 `src/ai/factor_suppression.py`에 구현.
   - 상위 0.0000000000000000000000001% 초극단 확신 자본 집중을 위한 34차 초볼록 순위 변조 함수 $g_{\text{v39}}(r) = 0.50 + 1.42 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{34})$ (F176.1, 레짐 적응형 $\gamma_{\text{top}}$ 최대 4.00)와 120차 Centaicosagonal($\alpha=120.0$) 쌍곡선 데드밴드(F176.2, 노이즈 누출률 $< 10^{-62}$)를 `src/ai/factor_suppression.py`에 추가.
   - `src/ai/ensemble_scorer.py`의 버전 분기(version >= 39)에서 이를 호출하여 Rank-IC와 선형 예측력을 추가 개선.

2. **Risk Allocation Specialist**:
   - `src/risk/unified_portfolio_allocator.py`에 Lurie-Clausen-Scholze Motivic Fisher-Rao 다양체 바리센터 블렌딩(F177.1, 메트릭 가중치 $\mu_{\text{lcs}} = [2.90, 2.40, 2.35, 3.45]$)을 버전 분기(version >= 39)로 추가.
   - `src/risk/portfolio_allocator.py`에 35차 큐뮬런트 전개 기반 Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze EVaR 꼬리위험 예산화($35! = 1,033,314,796,638,614,492,966,160,480,772,320,000,000$, $\xi_{\text{clausen\_scholze}} = 0.999995$)를 구현.
   - 목표: MDD $\le -0.00008\%$, Annualized Sharpe Ratio $\ge 26.75$.

3. **Microstructure & OMS Specialist**:
   - `src/core/fast_lob_engine.py`에 Kerr-Newman-Kiselev 18-Dark-Energy PCQTGBDDDDHKMA Dunkl-Hecke-Cherednik-Kostka-Macdonald-Askey-Wilson ($w_{\text{pcqtgbddddhkma}} = -20/3$, $k_{\text{askey}} = 0.10$) DAHA L3 오더북 수력학 모델(F177.2) 적용.
   - `src/execution/smart_order_router.py`에 메이커 플로어 0.000000000005.
   - `src/execution/oms_engine.py`에 틱 셰이딩 계수 $-0.999999998 \cdot \text{spread} \cdot (h - 0.0008)$, 다크풀 라우팅 99.99999998% ATS, Anti-Gaming MinQty 99.999999995% 구현.
   - 목표: 체결 슬리피지 $\le 0.0001$ bps, 거래 마찰비용 $\le 0.00015$ bps.

4. **Quant Verification Specialist**:
   - `trading_system/scripts/benchmark_phase39_quant_performance.py`(F178) 신규 작성.
   - 전용 단위/통합 테스트 스위트(`tests/test_phase39_*.py`) 구현 (100% 통과, Phase 38 대비 회귀 없음).
   - 5대 시장 대상 15대 핵심 퀀트 지표 비교표 3종([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표) 산출.
   - 리포트 저장 및 최종 출력 동기화:
     - `reports/quant_benchmark_comparison_phase39.md`
     - `trading_system/result/quant_benchmark_comparison_phase39.md`
     - `trading_system/reports/quant_benchmark_comparison_phase39.md`
     - `reports/quant_benchmark_comparison.md`
   - `AGENTS.md` Key Files 테이블에 `benchmark_phase39_quant_performance.py` 추가, Requirements History에 R55 추가, `PROJECT.md` 업데이트.

## Performance Targets (5-Market Aggregate Portfolio)
- Net Expected Return: >= 146.95% (Phase 38 대비 +2.10%p 이상 개선, 목표: 146.89% ~ 146.99%)
- Annualized Sharpe Ratio: >= 26.75 (+0.60 이상 개선, 목표: 26.78)
- Maximum Drawdown (MDD): <= -0.00008% (하방 꼬리위험 50% 극단적 압축, 목표: -0.00005%)
- Trading & Friction Costs: <= 0.00015 bps (-0.0001 bps 감소, 목표: 0.0001 bps)
- Execution Slippage: <= 0.0001 bps (기관급 최저 슬리피지 엄격 유지)
- Top-Decile Alpha Spread: >= 121.8% (+2.30%p 이상 확장, 목표: 121.82%)

## Execution Discipline
- Python executable: `.venv/Scripts/python.exe` (Windows)
- Maintain `progress.md` and `plan.md` in your working directory.
- Verify all tests pass before claiming completion.
- Complete backward compatibility with all prior phases (Phase 1~38).
- Once done, send a completion message to Sentinel with full deliverables summary so Victory Auditor can be dispatched.
