# Phase 19: Filter Hook + TypeScript Foundation — Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the frontend infrastructure that every subsequent RE dashboard chart page will consume:
- `/re-dashboard` route wired into App.tsx and Layout
- `ReDashboardFilterSidebar` component (right panel, always visible)
- `useReLoanFilters` hook (URL ↔ Zustand sync)
- Zustand filter store (`useFilterStore`)
- `frontend/src/types/re.ts` — all TypeScript interfaces for RE API responses

Phase gate: filter panel renders on `/re-dashboard`, selecting a filter updates URL params + Zustand simultaneously, "Clear all filters" resets both, and all TypeScript types compile without error. No chart data, no API calls — infrastructure only.

</domain>

<decisions>
## Implementation Decisions

### Filter Sidebar Layout
- **D-01:** Filter panel is a **right-side panel**, always visible, fixed width `w-72` (288px).
- **D-02:** Page layout on `/re-dashboard`: nav sidebar (w-60) | charts area (flex-1) | filter panel (w-72). Three-column flex row within the existing `<main>` content area.
- **D-03:** Filter panel is **always open** — no toggle, no collapse. Mirrors the left nav pattern (Phase 10 decision: always-expanded sidebar). No open/close state needed.

### New Library Additions
- **D-04:** Add **Zustand only** in Phase 19. TanStack Query is NOT installed here — Phase 20 installs it when the first chart component needs data fetching.
- **D-05:** Filter input controls are built with **raw Tailwind** — `<select>`, `<input type="date">`, `<input type="number">` elements styled to match the existing TWG Global brand (`#1a3868` navy). No component library (shadcn/ui, Headless UI) added.
- **D-06:** Filter controls per field:
  - `as_of_date` → `<input type="date" />`
  - `property_type` → `<select>` single-select (dropdown)
  - `state` → `<select>` single-select
  - `msa` → `<select>` single-select
  - `loan_size_min` / `loan_size_max` → two `<input type="number">` fields (min/max pair)
  - `risk_rating` → `<select>` single-select
  - `vintage_year` → `<select>` single-select
  - `borrower` → `<input type="text">` (partial match, case-insensitive per re_schemas.py)
  - `rate_type` → `<select>` single-select

### URL ↔ Zustand Sync Strategy
- **D-07:** **URL is source of truth.** `useReLoanFilters` reads from `useSearchParams()` on every render and writes to URL (via `setSearchParams`) when any filter changes. Zustand store is a mirror/cache — it reflects URL state.
- **D-08:** Hydration flow: on page load (or when URL changes externally, e.g. manual edit or back/forward), the hook reads URL params → updates Zustand store → returns the current filter object.
- **D-09:** The hook signature: `useReLoanFilters()` returns `{ filters: ReLoanFilters, setFilter, clearFilters }`. `filters` is the current filter object derived from URL params. This object serves as the TanStack Query key in Phase 20 — changing any filter causes the key object to change, triggering automatic refetch. No explicit `queryClient.invalidateQueries` in the hook.
- **D-10:** "Clear all filters" calls `clearFilters()` which calls `setSearchParams({})` (removes all filter query params from URL). Zustand store resets to defaults in the same action.

### TypeScript Types
- **D-11:** Types are **hand-written** in `frontend/src/types/re.ts`. No OpenAPI code-generation tooling. Types mirror `backend/api/re_schemas.py` — updated manually when schemas change.
- **D-12:** Monetary and rate fields typed as `number` in TypeScript. FastAPI serializes Python `Decimal` to JSON number. Frontend displays only — no precision arithmetic in the frontend.
- **D-13:** All filter param fields are `string | null` in the frontend type (URL params are strings; conversion to backend types happens at the API boundary). Exception: `loan_size_min`/`loan_size_max` are `number | null` (input type=number returns a number).

### Route Integration
- **D-14:** Add `/re-dashboard` route to `frontend/src/App.tsx` under the existing `<ProtectedRoute><Layout />` wrapper. No new Layout component — reuse the existing one.
- **D-15:** Add "RE Dashboard" nav link to `frontend/src/components/Layout.tsx` sidebar nav list. Placement: top-level item (not nested under a group).

### Claude's Discretion
- Zustand store file path and store shape (planner decides; suggestion: `frontend/src/stores/filterStore.ts`)
- Whether `useReLoanFilters` lives in `hooks/useReLoanFilters.ts` or alongside the store
- Exact Tailwind styling details for the filter panel (follow existing TWG Global brand patterns)
- Whether filter selects are populated with hardcoded option lists or left empty for Phase 20 to populate dynamically from API

</decisions>

<specifics>
## Specific Details

- TWG Global brand colors: `#1a3868` (navy), `#475569` (slate text), `#94a3b8` (muted), `#f8fafc` (background). Border: `border-gray-200`. Active nav: `border-l-4 border-[#1a3868]`.
- Filter panel header should include a "Clear all filters" button/link — required by FILTER-04.
- The Zustand store is scoped to the RE dashboard (not global app state). `useFilterStore` is the store hook.
- Phase verification gate (from ROADMAP.md success criteria):
  1. Filter sidebar renders on `/re-dashboard` with all 9 controls visible
  2. Selecting a filter updates URL params + Zustand simultaneously (no page reload)
  3. "Clear all filters" resets both URL params and store in one action
  4. Changing any filter causes all TanStack Query keys to invalidate — verified by watching network requests (Phase 20 concern, but the hook must be structured so this works)

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §FILTER — FILTER-01 through FILTER-04 (full filter field list and behavior)

### Existing Frontend Code
- `frontend/src/App.tsx` — Route definitions; add `/re-dashboard` route here
- `frontend/src/components/Layout.tsx` — Nav sidebar; add RE Dashboard nav link here
- `frontend/src/contexts/AuthContext.tsx` — Auth context pattern (`useAuth()`)

### Backend Schemas (for TypeScript type mirroring)
- `backend/api/re_schemas.py` — All Pydantic response models and `FilterParams` definition

### Phase 10 UI Decisions
- `.planning/phases/10-revamp-user-interface-phase-10/10-CONTEXT.md` — Brand colors, sidebar width, TWG Global styling conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Integration Points
- `frontend/src/App.tsx:21-40` — `<Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>` block; add `<Route path="re-dashboard" element={<ReDashboard />} />` inside it
- `frontend/src/components/Layout.tsx` — Nav list section; add `<Link to="/re-dashboard">` styled identically to existing nav links
- `frontend/src/main.tsx` — Zustand Provider not needed (Zustand doesn't require a Provider; import store hook directly)

### Established Patterns to Follow
- Auth: `const { user } = useAuth()` — same pattern for role-checking if needed on the RE dashboard
- Routing: `useLocation()` + `pathname.startsWith(...)` for active nav link detection
- Tailwind: no `className` helper libraries; inline string concatenation with template literals (existing pattern)
- No index.ts barrel files in existing codebase — import directly from file path

### Not Yet Present (Phase 19 creates)
- No Zustand in package.json — `npm install zustand` required
- No `/re-dashboard` route
- No `frontend/src/types/` directory
- No `frontend/src/stores/` directory
- No `frontend/src/hooks/useReLoanFilters.ts`

</code_context>

---

*Phase: 19-filter-hook-typescript-foundation*
*Context gathered: 2026-04-08 via /gsd-discuss-phase*
