# CI/CD Runbook — intrepid-poc

This runbook documents the GitHub Actions deploy pipeline for `intrepid-poc`. It covers required secrets/variables, first-time OIDC setup, and deploy sequence.

---

## Overview

On every push to `main`, the workflow `.github/workflows/deploy-test.yml` runs:

1. **Authenticate to AWS** via GitHub OIDC (no stored credentials)
2. **Build Docker image** from `deploy/Dockerfile` and push to ECR (`intrepid-poc-qa`)
3. **Run Alembic migrations** as an ECS one-off task — **aborts deploy if migrations fail**
4. **Update ECS service** with `--force-new-deployment`
5. **Wait for stability** — blocks until the new task is healthy (~10 min max)

A green workflow run means: image is live in ECR, migrations applied, new task is healthy and serving traffic.

---

## GitHub Secrets and Variables

Configure in the GitHub repo under **Settings → Secrets and variables → Actions**.

### Repository Variables (not secrets — not sensitive)

| Variable | Example Value | Source | Required |
|----------|---------------|--------|----------|
| `AWS_ROLE_ARN` | `arn:aws:iam::014148916722:role/github-actions-intrepid-poc-qa` | `terraform output github_actions_role_arn` in `deploy/terraform/qa/` | Yes |
| `ECS_SUBNET_IDS` | `subnet-abc123,subnet-def456` | `terraform output ecs_subnet_ids` | Yes |
| `ECS_SECURITY_GROUP` | `sg-xyz789` | `terraform output ecs_security_group_id` | Yes |
| `AWS_REGION` | `us-east-1` | Fixed for this project | No (defaults to `us-east-1`) |

### Repository Secrets

None required. The pipeline uses OIDC — no `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` are stored or needed.

---

## First-time OIDC Setup

This is a one-time setup. Once complete, the pipeline is self-sustaining.

### Step 1: Determine GitHub repo owner

Find the org/username that owns the `intrepid-poc` repository. It appears in the GitHub URL:
`https://github.com/OWNER/intrepid-poc`

### Step 2: Check for existing OIDC provider in AWS account

```powershell
aws iam list-open-id-connect-providers `
  --query "OpenIDConnectProviderList[*].Arn" `
  --output text
```

If output contains `token.actions.githubusercontent.com`, the provider already exists (see `github-oidc.tf` comments — it uses a `data` source in that case, not a `resource`).

### Step 3: Apply Terraform OIDC resources

```powershell
cd deploy\terraform\qa
terraform plan -out=oidc.tfplan
terraform apply oidc.tfplan
```

The plan should show new resources: the OIDC provider (if not pre-existing), the IAM role `github-actions-intrepid-poc-qa`, and its inline policy. No existing resources should be modified or destroyed.

### Step 4: Capture Terraform outputs

```powershell
terraform output github_actions_role_arn
terraform output ecs_subnet_ids
terraform output ecs_security_group_id
```

### Step 5: Set GitHub repo variables

In the GitHub repo, go to **Settings → Secrets and variables → Actions → Variables → New repository variable**:

| Variable name | Value |
|--------------|-------|
| `AWS_ROLE_ARN` | ARN from `github_actions_role_arn` output |
| `ECS_SUBNET_IDS` | Comma-separated IDs from `ecs_subnet_ids` output |
| `ECS_SECURITY_GROUP` | ID from `ecs_security_group_id` output |

### Step 6: Trigger a test deploy

Push a commit to `main` and watch the Actions run. All steps should complete green.

---

## First Deploy Checklist

After the first successful CI/CD deploy (GitHub Actions workflow green), complete these one-time steps to make the staging environment usable.

### Step 1: Verify the staging URL loads

Open in a browser:
```
http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com
```
The Loan Engine login page should appear with an amber "STAGING — Not Production" banner at the top.

### Step 2: Seed the staging admin user

Run the seed script as an ECS one-off task. Retrieve subnet and security group values from Terraform outputs (already set as GitHub repo variables):

```powershell
# Get values from Terraform outputs
cd deploy\terraform\qa
$SUBNET_IDS = terraform output -raw ecs_subnet_ids    # comma-separated, e.g. subnet-abc,subnet-def
$SG_ID = terraform output -raw ecs_security_group_id  # e.g. sg-xyz789

# Run seed script as ECS one-off task
$TASK_ARN = aws ecs run-task `
  --cluster intrepid-poc-qa `
  --task-definition intrepid-poc-qa `
  --launch-type FARGATE `
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" `
  --overrides '{\"containerOverrides\":[{\"name\":\"app\",\"command\":[\"python\",\"scripts/seed_staging_user.py\"]}]}' `
  --query 'tasks[0].taskArn' `
  --output text
echo "Task: $TASK_ARN"

# Wait for completion
aws ecs wait tasks-stopped --cluster intrepid-poc-qa --tasks $TASK_ARN

