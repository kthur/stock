"""Mirae Asset Securities API integration"""

from typing import Optional

from .simulated_broker import SimulatedBrokerBase


class MiraeAssetConnector(SimulatedBrokerBase):
    API_VERSION = "1.0"
    BROKER_NAME = "Mirae Asset"
    BROKER_CODE = "MA"
    ORDER_PREFIX = "MA"

    def __init__(self, account_number: Optional[str] = None):
        super().__init__(account_number)
