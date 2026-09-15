# DISPATCH: Phase 45 Quant Enhancement (Full Team)

## Working Directory
d:\Finance\code\stock\.agents\orchestrator_quant_phase45_1

## Context & Objectives
You are the Project Orchestrator leading a 4-specialist full team (Alpha Signal, Risk Allocation, Microstructure OMS, Quant Verification) to deliver Phase 45 Quant Enhancement across all 5 global equity markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).

Authoritative user request is recorded in:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T21:55:02Z)

## Verbatim User Task & Requirements
풀 팀(Full Team) — 알파 시그널, 리스크 배분, 미시구조 OMS, 퀀트 검증의 4개 전문 역할로 분업 수행

글로벌 5대 주식 시장(KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000)을 대상으로 시스템의 순수익률(Net Expected Return)을 159.55% 이상(Phase 44 대비 +2.10%p 개선, 목표: 159.59%)으로 끌어올리고 연율화 샤프 지수를 30.35 이상(목표: 30.38)으로 확장하기 위해 Phase 45 퀀트 고도화(Quantum Geometric Langlands Kac-Moody Whittaker Coupler, 40차 초볼록 순위 변조, 168차 Centahexaoctagonal 쌍곡선 데드밴드, Lurie-Kac-Moody-Whittaker Fisher-Rao 바리센터 및 41차 큐뮬런트 Trans-Singular-Kac-Moody-Whittaker EVaR, Kerr-Newman-Kiselev 24-Dark-Energy DAHA L3 오더북 수력학 및 99.9999999998% 다크풀 선제 체결)를 수행하고, 15대 퀀트 지표 정량 비교표 3종을 산출합니다.

Working directory: d:\Finance\code\stock
Integrity mode: benchmark

## Requirements

### R1. 37대 전략 다이나믹 알파 결합 및 신호 고도화 (Phase 45: F199, F200.1, F200.2)
- Quantum Geometric Langlands Chiral Affine Lie Superalgebra Kac-Moody Whittaker Coupler(F199, 카츠-무디-휘태커 장애 복합체 $E_{\text{km\_whit}}$, 양자 기하학적 랭글랜즈 위상 불변량 $Z_{\text{km\_whit}}$, $\kappa_{\text{km\_whit}}=8.50$, $\theta_0=0.50$, $\text{FERI}_{\text{v45}}$)를 `ensemble_scorer.py`와 `factor_suppression.py`에 구현합니다.
- 상위 확신 알파 기회 집중을 위한 40차 초볼록 순위 변조 함수 $g_{\text{v45}}(r) = 0.50 + 1.52 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{40})$ (F200.1, 레짐 적응형 $\gamma_{\text{top}}$ 최대 5.10)를 구현합니다.
- 168차($\alpha=168.0$) Centahexaoctagonal 쌍곡선 데드밴드(F200.2, 노이즈 누출률 $< 10^{-96}$)를 `factor_suppression.py`에 적용하여 임계치 이하($|z| \le 0.0003$) 마이크로 노이즈를 완전 제거합니다.
- `ensemble_scorer.py`의 버전 분기(version >= 45)에서 이를 통합 호출하여 5대 시장 횡단면 Rank-IC를 0.990 이상으로 끌어올립니다.

### R2. Lurie-Kac-Moody-Whittaker 바리센터 및 41차 큐뮬런트 Trans-Singular-Kac-Moody-Whittaker EVaR (Phase 45: F201.1)
- `unified_portfolio_allocator.py`에 Lurie-Kac-Moody-Whittaker Motivic Fisher-Rao 다양체 바리센터 블렌딩(F201.1, 메트릭 가중치 $\mu_{\text{lkmw}} = [3.50, 2.70, 2.65, 4.05]$)을 버전 분기(version >= 45)로 추가합니다.
- `portfolio_allocator.py`에 41차 큐뮬런트 전개 기반 Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne-Beilinson-W-Algebra-Virasoro-Kac-Moody EVaR 꼬리위험 예산화($41! \approx 3.345 \times 10^{49}$, $\xi_{\text{km}} = 0.9999998$)를 구현합니다.
- 복합 포트폴리오의 MDD를 $\le -0.00001\%$로 엄격 유지하고, 연율화 샤프 지수를 30.35 이상으로 확장합니다.

