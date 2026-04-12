---
phase: 24-origination-pipeline-market-context
plan: "01"
subsystem: backend-api, frontend-types
tags: [api, schemas, typescript, origination-pipeline, tdd]
dependency_graph:
  requires: []
  provides: [ORIGIN-01, ORIGIN-04]
  affects: [frontend/src/types/re.ts, backend/api/re_schemas.py, backend/api/re_routes.py]
tech_stack:
  added: []
  patterns: [TDD red-green, Pydantic v2 schema extension, SQLAlchemy group_by extension]
key_files:
  created: []
  modified:
    - backend/api/re_schemas.py
    - backend/api/re_routes.py
    - backend/tests/test_re_api.py
    - frontend/src/types/re.ts
decisions:
  - property_type fallback to "Unknown" when NULL in DB — consistent with other string group-by fields
  - avg_rate is Optional (None when all interest_rate values are NULL for a vintage year)
metrics:
  duration: ~10min
  completed: 2026-04-12
  tasks_completed: 2
  files_modified: 4
---

# Phase 24 Plan 01: Extend Origination Pipeline API with property_type and avg_rate Summary

**One-liner:** Added `property_type` grouping to origination-by-month query and `avg_rate` (avg interest_rate) to vintage breakdown, with matching Pydantic schema fields, TypeScript interface updates, and three new TDD tests.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 (RED) | Failing tests for property_type and avg_rate | 958cfb4 | backend/tests/test_re_api.py |
| 1 (GREEN) | Extend schemas + update API query | 7192148 | backend/api/re_schemas.py, backend/api/re_routes.py |
| 2 | Update TypeScript interfaces | 662e99b | frontend/src/types/re.ts |

## What Was Built

### Task 1 — Backend schemas and routes (TDD)

**RED:** Added three new tests to `test_re_api.py`:
- `test_origination_pipeline_property_type_field` — asserts every `origination_by_month` item has `property_type: str`
- `test_origination_pipeline_vintage_avg_rate` — asserts every `vintage_breakdown` item has `avg_rate` (number or null)
- `test_origination_pipeline_month_rows_split_by_property_type` — asserts no duplicate `(year, month, property_type)` tuples (rows not aggregated across types)

**GREEN:**
- `OriginationMonth` schema: added `property_type: str` between `month` and `loan_count`
- `VintageGroup` schema: added `avg_rate: Optional[JsonDecimal]` after `avg_dscr`
- `get_origination_pipeline` route: origination query now groups and orders by `RELoan.property_type`; row builder maps `row[2]` to `property_type` (fallback "Unknown"), `row[3]`/`row[4]` to counts/UPB
- Vintage query: added `func.avg(RELoan.interest_rate)` as column 5; row builder maps to `avg_rate`

### Task 2 — TypeScript interfaces

- `OriginationMonth`: added `property_type: string` after `month`
- `VintageGroup`: added `avg_rate: number | null` after `avg_dscr`
- `tsc --noEmit` exits 0 with no errors

## Verification

- `python -m pytest tests/test_re_api.py -k "origination" -v` — 4/4 passed
- `npx tsc --noEmit` — exit 0

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all fields are wired to real DB columns (`RELoan.property_type`, `RELoan.interest_rate`).

## Threat Flags

No new trust-boundary surface introduced. Filter params continue to flow through existing `build_re_filters` / `FilterParams` Pydantic validation (T-24-02 mitigation confirmed present). New `group_by` column uses `RELoan.property_type` model column directly — not user input.

## Self-Check: PASSED

- `backend/api/re_schemas.py` — `property_type: str` in OriginationMonth, `avg_rate: Optional[JsonDecimal]` in VintageGroup: confirmed
- `backend/api/re_routes.py` — `RELoan.property_type` in group_by, `func.avg(RELoan.interest_rate)` in vintage query: confirmed
- `frontend/src/types/re.ts` — `property_type: string` in OriginationMonth, `avg_rate: number | null` in VintageGroup: confirmed
- Commits 958cfb4, 7192148, 662e99b all present in git log
