# Run once, by you, with local state. It creates what CI needs before CI can
# run at all: the remote-state storage, the app resource group, and the two
# GitHub OIDC identities with their role assignments. Everything else lives in
# ../ and is applied by the pipeline.
#
# Keep the generated terraform.tfstate somewhere safe (it is gitignored). If
# you lose it, `terraform import` the resources back; nothing here is stateful
# beyond the storage account itself.

terraform {
  required_version = ">= 1.10"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.10"
    }
  }
}

provider "azurerm" {
  features {}
  # Shared keys are disabled on the state account, so the provider must use Entra ID for blob calls.
  storage_use_azuread = true
  # Registration is subscription-scoped. You (Owner) can do it; the CI identities
  # are RG-scoped and can't, which is why it happens here and not in ../.
  resource_providers_to_register = [
    "Microsoft.App",
    "Microsoft.ContainerRegistry",
    "Microsoft.Consumption",
    "Microsoft.Insights",
    "Microsoft.ManagedIdentity",
    "Microsoft.OperationalInsights",
    "Microsoft.Storage",
  ]
}

variable "github_repository" {
  type        = string
  description = "GitHub repository as owner/name. Federated credentials only trust tokens from this repo."
}

variable "location" {
  type    = string
  default = "eastus"
}

variable "app_resource_group_name" {
  type    = string
  default = "rg-olist-agent"
}

data "azurerm_client_config" "current" {}

locals {
  # Storage names are globally unique. Hashing the subscription id gives a stable
  # suffix with no random provider and no state to lose.
  suffix = substr(sha1(data.azurerm_client_config.current.subscription_id), 0, 8)

  # What each identity is allowed to be. `ref:refs/heads/main` only matches
  # workflows running on main; `pull_request` matches PR runs from this repo.
  # Fork PRs never get an OIDC token, so they can't use either.
  ci_subjects = {
    deploy = "repo:${var.github_repository}:ref:refs/heads/main"
    plan   = "repo:${var.github_repository}:pull_request"
  }

  # Roles the deploy identity may grant. Extend this list when a phase needs a new
  # runtime role (e.g. Key Vault Secrets User in P2).
  assignable_role_ids = [
    "7f951dda-4ed3-4680-a7ca-43fe172d538d", # AcrPull
  ]
}

# --- Remote state ---------------------------------------------------------

resource "azurerm_resource_group" "tfstate" {
  name     = "rg-olist-agent-tfstate"
  location = var.location
}

#trivy:ignore:AVD-AZU-0012 GitHub-hosted runners have no fixed IPs; access is gated by Entra ID RBAC instead.
resource "azurerm_storage_account" "tfstate" {
  name                     = "stolisttf${local.suffix}"
  resource_group_name      = azurerm_resource_group.tfstate.name
  location                 = azurerm_resource_group.tfstate.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  # Entra ID only: no account keys that could leak and grant full access.
  shared_access_key_enabled = false

  # State is the one thing here you can't rebuild. Versioning + soft delete let you recover a corrupted or deleted state file.
  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 30
    }
    container_delete_retention_policy {
      days = 30
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_container" "tfstate" {
  name               = "tfstate"
  storage_account_id = azurerm_storage_account.tfstate.id

  lifecycle {
    prevent_destroy = true
  }
}

