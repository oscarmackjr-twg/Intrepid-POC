---
phase: 16-linting
plan: 02
subsystem: tooling
tags: [husky, lint-staged, pre-commit, eslint, ruff, git-hooks]

# Dependency graph
requires:
  - phase: 16-linting
    plan: 01
    provides: ESLint v9 flat config and ruff clean baseline — required for lint-staged to run without errors
provides:
  - Git pre-commit hook (.husky/pre-commit) invoking lint-staged on staged files
  - lint-staged config in frontend/package.json: eslint --fix for .ts/.tsx, ruff check --fix for .py
  - husky prepare script wired for npm install automation
affects: [all future commits — lint violations caught before commit reaches CI]

# Tech tracking
tech-stack:
  added:
    - husky ^9.1.7 (git hooks manager)
    - lint-staged ^16.4.0 (run linters on staged files only)
  patterns:
    - "Monorepo husky setup: package.json in frontend/ subdirectory, .git at repo root — prepare script uses cd .. && node frontend/node_modules/husky/bin.js"
    - "lint-staged glob ../backend/**/*.py navigates up from frontend/ to match backend Python files"

key-files:
  created:
    - .husky/pre-commit
  modified:
    - frontend/package.json

key-decisions:
  - "prepare script uses cd .. && node frontend/node_modules/husky/bin.js instead of plain 'husky' — required because package.json lives in frontend/ subdirectory but .git is at repo root; husky checks for .git in cwd"
  - "Pre-commit hook: cd frontend && npx lint-staged — changes to frontend/ before running lint-staged so it reads config from frontend/package.json"

requirements-completed: [LINT-04]

# Metrics
duration: 3min
completed: 2026-03-25
---

# Phase 16 Plan 02: Husky + lint-staged pre-commit hooks

**Husky v9 + lint-staged pre-commit hook running eslint --fix on staged .ts/.tsx files and ruff check --fix on staged .py files — completing the linting enforcement chain: editor -> pre-commit -> CI**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-25T15:02:15Z
- **Completed:** 2026-03-25T15:05:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Installed `husky ^9.1.7` and `lint-staged ^16.4.0` as frontend devDependencies
- Added `prepare` script to `frontend/package.json` — runs husky from repo root
- Added `lint-staged` config in `frontend/package.json`: `eslint --fix` for `*.{ts,tsx}`, `ruff check --fix` for `../backend/**/*.py`
- Created `.husky/pre-commit` at repo root: `cd frontend && npx lint-staged`
- Configured git `core.hooksPath` to `.husky/_` via husky init
- `npm run prepare` exits 0

## Task Commits

1. **Task 1: Install husky + lint-staged and configure pre-commit hook** - `98ad425` (feat)

## Files Created/Modified

- `.husky/pre-commit` - Git pre-commit hook running `cd frontend && npx lint-staged`
- `frontend/package.json` - Added husky/lint-staged devDeps, prepare script, lint-staged config, package-lock.json updated

## Decisions Made

- The `prepare` script uses `cd .. && node frontend/node_modules/husky/bin.js` rather than simply `husky`. This is required because `frontend/package.json` lives in a subdirectory while `.git` is at the repo root. Husky v9's default `husky` binary checks for `.git` in the current working directory (frontend/), which fails. Running `node frontend/node_modules/husky/bin.js` from the repo root (`cd ..`) gives husky the `.git`-accessible context it needs.
- The pre-commit hook uses `cd frontend && npx lint-staged` so lint-staged reads its config from `frontend/package.json`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed spurious frontend/.husky/ directory**

- **Found during:** Task 1 (after running npx husky init from frontend/ as first attempt)
- **Issue:** An initial attempt to run `npx husky init` from `frontend/` directory (before discovering the .git detection issue) created `frontend/.husky/pre-commit` with `npm test` content — the wrong location and wrong command.
- **Fix:** Removed `frontend/.husky/` entirely. Correct `.husky/pre-commit` was created at repo root manually with the plan-specified content `cd frontend && npx lint-staged`.
- **Files modified:** frontend/.husky/ (removed)
- **Impact:** Prevents git from using wrong hook location; ensures all commits go through the correct linting path.

**2. [Rule 1 - Bug] prepare script adjusted for monorepo subdirectory layout**

- **Found during:** Task 1 (npm run prepare from frontend/ exits non-zero with ".git can't be found")
- **Issue:** Husky v9 requires `.git` to be present in the current working directory when running. The `prepare` script runs from `frontend/` (where package.json is), but `.git` is at the repo root.
- **Fix:** Changed prepare script from `"husky"` to `"cd .. && node frontend/node_modules/husky/bin.js"` to execute husky from the repo root context.
- **Files modified:** `frontend/package.json`
- **Verification:** `npm run prepare` exits 0.

---

**Total deviations:** 2 auto-fixed (Rule 1 bugs caused by monorepo subdirectory layout)
**Impact on plan:** Both fixes are necessary for correct operation. The lint-staged config and pre-commit hook content match the plan exactly; only the `prepare` script mechanism differs from the literal plan text (which specified `"prepare": "husky"`) to accommodate the actual directory layout.

## Known Stubs

None — all functionality is fully wired. Pre-commit hook invokes lint-staged which invokes eslint/ruff on staged files.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None. The `npm install` in `frontend/` will automatically run the `prepare` script and configure git hooks going forward.

## Next Phase Readiness

- Phase 16 is complete: ESLint config (plan 01) + pre-commit hooks (plan 02) + CI gate (plan 01 task 2) = full linting enforcement chain
- Future commits: staged .ts/.tsx files will be auto-fixed by eslint, staged .py files by ruff, before reaching CI

---
*Phase: 16-linting*
*Completed: 2026-03-25*
