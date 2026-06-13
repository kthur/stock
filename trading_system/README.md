# 📈 주식 자동매매 및 백테스트 통합 시스템 - 실행 가이드

본 가이드는 주식 자동매매 시스템의 코어 소스코드(`trading_system/`) 가동법, 가상환경 준비, 실행 명령어, API 연동 구성 및 주요 트러블슈팅 방법을 설명합니다.

---

## 📂 상세 설계 및 코어 전략 문서 링크

시스템의 알고리즘 세부 설계, 아키텍처 및 테스트 구성은 `docs/` 하위의 개별 설명서를 참조하십시오:

1. **[시스템 아키텍처 설계서 (docs/SYSTEM_ARCHITECTURE.md)](file:///d:/Finance/code/stock/trading_system/docs/SYSTEM_ARCHITECTURE.md)**
   - 이벤트 기반 아키텍처, 의존성 주입, DB 영속성 레이어, 텔레그램 연동 및 주문 관리 시스템(OMS).
2. **[전략 및 핵심 알고리즘 설명서 (docs/ALGORITHMS_AND_STRATEGY.md)](file:///d:/Finance/code/stock/trading_system/docs/ALGORITHMS_AND_STRATEGY.md)**
   - RF + XGBoost 머신러닝 앙상블, HMM 레짐 및 대가들의 투자 스타일 포트폴리오 로테이션, Optuna 파라미터 최적화, 리스크 한도 관리.
3. **[시스템 테스트 가이드 (docs/TEST_GUIDE.md)](file:///d:/Finance/code/stock/trading_system/docs/TEST_GUIDE.md)**
   - pytest 테스트 구조, 비동기 검증 팁, Windows 로컬 우회 테스트 가이드.

---

## 🚀 빠른 시작 (Quick Start)

### 1. 가상환경 활성화 및 의존성 패키지 설치
Windows 환경에서 명령 프롬프트(CMD) 또는 PowerShell을 열고 아래 명령어를 순서대로 실행합니다:

```powershell
# 가상환경 생성 (최초 1회)
python -m venv .venv

# 가상환경 활성화
.venv\Scripts\activate

# 의존성 라이브러리 설치 및 업그레이드
pip install -r requirements.txt
```

### 2. 환경 설정 파일(`.env`) 생성
템플릿 파일인 `.env.example`을 복사하여 `.env` 파일을 생성하고 필요한 API 키들을 입력합니다:

```powershell
copy .env.example .env
```

`.env` 파일에 각 제공자(Gemini, DeepSeek, OpenAI)의 API 키를 입력할 수 있습니다. (설정하지 않을 시 AI 분석 기능은 시뮬레이션/모의 모드로 가동됩니다.)

```ini
# 사용할 LLM 제공자 선택 (openai / gemini / deepseek)
LLM_PROVIDER=gemini

# Google Gemini API 설정 (기본 권장)
GEMINI_API_KEY=AIzaSy-YourActualGeminiAPIKeyHere
GEMINI_MODEL=gemini-1.5-flash

# DeepSeek API 설정 (OpenAI 호환 엔드포인트 지원)
DEEPSEEK_API_KEY=sk-YourDeepSeekAPIKey
DEEPSEEK_MODEL=deepseek-chat

# OpenAI API 설정
OPENAI_API_KEY=sk-YourOpenAIAPIKey
OPENAI_MODEL=gpt-4o-mini

# 텔레그램 봇 토큰 (실시간 알림 및 수동 제어용)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGh...
```

---

## 💻 실행 방법 및 스크립트 안내

### 1. 실시간 대시보드 및 백테스트 스캐너 가동
Plotly Dash 웹 데몬 및 실시간 포트폴리오 모니터링 화면을 가동합니다.
```powershell
python run_dashboard.py
```
- 실행 후 브라우저에서 `http://localhost:5000`으로 접속합니다.
- 대시보드에서는 실시간 자산 및 누적 수익률 추이, 텔레그램 상태를 확인하고 **백테스트 스캐너 탭**에서 여러 대가들의 투자 모방 전략에 대한 기간별 전수 스캔 및 벤치마크 대비 누적 수익 곡선(Equity Curve) 비교 차트를 조회할 수 있습니다.

### 2. 양방향 텔레그램 제어 봇 실행
텔레그램 메신저를 통해 실시간 알림을 받고 직접 명령어를 전송할 수 있는 봇을 실행합니다.
```powershell
python telegram_bot_runner.py
```
- 주요 명령어: `/status` (시스템 상태), `/portfolio` (자산 현황 및 종목별 비중), `/buy <symbol> <qty>` (수동 매수), `/sell <symbol> <qty>` (수동 매도)

### 3. 파라미터 최적화 스케줄러 실행
Optuna를 가동하여 백테스트 성과 지표(Log Loss, MDD 등)에 맞춰 최적의 매매 및 리스크 제어 변수를 동적으로 탐색하고 설정에 저장합니다.
```powershell
python update_optimize.py
```

### 4. 전체 시스템 통합 가상 시뮬레이션 테스트
실제 API 키나 외부 리소스 없이 전체 매매 시뮬레이션 파이프라인(데이터 수집 ➔ 머신러닝/지표 예측 ➔ 주문 OMS 처리 ➔ 포트폴리오 갱신)을 검증하는 독립 실행 파일입니다.
```powershell
python test_system.py
```

### 5. 파이프라인 자동화 오케스트레이터 데몬 (CLI & Scheduler)
매일 정기적으로 작동해야 하는 파이프라인(데이터 수집, 포스트마켓 스코어링, 모델 재학습 등)을 백그라운드 데몬으로 상시 가동하고 제어합니다.

- **데몬 시작 (Start)**:
  ```powershell
  python run_orchestrator.py start
  ```
  오케스트레이터 데몬(`orchestrator.py`)이 Windows 백그라운드 프로세스로 분리 실행되어 정해진 스케줄러 시각마다 관련 파이프라인을 자동 트리거합니다. (상태 로깅은 `orchestrator.log` 파일에 저장됩니다.)

- **데몬 정지 (Stop)**:
  ```powershell
  python run_orchestrator.py stop
  ```
  실행 중인 오케스트레이터 데몬에 종료 플래그(`stop.flag`) 또는 Windows 신호(`CTRL_BREAK_EVENT`)를 전송하여 수행 중인 배치 처리를 보호하고 Graceful하게 정지시킵니다.

- **데몬 상태 조회 (Status)**:
  ```powershell
  python run_orchestrator.py status
  ```
  현재 데몬의 작동 상태(RUNNING / STOPPED) 및 프로세스 ID(PID), 그리고 SQLite 데이터베이스 `pipeline_runs` 테이블을 조회하여 각 단계별 가장 최근에 가동 완료된 이력 정보를 출력합니다.

- **개별 파이프라인 즉시 강제 트리거 (Run-Now)**:
  ```powershell
  python run_orchestrator.py run-now <stage>
  ```
  특정 파이프라인 배치를 대기 시각 이전에 수동으로 즉시 구동합니다.
  - 지원 스테이지: `indicators` (시장 지표 수집), `universe` (유니버스 업데이트), `train` (ML 모델 재학습), `predict` (종가 예측), `score` (포스트마켓 대가 스타일 스코어링), `ingest` (지표 수집+유니버스), `weekly_train_predict` (재학습+예측), `all` (전체 가동)

---


## 🛠️ 트러블슈팅 (Troubleshooting)

### Q1. "can't open file 'run'" 에러 발생 시
* **증상**: `python run run_dashboard.py` 실행 시 `[Errno 2] No such file or directory` 에러 발생.
* **원인**: Windows CLI 환경에서 `run`이라는 명령어나 인자를 잘못 해석하여 발생한 단순 실행 오타입니다.
* **해결**: 반드시 가상환경 활성화 후 파일명을 단독으로 실행해야 합니다:
  ```powershell
  .venv\Scripts\activate
  python run_dashboard.py
  ```

### Q2. PyTorch 관련 DLL 로딩 오류 (`WinError 1114`) 발생 시
* **증상**: `import torch` 또는 테스트 실행 시 `OSError: [WinError 1114] A dynamic link library (DLL) initialization routine failed.` 발생.
* **원인**: 로컬 Windows 머신 내의 특정 PyTorch 연산 라이브러리(.dll)가 그래픽 드라이버(CUDA) 또는 인텔 CPU MKL 라이브러리와 충돌하여 발생하는 현상입니다.
* **해결 (테스트 실행 시)**: PyTorch 의존적 로직이 포함된 `phase3` 테스트 폴더를 무시하고 나머지 245개 핵심 로직 테스트만 필터링하여 실행합니다:
  ```powershell
  .venv\Scripts\python -m pytest tests/ --ignore=tests/phase3/
  ```

### Q3. "ModuleNotFoundError: No module named 'src'" 에러 발생 시
* **증상**: `pytest` 실행 시 소스 패키지인 `src` 모듈을 찾지 못함.
* **원인**: pytest 실행 시 파이썬 path(`sys.path`)에 현재 프로젝트 디렉터리가 등록되지 않아 생기는 문제입니다.
* **해결**: 단독 `pytest` 대신 파이썬 모듈 실행형태(`python -m pytest`)로 구동하여 현재 디렉터리를 path에 자동으로 로드해야 합니다:
  ```powershell
  .venv\Scripts\python -m pytest tests/
  ```