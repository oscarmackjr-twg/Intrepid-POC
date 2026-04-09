# Phase 19: Filter Hook + TypeScript Foundation — Research

**Researched:** 2026-04-08
**Domain:** React state management (Zustand), React Router URL params, TypeScript type authoring
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Filter panel is a right-side panel, always visible, fixed width `w-72` (288px).
- **D-02:** Page layout on `/re-dashboard`: nav sidebar (w-60) | charts area (flex-1) | filter panel (w-72). Three-column flex row within the existing `<main>` content area.
- **D-03:** Filter panel is always open — no toggle, no collapse. No open/close state needed.
- **D-04:** Add Zustand ONLY in Phase 19. TanStack Query is NOT installed here — Phase 20 installs it.
- **D-05:** Filter controls are built with raw Tailwind — `<select>`, `<input type="date">`, `<input type="number">` elements. No component library.
- **D-06:** Filter controls per field:
  - `as_of_date` → `<input type="date" />`
  - `property_type` → `<select>` single-select
  - `state` → `<select>` single-select
  - `msa` → `<select>` single-select
  - `loan_size_min` / `loan_size_max` → two `<input type="number">` fields (min/max pair)
  - `risk_rating` → `<select>` single-select
  - `vintage_year` → `<select>` single-select
  - `borrower` → `<input type="text">` (partial match, case-insensitive)
  - `rate_type` → `<select>` single-select
- **D-07:** URL is source of truth. `useReLoanFilters` reads from `useSearchParams()` on every render and writes to URL (via `setSearchParams`) when any filter changes. Zustand store is a mirror/cache.
- **D-08:** Hydration flow: page load → read URL params → update Zustand store → return filter object.
- **D-09:** Hook signature: `useReLoanFilters()` returns `{ filters: ReLoanFilters, setFilter, clearFilters }`. `filters` serves as the TanStack Query key in Phase 20.
- **D-10:** "Clear all filters" calls `clearFilters()` → `setSearchParams({})` → Zustand resets to defaults.
- **D-11:** Types are hand-written in `frontend/src/types/re.ts`. No OpenAPI codegen.
- **D-12:** Monetary and rate fields typed as `number` in TypeScript.
- **D-13:** All filter param fields are `string | null` in the frontend type. Exception: `loan_size_min`/`loan_size_max` are `number | null`.
- **D-14:** Add `/re-dashboard` route to `frontend/src/App.tsx` under the existing `<ProtectedRoute><Layout />` wrapper.
- **D-15:** Add "RE Dashboard" nav link to `frontend/src/components/Layout.tsx` sidebar nav list as a top-level item.

### Claude's Discretion

- Zustand store file path and store shape (suggestion: `frontend/src/stores/filterStore.ts`)
- Whether `useReLoanFilters` lives in `hooks/useReLoanFilters.ts` or alongside the store
- Exact Tailwind styling details for the filter panel (follow existing TWG Global brand patterns)
- Whether filter selects are populated with hardcoded option lists or left empty for Phase 20

### Deferred Ideas (OUT OF SCOPE)

- TanStack Query — Phase 20
- API calls from the filter panel — Phase 20
- Chart components — Phases 20–24
- Collapse/toggle behavior on filter panel — not in scope (always open)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FILTER-01 | Filter sidebar available on all dashboard pages with controls for: as-of date, property type, state/MSA, loan size range, risk rating, vintage, borrower, rate type | Covered by ReDashboardFilterSidebar component with 9 native HTML controls |
| FILTER-02 | Active filters persist in URL query params and sync with Zustand in-memory store | Covered by `useReLoanFilters` hook using `useSearchParams` + Zustand store |
| FILTER-03 | Changing any filter re-fetches all dashboard panels simultaneously without page reload | Hook structures `filters` object as the TanStack Query key — Phase 20 installs query; Phase 19 ensures key is stable |
| FILTER-04 | Filter sidebar has a "Clear all filters" control that resets all params | `clearFilters()` calls `setSearchParams({})` + store reset in one action |

</phase_requirements>

---

## Summary

