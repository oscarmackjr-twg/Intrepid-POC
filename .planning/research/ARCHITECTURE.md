# Architecture: RE Loan Dashboard Integration

**Project:** Intrepid Loan Purchase Platform — v2.0 RE Dashboard POC
**Researched:** 2026-04-08
**Mode:** Architecture for subsequent milestone on existing codebase
**Confidence:** HIGH (grounded in direct codebase analysis + verified library research)

---

## Existing Architecture Summary (Read-Only Context)

The running system is:

- **Frontend:** React 19 + TypeScript, Vite, React Router 6, Axios, Tailwind CSS. No chart library currently installed.
- **Backend:** Python FastAPI (`/api` prefix) with four registered routers: `api/routes.py`, `api/files.py`, `cashflow/routes.py`, `auth/routes.py`.
- **Auth:** Session cookies (HttpOnly), `get_current_user` dependency, role enum `admin | analyst | sales_team`. `User` model has `role` and `sales_team_id`.
- **DB:** SQLAlchemy 2.0 synchronous sessions, Alembic migrations, PostgreSQL on RDS. Existing tables: `users`, `sales_teams`, `pipeline_runs`, `loan_facts`, `loan_exceptions`, `holidays`, `audit_log`.
- **Numeric concern:** Existing `LoanFact` uses Python `Float` / SQL `FLOAT`. The PROJECT.md constraint requires `NUMERIC(18,6)` / `decimal.Decimal` for all monetary values in new work.
- **Infrastructure:** Single ECS Fargate container. FastAPI serves React static files in production via `StaticFiles` mount and SPA fallback catch-all route.
- **Patterns established:** New router modules register at `APIRouter(prefix="/api/...", dependencies=[Depends(get_current_user)])` and are wired into `api/main.py`. New pages are added to `frontend/src/App.tsx` under the existing `<Layout>` `<ProtectedRoute>` wrapper.

---

## Decision 1: Data Model — New ReLoan Table (not LoanFact reuse)

**Decision: Create a new `re_loans` table. Do not reuse `LoanFact`.**

Rationale:
- `LoanFact` is tied to `pipeline_runs` (FK `run_id`) and represents suitability-check outcomes for the consumer loan purchase workflow. Its columns (`fico_borrower`, `dti`, `pti`, `purchase_price_check`, `underwriting_pass`, `comap_pass`) are semantically wrong for RE portfolio loans.
- RE loans are a standing portfolio asset, not a per-run processing artifact. They have no `run_id` relationship.
- RE loans require fields that don't exist anywhere in the current schema: `dscr`, `noi`, `appraised_value`, `msa`, `maturity_date`, `risk_rating`, `delinquency_status`, `rate_type`.
- Adding these fields to `LoanFact` would pollute the consumer loan model with nulls for all existing rows and break existing pipeline analytics.

**Schema for `re_loans`:**

```python
# backend/db/models.py — add to existing file

from sqlalchemy import Numeric, CHAR

class ReLoan(Base):
    __tablename__ = "re_loans"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(String(100), unique=True, index=True, nullable=False)
    borrower_name = Column(String(255), nullable=True)

    # Property characteristics
    property_type = Column(String(50), index=True)          # Multifamily, Office, Retail, Industrial, Hotel, Mixed-Use
    state = Column(CHAR(2), index=True)                     # ISO 3166-2 US state code
    msa = Column(String(100), index=True)                   # Metropolitan Statistical Area name

    # Balances — NUMERIC(18,6) per financial accuracy constraint
    upb = Column(Numeric(18, 6), nullable=False)            # Unpaid principal balance (current)
    original_balance = Column(Numeric(18, 6), nullable=False)

    # Rate
    coupon_rate = Column(Numeric(10, 6), nullable=False)    # Annual coupon rate as decimal (e.g. 0.0625)
    rate_type = Column(String(20), index=True)              # Fixed | Floating | Hybrid

    # Dates
    origination_date = Column(Date, nullable=False, index=True)
    maturity_date = Column(Date, nullable=False, index=True)

    # Credit metrics — NUMERIC for precision
    ltv = Column(Numeric(8, 4))                             # Loan-to-value ratio as decimal (e.g. 0.65)
    dscr = Column(Numeric(8, 4))                            # Debt service coverage ratio
    noi = Column(Numeric(18, 6))                            # Net Operating Income (annualized)
    appraised_value = Column(Numeric(18, 6))

    # Risk
    risk_rating = Column(String(10), index=True)            # 1-Pass, 2-Watch, 3-Substandard, 4-Doubtful, 5-Loss
    delinquency_status = Column(String(20), index=True)     # Current, 30-59, 60-89, 90+, Foreclosure

    # Cashflow / performance (nullable — populated post-origination or via separate process)
    noi_actual_ytd = Column(Numeric(18, 6), nullable=True)
    noi_projected_annual = Column(Numeric(18, 6), nullable=True)
    last_payment_date = Column(Date, nullable=True)
    next_payment_date = Column(Date, nullable=True)

    # Advisor scope stub — links to sales_team for role-based filtering
    sales_team_id = Column(Integer, ForeignKey("sales_teams.id"), nullable=True, index=True)

    # Audit
    as_of_date = Column(Date, nullable=False, index=True)   # Reporting as-of date for this snapshot
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales_team = relationship("SalesTeam")
```

