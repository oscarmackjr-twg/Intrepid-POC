---
phase: 19-filter-hook-typescript-foundation
plan: "01"
subsystem: frontend
tags: [zustand, typescript, filter-hook, state-management, re-dashboard]
dependency_graph:
  requires: []
  provides:
    - frontend/src/types/re.ts
    - frontend/src/stores/filterStore.ts
    - frontend/src/hooks/useReLoanFilters.ts
  affects:
    - Phases 20-27 (all RE dashboard chart phases import from these files)
tech_stack:
  added:
    - zustand@^5.0.12
  patterns:
    - URL-as-source-of-truth with Zustand mirror store
    - Curried create<T>()() form for Zustand 5 TypeScript inference
    - URLSearchParams read-on-render with useEffect sync to store
key_files:
  created:
    - frontend/src/types/re.ts
    - frontend/src/stores/filterStore.ts
    - frontend/src/hooks/useReLoanFilters.ts
  modified:
    - frontend/package.json
    - frontend/package-lock.json
decisions:
  - "[D-07] URL params are authoritative; Zustand is a mirror/cache synchronized via useEffect"
  - "[D-12] Decimal fields typed as number in TypeScript (FastAPI serializes to JSON number)"
  - "[D-13] Filter fields are string|null except loan_size_min/max which are number|null"
  - "Zustand create<T>()() curried form used for TypeScript inference (Zustand 5 requirement)"
requirements:
  - FILTER-01
  - FILTER-02
  - FILTER-03
  - FILTER-04
metrics:
  duration: "~10 minutes"
  completed: "2026-04-09T01:55:19Z"
  tasks_completed: 2
  files_created: 3
  files_modified: 2
---

# Phase 19 Plan 01: Install Zustand, TypeScript types, and filter hook — Summary

**One-liner:** Zustand 5 installed, 25 TypeScript interfaces hand-authored from re_schemas.py, URL-Zustand sync hook with `{ filters, setFilter, clearFilters }` API.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Install Zustand and create TypeScript types | dc87b26 | frontend/package.json, frontend/src/types/re.ts |
| 2 | Create Zustand filter store and useReLoanFilters hook | ab8e136 | frontend/src/stores/filterStore.ts, frontend/src/hooks/useReLoanFilters.ts |

## What Was Built

### frontend/src/types/re.ts

25 exported TypeScript interfaces mirroring every Pydantic model in `backend/api/re_schemas.py`:

- `ReLoanFilters` — filter params used by the hook (all `string | null` except `loan_size_min`/`loan_size_max` as `number | null`)
- `KPIResponse`, `ConcentrationResponse`, `DistributionsResponse`, `MaturityProfileResponse` — chart endpoint types
- `LoanListResponse`, `LoanDetailResponse`, `PaymentHistorySummary` — loan list/detail types
- `CashflowPerformanceResponse`, `OriginationPipelineResponse`, `MarketContextResponse`, `SensitivityResponse` — additional endpoint types
- All monetary/rate fields typed as `number` (FastAPI serializes Python Decimal to JSON number; D-12)
- All date fields typed as `string` (JSON serializes Python date as ISO string)

### frontend/src/stores/filterStore.ts

Zustand 5 filter store:
- `useFilterStore` created with curried `create<FilterStore>()()` form for TypeScript inference
- `DEFAULT_FILTERS` exported (all fields null) — referenced by hook and tests
- Actions: `setFilters(filters)`, `resetFilters()`

### frontend/src/hooks/useReLoanFilters.ts

URL-Zustand sync hook:
- `parseFiltersFromParams(searchParams)` derives current filter state from URL (extracted as named function)
- `useEffect` syncs URL-derived filters into Zustand after render (not during render)
- `setFilter(key, value)` — sets a single filter; updates URL, which triggers re-derive + sync
- `clearFilters()` — calls `setSearchParams({})` AND `resetFilters()` in one action (FILTER-04)
- Returns `{ filters, setFilter, clearFilters }`

## Verification Results

1. `cd frontend && npx tsc --noEmit` — exits 0 (both after Task 1 and Task 2)
2. `grep -c "export interface" frontend/src/types/re.ts` — returns 25 (>= 20 required)
3. `grep "export const useFilterStore" frontend/src/stores/filterStore.ts` — matches
4. `grep "export function useReLoanFilters" frontend/src/hooks/useReLoanFilters.ts` — matches

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — this plan creates infrastructure (types, store, hook) with no UI rendering or data sources. No stubs that would prevent the plan's goal from being achieved.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. Filter store contains no sensitive data (only filter criteria; T-19-02 accepted per plan threat model).

## Self-Check: PASSED

- FOUND: frontend/src/types/re.ts
- FOUND: frontend/src/stores/filterStore.ts
- FOUND: frontend/src/hooks/useReLoanFilters.ts
- FOUND commit dc87b26 (Task 1)
- FOUND commit ab8e136 (Task 2)
