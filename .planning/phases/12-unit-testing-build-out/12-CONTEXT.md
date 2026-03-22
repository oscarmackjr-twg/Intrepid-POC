# Phase 12: Unit Testing Build Out - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the 8 currently-failing tests to get the suite fully green, then extend coverage into the cashflow compute engine (amortization, waterfall, prepayment), rules/comap.py, and orchestration/archive_run.py. Wire pytest into the CI deploy pipeline as a blocking gate (unit tests only, parallel with security-quality-gate). Add pytest-cov coverage reporting (report only, no hard threshold). Update tests/README.md to reflect the full test file inventory.

</domain>

<decisions>
## Implementation Decisions

### Fixing failing tests (8 failures + 2 errors)

- **D-01:** The 3 normalize header-row-skipping failures (`TestNormalizeSfyDf::test_header_row_skipping`, `TestNormalizeSfyDf::test_tu144_column_standardization`, `TestNormalizePrimeDf::test_header_row_skipping`) — fix the test assertions to match current normalize behavior, not the other way around. The normalize implementation is considered correct.
- **D-02:** The 3 scheduler failures (`TestScheduleDailyRuns::test_schedule_daily_runs_with_teams`, `TestSchedulerIntegration::test_scheduler_startup`, `TestSchedulerIntegration::test_scheduler_job_management`) — fix via proper teardown/reset between tests: stop the scheduler after each test that starts it. Maintain real scheduler (not mocked) — isolation issue only.
- **D-03:** The 2 integration pipeline errors (`TestPipelineExecution::test_pipeline_execution`, `TestPipelineExecution::test_pipeline_with_exceptions`) — fix by replacing file-based fixture setup with synthetic in-memory DataFrames from conftest.py. No external files should be required.
- **D-04:** The 1 purchase price exception failure (`TestGetPurchasePriceExceptions::test_exception_generation`) — fix assertion to match current exception output format. Fix in the same plan as the other failing tests.

### New coverage: cashflow compute

- **D-05:** Target the 3 most critical cashflow modules: `cashflow/compute/amortization.py`, `cashflow/compute/waterfall.py`, `cashflow/compute/prepayment.py`. Skip: arm_reset, behavioral_model, default_model, generator, run_cashflows — not in scope for Phase 12.
- **D-06:** New test file: `backend/tests/test_cashflow_amortization.py`, `test_cashflow_waterfall.py`, `test_cashflow_prepayment.py`. Use synthetic DataFrame inputs, no real loan data files.
- **D-07:** Tests must be pure unit tests — no DB, no file I/O, no network. Mark with `@pytest.mark.unit`.

### New coverage: rules/comap.py

- **D-08:** Add `backend/tests/test_rules_comap.py`. Cover: grid lookup by FICO band, oct25_cutoff skip logic, program-absent-from-all-columns skip (not flagged), SFY vs PRIME routing.
- **D-09:** Use synthetic comap grid DataFrames (in-line in the test file, not from conftest). CoMAP fixture in conftest.py is too minimal for edge-case coverage.

### New coverage: orchestration/archive_run.py

- **D-10:** Add `backend/tests/test_orchestration_archive.py`. Cover: date derivation logic, file-movement path construction. Use `temp_dir` fixture from conftest.py for filesystem operations.
- **D-11:** Skip `s3_input_sync.py` — pure S3 I/O, heavy mocking required, low ROI.

### CI test gate

- **D-12:** Add a `unit-tests` job to `.github/workflows/deploy-test.yml`. It runs in parallel with `security-quality-gate` (not sequentially after it).
- **D-13:** The `deploy` job's `needs:` field must be updated to include both `security-quality-gate` AND `unit-tests`, so a test failure blocks deploy.
- **D-14:** CI command: `pytest -m "not integration" --tb=short -q` — matches local default behavior (integration excluded).
- **D-15:** Python setup in CI job: `actions/setup-python@v5` with Python 3.12. Install: `pip install -r backend/requirements.txt` (pytest is already in requirements).

### Coverage reporting

- **D-16:** Add `pytest-cov` to `backend/requirements.txt` (if not already present). CI command becomes: `pytest -m "not integration" --tb=short -q --cov=backend --cov-report=term-missing`.
- **D-17:** No `--cov-fail-under` threshold — report only. Coverage percentage will be visible in CI logs as a baseline.
- **D-18:** Do NOT add coverage to local `pytest.ini` addopts — keep local run fast, coverage is CI-only.

