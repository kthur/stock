# 📈 Stock Trading System — 통합 주식 자동매매 및 예측 파이프라인

한국(KOSPI/KOSDAQ/KONEX) 및 미국(S&P500) 시장의 **3,379개 종목**을 대상으로
5개 ML/규칙 기반 전략을 병행 운영하는 통합 예측 파이프라인입니다.

---

## 🎯 5대 전략 개요

| # | 전략 | 방식 | 출력 파일 |
|---|------|------|-----------|
| **1** | XGBoost 회귀 | 8개 horizon(1~200일) 예상수익률 예측 | `pipeline_result.txt` |
| **2** | Surge 분류기 | 4개 horizon(1/3/5/20일) 20%↑ 급등 확률 | `surge_predictions.txt` |
| **3** | Lead-Lag 분석 | 시총 TOP50 leader 상관관계 기반 후행 종목 발굴 | `lead_lag_predictions.txt` |
| **4** | VCP 패턴 (규칙) | 변동성 수축 + 거래량 감소 + 고점 근접 규칙 | `vcp_patterns.txt` |
| **5** | VCP ML | 시장별 XGBClassifier 기반 VCP 급등 확률 | `vcp_ml_predictions.txt` |

---

## 🤖 자율 주식 거래 에이전트 (Autonomous Trading Agent)

예측 파이프라인 및 전략 엔진의 시그널을 수신하여 실제 계좌 거래를 안전하게 실행 및 통제하는 자동화 모듈입니다. (`src/ai/trading_agent.py`)

- **5대 운영 규칙**:
  - **Rule 1 (위험 관리)**: 단일 거래당 총 자본금의 최대 2% 리스크 제한.
  - **Rule 2 (감성 & VIX 필터)**: 최근 1시간 뉴스 감성이 극도로 부정적(< -0.2)이거나 VIX > 30.0일 때 진입 차단.
  - **Rule 3 (통계적 우위)**: 최근 90일 거래 횟수 5회 이상 시 승률 55% 이상 및 기댓값 > 0 검증.
  - **Rule 4 (보고 의무)**: 매매 전 진입/청산 상세 근거 요약 보고서 Telegram 자동 알림.
  - **Rule 5 (비상 프로토콜)**: 지수 일일 변동성 5% 이상 서킷 브레이커 시 pending 취소 및 전량 시장가 청산(현금화).
- **4대 핵심 퀀트 고도화**:
  - **Q1 (ATR 트레일링 스탑)**: 진입 이후 최고가 대비 `ATR(14) × 2.5` 수준의 동적 스탑라인 상향 조정.
  - **Q2 (상관관계 기반 분산)**: 신규 진입 종목과 기존 포트폴리오의 60일 Pearson 상관관계 계산 (≥0.85 BLOCK, ≥0.70 비중 50% 축소).
  - **Q3 (위기 리스크 캡)**: VIX 지수 기반 위기 단계별 단일 거래 리스크 한도 차등 적용 (NONE 2% ~ ACTIVE 1% / SEVERE 매수 차단).
  - **Q4 (실효 매매비용 내재화)**: 매수 시 수수료 0.015%+슬리피지 0.2%, 매도 시 세금/수수료 0.255%+슬리피지 0.2% 실효 거래비용을 내재화한 정밀 Net PnL 산출.

---

## 📂 프로젝트 구조

```
stock/
├── trading_system/             ← 핵심 시스템 (코드, 설정, 모델)
│   ├── run_pipeline.py         ← 통합 파이프라인 실행 스크립트
│   ├── orchestrator.py         ← 자동 스케줄러 데몬
│   ├── run_orchestrator.py     ← 오케스트레이터 CLI
│   ├── src/                    ← 소스코드 패키지
│   │   ├── ai/                 ← ML 모델 (예측, VCP, Lead-Lag)
│   │   ├── data_layer/         ← 데이터 수집·저장 레이어
│   │   ├── persistence/        ← DB 영속 계층 (SQLite)
│   │   ├── risk/               ← 리스크 관리·포지션 사이징
│   │   ├── config.py           ← TradingConfig (.env 기반 설정)
│   │   └── ...
│   ├── models/                 ← 학습된 XGBoost 모델 (.json)
│   ├── tests/                  ← pytest 기반 테스트
│   ├── docs/                   ← 상세 문서
│   └── .env.example            ← 환경 변수 템플릿
├── AGENTS.md                   ← AI 에이전트 참조 문서
├── OPTIMIZATION_REPORT.md      ← 성능 최적화 보고서
└── README.md                   ← 이 문서
```

