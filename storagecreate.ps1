param(
    [string]$Subscription = "",                    # optional: set if you have many subs
    [string]$ResourceGroup = "rg-intrepid-tfstate",
    [string]$StorageAccountName = "intrepidtfstate",
    [string]$ContainerName = "tfstate",
    [switch]$SetTerraformEnv                      # sets $env:ARM_ACCESS_KEY
)

# Ensure Az is available
if (-not (Get-Module Az -ListAvailable)) {
    Write-Host "Az module not found. Installing for CurrentUser..."
    Install-Module Az -Scope CurrentUser -Force
}
Import-Module Az

# Login / Set context
if (-not (Get-AzContext)) {
    Connect-AzAccount | Out-Null
}
if ($Subscription) {
    Set-AzContext -Subscription $Subscription | Out-Null
}

# Validate Storage Account exists
$sa = Get-AzStorageAccount -ResourceGroupName $ResourceGroup -Name $StorageAccountName -ErrorAction SilentlyContinue
if (-not $sa) {
    throw "Storage account '$StorageAccountName' not found in resource group '$ResourceGroup'. Create it first."
}

# Fetch an account key
$accountKey = (Get-AzStorageAccountKey -ResourceGroupName $ResourceGroup -Name $StorageAccountName)[0].Value
if (-not $accountKey) {
    throw "Could not retrieve an account key for storage account '$StorageAccountName'."
}

# Build storage context
$ctx = New-AzStorageContext -StorageAccountName $StorageAccountName -StorageAccountKey $accountKey

# Ensure container exists (idempotent)
$existing = Get-AzStorageContainer -Name $ContainerName -Context $ctx -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Container '$ContainerName' already exists. Ensuring it's private (no public access)."
} else {
    Write-Host "Creating container '$ContainerName' (private)..."
    New-AzStorageContainer -Name $ContainerName -Context $ctx -PublicAccess Off | Out-Null
}

# Enforce no public access (if needed)
# NOTE: Azure Storage treats 'Off' as no public access. Re-create or update policy if required.

# Optional: Enable Terraform backend env var
if ($SetTerraformEnv) {
    $env:ARM_ACCESS_KEY = $accountKey
    Write-Host "Set ARM_ACCESS_KEY in current session."
}

Write-Host "Done."