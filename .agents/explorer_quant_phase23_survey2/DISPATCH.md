# Survey Task 2: R2 Risk Allocation & R3 Microstructure OMS Architecture

## 2026-09-11T07:06:11Z

## Target Files
- `src/risk/unified_portfolio_allocator.py`
- `src/risk/portfolio_allocator.py`
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`

## Instructions
1. Read `ORIGINAL_REQUEST.md` (specifically ## 2026-09-11T07:03:36Z) and project rules in `AGENTS.md`.
2. Inspect how Phase 22 implemented F109.1 (Grothendieck Motive Fisher-Rao barycenter) and F109.2 (18th-order cumulant expansion EVaR) in portfolio allocation, and F110.1 (Kerr-Newman-AdS black hole L3 hydrodynamics) and F110.2 (maker floor, tick shading, dark pool ATS, Anti-Gaming MinQty) in microstructure/OMS.
3. Identify exact mathematical equations and code hook points for Phase 23:
   - F113.1: Lurie Geometric Langlands Fisher-Rao manifold barycenter blending with mu_langlands = [2.10, 1.60, 1.55, 2.60] in `unified_portfolio_allocator.py` under version >= 23 branching.
   - Ultra-Trans-Hyper EVaR tail risk budgeting with 19th-order cumulant expansion (19! = 121,645,100,408,832,000, xi_ultra_trans = 0.75) in `portfolio_allocator.py`.
   - F113.2: Kerr-Newman-Kiselev Quintessence-Phantom double dark energy (w_p = -4/3) black hole spacetime L3 order book hydrodynamics in `fast_lob_engine.py`.
   - Execution parameters: maker floor 0.000001 in `smart_order_router.py`, tick shading coefficient -0.9995 * spread * (h - 0.035), dark pool routing 99.995% ATS, Anti-Gaming MinQty 99.999% in `oms_engine.py`.
4. Produce a detailed exploration report in `handoff.md` with file locations, line numbers, function signatures, and recommended implementation plan.
