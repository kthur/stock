"""
Unit Tests for SmartOrderRouter (V6-31)
"""
import pytest
from src.execution.sor_router import SmartOrderRouter
from src.execution.smart_router import SmartOrderRouter as SmartRouterAlias


def test_v6_31_ats_residual_routed_to_primary():
    """
    V6-31: When an ATS (NXT) has best price for 50 shares, and total quantity is 100 shares,
    50 shares go to NXT and the residual 50 shares MUST go to the primary exchange (KRX),
    NOT creating a duplicate 50 share order on NXT.
    """
    sor = SmartOrderRouter()
    
    venues = [
        {
            "venue_id": "NXT",
            "is_primary": False,
            "ask_price": 69900.0,  # slightly better price
            "ask_vol": 50,
            "fee_bps": -0.5
        },
        {
            "venue_id": "KRX",
            "is_primary": True,
            "ask_price": 70000.0,
            "ask_vol": 1000,
            "fee_bps": 1.5
        }
    ]
    
    allocations = sor.route_order(
        symbol="005930.KS",
        action="BUY",
        total_quantity=100,
        venues=venues
    )
    
    assert len(allocations) == 2
    nxt_alloc = next(a for a in allocations if a["venue_id"] == "NXT")
    krx_alloc = next(a for a in allocations if a["venue_id"] == "KRX")
    
    assert nxt_alloc["allocated_quantity"] == 50
    assert krx_alloc["allocated_quantity"] == 50
    assert sum(a["allocated_quantity"] for a in allocations) == 100


def test_v6_31_merge_allocations_for_primary_venue():
    """
    V6-31: If primary venue was already partially allocated during the loop,
    any residual allocated to primary should MERGE into the primary record rather
    than creating duplicate entries.
    """
    sor = SmartOrderRouter()
    
    venues = [
        {
            "venue_id": "KRX",
            "is_primary": True,
            "ask_price": 70000.0,
            "ask_vol": 40,
            "fee_bps": 0.0
        },
        {
            "venue_id": "NXT",
            "is_primary": False,
            "ask_price": 70100.0,
            "ask_vol": 30,
            "fee_bps": 0.0
        }
    ]
    
    # Total order 100: KRX takes 40, NXT takes 30, residual 30 routes to KRX -> merged into 40 + 30 = 70 on KRX
    allocations = sor.route_order(
        symbol="005930.KS",
        action="BUY",
        total_quantity=100,
        venues=venues
    )
    
    assert len(allocations) == 2
    krx_alloc = next(a for a in allocations if a["venue_id"] == "KRX")
    nxt_alloc = next(a for a in allocations if a["venue_id"] == "NXT")
    
    assert krx_alloc["allocated_quantity"] == 70  # 40 + 30 residual merged
    assert nxt_alloc["allocated_quantity"] == 30
    assert sum(a["allocated_quantity"] for a in allocations) == 100


def test_smart_router_empty_and_zero_qty():
    sor = SmartOrderRouter()
    assert sor.route_order("AAPL", "BUY", 0, [{"venue_id": "NYSE"}]) == []
    assert sor.route_order("AAPL", "BUY", 100, []) == []

