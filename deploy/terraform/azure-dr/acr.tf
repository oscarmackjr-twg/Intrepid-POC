resource "azurerm_container_registry" "main" {
  name                = local.acr_name
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "app" {
  name                = local.app_identity_name
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = local.tags
}

# Role assignment requires Owner/User Access Administrator.
# After apply, run manually:
#   az role assignment create \
#     --assignee <app_identity_principal_id> \
#     --role AcrPull \
#     --scope <acr_resource_id>
# resource "azurerm_role_assignment" "acr_pull" {
#   scope                = azurerm_container_registry.main.id
#   role_definition_name = "AcrPull"
#   principal_id         = azurerm_user_assigned_identity.app.principal_id
# }
