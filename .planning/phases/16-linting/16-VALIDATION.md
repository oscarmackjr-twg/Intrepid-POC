---
phase: 16
slug: linting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend); no frontend test framework configured |
| **Config file** | `backend/pyproject.toml` (ruff config only; pytest uses defaults) |
| **Quick run command** | `cd frontend && npm run lint` + `python -m ruff check backend/` |
| **Full suite command** | `pytest --tb=short -q` (from `backend/`) |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run lint` and `python -m ruff check backend/`
- **After every plan wave:** Same — all changes are in the linting tooling itself
- **Before `/gsd:verify-work`:** Both linters clean + CI step confirmed
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | LINT-01/02/03 | smoke | `cd frontend && npm run lint` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | LINT-02 | smoke | `python -m ruff check backend/` | ✅ | ⬜ pending |
| 16-02-01 | 02 | 2 | LINT-04 | smoke | `cd frontend && npm install && ls .husky/pre-commit` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/eslint.config.js` — must be created (task 16-01-01); the linter itself is the artifact
- [ ] `.husky/pre-commit` — must be created after husky install (task 16-02-01)
- [ ] `husky` and `lint-staged` packages — must be installed (task 16-02-01) before pre-commit scaffold exists

*No new pytest test files required — linting tools are the deliverables, validated by running them.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI ESLint step present in deploy-test.yml | LINT-03 | File inspection | Read `.github/workflows/deploy-test.yml` — confirm `npm run lint` step exists in `security-quality-gate` job |
| husky pre-commit hook file exists | LINT-04 | File existence | Check `.husky/pre-commit` exists and contains `npx lint-staged` |
| `prepare` script in package.json | LINT-04 | File inspection | `grep -A1 "prepare" frontend/package.json` shows `"husky"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
