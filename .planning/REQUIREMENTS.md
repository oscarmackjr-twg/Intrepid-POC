# Requirements: v2.0 Real Estate Loan Dashboard POC

**Milestone:** v2.0
**Status:** Active
**Last updated:** 2026-04-08

---

## DATA — Data Foundation

- [ ] **DATA-01:** `re_loans` table exists with all required financial fields using `NUMERIC(18,6)` for monetary/rate columns, `as_of_date` index, `prior_risk_rating`, and `sales_team_id` FK
- [ ] **DATA-02:** `re_loan_cashflows` table exists with monthly records (period_date, scheduled/actual principal & interest) linked to `re_loans`
- [ ] **DATA-03:** Seed script populates 500–2,000 loans across ≥5 property types, ≥20 states, ≥8 MSAs, two `as_of_date` snapshots, and 12 months of cashflow records per loan
- [ ] **DATA-04:** Alembic migrations for both tables chain off the current head without conflicts; `alembic upgrade head` succeeds in CI

## API — Backend Endpoints

- [ ] **API-01:** `/api/re/kpis` returns total UPB, WAC (UPB-weighted), WAM, WA LTV, WA DSCR, active loan count, delinquency buckets (30/60/90+), portfolio yield — all respecting active filter params
- [ ] **API-02:** `/api/re/concentration` returns property type breakdown, state/MSA concentration, top-10 exposures, concentration limit proximity
- [ ] **API-03:** `/api/re/distributions` returns LTV histogram (color-banded), DSCR histogram (color-banded), loan size distribution
- [ ] **API-04:** `/api/re/maturity-profile` returns loan counts and UPB grouped by quarter/year
- [ ] **API-05:** `/api/re/loans` returns paginated, filterable, sortable loan list
- [ ] **API-06:** `/api/re/loans/{id}` returns full loan detail (terms, collateral, borrower, payment history summary, appraisal history)
- [ ] **API-07:** `/api/re/cashflow-performance` returns monthly P&I actual vs projected, NOI trend, gross/net yield, CPR, and loss/recovery metrics
- [ ] **API-08:** `/api/re/origination-pipeline` returns origination volume by month, payoffs/paydowns, pipeline funnel stage counts, vintage breakdown
- [ ] **API-09:** `/api/re/market-context` returns stubbed benchmark rates and CRE indices with code-level markers for live integration points
- [ ] **API-10:** `/api/re/sensitivity` returns portfolio impact under +/−100/200/300 bps interest rate scenarios
- [ ] **API-11:** All `/api/re/*` endpoints enforce `sales_team_id` scope server-side for `sales_team` role users

## FILTER — Global Filtering

- [ ] **FILTER-01:** Filter sidebar available on all dashboard pages with controls for: as-of date, property type, state/MSA, loan size range, risk rating, vintage, borrower, rate type
- [ ] **FILTER-02:** Active filters persist in URL query params and sync with Zustand in-memory store
- [ ] **FILTER-03:** Changing any filter re-fetches all dashboard panels simultaneously without page reload
- [ ] **FILTER-04:** Filter sidebar has a "Clear all filters" control that resets all params

## EXEC — Executive Summary

- [ ] **EXEC-01:** Executive Summary page displays KPI cards for: total UPB, WAC, WAM, WA LTV, WA DSCR, active loan count, delinquency rate (30/60/90+), portfolio yield vs benchmark spread
- [ ] **EXEC-02:** All KPI cards reflect active filter state and show loading and no-data states

## COMP — Portfolio Composition

- [ ] **COMP-01:** Portfolio Composition page shows a pie/donut chart of loans by property type (count and UPB)
- [ ] **COMP-02:** Portfolio Composition page shows a US state choropleth — or ranked bar chart fallback — showing UPB concentration by state, with click-to-filter
- [ ] **COMP-03:** Portfolio Composition page shows a loan size histogram
- [ ] **COMP-04:** Portfolio Composition page shows a maturity profile stacked bar chart grouped by quarter/year
- [ ] **COMP-05:** Portfolio Composition page shows a top-10 exposures table (by UPB) with LTV, DSCR, property type, and location
- [ ] **COMP-06:** Portfolio Composition page shows concentration limit indicators (visual proximity to policy limits for borrower, geography, property type)

## CREDIT — Credit Quality & Risk

- [ ] **CREDIT-01:** Credit Quality page shows LTV distribution histogram with green/yellow/red color bands (<65%, 65–75%, >75%)
- [ ] **CREDIT-02:** Credit Quality page shows DSCR distribution histogram with color bands (>1.4x, 1.0–1.4x, <1.0x)
- [ ] **CREDIT-03:** Credit Quality page shows a watchlist/criticized loans table filterable by risk rating, with trend arrows
- [ ] **CREDIT-04:** Credit Quality page shows a delinquency waterfall (current → 30 → 60 → 90 → default)
- [ ] **CREDIT-05:** Credit Quality page shows a risk rating migration matrix (current vs prior period)
- [ ] **CREDIT-06:** Credit Quality page shows interest rate sensitivity table (+/−100/200/300 bps portfolio impact)

## CASHFLOW — Cash Flow & Performance

- [ ] **CASHFLOW-01:** Cash Flow page shows monthly P&I as a line chart — actual vs projected with variance
- [ ] **CASHFLOW-02:** Cash Flow page shows aggregated NOI trend over time
- [ ] **CASHFLOW-03:** Cash Flow page shows yield analysis: gross yield, net yield after losses, spread to SOFR and Treasury
- [ ] **CASHFLOW-04:** Cash Flow page shows CPR trend line
- [ ] **CASHFLOW-05:** Cash Flow page shows loss/recovery tracking: realized losses, recoveries, net loss rate

