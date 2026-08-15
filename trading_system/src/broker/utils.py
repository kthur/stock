"""Broker utility functions — 모의투자 포맷 정규화 등"""

from typing import Dict, List


def normalize_holdings(raw_positions: Dict | List) -> Dict[str, int]:
    """보유 종목 포맷 정규화 (List[Dict] 또는 Dict[str, int] → Dict[str, int])"""
    import math
    normalized: Dict[str, int] = {}

    def _parse_qty(val) -> int:
        try:
            f = float(val)
            return int(f) if math.isfinite(f) else 0
        except (ValueError, TypeError):
            return 0

    if isinstance(raw_positions, list):
        for pos in raw_positions:
            if not isinstance(pos, dict):
                continue
            symbol = str(pos.get("symbol") or pos.get("code") or "").strip()
            qty = _parse_qty(pos.get("qty") or pos.get("quantity") or 0)
            if symbol:
                normalized[symbol] = max(0, qty)
    elif isinstance(raw_positions, dict):
        for k, v in raw_positions.items():
            sym = str(k).strip()
            if not sym:
                continue
            if isinstance(v, dict):
                qty = _parse_qty(v.get("qty") or v.get("quantity") or 0)
            else:
                qty = _parse_qty(v)
            normalized[sym] = max(0, qty)
    return normalized
