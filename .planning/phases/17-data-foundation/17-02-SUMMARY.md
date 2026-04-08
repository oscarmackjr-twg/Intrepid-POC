---
phase: 17-data-foundation
plan: "02"
subsystem: database
tags: [seed-data, faker, numpy, cre-portfolio, re-loans, integration-tests]
dependency_graph:
  requires: [17-01 (RELoan and RELoanCashflow models + migrations)]
  provides: [seed_re_loans.py, test_re_loans.py, 500 T0 loans, 500 T1 loans, 6000 cashflows]
  affects: [backend/scripts/seed_re_loans.py, backend/tests/test_re_loans.py]
tech_stack:
  added: [faker>=33.0.0 (already in requirements-dev.txt from Plan 01), numpy (already in requirements.txt)]
  patterns: [np.random.default_rng(seed=42) for reproducibility, to_dec() numpy-to-Decimal conversion, truncate child-before-parent for idempotency]
key_files:
  created:
    - backend/scripts/seed_re_loans.py
    - backend/tests/test_re_loans.py
  modified: []
decisions:
  - Seed uses db.flush() between T0 and cashflow generation to obtain auto-generated IDs before cashflow loop
  - T1 loans use same loan_number as T0 — same loan population, different as_of_date snapshot (per CONTEXT.md)
  - Cashflows linked to T0 loan IDs only — T1 snapshots do not duplicate cashflow records
  - rng.choice with normalized weights ensures reproducible weighted random selection without pandas dependency
  - 8 tests created (7 minimum per plan + 1 relationship test for ORM coverage)
metrics:
  duration_minutes: 3
  completed_date: "2026-04-08"
  tasks_completed: 2
  files_changed: 2
---

# Phase 17 Plan 02: CRE Seed Data and Integration Tests Summary

Seed script generating 500 T0 + 500 T1 RE loans with statistically realistic CRE distributions (LTV ~N(0.67,0.08), DSCR inversely correlated, bell-curved risk ratings around BBB) and 6,000 monthly cashflows across 6 property types, 21 states, 24 MSAs — plus 8 integration tests verifying schema precision and insert/query round-trips.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create seed_re_loans.py with realistic CRE portfolio data | 2d83489 | backend/scripts/seed_re_loans.py |
| 2 | Create test_re_loans.py integration tests verifying schema and seed data | a628aa6 | backend/tests/test_re_loans.py |

## What Was Built

### seed_re_loans.py

- `N_LOANS = 500`, `T0_DATE = 2025-09-30`, `T1_DATE = 2025-12-31`
- `rng = np.random.default_rng(seed=42)` and `Faker.seed(42)` for full reproducibility
- `to_dec(val, places=6)` converts numpy floats to `Decimal` via `Decimal(str(round(float(val), places)))`
- `generate_t0_loans()`: 500 T0 loans with weighted distributions for property type (35% multifamily), state (concentrate NY/CA/TX/FL/IL), risk rating (bell-curved around BBB), rate type (60% fixed), delinquency (85% current)
- `generate_t1_loans(t0_loans)`: 500 T1 loans with ~8% downgrades, ~5% upgrades, rest unchanged; `prior_risk_rating` stores T0 rating
- `generate_cashflows(t0_loans)`: 12 monthly records per T0 loan (Oct 2024 – Sep 2025); all amounts use `to_dec()`
- `seed_re_loans()`: truncates `re_loan_cashflows` then `re_loans` (child-before-parent), calls `db.flush()` after T0 insert to get IDs, then adds T1 + cashflows

### Verified distributions (post-seed):

| Metric | Expected | Actual |
|--------|----------|--------|
| T0 loans | >= 500 | 500 |
| T1 loans | >= 500 | 500 |
| Cashflows | 6000 (12 * 500) | 6000 |
| Property types | >= 5 | 6 |
| States | >= 20 | 21 |
| MSAs | >= 8 | 24 |
| Idempotency | same counts on re-run | PASSED |

### test_re_loans.py (8 tests, all passing)

| Test | Coverage |
|------|---------|
| `test_re_loans_table_columns` | All 24 RELoan columns match exactly (DATA-01) |
| `test_re_loans_numeric_precision` | upb/original_balance=NUMERIC(18,6); interest_rate/ltv/dscr=NUMERIC(10,6) |
| `test_re_loan_cashflows_table_columns` | All 9 RELoanCashflow columns match exactly (DATA-02) |
| `test_re_loan_cashflows_numeric_precision` | All 5 cashflow amounts=NUMERIC(18,6) |
| `test_re_loan_cashflows_fk` | loan_id FK -> re_loans.id |
| `test_re_loan_insert_and_query` | Insert with Decimal values, query back (DATA-03) |
| `test_re_loan_cashflow_insert` | Insert cashflow with FK, verify id and loan_id |
| `test_re_loan_cashflow_relationship` | ORM loan.cashflows returns 12 records (DATA-04) |

## Verification Results

1. `python scripts/seed_re_loans.py` exits 0, prints counts
2. `SELECT COUNT(*) FROM re_loans WHERE as_of_date = '2025-09-30'` = 500
3. `SELECT COUNT(*) FROM re_loans WHERE as_of_date = '2025-12-31'` = 500
4. `SELECT COUNT(*) FROM re_loan_cashflows` = 6000
5. `SELECT COUNT(DISTINCT property_type) FROM re_loans` = 6
6. `SELECT COUNT(DISTINCT state) FROM re_loans` = 21
7. `SELECT COUNT(DISTINCT msa) FROM re_loans` = 24
8. `python -m pytest tests/test_re_loans.py -x -q` — 8 passed
9. Re-run produces identical counts (idempotency confirmed)

## Deviations from Plan

**1. [Rule 2 - Enhancement] Added 8th test: test_re_loan_cashflow_relationship**

- **Found during:** Task 2 implementation
- **Reason:** Plan specified minimum 7 tests; an ORM relationship test covering `loan.cashflows` directly verifies the back-populate pattern and the "12 cashflows per loan" DATA-04 requirement at the ORM level (not just FK level)
- **Files modified:** backend/tests/test_re_loans.py

Otherwise — plan executed exactly as written.

## Known Stubs

None — seed script produces full data; no UI rendering stubs introduced.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. Seed script only touches `re_loan_cashflows` and `re_loans` tables — existing tables (users, pipeline_runs, etc.) are never modified per T-17-04 mitigation.

## Self-Check: PASSED

- [x] `backend/scripts/seed_re_loans.py` exists and contains `def seed_re_loans`
- [x] `backend/tests/test_re_loans.py` exists with 8 test functions
- [x] Commit 2d83489 verified in git log
- [x] Commit a628aa6 verified in git log
- [x] All 8 tests pass: `python -m pytest tests/test_re_loans.py -x -q`
- [x] Seed verified: 500 T0, 500 T1, 6000 cashflows, 6 prop types, 21 states, 24 MSAs
- [x] Idempotency verified: 2nd run produces same counts
