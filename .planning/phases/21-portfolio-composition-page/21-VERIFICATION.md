---
phase: 21-portfolio-composition-page
verified: 2026-04-09T14:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Navigate to /re-dashboard/portfolio and verify the four chart panels render with seeded data"
    expected: "Property Type donut, Top States bar, Loan Size histogram, Maturity Profile stacked bar all show chart content (not skeleton or No data)"
    why_human: "Cannot run browser; seeded data requires live DB connection to verify non-empty API responses"
  - test: "Click a property type donut slice and confirm URL gains ?property_type=<value> and KPI cards reload"
    expected: "URL changes, tab remains on Portfolio, KPI cards on Executive Summary tab reflect the filter"
    why_human: "Click-to-filter wiring is code-verified but end-to-end URL+KPI update requires browser interaction"
  - test: "Click a state bar in the Top States chart and confirm URL gains ?state=<value>"
    expected: "URL gains state param; chart re-renders filtered (or shows No data if only one state)"
    why_human: "Same as above — setSearchParams is code-verified but requires browser to confirm"
  - test: "Navigate to /re-dashboard and confirm 5 tabs are present; navigate between them"
    expected: "Executive Summary (active by default), Portfolio, Credit Quality, Cash Flow, Origination tabs visible; switching works; Credit/Cash Flow/Origination show 'Coming in a future phase.' text"
    why_human: "Tab strip styling (active border, hover state) and NavLink end={true} behavior require visual confirmation"
---

# Phase 21: Portfolio Composition Page Verification Report

**Phase Goal:** Users can see the full portfolio broken down by property type, geography, loan size, maturity, and top exposures — and can click any chart segment to filter the entire dashboard.
**Verified:** 2026-04-09T14:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| SC-1 | Portfolio page shows property type donut, loan size histogram, and maturity profile stacked bar, all populated from seeded data | VERIFIED | `RePortfolioPage.tsx` lines 72-154: `PieChart` with `innerRadius=60`, `BarChart` for histogram with `loan_size_distribution`, `BarChart` with `stackId="maturity"` — all in `ChartCard` wrappers with live `useQuery` data fetching |
| SC-2 | Geographic view shows ranked bar chart of top states by UPB | VERIFIED | `RePortfolioPage.tsx` lines 100-120: `BarChart layout="vertical"` consuming `topStates` (sorted by `total_upb` desc, `.slice(0, 10)`) from `/api/re/concentration` |
| SC-3 | Top-10 exposures table shows 10 largest loans with LTV, DSCR, property type, location | VERIFIED | `TopExposuresTable.tsx` renders 7 columns: Loan #, Borrower, UPB, LTV, DSCR, Property Type, State — wired in `RePortfolioPage.tsx` line 163 to `concentration.data?.top_10_exposures` |
| SC-4 | Clicking a pie slice or histogram bar applies dimension as filter — URL param change and updated KPIs | VERIFIED (code) | `RePortfolioPage.tsx` line 88: `setFilter('property_type', ...)` on pie click; line 115: `setFilter('state', ...)` on bar click. `useReLoanFilters.setFilter` calls `setSearchParams`, URL is authoritative. All `useQuery` keys include `filters` so KPIs refetch automatically. Browser confirmation needed. |
| SC-5 | Concentration limit indicators visible, showing proximity to policy limits | VERIFIED | `ConcentrationLimits.tsx`: `getBarColor(proximity)` returns `bg-green-500`/`bg-yellow-400`/`bg-red-500`; inline width `Math.min(proximity * 100, 100)%`. Backend `re_routes.py` lines 289-334 computes proximity from DB data for state, property_type, borrower. |

**Score:** 5/5 roadmap success criteria code-verified. Human confirmation needed for visual rendering and end-to-end click behavior.

### Deferred Items

