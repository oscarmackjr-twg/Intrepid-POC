---
phase: 4
slug: cicd-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | GitHub Actions workflow logs + AWS CLI verification |
| **Config file** | `.github/workflows/deploy.yml` |
| **Quick run command** | `act push --dry-run` (local) or `gh workflow view` |
| **Full suite command** | Trigger workflow via `git push` to main |
| **Estimated runtime** | ~300 seconds (full ECS deployment) |

---

## Sampling Rate

- **After every task commit:** Validate YAML syntax with `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"` or `act --list`
- **After every plan wave:** Run `gh workflow run` or push to verify workflow triggers
- **Before `/gsd:verify-work`:** Full deployment pipeline must be green
- **Max feedback latency:** ~300 seconds (ECS deploy cycle)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | CICD-01 | syntax | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"` | ❌ W0 | pending |
| 4-01-02 | 01 | 1 | CICD-01 | integration | `gh run list --limit 1` | ✅ | pending |
| 4-01-03 | 01 | 2 | CICD-02 | manual | Verify migration task exits 0 in ECS | n/a | pending |
| 4-01-04 | 01 | 2 | CICD-02 | integration | `aws ecs describe-tasks` exit code check | ✅ | pending |
| 4-01-05 | 01 | 3 | CICD-03 | manual | Confirm secrets documented in README/runbook | n/a | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `.github/workflows/deploy.yml` — workflow file (created as part of plan execution)
- [ ] Terraform OIDC provider config — `iam.tf` or equivalent

*Note: No traditional test framework required — CI/CD validation is integration-level via AWS CLI and GitHub Actions.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration runs and exits 0 | CICD-02 | Requires live RDS + ECS environment | Trigger push, check ECS task logs in CloudWatch, confirm exit code 0 |
| Secrets documented and configured | CICD-03 | Human confirmation of repo settings | Review README/runbook, confirm secrets exist in GitHub repo settings |
| End-to-end deploy completes | CICD-01 | Requires live AWS infra | Push to main, verify new ECS task version running with updated image |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
