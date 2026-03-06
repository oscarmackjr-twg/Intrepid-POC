---
phase: 05-staging-deployment
plan: 01
subsystem: ui
tags: [react, vite, docker, github-actions, staging-banner]

# Dependency graph
requires:
  - phase: 04-cicd-pipeline
    provides: deploy-test.yml GitHub Actions workflow for docker build + ECS deploy
provides:
  - StagingBanner React component — amber-400 sticky banner visible on all pages when VITE_APP_ENV != production
  - Layout.tsx updated — StagingBanner rendered before nav on all authenticated pages
  - Login.tsx updated — StagingBanner rendered at top of login page
  - Dockerfile frontend stage wires VITE_APP_ENV build arg into npm run build
  - deploy-test.yml passes --build-arg VITE_APP_ENV=staging to docker build
affects: [05-staging-deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Build-time env injection via Docker ARG/ENV + Vite import.meta.env — zero runtime overhead for feature flags"
    - "Safe-default banner: renders when VITE_APP_ENV is absent (local dev) or any non-production value"

key-files:
  created:
    - frontend/src/components/StagingBanner.tsx
  modified:
    - frontend/src/components/Layout.tsx
    - frontend/src/pages/Login.tsx
    - deploy/Dockerfile
    - .github/workflows/deploy-test.yml

key-decisions:
  - "StagingBanner renders when VITE_APP_ENV !== 'production' — undefined (no build arg) also shows banner, safe default for local dev"
  - "Banner placed as first child in Layout and Login outer div — sticky top-0 z-50 ensures it anchors to viewport top above all content"
  - "VITE_APP_ENV baked into Docker image at build time via ARG/ENV — no runtime secret, no env var injection into running container needed"

patterns-established:
  - "Build-time feature flags: ARG in Dockerfile frontend stage + --build-arg in CI workflow is the pattern for environment-specific UI behavior"

requirements-completed: [STAGE-03]

# Metrics
duration: 2min
completed: 2026-03-06
---

# Phase 5 Plan 01: Staging Banner Summary

**Amber sticky StagingBanner component baked into Docker image at build time via VITE_APP_ENV ARG — renders on every authenticated page and login, preventing staging/production confusion**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-06T20:59:07Z
- **Completed:** 2026-03-06T21:01:33Z
- **Tasks:** 2
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- StagingBanner.tsx: amber-400 sticky banner, z-50, shows when VITE_APP_ENV is not 'production' (undefined also shows — safe default)
- Layout.tsx and Login.tsx both import and render StagingBanner as first child at viewport top
- Dockerfile frontend stage declares ARG VITE_APP_ENV + ENV VITE_APP_ENV=$VITE_APP_ENV before npm run build — bakes value into Vite bundle
- deploy-test.yml docker build command passes --build-arg VITE_APP_ENV=staging

## Task Commits

Each task was committed atomically:

1. **Task 1: Create StagingBanner and integrate into Layout and Login** - `4e006a7` (feat)
2. **Task 2: Wire VITE_APP_ENV build arg through Dockerfile and GitHub Actions** - `349308c` (feat)

**Plan metadata:** committed after SUMMARY creation (docs: complete plan)

## Files Created/Modified

- `frontend/src/components/StagingBanner.tsx` - New component: amber-400 div, sticky top-0, z-50, guards on VITE_APP_ENV !== 'production'
- `frontend/src/components/Layout.tsx` - Added StagingBanner import + render as first child before nav
- `frontend/src/pages/Login.tsx` - Added StagingBanner import + render as first child of outer div
- `deploy/Dockerfile` - ARG VITE_APP_ENV + ENV VITE_APP_ENV=$VITE_APP_ENV added before RUN npm run build in frontend stage
- `.github/workflows/deploy-test.yml` - --build-arg VITE_APP_ENV=staging added to docker build command

## Decisions Made

- StagingBanner uses `import.meta.env.VITE_APP_ENV === 'production'` as guard — undefined (local dev without build arg) shows the banner, which is the safe default
- Banner uses `sticky top-0 z-50` so it stays visible on scroll and sits above the nav bar in Layout
- VITE_APP_ENV baked at build time (not runtime) — this is correct for Vite: env vars must be available during `npm run build` to be inlined into the bundle

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing backend test failures (27 failed, 33 errors) exist on the main branch unrelated to frontend changes — confirmed by running tests before and after my changes. No regressions introduced.

## User Setup Required

None - no external service configuration required. The banner will appear automatically in the next staging Docker build triggered by push to main.

## Next Phase Readiness

- STAGE-03 requirement satisfied: every page (authenticated and login) shows amber staging banner
- Next plans in phase 05 can proceed — banner infrastructure is in place
- Banner will be active in the next CI/CD push to main

---
*Phase: 05-staging-deployment*
*Completed: 2026-03-06*
