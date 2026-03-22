# Phase 12: Unit Testing Build Out - Research

**Researched:** 2026-03-21
**Domain:** Python unit testing — pytest, APScheduler, FastAPI, pandas, GitHub Actions CI
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Fixing failing tests (8 failures + 2 errors)**
- D-01: Fix 3 normalize header-row-skipping failures by updating test assertions to match current normalize behavior (implementation is authoritative).
- D-02: Fix 3 scheduler failures via proper teardown/reset — stop the scheduler after each test that starts it. Keep real APScheduler, no mocks.
- D-03: Fix 2 integration pipeline errors by replacing file-based fixture setup with synthetic in-memory DataFrames from conftest.py.
- D-04: Fix 1 purchase price exception failure by updating assertion to match current output format. Fix in same plan as other failing tests.

**New coverage: cashflow compute**
- D-05: Target only: `cashflow/compute/amortization.py`, `cashflow/compute/waterfall.py`, `cashflow/compute/prepayment.py`. Skip arm_reset, behavioral_model, default_model, generator, run_cashflows.
- D-06: New files: `backend/tests/test_cashflow_amortization.py`, `test_cashflow_waterfall.py`, `test_cashflow_prepayment.py`. Synthetic DataFrame inputs only, no real loan data files.
- D-07: Tests must be pure unit tests — no DB, no file I/O, no network. Mark with `@pytest.mark.unit`.

**New coverage: rules/comap.py**
- D-08: Add `backend/tests/test_rules_comap.py`. Cover: grid lookup by FICO band, oct25_cutoff skip logic, program-absent-from-all-columns skip (not flagged), SFY vs PRIME routing.
- D-09: Use synthetic comap grid DataFrames inline in the test file, not from conftest. The conftest comap fixture is too minimal for edge-case coverage.

**New coverage: orchestration/archive_run.py**
- D-10: Add `backend/tests/test_orchestration_archive.py`. Cover: date derivation logic, file-movement path construction. Use `temp_dir` fixture from conftest.py.
- D-11: Skip `s3_input_sync.py` — heavy S3 mocking, low ROI.

**CI test gate**
- D-12: Add `unit-tests` job to `.github/workflows/deploy-test.yml`. Runs in parallel with `security-quality-gate` (not sequentially after it).
- D-13: Update `deploy` job's `needs:` field to include both `security-quality-gate` AND `unit-tests`.
- D-14: CI command: `pytest -m "not integration" --tb=short -q`
- D-15: Python setup in CI: `actions/setup-python@v5` with Python 3.12. Install: `pip install -r backend/requirements.txt`.

**Coverage reporting**
- D-16: Add `pytest-cov` to `backend/requirements.txt` (not currently present — only pytest==8.3.3 and pytest-asyncio==0.24.0 are there).
- D-17: No `--cov-fail-under` threshold — report only. CI command becomes: `pytest -m "not integration" --tb=short -q --cov=backend --cov-report=term-missing`.
- D-18: Do NOT add coverage to local `pytest.ini` addopts — keep local run fast.

**Documentation**
- D-19: Update `backend/tests/README.md` — add all test files added since Phase 7 plus new Phase 12 files.

### Claude's Discretion
- Test fixture design for cashflow modules (shared conftest fixtures vs inline fixtures)
- Number of test cases per cashflow function (edge cases, boundary values)
- Whether to apply `@pytest.mark.unit` decorator to existing tests or only new ones
- Exact CI job name ("unit-tests" or "pytest" or "test")

### Deferred Ideas (OUT OF SCOPE)
- Hard coverage threshold (`--cov-fail-under`) — deferred until baseline percentage known
- Tests for arm_reset, behavioral_model, default_model, generator, run_cashflows
- s3_input_sync.py tests
- Frontend test suite (Vitest/React Testing Library)
- Test parallelization (pytest-xdist)
</user_constraints>

---

## Summary

