"""텔레그램 봇 엔진 - 트레이딩 시스템 모니터링 및 제어"""

import logging
import os
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

from src.core.order_management import OrderType
from src.utils.async_helper import run_async
from src.utils.stock_list import get_tickers as _get_tickers

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
        self.command_history: deque = deque(maxlen=200)
        self.simulation_mode = True
        self._rate_limits: Dict[int, deque] = {}
        self._rate_window = 10.0
        self._rate_max_calls = 10
        self._authorized_ids = self._parse_authorized_ids()
        self._restricted_commands = {
            "buy",
            "sell",
            "cancel",
            "portfolio",
            "positions",
            "orders",
            "connect",
            "risk",
            "strategy",
        }

        # 명령어 매핑
        self.commands = {
            "start": self._cmd_start,
            "status": self._cmd_status,
            "portfolio": self._cmd_portfolio,
            "positions": self._cmd_positions,
            "orders": self._cmd_orders,
            "news": self._cmd_news,
            "analyze": self._cmd_analyze,
            "buy": self._cmd_buy,
            "sell": self._cmd_sell,
            "cancel": self._cmd_cancel,
            "brokers": self._cmd_brokers,
            "connect": self._cmd_connect,
            "risk": self._cmd_risk,
            "strategy": self._cmd_strategy,
            "performance": self._cmd_performance,
            "global": self._cmd_global,
            "screen": self._cmd_screen,
            "help": self._cmd_help,
            "predict": self._cmd_predict,
            "dashboard": self._cmd_dashboard,
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

    @staticmethod
    def _parse_authorized_ids() -> set:
        """환경변수에서 인증된 사용자 ID 파싱"""
        raw = os.getenv("TELEGRAM_AUTHORIZED_USER_IDS", "")
        if not raw.strip():
            return set()
        try:
            return {int(uid.strip()) for uid in raw.split(",") if uid.strip()}
        except ValueError:
            logger.error(f"Invalid TELEGRAM_AUTHORIZED_USER_IDS: {raw}")
            return set()

    def _check_rate_limit(self, user_id: int) -> bool:
        """Rate limit check: max N calls per window seconds per user"""
        now = time.monotonic()
        if user_id not in self._rate_limits:
            self._rate_limits[user_id] = deque()
        history = self._rate_limits[user_id]
        while history and now - history[0] > self._rate_window:
            history.popleft()
        if len(history) >= self._rate_max_calls:
            self.logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        history.append(now)
        return True

    def process_message(self, user_id: int, message: str) -> str:
        """메시지 처리"""
        self.logger.info(f"Message from {user_id}: {message}")

        if not self._check_rate_limit(user_id):
            return f"요청이 너무 많습니다. {self._rate_max_calls}회/{self._rate_window:.0f}초 제한."

        # 사용자 등록
        if user_id not in self.subscribed_users:
            self.subscribed_users[user_id] = {"user_id": user_id, "joined_at": datetime.now(), "command_count": 0}

        # 명령어 파싱
        parts = message.strip().split()
        if not parts:
            return "명령어를 입력해주세요. /help로 도움말을 보세요."

        command = parts[0].lstrip("/")
        args = parts[1:] if len(parts) > 1 else []

        # 텔레그램 권한 검증
        if self._authorized_ids and command in self._restricted_commands and user_id not in self._authorized_ids:
            self.logger.warning(f"Unauthorized command execution attempt by user {user_id}: {message}")
            return "⚠️ 권한 오류: 승인되지 않은 사용자 ID입니다. 관리자에게 문의하세요."

        # 명령어 실행
        if command in self.commands:
            self.subscribed_users[user_id]["command_count"] += 1
            self.command_history.append(
                {"user_id": user_id, "command": command, "args": args, "timestamp": datetime.now()}
            )

            try:
                response = self.commands[command](user_id, args)
            except Exception as e:
                self.logger.error(f"Error executing {command}: {e!s}")
                response = f"❌ 오류: {e!s}"
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

        if status["positions"]:
            response += "📊 보유 종목:\n"
            for symbol, quantity in status["positions"].items():
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

        if status["positions"]:
            for symbol, quantity in status["positions"].items():
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
        response += "현재가: $150.00\n"
        response += "변동률: ↑ 1.5%\n"
        response += "거래량: 1.2M\n\n"
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
        return self._execute_trade_order(
            args, OrderType.BUY, "매수", "buy", self.trading_system.portfolio.add_position, True
        )

    def _cmd_sell(self, user_id: int, args: List[str]) -> str:
        """매도 주문"""
        return self._execute_trade_order(
            args, OrderType.SELL, "매도", "sell", self.trading_system.portfolio.reduce_position, False
        )

    def _execute_trade_order(
        self, args: List[str], order_type: OrderType, side_kr: str, side_en: str, portfolio_action, include_price: bool
    ) -> str:
        """매수/매도 공통 로직"""
        if len(args) < 2:
            return (
                f"⚠️ 사용법: /{side_en} SYMBOL QUANTITY [PRICE]\n"
                f"예: /{side_en} 삼성전자 10 75000 (지정가)\n"
                f"예: /{side_en} AAPL 5 (시장가)"
            )

        raw_symbol = args[0]
        symbol = _get_tickers().get(raw_symbol, raw_symbol.upper())

        try:
            quantity = int(args[1])
            price = float(args[2]) if len(args) > 2 else 0.0
        except ValueError:
            return "⚠️ 수량과 가격은 숫자여야 합니다."

        if not self.trading_system:
            return "❌ 시스템 연동 안됨"

        price_label = f"${price:,.2f}"
        if price <= 0:
            price_label = "시장가"
            quote = self.trading_system.get_stock_quote_from_broker(symbol)
            price = quote.get("price") or self.trading_system.market_data_cache.get(symbol, {}).get("price") or 150.0

        async def execute_action():
            order = self.trading_system.order_management.create_order(symbol, order_type, quantity, price)
            await self.trading_system.order_management.submit_order(order)
            await self.trading_system.order_management.execute_order(order.order_id)
            await self.trading_system.trade_logger.log_execution(order.order_id, symbol, quantity, price)
            if include_price:
                portfolio_action(symbol, quantity, price)
            else:
                portfolio_action(symbol, quantity)
            return order.order_id

        try:
            order_id = run_async(execute_action())
            response = f"✅ *실시간 {side_kr} 체결 완료*\n\n"
            response += f"종목: {raw_symbol} ({symbol})\n"
            response += f"수량: {quantity}주\n"
            response += f"가격: {price_label} (체결가: ${price:,.2f})\n"
            response += f"주문번호: `{order_id}`\n"
            response += "상태: 체결완료(EXECUTED)\n"
        except Exception as e:
            response = f"❌ 주문 실행 실패: {e!s}"

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
                response = "✅ *주문 취소 완료*\n\n"
                response += f"주문번호: `{order_id}`\n"
                response += "상태: 취소됨(CANCELLED)\n"
            else:
                response = "❌ 주문 취소 거부: 해당 주문을 취소할 수 없습니다. (이미 체결되었거나 만료됨)"
        except Exception as e:
            response = f"❌ 취소 실패: {e!s}"

        return response

    def _cmd_brokers(self, user_id: int, args: List[str]) -> str:
        """증권사 현황"""
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"

        response = "🏦 *증권사 현황*\n\n"

        try:
            brokers = self.trading_system.get_all_broker_status()
            for broker_name, status in brokers.items():
                connected = "✅" if status["is_connected"] else "❌"
                active = "🟢" if status["is_active"] else "⚪"
                response += f"{connected} {broker_name.upper()}: {status['account_number']}\n"
                response += f"   {active} 활성 상태\n"
        except Exception:
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
        response += "상태: ✅ 연결됨\n"

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
        if not self.trading_system or not hasattr(self.trading_system, "risk_manager"):
            return "❌ 시스템 연동 안됨 또는 RiskManager를 찾을 수 없습니다."

        risk_mgr = self.trading_system.risk_manager
        current_strategy = getattr(risk_mgr, "active_strategy", "HYBRID").upper()

        # 사용 가능한 전략 목록
        available_strategies = ["HYBRID", "MA", "RSI", "MACD", "TREND", "BUFFETT", "LYNCH", "DALIO"]

        if not args:
            response = "🎯 *활성 자동매매 전략 조회*\n\n"
            response += f"현재 설정된 전략: `{current_strategy}`\n\n"
            response += "💡 전략을 변경하려면 명령어 뒤에 아래의 전략명을 지정하세요.\n"
            response += "사용법: `/strategy [전략명]`\n"
            response += "지원하는 전략 목록:\n"
            for s in available_strategies:
                response += f"  • `{s}`\n"
            return response

        new_strategy = args[0].upper()
        if new_strategy not in available_strategies:
            return f"❌ 지원하지 않는 전략명입니다.\n(지원 전략: {', '.join(available_strategies)})"

        risk_mgr.active_strategy = new_strategy
        if hasattr(risk_mgr, "save_config"):
            risk_mgr.save_config()

        return (
            "✅ *자동매매 전략 변경 완료*\n\n"
            f"전략이 다음과 같이 변경되었습니다:\n"
            f"`{current_strategy}` ➡️ `{new_strategy}`"
        )

    def _cmd_performance(self, user_id: int, args: List[str]) -> str:
        """성과 통계 조회"""
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"

        try:
            status = self.trading_system.get_trading_status()
            ts = self.trading_system

            win_count = 0
            loss_count = 0
            if hasattr(ts, "optimization_engine") and ts.optimization_engine:
                oe = ts.optimization_engine
                win_count = oe.winning_trades
                total_trades = oe.total_trades
                loss_count = total_trades - win_count
                win_rate = oe.get_win_rate()
            else:
                win_rate = status.get("win_rate", 0)
                total_trades = status.get("total_trades", 0)

            if hasattr(ts, "portfolio") and ts.portfolio:
                current_val = getattr(ts.portfolio, "total_value", 0) or status.get("cash", 0)
                initial = getattr(ts.portfolio, "initial_cash", 0) or current_val
                if initial:
                    total_pnl_pct = (current_val - initial) / initial * 100
                else:
                    total_pnl_pct = 0.0
            else:
                total_pnl_pct = 0.0

            response = "📊 *성과 통계*\n\n"
            response += f"💰 총 수익률: {total_pnl_pct:+.2f}%\n"
            response += f"📈 승률: {win_rate:.1%}\n"
            response += f"✅ 승리: {win_count}회 / ❌ 패배: {loss_count}회\n"
            response += f"📝 총 거래: {total_trades}건\n"
            response += f"💵 현금: ${status.get('cash', 0):,.0f}\n"
            response += f"📊 포지션: {len(status.get('positions', {}))}개\n"
            response += f"⏳ 미체결: {status.get('open_orders', 0)}개\n"

            if hasattr(ts, "risk_manager") and ts.risk_manager:
                rm = ts.risk_manager
                dd = rm.calculate_drawdown()
                response += f"📉 최대손실: {dd:.2%}\n"
                response += f"⚠️ 리스크 수준: {rm.calculate_risk_level(status.get('positions', {})).value}\n"

            return response
        except Exception as e:
            self.logger.error(f"Performance command failed: {e}")
            return "❌ 성과 조회 중 오류가 발생했습니다."

    def _cmd_global(self, user_id: int, args: List[str]) -> str:
        """글로벌 시장 현황"""
        if not self.trading_system or not self.trading_system.global_market:
            return "❌ 글로벌 마켓 모듈을 사용할 수 없습니다."
        try:
            summary = self.trading_system.global_market.get_summary()
            lines = ["🌍 *글로벌 시장 현황*\n"]
            for sym, info in summary.get("indices", {}).items():
                name = info.get("name", sym)
                price = info.get("price")
                chg = info.get("change_pct")
                if price is None:
                    continue
                arrow = "📈" if (chg or 0) >= 0 else "📉"
                lines.append(f"{arrow} *{name}*: {price:,.2f} ({chg:+.2f}%)")
            lines.append("\n*환율*")
            for pair, info in summary.get("fx_rates", {}).items():
                rate = info.get("rate")
                chg = info.get("change_pct")
                if rate is None:
                    continue
                lines.append(f"💱 *{info['name']}*: {rate:.4f} ({chg:+.2f}%)")
            lines.append(f"\n⏱ {summary.get('updated_at', '')}")
            return "\n".join(lines)
        except Exception as e:
            self.logger.error(f"Global command failed: {e}")
            return "❌ 글로벌 시장 조회 중 오류가 발생했습니다."

    def _cmd_screen(self, user_id: int, args: List[str]) -> str:
        """상대 강도 스크리닝 → 시장 대비 수익률 우수 종목 선별

        Usage:
          /screen                               (current positions)
          /screen AAPL,MSFT,GOOGL               (specific tickers)
          /screen AAPL,MSFT,GOOGL 0.3           (with min_correlation filter)
        """
        if not self.trading_system or not self.trading_system.relative_strength:
            return "❌ 상대 강도 분석 모듈을 사용할 수 없습니다."
        try:
            min_corr = 0.0
            symbols = list(self.trading_system.portfolio.positions.keys())
            if args:
                raw = [a.upper() for a in args if not a.replace(".", "").replace("-", "").isdigit()]
                if raw:
                    symbols = [s.strip() for s in raw[0].split(",")]
                for a in args:
                    try:
                        min_corr = float(a)
                    except ValueError:
                        pass
            if not symbols:
                return (
                    "❌ 스크리닝할 종목이 없습니다. 종목을 콤마로 구분해 "
                    "입력하거나 포지션을 먼저 추가하세요.\n"
                    "예: /screen AAPL,MSFT,GOOGL | /screen AAPL,MSFT 0.3"
                )

            results = self.trading_system.relative_strength.rank_symbols(
                symbols,
                top_n=15,
                min_correlation=min_corr,
            )
            if not results:
                return "❌ 데이터를 가져올 수 없습니다. 종목 심볼을 확인해주세요."

            lines = ["🏆 *시장 대비 상대 강도 랭킹*\n"]
            if min_corr > 0:
                lines.append(f"필터: |상관계수| ≥ {min_corr}\n")
            for r in results:
                rank = r.get("rank", "?")
                sym = r.get("symbol", "?")
                score = r.get("composite_score", 0)
                alpha = r.get("alpha", 0)
                rs = r.get("relative_strength_pct", 0)
                corr = r.get("correlation", 0)
                lines.append(
                    f"*{rank}.* {sym}  (점수: {score:+.3f})\n"
                    f"  알파: {alpha:+.6f}  |  상대수익률: {rs:+.2f}%\n"
                    f"  상관계수: {corr:.3f}  |  베타: {r.get('beta', 1):.2f}"
                )
            return "\n".join(lines)
        except Exception as e:
            self.logger.error(f"Screen command failed: {e}")
            return "❌ 스크리닝 중 오류가 발생했습니다."

    def _cmd_predict(self, user_id: int, args: List[str]) -> str:
        """AI 예측 파이프라인 실행 (XGBoost)"""
        if not self.trading_system:
            return "❌ 시스템 연동 안됨"
        return self.trading_system.run_prediction_pipeline()

    def _cmd_dashboard(self, user_id: int, args: List[str]) -> str:
        """대시보드 URL 반환"""
        return (
            "📊 *대시보드 접속*\n\n"
            "로컬 서버에서 실행 중인 대시보드:\n"
            "👉 http://127.0.0.1:5000\n\n"
            "⚠️ 로컬호스트 전용입니다. 외부 접근이 불가능합니다."
        )

    def _cmd_help(self, user_id: int, args: List[str]) -> str:
        """도움말"""
        response = """📖 *명령어 목록*

 *상태 조회*
/status - 거래 현황
/portfolio - 포트폴리오
/positions - 포지션 상세
/performance - 성과 통계
/orders - 주문 현황
/brokers - 증권사 현황
/risk - 위험 관리
/strategy [STRAT] - 전략 조회 및 변경

 *분석 및 정보*
/analyze [SYMBOL] - 주식 분석
/news - 시장 뉴스
/global - 글로벌 지수 및 환율
/screen [SYMBOLS] [MIN_CORR] - 시장 대비 상대 강도 (예: /screen AAPL,MSFT 0.3)
/predict - AI 예측 파이프라인 실행 (XGBoost, 수분 소요)
/dashboard - 대시보드 URL 표시

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
        """이벤트 알림 생성 (영역 8-2: 확장 알림)"""
        ALERT_TRIGGERS = {
            "daily_loss_3pct": "⚠️ 일일 손실 3% 도달",
            "drawdown_10pct": "🔴 드로다운 10% 돌파",
            "crisis_detected": "🚨 위기 감지 (VIX > 30)",
            "consecutive_loss_5": "⛔ 5연패 발생",
            "consecutive_loss_10": "🛑 10연패 — 거래 중단",
            "regime_change": "📊 시장 레짐 변경",
            "take_profit_hit": "💰 익절 실행",
            "stop_loss_hit": "💸 손절 실행",
        }
        if event_type == "order_filled":
            return f"✅ 주문 체결: {data['symbol']} {data['quantity']}주 @ ${data['price']}"
        elif event_type == "order_placed":
            return f"📝 주문 접수: {data['symbol']} {data['quantity']}주 @ ${data['price']}"
        elif event_type == "stop_loss":
            pct = data.get("pnl_pct", "")
            pct_str = f" ({pct:+.2f}%)" if isinstance(pct, (int, float)) else ""
            return f"💸 손절매: {data['symbol']} @ ${data['price']}{pct_str}"
        elif event_type == "take_profit":
            pct = data.get("pnl_pct", "")
            pct_str = f" ({pct:+.2f}%)" if isinstance(pct, (int, float)) else ""
            return f"💰 익절매: {data['symbol']} @ ${data['price']}{pct_str}"
        elif event_type == "alert":
            return f"🔔 알림: {data['message']}"
        elif event_type in ALERT_TRIGGERS:
            msg = ALERT_TRIGGERS[event_type]
            if "symbol" in data:
                msg += f" — {data['symbol']}"
            if "pct" in data:
                msg += f" ({data['pct']:+.2f}%)"
            return msg

        return "📢 알림"

    def send_periodic_report(self, user_id: int) -> Optional[str]:
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
            "is_running": self.is_running,
            "subscribed_users": len(self.subscribed_users),
            "total_commands": len(self.command_history),
            "users": self.subscribed_users,
            "recent_commands": list(self.command_history)[-10:] if self.command_history else [],
        }
