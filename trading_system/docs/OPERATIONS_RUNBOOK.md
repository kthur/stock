# 운영 런북 (Operations Runbook)

실거래 및 31대 전략 예측 파이프라인 운영 시 반드시 지켜야 할 절차와 장애 대응 가이드입니다. **코드보다 운영 절차가 먼저다.**

---

## 1. 기본 원칙

| 항목 | 값 |
|------|------|
| 실매매 기본값 | **비활성** (`REALTIME_TRADE_ENABLED` 미설정 = DRY_RUN) |
| 실매매 활성 조건 | `REALTIME_TRADE_ENABLED=true` + 브로커 실연결 + 비시뮬레이션 |
| 주문 금액 상한 | `REALTIME_MAX_ORDER_VALUE_KRW` (기본 5,000만 원/건) |
| 위기 게이트 | CrisisLevel.SEVERE → 신규 주문 계획 전체 차단 |
| 킬 스위치 | `KILL_SWITCH` 파일 또는 `KILL_SWITCH=1` env |
| 7대 안전 게이트 | SEVERE 위기 차단, 킬 스위치, 티커 정규식, 가격 이상치, 10주 라운딩, 포지션 캡, 순알파 허들 |

실매매를 켜기 전에 아래 **체크리스트**를 통과해야 한다.

---

## 2. 파이프라인 실행

```bash
# 정기 배치 (31대 전략 학습 + 추론 + 횡단면 정규화 + 2D 앙상블 + HRP 포트폴리오 최적화 + 리포트 생성)
.venv/Scripts/python.exe trading_system/run_pipeline.py

# 훈련 스킵 (기존 모델 재사용 — 빠른 재추론)
.venv/Scripts/python.exe trading_system/run_pipeline.py --skip-training

# 특정 시장만
.venv/Scripts/python.exe trading_system/run_pipeline.py --target KOSPI
.venv/Scripts/python.exe trading_system/run_pipeline.py --target SP500
.venv/Scripts/python.exe trading_system/run_pipeline.py --target KRX
```

**반드시 성공해야 하는 검증 (실패 시 파이프라인 자체가 raise):**

| 검증 | 조건 |
|------|------|
| 핵심 출력 파일 | `pipeline_result.txt`, `surge_predictions.txt`, `ensemble_predictions.txt`, `strategy_data_coverage_report.txt` 존재 + 비어있지 않음 |
| 빈 추론 | `predict_all` 결과가 비면 런타임 오류 → 날짜 릴리즈 없음 |
| 전 종목 수익률 0.0 | 모든 expected return이 0.0이면 실패 (모델 고장 시그니처) |
| 심볼 손상 | order_plans에 `{`(dict 문자열) 심볼 또는 target_price<10 이면 실패 |
| 지표 신선도 | VIX/USDKRW 최신 날짜가 7일 초과면 실패 (크라이시스 게이트 입력) |
| 지표 값 범위 | 이름별 경계(VIX 5~150, usdkrw 900~3000 등) 벗어나면 저장 거부 |

---

## 3. 킬 스위치 (Kill Switch)

**언제**: 시스템 오작동, 계좌 이상, 시장 비정상, 원인 불명 매수가 발생하면 즉시.

### 3.1 활성화 방법 (3가지 모두 동일 효과)

```bash
# 1) 파일 방식 (가장 확실)
#     trading_system/ 디렉토리에 빈 파일 생성
New-Item -ItemType File trading_system\KILL_SWITCH

# 2) 환경변수 방식 (프로세스 재시작 시 유지됨)
$env:KILL_SWITCH = "1"

# 3) 코드 내 호출
python -c "import sys; sys.path.insert(0,'trading_system'); from src.execution.kill_switch import engage; engage('사유')"
```

### 3.2 킬 스위치가 하는 일

- `ExecutionOMSEngine.generate_order_plan` → 신규 주문 계획 **전체 차단**
- `TradeExecutor.execute` → 신규 매수/매도 **전체 차단**
- 단, `force_liquidate=True`로 호출하는 **긴급 청산 매도는 허용** (포지션 정리 용도)

### 3.3 상태 확인

```bash
Get-Content trading_system\kill_switch_state.json   # engaged/disengaged + 사유 + 시각
Test-Path trading_system\KILL_SWITCH                 # 파일 존재 확인
```

### 3.4 해제