**Alembic migration:** Generate via `alembic revision --autogenerate -m "add_re_loans_table"` after adding `ReLoan` to `models.py`. The migration must use `sa.Numeric(18, 6)` explicitly — do not let autogenerate emit `Float`.

**Index strategy for 2000 loans at POC scale:**

The following composite indexes cover all dashboard filter combinations without over-indexing:

```sql
-- Covers: property_type + state queries (concentration panels)
CREATE INDEX ix_re_loans_property_type_state ON re_loans (property_type, state);

-- Covers: risk/delinquency watchlist queries
CREATE INDEX ix_re_loans_risk_delinquency ON re_loans (risk_rating, delinquency_status);

-- Covers: as_of_date slicing (time-series panels)
CREATE INDEX ix_re_loans_as_of_date ON re_loans (as_of_date);

-- Single-column indexes declared inline on the model cover: loan_id, msa, rate_type, origination_date, maturity_date, sales_team_id
```

At 2,000 rows, PostgreSQL sequential scans cost microseconds. These indexes exist for correctness as the dataset grows, not for current performance urgency.

---

## Decision 2: Seeding — Alembic Migration + Seed Script

**Decision: Alembic migration creates the table; a dedicated Python seed script populates sample data. Do not embed seed logic inside Alembic migrations.**

Rationale: Alembic migrations run on every deploy (including production). Seed data belongs only in dev/staging. Mixing the two requires environment-conditional logic inside migrations, which is fragile and violates Alembic's single-purpose contract.

**Pattern:**

```
backend/
  scripts/
    seed_re_loans.py       ← new file; run manually once in dev/staging
```

`seed_re_loans.py` should:
1. Connect via `SessionLocal()` from `backend/db/connection.py` (same pattern as existing scripts).
2. Generate 500-2000 synthetic loans using `faker` or a deterministic seed with `random.seed(42)`.
3. Be idempotent: `INSERT ... ON CONFLICT (loan_id) DO NOTHING` or check-then-insert.
4. Use `decimal.Decimal` for all numeric values — never Python `float` for financial fields.
5. Accept a `--count` CLI arg (default 500, max 2000 for the POC).

`faker` is not in `requirements.txt`. Add it as a dev dependency only, or use pure `random` to avoid a new production dependency.

---

## Decision 3: API Design — New Router Module

**Decision: Create `backend/api/re_dashboard.py` as a new `APIRouter` with prefix `/api/re`.**

Register it in `backend/api/main.py` alongside the existing routers:

```python
from api.re_dashboard import router as re_dashboard_router
app.include_router(re_dashboard_router)
```

**Endpoint inventory:**

| Endpoint | Method | Purpose | Returns |
|----------|--------|---------|---------|
| `/api/re/loans` | GET | Paginated loan list with filter params | `{items: ReLoanRow[], total: int, page: int}` |
| `/api/re/loans/{loan_id}` | GET | Single loan detail card | `ReLoanDetail` |
| `/api/re/kpis` | GET | Executive KPI cards | `ReDashboardKPIs` |
| `/api/re/concentration` | GET | Property type + state concentration | `ReConcentration` |
| `/api/re/distributions` | GET | LTV / DSCR / loan-size histograms | `ReDistributions` |
| `/api/re/cashflow-performance` | GET | P&I, NOI actual vs projected | `ReCashflowPerformance` |
| `/api/re/origination-pipeline` | GET | Monthly origination + vintage | `ReOriginationPipeline` |
| `/api/re/market-context` | GET | Static market stub values | `ReMarketContext` |
| `/api/re/export/csv` | GET | CSV of filtered loan list | StreamingResponse |

