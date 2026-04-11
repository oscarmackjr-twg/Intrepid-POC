# Azure DR — Phase 0: Bootstrap

**Owner:** Dev/Ops
**Estimated effort:** 1–2 days
**Goal:** Create all one-time prerequisites that must exist before Terraform can run.

---

## Checklist

```
☐ 2.  Terraform backend storage account and container created
☐ 3.  GitHub OIDC configured and secrets added to repo
☐ 4.  DNS owner and cutover method decided and written down
☐ 5a. Terraform >= 1.6.0 installed
☐ 5b. Azure CLI installed and az login works
☐ 5c. Docker Desktop installed and daemon running
☐ 5d. psql, pg_dump, pg_restore installed
☐ 5e. AWS CLI installed and configured
```

---

## Step 2 — Create the Terraform backend storage account

Terraform stores its state file (the record of everything it created) in Azure Blob Storage.
This must exist before you can run `terraform init`.

### 2.1 Log in and set your subscription

```powershell
az login

# List all subscriptions visible to your account
az account list --output table

# Set the one you want to use
az account set --subscription "<your-subscription-id>"

# Confirm
az account show --query "{name:name, id:id}" --output table
```

> **Troubleshooting — SubscriptionNotFound:**
> If you see `SubscriptionNotFound`, your CLI is logged in to the wrong tenant.
> Try: `az login --tenant "<your-tenant-id-or-domain.onmicrosoft.com>"`
> Then re-run `az account list --all --output table` to find your subscription.

### 2.2 Create the resource group for Terraform state

```powershell
az group create `
  --name "rg-intrepid-tfstate" `
  --location "eastus"
```

### 2.3 Create the storage account

The name must be globally unique, 3–24 chars, lowercase letters and numbers only.

```powershell
az storage account create `
  --name "intrepidtfstatesa" `
  --resource-group "rg-intrepid-tfstate" `
  --location "eastus" `
  --sku Standard_LRS `
  --kind StorageV2
```

### 2.4 Create the blob container

```powershell
az storage container create `
  --name "tfstate" `
  --account-name "intrepidtfstatesa"
```

### 2.5 Record these values — you will need them in Phase 1

| Setting | Value |
|---|---|
| Resource group | `rg-intrepid-tfstate` |
| Storage account | `intrepidtfstatesa` |
| Container | `tfstate` |
| State key | `azure-dr/terraform.tfstate` |

These values go into `deploy/terraform/azure-dr/versions.tf` when you run `terraform init` in Phase 1.
The backend block is already written there — it just needs to be uncommented and filled in.

---

## Step 3 — Set up GitHub Actions identity (OIDC)

OIDC lets GitHub Actions authenticate to Azure without storing a password.
It is the recommended approach.

### 3.1 Create an App Registration

```powershell
az ad app create --display-name "github-intrepid-poc-dr"
```

Copy the `appId` value from the output. You will use it in the next steps.

### 3.2 Create a service principal for the app

```powershell
az ad sp create --id "<appId-from-3.1>"
```

### 3.3 Assign Contributor access to your subscription

```powershell
az role assignment create `
  --role "Contributor" `
  --assignee "<appId-from-3.1>" `
  --scope "/subscriptions/<your-subscription-id>"
```

### 3.4 Add the federated credential for the main branch

```powershell
az ad app federated-credential create `
  --id "<appId-from-3.1>" `
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:oscarmackjr-twg/Intrepid-POC:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### 3.5 Add GitHub repository secrets

Go to your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**.

| Secret name | How to get the value |
|---|---|
| `AZURE_CLIENT_ID` | The `appId` from step 3.1 |
| `AZURE_TENANT_ID` | `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id -o tsv` |

### Alternative: service principal with password (simpler, less secure)

If OIDC is too much complexity right now, you can use a JSON credential secret instead
and migrate to OIDC later:

```powershell
az ad sp create-for-rbac `
  --name "github-intrepid-poc-dr" `
  --role "Contributor" `
  --scopes "/subscriptions/<your-subscription-id>" `
  --sdk-auth
```

Copy the entire JSON output and add it as a single GitHub secret named `AZURE_CREDENTIALS`.

---

## Step 4 — Decide DNS ownership and cutover method

Fill this in and share with your team before rehearsing a cutover.

| Setting | Your value |
|---|---|
| Current public DNS record | e.g. `app.intrepid.yourdomain.com` |
| Current DNS target (AWS) | `intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com` |
| DNS hosted at | e.g. Route53 / Cloudflare / Azure DNS |
| Cutover method | Automated (Azure DNS) **or** Manual (registrar login) |
| Current TTL | e.g. 3600 — lower to 300 at least 1 day before any rehearsal |
| Who performs the DNS change | name / role |

**On TTL:** If your TTL is 3600 (1 hour), lower it to 300 (5 minutes) at least one day
before a planned cutover. That limits how long users are stuck on the old endpoint after
the DNS record is updated.

---

## Step 5 — Install local tools

### 5a — Terraform (>= 1.6.0 required)

```powershell
winget install HashiCorp.Terraform

# Verify
terraform -version
# Expected: Terraform v1.6.x or higher
```

If winget is unavailable, download the binary from https://developer.hashicorp.com/terraform/downloads
and place the `.exe` somewhere on your PATH.

### 5b — Azure CLI

```powershell
winget install Microsoft.AzureCLI

# Verify
az version
az login
```

### 5c — Docker Desktop

Download from https://docs.docker.com/desktop/install/windows-install/

After installing, enable **"Use WSL 2 based engine"** in Docker Desktop Settings.

```powershell
# Verify (both Client and Server must appear)
docker version
```

### 5d — PostgreSQL client tools

You need only the client tools, not a full server.

```powershell
winget install PostgreSQL.PostgreSQL

# Verify
psql --version
pg_dump --version
pg_restore --version
```

If the commands are not found after install, add PostgreSQL's `bin` folder to your PATH:
`C:\Program Files\PostgreSQL\16\bin` (adjust the version number to match what was installed).

### 5e — AWS CLI

```powershell
winget install Amazon.AWSCLI

# Verify
aws --version

# Configure credentials
aws configure
# Enter: Access Key ID, Secret Access Key, region=us-east-1, output=json

# Smoke test — list the QA S3 bucket
aws s3 ls s3://intrepid-poc-qa
```

---

## Phase 0 complete — ready for Phase 1 when all of the following are true

```
☐ az account show returns your subscription with State=Enabled
☐ Terraform backend storage account and container exist in Azure
☐ terraform -version shows >= 1.6.0
☐ docker version shows Client and Server
☐ psql --version, pg_dump --version, pg_restore --version all work
☐ aws s3 ls s3://intrepid-poc-qa returns file listing without error
☐ GitHub secrets AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID are set
☐ DNS cutover method is decided and written down in the table above
☐ DNS TTL lowered (or scheduled to be lowered before rehearsal)
```

Proceed to `AZURE_DR_PHASE_1.md`.
