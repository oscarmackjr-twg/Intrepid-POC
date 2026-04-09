---
phase: 21-portfolio-composition-page
plan: "02"
subsystem: frontend
tags: [recharts, tanstack-query, charts, portfolio, click-to-filter]
dependency_graph:
  requires: [21-01]
  provides: [re-portfolio-page, chart-card-wrapper, 4-recharts-panels]
  affects: [frontend/src/App.tsx, frontend/src/pages/RePortfolioPage.tsx, frontend/src/components/re/ChartCard.tsx]
tech_stack:
  added: []
  patterns: [recharts-responsive-container, tanstack-query-data-fetching, click-to-filter-setFilter]
key_files:
  created:
    - frontend/src/components/re/ChartCard.tsx
    - frontend/src/pages/RePortfolioPage.tsx
  modified:
    - frontend/src/App.tsx
decisions:
  - ChartCard accepts optional children to allow isEmpty/isLoading short-circuit without rendering child chart components
  - Pie onClick and Bar onClick cast through unknown to ConcentrationItem due to Recharts PieSectorDataItem/BarRectangleItem not exposing data fields directly
  - All 4 chart panels implemented in single task (Tasks 1 and 2 combined) since layout was defined upfront
metrics:
  duration: "~15 minutes"
  completed: "2026-04-09"
  tasks_completed: 2
  files_modified: 1
  files_created: 2
---

# Phase 21 Plan 02: RePortfolioPage with 4 Recharts Panels Summary

**One-liner:** Built RePortfolioPage with property type donut, top-states bar, loan size histogram, and maturity profile stacked bar — all wired to TanStack Query and click-to-filter via useReLoanFilters.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create ChartCard wrapper and RePortfolioPage scaffold with donut + histogram | 4acace2 | frontend/src/components/re/ChartCard.tsx, frontend/src/pages/RePortfolioPage.tsx, frontend/src/App.tsx |
| 2 | Add top states horizontal bar chart and maturity profile stacked bar | 4acace2 | frontend/src/pages/RePortfolioPage.tsx (both panels implemented in Task 1 commit) |

## What Was Built

- **`ChartCard.tsx`** — Shared card wrapper: `animate-pulse` skeleton when `isLoading`, muted "No data" when `isEmpty`, `children` rendered otherwise. Supports `colSpan="full"` for full-width panels.
- **`RePortfolioPage.tsx`** — Full portfolio page with 6-panel grid:
  - Panel 1: Property Type donut (`PieChart` + `Pie` with `innerRadius=60`) — click calls `setFilter('property_type', ...)`
  - Panel 2: Top States by UPB horizontal bar (`layout="vertical"`, top 10 sorted descending) — click calls `setFilter('state', ...)`
  - Panel 3: Loan Size Distribution histogram (`BarChart`, `dataKey="loan_count"`) — display-only
  - Panel 4: Maturity Profile stacked bar (`stackId="maturity"`, X-axis label `${year} Q${quarter}`) — display-only
  - Panel 5 & 6: Placeholder ChartCards (full-width) for Plan 03
- **Three TanStack Query hooks** fetching `/api/re/concentration`, `/api/re/distributions`, `/api/re/maturity-profile` following the `useKPIs` pattern
- **`App.tsx`** — `/re-dashboard/portfolio` route wired to `RePortfolioPage` (replacing `ReStubPage`)

## Verification

All acceptance criteria met:
- `ChartCard.tsx` contains `animate-pulse`, `No data`, `border-gray-200`
- `RePortfolioPage.tsx` contains `useQuery` (3 calls), `re-concentration`, `re-distributions`, `re-maturity-profile`
- `RePortfolioPage.tsx` contains `PieChart`, `innerRadius`, `setFilter('property_type'`
- `RePortfolioPage.tsx` contains `loan_size_distribution`, `loan_count`
- `RePortfolioPage.tsx` contains `ResponsiveContainer` (9 instances, >= 4 required)
- `RePortfolioPage.tsx` contains `grid-cols-1 md:grid-cols-2`
- `App.tsx` contains `RePortfolioPage` import and route
- `layout="vertical"` present (top states bar)
- `setFilter('state'` present (click-to-filter on state)
- `topStates` variable with `.sort(` and `.slice(0, 10)`
- `stackId="maturity"` present
- `Q${p.quarter}` quarter label format present
- All 4 ChartCard titles present: "Property Type", "Top States by UPB", "Loan Size Distribution", "Maturity Profile"
- `npx tsc --noEmit` exits with 0 errors (verified from main repo with node_modules)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] recharts not installed in node_modules**
- **Found during:** Task 1 TypeScript check
- **Issue:** `recharts ^3.8.1` was in `package.json` but `npm install` had not been run, so the module was missing from `node_modules`
- **Fix:** Ran `npm install recharts` in the main repo frontend directory
- **Files modified:** `node_modules/` (not tracked)
- **Commit:** n/a (npm install, no git change)

**2. [Rule 1 - Bug] Recharts click handler implicit any and type mismatch**
- **Found during:** Task 1 TypeScript check
- **Issue:** Recharts `Pie` onClick receives `PieSectorDataItem` and `Bar` onClick receives `BarRectangleItem` — neither exposes `category` directly, causing TS2769/TS2322 errors
- **Fix:** Used `(entry as unknown as ConcentrationItem)` double-cast with a `'category' in entry` guard
- **Files modified:** `frontend/src/pages/RePortfolioPage.tsx`
- **Commit:** 4acace2

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `<ChartCard title="Top-10 Exposures" isEmpty={true} colSpan="full" />` | frontend/src/pages/RePortfolioPage.tsx | Intentional placeholder; Plan 03 will replace with real table |
| `<ChartCard title="Concentration Limits" isEmpty={true} colSpan="full" />` | frontend/src/pages/RePortfolioPage.tsx | Intentional placeholder; Plan 03 will replace with progress bars |

These stubs do not block the plan goal — all 4 Recharts panels are functional.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. Chart click handlers call `setFilter` which only updates URL params; `useReLoanFilters` validates keys against `ReLoanFilters` interface.

## Self-Check: PASSED

- `frontend/src/components/re/ChartCard.tsx` — FOUND
- `frontend/src/pages/RePortfolioPage.tsx` — FOUND
- `frontend/src/App.tsx` (modified) — FOUND
- Commit `4acace2` — FOUND