---

## 🛠️ 시스템 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| Python | 3.10+ | 3.11+ |
| 디스크 | 3GB (DB 캐시 포함) | 5GB |
| RAM | 4GB | 8GB+ |
| OS | Windows 10 / Linux | Windows 11 |

---

## 🚀 빠른 시작 (Quick Start)

```powershell
# 1. trading_system 디렉터리로 이동
cd trading_system

# 2. 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 설정 (.env 파일 구성)
copy .env.example .env
# .env 파일을 열어 필요한 API 키 및 설정값 입력

# 5. 파이프라인 실행
.venv\Scripts\python run_pipeline.py
```

> **참고**: 파이프라인 첫 실행 시 3,379개 종목의 주가 데이터를 다운로드하므로 시간이 걸립니다.
> 이후 실행에서는 로컬 SQLite 캐시(`stock_prices.db`)를 활용합니다.

---

## 📚 상세 문서

| 문서 | 설명 |
|------|------|
| [trading_system/README.md](trading_system/README.md) | 설치 가이드, 실행 방법, 트러블슈팅 |
| [docs/ALGORITHMS_AND_STRATEGY.md](trading_system/docs/ALGORITHMS_AND_STRATEGY.md) | 5대 전략 알고리즘 상세 |
| [docs/SYSTEM_ARCHITECTURE.md](trading_system/docs/SYSTEM_ARCHITECTURE.md) | 시스템 아키텍처 및 데이터 흐름 |
| [docs/CONFIGURATION_REFERENCE.md](trading_system/docs/CONFIGURATION_REFERENCE.md) | `.env` 환경 변수 완전 참조 |
| [docs/KNOWN_ISSUES.md](trading_system/docs/KNOWN_ISSUES.md) | 알려진 이슈 및 개선 로드맵 |
| [docs/TEST_GUIDE.md](trading_system/docs/TEST_GUIDE.md) | 테스트 인프라 및 실행 가이드 |
| [OPTIMIZATION_REPORT.md](OPTIMIZATION_REPORT.md) | 성능 최적화 분석 보고서 |

---

## 📊 파이프라인 실행 흐름

```
1. 설정 로드 (TradingConfig)
2. 글로벌 지표 수집 (VIX, TNX, USDKRW 등)
3. 지표 DB 저장
4. 종목 유니버스 로드 (3,379 종목)
5. 지표 히스토리 수집
6. 학습 데이터 준비 (ThreadPoolExecutor + 펀더멘탈)
7. 모델 학습:
   a. 시장별 회귀 모델 (XGBoost + LightGBM + CatBoost)
   b. 시장별 Surge 분류기
   c. Lead-Lag 상관 행렬
   d. 시장별 VCP ML 분류기
8. 추론 데이터 수집
9. 예측 실행 (전 종목)
10. 결과 저장 → 5개 출력 파일 생성
```

---

## ⚙️ 주요 설정 항목

| 환경 변수 | 기본값 | 설명 |
|-----------|--------|------|
| `TRAIN_SAMPLE_SP500` | `50` | SP500 학습 종목 수 (`all` = 전량) |
| `TRAIN_SAMPLE_KRX` | `50` | KRX 학습 종목 수 (`all` = 전량) |
| `SKIP_TRAINING` | `False` | 기존 모델 재사용 (학습 건너뛰기) |
| `STOCK_PRICE_FRESHNESS_DAYS` | `7` | 캐시 유효일 (`none` = 오프라인) |
| `TRAIN_START_DATE` | `2023-01-01` | 학습 데이터 시작일 |

전체 설정 목록은 [CONFIGURATION_REFERENCE.md](trading_system/docs/CONFIGURATION_REFERENCE.md)를 참조하세요.
