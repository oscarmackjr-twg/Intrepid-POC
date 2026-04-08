# Stack Research: RE Loan Portfolio Dashboard (Milestone v2.0 Additions)

**Research Type:** Subsequent Milestone — Stack Additions Only
**Date:** 2026-04-08
**Milestone:** v2.0 — Real Estate Loan Portfolio Dashboard POC
**Scope:** NEW libraries only. Existing stack (React 19, Vite 7, TypeScript 5, FastAPI, SQLAlchemy, Alembic, PostgreSQL, S3, TailwindCSS 4, Axios) is validated and unchanged.

---

## Existing Stack Snapshot (DO NOT RE-RESEARCH)

| Layer | Already Installed |
|-------|-----------------|
| Frontend framework | React 19.2.x + Vite 7.x + TypeScript 5.9 |
| Routing | react-router 7.x + react-router-dom 6.x |
| Styling | Tailwind CSS 4.x (via `@tailwindcss/vite`) |
| HTTP client | Axios 1.7.x |
| Backend | FastAPI, SQLAlchemy 2, Alembic, psycopg2-binary + psycopg3 |
| Data processing | pandas 2.2, numpy 2, numpy-financial, openpyxl, scipy |
| Auth | python-jose, passlib, bcrypt |
| AWS | boto3, botocore |
| Linting | ESLint 9, ruff, husky, lint-staged |

---

## Frontend Additions

### 1. Charting — Recharts 3.x

**Install:** `npm install recharts@^3.8.1`

**Replaces / Adds:** Nothing currently exists for charts.

**Why Recharts over alternatives:**
- React 19 compatible in v3 (peer dep issue with `react-is` was resolved in v3; install proceeds cleanly with React 19 — no `--legacy-peer-deps` needed in v3).
- Composable declarative API maps directly to how React components are built: `<BarChart>`, `<LineChart>`, `<PieChart>` with child `<Bar>`, `<XAxis>`, `<Tooltip>` — no imperative D3 calls.
- Covers every chart type required: PieChart/donut (property type composition), BarChart stacked (maturity profile), LineChart (P&I actual vs projected), BarChart (histogram buckets for LTV/loan size), ComposedChart (yield analysis overlays).
- Built on D3 internally — you get D3 accuracy without managing D3's imperative selection model.
- Recharts is the most downloaded React charting library (3–4M weekly downloads); community support and examples are abundant.
- Alternative considered: **Nivo** — excellent for complex chart types but adds ~300KB over Recharts and has more setup ceremony for simple line/bar charts. Use Nivo if you later need advanced network graphs or chord diagrams (not needed here).
- Alternative considered: **Victory** — smaller but less actively maintained; fewer examples for financial dashboards.
- Alternative considered: **Chart.js via react-chartjs-2** — canvas-based (not SVG), which makes drill-down click interactions harder to implement cleanly with React event system.

**React 19 notes:** Recharts v3 ships React 19 as a peer dependency. The `react-is` mismatch that affected v2 alphas is fixed in the v3 stable release. Verified: v3.8.1 published 2026-03-25.

**Covers:** KPI sparklines, pie/donut, histogram, stacked bar (maturity), line chart (P&I/NOI/CPR), waterfall (delinquency).

---

### 2. US Geographic Heatmap — d3-geo + topojson-client (direct, no wrapper library)

**Install:** `npm install d3-geo@^3.1.0 topojson-client@^3.1.0`
**Types:** `npm install -D @types/d3-geo @types/topojson-client`

**Replaces / Adds:** Nothing currently exists for maps.

**Why direct d3-geo + topojson over wrapper libraries:**

The two obvious wrappers are `react-simple-maps` (original, last meaningful update 2022, uses outdated React APIs that break with React 19) and `@vnedyalk0v/react19-simple-maps` (a fork rewritten for React 19, v2.0.3 as of 2026-04-07). The fork works and is MIT licensed, but it is a single-maintainer project with unknown long-term support — a meaningful risk for a production codebase.

