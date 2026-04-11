---
phase: 23-cash-flow-performance-page
reviewed: 2026-04-10T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - backend/tests/test_re_api.py
  - frontend/src/pages/ReCashFlowPage.tsx
  - frontend/src/App.tsx
  - backend/api/re_routes.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 23: Code Review Report

**Reviewed:** 2026-04-10
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Four files were reviewed: the RE routes backend (`re_routes.py`), the new cash-flow frontend page (`ReCashFlowPage.tsx`), the router registration (`App.tsx`), and the integration test suite (`test_re_api.py`).

The cash-flow page itself is well-structured. The primary concerns are in `re_routes.py`: the net-loss-rate accumulator only sums interest shortfalls (excluding principal), the CPR formula produces `Decimal("0")` for both "zero prepayments" and "collection shortfall" without distinction, and the delinquency waterfall's "default" bucket is bounded to 180+ DPD rather than 90+ as is standard. Additionally, `page_size` is documented as bounded but the bound is never enforced. None of these are crashes — all are logic errors that produce incorrect financial output.

---

## Warnings

### WR-01: net_loss_rate accumulates interest only — principal shortfalls excluded

**File:** `backend/api/re_routes.py:700-701`
**Issue:** The two running-total accumulators (`total_scheduled_sum`, `total_actual_sum`) only add `sched_i_d` and `act_i_d` (interest). Principal values (`sched_p_d`, `act_p_d`) are never added. The denominator comment and the frontend label both state this is "(scheduled - actual) / total UPB" for P&I, but in practice only the interest delta is measured. Any principal shortfall (actual < scheduled principal) is silently ignored, understating the net loss rate.

```python
# Current (line 700-701): interest only
total_scheduled_sum += sched_i_d
total_actual_sum += act_i_d

# Fix: include both principal and interest
total_scheduled_sum += sched_p_d + sched_i_d
total_actual_sum += act_p_d + act_i_d
```

---

### WR-02: CPR formula conflates "no prepayments" with "principal shortfall"

**File:** `backend/api/re_routes.py:692-698`
**Issue:** When `act_p_d < sched_p_d` (i.e., the borrower paid less principal than scheduled — a shortfall), `smm` is negative. The branch `else: cpr = Decimal("0")` silently sets CPR to zero, which is the same value produced when there are genuinely no prepayments. The two semantically different states are indistinguishable in the output, and the frontend CPR trend chart will display 0% for both. A negative SMM indicates a collection problem, not a zero-prepayment environment.

```python
# Current
if smm > Decimal("0"):
    cpr = Decimal("1") - (Decimal("1") - smm) ** Decimal("12")
else:
    cpr = Decimal("0")

# Fix: CPR is a prepayment metric and is defined only when smm >= 0.
# Return None (not 0) for shortfall periods so the frontend can distinguish.
if smm > Decimal("0"):
    cpr = Decimal("1") - (Decimal("1") - smm) ** Decimal("12")
elif smm == Decimal("0"):
    cpr = Decimal("0")
else:
    cpr = None  # shortfall — not a prepayment event
```

The frontend already guards `p.cpr != null` on line 89 of `ReCashFlowPage.tsx`, so returning `None` is safe.

---

### WR-03: Delinquency waterfall "default" bucket captures 180+ DPD, not 90+

**File:** `backend/api/re_routes.py:948-955`
**Issue:** The `case` expression for the delinquency waterfall uses `days_past_due < 180` as the upper bound for the "90" bucket, meaning:
- "90" bucket = 90–179 DPD
- "default" bucket = 180+ DPD

Industry convention (and what users will expect from the label "default") is that 90+ DPD is the default threshold. Loans with 90–179 DPD appear in the "90" bucket, not "default," which misrepresents credit severity and will under-report the "default" balance. The test fixture `RE-007` has `days_past_due=200` and `delinquency_status="default"`, which passes the test only because 200 ≥ 180 — but a real loan with 120 DPD and status "default" would be miscategorized.

```python
# Current
bucket_expr = case(
    (RELoan.days_past_due == 0, "current"),
    (RELoan.days_past_due < 60, "30"),
    (RELoan.days_past_due < 90, "60"),
    (RELoan.days_past_due < 180, "90"),
    else_="default",
)

# Fix: use 90 as the default threshold
bucket_expr = case(
    (RELoan.days_past_due == 0, "current"),
    (RELoan.days_past_due < 60, "30"),
    (RELoan.days_past_due < 90, "60"),
    else_="default",  # 90+ DPD = default
)
# Drop the "90" bucket entirely, or re-label the last explicit bucket as "90+"
# and keep a separate "default" driven by delinquency_status == 'default':
# (RELoan.delinquency_status == "default", "default"),
```

Note: if a distinct "90" vs "default" distinction is intentional (e.g., 90–179 DPD is "90dpd" and 180+ is "default"), that should be driven by `delinquency_status` rather than a raw DPD threshold of 180.

---

### WR-04: page_size has no enforced upper bound despite documented security control T-18-04

**File:** `backend/api/re_routes.py:485-517`
**Issue:** The docstring on `get_loans` states "page_size bounded to prevent memory exhaustion (T-18-04)" but there is no `if page_size > MAX` guard anywhere in the function. A caller can pass `page_size=1000000` and the query will `LIMIT 1000000`, returning the full dataset in a single response. The documented control does not exist in the implementation.

```python
# Fix: add at the top of get_loans(), after the sort_by whitelist check
MAX_PAGE_SIZE = 200
if page_size < 1:
    raise HTTPException(status_code=400, detail="page_size must be >= 1")
if page_size > MAX_PAGE_SIZE:
    page_size = MAX_PAGE_SIZE  # or raise 400 — clamp is friendlier for clients
```

---

## Info

### IN-01: Dead code — formatPct and formatRate suppressed with void

**File:** `frontend/src/pages/ReCashFlowPage.tsx:39-41`
**Issue:** `formatPct` and `formatRate` are defined (lines 29-37) but not used in the component. They are retained via `void formatPct; void formatRate` to suppress the TypeScript unused-variable warning. This is dead code that will accumulate over time.

**Fix:** Remove both functions and the `void` suppression lines. If they are needed for a future panel, add them when the panel is implemented, or move them to a shared utility file (`src/utils/format.ts`).

---

### IN-02: Test hardcodes stub rate values — brittle if stub changes

**File:** `backend/tests/test_re_api.py:499-500`
**Issue:** `test_market_context_contract` asserts `float(treasury["value"]) == pytest.approx(4.25, abs=0.01)` and `sofr == pytest.approx(5.33, abs=0.01)`. These values are hardcoded in the test to match the hardcoded stub values in `re_routes.py`. If the stub values are updated, both files must be updated in sync. The test passes but the constraint is fragile.

**Fix:** Either import the stub constants from the route module, or document explicitly that these tests are intentionally tied to the stub values and must be updated together.

---

### IN-03: Concentration limits are hardcoded in-function with TODO comment

**File:** `backend/api/re_routes.py:265-268`
**Issue:** `_LIMITS` dict is defined inside `get_concentration()` on every request call with a `TODO: POLICY-CONFIG — move to DB settings in production` comment. This is dead-code-adjacent — the TODO has been present across phases without a tracking ticket.

**Fix:** Either promote to a module-level constant (acceptable for POC) or create a GitHub issue to track the DB-settings migration. At minimum, lift it to module level so it isn't re-allocated on every request.

```python
# Module-level (top of file)
_CONCENTRATION_LIMITS = {
    "state": Decimal("25"),
    "property_type": Decimal("40"),
    "borrower": Decimal("10"),
}
```

---

_Reviewed: 2026-04-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
