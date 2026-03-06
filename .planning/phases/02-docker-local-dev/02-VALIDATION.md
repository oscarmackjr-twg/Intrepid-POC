---
phase: 2
slug: docker-local-dev
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && pytest tests/test_api_routes.py -x -q` |
| **Full suite command** | `cd backend && pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/test_api_routes.py -x -q`
- **After every plan wave:** Run `cd backend && pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green + manual Docker smoke test
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | DOCKER-02 | static | `grep -r "C:\\\\" deploy/docker-compose.yml; test $? -ne 0` | existing | pending |
| 2-01-02 | 01 | 1 | DOCKER-01 | unit | `cd backend && pytest tests/test_api_routes.py -x -q` | existing | pending |
| 2-01-03 | 01 | 1 | DOCKER-04 | unit | `cd backend && pytest tests/test_api_routes.py -x -q` | existing | pending |
| 2-01-04 | 01 | 1 | DOCKER-03 | manual | `curl -f http://localhost:8000/health/ready` | manual-only | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

Existing test infrastructure covers all backend unit/integration requirements. Docker-level requirements are verified manually.

*No new test files required. Existing `tests/test_api_routes.py` validates backend import correctness after working_dir and config changes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docker compose up` starts all services | DOCKER-01 | Requires Docker daemon and running stack | Run `docker compose -f deploy/docker-compose.yml up -d && docker compose -f deploy/docker-compose.yml ps` — all services should show `Up` or `healthy` |
| App accessible at localhost:8000 | DOCKER-03 | Requires running container stack | Run `curl -f http://localhost:8000/health/ready` — expect 200 response |
| Migrations run automatically | DOCKER-04 | Requires running container with DB | Run `docker compose -f deploy/docker-compose.yml logs app` — expect `Running upgrade` in output |
| Frontend accessible at localhost:5173 | DOCKER-01 | Requires running frontend container | Open `http://localhost:5173` in browser — expect React app loads |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