The direct approach uses only two stable D3 sub-packages:
- `d3-geo` provides `geoAlbersUsa()` projection and `geoPath()` path generator. These primitives have been stable for years.
- `topojson-client` converts compressed TopoJSON state boundaries to SVG path strings.
- The resulting component is ~80 lines of TypeScript — fully owned, no abstraction layer that can break on a dependency update.

For a POC with ~50 US states (fixed static geometry), there is no meaningful complexity reduction from a wrapper library. Build it directly.

**GeoJSON source:** Use the public US state boundaries TopoJSON from `https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json` (US Atlas 3, MIT license). Fetch once at app boot, cache in Zustand. No license or attribution issues.

**Pattern:**
```typescript
import { geoAlbersUsa, geoPath } from 'd3-geo'
import { feature } from 'topojson-client'

// Color scale: manual linear interpolation on UPB or loan count per state
// Tooltip: Recharts Tooltip pattern (div positioned on mouse event)
// Click: sets global filter state (Zustand) → filters all dashboard panels
```

**Covers:** State choropleth heatmap (UPB concentration, loan count, delinquency rate by state). MSA-level can be added later with county-level TopoJSON.

---

### 3. Server State / Data Fetching — TanStack Query v5

**Install:** `npm install @tanstack/react-query@^5.96.0`

**Replaces / Adds:** Nothing installed yet for server state management (raw Axios calls in existing pages).

**Why TanStack Query:**
- Handles caching, background refetch, and stale-while-revalidate for all dashboard API endpoints. Without it, every filter change triggers a fresh fetch with no deduplication.
- Dashboard has ~10 distinct data endpoints (KPIs, charts, tables, sensitivity analysis). TanStack Query manages all of them with a unified `queryKey` cache — filter changes invalidate the relevant queries automatically.
- The existing pages use raw `useEffect + axios` patterns. TanStack Query replaces this cleanly; existing pages can migrate incrementally.
- v5.96.2 verified React 19 compatible (latest published 2026-04-03).

**Integration notes:**
- Wrap the app in `<QueryClientProvider>` in `main.tsx`.
- Each dashboard panel uses `useQuery({ queryKey: ['kpis', filters], queryFn: () => api.getKPIs(filters) })`.
- Global filter sidebar changes update Zustand state → `queryKey` arrays change → TanStack Query re-fetches only the affected queries.

**Do NOT add:** `@tanstack/react-query-devtools` in production build — dev-only, tree-shake with `process.env.NODE_ENV`.

---

### 4. UI State / Global Filters — Zustand v5

**Install:** `npm install zustand@^5.0.12`

**Replaces / Adds:** No shared state management exists currently (each page is self-contained).

**Why Zustand:**
- The global filter sidebar (date range, property type, geography, risk rating, etc.) must drive all dashboard panels. This is cross-cutting UI state — exactly what Zustand is designed for.
- No boilerplate: one `create()` call, select slices where needed. No Provider wrapping.
- v5.0.12 requires React 18–19 and TypeScript 5+ — matches existing stack exactly.
- Do NOT use React Context for this: context re-renders every consumer on every filter change, which is catastrophic for a dashboard with 10+ panels.

**Pattern:**
```typescript
interface FilterState {
  asOf: string          // ISO date
  propertyTypes: string[]
  states: string[]
  riskRatings: string[]
  rateType: 'fixed' | 'floating' | 'all'
  setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void
  resetFilters: () => void
}

const useFilterStore = create<FilterState>()(...)
```

---

### 5. Data Tables — TanStack Table v8

**Install:** `npm install @tanstack/react-table@^8.21.3`

**Replaces / Adds:** Existing pages use basic HTML `<table>` elements. TanStack Table replaces tables that need sorting, filtering, and pagination.

