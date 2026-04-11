# Phase 23: Cash Flow & Performance Page — Research

**Researched:** 2026-04-10
**Domain:** Recharts multi-series line charts, cashflow time-series visualization, yield/spread calculations
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CASHFLOW-01 | Monthly P&I line chart with actual vs projected series and variance indicator | `/api/re/cashflow-performance` returns `periods[].{scheduled_principal, actual_principal, scheduled_interest, actual_interest}` — compute projected_pi = scheduled_p + scheduled_i, actual_pi = actual_p + actual_i, variance = actual - projected client-side |
| CASHFLOW-02 | NOI trend chart over 12 months | `/api/re/cashflow-performance` returns `periods[].total_noi` — direct BarChart |
| CASHFLOW-03 | Yield analysis: gross yield, net yield after losses, spread to SOFR and Treasury | `cashflow-performance` has `gross_yield` per period and `net_loss_rate` at response level; `/api/re/market-context` has `sofr.value` and `ten_year_treasury.value` (stubs 5.33% and 4.25%) — spread computed client-side |
| CASHFLOW-04 | CPR trend line + loss/recovery tracking (realized losses, recoveries, net loss rate) | `cashflow-performance` has `periods[].cpr` and `net_loss_rate`; realized losses proxy = sum(scheduled_pi - actual_pi) across periods; recovery = 0 for POC (no recovery column in RELoanCashflow) |
| CASHFLOW-05 | Applying filter from sidebar updates all charts without page reload | `useReLoanFilters()` already established — same pattern as Phase 21/22 |
| UX-01 | Click chart segment applies filter | CPR/NOI/P&I don't map cleanly to filter dimensions — no-op click is acceptable per Phase 22 precedent for panels where segments don't correspond to filter keys |
</phase_requirements>

---

## Summary

Phase 23 replaces the `/re-dashboard/cashflow` stub with a fully implemented Cash Flow & Performance page. **No new backend endpoints are required** — all five success criteria can be satisfied by combining data from two existing endpoints:

1. `GET /api/re/cashflow-performance` (API-07) — returns 12 monthly periods with P&I actuals/projected, NOI, gross yield, CPR, and a net loss rate summary.
2. `GET /api/re/market-context` (API-09) — returns stub SOFR (5.33%) and 10Y Treasury (4.25%) rates for spread calculations.

The existing `CashflowPerformanceResponse` and `MarketContextResponse` TypeScript types in `re.ts` are already defined and complete — no new types are needed.

The frontend pattern is identical to Phase 22: `ReDashboard.tsx` already has the "Cash Flow" tab wired to `/re-dashboard/cashflow`. The only route change needed in `App.tsx` is replacing `<ReStubPage />` with `<ReCashFlowPage />` at that route.

**Primary recommendation:** 2-plan phase — Plan 01: full frontend page; Plan 02: verification.

---

## Standard Stack

### Core (all already installed — no new packages)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | 3.8.1 | Multi-series LineChart for P&I and CPR, BarChart for NOI | D-01 locked from Phase 21 |
| @tanstack/react-query | 5.96.2 | Data fetching with filter-keyed queries | Established pattern |
| react-router-dom | 6.30.3 | Route wiring; replace stub at `/re-dashboard/cashflow` | Already installed |
| axios | 1.7.7 | HTTP client inside queryFn | Already installed |
| tailwindcss | 4.1.18 | All styling | Already installed |

**No new npm installs required.**

---

## Endpoint Availability Analysis

### All Endpoints Exist — No New Backend Work Needed

