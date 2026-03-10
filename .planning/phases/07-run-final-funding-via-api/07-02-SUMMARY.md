---
phase: 07-run-final-funding-via-api
plan: 02
subsystem: infrastructure
tags: [terraform, security, git, networking, rds, alb, tls]
dependency_graph:
  requires: []
  provides: [rds-private-subnets, alb-https-listener, tightened-sg-egress, clean-git-index]
  affects: [deploy/terraform/qa]
tech_stack:
  added: []
  patterns: [count-gated-resource, sg-referenced-sg-egress]
key_files:
  created: []
  modified:
    - deploy/terraform/qa/rds.tf
    - deploy/terraform/qa/alb.tf
    - deploy/terraform/qa/security-groups.tf
    - deploy/terraform/qa/variables.tf
    - .gitignore
decisions:
  - id: HARD-01
    summary: RDS moved to private subnets (aws_subnet.private[*].id, publicly_accessible=false); ALB HTTP redirects to HTTPS with count-gated HTTPS listener; ECS SG egress tightened to specific ports (5432, 443, 53/udp)
  - id: HARD-07
    summary: app-bundle.zip removed from git tracking via git rm --cached; deploy/aws/eb/*.zip added to .gitignore to block future bundles
metrics:
  duration_seconds: 163
  completed_date: "2026-03-10"
  tasks_completed: 2
  files_modified: 5
---

# Phase 7 Plan 02: Infrastructure Hardening (Git Hygiene + Terraform Networking) Summary

Remove tracked EB bundle from git (HARD-07) and harden Terraform: RDS private subnets, ALB HTTPS redirect, and tightened ECS/RDS security group egress (HARD-01).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Repository hygiene — remove tracked EB bundle, verify PEM gitignore | c2a7f0d | .gitignore, deploy/aws/eb/app-bundle.zip |
| 2 | Terraform — RDS private subnets, ALB HTTPS, SG egress tightening | ba2b665 | rds.tf, alb.tf, security-groups.tf, variables.tf |

## Verification Results

All success criteria met:

- `git ls-files deploy/aws/eb/app-bundle.zip` returns empty
- `.gitignore` contains `deploy/aws/eb/*.zip`
- `terraform validate` passes: "Success! The configuration is valid."
- `rds.tf`: `publicly_accessible = false` and `aws_subnet.private[*].id`
- `alb.tf`: HTTP redirect listener (port 80 -> 443 HTTP_301) + count-gated HTTPS listener
- `variables.tf`: `acm_certificate_arn` variable with `default = ""`
- `security-groups.tf`: open 0.0.0.0/0 egress removed for ECS and RDS; specific port rules added

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1 work already present in commit c2a7f0d**
- **Found during:** Task 1 execution
- **Issue:** Plan 07-06 had already applied the .gitignore and git rm --cached changes (commit c2a7f0d). The app-bundle.zip was already untracked and .gitignore already contained `deploy/aws/eb/*.zip`.
- **Fix:** Verified done criteria were met, skipped re-doing the work, proceeded to Task 2 directly. Task 1 commit recorded as c2a7f0d.
- **Files modified:** .gitignore (already done)
- **Commit:** c2a7f0d

## Key Decisions Made

1. **HTTP redirect without cert**: When `acm_certificate_arn = ""` (default), the HTTP listener still redirects to HTTPS 443 via `HTTP_301`. This means the app will not be HTTP-accessible until a cert is provided. This is intentional — it enforces HTTPS infrastructure as the default path.

2. **RDS egress removed entirely**: The `rds_all` 0.0.0.0/0 egress rule was removed with no replacement rules. RDS (Postgres) does not initiate outbound connections. A comment was added in security-groups.tf to document this intentional omission.

3. **ECS egress via referenced SG**: `ecs_to_rds` uses `referenced_security_group_id` (security group reference) rather than a CIDR, so it tracks the RDS SG dynamically without needing to know the CIDR range.

## Self-Check: PASSED

- deploy/terraform/qa/rds.tf: FOUND
- deploy/terraform/qa/alb.tf: FOUND
- deploy/terraform/qa/security-groups.tf: FOUND
- deploy/terraform/qa/variables.tf: FOUND
- Commit ba2b665: FOUND (feat(07-02): harden AWS networking)
- Commit c2a7f0d: FOUND (feat(07-06): add security-quality-gate CI job)
- terraform validate: PASSED
