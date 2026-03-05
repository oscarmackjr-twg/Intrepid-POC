---
phase: 1
slug: local-dev
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.3 |
| **Config file** | `backend/pytest.ini` (exists) |
| **Quick run command** | `cd backend && venv/bin/pytest tests/ -x --tb=short -q` |
| **Full suite command** | `cd backend && venv/bin/pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds (unit tests, SQLite in-memory) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && venv/bin/pytest tests/ -x --tb=short -q`
- **After every plan wave:** Run `cd backend && venv/bin/pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green + all manual smoke checks completed
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-env-01 | env-config | 1 | LOCAL-03 | manual inspect | `grep -rn "C:\\\\" backend/.env` returns nothing | ✅ exists (modify) | ⬜ pending |
| 1-env-02 | env-config | 1 | LOCAL-04 | manual inspect | verify `backend/.env.example` covers all vars | ❌ W0 | ⬜ pending |
| 1-git-01 | env-config | 1 | LOCAL-06 | unit | `git check-ignore -v backend/data/sample/test.xlsx` returns nothing | ❌ W0 | ⬜ pending |
| 1-mig-01 | migrations | 2 | LOCAL-05 | integration | `cd backend && venv/bin/alembic upgrade head` exits 0 | ❌ W0 | ⬜ pending |
| 1-data-01 | sample-data | 2 | LOCAL-06 | integration | `cd backend && venv/bin/python main.py --pdate 2026-02-19` exits 0 | ❌ W0 | ⬜ pending |
| 1-make-01 | dev-tooling | 3 | LOCAL-01 | smoke | `make run-backend` starts uvicorn; `curl http://localhost:8000/api/health` returns 200 | ❌ W0 | ⬜ pending |
| 1-make-02 | dev-tooling | 3 | LOCAL-02 | smoke | `make run-frontend` starts Vite at port 5173 (visual verify) | ❌ W0 | ⬜ pending |
| 1-make-03 | dev-tooling | 3 | LOCAL-01 | integration | `make migrate` runs `alembic upgrade head` without error | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/data/sample/files_required/` — sample data directory with pipeline input files (covers LOCAL-06)
- [ ] `backend/.env.example` — committed env template with self-documenting comments (covers LOCAL-04)
- [ ] `backend/migrations/versions/<hash>_initial_schema.py` — generated via `alembic revision --autogenerate` (covers LOCAL-05)
- [ ] `Makefile` at project root — setup/run-backend/run-frontend/migrate targets (covers LOCAL-01, LOCAL-02)
- [ ] `DEVELOPMENT.md` at project root — onboarding guide documenting sample date and run instructions

*Existing test infrastructure in `backend/tests/` covers unit testing with SQLite in-memory — no new test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| uvicorn starts and connects to local Postgres | LOCAL-01 | Server process startup cannot be asserted in unit tests | Run `make run-backend`; verify startup log shows no errors; `curl http://localhost:8000/api/health` returns 200 |
| Vite dev server starts at port 5173 with HMR | LOCAL-02 | Browser-based frontend, visual confirmation needed | Run `make run-frontend`; open `http://localhost:5173`; verify app loads |
| `.env` has no hardcoded Windows paths | LOCAL-03 | Content inspection of gitignored file | Run `grep -n "C:\\\\" backend/.env`; must return no matches |
| New dev can onboard from `.env.example` alone | LOCAL-04 | Requires human judgment of doc completeness | Fresh clone: copy `.env.example` to `.env`, fill `DATABASE_URL`, run `make migrate` — must succeed without consulting any other file |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