All GET endpoints except `/export/csv` accept a shared **filter parameter set** as query params (see Decision 5).

The `/api/re/market-context` endpoint returns hardcoded static data from a Python dict. Add a comment `# TODO: wire to live feed` on each value. This keeps the stub explicit and replaceable.

---

## Decision 4: Aggregation Strategy — SQL for KPIs, Python for Histograms

**Decision: Compute KPI aggregations in SQL via SQLAlchemy expressions. Compute histogram bin assignments in Python (pandas). Never send raw loan rows to the frontend for aggregation.**

**Rationale for SQL KPIs:**

Weighted average formulas translate directly to SQL with no data transfer:

```python
# WAC: SUM(coupon_rate * upb) / SUM(upb)
from sqlalchemy import func

wac = db.query(
    (func.sum(ReLoan.coupon_rate * ReLoan.upb) / func.sum(ReLoan.upb))
    .label("wac")
).filter(*active_filters).scalar()

# WAM: SUM(months_to_maturity * upb) / SUM(upb)
# months_to_maturity derived via PostgreSQL date arithmetic:
# EXTRACT(EPOCH FROM (maturity_date - CURRENT_DATE)) / (30.4375 * 86400)
from sqlalchemy import text, extract
months_remaining = extract("epoch", ReLoan.maturity_date - func.current_date()) / (30.4375 * 86400)
wam = db.query(
    (func.sum(months_remaining * ReLoan.upb) / func.sum(ReLoan.upb)).label("wam")
).filter(*active_filters).scalar()
```

This avoids transferring 2,000 rows to Python just to reduce them to 4 numbers.

**Rationale for Python histogram binning:**

Histogram bin boundaries are application logic (e.g., LTV buckets: <50%, 50-60%, 60-70%, 70-75%, 75-80%, >80%). These are not natural SQL GROUP BY keys — computing them cleanly in SQL requires CASE expressions that must be maintained in two places. Pandas `cut()` is cleaner:

```python
# In re_dashboard.py endpoint handler
rows = db.query(ReLoan.ltv).filter(*active_filters).all()
ltv_series = pd.Series([float(r.ltv) for r in rows if r.ltv is not None])
bins = [0, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 1.0]
labels = ["<50", "50-60", "60-65", "65-70", "70-75", "75-80", ">80"]
counts = pd.cut(ltv_series, bins=bins, labels=labels).value_counts(sort=False)
```

At 2,000 rows, fetching a single `ltv` column is ~16KB of data. This is acceptable. Do not fetch full loan objects for histogram computation.

**Concentration panel (property type + state):**

Compute in SQL with GROUP BY — this is a natural aggregation:

```python
rows = db.query(
    ReLoan.property_type,
    ReLoan.state,
    func.count().label("loan_count"),
    func.sum(ReLoan.upb).label("total_upb"),
).filter(*active_filters).group_by(ReLoan.property_type, ReLoan.state).all()
```

**Summary: aggregation by layer:**

| Panel | Layer | Reason |
|-------|-------|--------|
| KPI cards (WAC, WAM, WA LTV, WA DSCR, total UPB, loan count) | SQL (SQLAlchemy expressions) | Pure reduction — no row data needed |
| Concentration by property type, state | SQL GROUP BY | Natural DB aggregation |
| Maturity profile (by year) | SQL GROUP BY on EXTRACT(YEAR, maturity_date) | Natural DB aggregation |
| Delinquency buckets | SQL GROUP BY delinquency_status | Natural DB aggregation |
| LTV histogram | Python pandas.cut() | Bin logic is application logic |
| DSCR histogram | Python pandas.cut() | Same |
| Loan size histogram | Python pandas.cut() | Same |
| P&I / NOI cashflow trends | Python (time-series reshape) | Multi-series aggregation is clearer in pandas |
| Paginated loan table | SQL with OFFSET/LIMIT | Standard DB pagination |

