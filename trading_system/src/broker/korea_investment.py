"""한국투자증권(Korea Investment & Securities) 오픈 API V1 연동 모듈"""

import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, cast

import requests

logger = logging.getLogger(__name__)


@dataclass
class KoreaInvestmentOrder:
    """한국투자증권 주문"""

    order_id: str
    code: str
    quantity: int
    price: float
    order_type: str  # 매수, 매도
    status: str
    timestamp: datetime


class KoreaInvestmentConnector:
    """한국투자증권 오픈 API 연동"""

    # 실전/모의투자 엔드포인트 분리
    PROD_DOMAIN = "https://openapi.koreainvestment.com:9443"
    MOCK_DOMAIN = "https://openapivts.koreainvestment.com:29443"

    def __init__(
        self,
        account_number: Optional[str] = None,
        use_mock: bool = True,
        max_order_value: float = 50_000_000.0,
        max_price_deviation_pct: float = 0.03,
    ):
        """
        한국투자증권 연동 초기화

        Args:
            account_number: 8~10자리 계좌번호
            use_mock: True면 모의투자 API, False면 실전투자 API
            max_order_value: 단일 주문 최대 금액 한도 (원)
            max_price_deviation_pct: 시장가 대비 주문가 허용 오차 (±3%)
        """
        self.account_number: Optional[str] = account_number
        self.is_connected = False

        self.app_key = os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_APP_SECRET")
        self.use_mock = use_mock
        self.max_order_value = max_order_value
        self.max_price_deviation_pct = max_price_deviation_pct

        # API 인증 및 환경 변수가 없으면 순수 시뮬레이션 모드로 작동
        self.simulation_mode = not bool(self.app_key and self.app_secret)
        self.domain = self.MOCK_DOMAIN if self.use_mock or self.simulation_mode else self.PROD_DOMAIN

        self.access_token: Optional[str] = None
        self.token_expired_at = 0.0

        self.orders: Dict[str, KoreaInvestmentOrder] = {}
        self.positions: Dict[str, int] = {}
        self.balance = 10000000
        self.logger = logger

    def _issue_token(self) -> bool:
        """접근 토큰 발급"""
        if self.simulation_mode:
            self.access_token = "SIMULATED_TOKEN_12345"
            self.token_expired_at = time.time() + 86400
            return True

        url = f"{self.domain}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {"grant_type": "client_credentials", "appkey": self.app_key, "appsecret": self.app_secret}

        try:
            res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
            res.raise_for_status()
            data = res.json()
            self.access_token = data.get("access_token")
            # 토큰 만료는 보통 24시간
            expires_in = int(data.get("expires_in", 86400))
            self.token_expired_at = time.time() + expires_in - 300  # 여유시간 5분
            self.logger.info("Korea Investment API access token issued.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to issue KIS access token: {e}")
            return False

    def _get_auth_headers(self, tr_id: str) -> Dict[str, str]:
        """기본 인증 헤더 생성"""
        if not self.access_token or time.time() > self.token_expired_at:
            self._issue_token()

        return {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key or "SIMULATED_KEY",
            "appsecret": self.app_secret or "SIMULATED_SECRET",
            "tr_id": tr_id,
        }

    def connect(self, account_number: str) -> bool:
        """서버 연결 (토큰 발급 테스트)"""
        self.account_number = account_number
        self.is_connected = self._issue_token()

        mode_str = "SIMULATION" if self.simulation_mode else ("MOCK(VTS)" if self.use_mock else "PRODUCTION")
        self.logger.info(f"Connected to Korea Investment API in {mode_str} mode. Account: {account_number}")

        return self.is_connected

    def disconnect(self) -> bool:
        """연결 해제"""
        self.is_connected = False
        self.access_token = None
        self.logger.info("Disconnected from Korea Investment API")
        return True

    def get_account_info(self) -> Dict:
        """계좌 잔고 및 평가 정보 조회"""
        if self.simulation_mode:
            return {
                "account_number": self.account_number,
                "balance": self.balance,
                "positions": self.positions,
                "total_value": self.balance + sum(self.positions.values()),
                "timestamp": datetime.now(),
            }

        # 실거래/모의거래 잔고조회 (TR_ID: VTTC8434R or TTTC8434R)
        tr_id = "VTTC8434R" if self.use_mock else "TTTC8434R"
        headers = self._get_auth_headers(tr_id)

        # 계좌번호 포맷 처리 (앞 8자리, 뒤 2자리)
        assert self.account_number is not None
        cano = self.account_number[:8] if len(self.account_number) >= 8 else self.account_number
        acnt_prdt_cd = self.account_number[-2:] if len(self.account_number) >= 10 else "01"

        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        url = f"{self.domain}/uapi/domestic-stock/v1/trading/inquire-balance"
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()

            # 응답 데이터 파싱
            output2 = data.get("output2", [{}])[0]
            cash = float(output2.get("dnca_tot_amt", 0))  # 예수금총금액
            total_eval = float(output2.get("tot_evlu_amt", 0))  # 총평가금액

            return {
                "account_number": self.account_number,
                "balance": cash,
                "positions": self.positions,  # 위치는 output1 파싱이 추가로 필요
                "total_value": total_eval,
                "timestamp": datetime.now(),
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch account info: {e}")
            return {"error": str(e)}

    def get_stock_quote(self, code: str) -> Dict:
        """주식 시세 조회 (BrokerProtocol)"""
        return self.get_live_quote(code)

    def get_live_quote(self, symbol: str) -> Dict:
        """현재가 조회 (FHKST01010100)"""
        if self.simulation_mode:
            return {"price": 10000.0 * (1 + random.uniform(-0.01, 0.01))}

        headers = self._get_auth_headers("FHKST01010100")

        # '.KS' 등 포맷 제거
        code = symbol.split(".")[0] if "." in symbol else symbol

        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}

        url = f"{self.domain}/uapi/domestic-stock/v1/quotations/inquire-price"
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()

            output = data.get("output", {})
            return {
                "price": float(output.get("stck_prpr", 0)),  # 주식 현재가
                "volume": int(output.get("acml_vol", 0)),  # 누적 거래량
                "timestamp": datetime.now(),
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch live quote for {symbol}: {e}")
            return {}

    def place_order(
        self,
        code: str,
        quantity: int,
        price: float,
        order_type: str,
        market_price: Optional[float] = None,
    ) -> str:
        """
        주식 현금 매수/매도 주문 (TR_ID: VTTC0802U 등)
        Pre-order safety guards applied:
          - Single order max value cap (max 50,000,000 KRW)
          - Limit price sanity bounds (max ±3% deviation from market price)
        """
        # Safety guard 1: Single order max value cap
        order_value = price * quantity if price > 0 else 0.0
        if order_value > self.max_order_value:
            raise ValueError(
                f"Order value {order_value:,.0f} KRW exceeds maximum allowed single order value limit of {self.max_order_value:,.0f} KRW"
            )

        # Safety guard 2: Limit price sanity bounds (±3%)
        if price > 0:
            ref_price = market_price
            if ref_price is None or ref_price <= 0:
                quote = self.get_live_quote(code)
                if isinstance(quote, dict) and quote.get("price", 0) > 0:
                    ref_price = quote["price"]

            if ref_price is not None and ref_price > 0:
                dev = abs(price - ref_price) / ref_price
                if dev > self.max_price_deviation_pct:
                    raise ValueError(
                        f"Order price {price:,.0f} deviates by {dev:.2%} from market price {ref_price:,.0f}, exceeding ±{self.max_price_deviation_pct:.0%} sanity bound"
                    )

        if self.simulation_mode:
            order_id = f"KIS_SIM_{datetime.now().timestamp()}"
            self.orders[order_id] = KoreaInvestmentOrder(
                order_id=order_id,
                code=code,
                quantity=quantity,
                price=price,
                order_type=order_type,
                status="SUBMITTED",
                timestamp=datetime.now(),
            )
            self.logger.info(f"Simulated order placed: {order_id} {order_type} {quantity}주 @ {price:,.0f}")
            return order_id

        clean_code = code.split(".")[0] if "." in code else code
        is_buy = order_type.upper() == "BUY"

        if self.use_mock:
            tr_id = "VTTC0802U" if is_buy else "VTTC0801U"
        else:
            tr_id = "TTTC0802U" if is_buy else "TTTC0801U"

        headers = self._get_auth_headers(tr_id)

        assert self.account_number is not None
        cano = self.account_number[:8] if len(self.account_number) >= 8 else self.account_number
        acnt_prdt_cd = self.account_number[-2:] if len(self.account_number) >= 10 else "01"

        # 가격이 0이면 시장가(01), 아니면 지정가(00)
        ord_dvsn = "01" if price <= 0 else "00"

        body = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "PDNO": clean_code,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0" if ord_dvsn == "01" else str(int(price)),
        }

        url = f"{self.domain}/uapi/domestic-stock/v1/trading/order-cash"
        try:
            res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
            res.raise_for_status()
            data = res.json()

            if data.get("rt_cd") != "0":
                self.logger.error(f"Order failed: {data.get('msg1')}")
                return ""

            order_id = str(data.get("output", {}).get("ODNO", ""))
            if order_id:
                self.orders[order_id] = KoreaInvestmentOrder(
                    order_id=order_id,
                    code=code,
                    quantity=quantity,
                    price=price,
                    order_type=order_type,
                    status="SUBMITTED",
                    timestamp=datetime.now(),
                )
            self.logger.info(f"Order submitted to KIS: {order_id}")
            return order_id
        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
            return ""

    def cancel_order(self, order_id: str, code: Optional[str] = None, quantity: Optional[int] = None) -> bool:
        """주문 취소 (TR_ID: VTTC0803U / TTTC0803U)"""
        if self.simulation_mode:
            if order_id in self.orders:
                self.orders[order_id].status = "CANCELLED"
                self.logger.info(f"Simulated order cancelled: {order_id}")
                return True
            return False

        tr_id = "VTTC0803U" if self.use_mock else "TTTC0803U"
        headers = self._get_auth_headers(tr_id)
        cano = self.account_number[:8] if self.account_number and len(self.account_number) >= 8 else (self.account_number or "")
        acnt_prdt_cd = self.account_number[-2:] if self.account_number and len(self.account_number) >= 10 else "01"
        code.split(".")[0] if code and "." in code else (code or "")

        body = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "KRX_FWDG_ORD_ORGNO": "",
            "ORGN_ODNO": order_id,
            "ORD_DVSN": "00",
            "RVSE_CNCL_DVSN_CD": "02",
            "ORD_QTY": str(quantity) if quantity else "0",
            "ORD_UNPR": "0",
            "QTY_ALL_ORD_YN": "Y" if not quantity else "N",
        }

        url = f"{self.domain}/uapi/domestic-stock/v1/trading/order-rvsecncl"
        try:
            res = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
            res.raise_for_status()
            data = res.json()
            if data.get("rt_cd") == "0":
                if order_id in self.orders:
                    self.orders[order_id].status = "CANCELLED"
                self.logger.info(f"Order cancelled in KIS: {order_id}")
                return True
            else:
                self.logger.error(f"Failed to cancel order {order_id}: {data.get('msg1')}")
                return False
        except Exception as e:
            self.logger.error(f"Error executing cancel_order: {e}")
            return False

    def get_order_status(self, order_id: str) -> Dict:
        """주문 상태 조회 (TR_ID: VTTC8001R / TTTC8001R)"""
        if self.simulation_mode or order_id in self.orders:
            if order_id in self.orders:
                order = self.orders[order_id]
                return {
                    "order_id": order.order_id,
                    "code": order.code,
                    "quantity": order.quantity,
                    "price": order.price,
                    "order_type": order.order_type,
                    "status": order.status,
                    "timestamp": order.timestamp,
                }
            return {}

        tr_id = "VTTC8001R" if self.use_mock else "TTTC8001R"
        headers = self._get_auth_headers(tr_id)
        cano = self.account_number[:8] if self.account_number and len(self.account_number) >= 8 else (self.account_number or "")
        acnt_prdt_cd = self.account_number[-2:] if self.account_number and len(self.account_number) >= 10 else "01"

        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "INQR_DVSN": "00",
            "ODNO": order_id,
        }

        url = f"{self.domain}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
            output = data.get("output", [{}])[0] if isinstance(data.get("output"), list) and data.get("output") else data.get("output", {})
            return {
                "order_id": order_id,
                "status": output.get("prcs_stat_name", "SUBMITTED"),
                "filled_qty": int(output.get("tot_ccld_qty", 0)),
                "order_price": float(output.get("ord_unpr", 0)),
                "raw_response": data,
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch order status for {order_id}: {e}")
            return {}

    def get_daily_chart(self, code: str, days: int = 20) -> List[Dict]:
        """일봉 차트 조회"""
        if self.simulation_mode:
            return self._simulate_daily_chart(code, days)
        return []

    def _simulate_daily_chart(self, code: str, days: int) -> List[Dict]:
        import random

        charts = []
        price = 100.0
        for _ in range(days):
            change = random.uniform(-0.02, 0.02)
            chart = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "open": price,
                "high": price * (1 + abs(change)),
                "low": price * (1 - abs(change)),
                "close": price * (1 + change),
                "volume": random.randint(1000000, 10000000),
            }
            charts.append(chart)
            price = float(cast(float, chart["close"]))
        return charts

    def get_broker_info(self) -> Dict:
        """증권사 정보"""
        return {
            "name": "한국투자증권",
            "code": "KOREA_INVESTMENT",
            "api_version": "1.0",
            "simulation_mode": self.simulation_mode,
        }