Phase 12 is a test quality phase with three goals: (1) repair 10 currently-failing/erroring tests, (2) add coverage for the three untested cashflow compute modules plus comap and archive_run, and (3) wire pytest as a blocking CI gate alongside the existing security-quality-gate job.

The failing tests divide neatly into four root causes: normalize assertions expect old behavior, scheduler tests leak state across test functions, integration pipeline tests depend on real files, and purchase price assertions check the wrong key name. None of the failures require production code changes — all fixes are in the test code itself.

The new test coverage targets are well-isolated pure-Python modules with no DB or file I/O dependencies: `amortization.py`, `waterfall.py`, and `prepayment.py` are entirely self-contained mathematical functions. `comap.py` operates on pandas DataFrames and requires careful grid construction to exercise the FICO-band routing, oct25_cutoff, and skip-not-flag logic. `archive_run.py` is the one module that touches the filesystem and storage backends — `_is_s3_style_prefix` and `_collect_input_paths` can be tested in isolation using the existing `temp_dir` fixture.

**Primary recommendation:** Fix all failing tests in one plan, add cashflow/comap/archive coverage in a second plan, then wire CI in a third plan (or combine CI + docs into one plan).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.3.3 | Test runner, fixtures, markers | Already in requirements.txt |
| pytest-asyncio | 0.24.0 | async test support (scheduler tests) | Already in requirements.txt |
| pytest-cov | latest (add) | Coverage reporting | Standard pytest coverage plugin |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | project version | Synthetic DataFrame construction | All data-layer tests |
| unittest.mock | stdlib | Patching external dependencies | Storage backend mocking in archive tests |

**Installation — pytest-cov addition:**
```bash
pip install pytest-cov
```

Add to `backend/requirements.txt`:
```
pytest-cov==6.0.0
```

**Version verification:** `pytest-cov` current stable is 6.x (as of early 2026). Confirm with `pip index versions pytest-cov` before pinning.

---

## Architecture Patterns

### Recommended Project Structure (test additions)

```
backend/tests/
├── conftest.py                       # Shared fixtures (DO NOT MODIFY unless adding fixtures)
├── test_cashflow_amortization.py     # NEW - Phase 12
├── test_cashflow_waterfall.py        # NEW - Phase 12
├── test_cashflow_prepayment.py       # NEW - Phase 12
├── test_rules_comap.py               # NEW - Phase 12
├── test_orchestration_archive.py     # NEW - Phase 12
├── test_normalize.py                 # FIX - update 3 assertions
├── test_scheduler.py                 # FIX - add teardown/shutdown
├── test_integration_pipeline.py      # FIX - replace file fixtures with DataFrames
└── test_rules_purchase_price.py      # FIX - update assertion key name
```

### Pattern 1: Inline Synthetic Grid DataFrames (CoMAP tests)

**What:** Build minimal grid DataFrames directly in the test function or as module-level fixtures. Do not share from conftest — conftest's `sample_comap_df` uses only 5 columns and doesn't cover multiple FICO band mappings.

**When to use:** Any test that needs a specific CoMAP grid shape for a given assertion. Each test gets the exact grid needed.

**Example:**
```python
@pytest.mark.unit
def test_prog_in_grid_present():
    grid = pd.DataFrame({
        '660-699': ['Prog A', 'Prog B'],
        '700-739': ['Prog C', None],
    })
    assert _prog_in_grid('Prog A', grid, {'660-699': 660, '700-739': 700})

@pytest.mark.unit
def test_prog_in_grid_absent_is_skipped():
    """Programs absent from ALL grid columns must be skipped (not flagged)."""
    grid = pd.DataFrame({
        '660-699': ['Other Prog'],
        '700-739': [None],
    })
    assert not _prog_in_grid('Unknown Prog', grid, {'660-699': 660, '700-739': 700})
```

### Pattern 2: Pure Function Unit Tests (cashflow compute)

