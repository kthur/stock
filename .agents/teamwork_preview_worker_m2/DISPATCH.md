## 2026-09-04T01:02:19Z
You are Worker 2: M2 Portfolio Execution Worker.
Your working directory: d:\Finance\code\stock\.agents\teamwork_preview_worker_m2
Maintain progress.md in your working directory.

MANDATORY FIRST STEP:
Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md completely.
Also read the detailed engineering blueprint from Explorer 3 at:
d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\handoff.md
And SCOPE.md at:
d:\Finance\code\stock\.agents\orchestrator_quant_opt4\SCOPE.md

WRITE OWNERSHIP:
You EXCLUSIVELY own and are permitted to modify:
1. `trading_system/src/risk/unified_portfolio_allocator.py`
2. `trading_system/src/execution/smart_order_router.py`
3. `trading_system/src/execution/oms_engine.py`
4. `tests/test_phase4_portfolio_execution.py` (new test suite)
Do NOT modify any other files.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks for Milestone 2 (R2 / Features F28 to F33):
1. F28: Downside Semi-Covariance (Sortino) EVT-CVaR Optimization (`unified_portfolio_allocator.py`):
   - In `calculate_cvar_weights`, incorporate `PortfolioAllocator.compute_downside_semi_cov` to construct:
     $\Sigma_{\text{effective}} = (1 - \lambda_{\text{semi}}) \Sigma_{\text{tail}} + \lambda_{\text{semi}} \Sigma^-$
   - Add parameters: `use_downside_semi_cov: bool = True`, `semi_cov_weight: float = 0.35` (defaulting safely to preserve backward compatibility).
   - Solves EVT-CVaR objective minimizing tail risk while penalizing only downside volatility, boosting the portfolio Sortino ratio.
2. F29: Dynamic Model Conviction & Return-Dispersion Blending (`unified_portfolio_allocator.py`):
   - In `optimize_multi_model_blend`, evaluate cross-sectional alpha dispersion $\sigma(\hat{\mu})$.
   - When dispersion is high ($\sigma(\hat{\mu}) > 0.03$) in Bull or Sideways regimes, scale up Black-Litterman model weight:
     $w_{\text{BL}}^{\text{adj}} = w_{\text{BL}} \cdot (1.0 + 0.30 \tanh((\sigma(\hat{\mu}) - 0.03) / 0.02))$
   - In high volatility or crisis, boost EVT-CVaR and HERC to preserve capital.
   - Renormalize model weights so $\sum_{m \in \{BL, HERC, RP, CVaR\}} w_m = 1.0000$.
3. F30: Market-Specific STT & Fee-Aware Leland Dynamic Buffer Bands (`unified_portfolio_allocator.py`):
   - In `apply_leland_no_trade_buffers`, support asset/market-specific transaction cost sizing via optional `symbols: Optional[List[str]] = None` or `asset_cost_bps: Optional[Union[np.ndarray, List[float]]] = None`.
   - If `symbols` is provided, automatically identify Korean assets (`.KS`, `.KQ`, or 6-digit symbols) and set $c_i = \max(\text{leland\_cost\_bps}, 25.0) \times 10^{-4}$ (incorporating Korea's 0.18% STT). For US assets, set $c_i = \min(\text{leland\_cost\_bps}, 8.0) \times 10^{-4}$ (low SEC fee).
   - This suppresses expensive KRX churn by 35%+ while keeping US rebalancing responsive.
4. F31: Multi-Tier L2 OBI & Volume-Weighted Micro-Price Pegging (`oms_engine.py`):
   - In `calculate_peg_limit_price`, accept optional `micro_price: Optional[float] = None` and `multi_obi: Optional[Dict[str, float]] = None`.
   - When `micro_price` is provided, use it as baseline price $P_{\text{base}} = P_{\text{micro}}$ instead of simple midpoint $P_{\text{mid}}$.
   - When `multi_obi` is provided with `OBI_1, OBI_5, OBI_10`, compute composite OBI: $\text{OBI}_{\text{comp}} = 0.50 \cdot \text{OBI}_1 + 0.35 \cdot \text{OBI}_5 + 0.15 \cdot \text{OBI}_{10}$.
   - Shift peg: $P_{\text{peg}} = P_{\text{base}} + 0.5 \cdot \text{spread} \cdot \tanh(\kappa \cdot \text{OBI}_{\text{comp}})$.
5. F32: Hawkes Arrival Intensity Adverse Selection Gating (`smart_order_router.py`):
   - In `route_order`, accept optional `hawkes_intensity: Optional[float] = None` and `baseline_intensity: float = 1.0`.
   - When $\lambda(t) > 2.5 \cdot \mu$ (aggressive order arrival cluster / toxic flow), reduce primary maker leg proportion from 70% to 30% and expand Tier 1 dark midpoint probing to protect maker legs against front-running and adverse selection.
6. F33: Closed-Loop Empirical Slippage Feedback Scaling:
   - In `unified_portfolio_allocator.py` and `oms_engine.py`, dynamically query `SlippageFeedbackEngine().calculate_realized_slippage()` if available, scaling $\kappa_{\text{eff}} = \kappa_0 \cdot \text{cost\_scaling\_factor} \cdot (1 - \phi_{\text{dark}})$.
7. Create comprehensive unit/property tests in `tests/test_phase4_portfolio_execution.py` verifying F28 through F33.
8. Verify test execution:
   Run: `.venv\Scripts\python.exe -m pytest tests/test_phase4_portfolio_execution.py tests/test_m2_portfolio_execution.py tests/test_m2_quant_enhancements.py tests/test_tier0_apex_quant_enhancements.py tests/test_fast_lob_engine.py tests/test_turnover_optimizer.py tests/test_slippage_feedback.py tests/test_institutional_portfolio_construction.py -v`
9. Write `handoff.md` in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\handoff.md` and notify caller via send_message.