### Documentation

- **D-19:** Update `backend/tests/README.md` — add all test files added since Phase 7 (test_final_funding_jobs.py, test_final_funding_runner.py, test_settings_guard.py, test_seed_admin.py, test_storage_local.py, test_api_files.py, test_audit_log.py, test_auth_security.py, test_auth_routes.py, test_rules_eligibility.py, test_eligibility_complete.py) plus the new Phase 12 files.

### Claude's Discretion
- Test fixture design for cashflow modules (whether to use shared conftest fixtures or inline fixtures)
- Number of test cases per cashflow function (edge cases, boundary values)
- Whether to add the `@pytest.mark.unit` decorator to existing tests or only new ones
- Exact CI job name ("unit-tests" or "pytest" or "test")

</decisions>

<specifics>
## Specific Ideas

- The scheduler fix is a teardown/isolation issue — not a mock replacement. Keep real APScheduler in tests.
- The normalize fix updates test expectations, not production code — the implementation is authoritative.
- cashflow compute modules are the biggest untested gap in the codebase — amortization/waterfall/prepayment are the revenue-critical ones to target first.
- Coverage reporting in CI (D-16/D-17) is for visibility only — no red lights on threshold yet.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing test infrastructure
- `backend/tests/conftest.py` — All shared fixtures (test_db_session, sample_buy_df, temp_dir, client, auth_headers_*); new tests should reuse these rather than duplicate
- `backend/tests/README.md` — Current test documentation (to be updated by this phase)
- `backend/pytest.ini` — Test configuration: testpaths, markers, addopts (integration excluded by default)

### Modules to fix (failing tests)
- `backend/tests/test_normalize.py` — 3 failing tests; assertions need updating to match current normalize behavior
- `backend/tests/test_scheduler.py` — 3 failing tests; teardown isolation needed
- `backend/tests/test_integration_pipeline.py` — 2 errors; file fixtures → synthetic DataFrames
- `backend/tests/test_rules_purchase_price.py` — 1 failure; assertion format update

### Modules to add coverage for
- `backend/cashflow/compute/amortization.py` — amortization engine (target for test_cashflow_amortization.py)
- `backend/cashflow/compute/waterfall.py` — waterfall model (target for test_cashflow_waterfall.py)
- `backend/cashflow/compute/prepayment.py` — prepayment model (target for test_cashflow_prepayment.py)
- `backend/rules/comap.py` — CoMAP grid rules with oct25_cutoff and skip logic (target for test_rules_comap.py)
- `backend/orchestration/archive_run.py` — archive logic (target for test_orchestration_archive.py)

### CI pipeline
- `.github/workflows/deploy-test.yml` — Current pipeline: security-quality-gate + deploy. Phase 12 adds unit-tests job in parallel with security-quality-gate; deploy needs both.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `conftest.py::temp_dir` — Used by test_orchestration_archive.py for filesystem tests
- `conftest.py::sample_buy_df`, `sample_sfy_df`, `sample_prime_df` — Reuse in fixed integration pipeline tests
- `conftest.py::test_db_session` with rollback isolation — Pattern to replicate if cashflow tests need DB

### Established Patterns
- Transaction-based rollback isolation in conftest.py (from Phase 7) — all DB tests use function-scoped session with rollback; new tests must follow this
- Self-contained per-function DB engines in test files (from Phase 7) — used where conftest session-scope causes UNIQUE constraint issues
- `@pytest.mark.unit` / `@pytest.mark.integration` markers defined in pytest.ini — use `not integration` for CI gate
- Import pattern: `from api.main import app` (not `from main import app`) for test client setup

### Integration Points
- `deploy-test.yml` `needs:` field on the `deploy` job — must add `unit-tests` alongside `security-quality-gate`
- `backend/requirements.txt` — pytest already present; add `pytest-cov` if not present

</code_context>

<deferred>
## Deferred Ideas

- Hard coverage threshold (--cov-fail-under) — deferred until we have a baseline percentage from the reporting-only run
- Tests for arm_reset, behavioral_model, default_model, generator, run_cashflows — deferred to a future testing phase
- s3_input_sync.py tests — deferred; heavy S3 mocking required
- Frontend test suite (Vitest/React Testing Library) — out of scope for Phase 12 (backend only)
- Test parallelization (pytest-xdist) — not needed at current test count

</deferred>

---

*Phase: 12-unit-testing-build-out*
*Context gathered: 2026-03-21*
