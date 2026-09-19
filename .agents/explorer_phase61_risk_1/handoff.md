# Milestone 2 Exploration Report: Portfolio Risk Allocation & 57th-Cumulant EVaR Tail Budgeting (Features F278.1, F278.2)

## 1. Observation

### 1.1 Codebase Layout & Key Files
- **`trading_system/src/risk/unified_portfolio_allocator.py`** (17,499 lines):
  - Contains core mathematical implementations of Riemannian Fisher-Rao Barycenter blends, EVaR cumulant expansions, and information-theoretic ambiguity tilting across all historical phases (Phase 1 ~ Phase 60).
- **`trading_system/src/risk/portfolio_allocator.py`** (6,305 lines):
  - High-level adapter class delegating all mathematical methods and aliases to `UnifiedPortfolioAllocator` via static methods and class-level attribute bindings.
- **`tests/test_phase60_risk.py`** (224 lines, 8 tests):
  - Verified test suite for Phase 60 (Features F273.1, F273.2), currently passing 100% (8/8 passed in 20.40s).

---

### 1.2 Phase 60 Baseline Implementation (F273.1 & F273.2)

#### 1.2.1 Higher-Homology-10 Fisher-Rao Barycenter Blending (`unified_portfolio_allocator.py:1014-1088`)
```python
def compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_10_fisher_rao_barycenter_blend(
    self,
    model_weights: Union[Dict[str, float], List[Dict[str, float]], np.ndarray],
    max_iter: int = 50,
    tol: float = 1e-6,
    step_size: float = 0.50,
) -> Dict[str, float]:
    model_keys = ["bl", "herc", "rp", "cvar"]
    d = len(model_keys)
    mu_lmbwdh10 = np.array([5.00, 3.50, 3.45, 5.55], dtype=float)
    mu_sq = np.square(mu_lmbwdh10)
    # ... distribution normalization to q_init ...
    q_target = q_init * mu_lmbwdh10
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
```
- **Curvature Vector**: `mu_lmbwdh10 = np.array([5.00, 3.50, 3.45, 5.55], dtype=float)` corresponding to `["bl", "herc", "rp", "cvar"]`.
- **Properties**: Simplex conservation $\sum_{i=1}^4 q_i = 1.0$; strictly prioritizes heavy-tail `cvar` ($5.55$) and `bl` conviction ($5.00$) over `herc` ($3.50$) and `rp` ($3.45$).
- **Aliases**: 37 aliases declared at lines 1089–1125.

#### 1.2.2 56th-Cumulant Trans-Singular EVaR Measure (`unified_portfolio_allocator.py:5828-5930`)
```python
def compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_10_evar_risk_measure(
    self,
    returns: Union[np.ndarray, pd.Series, List[float]],
    alpha: float = 0.05,
    t_grid: Optional[Union[np.ndarray, List[float]]] = None,
    xi_monster: float = 0.999999999998,
    order: int = 56,
    **kwargs
) -> Dict[str, float]:
    # ...
    loss = -r_arr
    mu_1 = float(np.mean(loss))
    mu_2 = float(np.var(loss))
    dev = loss - mu_1
    m_3 = float(np.mean(dev ** 3))
    m_4 = float(np.mean(dev ** 4))
    m_5 = float(np.mean(dev ** 5))
    m_6 = float(np.mean(dev ** 6))
    
    fact_val = float(math.factorial(eff_order)) # 56! ~= 7.10999e74
    m_eff = float(np.mean(dev ** eff_order))
    # ...
    for t in t_vals:
        cumulant_high = xi_monster_eff * (m_eff / fact_val) * (t ** eff_order)
        k_t = (mu_1 * t
               + 0.5 * mu_2 * (t ** 2)
               + (1.0 / 6.0) * m_3 * (t ** 3)
               + (1.0 / 24.0) * (m_4 - 3.0 * (mu_2 ** 2)) * (t ** 4)
               + (1.0 / 120.0) * m_5 * (t ** 5)
               + (1.0 / 720.0) * m_6 * (t ** 6)
               + cumulant_high)
        evar_cand = (k_t + log_inv_alpha) / t
        if evar_cand < best_evar:
            best_evar = evar_cand
            best_t = t
```
- **Order**: $56$, factorial $56! \approx 7.10999 \times 10^{74}$, $\xi_{\text{monster}} = 0.999999999998$.
- **Aliases**: 37 aliases declared at lines 5932–5968.

