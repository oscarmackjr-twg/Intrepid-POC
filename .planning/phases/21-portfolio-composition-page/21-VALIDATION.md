---
phase: 21
slug: portfolio-composition-page
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-08
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | No frontend test framework detected — no jest.config.*, vitest.config.*, or __tests__/ directories present |
| **Config file** | None |
| **Quick run command** | `cd frontend && npx tsc --noEmit` |
| **Full suite command** | `cd frontend && npx tsc --noEmit` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx tsc --noEmit`
- **After every plan wave:** Run `cd frontend && npx tsc --noEmit`
- **Before `/gsd-verify-work`:** TypeScript must compile clean AND all 5 success criteria visible in browser
- **Max feedback latency:** ~5 seconds (tsc) + manual browser check

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | routing refactor | — | N/A | tsc | `cd frontend && npx tsc --noEmit` | ❌ creates | ⬜ pending |
| 21-02-01 | 02 | 2 | COMP-01, COMP-02, COMP-03, UX-01 | — | chart click payloads are server-sourced strings, not user input | tsc + manual | `cd frontend && npx tsc --noEmit` | ❌ creates | ⬜ pending |
| 21-02-02 | 02 | 2 | COMP-04 | — | N/A | tsc + manual | `cd frontend && npx tsc --noEmit` | ❌ creates | ⬜ pending |
| 21-03-01 | 03 | 3 | COMP-05 | — | N/A | tsc + manual | `cd frontend && npx tsc --noEmit` | ❌ creates | ⬜ pending |
| 21-03-02 | 03 | 3 | COMP-06 | — | N/A | tsc + manual | `cd frontend && npx tsc --noEmit` | ❌ creates | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `cd frontend && npm install recharts` — install Recharts 3.8.1 (no test framework needed, recharts ships its own types)

*No test framework installation needed — no frontend test framework in this project.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Property type donut renders with data | COMP-01 | No frontend test framework | Navigate to `/re-dashboard/portfolio`, confirm donut chart visible with segments |
| Top states bar chart renders with data | COMP-02 | No frontend test framework | Confirm horizontal bar chart shows ≥1 state with UPB value |
| Loan size histogram renders | COMP-03 | No frontend test framework | Confirm histogram bars visible |
| Maturity profile stacked bar renders | COMP-04 | No frontend test framework | Confirm grouped bar chart shows quarter/year labels |
| Top-10 exposures table shows 10 rows | COMP-05 | No frontend test framework | Count rows in table, confirm LTV/DSCR/property type/state columns present |
| Concentration limit bars show correct color | COMP-06 | No frontend test framework | Confirm ≥1 limit bar visible with color band (green/yellow/red) |
| Pie slice click filters dashboard | UX-01 | No frontend test framework | Click a pie slice, confirm URL param updates (e.g., `?property_type=Multifamily`) and KPI card values change |

---

## Phase Gate Checklist (before `/gsd-verify-work`)

- [ ] `cd frontend && npx tsc --noEmit` exits 0 (clean compile)
- [ ] `/re-dashboard` (Executive Summary) still renders KPI cards — routing refactor did not break existing page
- [ ] Tab strip visible on `/re-dashboard` with all 5 tabs; active tab highlighted in `#1a3868` navy
- [ ] `/re-dashboard/portfolio` loads Portfolio Composition page without error
- [ ] All 6 panels render with non-zero data from seeded database
- [ ] Clicking a pie slice updates URL params and triggers KPI card refetch
- [ ] Filter sidebar still renders on portfolio page (inherited from ReDashboard shell)
