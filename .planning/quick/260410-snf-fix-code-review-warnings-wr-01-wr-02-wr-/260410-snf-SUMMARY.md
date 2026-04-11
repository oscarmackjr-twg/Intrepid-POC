---
phase: snf-fix-code-review-warnings-wr-01-wr-02-wr-03-wr-04
plan: "01"
subsystem: backend/api
tags: [bugfix, financial-accuracy, security, re-portfolio]
dependency_graph:
  requires: []
  provides: [correct-net-loss-rate, correct-cpr-semantics, correct-delinquency-buckets, page-size-dos-guard]
  affects: [cashflow-performance-endpoint, delinquency-waterfall-endpoint, loans-list-endpoint]
tech_stack:
  added: []
  patterns: [SQLAlchemy case expression, FastAPI query param clamping]
key_files:
  modified:
    - backend/api/re_routes.py
    - backend/tests/test_re_api.py
decisions:
  - WR-02 CPR returns None (not 0) for principal shortfall — semantically a shortfall is not a prepayment event
  - WR-03 removes the 90-bucket entirely — industry standard is 90+ DPD = default, no separate 90 tier
  - WR-04 guard placed after sort_by whitelist check, before filters — page_size clamped silently (200) rather than rejected
metrics:
  duration_minutes: 12
  completed_date: "2026-04-10"
  tasks_completed: 3
  files_modified: 2
---

# Phase snf Plan 01: Fix Code Review Warnings WR-01 through WR-04 Summary

**One-liner:** Fixed four financial/security logic errors in re_routes.py — net loss rate now includes principal, CPR is null on shortfall, 90+ DPD maps to default, and page_size is DoS-guarded at 200.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | WR-01 net_loss_rate + WR-02 CPR None on shortfall | d6ec896 | re_routes.py, test_re_api.py |
| 2 | WR-03 delinquency bucket + WR-04 page_size cap | 1036553 | re_routes.py, test_re_api.py |
| 3 | Full suite smoke check (verification only) | — | — |

## Changes Made

### WR-01: net_loss_rate accumulates both principal and interest

**File:** `backend/api/re_routes.py` (~line 679)

Before: `total_scheduled_sum += sched_i_d` / `total_actual_sum += act_i_d`
After: `total_scheduled_sum += sched_p_d + sched_i_d` / `total_actual_sum += act_p_d + act_i_d`

Impact: net_loss_rate previously only reflected interest shortfalls. A loan paying $0 principal but full interest reported net_loss_rate=0. Now correctly includes principal shortfalls.

### WR-02: CPR is None for principal shortfall periods

**File:** `backend/api/re_routes.py` (~line 673)

Added `elif smm == Decimal("0"): cpr = Decimal("0")` branch. The `else` branch now sets `cpr = None` instead of `Decimal("0")`. A negative SMM means actual principal < scheduled — that is a shortfall, not a prepayment event. Returning 0 misrepresented it as "no prepayment."

### WR-03: 90+ DPD loans land in "default" bucket

**File:** `backend/api/re_routes.py` (~line 927)

Removed `(RELoan.days_past_due < 180, "90")` from the `case()` expression. Updated `ORDER` dict from `{"current":0,"30":1,"60":2,"90":3,"default":4}` to `{"current":0,"30":1,"60":2,"default":3}`. Updated `test_delinquency_waterfall` `expected_order` to remove `"90"`.

### WR-04: page_size clamped to MAX_PAGE_SIZE=200

**File:** `backend/api/re_routes.py` (~line 502)

Added after sort_by whitelist check:
```python
MAX_PAGE_SIZE = 200
if page_size < 1:
    raise HTTPException(status_code=400, detail="page_size must be >= 1")
if page_size > MAX_PAGE_SIZE:
    page_size = MAX_PAGE_SIZE
```

Mitigates T-snf-01 DoS threat (untrusted integer crossing client→API boundary).

## Tests Added

| Test | Covers | Result |
|------|--------|--------|
| `test_cashflow_net_loss_rate_includes_principal` | WR-01 | PASS |
| `test_cashflow_cpr_none_on_shortfall` | WR-02 | PASS |
| `test_delinquency_waterfall_90dpd_is_default` | WR-03 | PASS |
| `test_loans_page_size_cap` | WR-04 | PASS |

Full suite: 30/30 passed.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None introduced.

## Threat Flags

None — WR-04 resolves T-snf-01 as planned; no new surface introduced.

## Self-Check: PASSED

- `backend/api/re_routes.py` — exists, modified
- `backend/tests/test_re_api.py` — exists, modified
- Commit d6ec896 — verified in log
- Commit 1036553 — verified in log
- 30/30 tests pass
