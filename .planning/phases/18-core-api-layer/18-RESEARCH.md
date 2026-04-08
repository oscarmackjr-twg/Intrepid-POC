# Phase 18: Core API Layer - Research

**Researched:** 2026-04-08
**Domain:** FastAPI endpoint implementation — SQLAlchemy aggregation, filter dependencies, pagination, role-scoped queries
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** All `/api/re/*` endpoints live in `backend/api/re_routes.py`. Do NOT add to existing `routes.py`.
- **D-02:** Register `re_routes.py` as a second router in `backend/api/main.py` alongside `api_router`.
- **D-03:** Shared `FilterParams` FastAPI `Depends` class — one Pydantic model injected into every `/api/re/*` endpoint. No per-endpoint repetition.
- **D-04:** Full filter field set: `as_of_date`, `property_type`, `state`, `msa`, `loan_size_min`, `loan_size_max`, `risk_rating`, `vintage_year`, `borrower`, `rate_type`. All fields optional.
- **D-05:** `/api/re/loans` uses offset/limit pagination via `?page=1&page_size=50`.
- **D-06:** Response envelope: `{"total": N, "page": N, "page_size": 50, "items": [...]}`. Default page_size = 50.
- **D-07:** KPI computations via SQL aggregations — `func.sum` / `func.avg` with UPB-weighting. Never load all rows into Python.
- **D-08:** All Pydantic response models in `backend/api/re_schemas.py`. `re_routes.py` imports from there.
- **D-09:** All `/api/re/*` endpoints use `require_sales_team_access()` or `require_role(...)`. For `sales_team` role users, filter all queries by `RELoan.sales_team_id == user.sales_team_id` before any other filter.
- **D-10:** Numeric columns use `NUMERIC` / Python `Decimal`, never `float`.

### Claude's Discretion

- Exact SQLAlchemy query structure per endpoint
- Whether to use async SQLAlchemy session or sync (match existing pattern)
- Caching strategy (if any)

### Deferred Ideas (OUT OF SCOPE)

- Live market data feeds
- PostgreSQL RLS
- Loan edit/write UI
- MSA-level geo drill-down (state-level only)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-01 | `/api/re/kpis` — total UPB, WAC (UPB-weighted), WAM, WA LTV, WA DSCR, active loan count, delinquency buckets, portfolio yield | SQLAlchemy `func.sum`/`func.avg` + UPB-weight formula documented in Architecture Patterns |
| API-02 | `/api/re/concentration` — property type breakdown, state/MSA concentration, top-10 exposures, concentration limit proximity | `func.sum` grouped by `property_type`, `state`, `msa`; order_by UPB desc limit 10 |
| API-03 | `/api/re/distributions` — LTV histogram, DSCR histogram, loan size distribution | CASE-based bucket aggregation or Python-side binning on aggregated data |
| API-04 | `/api/re/maturity-profile` — loan counts and UPB grouped by quarter/year | `func.extract` on `maturity_date`; group by year+quarter |
| API-05 | `/api/re/loans` — paginated, filterable, sortable loan list | offset/limit pattern; FilterParams Depends; total via `func.count` subquery |
| API-06 | `/api/re/loans/{id}` — full loan detail including payment history summary | Single RELoan + aggregated cashflow summary |
| API-07 | `/api/re/cashflow-performance` — monthly P&I actual vs projected, NOI trend, gross/net yield, CPR, loss/recovery | Grouped by `period_date` on `re_loan_cashflows`; join to RELoan for UPB |
| API-08 | `/api/re/origination-pipeline` — origination by month, payoffs/paydowns, pipeline funnel stage counts, vintage breakdown | Group by `origination_date` month; `pipeline_stage` counts; `vintage_year` groups |
| API-09 | `/api/re/market-context` — stubbed benchmark rates + CRE indices with live-feed hook markers | Hardcoded Python dict; code comments mark integration points |
| API-10 | `/api/re/sensitivity` — portfolio impact under +/-100/200/300 bps scenarios | Python-side computation on UPB-weighted aggregates from DB |
| API-11 | All `/api/re/*` endpoints enforce `sales_team_id` scope server-side for `sales_team` role users | `require_sales_team_access()` + conditional `filter(RELoan.sales_team_id == user.sales_team_id)` |
</phase_requirements>

---

## Summary

Phase 18 implements 11 read-only FastAPI endpoints backed by the `re_loans` and `re_loan_cashflows` tables seeded in Phase 17. All patterns needed for implementation already exist in the codebase — the new router follows the same sync SQLAlchemy (`Session` + `get_db`) style as `routes.py`, and auth/scoping reuses `require_sales_team_access()` and `get_user_sales_team_id()` unchanged.

The two new files are `backend/api/re_routes.py` (endpoint functions) and `backend/api/re_schemas.py` (Pydantic response models). A shared `FilterParams` Depends class applied to every endpoint avoids per-endpoint query-param repetition. KPI aggregations are computed in SQL using `func.sum`/`func.avg` with UPB-weighting — never loading full row sets. The loans list endpoint uses offset/limit pagination with a total-count query.

