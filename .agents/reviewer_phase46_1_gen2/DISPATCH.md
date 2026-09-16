# DISPATCH: Reviewer 1 gen2 (Alpha & Risk Review)

## Role & Working Directory
- Subagent Type: `teamwork_preview_reviewer`
- Role: Alpha & Risk Reviewer
- Working Directory: `d:\Finance\code\stock\.agents\reviewer_phase46_1_gen2`

## Authoritative Inputs
- Original Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-16T08:29:02Z)
- Orchestrator Plan: `d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1\plan.md`
- Target Files to Review:
  - `trading_system/src/ai/ensemble_scorer.py` (F203)
  - `trading_system/src/ai/factor_suppression.py` (F204.1, F204.2)
  - `trading_system/src/risk/unified_portfolio_allocator.py` (F205.1)
  - `trading_system/src/risk/portfolio_allocator.py` (F205.1)
  - `tests/test_phase46_alpha.py`
  - `tests/test_phase46_risk.py`

## Review Tasks
1. Verify Feature F203 implementation: Borcherds-Kac-Moody Whittaker Coupler, parameters ($\kappa=9.00, \theta_0=0.50$), energy $E_{\text{borch\_whit}}$, topological invariant $Z_{\text{borch\_whit}}$, $\text{FERI}_{\text{v46}}$, dynamic harmony factor $+2.65 \cdot h \cdot z$, and all aliases.
2. Verify Feature F204.1 implementation: 41st-order rank modulation $g_{\text{v46}}(r) = 0.50 + 1.52 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{41})$, regime table `REGIME_GAMMA_TOP_V46` (max 5.30), negative branch monotonicity.
3. Verify Feature F204.2 implementation: 176th-order deadband, noise leakage $< 10^{-102}$ for $|z| \le 0.0003$, 100% transmission for $|z| \ge 0.150$.
4. Verify Feature F205.1 implementation: Lurie-Borcherds-Whittaker Fisher-Rao barycenter ($\mu=[3.60, 2.75, 2.70, 4.15]$), 42nd-order cumulant EVaR ($42! \approx 1.405 \times 10^{51}$, $\xi=0.9999999$), lower bound guarantee $EVaR_{42} \ge EVaR_{41}$, ambiguity tilting, and alias parity.
5. Verify test pass rate and backward compatibility:
   ```powershell
   python -m pytest tests/test_phase46_alpha.py tests/test_phase46_risk.py tests/test_phase45_alpha.py tests/test_phase45_risk.py -v
   ```

## 2026-09-16T11:00:35Z
You are Reviewer 1 gen2 (Alpha & Risk Reviewer) for Phase 46 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\reviewer_phase46_1_gen2
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-16T08:29:02Z)
Read your specific instructions at: d:\Finance\code\stock\.agents\reviewer_phase46_1_gen2\DISPATCH.md
Read the orchestrator plan: d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1\plan.md

Review implementation of F203, F204.1, F204.2 in `ensemble_scorer.py` and `factor_suppression.py`, and F205.1 in `unified_portfolio_allocator.py` and `portfolio_allocator.py`.
Run unit tests:
```powershell
python -m pytest tests/test_phase46_alpha.py tests/test_phase46_risk.py tests/test_phase45_alpha.py tests/test_phase45_risk.py -v
```
Verify code quality, mathematical validity, alias completeness, and backward compatibility.
Write your review report and handoff at `d:\Finance\code\stock\.agents\reviewer_phase46_1_gen2\handoff.md` with an explicit verdict (**APPROVE** or **REQUEST_CHANGES**). Send a message when done.