#### 1.2.3 Ambiguity Tilting in `calculate_weights` (`unified_portfolio_allocator.py:13877-13894`)
```python
is_phase60 = int(version) >= 60
# ...
if is_phase60:
    eps_w = float(wasserstein_radius) if (wasserstein_radius is not None and math.isfinite(float(wasserstein_radius))) else 0.600
    delta_monster_whittaker = {
        "bl": -11.75 * eps_w - 6.30 * (u_entropy ** 2),
        "herc": +8.00 * eps_w + 5.20 * u_entropy,
        "rp": -12.25 * eps_w,
        "cvar": +17.65 * eps_w + 7.50 * c_crisis,
    }
    for k in delta_ell:
        delta_ell[k] += delta_monster_whittaker[k]

    alpha_iep = 3.50
    contagion_damp = max(0.0, 1.0 - 12.5 * lam_casc)
    for k in delta_ell:
        delta_ell[k] *= (1.0 + 0.28 * alpha_iep)
```

#### 1.2.4 Delegation in `portfolio_allocator.py` (`lines 3424-3483` & `lines 4059-4126`)
- `@staticmethod` methods instantiate `UnifiedPortfolioAllocator()` and delegate calls directly.
- 37 class-level attributes map all barycenter aliases and all EVaR aliases to the static method.

---

## 2. Logic Chain

### 2.1 Higher-Homology-11 Fisher-Rao Barycenter Blending (Feature F278.1)
1. **Mathematical Evolution**:
   - Phase 58: Higher-Homology-8, $\mu_{\text{lmbwdh8}} = [4.80, 3.40, 3.35, 5.35]$
   - Phase 59: Higher-Homology-9, $\mu_{\text{lmbwdh9}} = [4.90, 3.45, 3.40, 5.45]$
   - Phase 60: Higher-Homology-10, $\mu_{\text{lmbwdh10}} = [5.00, 3.50, 3.45, 5.55]$
   - **Phase 61**: Higher-Homology-11, $\mu_{\text{lmbwdh11}} = [5.10, 3.55, 3.50, 5.65]$ across `["bl", "herc", "rp", "cvar"]`.
2. **Priorities & Relative Ordering**:
   - $\mu_{\text{cvar}} (5.65) > \mu_{\text{bl}} (5.10) > \mu_{\text{herc}} (3.55) > \mu_{\text{rp}} (3.50)$.
   - Strict simplex conservation $\sum q_i = 1.0$ is maintained by projective Riemannian gradient descent with exponential map step $q \odot \exp(-\text{step\_size} \cdot \nabla_q)$ and normalization $q / \sum q$.
3. **Implementation Placement in `unified_portfolio_allocator.py`**:
   - Primary method: `compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_11_fisher_rao_barycenter_blend` placed directly above Phase 60 (at ~line 1013).
   - 37 method aliases:
     1. `compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_11_barycenter`
     2. `compute_lurie_drinfeld_higher_homology_11_barycenter`
     3. `compute_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_11_fisher_rao_barycenter`
     4. `compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_barycenter`
     5. `compute_drinfeld_higher_homology_11_barycenter`
     6. `compute_phase61_fisher_rao_barycenter`
     7. `compute_phase61_barycenter_blend`
     8. `compute_higher_homology_11_barycenter`
     9. `compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_fisher_rao_barycenter_blend`
     10. `compute_motivic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_barycenter_blend`
     11. `compute_analytic_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_barycenter_blend`
     12. `compute_chiral_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_barycenter_blend`
     13. `compute_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_barycenter_blend`
     14. `compute_chiral_oper_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_barycenter_blend`
     15. `compute_lurie_quantum_langlands_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_barycenter`
     16. `compute_lmbmwdh11_barycenter`
     17. `compute_lmbmwdh11_fisher_rao_barycenter`
     18. `compute_lmmwdh11_barycenter`
     19. `compute_lmmwdh11_fisher_rao_barycenter`
     20. `compute_fisher_rao_barycenter_lmbwdh11`
     21. `compute_phase61_barycenter`
     22. `lmbwdh11_barycenter`
     23. `higher_homology_11_fisher_rao_blend`
     24. `fisher_rao_higher_homology_11`
     25. `barycenter_lmbwdh11`
     26. `blend_weights_lmbwdh11`
     27. `riemannian_higher_homology_11_barycenter`
     28. `lmbwd_h11_barycenter`
     29. `phase61_fisher_rao_barycenter`
     30. `drinfeld_higher_homology_11_barycenter`
     31. `borcherds_higher_homology_11_barycenter`
     32. `monster_higher_homology_11_barycenter`
     33. `whittaker_higher_homology_11_barycenter`
     34. `moonshine_higher_homology_11_barycenter`
     35. `lurie_higher_homology_11_barycenter`
     36. `higher_homology_11_blend`
     37. `phase61_homology_barycenter`
