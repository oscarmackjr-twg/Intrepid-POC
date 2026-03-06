# Phase 3: AWS Infrastructure - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Audit and apply the existing Terraform configuration in `deploy/terraform/qa/` to provision the QA AWS environment: VPC/networking, ECR repository, RDS Postgres instance, Secrets Manager entries (DATABASE_URL, SECRET_KEY), IAM roles, ECS cluster and task definitions, ALB, and S3. This phase ends with infrastructure provisioned and verified — not with a running application (that requires a Docker image, which is Phase 4's first act).

</domain>

<decisions>
## Implementation Decisions

### Naming reconciliation
- Rename all resources from `loan-engine` naming to `intrepid-poc` naming
- Update `variables.tf` defaults to match: `app_name = "intrepid-poc"`, S3 bucket `intrepid-poc-qa`, RDS identifier `intrepid-poc-qa`, ECS cluster `intrepid-poc-qa`, ECR repo `intrepid-poc-qa`
- Update `terraform.tfvars.example` to reflect `intrepid-poc` naming throughout
- Existing `loan-engine-*` AWS resources are expendable (QA only, no real data) — Terraform destroy+recreate is acceptable
- Run `terraform plan` before `apply` to review the full list of replacements

### db_password provisioning
- Create `deploy/terraform/qa/terraform.tfvars` (gitignored) with real values for local apply
- Use the established password: `Intrepid456$%` for the new RDS instance
- Phase 4 CI/CD will use `TF_VAR_db_password` env var — document this in the tfvars.example comments

### ECS scope
- Apply full Terraform including ECS cluster, task definitions (app + cashflow-worker), and ECS service
- ECS tasks will be in a crash loop immediately after apply (no Docker image in ECR yet) — this is acceptable
- Phase 3 success criteria do not require running ECS tasks, only that the infrastructure resources exist
- Phase 4 first image push will bring the service healthy

### Verification approach
- **RDS reachability**: Connect directly via public endpoint using `psql` from local machine (RDS is `publicly_accessible = true` in QA — deliberate simplification)
- **ECR push test**: Authenticate via AWS CLI profile/SSO (`aws ecr get-login-password | docker login`) then push a test image tag to the ECR repository
- **Secrets Manager**: Verify via `aws secretsmanager get-secret-value` that DATABASE_URL and SECRET_KEY entries exist and are readable with current IAM credentials

### Claude's Discretion
- Order of Terraform file edits (variable defaults vs tfvars.example)
- Whether to use `terraform workspace` or rely on directory isolation for the qa environment
- Security group ingress rules review (confirm ECS SG allows port 5432 to RDS SG)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deploy/terraform/qa/`: Full Terraform configuration already exists — main.tf (VPC), ecr.tf, rds.tf, secrets.tf, iam.tf, ecs.tf, alb.tf, s3.tf, security-groups.tf, variables.tf, versions.tf, outputs.tf
- `.terraform.lock.hcl`: Already present — `terraform init` has been run, provider versions pinned (aws 5.100.0, random 3.8.1)
- `deploy/terraform/qa/terraform.tfvars.example`: Canonical reference for required variable values (use as template for terraform.tfvars)
- `deploy/terraform/qa/deploy-qa.ps1`: Existing PowerShell deploy script — review for whether it handles the rename

### Established Patterns
- `random_password` resource already used for `SECRET_KEY` — same pattern could be used for db_password in future, but current approach uses a known value via tfvars
- `name_prefix = "${var.app_name}-${var.environment}"` local drives all resource naming — changing `app_name` variable cascades to all resources
- ECS tasks reference ECR image as `${ecr_repository_url}:${docker_image_tag}` — image must exist before tasks can start (not before apply succeeds)
- RDS `publicly_accessible = true` is a deliberate QA simplification (commented in rds.tf)

### Integration Points
- `secrets.tf` → `iam.tf`: Secrets Manager ARNs are referenced in IAM policy for ECS task execution role and task role — both need to exist before Phase 4 can inject them as ECS secrets
- `ecs.tf` → `secrets.tf`: Task definition `secrets` block references Secrets Manager secret ARNs directly
- `ecs.tf` → `ecr.tf`: `local.ecr_image` uses `aws_ecr_repository.app.repository_url` — ECR repo must exist before ECS task definition can reference it (all in same apply)
- `variables.tf` defaults → `terraform.tfvars.example` → `terraform.tfvars`: Three-tier naming that all need to align on `intrepid-poc`

</code_context>

<specifics>
## Specific Ideas

- Run `terraform plan` output before `apply` to explicitly confirm the list of resources being destroyed (loan-engine-*) and recreated (intrepid-poc-*) — don't apply blind
- The `deploy-qa.ps1` PowerShell script may reference `loan-engine` naming internally — review it as part of the audit
- Verify `terraform.tfstate` is not tracking remote backend (should be local state in the directory) before applying

</specifics>

<deferred>
## Deferred Ideas

- Private RDS subnet (no public access) — appropriate for production but out of scope for QA in v1.0
- Terraform remote backend (S3 + DynamoDB state locking) — not needed for single-developer QA
- Terraform modules / reusable environments — future concern if a prod environment is added

</deferred>

---

*Phase: 03-aws-infrastructure*
*Context gathered: 2026-03-05*
