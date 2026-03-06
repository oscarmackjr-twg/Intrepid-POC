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
  - GitHub OIDC IAM role (github-actions-intrepid-poc-qa) trusted by oscarmackjr-twg/Intrepid-POC main branch
  - Least-privilege deploy policy (ECR push, ECS run/describe/update, PassRole, Secrets Manager read)
  - Terraform outputs: github_actions_role_arn, ecs_subnet_ids, ecs_security_group_id
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

patterns-established:
  - "OIDC pattern: GitHub Actions assumes IAM role via federated token — no static AWS keys stored anywhere"
  - "Least-privilege: ECR push scoped to intrepid-poc-qa repo ARN, ECS scoped to intrepid-poc-qa cluster/service/task-definition/task ARNs"

requirements-completed: [CICD-01]

# Metrics
duration: partial (awaiting terraform apply checkpoint)
completed: 2026-03-06
---

# Phase 4 Plan 01: GitHub OIDC Auth Foundation Summary

**Terraform OIDC provider + github-actions-intrepid-poc-qa IAM role with least-privilege deploy policy, locked to main branch of oscarmackjr-twg/Intrepid-POC**

## Performance

- **Duration:** ~10 min (Terraform authoring + validate)
- **Started:** 2026-03-06
- **Completed:** 2026-03-06 (pending terraform apply by user)
- **Tasks:** 1/3 automated tasks complete (Task 2 is human-action checkpoint)
- **Files modified:** 2

## Accomplishments

- Created `deploy/terraform/qa/github-oidc.tf` with OIDC provider, IAM role, and inline deploy policy
- Appended `ecs_subnet_ids` and `ecs_security_group_id` outputs to `outputs.tf`
- `terraform validate` passes with no errors
- Trust policy uses StringEquals locked to `repo:oscarmackjr-twg/Intrepid-POC:ref:refs/heads/main`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create github-oidc.tf and add subnet/SG outputs** - `ee3e2f3` (feat)

## Files Created/Modified

- `deploy/terraform/qa/github-oidc.tf` - OIDC provider resource, github-actions-intrepid-poc-qa IAM role with assume-role policy, inline deploy policy, and github_actions_role_arn output
- `deploy/terraform/qa/outputs.tf` - Appended ecs_subnet_ids and ecs_security_group_id outputs

## Decisions Made

- GitHub repo owner `oscarmackjr-twg` extracted from `git remote -v` (no manual input needed)
- New OIDC provider resource (not data source) because terraform state had no prior aws_iam_openid_connect_provider
- StringEquals condition (not StringLike) per plan requirement — restricts to exact main branch ref
- PassRole wildcards required due to `name_prefix` generating random suffix on ECS task roles

## Deviations from Plan

None - plan executed exactly as written. Task 0 checkpoint was resolved automatically using `git remote -v` output and terraform state inspection (both facts needed were discoverable without user input).

## User Setup Required

**Task 2 requires manual terraform apply and GitHub variable configuration.** See checkpoint details below.

### Steps for User

1. Refresh AWS credentials if expired (`aws sso login` or re-export tokens)
2. Run from `C:\Users\omack\Intrepid\pythonFramework\intrepid-poc\deploy\terraform\qa`:
   ```powershell
   terraform plan -out=oidc.tfplan
   terraform apply oidc.tfplan
   ```
3. Capture outputs:
   ```powershell
   terraform output github_actions_role_arn
   terraform output ecs_subnet_ids
   terraform output ecs_security_group_id
   ```
4. Set as GitHub repo variables (Settings -> Secrets and variables -> Actions -> Variables):
   - `AWS_ROLE_ARN` = value from `github_actions_role_arn`
   - `ECS_SUBNET_IDS` = value from `ecs_subnet_ids`
   - `ECS_SECURITY_GROUP` = value from `ecs_security_group_id`

## Next Phase Readiness

- Plan 02 can proceed once IAM role is applied and GitHub variables are set
- Blockers: terraform apply must complete and three GitHub repo variables must exist before Plan 02 workflow can authenticate

---
*Phase: 04-cicd-pipeline*
*Completed: 2026-03-06*
