# Phase 21: Portfolio Composition Page — Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the Portfolio Composition page at `/re-dashboard/portfolio` — six panels: property type pie/donut chart, top-states horizontal bar chart (geo fallback), loan size histogram, maturity profile stacked bar, top-10 exposures table, and concentration limit progress bars. All panels use Recharts, consume `/api/re/concentration`, `/api/re/distributions`, and `/api/re/maturity-profile` via TanStack Query, and wire click-to-filter via `useReLoanFilters`.

**Phase 21 also retrofits the RE dashboard routing:** `ReDashboard.tsx` becomes a shell with a tab strip and `<Outlet />`. The existing KPI cards move into `ReExecutiveSummaryPage.tsx` at the `/re-dashboard` index route. Portfolio content lives at `/re-dashboard/portfolio`.

Phase gate (from ROADMAP.md):
1. Portfolio Composition page shows pie/donut, loan size histogram, and maturity profile stacked bar — all populated from seeded data
2. Geographic view shows a ranked bar chart of top states by UPB — populated from seeded data
3. Top-10 exposures table shows 10 largest loans by UPB with LTV, DSCR, property type, and location
4. Clicking a pie slice or histogram bar applies that dimension as a filter — confirmed by URL param change and updated KPI cards
5. Concentration limit indicators are visible and show proximity to policy limits

</domain>

<decisions>
## Implementation Decisions

### Chart Library
- **D-01:** Install **Recharts** (`recharts` npm package) in Phase 21. This is the first chart phase — Recharts is the standard chart library for Phases 21–24. Do NOT install Nivo, Victory, Chart.js, or any other chart library.
- **D-02:** All charts use `ResponsiveContainer` wrapper from Recharts so they fill their grid cell width.

### Geographic View (COMP-02)
- **D-03:** Implement the **ranked horizontal bar chart** of top states by UPB — not a choropleth map. No mapping libraries (react-simple-maps, Leaflet, D3 geo) are needed or wanted.
- **D-04:** Data source: `ConcentrationResponse.state[]` (already typed in `re.ts`). Show top 10 states by `total_upb`, sorted descending. Use a Recharts `BarChart` with `layout="vertical"`.
- **D-05:** Clicking a state bar sets `state` filter via `setFilter('state', category)`. Same click-to-filter pattern as other charts.

### RE Dashboard Routing Refactor
- **D-06:** `ReDashboard.tsx` becomes a **layout shell**: renders the page header, the tab strip, `<ReDashboardFilterSidebar />`, and a `<Outlet />` (React Router v6). The three-column layout (nav | charts+tabs | filter sidebar) is preserved.
- **D-07:** Tab strip items and their routes:
  - `Executive Summary` → `/re-dashboard` (index route)
  - `Portfolio` → `/re-dashboard/portfolio`
  - `Credit Quality` → `/re-dashboard/credit` (stub, Phase 22)
  - `Cash Flow` → `/re-dashboard/cashflow` (stub, Phase 23)
  - `Origination` → `/re-dashboard/origination` (stub, Phase 24)
  Stub routes for Phases 22–24 render a placeholder `<p>Coming in a future phase.</p>` — no empty crashes.
- **D-08:** The existing KPI cards content from `ReDashboard.tsx` moves into a new file `frontend/src/pages/ReExecutiveSummaryPage.tsx`. This is a refactor of existing Phase 20 code, not a rewrite — logic and markup are preserved exactly.
- **D-09:** `App.tsx` nesting: `/re-dashboard` becomes a parent route with `ReDashboard` as the layout element. Child routes: `index` → `ReExecutiveSummaryPage`, `portfolio` → `RePortfolioPage`, `credit/cashflow/origination` → stubs.

### Page Layout (RePortfolioPage)
- **D-10:** Two-column CSS grid (`grid-cols-2 gap-6`) for the chart panels within the `<Outlet />` area. On narrow viewports, falls back to single column (`grid-cols-1`). Each panel is a card (white bg, `rounded-lg border border-gray-200 p-4`).
- **D-11:** Panel order (top-to-bottom, left-to-right):
  1. Property Type (pie/donut) — top-left
  2. Top States by UPB (horizontal bar) — top-right
  3. Loan Size Distribution (histogram) — middle-left
  4. Maturity Profile (stacked bar) — middle-right
  5. Top-10 Exposures table — full width (spans both columns)
  6. Concentration Limits — full width (spans both columns)

