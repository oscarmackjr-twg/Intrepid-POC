---
phase: 19
slug: filter-hook-typescript-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — no frontend test framework (no vitest/jest config) |
| **Config file** | N/A |
| **Quick run command** | `cd frontend && npx tsc --noEmit` (TypeScript type check only) |
| **Full suite command** | `cd frontend && npx tsc --noEmit` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx tsc --noEmit`
- **After every plan wave:** TypeScript check + manual browser smoke test
- **Before `/gsd-verify-work`:** Full TypeScript clean + all 4 manual verifications below
- **Max feedback latency:** ~5 seconds (TypeScript check)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | FILTER-01 | — | N/A | type-check | `cd frontend && npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | FILTER-01 | — | N/A | type-check | `cd frontend && npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 2 | FILTER-02 | — | URL params not eval'd | type-check + manual | `cd frontend && npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| 19-01-04 | 01 | 2 | FILTER-04 | — | N/A | manual | — | N/A | ⬜ pending |
| 19-02-01 | 02 | 1 | FILTER-01 | — | No dangerouslySetInnerHTML | type-check | `cd frontend && npx tsc --noEmit` | ❌ W0 | ⬜ pending |
| 19-02-02 | 02 | 2 | FILTER-02,03 | — | N/A | manual | — | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- No frontend test framework present — TypeScript compiler is the automated feedback mechanism
- `npx tsc --noEmit` is available without installation (TypeScript already in devDependencies)

*No Wave 0 stubs needed — TypeScript type check covers automated verification; manual browser checks cover behavioral verification.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Filter sidebar renders with 9 controls | FILTER-01 | Visual — no browser test framework | Navigate to `/re-dashboard`, confirm 9 filter controls visible in right panel |
| Filter updates URL + Zustand simultaneously | FILTER-02 | Requires DevTools inspection | Select a property type, check URL params updated, open React DevTools Zustand store tab |
| "Clear all filters" resets everything | FILTER-04 | Browser interaction | Apply filters, click "Clear all filters", verify URL params gone and store reset |
| FILTER-03 deferred | FILTER-03 | TanStack Query not installed in Phase 19 | Verified in Phase 20 when TanStack Query is added |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
