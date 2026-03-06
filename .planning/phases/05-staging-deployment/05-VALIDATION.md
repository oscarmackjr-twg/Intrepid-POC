---
phase: 5
slug: staging-deployment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend only — no frontend test runner) |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest tests/ -q --tb=short` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -q --tb=short`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green + all manual verifications complete
- **Max feedback latency:** ~10 seconds (backend), visual for frontend

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | STAGE-03 | manual (visual) | N/A | N/A | ⬜ pending |
| 05-01-02 | 01 | 1 | STAGE-03 | manual (visual) | N/A | N/A | ⬜ pending |
| 05-02-01 | 02 | 1 | STAGE-02 | manual | N/A | N/A | ⬜ pending |
| 05-03-01 | 03 | 2 | STAGE-01 | manual | N/A | N/A | ⬜ pending |
| 05-03-02 | 03 | 2 | STAGE-01 | manual | N/A | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

No new backend logic is introduced by Phase 5. The seed script is a one-off utility (not part of the running application). Frontend has no test runner; visual verification is the acceptance mechanism.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Staging URL loads app after deploy | STAGE-01 | Requires live AWS environment | Open `http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com` in browser; confirm app loads |
| Ops can log in and upload a file | STAGE-02 | Requires live staging + seeded user | Log in as `admin`, navigate to file upload, upload a sample loan spreadsheet, confirm accepted |
| Banner renders on every page | STAGE-03 | No frontend test runner | Check Login, Dashboard, Pipeline Runs, Exceptions, File Manager, Holiday Maintenance — each should show amber staging banner at top |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s (backend), visual for frontend
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
