# PITFALLS — RE Loan Portfolio Dashboard (v2.0 Milestone)

**Project:** Intrepid Loan Purchase Platform — v2.0 Real Estate Dashboard POC
**Research type:** Pitfall Analysis — Adding a data-heavy financial dashboard to an existing production system
**Date:** 2026-04-08
**Scope:** 9 feature areas: KPI cards, portfolio composition, credit quality, cashflow performance, origination pipeline, market context stubs, global filtering, drill-down, PDF/CSV export, role-based view stub

---

## How to Use This Document

Each pitfall entry follows this structure:

- **What goes wrong** — the concrete failure mode
- **Why it happens** — root cause, so you recognize it early
- **Prevention** — concrete, actionable steps (not "be careful")
- **Phase** — when this must be addressed in the roadmap

Pitfalls are ordered within each section by severity. Read all of them; the worst ones compound.

---

## 1. Data Model Pitfalls

### 1.1 Using Float for Any Monetary or Rate Field in the Seed Schema

**What goes wrong:** A developer defines `upb FLOAT`, `coupon_rate FLOAT`, or `ltv FLOAT` in the PostgreSQL seed schema because it's the path of least resistance. SQLAlchemy's ORM returns Python `float` objects by default. Aggregations across 500–5,000 loans accumulate floating-point error. WAC computed as `SUM(balance * rate) / SUM(balance)` drifts by several basis points when rates are stored as IEEE 754 floats. KPI cards show values that disagree with spreadsheet calculations by small but detectable amounts — enough to undermine credibility with a financial audience.

**Why it happens:** PostgreSQL's `FLOAT` and `DOUBLE PRECISION` types are easier to declare than `NUMERIC`. SQLAlchemy's `Float` column type is the obvious default. The PROJECT.md already mandates `NUMERIC(18,6)` but schema authors under time pressure skip it.

**Prevention:**
- Define every monetary column (`upb`, `original_balance`, `scheduled_payment`, `noi`, etc.) as `NUMERIC(18,6)` in the Alembic migration. Never use `FLOAT` or `DOUBLE PRECISION`.
- Define every rate column (`coupon_rate`, `dscr`, `ltv`, `spread`) as `NUMERIC(10,6)` — six decimal places covers basis-point precision.
- In SQLAlchemy models, use `Numeric(18, 6, asdecimal=True)` so the ORM returns `decimal.Decimal` objects, not Python floats. The `asdecimal=True` flag is not the default; it must be set explicitly.
- In FastAPI response schemas (Pydantic), serialize `Decimal` fields as strings or use `Decimal` type with a custom JSON encoder. Do not let Pydantic silently convert to float in the API response.
- Write a schema test that asserts column types via `information_schema.columns` — fail CI if any monetary column is not `numeric`.

**Phase:** Data Seed Schema (Phase 1 of milestone) — fix before any data is loaded. Retrofitting types after seeding requires a migration + data recast, which is painful.

---

### 1.2 Nullable Traps in Aggregation Columns

**What goes wrong:** The seed schema allows `NULL` in columns like `dscr`, `noi`, `maturity_date`, or `risk_rating` to reflect "unknown" values in real loan data. A WAC query using `SUM(balance * rate) / SUM(balance)` silently excludes any loan with a `NULL` rate (SQL `NULL` propagates through arithmetic). The KPI card shows a WAC that is systematically biased toward loans with known rates — which may be the highest-quality loans in the pool — without any warning to the user.

**Why it happens:** Nullable columns are correct for data quality reasons. The trap is not the nullability itself; it is failing to account for nulls in every aggregation query and failing to surface the "N loans excluded" count to the user.

