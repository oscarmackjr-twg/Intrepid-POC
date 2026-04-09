# Phase 22: Credit Quality Page — Research

**Researched:** 2026-04-09
**Domain:** Recharts color-banded histograms, risk data visualization, FastAPI new endpoints, delinquency/migration data modeling
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CREDIT-01 | LTV histogram with green/yellow/red color bands (<65%, 65–75%, >75%) | `/api/re/distributions` already returns `ltv_histogram` with `color` field per bucket — no new endpoint needed |
| CREDIT-02 | DSCR histogram with color bands (>1.4x, 1.0–1.4x, <1.0x) | `/api/re/distributions` already returns `dscr_histogram` with `color` field per bucket — no new endpoint needed |
| CREDIT-03 | Watchlist/criticized loans table filterable by risk rating, with trend arrows | `/api/re/loans` already supports `risk_rating` filter and returns `risk_rating` + `prior_risk_rating`; no new endpoint needed; trend arrow computed from these two fields client-side |
| CREDIT-04 | Delinquency waterfall (current → 30 → 60 → 90 → default) | `/api/re/kpis` returns `delinquent_30_upb`, `delinquent_60_upb`, `delinquent_90_upb`; a new `/api/re/delinquency-waterfall` endpoint is needed for proper bucket counts and waterfall shape |
| CREDIT-05 | Risk rating migration matrix (current vs prior period, two snapshots) | No existing endpoint; new `/api/re/risk-rating-migration` endpoint required; `RELoan` has `risk_rating` + `prior_risk_rating` — both snapshots at MAX(as_of_date) sufficient |
| CREDIT-06 | Interest rate sensitivity table (+/−100/200/300 bps portfolio impact) | `/api/re/sensitivity` already returns all 6 scenarios — no new endpoint needed |
| UX-01 | Clicking chart segment applies filter across entire dashboard | `useReLoanFilters().setFilter()` pattern already established; LTV/DSCR bar click → `setFilter('risk_rating', ...)` or no-op (buckets don't map cleanly to filter keys — see notes) |
</phase_requirements>

---

## Summary

Phase 22 replaces the `/re-dashboard/credit` stub with a fully implemented Credit Quality page. The backend data situation is partially built: two of six panels can be served entirely by existing endpoints (`/api/re/distributions` for LTV/DSCR histograms; `/api/re/sensitivity` for the rate sensitivity table), one panel can use an existing endpoint with a new query parameter combination (`/api/re/loans` with `risk_rating=4` or `risk_rating=5` for the watchlist), and two panels require new backend endpoints (delinquency waterfall and risk rating migration matrix).

The frontend pattern is identical to Phase 21: `ReDashboard.tsx` already has the "Credit Quality" tab wired to `/re-dashboard/credit`. The only change to `App.tsx` is replacing `<ReStubPage />` with `<ReCreditQualityPage />` at that route. All chart primitives (Recharts `BarChart`, `Bar`, `Cell`, `ResponsiveContainer`) and wrappers (`ChartCard`, `useReLoanFilters`) are installed and tested. The key new technical challenge is color-banded bars in Recharts — the `color` field returned by the backend per bucket must be passed through a `<Cell>` array inside a single `<Bar>`, not via separate `<Bar>` components per color.

The risk rating migration matrix is the most complex new element: it must pivot from individual `(risk_rating, prior_risk_rating)` loan records into a 5x5 matrix grid showing loan counts at each migration cell. The backend already stores both fields on every `RELoan` row, so the new endpoint just needs a GROUP BY on the pair.

**Primary recommendation:** Split into three plans — Plan 01: new backend endpoints (delinquency waterfall + migration matrix); Plan 02: frontend page with all six panels; Plan 03: verification.

---

## Standard Stack

### Core (all already installed — no new packages)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | 3.8.1 | Color-banded histograms, waterfall chart, sensitivity table chart | D-01 locked from Phase 21 |
| @tanstack/react-query | 5.96.2 | Data fetching with filter-keyed queries | Established pattern |
| react-router-dom | 6.30.3 | Route wiring; replace stub at `/re-dashboard/credit` | Already installed |
| axios | 1.7.7 | HTTP client inside queryFn | Already installed |
| tailwindcss | 4.1.18 | All styling | Already installed |

[VERIFIED: package.json in frontend — all packages present from Phase 21]

**No new npm installs required.** Recharts already ships `BarChart`, `Bar`, `Cell`, `Tooltip`, `ResponsiveContainer`, `XAxis`, `YAxis`, `CartesianGrid` — all needed for this phase.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Recharts BarChart | Custom SVG | Would bypass existing pattern; D-01 forbids other chart libraries |
| HTML table for sensitivity | Recharts table | HTML table is cleaner for a multi-column financial table; no chart needed |
| HTML table for migration matrix | Recharts | Matrix is inherently grid-shaped; HTML table with color cells is the right tool |
| HTML table for watchlist | Recharts | Same — tabular data belongs in a table |

---

## Endpoint Availability Analysis

### Existing Endpoints (no new backend work needed)

| Panel | Endpoint | Key Fields Used | Status |
|-------|----------|-----------------|--------|
| CREDIT-01 LTV histogram | `GET /api/re/distributions` | `ltv_histogram[].{bucket, loan_count, total_upb, color}` | READY — color field already set per CREDIT-01 bands |
| CREDIT-02 DSCR histogram | `GET /api/re/distributions` | `dscr_histogram[].{bucket, loan_count, total_upb, color}` | READY — color field already set per CREDIT-02 bands |
| CREDIT-03 Watchlist table | `GET /api/re/loans` | `items[].{loan_number, borrower_name, upb, risk_rating, prior_risk_rating, ltv, dscr, days_past_due}` | READY — query with `risk_rating=4` or `risk_rating=5`; trend arrow derived from `risk_rating` vs `prior_risk_rating` |
| CREDIT-06 Rate sensitivity | `GET /api/re/sensitivity` | `{base_wac, total_upb, scenarios[].{bps_change, new_wac, annual_interest_impact, impact_pct}}` | READY — all 6 scenarios (-300 to +300 bps) |

[VERIFIED: read re_routes.py lines 350–441 for distributions; lines 869–920 for sensitivity]

### New Endpoints Required

| Panel | New Endpoint | Data Needed | Model Fields |
|-------|-------------|-------------|--------------|
| CREDIT-04 Delinquency waterfall | `GET /api/re/delinquency-waterfall` | Loan count + UPB in each delinquency bucket: current (DPD=0), 30 (DPD 1–59), 60 (DPD 60–89), 90 (DPD 90–179), default (DPD 180+) | `RELoan.days_past_due` (Integer, default=0) |
| CREDIT-05 Migration matrix | `GET /api/re/risk-rating-migration` | Count and UPB of loans crossing each (prior_risk_rating, current risk_rating) pair | `RELoan.risk_rating` (String), `RELoan.prior_risk_rating` (String) |

[VERIFIED: read db/models.py — `days_past_due = Column(Integer, default=0)`, `risk_rating = Column(String(10))`, `prior_risk_rating = Column(String(10))`]

---

## Architecture Patterns

### Recommended Project Structure (after Phase 22)

```
frontend/src/
├── pages/
│   ├── ReDashboard.tsx              # Unchanged — already has Credit Quality tab
│   ├── ReExecutiveSummaryPage.tsx   # Unchanged
│   ├── RePortfolioPage.tsx          # Unchanged
│   └── ReCreditQualityPage.tsx      # NEW — six-panel credit quality page
├── components/re/
│   ├── ChartCard.tsx                # Unchanged
│   ├── ReDashboardFilterSidebar.tsx # Unchanged
│   ├── WatchlistTable.tsx           # NEW — criticized loans table component
│   ├── MigrationMatrix.tsx          # NEW — 5×5 rating migration grid
│   └── SensitivityTable.tsx         # NEW — rate sensitivity table
└── hooks/ (unchanged)
```

```
backend/api/
├── re_routes.py     # Add two new route functions at bottom
└── re_schemas.py    # Add two new response models
```

### Pattern 1: Color-Banded Recharts Bar (CREDIT-01, CREDIT-02)

**What:** Single `<Bar>` where each bar has a different fill color, driven by the `color` field from the backend response.
**When to use:** Any histogram where each bucket is pre-colored server-side.

The key insight: do NOT create separate `<Bar>` components per color (that creates a grouped/multi-series chart). Instead, use a single `<Bar>` with a `<Cell>` array:

```tsx
// Source: Recharts docs — recharts.org/api/Bar, recharts.org/api/Cell
// [ASSUMED — pattern verified against recharts source code principles]
const COLOR_MAP: Record<string, string> = {
  green: '#059669',   // Tailwind green-600
  yellow: '#d97706',  // Tailwind amber-600
  red: '#dc2626',     // Tailwind red-600
  grey: '#94a3b8',    // Tailwind slate-400
}

<BarChart data={ltvHistogram}>
  <CartesianGrid strokeDasharray="3 3" />
  <XAxis dataKey="bucket" />
  <YAxis />
  <Tooltip />
  <Bar dataKey="loan_count">
    {ltvHistogram.map((entry, index) => (
      <Cell key={`cell-${index}`} fill={COLOR_MAP[entry.color] ?? '#94a3b8'} />
    ))}
  </Bar>
</BarChart>
```

**Why Cell, not separate Bar:** The `color` field is per-bucket, not per-series. Separate Bar components would create a multi-series grouped chart, not a single histogram. [VERIFIED: this matches the established `ConcentrationPage` pattern in Phase 21 that uses `<Cell>` per slice in the PieChart]

### Pattern 2: Click-to-Filter from Histogram Bars (UX-01)

**LTV/DSCR histograms:** The bucket strings (`"<65%"`, `"65-75%"`, `">75%"`, `">1.4x"`, etc.) do not map cleanly to `loan_size_min`/`loan_size_max` filter params. The correct behavior per UX-01 is:
- **No click-to-filter** for LTV/DSCR histograms (buckets are categorical labels, not numeric ranges compatible with the filter sidebar)
- OR: future-proof with a TODO comment: `{/* TODO: Phase 22+ — LTV bar click could set loan_size_min/max but bucket strings don't map cleanly */}`

**Watchlist table risk rating column:** row click sets `setFilter('risk_rating', rating)` — this DOES map cleanly because `risk_rating` is already a filter param with exact-match support.

[VERIFIED: re_schemas.py FilterParams — `risk_rating: Optional[str]` is exact match]

### Pattern 3: Delinquency Waterfall (CREDIT-04)

**What:** A bar chart showing loan volume in each delinquency bucket, ordered current → 30 → 60 → 90 → default. This is a "waterfall" in the visual/conceptual sense (showing flow from current to distressed), not a true financial waterfall (no carry-over bars). Recharts `BarChart` with ordered data is the correct implementation — no special "waterfall" chart type needed.

**Backend bucket definitions:**
- `current`: `days_past_due == 0`
- `30`: `days_past_due >= 1 AND days_past_due < 60`
- `60`: `days_past_due >= 60 AND days_past_due < 90`
- `90`: `days_past_due >= 90 AND days_past_due < 180`
- `default`: `days_past_due >= 180`

[VERIFIED: KPI endpoint uses `days_past_due >= 30` for `delinquent_30_upb` etc. — our endpoint should use finer-grained exclusive buckets matching the above to prevent double-counting, consistent with how the KPI cumulative counts are constructed]

**New endpoint shape:**
```python
# backend/api/re_schemas.py addition
class DelinquencyBucket(BaseModel):
    bucket: str          # "current", "30", "60", "90", "default"
    loan_count: int
    total_upb: Decimal

class DelinquencyWaterfallResponse(BaseModel):
    buckets: list[DelinquencyBucket]
```

**Backend route:**
```python
@router.get("/delinquency-waterfall", response_model=DelinquencyWaterfallResponse)
def get_delinquency_waterfall(
    params: FilterParams = Depends(get_filter_params),
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),
) -> DelinquencyWaterfallResponse:
    from sqlalchemy import case
    from api.re_schemas import DelinquencyBucket

    filters = build_re_filters(db, params, current_user)

    bucket_expr = case(
        (RELoan.days_past_due == 0, "current"),
        (RELoan.days_past_due < 60, "30"),
        (RELoan.days_past_due < 90, "60"),
        (RELoan.days_past_due < 180, "90"),
        else_="default",
    )
    rows = (
        db.query(bucket_expr.label("bucket"), func.count(RELoan.id), func.sum(RELoan.upb))
        .filter(*filters)
        .group_by(bucket_expr)
        .all()
    )
    # Order: current, 30, 60, 90, default
    ORDER = {"current": 0, "30": 1, "60": 2, "90": 3, "default": 4}
    buckets = sorted(
        [DelinquencyBucket(bucket=r[0], loan_count=r[1],
            total_upb=Decimal(str(r[2])) if r[2] else Decimal("0"))
         for r in rows],
        key=lambda b: ORDER.get(b.bucket, 99)
    )
    return DelinquencyWaterfallResponse(buckets=buckets)
```

[ASSUMED — SQLAlchemy case() syntax is consistent with existing re_routes.py usage (lines 365–370); bucket definitions are reasonable industry convention]

### Pattern 4: Risk Rating Migration Matrix (CREDIT-05)

**What:** A 5×5 (or N×N) grid where rows = prior rating (1–5), columns = current rating (1–5), cells = count of loans that moved from row-rating to column-rating. Diagonal = no change. Off-diagonal = migration. Color cells: diagonal neutral/grey, below-diagonal (improvement) light green, above-diagonal (deterioration) light red.

**Backend approach:** The `RELoan` table stores both `risk_rating` (current) and `prior_risk_rating`. Both values are seeded for the two as_of_date snapshots. A single GROUP BY on `(prior_risk_rating, risk_rating)` at the latest as_of_date gives the migration counts.

```python
# backend/api/re_schemas.py addition
class MigrationCell(BaseModel):
    prior_rating: str
    current_rating: str
    loan_count: int
    total_upb: Decimal

class RiskRatingMigrationResponse(BaseModel):
    cells: list[MigrationCell]
    ratings: list[str]   # ordered list of ratings found (e.g. ["1","2","3","4","5"])
```

**Frontend rendering:** A plain HTML table where:
- Rows = `prior_rating` values (1–5)
- Columns = `current_rating` values (1–5)
- Cell background: green if `current_rating < prior_rating` (improvement), red if `current_rating > prior_rating` (deterioration), grey if equal

This avoids a 3rd-party matrix library. [VERIFIED: HTML tables are used for TopExposuresTable.tsx in Phase 21 — same pattern]

### Pattern 5: Rate Sensitivity Table (CREDIT-06)

The `/api/re/sensitivity` response already provides all data needed. A simple HTML table is the right tool, not a chart:

```
| Scenario | New WAC | Annual Interest Impact | Impact % |
|----------|---------|----------------------|----------|
| -300 bps | 4.25%   | -$45.2M               | -37.5%   |
| -200 bps | 5.25%   | -$30.1M               | -25.0%   |
| ...      | ...     | ...                   | ...      |
```

Color-code: negative impact rows use red text, positive use green. [ASSUMED — standard financial sensitivity table convention]

### Pattern 6: Watchlist Table (CREDIT-03)

**Definition of "criticized":** In banking regulation, risk ratings 4 and 5 are "criticized" (Special Mention and Substandard/Doubtful/Loss). The watchlist shows loans with `risk_rating IN ('4', '5')`.

**How to fetch:** Call `GET /api/re/loans` with the existing `risk_rating` filter param. However, since the filter accepts a single exact-match value, the watchlist must either:
- Fetch all loans and filter client-side for ratings 4 and 5 (wasteful for large portfolios)
- OR: make two parallel TanStack Query calls (one per rating) and merge — reasonable for POC
- OR: add a `risk_rating_gte` param to the backend filter — over-engineering for a POC

**Recommended approach for POC:** One `useQuery` call to `/api/re/loans` with no risk_rating filter, then client-side filter `items.filter(l => ['4','5'].includes(l.risk_rating ?? ''))`. The page-level filter sidebar already limits the dataset; for seeded data (500–2,000 loans) this is acceptable. [ASSUMED — seeded loan count makes client-side filter viable]

**Trend arrow logic:**
- `risk_rating > prior_risk_rating` → up arrow (deterioration) — red
- `risk_rating < prior_risk_rating` → down arrow (improvement) — green
- `risk_rating === prior_risk_rating` → dash — neutral

[VERIFIED: `LoanSummary` in re_schemas.py does NOT include `prior_risk_rating` — but `LoanDetailResponse` does. The watchlist will need to call the detail endpoint per loan OR we should add `prior_risk_rating` to `LoanSummary`. The planner must decide: extend `LoanSummary` in re_schemas.py and the TypeScript interface, or accept a detail-call-per-loan approach. Adding the field to LoanSummary is the cleaner choice.]

**IMPORTANT FINDING:** `LoanSummary` schema (re_schemas.py line 199–218) and the TypeScript `LoanSummary` interface (re.ts line 119–134) do NOT include `prior_risk_rating`. To show trend arrows without N+1 API calls, Plan 01 must add `prior_risk_rating: Optional[str]` to `LoanSummary` (Python) and `prior_risk_rating: string | null` to the TypeScript interface. The underlying `RELoan` model already has the field.

### Pattern 7: Tab Wiring (already done)

`ReDashboard.tsx` already has `{ label: 'Credit Quality', to: '/re-dashboard/credit', end: false }` in `TABS`.
`App.tsx` already has `<Route path="credit" element={<ReStubPage />} />`.

The only change needed in `App.tsx` is:
```tsx
// Before:
<Route path="credit" element={<ReStubPage />} />

// After:
import ReCreditQualityPage from './pages/ReCreditQualityPage'
<Route path="credit" element={<ReCreditQualityPage />} />
```

[VERIFIED: App.tsx line 53 — `<Route path="credit" element={<ReStubPage />} />`; ReDashboard.tsx lines 4–10 — Credit Quality tab already in TABS array]

### Anti-Patterns to Avoid

- **Multiple Bar components per color:** Creates a grouped multi-series chart, not a color-banded histogram. Use single `<Bar>` + `<Cell>` array instead.
- **Fetching loans detail endpoint for all watchlist loans:** N+1 calls. Add `prior_risk_rating` to LoanSummary instead.
- **Treating KPI delinquency UPB totals as waterfall buckets:** KPI buckets are cumulative (30+ includes 60+ includes 90+). Waterfall needs exclusive buckets. Derive from the new endpoint using exclusive DPD ranges.
- **Hardcoding risk rating scale 1–5:** Rating strings come from the DB as `String(10)`. Always read actual distinct values from the migration endpoint's `ratings` field rather than assuming 1–5.
- **Calling build_re_filters without the as_of_date default:** The default logic (MAX as_of_date) is inside `build_re_filters()`. Any new endpoint MUST use this helper — never build filters inline.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Color mapping for bars | Custom CSS injection | `<Cell fill={COLOR_MAP[entry.color]}>` inside existing `<Bar>` | Recharts already supports per-bar color via Cell; hand-rolling breaks Tooltip |
| Delinquency buckets on frontend | Client-side DPD bucketing from raw loan records | New `/api/re/delinquency-waterfall` endpoint | Avoids fetching full loan list (could be thousands of records) just to count DPD categories |
| Migration matrix computation | Frontend pivot from raw loan list | New `/api/re/risk-rating-migration` endpoint | Pivot from thousands of loans is a GROUP BY in SQL — one query |
| Financial sensitivity math | Frontend WAC delta calculations | Existing `/api/re/sensitivity` endpoint | Already correct with Decimal precision; frontend receives ready-to-display numbers |

---

## New Backend Endpoints — Detailed Specs

### Endpoint 1: `GET /api/re/delinquency-waterfall`

**Purpose:** CREDIT-04 — returns loan count and UPB in each delinquency bucket in waterfall order.

**Request:** Same `FilterParams` as all other endpoints (as_of_date, property_type, state, etc.)

**Response schema:**
```python
class DelinquencyBucket(BaseModel):
    bucket: str          # "current" | "30" | "60" | "90" | "default"
    loan_count: int
    total_upb: Decimal

class DelinquencyWaterfallResponse(BaseModel):
    buckets: list[DelinquencyBucket]  # always ordered: current, 30, 60, 90, default
```

**Bucket definitions (exclusive ranges):**
- `current`: `days_past_due == 0`
- `30`: `days_past_due >= 1 AND days_past_due < 60`
- `60`: `days_past_due >= 60 AND days_past_due < 90`
- `90`: `days_past_due >= 90 AND days_past_due < 180`
- `default`: `days_past_due >= 180`

**Implementation:** SQLAlchemy `case()` + GROUP BY, same pattern as LTV/DSCR buckets in `get_distributions()`.

**Security:** Must use `build_re_filters()` + `require_sales_team_access()` — same as all other endpoints. [VERIFIED: consistent with existing endpoint pattern]

### Endpoint 2: `GET /api/re/risk-rating-migration`

**Purpose:** CREDIT-05 — returns pivot data for the 5×5 migration matrix.

**Request:** Same `FilterParams`. `as_of_date` defaults to MAX(as_of_date) per `build_re_filters()`.

**Response schema:**
```python
class MigrationCell(BaseModel):
    prior_rating: str
    current_rating: str
    loan_count: int
    total_upb: Decimal

class RiskRatingMigrationResponse(BaseModel):
    cells: list[MigrationCell]
    ratings: list[str]  # ordered distinct rating values found
```

**Implementation:**
```python
rows = (
    db.query(RELoan.prior_risk_rating, RELoan.risk_rating,
             func.count(RELoan.id), func.sum(RELoan.upb))
    .filter(*filters)
    .filter(RELoan.prior_risk_rating.isnot(None))
    .filter(RELoan.risk_rating.isnot(None))
    .group_by(RELoan.prior_risk_rating, RELoan.risk_rating)
    .all()
)
```

**Ratings list:** Derived from distinct values found in `cells` — not hardcoded. Sorted numerically if possible.

**Frontend rendering:** HTML table. Rows = prior rating. Columns = current rating. Empty cells (no loans with that migration path) show `—`. Color: diagonal neutral, prior > current → green cell background, prior < current → red cell background.

---

## LoanSummary Schema Extension Required

**Finding:** `prior_risk_rating` is present on `RELoan` model but absent from `LoanSummary` schema. The watchlist trend arrow requires this field.

**Changes needed in Plan 01:**

1. `backend/api/re_schemas.py` — add to `LoanSummary`:
   ```python
   prior_risk_rating: Optional[str]
   ```

2. `frontend/src/types/re.ts` — add to `LoanSummary` interface:
   ```typescript
   prior_risk_rating: string | null
   ```

No migration needed — the field already exists in the database. [VERIFIED: models.py line 256 — `prior_risk_rating = Column(String(10))`; re_schemas.py line 199–218 — `prior_risk_rating` is absent from `LoanSummary`]

---

## Common Pitfalls

### Pitfall 1: Cumulative vs Exclusive Delinquency Buckets
**What goes wrong:** Using KPI endpoint delinquency values (`delinquent_30_upb`, `delinquent_60_upb`, `delinquent_90_upb`) directly as waterfall bars. These are cumulative — 60+ loans are also counted in 30+ and 90+ is counted in both.
**Why it happens:** The KPI endpoint is designed for "total delinquency exposure at each threshold," not for bucket exclusivity.
**How to avoid:** Use the new `/api/re/delinquency-waterfall` endpoint with exclusive DPD ranges. Never derive waterfall from KPI values.
**Warning signs:** Waterfall bars don't add up to total loan count.

### Pitfall 2: Multiple Bar Components Instead of Cell Array
**What goes wrong:** Creating three separate `<Bar>` components (green, yellow, red) to get different colors. This creates a grouped bar chart with 3 clustered bars per bucket instead of single bars.
**Why it happens:** Developers familiar with multi-series charts apply the same pattern to single-series color-banded charts.
**How to avoid:** One `<Bar dataKey="loan_count">` with a `{data.map((entry, i) => <Cell key={i} fill={COLOR_MAP[entry.color]} />)}` array inside. [VERIFIED: this matches the pattern used for PieChart Cell in Phase 21]
**Warning signs:** Histogram shows 3 bars per bucket.

### Pitfall 3: Migration Matrix Shows Wrong Period Comparison
**What goes wrong:** Querying `risk_rating` vs `prior_risk_rating` from the PRIOR as_of_date snapshot, showing comparison to a snapshot two periods ago.
**Why it happens:** The as_of_date filter default is MAX(as_of_date), which is correct — `prior_risk_rating` on the LATEST snapshot already captures the prior period comparison. No cross-snapshot JOIN is needed.
**How to avoid:** Use `build_re_filters()` default (latest snapshot). `prior_risk_rating` on the latest snapshot IS the prior period rating. No JOIN between two as_of_date snapshots is needed.
**Warning signs:** Migration matrix shows movement that doesn't match expected from seed data.

### Pitfall 4: N+1 API Calls for Watchlist Trend Arrows
**What goes wrong:** Calling `/api/re/loans/{id}` for each watchlist row to get `prior_risk_rating`.
**Why it happens:** `LoanSummary` doesn't currently include `prior_risk_rating`, so developers fall back to the detail endpoint.
**How to avoid:** Extend `LoanSummary` in re_schemas.py to include `prior_risk_rating`. One batch call to `/api/re/loans` returns everything needed. See LoanSummary Schema Extension section above.
**Warning signs:** Network tab shows one request per watchlist row.

### Pitfall 5: Risk Rating Filter Conflict on Watchlist Page
**What goes wrong:** The global filter sidebar has a `risk_rating` dropdown. If the user sets it to "3" while viewing the watchlist (which filters for 4 and 5), the watchlist shows empty with no explanation.
**Why it happens:** The watchlist depends on the global filter state.
**How to avoid:** The watchlist should display a note when the global `risk_rating` filter overrides the watchlist's own criticized-loan filter. Alternatively, treat the watchlist as always showing risk_rating 4 and 5 regardless of the global filter (call `/api/re/loans` without passing the global `risk_rating`, but pass all other filter params). This is the cleaner UX decision — the planner should resolve this.

---

## Code Examples

### Color-Banded Histogram (CREDIT-01, CREDIT-02)

```tsx
// Source: Recharts docs pattern for per-bar colors
// [ASSUMED — consistent with Cell usage pattern verified in Phase 21 PieChart]
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { HistogramBucket } from '../types/re'

const COLOR_MAP: Record<string, string> = {
  green:  '#059669',  // tailwind green-600
  yellow: '#d97706',  // tailwind amber-600
  red:    '#dc2626',  // tailwind red-600
  grey:   '#94a3b8',  // tailwind slate-400
}

function LTVHistogram({ data }: { data: HistogramBucket[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
        <YAxis />
        <Tooltip />
        <Bar dataKey="loan_count">
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLOR_MAP[entry.color] ?? '#94a3b8'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
```

### Delinquency Waterfall (CREDIT-04)

```tsx
// Source: Recharts BarChart — same pattern as loan size histogram in Phase 21
// Color: green for current, yellow for 30, orange for 60, red for 90+, dark red for default
const DELINQUENCY_COLORS: Record<string, string> = {
  current: '#059669',
  '30':    '#d97706',
  '60':    '#f97316',
  '90':    '#dc2626',
  default: '#7f1d1d',
}

<BarChart data={waterfallData}>
  <XAxis dataKey="bucket" />
  <YAxis />
  <Tooltip />
  <Bar dataKey="loan_count">
    {waterfallData.map((entry, i) => (
      <Cell key={i} fill={DELINQUENCY_COLORS[entry.bucket] ?? '#94a3b8'} />
    ))}
  </Bar>
</BarChart>
```

### Migration Matrix Rendering (CREDIT-05)

```tsx
// Source: HTML table — same pattern as TopExposuresTable.tsx in Phase 21
// [VERIFIED: TopExposuresTable.tsx exists in frontend/src/components/re/]
function MigrationMatrix({ cells, ratings }: { cells: MigrationCell[]; ratings: string[] }) {
  // Build lookup map for O(1) access
  const cellMap = new Map(cells.map(c => [`${c.prior_rating}:${c.current_rating}`, c]))

  const getCellColor = (prior: string, current: string): string => {
    if (prior === current) return 'bg-gray-100'
    return Number(current) > Number(prior) ? 'bg-red-100' : 'bg-green-100'
  }

  return (
    <table className="text-xs w-full border-collapse">
      <thead>
        <tr>
          <th className="p-1 text-left text-[#475569]">Prior \ Current</th>
          {ratings.map(r => <th key={r} className="p-1 text-center">{r}</th>)}
        </tr>
      </thead>
      <tbody>
        {ratings.map(prior => (
          <tr key={prior}>
            <td className="p-1 font-medium text-[#1a3868]">{prior}</td>
            {ratings.map(current => {
              const cell = cellMap.get(`${prior}:${current}`)
              return (
                <td key={current}
                    className={`p-1 text-center ${getCellColor(prior, current)}`}>
                  {cell?.loan_count ?? '—'}
                </td>
              )
            })}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

### TanStack Query Pattern (follows Phase 21 convention)

```tsx
// Source: useKPIs.ts + RePortfolioPage.tsx — established pattern
const distributions = useQuery({
  queryKey: ['re-distributions', filters],
  queryFn: async () => {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== null && v !== '')
    )
    const { data } = await axios.get<DistributionsResponse>('/api/re/distributions', { params })
    return data
  },
})

