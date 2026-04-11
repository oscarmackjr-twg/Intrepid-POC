---
phase: 16-linting
plan: 01
subsystem: testing
tags: [eslint, ruff, typescript, react, ci, github-actions]

# Dependency graph
requires:
  - phase: 12-unit-testing-build-out
    provides: CI pipeline with unit-tests job that this plan's ESLint step joins in security-quality-gate
provides:
  - ESLint v9 flat config for frontend TypeScript/React codebase (npm run lint passes)
  - Zero ruff violations in backend (unused import removed)
  - ESLint as blocking CI gate in security-quality-gate job
affects: [16-02, future frontend changes requiring lint pass]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ESLint v9 flat config using tseslint.config() helper with react-hooks and react-refresh plugins"
    - "Disable existing violations at ESLint setup time via rule overrides (enable incrementally as codebase cleans up)"

key-files:
  created:
    - frontend/eslint.config.js
  modified:
    - backend/tests/test_tagging_allocation.py
    - .github/workflows/deploy-test.yml

key-decisions:
  - "Disable @typescript-eslint/no-explicit-any and react-hooks/set-state-in-effect at setup time — pre-existing violations suppressed to achieve zero errors on first lint pass (D-03: no new violations at setup point)"
  - "ESLint step placed after npm audit and before Setup Terraform in security-quality-gate job — deploy cannot proceed if frontend lint fails"
  - "No changes to backend/pyproject.toml ruff config — existing config is correct (D-14)"

patterns-established:
  - "ESLint v9 flat config: eslint.config.js with tseslint.config() — required for package.json type=module projects"
  - "CI lint gate: separate npm ci + npm run lint step after npm audit for self-containment"

requirements-completed: [LINT-01, LINT-02, LINT-03]

# Metrics
duration: 15min
completed: 2026-03-25
---

# Phase 16 Plan 01: ESLint v9 flat config and ruff cleanup with CI gate

**ESLint v9 flat config (tseslint.config) enabling clean npm run lint, single ruff unused-import fix, and ESLint as blocking CI step in security-quality-gate**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-25T14:56:45Z
- **Completed:** 2026-03-25T15:11:30Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `frontend/eslint.config.js` with ESLint v9 flat config — `npm run lint` now exits 0
- Removed unused `import pytest` from `backend/tests/test_tagging_allocation.py` — ruff reports 0 violations
- Added ESLint blocking step to `security-quality-gate` in deploy-test.yml — frontend lint now gates CI deploy

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ESLint v9 flat config and fix ruff violation** - `a712dff` (feat)
2. **Task 2: Add ESLint CI gate to deploy-test.yml** - `10de876` (feat)

## Files Created/Modified

- `frontend/eslint.config.js` - ESLint v9 flat config using tseslint.config() with react-hooks and react-refresh plugins
- `backend/tests/test_tagging_allocation.py` - Removed unused `import pytest` (F401 violation)
- `.github/workflows/deploy-test.yml` - Added `ESLint (frontend)` step to security-quality-gate job

## Decisions Made

- Disabled `@typescript-eslint/no-explicit-any` and `react-hooks/set-state-in-effect` in the ESLint config to suppress pre-existing violations at setup time. Plan decision D-03 requires zero violations at the point of setup; the existing codebase has 37 `any` type usages and one setState-in-effect pattern. These are disabled with a comment explaining they should be enabled incrementally.
- No changes to `backend/pyproject.toml` per D-14 — existing ruff config with E712/E402 ignores and script exclusions is correct.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Disabled pre-existing ESLint violations to achieve zero-error lint pass**

- **Found during:** Task 1 (Create ESLint v9 flat config)
- **Issue:** `tseslint.configs.recommended` enables `@typescript-eslint/no-explicit-any` which caught 37 pre-existing `any` usages in the frontend codebase. Additionally `react-hooks/set-state-in-effect` flagged 1 error in CashFlow.tsx. These caused `npm run lint` to exit 1 (38 errors), violating plan success criteria (D-04: must pass cleanly).
- **Fix:** Added `'@typescript-eslint/no-explicit-any': 'off'` and `'react-hooks/set-state-in-effect': 'off'` to the rules block with a comment indicating these should be re-enabled as the codebase is cleaned up. This matches D-03 intent exactly: "No TypeScript strict rules — keep zero new violations at the point of setup."
- **Files modified:** `frontend/eslint.config.js`
- **Verification:** `npm run lint` exits 0 (0 errors, 13 warnings)
- **Committed in:** `a712dff` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in initial config not achieving plan goal)
**Impact on plan:** Auto-fix necessary for correctness — plan goal was zero-error lint pass. Rule overrides are the correct idiomatic approach per D-03. No scope creep.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 16-01 complete: `frontend/eslint.config.js` exists, `npm run lint` passes, ruff clean, CI gate in place
- Plan 16-02 can now proceed: husky + lint-staged pre-commit hooks (depends on 16-01 eslint.config.js existing)
- Note: 13 ESLint warnings remain (react-hooks/exhaustive-deps) — these are warnings, not errors, and do not block CI. Future cleanup optional.

---
*Phase: 16-linting*
*Completed: 2026-03-25*

## Self-Check: PASSED

- FOUND: frontend/eslint.config.js
- FOUND: backend/tests/test_tagging_allocation.py (import pytest removed)
- FOUND: .github/workflows/deploy-test.yml (ESLint step inserted)
- FOUND: .planning/phases/16-linting/16-01-SUMMARY.md
- FOUND commit a712dff: feat(16-01): create ESLint v9 flat config and fix ruff unused import
- FOUND commit 10de876: feat(16-01): add ESLint as blocking CI gate in security-quality-gate job
- FOUND commit ee97239: docs(16-01): complete ESLint config and ruff cleanup plan
