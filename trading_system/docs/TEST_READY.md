# E2E & Unit Test Suite Ready

## 1. 테스트 실행 도구 (Test Runner)

- **실행 명령**: `.venv\Scripts\python -m pytest tests/ -v`
- **수행 요약**: 전체 315개 테스트가 탐색되어 빌드 경고를 제외하고 모두 성공적으로 수행됩니다.
- **수행 상태**: 313 passed, 2 skipped.

## 2. 테스트 영역별 커버리지 요약

| 영역 (Test Target) | 파일명 | 테스트 수 | 설명 |
|-------------------|-------|----------|------|
| 핵심 메인 루프 & 사이징 | `test_system.py` | 50+ | 사이징 파이프라인 9단계, 트레일링 스탑, 리밸런싱 검증 |
| 위험 관리 엔진 | `test_risk_manager.py` | 33 | Kelly 공식, ATR 스탑레벨 계산, VaR/CVaR 검증 |
| 텔레그램 연동 봇 | `test_telegram_bot.py` | 17 | 명령어 분석 및 텔레그램 API 모사 작동 확인 |
| 머신러닝 앙상블 | `test_ml_ensemble.py` | 5 | RF+XGBoost 소프트 보팅 예측 및 HMM 레짐 결합 테스트 |
| 모의 투자 연동 | `test_mock_trading.py` | 11 | `mock_trading` 전송 및 백그라운드 체결 감시 동작 검증 |
| 데이터베이스 레이어 | `test_database.py` | 7 | 비동기 거래 내역, 자산 내역, AI 예측 영구 저장 테스트 |
| 기타 인프라 | `test_indicators.py` 등 | 190+ | 지표 연동, EventBus, 비동기 헬퍼, 매크로 분석 검증 |
| **전체 (Total)** | **-** | **315** | **완전 무결한 통합 검증 세트 구축 완료** |
