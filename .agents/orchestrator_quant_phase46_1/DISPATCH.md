# DISPATCH: Phase 46 Quant Enhancement (Full Team)

## Working Directory
d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal, Risk Allocation, Microstructure OMS, Quant Verification) to deliver Phase 46 Quant Enhancement across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-16T08:29:02Z)

## Verbatim User Task & Requirements
풀 팀(Full Team) — 알파 시그널, 리스크 배분, 미시구조 OMS, 퀀트 검증의 4개 전문 역할로 분업 수행

글로벌 5대 주식 시장(KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000)을 대상으로 시스템의 순수익률(Net Expected Return)을 161.65% 이상(Phase 45 대비 +2.10%p 개선, 목표: 161.69%)으로 끌어올리고 연율화 샤프 지수를 30.95 이상(목표: 30.98)으로 확장하기 위해 Phase 46 퀀트 고도화(Quantum Geometric Langlands Borcherds-Kac-Moody Whittaker Coupler, 41차 초볼록 순위 변조, 176차 Centaheptacontahexagonal 쌍곡선 데드밴드, Lurie-Borcherds-Whittaker Fisher-Rao 바리센터 및 42차 큐뮬런트 Trans-Singular-Borcherds-Whittaker EVaR, Kerr-Newman-Kiselev 25-Dark-Energy DAHA L3 오더북 수력학 및 99.99999999995% 다크풀 선제 체결)를 수행하고, 15대 퀀트 지표 정량 비교표 3종을 산출합니다.

Working directory: d:\Finance\code\stock
Integrity mode: benchmark

## Requirements

### R1. 37대 전략 다이나믹 알파 결합 및 신호 고도화 (Phase 46: F203, F204.1, F204.2)
- Quantum Geometric Langlands Chiral Affine Lie Superalgebra Borcherds-Kac-Moody Whittaker Coupler(F203, 보처즈-카츠-무디-휘태커 장애 복합체 $E_{\text{borch\_whit}}$, 양자 기하학적 랭글랜즈 위상 불변량 $Z_{\text{borch\_whit}}$, $\kappa_{\text{borch\_whit}}=9.00$, $\theta_0=0.50$, $\text{FERI}_{\text{v46}}$)를 `ensemble_scorer.py`와 `factor_suppression.py`에 구현합니다.
- 상위 확신 알파 기회 집중을 위한 41차 초볼록 순위 변조 함수 $g_{\text{v46}}(r) = 0.50 + 1.52 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{41})$ (F204.1, 레짐 적응형 $\gamma_{\text{top}}$ 최대 5.30)를 구현합니다.
- 176차($\alpha=176.0$) Centaheptacontahexagonal 쌍곡선 데드밴드(F204.2, 노이즈 누출률 $< 10^{-102}$)를 `factor_suppression.py`에 적용하여 임계치 이하($|z| \le 0.0003$) 마이크로 노이즈를 완전 제거합니다.
- `ensemble_scorer.py`의 버전 분기(version >= 46)에서 이를 통합 호출하여 5대 시장 횡단면 Rank-IC를 0.992 이상으로 끌어올립니다.

### R2. Lurie-Borcherds-Whittaker 바리센터 및 42차 큐뮬런트 Trans-Singular-Borcherds-Whittaker EVaR (Phase 46: F205.1)
- `unified_portfolio_allocator.py`에 Lurie-Borcherds-Whittaker Motivic Fisher-Rao 다양체 바리센터 블렌딩(F205.1, 메트릭 가중치 $\mu_{\text{lbw}} = [3.60, 2.75, 2.70, 4.15]$)을 버전 분기(version >= 46)로 추가합니다.
- `portfolio_allocator.py`에 42차 큐뮬런트 전개 기반 Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Beilinson-W-Algebra-Virasoro-Kac-Moody-Borcherds EVaR 꼬리위험 예산화($42! \approx 1.405 \times 10^{51}$, $\xi_{\text{borch}} = 0.9999999$)를 구현합니다.
- 복합 포트폴리오의 MDD를 $\le -0.00001\%$로 엄격 유지하고, 연율화 샤프 지수를 30.95 이상으로 확장합니다.

