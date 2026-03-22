---
phase: 12-unit-testing-build-out
plan: 02
subsystem: testing
tags: [pytest, cashflow, amortization, waterfall, prepayment, comap, archive, unit-tests]

# Dependency graph
requires:
  - phase: 12-unit-testing-build-out
    provides: pytest infrastructure and conftest fixtures from plan 01
provides:
  - 72 pure unit tests across 5 new test files covering cashflow compute, CoMAP grid rules, and archive path logic
  - Coverage for the 5 largest untested gaps: amortization, waterfall, prepayment, comap, archive_run
affects:
  - future regression runs (new tests can be run in CI)
  - 12-03 (final plan in phase — may build on this coverage)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inline grid DataFrames in CoMAP tests (not conftest) — column names imported from module constants to prevent silent false-negatives"
    - "pytest.approx() for all floating-point comparisons in cashflow tests"
    - "Class-per-function organization (TestLevelPaySchedule, TestApplyWaterfall, etc.)"
    - "temp_dir fixture used for file-system tests in archive tests"

key-files:
  created:
    - backend/tests/test_cashflow_amortization.py
    - backend/tests/test_cashflow_waterfall.py
    - backend/tests/test_cashflow_prepayment.py
    - backend/tests/test_rules_comap.py
    - backend/tests/test_orchestration_archive.py
  modified: []

key-decisions:
  - "Inline grid DataFrames for CoMAP tests — never use conftest sample_comap_df (too sparse, wrong column names for edge case coverage)"
  - "Column names for CoMAP grids must be imported from module constants (SFY_COMAP_COLS_MIN_FICO etc.) — mismatched names silently produce False results"
  - "Archive _collect_input_paths tests use temp_dir fixture from conftest; no mocking of file system needed"

patterns-established:
  - "CoMAP test pattern: import fico_col_mins dict, use its keys as DataFrame columns, build grid inline per test"
  - "Cashflow test pattern: inline scalar inputs, pytest.approx() for floats, classes named after function under test"

requirements-completed: [TEST-02, TEST-03, TEST-04]

# Metrics
duration: 4min
completed: 2026-03-22
---

# Phase 12 Plan 02: Unit Testing Build-Out (Cashflow + CoMAP + Archive) Summary

**72 pure unit tests across 5 files covering cashflow amortization/waterfall/prepayment engines, CoMAP grid skip-vs-flag logic, and archive path classification**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-22T02:11:01Z
- **Completed:** 2026-03-22T02:15:00Z
- **Tasks:** 2
- **Files created:** 5

## Accomplishments

- 45 cashflow compute tests: level-pay amortization (final balance zero, constant payment, zero-rate edge case, single period, invalid inputs), bullet schedule, custom schedule, waterfall priority ordering and excess allocation, CPR/PSA prepayment boundary values and model application
- 13 CoMAP tests: `_prog_in_grid` absent-from-all-columns skip logic, column key mismatch behavior, SFY vs PRIME vs NOTES grid routing, `_found_in_grid` FICO band minimum enforcement and oct25 grid verification
- 14 archive tests: `_is_s3_style_prefix` rejects Windows/Unix absolute paths and accepts S3-style keys; `_collect_input_paths` discovers reference files in files_required/, returns Path objects, handles missing files gracefully

## Task Commits

Each task was committed atomically:

1. **Task 1: Cashflow compute tests (amortization, waterfall, prepayment)** - `ed3603e` (test)
2. **Task 2: CoMAP rules + archive run tests** - `2212126` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/tests/test_cashflow_amortization.py` - 17 tests for level_pay_schedule, bullet_schedule, custom_schedule
- `backend/tests/test_cashflow_waterfall.py` - 8 tests for apply_waterfall and run_waterfall
- `backend/tests/test_cashflow_prepayment.py` - 20 tests for cpr_to_smm, psa_speed, apply_psa_prepayment, apply_cpr_prepayment
- `backend/tests/test_rules_comap.py` - 13 tests for _prog_in_grid and _found_in_grid with inline grids
- `backend/tests/test_orchestration_archive.py` - 14 tests for _is_s3_style_prefix and _collect_input_paths

## Decisions Made

- Inline DataFrames for CoMAP grids (not conftest `sample_comap_df`): conftest grid uses PRIME_COMAP_COLS_MIN_FICO2 column names but is too sparse for skip-logic edge cases; inline grids built from imported constant dict keys guarantee column name correctness
- Archive tests use `temp_dir` from conftest rather than mocking: simpler and tests the real file-walking logic

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — all 5 test files test real module behavior with no placeholder logic.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 5 untested modules now have unit test coverage
- 72 tests can be added to CI test runs with `-m unit` marker
- Plan 12-03 (if it exists) can build on this foundation

---
*Phase: 12-unit-testing-build-out*
*Completed: 2026-03-22*
