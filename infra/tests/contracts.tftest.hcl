# Contract tests: decisions from the ADRs that a refactor must not quietly undo.
# The mock provider means no Azure access or credentials: these run offline, in CI's
# iac job and in scripts/tf-toolbox.sh check. Run: terraform -chdir=infra test

# Mocks return random strings, but the provider still validates ID formats at plan
# time, so the resource group data source needs a realistic ID.
mock_provider "azurerm" {
  mock_data "azurerm_resource_group" {
    defaults = {
      id       = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-olist-agent"
      location = "eastus"
    }
  }

  # Postgres validates tenant_id as a UUID.
  mock_data "azurerm_client_config" {
    defaults = {
      tenant_id = "00000000-0000-0000-0000-000000000000"
    }
  }
}

variables {
  budget_alert_email = "alerts@example.com"
  operator_object_id = "00000000-0000-0000-0000-000000000001"
}

run "postgres_is_entra_only" {
  command = plan

  # ADR-0010: the endpoint is public, so there must be no password to guess or leak.
  assert {
    condition     = azurerm_postgresql_flexible_server.this.authentication[0].password_auth_enabled == false
    error_message = "Password auth must stay off on Postgres: Entra tokens only (ADR-0010)."
  }

  assert {
    condition     = azurerm_postgresql_flexible_server.this.authentication[0].active_directory_auth_enabled
    error_message = "Entra auth must be on, or nothing can sign in to Postgres."
  }
}

run "postgres_is_the_smallest_tier" {
  command = plan

  # ADR-0002: about $13/month. A bigger SKU or an HA standby multiplies the bill.
  assert {
    condition     = azurerm_postgresql_flexible_server.this.sku_name == "B_Standard_B1ms"
    error_message = "Postgres stays on B1ms burstable (ADR-0002)."
  }

  assert {
    condition     = length(azurerm_postgresql_flexible_server.this.high_availability) == 0
    error_message = "No HA standby: it doubles the Postgres bill."
  }

  # ADR-0002: East US is restricted for Flexible Server on this subscription; CD failed there.
  assert {
    condition     = azurerm_postgresql_flexible_server.this.location == "eastus2"
    error_message = "Postgres must stay in East US 2: East US refuses new Flexible Servers (ADR-0002)."
  }
}

run "data_storage_is_entra_only" {
  command = plan

  assert {
    condition     = azurerm_storage_account.data.shared_access_key_enabled == false
    error_message = "The data storage account must stay Entra-only (no account keys)."
  }
}

run "loader_job_is_manually_triggered" {
  command = plan

  # CD starts it after each deploy and waits for it. A schedule would load behind CD's back.
  assert {
    condition     = length(azurerm_container_app_job.loader.manual_trigger_config) == 1
    error_message = "The loader job must be manually triggered: CD starts it and checks the result."
  }
}

run "app_connects_with_its_identity" {
  command = plan

  # ADR-0010: the app signs in to Postgres with a token for this identity, so it needs
  # the database's address and the identity's client ID.
  assert {
    condition     = alltrue([for n in ["DATABASE_URL", "AZURE_CLIENT_ID"] : contains([for e in azurerm_container_app.app.template[0].container[0].env : e.name], n)])
    error_message = "The app container needs DATABASE_URL and AZURE_CLIENT_ID to reach Postgres."
  }
}

run "environment_is_workload_profiles" {
  command = plan

  # ADR-0004: P5's GPU profile needs this, and the environment type can't be changed later.
  assert {
    condition     = contains([for p in azurerm_container_app_environment.this.workload_profile : p.workload_profile_type], "Consumption")
    error_message = "The Container Apps environment must declare a Consumption workload profile (ADR-0004)."
  }
}

run "app_scales_to_zero" {
  command = plan

  assert {
    condition     = azurerm_container_app.app.template[0].min_replicas == 0
    error_message = "min_replicas must stay 0: an always-on replica bills around the clock."
  }

  assert {
    condition     = azurerm_container_app.app.ingress[0].target_port == 8080
    error_message = "Ingress must target 8080, the port the image and the CD smoke test use."
  }
}

run "app_sends_telemetry" {
  command = plan

  # ADR-0006: the app only turns on App Insights when this env var is set.
  assert {
    condition     = contains([for e in azurerm_container_app.app.template[0].container[0].env : e.secret_name if e.name == "APPLICATIONINSIGHTS_CONNECTION_STRING"], "appinsights-connection-string")
    error_message = "The container must get APPLICATIONINSIGHTS_CONNECTION_STRING from a secret, or App Insights stays off."
  }
}

run "cost_guardrails" {
  command = plan

  assert {
    condition     = azurerm_consumption_budget_resource_group.this.amount == 50
    error_message = "The default budget is $50/month."
  }

  assert {
    condition     = toset([for n in azurerm_consumption_budget_resource_group.this.notification : "${n.threshold}/${n.threshold_type}"]) == toset(["80/Actual", "100/Forecasted"])
    error_message = "Budget alerts must fire at 80% actual and 100% forecasted."
  }

  assert {
    condition     = azurerm_log_analytics_workspace.this.daily_quota_gb == 1
    error_message = "Log Analytics ingestion stays capped at 1 GB/day."
  }

  assert {
    condition     = azurerm_container_registry.this.admin_enabled == false
    error_message = "ACR admin user stays off: pulls use the app's managed identity."
  }
}
