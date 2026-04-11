---
phase: snf-fix-code-review-warnings-wr-01-wr-02-wr-03-wr-04
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/api/re_routes.py
  - backend/tests/test_re_api.py
autonomous: true
requirements:
  - WR-01
  - WR-02
  - WR-03
  - WR-04

must_haves:
  truths:
    - "net_loss_rate includes both principal and interest shortfalls"
    - "CPR returns None for principal shortfall periods, not Decimal('0')"
    - "Delinquency waterfall treats 90+ DPD as default (industry standard)"
    - "page_size is clamped to 200 — callers cannot pull full dataset in one call"
  artifacts:
    - path: "backend/api/re_routes.py"
      provides: "All four WR fixes applied"
    - path: "backend/tests/test_re_api.py"
      provides: "Tests covering WR-02 (cpr None), WR-03 (90 DPD default), WR-04 (page_size cap)"
  key_links:
    - from: "re_routes.py line ~700"
      to: "total_scheduled_sum / total_actual_sum accumulators"
      via: "+= sched_p_d + sched_i_d"
    - from: "re_routes.py line ~695"
      to: "cpr variable"
      via: "smm < 0 branch returns None"
    - from: "re_routes.py line ~953"
      to: "bucket_expr case"
      via: "no < 180 boundary — 90+ falls to else_='default'"
    - from: "re_routes.py line ~499"
      to: "get_loans body"
      via: "page_size clamped to MAX_PAGE_SIZE = 200"
---

<objective>
Fix four code review warnings (WR-01 through WR-04) in backend/api/re_routes.py. All are logic errors producing incorrect financial output — no crashes, but wrong numbers.

Purpose: Correct financial accuracy (net loss rate), metric semantics (CPR), credit severity classification (delinquency buckets), and a missing security guard documented but not implemented (page_size cap).
Output: Patched re_routes.py with all four fixes, new regression tests covering WR-02/03/04.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@backend/api/re_routes.py
@backend/tests/test_re_api.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Apply WR-01 and WR-02 — net_loss_rate and CPR logic fixes</name>
  <files>backend/api/re_routes.py, backend/tests/test_re_api.py</files>
  <behavior>
    - WR-01: total_scheduled_sum and total_actual_sum must accumulate both principal and interest each period
    - WR-02: When smm == Decimal("0"), cpr = Decimal("0"). When smm > Decimal("0"), cpr = 1-(1-smm)^12. When smm < Decimal("0") (shortfall), cpr = None
    - New test test_cashflow_cpr_none_on_shortfall: seed a loan with act_p < sched_p, call /api/re/cashflow-performance, assert that the period where act_p < sched_p has cpr == null in JSON
    - New test test_cashflow_net_loss_rate_includes_principal: seed a loan with act_p < sched_p and no interest shortfall, assert net_loss_rate > 0 (would have been 0 under the bug)
  </behavior>
  <action>
    In re_routes.py, locate the cashflow-performance loop (around lines 692-701):

    FIX WR-02 — replace the CPR else branch:
    ```python
    # Before
    if smm > Decimal("0"):
        cpr = Decimal("1") - (Decimal("1") - smm) ** Decimal("12")
    else:
        cpr = Decimal("0")

    # After
    if smm > Decimal("0"):
        cpr = Decimal("1") - (Decimal("1") - smm) ** Decimal("12")
    elif smm == Decimal("0"):
        cpr = Decimal("0")
    else:
        cpr = None  # principal shortfall — not a prepayment event
    ```

    FIX WR-01 — replace the two accumulator lines (around lines 700-701):
    ```python
    # Before
    total_scheduled_sum += sched_i_d
    total_actual_sum += act_i_d

    # After
    total_scheduled_sum += sched_p_d + sched_i_d
    total_actual_sum += act_p_d + act_i_d
    ```

    In test_re_api.py, add two new tests after the existing cashflow tests. Both tests need a fixture with scheduled_principal > actual_principal in a cashflow row. Use the existing pattern of inline db fixture creation (see test_cashflow_performance_contract for the client/db pattern). For the cpr test, assert that period["cpr"] is None. For the net_loss_rate test, assert float(data["net_loss_rate"]) > 0.
  </action>
  <verify>
    <automated>cd /c/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend && python -m pytest tests/test_re_api.py::test_cashflow_cpr_none_on_shortfall tests/test_re_api.py::test_cashflow_net_loss_rate_includes_principal -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>Both new tests pass. Existing cashflow tests still pass (run test_cashflow_performance, test_cashflow_performance_contract, test_cashflow_performance_no_loans_returns_empty to verify no regression).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Apply WR-03 and WR-04 — delinquency bucket and page_size cap</name>
  <files>backend/api/re_routes.py, backend/tests/test_re_api.py</files>
  <behavior>
    - WR-03: The "90" case expression row (days_past_due < 180) must be removed. The case becomes: current/30/60/else=default. A loan with 90 DPD must land in "default", not "90".
    - WR-04: At the top of get_loans(), after the sort_by whitelist check, add: MAX_PAGE_SIZE = 200; if page_size > MAX_PAGE_SIZE: page_size = MAX_PAGE_SIZE; if page_size < 1: raise HTTPException(400, "page_size must be >= 1").
    - New test test_delinquency_waterfall_90dpd_is_default: use a fixture loan with days_past_due=90, call /api/re/delinquency-waterfall, assert the loan lands in "default" bucket not "90".
    - New test test_loans_page_size_cap: call /api/re/loans?page_size=9999, assert response is 200 and response JSON page_size is <= 200.
  </behavior>
  <action>
    In re_routes.py, locate the bucket_expr case expression (around line 949):

    FIX WR-03 — remove the (days_past_due < 180, "90") line:
    ```python
    # Before
    bucket_expr = case(
        (RELoan.days_past_due == 0, "current"),
        (RELoan.days_past_due < 60, "30"),
        (RELoan.days_past_due < 90, "60"),
        (RELoan.days_past_due < 180, "90"),
        else_="default",
    )

    # After
    bucket_expr = case(
        (RELoan.days_past_due == 0, "current"),
        (RELoan.days_past_due < 60, "30"),
        (RELoan.days_past_due < 90, "60"),
        else_="default",  # 90+ DPD = default (industry standard)
    )
    ```

    Note: The ORDER dict on line 967 includes "90" as a key. After removing the "90" bucket, the ORDER dict should also be updated to remove "90": {"current": 0, "30": 1, "60": 2, "default": 3}. Verify the existing test_delinquency_waterfall test's expected_order assertion also references "90" and update it to ["current", "30", "60", "default"].

    FIX WR-04 — add page_size guard at the top of get_loans(), immediately after the sort_by whitelist check:
    ```python
    MAX_PAGE_SIZE = 200
    if page_size < 1:
        raise HTTPException(status_code=400, detail="page_size must be >= 1")
    if page_size > MAX_PAGE_SIZE:
        page_size = MAX_PAGE_SIZE
    ```

    In test_re_api.py, add the two new tests described in the behavior section. For the delinquency test: create a db-backed loan with days_past_due=90 (similar to existing fixture patterns), ensure the admin client hits the endpoint, parse buckets, find "default" bucket and assert its loan_count >= 1; assert no "90" bucket exists in response. For the page_size test: client.get("/api/re/loans?page_size=9999", headers=auth_headers_admin), assert status 200, assert data["page_size"] <= 200.
  </action>
  <verify>
    <automated>cd /c/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend && python -m pytest tests/test_re_api.py::test_delinquency_waterfall_90dpd_is_default tests/test_re_api.py::test_loans_page_size_cap tests/test_re_api.py::test_delinquency_waterfall -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>Both new tests pass. Existing test_delinquency_waterfall passes with updated expected_order (no "90" bucket). test_loans_sort_invalid and test_loans_list pass without regression.</done>
