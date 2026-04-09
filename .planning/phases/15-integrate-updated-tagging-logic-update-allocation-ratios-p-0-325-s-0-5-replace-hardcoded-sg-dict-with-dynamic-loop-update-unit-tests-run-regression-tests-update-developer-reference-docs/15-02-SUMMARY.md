---
phase: 15-integrate-updated-tagging-logic
plan: "02"
subsystem: backend/scripts, docs
tags: [regression-testing, golden-files, documentation, tagging]
dependency_graph:
  requires: [allocate_sg-function]
  provides: [regression-baseline, developer-reference-updated, tests-readme-updated]
  affects:
    - backend/tests/README.md
    - docs/Intrepid_Platform_Developer_Reference.docx
    - backend/TestData/93rd_buy/output/ (golden files)
    - backend/TestData/95th_buy/output/ (golden files)
key_files:
  modified:
    - backend/tests/README.md
    - docs/Intrepid_Platform_Developer_Reference.docx
decisions:
  - "Accepted pre-existing regression state: 38 missing files (93rd) / 23 missing (95th) in golden dirs are non-funding outputs from prior full pipeline runs — not caused by Phase 15"
  - "Re-baselined golden files twice: first run used old sg/cibc splits (wrong), second run re-ran tagging.py with new ratios first (correct)"
  - "98th_buy FundingSG crash is pre-existing (missing tape file) — not addressed in this phase"
metrics:
  duration: "~30 minutes"
  completed_date: "2026-04-08"
  tasks: 3
  files: 2
---

# Phase 15 Plan 02: Regression Tests + Developer Reference Docs

Ran regression tests after tagging ratio changes, re-baselined golden files for expected ratio-change diffs, updated developer reference (new section 5.9 with 50% SFY / 32.5% PRIME / dynamic loop) and tests README.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Run regression tests and re-baseline golden files | 0556864 | TestData/93rd_buy/, TestData/95th_buy/ |
| 2 | Update developer reference docs and tests README | 0556864 | docs/Intrepid_Platform_Developer_Reference.docx, backend/tests/README.md |
| 3 | Human verification checkpoint | — | Approved 2026-04-08 |

## What Was Built

### Task 1: Regression Test Re-baselining

- Ran `tagging.py` directly on TestData/files_required to apply new ratios before re-baselining
  - 93rd_buy: SG=650, CIBC=832 (new split with p=0.325, s=0.5)
  - 95th_buy: SG=443, CIBC=573 (new split)
- Ran `regression_test_funding.py --update-golden` twice (first pass used wrong old splits)
- Re-baselined 23 golden files each for 93rd and 95th buy — all ratio-change diffs resolved
- Final state: 0 differ, 38 missing (93rd) / 23 missing (95th) — missing files are pre-existing non-funding outputs

### Task 2: Developer Reference + Tests README

- `docs/Intrepid_Platform_Developer_Reference.docx`: Added section 5.9 documenting new allocation ratios (50% SFY, 32.5% PRIME) and dynamic loop behavior
- `backend/tests/README.md`: Added `test_tagging_allocation.py` entry (Tagging SG allocation logic — Phase 15)

### Task 3: Human Checkpoint

- User reviewed regression results and approved pre-existing golden directory state
- Pre-existing issues (38/23 missing files, 98th_buy crash) acknowledged as out of scope for Phase 15

## Verification Results

1. `regression_test_funding.py`: 0 differ on 93rd and 95th (all ratio-change diffs re-baselined) — PASS
2. `grep "test_tagging_allocation" backend/tests/README.md` — FOUND
3. Developer reference Word doc updated (section 5.9 present) — PASS
4. Human checkpoint — APPROVED

## Deviations from Plan

### Accepted Pre-existing State

**Pre-existing golden directory issue:**
- `regression_test_funding.py` shows 38 missing (93rd) and 23 missing (95th) after re-baselining
- These "missing" files are pre-funding and tagging outputs placed in golden dirs by prior full pipeline runs — never produced by the funding-only test
- Decision: accepted as pre-existing, not Phase 15's responsibility

## Known Issues

- 98th_buy FundingSG crashes (missing tape file) — pre-existing, not Phase 15 regression
- Golden directories contain non-funding outputs that the funding regression test doesn't generate — golden dir hygiene is a future cleanup candidate

## Self-Check: PASSED

Files exist:
- FOUND: backend/tests/README.md (contains test_tagging_allocation.py)
- FOUND: docs/Intrepid_Platform_Developer_Reference.docx (updated)

Commits exist:
- FOUND: 0556864 (feat(15-02): update developer reference docs and tests README)
