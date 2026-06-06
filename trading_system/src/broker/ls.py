"""LS Securities API integration"""

from typing import Optional
from .simulated_broker import SimulatedBrokerBase


class LSConnector(SimulatedBrokerBase):
    API_VERSION = "1.0"
    BROKER_NAME = "LS Securities"
    BROKER_CODE = "LS"
    ORDER_PREFIX = "LS"

    def __init__(self, account_number: Optional[str] = None):
        super().__init__(account_number)
