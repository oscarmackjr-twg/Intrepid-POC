---
phase: 23-cash-flow-performance-page
plan: "02"
subsystem: frontend/pages
tags: [frontend, cashflow, recharts, react-query, decimal-coercion]
dependency_graph:
  requires: [23-01]
  provides: [ReCashFlowPage, cashflow-route]
  affects: [frontend/src/pages/ReCashFlowPage.tsx, frontend/src/App.tsx]
tech_stack:
  added: []
  patterns: [Recharts LineChart multi-series, Recharts BarChart, tanstack-react-query with filter keyedQueries, Decimal-as-string Number() coercion]
key_files:
  created:
    - frontend/src/pages/ReCashFlowPage.tsx
  modified:
    - frontend/src/App.tsx
decisions:
  - "Tooltip formatter signatures use (value) => [...] without type annotation — avoids TS2322 from Recharts ValueType|undefined vs number mismatch; Number(value ?? 0) coerces safely"
  - "formatPct/formatRate helpers included but voided — kept for future extension without removing the established helper pattern from Phase 22"
  - "market-context query omits filters from queryKey — market rates are global benchmarks, not portfolio-filtered"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-04-10"
  tasks_completed: 2
  files_modified: 2
---

# Phase 23 Plan 02: Cash Flow Frontend Page Summary

## One-Liner

Five-panel ReCashFlowPage (P&I LineChart, NOI BarChart, Yield metric row, CPR LineChart, Loss metric row) wired to /re-dashboard/cashflow — replacing the ReStubPage placeholder.

## What Was Built

**`frontend/src/pages/ReCashFlowPage.tsx`** — New page component with five panels covering all CASHFLOW requirements:

1. **P&I Actual vs Projected** (full-width LineChart, CASHFLOW-01) — two series (`actual_pi`, `projected_pi`) computed client-side from `scheduled_principal + scheduled_interest` vs `actual_principal + actual_interest`. Variance available in tooltip.

2. **NOI Trend** (half-width BarChart, CASHFLOW-02) — `total_noi` per period displayed as vertical bars with UPB formatting.

3. **CPR Trend** (half-width LineChart, CASHFLOW-04 partial) — `cpr * 100` per period as a percentage line chart.

4. **Yield Analysis** (full-width metric card row, CASHFLOW-03) — four cards: Gross Yield (from last period), Net Yield (gross - net_loss_rate), SOFR Spread, Treasury Spread. Spreads computed client-side from `/api/re/market-context` stub rates (SOFR 5.33%, Treasury 4.25%).

5. **Loss and Recovery** (full-width metric card row, CASHFLOW-04) — Net Loss Rate from API response, Realized Losses proxy (sum of P&I shortfalls), Recovery stub ($0 — no recovery column in model).

**Filter reactivity (CASHFLOW-05):** Both queries include `filters` in their `queryKey`, so any sidebar filter change invalidates and refetches automatically.

**`frontend/src/App.tsx`** — One import added (`ReCashFlowPage`) and one route changed: `<Route path="cashflow" element={<ReCashFlowPage />} />` replaces the `<ReStubPage />` placeholder.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create ReCashFlowPage.tsx with five panels | ce8ca1e | frontend/src/pages/ReCashFlowPage.tsx |
| 2 | Wire ReCashFlowPage into App.tsx route | 0207601 | frontend/src/App.tsx |

## Verification Results

```
npx tsc --noEmit  — no output (clean, zero errors)

grep "ReCashFlowPage" App.tsx:
  import ReCashFlowPage from './pages/ReCashFlowPage'
  <Route path="cashflow" element={<ReCashFlowPage />} />

grep "re-cashflow-performance" ReCashFlowPage.tsx:
  queryKey: ['re-cashflow-performance', filters],

grep "re-market-context" ReCashFlowPage.tsx:
  queryKey: ['re-market-context'],

grep -c "Number(" ReCashFlowPage.tsx: 21 matches
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Recharts Tooltip formatter type mismatch**
- **Found during:** Task 1 TypeScript compile check
- **Issue:** Plan's formatter signatures typed `(value: number)` but Recharts `Formatter<ValueType, NameType>` passes `ValueType | undefined`. TS2322 errors on all three Tooltip formatters.
- **Fix:** Removed explicit `number` type annotation; used `Number(value ?? 0)` coercion pattern — consistent with the established Phase 22 Decimal coercion approach and handles `undefined` safely.
- **Files modified:** frontend/src/pages/ReCashFlowPage.tsx
- **Commit:** ce8ca1e (included in Task 1 commit)

## Known Stubs

- **Recovery metric** (`ReCashFlowPage.tsx` Panel 5): hardcoded `$0` — no recovery column exists in `RELoanCashflow` model. Intentional POC stub; documented in code comment. Does not prevent the plan's goal from being achieved.
- **Market rates** (SOFR 5.33%, Treasury 4.25%): returned as stubs from `/api/re/market-context`. Spread calculations are live computation against these stub values. Intentional per Phase 23 research — real-feed hook markers are a future concern.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes introduced. Both queries use existing endpoints authenticated via httpOnly cookie (T-23-04, T-23-05 accepted in plan threat register).

## Self-Check: PASSED

- `frontend/src/pages/ReCashFlowPage.tsx` exists: confirmed (created in Task 1)
- `frontend/src/App.tsx` modified: confirmed (import + route on lines 17, 56)
- Commit `ce8ca1e` exists: confirmed via git log
- Commit `0207601` exists: confirmed via git log
- TypeScript compiles clean: confirmed (no output from `npx tsc --noEmit`)