---

## Decision 5: Filtering — Server-Side with URL Query Params

**Decision: Server-side filtering via URL query params. Use React Router's `useSearchParams` as the filter state store. Do not implement client-side in-memory filtering.**

**Rationale:**

- At 2,000 loans, client-side filtering of the raw loan list is feasible on its own. However, all KPI panels and chart endpoints also need filtering applied. This means the server must re-filter for every aggregation endpoint regardless. Duplicating the filter logic in both the browser and the server creates a maintenance problem. Put filtering authority in one place: the server.
- URL query params make filter state shareable, bookmarkable, and persistent across page refreshes — consistent with the existing pattern (`/program-runs?type=sg`).

**Shared filter parameter set (applied to all `/api/re/*` endpoints):**

```
as_of_date       string  YYYY-MM-DD    (default: most recent as_of_date in table)
property_type    string  comma-separated, e.g. "Multifamily,Office"
state            string  comma-separated, e.g. "TX,FL,CA"
msa              string  comma-separated
rate_type        string  comma-separated: "Fixed,Floating,Hybrid"
risk_rating      string  comma-separated: "1-Pass,2-Watch,3-Substandard"
delinquency      string  comma-separated: "Current,30-59,60-89,90+"
upb_min          float   minimum UPB filter
upb_max          float   maximum UPB filter
origination_year integer vintage year filter
sales_team_id    integer auto-injected from session for sales_team role (not a user-facing param)
```

**FastAPI filter dependency:**

```python
# backend/api/re_dashboard.py
from fastapi import Depends, Query
from typing import Optional

class ReLoanFilters:
    def __init__(
        self,
        as_of_date: Optional[str] = Query(None),
        property_type: Optional[str] = Query(None),   # "Multifamily,Office"
        state: Optional[str] = Query(None),
        msa: Optional[str] = Query(None),
        rate_type: Optional[str] = Query(None),
        risk_rating: Optional[str] = Query(None),
        delinquency: Optional[str] = Query(None),
        upb_min: Optional[float] = Query(None),
        upb_max: Optional[float] = Query(None),
        origination_year: Optional[int] = Query(None),
    ):
        self.as_of_date = as_of_date
        self.property_type = [x.strip() for x in property_type.split(",")] if property_type else None
        # ... parse all comma-separated values

def build_filters(filters: ReLoanFilters, current_user: User) -> list:
    """Translate ReLoanFilters to SQLAlchemy filter expressions.
    Enforces sales_team_id scope for sales_team role."""
    clauses = []
    if filters.as_of_date:
        clauses.append(ReLoan.as_of_date == filters.as_of_date)
    if filters.property_type:
        clauses.append(ReLoan.property_type.in_(filters.property_type))
    if current_user.role == UserRole.SALES_TEAM and current_user.sales_team_id:
        clauses.append(ReLoan.sales_team_id == current_user.sales_team_id)
    # ... remaining filters
    return clauses
```

**React filter hook pattern:**

```tsx
// frontend/src/hooks/useReLoanFilters.ts
import { useSearchParams } from 'react-router-dom'

export function useReLoanFilters() {
  const [searchParams, setSearchParams] = useSearchParams()

  const filters = {
    as_of_date: searchParams.get('as_of_date') ?? undefined,
    property_type: searchParams.get('property_type') ?? undefined,
    // ...
  }

  const setFilter = (key: string, value: string | undefined) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      if (value) next.set(key, value)
      else next.delete(key)
      return next
    })
  }

  return { filters, setFilter }
}
```

Each dashboard panel passes `filters` as query params to its API call. The filter sidebar calls `setFilter`. All panels re-fetch when `searchParams` changes. This is the same `?type=sg` pattern already used in the existing Layout nav links.

**Debounce:** Apply 300ms debounce on free-text inputs (borrower name search, loan ID). No debounce needed on checkbox/select filters.

---

## Decision 6: Chart Data Flow — Recharts v3 with Typed Response Shapes

**Decision: Use Recharts v3 (currently at v3.8.x) as the chart library. Structure API responses to be directly consumable by Recharts data props with minimal frontend transformation.**

**Why Recharts:**

