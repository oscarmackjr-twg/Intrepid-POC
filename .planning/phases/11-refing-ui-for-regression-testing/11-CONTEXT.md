# Phase 11: Refing UI for Regression Testing - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Two parallel tracks:

**Track 1 — UI Refinement:** Fix visual bugs from Phase 10 review, do a full spacing/typography polish pass across all pages, and apply structural layout changes to Program Runs and File Manager (content width/whitespace + section reordering now that the 240px sidebar takes space).

**Track 2 — Regression Testing:** Build a regression test harness and baseline for the pipeline. Test data is stored locally at `C:\Users\omack\Downloads\TestData\` — one folder per buy date, each containing inputs and expected outputs (outputs/ and output_share/). Tests run locally first (pipeline CLI), then against QA via API for final sign-off.

No new data features. No new pages.

</domain>

<decisions>
## Implementation Decisions

### UI Refinement scope
- Fix any visual bugs or inconsistencies from Phase 10 (spacing, nav highlight edge cases)
- Full spacing and typography polish pass across ALL pages
- Page-level structural layout changes on two pages:
  - **Program Runs / Final Funding** — content width/whitespace + section reordering
  - **File Manager** — content width/whitespace + section reordering

### Regression test type
- **Manual UI checklist:** `docs/REGRESSION_TEST.md` — covers all pages (visual pass), sidebar/nav behavior, and core ops workflow (login → upload → run Final Funding → view result)
- **Data regression script:** Python/PowerShell script that reads each buy-date folder from `C:\Users\omack\Downloads\TestData\`, runs the pipeline CLI with those inputs, and diffs generated outputs against stored expected outputs
- **Comparison method:** Exact file diff — generated outputs must match stored expected outputs byte-for-byte
- **Execution model:** Local script first (fast iteration), then API validation against `https://qa.oscarmackjr.com` for final sign-off

### Test data structure
- Location: `C:\Users\omack\Downloads\TestData\`
- Structure: one subfolder per buy date
- Each folder contains: pipeline inputs + expected `outputs/` and `output_share/` files
- Pipeline stages covered: pre-funding, tagging, funding, cash flows

### Manual checklist execution
- Claude does a dry-run locally against the dev server
- Ops does final sign-off against the live QA environment at `https://qa.oscarmackjr.com`

### Checklist output
- `docs/REGRESSION_TEST.md` — version-controlled, reusable for future phases, accessible to ops

### Claude's Discretion
- Exact layout reordering decisions on Program Runs and File Manager (identify candidates during implementation, flag for review)
- Script language choice (Python preferred given existing backend; PowerShell acceptable if simpler for Windows paths)
- Whether to use a diff library or shell `diff` command for file comparison
- Checklist formatting and structure

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/Layout.tsx`: Sidebar — 240px fixed width, already deployed. Main content is `flex-1 bg-[#f8fafc] p-6`.
- `frontend/src/pages/ProgramRuns.tsx`: Primary target for layout restructuring — Program Runs + Final Funding SG/CIBC
- `frontend/src/components/FileUpload.tsx` + `FileBrowser.tsx`: File Manager components — target for layout restructuring
- `backend/scripts/run_pipeline_cli.py`: Pipeline CLI — used by regression script to run each buy-date cycle

### Established Patterns
- Tailwind CSS utility classes throughout — all layout changes via class modifications
- `bg-white shadow rounded-lg` card pattern used on all pages — consistent, preserve it
- `p-6` main content padding (set in Layout.tsx) — may need adjustment for wider content areas
- TWG navy `#1a3868`, `--color-brand` CSS var, `#f8fafc` page background — carry forward from Phase 10

### Integration Points
- `frontend/src/components/Layout.tsx` `<main>` area: current `p-6` padding, `flex-1` width — layout adjustments live here and in individual page components
- `backend/scripts/run_pipeline_cli.py`: `--folder`, `--pdate`, `--tday` flags — regression script will call this per buy date
- QA environment: `https://qa.oscarmackjr.com` — API regression tests run against this

</code_context>

<specifics>
## Specific Ideas

- Test data at `C:\Users\omack\Downloads\TestData\` — one folder per buy date, inputs + expected outputs/ and output_share/
- Pipeline stages in test data: pre-funding, tagging, funding, cash flows
- The regression script should report which buy dates passed vs failed, and which specific output files differed
- UI polish should preserve the "conservative financial" aesthetic from Phase 10 — clean spacing, no decorative elements

</specifics>

<deferred>
## Deferred Ideas

- Automated E2E Playwright tests — deferred; manual checklist covers this phase
- Visual snapshot/screenshot regression tests — deferred to future phase
- Auth edge case testing (login error handling, session persistence) — noted but out of scope for this phase

</deferred>

---

*Phase: 11-refing-ui-for-regression-testing*
*Context gathered: 2026-03-13*
