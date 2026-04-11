# Azure DR — Phase 1: Azure DR Infrastructure

**Owner:** Junior Dev/Ops with senior review
**Estimated effort:** 2–4 days
**Prerequisite:** Phase 0 complete (`AZURE_DR_PHASE_0.md`)
**Goal:** Deploy the full Azure DR stack from Terraform and confirm the app health endpoint responds.

---

## Checklist

```
☐ 1.  Backend block uncommented in versions.tf
☐ 2.  terraform.tfvars filled in
☐ 3.  terraform init succeeds (remote state connected)
☐ 4.  terraform plan reviewed and approved
☐ 5.  terraform apply succeeds — all resources created
☐ 6.  Docker image built and pushed to ACR
☐ 7.  Container app updated to use real image
☐ 8.  Health endpoint returns HTTP 200
```

---

## What Terraform will create

Running `terraform apply` in `deploy/terraform/azure-dr/` creates:

- Resource group `rg-intrepid-poc-dr`
- Log Analytics workspace
- Storage account with:
  - Azure Files share (`appdata`) — mounted into the container as the app's data folder
  - Blob containers `dr-packages` and `db-dumps` — for DR export packages
- Azure Key Vault — stores `DATABASE-URL` and `SECRET-KEY`
- PostgreSQL Flexible Server + application database `intrepid_poc`
- Azure Container Registry (ACR) — stores the app Docker image
- User-assigned managed identity for the container app
- Container Apps environment
- Container App for the web/API (starts with a placeholder image; replaced in step 7)
- Role assignment giving the managed identity pull access to ACR

---

## Step 1 — Uncomment the Terraform backend block

Open `deploy/terraform/azure-dr/versions.tf`.

Find the commented-out `backend "azurerm"` block and fill it in with the values
you recorded in Phase 0:

```hcl
backend "azurerm" {
  resource_group_name  = "rg-intrepid-tfstate"
  storage_account_name = "intrepidtfstatesa"
  container_name       = "tfstate"
  key                  = "azure-dr/terraform.tfstate"
}
```

Save the file.

---

## Step 2 — Create terraform.tfvars

In `deploy/terraform/azure-dr/`, create a file named `terraform.tfvars`.
This file is already in `.gitignore` so secrets will not be committed.

```hcl
# deploy/terraform/azure-dr/terraform.tfvars

# Azure region — must match the region you used in Phase 0
location = "eastus"

# Resource group for the DR stack (separate from the tfstate resource group)
resource_group_name = "rg-intrepid-poc-dr"

# Leave container_image empty for the first apply.
# Terraform will use a Microsoft placeholder image so the container app
# can be created before your real image exists in ACR.
container_image = ""

# PostgreSQL admin password — choose something strong, store it somewhere safe
db_admin_password = "<choose-a-strong-password>"

# Application secret key — use the same value as your AWS QA SECRET_KEY
# To retrieve from AWS:
#   aws secretsmanager get-secret-value --secret-id intrepid-poc/qa/SECRET_KEY --query SecretString --output text
secret_key = "<your-application-secret-key>"

# Optional: set this to your public hostname if you have one already
# Leave empty if you have not decided on a public hostname yet
public_hostname = ""
```

**All other variables have defaults** defined in `variables.tf` and do not need to be
set unless you want to override them. Key defaults:

| Variable | Default | Notes |
|---|---|---|
| `app_name` | `intrepid-poc` | Used in all resource names |
| `environment` | `dr` | Used in all resource names |
| `db_admin_username` | `intrepid_admin` | |
| `db_sku_name` | `B_Standard_B1ms` | Burstable B-series — low cost for DR warm standby |
| `db_storage_mb` | `32768` | 32 GB |
| `min_replicas` | `1` | Keep at least 1 warm replica running |
| `app_file_share_name` | `appdata` | Azure Files share name |

---

## Step 3 — terraform init

From the `deploy/terraform/azure-dr/` directory:

```powershell
cd deploy/terraform/azure-dr

terraform init
```

Expected output includes:
```
Initializing the backend...
Successfully configured the backend "azurerm"!
Terraform has been successfully initialized!
```

