---
status: partial
phase: 10-revamp-user-interface-phase-10
source: [10-VERIFICATION.md]
started: 2026-03-22T00:00:00Z
updated: 2026-03-22T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Login page — visual appearance
expected: Heading 'Intrepid Loan Platform' appears in navy (#1a3868), Sign In button is dark navy, background is light gray (#f8fafc)
result: [pending]

### 2. Sidebar — visible at ~240px on every authenticated page
expected: Left sidebar is rendered with white background and right border separator, content fills remaining width
result: [pending]

### 3. StagingBanner — full-width above sidebar
expected: Amber staging banner spans the full browser width above both sidebar and content, not constrained inside either panel
result: [pending]

### 4. Active nav item highlight
expected: Clicking Dashboard shows navy left border and navy semibold text on that item; clicking Program Runs does the same
result: [pending]

### 5. Admin gate — non-admin user
expected: When logged in as a non-admin, Cash Flow and Holiday Maintenance nav items are absent from the sidebar
result: [pending]

### 6. Admin gate — admin user
expected: When logged in as admin, Cash Flow and Holiday Maintenance nav items appear at the bottom of the nav list
result: [pending]

### 7. Browser tab title
expected: Browser tab reads 'Intrepid Loan Platform'
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