Phase 19 builds the frontend infrastructure skeleton that all subsequent RE dashboard phases will import unchanged. The three pillars are: (1) Zustand 5 filter store, (2) `useReLoanFilters` hook that keeps URL and store in sync with URL as the authoritative source, and (3) hand-written TypeScript interfaces in `frontend/src/types/re.ts` mirroring all Pydantic schemas from `backend/api/re_schemas.py`.

The critical design constraint is that `filters` — the object returned from `useReLoanFilters()` — must be referentially stable when nothing changes and structurally different (new object reference) whenever any filter changes. Phase 20's TanStack Query relies on this object as its cache key: a new reference triggers a refetch, an unchanged reference hits the cache. The correct implementation derives `filters` directly from `useSearchParams()` on each render (URL-derived), then syncs the result into Zustand as a side-effect via `useEffect`. This avoids stale closures because `useSearchParams` always returns the current URL state.

The layout decision (D-02) requires a structural change to `Layout.tsx`: the current `<main>` element renders `<Outlet />` inside a simple `div.p-6`. On the `/re-dashboard` route, the page component itself must render the three-column flex row (charts area + filter panel), not Layout. The filter panel is co-located with `ReDashboard` as a sibling — Layout remains unchanged.

**Primary recommendation:** Install Zustand 5, create `filterStore.ts` + `useReLoanFilters.ts` + `types/re.ts`, wire route/nav, and render filter sidebar. No API calls, no chart data — infrastructure only.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| zustand | 5.0.12 | Client-side filter state management | No Provider, minimal boilerplate, React 19 compatible [VERIFIED: npm registry] |
| react-router-dom | 6.30.3 (installed) | `useSearchParams` for URL state | Already in project; v6 `useSearchParams` is the canonical URL state hook [VERIFIED: npm registry] |
| TypeScript | ~5.9.3 (installed) | Type-safe interfaces | Already in project [VERIFIED: package.json] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-router | 7.12.0 (installed) | Also exports `useSearchParams` | Already installed; use from `react-router-dom` for consistency with existing code |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Zustand | React context + useReducer | Context requires Provider, causes full subtree re-renders; Zustand is selective |
| Zustand | nuqs | nuqs has built-in URL sync but adds a dependency; Zustand + manual sync is more explicit per D-07 |
| Hand-written types | openapi-typescript codegen | Codegen adds tooling complexity; hand-written is fine for a small, stable schema |

**Installation:**
```bash
cd frontend && npm install zustand
```

**Version verification:**
```
zustand@5.0.12 — verified 2026-04-08 via npm registry
peer deps: react >=18.0.0 (optional), @types/react >=18.0.0 (optional)
React 19 is compatible — peer dep is >= 18.0.0, optional flag means no hard requirement
```
[VERIFIED: npm registry]

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── types/
│   └── re.ts               # All TypeScript interfaces (hand-written from re_schemas.py)
├── stores/
│   └── filterStore.ts      # Zustand store — useFilterStore hook
├── hooks/
│   └── useReLoanFilters.ts # URL ↔ Zustand sync hook
├── pages/
│   └── ReDashboard.tsx     # Route page — renders filter sidebar + charts area
└── components/
    └── re/
        └── ReDashboardFilterSidebar.tsx  # Filter panel component (w-72, always visible)
```

**Note:** No `index.ts` barrel files — existing project pattern imports directly from file path. [VERIFIED: CONTEXT.md code_context section]

### Pattern 1: Zustand Store (No Provider)

**What:** Create a typed Zustand store that holds filter state. Export the hook directly — no Provider wrapping.

**When to use:** Always for this project — Zustand's no-Provider model is the defining advantage.

```typescript
// Source: pmndrs/zustand GitHub README + npm registry
// frontend/src/stores/filterStore.ts
import { create } from 'zustand'
import type { ReLoanFilters } from '../types/re'

interface FilterStore {
  filters: ReLoanFilters
  setFilters: (filters: ReLoanFilters) => void
  resetFilters: () => void
}

const DEFAULT_FILTERS: ReLoanFilters = {
  as_of_date: null,
  property_type: null,
  state: null,
  msa: null,
  loan_size_min: null,
  loan_size_max: null,
  risk_rating: null,
  vintage_year: null,
  borrower: null,
  rate_type: null,
}

