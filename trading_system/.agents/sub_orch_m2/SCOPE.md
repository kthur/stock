# Scope: Asset Allocation

## Architecture
- `src/strategy/allocation.py`: Asset allocation algorithm. Needs to provide `allocate_assets(prices_dict: dict) -> dict` returning normalized weights summing to 1.0.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Asset Allocation Logic | Implement Asset Allocation logic ensuring 100% total weight distribution across given assets. | none | IN_PROGRESS |

## Interface Contracts
### Asset Allocation
- `allocate_assets(prices_dict: dict) -> dict`: Returns normalized weights summing to 1.0.