None — all roadmap success criteria are addressed in this phase.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/pages/ReExecutiveSummaryPage.tsx` | KPI card grid extracted from ReDashboard | VERIFIED | Contains `KPI_CARDS` array, `useKPIs` hook, 10-card grid. Not hollow — fully functional. |
| `frontend/src/pages/ReDashboard.tsx` | Layout shell with tab strip and Outlet | VERIFIED | `NavLink` tab strip (5 tabs), `<Outlet />`, `ReDashboardFilterSidebar`. Does NOT contain `useKPIs` or `KPICard`. |
| `frontend/src/pages/RePortfolioPage.tsx` | Portfolio page with 4 Recharts panels and data fetching | VERIFIED | 6-panel grid, 3 `useQuery` calls, 4 chart panels + table + concentration limits. 179 lines, substantive. |
| `frontend/src/components/re/ChartCard.tsx` | Shared card wrapper with loading/no-data states | VERIFIED | `animate-pulse` skeleton, `No data` muted text, `border-gray-200`, `colSpan="full"` support. |
| `frontend/src/components/re/TopExposuresTable.tsx` | Top-10 exposures table component | VERIFIED | Contains `loan_number`, `borrower_name`, `formatUPB`, `formatRate`, `formatDSCR`, `TopExposure` type import. |
| `frontend/src/components/re/ConcentrationLimits.tsx` | Concentration limit progress bars | VERIFIED | Contains `proximity`, `bg-red-500`, `bg-yellow-400`, `bg-green-500`, `current_pct`, `limit_pct`, `Math.min` cap. |
| `frontend/package.json` | recharts in dependencies | VERIFIED | `"recharts": "^3.8.1"` at line 24. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `App.tsx` | `ReDashboard.tsx` | parent route `element={<ReDashboard />}` | WIRED | Line 50: `<Route path="re-dashboard" element={<ReDashboard />}>` with 5 child routes |
| `ReDashboard.tsx` | `<Outlet>` | react-router-dom Outlet | WIRED | Line 39 of ReDashboard.tsx: `<Outlet />` renders active child route |
| `App.tsx` | `ReExecutiveSummaryPage` | index child route | WIRED | Line 51: `<Route index element={<ReExecutiveSummaryPage />} />` |
| `App.tsx` | `RePortfolioPage` | `/portfolio` child route | WIRED | Line 52: `<Route path="portfolio" element={<RePortfolioPage />} />` |
| `RePortfolioPage.tsx` | `/api/re/concentration` | `useQuery` with `axios.get` | WIRED | Lines 33-39: queryKey `['re-concentration', filters]`, queryFn fetches `/api/re/concentration` |
| `RePortfolioPage.tsx` | `/api/re/distributions` | `useQuery` with `axios.get` | WIRED | Lines 41-47: queryKey `['re-distributions', filters]`, queryFn fetches `/api/re/distributions` |
| `RePortfolioPage.tsx` | `/api/re/maturity-profile` | `useQuery` with `axios.get` | WIRED | Lines 49-55: queryKey `['re-maturity-profile', filters]`, queryFn fetches `/api/re/maturity-profile` |
| `RePortfolioPage.tsx` | `useReLoanFilters` | `setFilter` on chart click | WIRED | Line 88: `setFilter('property_type', ...)` on pie click; line 115: `setFilter('state', ...)` on bar click |
| `RePortfolioPage.tsx` | `TopExposuresTable` | component import and render | WIRED | Imported line 17, rendered line 163 inside ChartCard panel 5 |
| `RePortfolioPage.tsx` | `ConcentrationLimits` | component import and render | WIRED | Imported line 18, rendered line 173 inside ChartCard panel 6 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `RePortfolioPage.tsx` (donut) | `concentration.data?.property_type` | `GET /api/re/concentration` → `get_concentration()` | Yes — `db.query(RELoan.property_type, func.count, func.sum)` at re_routes.py line 231 | FLOWING |
| `RePortfolioPage.tsx` (top states bar) | `topStates` derived from `concentration.data?.state` | same concentration query | Yes — same DB query grouped by `RELoan.state` | FLOWING |
| `RePortfolioPage.tsx` (histogram) | `distributions.data?.loan_size_distribution` | `GET /api/re/distributions` | Yes — `get_distributions()` at re_routes.py line 351 (CASE-based loan size bucketing against DB) | FLOWING |
| `RePortfolioPage.tsx` (maturity bar) | `maturityData` from `maturity.data?.periods` | `GET /api/re/maturity-profile` | Yes — `get_maturity_profile()` at re_routes.py line 450 | FLOWING |
| `TopExposuresTable` | `exposures` prop from `concentration.data?.top_10_exposures` | concentration query `.limit(10)` | Yes — `db.query(RELoan).order_by(RELoan.upb.desc()).limit(10)` at re_routes.py line 259 | FLOWING |
| `ConcentrationLimits` | `limits` prop from `concentration.data?.concentration_limits` | concentration query, borrower sub-query | Yes — computed from DB data at re_routes.py lines 289-334 | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED (requires running server with seeded database — cannot test API endpoints without live backend). TypeScript compilation checked as proxy.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| TypeScript compiles without errors | `node_modules/.bin/tsc --noEmit` | Exit 0, no output | PASS |
| recharts in package.json | `grep "recharts" frontend/package.json` | `"recharts": "^3.8.1"` | PASS |
| Commits exist in git history | `git log --oneline 5aed3ee 4acace2 62d0589 a86aa7e` | All 4 commits found | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| COMP-01 | 21-02 | Property type donut/pie chart | SATISFIED | `PieChart` with `innerRadius=60` in RePortfolioPage panel 1 |
| COMP-02 | 21-02 | Top states geographic view | SATISFIED | `BarChart layout="vertical"` with top 10 states in panel 2 |
| COMP-03 | 21-02 | Loan size histogram | SATISFIED | `BarChart` with `loan_size_distribution` in panel 3 |
| COMP-04 | 21-02 | Maturity profile stacked bar | SATISFIED | `BarChart` with `stackId="maturity"` in panel 4 |
| COMP-05 | 21-03 | Top-10 exposures table | SATISFIED | `TopExposuresTable` with 7 columns in panel 5 |
| COMP-06 | 21-03 | Concentration limit indicators | SATISFIED | `ConcentrationLimits` with green/yellow/red proximity bars in panel 6 |
| UX-01 | 21-02 | Click chart segment to filter dashboard | SATISFIED (code) | `setFilter('property_type', ...)` and `setFilter('state', ...)` on click; URL-authoritative filter pattern; browser confirm needed |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `TopExposuresTable.tsx` | 28-29 | `// TODO: Phase 25 — wire row click` with `onClick={undefined}` | Info | Intentional per D-18; row click for loan detail side-panel is explicitly deferred to Phase 25. Not a functional stub — table renders all data. |
| `re_routes.py` | 281 | `# TODO: POLICY-CONFIG — move to DB settings in production` | Info | Concentration limits are hardcoded POC values (`state: 25%`, `property_type: 40%`, `borrower: 10%`). Data still flows and renders correctly. Not a Phase 21 concern. |

