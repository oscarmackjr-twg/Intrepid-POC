---
phase: 02-docker-local-dev
plan: 01
subsystem: infra
tags: [docker, docker-compose, postgres, vite, uvicorn, alembic, hot-reload]

# Dependency graph
requires:
  - phase: 01-local-dev
    provides: backend FastAPI app, Alembic migrations, React/Vite frontend, sample data at backend/data/sample/
provides:
  - Cross-platform deploy/docker-compose.yml with db, app, and frontend services
  - Automatic Alembic migration on app container start
  - Backend hot reload via ../backend volume mount (pip packages isolated)
  - Vite dev server at port 5173 with HMR and anonymous node_modules volume
affects:
  - 02-02 (vite.config.ts proxy update uses VITE_API_TARGET env var set here)
  - 03-infra (Dockerfile and compose structure established here)
  - 04-cicd (migration pattern carries forward)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inline sh -c entrypoint pattern: alembic upgrade head && exec uvicorn (exec preserves PID 1)"
    - "Anonymous volume for node_modules prevents host Windows binaries shadowing Linux container binaries"
    - "All volume paths relative to compose file location (deploy/) — cross-platform by design"

key-files:
  created: []
  modified:
    - deploy/docker-compose.yml

key-decisions:
  - "Volume paths relative to deploy/ (../backend, ../frontend) not absolute — eliminates Windows path blocker DOCKER-02"
  - "DEV_OUTPUT and DEV_OUTPUT_SHARED moved to /tmp paths to avoid writing into read-only sample data mount"
  - "frontend service uses node:20-slim image directly (not production Dockerfile) for Vite HMR dev server"
  - "exec uvicorn pattern ensures uvicorn is PID 1 so Docker signals (SIGTERM) are delivered correctly"

patterns-established:
  - "Migration pattern: alembic upgrade head runs inline before uvicorn on every container start"
  - "Hot-reload isolation: mount only backend/ not repo root to avoid shadowing /usr/local/lib pip packages"

requirements-completed: [DOCKER-01, DOCKER-02, DOCKER-04]

# Metrics
duration: 2min
completed: 2026-03-06
---

# Phase 2 Plan 01: Docker Compose Overhaul Summary

**Cross-platform docker-compose.yml with three services (db, app, frontend), automatic Alembic migrations via inline sh -c entrypoint, backend hot reload via relative volume mount, and Vite dev server with anonymous node_modules isolation**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-06T02:28:59Z
- **Completed:** 2026-03-06T02:30:52Z
- **Tasks:** 3 (written as single atomic file update per plan instruction)
- **Files modified:** 1

## Accomplishments

- Eliminated hardcoded Windows absolute path — docker-compose.yml is now cross-platform (DOCKER-02)
- Added inline alembic migration entrypoint — migrations run automatically on `docker compose up` (DOCKER-04)
- Corrected DB name from `loan_engine` to `intrepid_poc` across both db and app services (DOCKER-01)
- Added frontend service with Vite HMR, anonymous node_modules volume, and VITE_API_TARGET env var for Plan 02 proxy config

## Task Commits

Tasks 1-3 were written together in a single atomic commit per plan instruction (all three tasks modify the same file):

1. **Tasks 1-3: Fix db name, app service, add frontend** - `7091656` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `deploy/docker-compose.yml` - Complete overhaul: cross-platform volumes, migration entrypoint, corrected DB name, new frontend service

## Decisions Made

- Tasks 1, 2, and 3 committed together (plan explicitly requires writing the file once to avoid intermediate broken states)
- DEV_OUTPUT changed to /tmp/dev_output instead of writing into the read-only sample mount
- exec prefix on uvicorn ensures PID 1 signal handling inside the container
- node:20-slim used directly (not the production Dockerfile) so the frontend container runs a live Vite dev server, not a static build

## Deviations from Plan

### Out-of-Scope Issues Logged

Pre-existing test failure in `tests/test_api_routes.py` (SQLite UNIQUE constraint on username — test isolation/ordering issue) was confirmed pre-existing before our change via git stash verification. Not caused by this plan. Logged to deferred items.

No auto-fixes were applied. No architectural changes required.

None — plan executed exactly as written for all three tasks.

## Issues Encountered

- Backend unit test `test_list_runs` fails with SQLite UNIQUE constraint on `users.username` — confirmed pre-existing (reproduces on the unmodified commit). This is a test teardown isolation issue unrelated to docker-compose changes. Deferred.

## User Setup Required

None — no external service configuration required for this plan. Docker Compose file changes take effect on next `docker compose -f deploy/docker-compose.yml up`.

## Next Phase Readiness

- `docker compose -f deploy/docker-compose.yml up` will start db, app, and frontend services
- Alembic migrations run automatically on app startup
- Plan 02 can now update vite.config.ts to consume `VITE_API_TARGET` env var for the proxy target

---
*Phase: 02-docker-local-dev*
*Completed: 2026-03-06*
