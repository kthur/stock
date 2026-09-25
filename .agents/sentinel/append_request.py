import os

request_text = """

## 2026-09-23T09:29:23Z

주식 자동매매 및 예측 시스템의 핵심 하위 시스템(시그널 생성, 앙상블 스코어링, OMS 실행 및 벤치마크 검증)에 걸친 약 116건의 실패 테스트와 런타임 수치 불일치 문제를 해결하여 전체 시스템 무결성을 달성합니다.

Working directory: d:\\Finance\\code\\stock
Integrity mode: development

## Requirements

### R1. 앙상블 및 수치 안정성 결함 해결 (Phase 5, 6, 7 적대적 엣지 케이스)
- All zeros, All ones, High NaN proportion (90~100%), 극단적 이상치, 소규모 유니버스(5~8 종목) 입력 조건에서도 수치 폭주(ZeroDivision, NaN 전파, 차원 불일치) 없이 견고하게 정규화 및 가중치 합산이 수행되도록 안정화합니다.
- 상위 10% 분위(Top-decile) 스프레드 확장 및 단조성(monotonicity) 조건 수식을 만족하도록 정합성을 보정합니다.

### R2. 시그널 인핸스먼트 및 감마/레짐 적응형 파라미터 보정 (Phase 8, 9)
- 하이퍼 익스포넨셜 랭크 변조 및 레짐 적응형 캡(`gamma_top`) 도달 가능성 테스트 실패를 해결합니다.
- 멀티 마켓 무작위 스트레스 환경에서 레짐 분기 순서 및 이전 버전 호환성 제약 조건을 온전히 충족하도록 수정합니다.

### R3. 벤치마크 리포트 및 SHA256 해시 동기화 복구 (Phase 60 ~ 65)
- Phase 60부터 Phase 65까지의 OMS 벤치마크 리포트 동기화(`test_benchmark_report_synchronization_vXX`) 및 SHA256 해시 검증 불일치(`test_report_sha256_hash_synchronization_vXX`)를 최신 산출물 상태와 정확히 일치하도록 동기화합니다.

### R4. 머신러닝 예측기 및 수익률 최적화 로직 복구 (Transformer, LSTM, Alpha Boosters)
- `TransformerPredictor`의 순전파 텐서 형태(forward shape), 학습-추론 파이프라인, 모델 저장 및 로드 실패 원인을 해결합니다.
- `Sprint3` Multivariate LSTM 시계열 추론 및 `v7` 알파 허들 레이트(P90 hurdle rate), 거래 비용 언스케일드 관련 수치 오차를 해소합니다.

### R5. 회귀 방지 및 전체 통합 파이프라인 무결성 보장
- 기존에 이미 정상 통과하고 있는 5624개 이상의 테스트가 깨지지 않도록(회귀 방지) 보장합니다.
- `trading_system/run_pipeline.py`가 정상 구동 가능한 상태를 유지해야 합니다.

## Verification Resources

- 프로젝트 내 기존 테스트 스위트:
  - `trading_system\\.venv\\Scripts\\python.exe -m pytest tests -k "test_phase5_m1_challenger2_adversarial or test_phase5_signal_enhancement"`
  - `trading_system\\.venv\\Scripts\\python.exe -m pytest tests -k "test_phase60_adversarial_oms_benchmark or test_phase61_adversarial_oms_benchmark or test_phase62_adversarial_oms_benchmark or test_phase63_adversarial_oms_benchmark or test_phase64_adversarial_oms_benchmark or test_phase65_adversarial_oms_benchmark"`
  - `trading_system\\.venv\\Scripts\\python.exe -m pytest tests -k "test_transformer_predictor or test_sprint3_alpha_refactor or test_v7_returns_maximization"`
  - 전체 단위 검증: `trading_system\\.venv\\Scripts\\python.exe -m pytest tests -k "not benchmark_phase" --tb=short`

## Acceptance Criteria

### Test Pass Verification
- [ ] 기존 실패했던 116개 테스트 케이스가 모두 재실행 시 성공(0 failed)할 것
- [ ] 기존 정상 통과하던 5624개 이상의 테스트 중 신규 실패(regression)가 발생하지 않을 것
- [ ] `trading_system\\.venv\\Scripts\\python.exe -m pytest tests -k "not benchmark_phase"` 실행 결과가 최종 Exit Code 0으로 통과할 것

### Pipeline Integrity
- [ ] `trading_system/run_pipeline.py` 모듈 구동 시 문법 오류 및 누락된 의존성 없이 정상 로딩될 것
- [ ] Git 변경 사항이 불필요한 테스트 코드 억제(skip 처리 등)가 아닌, 실제 코드 결함 및 정합성 보정을 통해 해결되었을 것
"""

paths = [
    r"d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md",
    r"d:\Finance\code\stock\ORIGINAL_REQUEST.md"
]

for p in paths:
    if os.path.exists(p):
        with open(p, "a", encoding="utf-8") as f:
            f.write(request_text)
        print(f"Appended to {p}")
    else:
        print(f"File not found: {p}")
