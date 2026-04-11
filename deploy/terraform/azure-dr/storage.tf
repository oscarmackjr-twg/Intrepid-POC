resource "azurerm_storage_account" "main" {
  name                     = local.storage_account_name
  resource_group_name      = data.azurerm_resource_group.main.name
  location                 = data.azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}

resource "azurerm_storage_share" "appdata" {
  name                 = var.app_file_share_name
  storage_account_name = azurerm_storage_account.main.name
  quota                = 100
}

resource "azurerm_storage_container" "artifacts" {
  name                  = var.artifact_blob_container_name
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "db_dumps" {
  name                  = var.db_dump_blob_container_name
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}
