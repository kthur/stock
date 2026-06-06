"""NH Investment Securities API integration"""

from typing import Optional
from .simulated_broker import SimulatedBrokerBase


class NHConnector(SimulatedBrokerBase):
    API_VERSION = "1.0"
    BROKER_NAME = "NH Investment"
    BROKER_CODE = "NH"
    ORDER_PREFIX = "NH"

    def __init__(self, account_number: Optional[str] = None):
        super().__init__(account_number)
