---
phase: 24-origination-pipeline-market-context
verified: 2026-04-12T00:00:00Z
status: human_needed
score: 6/7 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Confirm ORIGIN-02 scope acceptance: Net Origination Volume KPI shows gross origination total (no payoff subtraction)"
    expected: "Stakeholder accepts gross origination volume as satisfying ORIGIN-02 / roadmap SC#2, given that payoff data is not in the POC schema. If not accepted, payoff tracking must be added to the DB model and API."
    why_human: "Roadmap SC#2 explicitly states 'originations minus payoffs' but the CONTEXT decision D-05 documents that payoff tracking is not in the current schema. No payoff data exists anywhere in the backend. Whether gross origination volume satisfies the requirement intent is a product/scope decision."
  - test: "Visual check: Origination Pipeline page renders all 5 panels correctly"
    expected: "Navigate to /re-dashboard/origination. Verify: (1) stacked bar with property type segments, (2) Net Origination Volume dollar KPI, (3) horizontal pipeline funnel bars with loan counts in tooltip, (4) vintage analysis table with 6 columns, (5) Market Context section with 10Y Treasury/SOFR values and trend arrows, (6) cap/vacancy table. Click a bar segment and confirm the URL updates with ?property_type=X and all panels re-fetch."
    why_human: "Visual rendering, chart interactivity, and click-to-filter URL behavior cannot be verified programmatically."
  - test: "Check SOFR trend arrow rendering"
    expected: "Backend returns trend='declining' for SOFR but frontend checks trend==='down'. SOFR will show → (neutral) instead of ↓. Confirm whether this is acceptable for the POC or whether backend stub should use 'down' instead of 'declining'."
    why_human: "Cosmetic stub data mismatch — acceptable for POC but needs confirmation."
---

# Phase 24: Origination Pipeline + Market Context Verification Report

**Phase Goal:** Users can track new origination activity, portfolio growth, and pipeline stage progression, and can view stubbed market benchmark rates clearly labeled as indicative — completing all six dashboard sections
**Verified:** 2026-04-12
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Origination-pipeline API returns monthly data broken down by property type | VERIFIED | `re_schemas.py` line 331: `property_type: str` in `OriginationMonth`; `re_routes.py` groups by `RELoan.property_type` in query |
| 2 | Vintage breakdown includes average interest rate per vintage year | VERIFIED | `re_schemas.py` line 356: `avg_rate: Optional[JsonDecimal]` in `VintageGroup`; `re_routes.py` includes `func.avg(RELoan.interest_rate)` as column 5 |
| 3 | TypeScript interfaces match updated backend response shapes | VERIFIED | `re.ts` lines 203-224: `OriginationMonth` has `property_type: string`, `VintageGroup` has `avg_rate: number \| null` |
| 4 | User sees origination volume stacked bar chart broken down by property type per month | VERIFIED | `ReOriginationPage.tsx` lines 88-97: `stackId="origination"`, `onClick` on each `<Bar>` calls `setFilter('property_type', pt)` |
| 5 | User sees pipeline funnel horizontal bar with loan count and UPB per stage | VERIFIED | `ReOriginationPage.tsx` line 127: `layout="vertical"` horizontal BarChart; Tooltip shows UPB + loan_count |
| 6 | User sees vintage analysis table with loan count, UPB, avg LTV, avg DSCR, avg rate per year | VERIFIED | `ReOriginationPage.tsx` lines 154-178: HTML table with 6 columns (Vintage, Loans, UPB, Avg LTV, Avg DSCR, Avg Rate) |
| 7 | User sees Market Context section with Treasury and SOFR rate cards showing trend arrows | VERIFIED | `ReOriginationPage.tsx` lines 196-220: Treasury + SOFR cards with Unicode arrows (↑/↓/→) |
| 8 | User sees cap rates and vacancy rates table by property type labeled as indicative | VERIFIED | `ReOriginationPage.tsx` line 186: "Indicative values — not connected to live feeds"; cap/vacancy table lines 229-254 |
| 9 | Clicking a property type bar segment applies that property type as a global filter | VERIFIED | `ReOriginationPage.tsx` line 94: `onClick={() => setFilter('property_type', pt)}` |
| 10 | User sees a Net Origination Volume KPI card with dollar total | PARTIAL | Card exists (lines 102-116) and sums all `total_upb`; however roadmap SC#2 requires "originations minus payoffs" — no payoff data exists anywhere in the backend schema |