**What:** Call functions directly with scalar or small list inputs. No fixtures required. One class per source module function.

**When to use:** All cashflow compute tests — functions are pure Python (no side effects, no DB, no I/O).

**Example:**
```python
@pytest.mark.unit
class TestLevelPaySchedule:
    def test_final_balance_is_zero(self):
        schedule = level_pay_schedule(10000, 0.05, 12)
        assert schedule[-1]['remaining_balance'] == 0.0

    def test_period_count(self):
        schedule = level_pay_schedule(10000, 0.05, 12)
        assert len(schedule) == 12

    def test_zero_rate(self):
        schedule = level_pay_schedule(12000, 0.0, 12)
        assert schedule[0]['interest'] == 0.0
        assert pytest.approx(schedule[0]['principal'], rel=1e-6) == 1000.0

    def test_negative_principal_raises(self):
        with pytest.raises(ValueError, match="Principal must be positive"):
            level_pay_schedule(-1000, 0.05, 12)
```

### Pattern 3: Scheduler Teardown Isolation

**What:** Each test that calls `scheduler.start()` must call `scheduler.shutdown()` in a `finally` block. Tests that call `schedule_daily_runs()` (which adds jobs to a running scheduler) must also `scheduler.remove_all_jobs()` on teardown or use `scheduler.shutdown()`.

**When to use:** `TestScheduleDailyRuns::test_schedule_daily_runs_with_teams` and both `TestSchedulerIntegration` tests.

**Fix for `test_schedule_daily_runs_with_teams`:**
```python
def test_schedule_daily_runs_with_teams(self, test_db_session, sample_sales_team):
    with patch('scheduler.job_scheduler.settings') as mock_settings:
        mock_settings.ENABLE_SCHEDULER = True
        mock_settings.DAILY_RUN_TIME = "02:00"
        scheduler.remove_all_jobs()
        try:
            schedule_daily_runs()
            jobs = scheduler.get_jobs()
            assert len(jobs) > 0
            job_ids = [job.id for job in jobs]
            assert f"daily_pipeline_{sample_sales_team.id}" in job_ids
        finally:
            scheduler.remove_all_jobs()
```

**Fix for `TestSchedulerIntegration`:** The `finally: scheduler.shutdown()` is already present in `test_scheduler_job_management`. The isolation problem is that a prior test leaves the scheduler started without shutting down. Add `scheduler.shutdown()` teardown or use a pytest fixture with yield.

### Pattern 4: In-Memory DataFrame Pipeline Tests (integration_pipeline fix)

**What:** Replace `sample_input_dir` fixture (file-based) with direct DataFrame injection into `RunContext`. The current failure is that `test_pipeline_execution` uses `sample_input_dir` which creates real files that the real pipeline loader cannot find in the right shape.

**When to use:** D-03 fix — `TestPipelineExecution::test_pipeline_execution` and `test_pipeline_with_exceptions`.

**Approach (per D-03):** Replace file-based setup with conftest's `sample_buy_df`, `sample_sfy_df`, `sample_prime_df`. Patch the file discovery/loading layer to return these DataFrames. The test verifies orchestration logic, not file I/O.

### Pattern 5: Archive Tests Using `temp_dir`

**What:** For `archive_run.py` tests, use conftest `temp_dir` to create realistic local directory structures. The `_is_s3_style_prefix` and `_collect_input_paths` helpers are testable in isolation without a real storage backend.

**Example:**
```python
@pytest.mark.unit
def test_is_s3_style_prefix_local_path_rejected():
    assert not _is_s3_style_prefix("C:/Users/data")

@pytest.mark.unit
def test_is_s3_style_prefix_s3_key_accepted():
    assert _is_s3_style_prefix("runs/run_abc123/output")

@pytest.mark.unit
def test_collect_input_paths_reference_files(temp_dir):
    files_req = temp_dir / "files_required"
    files_req.mkdir()
    (files_req / "MASTER_SHEET.xlsx").write_bytes(b"")
    paths = _collect_input_paths(str(temp_dir), pdate=None)
    names = [p.name for p in paths]
    assert "MASTER_SHEET.xlsx" in names
```

