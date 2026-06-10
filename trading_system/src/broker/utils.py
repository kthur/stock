"""Broker utility functions — 모의투자 포맷 정규화 등"""

from typing import Dict, List


def normalize_holdings(raw_positions: Dict | List) -> Dict[str, int]:
    """보유 종목 포맷 정규화 (List[Dict] 또는 Dict[str, int] → Dict[str, int])"""
    normalized: Dict[str, int] = {}
    if isinstance(raw_positions, list):
        for pos in raw_positions:
            symbol = pos.get("symbol") or pos.get("code")
            qty = int(pos.get("qty") or pos.get("quantity") or 0)
            if symbol:
                normalized[symbol] = qty
    elif isinstance(raw_positions, dict):
        for k, v in raw_positions.items():
            if isinstance(v, dict):
                normalized[k] = int(v.get("qty") or v.get("quantity") or 0)
            else:
                normalized[k] = int(v)
    return normalized
