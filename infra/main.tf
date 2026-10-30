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
  features {
    # CI's plan identity is Reader, which has no data-plane access and can't list keys.
    # Without this, refreshing the data storage account calls the blob/queue APIs and fails.
    storage {
      data_plane_available = false
    }
  }
  # Shared keys are off on the data account, so any storage call must use Entra ID.
  storage_use_azuread = true
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

variable "operator_object_id" {
  type        = string
  sensitive   = true # An Azure ID: kept out of the public plan comment.
  description = "Your Entra user's object ID (az ad signed-in-user show --query id -o tsv). Postgres admin and blob uploader."

  # An unset GitHub secret arrives as "", which would fail much later, at apply.
  validation {
    condition     = can(regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", var.operator_object_id))
    error_message = "operator_object_id must be an Entra object ID (a GUID). Is the AZURE_OPERATOR_OBJECT_ID secret set?"
  }
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
      # No password: the app signs in with a token for its identity (ADR-0010). The
      # loader creates this role and lets it read sim only.
      env {
        name  = "DATABASE_URL"
        value = "${local.pg_dsn} user=${azurerm_user_assigned_identity.app.name}"
      }
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.app.client_id
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

# --- Loader identity ------------------------------------------------------

# The loader job's identity: Postgres Entra admin, reader of the raw data blob. The app's
# own identity gets neither; the loader makes it a Postgres role that can only read sim.
resource "azurerm_user_assigned_identity" "loader" {
  name                = "id-olist-agent-loader"
  resource_group_name = local.rg
  location            = local.location
}

resource "azurerm_role_assignment" "loader_acr_pull" {
  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.loader.principal_id
  principal_type       = "ServicePrincipal"
}

# --- Raw data storage -----------------------------------------------------

# Holds olist.sqlite, uploaded by scripts/upload-data.sh. The data is public (Kaggle),
# so network rules add nothing that Entra-only access doesn't already give.
# Not prevent_destroy: the file is re-uploadable, and teardown must work.
#trivy:ignore:AVD-AZU-0012 Container Apps without a VNet have no fixed outbound IPs; access is gated by Entra ID RBAC.
resource "azurerm_storage_account" "data" { # tflint-ignore: azurerm_resources_missing_prevent_destroy
  name                     = "stolistdata${local.suffix}"
  resource_group_name      = local.rg
  location                 = local.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  # Entra ID only: no account keys that could leak and grant full access.
  shared_access_key_enabled = false
}

# tflint-ignore: azurerm_resources_missing_prevent_destroy # Re-uploadable; teardown must work.
resource "azurerm_storage_container" "data" {
  name                  = "olist-data"
  storage_account_id    = azurerm_storage_account.data.id
  container_access_type = "private"
}

resource "azurerm_role_assignment" "loader_blob_reader" {
  scope                = azurerm_storage_container.data.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.loader.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "operator_blob_contributor" {
  scope                = azurerm_storage_container.data.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.operator_object_id
  principal_type       = "User"
}

# --- Postgres (ADR-0002, ADR-0010) ----------------------------------------

# About $13/month plus storage. Public endpoint, but Entra-only: there is no
# password, so reaching the port gets nobody in without a token for an admin or
# the app's identity. TLS is required by default (require_secure_transport = on).
# tflint-ignore: azurerm_resources_missing_prevent_destroy # The loader rebuilds it from Blob; teardown must work. tf_risk.py BLOCKs a replace.
resource "azurerm_postgresql_flexible_server" "this" {
  name                = "psql-olist-agent-${local.suffix}"
  resource_group_name = local.rg
  # This subscription can't create Flexible Servers in East US (region restricted) or East US 2
  # (zero quota: SkuNotAvailable). South Central US has Burstable quota and already runs a B1ms
  # for this subscription (ADR-0002). Everything else stays in East US.
  location              = "southcentralus"
  version               = "17"
  sku_name              = "B_Standard_B1ms"
  storage_mb            = 32768
  backup_retention_days = 7
  # No high_availability block: a standby doubles the bill.

  authentication {
    active_directory_auth_enabled = true
    password_auth_enabled         = false
    tenant_id                     = data.azurerm_client_config.current.tenant_id
  }

  # Azure picks an availability zone at create time. Without this, every apply after the
  # first tries to set zone back to null, and Azure rejects it ("zone can only be changed
  # when exchanged with ... standby_availability_zone").
  lifecycle {
    ignore_changes = [zone]
  }
}

# The server takes one operation at a time and rejects the rest ("another operation is
# in progress"), so the four resources below are chained with depends_on.

# Allowlisted for P3's embeddings, not created: the loader would need to CREATE EXTENSION.
resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "VECTOR"
}

# 0.0.0.0 is Azure's "allow Azure services" rule (ADR-0010): Container Apps without a
# VNet have no fixed outbound IPs. No other range is opened.
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAllAzureServicesAndResourcesWithinAzureIps"
  server_id        = azurerm_postgresql_flexible_server.this.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"

  depends_on = [azurerm_postgresql_flexible_server_configuration.extensions]
}

# The principal name becomes the Postgres role name: connect as that user with a token.
resource "azurerm_postgresql_flexible_server_active_directory_administrator" "loader" {
  server_name         = azurerm_postgresql_flexible_server.this.name
  resource_group_name = local.rg
  tenant_id           = data.azurerm_client_config.current.tenant_id
  object_id           = azurerm_user_assigned_identity.loader.principal_id
  principal_name      = azurerm_user_assigned_identity.loader.name
  principal_type      = "ServicePrincipal"

  depends_on = [azurerm_postgresql_flexible_server_firewall_rule.azure_services]
}

# You, for debugging through the toolbox: connect as user "operator" with
# `az account get-access-token --resource-type oss-rdbms` as the password.
resource "azurerm_postgresql_flexible_server_active_directory_administrator" "operator" {
  server_name         = azurerm_postgresql_flexible_server.this.name
  resource_group_name = local.rg
  tenant_id           = data.azurerm_client_config.current.tenant_id
  object_id           = var.operator_object_id
  principal_name      = "operator"
  principal_type      = "User"

  depends_on = [azurerm_postgresql_flexible_server_active_directory_administrator.loader]
}

locals {
  # Entra auth: no password in the DSN. The app and the loader add a fresh token at
  # connect time (olist_agent.db). pgaadauth only exists in the postgres database.
  pg_dsn = "host=${azurerm_postgresql_flexible_server.this.fqdn} dbname=postgres sslmode=require"
}

# --- Loader job -----------------------------------------------------------

# Same image as the app, its own entry point. CD starts it after every deploy and fails
# unless it succeeds. It exits 0 with "no source data" until olist.sqlite is uploaded.
resource "azurerm_container_app_job" "loader" {
  name                         = "job-olist-agent-loader"
  resource_group_name          = local.rg
  location                     = local.location
  container_app_environment_id = azurerm_container_app_environment.this.id
  workload_profile_name        = "Consumption"
  replica_timeout_in_seconds   = 1800
  replica_retry_limit          = 1 # The load is idempotent; one retry covers a transient failure.

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.loader.id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.loader.id
  }

  template {
    container {
      name = "loader"
      # Placeholder until CD's first `az containerapp job update --image`; never started.
      image   = "mcr.microsoft.com/dotnet/samples:aspnetapp"
      command = ["python", "-m", "olist_agent.loader"]
      cpu     = 0.5
      memory  = "1Gi"

      env {
        name  = "DATABASE_URL"
        value = "${local.pg_dsn} user=${azurerm_user_assigned_identity.loader.name}"
      }
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.loader.client_id
      }
      env {
        name  = "OLIST_BLOB_URL"
        value = "${azurerm_storage_account.data.primary_blob_endpoint}${azurerm_storage_container.data.name}/olist.sqlite"
      }
      # The app's role: created from its identity's object ID, granted read on sim only.
      env {
        name  = "APP_DB_ROLE"
        value = azurerm_user_assigned_identity.app.name
      }
      env {
        name  = "APP_DB_PRINCIPAL_ID"
        value = azurerm_user_assigned_identity.app.principal_id
      }
    }
  }

  # As for the app: CD owns the image.
  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }

  depends_on = [
    azurerm_role_assignment.loader_acr_pull,
    azurerm_role_assignment.loader_blob_reader,
    azurerm_postgresql_flexible_server_active_directory_administrator.loader,
  ]
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

output "loader_job_name" {
  value = azurerm_container_app_job.loader.name
}

output "app_url" {
  value = "https://${azurerm_container_app.app.ingress[0].fqdn}"
}
