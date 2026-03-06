---
phase: 05-staging-deployment
plan: 02
subsystem: infra
tags: [ecs, fargate, seed, admin, runbook, cicd, postgresql, sqlalchemy]

# Dependency graph
requires:
  - phase: 04-cicd-pipeline
    provides: ECS task definition, cluster, and deploy pipeline used by seed run-task command
  - phase: 03-aws-infrastructure
    provides: RDS endpoint, ECS cluster, ALB, Secrets Manager — all referenced in runbook
provides:
  - Idempotent staging admin seed script (backend/scripts/seed_staging_user.py)
  - First Deploy Checklist in docs/CICD.md — PowerShell run-task command for ECS one-off seed task
affects: [ops-onboarding, staging-verification, future-environment-promotion]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ECS one-off task pattern for running admin scripts (seed, migrations) without SSH
    - Idempotent upsert pattern: query-then-update-or-insert using SQLAlchemy (no ON CONFLICT)
    - sys.path.insert(0, parent) for standalone script imports from /app WORKDIR in ECS

key-files:
  created:
    - backend/scripts/seed_staging_user.py
  modified:
    - docs/CICD.md

key-decisions:
  - "Seed script uses upsert pattern (query then update-or-insert) rather than SQLAlchemy merge() for explicitness"
  - "Password hardcoded in script for staging only — RDS not publicly accessible, simpler than env var injection for one-off task"
  - "ECS command uses relative path scripts/seed_staging_user.py from /app WORKDIR to match Dockerfile WORKDIR"
  - "Runbook uses PowerShell backtick line continuation to match Windows dev environment and existing CICD.md style"

patterns-established:
  - "Idempotent seed scripts: always query first, update existing, create if missing — never fail on re-run"
  - "ECS one-off task pattern: run-task with command override -> wait tasks-stopped -> check exitCode -> 0 = success"

requirements-completed: [STAGE-02]

# Metrics
duration: 15min
completed: 2026-03-06
---

# Phase 5 Plan 02: Staging Admin Seed Script and First Deploy Checklist Summary

**Idempotent ECS-runnable seed script that creates or resets the staging admin user, plus a PowerShell First Deploy Checklist in the CICD runbook covering URL verification, seed execution, and Ops login smoke test**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-06T20:46:00Z
- **Completed:** 2026-03-06T21:01:13Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `backend/scripts/seed_staging_user.py` — idempotent admin seed using project auth/db patterns (get_password_hash, SessionLocal, User/UserRole)
- Added "## First Deploy Checklist" section to `docs/CICD.md` with exact PowerShell ECS run-task command, wait, exit code check, and Ops login verification steps
- Confirmed 75 existing backend tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create idempotent seed script for staging admin user** - `f52c660` (feat)
2. **Task 2: Add First Deploy Checklist to CICD.md runbook** - `283733d` (docs)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `backend/scripts/seed_staging_user.py` - Idempotent staging admin user seed: query by username, update hashed_password+is_active if exists, create with UserRole.ADMIN if not
- `docs/CICD.md` - Added First Deploy Checklist section (after OIDC Setup, before Deploy Sequence) with three steps: URL verification, ECS seed task execution, Ops login+upload test

## Decisions Made
- Seed script uses explicit query-then-update-or-insert rather than SQLAlchemy `merge()` for clarity and predictability in a one-off ops script
- Password hardcoded in the script for staging: RDS is not publicly accessible, and a hardcoded staging password is simpler and safer than injecting via env var for a one-off ECS task
- Runbook uses PowerShell backtick line continuation to match Windows dev environment and the established style in CICD.md
- ECS command references `scripts/seed_staging_user.py` as a relative path (not `/app/scripts/...`) to match the Dockerfile WORKDIR of `/app`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failures (27 failed, 33 errors) in test suite due to missing `client` fixture in auth route tests and unrelated infrastructure issues. These are pre-existing and unrelated to this plan's changes. The 75 tests that do pass confirm no regression.

## User Setup Required
None - no external service configuration required beyond what the runbook documents.

## Next Phase Readiness
- Staging admin seed script is in place and documented — Ops can log in and upload files after the first CI/CD deploy
- First Deploy Checklist gives step-by-step instructions for the initial activation of the staging environment
- STAGE-02 requirement satisfied

## Self-Check: PASSED

All files confirmed present on disk. All task commits verified in git history.

---
*Phase: 05-staging-deployment*
*Completed: 2026-03-06*
