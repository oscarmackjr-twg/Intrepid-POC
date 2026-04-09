---
phase: 18-core-api-layer
plan: "01"
subsystem: backend/api
tags: [fastapi, pydantic, sqlalchemy, re-portfolio, api, authentication]
dependency_graph:
  requires:
    - backend/db/models.py (RELoan, RELoanCashflow models)
    - backend/auth/security.py (require_sales_team_access)
    - backend/auth/audit.py (log_data_access)
    - backend/db/connection.py (get_db)
    - backend/tests/conftest.py (client, test_db_session, auth fixtures)
  provides:
    - backend/api/re_schemas.py (all Pydantic response models for Phase 18)
    - backend/api/re_routes.py (router with 4 working + 7 stub endpoints)
    - backend/api/main.py re_router registration
    - backend/tests/test_re_api.py (test infrastructure for all 11 endpoints)
  affects:
    - backend/api/main.py (router registration added)
tech_stack:
  added:
    - Pydantic v2 ConfigDict/from_attributes pattern for SQLAlchemy ORM models
    - SQLAlchemy func.extract for year/quarter maturity grouping
    - SQLAlchemy case() for histogram bucket classification
    - get_filter_params() function-based Depends wrapper (FastAPI query-param injection pattern)
  patterns:
    - build_re_filters(db, params, user) shared filter helper — 3-arg with MAX(as_of_date) default
    - Sales-team scope injected server-side from JWT before any client filter (T-18-01)
    - All monetary/rate fields use Decimal (never float, per D-10)
    - UPB-weighted averages via func.nullif(func.sum(upb), 0) division guard
key_files:
  created:
    - backend/api/re_schemas.py
    - backend/api/re_routes.py
    - backend/tests/test_re_api.py
  modified:
    - backend/api/main.py
decisions:
  - "[18-01-D1] build_re_filters uses 3-arg signature (db, params, user) — supersedes RESEARCH.md Pattern 6 (2-arg). MAX(as_of_date) subquery requires db session."
  - "[18-01-D2] Sales-team scope filter prepended before client filters — prevents T-18-01 privilege escalation. MAX(as_of_date) also scoped to sales-team first."
  - "[18-01-D3] All 4 aggregation endpoints implemented inline with Wave 0 scaffold — tasks 2 and 3 effectively merged. Tests written and passing immediately."
  - "[18-01-D4] portfolio_yield proxied as WAC per RESEARCH.md A5 — POC-appropriate; upgrade to actual yield calculation deferred."
  - "[18-01-D5] Concentration limits hardcoded as POC policy (state:25%, property_type:40%, borrower:10%) with TODO:POLICY-CONFIG comment for DB-based config in production."
metrics:
  duration: "~35 minutes"
  completed_date: "2026-04-08"
  tasks_completed: 3
  files_created: 3
  files_modified: 1
  tests_added: 13
  tests_passing: 5
  tests_skipped: 8
---

# Phase 18 Plan 01: Core API Layer Foundation Summary

**One-liner:** Pydantic v2 schemas + FastAPI router with 4 working RE aggregation endpoints (KPIs, concentration, distributions, maturity-profile) and Wave 0 test infrastructure for all 11 endpoints.

## What Was Built

### Task 1: re_schemas.py

All Pydantic response models for the entire Phase 18 API layer:

- `FilterParams` with 10 optional fields and `get_filter_params()` function-based Depends wrapper (required because FastAPI cannot inject BaseModel directly from query params)
- `KPIResponse`, `ConcentrationResponse`, `DistributionsResponse`, `MaturityProfileResponse` for the 4 aggregation endpoints implemented this plan
- `LoanListResponse`, `LoanDetailResponse` (with `appraisal_history: list` stubbed with `TODO: APPRAISAL-HOOK` comment) for Plan 02
- `CashflowPerformanceResponse`, `OriginationPipelineResponse`, `MarketContextResponse`, `SensitivityResponse` for Plan 02
- All monetary/rate fields use `Decimal` (never `float`), per D-10 and PROJECT.md constraint

### Task 2: re_routes.py scaffold + main.py registration + test stubs

