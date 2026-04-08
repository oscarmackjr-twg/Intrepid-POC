# Phase 18: Core API Layer - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement all eleven `/api/re/*` FastAPI endpoints backed by the `re_loans` and `re_loan_cashflows` Postgres tables seeded in Phase 17. All endpoints must return correctly shaped JSON for their respective dashboard panels and respect filter query params. Phase gate: all endpoints verifiable in Swagger UI before any frontend work begins.

Endpoints in scope: `/api/re/kpis`, `/api/re/concentration`, `/api/re/distributions`, `/api/re/maturity-profile`, `/api/re/loans`, `/api/re/loans/{id}`, `/api/re/cashflow-performance`, `/api/re/origination-pipeline`, `/api/re/market-context`, `/api/re/sensitivity`, plus API-11 (sales_team scoping on all endpoints).

</domain>

<decisions>
## Implementation Decisions

### Router Organization
- **D-01:** All `/api/re/*` endpoints live in a new dedicated file: `backend/api/re_routes.py`. Do NOT add to the existing `routes.py` (already ~900 lines).
- **D-02:** Register `re_routes.py` as a second router in `backend/api/main.py` alongside the existing `api_router`.

### Filter Query Params
- **D-03:** Use a shared `FilterParams` FastAPI `Depends` class — one Pydantic model injected into every `/api/re/*` endpoint. No per-endpoint repetition.
- **D-04:** Include the full filter field set from FILTER-01: `as_of_date`, `property_type`, `state`, `msa`, `loan_size_min`, `loan_size_max`, `risk_rating`, `vintage_year`, `borrower`, `rate_type`. All fields optional.

### Loans List Pagination
- **D-05:** `/api/re/loans` uses offset/limit pagination via `?page=1&page_size=50`.
- **D-06:** Response envelope shape: `{"total": N, "page": N, "page_size": 50, "items": [...]}`. Default page_size = 50.

### Aggregation Strategy
- **D-07:** KPI computations (WAC, WAM, WA LTV, WA DSCR, delinquency buckets, active loan count, UPB) are computed as SQL aggregations using SQLAlchemy `func.sum` / `func.avg` with UPB-weighting. Do NOT load all rows into Python memory for dashboard aggregations.
- **D-08:** All Pydantic response models are defined in a shared `backend/api/re_schemas.py`. `re_routes.py` imports from there. This keeps routes lean and schemas importable for tests.

### Auth / Scoping (Carry-forward)
- **D-09:** All `/api/re/*` endpoints use the existing `require_sales_team_access()` dependency (or `require_role([UserRole.ADMIN, UserRole.ANALYST])` for read-only endpoints). For `sales_team` role users, filter all queries by `RELoan.sales_team_id == user.sales_team_id` before any other filter is applied (API-11).
- **D-10:** Numeric columns use `NUMERIC` / Python `Decimal`, never `float`. Consistent with PROJECT.md D-01.

### Claude's Discretion
- Exact SQLAlchemy query structure per endpoint (planner decides)
- Whether to use async SQLAlchemy session or sync (match existing pattern in `backend/db/connection.py`)
- Caching strategy (if any) — not discussed, planner decides

</decisions>

<specifics>
## Specific Ideas

- Phase verification gate: all 11 endpoints must be smoke-testable via Swagger UI (`/docs`) against the seeded dataset before Phase 18 is declared complete.
- `/api/re/market-context` returns stubbed values — no live data feed yet. Code-level markers should indicate where live integration would hook in (per API-09 / MARKET-01).
- `/api/re/sensitivity` covers +/−100/200/300 bps interest rate scenario impacts (API-10 / CREDIT-06).

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §API — All eleven API requirements (API-01 through API-11) with full acceptance criteria
- `.planning/REQUIREMENTS.md` §FILTER — Filter field definitions (FILTER-01 through FILTER-04)

### Data Models
- `backend/db/models.py` — `RELoan` and `RELoanCashflow` model definitions (all available fields for aggregations)

### Auth Patterns
- `backend/auth/security.py` — `require_role`, `require_sales_team_access`, `get_current_user`
- `backend/auth/validators.py` — `get_user_sales_team_id`
- `backend/api/routes.py` — Existing auth usage patterns (lines 178–179 for sales_team scoping example)

### Database
- `backend/db/connection.py` — `get_db` session dependency (sync pattern to match)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `require_sales_team_access()` / `require_role()` — Drop-in auth dependencies for all `/api/re/*` endpoints
- `get_user_sales_team_id()` — Returns `sales_team_id` for filtering; already used in `routes.py:404`
- `get_db` — Standard SQLAlchemy session dependency, used on every existing endpoint
- `APIRouter` pattern — Register new `re_routes.py` router in `main.py` identically to `api_router`

### Integration Points
- `backend/api/main.py` — Add `from api.re_routes import router as re_router` and `app.include_router(re_router)`
- `backend/db/models.py` — `RELoan.sales_team_id` FK already present; standard filter: `query.filter(RELoan.sales_team_id == user.sales_team_id)`

### Established Patterns to Follow
- Sync SQLAlchemy (`Session`, `get_db`) — match existing `routes.py` style (not async)
- Response models defined outside route functions and referenced in `response_model=` param
- Audit logging via `log_data_access(current_user, ...)` for data reads (see `routes.py:481`)

</code_context>

---

*Phase: 18-core-api-layer*
*Context gathered: 2026-04-08 via /gsd-discuss-phase*
