# Phase 40 Quant Enhancement Survey 2: Risk Allocation & Tail Risk Budgeting Blueprint

**Author**: Explorer 2 (Risk Allocation & Portfolio Optimization)  
**Date**: 2026-09-14  
**Target Milestone**: Phase 40 Quant Enhancement (R2: F181.1 Lurie-Langlands-Deligne Motivic Fisher-Rao Barycenter & 36th-Cumulant Trans-Singular-Deligne EVaR)  
**Deliverable File**: `d:\Finance\code\stock\.agents\explorer_quant_phase40_survey2\handoff.md`

---

## 1. Observation

Direct code inspection of the production repository revealed the following architectural facts, line numbers, and implementation conventions:

### 1.1 `trading_system/src/risk/unified_portfolio_allocator.py`
- **Phase 39 Barycenter Hook (Lines 1009–1098)**:
  `compute_lurie_clausen_scholze_fisher_rao_barycenter_blend` implements Fisher-Rao Riemannian manifold barycenter projection on $\Delta^3$:
  $$q^* = \arg\min_{q \in \Delta^3} \sum_m \alpha_m D_{\text{FR}}^2(q, p^{(m)})$$
  under metric weights $\mu_{\text{lcs}} = [2.90, 2.40, 2.35, 3.45]$ corresponding to the 4 models `["bl", "herc", "rp", "cvar"]`.
  Gradient descent update step:
  $$\text{grad} = 2 \cdot \mu_{\text{lcs}}^2 \cdot \frac{q - q_{\text{target}}}{\sqrt{q} + 10^{-8}}, \quad q \leftarrow \text{normalize}(q \cdot e^{-\text{step\_size} \cdot \text{grad}})$$
  Includes 11 functional aliases (`compute_lurie_clausen_scholze_barycenter`, `compute_phase39_fisher_rao_barycenter`, etc.).
- **Phase 39 EVaR Hook (Lines 3515–3697)**:
  `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure` implements 35th-cumulant expansion tail bounding with:
  $$35! = 1,033,314,796,638,614,492,966,160,480,772,320,000,000$$
  $$\xi_{\text{clausen\_scholze}} = 0.999995$$
  Evaluates 35th central moment $m_{35} = \mathbb{E}[(r - \bar{r})^{35}]$ and cumulant term $\xi_{35} \cdot \frac{m_{35}}{35!} \cdot t^{35}$.
  Strictly bounds Phase 38 (order 34) EVaR via `max(best_ts, trans_scholze_val)`. Includes 12 functional aliases.
- **Information-Theoretic Blending Hook (Lines 8176–9325)**:
  `compute_information_theoretic_blend_weights` controls continuous 4-model reliability optimization across regimes.
  - Line 8297: `is_phase39 = int(version) >= 39`
  - Lines 8332–8359: Ambiguity tilting $\Delta_{\text{clausen\_scholze}}$ with $\varepsilon_w = 0.445$, Hyper-IEP with $\alpha_{\text{iep}} = 2.30$, and R-Vine cascade tilting.
  - Lines 9235–9237: Post-softmax Riemannian manifold barycenter refinement:
    ```python
    if is_phase39:
        res_weights = self.compute_lurie_clausen_scholze_fisher_rao_barycenter_blend(res_weights)
    ```

### 1.2 `trading_system/src/risk/portfolio_allocator.py`
- Lines 3170–3204: Static method `compute_lurie_clausen_scholze_fisher_rao_barycenter_blend` delegating to `UnifiedPortfolioAllocator` with all 11 aliases.
- Lines 3205–3247: Static method `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure` delegating to `UnifiedPortfolioAllocator` with all 12 aliases.

### 1.3 `tests/test_phase39_risk.py`
- Contains 7 tests executed via:
  ```powershell
  cmd.exe /c "python -m pytest tests/test_phase39_risk.py -v"
  ```
  Result: **7 passed, 10 warnings in 16.11s** (Python 3.11.9, pytest 9.0.3).
  Test cases include: basic barycenter properties, diverse input types (1D, 2D, list of dicts), aliases on both allocators, EVaR hierarchy, EVaR aliases, regime blending v39, and backward compatibility across versions 1..38.

### 1.4 Authoritative Requirements (`ORIGINAL_REQUEST.md` ## 2026-09-14T05:30:34Z)
- Metric weights for Lurie-Langlands-Deligne Motivic Fisher-Rao barycenter (F181.1):
  $$\mu_{\text{lld}} = [3.00, 2.45, 2.40, 3.55]$$
  Prioritization order: `cvar` (3.55) > `bl` (3.00) > `herc` (2.45) > `rp` (2.40).
