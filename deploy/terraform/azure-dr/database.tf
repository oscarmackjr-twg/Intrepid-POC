resource "azurerm_postgresql_flexible_server" "main" {
  name                          = local.postgres_server_name
  resource_group_name           = data.azurerm_resource_group.main.name
  location                      = data.azurerm_resource_group.main.location
  version                       = "16"
  administrator_login           = var.db_admin_username
  administrator_password        = var.db_admin_password
  zone                          = "1"
  sku_name                      = var.db_sku_name
  storage_mb                    = var.db_storage_mb
  backup_retention_days         = var.db_backup_retention_days
  public_network_access_enabled = true
  tags                          = local.tags
}

# Level 1 keeps networking simple by allowing Azure-hosted workloads to reach PostgreSQL.
# Tighten this in a later phase with private networking.
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = var.db_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}
