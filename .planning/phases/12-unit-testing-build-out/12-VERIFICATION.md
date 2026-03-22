---
phase: 12-unit-testing-build-out
verified: 2026-03-22T03:00:00Z
status: passed
score: 7/7 must-haves verified (reconciled Phase 13)
re_verification: true
reconciled: 2026-03-22
reconciled_by: "Phase 13 plan 13-03"
gaps: []

human_verification:
  - test: "Run CI pipeline on a push to main"
    expected: "unit-tests job appears in GitHub Actions UI, runs in parallel with security-quality-gate, and deploy job is blocked when unit-tests fails"
    why_human: "Cannot execute GitHub Actions locally; requires an actual push or workflow_dispatch trigger to verify parallel execution and blocking behavior"
---

# Phase 12: Unit Testing Build Out — Verification Report

**Phase Goal:** Fix the failing tests to get the suite fully green, add coverage for untested modules, and wire pytest into CI as a blocking deploy gate.
**Verified:** 2026-03-22T03:00:00Z
**Status:** passed
**Re-verification:** Yes — reconciled Phase 13 (2026-03-22)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All 10 previously-failing tests now pass | VERIFIED | All 10 targeted tests verified fixed. test_enrichment.py::test_merge_with_loan_types now passes (assertion fixed to check 'Platform' — applied before Phase 13). |
| 2 | `pytest -m "not integration"` exits 0 with no failures | VERIFIED | Exit code 0: 248 passed, 2 skipped, 4 deselected. test_enrichment.py fix applied before Phase 13; confirmed during Phase 13 planning. |
| 3 | No production code was modified (test-only changes in 12-01) | VERIFIED | Commit 33db8b1 touches only backend/tests/ files per SUMMARY |
| 4 | Cashflow amortization, waterfall, and prepayment modules have unit test coverage | VERIFIED | 3 files exist with 17+8+20=45 tests, all @pytest.mark.unit, importing from cashflow.compute.* modules |
| 5 | CoMAP grid lookup, oct25_cutoff skip logic, and program-absent skip logic are tested | VERIFIED | test_rules_comap.py: 13 tests covering _prog_in_grid and _found_in_grid with inline grids built from imported constant keys |
| 6 | Archive run date derivation and path construction are tested | VERIFIED | test_orchestration_archive.py: 14 tests for _is_s3_style_prefix and _collect_input_paths |
| 7 | CI deploy-test.yml has a unit-tests job that runs pytest and blocks deploy | VERIFIED | unit-tests job at line 71; deploy job needs: [security-quality-gate, unit-tests] at line 92; working-directory: backend; pytest -m "not integration" with --cov flags |

**Score:** 7/7 truths verified (reconciled Phase 13 — test_enrichment.py fix already applied)

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/tests/test_normalize.py` | Fixed header-row-skipping assertions | VERIFIED | Contains test_header_row_skipping (6-row fixture), test_tu144_column_standardization, normalize function imports present |
| `backend/tests/test_scheduler.py` | Scheduler teardown isolation | VERIFIED | autouse clean_scheduler fixture with _force_stop_scheduler(); STATE_STOPPED pattern; scheduler.shutdown present |
| `backend/tests/test_integration_pipeline.py` | In-memory DataFrame pipeline tests | VERIFIED | sample_buy_df used; @pytest.mark.integration applied to TestPipelineExecution (correctly deselected from default run) |
| `backend/tests/test_rules_purchase_price.py` | Fixed exception assertion | VERIFIED | test_exception_generation asserts exceptions[0]['seller_loan_number'] == 'SFC_1001' (not 'loan_number') |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/tests/test_cashflow_amortization.py` | Amortization engine unit tests | VERIFIED | @pytest.mark.unit on 3 classes; imports from cashflow.compute.amortization; 17 tests; pytest.approx for floats |
| `backend/tests/test_cashflow_waterfall.py` | Waterfall model unit tests | VERIFIED | @pytest.mark.unit on 2 classes; imports from cashflow.compute.waterfall; 8 tests |
| `backend/tests/test_cashflow_prepayment.py` | Prepayment model unit tests | VERIFIED | @pytest.mark.unit on 4 classes; imports from cashflow.compute.prepayment; 20 tests including cpr_to_smm and psa_speed |
| `backend/tests/test_rules_comap.py` | CoMAP grid rule tests | VERIFIED | @pytest.mark.unit; imports _prog_in_grid, _found_in_grid, and all 5 constant dicts directly from rules.comap; inline grids; no conftest sample_comap_df |
| `backend/tests/test_orchestration_archive.py` | Archive run path/date logic tests | VERIFIED | @pytest.mark.unit; imports _is_s3_style_prefix, _collect_input_paths from orchestration.archive_run; uses temp_dir fixture |

