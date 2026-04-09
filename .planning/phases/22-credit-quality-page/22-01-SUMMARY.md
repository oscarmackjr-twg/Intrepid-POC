---
phase: 22-credit-quality-page
plan: "01"
subsystem: backend-api
tags:
  - re-portfolio
  - credit-quality
  - endpoints
  - pydantic
  - tdd
dependency_graph:
  requires:
    - backend/api/re_routes.py
    - backend/api/re_schemas.py
    - backend/db/models.py
  provides:
    - GET /api/re/delinquency-waterfall
    - GET /api/re/risk-rating-migration
    - LoanSummary.prior_risk_rating
  affects:
    - frontend/src (Credit Quality page consumers)
tech_stack:
  added: []
  patterns:
    - SQLAlchemy case() expression for DPD bucketing
    - Derived ratings list from query result (not hardcoded)
    - TDD RED/GREEN cycle with fixture extension
key_files:
  created: []
  modified:
    - backend/api/re_schemas.py
    - backend/api/re_routes.py
    - backend/tests/test_re_api.py
decisions:
  - "Numeric risk_rating strings (1-5) used in fixture to enable integer sort on migration ratings list"
  - "DPD bucket boundary: days_past_due==0 is current; <60 is 30-bucket; <90 is 60-bucket; <180 is 90-bucket; else default"
  - "prior_risk_rating added to LoanSummary (not just LoanDetailResponse) to avoid N+1 calls from watchlist table"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-04-09"
  tasks_completed: 2
  files_modified: 3
requirements:
  - CREDIT-01
  - CREDIT-02
  - CREDIT-03
  - CREDIT-04
  - CREDIT-05
---

# Phase 22 Plan 01: Credit Quality Backend Endpoints Summary

Two new GET endpoints, four new Pydantic schemas, and prior_risk_rating added to LoanSummary — providing the full backend data layer for the Credit Quality page's delinquency waterfall, risk rating migration matrix, and watchlist trend arrows.

## Objective

Add backend support for the Credit Quality page: GET /api/re/delinquency-waterfall (CREDIT-04), GET /api/re/risk-rating-migration (CREDIT-05), prior_risk_rating in LoanSummary (CREDIT-03), and confirm existing distribution endpoints already return color bands (CREDIT-01, CREDIT-02).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write failing tests (RED) | 979c0d3 | backend/tests/test_re_api.py |
| 2 | Implement endpoints and schema fix (GREEN) | 37dd024 | backend/api/re_schemas.py, backend/api/re_routes.py |

## What Was Built

### New Schemas (re_schemas.py)
- `DelinquencyBucket` — single bucket with `bucket`, `loan_count`, `total_upb`
- `DelinquencyWaterfallResponse` — wraps `buckets: list[DelinquencyBucket]`
- `MigrationCell` — single matrix cell with `prior_rating`, `current_rating`, `loan_count`, `total_upb`
- `RiskRatingMigrationResponse` — wraps `cells` list + sorted `ratings` list
- `LoanSummary.prior_risk_rating: Optional[str] = None` — added field (CREDIT-03)

### New Endpoints (re_routes.py)
- `GET /api/re/delinquency-waterfall` — SQLAlchemy `case()` expression groups loans into 5 exclusive DPD buckets (current/30/60/90/default), sorted by defined order
- `GET /api/re/risk-rating-migration` — Groups loans by (prior_risk_rating, risk_rating) pairs, derives sorted ratings list from actual data

### Security (T-22-01 mitigated)
Both new endpoints use `Depends(require_sales_team_access())` and call `build_re_filters(db, params, current_user)` — sales_team users see only their scoped loans.

### Tests (test_re_api.py)
- 5 new test functions added
- Fixture extended: loans 1-5 updated with numeric risk_rating (1-5) and prior_risk_rating values; loans 6 (RE-006, 60dpd) and 7 (RE-007, default) added for waterfall coverage
- Count assertions updated: admin active_loan_count=7, admin total=7

## Test Results

```
26 passed in tests/test_re_api.py
289 passed, 2 skipped, 4 deselected in full suite — no regressions
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All endpoints return live query results from the test database.

## Threat Flags

No new security surface beyond what the plan's threat model addressed. T-22-01 mitigated via `build_re_filters` + `require_sales_team_access` on both new endpoints.

## Self-Check: PASSED

- [x] `backend/api/re_schemas.py` modified — confirmed
- [x] `backend/api/re_routes.py` modified — confirmed
- [x] `backend/tests/test_re_api.py` modified — confirmed
- [x] Commit 979c0d3 exists (RED tests)
- [x] Commit 37dd024 exists (GREEN implementation)
- [x] All 26 test_re_api.py tests pass
- [x] Full suite 289 passed, no failures
