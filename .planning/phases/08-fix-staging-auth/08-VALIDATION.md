---
phase: 8
slug: fix-staging-auth
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-03-11
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual verification (browser + AWS CLI) |
| **Config file** | n/a — no automated tests written in this phase |
| **Quick run command** | `aws ecs describe-services --cluster intrepid-poc-qa --services intrepid-poc-qa --query 'services[0].runningCount' --region us-east-1` |
| **Full suite command** | Browser smoke test checklist (human checkpoint gate in 08-02) |
| **Estimated runtime** | ~15 minutes (terraform apply + CI/CD pipeline + browser walkthrough) |

---

## Sampling Rate

- **After every task commit:** `gh run list --workflow=deploy-test.yml --limit=1 --json conclusion --jq '.[0].conclusion'`
- **After every plan wave:** Full browser smoke test checklist from 08-02-PLAN.md
- **Before `/gsd:verify-work`:** Smoke test human approval + REQUIREMENTS.md updated to `[x]`
- **Max feedback latency:** ~15 minutes (CI/CD pipeline runtime)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | MISS-01 | manual | `docker compose up -d && curl http://localhost:8000/health/ready && docker compose down` | ✅ existing | ⬜ pending |
| 08-01-02 | 01 | 1 | MISS-02 | manual | `terraform plan -out=tfplan` → review diff | ✅ existing ecs.tf | ⬜ pending |
| 08-01-03 | 01 | 1 | MISS-02 | automated | `terraform apply tfplan && aws ecs describe-services --cluster intrepid-poc-qa --services intrepid-poc-qa --query 'services[0].taskDefinition'` | ✅ AWS endpoint | ⬜ pending |
| 08-02-01 | 02 | 2 | STAGE-01/02/03 | automated | `gh run list --workflow=deploy-test.yml --limit=1 --json conclusion --jq '.[0].conclusion'` | ✅ GitHub Actions | ⬜ pending |
| 08-02-02 | 02 | 2 | STAGE-01 | smoke (human) | `Invoke-WebRequest -Uri http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com -UseBasicParsing` returns 200 | ✅ AWS endpoint | ⬜ pending |
| 08-02-03 | 02 | 2 | STAGE-02/03 | integration (human) | Manual browser: login, upload, verify banner on all pages | ✅ no file needed | ⬜ pending |
| 08-02-04 | 02 | 2 | STAGE-01/02/03 | docs | REQUIREMENTS.md updated to `[x]`; 05-VERIFICATION.md written | ⬜ W0 gap | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — no new test files needed. This phase writes no new application code. The existing test suite (50 tests from Phase 7) continues to pass; the CI `security-quality-gate` job runs them on every push to main.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Staging URL loads and app renders | STAGE-01 | Live AWS endpoint, not automatable in CI | `Invoke-WebRequest http://intrepid-poc-qa-alb-...` returns 200; browser shows login page |
| Admin can log in and upload a file | STAGE-02 | Browser form interaction required | Login with `admin` / `IntrepidStaging2024!`; upload a tape file; verify no auth error |
| Amber staging banner on all pages, sticky | STAGE-03 | Visual inspection required | Navigate all authenticated pages (Dashboard, Program Runs, Pipeline Runs, Exceptions, Rejected Loans, File Manager, Cash Flow, Holiday Maintenance); verify amber banner visible and sticky on scroll |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15 minutes
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