export const useFilterStore = create<FilterStore>()((set) => ({
  filters: DEFAULT_FILTERS,
  setFilters: (filters) => set({ filters }),
  resetFilters: () => set({ filters: DEFAULT_FILTERS }),
}))
```

**TypeScript note:** `create<FilterStore>()` uses curried form (double-call) — required for TypeScript inference. [ASSUMED — based on training knowledge of Zustand 4/5 TypeScript pattern; verified in spirit from community sources]

### Pattern 2: URL ↔ Zustand Sync Hook (URL as Source of Truth)

**What:** `useReLoanFilters` derives `filters` from `useSearchParams()` on every render. A `useEffect` syncs the URL-derived value into the Zustand store as a side-effect. This avoids stale closure issues because `useSearchParams` always reflects the current URL.

**Critical insight:** Do NOT derive `filters` from the Zustand store and then write the store — this creates a circular dependency. Always derive from URL → write to store. Components that need filters read from the hook, which reads from the URL.

```typescript
// frontend/src/hooks/useReLoanFilters.ts
import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useFilterStore } from '../stores/filterStore'
import type { ReLoanFilters } from '../types/re'

export function useReLoanFilters() {
  const [searchParams, setSearchParams] = useSearchParams()
  const setFilters = useFilterStore((s) => s.setFilters)
  const resetFilters = useFilterStore((s) => s.resetFilters)

  // Derive filters from URL on every render — URL is authoritative
  const filters: ReLoanFilters = {
    as_of_date: searchParams.get('as_of_date'),
    property_type: searchParams.get('property_type'),
    state: searchParams.get('state'),
    msa: searchParams.get('msa'),
    loan_size_min: searchParams.get('loan_size_min') !== null
      ? Number(searchParams.get('loan_size_min'))
      : null,
    loan_size_max: searchParams.get('loan_size_max') !== null
      ? Number(searchParams.get('loan_size_max'))
      : null,
    risk_rating: searchParams.get('risk_rating'),
    vintage_year: searchParams.get('vintage_year'),
    borrower: searchParams.get('borrower'),
    rate_type: searchParams.get('rate_type'),
  }

  // Sync URL-derived filters into Zustand store (side-effect)
  // useEffect not needed — setFilters call during render is fine since
  // Zustand updates are synchronous and don't cause re-renders in the same component
  // HOWEVER: to be safe and avoid render-phase side effects, use useEffect:
  // useEffect(() => { setFilters(filters) }, [searchParams])

  const setFilter = useCallback(
    (key: keyof ReLoanFilters, value: string | number | null) => {
      const next = new URLSearchParams(searchParams)
      if (value === null || value === '') {
        next.delete(key)
      } else {
        next.set(key, String(value))
      }
      setSearchParams(next)
    },
    [searchParams, setSearchParams]
  )

  const clearFilters = useCallback(() => {
    setSearchParams({})
    resetFilters()
  }, [setSearchParams, resetFilters])

  return { filters, setFilter, clearFilters }
}
```

**Stale closure prevention:** `setFilter` captures `searchParams` via `useCallback`. Because `searchParams` is a dependency, the callback is recreated whenever the URL changes — no stale reads. [ASSUMED — standard React closure pattern; no specific source found]

**Object identity for TanStack Query key (Phase 20):** The `filters` object is reconstructed on every render from `useSearchParams`. A new reference is created every time any search param changes, which is what Phase 20's TanStack Query needs — changing any filter creates a new key object, triggering a refetch. When no params change (same URL), the same logical values produce a semantically equivalent key. TanStack Query performs deep equality on keys, so referential identity is not required — structural equality is what matters. [ASSUMED — based on TanStack Query documentation knowledge; Phase 20 must verify]

### Pattern 3: ReDashboard Page Layout (Three-Column Flex)

**What:** The page component renders the three-column layout. Layout.tsx is NOT modified for the flex row — the `<Outlet />` renders `ReDashboard`, which owns the inner layout.

**Critical:** The existing `Layout.tsx` wraps `<Outlet />` in `<div className="p-6">`. This `p-6` padding will apply to all routes including `/re-dashboard`. The ReDashboard component should use `-m-6` negative margin or the Layout should be left as-is and ReDashboard uses full-width flex within the padded area. Simplest: leave Layout as-is, ReDashboard uses `flex gap-0 -mx-6 -my-6` to break out of the padding, or preferably design the filter/chart area to work within the padded container.

**Simpler approach:** Design the three-column layout within the `p-6` container — `w-72` filter panel stays inside. The charts area gets `flex-1`. This is the zero-friction path.

```tsx
// frontend/src/pages/ReDashboard.tsx
import { ReDashboardFilterSidebar } from '../components/re/ReDashboardFilterSidebar'