**Score:** 9/10 truths fully verified; 1 partial (ORIGIN-02 / roadmap SC#2)

### Deferred Items

None.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/api/re_schemas.py` | `property_type: str` in OriginationMonth, `avg_rate: Optional[JsonDecimal]` in VintageGroup | VERIFIED | Lines 331, 356 confirmed |
| `backend/api/re_routes.py` | Origination query groups by `RELoan.property_type`; vintage query includes `func.avg(RELoan.interest_rate)` | VERIFIED | Lines 758, 761, 803 confirmed |
| `frontend/src/types/re.ts` | `property_type: string` in OriginationMonth, `avg_rate: number \| null` in VintageGroup | VERIFIED | Lines 206, 223 confirmed |
| `frontend/src/pages/ReOriginationPage.tsx` | Complete origination pipeline + market context page, >= 150 lines | VERIFIED | 262 lines; all 5 panels present |
| `frontend/src/App.tsx` | Route wiring: `element={<ReOriginationPage />}` on origination path | VERIFIED | Line 54 confirmed; no ReStubPage remaining |
| `backend/tests/test_re_api.py` | 3 new tests for property_type field, avg_rate field, split-by-property-type | VERIFIED | Lines 438-477 confirmed; all 3 tests present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ReOriginationPage.tsx` | `/api/re/origination-pipeline` | TanStack Query with `['re-origination-pipeline', filters]` key | VERIFIED | Line 26: `queryKey: ['re-origination-pipeline', filters]` |
| `ReOriginationPage.tsx` | `/api/re/market-context` | TanStack Query with static `['re-market-context']` key | VERIFIED | Line 40: `queryKey: ['re-market-context']` |
| `ReOriginationPage.tsx` | `useReLoanFilters` | `setFilter('property_type', pt)` on bar click | VERIFIED | Line 94: `onClick={() => setFilter('property_type', pt)}` |
| `App.tsx` | `ReOriginationPage.tsx` | Route element at `path="origination"` | VERIFIED | Lines 18, 54: import + element confirmed |
| `re_routes.py` | `re_schemas.py` | OriginationMonth and VintageGroup imported and used | VERIFIED | Both schemas used in get_origination_pipeline |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `ReOriginationPage.tsx` | `origination.data` | `GET /api/re/origination-pipeline` via TanStack Query | Yes — routes to SQLAlchemy query on `RELoan` grouped by `year_col, month_col, RELoan.property_type` | FLOWING |
| `ReOriginationPage.tsx` | `market.data` | `GET /api/re/market-context` via TanStack Query | Static stub values — intentional per MARKET-01 (POC); labeled "Indicative" per D-09 | FLOWING (intentional stub) |
| `volumeData` | Pivot of `origination_by_month` rows | Map transform from live API data | Yes — populated from live query result | FLOWING |
| `netOriginationVolume` | Sum of `total_upb` from `origination_by_month` | Live API data | Yes — sums real DB values; no payoff subtraction | FLOWING (partial: gross only, not net) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend schemas have required fields | `grep "property_type: str" backend/api/re_schemas.py` | Found at line 331 | PASS |
| Backend route groups by property_type | `grep "RELoan.property_type" backend/api/re_routes.py` | Found in group_by at lines 758, 761 | PASS |
| TypeScript OriginationMonth has property_type | `grep "property_type: string" frontend/src/types/re.ts` | Found at line 206 | PASS |
| ReOriginationPage query key contains filters | `grep "re-origination-pipeline.*filters" frontend/src/pages/ReOriginationPage.tsx` | Found at line 26 | PASS |
| App.tsx routes to ReOriginationPage | `grep "origination.*ReOriginationPage" frontend/src/App.tsx` | Found at line 54 | PASS |
| Tests exist for new fields | `grep "test_origination_pipeline_property_type_field" backend/tests/test_re_api.py` | Found at line 438 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ORIGIN-01 | 24-01, 24-02 | Origination volume by month broken down by property type | SATISFIED | Stacked bar with property_type grouping; API groups by RELoan.property_type |
| ORIGIN-02 | 24-02 | Net portfolio growth/shrinkage (originations minus payoffs) | PARTIAL | Gross origination volume KPI exists; payoff data absent from schema — D-05 documents this as intentional POC scope limitation. Roadmap SC#2 explicitly requires "originations minus payoffs". |
| ORIGIN-03 | 24-02 | Pipeline funnel (underwriting → approved → closing → funded) | SATISFIED | Horizontal BarChart with layout="vertical" rendering pipeline_funnel stages |
| ORIGIN-04 | 24-01, 24-02 | Vintage analysis — performance metrics by origination year | SATISFIED | HTML table with loan_count, total_upb, avg_ltv, avg_dscr, avg_rate per vintage year |
| MARKET-01 | 24-02 | 10Y Treasury and SOFR stub values with trend shapes and live-feed hook markers | SATISFIED | Rate cards with Unicode arrows; backend has `# TODO: LIVE-FEED-HOOK` markers at lines 849, 852, 855, 864 |
| MARKET-02 | 24-02 | Stubbed cap rates and vacancy rates by property type, labeled indicative | SATISFIED | "Indicative values — not connected to live feeds" label; cap/vacancy table by property type |
| UX-01 | 24-02 | Clicking chart segment applies filter across entire dashboard | SATISFIED | `onClick={() => setFilter('property_type', pt)}` on stacked bar segments |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/api/re_routes.py` | 850-871 | Market context returns static stub values | Info | Intentional POC design per MARKET-01/MARKET-02 requirements; labeled "Indicative values" in UI and marked with LIVE-FEED-HOOK TODO comments |
| `backend/api/re_routes.py` | 853 | SOFR trend value `"declining"` does not match frontend's expected `"down"` string | Warning | SOFR trend arrow renders as → (neutral) instead of ↓ (declining); cosmetic only, no functional impact on data |

### Human Verification Required

#### 1. Confirm ORIGIN-02 scope acceptance

**Test:** Review whether the "Net Origination Volume" KPI card (showing gross origination total) satisfies ORIGIN-02.

**Expected:** Stakeholder explicitly accepts that for this POC, net portfolio growth means gross origination volume without payoff subtraction, because payoff data does not exist in the `re_loans` schema. If not accepted, `RELoan` model needs a `payoff_date` or equivalent column and the API must compute originations minus payoffs.

**Why human:** Roadmap success criterion #2 says "Net portfolio growth (originations minus payoffs) is visible as a trend or summary metric." The CONTEXT D-05 documents a scoping decision to show gross only. No payoff data exists anywhere in the backend. Whether this satisfies the requirement is a product/business decision, not a code issue.

#### 2. Visual check — Origination Pipeline page renders all 5 panels

**Test:** Start the dev server and navigate to `/re-dashboard/origination`. Verify:
1. Page loads (no stub/placeholder text)
2. Top-left: Stacked bar chart with property type color segments per month
3. Top-right: "Net Origination Volume" card with a dollar total
4. Bottom-left: Pipeline Funnel with horizontal bars; tooltip shows UPB and loan count
5. Bottom-right: Vintage Analysis table with columns Vintage, Loans, UPB, Avg LTV, Avg DSCR, Avg Rate
6. Below grid: "Market Context" heading with "Indicative values — not connected to live feeds" subtitle
7. Rate cards for 10Y Treasury and SOFR with trend arrows
8. Cap rates and vacancy rates table by property type
9. Click a property type bar segment — URL updates with `?property_type=X` and all panels re-fetch

**Expected:** All 5 panels visible with live data; click-to-filter updates URL and triggers re-fetch.

**Why human:** Visual rendering, chart interactivity, and URL parameter behavior cannot be verified programmatically.

#### 3. SOFR trend arrow cosmetic check

**Test:** Observe the SOFR rate card trend arrow in the Market Context section.

**Expected:** The backend returns `trend: "declining"` for SOFR, but the frontend checks `trend === 'down'`. The SOFR card will show → (neutral) instead of ↓. Confirm whether this is acceptable or whether the stub value should be changed to `"down"` for consistency.

**Why human:** Acceptable for POC (both values are stubs), but worth confirming the convention for trend string values is consistent (`"up"/"down"/"flat"`) across the codebase.

### Gaps Summary

No hard blocking gaps were found. All artifacts exist, are substantive, and are wired to live data sources.

The single notable issue is ORIGIN-02 / roadmap success criterion #2: the roadmap contract requires "originations minus payoffs" but no payoff data exists in the schema. The CONTEXT D-05 made an explicit scoping decision to show gross origination volume only. This is not a code defect but a requirements scope decision that needs stakeholder confirmation. Until that is confirmed, status is `human_needed`.

A cosmetic stub inconsistency exists: the backend returns `trend: "declining"` for SOFR while the frontend expects `"down"` — resulting in SOFR showing a neutral arrow instead of a declining arrow. This is low-severity for a POC stub.

---

_Verified: 2026-04-12_
_Verifier: Claude (gsd-verifier)_
