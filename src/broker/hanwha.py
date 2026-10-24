"""Hanwha Investment Securities API integration"""

from typing import Optional

from .simulated_broker import SimulatedBrokerBase


class HanwhaConnector(SimulatedBrokerBase):
    API_VERSION = "3.0"
    BROKER_NAME = "Hanwha Investment"
    BROKER_CODE = "HW"
    ORDER_PREFIX = "HW"

    def __init__(self, account_number: Optional[str] = None):
        super().__init__(account_number)
