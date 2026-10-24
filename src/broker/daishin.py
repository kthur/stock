"""Daishin Securities API integration"""

from typing import Optional

from .simulated_broker import SimulatedBrokerBase


class DaishinConnector(SimulatedBrokerBase):
    API_VERSION = "2.0"
    BROKER_NAME = "Daishin"
    BROKER_CODE = "DS"
    ORDER_PREFIX = "DS"

    def __init__(self, account_number: Optional[str] = None):
        super().__init__(account_number)
