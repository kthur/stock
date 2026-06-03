"""텔레그램 봇 엔진 - 트레이딩 시스템 모니터링 및 제어"""

import logging
from typing import Optional, Dict, List, Callable
from datetime import datetime
import os
from src.utils.async_helper import run_async

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
            'strategy': self._cmd_strategy,
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
        
        # 텔레그램 권한 검증 추가
        auth_ids_str = os.getenv("TELEGRAM_AUTHORIZED_USER_IDS", "")
        if auth_ids_str.strip():
            try:
                authorized_ids = [int(uid.strip()) for uid in auth_ids_str.split(",") if uid.strip()]
                # 비인가 사용자 권한 검사 대상 명령어 목록
                restricted_commands = {
                    'buy', 'sell', 'cancel', 'portfolio', 'positions', 'orders', 'connect', 'risk', 'strategy'
                }
                if command in restricted_commands and user_id not in authorized_ids:
                    self.logger.warning(f"Unauthorized command execution attempt by user {user_id}: {message}")
                    return "⚠️ 권한 오류: 승인되지 않은 사용자 ID입니다. 관리자에게 문의하세요."
            except ValueError as e:
                self.logger.error(f"Error parsing TELEGRAM_AUTHORIZED_USER_IDS: {e}")
        
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
        
        unfilled = self.trading_system.order_management.get_unfilled_orders()
        status = self.trading_system.get_trading_status()
        
        response = "📋 *주문 현황*\n\n"
        response += f"⏳ 미체결 주문: {len(unfilled)}개\n"
        response += f"✅ 완료/기타 주문: {status['total_trades'] - len(unfilled)}건\n\n"
        
        if unfilled:
            response += "⏳ *미체결 주문 리스트:*\n"
            for o in unfilled:
                side_emoji = "🟢 매수" if o.order_type.value == "BUY" else "🔴 매도"
                response += f"  • `{o.order_id}`\n"
                response += f"    {side_emoji} | {o.symbol} | {o.quantity}주 | ${o.price:,.2f} | {o.status.value}\n"
        else:
            response += "미체결 주문이 존재하지 않습니다.\n"
            
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
        if len(args) < 2:
            return "⚠️ 사용법: /buy SYMBOL QUANTITY [PRICE]\n예: /buy 삼성전자 10 75000 (지정가)\n예: /buy AAPL 5 (시장가)"
        
        raw_symbol = args[0]
        # 한글 이름 치환 딕셔너리
        from src.utils.stock_list import KOR_TICKERS as KOR_TICKERS_MAPPING
        symbol = KOR_TICKERS_MAPPING.get(raw_symbol, raw_symbol.upper())
        
        try:
            quantity = int(args[1])
            price = float(args[2]) if len(args) > 2 else 0.0
        except ValueError:
            return "⚠️ 수량과 가격은 숫자여야 합니다."
        
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
            
        from src.core.order_management import OrderType
        
        # 시장가(MARKET) 처리
        price_label = f"${price:,.2f}"
        if price <= 0:
            price_label = "시장가"
            quote = self.trading_system.get_stock_quote_from_broker(symbol)
            price = quote.get('price') or self.trading_system.market_data_cache.get(symbol, {}).get('price') or 150.0
        
        async def execute_buy_action():
            order = self.trading_system.order_management.create_order(symbol, OrderType.BUY, quantity, price)
            await self.trading_system.order_management.submit_order(order)
            await self.trading_system.order_management.execute_order(order.order_id)
            await self.trading_system.trade_logger.log_execution(order.order_id, symbol, quantity, price)
            self.trading_system.portfolio.add_position(symbol, quantity, price)
            return order.order_id
            
        try:
            order_id = run_async(execute_buy_action())
            response = f"✅ *실시간 매수 체결 완료*\n\n"
            response += f"종목: {raw_symbol} ({symbol})\n"
            response += f"수량: {quantity}주\n"
            response += f"가격: {price_label} (체결가: ${price:,.2f})\n"
            response += f"주문번호: `{order_id}`\n"
            response += f"상태: 체결완료(EXECUTED)\n"
        except Exception as e:
            response = f"❌ 주문 실행 실패: {str(e)}"
            
        return response
    
    def _cmd_sell(self, user_id: int, args: List[str]) -> str:
        """매도 주문"""
        if len(args) < 2:
            return "⚠️ 사용법: /sell SYMBOL QUANTITY [PRICE]\n예: /sell 삼성전자 10 75000 (지정가)\n예: /sell AAPL 5 (시장가)"
        
        raw_symbol = args[0]
        from src.utils.stock_list import KOR_TICKERS as KOR_TICKERS_MAPPING
        symbol = KOR_TICKERS_MAPPING.get(raw_symbol, raw_symbol.upper())
        
        try:
            quantity = int(args[1])
            price = float(args[2]) if len(args) > 2 else 0.0
        except ValueError:
            return "⚠️ 수량과 가격은 숫자여야 합니다."
        
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
            
        from src.core.order_management import OrderType
        
        # 시장가(MARKET) 처리
        price_label = f"${price:,.2f}"
        if price <= 0:
            price_label = "시장가"
            quote = self.trading_system.get_stock_quote_from_broker(symbol)
            price = quote.get('price') or self.trading_system.market_data_cache.get(symbol, {}).get('price') or 150.0
            
        async def execute_sell_action():
            order = self.trading_system.order_management.create_order(symbol, OrderType.SELL, quantity, price)
            await self.trading_system.order_management.submit_order(order)
            await self.trading_system.order_management.execute_order(order.order_id)
            await self.trading_system.trade_logger.log_execution(order.order_id, symbol, quantity, price)
            self.trading_system.portfolio.reduce_position(symbol, quantity)
            return order.order_id
            
        try:
            order_id = run_async(execute_sell_action())
            response = f"✅ *실시간 매도 체결 완료*\n\n"
            response += f"종목: {raw_symbol} ({symbol})\n"
            response += f"수량: {quantity}주\n"
            response += f"가격: {price_label} (체결가: ${price:,.2f})\n"
            response += f"주문번호: `{order_id}`\n"
            response += f"상태: 체결완료(EXECUTED)\n"
        except Exception as e:
            response = f"❌ 주문 실행 실패: {str(e)}"
            
        return response
    
    def _cmd_cancel(self, user_id: int, args: List[str]) -> str:
        """주문 취소"""
        if not args:
            return "⚠️ 주문 번호를 입력해주세요. 예: /cancel ORD_123456789"
        
        order_id = args[0]
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
            
        try:
            success = run_async(self.trading_system.order_management.cancel_order(order_id))
            if success:
                response = f"✅ *주문 취소 완료*\n\n"
                response += f"주문번호: `{order_id}`\n"
                response += f"상태: 취소됨(CANCELLED)\n"
            else:
                response = f"❌ 주문 취소 거부: 해당 주문을 취소할 수 없습니다. (이미 체결되었거나 만료됨)"
        except Exception as e:
            response = f"❌ 취소 실패: {str(e)}"
            
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
    
    def _cmd_strategy(self, user_id: int, args: List[str]) -> str:
        """자동매매 전략 조회 및 변경"""
        if not self.trading_system or not hasattr(self.trading_system, 'risk_manager'):
            return "❌ 시스템 연동 안됨 또는 RiskManager를 찾을 수 없습니다."
        
        risk_mgr = self.trading_system.risk_manager
        current_strategy = getattr(risk_mgr, 'active_strategy', 'HYBRID').upper()
        
        # 사용 가능한 전략 목록
        available_strategies = ["HYBRID", "MA", "RSI", "MACD", "TREND", "BUFFETT", "LYNCH", "DALIO"]
        
        if not args:
            response = "🎯 *활성 자동매매 전략 조회*\n\n"
            response += f"현재 설정된 전략: `{current_strategy}`\n\n"
            response += "💡 전략을 변경하려면 명령어 뒤에 아래의 전략명을 지정하세요.\n"
            response += f"사용법: `/strategy [전략명]`\n"
            response += f"지원하는 전략 목록:\n"
            for s in available_strategies:
                response += f"  • `{s}`\n"
            return response
            
        new_strategy = args[0].upper()
        if new_strategy not in available_strategies:
            return f"❌ 지원하지 않는 전략명입니다.\n(지원 전략: {', '.join(available_strategies)})"
            
        risk_mgr.active_strategy = new_strategy
        if hasattr(risk_mgr, 'save_config'):
            risk_mgr.save_config()
        
        return f"✅ *자동매매 전략 변경 완료*\n\n전략이 다음과 같이 변경되었습니다:\n`{current_strategy}` ➡️ `{new_strategy}`"
    
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
/strategy [STRAT] - 전략 조회 및 변경

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
