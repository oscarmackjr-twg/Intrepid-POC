# Research Summary: v2.0 RE Loan Dashboard POC

**Synthesized:** 2026-04-08
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md, PROJECT.md
**Confidence:** HIGH -- all four research files are grounded in direct codebase analysis and verified library documentation.

---

## Executive Summary

The v2.0 milestone adds a comprehensive CRE loan portfolio dashboard to the existing React 19 + FastAPI + PostgreSQL platform. The existing stack is well-suited and requires only frontend library additions -- no new backend packages, no new services, no infrastructure changes. The recommended approach is a new `re_loans` flat table (separate from the existing `loan_facts` pipeline artifact table), server-side SQL aggregations for KPIs, pandas for histogram binning, and a Zustand-based global filter store synchronized with URL query params. The entire feature ships inside the existing single ECS container.

The highest-risk element is the seed schema -- every downstream feature depends on it being correct before any API or UI code is written. `NUMERIC(18,6)` for all monetary and rate columns is non-negotiable per PROJECT.md constraints, and two time-period snapshots must be seeded to enable the risk rating migration matrix. The second-highest-risk element is the global filter architecture: it must be built before any chart component, because retrofitting filter propagation across 9 dashboard sections causes full rewrites.

The geo heatmap and PDF export both carry known complexity traps. Both have documented fallback options (ranked bar chart for geo; single-page rasterized capture for PDF) that preserve demo value without the implementation risk. The POC scope is well-defined -- stub markers for live data feeds, application-layer role scoping (not Postgres RLS), and html2canvas-pro for PDF are all explicitly right-sized decisions for a POC, not shortcuts that create production rewrites.

---

## Stack Additions

Frontend only. No new backend packages in `requirements.txt`.

| Library | Version | Purpose |
|---------|---------|---------|
| `recharts` | `^3.8.1` | All charts: pie/donut, bar, line, histogram, waterfall. React 19 compatible in v3 (peer dep issue fixed). |
| `d3-geo` + `topojson-client` | `^3.1.0` | US state choropleth via direct D3 sub-packages. Avoids wrapper library dependency risk. |
| `@tanstack/react-query` | `^5.96.0` | Server state with query-key-based cache invalidation on filter change. |
| `@tanstack/react-table` | `^8.21.3` | Watchlist, top-10 exposures, pipeline tables. Headless, Tailwind-styled. |
| `@tanstack/react-virtual` | `^3.13.0` | Row virtualization for the watchlist when row counts grow. |
| `zustand` | `^5.0.12` | Global filter store. Scoped to dashboard only, never imported in App.tsx or main.tsx. |
| `react-hook-form` + `zod` + `@hookform/resolvers` | `^7.72.1` / `^3.24.0` / `^3.10.0` | Filter sidebar form validation. |
| `html2canvas-pro` + `jspdf` | `^2.0.2` / `^4.2.1` | Client-side PDF snapshot export. Rasterized output, acceptable for POC. |
| `@types/d3-geo` + `@types/topojson-client` | devDependencies | TypeScript types for the geo map. |

**Dev-only Python addition:** `faker>=33.0.0` in a new `requirements-dev.txt` for the seed script. Never in `requirements.txt`.

**Version notes:**
- Recharts v3 resolves the `react-is` peer dependency issue that affected v2.x with React 19. Use v3, not v2.
- TanStack Table v9 is in alpha as of April 2026. Use v8 stable.
- jsPDF v4.0 fixed a path traversal CVE. Use v4.x, not v3.x.
- `react-simple-maps` (original) has known React 19 incompatibility. Use direct `d3-geo` instead.
- Do not add the full `d3` bundle. Only the `d3-geo` sub-package is needed.

**CSV export:** Native browser Blob API, no library. Ten lines of TypeScript per table.

---

## Critical Architecture Decisions

### Data Model: New `re_loans` Table, Not LoanFact Reuse

