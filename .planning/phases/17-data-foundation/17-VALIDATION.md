---
phase: 17
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pytest.ini (or pyproject.toml) |
| **Quick run command** | `cd backend && python -m pytest tests/test_re_loans.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_re_loans.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | DATA-01 | — | N/A | integration | `cd backend && alembic upgrade head && psql $DATABASE_URL -c "SELECT COUNT(*) FROM re_loans"` | ✅ / ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | DATA-02 | — | N/A | integration | `cd backend && psql $DATABASE_URL -c "\d re_loans" \| grep -E "NUMERIC(18,6)"` | ✅ / ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 2 | DATA-03 | — | N/A | integration | `cd backend && psql $DATABASE_URL -c "SELECT COUNT(*) FROM re_loan_cashflows"` | ✅ / ❌ W0 | ⬜ pending |
| 17-01-04 | 01 | 2 | DATA-04 | — | N/A | integration | `cd backend && python -m pytest tests/test_re_loans.py -x -q` | ✅ / ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_re_loans.py` — stubs for DATA-01 through DATA-04
- [ ] `tests/conftest.py` — db session fixture (reuse existing if present)
- [ ] `faker>=33.0.0` in `backend/requirements-dev.txt` — seed script dependency

*Note: Existing pytest infrastructure covers the framework; Wave 0 adds phase-specific test stubs and the faker dev dependency.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `alembic upgrade head` runs clean in CI without conflicts | DATA-01 | Requires live database + migration chain context | Run `alembic upgrade head` against a clean DB and verify exit 0 |
| Seeded data spans 5+ property types, 20+ states, 8+ MSAs, 2 as_of_date snapshots | DATA-04 | Distribution requires visual/SQL spot-check | `SELECT property_type, COUNT(*) FROM re_loans GROUP BY property_type` and `SELECT as_of_date, COUNT(*) FROM re_loans GROUP BY as_of_date` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
