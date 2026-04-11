# Azure DR Implementation Plan

## Goal

Deliver a Level 1 disaster recovery deployment in Azure that a junior Dev/Ops engineer can deploy, rehearse, and cut over with a documented runbook.

Level 1 means:

- Azure infrastructure is prebuilt and kept warm.
- The Azure app can be started and health-checked at any time.
- Database restore is done from a prepared PostgreSQL dump package.
- File data is restored from an export package.
- Public cutover is manual DNS change.

Target outcomes:

- RPO: up to 24 hours unless exports are run more often.
- RTO: 2 to 8 hours depending on database size and DNS TTL.

## Important App Constraint

The current app is not cloud-neutral yet.

- Storage supports `local` or `s3`, not Azure Blob.
- Cashflow worker launch is AWS ECS specific when `CASHFLOW_EXECUTION_MODE=ecs_task`.

For a practical Azure Level 1 DR deployment, use:

- `STORAGE_TYPE=local`
- Azure Files mounted into the container
- `CASHFLOW_EXECUTION_MODE=local`

That avoids an application rewrite in the first DR milestone.

## Target Azure Architecture

Core runtime:

- Azure Container Registry for images
- Azure Container Apps for the web/API workload
- Azure Files share mounted into the container for persisted input/output folders
- Azure Database for PostgreSQL Flexible Server for DR database restore target
- Azure Key Vault for secrets
- Log Analytics for logs and diagnostics

Supporting operations:

- Blob containers for staged DR packages
- Optional Azure DNS cutover if the public zone is hosted in Azure

Phase 2 hardening items, not required for Level 1:

- Azure Front Door and custom domain
- Azure Communication Services Email
- Azure Container Apps Job for heavy cashflow work
- Private networking between Container Apps and PostgreSQL
- Key Vault secret references directly from the container app

## What Must Exist In Advance

These are bootstrap items. Create them once before the environment is managed routinely.

### Identity and Access

- Azure subscription with Owner or Contributor access
- `az login` working for the operator
- GitHub Actions workload identity or service principal for CI/CD

### Terraform Backend

- One Azure Storage Account for Terraform state
- One Blob container for state files
- A documented state key naming convention

### DNS and Certificates

- Public DNS zone ownership
- Decision on who owns cutover DNS updates:
  - Azure DNS automated by script
  - External DNS updated manually

### DR Package Process

- A scheduled AWS export job or manual runbook that creates:
  - PostgreSQL dump file
  - File export package from S3
  - Manifest with timestamps and source environment details

## What Terraform Will Create

Under `deploy/terraform/azure-dr`, Terraform will allocate:

- Resource group
- Log Analytics workspace
- Storage account
- Azure Files share
- Blob containers for DR artifacts
- Key Vault
- PostgreSQL Flexible Server
- PostgreSQL application database
- Container Registry
- User-assigned managed identity
- Container Apps environment
- Container app for the web/API
- Role assignments needed for ACR pull

Terraform will not perform the live cutover itself. That is handled by PowerShell scripts under `deploy/azure`.

## Implementation Phases

### Phase 0: Bootstrap

Owner: Dev/Ops

Tasks:

1. Create Azure subscription access.
2. Create Terraform backend storage account and container.
3. Set up GitHub OIDC or service principal.
4. Decide DNS owner and cutover method.
5. Install local tools:
   - Terraform
   - Azure CLI
   - Docker
   - PostgreSQL client tools (`psql`, `pg_dump`, `pg_restore`)
   - AWS CLI for export packaging

Estimated effort:

- 1 to 2 days

### Phase 1: Azure DR Infrastructure

Owner: Junior Dev/Ops with review

Tasks:

1. Fill in `terraform.tfvars`.
2. Run Terraform to create the Azure DR stack.
3. Build and push the application image to ACR.
4. Update the container app to use the real image.
5. Confirm the Azure health endpoint responds.

Estimated effort:

- 2 to 4 days

### Phase 2: DR Package Workflow

Owner: Junior Dev/Ops with DBA review

