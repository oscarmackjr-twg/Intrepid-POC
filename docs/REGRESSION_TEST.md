# Regression Test Checklist
Version: Phase 11
Environment: [fill in: local / QA]
Tester: [fill in]
Date: [fill in]
Result: [ ] PASS  [ ] FAIL

---

## 1. Authentication

- [ ] Login page loads at /login — expected: TWG logo visible, "Intrepid Loan Platform" label, navy submit button
- [ ] Login with valid credentials (admin / admin123) — expected: redirects to /dashboard
- [ ] Login with invalid credentials — expected: error message displayed, no redirect
- [ ] Sign Out link in sidebar footer — expected: redirects to /login, session cleared

## 2. Sidebar Navigation

- [ ] Sidebar is visible on all pages — expected: 240px white sidebar with TWG logo and navy brand label
- [ ] StagingBanner visible on all pages (staging/local only) — expected: top banner present, unmissable
- [ ] Active state: click Dashboard — expected: only Dashboard item highlighted
- [ ] Active state: click Program Runs — expected: only Program Runs item highlighted (not Final Funding SG/CIBC)
- [ ] Active state: click Final Funding SG — expected: only Final Funding SG highlighted
- [ ] Active state: click Final Funding CIBC — expected: only Final Funding CIBC highlighted
- [ ] Active state: click Cash Flow SG — expected: only Cash Flow SG highlighted
- [ ] Active state: click Cash Flow CIBC — expected: only Cash Flow CIBC highlighted
- [ ] Active state: click File Manager — expected: only File Manager highlighted
- [ ] SG group label visible above SG items — expected: "SG" label in slate uppercase
- [ ] CIBC group label visible above CIBC items — expected: "CIBC" label in slate uppercase
- [ ] User name and role visible in sidebar footer — expected: username + role displayed

## 3. Dashboard

- [ ] Dashboard loads at /dashboard — expected: page title "Dashboard" or equivalent, run history visible
- [ ] Recent runs table shows run IDs, status, dates — expected: at least column headers visible if no runs present

## 4. Program Runs

- [ ] Program Runs page loads at /program-runs — expected: "Program Runs" heading, "Run Program" card visible
- [ ] "Run Program" card shows four buttons: Pre-Funding, Tagging, Final Funding SG, Final Funding CIBC — expected: all four buttons present and enabled
- [ ] "Standard Output" card is visible below Run Program — expected: shows "No output yet." by default
- [ ] "Output Directory" card is visible below Standard Output — expected: file table with Refresh button
- [ ] Content width is constrained — expected: content does not stretch edge-to-edge on wide screen (max ~1024px)
- [ ] Click Pre-Funding button — expected: effective date modal opens with today's date pre-filled
- [ ] Cancel in effective date modal — expected: modal closes, no run started

## 5. File Manager

- [ ] File Manager loads at /files — expected: "File Manager" heading, file list visible above upload zone
- [ ] File list appears above upload zone — expected: file table is the first content section after header
- [ ] Upload zone is compact — expected: single-line "Click to upload or drag and drop" text, not a large empty box
- [ ] Area selector (Inputs / Outputs) switches file area — expected: file list reloads showing inputs or outputs
- [ ] Upload a file via click — expected: file upload dialog opens, file uploaded, list refreshes
- [ ] Drag and drop a file — expected: drop zone highlights on drag-over, file uploads on drop

## 6. Core Ops Workflow (End-to-End)

Prerequisites: input files present in files_required/ (for local: backend/data/sample/files_required/)

- [ ] Upload a file to File Manager (Inputs area, files_required/) — expected: file appears in list
- [ ] Navigate to Program Runs — expected: page loads, folder path shows sample data dir (local mode)
- [ ] Click Pre-Funding, enter effective date, click Start Run — expected: "Pre-Funding run started" dialog shown
- [ ] Dismiss dialog, observe Standard Output — expected: Run ID and status appear, updates while running
- [ ] Wait for run to complete — expected: Standard Output shows status: completed (or check Dashboard)
- [ ] Observe Output Directory — expected: run output files appear in directory listing
- [ ] Download an output file — expected: file download dialog opens, file saved locally
- [ ] Click Final Funding SG — expected: status shows QUEUED then RUNNING then COMPLETED (or FAILED with error detail)

## 7. Visual / Brand

- [ ] All page backgrounds are #f8fafc (light gray) — expected: no white or other background color on main content area
- [ ] All cards use bg-white shadow rounded-lg pattern — expected: consistent card appearance
- [ ] No horizontal scrollbar on any page at 1280px viewport width — expected: clean horizontal layout
- [ ] Font rendering is antialiased — expected: text appears smooth (not pixelated)
- [ ] Heading letter-spacing is slightly tight — expected: headings look crisp, not spaced-out

---

## Sign-Off

Local dry-run (Claude): [x] PASS  [ ] FAIL — Date: 2026-03-13

Notes (Claude dry-run):

- Build: frontend npm run build exits 0 in 1.12s, 99 modules, no TypeScript errors.
- Nav active states: all 6 conditions verified in Layout.tsx — Program Runs uses !type= negation, SG/CIBC children use type=sg/type=cibc, Cash Flow admin link uses !type= negation. All unique.
- Layout: max-w-5xl confirmed on outer wrapper in both ProgramRuns.tsx (line 401) and FileManager.tsx (line 179).
- FileManager section order: File List JSX at line 228, Upload Area JSX at line 307 — file list is first. PASS.
- Regression script: ast.parse reports SYNTAX OK.
- REGRESSION_TEST.md: all 7 sections present plus Sign-Off block.
- Visual items (active state highlighting, card appearance, background color, font rendering) require browser verification — see QA sign-off below.

QA sign-off (Ops): [ ] PASS  [ ] FAIL — Date: ___________  Tester: ___________
