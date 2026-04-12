---
phase: 24-origination-pipeline-market-context
reviewed: 2026-04-12T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - backend/api/re_schemas.py
  - backend/api/re_routes.py
  - backend/tests/test_re_api.py
  - frontend/src/types/re.ts
  - frontend/src/pages/ReOriginationPage.tsx
  - frontend/src/App.tsx
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 24: Code Review Report

**Reviewed:** 2026-04-12
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

This review covers the origination pipeline (API-08) and market context (API-09) backend endpoints, their Pydantic schemas, integration tests, TypeScript type definitions, and the new `ReOriginationPage` frontend component. The overall structure is sound: security scoping is consistently applied, the sort whitelist prevents injection, and the 404-for-out-of-scope pattern is correctly implemented. No critical (security or data-loss) issues were found.

Five warnings describe logic errors or missing edge-case handling that could produce incorrect output or crashes under realistic data conditions. Four info items note dead code, type mismatches, and minor quality concerns.

---

## Warnings

### WR-01: Delinquency bucket expression silently misclassifies 1-29 DPD loans

**File:** `backend/api/re_routes.py:960-965`

**Issue:** The `bucket_expr` CASE statement has a gap. The first branch matches only `days_past_due == 0` (exact zero). A loan with `days_past_due` of 1–29 falls through to `< 60`, landing it in the `"30"` bucket. A 1-DPD loan is not delinquent; it should be classified as `"current"`.

```python
bucket_expr = case(
    (RELoan.days_past_due == 0, "current"),   # 1-29 DPD is NOT caught here
    (RELoan.days_past_due < 60, "30"),          # catches 1-59 DPD — too broad
    (RELoan.days_past_due < 90, "60"),
    else_="default",
)
```

**Fix:** Change the first condition to `<= 29` (or `< 30`) so it covers all non-delinquent loans:

```python
bucket_expr = case(
    (RELoan.days_past_due < 30, "current"),
    (RELoan.days_past_due < 60, "30"),
    (RELoan.days_past_due < 90, "60"),
    else_="default",
)
```

The existing test suite only seeds loans with `days_past_due=0` for the "current" case, so this gap is not caught. Add a fixture loan with `days_past_due=15` and assert it lands in `"current"`.

---

### WR-02: `build_re_filters` — `borrower` ilike injects unsanitized wildcards

**File:** `backend/api/re_routes.py:111`

**Issue:** The borrower filter wraps the user-supplied value in `%...%` and passes it directly to `ilike()`. If a caller supplies a value containing `%` or `_` characters (valid SQL LIKE wildcards), those characters are not escaped, producing unintended wildcard behaviour. For example, `borrower=%` matches every loan. While this is not SQL injection (SQLAlchemy parameterizes the value), it leaks data beyond the intended partial match.

```python
filters.append(RELoan.borrower_name.ilike(f"%{params.borrower}%"))
```

**Fix:** Escape LIKE special characters before interpolation:

```python
escaped = params.borrower.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
filters.append(RELoan.borrower_name.ilike(f"%{escaped}%", escape="\\"))
```

---

### WR-03: `get_cashflow_performance` — `cashflow_filters` does not replicate all `build_re_filters` client filters

**File:** `backend/api/re_routes.py:639-654`

**Issue:** `get_cashflow_performance` manually rebuilds the cashflow-scoped filter list and omits three `FilterParams` fields: `vintage_year`, `borrower`, and `rate_type`. This means those three query parameters are silently ignored on the cashflow endpoint while they work on every other endpoint. A user filtering by `vintage_year=2021` would see cashflow data for all vintages, not just 2021.

```python
# cashflow_filters omits:
# if params.vintage_year is not None: ...
# if params.borrower is not None: ...
# if params.rate_type is not None: ...
```

**Fix:** Add the three missing filter clauses to `cashflow_filters` to match the behaviour of `build_re_filters`:

```python
if params.vintage_year is not None:
    cashflow_filters.append(RELoan.vintage_year == params.vintage_year)
if params.borrower is not None:
    escaped = params.borrower.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    cashflow_filters.append(RELoan.borrower_name.ilike(f"%{escaped}%", escape="\\"))
if params.rate_type is not None:
    cashflow_filters.append(RELoan.rate_type == params.rate_type)
```

---

### WR-04: `ReLoanFilters.vintage_year` typed as `string | null` but backend expects `int`

**File:** `frontend/src/types/re.ts:26`

**Issue:** `vintage_year` is typed as `string | null` in `ReLoanFilters` (the filters hook interface), but the corresponding `FilterParams.vintage_year` on the backend is `Optional[int]`. When a non-null value is passed from the frontend as a string (e.g. `"2022"`) it will serialize correctly in the URL query string, but the type annotation misleads any TypeScript code that reads the field back out of the filter state — it will treat it as `string` not `number`, causing type errors if arithmetic or comparison is applied. All other numeric filter fields (`loan_size_min`, `loan_size_max`) are correctly typed as `number | null`.