`LoanFact` is a pipeline processing artifact tied to `pipeline_runs` via FK. RE portfolio loans are standing assets with no `run_id` relationship and require fields (`dscr`, `noi`, `appraised_value`, `msa`, `maturity_date`, `risk_rating`, `delinquency_status`) that do not exist in `LoanFact`. Adding them pollutes the consumer loan model. Create a separate `re_loans` table via Alembic migration.

All monetary columns: `NUMERIC(18,6)`. All rate columns: `NUMERIC(10,6)`. Use `asdecimal=True` on SQLAlchemy `Numeric` columns so the ORM returns `decimal.Decimal`, not Python `float`. The seed script must wrap all numeric literals: `Decimal("0.0625")` -- never Python float literals for financial fields.

Include `as_of_date` (indexed) for snapshot semantics, and `prior_risk_rating` alongside `risk_rating` to support the migration matrix without a separate status-history table.

### Aggregation Strategy: SQL for KPIs, pandas for Histograms

| Panel Type | Layer | Rationale |
|-----------|-------|-----------|
| KPI cards (WAC, WAM, WA-LTV, WA-DSCR, total UPB, loan count) | SQL via SQLAlchemy `func.sum()` | Pure reduction -- no row data needed in Python |
| Concentration by property type, state | SQL GROUP BY | Natural DB aggregation |
| Maturity profile, delinquency buckets | SQL GROUP BY | Natural DB aggregation |
| LTV / DSCR / loan-size histograms | pandas `cut()` on single-column fetch | Bin boundaries are application logic, cleaner in pandas than CASE chains |
| P&I / NOI cashflow trends | pandas time-series reshape | Multi-series joins are clearer in pandas |
| Paginated loan table | SQL with LIMIT/OFFSET | Standard |

Never send raw loan rows to the frontend for aggregation. Weighted average formulas must use current UPB as the weight variable -- not original balance, not loan count. Document the formula in a comment above every aggregation query.

### Filtering: Server-Side via useSearchParams

All filtering is server-side. The `useReLoanFilters` hook reads and writes URL query params via React Router `useSearchParams`. On filter change, TanStack Query invalidates the affected `queryKey` arrays and re-fetches. The FastAPI `ReLoanFilters` dependency class parses query params and `build_filters()` translates them to SQLAlchemy WHERE clauses.

The advisor scope filter (`sales_team_id`) is injected server-side from the authenticated user JWT -- never passed as a user-facing query param. The `build_filters()` function appends it automatically for `sales_team` role users. This must be correct at build time -- retrofitting enforcement across all aggregation endpoints is a full rewrite.

Filter state is in URL query params (shareable, bookmarkable), backed by Zustand (`useDashboardFilterStore`) for in-memory synchronization. The Zustand store is imported only inside `frontend/src/features/dashboard/` -- never in `App.tsx` or `main.tsx`.

Apply 300-400ms debounce on free-text inputs before triggering API calls. No debounce on checkbox and dropdown filters.

### PDF Export: html2canvas-pro + jsPDF (Client-Side Raster)

`html2canvas-pro` captures the dashboard DOM as a canvas; `jsPDF` embeds it as a bitmap PDF. This is a rasterized image, not vector text -- acceptable and clearly labeled as "Dashboard Snapshot" for POC purposes.

Key implementation requirements to prevent blank-chart captures:
- Set `isAnimationActive={false}` on all Recharts components before capture.
- Add an explicit 500ms delay after triggering export before the canvas capture fires.
- Cap canvas scale at 1.5, not `window.devicePixelRatio`, to prevent memory exhaustion on Retina displays.
- Apply a `pdf-export` CSS class to disable `position: sticky` and `backdrop-filter` before capture.

Note: ARCHITECTURE.md recommends `@react-pdf/renderer`. STACK.md and PITFALLS.md both recommend `html2canvas-pro + jsPDF`. The html2canvas-pro approach is correct for POC -- rebuilding dashboard layouts in react-pdf component model is a multi-week effort.

### Role Scoping Pattern

