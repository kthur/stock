"""
텔레그램 봇 - 트레이딩 시스템 모니터링 및 제어

===========================================
텔레그램 봇 통합 가이드
===========================================

## 1. 개요
==================

텔레그램 봇을 통해 트레이딩 시스템을 언제 어디서나 모니터링하고 제어할 수 있습니다.

**주요 기능:**
- 📊 포트폴리오 실시간 모니터링
- 💡 주식 분석 및 AI 의견 조회
- 💼 주문 접수 및 취소
- 🏦 다중 증권사 관리
- ⚠️ 거래 알림 (손절매, 익절매 등)
- 📈 일일 거래 보고서


## 2. 설정 방법
================

### 2.1 텔레그램 봇 생성

1. 텔레그램에서 **@BotFather** 검색
2. `/start` 입력
3. `/newbot` 명령 실행
4. 봇 이름 입력 (예: Trading Bot)
5. 봇 사용자명 입력 (예: trading_bot)
6. **API 토큰 받기** 및 저장

예:
```
6123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2.2 환경변수 설정

```bash
export TELEGRAM_BOT_TOKEN="6123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

또는 `.env` 파일에 추가:
```
TELEGRAM_BOT_TOKEN=6123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2.3 Python 의존성 설치

```bash
pip install python-telegram-bot
```

### 2.4 봇 시작

```python
from trading_system import StockTradingSystem

system = StockTradingSystem()
system.start_telegram_bot()

# 메시지 처리
response = system.process_telegram_message(user_id, "/status")
```


## 3. 명령어 가이드
===================

### 상태 조회

#### /status
현재 거래 상태 조회
```
/status
```
응답:
```
📊 *현재 거래 상태*
💰 현금: $1,000,000
📈 포지션: 0개
⏳ 미체결 주문: 0개
📝 총 거래: 0건
```

#### /portfolio
포트폴리오 조회
```
/portfolio
```

#### /positions
보유 포지션 상세 조회
```
/positions
```

#### /orders
미체결 주문 현황
```
/orders
```

#### /brokers
연결된 증권사 상태
```
/brokers
```

#### /risk
위험 관리 현황
```
/risk
```

### 분석 및 정보

#### /analyze [SYMBOL]
특정 주식 분석
```
/analyze AAPL
```
응답:
```
🔍 *AAPL 분석*
현재가: $150.00
변동률: ↑ 1.5%

💡 AI 분석:
  추천: 🟢 매수
  신뢰도: 85%
  목표가: $165

👥 투자자 의견:
  • 워렌 버펫: 보유
  • 성장투자: 매수
  • 모멘텀: 보유
```

#### /news
시장 뉴스 및 정보
```
/news
```

### 거래

#### /buy SYMBOL QUANTITY PRICE
매수 주문
```
/buy AAPL 10 150
```
응답:
```
✅ *매수 주문 접수*
종목: AAPL
수량: 10주
가격: $150.00
주문번호: ORD_123456789
상태: 접수됨
```

#### /sell SYMBOL QUANTITY PRICE
매도 주문
```
/sell MSFT 5 320
```

#### /cancel ORDER_ID
주문 취소
```
/cancel ORD_123456789
```

### 증권사 관리

#### /connect BROKER ACCOUNT
증권사 연결
```
/connect kiwoom 1234567890
/connect daishin 0987654321
/connect hanwha 5555555555
```

### 기타

#### /help
전체 명령어 도움말
```
/help
```

#### /start
시작 메시지
```
/start
```


## 4. 알림 (Notifications)
==========================

시스템이 자동으로 발생하는 이벤트에 대해 텔레그램으로 알립니다.

### 주문 알림
- 📝 주문 접수
- ✅ 주문 체결
- ❌ 주문 취소

### 거래 알림
- ⚠️ 손절매 발동
- 🎯 익절매 발동
- 🔔 일반 알림

### 예시
```
✅ 주문 체결: AAPL 10주 @ $152.50
⚠️ 손절매: MSFT @ $300.00
🎯 익절매: GOOGL @ $290.00
```


## 5. 일일 보고서
===================

매일 정해진 시간에 자동으로 거래 보고서를 전송합니다.

### 보고서 내용

```
📊 *일일 거래 보고서*

📅 날짜: 2026-06-01 09:00:00
💰 현금: $1,000,000
📈 포지션: 3개
✅ 완료된 거래: 5건
📊 수익률: +2.5%
```

### 수동으로 보고서 조회

```python
report = system.get_telegram_daily_report(user_id)
```


## 6. 봇 통계
==============

```python
stats = system.get_telegram_bot_stats()

# 결과:
{
    'is_running': True,
    'subscribed_users': 5,
    'total_commands': 150,
    'users': {...},
    'recent_commands': [...]
}
```


## 7. 실제 구현 예시
====================

### 예시 1: 시스템 시작 및 봇 연동

```python
from trading_system import StockTradingSystem
import os

# 환경변수에서 토큰 로드
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

# 시스템 초기화
system = StockTradingSystem(initial_cash=1000000)

# 봇 시작
system.start_telegram_bot()

# 사용자 메시지 처리
def on_telegram_message(user_id, message):
    response = system.process_telegram_message(user_id, message)
    # send_telegram_message(user_id, response)  # 실제 전송

on_telegram_message(123456789, "/status")
on_telegram_message(123456789, "/analyze AAPL")
on_telegram_message(123456789, "/buy AAPL 10 150")
```

### 예시 2: 자동 알림

```python
# 주문 체결 이벤트
system.send_telegram_notification(
    user_id=123456789,
    event_type="order_filled",
    data={'symbol': 'AAPL', 'quantity': 10, 'price': 152.50}
)

# 손절매 이벤트
system.send_telegram_notification(
    user_id=123456789,
    event_type="stop_loss",
    data={'symbol': 'MSFT', 'price': 300.00}
)
```

### 예시 3: 일일 보고서

```python
# 정기 보고서 생성
report = system.get_telegram_daily_report(user_id=123456789)
# send_telegram_message(123456789, report)  # 실제 전송
```


## 8. 고급 기능
================

### 다중 사용자 지원

```python
users = [123456789, 987654321, 555555555]

for user_id in users:
    status = system.process_telegram_message(user_id, "/status")
    # send_telegram_message(user_id, status)
```

### 명령어 히스토리

```python
stats = system.get_telegram_bot_stats()
for cmd in stats['recent_commands']:
    print(f"{cmd['command']} by user {cmd['user_id']}")
```

### 봇 상태 확인

```python
stats = system.get_telegram_bot_stats()
print(f"봇 상태: {'실행 중' if stats['is_running'] else '중지됨'}")
print(f"등록 사용자: {stats['subscribed_users']}명")
print(f"총 명령: {stats['total_commands']}건")
```


## 9. 트러블슈팅
=================

### 문제: "TELEGRAM_BOT_TOKEN not set"

**해결책:**
1. 환경변수 확인: `echo $TELEGRAM_BOT_TOKEN`
2. 토큰 설정: `export TELEGRAM_BOT_TOKEN="..."`
3. 또는 코드에서 직접 설정:
   ```python
   bot = TelegramBotEngine(api_token="your_token_here")
   ```

### 문제: 봇이 시뮬레이션 모드에서 실행됨

**원인:** TELEGRAM_BOT_TOKEN이 설정되지 않음

**해결책:** 환경변수 설정 후 봇 재시작

### 문제: 명령어 인식 안 됨

**확인사항:**
1. 명령어 철자 확인
2. 인수 개수 확인 (예: `/buy AAPL 10 150`)
3. `/help` 명령어로 사용 가능한 명령어 확인


## 10. 파일 구조
===================

```
src/telegram_bot/
├── __init__.py
└── bot_engine.py (TelegramBotEngine 클래스)

trading_system.py (Telegram Bot 메서드 추가)

demo_telegram.py (데모)
```

## 11. 향후 개선 사항
=======================

- [ ] 실시간 마켓 데이터 프로셔 연동
- [ ] 음성 명령 지원
- [ ] 그래프 및 차트 전송
- [ ] 알람 시간 커스터마이징
- [ ] 포트폴리오 성과 분석 그래프
- [ ] 메시지 반응 (마크업 버튼)
- [ ] 여러 언어 지원
- [ ] 웹훅 지원 (더 빠른 응답)

"""