Tasks:

1. Export PostgreSQL dump from AWS.
2. Export S3 data package from AWS.
3. Upload the latest package to Azure Blob.
4. Verify package timestamp and manifest.

Estimated effort:

- 2 to 3 days

### Phase 3: Cutover Rehearsal

Owner: Dev/Ops + app owner

Tasks:

1. Restore DB into Azure PostgreSQL.
2. Restore files into Azure Files.
3. Refresh Azure app if needed.
4. Run health checks.
5. Run smoke tests.
6. Change DNS to Azure target.
7. Confirm user traffic lands in Azure.

Estimated effort:

- 1 to 2 days per rehearsal

## Junior-Friendly Task Breakdown

### Terraform Work

The junior engineer is expected to:

- copy the example `terraform.tfvars`
- fill in names, passwords, and image tag
- run `terraform init`
- run `terraform plan`
- review outputs
- run `terraform apply`

The junior engineer is not expected to:

- redesign networking
- optimize Azure security posture
- build continuous database replication in the first pass

### Scripted Operations

The junior engineer can safely run:

- image publish script
- AWS export package script
- Azure cutover script
- Azure readiness verification script

The junior engineer should escalate before:

- changing production DNS TTL strategy
- changing PostgreSQL schema during a DR rehearsal
- enabling private networking or advanced ingress changes

## Cutover Checklist

### T-7 Days

- Confirm Azure subscription access still works.
- Confirm Terraform state backend is reachable.
- Confirm Azure DR stack exists and `terraform plan` is clean or understood.
- Confirm a recent Docker image exists in ACR.
- Confirm latest PostgreSQL dump package exists.
- Confirm latest file export package exists.
- Confirm DNS TTL is at or below planned cutover value.

### T-1 Day

- Freeze nonessential infrastructure changes.
- Export a fresh PostgreSQL dump from AWS.
- Export fresh S3 data package from AWS.
- Upload the latest package to Azure Blob.
- Verify Azure app health endpoint still works.
- Verify Azure PostgreSQL server is reachable with admin credentials.

### Cutover Start

- Announce incident and start time.
- Record current AWS endpoint and current public DNS target.
- Run Azure DB restore script.
- Run Azure file restore script.
- Run Azure readiness verification script.
- Run smoke test against Azure direct endpoint.

### DNS Change

- Update public CNAME to the Azure DR target.
- Wait for TTL expiration window.
- Verify public DNS now resolves to Azure target.
- Verify login, file browsing, and a representative processing workflow.

### Post-Cutover

- Record actual cutover time.
- Record actual restore duration.
- Capture any manual fixes performed.
- Preserve logs, manifest, and validation notes.

## Verification Checklist

Azure is considered DR-ready when all of the following pass:

- `terraform output` returns expected values
- Azure Container App health endpoint returns HTTP 200
- Azure PostgreSQL accepts `select 1`
- Key Vault contains expected secrets
- Azure Files share contains expected top-level folders
- A representative app smoke test completes

## Recommended File and Package Layout

Local DR package:

```text
dr-package/
  manifest.json
  db/
    intrepid-poc.dump
  files/
    input/
    outputs/
    output_share/
```

Blob containers:

- `dr-packages`
- `db-dumps`

Azure Files top-level folders:

- `input`
- `outputs`
- `output_share`

## Scope of Effort

For the first practical Level 1 implementation:

- Planning and bootstrap: 2 days
- Azure Terraform scaffold and deployment: 3 to 5 days
- Packaging and cutover scripts: 3 to 4 days
- First rehearsal and fixes: 2 to 3 days

Total:

- About 2 to 3 weeks for a junior engineer with periodic senior review

## Definition of Done

Level 1 is complete when:

- Azure DR infrastructure is deployed from Terraform
- Application image can be published to ACR
- A DB dump can be restored into Azure PostgreSQL
- File data can be restored into Azure Files
- Azure app passes health checks after restore
- DNS cutover steps are scripted or documented and rehearsed
- The team has evidence from at least one successful rehearsal
