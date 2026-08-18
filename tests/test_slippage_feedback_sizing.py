import pytest
from src.risk.portfolio_allocator import PortfolioAllocator


def test_slippage_feedback_haircut():
    allocator = PortfolioAllocator()

    weights = {
        '005930': 0.15,
        '000660': 0.12,
        '035420': 0.08,
    }

    # 005930 has excessive realized slippage (55 bps > 30 bps threshold)
    # 000660 has normal slippage (10 bps <= 30 bps)
    # 035420 has no slippage record (default 0.0)
    realized_slippage = {
        '005930': 55.0,
        '000660': 10.0,
    }

    adj_weights = allocator.apply_slippage_feedback_haircut(
        weights_dict=weights,
        realized_slippage_map=realized_slippage,
        max_slippage_bps_threshold=30.0
    )

    # 005930 weight should be scaled down
    assert adj_weights['005930'] < weights['005930']
    # 000660 and 035420 should maintain original weight
    assert adj_weights['000660'] == weights['000660']
    assert adj_weights['035420'] == weights['035420']
