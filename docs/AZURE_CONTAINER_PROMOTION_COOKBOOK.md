# Azure Container Promotion Cookbook

A short reference for promoting a Docker application from local/AWS to Azure Container Apps,
based on lessons learned in this project.

---

## Prerequisites

- Azure CLI installed and logged in (`az login`)
- Docker installed and daemon running
- Terraform >= 1.5 (if using IaC path)
- Contributor role on the target Resource Group (subscription-level not required for most steps)

---

## Step 1 — Provision Azure Container Registry (ACR)

If using Terraform (recommended), ACR is declared as:

```hcl
resource "azurerm_container_registry" "main" {
  name                = "<unique-name>acr"   # max 50 chars, alphanumeric only
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false
}
```

> **Gotcha:** `admin_enabled = false` is more secure but requires managed identity auth (see Step 3).

Or via CLI:
```bash
az acr create --name <acrName> --resource-group RG-Intrepid-POC --sku Basic
```

---

## Step 2 — Build and Push the Docker Image

```bash
# Authenticate Docker to ACR
az acr login --name <acrName>

# Build image (from project root)
docker build -t <acrName>.azurecr.io/<app-name>:<tag> .

# Push
docker push <acrName>.azurecr.io/<app-name>:<tag>
```

For CI/CD pipelines use a service principal:
```bash
az ad sp create-for-rbac --name <sp-name> --role AcrPush \
  --scopes /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.ContainerRegistry/registries/<acrName>
```

---

## Step 3 — Grant Container App Pull Access (AcrPull)

**This step requires Owner or User Access Administrator role.**
If you only have Contributor, the role assignment must be done by an admin.

```bash
# After the managed identity is created, get its principal ID
az identity show \
  --name <app-identity-name> \
  --resource-group RG-Intrepid-POC \
  --query principalId -o tsv

# Assign AcrPull
az role assignment create \
  --assignee <principal_id> \
  --role AcrPull \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.ContainerRegistry/registries/<acrName>
```

> **Learned the hard way:** Terraform's `azurerm_role_assignment` requires Owner/UAA.
> Comment it out of Terraform and run this manually, or ask an admin.

---

## Step 4 — Register Required Resource Providers

If deploying to a subscription for the first time, these providers may not be registered.
Requires subscription-level permissions (admin action).

```bash
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.KeyVault

# Check status (wait for "Registered")
az provider show --namespace Microsoft.App --query registrationState -o tsv
```

---

## Step 5 — Deploy to Azure Container Apps

Minimal Terraform skeleton for Container Apps:

```hcl
resource "azurerm_container_app_environment" "main" {
  name                       = "<name>-env"
  location                   = data.azurerm_resource_group.main.location
  resource_group_name        = data.azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
}

resource "azurerm_container_app" "main" {
  name                         = "<name>-app"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  template {
    container {
      name   = "<app-name>"
      image  = "<acrName>.azurecr.io/<app-name>:<tag>"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
    }
  }

  secret {
    name  = "database-url"
    value = var.database_url
  }
}
```

Or via CLI for a quick test deploy:
```bash
az containerapp create \
  --name <app-name> \
  --resource-group RG-Intrepid-POC \
  --environment <env-name> \
  --image <acrName>.azurecr.io/<app-name>:<tag> \
  --registry-server <acrName>.azurecr.io \
  --user-assigned <identity-resource-id> \
  --target-port 8000 \
  --ingress external
```

---

## Step 6 — Secrets and Config

Prefer Key Vault references over inline secrets in production.

```bash
# Store a secret
az keyvault secret set \
  --vault-name <kvName> \
  --name DATABASE-URL \
  --value "postgresql://user:pass@host:5432/db?sslmode=require"

# Grant Container App identity access
az keyvault set-policy \
  --name <kvName> \
  --object-id <principal_id> \
  --secret-permissions get list
```

In Terraform, use `azurerm_key_vault_secret` and reference via Container App secrets.

---

## Permissions Quick Reference

| Action | Required Role | Scope |
|---|---|---|
| Create/manage resources | Contributor | Resource Group |
| Push images to ACR | AcrPush | ACR resource |
| Pull images (managed identity) | AcrPull | ACR resource |
| Assign roles (Terraform) | Owner / User Access Admin | Resource Group |
| Register providers | Owner / Contributor | Subscription |

---

## Terraform Gotchas (from this project)

1. **Existing RG:** Use `data "azurerm_resource_group"` not `resource` if the RG already exists.
2. **Name constraints:** ACR names are globally unique, alphanumeric only, 5–50 chars.
   Use a random suffix: `random_string.suffix` to avoid collisions.
3. **Role assignments:** Comment them out of Terraform if you lack Owner; do them manually.
4. **Provider registration:** Blocked deployments are often just unregistered providers — check first.
5. **State:** Keep `terraform.tfvars` with passwords out of git. Use `.gitignore`.

---

## Promote a New Image Version

```bash
# Build and tag
docker build -t <acrName>.azurecr.io/<app-name>:v2 .
az acr login --name <acrName>
docker push <acrName>.azurecr.io/<app-name>:v2

# Update Container App revision
az containerapp update \
  --name <app-name> \
  --resource-group RG-Intrepid-POC \
  --image <acrName>.azurecr.io/<app-name>:v2
```

Or update the `image` field in Terraform and run `terraform apply`.

---

*Based on intrepid-poc Azure DR deployment (2026-03-21). Subscription: TWGGLOBAL_DEV.*