No blockers or functional stubs found. The `onClick={undefined}` in TopExposuresTable renders real data in all 7 columns — only the future click handler is absent.

### Human Verification Required

#### 1. Portfolio Charts Render with Seeded Data

**Test:** Log in, navigate to `/re-dashboard/portfolio`.
**Expected:** All four chart panels show actual chart content — donut slices for property types, horizontal bars for top states, histogram bars for loan sizes, stacked bars for maturity quarters. ChartCard titles "Property Type", "Top States by UPB", "Loan Size Distribution", "Maturity Profile" all visible.
**Why human:** Requires live DB with seeded RE loans; cannot verify chart rendering without a browser.

#### 2. Click-to-Filter Updates URL and KPI Cards

**Test:** On the Portfolio tab, click a property type donut slice. Observe URL. Navigate to Executive Summary tab.
**Expected:** URL gains `?property_type=<PropertyType>` query param. Executive Summary KPI cards reload and reflect filtered data (e.g., total UPB decreases to match only that property type).
**Why human:** `setFilter` → `setSearchParams` → `useQuery` refetch chain is code-verified, but the visual confirmation of KPI card refresh requires browser interaction.

#### 3. Top States Click-to-Filter

**Test:** Click a state bar in the Top States by UPB chart.
**Expected:** URL gains `?state=<StateCode>` param. Charts refetch with the state filter applied.
**Why human:** Same as above.

#### 4. Tab Navigation and Stub Pages

**Test:** Visit `/re-dashboard`, observe the 5-tab strip. Click each tab in order.
**Expected:** Executive Summary tab is active by default (underlined, navy). Portfolio tab shows chart grid. Credit Quality, Cash Flow, Origination tabs show "Coming in a future phase." text.
**Why human:** Tab active/inactive styling (`border-b-2 border-[#1a3868]`) and NavLink `end={true}` behavior require visual browser confirmation.

#### 5. Top-10 Exposures Table and Concentration Limits

**Test:** On the Portfolio tab, scroll down to the two full-width panels.
**Expected:** Top-10 Exposures shows 10 rows with formatted UPB (e.g., $1.2M), LTV (e.g., 65.0%), DSCR values. Concentration Limits shows 3 bars (state, property_type, borrower) with color-coded progress bars.
**Why human:** Data formatting and visual bar widths require browser rendering to confirm.

### Gaps Summary

No gaps found. All six required artifacts exist, are substantive (not stubs), are wired into the component tree, and have real data flowing from DB-backed API endpoints. TypeScript compiles with 0 errors. All 4 commits are in git history.

The phase is blocked on human verification only — 5 browser-observable behaviors cannot be confirmed programmatically.

---

_Verified: 2026-04-09T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
