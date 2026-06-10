# 📈 주식 자동매매 및 백테스트 통합 플랫폼 (Stock Trading System)

본 저장소는 **이벤트 기반 아키텍처(Event-Driven)**를 채택하여 시세 수집 ➔ 전략 분석 ➔ 리스크 검증 ➔ 주문 집행(OMS) ➔ 실시간 모니터링을 자동화한 주식 자동매매 시스템 및 시뮬레이션 플랫폼의 저장소입니다.

코어 소스코드와 환경 설정, 실행 스크립트 등 실제 시스템은 [trading_system/](file:///d:/Finance/code/stock/trading_system/) 디렉터리 내부에 구현되어 있습니다.

---

## 📂 저장소 문서 구성 가이드

현재 작동 중인 최신 시스템 코드베이스를 기준으로 재구축된 공식 문서 가이드라인입니다. 아래 링크를 통해 상세 정보를 확인하실 수 있습니다.

### 1. 사용법 및 시작 안내
* **[trading_system/README.md](file:///d:/Finance/code/stock/trading_system/README.md)**: 전체 시스템의 설치 가이드, 파이썬 가상환경 설정, 텔레그램 및 대시보드 실행 방법, `.env` 설정 템플릿 및 트러블슈팅 안내.

### 2. 아키텍처 및 시스템 상세 설계
* **[SYSTEM_ARCHITECTURE.md (시스템 구조)](file:///d:/Finance/code/stock/trading_system/docs/SYSTEM_ARCHITECTURE.md)**: 이벤트 버스(`EventBus`) 기반의 발행/구독(Pub/Sub) 아키텍처, 데이터 레이어, 주문 관리 시스템(OMS), 다중 브로커 인터페이스 구조 및 실시간 대시보드 처리 흐름.

### 3. 코어 전략 및 핵심 알고리즘
* **[ALGORITHMS_AND_STRATEGY.md (알고리즘 & 전략)](file:///d:/Finance/code/stock/trading_system/docs/ALGORITHMS_AND_STRATEGY.md)**: 
  * Random Forest와 XGBoost의 50:50 소프트 보팅(Soft Voting) 머신러닝 앙상블 모델.
  * GaussianHMM 기반 시장 레짐 분석 및 거물 투자가들(버핏, 린치, 달리오 등)의 복합 포트폴리오 스타일 로테이션.
  * Optuna 교차 검증 기반 적응형 파라미터 최적화기(`AdaptiveParameterOptimizer`).
  * 손절선(Stop-loss), 최대 익절선(Take-profit) 등의 리스크 한도 통제 로직.

### 4. 테스트 인프라 및 가이드
* **[TEST_GUIDE.md (테스트 가이드)](file:///d:/Finance/code/stock/trading_system/docs/TEST_GUIDE.md)**: pytest 기반 테스트 인프라, 비동기 테스트 팁, 모의 거래(Mock Trading) 테스트 케이스 검증 및 Windows 로컬 실행 가이드.

---

## 🛠️ 빠른 시작 요약 (Quick Start)

시스템을 실행하려면 반드시 `trading_system/` 디렉터리로 이동하여 아래의 순서대로 작업을 진행하십시오.

```bash
# 1. trading_system 디렉터리로 이동
cd trading_system

# 2. 가상환경 활성화 및 의존성 패키지 설치
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. 환경 설정 (.env) 구성
cp .env.example .env   # 복사 후 API 키 및 정보 기입

# 4. 실시간 대시보드 가동
python run_dashboard.py
```

자세한 옵션과 연동 정보는 **[trading_system/README.md](file:///d:/Finance/code/stock/trading_system/README.md)**를 참고하십시오.
