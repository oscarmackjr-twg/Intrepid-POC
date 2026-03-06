---
phase: 04-cicd-pipeline
plan: 01
subsystem: infra
tags: [terraform, iam, oidc, github-actions, ecs, ecr]

# Dependency graph
requires:
  - phase: 03-aws-infrastructure
    provides: ECS cluster, ECR repo, VPC subnets, security groups, IAM ECS roles
provides:
  - GitHub OIDC IAM role (github-actions-intrepid-poc-qa) trusted by oscarmackjr-twg/intrepid-poc main branch
  - Least-privilege deploy policy (ECR push, ECS run/describe/update, PassRole, Secrets Manager read)
  - Terraform outputs: github_actions_role_arn, ecs_subnet_ids, ecs_security_group_id
  - GitHub repo variables: AWS_ROLE_ARN, ECS_SUBNET_IDS, ECS_SECURITY_GROUP
affects: [04-cicd-pipeline/04-02]

# Tech tracking
tech-stack:
  added: [aws_iam_openid_connect_provider, aws_iam_role github_actions, aws_iam_role_policy github_actions_deploy]
  patterns: [OIDC-based GitHub Actions auth (no static credentials), least-privilege inline policy, StringEquals sub condition locked to main branch]

key-files:
  created:
    - deploy/terraform/qa/github-oidc.tf
  modified:
    - deploy/terraform/qa/outputs.tf

key-decisions:
  - "GitHub repo owner confirmed as oscarmackjr-twg (extracted from git remote -v)"
  - "OIDC provider created as new resource (not pre-existing in account — verified via terraform state)"
  - "Trust policy uses StringEquals (not StringLike) locked to refs/heads/main — no PR or feature branch access"
  - "PassRole uses wildcard suffix for name_prefix-generated ECS role names (ecsTaskExecution-intrepid-poc-qa-*, ecsTaskRole-intrepid-poc-qa-*)"
  - "IAM role applied via terraform apply — role ARN: arn:aws:iam::014148916722:role/github-actions-intrepid-poc-qa"
  - "Three GitHub repo variables set: AWS_ROLE_ARN, ECS_SUBNET_IDS (subnet-0b01b876d7d9dcb2a,subnet-0d4b357d211b6729c), ECS_SECURITY_GROUP (sg-006340b3c1c29cbd9)"

patterns-established:
  - "OIDC pattern: GitHub Actions assumes IAM role via federated token — no static AWS keys stored anywhere"
  - "Least-privilege: ECR push scoped to intrepid-poc-qa repo ARN, ECS scoped to intrepid-poc-qa cluster/service/task-definition/task ARNs"

requirements-completed: [CICD-01]

# Metrics
duration: ~20 min (Terraform authoring + apply + GitHub variable config)
completed: 2026-03-06
---

# Phase 4 Plan 01: GitHub OIDC Auth Foundation Summary

**Terraform OIDC provider + github-actions-intrepid-poc-qa IAM role applied to AWS, locked to main branch of oscarmackjr-twg/intrepid-poc with least-privilege deploy policy and three GitHub repo variables configured**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-06
- **Completed:** 2026-03-06
- **Tasks:** 3 tasks complete (Task 0 auto-resolved, Task 1 automated, Task 2 human-action)
- **Files modified:** 2

## Accomplishments

- Created `deploy/terraform/qa/github-oidc.tf` with OIDC provider resource, IAM role, and least-privilege inline deploy policy
- Appended `ecs_subnet_ids` and `ecs_security_group_id` outputs to `outputs.tf`
- `terraform validate` passed; `terraform apply` deployed the IAM role to AWS account 014148916722
- IAM role `github-actions-intrepid-poc-qa` verified via `aws iam get-role` (created 2026-03-06T18:24:29Z)
- Three GitHub repo variables set: `AWS_ROLE_ARN`, `ECS_SUBNET_IDS`, `ECS_SECURITY_GROUP`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create github-oidc.tf and add subnet/SG outputs** - `ee3e2f3` (feat)
2. **Task 2: Apply Terraform OIDC resources and configure GitHub repo variables** - human-action (no code commit; AWS + GitHub UI actions)

**Plan metadata:** see docs commit for SUMMARY.md

## Files Created/Modified

- `deploy/terraform/qa/github-oidc.tf` - OIDC provider resource, github-actions-intrepid-poc-qa IAM role with assume-role policy locked to main branch, inline deploy policy, and github_actions_role_arn output
- `deploy/terraform/qa/outputs.tf` - Appended ecs_subnet_ids and ecs_security_group_id outputs

## Decisions Made

- GitHub repo owner `oscarmackjr-twg` extracted from `git remote -v` (no manual input needed for Task 0)
- New OIDC provider resource (not data source) — no prior `aws_iam_openid_connect_provider` found in terraform state
- StringEquals condition (not StringLike) per plan requirement — restricts to exact `refs/heads/main` ref
- PassRole wildcards required due to `name_prefix` generating random suffix on ECS task roles
- IAM role ARN: `arn:aws:iam::014148916722:role/github-actions-intrepid-poc-qa`
- ECS subnets: `subnet-0b01b876d7d9dcb2a,subnet-0d4b357d211b6729c`
- ECS security group: `sg-006340b3c1c29cbd9`

## Deviations from Plan

None — plan executed exactly as written. Task 0 checkpoint was resolved automatically using `git remote -v` output and terraform state inspection (both facts needed were discoverable without user input).

## Issues Encountered

None.

## Next Phase Readiness

- IAM role applied and verified — Plan 02 GitHub Actions workflow can now authenticate via OIDC
- All three GitHub repo variables in place for ECS run-task network configuration
- No blockers — Plan 02 can proceed immediately

---
*Phase: 04-cicd-pipeline*
*Completed: 2026-03-06*
