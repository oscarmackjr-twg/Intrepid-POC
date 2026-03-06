---
phase: 03-aws-infrastructure
plan: 01
subsystem: infra
tags: [terraform, aws, ecs, rds, ecr, s3, alb, iam]

# Dependency graph
requires:
  - phase: 02-docker-local-dev
    provides: Dockerized application ready for ECR push and ECS deployment
provides:
  - Clean Terraform configuration with intrepid-poc naming throughout
  - terraform.tfvars with real QA credentials (gitignored)
  - All intrepid-poc-qa AWS resources provisioned (pending human apply)
affects: [04-cicd, 05-staging]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "terraform output -raw for dynamic ECS cluster/service name lookups in deploy scripts"
    - "gitignored terraform.tfvars holds real db_password; tfvars.example holds sanitized CHANGE_ME placeholder"

key-files:
  created:
    - deploy/terraform/qa/terraform.tfvars (gitignored, not committed)
  modified:
    - deploy/terraform/qa/versions.tf
    - deploy/terraform/qa/key-pair.tf
    - deploy/terraform/qa/deploy-qa.ps1
    - deploy/terraform/qa/terraform.tfvars.example
    - deploy/terraform/qa/outputs.tf

key-decisions:
  - "deploy-qa.ps1 ECS update-service uses terraform output -raw instead of hardcoded cluster/service names — handles any app_name change automatically"
  - "terraform.tfvars.example db_password changed from real value to CHANGE_ME placeholder to avoid accidental secret exposure"

patterns-established:
  - "Pattern 1: All AWS resource names derive from var.app_name (intrepid-poc) via name_prefix local — no hardcoded strings in resource blocks"
  - "Pattern 2: Deploy scripts use terraform output -raw for resource name lookups rather than hardcoding values"

requirements-completed: [INFRA-01]

# Metrics
duration: 15min
completed: 2026-03-06
---

# Phase 3 Plan 01: Fix loan-engine Naming and Provision QA Infrastructure Summary

**Terraform QA configuration renamed from loan-engine to intrepid-poc throughout all resource values; terraform validate passes; human-gated destroy+apply pending to provision 25 intrepid-poc-qa AWS resources**

## Performance

- **Duration:** ~15 min (Task 1 complete; Task 2 awaiting human checkpoint)
- **Started:** 2026-03-06T04:18:14Z
- **Completed:** 2026-03-06T04:33:00Z (Task 1); Task 2 pending
- **Tasks:** 1 of 2 (Task 2 is human-verify checkpoint)
- **Files modified:** 5

## Accomplishments
- Replaced all `loan-engine` resource values with `intrepid-poc` across 5 Terraform/deploy files
- Created gitignored `terraform.tfvars` with real QA credentials (db_password, all resource names)
- `terraform validate` passes with exit code 0 confirming configuration correctness
- `deploy-qa.ps1` now uses dynamic `terraform output` lookups instead of hardcoded ECS names

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix loan-engine naming remnants and create terraform.tfvars** - `7ad2729` (fix)
2. **Task 2: Human plan review then terraform destroy + apply** - PENDING HUMAN CHECKPOINT

**Plan metadata:** TBD (after Task 2 checkpoint approved)

## Files Created/Modified
- `deploy/terraform/qa/versions.tf` - Project tag updated from loan-engine to intrepid-poc
- `deploy/terraform/qa/key-pair.tf` - key_name and Name tag updated to intrepid-poc-qa
- `deploy/terraform/qa/deploy-qa.ps1` - ECS update-service now uses terraform output -raw for cluster/service names
- `deploy/terraform/qa/terraform.tfvars.example` - Rewrote with intrepid-poc values; added ecr_repository_name; sanitized db_password
- `deploy/terraform/qa/outputs.tf` - Updated two stale descriptions from loan-engine-qa to intrepid-poc-qa
- `deploy/terraform/qa/terraform.tfvars` - Created with real credentials (gitignored, not committed)

## Decisions Made
- `deploy-qa.ps1` uses `terraform output -raw` for ECS cluster/service names: decouples the deploy script from hardcoded naming and ensures it works for any future app_name value
- `terraform.tfvars.example` db_password set to CHANGE_ME placeholder (the real value was previously committed in the example — corrected)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- None. All five file edits applied cleanly. `terraform validate` passed on first run.
- `loan-engine` remnants found only in code comments (ecr.tf:1, ecs.tf:13, s3.tf:1, versions.tf backend comment, variables.tf description) — not resource values, satisfying done criteria.

## User Setup Required

**Task 2 requires manual execution.** Run in order from `deploy/terraform/qa/`:

1. `aws sts get-caller-identity` — confirm account 014148916722 active
2. `aws s3 ls s3://intrepid-poc-qa 2>&1` — pre-flight bucket check
3. `terraform plan` — review ~25 destroy+recreate operations
4. `terraform destroy` — removes old loan-engine-* resources
5. `terraform apply` — provisions intrepid-poc-qa resources (5-15 min for RDS)

**IMPORTANT:** ECS service will show UNHEALTHY after apply — expected (no ECR image yet, that is Phase 4).

## Next Phase Readiness
- Task 1 complete: Terraform config clean, validated, and committed
- Task 2 (human gate): After `terraform apply` completes successfully, all intrepid-poc-qa AWS resources will be provisioned
- Phase 4 (CI/CD) can then push Docker image to ECR and trigger ECS deployment

---
*Phase: 03-aws-infrastructure*
*Completed: 2026-03-06 (Task 1 done; Task 2 pending human action)*
