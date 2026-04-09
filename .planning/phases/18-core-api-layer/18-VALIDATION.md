---
phase: 18
slug: core-api-layer
status: draft
nyquist_compliant: false
wave_0_complete: false  # set to true after Plan 01 Task 2 completes
created: 2026-04-08
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pytest.ini` or `backend/pyproject.toml` |
| **Quick run command** | `cd backend && pytest tests/test_re_api.py -x -q` |
| **Full suite command** | `cd backend && pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/test_re_api.py -x -q`
- **After every plan wave:** Run `cd backend && pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 0 | API-01–11 | — | N/A | stub | `pytest tests/test_re_api.py -x -q` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | API-01 | — | N/A | integration | `pytest tests/test_re_api.py::test_kpis -x -q` | ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 1 | API-02 | — | N/A | integration | `pytest tests/test_re_api.py::test_concentration -x -q` | ❌ W0 | ⬜ pending |
| 18-01-04 | 01 | 1 | API-03 | — | N/A | integration | `pytest tests/test_re_api.py::test_distributions -x -q` | ❌ W0 | ⬜ pending |
| 18-01-05 | 01 | 1 | API-04 | — | N/A | integration | `pytest tests/test_re_api.py::test_maturity_profile -x -q` | ❌ W0 | ⬜ pending |
| 18-01-06 | 01 | 2 | API-05 | — | Filter enforcement verified | integration | `pytest tests/test_re_api.py::test_loans_list -x -q` | ❌ W0 | ⬜ pending |
| 18-01-07 | 01 | 2 | API-06 | — | N/A | integration | `pytest tests/test_re_api.py::test_loan_detail -x -q` | ❌ W0 | ⬜ pending |
| 18-01-08 | 01 | 2 | API-07 | — | N/A | integration | `pytest tests/test_re_api.py::test_cashflow_performance -x -q` | ❌ W0 | ⬜ pending |
| 18-01-09 | 01 | 3 | API-08 | — | N/A | integration | `pytest tests/test_re_api.py::test_origination_pipeline -x -q` | ❌ W0 | ⬜ pending |
| 18-01-10 | 01 | 3 | API-09 | — | N/A | integration | `pytest tests/test_re_api.py::test_market_context -x -q` | ❌ W0 | ⬜ pending |
| 18-01-11 | 01 | 3 | API-10 | — | N/A | integration | `pytest tests/test_re_api.py::test_sensitivity -x -q` | ❌ W0 | ⬜ pending |
| 18-01-12 | 01 | 3 | API-11 | T-18-01 | sales_team users see only their loans | integration | `pytest tests/test_re_api.py::test_sales_team_scoping -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_re_api.py` — test stubs for all 11 endpoints + scoping test (API-01 through API-11)
- [ ] `backend/tests/conftest.py` — ensure RE test fixtures (test DB with seeded RE data) are available

*Existing pytest infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| All endpoints accessible in Swagger UI | API-01–11 | Phase gate requires visual verification | Start backend, open `/docs`, exercise each `/api/re/*` endpoint with no filters |
| `/api/re/market-context` shows live-hook markers | API-09 | Code annotation review | Read response, confirm stubbed values include comments/markers indicating live integration points |
| All endpoints respond under 500ms | SC-5 | Timing requires a running DB with seeded data | Use Swagger UI or curl with `time` against seeded dataset |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
