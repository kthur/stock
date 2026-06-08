# Implementation Changes - Milestone 2

This document details the code modifications made to implement R1 (Portfolio Risk Parity Weight Optimization) and R2 (VIX-Linked Dynamic Asset Allocation Switch).

## R1: Portfolio Risk Parity Weight Optimization
- **File**: `src/analysis/portfolio_optimizer.py`
  - Created a new optimizer module implementing the Equal Risk Contribution (ERC) portfolio weights using scipy's `minimize` solver.
  - Implemented both log-barrier formulation (Formulation B, using `L-BFGS-B`) and direct variance minimization (Formulation A, using `SLSQP`) as numerical solvers.
  - Added robust cascading fallbacks: Log-Barrier Optimization -> Direct Variance SLSQP Optimization -> Inverse-Volatility Weighting -> Equal Weighting.
  - Ensured weights sum exactly to 1.0 and each weight is in $[0.0, 1.0]$.
  - Included the MANDATORY INTEGRITY WARNING verbatim.
- **File**: `src/strategy/asset_allocation.py`
  - Updated `_risk_parity` method to compute period simple returns, align returns series to the minimum shared historical length (falling back to equal weighting if length $< 2$), compute the sample covariance matrix, call the custom `calculate_risk_parity_weights` solver, and return normalized weights using the existing `_normalize` helper.
  - Included the MANDATORY INTEGRITY WARNING verbatim.

## R2: VIX-Linked Dynamic Asset Allocation (Risk-Off Switch)
- **File**: `src/risk/risk_manager.py`
  - Implemented `check_risk_off_signal(vix_value: float = None) -> bool` returning `True` if VIX $\ge 25.0$, and `False` otherwise.
  - Fetched VIX dynamically using `AlternativeDataClient().fetch_vix()` with error safety, falling back to `20.0` on error.
  - Included the MANDATORY INTEGRITY WARNING verbatim.
- **File**: `trading_system.py`
  - Inside `_create_and_submit_order`: added a VIX-linked risk-off switch check for `OrderType.BUY`.
  - Under risk-off conditions (VIX $\ge 25.0$), calculated the total portfolio value $PV = C + V_E$ (where $C$ is cash and $V_E$ is the total equity exposure based on current cached/average prices).
  - Enforced that post-trade cash satisfies $C' \ge 0.70 \times PV$, clamping the buy order quantity to $\max(0, \lfloor \frac{C - 0.70 \times PV}{\text{Price}} \rfloor)$.
  - Logged a warning when clamping is applied.
  - Included the MANDATORY INTEGRITY WARNING verbatim.

## Verification
- Created `tests/test_portfolio_risk.py` verifying R1 (weights sum to 1.0, lower-variance asset receives higher weight) and R2 (VIX threshold evaluation, buy order quantity clamping under VIX >= 25.0).
- Included the MANDATORY INTEGRITY WARNING verbatim.
