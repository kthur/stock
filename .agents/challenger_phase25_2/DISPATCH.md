## 2026-09-11T12:34:05Z

You are Challenger 2 (OMS & Benchmark Adversarial Challenger) for Phase 25 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\challenger_phase25_2

Authoritative User Request:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (under header ## 2026-09-11T12:11:40Z)

Scope:
Adversarial stress testing of Microstructure OMS and Benchmark modules:
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
- `trading_system/scripts/benchmark_phase25_quant_performance.py`

Tasks:
1. Design and run empirical stress tests targeting:
   - Kerr-Newman-Kiselev Quintom 4-Dark-Energy L3 hydrodynamics: horizon singularities $r \to r_H$, $r \to r_M$, extreme spin ($a \to M$), negative parameters, empty order book, inverted bids/asks.
   - SmartOrderRouter: toxic order arrival $\gamma_{\text{toxic}} \to 1.0$, verify maker floor strictly contracts to $0.0000002$ and never breaches, MinQty strictly caps at $0.999998$.
   - Execution OMS: Hawkes arrival explosion $h \to 10.0$, extreme spreads, verify tick shading $-0.9999 \cdot \text{spread} \cdot (h - 0.025)$ remains stable, bounded, and produces strictly valid peg prices.
   - Benchmark script: run subprocess, verify 15 metrics sanity, no NaN/inf values, exact table formatting, and strict satisfaction of all 6 acceptance criteria.
2. Run your stress tests using `.venv/Scripts/python.exe`.
3. Document tests, empirical results, and verdict (APPROVE or REQUEST_CHANGES) in `d:\Finance\code\stock\.agents\challenger_phase25_2\handoff.md`.
4. Send completion message back to orchestrator.
