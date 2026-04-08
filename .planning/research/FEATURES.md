# Feature Landscape: RE Loan Portfolio Dashboard POC

**Domain:** Commercial Real Estate (CRE) loan portfolio monitoring — internal ops dashboard POC
**Researched:** 2026-04-08
**Confidence:** MEDIUM-HIGH (domain patterns well-established; React/charting choices verified against current docs)

---

## Context: What This Is and Is Not

This is a **POC** — a seeded-data demonstration added to an existing React 19 + FastAPI + PostgreSQL app. The goal is to show stakeholders what CRE portfolio monitoring can look like, not to build a production-grade portfolio management system. That distinction drives every category decision below.

**Existing charting infrastructure:** None. The frontend has React 19 + Tailwind CSS + react-router-dom, no chart library installed. Adding one is required.

**Recommended chart library: Recharts 2.x** — 3.6M+ weekly downloads, built for React (not adapted from jQuery/Canvas), composable API, covers every chart type needed (bar, line, pie, area, funnel). Works with Tailwind. D3 is too low-level for a POC timeline. Nivo adds bundle weight without proportionate POC value.

**Recommended geo map: react-simple-maps** — thin wrapper around d3-geo + topojson, declarative React API, handles US state choropleth out of the box. No Mapbox/Google Maps license needed. Add `us-atlas` for TopoJSON data and `d3-scale` for color scales.

**Recommended PDF export: html2canvas + jsPDF** — rasterize-and-embed approach. Fast to implement; layout fidelity is sufficient for a POC snapshot. The clean alternative (`@react-pdf/renderer`) requires rewriting layouts as PDF components — high effort for marginal POC benefit.

---

## Feature Category Definitions (for this POC)

- **Table Stakes:** Missing this = the demo fails to communicate the product concept. Must build.
- **Differentiator:** Builds POC credibility beyond a static mockup. Build selectively — high signal-to-effort ratio.
- **Anti-Feature (POC):** Looks valuable but costs 3-5x more than the POC benefit justifies. Defer explicitly with a documented reason.

---

## Area 1: Executive Summary — KPI Cards

### Table Stakes

- **Total UPB** — single large formatted currency number. The anchoring number for every other metric.
- **Active loan count** — count of non-default, non-paid-off loans. Shows portfolio scope.
- **WAC (weighted average coupon)** — `SUM(rate * balance) / SUM(balance)`. Displayed as `X.XX%`. Must use `NUMERIC` arithmetic in Postgres or Python, never float.
- **WA LTV** — `SUM(ltv * balance) / SUM(balance)`. Displayed as `XX.X%`.
- **WA DSCR** — `SUM(dscr * balance) / SUM(balance)`. Displayed as `X.XXx`. Industry standard threshold references: >1.25x is healthy, <1.0x is distressed.
- **Delinquency buckets** — 30/60/90+ DPD as three sub-cells on a single card. Color: 30-day=yellow, 60-day=orange, 90+=red. Show both count and UPB per bucket.

### Differentiators

- **WAM (weighted average maturity)** — `SUM(months_to_maturity * balance) / SUM(balance)` displayed as `X.X yrs`. Requires `maturity_date` in seed. High credibility signal for a fixed-income audience.
- **Portfolio yield vs benchmark spread** — gross yield minus a static SOFR stub (hardcoded; e.g., 5.33%). Display: `Spread to SOFR: +XXX bps`. Mark clearly as `[STUB]` in UI with an info icon explaining the live feed hook.
- **KPI delta vs prior period** — small `+X.X% vs last quarter` label beneath each main number. Requires two time-point snapshots in seed data. High credibility: shows the tool tracks trends, not just a point-in-time.

### Anti-Features (POC)

- **Real-time KPI refresh / websocket updates** — POC uses seeded static data. Live feeds add weeks of infrastructure work for zero demo value.
- **Regulatory capital ratios (RWA, CECL reserve %)** — institution-specific; impossible to seed meaningfully. Produces misleading numbers.

**Complexity:** Low-Medium. All KPIs are SQL aggregate queries. The hard part is ensuring `NUMERIC` arithmetic (never `float`) and building a FastAPI endpoint that returns a single JSON object per the active filter state. React component is a CSS grid of styled cards.

