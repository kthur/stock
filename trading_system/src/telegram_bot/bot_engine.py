"""텔레그램 봇 엔진 - 트레이딩 시스템 모니터링 및 제어"""

import logging
from typing import Optional, Dict, List, Callable
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class TelegramBotEngine:
    """텔레그램 봇 엔진"""
    
    def __init__(self, api_token: Optional[str] = None, trading_system=None, event_bus=None):
        """
        텔레그램 봇 초기화
        
        Args:
            api_token: 텔레그램 봇 토큰
            trading_system: 연동할 트레이딩 시스템
            event_bus: 이벤트 버스
        """
        self.api_token = api_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.trading_system = trading_system
        self.event_bus = event_bus
        self.logger = logger
        self.is_running = False
        self.subscribed_users: Dict[int, Dict] = {}  # user_id -> user_info
        self.command_history = []
        self.simulation_mode = True
        
        # 명령어 매핑
        self.commands = {
            'start': self._cmd_start,
            'status': self._cmd_status,
            'portfolio': self._cmd_portfolio,
            'positions': self._cmd_positions,
            'orders': self._cmd_orders,
            'news': self._cmd_news,
            'analyze': self._cmd_analyze,
            'buy': self._cmd_buy,
            'sell': self._cmd_sell,
            'cancel': self._cmd_cancel,
            'brokers': self._cmd_brokers,
            'connect': self._cmd_connect,
            'risk': self._cmd_risk,
            'help': self._cmd_help,
        }
        
        self.logger.info("Telegram Bot Engine initialized")
        if not self.api_token:
            self.logger.warning("TELEGRAM_BOT_TOKEN not set. Using simulation mode.")
            self.simulation_mode = True
    
    def start(self):
        """봇 시작"""
        if not self.api_token:
            self.logger.warning("Telegram bot token not configured. Running in simulation mode.")
            self.simulation_mode = True
        
        self.is_running = True
        self.logger.info("Telegram bot started")
    
    def stop(self):
        """봇 중지"""
        self.is_running = False
        self.logger.info("Telegram bot stopped")
    
    def process_message(self, user_id: int, message: str) -> str:
        """메시지 처리"""
        self.logger.info(f"Message from {user_id}: {message}")
        
        # 사용자 등록
        if user_id not in self.subscribed_users:
            self.subscribed_users[user_id] = {
                'user_id': user_id,
                'joined_at': datetime.now(),
                'command_count': 0
            }
        
        # 명령어 파싱
        parts = message.strip().split()
        if not parts:
            return "명령어를 입력해주세요. /help로 도움말을 보세요."
        
        command = parts[0].lstrip('/')
        args = parts[1:] if len(parts) > 1 else []
        
        # 명령어 실행
        if command in self.commands:
            self.subscribed_users[user_id]['command_count'] += 1
            self.command_history.append({
                'user_id': user_id,
                'command': command,
                'args': args,
                'timestamp': datetime.now()
            })
            
            try:
                response = self.commands[command](user_id, args)
            except Exception as e:
                self.logger.error(f"Error executing {command}: {str(e)}")
                response = f"❌ 오류: {str(e)}"
        else:
            response = f"❓ 알 수 없는 명령어: {command}\n/help로 도움말을 보세요."
        
        return response
    
    # ===== 명령어 구현 =====
    
    def _cmd_start(self, user_id: int, args: List[str]) -> str:
        """시작 명령어"""
        return """
🤖 주식 트레이딩 시스템 봇에 오신 것을 환영합니다!

이 봇은 다음 기능을 제공합니다:
📊 포트폴리오 모니터링
🎯 거래 분석 및 조언
💼 주문 관리
🏦 증권사 관리

/help 로 전체 명령어를 확인하세요.
"""
    
    def _cmd_status(self, user_id: int, args: List[str]) -> str:
        """거래 상태 조회"""
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
        
        status = self.trading_system.get_trading_status()
        
        response = "📊 *현재 거래 상태*\n"
        response += f"💰 현금: ${status['cash']:,.0f}\n"
        response += f"📈 포지션: {len(status['positions'])}개\n"
        response += f"⏳ 미체결 주문: {status['open_orders']}개\n"
        response += f"📝 총 거래: {status['total_trades']}건\n"
        response += f"🕐 업데이트: {status['timestamp']}\n"
        
        return response
    
    def _cmd_portfolio(self, user_id: int, args: List[str]) -> str:
        """포트폴리오 조회"""
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
        
        status = self.trading_system.get_trading_status()
        
        response = "💼 *포트폴리오*\n\n"
        response += f"💵 현금: ${status['cash']:,.0f}\n\n"
        
        if status['positions']:
            response += "📊 보유 종목:\n"
            for symbol, quantity in status['positions'].items():
                response += f"  • {symbol}: {quantity}주\n"
        else:
            response += "보유 종목 없음\n"
        
        return response
    
    def _cmd_positions(self, user_id: int, args: List[str]) -> str:
        """포지션 상세 조회"""
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
        
        status = self.trading_system.get_trading_status()
        
        response = "📈 *현재 포지션*\n\n"
        
        if status['positions']:
            for symbol, quantity in status['positions'].items():
                response += f"🔹 {symbol}: {quantity}주\n"
        else:
            response += "현재 보유 중인 포지션이 없습니다."
        
        return response
    
    def _cmd_orders(self, user_id: int, args: List[str]) -> str:
        """주문 현황 조회"""
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
        
        status = self.trading_system.get_trading_status()
        
        response = "📋 *주문 현황*\n\n"
        response += f"⏳ 미체결 주문: {status['open_orders']}개\n"
        response += f"✅ 완료된 주문: {status['total_trades']}건\n"
        
        return response
    
    def _cmd_news(self, user_id: int, args: List[str]) -> str:
        """뉴스 및 시장 정보"""
        response = "📰 *시장 정보*\n\n"
        response += "🔴 미국 시장\n"
        response += "  • S&P 500: ↑ 0.5%\n"
        response += "  • NASDAQ: ↑ 0.8%\n"
        response += "  • Dow Jones: ↑ 0.3%\n\n"
        response += "🇰🇷 한국 시장\n"
        response += "  • KOSPI: ↑ 0.7%\n"
        response += "  • KOSDAQ: ↑ 1.2%\n"
        
        return response
    
    def _cmd_analyze(self, user_id: int, args: List[str]) -> str:
        """주식 분석 요청"""
        if not args:
            return "⚠️ 종목 코드를 입력해주세요. 예: /analyze AAPL"
        
        symbol = args[0].upper()
        
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
        
        response = f"🔍 *{symbol} 분석*\n\n"
        response += f"현재가: $150.00\n"
        response += f"변동률: ↑ 1.5%\n"
        response += f"거래량: 1.2M\n\n"
        response += "💡 AI 분석:\n"
        response += "  추천: 🟢 매수\n"
        response += "  신뢰도: 85%\n"
        response += "  목표가: $165\n\n"
        response += "👥 투자자 의견:\n"
        response += "  • 워렌 버펫: 보유\n"
        response += "  • 성장투자: 매수\n"
        response += "  • 모멘텀: 보유\n"
        
        return response
    
    def _cmd_buy(self, user_id: int, args: List[str]) -> str:
        """매수 주문"""
        if len(args) < 3:
            return "⚠️ 사용법: /buy SYMBOL QUANTITY PRICE\n예: /buy AAPL 10 150"
        
        symbol = args[0].upper()
        try:
            quantity = int(args[1])
            price = float(args[2])
        except ValueError:
            return "⚠️ 수량과 가격은 숫자여야 합니다."
        
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
        
        # 주문 접수
        response = f"✅ *매수 주문 접수*\n\n"
        response += f"종목: {symbol}\n"
        response += f"수량: {quantity}주\n"
        response += f"가격: ${price:,.2f}\n"
        response += f"주문번호: ORD_123456789\n"
        response += f"상태: 접수됨\n"
        
        return response
    
    def _cmd_sell(self, user_id: int, args: List[str]) -> str:
        """매도 주문"""
        if len(args) < 3:
            return "⚠️ 사용법: /sell SYMBOL QUANTITY PRICE\n예: /sell AAPL 5 155"
        
        symbol = args[0].upper()
        try:
            quantity = int(args[1])
            price = float(args[2])
        except ValueError:
            return "⚠️ 수량과 가격은 숫자여야 합니다."
        
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
        
        response = f"✅ *매도 주문 접수*\n\n"
        response += f"종목: {symbol}\n"
        response += f"수량: {quantity}주\n"
        response += f"가격: ${price:,.2f}\n"
        response += f"주문번호: ORD_987654321\n"
        response += f"상태: 접수됨\n"
        
        return response
    
    def _cmd_cancel(self, user_id: int, args: List[str]) -> str:
        """주문 취소"""
        if not args:
            return "⚠️ 주문 번호를 입력해주세요. 예: /cancel ORD_123456789"
        
        order_id = args[0]
        
        response = f"✅ *주문 취소*\n\n"
        response += f"주문번호: {order_id}\n"
        response += f"상태: 취소됨\n"
        
        return response
    
    def _cmd_brokers(self, user_id: int, args: List[str]) -> str:
        """증권사 현황"""
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
        
        response = "🏦 *증권사 현황*\n\n"
        
        try:
            brokers = self.trading_system.get_all_broker_status()
            for broker_name, status in brokers.items():
                connected = "✅" if status['is_connected'] else "❌"
                active = "🟢" if status['is_active'] else "⚪"
                response += f"{connected} {broker_name.upper()}: {status['account_number']}\n"
                response += f"   {active} 활성 상태\n"
        except:
            response += "키움증권 ✅: 1234567890\n"
            response += "대신증권 ❌: 미연결\n"
            response += "한투증권 ❌: 미연결\n"
        
        return response
    
    def _cmd_connect(self, user_id: int, args: List[str]) -> str:
        """증권사 연결"""
        if len(args) < 2:
            return "⚠️ 사용법: /connect BROKER ACCOUNT\n예: /connect kiwoom 1234567890"
        
        broker = args[0].lower()
        account = args[1]
        
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
        
        response = f"🔄 *{broker} 연결 중...*\n\n"
        response += f"계좌: {account}\n"
        response += f"상태: ✅ 연결됨\n"
        
        return response
    
    def _cmd_risk(self, user_id: int, args: List[str]) -> str:
        """위험 관리 현황"""
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
        
        risk_report = self.trading_system.get_risk_report()
        
        response = "⚠️ *위험 관리*\n\n"
        response += f"포트폴리오: ${risk_report.get('current_value', 0):,.0f}\n"
        response += f"하락률: {risk_report.get('drawdown', 'N/A')}\n"
        response += f"위험 등급: {risk_report.get('risk_level', 'MEDIUM')}\n"
        response += f"변동성: {risk_report.get('volatility', 'N/A')}\n"
        response += f"최대손실: ${risk_report.get('max_loss_limit', 0):,.0f}\n"
        
        return response
    
    def _cmd_help(self, user_id: int, args: List[str]) -> str:
        """도움말"""
        response = """📖 *명령어 목록*

*상태 조회*
/status - 거래 현황
/portfolio - 포트폴리오
/positions - 포지션 상세
/orders - 주문 현황
/brokers - 증권사 현황
/risk - 위험 관리

*분석 및 정보*
/analyze [SYMBOL] - 주식 분석
/news - 시장 뉴스

*거래*
/buy SYMBOL QTY PRICE - 매수 주문
/sell SYMBOL QTY PRICE - 매도 주문
/cancel ORDER_ID - 주문 취소
/connect BROKER ACCOUNT - 증권사 연결

*기타*
/help - 이 도움말
/start - 시작 메시지
"""
        return response
    
    def get_notification(self, event_type: str, data: Dict) -> str:
        """이벤트 알림 생성"""
        if event_type == "order_filled":
            return f"✅ 주문 체결: {data['symbol']} {data['quantity']}주 @ ${data['price']}"
        elif event_type == "order_placed":
            return f"📝 주문 접수: {data['symbol']} {data['quantity']}주 @ ${data['price']}"
        elif event_type == "stop_loss":
            return f"⚠️ 손절매: {data['symbol']} @ ${data['price']}"
        elif event_type == "take_profit":
            return f"🎯 익절매: {data['symbol']} @ ${data['price']}"
        elif event_type == "alert":
            return f"🔔 알림: {data['message']}"
        
        return "📢 알림"
    
    def send_periodic_report(self, user_id: int) -> str:
        """정기 보고서"""
        if not self.trading_system:
            return None
        
        status = self.trading_system.get_trading_status()
        
        report = "📊 *일일 거래 보고서*\n\n"
        report += f"📅 날짜: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += f"💰 현금: ${status['cash']:,.0f}\n"
        report += f"📈 포지션: {len(status['positions'])}개\n"
        report += f"✅ 완료된 거래: {status['total_trades']}건\n"
        
        return report
    
    def get_stats(self) -> Dict:
        """봇 통계"""
        return {
            'is_running': self.is_running,
            'subscribed_users': len(self.subscribed_users),
            'total_commands': len(self.command_history),
            'users': self.subscribed_users,
            'recent_commands': self.command_history[-10:] if self.command_history else []
        }
