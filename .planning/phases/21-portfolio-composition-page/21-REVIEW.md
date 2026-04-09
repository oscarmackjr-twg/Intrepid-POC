---
phase: 21-portfolio-composition-page
reviewed: 2026-04-09T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - frontend/src/App.tsx
  - frontend/src/components/re/ChartCard.tsx
  - frontend/src/components/re/ConcentrationLimits.tsx
  - frontend/src/components/re/TopExposuresTable.tsx
  - frontend/src/pages/ReDashboard.tsx
  - frontend/src/pages/ReExecutiveSummaryPage.tsx
  - frontend/src/pages/RePortfolioPage.tsx
  - frontend/package.json
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-04-09
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Eight files comprising the phase-21 portfolio composition page were reviewed: the router wiring in `App.tsx`, three new reusable components (`ChartCard`, `ConcentrationLimits`, `TopExposuresTable`), the `ReDashboard` layout, `ReExecutiveSummaryPage`, `RePortfolioPage`, and `package.json`.

The component implementations are well-structured and consistent with existing patterns in the codebase. The main concerns are: a dependency version conflict in `package.json` that can silently produce two router contexts at runtime (critical), stale-closure risk on query params in `RePortfolioPage`, a misleading `isNoData` heuristic in `ReExecutiveSummaryPage`, and array-index keys on `Cell` elements that cause incorrect chart reconciliation on data updates.

---

## Critical Issues

### CR-01: Incompatible react-router major versions in package.json

**File:** `frontend/package.json:21-22`
**Issue:** `react-router` is pinned at `^7.11.0` while `react-router-dom` is pinned at `^6.30.2`. These are incompatible major versions. React Router v7 folded `react-router-dom` into `react-router`; listing both at different majors means npm will install two distinct copies of the router internals. At runtime this can produce two separate `RouterContext` instances, causing hooks like `useSearchParams`, `NavLink`, and `Outlet` to silently operate on different contexts — leading to filters not updating the URL, active-tab styling breaking, or child routes not rendering under the `ReDashboard` layout.

**Fix:** Align both to v6, or migrate both to v7. For the minimal-change fix (stay on v6):
```json
"react-router": "^6.30.2",
"react-router-dom": "^6.30.2"
```
If v7 is intentional, remove `react-router-dom` entirely and update all imports from `react-router-dom` to `react-router` (v7 exports everything from the root package).

---

## Warnings

### WR-01: Stale closure on `params` inside query functions

**File:** `frontend/src/pages/RePortfolioPage.tsx:28-55`
**Issue:** `params` is derived outside the three `queryFn` closures but captured by each of them. If `filters` changes between the point where `params` is computed and when TanStack Query invokes `queryFn` (which can happen asynchronously), all three queries will send the _previous_ filter values even though the `queryKey` (based on `filters`) has already changed. This produces a one-render lag where the UI reflects updated keys but the request carries stale params.

**Fix:** Move the `params` derivation inside each `queryFn`:
```typescript
const concentration = useQuery({
  queryKey: ['re-concentration', filters],
  queryFn: async () => {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== null && v !== '')
    )
    const { data } = await axios.get<ConcentrationResponse>('/api/re/concentration', { params })
    return data
  },
})
```
Apply the same pattern to `distributions` and `maturity`.

### WR-02: `isNoData` hides real KPI values when active_loan_count is legitimately 0

**File:** `frontend/src/pages/ReExecutiveSummaryPage.tsx:28`
**Issue:** `isNoData` is `true` when `data.active_loan_count === 0`. This causes every KPI card to display `–` instead of its actual value (e.g., `total_upb` could still be non-zero if loans were paid off mid-period, or `portfolio_yield` may have a valid value). Using `active_loan_count` as a proxy for "no portfolio" is fragile — a portfolio in run-off genuinely has 0 active loans while other metrics remain meaningful.

**Fix:** Gate on a field that truly signals "no data returned from the API," such as checking whether the response itself is absent, or add an explicit `has_data: boolean` field to `KPIResponse`. At minimum, scope the en-dash override only to `active_loan_count` itself rather than all cards:
```typescript
// Before:
const isNoData = !isLoading && data !== undefined && data.active_loan_count === 0

// After (conservative — only suppress the count card, show real values for others):
// Remove `isNoData` entirely; let formatters handle null via their own '\u2013' guard.
// The `isNoData || (!isLoading && rawValue === null)` flag on KPICard already handles nulls.
```

### WR-03: Pie `Cell` keyed by array index causes incorrect reconciliation

**File:** `frontend/src/pages/RePortfolioPage.tsx:91-93`
**Issue:** `Cell` elements use `key={i}` (array index). When `concentration.data.property_type` changes (e.g., a filter is applied that removes a property type), React matches old cells to new cells by position. A slice that was at index 2 before the filter will re-use the DOM node that previously rendered index 2, causing animated transitions and tooltip labels to mismatch temporarily. This is also flagged as an anti-pattern by the React docs for lists with changing order or length.

**Fix:** Use the category string as the key:
```tsx
{(concentration.data?.property_type ?? []).map((item, i) => (
  <Cell key={item.category} fill={PIE_COLORS[i % PIE_COLORS.length]} />
))}
```

---

## Info

### IN-01: Double type cast `as unknown as ConcentrationItem` weakens type safety in click handlers

**File:** `frontend/src/pages/RePortfolioPage.tsx:88, 115`
**Issue:** The Pie and Bar `onClick` handlers cast the Recharts event payload via `as unknown as ConcentrationItem`. Recharts delivers a `PieSectorDataItem` / `DefaultLegendContentProps` object, not a `ConcentrationItem`. The `'category' in entry` runtime guard makes this safe in practice today, but if the Recharts payload shape changes or `category` collides with a Recharts internal property, the cast will silently pass bad data to `setFilter`.

**Fix:** Extract the category value explicitly from the data array using the active index supplied by the event, or narrow the type properly:
```typescript
onClick={(_, index) => {
  const item = concentration.data?.property_type?.[index]
  if (item) setFilter('property_type', item.category)
}}
```
This eliminates the need for the double cast entirely.

### IN-02: Inert `onClick={undefined}` with TODO comment on table rows

**File:** `frontend/src/components/re/TopExposuresTable.tsx:29`
**Issue:** `onClick={undefined}` is a no-op and adds no value — React treats a missing `onClick` and `onClick={undefined}` identically. The comment correctly documents intent (Phase 25 side-panel), but the dead prop adds noise and could confuse future readers into thinking the handler is conditionally assigned.

**Fix:** Remove the prop until Phase 25 implements the handler:
```tsx
<tr
  key={loan.loan_number}
  className="border-b border-gray-100 text-[#1a3868]"
  // TODO: Phase 25 — wire row click to loan detail side-panel
>
```

---

_Reviewed: 2026-04-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
