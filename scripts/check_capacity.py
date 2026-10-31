"""Check that every Postgres Flexible Server a plan creates is offered in its region.

Usage: terraform show -json tfplan > plan.json
       python3 scripts/check_capacity.py plan.json

terraform plan can't see whether a region takes new servers, so East US, which is
restricted for this subscription, failed only at apply, on main (ADR-0002). For each
planned server create this reads `az postgres flexible-server list-skus`: is the region
open, and does it offer the SKU and the Postgres version. Exit 0 when every create
passes, 1 otherwise, including when `az` fails, so the check fails closed.

It can't catch a capacity shortage: East US 2 passed every read API (list-skus, quota
usages, capabilities) and still failed with SkuNotAvailable. The first create in a new
region can still fail at apply.

The CI plan identity reads list-skus through its Postgres locations role
(infra/bootstrap). Output can carry Azure error text, so CI passes it through
scripts/redact.py.
"""

import json
import subprocess
import sys


def planned_servers(plan):
    """(address, location, sku_name, version) for each server the plan creates."""
    for rc in plan.get("resource_changes", []):
        change = rc["change"]
        if rc["type"] == "azurerm_postgresql_flexible_server" and "create" in change["actions"]:
            after = change["after"]
            yield rc["address"], after["location"], after["sku_name"], after.get("version")


def problems(location, sku_name, version, skus):
    """Why the region won't take this server, from list-skus output; [] if it's offered."""
    sku = sku_name.split("_", 1)[1]  # "B_Standard_B1ms" -> "Standard_B1ms"
    reasons = [c["reason"] for c in skus if c.get("reason")]
    if reasons:
        return [f"{location} is restricted: {reasons[0]}"]
    offered = {
        s["name"]
        for c in skus
        for e in c.get("supportedServerEditions") or []
        for s in e.get("supportedServerSkus") or []
    }
    if sku not in offered:
        return [f"{location} doesn't offer {sku}"]
    versions = {v["name"] for c in skus for v in c.get("supportedServerVersions") or []}
    if version and version not in versions:
        return [f"{location} doesn't offer Postgres {version}"]
    return []


def list_skus(location):
    out = subprocess.run(
        ["az", "postgres", "flexible-server", "list-skus", "-l", location, "-o", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(out.stdout)


def main(argv):
    with open(argv[1], encoding="utf-8") as f:
        plan = json.load(f)
    failed = False
    for address, location, sku_name, version in planned_servers(plan):
        try:
            skus = list_skus(location)
        except subprocess.CalledProcessError as e:
            print(f"{address}: couldn't read {location}'s SKUs: {e.stderr.strip()}")
            failed = True
            continue
        found = problems(location, sku_name, version, skus)
        for p in found:
            print(f"{address}: {p}")
        if not found:
            print(f"{address}: {location} offers {sku_name}")
        failed = failed or bool(found)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
