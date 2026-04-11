# Migration Analysis: AWS to Azure DR

## Date

- 2026-03-11

## Scope

This document captures the working analysis completed for:

- review of the current AWS Terraform deployment
- recommendation for an Azure Level 1 disaster recovery deployment
- implementation planning and cutover guidance
- cashflow launcher portability analysis for Azure and AWS

This is intended as a checkpoint document so the work can resume later without repeating discovery.

## Current AWS Deployment Summary

The current deployed model is a React/Node/Python application using PostgreSQL on AWS with Terraform.

Primary AWS services in scope:

- ECS Fargate
- RDS PostgreSQL
- ALB
- S3
- ECR
- SES
- Secrets Manager

Terraform reviewed in repo:

- [deploy/terraform/qa](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa)

## AWS Terraform Review Findings

### High Severity

1. ALB listener behavior can break access in the default configuration.

- HTTP always redirects to HTTPS in [alb.tf](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa/alb.tf#L37).
- HTTPS listener is only created when `acm_certificate_arn` is set in [alb.tf](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa/alb.tf#L53).
- Default `acm_certificate_arn` is empty in [variables.tf](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa/variables.tf#L128).
- Result: a default deployment can redirect users to port 443 when no 443 listener exists.

2. Secret and state handling are weak for a shared DR-capable process.

- Terraform backend is not configured in [versions.tf](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa/versions.tf#L15).
- State is local by default.
- `db_password` and full `DATABASE_URL` are handled in Terraform-managed resources in [rds.tf](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa/rds.tf#L21) and [secrets.tf](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa/secrets.tf#L14).
- README documents a fixed QA password in [README.md](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa/README.md#L32).

### Medium Severity

3. Database recovery posture is not production-grade.

- `backup_retention_period = 7`
- `skip_final_snapshot = true`
- no visible Multi-AZ or replica configuration
- see [rds.tf](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa/rds.tf#L15)

4. Runtime settings still look partly dev-oriented.

- `LOCAL_DEV_MODE = true` in ECS task env in [ecs.tf](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa/ecs.tf#L47)
- ECS tasks run in public subnets with public IPs in [ecs.tf](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa/ecs.tf#L137)
- cashflow workers also use public subnet launch settings in [ecs.tf](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/qa/ecs.tf#L66)

5. The stated AWS architecture and Terraform code do not fully match.

Not all declared operational features were visible in this Terraform folder. In particular, the reviewed QA Terraform did not show full provisioning for:

- SES
- Route53
- WAF
- autoscaling
- alarms
- certificate provisioning

This likely means some environment behavior is outside Terraform or managed elsewhere.

## Azure DR Recommendation

### Recommended DR Level

Start with a Level 1 warm-standby Azure deployment.

Characteristics:

- Azure infrastructure exists ahead of time
- application image is deployable and health-checked
- database recovery uses dump-and-restore
- file recovery uses export-and-restore
- DNS cutover is manual

Expected operating targets:

- RPO: up to 24 hours unless exports are run more frequently
- RTO: about 2 to 8 hours

### AWS to Azure Mapping

- ECS Fargate -> Azure Container Apps
- RDS PostgreSQL -> Azure Database for PostgreSQL Flexible Server
- S3 -> Azure Storage Account with Blob plus Azure Files where needed
- ECR -> Azure Container Registry
- Secrets Manager -> Azure Key Vault
- ALB -> Azure Front Door or Application Gateway
- SES -> Azure Communication Services Email

### Important Constraint

The current application is not yet cloud-neutral.

Storage and remote execution constraints found in the codebase:

- app storage supports `local` and `s3`, not Azure Blob
- cashflow remote execution supports AWS ECS-specific behavior

Because of that, the practical Level 1 Azure approach is:

- `STORAGE_TYPE=local`
- Azure Files mounted into the app container
- `CASHFLOW_EXECUTION_MODE=local`

That avoids a full app rewrite in the first DR milestone.

## Azure DR Delivery Plan

### Bootstrap Resources Required In Advance

These should exist before normal Terraform-driven DR work begins:

- Azure subscription and access model
- Terraform backend storage account and blob container
- CI/CD identity such as workload identity or service principal
- DNS ownership and cutover decision
- sender/domain verification if email is later moved to Azure Communication Services
- DR package process for database dump and file export

### Resources Terraform Can Create On Demand

For the proposed Azure DR stack, Terraform can create:

- resource group
- log analytics workspace
- storage account
- Azure Files share
- blob containers for DR artifacts
- key vault
- PostgreSQL flexible server
- application database
- container registry
- user-assigned managed identity
- container apps environment
- container app for the web/API workload
- role assignments for ACR pull

### Junior-Friendly Effort Estimate

- bootstrap and backend: 1 to 2 days
- Azure infrastructure build-out: 2 to 4 days
- secrets, image publish, storage, identity setup: 2 to 3 days
- DR package and restore flow: 2 to 4 days
- cutover testing and rehearsal: 2 to 3 days

Total estimate:

- about 2 to 3 weeks for a junior Dev/Ops engineer with senior review support

## Cutover Checklist Summary

### T-7 Days

- verify Azure access
- verify Terraform backend
- verify Azure DR stack still exists
- verify ACR image is available
- verify latest DB dump package exists
- verify latest file export package exists
- confirm DNS TTL

### T-1 Day

- freeze nonessential changes
- export fresh PostgreSQL dump from AWS
- export fresh S3 data package from AWS
- upload latest package to Azure
- verify Azure health endpoint
- verify Azure PostgreSQL access

### Cutover Start

- announce event and record start time
- record AWS endpoint and current DNS target
- restore DB into Azure
- restore files into Azure
- run readiness checks
- run smoke tests against Azure direct endpoint

### DNS Change

- update public CNAME to Azure target
- wait for TTL window
- verify public resolution
- verify app workflows

### Post-Cutover

- record duration
- record fixes performed
- preserve logs and manifest

## Cashflow Portability Analysis

### Recommendation

Refactor the cashflow feature around:

1. storage
2. execution backend

Do not refactor around business mode (`current_assets`, `sg`, `cibc`). Those are not the deployment boundary.

### Current Coupling Points

The compute logic itself is mostly portable. The main portability problems are in orchestration.

#### 1. Cashflow API is hard-wired to S3

Direct S3 operations are embedded in:

- [backend/cashflow/routes.py](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/cashflow/routes.py#L143)
- [backend/cashflow/routes.py](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/cashflow/routes.py#L187)
- [backend/cashflow/routes.py](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/cashflow/routes.py#L607)
- [backend/cashflow/routes.py](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/cashflow/routes.py#L619)
- [backend/cashflow/routes.py](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/cashflow/routes.py#L758)

This bypasses the existing app-wide storage abstraction in:

- [backend/storage/factory.py](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/storage/factory.py#L22)

#### 2. Worker launch is deployment-specific

Worker launch currently supports:

- AWS ECS task launch
- local subprocess launch

See:

- [backend/cashflow/routes.py](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/cashflow/routes.py#L424)

#### 3. Job persistence is ECS-shaped

The job table includes AWS-specific fields such as:

- `worker_task_arn`

See:

- [backend/cashflow/routes.py](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/cashflow/routes.py#L111)

This should become a generic worker reference field.

#### 4. Worker entrypoint depends on routes

The worker imports from the API routes module:

- [backend/cashflow/worker.py](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/cashflow/worker.py#L7)

That is the wrong dependency direction and makes future executor work harder.

#### 5. Azure local execution is only safe with one app replica

Local subprocesses are tracked in process memory:

- [backend/cashflow/routes.py](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/backend/cashflow/routes.py#L51)

If the app scales horizontally, one replica cannot safely manage jobs launched by another replica.

### What Is Not the Problem

The actual compute functions are mostly portable:

- `run_pipeline(...)`
- `run_purchase_package(...)`

They operate on local file paths inside the worker process and are not inherently tied to AWS.

The portfolio-analysis modes (`sg`, `cibc`) and `current_assets` mode are business modes, not cloud modes.

### Best Refactor Shape

Recommended module split:

- `cashflow/api.py`
  - FastAPI endpoints only
- `cashflow/job_service.py`
  - create job, update status, cancel job, reconcile state
- `cashflow/storage_service.py`
  - list inputs, upload input, download output, metadata lookups
- `cashflow/executors/base.py`
  - interface for `launch`, `cancel`, `is_active`
- `cashflow/executors/local.py`
  - subprocess execution
- `cashflow/executors/ecs.py`
  - ECS `run_task` execution
- `cashflow/runner.py`
  - `run_cashflow_job(...)` and worker main
- `cashflow/models_runtime.py`
  - runtime worker metadata

### Recommended Delivery Order

#### Short Term

1. Move worker logic out of `routes.py`.
2. Replace direct S3 calls with `get_storage_backend(...)`.
3. Introduce a generic `ExecutionBackend` interface.
4. Replace `worker_task_arn` with a generic worker reference field.
5. Run Azure with local executor mode and one replica.

#### Medium Term

6. Add a remote Azure executor implementation.
7. Keep AWS ECS executor as another implementation of the same interface.
8. Only then enable multi-replica cashflow-capable web app scaling safely.

### Final Recommendation

The smallest safe refactor is:

- keep the compute logic
- separate storage from execution
- abstract execution backend
- remove ECS-specific naming from the job model

This gives Azure support with the least regression risk and avoids rewriting the portfolio-analysis logic.

## Related Working Docs Created

Additional planning work created during this session:

- [AZURE_DR_IMPLEMENTATION_PLAN.md](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/docs/AZURE_DR_IMPLEMENTATION_PLAN.md)
- [deploy/terraform/azure-dr/README.md](/C:/Users/omack/Intrepid/pythonFramework/intrepid-poc/deploy/terraform/azure-dr/README.md)

## Suggested Next Session Starting Point

When resuming later, start with:

1. implement cashflow storage abstraction changes
2. extract execution backend interface
3. keep Azure cashflow on single-replica local execution first
4. only after that continue with Azure remote worker support
