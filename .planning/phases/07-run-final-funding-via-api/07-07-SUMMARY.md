---
phase: 07-run-final-funding-via-api
plan: "07"
subsystem: auth
tags: [audit-log, security, hardening, documentation, tdd]
dependency_graph:
  requires: [07-04-PLAN.md, 07-05-PLAN.md]
  provides: [HARD-06-complete, HARD-02-complete]
  affects: [backend/auth/routes.py, backend/tests/test_auth_routes.py, README.md]
tech_stack:
  added: []
  patterns: [TDD red-green, SQLAlchemy session pass-through]
key_files:
  created: []
  modified:
    - backend/auth/routes.py
    - backend/tests/test_auth_routes.py
    - README.md
decisions:
  - "Pass db=db and explicit outcome= to log_user_action at both login call sites; no other routes changed (create_user / update_user out of scope per VERIFICATION.md)"
  - "AuditLog import placed inside each test method rather than at module top — avoids conftest import ordering issues"
metrics:
  duration_minutes: 3
  tasks_completed: 2
  files_modified: 3
  completed_date: "2026-03-10"
requirements_closed: [HARD-06, HARD-02]
---

# Phase 7 Plan 07: Wire DB to Login Audit Calls + README Cleanup Summary

One-liner: Passed `db=db, outcome=` to both `log_user_action` login call sites and rewrote README credentials section to reference `seed_admin.py` instead of the removed `admin123` default password.

## Objective

Close the final Phase 7 gap: login audit events were being logged to console only (no `db=` session passed), so no rows appeared in the `audit_log` table. Also remove the stale `admin123` credential from README documentation.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Wire db session to login audit calls + assert DB rows in tests | e3585ca | backend/auth/routes.py, backend/tests/test_auth_routes.py |
| 2 | Remove admin123 from README credential section | 3b6e87c | README.md |

## What Was Built

**Task 1 — TDD: DB-persistent login audit (HARD-06)**

RED: Added `TestLoginAuditLog` class with 3 tests to `backend/tests/test_auth_routes.py`. Tests A (successful login writes row) and B (failed login writes row) failed as expected; test C (unknown user writes no row) passed because the existing `if user:` guard was already correct.

GREEN: Changed two lines in `backend/auth/routes.py`:
- Line 85: `log_user_action('login_failed', user, details=...)` → `log_user_action('login_failed', user, db=db, outcome='failure', details=...)`
- Line 112: `log_user_action('login', user)` → `log_user_action('login', user, db=db, outcome='success')`

All 3 new tests pass. All 26 auth route tests pass (23 existing + 3 new).

**Task 2 — README cleanup (HARD-02)**

Replaced the "Default Login Credentials" section (lines 78-84) that showed `admin123` with instructions to run `scripts/seed_admin.py`. Updated demo step line 93 to reference `seed_admin.py` output. `grep -c "admin123" README.md` returns `0`.

## Success Criteria Verification

- [x] Three new TestLoginAuditLog tests GREEN: successful login row present, failed login row present, unknown username row absent
- [x] All 26 auth route tests pass (0 failures in test_auth_routes.py)
- [x] `backend/auth/routes.py` line 85 passes `db=db, outcome='failure'` to log_user_action
- [x] `backend/auth/routes.py` line 112 passes `db=db, outcome='success'` to log_user_action
- [x] README.md contains zero occurrences of `admin123`
- [x] HARD-06 gap closed: login events durably persisted to audit_log table
- [x] HARD-02 documentation gap closed: README references seed_admin.py

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files verified:
- FOUND: C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/auth/routes.py (log_user_action with db=db at lines 85 and 112)
- FOUND: C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/tests/test_auth_routes.py (TestLoginAuditLog class appended)
- FOUND: C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/README.md (admin123 removed — grep count 0)

Commits verified:
- e3585ca: feat(07-07): wire db session to login audit calls + assert DB rows in tests
- 3b6e87c: docs(07-07): remove hardcoded admin123 from README credential section
