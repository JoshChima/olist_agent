"""Self-check for check_capacity.py. Run: python3 scripts/test_check_capacity.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from check_capacity import planned_servers, problems  # noqa: E402


def server(actions, location="southcentralus"):
    after = {"location": location, "sku_name": "B_Standard_B1ms", "version": "17"}
    return {
        "address": "azurerm_postgresql_flexible_server.this",
        "type": "azurerm_postgresql_flexible_server",
        "change": {"actions": actions, "after": after},
    }


# Shaped like `az postgres flexible-server list-skus`.
OPEN = [
    {
        "reason": None,
        "supportedServerEditions": [
            {"name": "Burstable", "supportedServerSkus": [{"name": "Standard_B1ms", "vCores": 1}]}
        ],
        "supportedServerVersions": [{"name": "16"}, {"name": "17"}],
    }
]
# East US in P1, as list-skus reported it.
RESTRICTED = [
    {"reason": "Provisioning is restricted in this region.", "supportedServerEditions": []}
]

# Only creates are checked; updates and no-ops never move a server.
plan = {"resource_changes": [server(["create"]), server(["update"]), server(["no-op"])]}
assert [s[1:] for s in planned_servers(plan)] == [("southcentralus", "B_Standard_B1ms", "17")]
assert list(planned_servers({"resource_changes": []})) == []

# An open region that offers the SKU and version passes.
assert problems("southcentralus", "B_Standard_B1ms", "17", OPEN) == []

# A restricted region fails, with Azure's reason.
found = problems("eastus", "B_Standard_B1ms", "17", RESTRICTED)
assert found == ["eastus is restricted: Provisioning is restricted in this region."], found

# A SKU or Postgres version the region doesn't offer.
assert problems("westus3", "B_Standard_B2s", "17", OPEN) == ["westus3 doesn't offer Standard_B2s"]
assert problems("westus3", "B_Standard_B1ms", "18", OPEN) == ["westus3 doesn't offer Postgres 18"]

print("check_capacity: all passed")
