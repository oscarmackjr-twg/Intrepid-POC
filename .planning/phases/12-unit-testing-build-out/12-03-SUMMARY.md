---
phase: 12-unit-testing-build-out
plan: 03
subsystem: testing
tags: [pytest, pytest-cov, ci, github-actions, coverage]

requires:
  - phase: 12-unit-testing-build-out
    provides: test files for cashflow amortization, prepayment, waterfall, CoMAP rules, and archive orchestration (plans 01-02)

provides:
  - unit-tests CI job in deploy-test.yml that runs pytest with coverage and blocks deploy
  - pytest-cov>=4.0 in backend/requirements.txt
  - Updated tests/README.md with complete 28-file test inventory

affects: [04-cicd-pipeline, deploy-test.yml, backend/requirements.txt, testing]

tech-stack:
  added: [pytest-cov>=4.0]
  patterns: [CI unit-tests job runs in parallel with security-quality-gate; both must pass before deploy job starts]

key-files:
  created: []
  modified:
    - .github/workflows/deploy-test.yml
    - backend/requirements.txt
    - backend/tests/README.md

key-decisions:
  - "unit-tests job runs in parallel with security-quality-gate (not after it) — parallelism keeps CI fast"
  - "working-directory: backend on pytest step — required because pytest.ini testpaths=tests is relative to backend/"
  - "No --cov-fail-under threshold — coverage is reporting-only in CI; no gate percentage set (D-17)"
  - "pytest-cov excluded from pytest.ini addopts — coverage only in CI, not local default runs (D-18)"

patterns-established:
  - "CI coverage via --cov=. --cov-report=term-missing in working-directory: backend"
  - "deploy job needs both security-quality-gate and unit-tests — either failure blocks deploy"

requirements-completed: [TEST-05, TEST-06, TEST-07]

duration: 2min
completed: 2026-03-22
---

# Phase 12 Plan 03: CI Unit-Test Gate + Coverage Summary

**pytest wired into CI as a blocking deploy gate via parallel unit-tests job with pytest-cov coverage reporting**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T02:21:52Z
- **Completed:** 2026-03-22T02:23:16Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `unit-tests` CI job to deploy-test.yml running in parallel with `security-quality-gate`, blocking deploy on failure
- Added `pytest-cov>=4.0` to backend/requirements.txt; CI runs with `--cov=. --cov-report=term-missing`
- Updated tests/README.md from 10-file stub to complete 28-file inventory covering all Phase 7 and Phase 12 additions

## Task Commits

1. **Task 1: Add unit-tests CI job + pytest-cov to requirements** - `e51f1a9` (feat)
2. **Task 2: Update tests/README.md with full test inventory** - `96b5bc2` (docs)

**Plan metadata:** (to be committed with SUMMARY.md)

## Files Created/Modified

- `.github/workflows/deploy-test.yml` - Added unit-tests job (parallel with security-quality-gate); deploy needs both
- `backend/requirements.txt` - Added pytest-cov>=4.0 after pytest-asyncio line
- `backend/tests/README.md` - Full 28-file test tree, CI command, updated categories; removed 80%+ coverage threshold

## Decisions Made

- unit-tests runs parallel to security-quality-gate (not after) — keeps CI fast, both gate deploy independently
- No `--cov-fail-under` — coverage is baseline reporting only, no threshold enforcement per D-17
- `--cov=.` (not `--cov=backend`) because `working-directory: backend` already sets the context
- pytest.ini addopts left unchanged — `--cov` flags are CI-only per D-18

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 12 complete: all three plans done (12-01 test fixes, 12-02 new test files, 12-03 CI gate)
- CI deploy is now gated by both security quality checks and unit test results
- Coverage baseline will be established on first CI run after this change

---
*Phase: 12-unit-testing-build-out*
*Completed: 2026-03-22*