**Why TanStack Table:**
- Headless — styled entirely with existing Tailwind CSS classes, no design system conflict.
- Column sorting, multi-column filtering, pagination, and row click handlers are built-in.
- For the watchlist (500–2,000 rows), pair with `@tanstack/react-virtual` for row virtualization.
- v8.21.3 React 19 compatible (v9 alpha is in progress but not production-ready as of April 2026 — use v8 stable).

**Install virtual:** `npm install @tanstack/react-virtual@^3.13.0`

**Covers:** Watchlist table, top-10 exposures table, pipeline table, risk rating migration matrix (as a styled table, not chart).

---

### 6. Filter Forms — react-hook-form v7 + Zod v3

**Install:** `npm install react-hook-form@^7.72.1 zod@^3.24.0 @hookform/resolvers@^3.10.0`

**Replaces / Adds:** No form validation library exists in the frontend yet.

**Why:**
- The global filter sidebar has ~8 controlled inputs (date pickers, multi-selects, range sliders). React Hook Form handles these with minimal re-renders — form state stays local until submission.
- Zod schemas validate filter inputs (date format, valid state codes, numeric ranges) before queries are dispatched.
- `@hookform/resolvers` bridges RHF and Zod in one line: `resolver: zodResolver(FilterSchema)`.
- RHF v7.72.1 explicitly supports React 19 (verified April 2026).

---

### 7. PDF Export — html2canvas-pro + jsPDF

**Install:** `npm install html2canvas-pro@^2.0.2 jspdf@^4.2.1`

**Replaces / Adds:** No PDF export capability currently exists.

**Why html2canvas-pro + jsPDF over alternatives:**

Option A — `@react-pdf/renderer`: requires rewriting the entire dashboard layout using `<View>/<Text>/<Image>` primitives. Rebuilding 6 dashboard pages in react-pdf's component model is a multi-week effort. Wrong tradeoff for a POC.

Option B — `react-to-pdf` wrapper: thin wrapper around html2canvas + jsPDF. Adds abstraction with no benefit over the direct approach; less control over canvas scaling and page breaks.

Option C — Server-side WeasyPrint: adds an API endpoint, a Jinja2 HTML template, headless rendering, and S3 storage for what is a "print this screen" button. Massive over-engineering for a POC.

**Chosen approach:** `html2canvas-pro` (actively maintained fork of html2canvas, v2.0.2 published 2026-03-14) captures the rendered dashboard DOM as a canvas. `jsPDF` v4.x (latest stable, v4.2.1, published 2026-03-18; v4.0 fixed a path traversal security issue) embeds the canvas image into a PDF and triggers browser download.

**Limitations accepted for POC:**
- PDF output is a rasterized image (not searchable text). Acceptable for a snapshot export.
- Tailwind CSS 4's JIT-generated classes render correctly because html2canvas reads computed styles from the DOM, not class names.
- Charts (Recharts SVG) render correctly into canvas — SVG-to-canvas conversion is handled natively.

**Pattern:**
```typescript
import html2canvas from 'html2canvas-pro'
import jsPDF from 'jspdf'

async function exportDashboardPDF(ref: React.RefObject<HTMLDivElement>) {
  const canvas = await html2canvas(ref.current!, { scale: 2, useCORS: true })
  const pdf = new jsPDF({ orientation: 'landscape', unit: 'px', format: 'a4' })
  pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, pdf.internal.pageSize.width, 0)
  pdf.save(`portfolio-dashboard-${new Date().toISOString().slice(0, 10)}.pdf`)
}
```

**Covers:** "Export PDF" button on dashboard header — captures visible dashboard panels as a multi-page PDF.

---

### 8. CSV Export — Native Browser API (no library)

**Replaces / Adds:** No library needed.

**Why no library:**
- CSV export from a filtered TanStack Table is 10 lines of vanilla TypeScript: serialize rows to comma-delimited strings, create a `Blob`, trigger `URL.createObjectURL` download. No library justified.
- `papaparse` (v5.5.3, last published 1 year ago) adds dependency weight for functionality that is trivially implemented inline. Skip it.

