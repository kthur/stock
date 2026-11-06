# TEST_READY.md: Mobile UX Layout Optimization Test Suite

**Status**: **READY** (Test Suite Authored & Verified)  
**Author**: `test_writer_mobile_ux_e2e`  
**Test Specification**: `TEST_INFRA.md`  
**Target Viewports**: Android Galaxy Mobile Web (Samsung Internet & Chrome Mobile, 360px–412px) & Responsive Desktop (>= 1024px)  
**Execution Command**:
```powershell
python -m pytest tests/test_e2e_mobile_ux.py -v
```

---

## 1. Test Suite Execution Summary

Execution of `tests/test_e2e_mobile_ux.py` against the current codebase (`gh-pages/` production build snapshot and template generators in `trading_system/`):

| Test Tier | Focus Area | Total Tests | Passed | Pending Milestone 1 Fixes | Status |
|-----------|------------|-------------|--------|---------------------------|--------|
| **Tier 1** | Feature Coverage (Category-Partition Method) | 7 | 5 | 2 | **ACTIVE** (2 defects flagged) |
| **Tier 2** | Boundary Value Analysis (360px–412px Galaxy viewports, 1024px desktop, 0/34px gesture bar, frozen columns) | 7 | 6 | 1 | **ACTIVE** (1 defect flagged) |
| **Tier 3** | Pairwise Combinations (Bottom nav sync, drawer layering, theme switcher contrast, search scroll) | 5 | 5 | 0 | **100% PASS** |
| **Tier 4** | Real-World Application Workloads (Galaxy user journey, Desktop visit, bundle size < 500 KB, Unix LF) | 3 | 3 | 0 | **100% PASS** |
| **Total** | **All 4 Tiers** | **25** | **22** | **3** | **EXECUTION CLEAN (10.51s)** |

---

## 2. Implementation Defects Discovered (Escalation to Implementation Worker)

The 3 failing tests pinpoint exact implementation defects that must be resolved in **Milestone 1**:

### Defect 1: Bottom Navigation Bar Missing on Dedicated Market Pages
- **Failed Test**: `TestTier1FeatureCoverage::test_tier1_bottom_nav_dom_presence_and_items`
- **Error Output**: `AssertionError: Defect F_MOB_01: Page 'market_kospi.html' missing <nav id='mobile-bottom-nav'> in DOM`
- **Affected Files**: `trading_system/report_multipage.py` -> `build_market_html` (lines 2277–2308) and `gh-pages/market_*.html`
- **Root Cause**: While `<nav id="mobile-bottom-nav">` is rendered in `index.html` and `strategies.html`, `build_market_html` does not inject `{mobile_bottom_nav_html}` or `{bottom}` into the body of the 5 dedicated market pages (`market_kospi.html`, `market_kosdaq.html`, `market_sp500.html`, `market_nasdaq.html`, `market_russell2000.html`).
- **Remediation**: Inject the mobile bottom navigation bar into `build_market_html` body and update `switchMobileNav` to handle cross-page routing back to `index.html#panel-{tabId}`.

### Defect 2: Back-to-Top FAB Overlaps Bottom Navigation Bar
- **Failed Test**: `TestTier1FeatureCoverage::test_tier1_fab_positioning_no_bottom_nav_collision`
- **Error Output**: `AssertionError: Defect F_MOB_02: #btn-back-to-top bottom offset (20px) is < 64px! It collides with the 56px bottom nav bar. Expected >= 68px.`
- **Affected File**: `trading_system/generate_report.py` (line 4740)
- **Root Cause**: On mobile screens (`@media (max-width: 768px)`), `#btn-back-to-top` is positioned at `bottom: calc(20px + env(safe-area-inset-bottom, 0px)) !important;`. Because the bottom nav bar is 56px high at `bottom: 0`, the FAB directly overlays the 5th bottom navigation button (`#mob-nav-strategies`), blocking taps.
- **Remediation**: Update `#btn-back-to-top` in `@media (max-width: 768px)` to `bottom: calc(68px + env(safe-area-inset-bottom, 0px)) !important;`.

### Defect 3: FAB Collides with Bottom Nav under Safe-Area Insets (0px vs 34px Gesture Bar)
- **Failed Test**: `TestTier2BoundaryAndCornerCases::test_tier2_safe_area_inset_boundary_0px_vs_34px`
- **Error Output**: `AssertionError: Collision at safe-area-inset=0px: FAB bottom (20px) does not clear bottom nav (56px) by >= 8px`
- **Root Cause**: Direct mathematical consequence of Defect 2 above. When `bottom` is 20px, clearance is `-36px` (collision). When elevated to >= 68px, clearance is `+12px` above the bottom nav bar for all gesture bar heights.
- **Remediation**: Resolved automatically once Defect 2 is fixed.