**Dependency:** KPI cards depend on the seed data schema. If seed has no `maturity_date`, WAM cannot be computed. Define seed schema before implementing this area.

---

## Area 2: Portfolio Composition

### Table Stakes

- **Property type donut chart** — slices: multifamily, office, retail, industrial, mixed-use, hotel. Recharts `PieChart` with `innerRadius` for donut shape. Tooltip shows type + UPB + count. Click slice applies global property-type filter (Area 7).
- **US state choropleth** — color by UPB concentration per state. `react-simple-maps` + `us-atlas` TopoJSON + `d3-scale` quantile color scale (light-to-dark blue). Hover tooltip: state + UPB + loan count. Click state applies geo filter (Area 7).
- **Loan size histogram** — buckets: <$1M, $1-5M, $5-10M, $10-25M, $25M+; y-axis: loan count. Recharts `BarChart`. Communicates portfolio granularity.
- **Maturity profile stacked bar** — x-axis: year (2025-2031); y-axis: UPB maturing; stacked by property type. Recharts `BarChart` with `stackId`. Shows refinancing wall / maturity concentration risk at a glance.
- **Top-10 exposures table** — sortable by UPB. Columns: borrower, property type, state, UPB, LTV, DSCR, maturity date, risk rating. Row click opens loan detail slide-out (Area 7). This is the "show me the biggest bets" view.

### Differentiators

- **Concentration limit indicators** — for each property type, a horizontal bar showing actual % of portfolio vs a policy limit (e.g., "Office: 18% / limit: 25%"). Color: green below 80% of limit, yellow 80-100%, red over limit. Define limits in a config constant (not a DB table for POC). This single feature is the highest-credibility signal for a risk governance audience — it shows the tool has policy enforcement DNA.
- **MSA drill-down from state** — clicking a state re-renders a second bar chart showing top MSAs within that state. Requires `msa` field on each seed loan. Medium complexity, high visual impact for a geo-heavy portfolio.

### Anti-Features (POC)

- **Mapbox/Google Maps tile layers** — irrelevant for portfolio concentration; adds licensing cost and external API dependency.
- **Loan-level lat/lng pin map** — 500 dots on a map communicates nothing useful; state-level choropleth is the correct level of abstraction for a portfolio view.
- **Animated map zoom transitions** — CSS transitions are fine; D3 zoom is a weekend of effort for cosmetic benefit.

**Complexity:** Medium. The geo map is the hardest piece in this section — `react-simple-maps` + TopoJSON + `d3-scale` quantile. Everything else is Recharts with straightforward data shapes. The concentration limit indicators require policy limit constants defined in a config file.

**Dependency:** Requires seed fields: `property_type`, `state`, `msa`, `current_upb`, `maturity_date`, `ltv`, `dscr`, `risk_rating`, `borrower`. The map will not render without a state-level aggregation API endpoint returning `{ state: "CA", upb: 42000000, count: 18 }` per state.

---

## Area 3: Credit Quality

### Table Stakes

- **LTV distribution histogram** — buckets: <55%, 55-65%, 65-75%, 75-85%, >85%. Bar colors: green (<65%), yellow (65-75%), orange (75-85%), red (>85%). Recharts `BarChart` with per-bar `Cell` fill. Industry reference: average LTV across CRE market circa 2025 is ~63%; >75% triggers heightened monitoring.
- **DSCR distribution histogram** — buckets: <0.9x, 0.9-1.0x, 1.0-1.25x, 1.25-1.5x, >1.5x. Colors: red (<1.0x), yellow (1.0-1.25x), green (>1.25x). Industry reference: 1.25x is standard minimum covenant; 1.35x is comfortable for well-located assets.
- **Watchlist/criticized loans table** — columns: loan ID, borrower, property type, balance, risk rating (1-9 scale), trend arrow (▲/▼/—), watch reason, last review date. Sortable by balance or rating. Row click opens detail card (Area 7).
- **Delinquency status bar** — horizontal stacked bar showing UPB split by status: Current, 30 DPD, 60 DPD, 90+ DPD, Default. Simpler and clearer than a funnel. Recharts `BarChart` with `layout="vertical"` and `stackId`.

