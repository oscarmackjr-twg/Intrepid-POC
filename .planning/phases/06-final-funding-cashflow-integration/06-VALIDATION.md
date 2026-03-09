---
phase: 6
slug: final-funding-cashflow-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest tests/test_final_funding_jobs.py tests/test_final_funding_runner.py -x -v` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_final_funding_jobs.py tests/test_final_funding_runner.py -x -v`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 1 | FF-01 | unit/integration | `pytest tests/test_final_funding_runner.py::test_sg_script_executes -x` | ❌ Wave 0 | ⬜ pending |
| 6-01-02 | 01 | 1 | FF-02 | unit/integration | `pytest tests/test_final_funding_runner.py::test_cibc_script_executes -x` | ❌ Wave 0 | ⬜ pending |
| 6-02-01 | 02 | 1 | FF-03 | unit | `pytest tests/test_final_funding_jobs.py::test_create_job_returns_queued -x` | ❌ Wave 0 | ⬜ pending |
| 6-02-02 | 02 | 1 | FF-04 | unit | `pytest tests/test_final_funding_jobs.py::test_job_lifecycle_success -x` | ❌ Wave 0 | ⬜ pending |
| 6-02-03 | 02 | 1 | FF-05 | unit | `pytest tests/test_final_funding_jobs.py::test_job_lifecycle_failure -x` | ❌ Wave 0 | ⬜ pending |
| 6-02-04 | 02 | 1 | FF-06 | unit | `pytest tests/test_final_funding_jobs.py::test_poll_endpoint -x` | ❌ Wave 0 | ⬜ pending |
| 6-02-05 | 02 | 1 | FF-09 | unit | `pytest tests/test_final_funding_jobs.py::test_concurrent_job_409 -x` | ❌ Wave 0 | ⬜ pending |
| 6-03-01 | 03 | 2 | FF-07 | unit | `pytest tests/test_final_funding_runner.py::test_cashflow_bridge_copies_file -x` | ❌ Wave 0 | ⬜ pending |
| 6-03-02 | 03 | 2 | FF-08 | unit | `pytest tests/test_final_funding_runner.py::test_cashflow_bridge_absent_is_noop -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_final_funding_jobs.py` — stubs for FF-03, FF-04, FF-05, FF-06, FF-09
- [ ] `backend/tests/test_final_funding_runner.py` — stubs for FF-01, FF-02, FF-07, FF-08
- [ ] `backend/tests/conftest.py` — extend with DB connection and temp input dir fixtures (if not already present)

Note: FF-01 and FF-02 (real script execution) require a minimal `files_required/` directory with placeholder Excel files. Mark these `@pytest.mark.integration` and skip in CI without sample data.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Final Funding SG run shows RUNNING then COMPLETED in Program Runs UI | FF-01, FF-03 | Requires real script + S3/local inputs | Trigger run from UI, watch status poll update without page refresh |
| Final Funding CIBC run shows RUNNING then COMPLETED in Program Runs UI | FF-02, FF-03 | Requires real script + S3/local inputs | Trigger run from UI, watch status poll update without page refresh |
| Cashflow output auto-available as Final Funding input | FF-07 | End-to-end storage bridge | Run cashflow mode, then trigger Final Funding — verify current_assets.csv present in temp dir without manual upload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