The most complex endpoints are API-01 (UPB-weighted WAC/WAM/LTV/DSCR), API-07 (cashflow performance metrics including CPR), and API-10 (sensitivity scenarios). These require compound SQL expressions. All other endpoints are straightforward grouped aggregations or single-row lookups.

**Primary recommendation:** Implement in two waves — Wave 1: re_schemas.py + FilterParams + the four aggregation endpoints (API-01, 02, 03, 04) + the loans list (API-05) + loan detail (API-06). Wave 2: cashflow performance (API-07), origination pipeline (API-08), market context stub (API-09), sensitivity (API-10), and the scope enforcement integration test (API-11).

---

## Standard Stack

All libraries are already installed in the project. No new dependencies required. [VERIFIED: backend/requirements.txt via codebase grep]

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | API framework, router, Depends, Query | Already the app framework |
| SQLAlchemy (sync) | existing | ORM queries, `func.sum`, `func.avg`, `func.count` | Matches existing `routes.py` pattern — sync `Session` |
| Pydantic v2 | existing | Response models in `re_schemas.py`, `FilterParams` | Already used for all response models |
| python-jose | existing | JWT decode in `get_current_user` (auth flow unchanged) | Already wired |

### No New Installations Needed

All dependencies (FastAPI, SQLAlchemy, Pydantic, python-jose, passlib, slowapi) are already in `requirements.txt`. The router registration in `main.py` requires only a one-line import and `app.include_router(re_router)`.

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
backend/
├── api/
│   ├── re_routes.py     # All /api/re/* endpoint functions (new)
│   └── re_schemas.py    # Pydantic response models for all RE endpoints (new)
├── tests/
│   └── test_re_api.py   # API endpoint tests (new — Wave 0)
```

### Pattern 1: Router Registration in main.py

**What:** Add re_router to `main.py` alongside existing routers.
**When to use:** Required once — identical pattern to existing routers.
**Example:**
```python
# Source: backend/api/main.py (existing pattern)
from api.re_routes import router as re_router
# ...
app.include_router(re_router)  # add after program_run_jobs_router
```

The `re_routes.py` router prefix should be `/api/re` with tag `re`:
```python
router = APIRouter(prefix="/api/re", tags=["re"])
```

### Pattern 2: Shared FilterParams Depends Class

**What:** Single Pydantic class injected into every `/api/re/*` endpoint via FastAPI `Depends`. All fields optional with `None` defaults.
**When to use:** Every endpoint function signature.

```python
# Source: FastAPI Depends pattern — [ASSUMED based on FastAPI docs conventions]
from fastapi import Depends, Query
from pydantic import BaseModel
from typing import Optional
from datetime import date

class FilterParams(BaseModel):
    as_of_date: Optional[date] = None
    property_type: Optional[str] = None
    state: Optional[str] = None
    msa: Optional[str] = None
    loan_size_min: Optional[float] = None  # Note: use Decimal in query, not float
    loan_size_max: Optional[float] = None
    risk_rating: Optional[str] = None
    vintage_year: Optional[int] = None
    borrower: Optional[str] = None
    rate_type: Optional[str] = None

# FastAPI query-param injection for Pydantic models:
def get_filter_params(
    as_of_date: Optional[date] = Query(None),
    property_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    msa: Optional[str] = Query(None),
    loan_size_min: Optional[float] = Query(None),
    loan_size_max: Optional[float] = Query(None),
    risk_rating: Optional[str] = Query(None),
    vintage_year: Optional[int] = Query(None),
    borrower: Optional[str] = Query(None),
    rate_type: Optional[str] = Query(None),
) -> FilterParams:
    return FilterParams(...)
```

**IMPORTANT NOTE:** FastAPI cannot directly inject a Pydantic BaseModel from query params using `Depends(FilterParams)` in older patterns. The correct approach is a function-based Depends (shown above) or a class with `__init__` accepting Query-annotated params. Use the function-based approach shown — it matches the existing Query() pattern in `routes.py`. [ASSUMED — pattern matches FastAPI docs conventions for query-param grouping]

### Pattern 3: Sales Team Scope Filter (API-11)

**What:** For `sales_team` role users, prepend `RELoan.sales_team_id` filter before any other filter is applied.
**When to use:** Every `/api/re/*` endpoint — identical helper function.

```python
# Source: backend/api/routes.py lines 176-183 (existing filter_by_sales_team pattern)
def apply_re_scope(query, user: User):
    """Apply sales_team_id scope filter to any RELoan query."""
    if user.role == UserRole.SALES_TEAM and user.sales_team_id:
        return query.filter(RELoan.sales_team_id == user.sales_team_id)
    return query  # admin and analyst see all
```

Auth dependency for all RE endpoints (read-only, all three roles allowed):
```python
current_user: User = Depends(require_sales_team_access())
```

`require_sales_team_access()` [VERIFIED: backend/auth/security.py lines 132-140] raises 403 if a `sales_team` user has no `sales_team_id` assigned — exactly the right guard for all RE endpoints.

### Pattern 4: UPB-Weighted Aggregation (API-01)

**What:** Compute WAC, WAM, WA LTV, WA DSCR as `SUM(value * upb) / SUM(upb)` in SQL.
**When to use:** KPI endpoint only. Never compute in Python across full row set (D-07).

```python
# Source: SQLAlchemy func documentation [ASSUMED — standard SQL pattern]
from sqlalchemy import func
from decimal import Decimal

wac = (
    func.sum(RELoan.interest_rate * RELoan.upb) /
    func.nullif(func.sum(RELoan.upb), 0)
)
wa_ltv = (
    func.sum(RELoan.ltv * RELoan.upb) /
    func.nullif(func.sum(RELoan.upb), 0)
)
```

Use `func.nullif(..., 0)` to guard against division by zero when UPB sum is zero (empty filter result).

Delinquency buckets via conditional sums:
```python
from sqlalchemy import case

bucket_30 = func.sum(case((RELoan.days_past_due >= 30, RELoan.upb), else_=0))
bucket_60 = func.sum(case((RELoan.days_past_due >= 60, RELoan.upb), else_=0))
bucket_90 = func.sum(case((RELoan.days_past_due >= 90, RELoan.upb), else_=0))
```

### Pattern 5: Offset/Limit Pagination (API-05)

**What:** Page-based pagination with a separate count query.
**When to use:** `/api/re/loans` only.

```python
# Source: Standard SQLAlchemy pattern [ASSUMED]
offset = (page - 1) * page_size
items = query.offset(offset).limit(page_size).all()
total = query.with_entities(func.count()).scalar()
# Response: {"total": total, "page": page, "page_size": page_size, "items": items}
```

Run the `func.count()` query before applying `offset`/`limit` so `total` reflects the full filtered count, not the page count.

### Pattern 6: build_filters() Helper

**What:** Single function that converts `FilterParams` + scope into a list of SQLAlchemy filter clauses.
**When to use:** Called at the top of every endpoint to keep endpoint bodies lean.

```python
# Source: [ASSUMED — recommended pattern based on existing codebase style]
def build_re_filters(params: FilterParams, user: User) -> list:
    filters = []
    # Scope first (API-11)
    if user.role == UserRole.SALES_TEAM and user.sales_team_id:
        filters.append(RELoan.sales_team_id == user.sales_team_id)
    # Then client-supplied filters
    if params.as_of_date:
        filters.append(RELoan.as_of_date == params.as_of_date)
    if params.property_type:
        filters.append(RELoan.property_type == params.property_type)
    if params.state:
        filters.append(RELoan.state == params.state)
    if params.msa:
        filters.append(RELoan.msa == params.msa)
    if params.loan_size_min is not None:
        filters.append(RELoan.upb >= params.loan_size_min)
    if params.loan_size_max is not None:
        filters.append(RELoan.upb <= params.loan_size_max)
    if params.risk_rating:
        filters.append(RELoan.risk_rating == params.risk_rating)
    if params.vintage_year:
        filters.append(RELoan.vintage_year == params.vintage_year)
    if params.borrower:
        filters.append(RELoan.borrower_name.ilike(f"%{params.borrower}%"))
    if params.rate_type:
        filters.append(RELoan.rate_type == params.rate_type)
    return filters
```

Usage in every endpoint: `query = db.query(...).filter(*build_re_filters(filters, current_user))`

### Pattern 7: Audit Logging (Data Access)

**What:** Log data access for all read endpoints — matches existing pattern in `routes.py:481`.
**When to use:** Every GET endpoint.

```python
# Source: backend/api/routes.py line 481 (existing pattern)
from auth.audit import log_data_access
log_data_access(current_user, "re_loans", sales_team_id=current_user.sales_team_id)
```

### Pattern 8: Returning Decimal-safe JSON

**What:** Pydantic v2 serializes `Decimal` to JSON string by default. Must configure `json_encoders` or use `model_config` to serialize as numeric type.
**When to use:** All RE schema models containing `Decimal` fields.

```python
# Source: Pydantic v2 docs [ASSUMED]
from pydantic import BaseModel, ConfigDict
from decimal import Decimal

class KPIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_upb: Decimal
    wac: Decimal | None
    # ...
```

Pydantic v2 with `from_attributes=True` serializes `Decimal` as a JSON number (not string) when used via FastAPI's default `JSONResponse`. Verify this in tests — if serialized as string, add a custom serializer. [ASSUMED — behavior depends on Pydantic version and FastAPI integration]

### Anti-Patterns to Avoid

- **Loading full row sets for aggregation:** Never `db.query(RELoan).all()` then compute in Python. All KPI/distribution/concentration data must use SQL aggregation (D-07).
- **Repeating filter params per endpoint:** Use the shared `FilterParams` Depends + `build_re_filters()`. Any per-endpoint repetition creates drift.
- **Float for monetary fields:** All response model fields that map to `NUMERIC(18,6)` or `NUMERIC(10,6)` columns must use `Decimal`, not `float` (D-10).
- **sales_team_id as a client query param:** Never expose `sales_team_id` as a user-controllable query param. It is injected server-side from the JWT via `user.sales_team_id` (confirmed in STATE.md: "sales_team_id scope injected server-side from JWT in build_filters() — never a user-facing query param").
- **Async session:** The existing codebase uses synchronous `Session` / `get_db`. Do not introduce `AsyncSession` — it requires a different engine and will break the test harness (D — Claude's discretion, but pattern is clear from existing code).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT auth + user lookup | Custom token parsing | `get_current_user` (existing) | Already handles cookie + header fallback, expiry, user-not-found |
| Sales team scope guard | Manual role check in each endpoint | `require_sales_team_access()` (existing) | Raises 403 if `sales_team` user has no assignment |
| Sales team ID for filtering | `user.sales_team_id` manual check | `get_user_sales_team_id()` from `auth/validators.py` | Validates assignment and returns ID atomically |
| Audit trail | Custom logger calls | `log_data_access()` from `auth/audit.py` | Writes to both logger and audit_log table; failures non-propagating |
| Rate limiting | Custom middleware | `slowapi` (already wired to app) | Already wired in `main.py`; auto-applies to all routes |
| UPB-weighted average | Python loop after DB fetch | `func.sum(value * upb) / func.sum(upb)` in SQL | Single round-trip, scales to 2000+ loans, avoids memory overhead |

**Key insight:** The auth/audit infrastructure is fully production-ready. Every endpoint is a thin function that calls `build_re_filters()`, runs 1-2 SQL queries, and returns a schema instance. No custom middleware, no new auth logic.

---

## Common Pitfalls

### Pitfall 1: FilterParams as Pydantic BaseModel Injected Directly via Depends

**What goes wrong:** `Depends(FilterParams)` does not auto-wire query params from a Pydantic `BaseModel` in FastAPI when the model has complex field types (e.g., `Optional[date]`). FastAPI will attempt to parse it as a request body instead.
**Why it happens:** FastAPI's automatic query param injection from `Depends` only works with classes that have `__init__` parameters decorated with `Query(...)` annotations, or with a function-based Depends.
**How to avoid:** Use a function `def get_filter_params(as_of_date: Optional[date] = Query(None), ...) -> FilterParams` and inject with `Depends(get_filter_params)`. [ASSUMED — known FastAPI behavior, confirm in implementation]
**Warning signs:** Swagger UI shows FilterParams as a request body field rather than query params.

### Pitfall 2: Count Query After offset/limit Applied

**What goes wrong:** Running `query.count()` after `.offset()` and `.limit()` have been applied returns the page count (e.g., 50), not the total filtered count.
**Why it happens:** The count executes against the already-windowed query.
**How to avoid:** Clone the base query before applying offset/limit. Use `count_query = base_query.with_entities(func.count(RELoan.id)).scalar()` first, then apply pagination.
**Warning signs:** `total` field always equals `page_size` in pagination response.

### Pitfall 3: Division by Zero in Weighted Averages

**What goes wrong:** When filters return zero loans, `SUM(upb)` is 0, causing a division-by-zero error in WAC/WAM/WA LTV/WA DSCR computation.
**Why it happens:** SQL division by zero raises a DB-level error in Postgres.
**How to avoid:** Wrap the denominator in `func.nullif(func.sum(RELoan.upb), 0)`. Return `None` for weighted averages when result is `NULL`.
**Warning signs:** 500 errors when applying aggressive filters that produce no matching loans.

### Pitfall 4: Decimal Serialization in JSON

**What goes wrong:** `Decimal` values serialize as strings (`"5.250000"`) rather than numbers (`5.25`) in JSON, causing frontend parse errors.
**Why it happens:** Python's `json` module does not natively serialize `Decimal`. FastAPI's default behavior may vary by Pydantic version.
**How to avoid:** Add `model_config = ConfigDict(from_attributes=True)` to all schema models. If Decimal still serializes as string, add a custom field serializer or use `json_encoders`. Verify in tests against the actual JSON output.
**Warning signs:** Frontend receives `"wac": "5.250000"` (string) instead of `"wac": 5.25` (number).

### Pitfall 5: Missing as_of_date Filter Causes Multi-Snapshot Duplication

**What goes wrong:** The `re_loans` table has two `as_of_date` snapshots (T0 and T1 from seeding). Without an `as_of_date` filter, KPI aggregations double-count loans (same loan appears in both snapshots).
**Why it happens:** The seed script creates 500 T0 loans and 500 T1 loans with the same `loan_number` values but different `as_of_date` values.
**How to avoid:** The `as_of_date` filter in `FilterParams` must default to the latest available `as_of_date` when not supplied, OR the API documentation must clearly note that callers must supply `as_of_date` to avoid cross-snapshot aggregation. The recommended approach: if `as_of_date` is not supplied, default to `MAX(as_of_date)` via a subquery.
**Warning signs:** KPI endpoint returns exactly double the expected UPB when no `as_of_date` filter is active.

### Pitfall 6: Cashflow Joins Amplify Loan Count

**What goes wrong:** For `cashflow-performance` (API-07), joining `re_loan_cashflows` to `re_loans` without aggregating by `period_date` returns one row per cashflow record per loan (12 months × N loans = 12N rows).
**Why it happens:** SQLAlchemy join without group-by produces a Cartesian product of the join.
**How to avoid:** Always group cashflow queries by `period_date` and sum the cashflow amounts. The join is needed only to apply `RELoan` filters (property type, state, etc.) to cashflow data.
**Warning signs:** API-07 returns many thousands of rows instead of 12 monthly aggregates.

### Pitfall 7: Router Prefix Collision

**What goes wrong:** If `re_routes.py` router is registered with prefix `/api` instead of `/api/re`, all endpoints will have paths like `/api/kpis` instead of `/api/re/kpis`, silently shadowing existing routes.
**Why it happens:** Simple copy-paste error from existing router config.
**How to avoid:** Set `router = APIRouter(prefix="/api/re", tags=["re"])` in `re_routes.py`. Verify in Swagger UI (`/docs`) that all endpoints appear under the `/api/re/` path group.
**Warning signs:** Existing endpoints in `routes.py` start returning 404 or unexpected responses.

---

## Code Examples

### Verified Patterns from Codebase

#### Auth Dependency Pattern (All Endpoints)
```python
# Source: backend/api/routes.py lines 186-190 (existing pattern)
@router.get("/kpis", response_model=KPIResponse)
def get_kpis(
    filters: FilterParams = Depends(get_filter_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_team_access()),
):
    log_data_access(current_user, "re_loans_kpis", sales_team_id=current_user.sales_team_id)
    base_filters = build_re_filters(filters, current_user)
    # ... SQL aggregation
```

#### Sync Session Pattern (matches existing codebase)
```python
# Source: backend/db/connection.py lines 15-21
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### Sales Team Filter (Existing Routes Pattern)
```python
# Source: backend/api/routes.py lines 176-183
def filter_by_sales_team(query, user: User):
    if user.role == UserRole.SALES_TEAM and user.sales_team_id:
        return query.filter(PipelineRun.sales_team_id == user.sales_team_id)
    elif user.role == UserRole.ADMIN:
        return query
    else:
        return query
```
The RE version of this helper replaces `PipelineRun.sales_team_id` with `RELoan.sales_team_id`.

#### Router Registration Pattern (main.py)
```python
# Source: backend/api/main.py lines 19-23 (existing pattern)
from api.routes import router as api_router
from api.re_routes import router as re_router  # new
# ...
app.include_router(api_router)
app.include_router(re_router)  # new — add after existing routers
```

#### Pydantic Response Model with from_attributes
```python
# Source: backend/api/routes.py lines 167-173 (HolidayResponse pattern)
class HolidayResponse(HolidayBase):
    id: int
    class Config:
        from_attributes = True
```
All RE schemas must include `model_config = ConfigDict(from_attributes=True)` (Pydantic v2 style) or `class Config: from_attributes = True`.

### KPI Aggregation Query Skeleton
```python
# Source: [ASSUMED — SQLAlchemy func pattern]
from sqlalchemy import func, case
from decimal import Decimal

result = db.query(
    func.sum(RELoan.upb).label("total_upb"),
    func.count(RELoan.id).label("active_loan_count"),
    (
        func.sum(RELoan.interest_rate * RELoan.upb) /
        func.nullif(func.sum(RELoan.upb), 0)
    ).label("wac"),
    (
        func.sum(RELoan.wam_months * RELoan.upb) /
        func.nullif(func.sum(RELoan.upb), 0)
    ).label("wam"),
    (
        func.sum(RELoan.ltv * RELoan.upb) /
        func.nullif(func.sum(RELoan.upb), 0)
    ).label("wa_ltv"),
    (
        func.sum(RELoan.dscr * RELoan.upb) /
        func.nullif(func.sum(RELoan.upb), 0)
    ).label("wa_dscr"),
    func.sum(case((RELoan.days_past_due >= 30, RELoan.upb), else_=0)).label("delinquent_30_upb"),
    func.sum(case((RELoan.days_past_due >= 60, RELoan.upb), else_=0)).label("delinquent_60_upb"),
    func.sum(case((RELoan.days_past_due >= 90, RELoan.upb), else_=0)).label("delinquent_90_upb"),
).filter(*build_re_filters(filters, current_user)).one()
```

### Pagination Query Skeleton
```python
# Source: [ASSUMED — standard SQLAlchemy pagination]
base_query = db.query(RELoan).filter(*build_re_filters(filters, current_user))
total = base_query.with_entities(func.count(RELoan.id)).scalar()
offset = (page - 1) * page_size
items = base_query.order_by(RELoan.id).offset(offset).limit(page_size).all()
return PaginatedLoansResponse(total=total, page=page, page_size=page_size, items=items)
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| Pydantic v1 `class Config: orm_mode = True` | Pydantic v2 `model_config = ConfigDict(from_attributes=True)` | Must use v2 style to match existing models |
| SQLAlchemy `Query.count()` | `query.with_entities(func.count()).scalar()` | More explicit; avoids subquery wrapping issues |
| `func.avg()` for weighted average | `func.sum(val * weight) / func.sum(weight)` | True UPB-weighted average, not simple mean |

---

## Endpoint-by-Endpoint Implementation Notes

### API-01: /api/re/kpis

Single `.one()` query using compound `func.sum`/`func.avg` expressions. Key fields:
- `total_upb`: `func.sum(RELoan.upb)`
- `wac`: UPB-weighted `interest_rate`
- `wam`: UPB-weighted `wam_months`
- `wa_ltv`: UPB-weighted `ltv`
- `wa_dscr`: UPB-weighted `dscr`
- `active_loan_count`: `func.count(RELoan.id)` (all rows in filter = active)
- `delinquency_buckets`: three `func.sum(case(...))` for 30/60/90+ dpd
- `portfolio_yield`: same as WAC — interest_rate UPB-weighted (proxy metric for POC)

**Default as_of_date handling:** If `filters.as_of_date` is None, add a default filter using `func.max(RELoan.as_of_date)` via subquery:
```python
if not filters.as_of_date:
    latest = db.query(func.max(RELoan.as_of_date)).scalar()
    if latest:
        base_filters.append(RELoan.as_of_date == latest)
```

### API-02: /api/re/concentration

Multiple grouped queries:
1. `GROUP BY property_type` with `func.sum(upb)`, `func.count(id)`
2. `GROUP BY state` with `func.sum(upb)` — returns top N by UPB
3. `GROUP BY msa` with `func.sum(upb)` — returns top N by UPB
4. Top-10 exposures: `ORDER BY upb DESC LIMIT 10` returning individual loan rows
5. Concentration limit proximity: compute percentage of total UPB per category; compare against hardcoded policy limits (e.g., single-borrower cap 10%, single-state cap 25%) — policy limits are POC constants, not DB config

### API-03: /api/re/distributions

Histogram binning approaches:
- **Option A (SQL bins):** Use SQL `CASE` expressions to assign bucket labels, then `GROUP BY` bucket. Most efficient.
- **Option B (Python bins):** Fetch aggregated data (e.g., all distinct LTV values with loan counts) then bin in Python. Acceptable only if distinct value count is small.

Recommended: Option A with fixed LTV buckets matching CREDIT-01 bands (`<0.65`, `0.65-0.75`, `>0.75`) and DSCR bands (`>1.4`, `1.0-1.4`, `<1.0`). Loan size bins can be dynamic if needed.

### API-04: /api/re/maturity-profile

```python
# Source: [ASSUMED — func.extract pattern]
from sqlalchemy import func, extract

db.query(
    extract('year', RELoan.maturity_date).label('year'),
    extract('quarter', RELoan.maturity_date).label('quarter'),
    func.count(RELoan.id).label('loan_count'),
    func.sum(RELoan.upb).label('total_upb'),
).filter(*base_filters).group_by('year', 'quarter').order_by('year', 'quarter').all()
```

### API-05: /api/re/loans

Sortable via optional `sort_by` and `sort_dir` query params (not in FilterParams — separate Query params). Default sort: `id ASC`. Expose `sort_by` options: `upb`, `ltv`, `dscr`, `interest_rate`, `maturity_date`, `origination_date`.

### API-06: /api/re/loans/{id}

Single `db.query(RELoan).filter(RELoan.id == loan_id).first()`. Apply scope check: if user is `sales_team` and loan's `sales_team_id` does not match, return 404 (not 403 — avoids disclosing loan existence). Payment history summary: aggregate linked cashflows (last 12 months `scheduled_interest`, `actual_interest`, `scheduled_principal`, `actual_principal` sums).

### API-07: /api/re/cashflow-performance

Join `RELoanCashflow` to `RELoan`, filter on `RELoan` columns using `build_re_filters`, group by `period_date`:
```python
db.query(
    RELoanCashflow.period_date,
    func.sum(RELoanCashflow.scheduled_principal).label("scheduled_principal"),
    func.sum(RELoanCashflow.actual_principal).label("actual_principal"),
    func.sum(RELoanCashflow.scheduled_interest).label("scheduled_interest"),
    func.sum(RELoanCashflow.actual_interest).label("actual_interest"),
    func.sum(RELoanCashflow.noi).label("total_noi"),
).join(RELoan, RELoanCashflow.loan_id == RELoan.id).filter(
    *build_re_filters(filters, current_user)
).group_by(RELoanCashflow.period_date).order_by(RELoanCashflow.period_date).all()
```

CPR (Conditional Prepayment Rate) computation: `CPR = 1 - (1 - SMM)^12` where `SMM = (actual_principal - scheduled_principal) / beginning_upb`. This requires UPB at start of period — approximate as loan's `upb` from `re_loans` (POC-level accuracy). Compute in Python after fetching aggregated cashflow data.

### API-08: /api/re/origination-pipeline

Uses `origination_date` and `pipeline_stage` columns from `re_loans`:
- Origination volume: `GROUP BY EXTRACT(year, origination_date), EXTRACT(month, origination_date)`
- Pipeline funnel: `GROUP BY pipeline_stage ORDER BY stage_order` (stage_order: hardcoded dict `{"underwriting": 1, "approved": 2, "closing": 3, "funded": 4}`)
- Vintage breakdown: `GROUP BY vintage_year`

### API-09: /api/re/market-context

Entirely hardcoded stub:
```python
# TODO: LIVE-FEED-HOOK — replace with FRED API call for 10Y Treasury
MARKET_CONTEXT_STUB = {
    "ten_year_treasury": {"value": 4.25, "trend": "flat", "source": "stub"},
    "sofr": {"value": 5.33, "trend": "declining", "source": "stub"},
    "cap_rates": {
        "multifamily": {"value": 5.0, "source": "stub"},
        "office": {"value": 7.5, "source": "stub"},
        # ...
    },
    # TODO: LIVE-FEED-HOOK — replace with CRE index provider API call
    "vacancy_rates": {...}
}
```

Markers are literal code comments `# TODO: LIVE-FEED-HOOK` per CONTEXT.md specifics.

### API-10: /api/re/sensitivity

Fetch UPB-weighted average interest rate and total UPB from DB (filtered). Then compute Python-side:
```python
scenarios = [-300, -200, -100, 100, 200, 300]  # bps
for bps in scenarios:
    new_rate = base_wac + (bps / 10000)
    # Annual interest impact = total_upb * delta_rate
    impact = total_upb * Decimal(str(bps / 10000))
```

For a POC, this is a linear approximation — no duration/convexity. The response shape maps each scenario to its impact amount.

---

## Validation Architecture

`workflow.nyquist_validation` is not set in `.planning/config.json` — treat as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none detected — uses pytest defaults with `--cov=.` and `working-directory: backend` |
| Quick run command | `cd backend && python -m pytest tests/test_re_api.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | GET /api/re/kpis returns non-zero UPB/WAC/WAM/LTV/DSCR from seeded data | integration | `pytest tests/test_re_api.py::test_kpis_returns_aggregates -x` | ❌ Wave 0 |
| API-02 | GET /api/re/concentration returns property_type breakdown | integration | `pytest tests/test_re_api.py::test_concentration -x` | ❌ Wave 0 |
| API-03 | GET /api/re/distributions returns LTV histogram buckets | integration | `pytest tests/test_re_api.py::test_distributions -x` | ❌ Wave 0 |
| API-04 | GET /api/re/maturity-profile returns quarterly groups | integration | `pytest tests/test_re_api.py::test_maturity_profile -x` | ❌ Wave 0 |
| API-05 | GET /api/re/loans?property_type=multifamily returns only multifamily loans | integration | `pytest tests/test_re_api.py::test_loans_filter -x` | ❌ Wave 0 |
| API-05 | GET /api/re/loans pagination envelope shape (total/page/page_size/items) | integration | `pytest tests/test_re_api.py::test_loans_pagination -x` | ❌ Wave 0 |
| API-06 | GET /api/re/loans/{id} returns full detail with cashflow summary | integration | `pytest tests/test_re_api.py::test_loan_detail -x` | ❌ Wave 0 |
| API-07 | GET /api/re/cashflow-performance returns 12 monthly period rows | integration | `pytest tests/test_re_api.py::test_cashflow_performance -x` | ❌ Wave 0 |
| API-08 | GET /api/re/origination-pipeline returns origination groups | integration | `pytest tests/test_re_api.py::test_origination_pipeline -x` | ❌ Wave 0 |
| API-09 | GET /api/re/market-context returns stub with hook markers | unit | `pytest tests/test_re_api.py::test_market_context_stub -x` | ❌ Wave 0 |
| API-10 | GET /api/re/sensitivity returns 6 scenario rows | integration | `pytest tests/test_re_api.py::test_sensitivity -x` | ❌ Wave 0 |
| API-11 | sales_team role JWT returns only that team's loans | integration | `pytest tests/test_re_api.py::test_sales_team_scope -x` | ❌ Wave 0 |

### Testing Infrastructure

The existing `conftest.py` already provides:
- `client` fixture — `TestClient(app)` with DB override, rate limiter reset
- `test_db_session` — SQLite in-memory with rollback isolation
- `auth_headers_admin` — Bearer token for admin user
- `auth_headers_sales` — Bearer token for sales_team user with assigned `sales_team_id`
- `sample_admin_user`, `sample_sales_user`, `sample_sales_team` — all needed fixtures

New test file `tests/test_re_api.py` needs to seed RE loan data before each test. A `re_loan_fixtures` fixture should create a handful of RELoan and RELoanCashflow rows covering multiple property types and one sales team — the existing `test_db_session` and rollback pattern handles cleanup automatically.

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_re_api.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_re_api.py` — all 12 test cases above (covers API-01 through API-11)

---

## Environment Availability

Step 2.6: Minimal audit needed — no new external tools required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (seeded re_loans) | All endpoints | ✓ (via Phase 17) | Postgres (RDS QA) | SQLite in-memory for tests |
| pytest | Test execution | ✓ (existing) | existing in requirements-dev.txt | — |

Phase 17 seeded `re_loans` with 1000 loans (T0 + T1 snapshots) and 6000 cashflow records. All Phase 18 endpoints can be verified against this data via Swagger UI.

---

## Security Domain

`security_enforcement` is not set to false in config — include this section.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `get_current_user` — JWT decode, user lookup, active check (existing) |
| V3 Session Management | yes | HttpOnly cookie + Authorization header fallback (existing) |
| V4 Access Control | yes | `require_sales_team_access()` + server-side `sales_team_id` scope injection |
| V5 Input Validation | yes | Pydantic `FilterParams` — type coercion, no raw SQL string injection |
| V6 Cryptography | no | Read-only endpoints — no encryption operations |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Horizontal privilege escalation — sales_team user accessing other team's loans | Elevation of privilege | `build_re_filters()` prepends `sales_team_id == user.sales_team_id` before any client filter; scope cannot be overridden by query params |
| Information disclosure via loan ID enumeration | Information disclosure | `/loans/{id}` returns 404 (not 403) for loans outside user's scope — same treatment as "not found" |
| Filter injection (e.g., `borrower` param with SQL metacharacters) | Tampering | SQLAlchemy parameterized queries; `.ilike()` uses bind params — no raw string interpolation |
| Missing auth on new router | Elevation of privilege | Every endpoint function must include `Depends(require_sales_team_access())` or `Depends(require_role(...))` — no endpoint without auth dependency |
| sales_team_id supplied as query param | Tampering | `build_re_filters()` reads `user.sales_team_id` from JWT (server-side); no client-supplied param accepted |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `FilterParams` must use a function-based Depends (not direct `Depends(FilterParams)`) for query param injection | Architecture Patterns, Pitfall 1 | Swagger UI shows request body instead of query params; easy to fix at implementation time |
| A2 | Pydantic v2 `ConfigDict(from_attributes=True)` correctly serializes Decimal as JSON number via FastAPI | Architecture Patterns, Pitfall 4 | Decimal serializes as string; fix by adding `json_encoders` or custom serializer in re_schemas.py |
| A3 | `func.extract('year', col)` / `func.extract('quarter', col)` work correctly in SQLAlchemy with Postgres for maturity profile grouping | Endpoint Notes API-04 | May need `extract(text('year'), col)` or `func.date_part` variant; test against actual Postgres |
| A4 | CPR computation as `1 - (1 - SMM)^12` is acceptable accuracy for POC | Endpoint Notes API-07 | Stakeholder may require more precise duration-adjusted calculation; flag at review |
| A5 | Portfolio yield = UPB-weighted interest_rate is an acceptable proxy metric for API-01 | Endpoint Notes API-01 | May need NOI/UPB yield computation if stakeholders require true economic yield |

---

## Open Questions

1. **Default as_of_date behavior when no filter supplied**
   - What we know: Seeded data has two snapshots (T0 and T1 with different `as_of_date` values). Without filtering, aggregations will double-count.
   - What's unclear: Should the API default to latest `as_of_date` automatically (requiring a subquery on every call) or should callers always supply `as_of_date`?
   - Recommendation: Default to latest `as_of_date` in `build_re_filters()` when `params.as_of_date` is None. This prevents double-counting silently and matches expected POC behavior. Add a note in the OpenAPI description.

2. **Concentration limit thresholds for API-02**
   - What we know: API-02 must return "concentration limit proximity."
   - What's unclear: What are the specific policy limits (e.g., single-borrower cap, single-state cap, property type cap) that define "proximity"?
   - Recommendation: Use hardcoded POC constants (e.g., state: 25%, property type: 40%, borrower: 10% of total UPB). Flag constants with `# TODO: POLICY-CONFIG — move to DB settings in production`.

3. **Sort fields for /api/re/loans (API-05)**
   - What we know: D-05/D-06 define pagination shape but not sort field list.
   - What's unclear: Which columns should be sortable? Allowing arbitrary column sort risks exposing internal column names.
   - Recommendation: Whitelist allowed sort columns: `["upb", "ltv", "dscr", "interest_rate", "maturity_date", "origination_date", "risk_rating"]`. Reject any `sort_by` value not in the whitelist with 400.

---

## Sources

### Primary (HIGH confidence)
- `backend/auth/security.py` — `require_sales_team_access()`, `require_role()`, `get_current_user` signatures verified
- `backend/auth/validators.py` — `get_user_sales_team_id()` signature and behavior verified
- `backend/auth/audit.py` — `log_data_access()` signature verified
- `backend/api/routes.py` — `filter_by_sales_team()` pattern, `log_data_access` usage at line 481 verified
- `backend/api/main.py` — router registration pattern verified (5 existing routers)
- `backend/db/connection.py` — sync `get_db` pattern verified
- `backend/db/models.py` — `RELoan` (24 cols) and `RELoanCashflow` (9 cols) field names and types verified
- `backend/tests/conftest.py` — `client`, `test_db_session`, `auth_headers_admin`, `auth_headers_sales` fixtures verified
- `.planning/REQUIREMENTS.md` — API-01 through API-11, FILTER-01 through FILTER-04 acceptance criteria
- `.planning/phases/18-core-api-layer/18-CONTEXT.md` — all D-01 through D-10 locked decisions
- `.planning/STATE.md` — "sales_team_id scope injected server-side from JWT in build_filters() — never a user-facing query param"

### Secondary (MEDIUM confidence)
- `backend/tests/test_re_loans.py` — Test infrastructure pattern for RE model verified (SQLite in-memory, Decimal assertions)

### Tertiary (LOW confidence — see Assumptions Log)
- FilterParams function-based Depends pattern — [ASSUMED] based on FastAPI conventions
- Decimal JSON serialization behavior — [ASSUMED] based on Pydantic v2 + FastAPI integration knowledge
- `func.extract` syntax for Postgres — [ASSUMED] standard SQLAlchemy pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed, verified in codebase
- Auth patterns: HIGH — verified directly in security.py, routes.py, validators.py
- SQLAlchemy aggregation: MEDIUM — standard patterns, specific syntax unverified against running DB
- FilterParams injection: MEDIUM — convention-based, confirmed by Pitfall 1 note requiring implementation verification

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable stack)
