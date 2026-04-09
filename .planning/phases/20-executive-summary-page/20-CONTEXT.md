# Phase 20: Executive Summary Page - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the placeholder in `ReDashboard.tsx` with real KPI cards connected to `/api/re/kpis`. Install TanStack Query (deferred from Phase 19), wire `useReLoanFilters` as the query key so filter changes trigger automatic refetch, and implement visible loading and no-data states per card. Clicking a delinquency KPI card applies a filter; remaining cards are display-only.

Phase gate (from ROADMAP.md):
1. `/re-dashboard` shows KPI cards for all 10 metrics populated with non-zero values from seeded data
2. Applying a filter from the sidebar updates all KPI card values without page reload
3. Filtering to zero matching loans shows `–` (muted) on each card — not zeros or blank space
4. A KPI card in loading state shows a pulsing skeleton — not a flash of empty content

</domain>

<decisions>
## Implementation Decisions

### KPI Card Layout
- **D-01:** Cards are arranged in a **4-column CSS grid** (`grid-cols-4` on wide, `grid-cols-2` on mobile).
- **D-02:** **10 individual cards** — each of the 10 `KPIResponse` fields gets its own card. The three delinquency buckets (30/60/90+ UPB) are separate cards, not grouped.
- **D-03:** Each card displays **metric value (large) + label below** only. No trend arrows, no secondary detail lines, no benchmark comparisons.

### Data Fetching
- **D-04:** Install **TanStack Query (`@tanstack/react-query`)** in this phase. This is the first chart component that needs API data.
- **D-05:** `useReLoanFilters().filters` (the full `ReLoanFilters` object) is used as the TanStack Query key. Changing any filter changes the key object, triggering automatic refetch — no explicit `queryClient.invalidateQueries` needed.
- **D-06:** Wrap the app (or the RE dashboard subtree) in `<QueryClientProvider>` in `App.tsx` or `main.tsx`.

### Loading State
- **D-07:** While `/api/re/kpis` is fetching, each KPI card shows a **pulsing skeleton block** (`animate-pulse` Tailwind) of the same card dimensions. No layout shift when data arrives. No spinner.

### No-Data State
- **D-08:** When the active filters return zero matching loans (API returns zeros / nulls for all metrics), each KPI card displays **`–`** in the metric position, styled in `#94a3b8` (muted slate). The card label remains visible. No "No data" text, no zeros.
- **D-09:** Detection logic: treat `active_loan_count === 0` as the no-data signal. When the loan count is zero, all cards render with `–` regardless of the other field values.

### Click-to-Filter Behavior (UX-01)
- **D-10:** **Delinquency cards only are clickable.** Delinquent 30, Delinquent 60, and Delinquent 90+ cards have `cursor-pointer` and apply a filter on click.
- **D-11:** The `ReLoanFilters` schema does not currently include a delinquency bucket field. The planner must decide: either (a) add a `delinquency_bucket` field to `ReLoanFilters`, `FilterParams` in `re_schemas.py`, and the filter sidebar — or (b) treat the click as a visual highlight only for Phase 20 with a TODO comment marking this for a later phase. **Claude's Discretion: choose option (b) unless (a) is straightforward given the backend filter structure.**
- **D-12:** Non-delinquency cards (Total UPB, WAC, WAM, WA LTV, WA DSCR, Active Loan Count, Portfolio Yield) are **not clickable** — no cursor change, no click handler.

### Number Formatting
- **D-13:** Dollar amounts (Total UPB, delinquency bucket UPBs) are **abbreviated**: ≥$1B → `$X.XXB`, ≥$1M → `$X.Xm`, otherwise full with comma separators. E.g., `$1.23B`, `$456.7M`.
- **D-14:** Rate and percentage fields: **`x.xx%`** — WAC, WA LTV, Portfolio Yield all rendered as `5.25%`, `68.40%`, `6.12%`.
- **D-15:** WAM: **`xmo`** — e.g., `84mo`.
- **D-16:** DSCR: **`x.xxX`** — e.g., `1.45x`.
- **D-17:** Active Loan Count: plain **integer with comma separators** — e.g., `1,234`.
- **D-18:** Null values from the API (fields typed `number | null`) render as `–` in muted slate (same as no-data state). E.g., if WAC is null (no rate data yet), the WAC card shows `–`.

