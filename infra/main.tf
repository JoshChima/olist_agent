# The app's infrastructure, applied by CD on every push to main. Prerequisites
# (state storage, resource group, CI identities) come from ./bootstrap.

terraform {
  required_version = ">= 1.10"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.10"
    }
  }
  # Partial config: backend blocks can't read variables, so the storage account
  # name is passed at init time (-backend-config=storage_account_name=...).
  backend "azurerm" {
    container_name   = "tfstate"
    key              = "olist_agent.tfstate"
    use_azuread_auth = true
  }
}

# Resource providers were registered by bootstrap. azurerm 5.x registers none by default, which suits an RG-scoped identity.
provider "azurerm" {
  features {}
}

variable "resource_group_name" {
  type    = string
  default = "rg-olist-agent"
}

variable "budget_amount" {
  type        = number
  default     = 50
  description = "Monthly budget in the billing currency."
}

variable "budget_alert_email" {
  type        = string
  sensitive   = true # Keeps it out of plan output, which CI posts on a public PR.
  description = "Where budget alerts go."
}

data "azurerm_client_config" "current" {}

data "azurerm_resource_group" "app" {
  name = var.resource_group_name
}

locals {
  rg       = data.azurerm_resource_group.app.name
  location = data.azurerm_resource_group.app.location
  # Globally unique names (ACR) need a suffix. Derived, not random, so it never changes.
  suffix = substr(sha1(data.azurerm_client_config.current.subscription_id), 0, 8)
}

# --- Registry -------------------------------------------------------------

# Basic costs about $5/month. Admin user stays off: the app pulls with its managed identity and CI pushes with OIDC.
resource "azurerm_container_registry" "this" {
  name                = "acrolistagent${local.suffix}"
  resource_group_name = local.rg
  location            = local.location
  sku                 = "Basic"
  admin_enabled       = false
}

# --- Observability --------------------------------------------------------

resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-olist-agent"
  resource_group_name = local.rg
  location            = local.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  # Ingestion is the usual surprise bill. 1 GB/day caps it at roughly $2-3/day.
  daily_quota_gb = 1
}

# Workspace-based: telemetry lands in the same Log Analytics workspace, so one
# KQL query can join app traces with container logs. The container app gets the
# connection string as a secret, and the app turns the SDK on when it's set.
resource "azurerm_application_insights" "this" {
  name                = "appi-olist-agent"
  resource_group_name = local.rg
  location            = local.location
  workspace_id        = azurerm_log_analytics_workspace.this.id
  application_type    = "web"
}

# --- Container Apps -------------------------------------------------------

# Declaring a workload_profile block is what makes this a workload-profiles
# environment rather than a legacy Consumption-only one. The type can't be
# changed later, and P5's serverless T4 GPU profile requires it, so it's set now
# even though "Consumption" is the only profile until then.
resource "azurerm_container_app_environment" "this" {
  name                       = "cae-olist-agent"
  resource_group_name        = local.rg
  location                   = local.location
  logs_destination           = "log-analytics" # Required in azurerm 5.x; without it logs are stream-only.
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  workload_profile {
    name                  = "Consumption" # The name must be exactly "Consumption".
    workload_profile_type = "Consumption"
  }
}

# The app's own identity, used to pull from ACR. It's separate from the CI
# identities: the runtime should never hold deploy rights.
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-olist-agent-app"
  resource_group_name = local.rg
  location            = local.location
}

resource "azurerm_role_assignment" "app_acr_pull" {
  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
  principal_type       = "ServicePrincipal" # Skips the Entra lookup that fails while a new identity is still replicating.
}

resource "azurerm_container_app" "app" {
  name                         = "ca-olist-agent"
  resource_group_name          = local.rg
  container_app_environment_id = azurerm_container_app_environment.this.id
  workload_profile_name        = "Consumption"
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  ingress {
    external_enabled = true
    target_port      = 8080
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  # A secret, not a plain env value, so it stays out of the revision's config.
  secret {
    name  = "appinsights-connection-string"
    value = azurerm_application_insights.this.connection_string
  }

  template {
    # Scale to zero: no requests, no compute bill. The first request after idle
    # takes a few seconds (cold start), so the CD smoke test retries.
    min_replicas = 0
    max_replicas = 1

    container {
      name = "app"
      # Placeholder for the very first apply, before CI has pushed anything to the
      # new ACR. It's a public MCR image that also listens on 8080.
      image  = "mcr.microsoft.com/dotnet/samples:aspnetapp"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }
    }
  }

  # Terraform owns the infrastructure, env included, and CD owns which image runs
  # (`az containerapp update --image`, which keeps env as is). Without this, every
  # apply would roll the app back to the placeholder.
  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }

  depends_on = [azurerm_role_assignment.app_acr_pull]
}

# --- Cost guardrail -------------------------------------------------------

# Alerts only. Azure budgets never stop spending; the app-level token cap (P2)
# and the Anthropic workspace limit are the real stops.
resource "azurerm_consumption_budget_resource_group" "this" {
  name              = "budget-olist-agent"
  resource_group_id = data.azurerm_resource_group.app.id
  amount            = var.budget_amount
  time_grain        = "Monthly"

  time_period {
    # The start date must be the first of a month. It's taken from apply time and then frozen (see ignore_changes).
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", timestamp())
  }

  notification {
    threshold      = 80
    threshold_type = "Actual"
    operator       = "GreaterThanOrEqualTo"
    contact_emails = [var.budget_alert_email]
  }

  notification {
    threshold      = 100
    threshold_type = "Forecasted"
    operator       = "GreaterThanOrEqualTo"
    contact_emails = [var.budget_alert_email]
  }

  lifecycle {
    ignore_changes = [time_period]
  }
}

# --- Outputs (read by the CD workflow) ------------------------------------

output "resource_group" {
  value = local.rg
}

output "acr_name" {
  value = azurerm_container_registry.this.name
}

output "acr_login_server" {
  value = azurerm_container_registry.this.login_server
}

output "container_app_name" {
  value = azurerm_container_app.app.name
}

output "app_url" {
  value = "https://${azurerm_container_app.app.ingress[0].fqdn}"
}
