# Phase 24: Origination Pipeline + Market Context - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the Origination Pipeline + Market Context page at `/re-dashboard/origination`, replacing the existing `ReStubPage` stub. Five panels: origination volume stacked bar, net growth KPI card, pipeline funnel horizontal bar, vintage analysis table, and market context section (rate cards + cap/vacancy table). All panels use Recharts and TanStack Query. Origination volume stacked bar supports click-to-filter by property type; all other panels are display-only.

This is the final chart page before Loan Detail (Phase 25) and Export (Phase 26). Completing this phase means all six RE dashboard sections are live.

</domain>

<decisions>
## Implementation Decisions

### Page Structure
- **D-01:** Single page `ReOriginationPage.tsx` at `/re-dashboard/origination`. Replaces the current `ReStubPage` stub in `App.tsx`. No new tab needed — "Origination" tab already exists in `ReDashboard.tsx`.
- **D-02:** Layout: 2×2 grid for origination panels (volume + net growth top row, funnel + vintage bottom row), then a full-width Market Context section below.

### Origination Volume (ORIGIN-01)
- **D-03:** Recharts `BarChart` with stacked bars. X-axis = month, segments = property types. Consistent with maturity profile chart pattern from RePortfolioPage.
- **D-04:** Click-to-filter: clicking a property type segment sets `filters.property_type` via `useReLoanFilters`. This is the only clickable panel on this page.

### Net Portfolio Growth (ORIGIN-02)
- **D-05:** Single KPI-style card showing gross origination volume as a dollar total for the filtered period. Payoff tracking is not in the current schema — POC shows net origination volume only. Label clearly: "Net Origination Volume" (not "Net Growth" which implies payoff subtraction).

### Pipeline Funnel (ORIGIN-03)
- **D-06:** Recharts horizontal `BarChart` — 4 bars (underwriting → approved → closing → funded), widest at top. Each bar shows loan count and UPB. Display-only, no click-to-filter.

### Vintage Analysis (ORIGIN-04)
- **D-07:** HTML table (not a chart). Rows = vintage years, columns = loan count, total UPB, avg LTV, avg DSCR, avg rate. Same styling pattern as TopExposuresTable in RePortfolioPage. Display-only.

### Market Context (MARKET-01, MARKET-02)
- **D-08:** Two KPI-style cards for 10Y Treasury and SOFR (value + trend direction arrow from API response). Below: compact HTML table for cap rates and vacancy rates by property type.
- **D-09:** Section subtitle disclaimer: "Indicative values — not connected to live feeds" in muted text below the "Market Context" heading. No per-card badges, no alert banners.
- **D-10:** Market context query uses a static query key (no filter params) — rates are global, not portfolio-specific. Same pattern as `ReCashFlowPage.tsx` which already consumes this endpoint.

### Claude's Discretion
- Color palette for stacked bar property type segments (reuse whatever palette exists in RePortfolioPage)
- Exact grid gap/spacing between panels
- Loading and empty state patterns (follow existing ChartCard patterns)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — ORIGIN-01, ORIGIN-02, ORIGIN-03, ORIGIN-04, MARKET-01, MARKET-02, UX-01

### Backend (already implemented)
- `backend/api/re_routes.py` — `/api/re/origination-pipeline` (API-08) and `/api/re/market-context` (API-09) endpoints
- `backend/api/re_schemas.py` — `OriginationPipelineResponse`, `MarketContextResponse`, and nested models

### Frontend (existing patterns to follow)
- `frontend/src/types/re.ts` — TypeScript interfaces already defined for both endpoints
- `frontend/src/pages/RePortfolioPage.tsx` — stacked bar chart pattern (maturity profile), TopExposuresTable pattern, ChartCard wrapper usage
- `frontend/src/pages/ReCashFlowPage.tsx` — market-context query pattern (static key, no filters)
- `frontend/src/pages/ReExecutiveSummaryPage.tsx` — KPI card pattern
- `frontend/src/pages/ReDashboard.tsx` — tab strip with "Origination" already present
- `frontend/src/App.tsx` — route at `/re-dashboard/origination` pointing to `ReStubPage` (replace)
- `frontend/src/hooks/useReLoanFilters.ts` — click-to-filter pattern
- `frontend/src/components/re/ReDashboardFilterSidebar.tsx` — filter sidebar

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChartCard` wrapper component — used by all chart pages for consistent card styling
- `useReLoanFilters` hook — filter state management and URL sync
- `formatUPB`, `formatPct`, `formatRate` — Decimal-safe formatters with `parseFloat(String(val))`
- Property type color palette — already defined in RePortfolioPage for donut chart
- `ResponsiveContainer` pattern from Recharts — all existing charts use this

### Established Patterns
- TanStack Query with filter object as query key for auto-refetch on filter change
- Market context uses static query key (no filters) — already proven in ReCashFlowPage
- Table components use raw Tailwind styling — no table library
- Click-to-filter wired via `useReLoanFilters().setFilter(key, value)`

### Integration Points
- `App.tsx` line 57: replace `ReStubPage` with `ReOriginationPage` import
- `ReDashboard.tsx` tab strip: "Origination" tab already wired to `/re-dashboard/origination`
- No backend changes needed — both API endpoints are implemented and tested

</code_context>

<specifics>
## Specific Ideas

- Pipeline funnel should show both loan count AND UPB per stage (not just one metric)
- Vintage table mirrors the TopExposuresTable look from Portfolio page
- Market Context rate cards use trend arrows (↑ ↓ →) from the API response `trend` field
- Net growth card explicitly labeled "Net Origination Volume" to avoid implying payoff subtraction

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-origination-pipeline-market-context*
*Context gathered: 2026-04-12*
