---
phase: 11-refing-ui-for-regression-testing
plan: "04"
subsystem: testing
tags: [python, subprocess, filecmp, regression, pipeline, cli]

requires:
  - phase: 01-local-dev
    provides: run_pipeline_cli.py CLI entry point with --folder/--pdate/--tday flags

provides:
  - "backend/scripts/regression_test.py — runnable local regression harness"
  - "Discover, run, and diff all buy-date test cases in TestData"
  - "Per-case PASS/FAIL with DIFF/MISSING/EXTRA file reporting"

affects:
  - future-regression-runs
  - qa-validation

tech-stack:
  added: []
  patterns:
    - "subprocess.run per test case with captured stdout/stderr and timeout=300"
    - "filecmp.cmp(shallow=False) for byte-level output comparison"
    - "Most-recently-modified cli_debug/ subdir detection for output discovery"
    - "shutil.rmtree cleanup after each case (--no-cleanup override)"

key-files:
  created:
    - backend/scripts/regression_test.py
  modified: []

key-decisions:
  - "Output dir discovery uses mtime >= started_epoch to identify the run just launched — handles concurrent runs gracefully"
  - "output_share generated dir tries {run_id}_share sibling first, then output_share/ subdirectory, to cover both pipeline layout variants"
  - "Date derivation: CLI --pdate/--tday override all; otherwise folder name used as pdate (works for YYYY-MM-DD folders); tday defaults to today"
  - "stdlib only (subprocess, pathlib, filecmp, shutil, datetime, argparse) — no third-party dependencies"

patterns-established:
  - "Regression harness pattern: discover → run CLI → find output dir → diff → cleanup → report"

requirements-completed: [REG-02]

duration: 5min
completed: 2026-03-13
---

# Phase 11 Plan 04: Regression Test Harness Summary

**stdlib-only Python regression harness that discovers buy-date folders, runs the pipeline CLI per case, and diffs generated outputs byte-for-byte against expected files**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-13T23:17:09Z
- **Completed:** 2026-03-13T23:22:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Wrote `backend/scripts/regression_test.py` — 448-line stdlib-only harness covering full discovery → run → diff → report loop
- Script accepts `--test-data`, `--backend-dir`, `--pdate`, `--tday`, `--no-cleanup` flags; defaults work out of the box from repo root
- Byte-for-byte diff via `filecmp.cmp(shallow=False)` with separate DIFF/MISSING/EXTRA categorization for each test case
- Auto-cleanup of `cli_debug/{run_id}/` after each case; `--no-cleanup` retains them for inspection
- Exit code 0 on all-pass, 1 on any failure — CI/shell-friendly

## Task Commits

1. **Task 1: Write backend/scripts/regression_test.py** - `51d42ef` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/scripts/regression_test.py` - Data regression harness: discover test cases, run pipeline CLI, diff outputs, print report

## Decisions Made

- Output directory discovery uses `mtime >= started_epoch` so the harness correctly identifies each run's output dir even if prior cli_debug/ subdirs exist.
- `output_share` generated path tries `{run_id}_share` sibling first, then `output_share/` subdirectory — future-proofs against either pipeline layout variant.
- Date derivation falls back gracefully: CLI args override, then folder name as pdate (YYYY-MM-DD folders work automatically), tday defaults to today.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

Precondition: `C:\Users\omack\Downloads\TestData\` must exist with at least one buy-date subfolder containing inputs and an `outputs/` or `output_share/` directory for the harness to run any cases.

## Next Phase Readiness

- `backend/scripts/regression_test.py` is ready to run: `python backend/scripts/regression_test.py`
- Once TestData is populated with a buy-date folder, the script will discover it, run the pipeline, and report diffs
- Remaining Phase 11 plans (UI polish, manual regression checklist) are unblocked

---
*Phase: 11-refing-ui-for-regression-testing*
*Completed: 2026-03-13*
