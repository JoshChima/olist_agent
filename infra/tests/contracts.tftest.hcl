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
}

variables {
  budget_alert_email = "alerts@example.com"
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