- Recharts v3 has full React 19 support (the react-is override workaround in v2.x is no longer needed in v3). Confirmed stable at v3.8.1 as of April 2026.
- Recharts is the lowest-bundle-size option among mature React chart libraries (uses D3 submodules, not full D3). For a single-container production image where React is already ~130KB, bundle growth matters.
- Nivo produces more visually polished defaults but its canvas/SVG dual-mode and larger bundle are unnecessary for this POC.
- No charting library is currently installed in `frontend/package.json`. Recharts is a clean addition with `npm install recharts`.

**API response shape convention:**

Design responses so Recharts `data` props receive arrays of objects directly:

```typescript
// KPI response
interface ReDashboardKPIs {
  total_upb: string        // Decimal as string to avoid float precision loss
  loan_count: number
  wac: string              // "0.062500" — format in frontend
  wam_months: number
  wa_ltv: string
  wa_dscr: string
  delinquency_90plus_count: number
  delinquency_90plus_upb: string
}

// Concentration response — ready for Recharts PieChart
interface ReConcentration {
  by_property_type: Array<{ name: string; upb: number; loan_count: number }>
  by_state: Array<{ state: string; upb: number; loan_count: number }>
}

// Histogram response — ready for Recharts BarChart
interface ReDistributions {
  ltv: Array<{ bucket: string; count: number }>
  dscr: Array<{ bucket: string; count: number }>
  loan_size: Array<{ bucket: string; count: number }>
}
```

**Decimal serialization:** FastAPI's `jsonable_encoder` does not handle `decimal.Decimal` by default — it raises `TypeError`. Add a custom encoder or override `model_config` on Pydantic response models:

```python
# In Pydantic response models
from pydantic import BaseModel, field_serializer
from decimal import Decimal

class ReDashboardKPIs(BaseModel):
    total_upb: Decimal
    wac: Decimal

    model_config = {"json_encoders": {Decimal: str}}
    # Or use field_serializer for Pydantic v2
```

The frontend receives Decimals as strings (`"0.062500"`). Format for display in a `formatPercent()` utility function — do not parse back to JS `number` for monetary values.

---

## Decision 7: PDF Export — Client-Side with @react-pdf/renderer

**Decision: Use `@react-pdf/renderer` (client-side) for dashboard snapshots, not server-side WeasyPrint/ReportLab.**

**Rationale:**

- The dashboard is chart-heavy. Server-side PDF generation would require either (a) running a headless browser (Playwright/Puppeteer) in the single ECS container — a 300MB+ addition to a container already running FastAPI, or (b) using WeasyPrint/ReportLab to re-draw charts as non-interactive SVG — significant duplicated rendering logic.
- `@react-pdf/renderer` generates PDFs entirely in the browser using React components. No server-side process, no container size impact, no subprocess. Charts can be exported as SVG/canvas data URLs and embedded.
- For CSV export of filtered tables, use the existing FastAPI `StreamingResponse` pattern — this is pure data, no rendering complexity.

**Pattern:**

```tsx
// ExportPDFButton.tsx
import { pdf } from '@react-pdf/renderer'
import { DashboardPDFDocument } from './DashboardPDFDocument'

async function exportPDF(kpis, concentration, distributions) {
  const blob = await pdf(
    <DashboardPDFDocument kpis={kpis} concentration={concentration} distributions={distributions} />
  ).toBlob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `re-portfolio-${new Date().toISOString().slice(0,10)}.pdf`
  a.click()
}
```

`DashboardPDFDocument` is a separate component tree using `@react-pdf/renderer` primitives (`<Document>`, `<Page>`, `<View>`, `<Text>`, `<Image>`). Charts are captured as base64 PNG via `<canvas>.toDataURL()` from the rendered Recharts SVG.

**CSV export** stays server-side (`GET /api/re/export/csv?<filter params>`). FastAPI `StreamingResponse` with `text/csv` content type. This is consistent with the existing Excel download pattern in `routes.py`.

---

## Decision 8: Role-Based Filtering Stub

**Decision: Use the existing `User.role` and `User.sales_team_id` fields. Add `sales_team_id` FK to `re_loans` for advisor scope. No schema changes to `users` or `sales_teams` tables.**

**Current role enum:** `admin | analyst | sales_team`

**Mapping to RE dashboard scope:**