### Anti-Patterns to Avoid

- **Mutating shared fixtures:** Never modify `sample_buy_df` in-place. Always `.copy()` or create inline DataFrames.
- **Leaving scheduler running:** Any test that calls `scheduler.start()` must shut it down in a `finally` block or pytest teardown.
- **Using conftest comap fixture for edge cases:** `sample_comap_df` is too sparse — it doesn't cover all FICO bands or skip-logic scenarios. Build inline grids.
- **Adding `--cov` to pytest.ini addopts:** Coverage flags belong in CI command only (D-18).
- **Integration marker on cashflow tests:** Cashflow compute functions are pure Python — mark `@pytest.mark.unit`, not integration.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coverage reporting | Custom coverage script | `pytest-cov` plugin | Standard, integrates with pytest, CI-native |
| Scheduler isolation | Custom scheduler mock | Real scheduler + `shutdown()` in finally | D-02 explicitly requires real APScheduler |
| DB isolation | Custom teardown | conftest rollback transaction pattern | Already established in Phase 7 |
| Temp filesystem | `os.makedirs` + manual cleanup | conftest `temp_dir` fixture | Auto-cleaned, already available |

**Key insight:** This phase is almost entirely about fixing test code, not production code. The only production artifact is `backend/requirements.txt` (adding pytest-cov) and `.github/workflows/deploy-test.yml` (adding unit-tests job).

---

## Common Pitfalls

### Pitfall 1: Normalize Assertion Shape

**What goes wrong:** Tests in `test_normalize.py` assert `len(result) == 1` for a 5-row input DataFrame, but `normalize_sfy_df` skips rows only when `len(df) > 4`. With 5 rows it skips the first 4, leaving 1 row — but then the column assignment uses that row as the new header, leaving 0 data rows. The behavior: with a 5-row input where row index 4 is the "data" row, after `df.iloc[4:]` we get 1 row; that becomes the column header; `df[1:]` = empty. The test with `['A': ..., 'B': ...]` having 5 values produces `len(result) == 0`, not 1.

**Why it happens:** The test was written expecting a different skip-row count than the implementation uses.

**How to avoid:** Run `normalize_sfy_df` against the exact fixture DataFrame and print/assert the actual result length before writing assertions. Correct assertion: `len(result) == 0` or add a 6th row of data.

**Warning signs:** `AssertionError: assert 0 == 1` on the normalize tests.

### Pitfall 2: Scheduler State Bleed Between Tests

**What goes wrong:** `TestSchedulerIntegration::test_scheduler_startup` starts the scheduler but then calls `scheduler.shutdown()`. If any preceding test already started the scheduler and did not shut it down, `scheduler.start()` raises `SchedulerAlreadyRunningError`.

**Why it happens:** APScheduler's module-level `scheduler` object is shared across all tests in the same process. The scheduler object from `from scheduler.job_scheduler import scheduler` is a singleton.

**How to avoid:** Every test that calls `scheduler.start()` must guarantee `scheduler.shutdown()` in a `finally` block. Check `if scheduler.running: scheduler.shutdown()` at the start of each test that needs to control scheduler state.

**Warning signs:** `apscheduler.schedulers.base.SchedulerAlreadyRunningError` in test output.

### Pitfall 3: Purchase Price Exception Key Name

**What goes wrong:** Test asserts `exceptions[0]['message']` contains `'SFC_1001'`, but the actual implementation uses `exceptions[0]['seller_loan_number']` — not a `message` field. The test for `exception_type` and `severity` pass but the `'SFC_1001' in exceptions[0]['message']` check fails with `KeyError`.

