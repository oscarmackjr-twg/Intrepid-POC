---
phase: 24-origination-pipeline-market-context
plan: "02"
subsystem: frontend-pages
tags: [react, recharts, tanstack-query, origination-pipeline, market-context, click-to-filter]
dependency_graph:
  requires: [24-01]
  provides: [ORIGIN-01, ORIGIN-02, ORIGIN-03, ORIGIN-04, MARKET-01, MARKET-02, UX-01]
  affects: [frontend/src/pages/ReOriginationPage.tsx, frontend/src/App.tsx]
tech_stack:
  added: []
  patterns: [TanStack Query filter-aware query key, stacked bar pivot transform, static market query key]
key_files:
  created:
    - frontend/src/pages/ReOriginationPage.tsx
  modified:
    - frontend/src/App.tsx
decisions:
  - volumeByMonth pivot uses Map with `as unknown as Record<string,number>` cast to satisfy TS index signature (month key is string, not number)
  - ReStubPage function removed from App.tsx — no longer referenced by any route
metrics:
  duration: ~15min
  completed: 2026-04-12
  tasks_completed: 1
  files_modified: 2
---

# Phase 24 Plan 02: Build ReOriginationPage with Origination Panels and Market Context Summary

**One-liner:** Built ReOriginationPage.tsx with 5 panels (stacked bar by property type, net volume KPI, pipeline funnel, vintage table, market context rate cards + cap/vacancy table) and wired it into App.tsx replacing the ReStubPage stub.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Create ReOriginationPage.tsx with all panels | 9f97b03 | frontend/src/pages/ReOriginationPage.tsx, frontend/src/App.tsx |

## Tasks Pending (awaiting checkpoint)

| # | Name | Type | Status |
|---|------|------|--------|
| 2 | Visual verification of Origination Pipeline + Market Context page | checkpoint:human-verify | Awaiting human verification |

## What Was Built

### Task 1 — ReOriginationPage.tsx + App.tsx route wiring

**ReOriginationPage.tsx (262 lines):**

- **Stacked bar (ORIGIN-01, D-03):** `origination_by_month` rows pivoted via Map into Recharts stacked bar format. Each `YYYY-MM` becomes one data point with property type UPB as keys. `stackId="origination"` ensures bars stack. `onClick` on each `<Bar>` calls `setFilter('property_type', pt)` for click-to-filter (UX-01).
- **Net Origination Volume KPI (ORIGIN-02, D-05):** Sums all `total_upb` from `origination_by_month`; displayed as `formatUPB()` in a centered card.
- **Pipeline Funnel (ORIGIN-03, D-06):** Horizontal `BarChart` (`layout="vertical"`) using `pipeline_funnel` data directly. Tooltip shows UPB + loan count per stage.
- **Vintage Analysis table (ORIGIN-04, D-07):** HTML table with columns: Vintage, Loans, UPB, Avg LTV, Avg DSCR, Avg Rate. Styled to match TopExposuresTable pattern.
- **Market Context (MARKET-01/02, D-08/09):** Full-width section below the 2x2 grid with "Indicative values — not connected to live feeds" disclaimer. Rate cards for 10Y Treasury and SOFR with Unicode trend arrows (↑/↓/→). Cap rates and vacancy rates joined by `property_type` in a combined table.
- Both queries follow established patterns: origination uses `[..., filters]` key for filter reactivity; market uses static `['re-market-context']` key (no filters — global rates).

**App.tsx:**
- Added `import ReOriginationPage from './pages/ReOriginationPage'`
- Replaced `element={<ReStubPage />}` with `element={<ReOriginationPage />}` on `path="origination"`
- Removed now-unused `ReStubPage` function definition

**TypeScript:** `npx tsc --noEmit` exits 0 with no errors.

## Verification

- `npx tsc --noEmit` — exit 0
- All 14 acceptance criteria checked via grep — all pass
- File is 262 lines (>= 150 minimum)
- Human visual verification pending (Task 2 checkpoint)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TS2352 type cast for volumeByMonth initial object**
- **Found during:** Task 1 tsc verification
- **Issue:** `{ month: key } as Record<string, number>` fails because `month: string` is not assignable to index signature `number`. Plan's code snippet used single `as` cast which tsc rejects.
- **Fix:** Changed to `{ month: key } as unknown as Record<string, number>`
- **Files modified:** frontend/src/pages/ReOriginationPage.tsx
- **Commit:** 9f97b03 (inline fix before commit)

## Known Stubs

None — all data is wired to live API endpoints (`/api/re/origination-pipeline`, `/api/re/market-context`). Market context values are intentionally static/indicative on the backend side (labeled "Indicative values" per D-09) but the frontend is fully wired.

## Threat Flags

No new trust-boundary surface introduced. T-24-05 mitigation confirmed: `setFilter` receives the `property_type` value from the API response (not free-text user input). The origination pipeline query passes filter params through the standard filter object, consistent with all other RE dashboard endpoints.

## Self-Check: PASSED

- `frontend/src/pages/ReOriginationPage.tsx` exists and is 262 lines: confirmed
- `queryKey: ['re-origination-pipeline', filters]` present: confirmed
- `queryKey: ['re-market-context']` present: confirmed
- `setFilter('property_type', pt)` present: confirmed
- `stackId="origination"` present: confirmed
- `layout="vertical"` present: confirmed
- `Indicative values` text present: confirmed
- Unicode trend arrows `\u2191`, `\u2193`, `\u2192` present: confirmed
- Vintage table `<th` headers (Vintage, Loans, UPB, Avg LTV, Avg DSCR, Avg Rate) present: confirmed
- `Net Origination Volume` label present: confirmed
- `import ReOriginationPage` in App.tsx: confirmed
- `element={<ReOriginationPage />}` on origination route: confirmed
- `element={<ReStubPage />}` absent: confirmed
- Commit 9f97b03 present in git log: confirmed