| Role | RE Dashboard Access | Implementation |
|------|--------------------|--------------------|
| `admin` | Full portfolio — all loans | No `sales_team_id` filter applied |
| `analyst` | Full portfolio — all loans | No `sales_team_id` filter applied (analyst = internal PM equivalent) |
| `sales_team` | Scoped to their `sales_team_id` | `WHERE re_loans.sales_team_id = current_user.sales_team_id` |

The PROJECT.md calls for "PM vs advisor" scoping. Map PM → `admin`/`analyst` (full view), advisor → `sales_team` (scoped view). This reuses existing infrastructure without touching the auth module.

**Enforcement in `build_filters()`:**

```python
if current_user.role == UserRole.SALES_TEAM:
    if current_user.sales_team_id is None:
        raise HTTPException(status_code=403, detail="No sales team assigned")
    clauses.append(ReLoan.sales_team_id == current_user.sales_team_id)
```

The seed script should assign `sales_team_id` to a subset of loans to enable testing the advisor scope in dev.

---

## Decision 9: Routing

**Backend routing — no conflicts with existing prefixes:**

The new router uses prefix `/api/re`. Existing prefixes are `/api`, `/api/files`, `/api/cashflow`, `/auth`. There is no collision.

```python
# backend/api/re_dashboard.py
router = APIRouter(
    prefix="/api/re",
    tags=["re-dashboard"],
    dependencies=[Depends(get_current_user)],
)
```

**Frontend routing — add a nav section and sub-routes:**

```tsx
// App.tsx additions inside existing <Layout> <ProtectedRoute>
<Route path="re-dashboard" element={<ReDashboard />} />
<Route path="re-dashboard/portfolio" element={<REPortfolioComposition />} />
<Route path="re-dashboard/credit" element={<RECreditQuality />} />
<Route path="re-dashboard/cashflow" element={<RECashflowPerformance />} />
<Route path="re-dashboard/origination" element={<REOriginationPipeline />} />
<Route path="re-dashboard/market" element={<REMarketContext />} />
<Route path="re-dashboard/loans/:loanId" element={<RELoanDetail />} />
```

**Layout nav additions** (in `Layout.tsx`, below existing nav items):

```tsx
<span className="px-5 pt-4 pb-1 text-xs font-bold tracking-widest text-[#94a3b8] uppercase select-none block">
  RE Portfolio
</span>
<Link to="/re-dashboard">Executive Summary</Link>
<Link to="/re-dashboard/portfolio">Composition</Link>
<Link to="/re-dashboard/credit">Credit & Risk</Link>
<Link to="/re-dashboard/cashflow">Cash Flow</Link>
<Link to="/re-dashboard/origination">Origination</Link>
<Link to="/re-dashboard/market">Market Context</Link>
```

The `<Layout>` sidebar already handles active-link styling via `location.pathname.startsWith(...)`. The new group follows the existing SG/CIBC section pattern exactly.

**Global filter sidebar:** Implemented as a shared component rendered inside each RE dashboard page (not in `<Layout>`). RE pages use a two-column layout: narrow filter sidebar on the left, chart grid on the right. The filter sidebar is not visible on non-RE pages.

---

## Decision 10: Performance — Appropriate for 2000-Loan POC Scale

**At 2,000 rows, no caching layer is needed. Standard indexing + SQL aggregation is sufficient.**

Concrete performance profile:
- Full-table KPI aggregation (WAC, WAM, WA LTV, WA DSCR): ~5ms on indexed Postgres at 2,000 rows.
- Filtered loan list with pagination (50 rows): ~2ms with index on `as_of_date` + filter columns.
- Histogram bin fetch (single column, 2,000 values): ~1ms fetch + ~1ms pandas cut = negligible.

**What to avoid at this scale:**
- Do not add Redis or in-memory caching. It adds operational complexity with no measurable benefit at 2,000 rows. Revisit at 50,000+ rows.
- Do not use background precomputation jobs for aggregations. The query is fast enough to run on demand.
- Do not send all 2,000 loan rows to the frontend for client-side aggregation. Even though this is technically feasible (~200KB JSON), it sets a pattern that breaks as the dataset grows.

**What to add proactively:**
- The composite indexes listed in Decision 1 are cheap to create and prevent sequential scans if the dataset grows 10x.
- Add `as_of_date` to the index. The dashboard will be queried "as of a specific date" constantly. Without this index, every KPI query scans the full table.