**Why it happens:** The test was written before the implementation settled on `seller_loan_number` as the key (the `message` field is a formatted string that contains the loan number, but the test may have been checking a non-existent `loan_id` or `loan_number` key).

**How to avoid:** Read `rules/purchase_price.py` `get_purchase_price_exceptions` return dict structure directly. Correct test: `assert exceptions[0]['seller_loan_number'] == 'SFC_1001'` or `assert 'SFC_1001' in exceptions[0]['message']` (message does contain the loan number via `seller_loan_number` key — actually the exception dict has a `message` field, check the f-string: it uses `row.get('SELLER Loan #')` which maps to the value 'SFC_1001' in the message string).

**Resolution:** The test assertion `assert 'SFC_1001' in exceptions[0]['message']` is correct — the `message` key exists and contains the loan number. The actual failure is likely `exceptions[0]['exception_type'] == 'purchase_price'` is correct, but `exceptions[0]['severity'] == 'error'` is correct too. Investigate actual assertion failure message before fixing.

### Pitfall 4: CoMAP Grid Column Presence

**What goes wrong:** `_found_in_grid` and `_prog_in_grid` silently return `False` if the FICO band column names in `fico_col_mins` don't match any columns in the test grid.

**Why it happens:** `avail = [c for c in fico_col_mins if c in grid.columns]` — if test grid uses `'660-699'` but fico_col_mins uses `'660-719'`, `avail` is empty and the function always returns `False`.

**How to avoid:** Always construct test grids whose column names exactly match the `fico_col_mins` dict keys being tested (e.g., `SFY_COMAP_COLS_MIN_FICO`, `PRIME_COMAP_COLS_MIN_FICO2`). Import the dict constants from `rules.comap` into the test file.

**Warning signs:** All comap tests return "not found" regardless of FICO/program values.

### Pitfall 5: Working Directory for `pytest` CI

**What goes wrong:** `pytest -m "not integration"` with `testpaths = tests` in `pytest.ini` needs to be run from the `backend/` directory. Running from repo root fails.

**Why it happens:** `pytest.ini` is in `backend/`, and `testpaths = tests` is relative to it. CI jobs must `cd backend` or use `working-directory: backend`.

**How to avoid:** CI job must include `working-directory: backend` on all pytest-related steps.

---

## Code Examples

Verified patterns from source code inspection:

### Normalize Fix: Correct Header-Row-Skip Assertion

The normalize implementation skips `df.iloc[4:]` (rows 0–3 are skipped), then uses row 0 of the slice as headers, then drops that row. So a 5-row DataFrame with data in row index 4 produces 0 data rows. A 6-row DataFrame with data in rows 4 and 5 produces 1 data row.

```python
# Source: backend/transforms/normalize.py lines 43-46
# Fix: add a 6th row so there is 1 data row after header promotion
def test_header_row_skipping(self):
    df = pd.DataFrame({
        'A': ['', '', '', 'Header1', 'Header1', 'Data1'],
        'B': ['', '', '', 'Header2', 'Header2', 'Data2'],
    })
    result = normalize_sfy_df(df)
    assert len(result) == 1
    assert 'Header1' in result.columns
```

### Purchase Price Exception: Actual Dict Structure

```python
# Source: backend/rules/purchase_price.py lines 28-35
# Exception dict keys: seller_loan_number, exception_type, exception_category,
#                      severity, message, loan_data
# The 'message' field contains the loan number but not as a separate key.
# Fix the test:
def test_exception_generation(self):
    ...
    assert exceptions[0]['exception_type'] == 'purchase_price'
    assert exceptions[0]['severity'] == 'error'
    assert exceptions[0]['seller_loan_number'] == 'SFC_1001'  # use correct key
```

### Cashflow: Level Pay Boundary Values

