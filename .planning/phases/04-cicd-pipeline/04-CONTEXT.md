# Phase 4: CI/CD Pipeline - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Update the existing `.github/workflows/deploy-test.yml` to target `intrepid-poc-qa` infrastructure provisioned in Phase 3: fix ECR/ECS names, add GitHub OIDC authentication via Terraform, add an explicit Alembic migration step (ECS one-off task), wait for ECS stability, and create a CICD runbook documenting all required secrets/variables and OIDC setup. Phase ends when a push to main triggers the full pipeline end-to-end without manual steps.

</domain>

<decisions>
## Implementation Decisions

### AWS Authentication
- Use GitHub OIDC + IAM role — no static long-lived credentials stored in GitHub
- OIDC IAM role created via Terraform (new `github-oidc.tf` in `deploy/terraform/qa/`)
- Trust policy restricted to repo + `refs/heads/main` only (no other branches or PRs)
- Workflow uses `aws-actions/configure-aws-credentials@v4` with `role-to-assume` (not access keys)
- No `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` secrets needed — replace with `AWS_ROLE_ARN` repo variable

### Migration Execution
- Run `alembic upgrade head` as an explicit ECS one-off task **before** `update-service`
- Reuse the existing app task definition with a CMD override (`alembic upgrade head`) — no separate task definition
- If migration task exits non-zero: abort the workflow, do not proceed to `update-service`
- Container entrypoint still runs migrations on startup (belt-and-suspenders) — this is not removed

### Post-Deploy Validation
- After `update-service`, add `aws ecs wait services-stable` to block until new task is healthy
- Default wait timeout (~10 min) — if exceeded, the workflow step fails and GitHub marks the run failed
- No "warn and continue" — a timed-out wait is a failed deploy

### Secrets Documentation
- Create `docs/CICD.md` as a dedicated runbook
- Runbook covers: all required GitHub secrets and repo variables (with descriptions), and step-by-step OIDC IAM role setup (Terraform apply + GitHub repo variable config)

### Claude's Discretion
- Exact IAM policy permissions on the OIDC role (least-privilege: ECR push, ECS run-task/update-service/describe, Secrets Manager read for the intrepid-poc/qa/* path)
- Whether to rename `deploy-test.yml` to `deploy.yml` or keep the existing filename
- `aws ecs wait` timeout override if 10 min proves too short

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/deploy-test.yml`: Existing workflow with ECR login, build/push, and ECS update-service steps — needs OIDC auth swap, name fixes, and migration + wait steps added
- `deploy/Dockerfile`: Production image used in the workflow build step
- `deploy/terraform/qa/`: Full Terraform config — OIDC role goes here as `github-oidc.tf`

### Established Patterns
- Workflow already uses `aws-actions/configure-aws-credentials@v4` — supports `role-to-assume` directly (no action change needed)
- `aws-actions/amazon-ecr-login@v2` outputs `registry` for ECR URL — pattern already in place
- ECS service names from Terraform outputs: cluster `intrepid-poc-qa`, service `intrepid-poc-qa-app`
- ECR repo: `014148916722.dkr.ecr.us-east-1.amazonaws.com/intrepid-poc-qa`
- Terraform `name_prefix` pattern: `${var.app_name}-${var.environment}` → `intrepid-poc-qa`

### Integration Points
- OIDC Terraform role → GitHub repo variable `AWS_ROLE_ARN` → workflow `role-to-assume`
- ECS task definition for migration override: use `aws ecs describe-task-definition` to get latest ARN or reference Terraform output
- `secrets.tf` already stores `DATABASE_URL` as ECS secret — migration task inherits it via task role (no extra config)

</code_context>

<specifics>
## Specific Ideas

- Workflow deploy sequence: checkout → configure AWS (OIDC) → ECR login → build & push image → run migration ECS task → wait for migration → update-service → wait services-stable → summary
- OIDC trust condition: `"token.actions.githubusercontent.com:sub": "repo:{owner}/intrepid-poc:ref:refs/heads/main"` — repo owner TBD (no git remote configured locally)
- Migration task: `aws ecs run-task --cluster intrepid-poc-qa --task-definition intrepid-poc-qa-app --overrides '{"containerOverrides":[{"name":"app","command":["alembic","upgrade","head"]}]}'`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-cicd-pipeline*
*Context gathered: 2026-03-06*
