"""Self-check for the guards between agents and real Azure (ADR-0007).

Run: python3 scripts/test_guards.py. Each guard runs as Claude Code or tf-toolbox.sh
would run it: a subprocess fed on stdin, judged by exit code and output.
"""

import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SHA = "a" * 64


def run(script, stdin, *args, env=None):
    return subprocess.run(
        [sys.executable, str(HERE / script), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


def hook(script, command):
    return run(script, json.dumps({"tool_input": {"command": command}}))


# guard_tf_bash.py: the subagent's Bash runs only exact tf-toolbox.sh commands (exit 2 blocks).
allowed = [
    "scripts/tf-toolbox.sh up",
    "scripts/tf-toolbox.sh login",
    "scripts/tf-toolbox.sh check infra",
    "scripts/tf-toolbox.sh plan bootstrap",
    f"scripts/tf-toolbox.sh apply bootstrap /tmp/plans/bootstrap.tfplan {SHA}",
    "scripts/tf-toolbox.sh down",
]
blocked = [
    "ls",
    "terraform apply",
    "bash scripts/tf-toolbox.sh up",  # a prefix would dodge the ask rule's match
    "scripts/tf-toolbox.sh up && terraform apply",
    "scripts/tf-toolbox.sh up; rm -rf /",
    f"scripts/tf-toolbox.sh apply infra /tmp/plans/infra.tfplan {SHA}",
    "scripts/tf-toolbox.sh apply bootstrap /tmp/plans/bootstrap.tfplan abc",
    "scripts/tf-toolbox.sh plan prod",
]
for command in allowed:
    assert hook("guard_tf_bash.py", command).returncode == 0, f"guard blocked {command!r}"
for command in blocked:
    assert hook("guard_tf_bash.py", command).returncode == 2, f"guard allowed {command!r}"

# ask_tf_apply.py: any tf-toolbox apply asks a person; everything else passes silently.
for command in [
    f"scripts/tf-toolbox.sh apply bootstrap x {SHA}",
    "bash scripts/tf-toolbox.sh apply infra x y",
]:
    out = hook("ask_tf_apply.py", command)
    decision = json.loads(out.stdout)["hookSpecificOutput"]["permissionDecision"]
    assert out.returncode == 0 and decision == "ask", (command, out.stdout)
for command in ["scripts/tf-toolbox.sh plan bootstrap", "git status"]:
    out = hook("ask_tf_apply.py", command)
    assert out.returncode == 0 and out.stdout == "", (command, out.stdout)


# tf_risk.py --gate: the apply decision. Only exit 0 lets tf-toolbox.sh apply.
def gate(plan_json):
    return run("tf_risk.py", plan_json, "-", "--root", "bootstrap", "--gate").returncode


def change(kind, actions):
    return {"address": f"{kind}.x", "type": kind, "change": {"actions": actions}}


def plan(*changes):
    return json.dumps({"resource_changes": list(changes)})


assert gate(plan()) == 0, "no-change plan must be applicable"
assert gate(plan(change("azurerm_role_assignment", ["update"]))) == 0, "REVIEW applies"
assert gate(plan(change("azurerm_role_assignment", ["delete"]))) == 0, "approved DANGER applies"
assert gate(plan(change("azurerm_storage_account", ["delete", "create"]))) != 0, "BLOCK refuses"
# The P0 bug: a broken `terraform show` feeds the checker nothing. That must refuse.
assert gate("") != 0, "empty input must refuse"
assert gate("not json") != 0, "garbage input must refuse"

# redact.py: CI/CD output loses IDs, and the canary withholds anything redaction missed.
SUB = "12345678-aaaa-bbbb-cccc-1234567890ab"
ARM = {"ARM_SUBSCRIPTION_ID": SUB, "ARM_USE_OIDC": "true"}
b64 = base64.b64encode(f"subscriptionId={SUB};tenantId=x".encode()).decode()
out = run(
    "redact.py", f"rg: Read complete [id={b64}]\nid = /subscriptions/{SUB}/rg\nsha {SHA}\n", env=ARM
)
assert out.returncode == 0, out.stdout
assert out.stdout == f"rg: Read complete\nid = /subscriptions/<guid>/rg\nsha {SHA}\n", out.stdout
# base64 outside [id=...]: redaction misses it, so the canary must catch it.
out = run("redact.py", f'config = "{b64}"\n', env=ARM)
assert out.returncode == 1 and b64 not in out.stdout, out.stdout
assert "ARM_SUBSCRIPTION_ID" in out.stdout, out.stdout


# guard_ids.py: agent text bound for GitHub or Linear can't carry a known ID (exit 2 blocks).
KNOWN = json.dumps({"AZURE_SUBSCRIPTION_ID": SUB})


def post(tool, tool_input, known=KNOWN):
    stdin = json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": str(HERE)})
    return run("guard_ids.py", stdin, env={"OLIST_KNOWN_IDS": known}).returncode


with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
    f.write(f"Evidence: /subscriptions/{SUB}\n")
body = f.name
LINEAR = "mcp__plugin_productivity_linear__save_comment"
for tool, tool_input in [
    ("Bash", {"command": f'gh pr comment 6 --body "id {SUB}"'}),
    ("Bash", {"command": f'gh pr create --title t --body "see {SUB[:8]}"'}),  # a prefix is enough
    ("Bash", {"command": f"gh pr edit 6 --body {b64}"}),
    ("Bash", {"command": f"gh pr create --body-file {body}"}),
    ("Bash", {"command": f"gh api repos/o/r/issues/1/comments -F body=@{body}"}),
    (LINEAR, {"issueId": "AIE-1", "body": f"state account {SUB.upper()}"}),
]:
    assert post(tool, tool_input) == 2, f"guard_ids allowed {tool} {tool_input}"
for tool, tool_input in [
    ("Bash", {"command": 'gh pr create --title t --body "all clean"'}),
    ("Bash", {"command": f"echo {SUB}"}),  # not posted anywhere
    ("mcp__plugin_productivity_linear__get_issue", {"id": SUB}),  # a read
    (LINEAR, {"issueId": "AIE-1", "body": "clean"}),
]:
    assert post(tool, tool_input) == 0, f"guard_ids blocked {tool} {tool_input}"
assert post(LINEAR, {"body": "clean"}, known="not json") == 2, "unknown IDs must block"
Path(body).unlink()


# check_base.py: a session in a checkout behind origin/main is told so; otherwise silence.
def base(repo):
    return run("check_base.py", "", env={"CLAUDE_PROJECT_DIR": str(repo)})


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    def git(*args):
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            check=True,
            capture_output=True,
        )

    git("init", "-q", "-b", "main", str(tmp / "origin"))
    for n in range(3):
        git("-C", str(tmp / "origin"), "commit", "-q", "--allow-empty", "-m", str(n))
    git("clone", "-q", str(tmp / "origin"), str(tmp / "clone"))
    out = base(tmp / "clone")
    assert out.returncode == 0 and out.stdout == "", f"up to date must be silent: {out.stdout!r}"
    git("-C", str(tmp / "clone"), "reset", "-q", "--hard", "HEAD~2")
    out = base(tmp / "clone")
    assert out.returncode == 0 and "2 commit(s) behind origin/main" in out.stdout, out.stdout
    out = base(tmp)  # not a git checkout
    assert out.returncode == 0 and out.stdout == "", f"outside git must be silent: {out.stdout!r}"

print("guards: all checks passed")