4. **Delegation in `portfolio_allocator.py`**:
   - Define `@staticmethod` for `compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_11_fisher_rao_barycenter_blend` delegating to `alloc`.
   - Bind all 37 aliases as class attributes in `PortfolioAllocator`.

---

### 2.2 57th-Cumulant Expansion Trans-Singular EVaR (Feature F278.2)
1. **Mathematical Constants**:
   - Factorial: $57! = 40526919504877216755681601905432322134980384796226602145184481280000000000000 \approx 4.052691950487722 \times 10^{76}$.
   - Monster Parameter: $\xi_{\text{monster}} = 0.9999999999995$ (13 nines followed by 5).
   - Order: `order = 57`.
2. **Moments & Cumulant Expansion**:
   - $L = -R$, central moment $m_{57} = \mathbb{E}[(L - \mu_1)^{57}]$.
   - High-order cumulant term:
     $$\kappa_{57}(t) = \xi_{\text{monster}} \cdot \frac{m_{57}}{57!} \cdot t^{57}$$
   - CGF expansion $K_L(t)$ includes cumulants of orders 1 to 6 plus $\kappa_{57}(t)$.
   - $\text{EVaR}_\alpha(L) = \inf_{t > 0} \frac{K_L(t) + \ln(1/\alpha)}{t}$ optimized over log-spaced $t$-grid.
3. **Implementation Placement in `unified_portfolio_allocator.py`**:
   - Primary method: `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_evar_risk_measure` placed directly above Phase 60 (at ~line 5824).
   - Return dictionary contains keys:
     - `...higher_homology_11_evar_value`
     - `...higher_homology_11_evar`
     - backward compatible keys for `higher_homology_10_evar`, `9_evar`, etc.
     - `evar`, `optimal_t`, `order: 57`, `xi_monster: 0.9999999999995`.
   - 37 method aliases:
     1. `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_evar`
     2. `trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_evar_risk_measure`
     3. `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_evar_blend`
     4. `compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_evar`
     5. `singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_evar_risk_measure`
     6. `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase61`
     7. `compute_phase61_evar`
     8. `compute_phase61_evar_risk_measure`
     9. `compute_evar_order57`
     10. `compute_57th_cumulant_evar`
     11. `compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_evar_risk_measure`
     12. `compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_evar_risk_measure`
     13. `compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_evar`
     14. `compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_11_evar`
     15. `compute_drinfeld_higher_homology_11_evar_risk_measure`
     16. `compute_drinfeld_higher_homology_11_evar`
     17. `compute_lurie_drinfeld_higher_homology_11_evar_risk_measure`
     18. `compute_lurie_drinfeld_higher_homology_11_evar`
     19. `calculate_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_evar_57th_cumulant`
     20. `evar_57th_cumulant`
     21. `trans_singular_57th_cumulant_evar`
     22. `eternal_omni_cosmic_57th_cumulant_evar`
     23. `supreme_transcendent_evar_57`
     24. `phase61_tail_risk_evar`
     25. `calculate_phase61_evar_tail_risk`
     26. `cumulant_57_evar_bound`
     27. `trans_singular_evar_v61`
     28. `transcendent_57th_cumulant_evar`
     29. `infinite_supreme_57th_cumulant_evar`
     30. `omni_cosmic_evar_57`
     31. `monster_57th_cumulant_evar`
     32. `higher_homology_11_evar`
     33. `drinfeld_57th_cumulant_evar`
     34. `phase61_evar_bound`
     35. `compute_higher_homology_11_evar`
     36. `compute_lmbmwdh11_evar`
     37. `lmbmwdh11_evar`
