---
phase: 21-portfolio-composition-page
plan: "03"
subsystem: frontend
tags: [react, typescript, recharts, portfolio, re-dashboard]
dependency_graph:
  requires: ["21-02"]
  provides: ["TopExposuresTable component", "ConcentrationLimits component", "all 6 RePortfolioPage panels implemented"]
  affects: ["frontend/src/pages/RePortfolioPage.tsx"]
tech_stack:
  added: []
  patterns: ["Recharts-free table component", "Tailwind progress bar with inline style width", "TWG brand color classes"]
key_files:
  created:
    - frontend/src/components/re/TopExposuresTable.tsx
    - frontend/src/components/re/ConcentrationLimits.tsx
  modified:
    - frontend/src/pages/RePortfolioPage.tsx
decisions:
  - "Math.min(proximity * 100, 100) caps progress bar width at 100% — T-21-08 mitigation for proximity values > 1.0"
  - "onClick={undefined} stub on tr with TODO comment per D-18 — Phase 25 wires row click to loan detail side-panel"
  - "No additional API query needed — concentration query already returns top_10_exposures and concentration_limits"
metrics:
  duration: "~15 min"
  completed: "2026-04-09T13:37:18Z"
  tasks_completed: 2
  files_changed: 3
requirements: [COMP-05, COMP-06]
---

# Phase 21 Plan 03: Top-10 Exposures Table and Concentration Limits Summary

**One-liner:** TopExposuresTable (7-col HTML table with formatKpi formatters) and ConcentrationLimits (Tailwind progress bars with green/yellow/red proximity color coding) wired into RePortfolioPage slots 5 and 6, completing all six portfolio panels.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create TopExposuresTable component and wire into RePortfolioPage | 62d0589 | TopExposuresTable.tsx (created), RePortfolioPage.tsx (modified) |
| 2 | Create ConcentrationLimits component and wire into RePortfolioPage | a86aa7e | ConcentrationLimits.tsx (created), RePortfolioPage.tsx (modified) |

## What Was Built

### TopExposuresTable (`frontend/src/components/re/TopExposuresTable.tsx`)

- 7-column HTML table: Loan #, Borrower, UPB, LTV, DSCR, Property Type, State
- UPB formatted with `formatUPB`, LTV with `formatRate`, DSCR with `formatDSCR` (reused from `formatKpi.ts`)
- `onClick={undefined}` stub with `TODO: Phase 25` comment per D-18
- TWG navy `#1a3868` for row text, `#475569` for headers
- No pagination, no sorting — fixed 10 rows per D-16

### ConcentrationLimits (`frontend/src/components/re/ConcentrationLimits.tsx`)

- Horizontal Tailwind progress bars (plain divs, no chart library)
- Color: green (`bg-green-500`) < 70% proximity, yellow (`bg-yellow-400`) 70-90%, red (`bg-red-500`) >= 90%
- `Math.min(proximity * 100, 100)` caps inline `width` style at 100% — T-21-08 mitigation
- Displays `category`, `current_pct * 100` with 1 decimal, `limit_pct * 100` label

### RePortfolioPage wiring

- Slot 5 (Top-10 Exposures): replaced static placeholder with live `concentration.data?.top_10_exposures`
- Slot 6 (Concentration Limits): replaced static placeholder with live `concentration.data?.concentration_limits`
- Both slots use `concentration.isLoading` and non-empty checks for ChartCard loading/no-data states
- No new API query needed — both data fields are already in the `ConcentrationResponse` from the existing concentration query

## Verification Results

All 6 checks from plan verification section passed:
- `TopExposuresTable` present in RePortfolioPage
- `ConcentrationLimits` present in RePortfolioPage
- `bg-red-500` present in ConcentrationLimits
- `formatUPB` present in TopExposuresTable
- All 6 panel titles present: Property Type, Top States by UPB, Loan Size Distribution, Maturity Profile, Top-10 Exposures, Concentration Limits
- No placeholder ChartCards with `isEmpty={true} isLoading={false}` remain

TypeScript: no errors introduced by new components (pre-existing baseline errors from missing node_modules in worktree are unrelated to this plan's changes).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

- `TopExposuresTable` `<tr onClick={undefined}>` — intentional per D-18; Phase 25 will wire this to the loan detail side-panel.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Both components are pure render components consuming already-fetched API data. T-21-08 (progress bar width overflow) mitigated via `Math.min`. T-21-09 (XSS) mitigated via React JSX auto-escaping — no `dangerouslySetInnerHTML` used.

## Self-Check: PASSED

- `frontend/src/components/re/TopExposuresTable.tsx` — FOUND
- `frontend/src/components/re/ConcentrationLimits.tsx` — FOUND
- Commit 62d0589 — verified in git log
- Commit a86aa7e — verified in git log
