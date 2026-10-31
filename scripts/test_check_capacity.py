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


# Shaped like `az postgres flexible-server list-skus` and the quota usages API.
OPEN = [
    {
        "reason": None,
        "supportedServerEditions": [
            {"name": "Burstable", "supportedServerSkus": [{"name": "Standard_B1ms", "vCores": 1}]}
        ],
        "supportedServerVersions": [{"name": "16"}, {"name": "17"}],
    }
]
RESTRICTED = [
    {"reason": "Provisioning is restricted in this region.", "supportedServerEditions": []}
]


def usage(name, limit, current=0):
    return {"name": {"value": name}, "limit": limit, "currentValue": current}


QUOTA = [usage("cores", 384), usage("standardBSFamily", 40)]

# Only creates are checked; updates and no-ops never move a server.
plan = {"resource_changes": [server(["create"]), server(["update"]), server(["no-op"])]}
assert [s[1:] for s in planned_servers(plan)] == [("southcentralus", "B_Standard_B1ms", "17")]
assert list(planned_servers({"resource_changes": []})) == []

# A region with room passes.
assert problems("southcentralus", "B_Standard_B1ms", "17", OPEN, QUOTA) == []

# East US in P1: the region is closed to new servers.
found = problems("eastus", "B_Standard_B1ms", "17", RESTRICTED, QUOTA)
assert found == ["eastus is restricted: Provisioning is restricted in this region."], found

# East US 2 in P1: list-skus looked fine, but there was no quota at all.
found = problems("eastus2", "B_Standard_B1ms", "17", OPEN, [])
assert len(found) == 2 and all("0" in f for f in found), found

# Quota that exists but is used up fails too, naming the family.
found = problems(
    "westus3", "B_Standard_B1ms", "17", OPEN, [usage("cores", 384), usage("standardBSFamily", 1, 1)]
)
assert found == ["westus3 has 0 standardBSFamily quota left; Standard_B1ms needs 1"], found

# A SKU or Postgres version the region doesn't offer.
assert problems("westus3", "B_Standard_B2s", "17", OPEN, QUOTA) == [
    "westus3 doesn't offer Standard_B2s"
]
assert problems("westus3", "B_Standard_B1ms", "18", OPEN, QUOTA) == [
    "westus3 doesn't offer Postgres 18"
]

print("check_capacity: all passed")