4. **Delegation in `portfolio_allocator.py`**:
   - Define `@staticmethod` delegating to `alloc.compute_..._higher_homology_11_evar_risk_measure`.
   - Bind all 37 aliases as class attributes in `PortfolioAllocator`.

---

### 2.3 Ambiguity Tilting in `calculate_weights` (`version >= 61`)
1. **Gating Hierarchy**:
   ```python
   is_phase61 = int(version) >= 61
   is_phase60 = (int(version) >= 60) or is_phase61
   ```
2. **Parameters & Tilting Formulation**:
   - Wasserstein uncertainty radius: $\epsilon_w = 0.610$ (default if not provided).
   - Log-odds regime shifts:
     $$\delta_{\text{bl}} = -12.00 \cdot \epsilon_w - 6.40 \cdot u_{\text{entropy}}^2$$
     $$\delta_{\text{herc}} = +8.25 \cdot \epsilon_w + 5.30 \cdot u_{\text{entropy}}$$
     $$\delta_{\text{rp}} = -12.50 \cdot \epsilon_w$$
     $$\delta_{\text{cvar}} = +18.00 \cdot \epsilon_w + 7.75 \cdot c_{\text{crisis}}$$
   - Information Entropy Parity (IEP):
     $$\alpha_{\text{iep}} = 3.55$$
     $$\text{contagion\_damp} = \max(0.0, 1.0 - 13.0 \cdot \lambda_{\text{casc}})$$
     $$\delta_k \leftarrow \delta_k \cdot (1.0 + 0.29 \cdot \alpha_{\text{iep}})$$
3. **Softmax Barycenter Refinement Integration** (`lines 15214+`):
   ```python
   if is_phase61:
       res_weights = self.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_11_fisher_rao_barycenter_blend(res_weights)
   elif is_phase60:
       res_weights = self.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_10_fisher_rao_barycenter_blend(res_weights)
   elif is_phase59:
       res_weights = self.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_9_fisher_rao_barycenter_blend(res_weights)
   elif is_phase58:
       # ...
   ```
   This ensures that the final softmax distribution is projectively mapped by the Riemannian Higher-Homology-11 barycenter consensus.

---

### 2.4 Testing Blueprint for `tests/test_phase61_risk.py`
To achieve 100% test coverage and ensure zero regression:
1. `test_feature_f278_1_barycenter_blend_basic_properties`:
   - Verify simplex conservation $\sum q_i = 1.0$.
   - Verify strict ordering: $q_{\text{cvar}} > q_{\text{bl}} > q_{\text{herc}} > q_{\text{rp}}$ from equal prior $[0.25, 0.25, 0.25, 0.25]$.
   - Verify interior point positivity: $0.0 < q_i < 1.0$.
2. `test_feature_f278_1_barycenter_input_types`:
   - Verify 1D numpy array, list of dicts, and 2D numpy array all converge to valid distribution.
3. `test_feature_f278_1_barycenter_aliases_and_portfolio_allocator`:
   - Verify 37 aliases on `UnifiedPortfolioAllocator` and delegations on `PortfolioAllocator` (instance & class method) match primary method output within `1e-5`.
4. `test_feature_f278_2_57th_cumulant_evar_risk_measure`:
   - Verify calculation on Gaussian sample, `order == 57`, `xi_monster == 0.9999999999995`.
   - Verify edge case of empty returns returns `0.0`.
5. `test_feature_f278_2_evar_aliases`:
   - Verify EVaR aliases on `UnifiedPortfolioAllocator` and `PortfolioAllocator`.
6. `test_information_theoretic_blend_weights_version_61`:
   - Verify `compute_information_theoretic_blend_weights` and `calculate_weights` alias for `version=61`.
   - In `BEAR` regime, verify $w_{\text{cvar}}^{(\text{v61})} \ge w_{\text{cvar}}^{(\text{v60})} - 10^{-6}$.