### R3. KNK 24-Dark-Energy DAHA L3 수력학 및 초미세 마찰비용 극소화 (Phase 45: F201.2)
- `fast_lob_engine.py`에 Kerr-Newman-Kiselev 24-Dark-Energy PCQTGBDDDDHKMAEETUVW ($w = -26/3$, $k_{\text{daha}} = 0.16$, daha_24_factor = 2.21) DAHA L3 오더북 유체역학 모델(F201.2)을 적용합니다.
- `smart_order_router.py`에 리트 메이커 플로어 $1 \times 10^{-17}$ ($0.00000000000000001$), 다크풀 라우팅 99.9999999998% ATS 캡, Anti-Gaming MinQty 99.99999999995%를 구현합니다.
- `oms_engine.py`에 선제적 틱 셰이딩 계수 $-0.99999999998 \cdot \text{spread} \cdot (h - 0.0002)$을 적용하여 체결 슬리피지 및 마찰비용을 $0.000003\text{ bps}$ 수준으로 50% 추가 절감합니다.

### R4. 5대 시장 실증 퀀트 벤치마크 및 결과 표 출력 (Phase 45: F202)
- `trading_system/scripts/benchmark_phase45_quant_performance.py`(F202)를 신규 작성하고, 전용 테스트 스위트(`tests/test_phase45_*.py`)를 구현하여 100% 통과를 검증합니다.
- 5대 시장 대상 15대 핵심 퀀트 지표 비교표 3종([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표)을 4개 경로(`reports/quant_benchmark_comparison_phase45.md`, `trading_system/result/quant_benchmark_comparison_phase45.md`, `trading_system/reports/quant_benchmark_comparison_phase45.md`, `reports/quant_benchmark_comparison.md`)에 저장하고 최종 출력합니다.
- `AGENTS.md` Key Files 및 `PROJECT.md` 마일스톤(M1~M4 P45) 및 Feature Inventory(F199~F202)를 업데이트합니다.

## Acceptance Criteria

### 1. Performance Targets (5-Market Aggregate Portfolio)
- [ ] Net Expected Return: >= 159.55% (Phase 44 대비 +2.10%p 이상 개선, 목표: 159.59%)
- [ ] Annualized Sharpe Ratio: >= 30.35 (+0.60 이상 개선, 목표: 30.38)
- [ ] Maximum Drawdown (MDD): <= -0.00001% (극단 꼬리위험 엄격 방어 유지)
- [ ] Trading & Friction Costs: <= 0.000005 bps (목표: 0.000003 bps, 추가 50% 절감)
- [ ] Execution Slippage: <= 0.000005 bps (목표: 0.0000025 bps, 추가 50% 절감)
- [ ] Top-Decile Alpha Spread: >= 135.60% (+2.30%p 이상 확장, 목표: 135.62%)
- [ ] Win Rate: 100.0% 엄격 유지 (노이즈 누출률 < 10^-96 소멸)

### 2. Verification & Deliverables
- [ ] 15대 퀀트 지표 비교표 3종([표 1], [표 2], [표 3]) 완벽 산출 및 출력
- [ ] 전용 단위/통합 테스트 스위트(`tests/test_phase45_*.py`) 작성 및 Phase 44 회귀 없이 100% 통과
- [ ] 벤치마크 리포트 파일(`reports/quant_benchmark_comparison_phase45.md` 등) 4개 경로 동기화 완료
- [ ] `AGENTS.md` 및 `PROJECT.md` 업데이트 완료
- [ ] 이전 모든 페이즈(Phase 1~44)와의 완전한 하위 호환성 검증
- [ ] 엄격한 정량 검증을 통한 VICTORY CONFIRMED 획득

---
*Phase 44 baseline: Net Return 157.49%, Sharpe 29.78, MDD -0.00001%, Friction 0.000006 bps, Slippage 0.000005 bps, Top-Decile 133.32%*

## Execution Discipline
- Python executable: .venv/Scripts/python.exe (Windows)
- Maintain progress.md and plan.md in your working directory (d:\Finance\code\stock\.agents\orchestrator_quant_phase45_1).
- Verify all tests pass before claiming completion.
- Complete backward compatibility with all prior phases (Phase 1~44).
- Once done, send a completion message to Sentinel with full deliverables summary so Victory Auditor can be dispatched.