### Plan 03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/workflows/deploy-test.yml` | unit-tests CI job blocking deploy | VERIFIED | unit-tests job at line 71; deploy needs: [security-quality-gate, unit-tests]; working-directory: backend; --cov=. --cov-report=term-missing; no --cov-fail-under |
| `backend/requirements.txt` | pytest-cov dependency | VERIFIED | Line 26: pytest-cov>=4.0 |
| `backend/tests/README.md` | Updated test file inventory | VERIFIED | All 27 test files listed including all 5 Phase 12 additions; CI command present; no "80%+ coverage" text |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `test_scheduler.py` | `scheduler.job_scheduler.scheduler` | shutdown() in finally blocks | VERIFIED | _force_stop_scheduler() sets scheduler.state = STATE_STOPPED; autouse fixture wraps all tests |
| `test_integration_pipeline.py` | `backend/tests/conftest.py` | synthetic DataFrame fixtures | VERIFIED | sample_buy_df, sample_sfy_df, sample_prime_df referenced at lines 97, 100, 134 |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `test_cashflow_amortization.py` | `backend/cashflow/compute/amortization.py` | direct function imports | VERIFIED | `from cashflow.compute.amortization import level_pay_schedule, bullet_schedule, custom_schedule` |
| `test_cashflow_waterfall.py` | `backend/cashflow/compute/waterfall.py` | direct function imports | VERIFIED | `from cashflow.compute.waterfall import apply_waterfall, run_waterfall` |
| `test_cashflow_prepayment.py` | `backend/cashflow/compute/prepayment.py` | direct function imports | VERIFIED | `from cashflow.compute.prepayment import cpr_to_smm, psa_speed, apply_psa_prepayment, apply_cpr_prepayment` |
| `test_rules_comap.py` | `backend/rules/comap.py` | direct function and constant imports | VERIFIED | `from rules.comap import _prog_in_grid, _found_in_grid, SFY_COMAP_COLS_MIN_FICO, SFY_COMAP_COLS_MIN_FICO2, PRIME_COMAP_COLS_MIN_FICO, PRIME_COMAP_COLS_MIN_FICO2, NOTES_COMAP_COLS_MIN_FICO` |
| `test_orchestration_archive.py` | `backend/orchestration/archive_run.py` | direct function imports | VERIFIED | `from orchestration.archive_run import _is_s3_style_prefix, _collect_input_paths` |

### Plan 03 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `.github/workflows/deploy-test.yml` | deploy job | needs field | VERIFIED | Line 92: `needs: [security-quality-gate, unit-tests]` |
| `.github/workflows/deploy-test.yml` | `backend/requirements.txt` | pip install | VERIFIED | Line 85: `run: pip install -r backend/requirements.txt` (in unit-tests job) |

---

## Requirements Coverage

The TEST-01 through TEST-07 requirement IDs are referenced exclusively in the ROADMAP.md (Phase 12 section) and the individual plan frontmatter. They do not appear in REQUIREMENTS.md (which covers only v1.0 requirements LOCAL-xx through STAGE-xx). This is an orphaned requirements namespace — the TEST-xx IDs are phase-internal tracking identifiers, not formally defined in REQUIREMENTS.md.

