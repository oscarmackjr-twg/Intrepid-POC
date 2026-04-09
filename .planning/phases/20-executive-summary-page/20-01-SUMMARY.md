---
phase: 20-executive-summary-page
plan: 01
subsystem: ui
tags: [react, tanstack-query, tailwind, kpi, dashboard]

# Dependency graph
requires:
  - phase: 19-filter-hook-typescript-foundation
    provides: useReLoanFilters hook, ReLoanFilters types, ReDashboard placeholder, ReDashboardFilterSidebar
  - phase: 18-core-api-layer
    provides: /api/re/kpis endpoint, KPIResponse schema
provides:
  - TanStack Query installation and QueryClientProvider wiring in App.tsx
  - formatKpi.ts with 5 pure formatting functions (UPB, rate, WAM, DSCR, count)
  - KPICard component with loading skeleton, no-data, normal, and clickable highlight states
  - useKPIs hook wrapping /api/re/kpis with filters as query key
  - ReDashboard page with 10-card responsive KPI grid wired to live API
affects: [21, 22, 23, chart-phases, future-re-dashboard-plans]

# Tech tracking
tech-stack:
  added: ["@tanstack/react-query ^5.96.2"]
  patterns:
    - "QueryClient instance at module scope in App.tsx, QueryClientProvider wraps full app"
    - "useQuery with full filters object as queryKey — filter changes trigger automatic refetch"
    - "Pure formatting functions for null-safe display (null -> en-dash U+2013)"
    - "KPI cards: loading skeleton same dimensions as card (no layout shift), no-data en-dash in muted slate"
    - "Delinquency card toggle: useState<string | null> tracks highlighted key, click same card to deselect"

key-files:
  created:
    - frontend/src/utils/formatKpi.ts
    - frontend/src/components/re/KPICard.tsx
    - frontend/src/hooks/useKPIs.ts
  modified:
    - frontend/src/App.tsx
    - frontend/src/pages/ReDashboard.tsx
    - frontend/package.json

key-decisions:
  - "QueryClientProvider wraps full app in App.tsx (not just RE subtree) — simpler, no overhead for this app size"
  - "Delinquency click is visual highlight only with TODO referencing FILTER-01 — no schema change to ReLoanFilters (D-11 option b)"
  - "KPI_CARDS array typed with keyof KPIResponse to guarantee key safety against future API schema changes"
  - "No-data signal is active_loan_count === 0 — all 10 cards show en-dash regardless of individual field values"

patterns-established:
  - "TanStack Query pattern: useKPIs() as the template for all future /api/re/* hooks in this dashboard"
  - "Null-safe formatting: every formatter returns en-dash string for null input, never crashes on missing data"
  - "KPICard is pure display — receives pre-formatted string, knows nothing about data fetching"

requirements-completed: [EXEC-01, EXEC-02, UX-01]

# Metrics
duration: 25min
completed: 2026-04-08
---

# Phase 20 Plan 01: Executive Summary Page Summary

**TanStack Query-powered KPI grid with 10 live metric cards, loading skeletons, no-data en-dash states, and delinquency click-highlight on /re-dashboard**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-08
- **Completed:** 2026-04-08
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Installed `@tanstack/react-query` and wired `QueryClientProvider` around the full app in `App.tsx`
- Created `formatKpi.ts` with 5 null-safe formatting functions (UPB abbreviation, rate %, WAM months, DSCR x, count with commas)
- Created `KPICard` component with loading skeleton (animate-pulse, no layout shift), no-data en-dash (muted slate), normal value (navy bold), and delinquency clickable highlight states
- Created `useKPIs` hook — `useQuery` wrapping `/api/re/kpis` with full `filters` object as query key so any filter change triggers automatic refetch
- Replaced ReDashboard placeholder with 10-card responsive grid (2 cols mobile / 4 cols lg) wired to live KPI data

## Task Commits

1. **Task 1: Install TanStack Query and create KPI card foundation** - `c69bdd2` (feat)
2. **Task 2: Wire ReDashboard page with KPI grid** - `600077c` (feat)

## Files Created/Modified

- `frontend/src/utils/formatKpi.ts` — 5 pure formatting functions: formatUPB, formatRate, formatWAM, formatDSCR, formatCount
- `frontend/src/components/re/KPICard.tsx` — Reusable KPI card with loading/no-data/normal/clickable states
- `frontend/src/hooks/useKPIs.ts` — TanStack Query hook for /api/re/kpis, filters as query key
- `frontend/src/App.tsx` — Added QueryClient + QueryClientProvider wrapping full app
- `frontend/src/pages/ReDashboard.tsx` — 10-card KPI grid replacing placeholder
- `frontend/package.json` — Added @tanstack/react-query ^5.96.2

## Decisions Made

- `QueryClientProvider` wraps the full app in `App.tsx` (not a subtree) — simpler for an app this size with no performance concern
- Delinquency click behavior uses visual highlight only (D-11 option b) — no schema change to `ReLoanFilters`; TODO comment references `FILTER-01` for future implementation
- `KPI_CARDS` typed as `{ key: keyof KPIResponse; ... }[]` (not `as const`) to allow the explicit generic type annotation without TypeScript inference conflicts

## Deviations from Plan

None — plan executed exactly as written. The worktree required restoring Phase 19 files via `git checkout 2bcb1fd -- <files>` before implementation (baseline issue, not a plan deviation).

## Issues Encountered

- Worktree branch was based on an older commit than the target; after `git reset --soft 2bcb1fd`, Phase 19 implementation files (ReDashboard, useReLoanFilters, types/re.ts, etc.) were staged as deleted. Resolved by restoring them with `git checkout 2bcb1fd -- <files>` before starting implementation.

## Known Stubs

None — KPI data is fetched live from `/api/re/kpis`. No hardcoded placeholder values flow to the UI.

## Self-Check: PASSED

- FOUND: frontend/src/utils/formatKpi.ts
- FOUND: frontend/src/components/re/KPICard.tsx
- FOUND: frontend/src/hooks/useKPIs.ts
- FOUND: frontend/src/pages/ReDashboard.tsx
- FOUND: commit c69bdd2
- FOUND: commit 600077c

## Next Phase Readiness

- TanStack Query pattern established — all subsequent chart/data hooks should follow `useKPIs` as a template
- `/re-dashboard` now shows live KPI data; filter sidebar drives automatic refetch
- Delinquency click highlight is visual-only pending FILTER-01 (delinquency_bucket filter field in ReLoanFilters schema)
- Ready for Phase 21+ chart panels to be added to the flex-1 charts area

---
*Phase: 20-executive-summary-page*
*Completed: 2026-04-08*
