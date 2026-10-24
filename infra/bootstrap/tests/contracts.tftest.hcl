# Contract tests for bootstrap, the root with no pipeline behind it. The mock
# provider means these run offline. Run: terraform -chdir=infra/bootstrap test

mock_provider "azurerm" {}

variables {
  github_repository = "octo/olist_agent"
  github_sub_prefix = "repo:octo@1001/olist_agent@2002"
}

run "oidc_subjects_use_the_prefix" {
  command = plan

  # GitHub matches these as exact strings. A wrong subject locks CI out of Azure.
  assert {
    condition     = azurerm_federated_identity_credential.ci["deploy"].subject == "repo:octo@1001/olist_agent@2002:ref:refs/heads/main"
    error_message = "deploy must trust only main, under the immutable sub prefix."
  }

  assert {
    condition     = azurerm_federated_identity_credential.ci["plan"].subject == "repo:octo@1001/olist_agent@2002:pull_request"
    error_message = "plan must trust only pull_request runs, under the immutable sub prefix."
  }
}

run "old_style_prefix_is_rejected" {
  command = plan

  # The format that broke CI in P0 (no owner/repo IDs).
  variables {
    github_sub_prefix = "repo:octo/olist_agent"
  }

  expect_failures = [var.github_sub_prefix]
}

run "deploy_can_only_grant_acrpull" {
  command = plan

  # The ABAC condition lists the allowed role IDs (for write and for delete). If every
  # GUID in it is AcrPull, deploy can't hand out any other role.
  assert {
    condition     = toset(regexall("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", azurerm_role_assignment.deploy_rbac_admin.condition)) == toset(["7f951dda-4ed3-4680-a7ca-43fe172d538d"])
    error_message = "deploy's RBAC Administrator condition must allow AcrPull and nothing else."
  }
}

run "plan_identity_is_read_only" {
  command = plan

  assert {
    condition     = azurerm_role_assignment.plan_reader.role_definition_name == "Reader"
    error_message = "The PR identity runs untrusted branch code, so it must stay Reader."
  }

  assert {
    condition     = azurerm_role_assignment.plan_state.role_definition_name == "Storage Blob Data Reader"
    error_message = "The PR identity must only read state."
  }
}

run "state_storage_is_locked_down" {
  command = plan

  assert {
    condition     = azurerm_storage_account.tfstate.shared_access_key_enabled == false
    error_message = "State storage must stay Entra-only (no account keys)."
  }

  assert {
    condition     = azurerm_storage_account.tfstate.blob_properties[0].versioning_enabled
    error_message = "Blob versioning is how a corrupted state file gets recovered."
  }
}