# Owner is a control-plane role: it does not include reading blobs. You need
# this to run `terraform plan` against the remote state from your machine.
resource "azurerm_role_assignment" "state_you" {
  scope                = azurerm_storage_container.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# --- App resource group ---------------------------------------------------
# Created here, not in ../, so the deploy identity can be scoped to it.
# Subscription-wide Contributor would be simpler and much more dangerous.

resource "azurerm_resource_group" "app" {
  name     = var.app_resource_group_name
  location = var.location
}

# --- GitHub OIDC identities -----------------------------------------------
# These live in the tfstate RG, so the deploy identity (Contributor on the app
# RG) can't delete or change itself.

resource "azurerm_user_assigned_identity" "ci" {
  for_each            = local.ci_subjects
  name                = "id-olist-agent-${each.key}"
  resource_group_name = azurerm_resource_group.tfstate.name
  location            = azurerm_resource_group.tfstate.location
}

resource "azurerm_federated_identity_credential" "ci" {
  for_each                  = local.ci_subjects
  name                      = "github-${each.key}"
  user_assigned_identity_id = azurerm_user_assigned_identity.ci[each.key].id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = each.value
}

# deploy (main branch): creates and changes resources in the app RG.
resource "azurerm_role_assignment" "deploy_contributor" {
  scope                = azurerm_resource_group.app.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.ci["deploy"].principal_id
}

# Terraform also grants roles (e.g. AcrPull to the app's identity). Contributor
# can't do that. User Access Administrator could, but it could also make itself
# Owner. This role plus an ABAC condition can only grant/revoke the listed roles.
resource "azurerm_role_assignment" "deploy_rbac_admin" {
  scope                = azurerm_resource_group.app.id
  role_definition_name = "Role Based Access Control Administrator"
  principal_id         = azurerm_user_assigned_identity.ci["deploy"].principal_id
  condition_version    = "2.0"
  condition            = <<-EOT
    (
      (!(ActionMatches{'Microsoft.Authorization/roleAssignments/write'}))
      OR
      (@Request[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {${join(", ", local.assignable_role_ids)}})
    )
    AND
    (
      (!(ActionMatches{'Microsoft.Authorization/roleAssignments/delete'}))
      OR
      (@Resource[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {${join(", ", local.assignable_role_ids)}})
    )
  EOT
}

resource "azurerm_role_assignment" "deploy_state" {
  scope                = azurerm_storage_container.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.ci["deploy"].principal_id
}

# plan (pull requests): read-only. A PR branch runs whatever code it contains, so
# this identity must not be able to change anything.
resource "azurerm_role_assignment" "plan_reader" {
  scope                = azurerm_resource_group.app.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.ci["plan"].principal_id
}

# The azurerm provider calls listSecrets when it refreshes a container app, and
# Reader doesn't include that action, so plan would fail without this role.
resource "azurerm_role_definition" "plan_list_secrets" {
  name  = "olist-agent terraform plan: list container app secrets"
  scope = azurerm_resource_group.app.id
  permissions {
    actions = ["Microsoft.App/containerApps/listSecrets/action"]
  }
  assignable_scopes = [azurerm_resource_group.app.id]
}

resource "azurerm_role_assignment" "plan_list_secrets" {
  scope              = azurerm_resource_group.app.id
  role_definition_id = azurerm_role_definition.plan_list_secrets.role_definition_resource_id
  principal_id       = azurerm_user_assigned_identity.ci["plan"].principal_id
}

# Read-only on state. CI runs plan with -lock=false, because taking the lock (a blob lease) is a write.
resource "azurerm_role_assignment" "plan_state" {
  scope                = azurerm_storage_container.tfstate.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.ci["plan"].principal_id
}

# --- Outputs --------------------------------------------------------------

output "tfstate_storage_account" {
  value = azurerm_storage_account.tfstate.name
}

output "github_variables_commands" {
  description = "Run these to configure the repo. None of these values are secret: OIDC has no client secret."
  value       = <<-EOT
    gh variable set AZURE_TENANT_ID         -R ${var.github_repository} --body ${data.azurerm_client_config.current.tenant_id}
    gh variable set AZURE_SUBSCRIPTION_ID   -R ${var.github_repository} --body ${data.azurerm_client_config.current.subscription_id}
    gh variable set AZURE_CLIENT_ID_DEPLOY  -R ${var.github_repository} --body ${azurerm_user_assigned_identity.ci["deploy"].client_id}
    gh variable set AZURE_CLIENT_ID_PLAN    -R ${var.github_repository} --body ${azurerm_user_assigned_identity.ci["plan"].client_id}
    gh variable set TFSTATE_STORAGE_ACCOUNT -R ${var.github_repository} --body ${azurerm_storage_account.tfstate.name}
  EOT
}
