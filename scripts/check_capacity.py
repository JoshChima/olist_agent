"""Check that every Postgres Flexible Server a plan creates can actually be created there.

Usage: terraform show -json tfplan > plan.json
       python3 scripts/check_capacity.py plan.json

terraform plan can't see region capacity: a restricted region or one with zero quota only
fails at apply, on main (P1 hit both, ADR-0002). For each planned server create this asks
Azure through `az`: list-skus (is the region open, does it offer the SKU and version) and
the regional quota usages. Exit 0 when every create fits, 1 otherwise, including when `az`
fails, so the check fails closed. The CI plan identity reads both through its Postgres
locations role (infra/bootstrap). Output can carry Azure error text, so CI passes it
through scripts/redact.py.
"""

import json
import subprocess
import sys

# {subscriptionId} is filled in by `az rest`, so the ID never appears here or in the log.
USAGES = (
    "https://management.azure.com/subscriptions/{subscriptionId}/providers/"
    "Microsoft.DBforPostgreSQL/locations/%s/resourceType/flexibleServers/usages"
    "?api-version=2024-08-01"
)
# ponytail: only Burstable maps to its quota family; other tiers check total cores only.
# Add their families (standardDDSv5Family, ...) when a non-Burstable server is planned.
FAMILY = {"B": "standardBSFamily"}


def planned_servers(plan):
    """(address, location, sku_name, version) for each server the plan creates."""
    for rc in plan.get("resource_changes", []):
        change = rc["change"]
        if rc["type"] == "azurerm_postgresql_flexible_server" and "create" in change["actions"]:
            after = change["after"]
            yield rc["address"], after["location"], after["sku_name"], after.get("version")


def problems(location, sku_name, version, skus, usages):
    """Why a server can't be created, from list-skus output and quota usages; [] if it can."""
    tier, sku = sku_name.split("_", 1)  # "B_Standard_B1ms" -> ("B", "Standard_B1ms")
    reasons = [c["reason"] for c in skus if c.get("reason")]
    if reasons:
        return [f"{location} is restricted: {reasons[0]}"]
    offered = {
        s["name"]: s["vCores"]
        for c in skus
        for e in c.get("supportedServerEditions") or []
        for s in e.get("supportedServerSkus") or []
    }
    if sku not in offered:
        return [f"{location} doesn't offer {sku}"]
    found = []
    versions = {v["name"] for c in skus for v in c.get("supportedServerVersions") or []}
    if version and version not in versions:
        found.append(f"{location} doesn't offer Postgres {version}")
    left = {u["name"]["value"]: u["limit"] - u["currentValue"] for u in usages}
    for name in filter(None, [FAMILY.get(tier), "cores"]):
        if left.get(name, 0) < offered[sku]:
            found.append(
                f"{location} has {left.get(name, 0)} {name} quota left; {sku} needs {offered[sku]}"
            )
    return found


def az(*args):
    out = subprocess.run(["az", *args, "-o", "json"], check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def main(argv):
    with open(argv[1], encoding="utf-8") as f:
        plan = json.load(f)
    failed = False
    for address, location, sku_name, version in planned_servers(plan):
        try:
            skus = az("postgres", "flexible-server", "list-skus", "-l", location)
            usages = az("rest", "--method", "get", "--url", USAGES % location)["value"]
        except subprocess.CalledProcessError as e:
            print(f"{address}: couldn't read {location}'s capacity: {e.stderr.strip()}")
            failed = True
            continue
        found = problems(location, sku_name, version, skus, usages)
        for p in found:
            print(f"{address}: {p}")
        if not found:
            print(f"{address}: {location} has capacity for {sku_name}")
        failed = failed or bool(found)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