Map existing roles to dashboard access: `admin` and `analyst` see the full portfolio; `sales_team` sees only loans where `re_loans.sales_team_id` matches their assigned team. No new role types, no RBAC library, no Postgres RLS. Add `sales_team_id` FK to `re_loans` (nullable). The `build_filters()` function enforces scope at the API layer for every endpoint.

Audit the existing JWT payload before implementation to confirm whether `sales_team_id` is already in the token claims. If not, add it as a backward-compatible addition (null for PM/analyst users).

### API Router

New `APIRouter` at prefix `/api/re` registered in `backend/api/main.py` before the SPA catch-all fallback. No collision with existing prefixes (`/api`, `/api/files`, `/api/cashflow`, `/auth`). New frontend routes use the `/re-dashboard` prefix to avoid conflict with the existing `/dashboard` ops page.

---

## Feature Build Order (Critical Path)

```
Phase 1 -- Seed Schema Design
  GATE: schema locked before any code is written

Phase 2 -- Alembic Migration + Seed Script
  GATE: SELECT COUNT(*), SUM(upb) FROM re_loans returns data

Phase 3 -- Core API (re_dashboard.py router)
  Endpoints: /api/re/kpis, /api/re/concentration, /api/re/distributions
             /api/re/loans (paginated), /api/re/loans/{id}
             /api/re/cashflow-performance, /api/re/origination-pipeline
             /api/re/market-context (static stub)
  GATE: all endpoints return correct data via Swagger UI with and without filter params

Phase 4 -- Filter Hook + Types (frontend)
  useReLoanFilters hook, TypeScript response types, REFilterSidebar component
  GATE: filter sidebar updates URL params; TanStack Query keys change on filter change

Phase 5 -- Dashboard Pages
  Build order within this phase:
    1. Executive Summary (KPI cards first, charts second)
    2. Portfolio Composition (donut, geo map with 3-day timebox, top-10 table)
    3. Credit Quality (LTV/DSCR histograms, watchlist table, migration matrix)
    4. Cash Flow and Performance (P&I chart, yield stub row)
    5. Origination Pipeline (volume bar, funnel, vintage)
    6. Market Context stub panel (no dependencies, can be built anytime after Phase 3)

Phase 6 -- Loan Detail Side-Panel
  Read-only display. No edit capability, no deep-link URL.

Phase 7 -- Export
  CSV: add per table as each table is built. No library needed.
  PDF: build last, after all sections exist and are stable.

Phase 8 -- Role Scope Validation
  Seed two users, assign loan subsets, verify API-level enforcement.
```

**Dependency rationale:**
- Seed schema first: a wrong schema means all subsequent phases get re-done.
- Filter hook before charts: chart components call `useReLoanFilters()` directly. Building charts first means full rewrites when the hook is introduced.
- Market context stub has zero dependencies. Can be built as an early confidence win in parallel with other sections.
- PDF export depends on all sections being stable and charts being in their final render state. Always last.

---

## Top Pitfalls to Avoid

**1. Float in any monetary or rate column (Critical, Phase 1)**
Use `NUMERIC(18,6)` for all monetary fields and `NUMERIC(10,6)` for all rate fields in the Alembic migration. Use `Numeric(18, 6, asdecimal=True)` in SQLAlchemy models. The seed script must use `Decimal("0.0625")`, never Python float literals. There is no fix-later option -- retrofitting column types after seeding requires a migration and a full data recast.

**2. Wrong WAC/WAM weighting formula (Critical, Phase 2)**
WAC = `SUM(current_upb * coupon_rate) / NULLIF(SUM(current_upb), 0)`. Not `AVG(coupon_rate)`. Weight every portfolio metric by current UPB, not original balance or loan count. Document the formula in a comment above every query before writing it. Finance stakeholders will catch a 30-basis-point WAC error during the first demo.

**3. Alembic migration conflicts with existing history (Critical, Phase 1)**
Run `alembic heads` before creating the `re_loans` migration. Chain the new revision off the current main-branch head. All new tables use the `re_` prefix. No `ALTER TABLE` on any existing table. Add `alembic upgrade head` to CI before the dashboard branch merges.