### Differentiators

- **Risk rating migration matrix** — an NxN grid (rows = prior period rating, columns = current rating). Cell values show count of loans that moved. Diagonal = stable, below diagonal = upgrade (green), above = downgrade (red). Implement as a plain HTML `<table>` with Tailwind background colors per cell. Do not use a charting library hack — a table is more readable and takes less time to build. Requires two rating snapshots in seed data. This is the most sophisticated credit risk feature in the POC; it signals "this tool understands credit portfolio management."
- **Interest rate sensitivity stub table** — static 3×4 table: rows are scenarios (+100bps, +200bps, +300bps), columns are DSCR impact per property type bucket. Values computed offline at seed time and stored as a JSON constant. Display only. No live model. Label clearly as `[SCENARIO STUB]`.

### Anti-Features (POC)

- **Per-loan live stress testing** — requires a cashflow model per loan at N rate scenarios. Weeks of backend work.
- **External credit rating (Moody's, S&P) integration** — paid API, not available for an internal POC.
- **Probability of default (PD) model output** — no model exists; presenting random numbers as PD scores would actively mislead stakeholders.

**Complexity:** Medium-High. The two histograms are simple. The migration matrix is the hardest feature in this section — the seed must have `risk_rating` and `risk_rating_prior` per loan, and the API must return a pre-aggregated N×N grid. The interest rate sensitivity table is purely static display.

**Dependency:** Requires seed fields: `risk_rating`, `risk_rating_prior`, `dpd`, `watch_reason`, `last_review_date`. The migration matrix only works if the seed is deliberately designed with rating changes across loans (e.g., 15% of loans have a different `risk_rating_prior`).

---

## Area 4: Cash Flow & Performance

### Table Stakes

- **Monthly P&I actual vs projected line chart** — dual line: actual (solid blue), projected (dashed gray) over 12 trailing months. Recharts `LineChart` with two `Line` components. Y-axis in $M. This directly leverages the existing cashflow computation infrastructure and is the strongest continuity point between the existing app and the new dashboard.
- **Yield analysis row** — four inline numbers: gross yield, net yield (gross minus servicing spread), spread to SOFR, spread to 10Y Treasury. Static SOFR (5.33%) and Treasury (4.22%) stubs. Label with `[STUB]` and an info icon: "Live feed would pull from FRED API." This is intentional stub design, not a limitation to hide.

### Differentiators

- **CPR trend chart** — 12-month trailing Conditional Prepayment Rate as a bar chart. CPR formula: `CPR = 1 - (1 - SMM)^12` where `SMM = prepayment_in_month / beginning_balance`. Shows portfolio runoff speed. Requires monthly cashflow records with `prepayment_amount` and `beginning_upb` per loan per month in seed. If seed cannot support this computation, stub with flat CPR line and label it.
- **NOI trend chart** — quarterly aggregate NOI as a bar chart over 6 quarters. If seed does not have property-level income statements, derive as `DSCR × debt_service` per loan per period. This approximation is acceptable for POC and is clearly labeled.
- **Loss/recovery table** — columns: loan ID, disposition date, original balance, recovered amount, loss severity %. Requires a handful of "resolved" seed loans with `status = liquidated`. Simple table, no chart needed. Shows the tool tracks credit losses, not just performing loans.

### Anti-Features (POC)

- **Narrative variance commentary auto-generation** — requires LLM integration, out of scope.
- **Duration/convexity analytics** — requires full cashflow model per loan at multiple rate scenarios. Deeply complex mortgage math.
- **Per-loan IRR computation** — requires full cashflow history per loan; overcomplicates seed.
- **Actual vs projected variance alerts / breach notifications** — alerting infrastructure is out of scope for a POC.

**Complexity:** Low-Medium for the P&I chart (if seed has monthly cashflow records). Medium for CPR (formula + monthly data). The yield row is arithmetic. The loss table is simple display. The cashflow area is the most data-intensive and has the strongest dependency on seed schema design.

**Dependency:** Requires seed tables with time-series cashflow records (not just one row per loan): `loan_id`, `period` (month), `scheduled_principal`, `scheduled_interest`, `actual_principal`, `actual_interest`, `prepayment_amount`, `beginning_upb`. This is the single most important seed schema decision after the core loan table.

---

## Area 5: Origination Pipeline

### Table Stakes

- **Origination volume bar chart** — monthly bars for trailing 12 months: UPB originated per month. Recharts `BarChart`. Requires `origination_date` on each seed loan.
- **Payoffs/paydowns bar chart** — monthly payoff UPB vs scheduled paydown UPB, side-by-side bars. Shows portfolio runoff. Requires the monthly cashflow records from Area 4.

### Differentiators

- **Pipeline funnel** — four stages: Underwriting → Approved → In Closing → Funded. Shows count and UPB at each stage. Requires seed loans with `pipeline_status` for in-progress (not yet funded) loans. Recharts `FunnelChart` (available in recharts@2.x). Include at least 5-10 "in pipeline" seed loans or the funnel is a flat bar.
- **Vintage analysis** — x-axis: origination year; stacked bars by property type; bars colored by current risk rating quartile (green/yellow/red). Shows credit quality by cohort. Requires `origination_year` and `risk_rating` per loan. High analytical value for a portfolio risk audience.

### Anti-Features (POC)

- **Integration with the existing loan purchase pipeline** — the existing pipeline (suitability check, counterparty tagging, wire instructions) is for loan *purchase* evaluation against counterparty criteria, not CRE origination workflow. These are different business processes. Do not conflate them. The dashboard POC is a separate reporting layer.
- **Borrower communication log / loan application tracking** — CRM functionality, entirely out of scope.
- **Automated underwriting model scores** — no model exists in this codebase.

**Complexity:** Low. This is the simplest section if seed has `origination_date`, `current_upb`, `pipeline_status`, and `origination_year`. All charts are straightforward bar/funnel. Vintage analysis adds one grouping dimension but is still a single Recharts BarChart.

**Dependency:** The payoffs/paydowns chart shares the monthly cashflow records with Area 4. The pipeline funnel requires deliberately seeding 5-10 pre-funded pipeline loans.

---

## Area 6: Market Context (Stub Panel)

### Table Stakes

- **Static rate display panel** — four labeled values with visible `[STUB]` badge: 10Y Treasury yield (4.22%), SOFR (5.33%), CRE cap rates by property type (multifamily: 5.5%, office: 7.8%, retail: 7.2%, industrial: 5.8%), vacancy rates (office: 18.2%, multifamily: 6.1%). Values returned from a `/api/market-context` endpoint reading from a seed JSON or a config constant. Not from a live feed.
- **Live feed hook markers** — each value in the API layer has a `# TODO: replace with live feed - [source: FRED, CoStar, etc.]` comment. In the UI, each value shows a small `(i)` tooltip explaining it is a static stub. This communicates architecture intent to stakeholders; it is not cosmetic.

### Differentiators

- **FRED API commented stub** — a commented-out `requests.get("https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&...")` in the market context service file. Shows stakeholders exactly where real data would come from and how little plumbing it takes. Zero development effort for the comment; high demo credibility.

### Anti-Features (POC)

- **Live rate fetch from any external API** — introduces network dependency, API key management, CORS handling, and potential rate limiting in a demo environment. Not worth it for static-data POC.
- **CRE index feeds (Green Street, CoStar, CBRE)** — paid data, no free API, contractually complex.

**Complexity:** Very Low. Single FastAPI endpoint returning a JSON object of static values. React component is a small panel of labeled numbers. Total effort: 2-4 hours. Build this first as a low-risk confidence win.

**Dependency:** None. Fully independent. Can be built at any time.

---

## Area 7: Interactivity — Global Filter Sidebar + Drill-Down

### Table Stakes

- **Global filter sidebar** — persistent left panel, collapsible. Filter controls: as-of date (quarter/date picker), property type (multi-select checkboxes), state (searchable dropdown or multi-select), loan size range (min/max inputs), risk rating (multi-select 1-9), rate type (fixed/floating/hybrid). Store filter state in URL query params (preferred over React context alone) — shareable links, survives page refresh.
- **API-driven filtering** — on filter change, all dashboard data re-fetches from API with filter params included. The API handles aggregation; React does not filter already-loaded data client-side. This is non-negotiable. Client-side filtering creates invisible inconsistencies when a filter affects a computed aggregate (e.g., WAC changes when property type changes).
- **Chart segment click → filter** — clicking a pie slice or bar segment applies that dimension as a global filter. Recharts `onClick` prop passes the clicked value to filter state. Example: clicking "Office" in the property type donut sets `property_type=office` and all charts re-fetch.
- **Loan row click → detail slide-out** — clicking any loan in any table opens a right-side slide-out panel (not a new route). Slide-out shows: loan ID, borrower, property type, address, balance, rate, LTV, DSCR, maturity date, risk rating, DPD status, origination date. Implemented as an absolutely-positioned aside with a close button. No routing change.

### Differentiators

- **Active filter chips** — when filters are active, show removable chips above the dashboard ("Property Type: Office ×  |  State: CA ×"). Each chip has an × to remove that filter. Standard UX pattern, high usability signal, moderate effort (~4 hours).
- **Filter presets** — "Watchlist View", "Office Exposure", "High LTV" saved to `localStorage`. Low backend cost, demonstrates the tool is designed for repeated use.

### Anti-Features (POC)

- **Server-side cursor pagination on every table** — a seeded dataset of 200-500 loans does not require cursor pagination. Client-side sort on a fully fetched result set is correct at this scale. Premature optimization that adds complexity to every table component and API endpoint.
- **Client-side cross-filter without API round-trip** — appears to simplify but breaks aggregate consistency. Always re-fetch on filter change.
- **Drag-and-drop widget reordering / personalized dashboard layouts** — out of scope for POC.
- **Real-time filter debounce with instant chart updates** — 300ms debounce before API call is sufficient. Sub-100ms live filtering requires client-side data which violates the aggregation consistency requirement above.

**Complexity:** High. This is the architecturally heaviest feature in the entire POC. The filter state must flow from the sidebar to every data-fetching hook. Recommended pattern:

1. A `PortfolioFilterContext` (React context) holding the current filter state object.
2. A `usePortfolioData(endpoint, filters)` custom hook that builds the query string from filter state, fires on filter change, and returns `{ data, loading, error }`.
3. All API endpoints accept a consistent set of query parameters: `property_type`, `state`, `size_min`, `size_max`, `risk_rating`, `rate_type`, `as_of`.
4. The FastAPI layer translates these params into SQLAlchemy filter clauses.

**Build this first.** Every chart and table in every other area depends on this. Bolting it on after the fact causes rewrites across the entire codebase.

**Dependency:** This is the foundation layer. All other feature areas depend on it.

---

## Area 8: Export — PDF Snapshot + CSV

### Table Stakes

- **CSV export per table** — "Download CSV" button on each data table (top-10 exposures, watchlist, delinquency, loss/recovery). Pure frontend: take the table's current data array, construct a CSV string, trigger a `Blob` download. No backend involvement. ~20 lines of TypeScript per table. Zero complexity.
- **PDF dashboard snapshot** — "Export Dashboard" button triggers `html2canvas` to rasterize the dashboard viewport, then `jsPDF` to embed as a PDF page. Produces a bitmap PDF (not vector text). Acceptable for POC snapshot. Caveat: label clearly as "Dashboard Snapshot" not "Report."

### Differentiators

- **Section-scoped PDF export** — user selects which sections to include (checkboxes: "Executive Summary", "Credit Quality", etc.). Implemented by rasterizing specific named DOM refs in sequence. Medium effort, useful for presenting to different audiences.

### Anti-Features (POC)

- **Server-side PDF generation (WeasyPrint / pdfkit from FastAPI)** — produces vector PDFs with correct fonts, but requires a new FastAPI endpoint, a headless rendering environment, and significant CSS porting work. Disproportionate to POC needs.
- **Scheduled PDF email delivery** — SES is slated for v1.1 of the existing product but not for this dashboard POC.
- **Excel export with embedded charts** — `openpyxl` with chart embedding is complex; CSV covers the data need.

**Complexity:** Low-Medium. CSV is trivially simple. PDF export has a known pitfall: `html2canvas` does not render CSS custom properties (Tailwind variables) reliably, and elements outside the viewport are clipped. Mitigation: render a dedicated print-view component into a hidden `div` and rasterize that, not the live DOM. This adds ~3-4 hours but produces a consistent output.

**Dependency:** PDF export depends on all dashboard sections existing. Build CSV export incrementally as each table is built; build PDF export last.

---

## Area 9: Role Stub — PM vs Advisor

### Table Stakes

- **Role field on session** — `role` field on the JWT payload: `"pm"` (full portfolio view) or `"advisor"` (their book only). Seed creates two users with different roles. No admin UI needed for POC.
- **Advisor book filter** — when `role == "advisor"`, all API calls automatically append a `borrower_group_id` filter matching the advisor's assigned loans. Enforced server-side in the FastAPI `get_current_user` dependency. The filter is invisible to the advisor (they cannot override it). The PM sees the full portfolio by default.
- **UI label differentiation** — advisor sees "Your Book" in the dashboard header; PM sees "Full Portfolio." A small badge or subtitle, not a full page redesign.

### Differentiators

- **PM "view as advisor" toggle** — a PM can switch into an advisor's view to see what they see. Useful for demonstrating access control in a demo. Implemented as a UI state override that appends the selected advisor's `borrower_group_id` to API calls. ~4 hours.

### Anti-Features (POC)

- **Full RBAC system with permissions matrix and admin management UI** — two hardcoded roles in seed data is sufficient for a POC. A permissions management UI is a significant product in itself.
- **Postgres row-level security (RLS) for advisor isolation** — correct architecture for production, but RLS setup for a seeded POC adds a full day of infrastructure work. Use application-layer filtering (FastAPI appends the filter based on session role). Document explicitly that production would use RLS.
- **Audit logging of data access per role** — valuable compliance feature, deferred to production.

**Complexity:** Low. The mechanism is: `get_current_user` dependency returns `{ role, borrower_group_id }`. Every portfolio endpoint checks role and appends filter if advisor. React shows/hides the "view as advisor" toggle based on role. Seed needs 2 users and a `borrower_group_id` on each loan (or a join table loans↔advisor_groups). Total: 4-6 hours.

**Dependency:** Depends on the global filter context (Area 7) being built first. The advisor filter is just another filter that is automatically applied and immutable for advisor sessions.

---

## Feature Dependencies (Build Order)

```
1. Seed Data Schema (defines what every other area can compute)
   |
   ├── Area 6: Market Context stub  ← independent, build first for confidence
   ├── Area 9: Role stub            ← validates auth model early, low effort
   |
   └── Area 7: Global Filter Context + API param convention
         |      (MUST exist before any chart is built)
         |
         ├── Area 1: Executive Summary KPI cards
         ├── Area 2: Portfolio Composition charts
         |     └── Geo map (after installing react-simple-maps + us-atlas)
         ├── Area 3: Credit Quality
         |     └── Migration matrix (requires two-period seed data)
         ├── Area 4: Cash Flow & Performance
         |     └── CPR chart (requires monthly cashflow records in seed)
         ├── Area 5: Origination Pipeline
         |
         └── Area 8: Export
               ├── CSV (add per table as each table is built)
               └── PDF snapshot (build last, after all sections exist)
```

**Critical path:** Seed schema → Filter context/API convention → KPI cards → one section at a time → Export last.

---

## MVP Recommendation for POC

**Must build (table stakes):**
1. Seed schema (design this before writing any code — it unblocks everything)
2. Global filter sidebar + filter context + API param convention (Area 7)
3. Executive Summary KPI cards: UPB, count, WAC, LTV, DSCR, delinquency buckets (Area 1)
4. Property type donut + US state choropleth + top-10 table (Area 2)
5. LTV and DSCR histograms + watchlist table (Area 3)
6. P&I actual vs projected chart + yield stub row (Area 4)
7. Origination volume bar chart (Area 5)
8. Market context stub panel (Area 6)
9. Role stub: two users, advisor filter (Area 9)
10. CSV export per table (Area 8)

**Build for differentiation (high credibility / moderate effort):**
- Concentration limit indicators (Area 2) — highest credibility feature for a risk governance audience
- Risk rating migration matrix (Area 3) — most sophisticated credit signal
- WAM + delta vs prior period on KPI cards (Area 1)
- Pipeline funnel (Area 5)
- Filter chips display (Area 7)
- PDF snapshot export (Area 8) — build last

**Explicitly defer:**
| Feature | Reason |
|---------|--------|
| Real-time data feeds | Entire point of stub markers is to flag where they'd go |
| Per-loan stress testing / full cashflow model | Weeks of backend work; POC does not need live analytics |
| Server-side PDF with WeasyPrint | Disproportionate effort; html2canvas screenshot is sufficient |
| Postgres RLS for role isolation | Correct for production; application-layer filter is correct for POC |
| Drag-and-drop dashboard layout | Out of scope for POC |
| Cursor pagination | Seeded dataset is 200-500 loans; not needed |
| NOI from property income statements | Derive from DSCR × debt_service as approximation |

---

## POC vs Production Architecture Distinctions

| Feature | POC Approach | Production Approach |
|---------|-------------|---------------------|
| Market rates | Static constants / seed JSON | FRED API / Bloomberg / data vendor |
| Interest rate sensitivity | Pre-computed stub table | Per-loan cashflow model at N rate scenarios |
| PDF export | html2canvas bitmap screenshot | Server-side WeasyPrint or dedicated PDF microservice |
| Role/data isolation | Application-layer filter in FastAPI | Postgres RLS + proper RBAC with admin UI |
| CPR computation | Formula on seed monthly data | Servicer data feed + reconciliation layer |
| Data freshness | Seeded static dataset | Nightly ETL from servicer/custodian/CMBS trustee |
| NOI aggregation | DSCR × debt_service approximation | Property operating statement ingestion |
| Table pagination | Client-side sort on full fetch | Server-side cursor pagination + DB indexes |
| Delinquency data | Seeded DPD field per loan | Servicer advancing / master servicer reporting |

---

## Sources

- [Built: Risk Management Dashboards for CRE Lenders](https://getbuilt.com/blog/risk-management-dashboards-lender/)
- [CRED iQ: CRE Delinquency Trends Q1 2025](https://cred-iq.com/blog/2025/07/02/tracking-cre-delinquency-trends-insights-from-the-great-financial-crisis-to-q1-2025/)
- [Agent Skills Finance: Loan Portfolio Monitoring](https://agentskills.finance/skills/managing-loan-portfolio-monitoring)
- [Bryt Software: 9 Key Metrics for Loan Portfolio Analysis](https://www.brytsoftware.com/metrics-help-loan-portfolio-analysis-maximum-financial-gains/)
- [LogRocket: Best React Chart Libraries 2025](https://blog.logrocket.com/best-react-chart-libraries-2025/)
- [React Simple Maps Documentation](https://www.react-simple-maps.io/)
- [React Simple Maps: US Choropleth Quantile Example](https://www.react-simple-maps.io/examples/usa-counties-choropleth-quantile/)
- [Pencil & Paper: Filter UX Design Patterns](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-filtering)
- [Pencil & Paper: Dashboard UX Patterns](https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards)
- [FasterCapital: Loan Performance Dashboard](https://fastercapital.com/content/Loan-Performance-Reporting--How-to-Create-and-Analyze-Your-Loan-Performance-Dashboard.html)
- [Nutrient: html2canvas + jsPDF in React](https://www.nutrient.io/blog/how-to-convert-html-to-pdf-using-react/)
- [Biz2X: Loan Portfolio Analytics Framework](https://www.biz2x.com/loan-portfolio-monitoring/loan-portfolio-analytics-framework-data-quality-stress-testing/)
- [Terry Dale Capital: DSCR & LTV Requirements 2025](https://terrydalecapital.com/learn/dscr-ltv-commercial-real-estate-2025)