### Charts
- **D-12:** **Property type pie/donut:** Recharts `PieChart` + `Pie` with `innerRadius` set (donut style). Data from `ConcentrationResponse.property_type[]`. `dataKey="total_upb"`, `nameKey="category"`. Click a slice → `setFilter('property_type', category)`. TWG navy palette for segment colors.
- **D-13:** **Loan size histogram:** Recharts `BarChart`. Data from `DistributionsResponse.loan_size_distribution[]`. `dataKey="loan_count"` on Y-axis. Click a bar → `setFilter` not applicable (no direct loan_size_bucket filter exists) — bars are display-only. Note: `loan_size_min`/`loan_size_max` filters exist but histogram buckets don't map cleanly — Claude's Discretion on whether to wire or display-only.
- **D-14:** **Maturity profile stacked bar:** Recharts `BarChart` with `stackId`. Data from `MaturityProfileResponse.periods[]`. X-axis: `${year} Q${quarter}`. One stack per property type if available, otherwise a single `total_upb` stack. Click-to-filter not required for this chart.
- **D-15:** All chart tooltips use Recharts default `<Tooltip />` — no custom tooltip component needed.

### Top-10 Exposures Table (COMP-05)
- **D-16:** Data from `ConcentrationResponse.top_10_exposures[]` (already typed as `TopExposure[]` in `re.ts`). Fixed 10 rows — no pagination, no sorting controls.
- **D-17:** Columns: Loan #, Borrower, UPB, LTV, DSCR, Property Type, State. UPB formatted with `formatUPB` (reuse from Phase 20). LTV/DSCR formatted with existing formatters.
- **D-18:** Row click: **no action in Phase 21.** Phase 25 adds the loan detail side-panel. Add a `TODO: Phase 25 — wire row click to loan detail side-panel` comment on the `<tr onClick>` stub.

### Concentration Limit Indicators (COMP-06)
- **D-19:** Visual style: **horizontal progress bars**. Bar fills from 0% to 100% of the policy limit. Bar color by proximity: green (`bg-green-500`) when < 70% of limit, yellow (`bg-yellow-400`) when 70–90% of limit, red (`bg-red-500`) when ≥ 90% of limit.
- **D-20:** Data from `ConcentrationResponse.concentration_limits[]` (typed as `ConcentrationLimit[]` in `re.ts`). The `proximity` field (0–1 float) drives bar width and color. Display: category name, `{(current_pct * 100).toFixed(1)}%` current, `limit_pct` label.
- **D-21:** Progress bar is a plain Tailwind div: outer `w-full bg-gray-200 rounded h-2`, inner `h-2 rounded` with dynamic `width` inline style (`${proximity * 100}%`) and color class.

### Data Fetching
- **D-22:** Three TanStack Query calls in `RePortfolioPage`:
  - `useQuery({ queryKey: ['re-concentration', filters], queryFn: ... })` → `/api/re/concentration`
  - `useQuery({ queryKey: ['re-distributions', filters], queryFn: ... })` → `/api/re/distributions`
  - `useQuery({ queryKey: ['re-maturity-profile', filters], queryFn: ... })` → `/api/re/maturity-profile`
  Where `filters` comes from `useReLoanFilters().filters` (same pattern as Phase 20).
- **D-23:** Loading state per panel: show `animate-pulse` skeleton block of same card dimensions — same pattern as Phase 20 KPI cards.
- **D-24:** No-data state per panel: when `isLoading` is false and data is empty/null, show muted text `—` or `No data` centered in the card area.

### Styling
- **D-25:** Follow TWG Global brand: `#1a3868` navy for headings, `#475569` slate for labels, `#94a3b8` muted, `#f8fafc` background. Panel card: `bg-white rounded-lg border border-gray-200 p-4`. Raw Tailwind only — no component library.
- **D-26:** Tab strip: active tab has `border-b-2 border-[#1a3868] text-[#1a3868]`, inactive has `text-[#475569] hover:text-[#1a3868]`. Uses React Router `<NavLink>` with `end` prop for the index tab.

### Claude's Discretion
- Component file names and paths (suggestion: `frontend/src/pages/RePortfolioPage.tsx`, `frontend/src/components/re/ConcentrationLimits.tsx`, `frontend/src/components/re/TopExposuresTable.tsx`)
- Whether to create a `useConcentration()` / `useDistributions()` / `useMaturityProfile()` custom hooks or call `useQuery` directly in `RePortfolioPage`
- Exact color palette for pie chart slices (follow existing TWG Global brand, suggest: `#1a3868`, `#2563eb`, `#0ea5e9`, `#7c3aed`, `#db2777`)
- Whether to extract a shared `ChartCard` wrapper component for the panel card styling (reasonable if 4+ panels share it)
- Error state handling for chart fetches — Claude's choice on whether to show an error card or log silently

