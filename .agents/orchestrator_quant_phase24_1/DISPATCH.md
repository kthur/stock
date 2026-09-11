# DISPATCH: Phase 24 Quant Enhancement (Full Team)

## Working Directory
`d:\Finance\code\stock\.agents\orchestrator_quant_phase24_1`

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal, Risk Allocation, Microstructure OMS, Quant Verification) to deliver Phase 24 Quant Enhancement across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-11T10:54:49Z`)

## Four Specialized Roles to Decompose:
1. **Alpha Signal Specialist**:
   - Derived Arithmetic Topology & Étale-Motivic Spectral Homotopy 기반 팩터 얽힘 해소 커플러(F115, 에탈-모티브 스펙트럼 코호몰로지 $H^*_{\text{ét-mot}}$, 아르틴-베르디에 쌍대 장애 복합체 $E_{\text{arithmetic}}$, 모티브 L-함수 보수 불변량 $Z_{\text{spectral}}$)를 `src/ai/ensemble_scorer.py`와 `src/ai/factor_suppression.py`에 구현.
   - 상위 0.0000000001% 초극단 확신 자본 집중을 위한 19차 초볼록 순위 변조 함수 $g_{\text{v24}}(r) = 0.50 + 1.12 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{19})$ (F116.1, 레짐 적응형 $\gamma_{\text{top}}$ 최대 2.50)와 60차 Hexacontagonal($\alpha=60.0$) 쌍곡선 데드밴드(F116.2, 노이즈 누출률 $< 10^{-32}$)를 `src/ai/factor_suppression.py`에 추가.
   - `src/ai/ensemble_scorer.py`의 버전 분기(version >= 24)에서 이를 호출하여 Rank-IC와 선형 예측력 추가 개선.

2. **Risk Allocation Specialist**:
   - `src/risk/unified_portfolio_allocator.py`에 Lurie Arithmetic Spectral Fisher-Rao 다양체 바리센터 블렌딩(F117.1, 메트릭 가중치 $\mu_{\text{arithmetic}} = [2.15, 1.65, 1.60, 2.70]$)을 버전 분기(version >= 24)로 추가.
   - `src/risk/portfolio_allocator.py`에 20차 큐뮬런트 전개 기반 Trans-Super-Hyper EVaR 꼬리위험 예산화($20! = 2,432,902,008,176,640,000$, $\xi_{\text{super\_hyper}} = 0.80$) 구현.
   - 목표: MDD $\le -0.018\%$, Annualized Sharpe Ratio $\ge 17.75$.

3. **Microstructure & OMS Specialist**:
   - `src/core/fast_lob_engine.py`에 Kerr-Newman-Kiselev 퀸트에센스-팬텀-타키온 3중 암흑에너지($w_{\text{tachyon}} = -5/3$) 블랙홀 스페이스타임 L3 오더북 수력학 모델(F117.2) 적용.
   - `src/execution/smart_order_router.py`에 메이커 플로어 0.0000005 적용.
   - `src/execution/oms_engine.py`에 틱 셰이딩 계수 $-0.9998 \cdot \text{spread} \cdot (h - 0.030)$, 다크풀 라우팅 99.998% ATS, Anti-Gaming MinQty 99.9995% 구현.
   - 목표: 체결 슬리피지 $\le 0.0010$ bps, 거래 마찰비용 $\le 0.018$ bps.

4. **Quant Verification Specialist**:
   - `trading_system/scripts/benchmark_phase24_quant_performance.py`(F118) 작성.
   - 전용 단위/통합 테스트 스위트(`tests/test_phase24_*.py`) 구현 (100% pass, no regression).
   - 5대 시장 대상 15대 핵심 퀀트 지표 비교표 3종([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표) 산출.
   - `reports/quant_benchmark_comparison_phase24.md` 및 `trading_system/result/quant_benchmark_comparison_phase24.md` 저장 및 최종 출력.
   - `AGENTS.md` Key Files 테이블에 `benchmark_phase24_quant_performance.py` 추가, Requirements History에 R40 추가.

## Performance Targets
- Net Expected Return: >= 115.45% (Phase 23 baseline 113.38% 대비 +2.07%p 이상 개선)
- Annualized Sharpe Ratio: >= 17.75 (+0.57 이상)
- Maximum Drawdown (MDD): <= -0.018%
- Trading & Friction Costs: <= 0.018 bps (-0.006 bps 이하)
- Execution Slippage: <= 0.0010 bps
- Top-Decile Alpha Spread: >= 87.2% (+2.3%p 이상)

## Execution Discipline
- Python executable: `.venv/Scripts/python.exe` (Windows)
- Maintain `progress.md` and `plan.md` in your working directory.
- Verify all tests pass before claiming completion.
- Once done, send a message to Sentinel with the completed deliverables and handoff summary.
