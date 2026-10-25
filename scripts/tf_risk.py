"""Classify a Terraform plan into risk tiers before anything reaches Azure.

Usage: terraform show -json plan.tfplan > plan.json
       python3 scripts/tf_risk.py plan.json [--root bootstrap]
       python3 scripts/tf_risk.py refresh.json --drift
       python3 scripts/tf_risk.py plan.json --root bootstrap --gate

Prints a markdown table. Exit code: 0 SAFE/REVIEW, 2 DANGER, 3 BLOCK.
With --gate (the apply decision): exit 0 means apply may proceed (SAFE, REVIEW, or DANGER
that a person approved at the prompt). Anything else refuses, including a crash or bad
input (Python exits 1), so the gate fails closed by construction.
With --drift (a `plan -refresh-only` JSON): lists drifted resources, exit 2 if any.
Don't use `-refresh-only -detailed-exitcode` for that: it exits 2 on any state
refresh, even when nothing drifted.
Shared by the terraform-operator subagent (scripts/tf-toolbox.sh) and CI's plan job,
so both always reach the same verdict.
"""

import json
import sys

TIERS = ["SAFE", "REVIEW", "DANGER", "BLOCK"]
EXIT = {"SAFE": 0, "REVIEW": 0, "DANGER": 2, "BLOCK": 3}

# Deleting or replacing these loses data or takes the platform down. Add P1+ stateful types here.
PROTECTED = {
    "azurerm_storage_account",  # holds Terraform state
    "azurerm_storage_container",
    "azurerm_container_app_environment",  # replacing it means downtime and new URLs (ADR-0004)
    "azurerm_postgresql_flexible_server",
    "azurerm_key_vault",
}

# Changing these can lock CI out of Azure (as the OIDC subject mismatch did) or widen access.
SENSITIVE = {
    "azurerm_federated_identity_credential",
    "azurerm_role_assignment",
    "azurerm_role_definition",
    "azurerm_user_assigned_identity",
}


def _normalize(value):
    """Values with CRLF turned into LF, to spot diffs that are only line endings."""
    if isinstance(value, str):
        return value.replace("\r\n", "\n")
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def classify(rc, root):
    """(tier, note) for one entry of the plan's resource_changes."""
    actions = rc["change"]["actions"]
    kind = rc["type"]
    if actions in (["no-op"], ["read"]):
        return None
    note = rc.get("action_reason", "")
    if "delete" in actions:
        paths = rc["change"].get("replace_paths") or []
        if paths:
            note = "forced by " + ", ".join(".".join(map(str, p)) for p in paths)
        return ("BLOCK" if kind in PROTECTED else "DANGER"), note
    if actions == ["update"]:
        before, after = rc["change"].get("before"), rc["change"].get("after")
        if _normalize(before) == _normalize(after):
            note = "line endings only"
    if kind in SENSITIVE or root == "bootstrap" or actions == ["forget"]:
        return "REVIEW", note
    return "SAFE", note


def assess(plan, root=""):
    """(overall tier, rows) where rows are (address, actions, tier, note)."""
    rows = []
    for rc in plan.get("resource_changes", []):
        result = classify(rc, root)
        if result:
            rows.append((rc["address"], "/".join(rc["change"]["actions"]), *result))
    overall = max((r[2] for r in rows), key=TIERS.index, default="SAFE")
    return overall, rows


def drift(plan):
    """Addresses whose real Azure object no longer matches state, with Terraform's actions."""
    drifted = plan.get("resource_drift", [])
    return [(d["address"], "/".join(d["change"]["actions"])) for d in drifted]


def render(overall, rows):
    lines = [f"**Risk: {overall}**", ""]
    if rows:
        lines += ["| Resource | Action | Tier | Note |", "|---|---|---|---|"]
        lines += [f"| `{a}` | {act} | {t} | {n} |" for a, act, t, n in rows]
    else:
        lines.append("No resource changes.")
    return "\n".join(lines)


def main(argv):
    path = argv[1]
    root = argv[3] if len(argv) > 3 and argv[2] == "--root" else ""
    with sys.stdin if path == "-" else open(path, encoding="utf-8") as f:
        plan = json.load(f)
    if "--drift" in argv:
        drifted = drift(plan)
        print("\n".join(f"{a} ({act})" for a, act in drifted) or "No drift.")
        return 2 if drifted else 0
    overall, rows = assess(plan, root)
    print(render(overall, rows))
    if "--gate" in argv:
        return 3 if overall == "BLOCK" else 0
    return EXIT[overall]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