# Check exit code (0 = success)
aws ecs describe-tasks --cluster intrepid-poc-qa --tasks $TASK_ARN `
  --query 'tasks[0].containers[?name==`app`].exitCode' --output text
```

The script is idempotent — safe to run again if needed (updates password if user exists).

### Step 3: Verify Ops login and upload

1. Open the staging URL in a browser
2. Log in as `admin` with the staging password (see `backend/scripts/seed_staging_user.py`)
3. Navigate to File Manager
4. Upload a sample loan spreadsheet from `backend/data/sample/`
5. Confirm the file is accepted (no error, appears in the file list)

### Troubleshooting seed script failures

Check CloudWatch Logs for the seed task:
- Log group: `/ecs/intrepid-poc-qa`
- Filter by the task ARN shown above
- Common cause: `ModuleNotFoundError` — ensure the task definition WORKDIR is `/app` and the command is `["python", "scripts/seed_staging_user.py"]` (relative path, not absolute)

---

## Deploy Sequence

Each workflow step and what to do if it fails:

| Step | What it does | Failure means |
|------|-------------|---------------|
| Configure AWS (OIDC) | Exchanges GitHub OIDC JWT for temporary AWS credentials | Wrong `AWS_ROLE_ARN`, wrong repo owner in trust policy, or `id-token: write` permission missing |
| Login to ECR | Authenticates Docker to the ECR registry | OIDC role missing ECR `GetAuthorizationToken` permission |
| Build and push image | Builds `deploy/Dockerfile` from repo root, tags with commit SHA and `latest`, pushes to `intrepid-poc-qa` ECR | Docker build error, ECR repo doesn't exist, or OIDC role missing ECR push permissions |
| Run Alembic migration | Launches ECS one-off task with `alembic upgrade head` command override | `iam:PassRole` missing, wrong subnet/SG IDs, or task definition not found |
| Wait for migration | Blocks until migration task reaches STOPPED state (~10 min max) | Task stuck in PENDING/RUNNING (infrastructure issue) |
| Check migration exit code | Reads container exit code via `describe-tasks` — fails workflow if non-zero | Alembic migration script error — check CloudWatch logs for `/ecs/intrepid-poc-qa` |
| Deploy to ECS | Calls `update-service --force-new-deployment` | OIDC role missing `ecs:UpdateService` permission |
| Wait for service stability | Blocks until new task is healthy — 40 attempts × 15s = ~10 min max | New container crashes on startup (check CloudWatch logs) or health check failing |
| Deployment summary | Prints image URI and cluster/service names | Never fails |

---

## Troubleshooting

### "AccessDenied" at Configure AWS step
The OIDC role assumption failed. Check:
1. `AWS_ROLE_ARN` repo variable is set and matches the role ARN in IAM
2. The trust policy `sub` condition exactly matches `repo:OWNER/intrepid-poc:ref:refs/heads/main` (substituting the actual owner)
3. The trust policy uses `StringEquals` (not `StringLike`) — `StringLike` with `*` would allow all branches

### "AccessDeniedException: iam:PassRole" at Run migration step
The OIDC role is missing `iam:PassRole` for the ECS execution and task roles. Verify the deploy policy in `deploy/terraform/qa/github-oidc.tf` includes `iam:PassRole` for `ecsTaskExecution-intrepid-poc-qa-*` and `ecsTaskRole-intrepid-poc-qa-*`.

### "InvalidParameterException: Network Configuration must be provided" at Run migration step
The `ECS_SUBNET_IDS` or `ECS_SECURITY_GROUP` repo variables are missing or malformed. Verify the values match `terraform output ecs_subnet_ids` and `terraform output ecs_security_group_id`. Subnet IDs must be comma-separated with no spaces.

### Migration exit code check fails (exit code non-zero)
Alembic failed to apply a migration. Check CloudWatch Logs:
- Log group: `/ecs/intrepid-poc-qa`
- Filter by the migration task ARN (shown in workflow logs)
- Common causes: bad SQL in a migration script, RDS connection failure, wrong `DATABASE_URL`

### "Wait services-stable" times out after ~10 minutes
The new ECS task failed to reach a healthy state. Check:
- CloudWatch Logs for the app container (startup crash, port bind failure)
- ALB target group health checks (target group deregistration events)
- ECS service events in the AWS console

---

## Infrastructure Reference

| Resource | Name / ARN |
|----------|-----------|
| AWS Account | `014148916722` |
| Region | `us-east-1` |
| ECR repository | `014148916722.dkr.ecr.us-east-1.amazonaws.com/intrepid-poc-qa` |
| ECS cluster | `intrepid-poc-qa` |
| ECS service | `intrepid-poc-qa` |
| ECS task definition family | `intrepid-poc-qa` |
| CloudWatch log group | `/ecs/intrepid-poc-qa` |
| GitHub Actions IAM role | `github-actions-intrepid-poc-qa` |
| Secrets Manager prefix | `intrepid-poc/qa/` |
| Terraform config | `deploy/terraform/qa/` |
