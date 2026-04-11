# Phase 21: Portfolio Composition Page — Research

**Researched:** 2026-04-08
**Domain:** Recharts, React Router v6 nested routes, TanStack Query parallel fetching
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Install `recharts` npm package in Phase 21. No Nivo, Victory, Chart.js, or any other chart library.
- **D-02:** All charts use `ResponsiveContainer` wrapper so they fill their grid cell width.
- **D-03:** Geographic view is a ranked horizontal bar chart — no choropleth, no mapping libraries.
- **D-04:** State bar data from `ConcentrationResponse.state[]`, top 10 by `total_upb` descending, `layout="vertical"` BarChart.
- **D-05:** State bar click calls `setFilter('state', category)`.
- **D-06:** `ReDashboard.tsx` becomes a layout shell with page header, tab strip, `<ReDashboardFilterSidebar />`, and `<Outlet />`.
- **D-07:** Tab strip routes: Executive Summary → `/re-dashboard` (index), Portfolio → `/re-dashboard/portfolio`, Credit → `/re-dashboard/credit` (stub), Cash Flow → `/re-dashboard/cashflow` (stub), Origination → `/re-dashboard/origination` (stub). Stubs render `<p>Coming in a future phase.</p>`.
- **D-08:** KPI cards from `ReDashboard.tsx` move into new `ReExecutiveSummaryPage.tsx` — logic and markup preserved exactly.
- **D-09:** `App.tsx` nesting: `/re-dashboard` is parent route with `ReDashboard` as layout element. Children: `index` → `ReExecutiveSummaryPage`, `portfolio` → `RePortfolioPage`, stubs for credit/cashflow/origination.
- **D-10:** Two-column CSS grid (`grid-cols-2 gap-6`) for chart panels; single column on narrow (`grid-cols-1`). Panel card: `bg-white rounded-lg border border-gray-200 p-4`.
- **D-11:** Panel order: (1) Property Type pie (top-left), (2) Top States bar (top-right), (3) Loan Size histogram (middle-left), (4) Maturity Profile stacked bar (middle-right), (5) Top-10 Exposures table (full-width), (6) Concentration Limits (full-width).
- **D-12:** Property type donut: `PieChart` + `Pie` with `innerRadius`. Data from `ConcentrationResponse.property_type[]`. `dataKey="total_upb"`, `nameKey="category"`. Slice click → `setFilter('property_type', category)`.
- **D-13:** Loan size histogram: `BarChart`, data from `DistributionsResponse.loan_size_distribution[]`, `dataKey="loan_count"`. Display-only — no click-to-filter (buckets don't map cleanly to loan_size_min/max).
- **D-14:** Maturity profile stacked bar: `BarChart` with `stackId`. Data from `MaturityProfileResponse.periods[]`. X-axis: `${year} Q${quarter}`. Click-to-filter not required.
- **D-15:** All chart tooltips use Recharts default `<Tooltip />`.
- **D-16:** Top-10 table from `ConcentrationResponse.top_10_exposures[]`. Fixed 10 rows, no pagination, no sorting.
- **D-17:** Table columns: Loan #, Borrower, UPB, LTV, DSCR, Property Type, State. Reuse `formatUPB`, `formatRate`, `formatDSCR`.
- **D-18:** Row click: no action in Phase 21. Add `TODO: Phase 25 — wire row click to loan detail side-panel` comment on `<tr onClick>` stub.
- **D-19:** Concentration limits: horizontal progress bars. Green < 70%, yellow 70–90%, red ≥ 90% of policy limit. Classes: `bg-green-500`, `bg-yellow-400`, `bg-red-500`.
- **D-20:** Concentration data from `ConcentrationResponse.concentration_limits[]`. `proximity` field (0–1 float) drives bar width and color.
- **D-21:** Progress bar: outer `w-full bg-gray-200 rounded h-2`, inner `h-2 rounded` with inline `width: ${proximity * 100}%` and dynamic color class.
- **D-22:** Three TanStack Query calls in `RePortfolioPage`: `['re-concentration', filters]`, `['re-distributions', filters]`, `['re-maturity-profile', filters]`.
- **D-23:** Loading: `animate-pulse` skeleton block same card dimensions — same pattern as Phase 20.
- **D-24:** No-data: when `isLoading` false and data empty/null, show muted `—` or `No data` centered.
- **D-25:** TWG Global brand: `#1a3868` navy headings, `#475569` slate labels, `#94a3b8` muted, `#f8fafc` background. Raw Tailwind only — no component library.
- **D-26:** Tab strip: active tab `border-b-2 border-[#1a3868] text-[#1a3868]`, inactive `text-[#475569] hover:text-[#1a3868]`. Use React Router `<NavLink>` with `end` prop on the index tab.

### Claude's Discretion
- Component file names/paths (suggestion: `RePortfolioPage.tsx`, `ConcentrationLimits.tsx`, `TopExposuresTable.tsx`)
- Whether to use custom hooks or call `useQuery` directly in `RePortfolioPage`
- Exact color palette for pie chart slices
- Whether to extract a shared `ChartCard` wrapper component
- Error state handling for chart fetches

### Deferred Ideas (OUT OF SCOPE)
- Choropleth map / mapping libraries
- Loan detail side-panel row click (Phase 25)
- Export / CSV download
- Mobile/responsive optimization
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMP-01 | Portfolio Composition page shows pie/donut chart of loans by property type | Recharts PieChart + Pie + Cell pattern verified |
| COMP-02 | Geographic view shows ranked bar chart of top states by UPB, click-to-filter | Recharts BarChart layout="vertical" verified; setFilter('state', ...) wiring documented |
| COMP-03 | Loan size histogram | Recharts BarChart standard use; data from DistributionsResponse.loan_size_distribution |
| COMP-04 | Maturity profile stacked bar chart by quarter/year | Recharts BarChart with stackId; data from MaturityProfileResponse.periods |
| COMP-05 | Top-10 exposures table (UPB, LTV, DSCR, property type, location) | HTML table; formatters already exist in formatKpi.ts |
| COMP-06 | Concentration limit indicators with visual proximity | Tailwind div progress bars; data from ConcentrationResponse.concentration_limits |
| UX-01 | Click any chart segment applies that dimension as a filter across dashboard | useReLoanFilters().setFilter() wiring verified; Recharts onClick payload documented |
</phase_requirements>

---

## Summary

Phase 21 is a frontend-only phase. The backend API endpoints (`/api/re/concentration`, `/api/re/distributions`, `/api/re/maturity-profile`) already exist from Phase 18. All TypeScript types are already defined in `frontend/src/types/re.ts`. The only new dependency is `recharts` (latest: 3.8.1). The phase has two distinct tracks: (1) routing refactor — turning `ReDashboard.tsx` into a React Router v6 layout shell with `Outlet` and converting the flat `/re-dashboard` route in `App.tsx` into a nested route tree; (2) building `RePortfolioPage.tsx` with six panels using Recharts components.

The click-to-filter pattern is straightforward: Recharts `Pie` and `Bar` components both accept an `onClick` prop that receives `(data, index)`. The `data` parameter is the raw data entry from the chart's data array — `data.category` for `ConcentrationItem[]`, or whatever fields exist on the data object. Calling `setFilter('property_type', data.category)` updates the URL, which propagates through the existing `useReLoanFilters` → TanStack Query key chain, causing all panel queries to refetch automatically.

The routing refactor is a structural surgery on two files (`App.tsx` and `ReDashboard.tsx`) plus creating `ReExecutiveSummaryPage.tsx` from extracted markup. No logic changes — the KPI card content is lifted verbatim. React Router v6's `NavLink` with the `className` render-prop pattern handles tab active state cleanly, with `end` prop required on the index tab to prevent it staying active on all child routes.

**Primary recommendation:** Implement in three waves — Wave 1: routing refactor + file scaffolding; Wave 2: data fetching and panel layout; Wave 3: individual chart components.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | 3.8.1 | All chart rendering | D-01 locked; ships own TypeScript types |
| react-router-dom | 6.30.3 (installed) | Nested routes, NavLink, Outlet | Already installed; v6 nested route API is stable |
| @tanstack/react-query | 5.96.2 (installed) | Parallel data fetching | Already installed; multiple useQuery pattern |

[VERIFIED: npm registry — `npm view recharts version` returned 3.8.1 on 2026-04-08]
[VERIFIED: package.json — react-router-dom ^6.30.2 in dependencies; node_modules shows 6.30.3 installed]

### Supporting (already installed, no new installs)
| Library | Version | Purpose |
|---------|---------|---------|
| axios | 1.7.7 | HTTP calls inside queryFn |
| zustand | 5.0.12 | Filter store (useReLoanFilters reads it) |
| tailwindcss | 4.1.18 | All styling |

**Recharts peer dependencies:** `react ^16.8+`, `react-dom ^16.0+`, `react-is ^16.8+` — all satisfied by React 19 in this project. [VERIFIED: npm view recharts peerDependencies]

**No `@types/recharts` needed** — Recharts 3.x ships its own TypeScript declarations. [CITED: 21-CONTEXT.md specifics section]

**Installation:**
```bash
cd frontend
npm install recharts
```

**Version verification:**
```bash
npm view recharts version
# Returns: 3.8.1
```

---

## Architecture Patterns

### Recommended Project Structure

After Phase 21:
```
frontend/src/
├── pages/
│   ├── ReDashboard.tsx          # REFACTORED — layout shell (Outlet + tab strip)
│   ├── ReExecutiveSummaryPage.tsx # NEW — extracted KPI cards from ReDashboard
│   └── RePortfolioPage.tsx      # NEW — six-panel portfolio page
├── components/re/
│   ├── KPICard.tsx              # Unchanged
│   ├── ReDashboardFilterSidebar.tsx  # Unchanged
│   ├── ChartCard.tsx            # NEW (if extracted) — shared panel card wrapper
│   ├── TopExposuresTable.tsx    # NEW
│   └── ConcentrationLimits.tsx  # NEW
└── hooks/
    └── useReLoanFilters.ts      # Unchanged
```

### Pattern 1: React Router v6 Nested Routes with Outlet

**What:** Parent route renders layout (header, tabs, sidebar) and an `<Outlet />` where children render.
**When to use:** Dashboard with tabs — each tab is a child route. Shared chrome stays mounted.

**App.tsx change:**
```tsx
// Source: React Router v6 docs — reactrouter.com/docs/en/v6/components/nav-link
import { Routes, Route, Navigate } from 'react-router-dom'
import ReDashboard from './pages/ReDashboard'
import ReExecutiveSummaryPage from './pages/ReExecutiveSummaryPage'
import RePortfolioPage from './pages/RePortfolioPage'

// Replace the flat:
//   <Route path="re-dashboard" element={<ReDashboard />} />
// With:
<Route path="re-dashboard" element={<ReDashboard />}>
  <Route index element={<ReExecutiveSummaryPage />} />
  <Route path="portfolio" element={<RePortfolioPage />} />
  <Route path="credit" element={<p className="text-sm text-[#475569] p-6">Coming in a future phase.</p>} />
  <Route path="cashflow" element={<p className="text-sm text-[#475569] p-6">Coming in a future phase.</p>} />
  <Route path="origination" element={<p className="text-sm text-[#475569] p-6">Coming in a future phase.</p>} />
</Route>
```

**ReDashboard.tsx refactored shell:**
```tsx
// Source: React Router v6 docs
import { Outlet, NavLink } from 'react-router-dom'
import { ReDashboardFilterSidebar } from '../components/re/ReDashboardFilterSidebar'

const TABS = [
  { label: 'Executive Summary', to: '/re-dashboard', end: true },
  { label: 'Portfolio', to: '/re-dashboard/portfolio', end: false },
  { label: 'Credit Quality', to: '/re-dashboard/credit', end: false },
  { label: 'Cash Flow', to: '/re-dashboard/cashflow', end: false },
  { label: 'Origination', to: '/re-dashboard/origination', end: false },
]

export default function ReDashboard() {
  return (
    <div className="flex gap-6 min-h-[calc(100vh-theme(spacing.12))]">
      <div className="flex-1 min-w-0">
        <h1 className="text-2xl font-bold text-[#1a3868] mb-4">RE Portfolio Dashboard</h1>

        {/* Tab strip */}
        <nav className="flex gap-6 border-b border-gray-200 mb-6">
          {TABS.map(({ label, to, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                isActive
                  ? 'pb-2 border-b-2 border-[#1a3868] text-[#1a3868] text-sm font-medium'
                  : 'pb-2 text-[#475569] hover:text-[#1a3868] text-sm font-medium'
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Child route content */}
        <Outlet />
      </div>
      <ReDashboardFilterSidebar />
    </div>
  )
}
```

**Critical:** The `end` prop on the Executive Summary NavLink is REQUIRED. Without it, `/re-dashboard` matches all child paths and the Executive Summary tab stays highlighted on all sub-routes. [VERIFIED: NavLink docs — reactrouter.com]

### Pattern 2: Recharts PieChart / Donut

**What:** `PieChart` container, `Pie` child with `innerRadius` for donut shape, `Cell` per data entry for colors.

```tsx
// Source: recharts.github.io/api/Pie/ + verified component signatures
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import type { ConcentrationItem } from '../../types/re'

const PIE_COLORS = ['#1a3868', '#2563eb', '#0ea5e9', '#7c3aed', '#db2777', '#f59e0b', '#10b981']

interface Props {
  data: ConcentrationItem[]
  onSliceClick: (category: string) => void
}

function PropertyTypePieChart({ data, onSliceClick }: Props) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          dataKey="total_upb"
          nameKey="category"
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          onClick={(data, _index) => {
            // data is the ConcentrationItem entry — data.category is the property type string
            if (data && data.category) onSliceClick(data.category)
          }}
          style={{ cursor: 'pointer' }}
        >
          {data.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(value: number) => formatUPB(value)} />
      </PieChart>
    </ResponsiveContainer>
  )
}
```

**onClick payload:** The `onClick` handler on `<Pie>` receives `(data, index)` where `data` is the raw data entry from the Pie's `data` prop. For `ConcentrationItem[]`, this is `{ category, loan_count, total_upb, pct_of_total }`. [VERIFIED: recharts.github.io/api/Pie/ — "customized event handler of click on the sectors"; confirmed via GitHub issue #5308 which documents the three-arg signature `(data, index, event)`]

### Pattern 3: Recharts BarChart — Vertical Layout (State Chart)

**What:** `layout="vertical"` on `BarChart` swaps axes. `XAxis` becomes `type="number"`, `YAxis` becomes `type="category"` with `dataKey` pointing at the label field.

```tsx
// Source: recharts BarChart docs — layout prop verified
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

// data is ConcentrationItem[] sorted descending by total_upb, sliced to top 10
<ResponsiveContainer width="100%" height={300}>
  <BarChart data={topStates} layout="vertical" margin={{ left: 20, right: 20 }}>
    <XAxis type="number" tickFormatter={(v) => formatUPB(v)} />
    <YAxis type="category" dataKey="category" width={30} />
    <Tooltip formatter={(v: number) => formatUPB(v)} />
    <Bar
      dataKey="total_upb"
      fill="#1a3868"
      onClick={(data, _index) => {
        // data is the ConcentrationItem — data.category is the state abbreviation
        if (data && data.category) onBarClick(data.category)
      }}
      style={{ cursor: 'pointer' }}
    />
  </BarChart>
</ResponsiveContainer>
```

[VERIFIED: recharts.github.io/en-US/api/BarChart/ — `layout` prop accepts `"horizontal" | "vertical"`]

### Pattern 4: Recharts Stacked BarChart (Maturity Profile)

**What:** Multiple `Bar` components sharing the same `stackId` on a `BarChart`. Each Bar is a different data key.

The maturity data (`MaturityPeriod[]`) has `total_upb` but no per-property-type breakdown. D-14 says: "one stack per property type if available, otherwise a single `total_upb` stack." Since `MaturityProfileResponse` only has `total_upb`, this renders as a single-stack bar chart.

```tsx
// Source: recharts Bar docs — stackId prop verified
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts'

// Transform periods: label = `${year} Q${quarter}`
const chartData = periods.map(p => ({
  label: `${p.year} Q${p.quarter}`,
  total_upb: p.total_upb,
  loan_count: p.loan_count,
}))

<ResponsiveContainer width="100%" height={280}>
  <BarChart data={chartData}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="label" tick={{ fontSize: 11 }} />
    <YAxis tickFormatter={(v) => formatUPB(v)} />
    <Tooltip formatter={(v: number) => formatUPB(v)} />
    <Bar dataKey="total_upb" stackId="maturity" fill="#1a3868" />
  </BarChart>
</ResponsiveContainer>
```

[VERIFIED: recharts.github.io/en-US/api/Bar/ — `stackId` prop documented; same stackId on multiple Bars creates stacked chart]

### Pattern 5: Multiple Parallel TanStack Queries

**What:** Three independent `useQuery` calls in the same component. They fire simultaneously on mount — no coordination needed.

```tsx
// Source: tanstack.com/query/v5/docs/framework/react/guides/parallel-queries
import { useQuery } from '@tanstack/react-query'
import { useReLoanFilters } from '../hooks/useReLoanFilters'
import axios from 'axios'

export default function RePortfolioPage() {
  const { filters } = useReLoanFilters()

  // Strip null/empty values (same pattern as useKPIs)
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== null && v !== '')
  )

  const concentrationQuery = useQuery({
    queryKey: ['re-concentration', filters],
    queryFn: async () => {
      const { data } = await axios.get<ConcentrationResponse>('/api/re/concentration', { params })
      return data
    },
  })

  const distributionsQuery = useQuery({
    queryKey: ['re-distributions', filters],
    queryFn: async () => {
      const { data } = await axios.get<DistributionsResponse>('/api/re/distributions', { params })
      return data
    },
  })

  const maturityQuery = useQuery({
    queryKey: ['re-maturity-profile', filters],
    queryFn: async () => {
      const { data } = await axios.get<MaturityProfileResponse>('/api/re/maturity-profile', { params })
      return data
    },
  })
  // ...
}
```

[VERIFIED: tanstack.com/query/v5/docs/framework/react/guides/parallel-queries — "just call useQuery multiple times" is the documented pattern]

### Pattern 6: Click-to-Filter Wiring

**What:** Recharts onClick → `setFilter` → URL param update → TQ query key change → automatic refetch of all panels.

```tsx
// Source: useReLoanFilters.ts (verified in codebase)
const { filters, setFilter } = useReLoanFilters()

// Pie slice click
<Pie onClick={(data) => setFilter('property_type', data.category)} ... />

// State bar click
<Bar onClick={(data) => setFilter('state', data.category)} ... />
```

The `setFilter` function signature: `(key: keyof ReLoanFilters, value: string | number | null) => void`. It updates the URL via `setSearchParams`, which causes `filters` to re-derive on the next render. Since `filters` is the TQ query key for all three queries, they all refetch. [VERIFIED: useReLoanFilters.ts lines 40–51]

### Pattern 7: Concentration Limits Progress Bar

**What:** Pure Tailwind divs. No chart library needed.

```tsx
// Source: D-21 from CONTEXT.md
function getBarColor(proximity: number): string {
  if (proximity >= 0.9) return 'bg-red-500'
  if (proximity >= 0.7) return 'bg-yellow-400'
  return 'bg-green-500'
}

{limit.concentration_limits.map((item) => (
  <div key={item.category} className="mb-3">
    <div className="flex justify-between text-xs text-[#475569] mb-1">
      <span>{item.category}</span>
      <span>{(item.current_pct * 100).toFixed(1)}% / {(item.limit_pct * 100).toFixed(1)}% limit</span>
    </div>
    <div className="w-full bg-gray-200 rounded h-2">
      <div
        className={`h-2 rounded ${getBarColor(item.proximity)}`}
        style={{ width: `${Math.min(item.proximity * 100, 100)}%` }}
      />
    </div>
  </div>
))}
```

### Anti-Patterns to Avoid

- **PieChart-level onClick vs Pie-level onClick:** Place `onClick` on the `<Pie>` component, not on `<PieChart>`. PieChart-level onClick has known inconsistencies with sector hit detection. [CITED: recharts/recharts GitHub issue #254]
- **Fixed height on ResponsiveContainer without parent height:** `ResponsiveContainer` with `width="100%"` and `height={280}` works inside a block container. Do NOT use `height="100%"` — it requires the parent to have an explicit height. [CITED: recharts.github.io/en-US/api/ResponsiveContainer/]
- **YAxis width too narrow for state labels:** When `layout="vertical"`, the YAxis renders state abbreviations (2 chars). `width={30}` is sufficient. If using full state names, increase to `width={80}`.
- **Flat route not becoming layout route:** If `App.tsx` keeps `<Route path="re-dashboard" element={<ReDashboard />} />` as a childless route, the `<Outlet />` in `ReDashboard` renders nothing. The route MUST have child routes defined inside it.
- **Missing `end` prop on index NavLink:** Without `end`, the `/re-dashboard` NavLink matches all sub-routes and the Executive Summary tab appears active everywhere.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pie/donut chart rendering | Custom SVG arc math | `PieChart` + `Pie` + `Cell` | Arc calculation, label placement, animation are subtle |
| Bar chart with axis management | Canvas/SVG bar math | `BarChart` + `Bar` + axes | Tick formatting, responsive scaling, tooltip positioning |
| Tooltip on hover | Custom div positioned to mouse | Recharts `<Tooltip />` | Positioning near viewport edges, SSR, pointer events |
| Stacked bar math | Manual % calculation | `Bar stackId` | Recharts handles offset calculation automatically |
| Responsive chart container | ResizeObserver wrapper | `ResponsiveContainer` | Cross-browser resize handling already solved |
| Progress bar color logic | CSS animation library | Tailwind class switch (see Pattern 7) | Three-state logic is trivial; no library needed |

---

## Common Pitfalls

### Pitfall 1: `useReLoanFilters` outside a Router context
**What goes wrong:** `useReLoanFilters` calls `useSearchParams` from react-router-dom. If `RePortfolioPage` is tested or rendered outside a `<BrowserRouter>`, it throws: "useSearchParams may be used only in the context of a Router component."
**Why it happens:** Router context is provided at the App level; integration tests that shallow-render the page component miss it.
**How to avoid:** Wrap test renders in `<MemoryRouter>`. Not a concern for production.

### Pitfall 2: Recharts `ResponsiveContainer` with zero-height parent
**What goes wrong:** Chart renders with 0px height — invisible.
**Why it happens:** `width="100%"` and a numeric `height` work fine. But `height="100%"` requires the parent element to have an explicit pixel height; if the parent is auto-sized by content, the container collapses.
**How to avoid:** Always use a numeric `height` on `ResponsiveContainer` (e.g., `height={280}`). Only use `height="100%"` when the card has a fixed `h-XX` Tailwind class.

### Pitfall 3: Stale `params` object in queryFn closure
**What goes wrong:** After filter change, the queryFn still uses old params because the object reference didn't change.
**Why it happens:** `params` is re-derived from `filters` on every render, but the queryFn closure captures the value at query creation time.
**How to avoid:** TanStack Query solves this automatically: `queryKey: ['re-concentration', filters]` — when `filters` changes, TQ treats it as a new query and calls `queryFn` fresh. This is exactly the pattern used in `useKPIs.ts`. [VERIFIED: useKPIs.ts line 13–15]

### Pitfall 4: Recharts types for onClick are `any`
**What goes wrong:** TypeScript doesn't know `data.category` exists — you get implicit `any` warnings.
**Why it happens:** Recharts onClick handler types are intentionally broad (`any`) as of v2.15.0+ to accommodate arbitrary data shapes. [CITED: recharts/recharts GitHub issue #5308]
**How to avoid:** Cast the data parameter to your known type inside the handler:
```tsx
<Pie
  onClick={(rawData) => {
    const item = rawData as ConcentrationItem
    if (item?.category) setFilter('property_type', item.category)
  }}
/>
```

### Pitfall 5: Nested route not rendering child
**What goes wrong:** `/re-dashboard/portfolio` shows only the shell (header + tabs + sidebar) with no chart content.
**Why it happens:** Either (a) `<Outlet />` is missing from `ReDashboard.tsx`, or (b) the child routes are not defined inside the parent `<Route>` in `App.tsx`.
**How to avoid:** Verify both: `<Outlet />` in the shell JSX, and `<Route path="portfolio" element={...}>` nested inside `<Route path="re-dashboard" ...>` in App.tsx.

### Pitfall 6: Double-mounting filter sidebar after refactor
**What goes wrong:** Filter sidebar appears twice — once from the shell and once from the old `ReDashboard` content.
**Why it happens:** If `ReExecutiveSummaryPage.tsx` accidentally includes `<ReDashboardFilterSidebar />` copied from the original `ReDashboard.tsx`, it renders twice.
**How to avoid:** `ReExecutiveSummaryPage.tsx` must only contain the KPI grid — no sidebar. The sidebar lives in `ReDashboard.tsx` (the shell) only.

---

## Code Examples

### Verified: Complete RePortfolioPage skeleton

```tsx
// frontend/src/pages/RePortfolioPage.tsx
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useReLoanFilters } from '../hooks/useReLoanFilters'
import type { ConcentrationResponse, DistributionsResponse, MaturityProfileResponse } from '../types/re'

export default function RePortfolioPage() {
  const { filters, setFilter } = useReLoanFilters()
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== null && v !== '')
  )

  const concentrationQuery = useQuery({
    queryKey: ['re-concentration', filters],
    queryFn: async () => {
      const { data } = await axios.get<ConcentrationResponse>('/api/re/concentration', { params })
      return data
    },
  })

  const distributionsQuery = useQuery({
    queryKey: ['re-distributions', filters],
    queryFn: async () => {
      const { data } = await axios.get<DistributionsResponse>('/api/re/distributions', { params })
      return data
    },
  })

  const maturityQuery = useQuery({
    queryKey: ['re-maturity-profile', filters],
    queryFn: async () => {
      const { data } = await axios.get<MaturityProfileResponse>('/api/re/maturity-profile', { params })
      return data
    },
  })

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Panel 1: Property Type Donut */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h2 className="text-sm font-semibold text-[#1a3868] mb-3">Property Type</h2>
        {/* PropertyTypePieChart component here */}
      </div>

      {/* Panel 2: Top States */}
      {/* ... */}

      {/* Panel 5: Top-10 Exposures — full width */}
      <div className="col-span-1 lg:col-span-2 bg-white rounded-lg border border-gray-200 p-4">
        {/* TopExposuresTable component here */}
      </div>

      {/* Panel 6: Concentration Limits — full width */}
      <div className="col-span-1 lg:col-span-2 bg-white rounded-lg border border-gray-200 p-4">
        {/* ConcentrationLimits component here */}
      </div>
    </div>
  )
}
```

### Verified: Skeleton loading pattern (from KPICard.tsx)

```tsx
// Matches Phase 20 pattern — animate-pulse skeleton block
{isLoading ? (
  <div className="animate-pulse bg-gray-200 rounded h-[280px] w-full" />
) : !data ? (
  <div className="flex items-center justify-center h-[280px] text-sm text-[#94a3b8]">No data</div>
) : (
  <ActualChartComponent data={data} />
)}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat `/re-dashboard` route rendering full page | Nested layout route with `<Outlet>` | Phase 21 (this phase) | Required to support multiple tabs without duplicate chrome |
| All dashboard content in `ReDashboard.tsx` | `ReDashboard.tsx` = shell, page content in separate files | Phase 21 | Consistent with standard dashboard pattern |
| Manual chart libraries (D3/SVG) | Recharts with `ResponsiveContainer` | Industry standard 2022+ | Declarative, typed, works with React 19 |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | MaturityProfileResponse.periods[] only has `total_upb`, not per-property-type breakdown — so stacked bar reduces to single stack | Architecture Patterns / Pattern 4 | If backend returns multiple property keys, need to dynamically generate Bar components per key |
| A2 | Recharts Pie onClick `data` parameter contains all fields from the original data array entry (i.e., `data.category` is accessible) | Architecture Patterns / Pattern 2 | If payload shape differs in v3, would need to use `data.payload.category` or another accessor |

[ASSUMED] — A1: confirmed by reading `re.ts` (MaturityPeriod has `total_upb: number`, no property_type breakdown), and `re_schemas.py` header shows the same schema. This is HIGH confidence — it's our own codebase.
[ASSUMED] — A2: confirmed by GitHub issue #5308 docs which describe `(data: any, index: number, event)` where data mirrors the input data entry. HIGH confidence.

---

## Open Questions (RESOLVED)

1. **Loan size histogram: display-only or wired?**
   - What we know: `loan_size_min`/`loan_size_max` filters exist in `ReLoanFilters`. `loan_size_distribution` buckets have `bucket` string labels (e.g., "0-500K"), not numeric boundaries.
   - What's unclear: Whether bucket label strings can be reverse-parsed to set `loan_size_min`/`loan_size_max`. D-13 says "Claude's Discretion."
   - Recommendation: Display-only. Reverse-parsing bucket strings is fragile and introduces a contract between backend bucket labels and frontend parsing logic. A future phase can add proper loan-size range click behavior with cleaner data.
   - RESOLVED: Display-only (D-13 Claude's Discretion — bars have no onClick handler).

2. **ChartCard wrapper component — extract or inline?**
   - What we know: Six panels share identical card markup (`bg-white rounded-lg border border-gray-200 p-4`).
   - What's unclear: User preference for component granularity.
   - Recommendation: Extract `ChartCard.tsx`. Four-plus identical patterns justifies a shared wrapper; it makes the page component cleaner and skeleton/no-data states composable.
   - RESOLVED: ChartCard extracted — see Plan 02 Task 1 (`frontend/src/components/re/ChartCard.tsx`).

---

## Environment Availability

No new external dependencies. All required tools already available:

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|---------|
| Node.js | npm install recharts | yes | v24.11.1 | — |
| npm | recharts install | yes | 11.7.0 | — |
| recharts (npm package) | all charts | not yet installed | 3.8.1 available | — |
| react-router-dom | nested routes | yes (installed) | 6.30.3 | — |
| @tanstack/react-query | data fetching | yes (installed) | 5.96.2 | — |

**Missing dependencies with no fallback:**
- `recharts` — not yet in `node_modules`. Install command: `cd frontend && npm install recharts`.

---

## Validation Architecture

> `workflow.nyquist_validation` key is absent from config.json — treating as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | No frontend test framework detected — no jest.config.*, vitest.config.*, or __tests__/ directories present |
| Config file | None — Wave 0 would add if tests are required |
| Quick run command | N/A |
| Full suite command | N/A |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-01 | Property type donut renders from seeded data | manual-only | N/A — no frontend test framework | N/A |
| COMP-02 | State bar chart renders from seeded data | manual-only | N/A | N/A |
| COMP-03 | Loan size histogram renders | manual-only | N/A | N/A |
| COMP-04 | Maturity profile stacked bar renders | manual-only | N/A | N/A |
| COMP-05 | Top-10 table shows 10 rows with correct columns | manual-only | N/A | N/A |
| COMP-06 | Concentration limit bars show correct color | manual-only | N/A | N/A |
| UX-01 | Pie slice click changes URL param and refetches KPIs | manual-only | N/A | N/A |

**Note:** No frontend unit/component test framework (Vitest, Jest, Testing Library) is installed in this project. All Phase 21 validation is via browser smoke test against running dev server or QA environment. The planner should NOT add a Wave 0 test scaffolding task unless the user explicitly requests it.

### Sampling Rate
- **Per task commit:** Manual: `cd frontend && npm run dev` → navigate to `/re-dashboard/portfolio`
- **Phase gate:** All 5 success criteria visible in browser before `/gsd-verify-work`

### Wave 0 Gaps
- None for test framework (no frontend tests in project)
- Required before implementation: `npm install recharts` in Wave 1

---

## Security Domain

> `security_enforcement` key absent from config.json — treating as enabled.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | All RE routes behind `ProtectedRoute` — no new auth needed |
| V3 Session Management | no | No session changes in this phase |
| V4 Access Control | no | No new role checks — existing `ProtectedRoute` covers RE routes |
| V5 Input Validation | yes (low risk) | Chart click payloads are `data.category` (string from our own API response) — not user-typed input. No XSS surface. |
| V6 Cryptography | no | No new crypto in frontend chart components |

### Known Threat Patterns for Recharts + React Router

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via chart label injection | Spoofing | React renders all chart labels as escaped text — not innerHTML. No risk if data is from controlled API. |
| Filter param injection via URL | Tampering | `useReLoanFilters` reads URL params and passes as query params to backend. Backend validates via `FilterParams` Pydantic model. No additional frontend sanitization needed. |

---

## Sources

### Primary (HIGH confidence)
- `frontend/package.json` — confirmed installed dependency versions
- `frontend/node_modules/react-router-dom/package.json` — confirmed v6.30.3 installed
- `frontend/src/types/re.ts` — all response type shapes verified directly
- `frontend/src/hooks/useReLoanFilters.ts` — setFilter signature and URL-as-source-of-truth pattern verified
- `frontend/src/pages/ReDashboard.tsx` — current structure before refactor verified
- `frontend/src/App.tsx` — current flat route structure verified
- `frontend/src/hooks/useKPIs.ts` — queryFn pattern (params stripping, queryKey) verified
- `frontend/src/components/re/KPICard.tsx` — skeleton loading pattern verified

### Secondary (MEDIUM confidence)
- [recharts.github.io/api/Pie/](https://recharts.github.io/api/Pie/) — Pie props: dataKey, nameKey, innerRadius, outerRadius, onClick
- [recharts.github.io/en-US/api/BarChart/](https://recharts.github.io/en-US/api/BarChart/) — layout prop values verified
- [recharts.github.io/en-US/api/Bar/](https://recharts.github.io/en-US/api/Bar/) — stackId, onClick props
- [reactrouter.com/docs/en/v6/components/nav-link](https://reactrouter.com/docs/en/v6/components/nav-link) — NavLink className render prop, end prop behavior verified
- [tanstack.com/query/v5/docs/framework/react/guides/parallel-queries](https://tanstack.com/query/v5/docs/framework/react/guides/parallel-queries) — multiple useQuery pattern verified
- npm registry — `npm view recharts version` → 3.8.1; `npm view recharts peerDependencies` → React 16.8+/19 compatible

### Tertiary (LOW confidence)
- [github.com/recharts/recharts/issues/5308](https://github.com/recharts/recharts/issues/5308) — onClick payload is `(data: any, index: number, event)` — closed as fixed in 2.15.0, applicable to 3.x by extension
- [github.com/recharts/recharts/issues/254](https://github.com/recharts/recharts/issues/254) — onClick placement on Pie vs PieChart

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified from npm registry and installed node_modules
- Architecture: HIGH — existing codebase patterns directly observed; Recharts API verified from official docs
- Pitfalls: HIGH — codebase-specific pitfalls derived from reading actual files; Recharts pitfalls from official issues
- Click payload: MEDIUM — onClick signature documented but exact field names rely on our own data types (ConcentrationItem), which are verified

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (Recharts 3.x API is stable; React Router v6 nested route API is stable)