**4. Role filter enforced only in the frontend (Critical, Phase 2)**
The `sales_team_id` scope filter must be applied server-side in `build_filters()` for every `/api/re/*` endpoint, derived from the authenticated JWT. A user calling the API directly must not be able to see out-of-scope loans. This must be correct from the first endpoint -- retrofitting enforcement across all aggregation endpoints is a full rewrite.

**5. Building chart components before the filter hook exists (High, Phase 4)**
Every chart component passes the filter object as part of its TanStack Query key. Building charts before the filter hook exists means every component needs rewriting when the hook is introduced. The filter hook is a build-first dependency.

**6. Division by zero on empty filter subsets (High, Phase 2)**
Wrap every SQL division with `NULLIF(SUM(upb), 0)`. Every KPI card must have three distinct render states: loading, no-data (zero loans match the active filters), and error. Test filter combinations that produce zero results before each dashboard phase is declared complete.

**7. Geo heatmap complexity underestimation (High, Phase 5)**
The US state choropleth requires TopoJSON loading, D3 Albers USA projection, color scale normalization, hover tooltips, and click-to-filter integration. Time-box to 3 days. If over budget, ship a "Top States by UPB" ranked bar chart instead -- same data, same API endpoint, no TopoJSON or projection code required.

**8. Blank charts in PDF export due to render timing (High, Phase 7)**
`html2canvas` fires before Recharts SVG animations complete. Fix: disable chart animations (`isAnimationActive={false}`) before capture, add 500ms delay before canvas capture, cap canvas scale at 1.5. Test with the full populated dashboard, not a single chart in isolation, before declaring the export feature complete.

---

## Open Questions for Roadmap

These must be confirmed in Phase 1 planning. None block starting the seed schema design, but all affect scope estimates for later phases.

1. **Cashflow time-series seed design.** The P&I actual vs projected chart and CPR tracking require monthly cashflow records per loan -- a separate time-series table, not one row per loan. Does the roadmap include building a `re_loan_cashflows` seed table, or is the P&I chart a stub with a single aggregate data point? This is the biggest scope decision after the core `re_loans` schema.

2. **Risk rating migration matrix scope.** Seeding two time-period snapshots adds meaningful complexity to the seed script. If the migration matrix is a differentiator rather than table stakes, the seed can start simpler with `prior_risk_rating` as a single column on `re_loans` rather than a full status-history table. Confirm before writing the seed script.

3. **As-of date semantics.** Define precisely before writing any aggregation query: "current portfolio snapshot" (single point in time, no time-travel) vs true temporal filtering (`valid_from`/`valid_to` per loan status). The POC should use the simpler single-snapshot approach. Changing this afterward requires reseeding.

4. **Geo heatmap vs bar chart fallback.** Should the phase plan explicitly budget both options and define the 3-day decision trigger? Confirming upfront prevents the geo map from becoming an open-ended time sink during Phase 5.

5. **`sales_team_id` in existing JWTs.** Does the current JWT payload include `sales_team_id`? If not, adding it is a one-time backward-compatible change to the auth module that must happen before Phase 8. Confirm via a quick audit of `backend/auth/routes.py`.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (library choices and versions) | HIGH | All versions verified on npm registry as of 2026-04-08. React 19 compat confirmed for all choices. |
| Features (what to build, what to defer) | HIGH | Feature categorization grounded in CRE domain conventions and established UX patterns. |
| Architecture (data model, aggregation, routing) | HIGH | Grounded in direct codebase analysis of actual project files. No assumptions about the stack. |
| Pitfalls (severity and prevention) | HIGH | Financial calculation pitfalls cite industry conventions. Integration pitfalls based on actual codebase structure. |
| PDF export fidelity (html2canvas-pro + Tailwind 4) | MEDIUM | Not independently verified. Test early in Phase 7 with a fully populated dashboard. |
| Cashflow seed complexity | MEDIUM | P&I and CPR features depend on a monthly cashflow time-series table whose scope needs confirmation in Phase 1 planning. |