export default function ReDashboard() {
  return (
    <div className="flex gap-6 min-h-full">
      {/* Charts area */}
      <div className="flex-1 min-w-0">
        {/* Chart panels go here in Phase 20+ */}
        <p className="text-[#475569] text-sm">RE Dashboard — charts coming in Phase 20</p>
      </div>

      {/* Filter panel — right side, always visible */}
      <ReDashboardFilterSidebar />
    </div>
  )
}
```

### Pattern 4: Route Integration in App.tsx

**What:** Add a child route inside the existing `<ProtectedRoute><Layout />` block.

```tsx
// In App.tsx — add after existing child routes:
import ReDashboard from './pages/ReDashboard'

// Inside the Route path="/" block:
<Route path="re-dashboard" element={<ReDashboard />} />
```

Note: Use `path="re-dashboard"` (no leading slash) because it is a child route relative to `"/"`. [VERIFIED: App.tsx existing pattern — all child routes use no leading slash]

### Pattern 5: Nav Link in Layout.tsx

**What:** Add a top-level nav link using the same Tailwind pattern as existing links.

```tsx
// In Layout.tsx nav section — add before or after "File Manager":
<Link
  to="/re-dashboard"
  className={`px-5 py-2 text-sm flex items-center gap-2 border-l-4 ${
    location.pathname.startsWith('/re-dashboard')
      ? 'border-[#1a3868] text-[#1a3868] font-semibold bg-gray-50'
      : 'border-transparent text-[#475569] hover:text-[#1a3868] hover:bg-gray-50'
  }`}
>
  RE Dashboard
</Link>
```

[VERIFIED: Layout.tsx — identical pattern used by all existing nav links]

### Anti-Patterns to Avoid

- **Deriving filters from Zustand store, not URL:** Breaks URL-as-source-of-truth. Always derive from `useSearchParams()`.
- **Using Provider from Zustand:** Zustand 5 does not require a Provider. Importing `useFilterStore` directly works anywhere in the component tree.
- **Calling `useSearchParams` outside Router context:** `useSearchParams` requires the component to be rendered inside a `<Router>`. All pages are already inside `<AuthProvider>` → `<Routes>` so this is not an issue, but filter components must be rendered as descendants of the Router.
- **Storing filter values as separate Zustand fields:** Keep the full `ReLoanFilters` object as a single field — this makes setting and resetting atomic and produces a single object reference for use as a TanStack Query key.
- **Using `useState` for filter values alongside URL params:** Creates two sources of truth. Use URL only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Client state without Provider | Custom context | Zustand `create()` | Zustand is zero-config, no Provider, selective re-renders |
| URL param serialization | Custom string building | `URLSearchParams` (browser built-in) | Handles encoding, duplicate keys, null removal |
| TypeScript generics for store | Manual type casting | `create<StateType>()()` curried call | Zustand's TypeScript pattern handles inference automatically |

**Key insight:** The only custom code in this phase is the glue between URL and Zustand. Everything else — URL parsing, state management, type safety — uses established primitives.

---

## TypeScript Interface Definitions

All types must be written in `frontend/src/types/re.ts`. Source: `backend/api/re_schemas.py` [VERIFIED: re_schemas.py read in full].

### Filter Type (mirrors FilterParams)

```typescript
// All filter fields: string | null for URL params, except number fields
export interface ReLoanFilters {
  as_of_date: string | null        // date → string in URL; API converts to date
  property_type: string | null
  state: string | null
  msa: string | null
  loan_size_min: number | null     // number per D-13
  loan_size_max: number | null     // number per D-13
  risk_rating: string | null
  vintage_year: string | null      // int in Python; string in URL; API converts
  borrower: string | null
  rate_type: string | null
}
```

**Design note on vintage_year:** Python backend is `Optional[int]`. URL params are always strings. Frontend receives this as a string from the URL. Decision D-13 says `string | null` for URL params — so `vintage_year` is `string | null` in `ReLoanFilters`. The backend's FastAPI `get_filter_params` handles the string-to-int conversion. This is consistent.

### KPI Response (mirrors KPIResponse)

```typescript
export interface KPIResponse {
  total_upb: number
  wac: number | null
  wam: number | null
  wa_ltv: number | null
  wa_dscr: number | null
  active_loan_count: number
  delinquent_30_upb: number
  delinquent_60_upb: number
  delinquent_90_upb: number
  portfolio_yield: number | null
}
```

### Concentration Types (mirrors ConcentrationItem, TopExposure, ConcentrationLimit, ConcentrationResponse)

```typescript
export interface ConcentrationItem {
  category: string
  loan_count: number
  total_upb: number
  pct_of_total: number
}

