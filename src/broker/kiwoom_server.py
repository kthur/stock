"""Kiwoom 32-bit Microservice Server

이 프로세스는 32비트 환경에서 실행되어야 하며, 키움증권 Open API+ COM 객체와 직접 통신합니다.
64비트 메인 프로세스(FastAPI/트레이딩 엔진)와는 ZeroMQ(TCP)를 통해 통신합니다.
"""

import logging
import signal
from datetime import datetime

import zmq

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("KiwoomServer")


class Kiwoom32Server:
    """키움증권 API 전용 32비트 서버"""

    def __init__(self, port: int = 5555):
        safe_port = max(1024, min(65535, int(port))) if port is not None else 5555
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://127.0.0.1:{safe_port}")
        self.logger = logger
        self.is_connected = False

        # 실제 32비트 환경에서는 여기에 PyQt5 QApplication과 QAxWidget을 초기화합니다.
        # self.app = QApplication(sys.argv)
        # self.kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")

    def run(self):
        self.logger.info("Starting Kiwoom 32-bit Microservice on port 5555...")

        self._running = True
        signal.signal(signal.SIGINT, lambda s, f: setattr(self, "_running", False))

        while self._running:
            try:
                message = self.socket.recv_json()
                command = message.get("command")
                args = message.get("args", {})

                self.logger.info(f"Received command: {command}")

                response = self._handle_command(command, args)
                self.socket.send_json(response)

            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                try:
                    self.socket.send_json({"status": "error", "message": str(e)})
                except Exception:
                    self.logger.exception("Failed to send error response")

    def _handle_command(self, command: str, args: dict) -> dict:
        """수신된 명령 처리"""
        if command == "connect":
            # 키움 API 로그인 로직 수행
            self.is_connected = True
            return {"status": "success", "data": True}

        elif command == "get_account_balance":
            # 실제 API의 예수금/잔고 조회 로직
            return {"status": "success", "data": {"cash": 1000000.0, "holdings": [], "total_value": 1000000.0}}

        elif command == "place_order":
            order_id = f"ORD_{datetime.now().timestamp()}"
            return {"status": "success", "data": order_id}

        elif command == "ping":
            return {"status": "success", "data": "pong"}

        else:
            return {"status": "error", "message": f"Unknown command: {command}"}


if __name__ == "__main__":
    server = Kiwoom32Server()
    server.run()