```typescript
// re.ts line 26 — wrong type
vintage_year: string | null
```

**Fix:**
```typescript
vintage_year: number | null
```

---

### WR-05: `ReOriginationPage` — non-null assertion on `volumeByMonth.get(key)` after `has` check

**File:** `frontend/src/pages/ReOriginationPage.tsx:59`

**Issue:** The code calls `volumeByMonth.get(key)!` (non-null assertion) on line 59. Although a `has` check was done two lines earlier, the `!` operator suppresses TypeScript's null safety. The pattern is correct at runtime but relies on the assumption that no concurrent modification can occur. More importantly, the same pattern uses `as unknown as Record<string, number>` to cast the initial object, which hides a type mismatch: `{ month: key }` is typed as `Record<string, number>` but `month` holds a `string`. Any downstream code that destructures this object expecting `month: number` would silently receive a `string`.

```typescript
// line 58-59
if (!volumeByMonth.has(key)) volumeByMonth.set(key, { month: key } as unknown as Record<string, number>)
volumeByMonth.get(key)![row.property_type] = Number(row.total_upb)
```

**Fix:** Introduce a typed pivot record interface and remove the `as unknown` cast:

```typescript
type PivotRow = { month: string; [propertyType: string]: string | number }
const volumeByMonth = new Map<string, PivotRow>()
for (const row of origination.data?.origination_by_month ?? []) {
  const key = `${row.year}-${String(row.month).padStart(2, '0')}`
  if (!volumeByMonth.has(key)) volumeByMonth.set(key, { month: key })
  volumeByMonth.get(key)![row.property_type] = Number(row.total_upb)
}
```

---

## Info

### IN-01: `get_market_context` accepts `db` dependency it never uses

**File:** `backend/api/re_routes.py:837-838`

**Issue:** `get_market_context` declares `db: Session = Depends(get_db)` but never queries the database. This opens a database connection for every call to the market-context endpoint unnecessarily.

```python
def get_market_context(
    current_user: User = Depends(require_sales_team_access()),
    db: Session = Depends(get_db),   # never used
) -> MarketContextResponse:
```

**Fix:** Remove the `db` parameter until a live data source is implemented. When the `TODO: LIVE-FEED-HOOK` is connected, add it back.

---

### IN-02: Market context `property_type` values use lowercase but loan data uses title case

**File:** `backend/api/re_routes.py:856-870`

**Issue:** The stubbed cap rates and vacancy rates use lowercase property type strings (`"multifamily"`, `"office"`, `"industrial"`, `"retail"`, `"hotel"`), while loan data throughout the system uses title case (`"Multifamily"`, `"Office"`, etc.). The frontend `ReOriginationPage` attempts to join them with `find((v) => v.property_type === cr.property_type)` (line 239), which is an exact-match comparison. When live data replaces the stubs this case mismatch will cause all vacancy rate lookups to return `undefined`.

**Fix:** Normalise the stub values to match the loan data convention (title case), or add a case-insensitive join in the frontend. Since the backend is the authoritative source, fix it there:

```python
cap_rates = [
    CapRate(property_type="Multifamily", value=Decimal("5.0"), source="stub"),
    CapRate(property_type="Office",      value=Decimal("7.5"), source="stub"),
    ...
]
```

---

### IN-03: `appraisal_history: list = Field(default_factory=list)` uses unparameterized `list`

**File:** `backend/api/re_schemas.py:287`

**Issue:** `appraisal_history` is typed as the bare `list` (no element type). This is a stub per the TODO comment, but the corresponding TypeScript type is `unknown[]`. When this field is eventually populated, downstream consumers will have no type information to work from. Using `list[dict]` or a typed stub model now would make the future migration cleaner.

**Fix:** At minimum, annotate as `list[Any]` with an `Any` import, or create a placeholder `AppraisalStub` model. This is a low-priority cleanup — acceptable for the current POC.

---

### IN-04: `test_loans_sort_valid` — assertion is vacuously true for single-page results

**File:** `backend/tests/test_re_api.py:352-354`

**Issue:** The sort-order assertion extracts UPBs from the response and checks they are sorted descending. With 7 fixture loans all on one page, this works. However, the assertion compares the filtered `upbs` list against `sorted(upbs, reverse=True)`, which is always true if all loans have distinct UPBs. The test does not assert the _first_ item has the highest UPB, nor that there is more than one item. If a future change returns only one loan the test would still pass vacuously.

**Fix:** Add an explicit multi-item check:
```python
assert len(upbs) > 1, "Sort test needs more than one loan to verify order"
assert upbs[0] >= upbs[-1], "First item must be >= last item in descending sort"
```

---

_Reviewed: 2026-04-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