```bash
Remove-Item trading_system\KILL_SWITCH
# 또는 코드: disengage()
```

**주의**: 원인을 기록하고 해결한 뒤에만 해제할 것. 해제 후 첫 주문은 소액으로 확인.

---

## 4. 실매매 활성화 체크리스트

실거래를 시작하기 전:

- [ ] `REALTIME_TRADE_ENABLED` 가 의도적으로 `true`로 설정됐는가 (기본 false)
- [ ] `BROKER_TYPE` 이 올바른가 (`KIS` → `KOREA_INVESTMENT` 별칭, 그 외 `KIWOOM/DAISHIN/...`)
  - 잘못된 값이면 설정 로드 시점에 **명시적 오류로 즉시 종료** (조용한 기본 브로커 대체 없음)
- [ ] 브로커가 실연결(비시뮬레이션) 상태인가
- [ ] `MOCK_TRADING_ENABLED` 의도 확인
- [ ] `REALTIME_MAX_ORDER_VALUE_KRW` 상한 확인
- [ ] `KILL_SWITCH` 파일이 없어야 실거래 가능 (있으면 계획 생성 자체가 차단)
- [ ] VIX/USDKRW 지표가 최근(7일 이내)인가 — 크라이시스 게이트 입력이므로
- [ ] 통화 변환 분모(FX Denominator) 검증: US 주식 주문 시 USD 환산 단가 정상 여부
- [ ] 주문수량: KRX 10주 단위 반올림, US 1주 단위. `quantity<=0`이면 계획 자체를 생성하지 않음

---

## 5. 장애 대응

| 증상 | 1차 조치 | 2차 조치 |
|------|----------|----------|
| 예상 외 매수 주문 발생 | **킬 스위치 즉시 활성화** (3.1) | order_plans/execution_logs 조회, 포지션 청산 |
| 파이프라인 실패 (검증 raise) | 로그 확인 (`logs/pipeline.log*`) | 원인 수정 후 재실행. 실패한 날짜는 재발행하지 말 것 |
| VIX가 갑자기 100 이상 | 지표 sanity 게이트가 저장 거부(VIX 5~150) | yfinance 데이터 확인, `market_indicators` 테이블 수동 점검 |
| 추론 결과 0건 | 빈 결과 → 파이프라인 실패(의도된 동작) | 데이터 페치 실패 원인 확인 (유니버스/가격 캐시) |
| 심볼이 `{...}` 형태 | OMS 게이트가 차단 + 검증 실패 | upstream 전략(앙상블) dict 변환 버그 점검 |
| 주문 체결 안 됨 | DRY_RUN 모드인지 확인 (mode=dry_run) | 브로커 연결 상태 확인 |
| 텔레그램 알림 안 옴 | `is_enabled()`: placeholder 토큰이면 비활성으로 간주 | 실제 봇 토큰(콜론 포함) + chat_id 설정 |

---

## 6. 데이터 무결성 점검

| 점검 | 명령/방법 | 기준 |
|------|-----------|------|
| 유니버스 신선도 | `get_universe_max_age_days()` | ≤ 30일 (기본 `universe_refresh_days`) |
| 지표 최신일 | `SELECT MAX(date) FROM market_indicators WHERE name='VIX'` | 7일 이내 |
| 펀더멘탈 분기 여부 | fundamentals 테이블 `fiscal_period` | `quarterly` 우선 (annual은 fallback), 동적 Filing Lag (KRX 45d, US 40d) 적용 |
| 가격 조정 컨벤션 | Tier1(yfinance)=조정, Tier2~4=비조정 → 분할 역조정 적용됨 | 최근 가격 수준 보존 |
| order_plans 수량 | `SELECT symbol, quantity, target_amount, target_price FROM order_plans` | KRX 10주 배수, US 1주 |

---

## 7. 상태 파일 / DB 위치

| 항목 | 경로 |
|------|------|
| 킬 스위치 파일 | `trading_system/KILL_SWITCH` |
| 킬 스위치 상태 | `trading_system/kill_switch_state.json` |
| 거래 로그 | `trading_system/trade_logs.db` (`order_plans`, `execution_logs`) |
| 지표 DB | `trading_system/market_indicators.db` |
| 주가 DB | `trading_system/stock_prices.db` |
| 파이프라인 로그 | `trading_system/logs/pipeline.log*` |
