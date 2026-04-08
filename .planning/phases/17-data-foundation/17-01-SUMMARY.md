---
phase: 17-data-foundation
plan: "01"
subsystem: database
tags: [alembic, sqlalchemy, schema, migrations, re-loans]
dependency_graph:
  requires: [efe3898fdf4b migration (audit_log head)]
  provides: [re_loans table, re_loan_cashflows table, RELoan model, RELoanCashflow model]
  affects: [backend/db/models.py, alembic migration chain]
tech_stack:
  added: [faker>=33.0.0 (dev-only)]
  patterns: [SQLAlchemy Numeric(18,6) for monetary, Numeric(10,6) for rates, chained Alembic migrations]
key_files:
  created:
    - backend/migrations/versions/c56f6c6372a0_add_re_loans_table.py
    - backend/migrations/versions/119641453e41_add_re_loan_cashflows_table.py
    - backend/requirements-dev.txt
  modified:
    - backend/db/models.py
decisions:
  - NUMERIC(18,6) for all monetary columns (upb, original_balance) — per PROJECT.md financial accuracy constraint; never Float
  - NUMERIC(10,6) for rate columns (interest_rate, ltv, dscr) — lower precision sufficient for rates
  - Hand-written migrations (not autogenerate) to guarantee exact NUMERIC precision per T-17-01 threat mitigation
  - faker placed in requirements-dev.txt (not requirements.txt) — seed-only dependency must not reach production container
metrics:
  duration_minutes: 10
  completed_date: "2026-04-08"
  tasks_completed: 2
  files_changed: 4
---

# Phase 17 Plan 01: Database Schema Foundation Summary

SQLAlchemy models and Alembic migrations for re_loans (24 columns, 6 indexes) and re_loan_cashflows (9 columns, composite index) tables, chaining cleanly from the efe3898fdf4b audit_log head with NUMERIC precision throughout.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add RELoan and RELoanCashflow models + re_loans migration | 8c4f3b4 | backend/db/models.py, c56f6c6372a0_add_re_loans_table.py |
| 2 | Create re_loan_cashflows migration + add requirements-dev.txt | 6483dc7 | 119641453e41_add_re_loan_cashflows_table.py, requirements-dev.txt |

## What Was Built

### models.py additions
- Added `Numeric` to the sqlalchemy import line
- `RELoan(Base)` class: 24 columns — identity/admin (5), financials using NUMERIC precision (6), classification (6), dates (2), delinquency (2), pipeline (2), audit (1) — plus relationships to SalesTeam and RELoanCashflow
- `RELoanCashflow(Base)` class: 9 columns — id, loan_id FK, period_date, 5 cashflow NUMERIC columns, created_at — plus relationship back to RELoan

### Migration chain
```
60a8a67090c8 -> efe3898fdf4b -> c56f6c6372a0 -> 119641453e41
(holidays)      (audit_log)     (re_loans)      (re_loan_cashflows)
```

### re_loans table (c56f6c6372a0)
- 24 columns with correct NUMERIC precision:
  - Monetary: `upb`, `original_balance` → NUMERIC(18,6)
  - Rates: `interest_rate`, `ltv`, `dscr` → NUMERIC(10,6)
- 6 indexes: id, loan_number, as_of_date, property_type, state, sales_team_id
- ForeignKeyConstraint to sales_teams.id

### re_loan_cashflows table (119641453e41)
- 9 columns; all 5 cashflow amount columns → NUMERIC(18,6)
- ForeignKeyConstraint to re_loans.id
- Composite index `ix_re_loan_cashflows_loan_id_period_date` on (loan_id, period_date) for efficient per-loan time-series queries

### requirements-dev.txt
- Created new file with `faker>=33.0.0` — dev/seed-only, NOT in production requirements.txt

## Verification Results

- `alembic upgrade head` applied both new migrations with no errors
- `re_loans` table confirmed with 24 columns including correct NUMERIC precision (verified via information_schema.columns query: upb=numeric(18,6), interest_rate=numeric(10,6), dscr=numeric(10,6))
- `re_loan_cashflows` table confirmed with 9 columns including loan_id FK
- Models import cleanly: `from db.models import RELoan, RELoanCashflow` with all required attributes present
- faker not present in requirements.txt (production container unaffected)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — this plan creates schema only; no data rendering or stubs introduced.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundary changes introduced. Schema changes are internal DB only with no external exposure.

## Self-Check: PASSED

- [x] `backend/db/models.py` modified (RELoan and RELoanCashflow classes added)
- [x] `backend/migrations/versions/c56f6c6372a0_add_re_loans_table.py` created
- [x] `backend/migrations/versions/119641453e41_add_re_loan_cashflows_table.py` created
- [x] `backend/requirements-dev.txt` created
- [x] Commit 8c4f3b4 verified in git log
- [x] Commit 6483dc7 verified in git log