## ORIGIN — Origination Pipeline

- [ ] **ORIGIN-01:** Origination Pipeline page shows new origination volume by month broken down by property type
- [ ] **ORIGIN-02:** Origination Pipeline page shows net portfolio growth/shrinkage (originations minus payoffs)
- [ ] **ORIGIN-03:** Origination Pipeline page shows a pipeline funnel (underwriting → approved → closing → funded)
- [ ] **ORIGIN-04:** Origination Pipeline page shows vintage analysis — performance metrics by origination year

## MARKET — Market Context

- [ ] **MARKET-01:** Market Context panel shows stubbed 10Y Treasury and SOFR with trend shapes, labeled with live-feed hook markers
- [ ] **MARKET-02:** Market Context panel shows stubbed cap rates by property type and vacancy rates, labeled as indicative

## UX — Interactivity

- [ ] **UX-01:** Clicking any chart segment (pie slice, histogram bar, map state) applies that dimension as a filter across the entire dashboard
- [ ] **UX-02:** Clicking any loan row opens a read-only loan detail side-panel (full terms, collateral, borrower, payment history summary, appraisal history)
- [ ] **UX-03:** Loan detail side-panel closes without navigating away from the current page

## EXPORT — Export

- [ ] **EXPORT-01:** Any filterable table has a "Download CSV" button that exports the current filtered and sorted data
- [ ] **EXPORT-02:** A "Download PDF" button captures a rasterized snapshot of the current dashboard page (labeled "Dashboard Snapshot")

## ROLES — Role-Based View Stub

- [ ] **ROLES-01:** Users with `admin` or `analyst` role see the full portfolio on all dashboard pages
- [ ] **ROLES-02:** Users with `sales_team` role see only their assigned loans, enforced server-side on all `/api/re/*` endpoints
- [ ] **ROLES-03:** Dashboard nav link is visible to all authenticated users

---

## Future Requirements

- Live market data feeds (FRED API for Treasury/SOFR, CRE index providers)
- Real-time / intraday refresh cadence (vs monthly snapshot POC)
- Cashflow projection modeling (vs seeded projected values)
- Full advisor book-of-business management UI (assign loans to sales teams)
- PostgreSQL RLS for row-level security (vs application-layer enforcement in POC)
- MSA/metro drill-down on geo map (vs state-level only in POC)
- Loan edit / data entry UI
- Integration with existing loan tape pipeline (LoanFact → re_loans bridge)
- Email alerts on watchlist threshold breaches

## Out of Scope (v2.0)

- Live external data API integration (market context is stubbed) — production integration deferred
- PostgreSQL RLS — application-layer scope enforcement sufficient for POC
- Loan edit/write UI — dashboard is read-only
- Integration with existing LoanFact pipeline data — separate seed dataset
- MSA-level geo drill-down — state-level choropleth only
- Mobile / responsive layout optimization
- Multi-tenant or external user access

---

## Traceability

*Filled by roadmapper — maps each REQ-ID to its phase.*

| REQ-ID | Phase | Status |
|--------|-------|--------|
| DATA-01 | Phase 17 | Pending |
| DATA-02 | Phase 17 | Pending |
| DATA-03 | Phase 17 | Pending |
| DATA-04 | Phase 17 | Pending |
| API-01 | Phase 18 | Pending |
| API-02 | Phase 18 | Pending |
| API-03 | Phase 18 | Pending |
| API-04 | Phase 18 | Pending |
| API-05 | Phase 18 | Pending |
| API-06 | Phase 18 | Pending |
| API-07 | Phase 18 | Pending |
| API-08 | Phase 18 | Pending |
| API-09 | Phase 18 | Pending |
| API-10 | Phase 18 | Pending |
| API-11 | Phase 18 | Pending |
| FILTER-01 | Phase 19 | Pending |
| FILTER-02 | Phase 19 | Pending |
| FILTER-03 | Phase 19 | Pending |
| FILTER-04 | Phase 19 | Pending |
| EXEC-01 | Phase 20 | Pending |
| EXEC-02 | Phase 20 | Pending |
| COMP-01 | Phase 21 | Pending |
| COMP-02 | Phase 21 | Pending |
| COMP-03 | Phase 21 | Pending |
| COMP-04 | Phase 21 | Pending |
| COMP-05 | Phase 21 | Pending |
| COMP-06 | Phase 21 | Pending |
| CREDIT-01 | Phase 22 | Complete |
| CREDIT-02 | Phase 22 | Complete |
| CREDIT-03 | Phase 22 | Complete |
| CREDIT-04 | Phase 22 | Complete |
| CREDIT-05 | Phase 22 | Complete |
| CREDIT-06 | Phase 22 | Complete |
| CASHFLOW-01 | Phase 23 | Pending |
| CASHFLOW-02 | Phase 23 | Pending |
| CASHFLOW-03 | Phase 23 | Pending |
| CASHFLOW-04 | Phase 23 | Pending |
| CASHFLOW-05 | Phase 23 | Pending |
| ORIGIN-01 | Phase 24 | Pending |
| ORIGIN-02 | Phase 24 | Pending |
| ORIGIN-03 | Phase 24 | Pending |
| ORIGIN-04 | Phase 24 | Pending |
| MARKET-01 | Phase 24 | Pending |
| MARKET-02 | Phase 24 | Pending |
| UX-01 | Phases 20–24 | Complete |
| UX-02 | Phase 25 | Pending |
| UX-03 | Phase 25 | Pending |
| EXPORT-01 | Phase 26 | Pending |
| EXPORT-02 | Phase 26 | Pending |
| ROLES-01 | Phase 27 | Pending |
| ROLES-02 | Phase 27 | Pending |
| ROLES-03 | Phase 27 | Pending |
