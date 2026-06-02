# 📈 주식 자동매매 및 백테스트 통합 플랫폼 (Stock Trading System)

본 플랫폼은 **이벤트 기반 아키텍처(Event-Driven)**를 채택하여 시세 수집 ➔ 전략 분석 ➔ 리스크 검증 ➔ 주문 집행(OMS) ➔ 실시간 모니터링을 자동화한 주식 거래 및 시뮬레이션 시스템입니다. 

FastAPI 대시보드를 통해 실시간 자산 상황과 주문 흐름을 모니터링할 수 있으며, 유명 자산가들의 복합 투자 전략 및 기간별 백테스트 스캐닝 툴을 함께 제공합니다.

---

## 🚀 핵심 기능 요약

### 1. 실시간 모니터링 & 웹 대시보드
- **FastAPI + WebSockets**: 서버 상태, 자산 변동, 체결 내역을 브라우저에 지연 없이 실시간 푸시.
- **다크 테마 프리미엄 UI**: 가시성이 높은 차트 및 포트폴리오 요약 통계 대시보드 제공.

### 2. 백테스트 스캐너 (Backtest Scanner)
- **전 종목 전수 스캔**: 한국 시장(KOSPI, KOSDAQ) 및 미국 시장(NASDAQ, NYSE)의 주요 40개 유니버스를 백그라운드 스캔.
- **다차원 기간 필터**: `1개월, 3개월, 6개월, 1년, 3년, 5년, 10년` 등 자유로운 시뮬레이션 주기 선택.
- **수익률 및 성과 지표**: 샤프 비율(Sharpe Ratio), 최대 낙폭(MDD), 승률, 총 거래 횟수 자동 산출 및 정렬.
- **인터랙티브 팝업 차트**: 스캔 결과 테이블에서 종목 클릭 시, 벤치마크 대비 포트폴리오 가치(Equity Curve) 추이와 매수/매도 시점을 라인 차트로 즉시 팝업 시각화.

### 3. 멀티 브로커 & 실거래 연동 아키텍처
- **대신증권 / 한화투자증권**: 모의/시뮬레이션 연동 모듈 제공.
- **키움증권 ZMQ 하이브리드 서버**: 32비트 Windows 환경(OpenAPI)과 64비트 메인 시스템 간의 프로세스 통신 장벽을 극복하기 위해 **ZeroMQ** 기반 소켓 IPC 통신 연동.

### 4. 대가들의 투자 전략 모방 시뮬레이션
- **워렌 버핏(Buffett)**: 가치 지표 위주 하락 포착 전략.
- **피터 린치(Lynch)**: 성장 모멘텀 및 신저점 돌파 전략.
- **레이 달리오(Dalio)**: 변동성(ATR) 통제 기반 올웨더 안정화 모형.
- **추세 추종(Trend Following)**: 이동평균선(20/50/200) 정배열 돌파 기법.
- **AI/LLM 피드백**: OpenAI 모델을 연동하여 투자 시그널 보완(API 미지정 시 모의 모드로 동작).

### 5. 양방향 텔레그램 봇
- `/status`, `/portfolio`, `/buy`, `/sell` 등 채팅을 통해 실시간 자산 조회 및 수동 매매 컨트롤 지원.

---

## 🛠️ 빠른 시작 가이드 (Quick Start)

### 1. 가상환경 구성 및 의존성 설치

```bash
# 레포지토리 루트로 이동
cd d:\Finance\code\stock\trading_system

# 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate

# 필수 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 설정 (`.env`)

`trading_system/` 폴더 내부에 `.env` 파일을 작성합니다. (환경설정이 없어도 기본 모의 모드로 자동 가동됩니다.)

```env
# OpenAI API 키 (투자 의견 생성용, 선택)
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo

# 텔레그램 봇 토큰 (채팅 알림용, 선택)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

### 3. 실행 방법

#### 1) 웹 대시보드 및 백테스트 스캐너 실행

```bash
python run_dashboard.py
```
- 브라우저를 열고 `http://localhost:5000`으로 접속합니다.
- **스캐너 탭**으로 이동하여 원하는 전략과 기간을 설정하고 **스캔 시작**을 눌러보세요.

#### 2) 텔레그램 봇 러너 가동

```bash
python telegram_bot_runner.py
```

#### 3) 기본 시스템 시뮬레이션 테스트

```bash
python test_system.py
```

---

## 📂 아키텍처 상세 문서 안내

시스템의 상세한 소스코드 구조 및 이벤트 전달 다이어그램은 [code_structure.md](file:///d:/Finance/code/stock/code_structure.md) 문서를 참고하시기 바랍니다.

- **`trading_system/src/core/`**: 핵심 트레이딩 자산, 주문 제어기(OMS)
- **`trading_system/src/web/`**: FastAPI 웹 데몬 및 프론트엔드 리소스
- **`trading_system/src/broker/`**: 32비트 키움증권 IPC ZeroMQ 커넥터 및 기타 연동부
- **`trading_system/src/utils/`**: 서킷 브레이커, 비동기 이벤트 버스

---

## ⚙️ 주의 및 참고사항

- **Windows 환경 크래시 방지**: 타이머나 이벤트 대기 스레드에서 Unix 전용 `signal.SIGALRM` 호출 문제를 해결하였으므로, Windows 환경에서 안심하고 가동하셔도 됩니다.
- **실계좌 연동**: 키움증권을 통한 실제 연동이 필요할 시 [PHASE5_IMPLEMENTATION.md](file:///d:/Finance/code/stock/PHASE5_IMPLEMENTATION.md)의 ZMQ 설정 부분을 반드시 정독하시고 별도의 32비트 파이썬 환경에서 `kiwoom_server.py`를 실행하십시오.