export interface TopExposure {
  loan_number: string
  borrower_name: string
  upb: number
  ltv: number | null
  dscr: number | null
  property_type: string
  state: string
}

export interface ConcentrationLimit {
  category: string
  current_pct: number
  limit_pct: number
  proximity: number
}

export interface ConcentrationResponse {
  property_type: ConcentrationItem[]
  state: ConcentrationItem[]
  msa: ConcentrationItem[]
  top_10_exposures: TopExposure[]
  concentration_limits: ConcentrationLimit[]
}
```

### Distribution Types (mirrors HistogramBucket, DistributionsResponse)

```typescript
export interface HistogramBucket {
  bucket: string
  loan_count: number
  total_upb: number
  color: string
}

export interface DistributionsResponse {
  ltv_histogram: HistogramBucket[]
  dscr_histogram: HistogramBucket[]
  loan_size_distribution: HistogramBucket[]
}
```

### Maturity Profile (mirrors MaturityPeriod, MaturityProfileResponse)

```typescript
export interface MaturityPeriod {
  year: number
  quarter: number
  loan_count: number
  total_upb: number
}

export interface MaturityProfileResponse {
  periods: MaturityPeriod[]
}
```

### Loan List / Detail (mirrors LoanSummary, LoanListResponse, PaymentHistorySummary, LoanDetailResponse)

```typescript
export interface LoanSummary {
  id: number
  loan_number: string
  borrower_name: string | null
  upb: number | null
  interest_rate: number | null
  ltv: number | null
  dscr: number | null
  property_type: string | null
  state: string | null
  risk_rating: string | null
  maturity_date: string | null   // date → ISO string in JSON
  origination_date: string | null
  days_past_due: number | null
  delinquency_status: string | null
}

export interface LoanListResponse {
  total: number
  page: number
  page_size: number
  items: LoanSummary[]
}

export interface PaymentHistorySummary {
  total_scheduled_principal: number | null
  total_actual_principal: number | null
  total_scheduled_interest: number | null
  total_actual_interest: number | null
  periods: number
}

export interface LoanDetailResponse extends LoanSummary {
  msa: string | null
  original_balance: number | null
  wam_months: number | null
  rate_type: string | null
  prior_risk_rating: string | null
  pipeline_stage: string | null
  vintage_year: number | null
  as_of_date: string | null
  payment_history: PaymentHistorySummary | null
  appraisal_history: unknown[]   // stubbed in Phase 18 per TODO comment in re_schemas.py
}
```

### Cashflow Performance (mirrors CashflowPeriod, CashflowPerformanceResponse)

```typescript
export interface CashflowPeriod {
  period_date: string
  scheduled_principal: number
  actual_principal: number
  scheduled_interest: number
  actual_interest: number
  total_noi: number
  gross_yield: number | null
  cpr: number | null
}

export interface CashflowPerformanceResponse {
  periods: CashflowPeriod[]
  net_loss_rate: number | null
}
```

### Origination Pipeline (mirrors OriginationMonth, PipelineFunnelStage, VintageGroup, OriginationPipelineResponse)

```typescript
export interface OriginationMonth {
  year: number
  month: number
  loan_count: number
  total_upb: number
}

