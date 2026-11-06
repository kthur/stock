# TEST_INFRA.md: 4-Tier Test Architecture for Mobile UX & Responsive Dashboard

> **Target Platform**: Android Galaxy Mobile Web (Samsung Internet & Chrome Mobile, 360px–412px viewports) & Responsive Desktop (>= 1024px)  
> **Deployment Target**: `gh-pages/` (Executive Summary `index.html`, Technical Encyclopedia `strategies.html`, Market Universe Pages `market_*.html`)  
> **Hard Invariants**: `gh-pages/index.html` size < 512,000 bytes (500 KB), Unix LF (`\n`) only, Touch Targets >= 44px, Zero Horizontal Blowout

---

## 1. System Under Test (SUT) & Architectural Topology

The Stock Trading System Web Dashboard delivers institutional quantitative insights (37 multi-factor strategies, 2D regime gating, HRP portfolio construction, 30-year compounding benchmark) across 5 markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, Russell 2000).

```
                                  [User Access]
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
        [Android Galaxy Mobile Web]                 [Desktop PC Browser]
            - Viewports: 360px–412px                    - Viewport: >= 1024px
            - Single-hand thumb zone                    - Mouse & keyboard focus
            - Gesture bar (0px–34px)                    - 2-Column Grid (310px + 1fr)
                    │                                       │
                    ▼                                       ▼
      ┌───────────────────────────┐           ┌───────────────────────────┐
      │     Navigation Layer      │           │     Navigation Layer      │
      │ - Top Sticky Nav (<=56px) │           │ - Top Sticky Nav (Full)   │
      │ - Bottom Nav (Fixed 56px) │           │ - Bottom Nav: display:none│
      │ - FAB: bottom: 68px+safe  │           │ - FAB: bottom: 24px       │
      └─────────────┬─────────────┘           └─────────────┬─────────────┘
                    │                                       │
                    ▼                                       ▼
      ┌───────────────────────────┐           ┌───────────────────────────┐
      │     Content Containers    │           │     Content Containers    │
      │ - Single-column stacking  │           │ - Multi-column card grids │
      │ - 188px frozen columns    │           │ - Unrestricted wide tables│
      │ - 172px+ scrollable body  │           │ - 480px slide-in sidebar  │
      │ - 90vh bottom-sheet drawer│           │ - Hover/keyboard tooltips │
      └───────────────────────────┘           └───────────────────────────┘
```

### Static Page Inventory (`gh-pages/`):
1. `index.html`: Executive Summary Dashboard (< 500 KB budget, regime matrix, strategy health, HRP portfolio, top picks).
2. `strategies.html`: 37-Strategy Technical Encyclopedia & Live Ranking Tabs (MathJax LaTeX, candidate tables).
3. `market_kospi.html`: Dedicated 42-column universe ranking table for KOSPI.
4. `market_kosdaq.html`: Dedicated 42-column universe ranking table for KOSDAQ.
5. `market_sp500.html`: Dedicated 42-column universe ranking table for S&P 500.
6. `market_nasdaq.html`: Dedicated 42-column universe ranking table for NASDAQ.
7. `market_russell2000.html`: Dedicated 42-column universe ranking table for Russell 2000.

---

## 2. 4-Tier Test Architecture Overview