| Panel | Endpoint | Key Fields | Status |
|-------|----------|-----------|--------|
| CASHFLOW-01 P&I line chart | `GET /api/re/cashflow-performance` | `periods[].{period_date, scheduled_principal, scheduled_interest, actual_principal, actual_interest}` | READY — compute projected_pi and actual_pi client-side |
| CASHFLOW-02 NOI trend | `GET /api/re/cashflow-performance` | `periods[].{period_date, total_noi}` | READY — direct BarChart |
| CASHFLOW-03 Yield analysis | `GET /api/re/cashflow-performance` + `GET /api/re/market-context` | `periods[].gross_yield`, `net_loss_rate`, `sofr.value`, `ten_year_treasury.value` | READY — gross yield from last period; spreads = gross_yield - benchmark rates |
| CASHFLOW-04 CPR trend | `GET /api/re/cashflow-performance` | `periods[].{period_date, cpr}` | READY — LineChart |
| CASHFLOW-04 Loss/recovery | `GET /api/re/cashflow-performance` | `net_loss_rate`, computed realized_losses = sum(scheduled_pi - actual_pi) | READY — net_loss_rate from response; recovery = 0 (no recovery column in model) |
| CASHFLOW-05 Filter reactivity | `useReLoanFilters()` | Filter queryKey integration | READY — same pattern as Phase 21/22 |

[VERIFIED: re_routes.py lines 605-701 for cashflow-performance; lines 798-842 for market-context; re_schemas.py lines 290-311 for types; frontend/src/types/re.ts lines 183-248 for TS types]

---

## Architecture Patterns

### Recommended Project Structure (after Phase 23)

```
frontend/src/
├── pages/
│   ├── ReDashboard.tsx              # Unchanged — already has Cash Flow tab wired
│   ├── ReExecutiveSummaryPage.tsx   # Unchanged
│   ├── RePortfolioPage.tsx          # Unchanged
│   ├── ReCreditQualityPage.tsx      # Unchanged
│   └── ReCashFlowPage.tsx           # NEW — five-panel cash flow page
├── types/
│   └── re.ts                        # No changes — all types already present
└── App.tsx                          # 1-line change: ReStubPage → ReCashFlowPage
```

### Five Panel Layout

```
┌─────────────────────────────────────────────────────┐
│  P&I Actual vs Projected (LineChart, 2 series)       │
│  ← actual_pi, projected_pi, variance tooltip         │
├──────────────────┬──────────────────────────────────┤
│  NOI Trend       │  CPR Trend                        │
│  (BarChart)      │  (LineChart)                      │
├──────────────────┴──────────────────────────────────┤
│  Yield Analysis (metric card row)                    │
│  Gross Yield | Net Yield | SOFR Spread | T-spread    │
├─────────────────────────────────────────────────────┤
│  Loss & Recovery (metric card row)                   │
│  Net Loss Rate | Realized Losses | Recovery (stub)   │
└─────────────────────────────────────────────────────┘
```

### Recharts Multi-Series Line Chart Pattern

```tsx
<LineChart data={data}>
  <Line dataKey="actual_pi" stroke="#0f2e5a" name="Actual P&I" />
  <Line dataKey="projected_pi" stroke="#94a3b8" strokeDasharray="4 2" name="Projected P&I" />
  <Tooltip formatter={(value, name) => [formatCurrency(value), name]} />
</LineChart>
```

### Yield Analysis Calculation

```ts
// From last period (most recent month)
const lastPeriod = periods[periods.length - 1]
const grossYield = lastPeriod?.gross_yield ?? 0
const netYield = grossYield - (netLossRate ?? 0)
const sofrSpread = grossYield - (sofr?.value ?? 0)
const treasurySpread = grossYield - (tenYearTreasury?.value ?? 0)
```

---

## Technical Notes

### CPR Calculation (already in backend)
The backend computes CPR per period using SMM = (actual_principal - scheduled_principal) / total_upb, then CPR = 1 - (1 - SMM)^12. When actual < scheduled (no prepayment), CPR = 0. The frontend renders this as a percentage line chart.

### Loss Proxy
`net_loss_rate` in the response = max(0, (sum_scheduled_pi - sum_actual_pi) / total_upb). This is a proxy; the seeded data may produce 0 if actuals match scheduled. Showing 0.00% is acceptable for POC — same approach as Phase 22's stub recovery.

### UX-01 Click-to-Filter
P&I, NOI, and CPR line charts don't map to filter dimensions cleanly. Following Phase 22 precedent (LTV/DSCR buckets also didn't apply clean filters), the charts will have no click handler. The sidebar remains the filter mechanism.

### Filter Reactivity (CASHFLOW-05)
Both queries use `[..., filters]` in the queryKey, which invalidates and refetches when the Zustand filter store updates — identical to credit quality implementation.
