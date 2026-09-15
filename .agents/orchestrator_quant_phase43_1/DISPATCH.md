# DISPATCH: Phase 43 Quant Enhancement (Full Team)

## Working Directory
d:\Finance\code\stock\.agents\orchestrator_quant_phase43_1

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal, Risk Allocation, Microstructure OMS, Quant Verification) to deliver Phase 43 Quant Enhancement across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T06:20:40Z)

## Four Specialized Roles to Decompose:
1. **Alpha Signal Specialist**:
   - Quantum Langlands Duality & Affine W-Algebra Chiral Oper Homology 기반 팩터 얽힘 해소 커플러(F191, W-대수 오퍼 장애 복합체 $E_{\text{w\_algebra}}$, 양자 랭글랜즈 불변량 $Z_{\text{quant\_langlands}}$, $\kappa_{\text{w\_alg}}=7.50$)를 `src/ai/ensemble_scorer.py`와 `src/ai/factor_suppression.py`에 구현.
   - 상위 0.000000000000000000000000000001% 초극단 확신 자본 집중을 위한 38차 초볼록 순위 변조 함수 $g_{\text{v43}}(r) = 0.50 + 1.52 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{38})$ (F192.1, 레짐 적응형 $\gamma_{\text{top}}$ 최대 4.70)와 152차($\alpha=152.0$) Centapentacontaduo-gonal 쌍곡선 데드밴드(F192.2, 노이즈 누출률 $< 10^{-84}$)를 `src/ai/factor_suppression.py`에 추가.
   - `src/ai/ensemble_scorer.py`의 버전 분기(version >= 43)에서 이를 호출하여 Rank-IC와 선형 예측력을 추가 개선.

2. **Risk Allocation Specialist**:
   - `src/risk/unified_portfolio_allocator.py`에 Lurie-W-Algebra Motivic Fisher-Rao 다양체 바리센터 블렌딩(F193.1, 메트릭 가중치 $\mu_{\text{lwa}} = [3.30, 2.60, 2.55, 3.85]$)을 버전 분기(version >= 43)로 추가.
   - `src/risk/portfolio_allocator.py`에 39차 큐뮬런트 전개 기반 Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Beilinson-W-Algebra EVaR 꼬리위험 예산화($39! \approx 2.040 \times 10^{46}$, $\xi_{\text{w\_alg}} = 0.999999$)를 구현.
   - 목표: MDD $\le -0.00001\%$, Annualized Sharpe Ratio $\ge 29.15$.

3. **Microstructure & OMS Specialist**:
   - `src/core/fast_lob_engine.py`에 Kerr-Newman-Kiselev 22-Dark-Energy PCQTGBDDDDHKMAEETU Elliptic-Hypergeometric-Askey-Wilson ($w = -24/3 = -8$, $k_{\text{daha}} = 0.14$) DAHA L3 오더북 수력학 모델(F193.2) 적용.
   - `src/execution/smart_order_router.py`에 메이커 플로어 $1 \times 10^{-15}$.
   - `src/execution/oms_engine.py`에 선제적 틱 셰이딩 계수 $-0.9999999999 \cdot \text{spread} \cdot (h - 0.0004)$, 다크풀 라우팅 99.999999999% ATS, Anti-Gaming MinQty 99.9999999998% 구현.
   - 목표: 체결 슬리피지 $\le 0.00002$ bps, 거래 마찰비용 $\le 0.00002$ bps.

4. **Quant Verification Specialist**:
   - `trading_system/scripts/benchmark_phase43_quant_performance.py`(F194) 신규 작성.
   - 전용 단위/통합 테스트 스위트(`tests/test_phase43_*.py`) 구현 (100% 통과, Phase 42 대비 회귀 없음).
   - 5대 시장 대상 15대 핵심 퀀트 지표 비교표 3종([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표) 산출.
   - 리포트 저장 및 최종 출력 동기화:
     - `reports/quant_benchmark_comparison_phase43.md`
     - `trading_system/result/quant_benchmark_comparison_phase43.md`
     - `trading_system/reports/quant_benchmark_comparison_phase43.md`
     - `reports/quant_benchmark_comparison.md`
   - `AGENTS.md` Key Files 테이블에 `benchmark_phase43_quant_performance.py` 추가, Requirements History에 R59 추가, `PROJECT.md` 업데이트.

## Performance Targets (5-Market Aggregate Portfolio)
- Net Expected Return: >= 155.35% (Phase 42 대비 +2.10%p 이상 개선, 목표: 155.39%)
- Annualized Sharpe Ratio: >= 29.15 (+0.60 이상 개선, 목표: 29.18)
- Maximum Drawdown (MDD): <= -0.00001% (극단 꼬리위험 억제 지속, 목표: -0.00001%)
- Trading & Friction Costs: <= 0.00002 bps (50% 추가 절감, 목표: 0.00001 bps)
- Execution Slippage: <= 0.00002 bps (기관급 극초미세 슬리피지 엄격 유지, 목표: 0.00001 bps)
- Top-Decile Alpha Spread: >= 131.00% (+2.30%p 이상 확장, 목표: 131.02%)

## Execution Discipline
- Python executable: `.venv/Scripts/python.exe` (Windows)
- Maintain `progress.md` and `plan.md` in your working directory (`d:\Finance\code\stock\.agents\orchestrator_quant_phase43_1`).
- Verify all tests pass before claiming completion.
- Complete backward compatibility with all prior phases (Phase 1~42).
- Once done, send a completion message to Sentinel with full deliverables summary so Victory Auditor can be dispatched.
