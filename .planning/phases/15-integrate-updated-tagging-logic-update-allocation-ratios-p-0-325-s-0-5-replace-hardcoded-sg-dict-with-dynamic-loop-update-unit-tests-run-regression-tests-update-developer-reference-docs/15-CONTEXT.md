# Phase 15: Integrate Updated Tagging Logic - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Update `backend/scripts/tagging.py` with new allocation ratios (p=0.325, s=0.5) and replace the hardcoded SG dict with a dynamic loop. Fix the KeyError guard. Add unit tests for the allocation logic. Run regression tests to confirm output is stable. Update the developer reference Word doc and inline comment to reflect the new ratios and dynamic approach.

No new pipeline features, no new API endpoints, no UI changes.

</domain>

<decisions>
## Implementation Decisions

### Allocation ratios
- **D-01:** Change `p = 0.3` → `p = 0.325` (PRIME SG allocation)
- **D-02:** Change `s = 0.6` → `s = 0.5` (SFY SG allocation)

### Dynamic SG dict
- **D-03:** Replace hardcoded 12-key dict with a loop over `grouped_sum` keys
- **D-04:** Classification: `startswith("SFY")` → multiply by `s`; `startswith("PRIME")` → multiply by `p`
- **D-05:** `_bd`-suffix tags always get 0 SG allocation — set to 0 in the loop (or skip and rely on guard). Preserves current behavior that bad-debt loans always go to CIBC.

### KeyError guard
- **D-06:** Replace `if tag in sg and sg[tag] > 0:` with `if sg.get(tag, 0) > 0:` — handles tags in buy_df that were absent from grouped_sum (e.g. zero-balance groups filtered out)

### Unit tests
- **D-07:** Create new `backend/tests/test_tagging_allocation.py`
- **D-08:** Extract the allocation logic (build sg dict + assign `final` column) into a standalone function in tagging.py so tests can import and call it directly — no subprocess, no file I/O
- **D-09:** Tests use inline DataFrames with explicit column values (follows Phase 12 pattern from test_comap.py)
- **D-10:** Test coverage: ratio values, dynamic dict building (SFY vs PRIME classification), `_bd` exclusion, `sg.get(tag, 0)` guard for unknown tags

### Docs update
- **D-11:** Update inline comment in tagging.py line 120 (currently says "SG allocation targets: 60% of SFY, 30% of PRIME") to reflect new ratios (50% SFY, 32.5% PRIME)
- **D-12:** Update `docs/Intrepid_Platform_Developer_Reference.docx` to reflect new ratios and dynamic loop behavior

### Regression tests
- **D-13:** Run `backend/scripts/regression_test.py` and `regression_test_funding.py` against sample data after changes; if outputs differ only due to ratio change, re-baseline golden files with `--update-golden`

### Claude's Discretion
- Exact function signature for the extracted allocation function
- Whether to use `sg[tag] = 0` or `continue` for `_bd` tags in the loop
- Test fixture structure (parametrize vs separate test methods)

</decisions>

<specifics>
## Specific Ideas

- The summary writer at line 177 already uses `s if tag.startswith("SFY") else p` — the dynamic loop should use the same prefix logic for consistency
- The existing `if tag in sg and sg[tag] > 0:` guard works but `.get()` is cleaner; both are acceptable
- The extracted function should take `buy_df` and `grouped_sum` as inputs and return `buy_df` with `final` column populated

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Tagging implementation
- `backend/scripts/tagging.py` — Current implementation; lines 120–154 contain the allocation logic to be refactored
- `backend/orchestration/tagging_runner.py` — Runner that calls tagging.py via subprocess; no changes needed here

### Existing test patterns
- `backend/tests/test_enrichment.py` — Tagging tests using inline DataFrames (Phase 12 pattern to replicate)
- `backend/tests/README.md` — Test conventions and pytest invocation

### Docs
- `docs/Intrepid_Platform_Developer_Reference.docx` — Developer reference to update with new ratios

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `grouped_sum = buy_df.groupby("tags")["Orig. Balance"].sum()` — already computed before the dict; dynamic loop can iterate directly over it
- Line 177 `s if tag.startswith("SFY") else p` — existing prefix-based ratio selection to mirror in the loop

### Established Patterns
- Phase 12: inline DataFrames with explicit column names in test fixtures
- Phase 12: separate test files per module (test_enrichment.py, test_comap.py, test_archive.py)
- tagging.py is a module-level script (runs on import); extraction into a function requires careful scoping

### Integration Points
- `tagging_runner.py` calls tagging.py as a subprocess — extraction of a testable function does NOT affect the runner
- `regression_test.py` runs the full pipeline CLI; tagging is one phase in that pipeline

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-integrate-updated-tagging-logic*
*Context gathered: 2026-03-23*
