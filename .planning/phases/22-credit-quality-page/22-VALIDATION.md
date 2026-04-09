---
phase: 22
slug: credit-quality-page
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && pytest tests/test_re_api.py -x -q` |
| **Full suite command** | `cd backend && pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/test_re_api.py -x -q`
- **After every plan wave:** Run `cd backend && pytest -x -q`
- **Before `/gsd-verify-work`:** Full backend suite green + manual browser verification of all 6 panels
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | CREDIT-04 | T-22-01 | Sales team scoped — `build_re_filters()` applied | integration | `pytest tests/test_re_api.py::test_delinquency_waterfall -x -q` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | CREDIT-05 | T-22-01 | Sales team scoped — `build_re_filters()` applied | integration | `pytest tests/test_re_api.py::test_risk_rating_migration -x -q` | ❌ W0 | ⬜ pending |
| 22-01-03 | 01 | 1 | CREDIT-03 | T-22-02 | LoanSummary exposes prior_risk_rating for trend arrows | integration | `pytest tests/test_re_api.py::test_loans_list_has_prior_risk_rating -x -q` | ❌ W0 | ⬜ pending |
| 22-01-04 | 01 | 1 | CREDIT-01,02 | — | Existing /distributions returns correct color bands | integration | `pytest tests/test_re_api.py::test_distributions_ltv_color_bands tests/test_re_api.py::test_distributions_dscr_color_bands -x -q` | ❌ W0 | ⬜ pending |
| 22-02-01 | 02 | 1 | CREDIT-01 | — | LTV histogram renders with color-banded bars | manual | Open /re-dashboard/credit in browser; verify green/yellow/red bars | N/A | ⬜ pending |
| 22-02-02 | 02 | 1 | CREDIT-02 | — | DSCR histogram renders with color-banded bars | manual | Same page — DSCR panel shows green/yellow/red bars | N/A | ⬜ pending |
| 22-02-03 | 02 | 1 | CREDIT-03 | — | Watchlist shows risk_rating 4–5 loans with trend arrows | manual | Watchlist panel shows criticized loans; trend arrows visible | N/A | ⬜ pending |
| 22-02-04 | 02 | 1 | CREDIT-04 | — | Delinquency waterfall shows 5 ordered buckets | manual | Waterfall panel: Current → 30 → 60 → 90 → Default buckets populated | N/A | ⬜ pending |
| 22-02-05 | 02 | 1 | CREDIT-05 | — | Migration matrix renders prior→current rating movement | manual | Matrix visible with cells; two as_of_date snapshot values present | N/A | ⬜ pending |
| 22-02-06 | 02 | 1 | CREDIT-06 | — | Sensitivity table shows ±100/200/300 bps scenarios | manual | Sensitivity table: 6 rows of scenario data populated | N/A | ⬜ pending |
| 22-02-07 | 02 | 1 | UX-01 | — | Filter sidebar updates all panels without page reload | manual | Change property_type in sidebar; all 6 panels refresh | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_re_api.py` — add stubs for:
  - `test_delinquency_waterfall` (CREDIT-04)
  - `test_risk_rating_migration` (CREDIT-05)
  - `test_loans_list_has_prior_risk_rating` (CREDIT-03)
  - `test_distributions_ltv_color_bands` (CREDIT-01)
  - `test_distributions_dscr_color_bands` (CREDIT-02)

*Existing test file from Phase 18 — extend, do not recreate.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LTV histogram renders green/yellow/red bars | CREDIT-01 | No frontend test framework | Open /re-dashboard/credit; confirm bars have correct colors |
| DSCR histogram renders green/yellow/red bars | CREDIT-02 | No frontend test framework | Same page — DSCR panel |
| Watchlist trend arrows visible | CREDIT-03 | Visual rendering; no frontend tests | Watchlist panel — confirm ↑↓→ arrows render per risk_rating change |
| Delinquency waterfall ordered correctly | CREDIT-04 | Visual layout; no frontend tests | Current → 30 → 60 → 90 → Default left-to-right order |
| Migration matrix cells populated | CREDIT-05 | Requires two snapshot dates; manual verification | Matrix: confirm cells show loan counts per prior→current rating pair |
| Sensitivity table ±300 bps row renders | CREDIT-06 | Visual rendering | Table: confirm all 6 scenario rows populated |
| Filter propagation to all 6 panels | UX-01 | Browser network verification | Change filter; watch Network tab for 3+ API calls to fire |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