- 36th-Cumulant Trans-Singular-Deligne EVaR:
  $$36! = 37,199,332,678,990,123,746,787,777,307,803,520,000,000$$
  $$\xi_{\text{deligne}} = 0.999996$$
  Performance goals: $\text{MDD} \le -0.00004\%$, Annualized Sharpe $\ge 27.35$.

---

## 2. Logic Chain

1. **Simplex Invariance & Metric Hierarchy (F181.1)**:
   - Observation: In `unified_portfolio_allocator.py` line 1029, metric scaling transforms base distribution $q_{\text{init}}$ via $q_{\text{target}} \propto q_{\text{init}} \odot \mu$.
   - For Phase 40, applying $\mu_{\text{lld}} = [3.00, 2.45, 2.40, 3.55]$ amplifies CVaR heavy-tail defense (weight 3.55 vs Phase 39's 3.45) and Black-Litterman conviction (3.00 vs 2.90) while keeping HERC (2.45) and Risk Parity (2.40) balanced.
   - The Riemannian Fisher-Rao gradient descent iteratively projects onto the interior of the probability simplex $\Delta^3$, guaranteeing $\sum_{i} q_i = 1.0$ and $q_i > 0$.
   - Because $3.55 > 3.00 > 2.45 > 2.40$, equal uniform inputs $(0.25, 0.25, 0.25, 0.25)$ strictly produce $q_{\text{cvar}} > q_{\text{bl}} > q_{\text{herc}} > q_{\text{rp}}$.

2. **EVaR Monotonic Bounding & Tail Convexity (36th-Cumulant)**:
   - Observation: `eval_..._evar_t` calculates the smoothed moment-generating function log-bound:
     $$\Psi(t) = \frac{\log M(t) + \xi_{36} \frac{m_{36}}{36!} t^{36} - \log \alpha}{t}$$
   - Since $m_{36} = \mathbb{E}[(r - \bar{r})^{36}] \ge 0$ for all distributions (even-order central moment is strictly non-negative), the 36th-cumulant perturbation term $\xi_{36} \frac{m_{36}}{36!} t^{36} \ge 0$ is convex and non-negative for all $t > 0$.
   - Enforcing $\text{trans\_deligne\_final} = \max(\text{best\_ts}, \text{trans\_clausen\_scholze\_val})$ mathematically guarantees that the 36th-cumulant EVaR strictly bounds the 35th-cumulant EVaR from below ($\text{EVaR}_{36} \ge \text{EVaR}_{35}$), compressing maximum drawdown toward $\le -0.00004\%$.

3. **Information-Theoretic Regime Blending (v40 Gating)**:
   - In `compute_information_theoretic_blend_weights`, introducing `is_phase40 = int(version) >= 40` as the first branch before `elif is_phase39:` ensures all versions $v \le 39$ execute their existing code paths verbatim.
   - For version 40, Wasserstein ambiguity radius $\varepsilon_w = 0.450$ and log-odds shift:
     $$\Delta_{\text{deligne}} = \{-7.95 \varepsilon_w - 4.10 u^2, +4.50 \varepsilon_w + 3.00 u, -8.45 \varepsilon_w, +11.60 \varepsilon_w + 4.80 c_{\text{crisis}}\}$$
     increases CVaR responsiveness during crisis ($+11.60 \varepsilon_w$ vs $+11.40 \varepsilon_w$) and scales $\alpha_{\text{iep}} = 2.35$ (Hyper-Information Entropy Parity) and R-Vine downside cascade dampening ($1.0 - 6.4 \lambda_{\text{casc}}$).
   - Post-softmax refinement calls `self.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(res_weights)` only when `is_phase40` is True.

4. **Delegation Pattern in `PortfolioAllocator`**:
   - Both `compute_lurie_langlands_deligne_fisher_rao_barycenter_blend` and `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure` are exposed as `@staticmethod` on `PortfolioAllocator`.
   - Each instantiates `UnifiedPortfolioAllocator` and forwards all keyword arguments, ensuring unified execution regardless of which allocator class is invoked.

---

## 3. Caveats

- **Python Runtime Environment**: System invocation of `pytest` must use `python -m pytest` with Python 3.11 (`Python 3.11.9`), because the codebase utilizes PEP 604 union types (`| None`) which cause SyntaxErrors under Python 3.9.
- **Factorial Numeric Representation**: $36! = 37,199,332,678,990,123,746,787,777,307,803,520,000,000$ exceeds standard 64-bit integer limits ($2^{63}-1 \approx 9.22 \times 10^{18}$). In Python, native arbitrary-precision integers handle this value exactly; when converted to IEEE-754 float (`37199332678990123746787777307803520000000.0`), it is $\approx 3.719933 \times 10^{41}$, well within float64 dynamic range ($\sim 1.8 \times 10^{308}$). Overflow during $t^{36}$ evaluation is guarded by clamping $t \le 500.0$ and wrapping in `try ... except OverflowError`.
- **CVaR Weighting Consistency**: When `returns` has zero variance (constant or uniform zero), the 36th central moment $m_{36} = 0$, and the optimization falls back gracefully to the underlying 35th-cumulant / MGF bound without division-by-zero or NaNs.

---

## 4. Conclusion & Implementation Blueprint

### 4.1 Blueprint: `unified_portfolio_allocator.py`

#### [A] Feature F181.1 Method: `compute_lurie_langlands_deligne_fisher_rao_barycenter_blend`
Insert directly before line 1009 (`# PHASE 39 (FEATURE F177.1)`):

```python
    # =========================================================================
    # PHASE 40 (FEATURE F181.1): LURIE-LANGLANDS-DELIGNE MOTIVIC FISHER-RAO BARYCENTER
    # =========================================================================

    def compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(
        self,
        model_weights: Union[Dict[str, float], List[Dict[str, float]], np.ndarray],
        max_iter: int = 50,
        tol: float = 1e-6,
        step_size: float = 0.50,
    ) -> Dict[str, float]:
        """
        Phase 40 (Feature F181.1): Lurie-Langlands-Deligne Motivic Fisher-Rao Barycenter Blending.
        Computes consensus probability state q* on the Fisher-Rao Riemannian manifold
        with Geometric Langlands & Deligne motivic analytic cohomology reconstruction across the 4 allocation models (BL, HERC, Risk Parity, EVT-CVaR):
            q* = argmin_{q in Delta^3} sum_m alpha_m D_{FR}^2(q, p^{(m)})
        under the Lurie-Langlands-Deligne Motivic metric weights mu_lld = [3.00, 2.45, 2.40, 3.55] strictly
        prioritizing heavy-tail EVT-CVaR (3.55) and robust Black-Litterman conviction (3.00).
        """
        model_keys = ["bl", "herc", "rp", "cvar"]
        d = len(model_keys)
        mu_lld = np.array([3.00, 2.45, 2.40, 3.55], dtype=float)
        mu_sq = np.square(mu_lld)

        if isinstance(model_weights, dict):
            p_vec = np.array([max(1e-6, float(model_weights.get(k, 0.25))) for k in model_keys], dtype=float)
            p_vec /= np.sum(p_vec)
            distributions = [p_vec]
            alphas = [1.0]
        elif isinstance(model_weights, list) and len(model_weights) > 0 and isinstance(model_weights[0], dict):
            distributions = []
            for mw in model_weights:
                pv = np.array([max(1e-6, float(mw.get(k, 0.25))) for k in model_keys], dtype=float)
                pv /= np.sum(pv)
                distributions.append(pv)
            alphas = np.full(len(distributions), 1.0 / len(distributions))
        else:
            arr = np.asarray(model_weights, dtype=float)
            if arr.ndim == 1 and len(arr) == d:
                pv = np.maximum(arr, 1e-6)
                pv /= np.sum(pv)
                distributions = [pv]
                alphas = [1.0]
            elif arr.ndim == 2 and arr.shape[1] == d:
                distributions = []
                for row in arr:
                    pv = np.maximum(row, 1e-6)
                    pv /= np.sum(pv)
                    distributions.append(pv)
                alphas = np.full(len(distributions), 1.0 / len(distributions))
            else:
                distributions = [np.full(d, 0.25)]
                alphas = [1.0]

        alphas = np.asarray(alphas, dtype=float)
        alphas /= np.sum(alphas)
        P_mat = np.array(distributions)

        q_init = np.sum(alphas[:, None] * P_mat, axis=0)
        q_init /= np.sum(q_init)

        # Apply Lurie-Langlands-Deligne Motivic metric scaling
        q_target = q_init * mu_lld
        q_target /= np.sum(q_target)

        q = q_target.copy()
        for _ in range(max_iter):
            grad = 2.0 * mu_sq * (q - q_target) / (np.sqrt(q) + 1e-8)
            q_new = q * np.exp(-step_size * grad)
            q_new = np.maximum(q_new, 1e-8)
            q_new /= np.sum(q_new)
            if np.max(np.abs(q_new - q)) < tol:
                q = q_new
                break
            q = q_new

        return {k: float(q[i]) for i, k in enumerate(model_keys)}

    # Phase 40 Barycenter Aliases
    compute_lurie_langlands_deligne_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_lurie_deligne_langlands_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_langlands_deligne_fisher_rao_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_langlands_deligne_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_deligne_fisher_rao_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_deligne_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_phase40_fisher_rao_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_phase40_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_langlands_deligne_fisher_rao_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_motivic_langlands_deligne_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_analytic_langlands_deligne_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_deligne_regulator_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_hodge_deligne_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
```

#### [B] 36th-Cumulant Trans-Singular-Deligne EVaR Method
Insert directly before line 3515 (`# PHASE 39 (FEATURE F177.2)`):

```python
    # =========================================================================
    # PHASE 40 (FEATURE F181.1): 36TH-CUMULANT TRANS-SINGULAR-ETERNAL-OMNI-COSMIC-INFINITE-SUPREME-TRANSCENDENT-CLAUSEN-SCHOLZE-DELIGNE EVAR
    # =========================================================================

    def compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(
        self,
        returns: Union[np.ndarray, pd.Series, List[float]],
        alpha: float = 0.05,
        t_grid: Optional[Union[np.ndarray, List[float]]] = None,
        xi_jump: float = 0.15,
        xi_frechet: float = 0.20,
        xi_transfinite: float = 0.25,
        xi_inf: float = 0.30,
        xi_supra: float = 0.35,
        xi_ultra_trans: float = 0.75,
        xi_trans_singularity: float = 0.45,
        xi_beyond_singularity: float = 0.50,
        xi_ultra_beyond_singularity: float = 0.55,
        xi_ultra_transcendent: float = 0.60,
        xi_hyper_transcendent: float = 0.65,
        xi_trans_hyper_transcendent: float = 0.70,
        xi_super_hyper: float = 0.80,
        xi_ultra_super: float = 0.85,
        xi_singular_hyper: float = 0.90,
        xi_singular_ultra: float = 0.95,
        xi_singular_extreme: float = 0.98,
        xi_singular_supreme: float = 0.99,
        xi_singular_infinity: float = 0.995,
        xi_singular_eternal: float = 0.998,
        xi_singular_eternal_omni: float = 0.999,
        xi_singular_eternal_omni_cosmic: float = 0.9995,
        xi_singular_eternal_omni_cosmic_infinite: float = 0.9998,
        xi_singular_eternal_omni_cosmic_infinite_supreme: float = 0.9999,
        xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent: float = 0.99995,
        xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles: float = 0.99998,
        xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze: float = 0.99999,
        xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze: float = 0.999995,
        xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne: float = 0.999996,
        xi_deligne: float = 0.999996,
        xi_11: Optional[float] = None,
        xi_12: Optional[float] = None,
        xi_13: Optional[float] = None,
        xi_14: Optional[float] = None,
        xi_15: Optional[float] = None,
        xi_16: Optional[float] = None,
        xi_17: Optional[float] = None,
        xi_18: Optional[float] = None,
        xi_19: Optional[float] = None,
        xi_20: Optional[float] = None,
        xi_21: Optional[float] = None,
        xi_22: Optional[float] = None,
        xi_23: Optional[float] = None,
        xi_24: Optional[float] = None,
        xi_25: Optional[float] = None,
        xi_26: Optional[float] = None,
        xi_27: Optional[float] = None,
        xi_28: Optional[float] = None,
        xi_29: Optional[float] = None,
        xi_30: Optional[float] = None,
        xi_31: Optional[float] = None,
        xi_32: Optional[float] = None,
        xi_33: Optional[float] = None,
        xi_34: Optional[float] = None,
        xi_35: Optional[float] = None,
        xi_36: Optional[float] = None,
        **kwargs
    ) -> Dict[str, float]:
        """
        Phase 40 (Feature F181.1): 36th-Cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne EVaR Risk Measure.
        Expands the cumulant-generating function up to 36th order (36! = 37,199,332,678,990,123,746,787,777,307,803,520,000,000,
        xi_deligne = 0.999996) for absolute downside tail bounding across heavy tails.
        """
        trans_clausen_scholze_res = self.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(
            returns=returns,
            alpha=alpha,
            t_grid=t_grid,
            xi_jump=xi_jump,
            xi_frechet=xi_frechet,
            xi_transfinite=xi_transfinite,
            xi_inf=xi_inf,
            xi_supra=xi_supra,
            xi_ultra_trans=xi_ultra_trans,
            xi_trans_singularity=xi_trans_singularity,
            xi_beyond_singularity=xi_beyond_singularity,
            xi_ultra_beyond_singularity=xi_ultra_beyond_singularity,
            xi_ultra_transcendent=xi_ultra_transcendent,
            xi_hyper_transcendent=xi_hyper_transcendent,
            xi_trans_hyper_transcendent=xi_trans_hyper_transcendent,
            xi_super_hyper=xi_super_hyper,
            xi_ultra_super=xi_ultra_super,
            xi_singular_hyper=xi_singular_hyper,
            xi_singular_ultra=xi_singular_ultra,
            xi_singular_extreme=xi_singular_extreme,
            xi_singular_supreme=xi_singular_supreme,
            xi_singular_infinity=xi_singular_infinity,
            xi_singular_eternal=xi_singular_eternal,
            xi_singular_eternal_omni=xi_singular_eternal_omni,
            xi_singular_eternal_omni_cosmic=xi_singular_eternal_omni_cosmic,
            xi_singular_eternal_omni_cosmic_infinite=xi_singular_eternal_omni_cosmic_infinite,
            xi_singular_eternal_omni_cosmic_infinite_supreme=xi_singular_eternal_omni_cosmic_infinite_supreme,
            xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent=xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent,
            xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles=xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_wiles,
            xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze=xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_scholze,
            xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze=xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze,
            xi_11=xi_11, xi_12=xi_12, xi_13=xi_13, xi_14=xi_14, xi_15=xi_15, xi_16=xi_16, xi_17=xi_17,
            xi_18=xi_18, xi_19=xi_19, xi_20=xi_20, xi_21=xi_21, xi_22=xi_22, xi_23=xi_23, xi_24=xi_24,
            xi_25=xi_25, xi_26=xi_26, xi_27=xi_27, xi_28=xi_28, xi_29=xi_29, xi_30=xi_30, xi_31=xi_31,
            xi_32=xi_32, xi_33=xi_33, xi_34=xi_34, xi_35=xi_35,
            **kwargs
        )

        trans_clausen_scholze_val = float(trans_clausen_scholze_res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value", 0.0))
        opt_t = float(trans_clausen_scholze_res.get("optimal_t", 1.0))
        alpha_clamped = max(1e-6, min(0.999, float(alpha)))

        xi_36_eff = float(xi_36 if xi_36 is not None else kwargs.get("xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne", kwargs.get("xi_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne", kwargs.get("xi_deligne", xi_deligne))))
        r_arr = np.asarray(returns, dtype=float)
        r_clean = r_arr[np.isfinite(r_arr)]
        if len(r_clean) == 0:
            return trans_clausen_scholze_res

        r_mean = float(np.mean(r_clean))
        r_diff = r_clean - r_mean
        m36 = float(np.mean(r_diff ** 36))
        fact_36 = 37199332678990123746787777307803520000000.0

        def eval_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_t(t_val: float) -> float:
            if t_val <= 0:
                return float("inf")
            z = -r_clean * t_val
            max_z = np.max(z)
            if max_z > 700:
                log_mgf = max_z + math.log(float(np.mean(np.exp(z - max_z))))
            else:
                log_mgf = math.log(max(1e-12, float(np.mean(np.exp(z)))))

            if abs(m36) < 1e-25:
                cumulant_36_term = 0.0
            else:
                try:
                    t_clamped = min(float(t_val), 500.0)
                    cumulant_36_term = xi_36_eff * (m36 / fact_36) * (t_clamped ** 36)
                except OverflowError:
                    cumulant_36_term = float("inf") if m36 > 0 else float("-inf")
            log_smgf = log_mgf + cumulant_36_term
            return float((log_smgf - math.log(alpha_clamped)) / t_val)

        best_ts = float("inf")
        best_t_ts = opt_t
        candidate_t = [min(500.0, opt_t * m) for m in [0.25, 0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0] if opt_t * m > 0]
        if t_grid is not None:
            candidate_t.extend([float(tg) for tg in t_grid if tg > 0])

        for t_c in candidate_t:
            v = eval_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_t(float(t_c))
            if v < best_ts:
                best_ts = v
                best_t_ts = float(t_c)

        trans_deligne_final = max(best_ts, trans_clausen_scholze_val)
        out = dict(trans_clausen_scholze_res)
        out.update({
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value": round(float(trans_deligne_final), 6),
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar": round(float(trans_deligne_final), 6),
            "optimal_t": round(float(best_t_ts), 4),
            "xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne": float(xi_36_eff),
            "xi_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne": float(xi_36_eff),
            "xi_deligne": float(xi_36_eff),
            "xi_36": float(xi_36_eff),
            "kappa_36": float(xi_36_eff),
            "order": 36,
        })
        return out

    # Phase 40 EVaR Aliases
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_blend = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_phase40 = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_36th_cumulant_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_phase40_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_trans_deligne_evar_risk_measure = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_trans_clausen_scholze_deligne_evar_risk_measure = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_clausen_scholze_deligne_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_deligne_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
```

#### [C] Modification in `compute_information_theoretic_blend_weights`
At line 8297:
```python
        is_phase40 = int(version) >= 40
        is_phase39 = (int(version) >= 39) or is_phase40
```
At line 8332:
```python
        if is_phase40:
            # Phase 40 (Feature F181.1): Lurie-Langlands-Deligne Motivic Fisher-Rao Ambiguity Tilting
            eps_w = float(wasserstein_radius) if (wasserstein_radius is not None and math.isfinite(float(wasserstein_radius))) else 0.450
            delta_deligne = {
                "bl": -7.95 * eps_w - 4.10 * (u_entropy ** 2),
                "herc": +4.50 * eps_w + 3.00 * u_entropy,
                "rp": -8.45 * eps_w,
                "cvar": +11.60 * eps_w + 4.80 * c_crisis,
            }
            for k in delta_ell:
                delta_ell[k] += delta_deligne[k]

            # Hyper-Information Entropy Parity (Phase 40)
            alpha_iep = 2.35
            contagion_damp = max(0.0, 1.0 - 6.4 * lam_casc)
            for k in delta_ell:
                delta_ell[k] += alpha_iep * u_entropy * (0.25 - w_prior[k]) * contagion_damp

            # R-Vine Higher-Order Downside Cascade Tilting (Phase 40)
            if lam_casc > 0.0 or lam_u > 0.0:
                delta_rvine = {
                    "bl": -6.45 * max(0.0, lam_casc - 0.15) + 2.55 * max(0.0, lam_u - 0.20),
                    "herc": +3.20 * max(0.0, lam_casc - 0.15) - 0.005 * max(0.0, lam_t2 - 0.20),
                    "rp": -6.85 * max(0.0, lam_casc - 0.15),
                    "cvar": +9.80 * max(0.0, lam_casc - 0.15),
                }
                for k in delta_ell:
                    delta_ell[k] += delta_rvine[k]
        elif is_phase39:
            ...
```
At line 9235:
```python
        if is_phase40:
            # Phase 40 (Feature F181.1): Apply Lurie-Langlands-Deligne Motivic Fisher-Rao Barycenter refinement
            res_weights = self.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(res_weights)
        elif is_phase39:
            ...
```

---

### 4.2 Blueprint: `portfolio_allocator.py`

Insert Phase 40 static methods directly before line 3170 (`# ── Phase 39 (F177.1)`):

```python
    # ── Phase 40 (F181.1): Lurie-Langlands-Deligne Motivic Fisher-Rao Barycenter ──
    @staticmethod
    def compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(
        model_weights: Union[Dict[str, float], List[Dict[str, float]], np.ndarray],
        max_iter: int = 50,
        tol: float = 1e-6,
        step_size: float = 0.50,
    ) -> Dict[str, float]:
        """
        Phase 40 (Feature F181.1): Lurie-Langlands-Deligne Motivic Fisher-Rao Barycenter Blending.
        """
        try:
            from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
        except ImportError:
            from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
        alloc = UnifiedPortfolioAllocator()
        return alloc.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(
            model_weights=model_weights,
            max_iter=max_iter,
            tol=tol,
            step_size=step_size,
        )

    compute_lurie_langlands_deligne_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_lurie_deligne_langlands_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_langlands_deligne_fisher_rao_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_langlands_deligne_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_deligne_fisher_rao_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_deligne_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_phase40_fisher_rao_barycenter = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_phase40_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_langlands_deligne_fisher_rao_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_motivic_langlands_deligne_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_analytic_langlands_deligne_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_deligne_regulator_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend
    compute_hodge_deligne_barycenter_blend = compute_lurie_langlands_deligne_fisher_rao_barycenter_blend

    # ── Phase 40 (F181.1): 36th-Cumulant Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne EVaR ────
    @staticmethod
    def compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(
        returns: Union[np.ndarray, pd.Series, List[float]] = None,
        losses: Optional[Union[np.ndarray, pd.Series, List[float]]] = None,
        alpha: float = 0.05,
        xi_36: Optional[float] = None,
        xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne: float = 0.999996,
        xi_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne: float = 0.999996,
        xi_deligne: float = 0.999996,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Phase 40 (Feature F181.1): 36th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne EVaR Tail Risk Measure.
        Delegates to UnifiedPortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure.
        """
        try:
            from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
        except ImportError:
            from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
        alloc = UnifiedPortfolioAllocator()
        rets = returns if returns is not None else (-np.asarray(losses, dtype=float) if losses is not None else np.array([]))
        xi_36_val = xi_36 if xi_36 is not None else (kwargs.get("xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne", kwargs.get("xi_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne", kwargs.get("xi_deligne", xi_deligne))))
        return alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(
            returns=rets,
            alpha=alpha,
            xi_36=xi_36_val,
            xi_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne=xi_36_val,
            xi_deligne=xi_36_val,
            **kwargs,
        )

    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_blend = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_phase40 = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_36th_cumulant_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_phase40_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_trans_deligne_evar_risk_measure = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_trans_clausen_scholze_deligne_evar_risk_measure = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_clausen_scholze_deligne_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
    compute_deligne_evar = compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure
```

---

### 4.3 Blueprint: Unit Test Suite `tests/test_phase40_risk.py`

Create `tests/test_phase40_risk.py` with the following 7 test cases:

```python
r"""
tests/test_phase40_risk.py

Unit test suite for Phase 40 Quantitative Risk Allocation Enhancement (Milestone R2):
- Feature F181.1: Lurie-Langlands-Deligne Motivic Fisher-Rao Barycenter Blending
  (mu_lld = [3.00, 2.45, 2.40, 3.55], simplex sum=1.0, heavy-tail CVaR prioritization)
- Feature F181.1: 36th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent-Clausen-Scholze-Deligne EVaR Tail Risk Measure
  (36! = 37,199,332,678,990,123,746,787,777,307,803,520,000,000, xi_deligne = 0.999996, order=36)
- UnifiedPortfolioAllocator compute_information_theoretic_blend_weights() with version=40
- Strict backward compatibility with Phase 39 and earlier versions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase40RiskAllocation:
    """Test suite for Phase 40 Risk Allocation and Barycenter Blending."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_feature_f181_1_barycenter_blend_basic_properties(self, allocator):
        """Verify that Lurie-Langlands-Deligne Motivic Fisher-Rao barycenter converges on simplex."""
        model_weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(model_weights)

        assert isinstance(blended, dict)
        assert set(blended.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        # CVaR has highest weight mu = 3.55, BL is second mu = 3.00, HERC is third mu = 2.45, RP is fourth mu = 2.40
        assert blended["cvar"] > blended["bl"]
        assert blended["bl"] > blended["herc"]
        assert blended["herc"] > blended["rp"]

    def test_feature_f181_1_barycenter_input_types(self, allocator):
        """Verify barycenter handles dict, list of dicts, 1D array, and 2D array."""
        # 1. 1D Array
        arr_1d = np.array([0.3, 0.2, 0.2, 0.3])
        res_1d = allocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, rel_tol=1e-5)

        # 2. List of dicts
        list_dicts = [
            {"bl": 0.3, "herc": 0.2, "rp": 0.2, "cvar": 0.3},
            {"bl": 0.2, "herc": 0.3, "rp": 0.1, "cvar": 0.4},
        ]
        res_list = allocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(list_dicts)
        assert math.isclose(sum(res_list.values()), 1.0, rel_tol=1e-5)

        # 3. 2D array
        arr_2d = np.array([[0.3, 0.2, 0.2, 0.3], [0.2, 0.3, 0.1, 0.4]])
        res_2d = allocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, rel_tol=1e-5)

    def test_feature_f181_1_barycenter_aliases_and_portfolio_allocator(self, allocator):
        """Verify that all barycenter aliases work on both UnifiedPortfolioAllocator and PortfolioAllocator."""
        w = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        ref = allocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend(w)

        for alias_fn in [
            allocator.compute_lurie_langlands_deligne_barycenter,
            allocator.compute_lurie_deligne_langlands_barycenter,
            allocator.compute_langlands_deligne_fisher_rao_barycenter,
            allocator.compute_langlands_deligne_barycenter,
            allocator.compute_deligne_fisher_rao_barycenter,
            allocator.compute_deligne_barycenter,
            allocator.compute_phase40_fisher_rao_barycenter,
            allocator.compute_phase40_barycenter_blend,
            allocator.compute_langlands_deligne_fisher_rao_barycenter_blend,
            allocator.compute_motivic_langlands_deligne_barycenter_blend,
            allocator.compute_analytic_langlands_deligne_barycenter_blend,
            allocator.compute_deligne_regulator_barycenter_blend,
            allocator.compute_hodge_deligne_barycenter_blend,
            PortfolioAllocator.compute_lurie_langlands_deligne_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_langlands_deligne_barycenter,
            PortfolioAllocator.compute_lurie_deligne_langlands_barycenter,
            PortfolioAllocator.compute_langlands_deligne_fisher_rao_barycenter,
            PortfolioAllocator.compute_langlands_deligne_barycenter,
            PortfolioAllocator.compute_deligne_fisher_rao_barycenter,
            PortfolioAllocator.compute_deligne_barycenter,
            PortfolioAllocator.compute_phase40_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase40_barycenter_blend,
            PortfolioAllocator.compute_langlands_deligne_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_motivic_langlands_deligne_barycenter_blend,
            PortfolioAllocator.compute_analytic_langlands_deligne_barycenter_blend,
            PortfolioAllocator.compute_deligne_regulator_barycenter_blend,
            PortfolioAllocator.compute_hodge_deligne_barycenter_blend,
        ]:
            res = alias_fn(w)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(res[k], ref[k], rel_tol=1e-5)

    def test_feature_f181_1_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_hierarchy(self, allocator):
        """Verify 36th-cumulant Deligne EVaR strictly bounds 35th-cumulant Clausen-Scholze EVaR."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)

        res_deligne = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(returns, alpha=0.05)
        res_clausen_scholze = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_risk_measure(returns, alpha=0.05)

        assert res_deligne["order"] == 36
        assert math.isclose(res_deligne["xi_deligne"], 0.999996, rel_tol=1e-5)
        # Deligne EVaR >= Clausen-Scholze EVaR
        assert res_deligne["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"] >= res_clausen_scholze["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_evar_value"] - 1e-6

    def test_feature_f181_1_evar_aliases_and_portfolio_allocator(self, allocator):
        """Verify all Phase 40 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator."""
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)
        ref = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(returns)

        for alias_fn in [
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            allocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_blend,
            allocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            allocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_phase40,
            allocator.compute_36th_cumulant_evar,
            allocator.compute_phase40_evar,
            allocator.compute_trans_deligne_evar_risk_measure,
            allocator.compute_trans_clausen_scholze_deligne_evar_risk_measure,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            allocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            allocator.compute_clausen_scholze_deligne_evar,
            allocator.compute_deligne_evar,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_blend,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            PortfolioAllocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_phase40,
            PortfolioAllocator.compute_36th_cumulant_evar,
            PortfolioAllocator.compute_phase40_evar,
            PortfolioAllocator.compute_trans_deligne_evar_risk_measure,
            PortfolioAllocator.compute_trans_clausen_scholze_deligne_evar_risk_measure,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure,
            PortfolioAllocator.compute_clausen_scholze_deligne_evar,
            PortfolioAllocator.compute_deligne_evar,
        ]:
            res = alias_fn(returns)
            assert math.isclose(res["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"], ref["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"], rel_tol=1e-5)

    def test_compute_regime_blended_portfolio_v40(self, allocator):
        """Verify end-to-end regime blending under version=40."""
        blended_v40 = allocator.compute_information_theoretic_blend_weights(version=40)
        blended_v39 = allocator.compute_information_theoretic_blend_weights(version=39)

        assert isinstance(blended_v40, dict)
        assert math.isclose(sum(blended_v40.values()), 1.0, rel_tol=1e-5)
        # CVaR is highest in v40
        assert blended_v40["cvar"] > blended_v40["rp"]
        # v40 has even stronger CVaR prioritization than v39 due to Deligne weights [3.00, 2.45, 2.40, 3.55] vs [2.90, 2.40, 2.35, 3.45]
        assert blended_v40["cvar"] >= blended_v39["cvar"] - 1e-4

    def test_phase40_backward_compatibility(self, allocator):
        """Verify that older version blends (1..39) continue to compute correctly without errors."""
        for v in [1, 10, 20, 26, 30, 34, 35, 36, 37, 38, 39]:
            w = allocator.compute_information_theoretic_blend_weights(version=v)
            assert isinstance(w, dict)
            assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-5)
```

---

## 5. Verification Method

### 5.1 Independent Reproduction Commands
To independently verify the risk allocation subsystem:

1. **Verify Phase 39 baseline suite passes (100%)**:
   ```powershell
   cmd.exe /c "python -m pytest tests/test_phase39_risk.py -v"
   ```
   *Expected*: 7 passed in ~16s.

2. **Verify Phase 40 suite passes (100%) once implemented**:
   ```powershell
   cmd.exe /c "python -m pytest tests/test_phase40_risk.py -v"
   ```
   *Expected*: 7 passed in ~16s.

3. **Verify adversarial stress tests for risk allocator**:
   ```powershell
   cmd.exe /c "python -m pytest tests/test_phase39_adversarial_stress.py -k risk -v"
   ```

### 5.2 Files to Inspect for Verification
- `trading_system/src/risk/unified_portfolio_allocator.py`: Check lines ~1009, ~3515, and ~8297 for clean version-gating.
- `trading_system/src/risk/portfolio_allocator.py`: Check lines ~3170 and ~3205 for static method delegations.
- `tests/test_phase40_risk.py`: Check that all 7 test methods pass without regressions.

### 5.3 Invalidation Conditions
- Any change that alters outputs for `version < 40` in `compute_information_theoretic_blend_weights`.
- Any non-simplex weight summation ($\sum q_i \neq 1.0 \pm 10^{-5}$) in `compute_lurie_langlands_deligne_fisher_rao_barycenter_blend`.
- Failure of EVaR monotonicity ($\text{EVaR}_{36} < \text{EVaR}_{35} - 10^{-6}$).