---

## Component Boundary Map

### New Components (to build)

| Component | Location | Type | Depends On |
|-----------|----------|------|------------|
| `ReLoan` SQLAlchemy model | `backend/db/models.py` | Modified file | Nothing |
| Alembic migration | `backend/migrations/versions/` | New file | `ReLoan` model |
| `seed_re_loans.py` | `backend/scripts/` | New file | `ReLoan` model + `SessionLocal` |
| `re_dashboard.py` router | `backend/api/` | New file | `ReLoan` model + `ReLoanFilters` |
| Registration in `main.py` | `backend/api/main.py` | Modified file | `re_dashboard.py` |
| `useReLoanFilters` hook | `frontend/src/hooks/` | New file | React Router `useSearchParams` |
| `ReDashboardKPIs` types | `frontend/src/types/` | New file | Nothing |
| `REFilterSidebar` component | `frontend/src/components/` | New file | `useReLoanFilters` |
| `ReDashboard` page | `frontend/src/pages/` | New file | All RE API endpoints + Recharts |
| Sub-pages (Portfolio, Credit, Cashflow, Origination, Market) | `frontend/src/pages/` | New files | Filter hook + Recharts |
| `RELoanDetail` page | `frontend/src/pages/` | New file | `/api/re/loans/:id` |
| `DashboardPDFDocument` | `frontend/src/components/` | New file | `@react-pdf/renderer` |
| Route additions | `frontend/src/App.tsx` | Modified file | New pages |
| Nav additions | `frontend/src/components/Layout.tsx` | Modified file | New routes |

### Modified Existing Files (minimal surface area)

| File | Change | Risk |
|------|--------|------|
| `backend/db/models.py` | Add `ReLoan` class | Low — additive only |
| `backend/api/main.py` | Import and register `re_dashboard_router` | Low — one `include_router` call |
| `frontend/src/App.tsx` | Add 6 RE routes under existing `<ProtectedRoute>/<Layout>` | Low — additive only |
| `frontend/src/components/Layout.tsx` | Add RE Portfolio nav section | Low — follows existing pattern |

---

## Data Flow: DB to Chart Component

```
PostgreSQL re_loans table
  |
  | SQLAlchemy query (with filter clauses from ReLoanFilters)
  v
FastAPI endpoint handler (backend/api/re_dashboard.py)
  |
  | Pydantic response model (Decimal serialized as str)
  v
JSON response { by_property_type: [{name: "Multifamily", upb: 450000000, loan_count: 142}, ...] }
  |
  | Axios GET /api/re/concentration?as_of_date=2026-04-01&property_type=Multifamily
  v
React page component (useSWR or useEffect + useState, not new state library)
  |
  | Map: [{name, upb, loan_count}] — already in Recharts data format
  v
<PieChart data={concentration.by_property_type}>
  <Pie dataKey="upb" nameKey="name" />
</PieChart>
```

No intermediate transformation layer is needed. The API response shape is designed to match Recharts `data` prop expectations directly.

---

## Suggested Build Order

Dependencies flow in this sequence. Each step is unblocked by the previous.

### Step 1: Data Foundation (backend)
1. Add `ReLoan` model to `backend/db/models.py`
2. Generate and run Alembic migration
3. Write and run `seed_re_loans.py` (verify data in psql)
4. Verify table exists with correct types (check `coupon_rate` is NUMERIC, not FLOAT)

**Gate:** `SELECT COUNT(*), SUM(upb) FROM re_loans` returns data.

