---
phase: 3
slug: aws-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — infrastructure validation is CLI-only (terraform, aws CLI, psql, docker) |
| **Config file** | n/a |
| **Quick run command** | `terraform validate` |
| **Full suite command** | `terraform plan -detailed-exitcode` |
| **Estimated runtime** | ~30 seconds (validate) / ~60 seconds (plan) |

---

## Sampling Rate

- **After every task commit:** Run `terraform validate`
- **After every plan wave:** Run `terraform plan -detailed-exitcode`
- **Before `/gsd:verify-work`:** All 4 INFRA verification checks must pass
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | INFRA-01 | smoke | `terraform validate` | n/a | pending |
| 3-01-02 | 01 | 1 | INFRA-01 | smoke | `terraform plan -detailed-exitcode` | n/a | pending |
| 3-01-03 | 01 | 2 | INFRA-01 | smoke | `terraform apply -auto-approve && echo "EXIT:$?"` | n/a | pending |
| 3-01-04 | 01 | 3 | INFRA-02 | smoke | `aws secretsmanager get-secret-value --secret-id intrepid-poc/qa/DATABASE_URL --query SecretString --output text` | n/a | pending |
| 3-01-05 | 01 | 3 | INFRA-03 | smoke | `docker push $REPO_URL:test-push` after `ecr get-login-password` | n/a | pending |
| 3-01-06 | 01 | 3 | INFRA-04 | manual | `psql "postgresql://..."` from local with temp SG ingress | n/a | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

None — this phase has no code to test in the traditional sense. All validation is post-apply CLI verification.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RDS reachable on private endpoint from local machine | INFRA-04 | Requires temporary SG ingress rule; cannot be fully automated without modifying AWS infrastructure mid-test | 1. Get RDS SG ID: `aws ec2 describe-security-groups --filters Name=group-name,Values=intrepid-poc-qa-rds-sg-* --query 'SecurityGroups[0].GroupId' --output text` 2. Add ingress: `aws ec2 authorize-security-group-ingress --group-id <sg-id> --protocol tcp --port 5432 --cidr $(curl -s https://checkip.amazonaws.com)/32 --region us-east-1` 3. Connect: `psql "postgresql://postgres:Intrepid456\$%@<endpoint>:5432/intrepid_poc?sslmode=require" -c "SELECT version();"` 4. Revoke ingress after test |
| `terraform plan` output reviewed before apply | INFRA-01 | Human review required to confirm expected destroy+recreate scope (~25 resources) | Review output, confirm old `loan-engine-*` resources are being destroyed and `intrepid-poc-*` being created |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
