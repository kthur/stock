## 2026-08-05T15:54:10Z
Task:
Audit HRP (Hierarchical Risk Parity) portfolio allocation, covariance shrinkage, liquidity constraints, position sizing limits, microstructure transaction costs, and RiskManager & CrisisGating.

Investigate:
1. Is HRP (Hierarchical Risk Parity) allocation correctly implemented using Ledoit-Wolf or shrinkage covariance matrices and hierarchical clustering?
2. Are position sizing limits, single-asset caps, sector neutrality/exposure limits, and liquidity rules (e.g. ADV volume limits) strictly enforced?
3. Is the microstructure transaction cost model (STT tax 0.18/0.20%, SEC fee, bid-ask spread, market impact based on square-root model/volume) strictly deducted from expected returns?
4. How does `RiskManager` & `CrisisDetector` perform when market indicators (VIX, USDKRW, yield curve) breach crisis thresholds? Is dynamic score attenuation/gating working properly?

Document all findings, evidence, line numbers, code snippets, and recommended fixes in `analysis.md` and write a handoff report (`handoff.md`) in your working directory. Send a message to parent when complete.