### Step 2: Core API (backend)
1. Create `backend/api/re_dashboard.py` with `ReLoanFilters` dependency and `build_filters()` helper
2. Implement `/api/re/kpis` — KPI aggregation in SQL
3. Implement `/api/re/concentration` — GROUP BY property_type + state
4. Implement `/api/re/distributions` — column fetch + pandas cut for LTV/DSCR/size
5. Implement `/api/re/loans` — paginated list with filter support
6. Implement `/api/re/loans/{loan_id}` — single loan detail
7. Register router in `main.py`
8. Smoke test all endpoints via `/docs` (FastAPI's Swagger UI)

**Gate:** All endpoints return correct data with and without filter params.

### Step 3: Filter Hook and Types (frontend)
1. Install `recharts`: `npm install recharts`
2. Create TypeScript response types in `frontend/src/types/re-dashboard.ts`
3. Create `useReLoanFilters` hook
4. Create `REFilterSidebar` component (renders filter controls, calls `setFilter`)

**Gate:** Filter sidebar updates URL params; hook reads them correctly.

### Step 4: Dashboard Pages (frontend)
1. Add routes to `App.tsx`
2. Add nav section to `Layout.tsx`
3. Build `ReDashboard` (Executive Summary) page — KPI cards first, no charts yet
4. Add Recharts charts to Executive Summary (pie for property type, bar for delinquency)
5. Build remaining sub-pages in order: Portfolio Composition, Credit Quality, Cashflow, Origination, Market Context (static stub)
6. Build `RELoanDetail` modal/page

**Gate:** All pages render with seeded data; filter changes trigger re-fetch; charts display correctly.

### Step 5: Export
1. Implement `GET /api/re/export/csv` endpoint (server-side StreamingResponse)
2. Install `@react-pdf/renderer`: `npm install @react-pdf/renderer`
3. Build `DashboardPDFDocument` component
4. Wire `ExportPDFButton` into Executive Summary page

**Gate:** CSV download contains filtered data; PDF download captures KPI cards and charts.

### Step 6: Role Scope Validation
1. Create a `sales_team`-role test user in seed script
2. Assign a subset of loans to that user's `sales_team_id`
3. Verify dashboard shows only scoped loans when logged in as that user
4. Verify `admin`/`analyst` see full portfolio

**Gate:** Role scoping enforced at API level, not just UI level.

---

## Pitfalls to Avoid

**Float vs Decimal:** The existing `LoanFact` model uses Python `Float`. `ReLoan` must use `sqlalchemy.Numeric` and `decimal.Decimal` throughout. When writing the seed script, do not pass Python float literals — wrap them: `Decimal("0.0625")` not `0.0625`.

**Recharts and Decimal strings:** Recharts `dataKey` expects a JavaScript number. Convert Decimal strings to `parseFloat()` in the chart data mapping layer — this is the one place where string-to-float conversion is acceptable because it is for display only, not computation.

**FastAPI Decimal serialization:** FastAPI's default JSON encoder raises `TypeError` on `decimal.Decimal`. Apply a Pydantic v2 `field_serializer` or `model_config = {"json_encoders": {Decimal: str}}` on every response model that contains Decimal fields.

**SPA fallback route ordering:** `api/main.py` registers the SPA catch-all `/{full_path:path}` at the bottom, which catches any unregistered path. New API routes registered via `include_router` before that catch-all are fine. Confirm `re_dashboard_router` is registered before the `@app.get("/{full_path:path}")` fallback.

**Filter injection for sales_team role:** The `sales_team_id` scope filter must be applied in `build_filters()` server-side. Do not rely on the frontend omitting the param — a determined user could call the API directly.

---

## Sources

- Direct codebase analysis: `backend/db/models.py`, `backend/api/main.py`, `backend/api/routes.py`, `backend/cashflow/routes.py`, `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`, `frontend/src/contexts/AuthContext.tsx`, `frontend/package.json`, `backend/requirements.txt`, `.planning/PROJECT.md`
- Recharts v3 React 19 status: [GitHub recharts releases](https://github.com/recharts/recharts/releases) — v3.8.1 confirmed stable, React 19 support resolved in v3
- React filter/URL state patterns: [LogRocket — useSearchParams](https://blog.logrocket.com/url-state-usesearchparams/)
- Client vs server-side filtering thresholds: [DEV Community](https://dev.to/marmariadev/deciding-between-client-side-and-server-side-filtering-22l9)
- PDF export tradeoffs: [@react-pdf/renderer approach](https://pdfnoodle.com/blog/how-to-generate-pdfs-from-react-components-using-react-to-pdf), [WeasyPrint vs ReportLab](https://dev.to/claudeprime/generate-pdfs-in-python-weasyprint-vs-reportlab-ifi)
- SQLAlchemy weighted average in PostgreSQL: [SQLAlchemy 2.1 docs](https://docs.sqlalchemy.org/en/21/core/functions.html)