The test architecture is structured into four progressive tiers designed to test functional correctness, boundary limits, cross-feature interactions, and realistic end-to-end user workflows.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Tier 4: Real-World Application Workloads & Journeys                         │
│ - Galaxy Mobile User Session (Landing -> Portfolio -> Drawer -> Hub)        │
│ - Desktop PC Browser Full-Readability Session (Grid, Sidebar, Shortcuts)   │
│ - Bundle Size (< 512,000 bytes) & Unix LF Encoding Invariant Guard          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tier 3: Pairwise Combinations & Cross-Feature Interactions                  │
│ - Bottom Nav Active State Syncing with Top Sticky Nav & Tab Panels         │
│ - Stock Detail Drawer (Bottom Sheet) & Bottom Nav Z-Index Layering          │
│ - Theme Switcher (Dark/Terminal/Light) x Touch Target x Contrast Ratios     │
│ - Table Search Filtering x Horizontal Scroll x Sticky Column Geometry       │
│ - Cross-Page Deep-Linking (strategies.html <-> index.html#panel-{tabId})    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tier 2: Boundary Value Analysis (BVA) & Corner Cases                        │
│ - Galaxy Viewports: 360px, 375px, 384px, 393px, 412px                      │
│ - Breakpoint Transition Boundary: 1023px vs 1024px Desktop Threshold        │
│ - Safe-Area Inset: 0px (standard) vs 34px (gesture navigation pill bar)     │
│ - Table Frozen Columns Budget: Rank+Symbol+Name <= 190px (leaves >= 170px)  │
│ - Search Input Corner Cases: Empty string, whitespace, regex special chars  │
│ - Extreme Aspect Ratios: Ultra-tall 20:9/21:9 & Foldable Unfolded Aspect    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tier 1: Feature Coverage (Category-Partition Method)                       │
│ - Bottom Nav Presence, 5 Core Items, Fixed Positioning, Z-Index, Thumb Zone │
│ - Interactive Touch Targets >= 44px (Buttons, Links, Tabs, Pills, Inputs)   │
│ - Safe-Area Inset CSS declarations on Bottom Nav, FAB, and Body Padding     │
│ - Top Sticky Nav Header (<=56px height, nowrap carousel, auto-centering)    │
│ - Back-to-Top FAB Collision Resolution (bottom >= 68px on mobile)           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Specifications per Tier

### Tier 1: Feature Coverage (Category-Partition Method)

Tier 1 partitions each functional requirement into discrete input categories and verifies that every individual UI/UX component satisfies its specification in isolation.

| Component / Feature | Category & Partitions | Expected Value / Behavior | Test ID |
|---------------------|----------------------|---------------------------|---------|
| **Bottom Navigation Bar** | Presence across pages | DOM element `<nav id="mobile-bottom-nav" class="mobile-bottom-nav">` present on `index.html`, `strategies.html`, and `market_*.html`. | `test_tier1_bottom_nav_dom_presence` |
| **Bottom Nav Items** | 5 Thumb-Reachable Items | Exactly 5 buttons with IDs: `#mob-nav-ensemble`, `#mob-nav-portfolio`, `#mob-nav-backtest`, `#mob-nav-regime`, `#mob-nav-strategies`. Icons (`.mob-nav-icon`), labels (`.mob-nav-label`), and `aria-label`. | `test_tier1_bottom_nav_items_and_labels` |
| **Bottom Nav Styling** | CSS Positioning & Z-Index | `position: fixed`, `bottom: 0`, `left: 0`, `right: 0`, `z-index: 999`, `display: flex` on mobile (`@media (max-width: 768px)`), `display: none` on desktop. | `test_tier1_bottom_nav_css_fixed_position` |
| **Bottom Nav Reachability**| Thumb reach zone | Distributed evenly across viewport width (`justify-content: space-around` or `flex: 1`). Item width >= 44px, height >= 44px. | `test_tier1_bottom_nav_thumb_reachability` |
| **Touch Targets (>= 44px)** | Buttons, links, pills, tabs | `min-height: 44px !important` and `min-width: 44px !important` across: `.nav-link`, `.mobile-nav-item`, `.filter-btn`, `.chip-btn`, `.theme-btn`, `.health-pill`, `.market-search-input`, `.btn-csv-export`, `#btn-back-to-top`, `.drawer-nav-btn`, `.drawer-copy-btn`, `.drawer-factor-tab`, `.ext-portal-btn`, `.hub-item-btn`, `.hub-close-btn`, `.tab`, `.btn-watchlist`. | `test_tier1_touch_targets_dimension_compliance` |
| **Safe-Area Insets** | CSS Inset Integration | `env(safe-area-inset-bottom, 0px)` in `.mobile-bottom-nav`, `#btn-back-to-top`, and body padding (`calc(64px + env(safe-area-inset-bottom, 0px))`). | `test_tier1_safe_area_insets_css_integration` |
| **Back-to-Top FAB** | Collision Avoidance | On mobile (`max-width: 768px`), `#btn-back-to-top` has `bottom: calc(68px + env(safe-area-inset-bottom, 0px))` so it floats >= 12px above the 56px bottom nav bar. Dimensions >= 44px x 44px. | `test_tier1_fab_positioning_no_bottom_nav_collision` |
| **Sticky Navigation** | Top Nav Carousel | Height <= 56px (`height: 52px` or `max-height: 56px`), `flex-wrap: nowrap`, `overflow-x: auto`, `-webkit-overflow-scrolling: touch`, auto-centering JS `scrollIntoView({ inline: 'center' })`. | `test_tier1_sticky_nav_height_and_autocentering` |

---

### Tier 2: Boundary Value Analysis (BVA) & Corner Cases

Tier 2 evaluates system behavior at exact mathematical boundaries, aspect ratio extremes, and edge-case user inputs.

| Boundary Dimension | Test Values | Test Invariant / Assertion | Test ID |
|--------------------|-------------|----------------------------|---------|
| **Galaxy Viewport Widths** | `360px`, `375px`, `384px`, `393px`, `412px` | No container width > viewport. Body `overflow-x: hidden`. Card grids (`.macro-grid`, `.health-grid`, `.charts-grid`) collapse to single-column `1fr`. | `test_tier2_galaxy_viewport_widths_stacking` |
| **Desktop Breakpoint Threshold** | `1023px` vs `1024px` | At `1023px`: `.row1-wrapper` is `1fr`. At `1024px`: `.row1-wrapper` is `310px 1fr`, `.mobile-bottom-nav` is `display: none`, `#stock-drawer` is right-hand sidebar. | `test_tier2_desktop_breakpoint_boundary_1024px` |
| **Safe-Area Inset Boundary** | `0px` (no gesture bar) vs `34px` (One UI gesture pill) | At `0px`: bottom nav = 56px, FAB bottom = 68px (gap = 12px). At `34px`: bottom nav = 90px, FAB bottom = 102px (gap = 12px). Invariant: `FAB bottom > bottom nav height` holds for all `safe-area-inset-bottom >= 0`. | `test_tier2_safe_area_inset_boundary_0px_vs_34px` |
| **Table Frozen Columns Budget** | Rank (34-36px), Symbol (66-68px), Name (86-88px) | Total frozen width <= 190px (target 188px). On 360px Galaxy screen: `360 - 188 = 172px` scrollable body (>= 170px requirement). Name column has ellipsis. | `test_tier2_table_frozen_columns_geometry_budget` |
| **Search Input Boundaries** | `""` (empty), `"   "` (spaces), special chars `[A]`, `(주)` | Empty/blank input shows all rows without error. Regex meta-characters in search query are escaped without JS exception. Clear button resets filter. | `test_tier2_search_input_empty_and_special_chars` |
| **Extreme Aspect Ratios** | Ultra-tall `20:9` / `21:9` vs Foldable unfolded `4:3` (~673px) | On ultra-tall viewports: drawer `height: 90vh` preserves visible backdrop at top. On foldable unfolded viewports: content max-width 100vw, no horizontal overflow. | `test_tier2_extreme_aspect_ratios_and_foldables` |

---

### Tier 3: Pairwise Combinations & Cross-Feature Interactions

Tier 3 exercises the interactions between multiple concurrently active UI systems to detect stacking context leaks, synchronization drift, or styling collisions.

| Interaction Pair | Interacting Subsystems | Expected Integrated Behavior | Test ID |
|------------------|------------------------|------------------------------|---------|
| **Bottom Nav <-> Top Nav Sync** | `#mobile-bottom-nav` click & `.sticky-nav` / `#panel-*` | Tapping bottom nav item adds `.active` class to tapped item, removes `.active` from siblings, reveals corresponding panel, and updates URL hash without page jump. | `test_tier3_bottom_nav_sync_with_panels_and_top_nav` |
| **Drawer <-> Bottom Nav Layering** | `#stock-drawer`, `#stock-drawer-overlay`, `#mobile-bottom-nav` | Overlay has `z-index: 1000`, drawer has `z-index: 1001`, bottom nav has `z-index: 999`. Open drawer covers bottom nav. Swipe-down gesture (`diffY > 70`) dismisses drawer. | `test_tier3_stock_drawer_bottom_sheet_layering` |
| **Theme Switcher x Touch x Contrast** | Theme switch (`dark`, `terminal`, `light`) x Touch target sizing | Switching themes preserves `min-height: 44px` on `.theme-btn`. Text contrast ratio against surface exceeds WCAG AA (4.5:1) and AAA (7:1) across all 3 themes. | `test_tier3_theme_switcher_touch_and_contrast` |
| **Search Filter x Table Scroll** | Search filtering x Horizontal scroll x Sticky columns | Filtering table rows preserves `.table-wrap` horizontal scrolling, sticky column offsets (`left: 0`, `left: 34px`, `left: 100px`), and sticky header elevation. | `test_tier3_table_search_filtering_with_horizontal_scroll` |
| **Cross-Page Deep-Linking** | `strategies.html` / `market_*.html` <-> `index.html#panel-{tabId}` | Tapping bottom nav items from sub-pages smoothly routes back to `index.html#panel-{tabId}`. Strategy Hub modal chips route directly to target strategy anchors. | `test_tier3_cross_page_navigation_and_strategy_hub` |

---

### Tier 4: Real-World Application Workloads & Journeys

Tier 4 simulates comprehensive, full-session end-to-end user journeys under realistic operating conditions.

#### Scenario 4.1: Samsung Galaxy Mobile User Journey
- **Device Profile**: Samsung Galaxy S24 / S23 (393px x 851px, viewport-fit=cover, Android gesture bar 34px).
- **Execution Flow**:
  1. User loads `gh-pages/index.html`.
  2. Verifies sticky header (<= 56px) and fixed bottom nav (56px + 34px) are rendered without horizontal scrollbar.
  3. User thumb-taps `#mob-nav-portfolio` -> page scrolls/switches to `#panel-portfolio`.
  4. Inspects HRP asset allocation donut chart (`#hrpDonutChart`) and exposure bar chart (`#marketExposureChart`).
  5. User scrolls down to Top Picks ensemble table, taps a stock row -> opens 90vh detail drawer bottom sheet (`openStockDrawer`).
  6. Inspects factor radar chart (`#drawer-radar-canvas`), checks factor category pills, taps copy code button (`.drawer-copy-btn`).
  7. Dismisses drawer via close button (`.drawer-close-btn`) or swipe gesture.
  8. User thumb-taps 5th bottom nav item `#mob-nav-strategies` -> opens 37-Strategy Hub bottom sheet (`#strategy-hub-sheet`).
  9. Navigates to a strategy link.

#### Scenario 4.2: Desktop PC Browser Visit
- **Device Profile**: 1440px / 1920px Full HD desktop monitor, Chrome / Firefox / Edge.
- **Execution Flow**:
  1. Top sticky nav displays all 7 navigation links in a single row without horizontal scroll.
  2. `.row1-wrapper` displays 2-column layout (310px strategy weights sidebar + `1fr` main rankings table).
  3. Card 1 displays side-by-side matrices; Card 2 displays multi-column strategy cards; Card 3 displays side-by-side charts.
  4. Bottom nav bar is completely hidden (`display: none`).
  5. Tapping a stock row opens `#stock-drawer` as a 480px right-hand slide-in sidebar.
  6. Tooltips trigger on hover/focus, and `/` keyboard shortcut focuses the search input.

#### Scenario 4.3: HTML Payload & Hygiene Invariants
- `gh-pages/index.html` size strictly < 512,000 bytes (500 KB).
- Strict Unix LF line endings (`b"\r\n"` count == 0).
- Valid UTF-8 encoding without BOM.

---

## 4. Requirement Traceability Matrix

| Requirement | Description | Milestone | Tier 1 Tests | Tier 2 Tests | Tier 3 Tests | Tier 4 Tests |
|---|---|---|---|---|---|---|
| **R1 / F_MOB_01** | Fixed Bottom Navigation Bar on Mobile Viewports | M1 | `test_tier1_bottom_nav_*` | `test_tier2_galaxy_viewport_widths_stacking` | `test_tier3_bottom_nav_sync_*` | `test_tier4_galaxy_mobile_user_journey` |
| **R1 / F_MOB_02** | FAB Collision Avoidance | M1 | `test_tier1_fab_positioning_no_bottom_nav_collision` | `test_tier2_safe_area_inset_boundary_0px_vs_34px` | — | `test_tier4_galaxy_mobile_user_journey` |
| **R1 / F_MOB_03** | Safe-Area Inset Handling | M1 | `test_tier1_safe_area_insets_css_integration` | `test_tier2_safe_area_inset_boundary_0px_vs_34px` | — | `test_tier4_galaxy_mobile_user_journey` |
| **R1 / F_MOB_04** | Interactive Touch Targets >= 44px | M1 | `test_tier1_touch_targets_dimension_compliance` | — | `test_tier3_theme_switcher_touch_and_contrast` | `test_tier4_galaxy_mobile_user_journey` |
| **R1 / F_MOB_05** | Cross-Page Aware Navigation | M1 | `test_tier1_bottom_nav_dom_presence` | — | `test_tier3_cross_page_navigation_and_strategy_hub` | `test_tier4_galaxy_mobile_user_journey` |
| **R1 / F_MOB_06** | Mobile Viewport Overflow & 188px Frozen Columns | M2 | `test_tier1_sticky_nav_height_and_autocentering` | `test_tier2_table_frozen_columns_geometry_budget` | `test_tier3_table_search_filtering_with_horizontal_scroll` | `test_tier4_galaxy_mobile_user_journey` |
| **R2 / F_MOB_07** | Desktop (>= 1024px) Responsive Layout | M2 | — | `test_tier2_desktop_breakpoint_boundary_1024px` | — | `test_tier4_desktop_pc_browser_session` |
| **R3 / F_MOB_08** | File Size Budget (< 500 KB / 512,000 bytes) | M3 | — | — | — | `test_tier4_html_file_size_and_hygiene` |
| **R3 / F_MOB_09** | Unix LF Line Ending & Byte Budget Guard | M3 | — | — | — | `test_tier4_html_file_size_and_hygiene` |
| **AC / F_MOB_10** | 100% Test Suite & Invariant Verification | Final | All Tier 1 | All Tier 2 | All Tier 3 | All Tier 4 |

---

## 5. Verification Commands

Run the full E2E Mobile UX test suite:
```powershell
python -m pytest tests/test_e2e_mobile_ux.py -v
```

Run specific test tiers:
```powershell
# Tier 1: Feature Coverage
python -m pytest tests/test_e2e_mobile_ux.py -k "tier1" -v

# Tier 2: Boundary Value Analysis
python -m pytest tests/test_e2e_mobile_ux.py -k "tier2" -v

# Tier 3: Pairwise Combinations
python -m pytest tests/test_e2e_mobile_ux.py -k "tier3" -v

# Tier 4: Real-World Workloads
python -m pytest tests/test_e2e_mobile_ux.py -k "tier4" -v
```

Verify HTML file size and line endings directly:
```powershell
python -c "
from pathlib import Path
p = Path('gh-pages/index.html')
raw = p.read_bytes()
print(f'Size: {len(raw):,} bytes (Budget: < 512,000 bytes) -> {len(raw) < 512000}')
print(f'CRLF count: {raw.count(b\"\r\n\")} -> Unix LF clean: {raw.count(b\"\r\n\") == 0}')
"
```