```python
# Source: backend/cashflow/compute/amortization.py
@pytest.mark.unit
class TestLevelPaySchedule:
    def test_final_balance_is_zero(self):
        schedule = level_pay_schedule(10000, 0.05, 12)
        assert schedule[-1]['remaining_balance'] == 0.0

    def test_constant_payment(self):
        schedule = level_pay_schedule(10000, 0.05, 12)
        payments = [row['payment'] for row in schedule]
        assert max(payments) - min(payments) < 1e-9  # all equal

    def test_zero_rate_equal_principal(self):
        schedule = level_pay_schedule(12000, 0.0, 12)
        for row in schedule:
            assert row['interest'] == 0.0
            assert pytest.approx(row['principal'], rel=1e-6) == 1000.0
```

### Waterfall: Senior Tranche Paid First

```python
# Source: backend/cashflow/compute/waterfall.py
@pytest.mark.unit
def test_senior_tranche_paid_before_junior():
    cashflows = [{'period': 1, 'interest': 3.0, 'principal': 5.0}]
    tranches = [
        {'tranche_id': 'A', 'priority': 1, 'notional': 80.0, 'coupon': 0.04},
        {'tranche_id': 'B', 'priority': 2, 'notional': 20.0, 'coupon': 0.08},
    ]
    result = apply_waterfall(cashflows, tranches)
    # Senior tranche receives all available interest first
    assert result['A'][0]['interest'] <= 3.0
    assert result['A'][0]['interest'] >= result['B'][0]['interest']
```

### Prepayment: CPR to SMM Conversion

```python
# Source: backend/cashflow/compute/prepayment.py
@pytest.mark.unit
def test_cpr_to_smm_zero_cpr():
    assert cpr_to_smm(0.0) == 0.0

@pytest.mark.unit
def test_cpr_to_smm_full_cpr():
    # 100% CPR means everyone prepays: SMM should be 1.0
    assert pytest.approx(cpr_to_smm(1.0), abs=1e-9) == 1.0

@pytest.mark.unit
def test_psa_month_30_plateau():
    # Month 30+: CPR should be at 6% (PSA 100%)
    assert psa_speed(30, 100.0) == pytest.approx(0.06)
    assert psa_speed(60, 100.0) == pytest.approx(0.06)
```

### CoMAP: Skip Logic (Program Absent from All Columns)

```python
# Source: backend/rules/comap.py lines 54-61
@pytest.mark.unit
def test_prog_absent_from_grid_is_skipped():
    """Program not in any grid column -> _prog_in_grid returns False -> loan skipped."""
    grid = pd.DataFrame({'660-699': ['Known Prog'], '700-739': [None]})
    fico_mins = {'660-699': 660, '700-739': 700}
    assert not _prog_in_grid('Unknown Prog', grid, fico_mins)
```

### Archive: _is_s3_style_prefix

```python
# Source: backend/orchestration/archive_run.py lines 180-187
@pytest.mark.unit
def test_is_s3_style_prefix_rejects_absolute_windows_path():
    assert not _is_s3_style_prefix("C:/Users/data/output")

@pytest.mark.unit
def test_is_s3_style_prefix_rejects_absolute_unix_path():
    assert not _is_s3_style_prefix("/home/user/data")

@pytest.mark.unit
def test_is_s3_style_prefix_accepts_s3_key():
    assert _is_s3_style_prefix("runs/run_abc/output")

@pytest.mark.unit
def test_is_s3_style_prefix_rejects_empty():
    assert not _is_s3_style_prefix("")
    assert not _is_s3_style_prefix(None)
```

### CI: unit-tests job structure

```yaml
# .github/workflows/deploy-test.yml addition
unit-tests:
  runs-on: ubuntu-latest
  permissions:
    contents: read

  steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: Install dependencies
      run: pip install -r backend/requirements.txt

    - name: Run unit tests with coverage
      working-directory: backend
      run: pytest -m "not integration" --tb=short -q --cov=backend --cov-report=term-missing

# deploy job needs update:
deploy:
  needs: [security-quality-gate, unit-tests]
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.3 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && pytest -m "not integration" --tb=short -q` |
| Full suite command | `cd backend && pytest -m "not integration" --tb=short -q --cov=backend --cov-report=term-missing` |

