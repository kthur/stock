# DISPATCH: Phase 26 Quant Enhancement (Full Team)

## Working Directory
`d:\Finance\code\stock\.agents\orchestrator_quant_phase26_1`

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal, Risk Allocation, Microstructure OMS, Quant Verification) to deliver Phase 26 Quant Enhancement across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-11T13:18:53Z`)

## Four Specialized Roles to Decompose:
1. **Alpha Signal Specialist**:
   - Perfectoid Shimura Variety & Mochizuki Inter-Universal Teichmüller (IUT) Reconstruction 기반 팩터 얽힘 해소 커플러(F123, 호지-테이트 필트레이션 장애 복합체 $E_{\text{shimura}}$, 모치즈키 세타-링크 불변량 $Z_{\text{mochizuki}}$)를 `src/ai/ensemble_scorer.py`와 `src/ai/factor_suppression.py`에 구현.
   - 상위 0.000000000001% 초극단 확신 자본 집중을 위한 21차 초볼록 순위 변조 함수 $g_{\text{v26}}(r) = 0.50 + 1.16 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{21})$ (F124.1, 레짐 적응형 $\gamma_{\text{top}}$ 최대 2.70)와 68차 Hexaoctagonal($\alpha=68.0$) 쌍곡선 데드밴드(F124.2, 노이즈 누출률 $< 10^{-36}$)를 `src/ai/factor_suppression.py`에 추가.
   - `src/ai/ensemble_scorer.py`의 버전 분기(version >= 26)에서 이를 호출하여 Rank-IC와 선형 예측력 추가 개선.

2. **Risk Allocation Specialist**:
   - `src/risk/unified_portfolio_allocator.py`에 Lurie Mochizuki IUT Fisher-Rao 다양체 바리센터 블렌딩(F125.1, 메트릭 가중치 $\mu_{\text{mochizuki}} = [2.25, 1.75, 1.70, 2.80]$)을 버전 분기(version >= 26)로 추가.
   - `src/risk/portfolio_allocator.py`에 22차 큐뮬런트 전개 기반 Trans-Singular-Hyper EVaR 꼬리위험 예산화($22! = 1,124,000,727,777,607,680,000$, $\xi_{\text{singular\_hyper}} = 0.90$) 구현.
   - 목표: MDD $\le -0.011\%$, Annualized Sharpe Ratio $\ge 18.95$.

3. **Microstructure & OMS Specialist**:
   - `src/core/fast_lob_engine.py`에 Kerr-Newman-Kiselev 카멜레온 5중 암흑에너지($w_{\text{chameleon}} = -7/3$) 블랙홀 스페이스타임 L3 오더북 수력학 모델(F125.2) 적용.
   - `src/execution/smart_order_router.py`에 메이커 플로어 0.0000001 적용.
   - `src/execution/oms_engine.py`에 틱 셰이딩 계수 $-0.99995 \cdot \text{spread} \cdot (h - 0.020)$, 다크풀 라우팅 99.9995% ATS, Anti-Gaming MinQty 99.9999% 구현.
   - 목표: 체결 슬리피지 $\le 0.0005$ bps, 거래 마찰비용 $\le 0.010$ bps.

4. **Quant Verification Specialist**:
   - `trading_system/scripts/benchmark_phase26_quant_performance.py`(F126) 작성.
   - 전용 단위/통합 테스트 스위트(`tests/test_phase26_*.py`) 구현 (100% pass, no regression).
   - 5대 시장 대상 15대 핵심 퀀트 지표 비교표 3종([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표) 산출.
   - `reports/quant_benchmark_comparison_phase26.md` 및 `trading_system/result/quant_benchmark_comparison_phase26.md` 저장 및 최종 출력.
   - `AGENTS.md` Key Files 테이블에 `benchmark_phase26_quant_performance.py` 추가, Requirements History에 R42 추가.

## Performance Targets
- Net Expected Return: >= 119.65% (Phase 25 baseline 117.59% 대비 +2.06%p 이상 개선)
- Annualized Sharpe Ratio: >= 18.95 (+0.57 이상)
- Maximum Drawdown (MDD): <= -0.011% (하방 꼬리위험 극단적 압축)
- Trading & Friction Costs: <= 0.010 bps (-0.002 bps 이하)
- Execution Slippage: <= 0.0005 bps
- Top-Decile Alpha Spread: >= 91.8% (+2.2%p 이상)

## Execution Discipline
- Python executable: `.venv/Scripts/python.exe` (Windows)
- Maintain `progress.md` and `plan.md` in your working directory.
- Verify all tests pass before claiming completion.
- Once done, send a message to Sentinel with the completed deliverables and handoff summary.