| Requirement | Source Plan | Description (inferred from ROADMAP) | Status | Evidence |
|-------------|-------------|--------------------------------------|--------|----------|
| TEST-01 | 12-01-PLAN.md | Fix 10 failing/erroring tests across 4 files | SATISFIED | All 10 targeted tests verified fixed including test_enrichment.py::test_merge_with_loan_types (assertion corrected to 'Platform'). |
| TEST-02 | 12-02-PLAN.md | New coverage: cashflow compute (amortization, waterfall, prepayment) | SATISFIED | 3 test files, 45 tests, all @pytest.mark.unit, all wired to production modules |
| TEST-03 | 12-02-PLAN.md | New coverage: CoMAP rules grid lookup and skip logic | SATISFIED | 13 tests in test_rules_comap.py; absent-from-all-columns skip logic tested |
| TEST-04 | 12-02-PLAN.md | New coverage: orchestration/archive_run path logic | SATISFIED | 14 tests in test_orchestration_archive.py; _is_s3_style_prefix and _collect_input_paths covered |
| TEST-05 | 12-03-PLAN.md | CI unit-tests job runs pytest as blocking gate | SATISFIED | unit-tests job in deploy-test.yml, deploy needs both jobs |
| TEST-06 | 12-03-PLAN.md | pytest-cov wired in CI for coverage reporting | SATISFIED | pytest-cov>=4.0 in requirements.txt; --cov=. --cov-report=term-missing in CI step |
| TEST-07 | 12-03-PLAN.md | tests/README.md updated with full test inventory | SATISFIED | All 27 test files listed; CI command documented; no 80% threshold |

**Orphaned requirements:** None — all 7 TEST-xx IDs are accounted for across the 3 plans.

**Note on REQUIREMENTS.md:** TEST-01 through TEST-07 do not appear in `.planning/REQUIREMENTS.md`. The requirements file covers v1.0 infrastructure requirements only. These TEST-xx IDs exist solely in ROADMAP.md and plan frontmatter as phase-internal tracking. This is not a gap — the phase is self-consistent, but the REQUIREMENTS.md traceability table does not cover Phase 12.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/tests/test_enrichment.py` | 112 | Previously `assert 'type' in result.columns or 'platform' in result.columns` — now fixed to `assert "Platform" in result.columns` | Resolved | Fix applied before Phase 13; confirmed 248 passed 0 failed |

No stub anti-patterns found in the 9 new/modified test files (test_normalize.py, test_scheduler.py, test_integration_pipeline.py, test_rules_purchase_price.py, test_cashflow_amortization.py, test_cashflow_waterfall.py, test_cashflow_prepayment.py, test_rules_comap.py, test_orchestration_archive.py). All tests import real production modules and make substantive assertions. No `return null`, placeholder comments, or empty implementations found.

pytest.ini addopts does not contain --cov (correct per D-18). CI does not contain --cov-fail-under (correct per D-17).

---

## Human Verification Required

### 1. CI Parallel Execution and Deploy Block

**Test:** Push a commit to main (or use workflow_dispatch). Then force a test failure by temporarily breaking a test and push again.
**Expected:** On first push — unit-tests and security-quality-gate run in parallel; deploy job starts only after both pass. On second push — deploy job is blocked when unit-tests fails.
**Why human:** GitHub Actions execution model cannot be verified without actually running the workflow. Local pytest run confirms tests pass, but the parallelism and gating behavior in GitHub Actions requires a live run.

---

## Gaps Summary

No gaps remain. The single gap identified during initial verification (test_enrichment.py::test_merge_with_loan_types failing due to lowercase column assertion) has been resolved. The assertion was corrected to `assert "Platform" in result.columns` (matching actual merge output). Full test suite: 248 passed, 2 skipped, 4 deselected.

Fix confirmed during Phase 13 planning (2026-03-22). The fix was already present in the codebase prior to Phase 13 execution.

---

## Acceptance Notes

### CI Human Verification: Parallel Execution and Deploy Block

The `human_verification` item in frontmatter (CI parallel execution and deploy block behavior) is formally accepted as a pending verification that does not block v1.0 completion.

**What it tests:** Pushing to main triggers the `unit-tests` and `security-quality-gate` jobs in parallel in GitHub Actions; the `deploy` job starts only after both pass; a failing test blocks deploy.

**Why it remains pending:** This behavior can only be verified by an actual push to main (or workflow_dispatch trigger). It cannot be tested locally or simulated. The CI workflow configuration is verified correct in code (`deploy-test.yml` line 92: `needs: [security-quality-gate, unit-tests]`), but runtime behavior requires a live GitHub Actions run.

**Acceptance rationale:** The code-level wiring is verified correct. The first production push to main will serve as the live verification. This is an infrastructure observation, not a code gap. Accepted as non-blocking for v1.0 milestone completion.

---

_Reconciled: 2026-03-22 (Phase 13 plan 13-03)_
_Verifier: Claude (gsd-verifier)_