### R3. KNK 25-Dark-Energy DAHA L3 수력학 및 초미세 마찰비용 극소화 (Phase 46: F205.2)
- `fast_lob_engine.py`에 Kerr-Newman-Kiselev 25-Dark-Energy PCQTGBDDDDHKMAEETUVWX ($w = -27/3 = -9.0$, $k_{\text{daha}} = 0.17$, daha_25_factor = 2.38) DAHA L3 오더북 유체역학 모델(F205.2)을 적용합니다.
- `smart_order_router.py`에 리트 메이커 플로어 $1 \times 10^{-18}$ ($0.000000000000000001$), 다크풀 라우팅 99.99999999995% ATS 캡, Anti-Gaming MinQty 99.99999999998%를 구현합니다.
- `oms_engine.py`에 선제적 틱 셰이딩 계수 $-0.99999999999 \cdot \text{spread} \cdot (h - 0.00015)$을 적용하여 체결 슬리피지 및 마찰비용을 $0.0000015\text{ bps}$ 수준으로 50% 추가 절감합니다.

### R4. 5대 시장 실증 퀀트 벤치마크 및 결과 표 출력 (Phase 46: F206)
- `trading_system/scripts/benchmark_phase46_quant_performance.py`(F206)를 신규 작성하고, 전용 테스트 스위트(`tests/test_phase46_*.py`)를 구현하여 100% 통과를 검증합니다.
- 5대 시장 대상 15대 핵심 퀀트 지표 비교표 3종([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표)을 4개 경로(`reports/quant_benchmark_comparison_phase46.md`, `trading_system/result/quant_benchmark_comparison_phase46.md`, `trading_system/reports/quant_benchmark_comparison_phase46.md`, `reports/quant_benchmark_comparison.md`)에 저장하고 최종 출력합니다.
- `AGENTS.md` Key Files 및 `PROJECT.md` 마일스톤(M1~M4 P46) 및 Feature Inventory(F203~F206)를 업데이트합니다.

## Acceptance Criteria

### 1. Performance Targets (5-Market Aggregate Portfolio)
- [ ] Net Expected Return: >= 161.65% (Phase 45 대비 +2.10%p 이상 개선, 목표: 161.69%)
- [ ] Annualized Sharpe Ratio: >= 30.95 (+0.60 이상 개선, 목표: 30.98)
- [ ] Maximum Drawdown (MDD): <= -0.00001% (극단 꼬리위험 엄격 방어 유지)
- [ ] Trading & Friction Costs: <= 0.000003 bps (목표: 0.0000015 bps, 50% 추가 절감)
- [ ] Execution Slippage: <= 0.0000025 bps (목표: 0.00000125 bps, 50% 추가 절감)
- [ ] Top-Decile Alpha Spread: >= 137.90% (+2.30%p 이상 확장, 목표: 137.92%)
- [ ] Win Rate: 100.0% 엄격 유지 (노이즈 누출률 < 10^-102 소멸)

### 2. Verification & Deliverables
- [ ] 15대 퀀트 지표 비교표 3종([표 1], [표 2], [표 3]) 완벽 산출 및 출력
- [ ] 전용 단위/통합 테스트 스위트(`tests/test_phase46_*.py`) 작성 및 Phase 45 회귀 없이 100% 통과
- [ ] 벤치마크 리포트 파일(`reports/quant_benchmark_comparison_phase46.md` 등) 4개 경로 동기화 완료
- [ ] `AGENTS.md` 및 `PROJECT.md` 업데이트 완료
- [ ] 이전 모든 페이즈(Phase 1~45)와의 완전한 하위 호환성 검증
- [ ] 엄격한 정량 검증을 통한 VICTORY CONFIRMED 획득

---
*Phase 45 baseline: Net Return 159.59%, Sharpe 30.38, MDD -0.00001%, Friction 0.000003 bps, Slippage 0.0000025 bps, Top-Decile 135.62%*

## Execution Discipline
- Python executable: .venv/Scripts/python.exe (Windows)
- Maintain progress.md and plan.md in your working directory (d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1).
- Decompose and orchestrate across 4 specialist roles:
  1. Alpha Signal Specialist: F203, F204.1, F204.2 in `ensemble_scorer.py` and `factor_suppression.py`
  2. Risk Allocation Specialist: F205.1 in `unified_portfolio_allocator.py` and `portfolio_allocator.py`
  3. Microstructure OMS Specialist: F205.2 in `fast_lob_engine.py`, `smart_order_router.py`, and `oms_engine.py`
  4. Quant Verification Specialist: F206 benchmark script, test suite, reports 4-path sync, and doc updates
- Verify all tests pass before claiming completion.
- Complete backward compatibility with all prior phases (Phase 1~45).
- Once done, send a completion message to Sentinel with full deliverables summary so Victory Auditor can be dispatched.