</task>

<task type="auto">
  <name>Task 3: Full test suite smoke check</name>
  <files></files>
  <action>
    Run the full re_api test suite to verify no regressions from the four fixes. Do not modify any files — this is a verification-only task.
  </action>
  <verify>
    <automated>cd /c/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend && python -m pytest tests/test_re_api.py -q 2>&1 | tail -30</automated>
  </verify>
  <done>All tests in test_re_api.py pass (0 failures). The four WR fixes are complete and do not break any existing contract tests.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client→API | page_size query param crosses here — untrusted integer |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-snf-01 | Denial of Service | GET /api/re/loans page_size param | mitigate | Clamp page_size to MAX_PAGE_SIZE=200 in get_loans() body (WR-04) |
</threat_model>

<verification>
After all tasks complete:
- GET /api/re/cashflow-performance: net_loss_rate reflects P+I shortfalls, cpr is null for shortfall periods
- GET /api/re/delinquency-waterfall: no "90" bucket; loans with 90 DPD land in "default"
- GET /api/re/loans?page_size=9999: returns 200 with page_size capped at 200 in response body
- All test_re_api.py tests pass
</verification>

<success_criteria>
- WR-01: total_scheduled_sum += sched_p_d + sched_i_d; total_actual_sum += act_p_d + act_i_d
- WR-02: smm < 0 branch sets cpr = None (not Decimal("0"))
- WR-03: bucket_expr has no (days_past_due < 180, "90") case; ORDER dict has no "90" key
- WR-04: MAX_PAGE_SIZE = 200 guard enforced before query execution
- 4 new regression tests added (2 per task), all green
- Full test_re_api.py suite passes with no failures
</success_criteria>

<output>
After completion, create `.planning/quick/260410-snf-fix-code-review-warnings-wr-01-wr-02-wr-/260410-snf-SUMMARY.md`
</output>