### Phase Requirements → Test Map

Phase 12 has no formal requirement IDs (mapped as TBD in REQUIREMENTS.md). The phase is self-referential — its deliverables ARE tests. The table below maps the phase's CONTEXT.md decisions to verification.

| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|--------------|
| D-01/D-02/D-03/D-04 | All currently-failing 10 tests now pass | unit | `pytest tests/test_normalize.py tests/test_scheduler.py tests/test_integration_pipeline.py tests/test_rules_purchase_price.py -v` | ✅ (files exist, need fixes) |
| D-05/D-06/D-07 | Cashflow compute tests exist and pass | unit | `pytest tests/test_cashflow_amortization.py tests/test_cashflow_waterfall.py tests/test_cashflow_prepayment.py -v` | ❌ Wave 0 |
| D-08/D-09 | CoMAP tests cover all 4 scenarios | unit | `pytest tests/test_rules_comap.py -v` | ❌ Wave 0 |
| D-10 | Archive tests cover path logic | unit | `pytest tests/test_orchestration_archive.py -v` | ❌ Wave 0 |
| D-12/D-13 | CI unit-tests job exists and blocks deploy | CI/manual | CI run on push to main | ❌ Wave 0 |
| D-16 | pytest-cov in requirements.txt | smoke | `pip install -r backend/requirements.txt && pytest --co` | ❌ Wave 0 |
| D-19 | tests/README.md lists all test files | manual | Review README.md | Partial (stale) |

### Sampling Rate
- **Per task commit:** `cd backend && pytest -m "not integration" --tb=short -q`
- **Per wave merge:** `cd backend && pytest -m "not integration" --tb=short -q --cov=backend --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_cashflow_amortization.py` — covers D-05/D-06/D-07 amortization
- [ ] `backend/tests/test_cashflow_waterfall.py` — covers D-05/D-06/D-07 waterfall
- [ ] `backend/tests/test_cashflow_prepayment.py` — covers D-05/D-06/D-07 prepayment
- [ ] `backend/tests/test_rules_comap.py` — covers D-08/D-09
- [ ] `backend/tests/test_orchestration_archive.py` — covers D-10
- [ ] `pytest-cov` added to `backend/requirements.txt` — covers D-16
- [ ] `unit-tests` job added to `.github/workflows/deploy-test.yml` — covers D-12/D-13

---

## Existing Test Inventory (current state)

Files currently in `backend/tests/` that are NOT in the README.md (README is stale from Phase 7):

| File | Status | Phase Added |
|------|--------|-------------|
| test_api_files.py | Passing (assumed) | Phase 7 |
| test_audit_log.py | Passing (assumed) | Phase 7 |
| test_auth_routes.py | Passing (assumed) | Phase 7 |
| test_auth_security.py | Passing (assumed) | Phase 7 |
| test_auth_validators.py | Passing (assumed) | Phase 7 |
| test_eligibility_complete.py | Passing (assumed) | Phase 7 |
| test_final_funding_jobs.py | Passing (assumed) | Phase 7 |
| test_final_funding_runner.py | Passing (assumed) | Phase 7 |
| test_holiday_calendar.py | Passing (assumed) | Phase 7 |
| test_rules_eligibility.py | Passing (assumed) | Phase 7 |
| test_seed_admin.py | Passing (assumed) | Phase 7 |
| test_settings_guard.py | Passing (assumed) | Phase 7 |
| test_storage_local.py | Passing (assumed) | Phase 7 |

Failing/erroring files requiring fixes:
| File | Failures | Root Cause |
|------|----------|------------|
| test_normalize.py | 3 failures | Assertions expect old header-skip behavior |
| test_scheduler.py | 3 failures | Scheduler state leaks between tests |
| test_integration_pipeline.py | 2 errors | File fixtures not found at runtime |
| test_rules_purchase_price.py | 1 failure | Wrong dict key in assertion |