### Claude's Discretion
- KPI card component name and file path (suggestion: `frontend/src/components/re/KPICard.tsx`)
- Whether to create a `useKPIs()` custom hook or call `useQuery` directly in `ReDashboard.tsx`
- Exact Tailwind card styling details — follow TWG Global brand conventions from Phase 10/19 patterns
- Whether `<QueryClientProvider>` wraps the full app in `main.tsx` or just the RE dashboard subtree
- Whether to handle TanStack Query error state (network failure) with an error card or ignore for this POC

</decisions>

<specifics>
## Specific Details

- TWG Global brand: `#1a3868` navy (headings, active states), `#475569` slate text, `#94a3b8` muted, `#f8fafc` background, `border-gray-200`.
- Card label text should use `#475569` slate. Metric value uses a larger font — planner decides size (suggestion: `text-2xl` or `text-3xl font-bold`).
- The `KPIResponse` TypeScript interface is already defined in `frontend/src/types/re.ts` — do NOT redefine it.
- Phase verification requires non-zero values — seed data from Phase 17 must be running in the target environment.
- Delinquency card click behavior (D-11): the simpler path (b) is preferred to avoid scope creep into filter schema changes. The TODO comment should reference FILTER-01 for future follow-up.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §EXEC — EXEC-01, EXEC-02 (KPI card fields, loading/no-data requirements)
- `.planning/REQUIREMENTS.md` §UX — UX-01 (click-to-filter requirement)
- `.planning/REQUIREMENTS.md` §FILTER — FILTER-01 through FILTER-04 (filter field definitions and behavior)

### Prior Phase Decisions
- `.planning/phases/19-filter-hook-typescript-foundation/19-CONTEXT.md` — D-04 (TanStack Query deferred to Phase 20), D-07/D-08/D-09 (URL-as-source-of-truth, `filters` as query key), D-05 (raw Tailwind only)
- `.planning/phases/10-revamp-user-interface-phase-10/10-CONTEXT.md` — Brand colors and sidebar conventions

### Existing Frontend Code (read before modifying)
- `frontend/src/pages/ReDashboard.tsx` — Current placeholder; this file gets the KPI grid added
- `frontend/src/types/re.ts` — `KPIResponse` interface already defined here; also `ReLoanFilters`
- `frontend/src/hooks/useReLoanFilters.ts` — `useReLoanFilters()` hook; `filters` object is the TQ query key
- `frontend/src/stores/filterStore.ts` — Zustand filter store
- `frontend/src/App.tsx` — Where `<QueryClientProvider>` wrapper may be added

### Backend API
- `backend/api/re_routes.py` — `/api/re/kpis` endpoint implementation
- `backend/api/re_schemas.py` — `KPIResponse` Pydantic model (source of truth for field names/types)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useReLoanFilters()` (`frontend/src/hooks/useReLoanFilters.ts`) — Returns `{ filters, setFilter, clearFilters }`. Pass `filters` as TanStack Query key directly.
- `KPIResponse` interface (`frontend/src/types/re.ts:34-45`) — Already has all 10 fields typed. No redefinition needed.
- `ReDashboard.tsx` — Currently renders a flex container with the filter sidebar. KPI grid goes in the `flex-1` charts area div, replacing the placeholder `<p>` tag.

### Established Patterns
- Auth: `const { user } = useAuth()` if role-checking is needed
- Tailwind: inline string classes, no className helper libraries, no component library
- No index.ts barrel files — import directly from file path
- Axios is available (`axios` in dependencies) — use it for the API call inside `useQuery`

### Integration Points
- `frontend/src/pages/ReDashboard.tsx:7-9` — Replace `<p>Chart panels will appear here...</p>` with the KPI grid
- `frontend/src/App.tsx` — Wrap with `<QueryClientProvider>` (or `main.tsx` — planner decides)

### Not Yet Present (Phase 20 creates)
- No `@tanstack/react-query` in `package.json` — `npm install @tanstack/react-query` required
- No KPI card component
- No `useKPIs` hook (or inline `useQuery` call)

</code_context>

---

*Phase: 20-executive-summary-page*
*Context gathered: 2026-04-08 via /gsd-discuss-phase*
