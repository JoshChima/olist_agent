"""Self-check for tf_risk.py. Run: python3 scripts/test_tf_risk.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tf_risk import assess, drift  # noqa: E402


def rc(address, kind, actions, before=None, after=None, **extra):
    change = {"actions": actions, "before": before, "after": after, **extra}
    return {"address": address, "type": kind, "change": change}


def plan(*changes):
    return {"resource_changes": list(changes)}


# No-ops and data reads are ignored.
noop = rc("azurerm_container_registry.this", "azurerm_container_registry", ["no-op"])
assert assess(plan(noop)) == ("SAFE", [])

# A plain update is SAFE; the same change in bootstrap needs review.
law = "azurerm_log_analytics_workspace"
update = rc(f"{law}.this", law, ["update"], {"q": 1}, {"q": 2})
assert assess(plan(update))[0] == "SAFE"
assert assess(plan(update), root="bootstrap")[0] == "REVIEW"

# Identity/auth changes need review, and CRLF-only diffs are labelled.
crlf = rc(
    "azurerm_role_assignment.deploy_rbac_admin",
    "azurerm_role_assignment",
    ["update"],
    {"condition": "(\r\n a\r\n)"},
    {"condition": "(\n a\n)"},
)
overall, rows = assess(plan(crlf))
assert overall == "REVIEW" and rows[0][3] == "line endings only", rows

# Replacing an ordinary resource is DANGER and names the attribute forcing it.
replace = rc(
    "azurerm_container_app.app",
    "azurerm_container_app",
    ["delete", "create"],
    replace_paths=[["template", 0, "container", 0, "name"]],
)
overall, rows = assess(plan(replace))
assert overall == "DANGER" and rows[0][3] == "forced by template.0.container.0.name", rows

# Deleting a protected resource is BLOCK, and the worst row wins.
delete_state = rc("azurerm_storage_account.tfstate", "azurerm_storage_account", ["delete"])
assert assess(plan(update, replace, delete_state))[0] == "BLOCK"

# Drift comes only from resource_drift; a refresh with no drift reports none even
# though `-refresh-only -detailed-exitcode` would exit 2 for it.
assert drift({"resource_drift": [], "resource_changes": [noop]}) == []
fic = "azurerm_federated_identity_credential"
moved = rc(f'{fic}.ci["plan"]', fic, ["update"])
assert drift({"resource_drift": [moved]}) == [(f'{fic}.ci["plan"]', "update")]

print("tf_risk: all checks passed")