---

## Open Questions

1. **Actual failure messages for test_normalize.py**
   - What we know: 3 tests fail in `TestNormalizeSfyDf` and `TestNormalizePrimeDf`; normalize implementation uses `df.iloc[4:]` skip.
   - What's unclear: Whether the 5-row test input produces 0 or 1 data rows (the column-promotion step). Analyzed above as 0 rows — the test assertion `assert len(result) == 1` fails.
   - Recommendation: Implementer should run `pytest tests/test_normalize.py -v --no-header` to capture exact messages before editing.

2. **Actual failure message for test_rules_purchase_price.py**
   - What we know: `get_purchase_price_exceptions` returns a dict with key `seller_loan_number` (not `loan_number`). The test assertion was `assert 'SFC_1001' in exceptions[0]['message']`.
   - What's unclear: Whether the `message` field actually contains the string 'SFC_1001'. Looking at the implementation, `message` uses `row.get('SELLER Loan #', 'UNKNOWN')` which would be the string value 'SFC_1001'. The assertion may actually be correct — the real failure may be a different assertion line.
   - Recommendation: Run `pytest tests/test_rules_purchase_price.py::TestGetPurchasePriceExceptions::test_exception_generation -v -s` to see the exact assertion error.

3. **pytest-cov exact version to pin**
   - What we know: pytest-cov 6.x is current stable.
   - What's unclear: Minimum compatible version with pytest 8.3.3.
   - Recommendation: Use `pytest-cov>=4.0` without hard pin, or verify with `pip install "pytest-cov" && pip show pytest-cov`.

---

## Sources

### Primary (HIGH confidence)
- Direct source code inspection: `backend/transforms/normalize.py` — exact skip logic verified
- Direct source code inspection: `backend/rules/purchase_price.py` — exact exception dict structure verified
- Direct source code inspection: `backend/cashflow/compute/amortization.py`, `waterfall.py`, `prepayment.py` — all function signatures and docstrings verified
- Direct source code inspection: `backend/rules/comap.py` — FICO band constants, `_prog_in_grid`, `_found_in_grid` verified
- Direct source code inspection: `backend/orchestration/archive_run.py` — `_is_s3_style_prefix`, `_collect_input_paths` verified
- Direct source code inspection: `backend/pytest.ini` — markers, addopts, testpaths verified
- Direct source code inspection: `backend/tests/conftest.py` — all fixtures verified
- Direct source code inspection: `.github/workflows/deploy-test.yml` — existing CI structure verified
- Direct source code inspection: `backend/requirements.txt` — pytest==8.3.3, pytest-asyncio==0.24.0 confirmed; pytest-cov absent confirmed

### Secondary (MEDIUM confidence)
- APScheduler behavior (scheduler singleton, `SchedulerAlreadyRunningError`) — inferred from test code structure and APScheduler documentation patterns

### Tertiary (LOW confidence)
- pytest-cov current version (6.x) — from general knowledge; confirm with `pip index versions pytest-cov`

---

## Metadata

**Confidence breakdown:**
- Failing test root causes: HIGH — normalized implementation read directly; scheduler pattern clear from code
- Cashflow function interfaces: HIGH — all three modules read directly; pure functions with no dependencies
- CoMAP test design: HIGH — FICO band constants and skip logic read directly from comap.py
- Archive test design: HIGH — `_is_s3_style_prefix` and `_collect_input_paths` read directly
- CI workflow changes: HIGH — existing deploy-test.yml structure verified; pattern is straightforward YAML addition
- pytest-cov version: MEDIUM — general knowledge; verify before pinning

**Research date:** 2026-03-21
**Valid until:** 2026-04-20 (stable libraries; pytest-cov version may change but interface is stable)
