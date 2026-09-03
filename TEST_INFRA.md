# E2E Test Infra: Dashboard Strategy Data & UI Integrity

## Test Philosophy
- Opaque-box, requirement-driven testing covering dashboard strategy data parsing, multi-market table rendering, schema synchronization, interactive UI/filtering, and CLI execution.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing.

## Feature Inventory & Test Mapping
| # | Feature | Requirement | Tier 1 (Happy) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Workload) |
|---|---------|-------------|:--------------:|:-----------------:|:-----------------:|:-----------------:|
| 1 | Strategy Proxy Fallback Scoring | R1, R2 | 5 | 5 | ✓ | ✓ |
| 2 | Pipeline Strategy Report Saving | R1, R2 | 5 | 5 | ✓ | ✓ |
| 3 | Robust Market Discovery in Merger | R2 | 5 | 5 | ✓ | ✓ |
| 4 | Ensemble Section Header Sync | R2 | 5 | 5 | ✓ | ✓ |
| 5 | 37-Strategy File Merge Alignment | R2, R14 | 5 | 5 | ✓ | ✓ |
| 6 | Core 5-Market Dashboard Parity | R1, R3 | 5 | 5 | ✓ | ✓ |
| 7 | Strategy Parser Enhancements | R1 | 5 | 5 | ✓ | ✓ |
| 8 | Client JavaScript Hardening | R3 | 5 | 5 | ✓ | ✓ |
| 9 | CLI Execution & Parity Test Suite | Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 10 | Zero NaN/Mojibake & Encoding Integrity | Acceptance Criteria | 5 | 5 | ✓ | ✓ |
| 11 | Unified Portfolio Allocator (BL+HERC+RP+CVaR) | R15 | 5 | 5 | ✓ | ✓ |
| 12 | OMS Gate 8 Synthetic Inverse Hedge Overlay | R15 | 5 | 5 | ✓ | ✓ |
| 13 | V8 System Integrity & Defect Remediation | V8 Audit | 5 | 5 | ✓ | ✓ |
| 14 | World-Class Trader Return Enhancements | World-Class Upgrade | 5 | 5 | ✓ | ✓ |
| 15 | Fast LOB Ring Buffer & L3 Hawkes Matching | R16 | 5 | 5 | ✓ | ✓ |
| 16 | FIX 4.4 Protocol DMA & IBKR Connector | R16 | 5 | 5 | ✓ | ✓ |
| 17 | Smart Order Router & RL Execution Agent | R16 | 5 | 5 | ✓ | ✓ |
| 18 | Master Plan Phase 1-3 Quant Enhancements | R19 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Test Runner**: `pytest tests/` via `.venv/bin/pytest` or `.venv\Scripts\pytest.exe`.
- **Target Suites**:
  - `tests/test_fast_lob_engine.py`: Fast LOB 제로카피 링버퍼, L3 오더북 매칭, Hawkes 도착 강도 모델 검증.
  - `tests/test_fix_and_ibkr_broker.py`: FIX 4.4 프로토콜 세션/메시지 처리 및 IBKR 브로커 커넥터 검증.
  - `tests/test_rl_execution_agent.py`: 강화학습(RL) 기반 동적 최적 주문 슬라이싱 에이전트 검증.
  - `tests/test_system_architecture_fixes.py`: KOSDAQ STT 0.15%, .bfill 룩어헤드 제거, OMS 알파 반감기 라우팅 등 6대 아키텍처 결함 해결 검증.
  - `tests/test_v8_remediation.py`: 43개 결함(Critical 13, High 16, Medium 14) 완결 검증.
  - `tests/test_world_class_quant_enhancements.py`: 연속 켈리, 팩터 중립화, 호가단위 그리드, 회전율 페널티 MVO.
  - `tests/test_world_class_trader_return_enhancements.py`: 미드포인트 페그, 장중 ATR 트레일링 스탑 래칫, 컨플루언스 알파 부스트.
  - `tests/test_v7_returns_maximization.py`: 수익률 극대화, VIF 임계값, 항복 매수 오버라이드.
  - `tests/test_v6_improvements.py`: 4-Tier 회귀 테스트 (35개 항목 직교 검증).
  - `tests/test_v6_adversarial_stress.py`: 적대적 극단값 및 단일종목 N=1 스트레스 테스트.
  - `tests/test_report_generator_hrp.py`: 통합 포트폴리오 배분 파싱 & HTML 리포트 생성.
  - `tests/test_merge_generic_strategies.py`: 37대 전략 다중 시장 파일 병합.
  - `tests/test_verify_gha_artifacts.py`: GHA 산출물 검증 및 37대 정규 전략 순서 검증.
- **Pass / Fail Semantics**: 100% test pass (**2,182 collected test items**), exit code 0, zero regressions.

## Coverage Thresholds
- Tier 1: ≥5 test cases per feature (happy path parsing, standard multi-market rows)
- Tier 2: ≥5 test cases per feature (boundary/corrupt files, 0-row fallback, missing columns, signed NaNs, missing delimiters)
- Tier 3: Pairwise combinations across 5 markets x 37 strategies x 3 file formats
- Tier 4: Real-world workload scenarios (Full pipeline generation -> 37-strategy merge -> HTML report compilation -> HTML DOM validation)