If you see an authentication error, make sure you are still logged in:
```powershell
az login
az account set --subscription "<your-subscription-id>"
```

---

## Step 4 — terraform plan

```powershell
terraform plan -out=tfplan
```

Review the output. You should see approximately **20–25 resources to add** and zero
resources to change or destroy.

Things to check before approving:
- Location matches what you set in `terraform.tfvars`
- Resource group name is `rg-intrepid-poc-dr` (not the tfstate group)
- PostgreSQL server name looks like `intrepidpocdr<5chars>pg`
- Container App name looks like `intrepid-poc-dr-app`
- No resources are marked as destroyed (`-`) unless you intended it

If anything looks wrong, fix `terraform.tfvars` and re-run `terraform plan` before proceeding.

---

## Step 5 — terraform apply

```powershell
terraform apply tfplan
```

This takes approximately **8–15 minutes**. PostgreSQL provisioning is the slowest step.

When it finishes you will see:
```
Apply complete! Resources: ~22 added, 0 changed, 0 destroyed.

Outputs:
  app_url            = "https://intrepid-poc-dr-app.<hash>.eastus.azurecontainerapps.io"
  acr_login_server   = "intrepidpocdr<hash>acr.azurecr.io"
  ...
```

Save the `app_url` and `acr_login_server` values — you need them in the next steps.

```powershell
# You can retrieve outputs at any time:
terraform output
```

---

## Step 6 — Build and push the application image to ACR

### 6.1 Log Docker in to your ACR

```powershell
# Get the ACR login server from Terraform output
$ACR_SERVER = $(terraform output -raw acr_login_server)

az acr login --name $ACR_SERVER
```

### 6.2 Build the image

Run from the **repository root** (not the terraform directory):

```powershell
cd <repo-root>

docker build -t "$ACR_SERVER/intrepid-poc:latest" .
```

This will take a few minutes on first build (downloading base image layers).

### 6.3 Push to ACR

```powershell
docker push "$ACR_SERVER/intrepid-poc:latest"
```

### 6.4 Confirm the image is in ACR

```powershell
az acr repository list --name $ACR_SERVER --output table

az acr repository show-tags `
  --name $ACR_SERVER `
  --repository intrepid-poc `
  --output table
```

You should see `intrepid-poc` listed with tag `latest`.

---

## Step 7 — Update the container app to use the real image

Now that the image is in ACR, update `terraform.tfvars` to point to it:

```hcl
container_image = "<acr_login_server>/intrepid-poc:latest"
# Example: container_image = "intrepidpocdr12ab3acr.azurecr.io/intrepid-poc:latest"
```

Then re-run Terraform:

```powershell
terraform plan -out=tfplan
terraform apply tfplan
```

This time only the container app will update (1–2 minutes). The plan should show
approximately 1 resource to change.

---

## Step 8 — Confirm the health endpoint responds

```powershell
# Get the app URL
$APP_URL = $(terraform output -raw app_url)

# Check the health endpoint
curl "$APP_URL/health"
# Expected: HTTP 200 with {"status": "ok"} or similar

# Or open in a browser:
Write-Host "Open: $APP_URL/health"
```

If the health check fails:

1. Check container app logs in the Azure Portal:
   - Portal → Resource Groups → `rg-intrepid-poc-dr` → Container App → Log stream
2. Check for Key Vault access errors — the managed identity must be able to read secrets
3. Check for database connection errors — PostgreSQL may still be provisioning (wait 2 minutes and retry)

---

## Phase 1 complete — Azure DR stack is live when all of the following pass

```
☐ terraform output returns app_url and acr_login_server without error
☐ curl $APP_URL/health returns HTTP 200
☐ az acr repository list shows intrepid-poc
☐ Azure Portal: PostgreSQL Flexible Server status = Available
☐ Azure Portal: Key Vault contains DATABASE-URL and SECRET-KEY secrets
☐ Azure Portal: Azure Files share appdata/ exists
```

Proceed to Phase 2 (DR Package Workflow) — exporting data from AWS and staging it in Azure
for the first cutover rehearsal.