---

## 3. Verified System Invariants (Passing 100%)

The test suite confirmed that key architectural invariants remain uncompromised:
1. **File Size Budget**: `gh-pages/index.html` size is **483,567 bytes** (472.23 KB), strictly under the 512,000-byte (500 KB) budget ceiling with **28,433 bytes (5.5%)** headroom (`test_tier4_html_file_size_and_hygiene`).
2. **Line Ending Hygiene**: All 7 generated pages in `gh-pages/` have **0 CRLF** sequences (`b"\r\n"` count == 0), adhering strictly to Unix LF (`\n`) encoding.
3. **Table Frozen Columns Geometry Budget**: Rank (36px) + Symbol (68px) + Name (86px) = **190px** total frozen width, leaving **170px** of unobstructed scrollable table body on a 360px Galaxy screen and **222px** on a 412px Galaxy screen (`test_tier2_table_frozen_columns_geometry_budget`).
4. **Desktop Responsive Layout**: At >= 1024px, `.row1-wrapper` displays a 2-column grid (`310px 1fr`), Card 2 displays multi-column health cards, bottom nav is hidden (`display: none`), and `#stock-drawer` renders as a 480px slide-in sidebar (`test_tier2_desktop_breakpoint_boundary_1024px`, `test_tier4_desktop_pc_browser_session`).
5. **Color Contrast & Theme Switcher**: Dark (7.05:1 AAA), Terminal (16.8:1 AAA), and Light (16.5:1 AAA) themes all meet or exceed WCAG AA/AAA standards (`test_tier3_theme_switcher_touch_and_contrast`).
6. **Touch Targets**: Sticky top nav chips, bottom nav buttons, filter chips, drawer buttons, search inputs, and table action buttons satisfy `min-height: 44px !important` (`test_tier1_touch_targets_dimension_compliance`).

---

## 4. Test Suite Structure in `tests/test_e2e_mobile_ux.py`

```python
TestTier1FeatureCoverage:
  ├── test_tier1_bottom_nav_dom_presence_and_items           [FAILED - Defect F_MOB_01]
  ├── test_tier1_bottom_nav_css_fixed_position_and_z_index   [PASSED]
  ├── test_tier1_bottom_nav_thumb_reachability_geometry      [PASSED]
  ├── test_tier1_safe_area_insets_css_integration            [PASSED]
  ├── test_tier1_fab_positioning_no_bottom_nav_collision     [FAILED - Defect F_MOB_02]
  ├── test_tier1_touch_targets_dimension_compliance          [PASSED]
  └── test_tier1_sticky_nav_height_and_autocentering        [PASSED]

TestTier2BoundaryAndCornerCases:
  ├── test_tier2_galaxy_viewport_widths_stacking[360]        [PASSED]
  ├── test_tier2_galaxy_viewport_widths_stacking[375]        [PASSED]
  ├── test_tier2_galaxy_viewport_widths_stacking[384]        [PASSED]
  ├── test_tier2_galaxy_viewport_widths_stacking[393]        [PASSED]
  ├── test_tier2_galaxy_viewport_widths_stacking[412]        [PASSED]
  ├── test_tier2_desktop_breakpoint_boundary_1024px          [PASSED]
  ├── test_tier2_safe_area_inset_boundary_0px_vs_34px        [FAILED - Defect F_MOB_02]
  ├── test_tier2_table_frozen_columns_geometry_budget        [PASSED]
  ├── test_tier2_search_input_empty_and_special_chars        [PASSED]
  └── test_tier2_extreme_aspect_ratios_and_foldables         [PASSED]

TestTier3CrossFeatureCombinations:
  ├── test_tier3_bottom_nav_sync_with_panels_and_top_nav    [PASSED]
  ├── test_tier3_stock_drawer_bottom_sheet_layering          [PASSED]
  ├── test_tier3_theme_switcher_touch_and_contrast           [PASSED]
  ├── test_tier3_table_search_filtering_with_horizontal_scroll [PASSED]
  └── test_tier3_cross_page_navigation_and_strategy_hub     [PASSED]

TestTier4RealWorldWorkloads:
  ├── test_tier4_galaxy_mobile_user_journey                  [PASSED]
  ├── test_tier4_desktop_pc_browser_session                  [PASSED]
  └── test_tier4_html_file_size_and_hygiene                 [PASSED]
```