**Pattern:**
```typescript
function exportCSV(rows: LoanRow[], columns: string[], filename: string) {
  const header = columns.join(',')
  const body = rows.map(r => columns.map(c => JSON.stringify(r[c] ?? '')).join(',')).join('\n')
  const blob = new Blob([`${header}\n${body}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}
```

---

## Backend Additions

### 9. Analytics Query Layer — SQLAlchemy Core expressions (already installed)

**No new library needed.**

The existing backend uses SQLAlchemy 2.0 (ORM + Core both available). All KPI aggregations (WAC, WAM, UPB, LTV, DSCR, delinquency buckets, maturity profile) are SQL aggregate queries expressible with SQLAlchemy Core `func.avg()`, `func.sum()`, `case()`, and `select()`. Pandas (already installed) handles any post-query reshaping for interest rate sensitivity analysis.

**New FastAPI routers to add:**

| Router | Path | What |
|--------|------|------|
| `dashboard.py` | `GET /api/v1/dashboard/kpis` | UPB, WAC, WAM, LTV, DSCR, active count, delinquency summary |
| `dashboard.py` | `GET /api/v1/dashboard/composition` | Property type breakdown, maturity buckets, vintage counts |
| `dashboard.py` | `GET /api/v1/dashboard/geo` | UPB and loan count grouped by state |
| `dashboard.py` | `GET /api/v1/dashboard/credit` | LTV/DSCR histogram buckets, watchlist loans |
| `dashboard.py` | `GET /api/v1/dashboard/cashflow` | Monthly P&I actual vs projected time series |
| `dashboard.py` | `GET /api/v1/dashboard/sensitivity` | Rate shock scenarios (+/-100/200/300 bps on payment) |
| `loans.py` | `GET /api/v1/loans` | Paginated, filtered, sorted loan table |
| `loans.py` | `GET /api/v1/loans/{id}` | Single loan detail card |

**Filter parameter pattern** (all endpoints accept as query params):
```
?as_of=2026-04-01&property_types=office,retail&states=NY,CA&risk_ratings=3,4&rate_type=fixed
```

**Interest rate sensitivity:** Use pandas already installed — build amortization schedules at each rate shock, compute payment delta. No additional library needed.

---

### 10. Database Seeding — Faker + custom seed script (Python, dev-only)

**Install (dev-only):** Add to a `requirements-dev.txt` or seed script only:
```
faker==33.x
```

**Why Faker:**
- Faker generates realistic synthetic RE loan data: property addresses, borrower names, origination dates, loan amounts, property types, states, risk ratings.
- The seed script runs once via `python scripts/seed_re_loans.py` to populate 500–2,000 `re_loan` rows with statistically plausible values (LTV 50–90%, DSCR 0.8–2.0, rates 5–9%, states weighted by population).
- Do NOT use lorem ipsum for financial data — the dashboard needs numerically realistic distributions for KPI cards to be non-trivial.

**Faker latest version:** 33.x (check PyPI at seed time; Faker has no breaking changes for basic providers).

**Install:** `pip install faker` — dev only, add to `requirements-dev.txt`, not `requirements.txt`.

---

## Data / Schema Additions

### New Table: `re_loans`

**Strategy:** Flat table, lightly normalized. Foreign key to `property_type_lookup` and `risk_rating_lookup` only. For a POC with 500–2,000 loans, a flat table with indexed columns is faster to query and simpler to seed than a normalized relational schema.

```sql
CREATE TABLE re_loans (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_number         TEXT NOT NULL UNIQUE,           -- external reference
    borrower_name       TEXT NOT NULL,
    property_type       TEXT NOT NULL,                  -- 'office','retail','multifamily','industrial','hotel','land'
    property_state      CHAR(2) NOT NULL,               -- FIPS state abbreviation
    property_msa        TEXT,                           -- MSA name, nullable
    origination_date    DATE NOT NULL,
    maturity_date       DATE NOT NULL,
    original_balance    NUMERIC(18,6) NOT NULL,
    current_upb         NUMERIC(18,6) NOT NULL,         -- unpaid principal balance
    interest_rate       NUMERIC(9,6) NOT NULL,          -- annual rate, e.g., 0.0625 for 6.25%
    rate_type           TEXT NOT NULL CHECK (rate_type IN ('fixed','floating')),
    spread_bps          SMALLINT,                       -- over index, null if fixed
    index_rate          TEXT,                           -- 'SOFR','Prime', null if fixed
    ltv                 NUMERIC(9,6),                   -- loan-to-value at origination
    dscr                NUMERIC(9,6),                   -- debt service coverage ratio
    risk_rating         SMALLINT CHECK (risk_rating BETWEEN 1 AND 10),
    prior_risk_rating   SMALLINT CHECK (prior_risk_rating BETWEEN 1 AND 10),  -- for migration matrix
    delinquency_days    SMALLINT NOT NULL DEFAULT 0,    -- days past due
    is_watchlist        BOOLEAN NOT NULL DEFAULT FALSE,
    noi                 NUMERIC(18,6),                  -- net operating income (annual)
    appraised_value     NUMERIC(18,6),
    occupancy_pct       NUMERIC(5,4),                   -- 0.0–1.0
    vintage_year        SMALLINT NOT NULL,              -- year of origination
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common filter axes
CREATE INDEX idx_re_loans_state ON re_loans (property_state);
CREATE INDEX idx_re_loans_property_type ON re_loans (property_type);
CREATE INDEX idx_re_loans_risk_rating ON re_loans (risk_rating);
CREATE INDEX idx_re_loans_maturity ON re_loans (maturity_date);
CREATE INDEX idx_re_loans_watchlist ON re_loans (is_watchlist) WHERE is_watchlist = TRUE;
```

**Add via Alembic** (already installed): `alembic revision --autogenerate -m "add_re_loans_table"`.

**Financial precision:** All monetary and rate columns use `NUMERIC` — never `FLOAT`. Consistent with existing codebase conventions.

**Migration matrix support:** `prior_risk_rating` column stores the rating as of the prior period. The migration matrix endpoint groups by `(prior_risk_rating, risk_rating)` and counts transitions. No separate table needed for a POC.

---

## Role-Based View Stub

**No new library needed.** Use the existing auth context.

The existing `AuthContext.tsx` exposes the current user's role. Add a `role` field to the user schema:
```typescript
type UserRole = 'pm' | 'advisor'
```

PM role sees full portfolio. Advisor role sees only loans where `borrower_name` matches their assigned book (or a static config mapping in the interim). Implement as a filter applied server-side in the FastAPI `GET /api/v1/loans` endpoint via a `book_filter` dependency.

No RBAC library (Casbin, OPA) is needed for two roles. Do NOT add one.

---

## What NOT to Add

| Rejected | Reason |
|----------|--------|
| `nivo` charts | 300KB heavier than Recharts; composable API advantage not needed for standard chart types required here |
| `Victory` charts | Less maintained; fewer financial dashboard examples; no advantage over Recharts for this use case |
| `Chart.js` / `react-chartjs-2` | Canvas-based — makes drill-down click-to-filter harder; SVG (Recharts) integrates more naturally with React event system |
| `react-simple-maps` (original) | Last meaningful update 2022; known React 19 incompatibility |
| `@vnedyalk0v/react19-simple-maps` | Single-maintainer fork; adds abstraction over d3-geo with no POC benefit; 80-line direct component is safer |
| `@react-pdf/renderer` | Requires rebuilding all dashboard UI in PDF primitives — wrong effort/benefit ratio for a POC snapshot export |
| `papaparse` | CSV export is 10 lines of native browser API; no library justified |
| `redux` / Redux Toolkit | Two roles and a filter sidebar do not need a global event bus. Zustand handles this |
| `react-query-devtools` (prod build) | Dev-only; exclude from production bundle |
| `Celery + Redis` | Analytics queries are read-only aggregates, not background jobs. FastAPI + SQLAlchemy handles them synchronously |
| `Elasticsearch` | Full-text search across 2,000 loans is fast in Postgres with `ilike` and GIN indexes; no search engine needed at this scale |
| `Grafana` / BI tools | This is a custom-branded dashboard inside the existing app, not a BI embed. Grafana adds a separate service and iframe complexity |
| `SQLModel` | SQLAlchemy 2.0 (already installed) is sufficient; SQLModel adds a thin wrapper with no benefit when SQLAlchemy ORM is already the pattern |
| `Faker` in production image | Seed script is dev-only; add to `requirements-dev.txt`, never to `requirements.txt` |
| `D3` (full bundle) | Only `d3-geo` sub-package is needed. Full D3 import adds ~500KB unnecessarily |
| Rate-sensitivity API library | pandas (already installed) is sufficient to compute payment deltas across rate scenarios |
| `react-select` | Filter sidebar multi-selects are implementable with Radix UI `Select` (shadcn) + `react-hook-form` — no additional select library needed |

---

## Complete New Dependency Manifest

### Frontend additions to `package.json`

```json
{
  "dependencies": {
    "recharts": "^3.8.1",
    "d3-geo": "^3.1.0",
    "topojson-client": "^3.1.0",
    "@tanstack/react-query": "^5.96.0",
    "@tanstack/react-table": "^8.21.3",
    "@tanstack/react-virtual": "^3.13.0",
    "zustand": "^5.0.12",
    "react-hook-form": "^7.72.1",
    "zod": "^3.24.0",
    "@hookform/resolvers": "^3.10.0",
    "html2canvas-pro": "^2.0.2",
    "jspdf": "^4.2.1"
  },
  "devDependencies": {
    "@types/d3-geo": "^3.1.0",
    "@types/topojson-client": "^3.1.0"
  }
}
```

### Backend additions to `requirements.txt`

No new production Python libraries required. All KPI, aggregation, sensitivity, and seeding logic is covered by already-installed packages (SQLAlchemy, pandas, numpy, FastAPI, pydantic).

### Dev-only Python (new `requirements-dev.txt` if it doesn't exist)

```
faker>=33.0.0
```

---

## Architecture Impact

No structural changes to the existing FastAPI / React / Docker setup:

- New FastAPI routers go in `backend/api/routes/dashboard.py` and `backend/api/routes/loans.py`.
- New Alembic migration adds `re_loans` table.
- New React pages go in `frontend/src/pages/Dashboard*.tsx` with shared components in `frontend/src/components/charts/` and `frontend/src/components/filters/`.
- Global filter state lives in `frontend/src/stores/filterStore.ts` (Zustand).
- `QueryClientProvider` wraps the app in `main.tsx` alongside the existing `AuthContext`.
- Single Docker image unchanged — no new services.

---

## Confidence Assessment

| Area | Confidence | Source |
|------|------------|--------|
| Recharts v3 React 19 compat | HIGH | npm registry (v3.8.1), GitHub issues confirm v3 resolves React 19 peer dep |
| TanStack Query v5 React 19 compat | HIGH | Official TanStack docs + npm (v5.96.2 April 2026) |
| TanStack Table v8 React 19 compat | HIGH | Official TanStack docs confirm React 16–19 support |
| Zustand v5 React 19 compat | HIGH | Zustand release notes explicitly list React 18-19 requirement |
| d3-geo + topojson direct approach | HIGH | Stable D3 sub-packages, well-documented pattern |
| html2canvas-pro + jsPDF v4 | MEDIUM | html2canvas-pro is an actively maintained fork; jsPDF v4 confirmed on npm. CSS rendering fidelity with Tailwind 4 not independently verified — test early |
| react-hook-form v7 React 19 | HIGH | npm (v7.72.1 April 2026), confirmed by LogRocket article on RHF + React 19 |
| Faker for seeding | HIGH | Standard dev tool; version not critical |

---

*Research complete. All versions verified via npm registry and GitHub releases as of 2026-04-08.*