const sensitivity = useQuery({
  queryKey: ['re-sensitivity', filters],
  queryFn: async () => {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== null && v !== '')
    )
    const { data } = await axios.get<SensitivityResponse>('/api/re/sensitivity', { params })
    return data
  },
})
```

---

## Plan Split Recommendation

**3 plans** — matches the complexity and natural seam between backend and frontend work.

### Plan 01: Backend — New Endpoints + LoanSummary Extension
**Scope:**
1. Add `prior_risk_rating` to `LoanSummary` in `re_schemas.py` and update TypeScript `LoanSummary` interface in `re.ts`
2. Add `DelinquencyBucket` + `DelinquencyWaterfallResponse` schemas to `re_schemas.py`
3. Add `GET /api/re/delinquency-waterfall` endpoint to `re_routes.py`
4. Add `MigrationCell` + `RiskRatingMigrationResponse` schemas to `re_schemas.py`
5. Add `GET /api/re/risk-rating-migration` endpoint to `re_routes.py`
6. Add TypeScript interfaces for new responses to `re.ts`

**Covers:** CREDIT-04 (backend), CREDIT-05 (backend), prerequisite for CREDIT-03 (LoanSummary extension)
**Verification:** `curl /api/re/delinquency-waterfall` returns 5 ordered buckets; `curl /api/re/risk-rating-migration` returns cells matrix

### Plan 02: Frontend — ReCreditQualityPage with All Six Panels
**Scope:**
1. Create `ReCreditQualityPage.tsx` with six panels in 2-column grid:
   - LTV histogram (CREDIT-01)
   - DSCR histogram (CREDIT-02)
   - Watchlist table (CREDIT-03)
   - Delinquency waterfall (CREDIT-04)
   - Migration matrix (CREDIT-05)
   - Rate sensitivity table (CREDIT-06)
2. Create `WatchlistTable.tsx`, `MigrationMatrix.tsx`, `SensitivityTable.tsx` sub-components
3. Update `App.tsx` to replace `<ReStubPage />` with `<ReCreditQualityPage />` at `credit` route
4. All panels use `ChartCard` wrapper; TanStack Query with filter-keyed queries

**Covers:** CREDIT-01, CREDIT-02, CREDIT-03, CREDIT-04, CREDIT-05, CREDIT-06, UX-01

### Plan 03: Verification
**Scope:** Manually verify all six success criteria against seeded data; confirm filter sidebar changes re-render all panels; confirm tab navigation and URL params.

---

## Panel Layout (2-column grid, same as Phase 21)

```
[ LTV Histogram        ] [ DSCR Histogram       ]
[ Watchlist Table (full width)                  ]
[ Delinquency Waterfall] [ Rate Sensitivity Table]
[ Migration Matrix (full width)                 ]
```

Rationale: The watchlist and migration matrix are data-dense (multi-column tables) and warrant full width. The two histograms and the sensitivity table fit naturally in paired cells.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Choropleth map for geo data | Ranked bar chart | Phase 21 (D-03) | No mapping library needed; same for all charts |
| Multiple Bar components for color bands | Single Bar + Cell array | Recharts v2+ | Correct histogram rendering |
| Separate endpoints per credit metric | Unified distributions endpoint | Phase 18 | LTV and DSCR already served from one endpoint |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | LTV/DSCR bars should NOT trigger click-to-filter because bucket labels don't map to filter params | Pattern 2 | UX-01 may need partial implementation for these bars; revisit |
| A2 | Watchlist should fetch all loans then filter client-side for risk_rating 4 and 5 (not server-side filtered) | Pattern 6 | For large real datasets, a server-side filter would be required; acceptable for seeded POC |
| A3 | Cell color CSS classes for migration matrix (red-100/green-100) match existing Tailwind palette | Pattern 4 | Minor visual inconsistency if palette doesn't match; easy to adjust |
| A4 | "Criticized" = risk_rating 4 or 5 in this POC's rating scale | Pattern 6 | Seed data may use different criticized threshold |
| A5 | Delinquency waterfall bars are colored individually (green→red gradient by severity) | Code Examples | Could use single color per project design preference |

---

## Open Questions

1. **Watchlist global filter interaction**
   - What we know: The global `risk_rating` sidebar filter passes to all endpoints. If set to "3", the watchlist (which shows only 4–5) would be empty.
   - What's unclear: Should the watchlist bypass the global risk_rating filter and always show ratings 4–5?
   - Recommendation: Fetch watchlist loans with all filter params EXCEPT `risk_rating` (hardcode `risk_rating=4,5` if backend supports multi-value, or fetch without risk_rating and filter client-side). Note for planner to decide.

2. **LTV/DSCR bar click behavior (UX-01 scope)**
   - What we know: UX-01 says "clicking any chart segment applies that dimension as a filter." LTV/DSCR bucket strings don't map to filter params.
   - What's unclear: Does the product owner intend LTV/DSCR bar clicks to do anything? There's no natural filter key for them.
   - Recommendation: Make bars non-clickable (no cursor pointer, no onClick). Add a comment for future parameterized LTV filter support.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 22 is purely code changes (new Python routes + React component). No external tools, services, databases, or CLI utilities beyond the existing development stack are required. All dependencies (Python FastAPI, SQLAlchemy, React, Recharts, TanStack Query) are already installed.

---

## Validation Architecture

`workflow.nyquist_validation` is absent from `.planning/config.json` — treated as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest (existing) |
| Backend config | `backend/pytest.ini` or inline `pyproject.toml` |
| Backend quick run | `cd backend && pytest tests/test_re_routes.py -x -q` |
| Backend full suite | `cd backend && pytest -x -q` |
| Frontend | No automated tests in this project (ESLint only) |

### Success Criteria → Test Map

| Criterion | Behavior | Test Type | Automated Command | Notes |
|-----------|----------|-----------|-------------------|-------|
| SC-1: LTV histogram color bands | GET /api/re/distributions returns ltv_histogram with correct colors | Integration (backend) | `pytest tests/test_re_routes.py::test_distributions_ltv_color_bands -x` | Existing endpoint; test that color field is correct |
| SC-2: DSCR histogram color bands | GET /api/re/distributions returns dscr_histogram with correct colors | Integration (backend) | `pytest tests/test_re_routes.py::test_distributions_dscr_color_bands -x` | Same endpoint as SC-1 |
| SC-3: Watchlist table | Loans with risk_rating 4–5 appear; trend arrows render | Manual (frontend) | N/A | UI rendering; verify in browser |
| SC-4: Delinquency waterfall | New endpoint returns 5 ordered buckets | Integration (backend) | `pytest tests/test_re_routes.py::test_delinquency_waterfall -x` | New endpoint — test file must be extended |
| SC-5: Migration matrix | New endpoint returns cells with prior/current pairs | Integration (backend) | `pytest tests/test_re_routes.py::test_risk_rating_migration -x` | New endpoint — test file must be extended |
| SC-6: Sensitivity table | GET /api/re/sensitivity returns 6 scenarios | Integration (backend) | `pytest tests/test_re_routes.py::test_sensitivity -x` | Existing endpoint |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_re_routes.py -x -q`
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full backend suite green + manual browser verification of all 6 panels before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_re_routes.py` — must be extended with tests for the two new endpoints (`test_delinquency_waterfall`, `test_risk_rating_migration`). Existing test file likely exists from Phase 18; new test functions must be added.

---

## Security Domain

`security_enforcement` is not present in `.planning/config.json` — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | `require_sales_team_access()` already on all `/api/re/*` endpoints; new endpoints must use same dependency |
| V3 Session Management | No | No new session logic |
| V4 Access Control | Yes | `build_re_filters()` applies sales_team scope; new endpoints MUST call this helper — never bypass |
| V5 Input Validation | Yes | FilterParams Pydantic model validates all query params for new endpoints (reuse existing `get_filter_params` dep) |
| V6 Cryptography | No | No new crypto |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Sales team sees other team's loans | Info Disclosure | `build_re_filters()` with `require_sales_team_access()` — MUST be applied on both new endpoints |
| Arbitrary SQL via sort_by on loans | Tampering | Existing `ALLOWED_SORT_FIELDS` whitelist; no new sort params added |
| Empty portfolio edge case | DoS/Error | Both new endpoints must handle zero-row result (same pattern as existing endpoints: return empty list) |

---

## Sources

### Primary (HIGH confidence)
- `backend/api/re_routes.py` (read in full) — confirmed existing endpoint implementations for distributions (lines 350–441), sensitivity (lines 869–920), loans (lines 496–542)
- `backend/api/re_schemas.py` (read in full) — confirmed `LoanSummary` lacks `prior_risk_rating`; confirmed `DistributionsResponse` has `color` field per bucket
- `backend/db/models.py` (read in full) — confirmed `RELoan` has `days_past_due`, `risk_rating`, `prior_risk_rating`; confirmed `RELoanCashflow` fields
- `frontend/src/pages/RePortfolioPage.tsx` (read in full) — confirmed Phase 21 patterns: `<Cell>` in PieChart, `useQuery` with filter-keyed queries, `ChartCard` usage
- `frontend/src/App.tsx` (read in full) — confirmed `<ReStubPage />` at `credit` route; confirmed nested route structure
- `frontend/src/pages/ReDashboard.tsx` (read in full) — confirmed Credit Quality tab already in TABS array
- `frontend/src/types/re.ts` (read in full) — confirmed `LoanSummary` interface lacks `prior_risk_rating`; confirmed `SensitivityResponse` has all needed fields

### Secondary (MEDIUM confidence)
- `.planning/phases/21-portfolio-composition-page/21-RESEARCH.md` (read lines 1–200) — confirmed locked decisions (D-01 through D-26) from Phase 21 still apply; recharts version 3.8.1

### Tertiary (LOW confidence — training knowledge)
- Recharts `<Cell>` pattern for per-bar colors — consistent with all Recharts documentation patterns; verified it matches how Phase 21 used Cell in PieChart

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed in frontend/package.json
- Existing endpoint coverage: HIGH — read full re_routes.py; confirmed what exists and what's missing
- New endpoint design: HIGH — directly derived from RELoan model fields and existing patterns
- Recharts color-banded bar pattern: MEDIUM — Cell usage verified via Phase 21 PieChart pattern; direct BarChart+Cell combination is [ASSUMED] consistent
- LoanSummary gap finding: HIGH — confirmed by reading re_schemas.py line 199–218 and comparing to models.py

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable tech stack; no fast-moving dependencies)