</decisions>

<specifics>
## Specific Details

- Recharts install: `npm install recharts` (no `@types/recharts` needed — Recharts ships its own types)
- `ConcentrationResponse`, `DistributionsResponse`, `MaturityProfileResponse`, `TopExposure`, `ConcentrationLimit` types are **already defined** in `frontend/src/types/re.ts` — do NOT redefine them.
- `useReLoanFilters().setFilter` is the mechanism for click-to-filter. Calling `setFilter('property_type', 'Multifamily')` updates the URL param and Zustand store, which changes the TQ query key, which triggers automatic refetch of all panels.
- Phase 21 is responsible for the routing refactor (D-06 through D-09). Planner must include tasks to move KPI card logic into `ReExecutiveSummaryPage.tsx` and refactor `ReDashboard.tsx` into a shell — this is not optional.
- `formatUPB`, `formatRate`, `formatDSCR`, `formatCount` are already in `frontend/src/utils/formatKpi.ts` — reuse them in the top-10 table.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §COMP — COMP-01 through COMP-06 (all Portfolio Composition requirements)
- `.planning/REQUIREMENTS.md` §UX — UX-01 (click-to-filter)

### Prior Phase Decisions
- `.planning/phases/20-executive-summary-page/20-CONTEXT.md` — D-04 (TanStack Query installed), D-07 (skeleton loading), D-08/D-09 (no-data detection), D-13 through D-18 (number formatting utils)
- `.planning/phases/19-filter-hook-typescript-foundation/19-CONTEXT.md` — D-07/D-08/D-09 (URL-as-source-of-truth, `filters` as TQ query key), D-05 (raw Tailwind only)
- `.planning/phases/10-revamp-user-interface-phase-10/10-CONTEXT.md` — Brand colors and UI conventions

### Existing Frontend Code (read before modifying)
- `frontend/src/pages/ReDashboard.tsx` — MUST be refactored into layout shell (D-06). Read before touching.
- `frontend/src/types/re.ts` — All RE TypeScript types; `ConcentrationResponse`, `DistributionsResponse`, `MaturityProfileResponse` already defined here
- `frontend/src/hooks/useReLoanFilters.ts` — `useReLoanFilters()` hook; `filters` object and `setFilter` function
- `frontend/src/components/re/KPICard.tsx` — Reference component for card styling and skeleton loading pattern
- `frontend/src/utils/formatKpi.ts` — Existing formatters to reuse in top-10 table
- `frontend/src/App.tsx` — Route definitions; nested routes for RE dashboard added here

### Backend API
- `backend/api/re_routes.py` — `/api/re/concentration`, `/api/re/distributions`, `/api/re/maturity-profile` endpoints
- `backend/api/re_schemas.py` — Pydantic response models (source of truth for field names/types)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useReLoanFilters()` — Returns `{ filters, setFilter, clearFilters }`. `filters` is the TQ query key.
- All TypeScript response types for Phase 21 endpoints already exist in `frontend/src/types/re.ts`.
- `formatUPB`, `formatRate`, `formatDSCR`, `formatCount` in `frontend/src/utils/formatKpi.ts` — use in top-10 table.
- `KPICard.tsx` skeleton loading pattern (`animate-pulse` div) — replicate for chart panel loading states.
- `ReDashboardFilterSidebar.tsx` — Already renders in `ReDashboard.tsx`; stays in the shell after refactor.

### Established Patterns
- Auth: `const { user } = useAuth()` if role-checking needed
- Tailwind: inline string classes, no className helpers, no component library
- No index.ts barrel files — import directly from file path
- Axios for API calls inside `useQuery` (same as Phase 20)

### Integration Points
- `frontend/src/App.tsx` — Replace flat `/re-dashboard` route with nested route structure (D-09)
- `frontend/src/pages/ReDashboard.tsx` — Refactor into shell; move KPI content to `ReExecutiveSummaryPage.tsx`
- `frontend/src/components/re/` — New chart components go here

### Not Yet Present (Phase 21 creates)
- No `recharts` in `package.json`
- No `RePortfolioPage.tsx`
- No `ReExecutiveSummaryPage.tsx` (KPI cards currently inline in `ReDashboard.tsx`)
- No tab strip component
- No nested RE dashboard routes in `App.tsx`

</code_context>

---

*Phase: 21-portfolio-composition-page*
*Context gathered: 2026-04-08 via /gsd-discuss-phase*