- `build_re_filters(db, params, user)`: shared 3-arg filter helper
  - Prepends sales-team scope from JWT (never from query params — T-18-01)
  - Defaults `as_of_date` to `MAX(as_of_date)` via subquery when not supplied (prevents dual-snapshot double-counting)
  - Applies all 10 FilterParams fields with parameterized binds (T-18-02)
- `router = APIRouter(prefix="/api/re", tags=["re"])` registered in `main.py`
- All 11 endpoints present: 4 implemented, 7 raise HTTP 501 stub
- `test_re_api.py`: `re_loan_fixtures` fixture (5 loans across 4 property types + 2 states, 3 with sales_team_id, 3 cashflows each); 13 tests collected

### Task 3: 4 aggregation endpoint implementations + tests fleshed out

Implementations were written inline with Task 2's scaffold (atomically). Tests active (no skip):

- **GET /api/re/kpis (API-01):** Single aggregation query with UPB-weighted WAC, WAM, WA-LTV, WA-DSCR; delinquency buckets via SQL `case()`. Zero-row guard returns all-zero response.
- **GET /api/re/concentration (API-02):** Property type, state, MSA breakdowns with pct_of_total; top-10 exposures; hardcoded POC concentration limits (state 25%, property_type 40%, borrower 10%).
- **GET /api/re/distributions (API-03):** LTV histogram (CREDIT-01 bands: <65% green, 65-75% yellow, >75% red); DSCR histogram (CREDIT-02 bands); loan size distribution (5 fixed bands).
- **GET /api/re/maturity-profile (API-04):** Year/quarter grouping via `func.extract`; null maturity_date excluded.

## Test Results

```
268 passed, 10 skipped, 4 deselected — full suite, no regressions
5 passed, 8 skipped — test_re_api.py (API-01..04 + API-11 active; API-05..10 skipped for Plan 02)
```

## Deviations from Plan

### Auto-decisions (within task scope)

**1. Tasks 2 and 3 merged atomically**
- **Found during:** Task 2 execution
- **Situation:** The plan asked for Wave 0 stubs in Task 2 and real implementations in Task 3. Since `build_re_filters()` and the 4 endpoint logic were being written anyway for the scaffold, implementing them fully in a single pass was more efficient.
- **Result:** All 4 endpoints implemented and tests passing after Task 2 commit. Task 3 verification run confirmed passing state. No functional deviation — both tasks' done criteria are met.

None — plan executed exactly as written in terms of correctness and output.

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `appraisal_history: list = Field(default_factory=list)` | `backend/api/re_schemas.py:LoanDetailResponse` | RELoan model has no appraisal columns. Intentional Phase 18 POC stub. Future plan adds appraisal table. |
| `GET /api/re/loans` | `backend/api/re_routes.py` | Plan 02 implementation |
| `GET /api/re/loans/{loan_id}` | `backend/api/re_routes.py` | Plan 02 implementation |
| `GET /api/re/cashflow-performance` | `backend/api/re_routes.py` | Plan 02 implementation |
| `GET /api/re/origination-pipeline` | `backend/api/re_routes.py` | Plan 02 implementation |
| `GET /api/re/market-context` | `backend/api/re_routes.py` | Plan 02 implementation |
| `GET /api/re/sensitivity` | `backend/api/re_routes.py` | Plan 02 implementation |

All stubs return HTTP 501 and are intentional — Plan 02 implements them. The plan's goal (4 aggregation endpoints + schema foundation) is fully achieved.

## Threat Surface

All T-18-01 through T-18-06 mitigations applied as designed:
- Sales-team scope injected server-side from JWT (T-18-01)
- All filter binds use SQLAlchemy parameterized queries (T-18-02)
- Aggregation queries apply scope before returning (T-18-03)
- Every endpoint has `Depends(require_sales_team_access())` (T-18-04, T-18-06)
- Rate limiting inherited from main.py slowapi setup (T-18-05)

## Self-Check: PASSED

Files created:
- backend/api/re_schemas.py — FOUND
- backend/api/re_routes.py — FOUND
- backend/tests/test_re_api.py — FOUND

Commits:
- d072a35 feat(18-01): create re_schemas.py with all Pydantic response models — FOUND
- b6fe16e feat(18-01): create re_routes.py scaffold, register router, and test stubs — FOUND