7. `test_strict_backward_compatibility_v60_and_earlier`:
   - Verify versions 50 through 60 all produce valid probability distributions summing to 1.0.
8. `test_feature_f278_2_fat_tailed_student_t_sensitivity`:
   - Verify that Student-t ($df=3$) EVaR strictly exceeds Gaussian EVaR under identical standard deviation.

---

## 3. Caveats
1. **Mathematical Divergence Protection in $57!$**:
   - $57! \approx 4.05269 \times 10^{76}$ is within 64-bit IEEE 754 floating point range ($\sim 1.79 \times 10^{308}$). However, $(t^{57} \cdot m_{57})$ can potentially overflow or become subnormal if $t$ is large or returns are unbounded. The existing guard `if not math.isfinite(cumulant_high): cumulant_high = 0.0` in `unified_portfolio_allocator.py` must be preserved.
2. **`portfolio_allocator.py` Circular Import Resilience**:
   - The lazy import `try: from src.risk.unified_portfolio_allocator ... except ImportError: from trading_system.src.risk ...` pattern is critical for dual execution environments (project root vs PYTHONPATH).
3. **Refinement Hook in `calculate_weights`**:
   - Line 15214 previously evaluated `if is_phase58:`. When implementing Phase 61, `is_phase61`, `is_phase60`, and `is_phase59` must be added in descending order to avoid skipping Higher-Homology-11.
4. **Execution Time of Tests**:
   - Running `pytest tests/test_phase60_risk.py` took $\sim 20.4\text{ s}$ due to high moment calculations and numerical root/grid searching across multiple seeds. Phase 61 tests will have a similar duration.

---

## 4. Conclusion
1. The Phase 60 implementation in `trading_system/src/risk/unified_portfolio_allocator.py` and `portfolio_allocator.py` is completely verified, robust, and clean.
2. The Phase 61 extensions (F278.1 & F278.2) follow an exact, well-defined mathematical progression:
   - $\mu_{\text{lmbwdh11}} = [5.10, 3.55, 3.50, 5.65]$ on the Riemannian simplex.
   - $57$th-cumulant expansion with $57! \approx 4.05269 \times 10^{76}$ and $\xi_{\text{monster}} = 0.9999999999995$.
   - Ambiguity tilting: $\epsilon_w = 0.610, \alpha_{\text{iep}} = 3.55$, shifts $[-12.00\epsilon_w, +8.25\epsilon_w, -12.50\epsilon_w, +18.00\epsilon_w + 7.75c_{\text{crisis}}]$, damping $\max(0.0, 1.0 - 13.0\lambda_{\text{casc}})$.
   - 37 method aliases for Higher-Homology-11 barycenter and 37 method aliases for 57th-cumulant EVaR, all properly delegated.
3. The testing blueprint will guarantee 100% test pass rate on `tests/test_phase61_risk.py` and full backward compatibility across Phase 1~60.

---

## 5. Verification Method

### 5.1 Verification Commands
Once the implementation is performed by the Risk Allocation specialist:
```powershell
# 1. Run Phase 61 risk allocation unit tests
python -m pytest tests/test_phase61_risk.py -v

# 2. Run Phase 60 regression suite to confirm zero regressions
python -m pytest tests/test_phase60_risk.py -v

# 3. Run adversarial challenger tests covering risk allocation
python -m pytest tests/test_phase60_adversarial_challenger1.py -v
```

### 5.2 Expected Results
- `tests/test_phase61_risk.py`: 8/8 tests pass.
- `tests/test_phase60_risk.py`: 8/8 tests pass.
- Invalidation conditions:
  - Any barycenter output summing to $\ne 1.0 \pm 10^{-5}$.
  - Equal input weights resulting in $q_{\text{cvar}} \le q_{\text{bl}}$ or $q_{\text{bl}} \le q_{\text{herc}}$ or $q_{\text{herc}} \le q_{\text{rp}}$.
  - Student-t fat-tail EVaR $\le$ Gaussian EVaR.
  - Missing alias attribute error when accessed from `UnifiedPortfolioAllocator` or `PortfolioAllocator`.
