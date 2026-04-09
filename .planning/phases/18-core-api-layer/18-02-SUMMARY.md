---
phase: 18-core-api-layer
plan: "02"
subsystem: backend/api
tags: [fastapi, sqlalchemy, pydantic, re-portfolio, api, pagination, security, scoping]
dependency_graph:
  requires:
    - backend/api/re_schemas.py (all Pydantic models from Plan 01)
    - backend/api/re_routes.py (scaffold + 4 working endpoints from Plan 01)
    - backend/db/models.py (RELoan, RELoanCashflow)
    - backend/tests/test_re_api.py (test stubs + API-01..04 tests from Plan 01)
    - backend/tests/conftest.py (client, test_db_session, auth fixtures)
  provides:
    - backend/api/re_routes.py (all 11 /api/re/* endpoints fully implemented)
    - backend/tests/test_re_api.py (21 tests covering all 11 endpoints + full scoping)
  affects:
    - Phase 18 gate-complete: all endpoints Swagger-testable
tech_stack:
  added:
    - SQLAlchemy func.extract for origination year/month grouping
    - CPR/SMM calculation in Python post-processing from aggregated cashflow rows
    - Decimal arithmetic for all BPS scenario math (sensitivity endpoint)
  patterns:
    - Sort whitelist (ALLOWED_SORT_FIELDS) prevents arbitrary column access (T-18-03)
    - 404 for out-of-scope loan detail prevents enumeration (T-18-01/T-18-02)
    - Cashflow join scoped via build_re_filters() — same scope as loan queries (T-18-05)
    - LIVE-FEED-HOOK TODO markers in market-context for future FRED/CRE API wiring
    - Group-by period_date in cashflow query prevents Cartesian product explosion (Pitfall 6)
key_files:
  created: []
  modified:
    - backend/api/re_routes.py
    - backend/tests/test_re_api.py
decisions:
  - "[18-02-D1] sort_by param added as plain Query param (not in FilterParams) to keep FilterParams focused on data filters only; pagination params (page, page_size, sort_by, sort_dir) treated as presentation concerns."
  - "[18-02-D2] get_loan_detail adds FilterParams as Depends to apply as_of_date scope consistently — ensures sales_team scoping applies even on single-loan fetch."
  - "[18-02-D3] Sensitivity endpoint returns empty scenarios list when UPB=0 (empty portfolio guard) rather than raising 500."
  - "[18-02-D4] Cashflow CPR uses Decimal exponentiation via ** operator — Python Decimal supports integer exponents natively without float conversion."
metrics:
  duration: "~25 minutes"
  completed_date: "2026-04-08"
  tasks_completed: 3
  files_created: 0
  files_modified: 2
  tests_added: 16
  tests_passing: 21
  tests_skipped: 0
---

# Phase 18 Plan 02: Core API Layer — Complete Implementation Summary

**One-liner:** All 7 remaining /api/re/* endpoints implemented with pagination, sort whitelist, 404 scoping, cashflow join, hardcoded market stubs, and 6-BPS sensitivity scenarios; 21 tests passing with full API-11 scoping coverage.

## What Was Built

### Task 1: /loans, /loans/{id}, /cashflow-performance (API-05, API-06, API-07)

**GET /api/re/loans (API-05)**
- Paginated, filterable, sortable loan list
- Separate `page`, `page_size`, `sort_by`, `sort_dir` Query params (not in FilterParams — presentation concerns)
- `ALLOWED_SORT_FIELDS` whitelist: `{upb, ltv, dscr, interest_rate, maturity_date, origination_date, risk_rating}` — returns 400 on unknown field (T-18-03)
- `page_size` bounded via `Query(50, ge=1, le=200)` — prevents memory exhaustion (T-18-04)
- Count before pagination via `with_entities(func.count())` — Pitfall 2 guard
- `LoanSummary.model_validate(loan)` for ORM-to-schema conversion

**GET /api/re/loans/{loan_id} (API-06)**
- Adds `FilterParams` as Depends to apply `as_of_date` and sales_team scope consistently
- Returns `404` (not `403`) for both non-existent and out-of-scope loans — prevents enumeration of loan existence (T-18-02)
- Aggregates payment history via single `func.sum` / `func.count` cashflow query
- Builds `LoanDetailResponse` manually from ORM object (all extended fields included)

**GET /api/re/cashflow-performance (API-07)**
- Joins `RELoanCashflow` to `RELoan` to apply scoping filters (T-18-05)
- Groups by `period_date` — prevents Cartesian product explosion (Pitfall 6)
- Post-processes in Python: gross yield (annualized `actual_interest / total_upb * 12`), CPR via SMM formula (`1 - (1 - SMM)^12`), net loss rate clamped to 0
- All arithmetic in `Decimal` — never float

### Task 2: /origination-pipeline, /market-context, /sensitivity (API-08, API-09, API-10)

**GET /api/re/origination-pipeline (API-08)**
- Three independent aggregation queries: origination by month (year+month GROUP BY), pipeline funnel (stage GROUP BY, sorted by `PIPELINE_STAGE_ORDER` dict), vintage breakdown (vintage_year GROUP BY with avg LTV/DSCR)
- NULL origination_date and NULL vintage_year excluded from respective queries

**GET /api/re/market-context (API-09)**
- Entirely hardcoded stubs — no DB queries
- Four `TODO: LIVE-FEED-HOOK` comments marking FRED API and CRE index provider integration points
- Auth still required via `Depends(require_sales_team_access())` — prevents unauthenticated enumeration (T-18-07)
- All values: 10Y Treasury 4.25%, SOFR 5.33%, cap rates per property type, vacancy rates per property type; all `source="stub"`

**GET /api/re/sensitivity (API-10)**
- Fetches base WAC and total UPB via UPB-weighted aggregate (same pattern as KPI endpoint)
- 6 BPS scenarios: `[-300, -200, -100, 100, 200, 300]`
- All math in Decimal: `new_wac = base_wac + Decimal(bps) / 10000`, `annual_interest_impact = total_upb * bps_decimal`
- Empty portfolio guard: returns `scenarios=[]` when UPB is None/zero

### Task 3: API-11 Full Scoping Tests + Regression

**New scoping tests (5 tests):**
- `test_sales_team_scope_loans_list`: admin sees 5, sales sees 3
- `test_sales_team_scope_loan_detail_own`: sales user can fetch their own team's loan (200)
- `test_sales_team_scope_loan_detail_other`: sales user gets 404 for out-of-scope loan
- `test_sales_team_scope_concentration`: sales total loan count < admin total (scoped data confirmed)
- `test_unauthenticated_rejected`: no-auth request to /api/re/kpis returns 401

**Additional coverage tests added:**
- `test_loans_sort_invalid`: 400 on non-whitelisted sort field
- `test_loans_sort_valid`: sort_by=upb + sort_dir=desc returns correctly ordered items
- `test_loan_detail_not_found`: 404 for non-existent loan ID
- `test_loan_detail_out_of_scope_returns_404`: 404 (not 403) for out-of-scope ID

## Test Results

```
21 passed, 0 skipped — test_re_api.py (all 11 endpoint groups + full API-11 scoping)
284 passed, 2 skipped, 4 deselected — full suite (no regressions)
```

The 2 pre-existing skips are in `test_final_funding_jobs.py` (integration-marked tests, unchanged from Plan 01 baseline of 268+10 skipped).

## Deviations from Plan

### Auto-decisions (within task scope)

**1. Tasks 1 and 2 committed atomically in one feat commit**
- **Found during:** Task 1 execution
- **Situation:** The plan specifies separate tasks for the two endpoint groups (1a/1b/1c vs 2a/2b/2c), but all endpoint implementations and tests were written in the same two file edits (re_routes.py + test_re_api.py). Splitting into multiple commits would require re-reading files mid-task with no benefit.
- **Result:** Single `feat(18-02)` commit captures all 7 endpoint implementations + all 21 tests. Task 3 scoping tests were authored in the same test file write. No functional deviation — all tasks' done criteria are met.

**2. `get_loan_detail` adds FilterParams Depends**
- **Found during:** Task 1 implementation
- **Issue:** Plan stub had only `loan_id`, `current_user`, `db` — no FilterParams. Without it, `build_re_filters()` cannot apply `as_of_date` scoping, meaning a sales_team user with a specific `as_of_date` filter would get inconsistent behavior vs the list endpoint.
- **Fix:** Added `params: FilterParams = Depends(get_filter_params)` to `get_loan_detail`. Scoping is consistent with all other endpoints.
- **Impact:** No breaking change — FilterParams fields are all optional with None defaults.

None of the above required architectural changes.

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `appraisal_history: list = Field(default_factory=list)` | `backend/api/re_schemas.py:LoanDetailResponse` | Carried from Plan 01. RELoan model has no appraisal columns. Intentional Phase 18 POC stub. |
| `TODO: LIVE-FEED-HOOK` (4 occurrences) | `backend/api/re_routes.py:get_market_context` | Intentional — marks FRED API and CRE index provider integration points for production wiring. All values hardcoded as stubs. |

The market-context stubs do NOT block the plan's goal — the endpoint returns correctly shaped JSON with `source="stub"`. Frontend can render stubs and the TODO markers identify exactly where live feeds plug in.

## Threat Surface

All T-18-01 through T-18-07 mitigations applied as designed:

| Threat | Mitigation Applied |
|--------|-------------------|
| T-18-01 | build_re_filters() prepends sales_team scope; get_loan_detail uses same filters |
| T-18-02 | /loans/{id} returns 404 for both non-existent and out-of-scope — identical response |
| T-18-03 | ALLOWED_SORT_FIELDS whitelist; 400 on unknown sort_by value |
| T-18-04 | page_size constrained via Query(50, ge=1, le=200) |
| T-18-05 | cashflow-performance join applies same build_re_filters() scope |
| T-18-06 | Accept (POC-appropriate; group_by period_date bounds row count) |
| T-18-07 | market-context requires auth despite returning only stubs |

## Self-Check: PASSED

Files modified:
- backend/api/re_routes.py — FOUND (d479f24)
- backend/tests/test_re_api.py — FOUND (d479f24)

Commits:
- d479f24 feat(18-02): implement /loans, /loans/{id}, /cashflow-performance endpoints — FOUND

Test counts verified:
- test_re_api.py: 21 passed, 0 skipped — confirmed
- Full suite: 284 passed, 2 skipped — confirmed
