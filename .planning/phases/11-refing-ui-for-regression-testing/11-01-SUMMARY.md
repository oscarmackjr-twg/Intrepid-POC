---
phase: 11-refing-ui-for-regression-testing
plan: "01"
subsystem: ui
tags: [react, react-router, tailwind, typography, css]

# Dependency graph
requires:
  - phase: 10-revamp-user-interface-phase-10
    provides: TWG brand theme, sidebar nav structure, Phase 10 CSS variables in index.css
provides:
  - Unique per-link active state checks in sidebar nav (no two links share the same active condition)
  - Typography CSS custom properties (--line-height-body, --line-height-heading) and heading letter-spacing
affects: [regression-testing, future-ui-phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Nav active state: combine pathname.startsWith() with location.search.includes('type=X') for query-param child links"
    - "Top-level nav item uses !location.search.includes('type=') to avoid co-highlighting with typed children"

key-files:
  created: []
  modified:
    - frontend/src/components/Layout.tsx
    - frontend/src/index.css

key-decisions:
  - "Nav active state uses pathname + search query combination — not pathname alone — for child links differentiated only by query param"
  - "Admin Cash Flow link (/cashflow no type param) active only when !type= to avoid co-highlighting with Cash Flow SG/CIBC"

patterns-established:
  - "Active nav check pattern: location.pathname.startsWith('/base') && location.search.includes('type=X') for query-param children"

requirements-completed: [UI-06]

# Metrics
duration: 2min
completed: 2026-03-13
---

# Phase 11 Plan 01: Nav Active-State Fix + Typography Polish Summary

**Fixed sidebar nav active-state bug where all /program-runs and /cashflow child links highlighted simultaneously, using pathname+search query combination; added typography CSS variables for line-height and heading letter-spacing**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-13T23:17:00Z
- **Completed:** 2026-03-13T23:18:44Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Fixed all 5 buggy nav active state checks — each link now highlights independently
- Top-level "Program Runs" and admin "Cash Flow" links no longer co-highlight with their type-param children
- Added `--line-height-body: 1.6` and `--line-height-heading: 1.25` CSS vars to `:root`
- Applied `line-height: var(--line-height-body)` to body rule
- Added `h1, h2, h3, h4` rule with tightened `letter-spacing: -0.01em` for conservative financial aesthetic
- Added `table { border-collapse: collapse }` for clean table borders site-wide

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix nav active-state logic in Layout.tsx** - `c385343` (fix)
2. **Task 2: Typography and spacing polish pass (index.css)** - `3b92ff8` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `frontend/src/components/Layout.tsx` - Fixed 6 active-state boolean expressions to use pathname+search query checks
- `frontend/src/index.css` - Added line-height vars, h1-h4 rule, table border-collapse; body line-height set

## Decisions Made
- Nav active state uses `location.search.includes('type=sg')` / `type=cibc` — simple string inclusion check sufficient since type values are unique and won't collide
- Top-level links use `!location.search.includes('type=')` negation to remain inactive when on a typed child route

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None — index.css already had `-webkit-font-smoothing: antialiased` from Phase 10; Task 2 was purely additive.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Nav active states are now reliable — suitable for regression testing (Phase 11's stated goal)
- Typography polish applied — consistent conservative-financial appearance across all pages
- No blockers for subsequent Phase 11 plans

---
*Phase: 11-refing-ui-for-regression-testing*
*Completed: 2026-03-13*
