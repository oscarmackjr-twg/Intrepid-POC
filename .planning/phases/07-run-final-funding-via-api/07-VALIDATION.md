---
phase: 7
slug: run-final-funding-via-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.3 |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && pytest tests/ -x -q -m "not integration"` |
| **Full suite command** | `cd backend && pytest tests/` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/ -x -q -m "not integration"`
- **After every plan wave:** Run `cd backend && pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-xx-01 | TBD | 0 | HARD-02 | unit | `pytest tests/test_settings_guard.py -x` | ❌ W0 | ⬜ pending |
| 7-xx-02 | TBD | 0 | HARD-02 | unit | `pytest tests/test_seed_admin.py -x` | ❌ W0 | ⬜ pending |
| 7-xx-03 | TBD | 0 | HARD-03 | unit | `pytest tests/test_auth_security.py -x -k cookie` | ❌ W0 | ⬜ pending |
| 7-xx-04 | TBD | 0 | HARD-04 | unit | `pytest tests/test_api_files.py -x -k error_message` | ❌ W0 | ⬜ pending |
| 7-xx-05 | TBD | 0 | HARD-04 | unit | `pytest tests/test_storage_local.py -x -k no_file_uri` | ❌ W0 | ⬜ pending |
| 7-xx-06 | TBD | 0 | HARD-06 | unit | `pytest tests/test_audit_log.py -x` | ❌ W0 | ⬜ pending |
| 7-xx-07 | TBD | 1 | HARD-01 | smoke | `terraform validate` (in CI gate) | N/A — CI | ⬜ pending |
| 7-xx-08 | TBD | 1 | HARD-02 | unit | `pytest tests/test_auth_routes.py -x -k password_policy` | ❌ W0 | ⬜ pending |
| 7-xx-09 | TBD | 1 | HARD-03 | unit | `pytest tests/test_auth_routes.py -x -k cookie` | ❌ W0 | ⬜ pending |
| 7-xx-10 | TBD | 1 | HARD-03 | unit | `pytest tests/test_auth_routes.py -x -k rate_limit` | ❌ W0 | ⬜ pending |
| 7-xx-11 | TBD | 1 | HARD-05 | manual | Review deploy-test.yml `needs:` wiring | N/A — manual | ⬜ pending |
| 7-xx-12 | TBD | 1 | HARD-07 | manual | `git ls-files deploy/aws/eb/app-bundle.zip` → empty | N/A — manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_settings_guard.py` — startup validation fails with fallback SECRET_KEY (HARD-02)
- [ ] `backend/tests/test_seed_admin.py` — seed script generates non-hardcoded password (HARD-02)
- [ ] `backend/tests/test_auth_security.py` — `get_current_user` accepts cookie token (HARD-03)
- [ ] `backend/tests/test_api_files.py` — file list error returns generic message + correlation ID (HARD-04)
- [ ] `backend/tests/test_storage_local.py` — `get_file_url` returns API path not `file://` URI (HARD-04)
- [ ] `backend/tests/test_audit_log.py` — AuditLog DB write on login + table schema (HARD-06)

Extend existing files:
- [ ] `backend/tests/test_auth_routes.py` — add password policy tests, cookie-set tests, rate limit tests (HARD-02, HARD-03)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI gate job blocks deploy on lint failure | HARD-05 | GitHub Actions — no local equivalent | Review `deploy-test.yml` `needs:` field wires lint/test jobs before deploy |
| app-bundle.zip removed from git index | HARD-07 | Git history artifact — must verify index, not working tree | `git ls-files deploy/aws/eb/app-bundle.zip` must return empty |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