export interface PipelineFunnelStage {
  stage: string
  loan_count: number
  total_upb: number
}

export interface VintageGroup {
  vintage_year: number
  loan_count: number
  total_upb: number
  avg_ltv: number | null
  avg_dscr: number | null
}

export interface OriginationPipelineResponse {
  origination_by_month: OriginationMonth[]
  pipeline_funnel: PipelineFunnelStage[]
  vintage_breakdown: VintageGroup[]
}
```

### Market Context (mirrors MarketRate, CapRate, MarketContextResponse)

```typescript
export interface MarketRate {
  value: number
  trend: string
  source: string
}

export interface CapRate {
  property_type: string
  value: number
  source: string
}

export interface MarketContextResponse {
  ten_year_treasury: MarketRate
  sofr: MarketRate
  cap_rates: CapRate[]
  vacancy_rates: CapRate[]
}
```

### Sensitivity (mirrors SensitivityScenario, SensitivityResponse)

```typescript
export interface SensitivityScenario {
  bps_change: number
  new_wac: number
  annual_interest_impact: number
  impact_pct: number
}

export interface SensitivityResponse {
  base_wac: number
  total_upb: number
  scenarios: SensitivityScenario[]
}
```

---

## Common Pitfalls

### Pitfall 1: Using `useSearchParams` Outside Router Context
**What goes wrong:** Component throws "useSearchParams() may be used only in the context of a Router component"
**Why it happens:** `useSearchParams` is a React Router hook; any component using it must be rendered inside `<Routes>` (or equivalent router context).
**How to avoid:** All RE dashboard components are rendered as `<Outlet />` children of `<ProtectedRoute><Layout />` which is inside `<Routes>` in App.tsx. No issue as long as filter sidebar is rendered inside `ReDashboard`.
**Warning signs:** Error thrown immediately on render if sidebar is moved outside the route tree.

### Pitfall 2: Circular Update Loop (Zustand ↔ URL)
**What goes wrong:** `setFilter` updates URL → `useSearchParams` re-renders → `useEffect` updates Zustand → (if Zustand drives setSearchParams) → infinite loop.
**Why it happens:** Bidirectional sync where each side triggers the other.
**How to avoid:** One-way flow only: URL → Zustand (read URL, write to store). Never write to URL from a Zustand subscriber. `setFilter` writes to URL via `setSearchParams` directly; the hook re-renders due to URL change, reads new URL, updates store. The store update does NOT call `setSearchParams` again.
**Warning signs:** React "too many re-renders" error in DevTools.

### Pitfall 3: `filters` Object Reference Equality
**What goes wrong:** Phase 20's TanStack Query key never changes even when filters change.
**Why it happens:** If `filters` is stored in Zustand and the store holds a reference that doesn't change when values do (e.g., mutation), the key appears identical.
**How to avoid:** Derive `filters` fresh from `useSearchParams()` on every render. `URLSearchParams.get()` always returns current values. The resulting object is a new reference on every render. TanStack Query uses deep (JSON) equality for keys, not referential equality — this is actually fine. The filter values changing is what matters.
**Warning signs:** Filters change in the URL but charts don't refresh in Phase 20.

### Pitfall 4: Zustand Curried TypeScript Syntax
**What goes wrong:** TypeScript error "Expected 1 arguments, but got 2" or inference failures.
**Why it happens:** Zustand 4+ requires curried call for TypeScript: `create<State>()((set) => ...)` (two calls). Single-call `create<State>((set) => ...)` does not properly infer types.
**How to avoid:** Always use `create<FilterStore>()((set) => ({ ... }))` — note the `()` after the generic.
**Warning signs:** TypeScript errors in store file, actions typed as `any`.

### Pitfall 5: Both `react-router` and `react-router-dom` Installed
**What goes wrong:** Imports from wrong package, version mismatch, duplicate Router instances.
**Why it happens:** Project has both `react-router@7.12.0` and `react-router-dom@6.30.3` in package.json — this is unusual (v7 and v6 coexist).
**How to avoid:** Import `useSearchParams`, `useLocation`, `Link` from `react-router-dom` (v6) to match the existing codebase pattern. The existing `App.tsx`, `AuthContext.tsx`, and `Layout.tsx` all import from `react-router-dom`. Do not mix imports between packages.
**Warning signs:** Hooks not reactive to navigation, multiple Router instances in React DevTools.

### Pitfall 6: `<input type="number">` Returns String from `onChange`
**What goes wrong:** `event.target.value` is always a string even for `type="number"`.
**Why it happens:** HTML input `value` is always a string in the DOM.
**How to avoid:** Parse explicitly: `Number(event.target.value) || null` (returns null if empty/NaN). The `ReLoanFilters` type has `loan_size_min: number | null` per D-13.

---

## Runtime State Inventory

Step 2.5: SKIPPED — Phase 19 is greenfield frontend infrastructure. No rename, refactor, or migration. No stored data or runtime state is affected.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js + npm | `npm install zustand` | Must verify at execution | — | — |
| zustand | Filter state | Not yet installed | 5.0.12 (latest) | — |
| react-router-dom | `useSearchParams` | ✓ (installed) | 6.30.3 | — |
| TypeScript | Type compilation | ✓ (installed) | ~5.9.3 | — |
| Vite | Dev server / build | ✓ (installed) | ^7.x | — |

**Missing dependencies with no fallback:**
- `zustand` — must be installed via `npm install zustand` before implementation. No fallback; it is the locked choice (D-04).

**Missing dependencies with fallback:**
- None.

---

## Validation Architecture

`workflow.nyquist_validation` is absent from `.planning/config.json` — treated as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None detected in frontend (no jest.config, no vitest.config, no test scripts in package.json) |
| Config file | None — Wave 0 must assess if frontend testing is in scope |
| Quick run command | N/A |
| Full suite command | N/A |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FILTER-01 | Filter sidebar renders on `/re-dashboard` with 9 controls | manual-only (visual) | — | N/A |
| FILTER-02 | Selecting filter updates URL params + Zustand simultaneously | manual-only (browser DevTools) | — | N/A |
| FILTER-03 | Filter change triggers TanStack Query refetch | deferred to Phase 20 | — | N/A |
| FILTER-04 | "Clear all filters" resets URL and store | manual-only (browser) | — | N/A |

**Manual-only justification:** Phase 19 is pure UI/state infrastructure with no backend calls. Automated browser testing (Playwright/Cypress) is not in the current stack. Visual and DevTools verification is the phase gate per CONTEXT.md success criteria.

### Wave 0 Gaps

- No frontend test framework detected — no action needed for Phase 19 (all verification is manual per phase gate definition in CONTEXT.md)

---

## Security Domain

`security_enforcement` is absent from config — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No — filter state is not auth-related | — |
| V3 Session Management | No — filters are not session secrets | — |
| V4 Access Control | Partial — RE Dashboard link should be visible to all authenticated users (ROLES-03, Phase 27) | ProtectedRoute already enforces authentication |
| V5 Input Validation | Yes — filter inputs are user-supplied | No server-side validation in this phase; validation happens at API boundary (FastAPI `get_filter_params`) |
| V6 Cryptography | No | — |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| URL param injection (XSS via query string) | Tampering | React/JSX auto-escapes rendered strings; no `dangerouslySetInnerHTML`; no eval of URL values |
| Filter bypass (URL manipulation) | Elevation of privilege | Server-side scope enforcement in `build_filters()` — never trust client-side filter values alone |

**Security note:** Filter params are sanitized server-side by FastAPI's `get_filter_params` function. The frontend's role is only to pass values via query string. No sensitive data is stored in URL params or Zustand state.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Zustand v3/v4 single `create()` call (TypeScript) | Zustand v5 curried `create<T>()()` | Zustand 4.x | Required pattern for proper type inference |
| Redux / MobX for client state | Zustand (no Provider, minimal API) | 2021+ | Zustand is now the dominant lightweight state manager |
| Storing filters in component `useState` | URL params as source of truth | 2022+ | URL state enables shareable URLs, back/forward navigation |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Zustand curried `create<T>()()` is required for TypeScript in v5 | Architecture Patterns, Pitfall 4 | TypeScript errors in store file; can be fixed without logic change |
| A2 | `useEffect` is needed to sync URL → Zustand store (not during render phase) | Pattern 2 code comment | Minor: React strict mode double-invoke may cause extra store updates; not a correctness issue |
| A3 | TanStack Query uses deep equality (not referential) for query keys | Pitfall 3 | If wrong, Phase 20 may need to memoize `filters` with `useMemo`; easy fix |
| A4 | `vintage_year` should be `string | null` in `ReLoanFilters` per D-13 | TypeScript Interface Definitions | If typed as `number | null`, the URL string won't parse automatically; requires explicit Number() conversion in setFilter |

---

## Open Questions

1. **Filter select option populations**
   - What we know: D-05 says no component library; Claude's discretion whether option lists are hardcoded or empty.
   - What's unclear: Should `property_type` / `state` selects have hardcoded placeholder options (e.g., "Multifamily", "Office") or be empty `<select>` with only a "-- All --" option for Phase 19?
   - Recommendation: Render hardcoded option lists matching the seed data values from Phase 17 (`property_type` values from `seed_re_loans.py`). Phase 20 can replace with API-populated options. This satisfies FILTER-01's "controls visible" requirement without needing API calls.

2. **Layout padding interaction**
   - What we know: `Layout.tsx` wraps `<Outlet />` in `<div className="p-6">`. ReDashboard renders inside Outlet.
   - What's unclear: Should the filter panel be full-height (flush to screen edges) or padded like the rest of the content?
   - Recommendation: Keep the `p-6` padding — filter panel and charts area are both inside the padded container. The `w-72` filter panel is relative to the content area, not the viewport. This is simpler and consistent with the existing layout.

3. **`react-router` v7 + `react-router-dom` v6 coexistence**
   - What we know: Both are installed. Existing code uses `react-router-dom`.
   - What's unclear: Whether this causes peer dep warnings or conflicts at runtime.
   - Recommendation: Import exclusively from `react-router-dom` throughout Phase 19. This matches the entire existing codebase. Do not import from `react-router` directly.

---

## Sources

### Primary (HIGH confidence)
- npm registry (direct API call) — `zustand@5.0.12`, peer deps `react >= 18.0.0 (optional)`, confirmed 2026-04-08 [VERIFIED]
- `frontend/package.json` — installed versions of react-router-dom (6.30.3), react-router (7.12.0), TypeScript (~5.9.3) [VERIFIED]
- `backend/api/re_schemas.py` — all Pydantic models read verbatim; TypeScript types derived directly [VERIFIED]
- `frontend/src/App.tsx` — route structure and child route pattern [VERIFIED]
- `frontend/src/components/Layout.tsx` — nav link pattern, active state logic, Tailwind classes [VERIFIED]
- `frontend/src/contexts/AuthContext.tsx` — auth hook pattern and User interface [VERIFIED]
- `.planning/phases/19-filter-hook-typescript-foundation/19-CONTEXT.md` — all locked decisions [VERIFIED]

### Secondary (MEDIUM confidence)
- pmndrs/zustand GitHub README (via WebFetch) — `create()` pattern, no-Provider model, selector hook usage
- tkdodo.eu "Working with Zustand" (via WebFetch) — store organization, atomic selectors, actions namespace pattern
- logrocket.com "URL state useSearchParams" (via WebFetch) — URL-as-source-of-truth pattern, setSearchParams updater pattern

### Tertiary (LOW confidence)
- WebSearch results on Zustand 5 + React 19 compatibility — consistent with npm registry peer deps (converging evidence upgrades to MEDIUM)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — npm registry confirmed Zustand 5.0.12, all other packages verified in package.json
- TypeScript types: HIGH — derived verbatim from re_schemas.py source code
- Architecture patterns: MEDIUM — Zustand and React Router patterns are well-established; URL sync pattern is [ASSUMED] on stale-closure avoidance details
- Pitfalls: MEDIUM — most derived from first-principles React patterns; Zustand TypeScript curried syntax is [ASSUMED]

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (Zustand is stable; React Router v6 is stable)
