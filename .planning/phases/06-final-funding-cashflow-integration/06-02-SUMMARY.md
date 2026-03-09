---
phase: 06-final-funding-cashflow-integration
plan: 02
subsystem: backend/scripts
tags: [final-funding, workbook-scripts, sg, cibc, env-convention]
dependency_graph:
  requires: []
  provides:
    - backend/scripts/final_funding_sg.py (real SG workbook logic, FOLDER env convention)
    - backend/scripts/final_funding_cibc.py (real CIBC workbook logic, FOLDER env convention)
  affects:
    - backend/orchestration/final_funding_runner.py (discovers bundled scripts via _BUNDLED_SG / _BUNDLED_CIBC)
tech_stack:
  added: []
  patterns:
    - FOLDER env var injected by runner before subprocess call; scripts read via os.environ.get("FOLDER", ".")
key_files:
  created: []
  modified:
    - backend/scripts/final_funding_sg.py
    - backend/scripts/final_funding_cibc.py
decisions:
  - Retained the commented-out fx4_servicing_file line referencing C:/Users/gdehankar (different user, forward slash) — it is a legacy comment from the original script preserved per "copy verbatim" instruction; plan verification checks for backslash C:\Users only and passes
  - Known-limitation comment placed immediately after folder= line to warn future operators that date variables (pdate, curr_date, last_end, fd, yestarday) must be updated per buy cycle
metrics:
  duration: 8min
  completed_date: "2026-03-09"
  tasks_completed: 2
  files_modified: 2
requirements_satisfied:
  - FF-01
  - FF-02
---

# Phase 06 Plan 02: Replace Final Funding Script Stubs Summary

**One-liner:** Replaced 25-line stub scripts with 815-line real workbook scripts (SG) and 817-line real workbook scripts (CIBC) from legacy loan_engine repo, patched to read FOLDER from env.

## What Was Built

Both `backend/scripts/final_funding_sg.py` and `backend/scripts/final_funding_cibc.py` were replaced with the full real workbook scripts from `loan_engine/inputs/93rd_buy/bin/`. Each script:

- Reads `FOLDER` from `os.environ.get("FOLDER", ".")` instead of a hardcoded Windows path
- Carries a known-limitation comment block immediately after the `folder =` line explaining that date variables are hard-coded to the 93rd buy cycle
- Preserves all original logic verbatim: pandas Excel I/O, underwriting checks, COMAP grid lookups, eligibility checks A-L, output Excel generation to `output/` and `output_share/`
- Creates output files in `folder/output/` and `folder/output_share/` (directories created by runner before calling script)

The runner (`backend/orchestration/final_funding_runner.py`) discovers these via `_BUNDLED_SG` and `_BUNDLED_CIBC` constants and injects `FOLDER` via subprocess env. No runner changes were needed.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Copy and patch final_funding_sg.py from legacy repo | d0c6d2d | backend/scripts/final_funding_sg.py |
| 2 | Copy and patch final_funding_cibc.py from legacy repo | f145ee3 | backend/scripts/final_funding_cibc.py |

## Verification Results

Both scripts pass all plan verification checks:
- `ast.parse()` — no SyntaxError
- Contains `os.environ.get` — confirmed
- Does not contain `C:\Users` (backslash) — confirmed
- Known-limitation comment present — confirmed
- File size: SG 815 lines, CIBC 817 lines (vs 25-line stubs)

## Deviations from Plan

None — plan executed exactly as written.

The commented-out `fx4_servicing_file` line referencing `C:/Users/gdehankar` (forward slash, different user) was retained verbatim per the "copy full script body verbatim" instruction. The plan's verification check uses `r'C:\Users'` (backslash) and passes correctly.

## Self-Check

Files created:
- backend/scripts/final_funding_sg.py — modified
- backend/scripts/final_funding_cibc.py — modified

Commits:
- d0c6d2d — feat(06-02): replace stub with real SG workbook script from legacy repo
- f145ee3 — feat(06-02): replace stub with real CIBC workbook script from legacy repo

## Self-Check: PASSED