**Prevention:**
- For every aggregation endpoint, explicitly count `NULL` exclusions: `COUNT(*) FILTER (WHERE rate IS NULL) AS excluded_from_wac`. Return this count in the API response alongside the aggregate value.
- Display "Based on X of Y loans (Z excluded — rate unknown)" on KPI cards where exclusions occur. Never silently drop loans from calculations.
- In SQL aggregations, use `COALESCE` only when a business-defined default exists and is documented. Do not use `COALESCE(rate, 0)` to avoid nulls in rate fields — a zero rate is wrong, not neutral.
- Document the null-handling rule per column in a data dictionary (even a simple table in the seed migration's docstring).

**Phase:** Data Seed Schema + Aggregation API (Phases 1–2 of milestone).

---

### 1.3 Treating "As-Of Date" as a Simple WHERE Clause

**What goes wrong:** The global filter includes an "as-of date" field. A developer implements it as `WHERE origination_date <= as_of_date` — filtering originations up to the chosen date. But "as-of date" in a loan portfolio context means: show the portfolio state as it existed on that date — including loans that were active on that date but have since paid off, matured, or defaulted. A simple date filter on origination does not produce this. Users selecting a past as-of date see a portfolio that never existed.

**Why it happens:** The temporal semantics of "portfolio state at a point in time" are not obvious to developers without loan portfolio domain knowledge. It requires a different schema design: either a status-history table, period-of-validity columns (`valid_from`, `valid_to` on each status), or a snapshot table per reporting period.

**Prevention:**
- Define the as-of date semantic precisely before writing any query: "Show all loans that had active status on or before `as_of_date` and had not yet reached their final payoff or maturity date." Document this definition in a comment in the aggregation endpoint.
- For a POC with seeded data, simplify by seeding a single snapshot state and clearly labeling the as-of date as "current portfolio date" — do not promise time-travel filtering unless the schema supports it.
- If time-travel is desired, add `status_effective_date` and `status_end_date` columns to the loan table during seed schema design, not as a retrofit. A retrofit requires reseeding.
- Guard the API: if a caller passes an as-of date earlier than the earliest seed data date, return a clear error rather than an empty result set.

**Phase:** Data Seed Schema (Phase 1) — schema design decision. Aggregation API (Phase 2) — query implementation.

---

## 2. Aggregation Calculation Pitfalls

### 2.1 Incorrect Weighting in WAC, WAM, WA-LTV, and DSCR

**What goes wrong:** WAC (Weighted Average Coupon) is defined as `SUM(upb * coupon_rate) / SUM(upb)` — weighted by current outstanding balance. Developers who are unfamiliar with the convention implement it as a simple average (`AVG(coupon_rate)`) or weight by original balance instead of current UPB. For a portfolio with significant paydown history, the difference between a simple average and UPB-weighted average can be 20–50 basis points. Finance stakeholders will catch this immediately.

**Why it happens:** "Weighted average" is used colloquially to mean different things. The weight variable (current UPB vs. original balance vs. loan count) differs by metric and is not obvious without domain knowledge.

**Prevention:**
- Define the exact formula for each metric in a comment above the SQL query or Python calculation, citing the convention (e.g., "WAC = SUM(current_upb * coupon_rate) / SUM(current_upb), per MBS convention"):
  - WAC: weight by current UPB
  - WAM: weight by current UPB, result in months remaining to maturity
  - WA-LTV: weight by current UPB, use current appraised value (not original)
  - WA-DSCR: weight by current UPB (exclude loans with NULL DSCR and flag the count)
- Write unit tests with a three-loan synthetic portfolio where the expected output is hand-calculated. Assert exact decimal equality (not approximate) at the expected precision.
- Have a finance stakeholder sign off on the formula definitions before implementation, not after.

**Phase:** Aggregation API (Phase 2 of milestone).

---

### 2.2 Division by Zero in Aggregations When Filters Produce Empty Subsets

**What goes wrong:** A user applies a combination of global filters (e.g., property type = "Office" + risk rating = "Watch" + state = "Montana") that matches zero loans. The WAC aggregation performs `SUM(upb * rate) / SUM(upb)` where `SUM(upb)` is zero. PostgreSQL returns `NULL` for division by zero in this case (not an error), but the API serializes `NULL` as `null` in JSON, which the frontend renders as "—" or crashes on if not null-guarded. KPI cards go blank without explanation.

**Why it happens:** Developers test with the full dataset where denominators are never zero. Filter combinations that produce empty subsets are not tested.

**Prevention:**
- Wrap every division in SQL using `NULLIF`: `SUM(upb * rate) / NULLIF(SUM(upb), 0)`. Always.
- In the API response schema, handle `None` explicitly for every aggregate field and return a structured response indicating whether the value is `null` due to no-data or due to exclusions: `{"wac": null, "wac_loan_count": 0, "wac_excluded": 0}`.
- In the React frontend, every KPI card must have a `noData` render state distinct from a loading state and an error state. "No loans match the current filters" is a valid state, not a bug.
- Test filter combinations that produce zero results in integration tests.

**Phase:** Aggregation API (Phase 2) + KPI Card component (Phase 3).

---

### 2.3 CPR Calculation Using the Wrong Formula

**What goes wrong:** CPR (Conditional Prepayment Rate) is correctly defined as an annualized rate derived from SMM (Single Monthly Mortality): `CPR = 1 - (1 - SMM)^12`. Developers who are unfamiliar with the convention compute it as `total_prepayments / starting_balance` — which is the annual CPR only if prepayments happen to equal one year's worth, and is simply wrong otherwise. Or they compute SMM as `prepayments_this_month / starting_balance_this_month` but use ending balance instead of starting balance. For a POC with seeded data, the error may not be visible, but it will surface when real data is applied.

**Why it happens:** CPR has a specific industry definition that is not documented in most general programming resources. Developers derive their own formula from first principles and get it wrong.

**Prevention:**
- Use the canonical formula: `SMM_t = prepayments_t / (starting_balance_t - scheduled_principal_t)`. Then `CPR = 1 - (1 - SMM)^12`. Document the source (e.g., dv01 CPR Calculation support article, or Fannie Mae Benchmark CPR methodology).
- For a POC with seeded data where you control prepayment history, consider computing CPR as a derived/display value from the seed data directly rather than from a formula applied to simulated monthly cashflows — this avoids implementing the full SMM → CPR pipeline for a POC.
- If CPR is computed from actual cashflow data, write a test using the three-loan example from the Open Risk Manual or dv01 documentation where the answer is known.

**Phase:** Aggregation API (Phase 2) — cashflow performance endpoints.

---

### 2.4 Histogram Bucket Boundary Off-By-One Errors

**What goes wrong:** LTV histogram with buckets `[0-60, 60-70, 70-80, 80+]`: a loan with LTV exactly 70 is counted in both the 60-70 bucket and the 70-80 bucket (or in neither) depending on whether bucket boundaries are inclusive or exclusive. The total loan count across all histogram bars does not equal the total portfolio loan count. A finance stakeholder adds up the bars and notices.

**Why it happens:** SQL `CASE WHEN ltv < 60` vs `CASE WHEN ltv <= 60` is easy to get wrong, especially across multiple metrics where the convention varies.

**Prevention:**
- Use a consistent, documented convention: lower-bound inclusive, upper-bound exclusive (e.g., `[70, 80)` means `ltv >= 70 AND ltv < 80`). Apply this consistently across all histograms.
- Write a test that asserts: `SUM of all histogram bucket counts == total loan count for that filter`. This catches off-by-one errors immediately.
- For the top-open bucket (`80+`), use `ltv >= 80` explicitly, not `ltv > 79`.

**Phase:** Aggregation API (Phase 2) + Chart components (Phase 3).

---

### 2.5 Delinquency Rate Defined Inconsistently

**What goes wrong:** "Delinquency rate" is used in three different ways in practice: (1) count of loans 30+ DPD / total active loans, (2) UPB of loans 30+ DPD / total active UPB, (3) count of loans in any delinquency bucket / total. A chart labeled "Delinquency Rate" could mean any of these. Different stakeholders interpret it differently. If two KPI cards on the same dashboard use different definitions, finance stakeholders will notice the inconsistency in the numbers.

**Why it happens:** The term is ambiguous and developers pick whichever interpretation is easiest to query.

**Prevention:**
- Define delinquency rate as UPB-weighted by convention for the portfolio dashboard (consistent with the WAC/WAM weighting convention). Label it explicitly: "Delinquency Rate (% UPB, 30+ DPD)."
- Use the same denominator everywhere: active UPB only (exclude paid-off, matured, or charged-off loans from the denominator unless explicitly showing a historical metric).
- Document the definition in a comment in the aggregation query and on the UI tooltip/footnote.

**Phase:** Aggregation API (Phase 2) — define before implementing any delinquency display.

---

## 3. Filtering Pitfalls

### 3.1 Prop-Drilling Global Filter State Through Existing Page Components

**What goes wrong:** The dashboard has 9 feature areas and a global filter sidebar. A developer passes filter state via React props from the top-level Dashboard page down through section components. The existing app has its own component tree (Dashboard, RunDetail, ProgramRuns, CashFlow, Exceptions, FileManager). Adding a prop-drilled filter state to the new dashboard page forces every new chart component to accept filter props, and any future change to the filter shape requires touching every component in the chain.

**Why it happens:** Prop drilling is the path of least resistance for small component trees. It becomes unmanageable at 6+ levels or with 7+ filter dimensions.

**Prevention:**
- Use Zustand for the dashboard filter store. Scope it to the dashboard module: a `useDashboardFilterStore` hook that is only imported by dashboard components. Do not use React Context (which causes whole-tree re-renders on any filter change) and do not use Redux (overkill for a POC).
- The Zustand store lives in `frontend/src/features/dashboard/store/filterStore.ts`. Dashboard components import directly from there. The existing app's pages are not touched.
- The store shape: `{ asOfDate, propertyTypes, states, loanSizeRange, riskRatings, vintageRange, borrower, rateType, setFilter, resetFilters }`.
- Do not initialize the filter store in the app root — initialize it lazily when the dashboard feature is first mounted.

**Phase:** Global Filter (Phase 4 of milestone) — store design before any chart component is written.

---

### 3.2 Server vs. Client Filtering — Wrong Decision Causes Either Performance Problems or Stale Data

**What goes wrong:** A developer fetches the entire loan dataset to the client and filters in JavaScript (client-side filtering). With 5,000 seed loans and 9 filter dimensions, this means ~2MB of JSON on every page load, with re-filtering on every filter change running in the browser's main thread. Alternatively, a developer makes a new API call for every filter change without debouncing, generating 7 rapid API calls when a user adjusts a range slider.

**Why it happens:** Client-side filtering feels simpler to implement initially. Server-side filtering requires API parameter design and debouncing logic.

**Prevention:**
- All filtering is server-side. The client sends filter parameters to the API on every filter change; the server runs the SQL WHERE clause and returns pre-aggregated results. Never send raw loan-level data to the client for client-side filtering.
- Debounce filter changes: use a 400ms debounce on range slider inputs before triggering API calls. Discrete filter changes (checkbox, dropdown) can trigger immediately.
- Use React Query (TanStack Query) for all dashboard data fetching. The query key includes the filter object: `['portfolio', 'kpis', filterState]`. Filter changes automatically invalidate and refetch the right queries.
- The API accepts a flat filter parameters object (query string or POST body) — not a GraphQL query or complex filter DSL. Keep it simple for a POC.

**Phase:** Aggregation API (Phase 2) + Global Filter (Phase 4).

---

### 3.3 Filter State Not Persisted in URL — Users Cannot Share or Bookmark a View

**What goes wrong:** A user configures a specific filter combination to show a watchlist view (Office loans, Watch-rated, Eastern states). They want to share it with a colleague or bookmark it. Filter state is in Zustand only — refreshing the page resets to defaults. This is a minor UX problem for a POC but becomes a significant friction point during stakeholder demos.

**Why it happens:** URL synchronization requires additional boilerplate and developers defer it.

**Prevention:**
- Use `nuqs` (Next.js) or a hand-rolled URL sync hook to persist filter state in the URL query string. For React Router (which this app likely uses), implement a `useFilterSync` hook that reads initial state from `URLSearchParams` and writes changes back via `useSearchParams`.
- Serialize only non-default filter values into the URL to keep it readable. Empty/default filters produce a clean URL.
- This is low-effort for a POC if built from the start. It is painful to retrofit after the filter store is wired to 9 components.

**Phase:** Global Filter (Phase 4) — implement alongside the filter store, not after.

---

## 4. Chart Library Pitfalls

### 4.1 Recharts SVG Re-Renders Causing Jank When Global Filters Change

**What goes wrong:** Every filter change triggers a re-fetch of all aggregated data. When data arrives, every chart on the page re-renders simultaneously — 8–12 SVG charts re-rendering at once causes a visible frame drop on mid-range hardware. For a financial dashboard where stakeholders are doing live demos, this is a credibility problem.

**Why it happens:** React re-renders all chart components when the parent's data state updates, even if a specific chart's data didn't change. Recharts re-creates the entire SVG on each render by default.

**Prevention:**
- Wrap each chart component in `React.memo` with a custom comparison function that compares the chart's specific data slice, not the full filter object.
- Fetch data per chart section independently (React Query, separate query keys) rather than one monolithic endpoint. This means charts that don't depend on a changed filter don't re-render.
- Use `useMemo` for computed data transformations (e.g., converting raw aggregation results to Recharts `data` array format) so the transformation does not rerun on unrelated renders.
- Stagger chart loading with `Suspense` boundaries per section so the page doesn't attempt to render all charts simultaneously on initial load.

**Phase:** Chart Components (Phase 3 of milestone).

---

### 4.2 Geo Heatmap Is a Rabbit Hole — Underestimate at Your Peril

**What goes wrong:** "US geo heatmap by state/MSA" sounds like a single chart component. In practice it requires: loading a TopoJSON file (~300KB for US states), D3-geo projection setup (Albers USA), color scale normalization per metric, hover tooltip with state name and value, click-to-filter integration, and responsive sizing. MSA-level (Metropolitan Statistical Area) maps require a separate, larger TopoJSON and FIPS code mapping. A developer who estimates this as "2 days" will spend a week on it.

**Why it happens:** Geo visualization is categorically more complex than bar/pie/line charts. It has its own coordinate system (geographic projections), data format (TopoJSON/GeoJSON), and library ecosystem (D3-geo, react-simple-maps) that is separate from the rest of the chart stack.

**Prevention:**
- For the POC, implement state-level only (not MSA). MSA-level is deferred post-POC.
- Use `react-simple-maps` rather than raw D3 for the React integration layer. It handles projection setup and React lifecycle correctly. Add `d3-scale-chromatic` for color scales.
- Time-box the geo heatmap to 3 days. If it takes longer, replace with a ranked bar chart (Top States by UPB) as the fallback for the POC — this conveys the same information for a demo.
- Source the TopoJSON from a CDN or bundle the US states TopoJSON statically (it's ~200KB compressed and doesn't change). Do not fetch it from an external API at runtime.

**Phase:** Chart Components (Phase 3) — plan with fallback option explicitly in the phase plan.

---

### 4.3 React 19 Compatibility Issues With Older Chart Libraries

**What goes wrong:** Some chart libraries have not been tested against React 19's concurrent rendering changes. Specifically, libraries that use `ReactDOM.render` internally (deprecated in React 18, removed-from-default in React 19) or that have incorrect `useEffect` dependencies that assume synchronous rendering will behave unexpectedly. Chart.js wrappers (`react-chartjs-2`) and some D3-React integration layers have known issues.

**Why it happens:** React 19 was released in December 2024. Many libraries updated for React 18 but not yet for React 19's stricter concurrent mode behavior.

**Prevention:**
- Use Recharts (v2.x) as the primary chart library — it is built on React primitives natively and has explicit React 19 compatibility.
- Before adding any chart library, check its GitHub issues for "React 19" — look for open issues within the last 6 months.
- Avoid `react-chartjs-2` in this stack — it wraps Chart.js (Canvas-based) with a React layer that has historically lagged React version compatibility.
- If a library is needed for a specific chart type (e.g., `react-simple-maps` for geo), install it and render a basic test chart in isolation before wiring it to real data.

**Phase:** Chart Components (Phase 3) — validate library compatibility in a spike before committing.

---

## 5. PDF Export Pitfalls

### 5.1 Blank Charts in PDF Capture Due to Render Timing

**What goes wrong:** The PDF export captures a snapshot of the dashboard using `html2canvas`. Charts rendered with SVG (Recharts) or Canvas (ECharts) are frequently blank or partially rendered in the captured PDF because `html2canvas` runs before the chart animation completes or before the SVG is fully painted. The user downloads a PDF with all KPI cards visible but charts that are empty boxes.

**Why it happens:** `html2canvas` does not wait for SVG animations or async rendering to complete. Chart libraries use `requestAnimationFrame` for initial rendering, and `html2canvas` may fire between frames.

**Prevention:**
- Disable all chart animations for the PDF export render: set `isAnimationActive={false}` on Recharts components (or equivalent flag) before capturing. Re-enable after capture.
- Use an explicit delay (`setTimeout(capture, 500)`) after triggering the export to allow the final render frame to complete. 500ms is empirically reliable for Recharts SVG on mid-range hardware.
- Alternatively, use `html-to-image` (which uses SVG serialization) instead of `html2canvas` (which rasterizes the DOM). SVG serialization is more reliable for chart content.
- Test PDF export with the full dashboard populated — not just a single chart in isolation.

**Phase:** Export (Phase 6 of milestone).

---

### 5.2 CSS That Works in Browser But Breaks in PDF Capture

**What goes wrong:** The dashboard uses CSS Grid and Flexbox for layout. `html2canvas` does not support all CSS properties: `position: sticky` headers are captured at their sticky position and overlap content, `backdrop-filter` (glass morphism) renders as transparent, CSS custom properties (variables) inside SVG elements are not resolved, and `overflow: hidden` containers clip content that overflows in the captured canvas.

**Why it happens:** `html2canvas` implements a subset of CSS. Properties that require browser-native rendering (compositing, blur, sticky positioning) are not supported.

**Prevention:**
- Apply a `pdf-export` CSS class to the root element before capture and use it to override problematic styles: disable sticky positioning, remove backdrop filters, ensure all containers have explicit dimensions rather than `auto`.
- Test the PDF export on every major section of the dashboard before the export phase is "done." One un-tested section will have a layout problem.
- Consider a server-side PDF approach (Playwright headless Chrome on the FastAPI server rendering a print-specific dashboard URL) for higher fidelity. The tradeoff is backend complexity; client-side html2canvas is sufficient for a POC if tested.

**Phase:** Export (Phase 6) — also requires a print-specific CSS review in the Chart Components phase.

---

### 5.3 Large Export Memory Issues in the Browser

**What goes wrong:** A dashboard with 12 charts is captured as 12 separate high-resolution canvas elements, then merged into a multi-page PDF using jsPDF. The total in-memory canvas allocation can exceed 500MB on a browser with many high-resolution displays (devicePixelRatio = 2 on Retina screens), causing the tab to crash mid-export.

**Why it happens:** `html2canvas` with `scale: window.devicePixelRatio` on a Retina display at 2560px wide produces a canvas element that is 5120px × very-tall-px. Each canvas is ~80MB uncompressed.

**Prevention:**
- Cap the capture scale at 1.5 (not `window.devicePixelRatio`) — this balances quality and memory.
- Capture and release each section sequentially: capture section → add to PDF page → null the canvas reference → capture next section. Do not hold all canvases in memory simultaneously.
- For a POC, a single-page PDF with reduced resolution is acceptable. Document the limitation explicitly.

**Phase:** Export (Phase 6).

---

## 6. Role-Based View Pitfalls

### 6.1 A View Stub That Cannot Be Made Real Without a Rewrite

**What goes wrong:** The "role-based view stub" is implemented as a React-side check: `if (user.role === 'advisor') { filter by advisorId }`. The advisorId filter is applied in the frontend before the API call, or is passed as an optional query param that the API ignores when not present. When the stub needs to become real security, the API must be changed to enforce the filter server-side — but by then the API shape has been built for the `if (role)` pattern and the retrofit is extensive.

**Why it happens:** Frontend role gating feels like "we can always harden it later." In a financial system, "later" means a rewrite of every aggregation endpoint.

**Prevention:**
- Even for a stub, pass the scoping parameter from the authenticated user's JWT claims, not from the frontend. The API reads `user.advisor_id` from the token (set to `NULL` for PM role) and applies it in the WHERE clause: `WHERE (advisor_id = :advisor_id OR :advisor_id IS NULL)`. This query works for both roles with no API surface change when the stub becomes real.
- Never implement the advisor filter as a frontend-only filter that sends different API calls based on role. The backend must enforce scope, even in POC form.
- Do not expose PM-scoped aggregate endpoints to advisor-role users even in the stub. Implement the route decorator now: `@require_role("pm")` on PM-only endpoints. Raise 403 for advisors hitting those endpoints. The stub is complete when the 403 is returned correctly, not when the UI hides the button.

**Phase:** Role Stub (Phase 7 of milestone) — but the API scoping pattern must be decided in the Aggregation API phase (Phase 2) because it affects every endpoint signature.

---

### 6.2 JWT Claims Not Sufficient for Row-Level Scoping

**What goes wrong:** The existing auth system issues JWTs with a `role` claim but no `advisor_id` or `book_id` claim. Implementing the advisor scope requires adding a new claim to the token, which requires changing the token issuance code, invalidating existing sessions, and potentially changing how the existing pages read user identity. This breaks the existing system while adding the dashboard.

**Why it happens:** Adding claims to an existing JWT schema is a cross-cutting change that is not visible from the dashboard feature branch.

**Prevention:**
- Audit the existing JWT payload before designing the role stub. Check what claims are present: `user_id`, `role`, `email` are common; `advisor_id` or `book_id` may not be.
- If `advisor_id` is not present, add it to the JWT payload as part of the dashboard phase, with `advisor_id: null` for PM users. This is a backward-compatible addition.
- Do not change the JWT secret or algorithm — only add a new claim field. Existing tokens will still validate; they just won't have the new claim, which the app can handle with a default.

**Phase:** Role Stub (Phase 7) — but requires a one-time JWT payload audit at project start.

---

## 7. Integration Pitfalls (Existing System)

### 7.1 Alembic Migration Conflicts Between Dashboard Schema and Existing Migrations

**What goes wrong:** The existing app has a migration history for `loan_facts`, `loan_exceptions`, `program_runs`, and supporting tables. Adding the dashboard requires new tables: `re_loans`, `re_loan_metrics`, `market_data_stubs`. A developer creates the new migration from the feature branch. When merged, Alembic has multiple heads — the existing head and the new dashboard head. `alembic upgrade head` fails with a "Multiple head revisions" error. Deployment to staging breaks.

**Why it happens:** Working on a feature branch while the main branch's migration history was updated, without running `alembic merge heads` before finalizing the branch.

**Prevention:**
- All new dashboard migrations must chain off the current head of `main` at the time of implementation. Check `alembic heads` before writing any new migration revision.
- After merging to `main`, immediately run `alembic upgrade head` locally to confirm no multiple-heads error.
- In the CI/CD pipeline, add a step that runs `alembic upgrade head` against a fresh test database before the build passes. This catches migration conflicts before staging deployment.
- Dashboard tables use distinct names (`re_loans`, `re_portfolio_*`) and do not alter any existing table. All dashboard schema additions are purely additive — no `ALTER TABLE` on existing tables.

**Phase:** Data Seed Schema (Phase 1) — migration design must account for the existing history.

---

### 7.2 New React Router Routes Breaking Existing Page Navigation

**What goes wrong:** Adding `/dashboard/portfolio` (the new RE dashboard) as a route conflicts with the existing `/dashboard` route (the existing ops dashboard). React Router's route matching resolves `/dashboard/portfolio` to the existing `/dashboard` component with `portfolio` as an unhandled path segment, rendering the wrong page. Or, a new `<Route>` wrapper added at the app level re-renders the entire app on dashboard navigation, causing all existing pages to lose their scroll position and component state.

**Why it happens:** Adding routes to an existing React Router configuration without reading the existing route structure carefully.

**Prevention:**
- Read the existing `App.tsx` route configuration fully before adding any new routes.
- Use a dedicated route prefix for the dashboard feature: `/re-dashboard` or `/portfolio`. Do not use `/dashboard` (already taken by the ops dashboard).
- Wrap dashboard routes in a nested `<Route path="/portfolio">` with a `<Outlet>` — this scopes all dashboard sub-routes without touching the existing route definitions.
- Add the new route import with `React.lazy()` so the dashboard bundle is code-split and does not increase the existing pages' load time.

**Phase:** Integration Setup (Phase 1 or early Phase 3) — resolve before writing any dashboard page component.

---

### 7.3 Zustand Store Polluting Existing App State

**What goes wrong:** The dashboard's Zustand filter store is initialized at the app root (inside `main.tsx` or `App.tsx`) to make it available everywhere. Existing pages that do not need filter state begin re-rendering when dashboard filters change because they are subscribed to the same store root. Or, a developer uses the same Zustand store for both dashboard filters and a different global concern, and the two get entangled.

**Why it happens:** Zustand stores are module-level singletons. They are initialized when first imported, not when the component mounts. An import from `App.tsx` means the store is always initialized.

**Prevention:**
- The dashboard filter store is only imported inside dashboard feature components (`src/features/dashboard/`). It is never imported in `App.tsx`, `main.tsx`, or any existing page.
- Use Zustand's built-in selector pattern so components only re-render when their specific slice of state changes: `const propertyTypes = useDashboardFilterStore(s => s.propertyTypes)`.
- Name the store `useDashboardFilterStore` (not `useFilterStore` or `useAppStore`) to make the scope explicit and prevent accidental reuse.

**Phase:** Global Filter (Phase 4) — enforce as an architectural rule from the store's first commit.

---

### 7.4 Seeded Data Using the Same Tables as Production Pipeline Data

**What goes wrong:** The seed script (`seed_re_portfolio.py`) inserts RE loan records into a table that the existing pipeline also writes to (e.g., `loan_facts`). After the seeding step, pipeline test runs produce unexpected results because the seed data is present alongside real pipeline output. Conversely, clearing the seed data removes test pipeline runs.

**Why it happens:** Attempting to reuse existing tables for RE portfolio data to avoid creating new tables.

**Prevention:**
- RE portfolio loan data lives in separate tables (`re_loans`, `re_loan_status_history`, etc.) with no overlap with `loan_facts` or `loan_exceptions`. These are different data domains — the existing tables represent pipeline processing artifacts, the new tables represent a managed loan portfolio.
- The seed script is idempotent: `INSERT ... ON CONFLICT DO NOTHING` or a `TRUNCATE` + re-insert pattern. Running it twice produces the same state.
- The seed script has an environment guard: it refuses to run in a production-flagged environment.

**Phase:** Data Seed Schema (Phase 1).

---

## 8. POC Scope Creep Pitfalls

### 8.1 Drill-Down Interactivity Expanding Into a Full Modal System

**What goes wrong:** "Chart segment click filters dashboard; loan row click opens detail card" sounds contained. In implementation, the loan detail card requires: a modal component, a separate API endpoint (`GET /re-loans/{loan_id}`), a full loan detail schema, error handling, keyboard navigation (accessibility), mobile breakpoint handling, a close animation, and a "back to portfolio" breadcrumb state. Each of these is small but the total is 3–5 days.

**Why it happens:** Interactivity is underestimated because each individual interaction seems trivial. The compound cost of making 8–12 chart segments clickable (each with its own filter logic) plus a loan detail modal is not trivial.

**Prevention:**
- For the POC, implement drill-down as: chart segment click applies a filter (changes Zustand state + triggers API refetch). Loan row click shows a read-only detail card in a side-panel (not a modal), populated by a single `GET /re-loans/{loan_id}` endpoint.
- Explicitly descope: the side-panel has no edit capability, no print button, no deep-link URL. It is a read-only data display.
- Time-box drill-down to 2 days. If the chart-segment-to-filter logic is not working in 2 days, ship with static charts and remove drill-down from the POC scope.

**Phase:** Drill-Down (Phase 5 of milestone) — define the scope ceiling explicitly in the phase plan.

---

### 8.2 Market Context Stubs Expanding Into a Real Data Feed Integration

**What goes wrong:** "Stubbed static values (10Y Treasury, SOFR, cap rates, vacancy rates) with real-feed hook markers" is clear. But stakeholders seeing the stub during a demo will immediately ask "can we make that live?" and a developer will start investigating FRED API integration, websocket market data, SOFR term rates, and cap rate data sources. This is 2–3 weeks of work dressed up as a "stub."

**Why it happens:** Stubs that look realistic invite real-data requests. The stub's visual completeness signals technical readiness that doesn't exist.

**Prevention:**
- The market context section is clearly labeled in the UI: "Market Context (Static — [Date])." The date is hardcoded with the seed date. This label is non-negotiable — it signals the stub nature and manages expectations.
- The API endpoint is `GET /market-context/stub` — the word "stub" is in the route. No refactoring of this endpoint is in scope for the POC milestone.
- When stakeholders ask for live data, the answer is: "The hook is in place. The integration is a separate milestone. We're building the POC to validate the dashboard design, not the data feed."

**Phase:** Market Context (Phase 3) — stub design prevents scope creep by design.

---

### 8.3 Risk Rating Migration Matrix Being Harder Than It Looks

**What goes wrong:** The "risk rating migration matrix" (a heatmap/table showing how loans migrated between risk ratings from one period to the next, e.g., from Watch to Performing) requires: two snapshots of loan risk ratings separated by a time period, a pivot query joining the two snapshots on loan ID, and a matrix display component. This is not a simple aggregation — it requires temporal comparison logic. For a POC with seeded data, implementing this requires seeding at least two time periods of loan status.

**Why it happens:** The term "migration matrix" sounds like a display component. The complexity is in the data model (two time periods) and the join logic, not the chart.

**Prevention:**
- Seed two periods of loan status data: `period_1` (12 months ago) and `period_2` (current). The seed script generates both.
- The migration matrix query is: `SELECT p1.risk_rating AS from_rating, p2.risk_rating AS to_rating, COUNT(*), SUM(p2.upb) FROM re_loan_status p1 JOIN re_loan_status p2 ON p1.loan_id = p2.loan_id WHERE p1.period = 'period_1' AND p2.period = 'period_2' GROUP BY 1, 2`.
- If seeding two periods of status adds more than 1 day to the seed phase, descope to "current period risk rating distribution" (a simple bar chart) and label it as "Migration matrix — Q3 roadmap."

**Phase:** Data Seed Schema (Phase 1) — seed design must account for this; Chart Components (Phase 3) — display.

---

## 9. Financial Calculation Correctness Pitfalls

### 9.1 Spread to Benchmark Computed Against Wrong Benchmark Tenor

**What goes wrong:** "Spread to benchmark" is displayed on a KPI card. A developer computes it as `coupon_rate - 10Y_treasury_rate` for all loans. But commercial real estate loans are benchmarked against different tenors: 5-year loans are typically spread to the 5Y Treasury, 10-year loans to the 10Y Treasury, floating-rate loans to SOFR + spread. Computing all spreads against the 10Y rate misrepresents the spread for short-duration and floating-rate loans.

**Why it happens:** The 10Y Treasury is the most commonly cited benchmark and developers apply it universally without domain knowledge.

**Prevention:**
- For the POC, seed the market context stubs with a single benchmark rate and label the spread KPI card explicitly: "Avg Spread to 10Y Treasury (Fixed-Rate Loans Only)." Exclude floating-rate loans from this calculation and show the count excluded.
- The `re_loans` seed schema includes a `rate_type` column (`FIXED` / `FLOATING`). Spread calculations filter on `rate_type = 'FIXED'`.
- Document the benchmark selection rule in the aggregation endpoint comment.

**Phase:** Aggregation API (Phase 2) — define before implementing the KPI endpoint.

---

### 9.2 NOI Trends Chart Not Accounting for Portfolio Composition Changes

**What goes wrong:** A "NOI Trends" chart shows NOI declining from Q1 to Q3. A stakeholder concludes the portfolio is performing worse. But the decline is entirely explained by a large payoff in Q2 (a loan with high NOI left the portfolio). The chart is technically correct but misleading — it conflates performance changes with composition changes.

**Why it happens:** Aggregate trend charts are inherently susceptible to composition effects. This is a domain-specific interpretation problem, not a calculation error.

**Prevention:**
- For the POC, label trend charts with the loan count for each period: "NOI by Quarter (n=47, 45, 43 loans)." A stakeholder who sees declining loan count understands the context.
- Alternatively, show NOI per loan (average NOI) alongside total NOI — composition-normalized metrics are harder to misinterpret.
- Add a footnote: "Trend reflects portfolio composition changes. Loans that paid off in the period are excluded from subsequent periods."

**Phase:** Chart Components (Phase 3) — labeling and annotation decisions.

---

## Priority Summary

| # | Pitfall | Severity | Phase |
|---|---------|----------|-------|
| 1.1 | Float in monetary/rate fields in seed schema | Critical | Phase 1 (Data Seed) |
| 2.1 | Wrong weighting in WAC/WAM/WA-LTV | Critical | Phase 2 (Aggregation API) |
| 7.1 | Alembic migration conflicts with existing history | Critical | Phase 1 (Data Seed) |
| 6.1 | Role stub not enforceable server-side later | Critical | Phase 2 + Phase 7 |
| 2.2 | Division by zero on empty filter subsets | High | Phase 2 + Phase 3 |
| 3.1 | Prop-drilling filter state — use Zustand | High | Phase 4 (Filter) |
| 3.2 | Client-side filtering with large dataset | High | Phase 2 + Phase 4 |
| 5.1 | Blank charts in PDF due to render timing | High | Phase 6 (Export) |
| 7.2 | New routes breaking existing page navigation | High | Phase 1 or early Phase 3 |
| 4.2 | Geo heatmap complexity trap | High | Phase 3 (Charts) |
| 1.3 | As-of date filtering with wrong temporal semantics | High | Phase 1 + Phase 2 |
| 8.1 | Drill-down expanding into full modal system | Medium | Phase 5 (Drill-Down) |
| 2.3 | CPR formula wrong | Medium | Phase 2 (Aggregation) |
| 2.4 | Histogram bucket off-by-one | Medium | Phase 2 + Phase 3 |
| 2.5 | Delinquency rate defined inconsistently | Medium | Phase 2 |
| 1.2 | Nullable traps in aggregations | Medium | Phase 1 + Phase 2 |
| 4.1 | Recharts SVG re-render jank on filter change | Medium | Phase 3 |
| 4.3 | React 19 chart library compatibility | Medium | Phase 3 |
| 5.2 | CSS breaks in PDF capture | Medium | Phase 3 + Phase 6 |
| 6.2 | JWT claims insufficient for row-level scoping | Medium | Phase 7 |
| 7.3 | Zustand store polluting existing app state | Medium | Phase 4 |
| 7.4 | Seed data colliding with pipeline tables | Medium | Phase 1 |
| 8.2 | Market context stub expanding to live feed | Low | Phase 3 |
| 8.3 | Migration matrix harder than it looks | Low | Phase 1 + Phase 3 |
| 9.1 | Spread to wrong benchmark tenor | Low | Phase 2 |
| 9.2 | NOI trend chart misleading due to composition | Low | Phase 3 |
| 5.3 | PDF export OOM on Retina displays | Low | Phase 6 |
| 3.3 | Filter state not URL-persisted | Low | Phase 4 |

---

*Generated by gsd-project-researcher — 2026-04-08*
*Covers: data model, financial aggregation, filtering architecture, chart library, PDF export, role-based views, integration with existing system, POC scope management, financial calculation correctness*
