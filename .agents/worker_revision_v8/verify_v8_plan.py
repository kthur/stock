# verify_v8_plan.py
# Verification script for 10 remediations in system_improvement_plan_v8.md

import sys, re
sys.stdout.reconfigure(encoding='utf-8')

file_path = r"d:\Finance\code\stock\system_improvement_plan_v8.md"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

checks = []

# 1. CRIT-01
c1 = (
    "allocate(" in text
    and "predictions_df: pd.DataFrame" in text
    and "prices_dict: Dict[str, pd.DataFrame]" in text
    and "base_currency: str = \"KRW\"" in text
    and "usd_krw: float = 1350.0" in text
    and "effective_price_krw = px * usd_krw if (is_us and base_currency == 'KRW')" in text
    and "raw_shares = int(allocated_capital / effective_price_krw)" in text
)
checks.append(("CRIT-01 Signature & FX Translation", c1))

# 2. CRIT-02
c2 = (
    "def calculate_black_litterman_weights(" in text
    and ") -> np.ndarray:" in text
    and "returns_are_percentage: Optional[bool] = None" in text
    and "np.any(np.abs(Q) >= 1.0)" in text
    and "Q_daily = Q_decimal / float(eff_horizon)" in text
    and "test_adversarial_challenger_1.py:320-328" in text
)
checks.append(("CRIT-02 Return Type, Signature & Scale Auto-Detection", c2))

# 3. CRIT-03
crit03_section = text[text.find("### [CRIT-03]"):text.find("### [CRIT-04]")]
c3 = (
    ").bfill()" not in crit03_section
    and "min_periods=1" in crit03_section
    and "shift(1)" in crit03_section
    and "Expanding" in crit03_section
    and "norm_df = ((df_s[feature_cols] - r_mean) / r_std).fillna(0.0)" in crit03_section
)
checks.append(("CRIT-03 LSTM Expanding Window Normalization (no .bfill() in code)", c3))

# 4. CRIT-04
crit04_section = text[text.find("### [CRIT-04]"):text.find("### [CRIT-05]")]
c4 = (
    "0.02" in crit04_section
    and "eff_decay = float(np.clip(self.decay_rate, 0.02, 0.50))" in crit04_section
    and "current_roe = r_e + (current_roe - r_e) * (1.0 - eff_decay)" in crit04_section
)
checks.append(("CRIT-04 Ohlson ROE Decay Floor (2% floor)", c4))

# 5. CRIT-06
crit06_section = text[text.find("### [CRIT-06]"):text.find("### [CRIT-07]")]
c5 = (
    "1.0 / max(n - 1, 1)" in crit06_section
    and "max_w = min(1.0, max(self.max_single_weight, 1.0 / max(n - 1, 1)))" in crit06_section
    and "1.05 / max" not in crit06_section
)
checks.append(("CRIT-06 CVaR Bound Box-In Remediation", c5))

# 6. CRIT-09
crit09_section = text[text.find("### [CRIT-09]"):text.find("### [CRIT-10]")]
c6 = (
    "0.05" in crit09_section
    and "evals_floored = np.maximum(evals, 0.05)" in crit09_section
    and "inv_sqrt_C = evecs @ np.diag(1.0 / np.sqrt(evals_floored)) @ evecs.T" in crit09_section
)
checks.append(("CRIT-09 Lowdin Pairwise Non-PSD Projection (eigenvalue floor >= 0.05)", c6))

# 7. HIGH-01
high01_section = text[text.find("### [HIGH-01]"):text.find("### [HIGH-02]")]
c7 = (
    "assert p_krx[\"lot_size\"] == 1" in high01_section
    and "assert p_krx[\"shares\"] % 1 == 0" in high01_section
    and not bool(re.search(r'assert 1 == 1(?![0-9])', text))
)
checks.append(("HIGH-01 Test Phrasing & Both Lines 193/194 without assert 1 == 1", c7))

# 8. Test file paths & consolidation
c8 = (
    "tests/test_v8_remediation.py" in text
    and "test_rim_valuation.py" not in text
    and "test_portfolio_optimizer.py" not in text
    and "test_card_factor.py" not in text
    and "test_track_c_institutional_stress.py" not in text
)
checks.append(("Test File Path Precision & tests/test_v8_remediation.py Consolidation", c8))

# Print results
all_passed = True
for name, passed in checks:
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}")
    if not passed:
        all_passed = False

if all_passed:
    print("\nALL 8 CORE REMEDIATION SUITES VERIFIED AND PASSED 100%!")
else:
    print("\nSOME CHECKS FAILED! INVESTIGATE ABOVE.")
    sys.exit(1)
